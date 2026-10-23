import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.events import (
    Event,
    MeetingCreated,
    ParticipantsConfirmed,
    PartsReady,
    RetryRequested,
)
from snook.core.settings import Settings
from snook.main import create_app
from tests.auth.helpers import Users
from tests.meetings.helpers import URL, FakeProbe, set_fields, upload

INTERRUPTED = "processamento interrompido"
CONFIRMED_AT = "2026-10-23T12:00:00Z"


@contextmanager
def _running(settings: Settings, received: list[Event] | None = None) -> Iterator[TestClient]:
    """Sobe a app sobre o mesmo banco; consumidores entram antes da subida."""
    app: FastAPI = create_app(settings)
    app.state.media_probe = FakeProbe()
    app.state.clock = FakeClock(datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    if received is not None:
        for kind in (MeetingCreated, RetryRequested, ParticipantsConfirmed, PartsReady):
            app.state.event_bus.subscribe(kind, received.append)
    with TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"}
    ) as client:
        yield client


def _seed(settings: Settings, statuses: dict[str, dict[str, Any]]) -> tuple[dict[str, str], str]:
    """Uma Reunião por chave, gravada com as colunas dadas. Devolve ids e o cookie da Ana."""
    ids: dict[str, str] = {}
    with _running(settings) as client:
        Users(client).add("ana")
        for minute, (name, values) in enumerate(statuses.items()):
            meeting_id = upload(client).json()["id"]
            set_fields(
                settings.database_path,
                meeting_id,
                created_at=f"2026-10-23T12:{minute:02d}:00Z",
                **values,
            )
            ids[name] = meeting_id
        return ids, client.cookies["snook_session"]


def _state(db: Path, meeting_id: str) -> tuple[Any, ...]:
    with sqlite3.connect(db) as conn:
        [row] = conn.execute(
            "SELECT status, failed_stage, error_message, run_id, updated_at FROM meetings "
            "WHERE id = ?",
            (meeting_id,),
        ).fetchall()
    return tuple(row)


def test_interrupted_work_becomes_failed(settings: Settings) -> None:
    """`meetings` 44, 49."""
    ids, cookie = _seed(
        settings,
        {
            "processing": {"status": "processing"},
            "generating": {"status": "generating"},
            "confirmed": {"status": "transcribed", "participants_confirmed_at": CONFIRMED_AT},
        },
    )

    with _running(settings) as client:
        client.cookies.set("snook_session", cookie)
        details = {name: client.get(f"{URL}/{mid}").json() for name, mid in ids.items()}

    got = {
        name: (d["status"], d["failed_stage"], d["error_message"]) for name, d in details.items()
    }
    assert got == {
        "processing": ("failed", "transcription", INTERRUPTED),
        "generating": ("failed", "generation", INTERRUPTED),
        "confirmed": ("failed", "generation", INTERRUPTED),
    }


def test_marking_ends_before_requests_and_emits_nothing(settings: Settings) -> None:
    """`meetings` 45: o primeiro consumidor e a primeira requisição já veem a marcação."""
    ids, cookie = _seed(
        settings,
        {"processing": {"status": "processing"}, "pending": {"status": "pending"}},
    )
    seen_at_requeue: list[str] = []
    received: list[Event] = []

    def watch(event: Event) -> None:
        seen_at_requeue.append(_state(settings.database_path, ids["processing"])[0])

    app: FastAPI = create_app(settings)
    app.state.event_bus.subscribe(MeetingCreated, watch)
    for kind in (MeetingCreated, RetryRequested, ParticipantsConfirmed, PartsReady):
        app.state.event_bus.subscribe(kind, received.append)
    with TestClient(app, base_url="http://localhost") as client:
        client.cookies.set("snook_session", cookie)
        assert client.get(f"{URL}/{ids['processing']}").json()["status"] == "failed"

    assert seen_at_requeue == ["failed"]
    assert [type(e) for e in received] == [MeetingCreated]
    assert received[0].meeting_id == ids["pending"]


def test_other_states_do_not_change(settings: Settings) -> None:
    """`meetings` 50."""
    ids, _ = _seed(
        settings,
        {
            "transcribed": {"status": "transcribed"},
            "pending": {"status": "pending"},
            "needs_split": {"status": "needs_split"},
            "done": {"status": "done"},
            "failed": {
                "status": "failed",
                "failed_stage": "transcription",
                "error_message": "falhou antes",
            },
        },
    )
    before = {name: _state(settings.database_path, mid) for name, mid in ids.items()}

    with _running(settings):
        pass

    assert {name: _state(settings.database_path, mid) for name, mid in ids.items()} == before


def test_retry_works_after_marking(settings: Settings) -> None:
    """`meetings` 46: como nos critérios 24 e 25."""
    ids, cookie = _seed(
        settings,
        {"processing": {"status": "processing"}, "generating": {"status": "generating"}},
    )
    received: list[Event] = []

    with _running(settings, received) as client:
        client.cookies.set("snook_session", cookie)
        first = client.post(f"{URL}/{ids['processing']}/retry")
        second = client.post(f"{URL}/{ids['generating']}/retry")

    assert (first.status_code, first.json()["status"]) == (202, "pending")
    assert (second.status_code, second.json()["status"]) == (202, "transcribed")
    assert [(type(e), e.meeting_id) for e in received] == [
        (RetryRequested, ids["processing"]),
        (RetryRequested, ids["generating"]),
    ]
    assert [e.stage for e in received if isinstance(e, RetryRequested)] == [
        "transcription",
        "generation",
    ]


def test_pending_is_requeued_in_creation_order(settings: Settings) -> None:
    """ADR-0007: `MeetingCreated` interno, em ordem de `created_at`, com o `run_id` gravado."""
    ids, _ = _seed(
        settings,
        {
            "first": {"status": "pending"},
            "done": {"status": "done"},
            "second": {"status": "pending"},
            "third": {"status": "pending"},
        },
    )
    # Ordem de criação, não de inserção: a primeira passa a ser a mais nova.
    set_fields(settings.database_path, ids["first"], created_at="2026-10-23T13:00:00Z")
    received: list[Event] = []

    with _running(settings, received):
        pass

    runs = {name: _state(settings.database_path, mid)[3] for name, mid in ids.items()}
    assert received == [
        MeetingCreated(meeting_id=ids[name], run_id=runs[name])
        for name in ("second", "third", "first")
    ]
