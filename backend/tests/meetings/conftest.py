from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.events import Event, MeetingCreated
from tests.auth.helpers import Users
from tests.meetings.helpers import FakeProbe


@pytest.fixture
def clock(app: FastAPI) -> FakeClock:
    fake = FakeClock(datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    app.state.clock = fake
    return fake


@pytest.fixture
def probe(app: FastAPI) -> FakeProbe:
    fake = FakeProbe()
    app.state.media_probe = fake
    return fake


@pytest.fixture
def users(client: TestClient, clock: FakeClock) -> Users:
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
def events(client: TestClient) -> list[Event]:
    """Avisos `MeetingCreated` publicados (consumidor fake)."""
    received: list[Event] = []
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(MeetingCreated, received.append)
    return received
