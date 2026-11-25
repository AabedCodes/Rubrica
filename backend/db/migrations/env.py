"""Alembic must use an explicitly opened migration-owner connection."""

from alembic import context

from backend.db.models import Base


def run_migrations() -> None:
    connection = context.config.attributes.get("connection")
    if connection is None or context.is_offline_mode():
        raise RuntimeError("Run migrations with python -m backend.db.migrate")

    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('rubrica-alembic'))")
        context.run_migrations()


run_migrations()
