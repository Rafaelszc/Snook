from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.errors import AppError
from snook.core.events import Event, ParticipantsConfirmed
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.participants import service
from snook.modules.participants.schemas import ParticipantOut
from tests.meetings.helpers import URL, set_fields
from tests.participants.conftest import activate_provider
from tests.participants.helpers import names, stored, transcribed, url

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _confirmed(
    client: TestClient, settings: Settings, *, activate: bool = True
) -> tuple[str, dict[str, int]]:
    """Reunião confirmada com Ana (SPEAKER_00, SPEAKER_02) e Bia (SPEAKER_01)."""
    if activate:
        activate_provider(settings)
    meeting_id = transcribed(client, settings)
    created = client.put(url(meeting_id), json=names(SPEAKER_02="Ana")).json()
    return meeting_id, {p["name"]: p["id"] for p in created}


def _rename(uow: Uow, meeting_id: str, participant_id: int, name: str, **kwargs: Any) -> Any:
    with uow() as unit:
        return service.rename(unit, meeting_id, participant_id, name, **kwargs)


def _refused(uow: Uow, meeting_id: str, participant_id: int, name: str) -> AppError:
    with pytest.raises(AppError) as caught:
        _rename(uow, meeting_id, participant_id, name)
    return caught.value


def test_new_name_keeps_id_and_links(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`participants` 17."""
    meeting_id, ids = _confirmed(idle, settings)

    result = _rename(uow, meeting_id, ids["Bia"], "  Beatriz ")

    assert result == service.RenameResult(
        participant=ParticipantOut(id=ids["Bia"], name="Beatriz", speaker_labels=["SPEAKER_01"])
    )
    assert stored(settings.database_path) == (
        [("Ana", "ana"), ("Beatriz", "beatriz")],
        [("SPEAKER_00", "Ana"), ("SPEAKER_01", "Beatriz"), ("SPEAKER_02", "Ana")],
    )


def test_own_name_in_other_case_is_not_a_merge(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`participants` 17: mesmo Participante, só a grafia muda."""
    meeting_id, ids = _confirmed(idle, settings)

    result = _rename(uow, meeting_id, ids["Ana"], "ANA")

    assert result.absorbed_id is None
    assert result.participant.id == ids["Ana"]
    assert result.participant.name == "ANA"


def test_existing_name_merges_into_holder(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`participants` 18: sobrevive quem já tinha o nome, com a grafia dele."""
    meeting_id, ids = _confirmed(idle, settings)

    result = _rename(uow, meeting_id, ids["Bia"], " ana ")

    assert result == service.RenameResult(
        participant=ParticipantOut(
            id=ids["Ana"], name="Ana", speaker_labels=["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]
        ),
        absorbed_id=ids["Bia"],
    )
    assert stored(settings.database_path) == (
        [("Ana", "ana")],
        [("SPEAKER_00", "Ana"), ("SPEAKER_01", "Ana"), ("SPEAKER_02", "Ana")],
    )


def test_before_absorb_runs_before_delete(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`before_absorb(absorbed_id, survivor_id)` com o absorvido ainda gravado."""
    meeting_id, ids = _confirmed(idle, settings)
    seen: list[tuple[int, int, list[int]]] = []

    with uow() as unit:

        def before_absorb(absorbed_id: int, survivor_id: int) -> None:
            alive = [p.id for p in service.list_participants(unit, meeting_id)]
            seen.append((absorbed_id, survivor_id, alive))

        service.rename(unit, meeting_id, ids["Bia"], "Ana", before_absorb=before_absorb)

    assert seen == [(ids["Bia"], ids["Ana"], sorted(ids.values()))]


def test_before_absorb_failure_rolls_back(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """Mesma transação de quem chama: falha desfaz a união."""
    meeting_id, ids = _confirmed(idle, settings)
    before = stored(settings.database_path)

    def failing(absorbed_id: int, survivor_id: int) -> None:
        raise RuntimeError("falha nas US")

    with pytest.raises(RuntimeError):
        _rename(uow, meeting_id, ids["Bia"], "Ana", before_absorb=failing)

    assert stored(settings.database_path) == before


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_refused(idle: TestClient, settings: Settings, uow: Uow, name: str) -> None:
    """`participants` 19."""
    meeting_id, ids = _confirmed(idle, settings)
    before = stored(settings.database_path)

    error = _refused(uow, meeting_id, ids["Bia"], name)

    assert (error.code, error.http_status) == ("validation_error", 422)
    assert stored(settings.database_path) == before


def test_name_over_100_is_refused(idle: TestClient, settings: Settings, uow: Uow) -> None:
    meeting_id, ids = _confirmed(idle, settings)
    before = stored(settings.database_path)

    error = _refused(uow, meeting_id, ids["Bia"], "B" * 101)

    assert (error.code, error.http_status) == ("validation_error", 422)
    assert stored(settings.database_path) == before


def test_without_confirmed_participants_is_refused(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`participants` 20."""
    meeting_id = transcribed(idle, settings)

    error = _refused(uow, meeting_id, 1, "Ana")

    assert (error.code, error.http_status) == ("not_confirmed", 409)
    assert stored(settings.database_path) == ([], [])


def test_unknown_or_foreign_participant_is_404(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    meeting_id, _ = _confirmed(idle, settings)
    _, other_ids = _confirmed(idle, settings, activate=False)

    assert _refused(uow, meeting_id, 9999, "X").http_status == 404
    assert _refused(uow, meeting_id, other_ids["Bia"], "X").code == "participant_not_found"


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "transcribed"},
        {"status": "needs_split", "split_reason": "too_long"},
        {"status": "done"},
        {"status": "failed", "failed_stage": "generation", "error_message": "x"},
    ],
    ids=["transcribed", "needs_split", "done", "failed_generation"],
)
def test_accepted_statuses(
    idle: TestClient, settings: Settings, uow: Uow, fields: dict[str, str]
) -> None:
    """`participants` 21: aceita, e o status não muda (22)."""
    meeting_id, ids = _confirmed(idle, settings)
    set_fields(settings.database_path, meeting_id, **fields)

    assert _rename(uow, meeting_id, ids["Bia"], "Beatriz").participant.name == "Beatriz"
    assert idle.get(f"{URL}/{meeting_id}").json()["status"] == fields["status"]


def test_generating_is_refused(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`participants` 21."""
    meeting_id, ids = _confirmed(idle, settings)
    set_fields(settings.database_path, meeting_id, status="generating")
    before = stored(settings.database_path)

    error = _refused(uow, meeting_id, ids["Bia"], "Beatriz")

    assert (error.code, error.http_status) == ("invalid_status", 409)
    assert stored(settings.database_path) == before


def test_no_llm_no_event_no_status_change(
    idle: TestClient, settings: Settings, uow: Uow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`participants` 22."""
    meeting_id, ids = _confirmed(idle, settings)
    received: list[Event] = []
    app: FastAPI = idle.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(ParticipantsConfirmed, received.append)

    class NoLlm:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"llm_providers.{name} chamado")

    monkeypatch.setattr(service, "llm_providers", NoLlm())

    _rename(uow, meeting_id, ids["Bia"], "Beatriz")
    _rename(uow, meeting_id, ids["Bia"], "Ana")

    assert received == []
    assert idle.get(f"{URL}/{meeting_id}").json()["status"] == "transcribed"
