from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.events import Event, PartsReady
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import service
from tests.meetings.conftest import ana, clock, probe, uow, users  # noqa: F401
from tests.participants.conftest import idle  # noqa: F401
from tests.transcript_split.helpers import FakeEstimate

Prepare = Callable[..., str]


@pytest.fixture
def ready(idle: TestClient) -> list[Event]:  # noqa: F811
    """Avisos `PartsReady` publicados (consumidor fake de `backlog_generation`)."""
    received: list[Event] = []
    app: FastAPI = idle.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(PartsReady, received.append)
    return received


@pytest.fixture
def prepare(idle: TestClient) -> Prepare:  # noqa: F811
    """ "Preparar geração" numa transação, com "Estimar tokens" de um token por caractere."""
    app: FastAPI = idle.app  # type: ignore[assignment]

    def run(meeting_id: str, mode: service.Mode = "normal") -> str:
        with UnitOfWork(app.state.session_factory, app.state.event_bus.publish) as unit:
            return service.prepare_generation(
                unit, meeting_id, mode, now=app.state.clock.now(), estimate=FakeEstimate()
            )

    return run
