"""Lease blog indexing jobs and scope access to their source records."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_SCOPE = "current_setting('rubrica.actor_kind', true) = 'system'"


def _job_policy(kinds: str) -> None:
    scope = f"{_SCOPE} AND kind IN ({kinds})"
    op.execute(f"ALTER POLICY ingest_select ON jobs USING ({scope})")
    op.execute(f"""
        ALTER POLICY ingest_update ON jobs USING ({scope})
        WITH CHECK ({scope} AND status IN ('queued', 'parsing', 'done', 'failed'))
    """)


def upgrade() -> None:
    _job_policy("'parse_material', 'parse_submission', 'index_blog'")
    op.execute("""
        CREATE FUNCTION public.blog_index_source(wanted_origin text, wanted_id uuid)
        RETURNS TABLE (author_id uuid, body text)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        DECLARE
            scoped_course uuid := NULLIF(current_setting('rubrica.course_id', true), '')::uuid;
        BEGIN
            IF current_setting('rubrica.actor_kind', true) IS DISTINCT FROM 'system'
               OR scoped_course IS NULL THEN
                RETURN;
            END IF;
            IF wanted_origin = 'post' THEN
                RETURN QUERY
                    SELECT p.author_id, p.body::text
                    FROM public.blog_posts p
                    WHERE p.id = wanted_id AND p.course_id = scoped_course
                    FOR KEY SHARE OF p;
            ELSIF wanted_origin = 'comment' THEN
                RETURN QUERY
                    SELECT c.author_id, c.body::text
                    FROM public.blog_comments c
                    JOIN public.blog_posts p ON p.id = c.post_id
                    WHERE c.id = wanted_id AND p.course_id = scoped_course
                    FOR KEY SHARE OF c, p;
            END IF;
        END;
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.blog_index_source(text, uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.blog_index_source(text, uuid) TO rubrica_ingest")
    op.execute("""
        CREATE FUNCTION public.delete_blog_origin_chunks()
        RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        BEGIN
            DELETE FROM public.blog_chunks WHERE origin_id = OLD.id AND origin = TG_ARGV[0];
            RETURN OLD;
        END;
        $$;
    """)
    op.execute("""
        CREATE FUNCTION public.enqueue_blog_origin()
        RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        DECLARE
            source_course uuid;
        BEGIN
            IF TG_ARGV[0] = 'post' THEN
                source_course := NEW.course_id;
            ELSE
                SELECT p.course_id INTO STRICT source_course
                FROM public.blog_posts p WHERE p.id = NEW.post_id;
            END IF;
            INSERT INTO public.jobs (kind, status, payload)
            VALUES ('index_blog', 'queued', jsonb_build_object(
                'course_id', source_course, 'origin', TG_ARGV[0], 'origin_id', NEW.id
            ));
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.enqueue_blog_origin() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER enqueue_blog_post AFTER INSERT ON blog_posts
        FOR EACH ROW EXECUTE FUNCTION public.enqueue_blog_origin('post')
    """)
    op.execute("""
        CREATE TRIGGER enqueue_blog_comment AFTER INSERT ON blog_comments
        FOR EACH ROW EXECUTE FUNCTION public.enqueue_blog_origin('comment')
    """)
    op.execute("""
        INSERT INTO jobs (kind, status, payload)
        SELECT 'index_blog', 'queued', jsonb_build_object(
            'course_id', p.course_id, 'origin', 'post', 'origin_id', p.id
        )
        FROM blog_posts p
        WHERE NOT EXISTS (
            SELECT 1 FROM jobs j WHERE j.kind = 'index_blog'
            AND j.payload ->> 'origin' = 'post' AND j.payload ->> 'origin_id' = p.id::text
        )
        UNION ALL
        SELECT 'index_blog', 'queued', jsonb_build_object(
            'course_id', p.course_id, 'origin', 'comment', 'origin_id', c.id
        )
        FROM blog_comments c JOIN blog_posts p ON p.id = c.post_id
        WHERE NOT EXISTS (
            SELECT 1 FROM jobs j WHERE j.kind = 'index_blog'
            AND j.payload ->> 'origin' = 'comment' AND j.payload ->> 'origin_id' = c.id::text
        )
    """)
    op.execute("REVOKE ALL ON FUNCTION public.delete_blog_origin_chunks() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER delete_indexed_blog_post AFTER DELETE ON blog_posts
        FOR EACH ROW EXECUTE FUNCTION public.delete_blog_origin_chunks('post')
    """)
    op.execute("""
        CREATE TRIGGER delete_indexed_blog_comment AFTER DELETE ON blog_comments
        FOR EACH ROW EXECUTE FUNCTION public.delete_blog_origin_chunks('comment')
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER enqueue_blog_comment ON blog_comments")
    op.execute("DROP TRIGGER enqueue_blog_post ON blog_posts")
    op.execute("DROP FUNCTION public.enqueue_blog_origin()")
    op.execute("DROP TRIGGER delete_indexed_blog_comment ON blog_comments")
    op.execute("DROP TRIGGER delete_indexed_blog_post ON blog_posts")
    op.execute("DROP FUNCTION public.delete_blog_origin_chunks()")
    op.execute("DROP FUNCTION public.blog_index_source(text, uuid)")
    _job_policy("'parse_material', 'parse_submission'")
