import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.backlog_generation.helpers import FakeGenerate
from tests.meetings.conftest import ana, clock, probe, uow, users  # noqa: F401
from tests.participants.conftest import idle  # noqa: F401


@pytest.fixture
def generate(idle: TestClient) -> FakeGenerate:  # noqa: F811
    """ "Gerar" fake e geração síncrona: o aviso "Partes prontas" roda a geração no teste."""
    app: FastAPI = idle.app  # type: ignore[assignment]
    fake = FakeGenerate()
    app.state.generate = fake
    app.state.generate_backlog = app.state.generation.run
    return fake
