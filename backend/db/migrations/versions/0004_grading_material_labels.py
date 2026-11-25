"""Allow the grader to label sources for its scoped published material."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT SELECT (id, course_id, status, source_kind) ON materials TO rubrica_grading")
    op.execute("""
        CREATE POLICY grading_select ON materials FOR SELECT TO rubrica_grading
        USING (
            status = 'published'
            AND EXISTS (SELECT 1 FROM assignments a WHERE a.course_id = materials.course_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY grading_select ON materials")
    op.execute(
        "REVOKE SELECT (id, course_id, status, source_kind) ON materials FROM rubrica_grading"
    )
