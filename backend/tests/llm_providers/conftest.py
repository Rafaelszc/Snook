import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from snook.core.clock import FakeClock
from snook.core.db import create_db_engine, create_session_factory, upgrade_database
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.adapters.base import GenerationRequest, LLMError, ProviderTarget
from tests.auth.helpers import Users, rows

# Nomes liberados no .gitleaks.toml.
API_KEY = "sk-TesteChave-0123456789abcdef"
OTHER_KEY = "sk-OutraChave-9876543210fedcba"
URL = "/api/llm-configs"


class FakeAdapter:
    """Adapter trocável: `error` define a falha do próximo teste; `calls` guarda os alvos."""

    def __init__(self) -> None:
        self.error: LLMError | None = None
        self.calls: list[ProviderTarget] = []
        self.models: list[str] = ["model-a", "model-b"]

    def test_connection(self, target: ProviderTarget) -> None:
        self.calls.append(target)
        if self.error is not None:
            raise self.error

    def list_models(self, target: ProviderTarget) -> list[str]:
        self.calls.append(target)
        if self.error is not None:
            raise self.error
        return self.models

    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        raise NotImplementedError


@pytest.fixture
def clock(app: FastAPI) -> FakeClock:
    fake = FakeClock(datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    app.state.clock = fake
    return fake


@pytest.fixture
def fakes(app: FastAPI) -> dict[str, FakeAdapter]:
    adapters = {name: FakeAdapter() for name in ("openai", "anthropic", "deepseek", "ollama")}
    app.state.llm_adapters = adapters
    return adapters


@pytest.fixture
def db(settings: Settings) -> Path:
    return settings.database_path


@pytest.fixture
def users(client: TestClient, clock: FakeClock, fakes: dict[str, FakeAdapter]) -> Users:
    """Ana e Bia cadastradas; o cliente fica como Ana."""
    found = Users(client)
    found.add("bia")
    found.add("ana")
    return found


@pytest.fixture
def ana(users: Users, client: TestClient) -> Iterator[TestClient]:
    users.use("ana")
    yield client


@pytest.fixture
def factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    """SQLite migrado com Usuários `u1` e `u2`, para testar o service sem HTTP."""
    path = tmp_path / "service.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        for user_id in ("u1", "u2"):
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, 'hash', '2026-10-23T12:00:00Z')",
                (user_id, f"{user_id}@x.com", f"{user_id}@x.com", user_id, user_id),
            )
    engine = create_db_engine(path)
    yield create_session_factory(engine)
    engine.dispose()


def new_uow(factory: sessionmaker[Session]) -> UnitOfWork:
    return UnitOfWork(factory, lambda _event: None)


def save(client: TestClient, provider: str = "openai", **body: Any) -> Any:
    if provider != "ollama":
        body.setdefault("api_key", API_KEY)
    else:
        body.setdefault("base_url", "http://host.docker.internal:11434")
    return client.put(f"{URL}/{provider}", json=body)


def by_provider(client: TestClient) -> dict[str, dict[str, Any]]:
    response = client.get(URL)
    assert response.status_code == 200
    return {item["provider"]: item for item in response.json()}


def config_rows(db: Path) -> list[tuple[Any, ...]]:
    return rows(
        db,
        "SELECT u.username, c.provider, c.model, c.context_window, c.is_active "
        "FROM llm_configs c JOIN users u ON u.id = c.user_id ORDER BY c.id",
    )
