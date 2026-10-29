import logging
import sqlite3
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger("snook.db")

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


def _alembic_config(database_path: Path | str, script_location: Path) -> Config:
    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.attributes["database_path"] = Path(database_path)
    return config


def upgrade_database(database_path: Path | str, script_location: Path = _ALEMBIC_DIR) -> None:
    """Roda `alembic upgrade head` no banco informado."""
    command.upgrade(_alembic_config(database_path, script_location), "head")


def _current_revision(database_path: Path) -> str:
    """Revisão gravada no banco; `base` se ainda não há tabela de versão."""
    with sqlite3.connect(database_path) as conn:
        try:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        except sqlite3.OperationalError:
            return "base"
    return str(row[0]) if row else "base"


def backup_database(database_path: Path, backup_path: Path) -> None:
    backup_path.unlink(missing_ok=True)
    source = sqlite3.connect(database_path)
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    backup_path.chmod(0o600)


def migrate_with_backup(database_path: Path | str, script_location: Path = _ALEMBIC_DIR) -> None:
    """Copia o banco para `<banco>.bak-<revisão>` antes de migrar e, depois do sucesso,
    mantém só essa cópia (SEC-22). Sem migração pendente, não mexe em backup."""
    database_path = Path(database_path)
    head = ScriptDirectory.from_config(
        _alembic_config(database_path, script_location)
    ).get_current_head()
    backup_path: Path | None = None
    if database_path.exists() and head is not None:
        current = _current_revision(database_path)
        if current != head:
            backup_path = database_path.with_name(f"{database_path.name}.bak-{current}")
            backup_database(database_path, backup_path)
    try:
        upgrade_database(database_path, script_location)
    except Exception:
        logger.error("database migration failed; backup kept at %s", backup_path)
        raise
    if backup_path is not None:
        for old in database_path.parent.glob(f"{database_path.name}.bak-*"):
            if old != backup_path:
                old.unlink()
