import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

PASSWORD = "senha-forte-1"


def registration(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"email": "ana@x.com", "username": "ana", "password": PASSWORD}
    body.update(overrides)
    return body


def rows(db: Path, query: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(db) as conn:
        return conn.execute(query).fetchall()


def user_count(db: Path) -> int:
    return int(rows(db, "SELECT COUNT(*) FROM users")[0][0])


class Users:
    """Cadastra Usuários e troca o cookie do cliente entre eles."""

    def __init__(self, client: TestClient) -> None:
        self._client = client
        self._tokens: dict[str, str] = {}

    def add(self, name: str) -> None:
        self._client.cookies.clear()
        body = registration(email=f"{name}@x.com", username=name)
        response = self._client.post("/api/auth/register", json=body)
        assert response.status_code == 201
        self._tokens[name] = response.cookies["snook_session"]
        # Cookie `Secure` em localhost não volta por http no TestClient: grava sem a flag.
        self.use(name)

    def use(self, name: str) -> None:
        self._client.cookies.clear()
        self._client.cookies.set("snook_session", self._tokens[name])
