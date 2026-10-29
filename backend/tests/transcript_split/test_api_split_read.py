import sqlite3
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.events import Event, PartsReady
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import messages, service
from tests.auth.helpers import rows
from tests.meetings.helpers import set_fields
from tests.transcript_split.helpers import (
    SEGMENTS,
    LineEstimate,
    confirmed,
    segment_ids,
    split_url,
    waiting_split,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
PARTS = 'SELECT "index", first_segment_id, last_segment_id FROM transcript_parts ORDER BY 1'


def _two_parts(sizes: list[int]) -> int:
    """Orçamento para a regra gulosa dar `[0, 1]` e `[2]`."""
    return sizes[0] + sizes[1]


def _whole(sizes: list[int]) -> int:
    return sum(sizes)


def _database(settings: Settings) -> list[Any]:
    return [
        rows(settings.database_path, "SELECT * FROM meetings"),
        rows(settings.database_path, "SELECT * FROM transcript_parts"),
    ]


def test_get_returns_split_state(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 7 e 10: orçamento, provedor, estimativa, segmentos, cortes, Partes."""
    meeting_id, budget = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)
    sizes = [32, 54, 36]  # `LineEstimate` das três linhas de `SEGMENTS`

    response = split.get(split_url(meeting_id))

    assert response.status_code == 200
    body = response.json()
    assert {k: body[k] for k in body if k not in ("segments", "parts")} == {
        "status": "needs_split",
        "split_reason": "too_long",
        "can_cancel": False,
        "read_only": False,
        "message": None,
        "provider": "ollama",
        "model": "llama3",
        "budget": budget,
        "total_tokens": sum(sizes),
        "cuts": [ids[1]],
    }
    assert body["segments"] == [
        {
            "id": ids[i],
            "start_seconds": start,
            "end_seconds": end,
            "participant": "Ana" if label == "SPEAKER_00" else "Bia",
            "text": text,
            "tokens": sizes[i],
        }
        for i, (label, start, end, text) in enumerate(SEGMENTS)
    ]
    assert body["parts"] == [
        {
            "index": 1,
            "first_segment_id": ids[0],
            "last_segment_id": ids[1],
            "start_seconds": 0.0,
            "end_seconds": 3725.0,
            "estimated_tokens": 86,
            "fits": True,
        },
        {
            "index": 2,
            "first_segment_id": ids[2],
            "last_segment_id": ids[2],
            "start_seconds": 3725.9,
            "end_seconds": 3730.0,
            "estimated_tokens": 36,
            "fits": True,
        },
    ]
    assert ready == []


def test_get_allows_cancel_only_with_backlog(
    split: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 7: "Cancelar divisão" só com backlog gravado."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts, split_reason="adjust")
    set_fields(settings.database_path, meeting_id, backlog_saved_at="2026-10-23T12:00:00Z")

    body = split.get(split_url(meeting_id)).json()

    assert (body["can_cancel"], body["split_reason"]) == (True, "adjust")


def test_get_suggests_current_cuts_while_they_fit(
    split: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 22: Partes anteriores que cabem viram a sugestão, não a gulosa."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    with uow() as unit:
        snapshot = service.owner_provider(unit, meeting_id)
        service.save_parts(unit, snapshot, meeting_id, [(0, 0), (1, 2)], estimate=LineEstimate())
    ids = segment_ids(settings, meeting_id)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE llm_configs SET context_window = context_window + 20")

    body = split.get(split_url(meeting_id)).json()

    assert body["cuts"] == [ids[0]]
    assert [part["fits"] for part in body["parts"]] == [True, True]


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "transcribed"},
        {"status": "generating"},
        {"status": "done"},
        {"status": "failed", "failed_stage": "generation", "error_message": "Falha."},
    ],
)
def test_get_outside_needs_split_is_409(
    split: TestClient, settings: Settings, fields: dict[str, str]
) -> None:
    """`transcript-split` 11: fora de `needs_split`, 409 (`done` sem divisão incluso)."""
    meeting_id = confirmed(split, settings)
    set_fields(settings.database_path, meeting_id, **fields)

    response = split.get(split_url(meeting_id))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "split_not_available"


def test_get_done_divided_is_read_only(split: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 11: `done` já dividida devolve os cortes atuais, só leitura."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)
    assert split.put(split_url(meeting_id), json={"cuts": [ids[1]]}).status_code == 202
    set_fields(settings.database_path, meeting_id, status="done")
    before = _database(settings)

    response = split.get(split_url(meeting_id))

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["read_only"], body["cuts"]) == ("done", True, [ids[1]])
    assert _database(settings) == before


@pytest.mark.parametrize("status", ["transcribed", "generating", "done"])
def test_refresh_outside_needs_split_is_409_and_unchanged(
    split: TestClient, settings: Settings, status: str, ready: list[Event]
) -> None:
    """`transcript-split` 11."""
    meeting_id = confirmed(split, settings)
    set_fields(settings.database_path, meeting_id, status=status)
    before = _database(settings)

    response = split.post(split_url(meeting_id, "/refresh"))

    assert response.status_code == 409
    assert _database(settings) == before
    assert ready == []


def test_refresh_when_it_now_fits_saves_single_part(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 43: Parte única, `generating`, "Partes prontas" uma vez, sem cortes."""
    meeting_id, _ = waiting_split(split, settings, uow, _whole)
    ids = segment_ids(settings, meeting_id)

    response = split.post(split_url(meeting_id, "/refresh"))

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["cuts"], body["parts"]) == ("generating", [], [])
    assert rows(settings.database_path, PARTS) == [(1, ids[0], ids[2])]
    [run_id] = rows(settings.database_path, "SELECT run_id FROM meetings")[0]
    assert ready == [PartsReady(meeting_id=meeting_id, run_id=run_id)]


def test_refresh_when_still_too_long_changes_nothing(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 43: não cabe, nada muda; responde como o `GET`."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    before = _database(settings)

    refreshed = split.post(split_url(meeting_id, "/refresh"))

    assert refreshed.status_code == 200
    assert refreshed.json() == split.get(split_url(meeting_id)).json()
    assert _database(settings) == before
    assert ready == []


def test_get_never_changes_state_even_when_it_fits(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 43: `GET` só lê; o banco não muda."""
    meeting_id, _ = waiting_split(split, settings, uow, _whole)
    before = _database(settings)

    body = split.get(split_url(meeting_id)).json()

    assert body["status"] == "needs_split"
    assert _database(settings) == before
    assert ready == []


@pytest.mark.parametrize(("method", "action"), [("GET", ""), ("POST", "/refresh")])
def test_without_provider_only_message(
    split: TestClient, settings: Settings, uow: Uow, method: str, action: str
) -> None:
    """`transcript-split` 44: só a mensagem; segue em `needs_split`, nada muda."""
    meeting_id, _ = waiting_split(split, settings, uow, _whole)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("DELETE FROM llm_configs")
    before = _database(settings)

    response = split.request(method, split_url(meeting_id, action))

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == messages.NO_ACTIVE_PROVIDER
    assert (body["status"], body["budget"], body["provider"]) == ("needs_split", None, None)
    assert (body["cuts"], body["parts"], body["segments"]) == ([], [], [])
    assert _database(settings) == before
