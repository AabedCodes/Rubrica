"""Allow the ingestion worker to lease and finish document parser jobs."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_SCOPE = (
    "current_setting('rubrica.actor_kind', true) = 'system' "
    "AND kind IN ('parse_material', 'parse_submission')"
)


def upgrade() -> None:
    op.execute("GRANT SELECT ON jobs TO rubrica_ingest")
    op.execute("GRANT UPDATE (status, attempts, run_after, locked_at) ON jobs TO rubrica_ingest")
    op.execute(f"CREATE POLICY ingest_select ON jobs FOR SELECT TO rubrica_ingest USING ({_SCOPE})")
    op.execute(f"""
        CREATE POLICY ingest_update ON jobs FOR UPDATE TO rubrica_ingest
        USING ({_SCOPE})
        WITH CHECK ({_SCOPE} AND status IN ('queued', 'parsing', 'done', 'failed'))
    """)

    op.execute("""
        CREATE FUNCTION public.store_parsed_submission(wanted uuid, digest text, contents text)
        RETURNS boolean
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $$
            WITH changed AS (
                UPDATE public.submissions s
                SET extracted_text = contents
                FROM public.assignments a
                WHERE s.id = wanted AND s.assignment_id = a.id AND s.sha256 = digest
                  AND current_setting('rubrica.actor_kind', true) = 'system'
                  AND a.course_id = NULLIF(current_setting('rubrica.course_id', true), '')::uuid
                RETURNING 1
            )
            SELECT EXISTS (SELECT 1 FROM changed);
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.store_parsed_submission(uuid,text,text) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.store_parsed_submission(uuid,text,text) TO rubrica_ingest"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION public.store_parsed_submission(uuid,text,text)")
    op.execute("DROP POLICY ingest_update ON jobs")
    op.execute("DROP POLICY ingest_select ON jobs")
    op.execute("REVOKE UPDATE (status, attempts, run_after, locked_at) ON jobs FROM rubrica_ingest")
    op.execute("REVOKE SELECT ON jobs FROM rubrica_ingest")
