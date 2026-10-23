import sqlite3
from pathlib import Path
from typing import Any

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
