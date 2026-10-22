from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BUSY_TIMEOUT_MS = 5000
_ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "alembic"


class Base(DeclarativeBase):
    """Base declarativa única; cada módulo é dono das próprias tabelas."""


def create_db_engine(database_path: Path | str) -> Engine:
    engine = create_engine(f"sqlite:///{database_path}")

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        # Transação sob controle do SQLAlchemy (evento "begin" abaixo), não do driver.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        finally:
            cursor.close()

    @event.listens_for(engine, "begin")
    def _on_begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def upgrade_database(database_path: Path | str) -> None:
    """Roda `alembic upgrade head` no banco informado."""
    config = Config()
    config.set_main_option("script_location", str(_ALEMBIC_DIR))
    config.attributes["database_path"] = Path(database_path)
    command.upgrade(config, "head")
