from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.events import Event, ParticipantsConfirmed
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.meetings import service as meetings
from snook.modules.participants import repository
from tests.auth.helpers import rows
from tests.meetings.helpers import URL, set_fields
from tests.participants.conftest import activate_provider
from tests.participants.helpers import confirmed_at, names, stored, transcribed, url

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


@pytest.fixture
def confirmed(idle: TestClient) -> list[Event]:
    """Consumidor fake de `ParticipantsConfirmed`."""
    received: list[Event] = []
    app: FastAPI = idle.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(ParticipantsConfirmed, received.append)
    return received


def _run_id(settings: Settings, meeting_id: str) -> str:
    [(value,)] = rows(
        settings.database_path,
        f"SELECT run_id FROM meetings WHERE id = '{meeting_id}'",  # noqa: S608
    )
    return str(value)


def test_confirmation_emits_once_and_marks_meeting(
    idle: TestClient, settings: Settings, confirmed: list[Event], uow: Uow
) -> None:
    """`participants` 10."""
    activate_provider(settings)
    meeting_id = transcribed(idle, settings)

    assert idle.put(url(meeting_id), json=names()).status_code == 200

    assert confirmed == [
        ParticipantsConfirmed(meeting_id=meeting_id, run_id=_run_id(settings, meeting_id))
    ]
    with uow() as unit:
        assert meetings.read_flags(unit, meeting_id).participants_confirmed
    assert idle.get(f"{URL}/{meeting_id}").json()["status"] == "transcribed"


def test_failed_write_keeps_no_mark_and_no_event(
    idle: TestClient,
    settings: Settings,
    confirmed: list[Event],
    uow: Uow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`participants` 10: falha na gravação desfaz tudo."""
    activate_provider(settings)
    meeting_id = transcribed(idle, settings)
    calls = 0
    link_speaker = repository.link_speaker

    def failing_second_link(*args: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("disco cheio")
        link_speaker(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(repository, "link_speaker", failing_second_link)

    with pytest.raises(RuntimeError):
        idle.put(url(meeting_id), json=names())

    assert stored(settings.database_path) == ([], [])
    assert confirmed_at(settings.database_path, meeting_id) is None
    assert confirmed == []
    with uow() as unit:
        assert not meetings.read_flags(unit, meeting_id).participants_confirmed


def test_without_active_provider_is_409_and_nothing_changes(
    idle: TestClient, settings: Settings, confirmed: list[Event]
) -> None:
    """`participants` 11."""
    meeting_id = transcribed(idle, settings)

    response = idle.put(url(meeting_id), json=names())

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "no_active_provider"
    assert "Configurações" in error["message"]
    assert stored(settings.database_path) == ([], [])
    assert confirmed_at(settings.database_path, meeting_id) is None
    assert confirmed == []
    assert idle.get(f"{URL}/{meeting_id}").json()["status"] == "transcribed"


def test_other_users_provider_does_not_count(idle: TestClient, settings: Settings) -> None:
    """Provedor ativo é o do dono da Reunião."""
    activate_provider(settings, "bia")
    meeting_id = transcribed(idle, settings)

    response = idle.put(url(meeting_id), json=names())

    assert response.json()["error"]["code"] == "no_active_provider"


def test_participants_survive_generation_retry_and_regeneration(
    idle: TestClient, settings: Settings
) -> None:
    """`participants` 16: retry de `generation` e nova geração não tocam nos Participantes."""
    activate_provider(settings)
    meeting_id = transcribed(idle, settings)
    created = idle.put(url(meeting_id), json=names(SPEAKER_02="Ana")).json()

    for status in ("generating", "done", "generating"):
        set_fields(settings.database_path, meeting_id, status=status)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="x",
    )
    assert idle.post(f"{URL}/{meeting_id}/retry").status_code == 202

    assert idle.get(url(meeting_id)).json() == created
