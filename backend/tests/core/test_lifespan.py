import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.db import _ALEMBIC_DIR, migrate_with_backup
from snook.core.runlock import RunLockError
from snook.core.settings import Settings
from snook.main import create_app

_REVISION = """
from alembic import op
import sqlalchemy as sa

revision = "{rev}"
down_revision = {down!r}
branch_labels = None
depends_on = None


def upgrade() -> None:
    {body}
"""


def _script_dir(tmp_path: Path, revisions: list[tuple[str, str | None, str]]) -> Path:
    """Diretório Alembic temporário: env.py e mako reais, revisões de teste."""
    target = tmp_path / "alembic_test"
    shutil.copytree(_ALEMBIC_DIR, target, ignore=shutil.ignore_patterns("versions"))
    (target / "versions").mkdir()
    for rev, down, body in revisions:
        (target / "versions" / f"{rev}.py").write_text(
            _REVISION.format(rev=rev, down=down, body=body)
        )
    return target


_CREATE_T = 'op.create_table("t", sa.Column("id", sa.Integer, primary_key=True))'
_CREATE_U = 'op.create_table("u", sa.Column("id", sa.Integer, primary_key=True))'
_BOOM = 'raise RuntimeError("migração quebrada")'


def _tables(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def _backups(db: Path) -> list[str]:
    return sorted(p.name for p in db.parent.glob(db.name + ".bak-*"))


def test_app_holds_the_lock_and_a_second_app_fails(settings: Settings) -> None:
    with (
        TestClient(create_app(settings)),
        pytest.raises(RunLockError),
        TestClient(create_app(settings)),
    ):
        pass
    with TestClient(create_app(settings)):
        pass


def test_lock_is_released_when_app_stops(settings: Settings) -> None:
    with TestClient(create_app(settings)):
        pass
    with TestClient(create_app(settings), base_url="http://localhost") as client:
        assert client.get("/api/health").status_code == 200


def test_audios_tmp_is_emptied_on_startup(settings: Settings) -> None:
    tmp = settings.audio_root / ".tmp"
    (tmp / "sub").mkdir(parents=True)
    (tmp / "sub" / "x.flac").write_bytes(b"x")
    (tmp / "orfao").write_bytes(b"x")
    outside = settings.audio_root / "keep.txt"
    outside.write_text("keep")
    (tmp / "link").symlink_to(outside)
    with TestClient(create_app(settings)):
        pass
    assert tmp.is_dir()
    assert list(tmp.iterdir()) == []
    assert outside.read_text() == "keep"


def test_audios_tmp_is_created_when_missing(settings: Settings) -> None:
    with TestClient(create_app(settings)):
        pass
    assert (settings.audio_root / ".tmp").is_dir()


def test_fresh_database_migrates_without_backup(tmp_path: Path) -> None:
    db = tmp_path / "snook.db"
    scripts = _script_dir(tmp_path, [("0001", None, _CREATE_T)])
    migrate_with_backup(db, scripts)
    assert "t" in _tables(db)
    assert _backups(db) == []


def test_backup_exists_before_migration_with_current_revision(tmp_path: Path) -> None:
    db = tmp_path / "snook.db"
    scripts = _script_dir(tmp_path, [("0001", None, _CREATE_T)])
    migrate_with_backup(db, scripts)
    scripts = _script_dir(tmp_path / "v2", [("0001", None, _CREATE_T), ("0002", "0001", _CREATE_U)])
    migrate_with_backup(db, scripts)
    assert _backups(db) == ["snook.db.bak-0001"]
    backup = db.parent / "snook.db.bak-0001"
    assert _tables(backup) >= {"t"}
    assert "u" not in _tables(backup)
    assert "u" in _tables(db)
    assert (backup.stat().st_mode & 0o777) == 0o600


def test_only_last_backup_is_kept_after_successful_migration(tmp_path: Path) -> None:
    db = tmp_path / "snook.db"
    revs = [("0001", None, _CREATE_T)]
    migrate_with_backup(db, _script_dir(tmp_path / "a", revs))
    revs.append(("0002", "0001", _CREATE_U))
    migrate_with_backup(db, _script_dir(tmp_path / "b", revs))
    revs.append(
        ("0003", "0002", 'op.create_table("v", sa.Column("id", sa.Integer, primary_key=True))')
    )
    migrate_with_backup(db, _script_dir(tmp_path / "c", revs))
    assert _backups(db) == ["snook.db.bak-0002"]


def test_no_pending_migration_keeps_existing_backup(tmp_path: Path) -> None:
    db = tmp_path / "snook.db"
    revs = [("0001", None, _CREATE_T)]
    migrate_with_backup(db, _script_dir(tmp_path / "a", revs))
    revs.append(("0002", "0001", _CREATE_U))
    scripts = _script_dir(tmp_path / "b", revs)
    migrate_with_backup(db, scripts)
    migrate_with_backup(db, scripts)
    assert _backups(db) == ["snook.db.bak-0001"]


def test_failed_migration_raises_and_keeps_backup(tmp_path: Path) -> None:
    db = tmp_path / "snook.db"
    migrate_with_backup(db, _script_dir(tmp_path / "a", [("0001", None, _CREATE_T)]))
    broken = _script_dir(tmp_path / "b", [("0001", None, _CREATE_T), ("0002", "0001", _BOOM)])
    with pytest.raises(RuntimeError, match="migração quebrada"):
        migrate_with_backup(db, broken)
    assert _backups(db) == ["snook.db.bak-0001"]
    assert "t" in _tables(db)
