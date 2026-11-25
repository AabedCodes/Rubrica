"""Run Alembic using the owner credentials mounted on the migration service."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.db.session import OWNER_ROLE, _create_engine


def migration_config() -> Config:
    return Config(str(Path(__file__).with_name("alembic.ini")))


def main() -> None:
    engine = _create_engine(OWNER_ROLE, "db_owner_password")
    try:
        with engine.connect() as connection:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
