import logging
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from snook.core.db import create_db_engine, create_session_factory, upgrade_database
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers import service
from snook.modules.llm_providers.crypto import KeyCipher, SealedKey
from tests.auth.helpers import rows

KEY_A = bytes(range(32))
KEY_B = bytes(range(32, 64))
API_KEY = "sk-test-0123456789abcdef"
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "snook.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        for user_id in ("u1", "u2"):
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, 'hash', '2026-10-23T12:00:00Z')",
                (user_id, f"{user_id}@x.com", f"{user_id}@x.com", user_id, user_id),
            )
    return path


@pytest.fixture
def factory(db: Path) -> Iterator[sessionmaker[Session]]:
    engine = create_db_engine(db)
    yield create_session_factory(engine)
    engine.dispose()


def _uow(factory: sessionmaker[Session]) -> UnitOfWork:
    return UnitOfWork(factory, lambda _event: None)


def _save(factory: sessionmaker[Session], cipher: KeyCipher, user_id: str = "u1") -> None:
    with _uow(factory) as uow:
        service.save_config(
            uow,
            cipher,
            user_id=user_id,
            provider="openai",
            model="gpt-4o-mini",
            context_window=128000,
            api_key=API_KEY,
            base_url=None,
            now=NOW,
        )


def test_stored_key_differs_and_decrypts_with_master_key(
    factory: sessionmaker[Session], db: Path
) -> None:
    """`llm-providers` 12, transversal 6."""
    cipher = KeyCipher(KEY_A)
    _save(factory, cipher)
    [(ciphertext, nonce, version, mask, status)] = rows(
        db, "SELECT key_ciphertext, key_nonce, key_version, key_mask, key_status FROM llm_configs"
    )
    assert API_KEY.encode() not in ciphertext
    sealed = SealedKey(ciphertext=ciphertext, nonce=nonce, version=version)
    assert cipher.decrypt(sealed, user_id="u1", provider="openai") == API_KEY
    assert (mask, status) == ("sk-...cdef", "ok")


def test_key_text_not_in_sqlite_files(factory: sessionmaker[Session], db: Path) -> None:
    """SEC-07: lê os bytes do banco e do WAL."""
    _save(factory, KeyCipher(KEY_A))
    for path in (db, Path(f"{db}-wal")):
        if path.exists():
            assert API_KEY.encode() not in path.read_bytes()


def test_read_key_returns_plaintext(factory: sessionmaker[Session]) -> None:
    cipher = KeyCipher(KEY_A)
    _save(factory, cipher)
    with _uow(factory) as uow:
        assert service.read_api_key(uow, cipher, user_id="u1", provider="openai") == API_KEY


def test_changed_master_key_marks_unreadable_without_error(
    factory: sessionmaker[Session], db: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ADR-0009: mestra trocada sem rotação marca `unreadable`, sem 500 e sem vazar."""
    _save(factory, KeyCipher(KEY_A))
    caplog.set_level(logging.DEBUG)
    with _uow(factory) as uow:
        assert service.read_api_key(uow, KeyCipher(KEY_B), user_id="u1", provider="openai") is None
    [(status, ciphertext)] = rows(db, "SELECT key_status, key_ciphertext FROM llm_configs")
    assert status == "unreadable"
    assert ciphertext is not None  # nada é apagado sozinho
    assert API_KEY not in caplog.text


def test_new_key_clears_unreadable(factory: sessionmaker[Session], db: Path) -> None:
    _save(factory, KeyCipher(KEY_A))
    cipher_b = KeyCipher(KEY_B)
    with _uow(factory) as uow:
        service.read_api_key(uow, cipher_b, user_id="u1", provider="openai")
    _save(factory, cipher_b)
    assert rows(db, "SELECT key_status FROM llm_configs") == [("ok",)]


def test_user_delete_cascades_configs(factory: sessionmaker[Session], db: Path) -> None:
    """`04-data-model.md`: `ON DELETE CASCADE` de `users`."""
    cipher = KeyCipher(KEY_A)
    _save(factory, cipher, user_id="u1")
    _save(factory, cipher, user_id="u2")
    engine = create_db_engine(db)  # liga foreign_keys
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM users WHERE id = 'u1'")
    engine.dispose()
    assert rows(db, "SELECT user_id FROM llm_configs") == [("u2",)]


def test_one_row_per_user_and_provider(factory: sessionmaker[Session], db: Path) -> None:
    cipher = KeyCipher(KEY_A)
    _save(factory, cipher)
    _save(factory, cipher)
    assert rows(db, "SELECT COUNT(*) FROM llm_configs") == [(1,)]


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO llm_configs (user_id, provider, model, context_window, key_status, "
        "is_active, created_at, updated_at) VALUES ('u1', 'gemini', 'm', 1, 'ok', 0, 't', 't')",
        "INSERT INTO llm_configs (user_id, provider, model, context_window, key_status, "
        "is_active, created_at, updated_at) VALUES ('u1', 'openai', 'm', 0, 'ok', 0, 't', 't')",
        "INSERT INTO llm_configs (user_id, provider, model, context_window, key_status, "
        "is_active, created_at, updated_at) VALUES ('u1', 'openai', 'm', 1, 'bad', 0, 't', 't')",
    ],
)
def test_check_constraints(db: Path, sql: str) -> None:
    with sqlite3.connect(db) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)


def test_at_most_one_active_per_user(db: Path) -> None:
    """`llm-providers` 20: índice único parcial."""
    insert = (
        "INSERT INTO llm_configs (user_id, provider, model, context_window, key_status, "
        "is_active, created_at, updated_at) VALUES ('u1', ?, 'm', 1, 'ok', 1, 't', 't')"
    )
    with sqlite3.connect(db) as conn:
        conn.execute(insert, ("openai",))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("anthropic",))


@pytest.mark.parametrize(
    ("key", "mask"),
    [("sk-test-0123456789abcdef", "sk-...cdef"), ("123456789012", "123...9012"), ("short", "...")],
)
def test_mask_key(key: str, mask: str) -> None:
    """`llm-providers` 3: 3 primeiros e 4 últimos; menos de 12 vira `...`."""
    assert service.mask_key(key) == mask
