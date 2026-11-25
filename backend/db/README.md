# Rubrica database

On `make up`, the one-shot `migrate` service waits for PostgreSQL, applies
Alembic revisions as `rubrica_owner`, then exits. Database-backed services
wait for that successful exit. Compose mounts the owner credential only in
`db` and `migrate`. Each database-backed runtime service gets its own
credential and `DB_ROLE`.

Use `docker compose -f deploy/docker-compose.yml ps --all migrate` to check
the migration exit status, and `docker compose -f deploy/docker-compose.yml
logs migrate` for its output.

## Service transactions

Open database work with `backend.db.session(role, context)`. Build
`SessionContext` from the verified session, capability token or job. For
course-scoped operations, supply `course_id`. A grading run also supplies
`run_id`. The context manager commits on success and rolls back on error.
For insert-only tables, supply any ID the caller needs in advance and use
an insert without `RETURNING`, which would require a read grant.

The web role can read audit rows for instructors in their enrolled course.
All runtime roles can append audit events, and the table rejects mutation.
The web role can approve a pending grade and the release role can release
an approved grade through `release_approved_grade(grade_id)`. The function
returns whether it changed a row. The approval and release handlers are responsible for
verifying the instructor's recent re-authentication before opening their
transactions.

D1 covers the grants required by the current database contract. Owners of
identity, background jobs, and other later services should add their grants
and policies alongside the corresponding service paths through new migrations.

## Verification

`tests/authz/test_d1_database.py` exercises the migrations, service roles, and
row-level policies with synthetic data. To opt in, point
`RUBRICA_D1_TEST_PORT` at a disposable PostgreSQL 18/pgvector instance bound to
loopback with an empty `rubrica` database and a local `rubrica_owner` login.
Run `uv run --project backend --frozen pytest tests/authz/test_d1_database.py`
from the repository root. The fixture applies and rolls back the schema and
uses temporary database roles.
