from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings
from snook.modules.llm_providers.adapters.base import GenerationRequest, LLMError, ProviderTarget
from tests.auth.helpers import registration, rows

# Nomes liberados no .gitleaks.toml.
API_KEY = "sk-TesteChave-0123456789abcdef"
OTHER_KEY = "sk-OutraChave-9876543210fedcba"
URL = "/api/llm-configs"


class FakeAdapter:
    """Adapter trocável: `error` define a falha do próximo teste; `calls` guarda os alvos."""

    def __init__(self) -> None:
        self.error: LLMError | None = None
        self.calls: list[ProviderTarget] = []

    def test_connection(self, target: ProviderTarget) -> None:
        self.calls.append(target)
        if self.error is not None:
            raise self.error

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
