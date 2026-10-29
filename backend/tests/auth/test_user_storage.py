from pathlib import Path

import bcrypt
from fastapi.testclient import TestClient

from snook.core.db import upgrade_database
from snook.core.settings import Settings
from tests.auth.helpers import PASSWORD, registration, rows


def test_password_column_holds_bcrypt_hash(client: TestClient, settings: Settings) -> None:
    """`auth` 9."""
    assert client.post("/api/auth/register", json=registration()).status_code == 201
    [(stored,)] = rows(settings.database_path, "SELECT password_hash FROM users")
    assert stored.startswith("$2b$")
    assert bcrypt.checkpw(PASSWORD.encode(), stored.encode())


def test_bcrypt_cost_comes_from_settings(client: TestClient, settings: Settings) -> None:
    client.post("/api/auth/register", json=registration())
    [(stored,)] = rows(settings.database_path, "SELECT password_hash FROM users")
    assert stored.startswith(f"$2b${settings.bcrypt_rounds:02d}$")


def test_email_uniqueness_ignores_case(client: TestClient, settings: Settings) -> None:
    """`auth` 6, email."""
    client.post("/api/auth/register", json=registration(email="Ana@x.com", username="ana"))
    response = client.post(
        "/api/auth/register", json=registration(email="ana@x.com", username="outra")
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert rows(settings.database_path, "SELECT email, email_norm FROM users") == [
        ("Ana@x.com", "ana@x.com")
    ]


def test_username_uniqueness_ignores_case(client: TestClient, settings: Settings) -> None:
    """`auth` 6, nome de usuário."""
    client.post("/api/auth/register", json=registration(email="a@x.com", username="Ana"))
    response = client.post("/api/auth/register", json=registration(email="b@x.com", username="ana"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "username_taken"
    assert rows(settings.database_path, "SELECT username, username_norm FROM users") == [
        ("Ana", "ana")
    ]


def test_password_text_not_in_sqlite(client: TestClient, settings: Settings) -> None:
    """`auth` 10, armazenamento (SEC-05). Lê os bytes do banco e do WAL."""
    client.post("/api/auth/register", json=registration())
    client.close()
    db = settings.database_path
    for path in (db, Path(f"{db}-wal")):
        if path.exists():
            assert PASSWORD.encode() not in path.read_bytes()


def test_migration_creates_auth_tables(tmp_path: Path) -> None:
    db = tmp_path / "fresh.db"
    upgrade_database(db)
    tables = {name for (name,) in rows(db, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "sessions"} <= tables
