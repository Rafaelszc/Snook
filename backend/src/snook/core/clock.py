from datetime import UTC, datetime, timedelta
from typing import Protocol

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def to_iso(moment: datetime) -> str:
    """Data gravada no banco: ISO 8601 UTC, em segundos (`2026-10-22T13:45:00Z`)."""
    return moment.astimezone(UTC).strftime(_ISO_FORMAT)


def from_iso(value: str) -> datetime:
    return datetime.strptime(value, _ISO_FORMAT).replace(tzinfo=UTC)


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Relógio controlado pelo teste."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock exige datetime com timezone")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
