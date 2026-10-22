import logging
from dataclasses import FrozenInstanceError

import pytest

from snook.core.events import (
    EventBus,
    MeetingCreated,
    ParticipantsConfirmed,
    PartsReady,
    RetryRequested,
)


@pytest.mark.parametrize(
    "event",
    [
        MeetingCreated(meeting_id="m1", run_id="r1"),
        ParticipantsConfirmed(meeting_id="m1", run_id="r1"),
        PartsReady(meeting_id="m1", run_id="r1"),
        RetryRequested(meeting_id="m1", run_id="r1", stage="transcription"),
    ],
)
def test_every_event_carries_meeting_and_run_id(event: object) -> None:
    assert getattr(event, "meeting_id") == "m1"  # noqa: B009
    assert getattr(event, "run_id") == "r1"  # noqa: B009


def test_events_are_immutable() -> None:
    event = MeetingCreated(meeting_id="m1", run_id="r1")
    with pytest.raises(FrozenInstanceError):
        event.run_id = "r2"  # type: ignore[misc]


def test_bus_delivers_to_registered_consumer() -> None:
    bus = EventBus()
    received: list[MeetingCreated] = []
    bus.subscribe(MeetingCreated, received.append)
    event = MeetingCreated(meeting_id="m1", run_id="r1")
    bus.publish(event)
    assert received == [event]


def test_bus_routes_by_event_type() -> None:
    bus = EventBus()
    created: list[object] = []
    parts: list[object] = []
    bus.subscribe(MeetingCreated, created.append)
    bus.subscribe(PartsReady, parts.append)
    bus.publish(PartsReady(meeting_id="m1", run_id="r1"))
    assert created == []
    assert len(parts) == 1


def test_consumer_can_ignore_stale_run_id() -> None:
    bus = EventBus()
    current_run_id = "r2"
    handled: list[str] = []

    def consumer(event: MeetingCreated) -> None:
        if event.run_id != current_run_id:
            return
        handled.append(event.meeting_id)

    bus.subscribe(MeetingCreated, consumer)
    bus.publish(MeetingCreated(meeting_id="old", run_id="r1"))
    bus.publish(MeetingCreated(meeting_id="new", run_id="r2"))
    assert handled == ["new"]


def test_publish_without_consumer_is_a_noop() -> None:
    EventBus().publish(PartsReady(meeting_id="m1", run_id="r1"))


def test_failing_consumer_does_not_block_others(caplog: pytest.LogCaptureFixture) -> None:
    bus = EventBus()
    received: list[object] = []

    def broken(_event: MeetingCreated) -> None:
        raise RuntimeError("consumidor quebrou")

    bus.subscribe(MeetingCreated, broken)
    bus.subscribe(MeetingCreated, received.append)
    with caplog.at_level(logging.ERROR):
        bus.publish(MeetingCreated(meeting_id="m1", run_id="r1"))
    assert len(received) == 1
    assert "event consumer failed" in caplog.text
