import base64
import logging
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from snook import cli
from snook.core.db import create_db_engine, create_session_factory, upgrade_database
from snook.core.runlock import RunLock
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers import service
from snook.modules.llm_providers.crypto import KeyCipher, SealedKey
from tests.auth.helpers import rows

KEY_OLD = bytes(range(32))
KEY_NEW = bytes(range(32, 64))
API_KEYS = {"u1": "sk-TesteChave-0123456789abcdef", "u2": "sk-OutraChave-fedcba9876543210"}


def _b64(key: bytes) -> str:
    return base64.urlsafe_b64encode(key).decode()


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "snook.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        for user_id in API_KEYS:
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, 'hash', '2026-10-23T12:00:00Z')",
                (user_id, f"{user_id}@x.com", f"{user_id}@x.com", user_id, user_id),
            )
    engine = create_db_engine(path)
    old = KeyCipher(KEY_OLD)
    with UnitOfWork(create_session_factory(engine), lambda _e: None) as uow:
        for user_id, api_key in API_KEYS.items():
            service.save_config(
                uow,
                old,
                user_id=user_id,
                provider="openai",
                model="gpt-4o-mini",
                context_window=128000,
                api_key=api_key,
                base_url=None,
                now=datetime(2026, 10, 23, tzinfo=UTC),
            )
    engine.dispose()
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.setenv("SNOOK_MASTER_KEY", _b64(KEY_NEW))
    monkeypatch.setenv("SNOOK_MASTER_KEY_PREVIOUS", _b64(KEY_OLD))
    monkeypatch.chdir(tmp_path)  # sem `.env` do repo
    yield path


def _stored(db: Path) -> list[tuple[str, bytes, bytes, int, str]]:
    return rows(
        db,
        "SELECT user_id, key_ciphertext, key_nonce, key_version, key_status "
        "FROM llm_configs ORDER BY user_id",
    )


def test_rotation_reencrypts_every_key_with_new_master(db: Path) -> None:
    """ADR-0009: depois da rotação, toda chave decifra com a nova e o valor mudou."""
    before = _stored(db)
    assert cli.main(["rotate-master-key"]) == 0
    after = _stored(db)
    new = KeyCipher(KEY_NEW)
    for (user_id, old_ct, *_), (_, ciphertext, nonce, version, status) in zip(
        before, after, strict=True
    ):
        assert ciphertext != old_ct
        assert status == "ok"
        sealed = SealedKey(ciphertext=ciphertext, nonce=nonce, version=version)
        assert new.decrypt(sealed, user_id=user_id, provider="openai") == API_KEYS[user_id]


def test_rotation_keeps_backup(db: Path) -> None:
    assert cli.main(["rotate-master-key"]) == 0
    backup = db.with_name("snook.db.bak-rotate")
    assert backup.exists()
    assert rows(backup, "SELECT COUNT(*) FROM llm_configs") == [(2,)]


def test_busy_lock_stops_without_writing(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """SEC-24, ADR-0006: backend no ar, comando para com erro."""
    before = _stored(db)
    with RunLock(db.with_name("snook.lock")):
        assert cli.main(["rotate-master-key"]) == 1
    assert _stored(db) == before
    assert not db.with_name("snook.db.bak-rotate").exists()
    assert "snook.lock" in capsys.readouterr().err


def test_requires_previous_key(
    db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SNOOK_MASTER_KEY_PREVIOUS")
    before = _stored(db)
    assert cli.main(["rotate-master-key"]) == 1
    assert _stored(db) == before
    assert "SNOOK_MASTER_KEY_PREVIOUS" in capsys.readouterr().err


def test_no_key_in_output_or_log(
    db: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-07, SEC-20."""
    caplog.set_level(logging.DEBUG)
    assert cli.main(["rotate-master-key"]) == 0
    captured = capsys.readouterr()
    text = captured.out + captured.err + caplog.text
    secrets = [*API_KEYS.values(), _b64(KEY_OLD), _b64(KEY_NEW)]
    for secret in secrets:
        assert secret not in text
    assert "operator.master_key_rotated" in caplog.text


def test_undecryptable_key_marked_unreadable_and_kept(
    db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chave de outra mestra: fica `unreadable`, nada é apagado; as demais giram."""
    stranger = KeyCipher(bytes(range(64, 96))).encrypt(
        API_KEYS["u2"], user_id="u2", provider="openai"
    )
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE llm_configs SET key_ciphertext = ?, key_nonce = ?, key_version = ? "
            "WHERE user_id = 'u2'",
            (stranger.ciphertext, stranger.nonce, stranger.version),
        )
    assert cli.main(["rotate-master-key"]) == 0
    after = {row[0]: row for row in _stored(db)}
    assert after["u1"][4] == "ok"
    assert after["u2"][4] == "unreadable"
    assert after["u2"][1] == stranger.ciphertext
