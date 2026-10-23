from datetime import UTC, datetime

import pytest
from fastapi import FastAPI

from snook.core.clock import FakeClock


@pytest.fixture
def clock(app: FastAPI) -> FakeClock:
    fake = FakeClock(datetime(2026, 10, 22, 12, 0, tzinfo=UTC))
    app.state.clock = fake
    return fake
