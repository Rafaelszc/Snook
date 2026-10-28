import sqlite3
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.events import Event, PartsReady
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import messages
from tests.auth.helpers import rows
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields
from tests.participants.conftest import add_segments
from tests.transcript_split.helpers import segment_ids, split_url, waiting_split

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
PARTS = (
    'SELECT "index", first_segment_id, last_segment_id, start_seconds, end_seconds, '
    "estimated_tokens FROM transcript_parts ORDER BY 1"
)
STATE = "SELECT status, failed_stage, error_message FROM meetings"


def _two_parts(sizes: list[int]) -> int:
    """Cabe `[0, 1]` (86) mas não `[1, 2]` (90) nem a Transcrição inteira (122)."""
    return sizes[0] + sizes[1]


def _database(settings: Settings) -> list[Any]:
    return [
        rows(settings.database_path, "SELECT * FROM meetings"),
        rows(settings.database_path, "SELECT * FROM transcript_parts"),
    ]


def _window(settings: Settings, delta: int) -> None:
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE llm_configs SET context_window = context_window + ?", (delta,))


def test_valid_cuts_save_parts_and_start_generation(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 12 e 18: Partes em ordem, `generating`, "Partes prontas" uma vez."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)

    response = split.put(split_url(meeting_id), json={"cuts": [ids[1]]})

    assert response.status_code == 202
    assert response.json() == {"status": "generating"}
    assert rows(settings.database_path, PARTS) == [
        (1, ids[0], ids[1], 0.0, 3725.0, 86),
        (2, ids[2], ids[2], 3725.9, 3730.0, 36),
    ]
    [(run_id,)] = rows(settings.database_path, "SELECT run_id FROM meetings")
    assert ready == [PartsReady(meeting_id=meeting_id, run_id=run_id)]


@pytest.mark.parametrize("cut", ["missing", "last", "other_meeting"])
def test_cut_not_at_segment_end_is_422(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event], cut: str
) -> None:
    """`transcript-split` 13: id que não é segmento da Reunião, ou o último, é recusado."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)
    other = create(split)
    add_segments(settings, other, [("SPEAKER_00", 0.0, 1.0), ("SPEAKER_00", 1.0, 2.0)])
    chosen = {"missing": 999_999, "last": ids[-1], "other_meeting": segment_ids(settings, other)[0]}
    before = _database(settings)

    response = split.put(split_url(meeting_id), json={"cuts": [chosen[cut]]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cut_not_at_segment_end"
    assert _database(settings) == before
    assert ready == []


@pytest.mark.parametrize("order", [[0, 0], [1, 0]])
def test_repeated_or_unordered_cuts_are_422(
    split: TestClient, settings: Settings, uow: Uow, order: list[int]
) -> None:
    """`transcript-split` 14."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)
    before = _database(settings)

    response = split.put(split_url(meeting_id), json={"cuts": [ids[i] for i in order]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cuts_not_ordered"
    assert _database(settings) == before


def test_part_that_does_not_fit_is_422_with_index_and_estimate(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 15: `part_too_large`, Reunião segue em `needs_split`."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    ids = segment_ids(settings, meeting_id)
    before = _database(settings)

    response = split.put(split_url(meeting_id), json={"cuts": [ids[0]]})

    assert response.status_code == 422
    error = response.json()["error"]
    assert (error["code"], error["part_index"], error["estimated_tokens"]) == (
        "part_too_large",
        2,
        90,
    )
    assert _database(settings) == before
    assert ready == []


def test_validation_uses_provider_active_at_put(
    split: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 16: janela menor depois do `GET`; corte sugerido deixa de caber."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    cuts = split.get(split_url(meeting_id)).json()["cuts"]
    _window(settings, -2)

    response = split.put(split_url(meeting_id), json={"cuts": cuts})

    assert response.status_code == 422
    assert response.json()["error"]["part_index"] == 1
    assert rows(settings.database_path, STATE) == [("needs_split", None, None)]


@pytest.mark.parametrize("status", ["transcribed", "generating", "done"])
def test_put_outside_needs_split_is_409(
    split: TestClient, settings: Settings, uow: Uow, status: str
) -> None:
    """`transcript-split` 17."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    set_fields(settings.database_path, meeting_id, status=status)
    before = _database(settings)

    response = split.put(
        split_url(meeting_id), json={"cuts": [segment_ids(settings, meeting_id)[1]]}
    )

    assert response.status_code == 409
    assert _database(settings) == before


def test_without_provider_goes_to_failed(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 41: `failed/generation`, sem Parte nem aviso."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("DELETE FROM llm_configs")

    response = split.put(
        split_url(meeting_id), json={"cuts": [segment_ids(settings, meeting_id)[1]]}
    )

    assert response.json() == {"status": "failed"}
    assert rows(settings.database_path, STATE) == [
        ("failed", "generation", messages.NO_ACTIVE_PROVIDER)
    ]
    assert rows(settings.database_path, PARTS) == []
    assert ready == []


def test_segment_above_budget_goes_to_failed(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 42: segmento de 54 com orçamento menor; mensagem do critério 6."""
    meeting_id, _ = waiting_split(split, settings, uow, lambda sizes: sizes[2])

    response = split.put(
        split_url(meeting_id), json={"cuts": [segment_ids(settings, meeting_id)[0]]}
    )

    assert response.json() == {"status": "failed"}
    assert rows(settings.database_path, STATE) == [
        ("failed", "generation", messages.SEGMENT_TOO_LONG)
    ]
    assert rows(settings.database_path, PARTS) == []
    assert ready == []


def test_put_when_it_now_fits_ignores_cuts(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """`transcript-split` 43: Parte única, cortes enviados ignorados."""
    meeting_id, _ = waiting_split(split, settings, uow, sum)
    ids = segment_ids(settings, meeting_id)

    response = split.put(split_url(meeting_id), json={"cuts": [ids[0]]})

    assert response.json() == {"status": "generating"}
    assert [row[:3] for row in rows(settings.database_path, PARTS)] == [(1, ids[0], ids[2])]
    assert len(ready) == 1


@pytest.mark.parametrize(
    "body",
    [{"cuts": []}, {"cuts": list(range(1, 502))}, {"cuts": [1], "extra": 1}, {}],
)
def test_invalid_body_is_422(
    split: TestClient, settings: Settings, uow: Uow, body: dict[str, Any]
) -> None:
    """1 a 500 cortes, sem campo extra (SEC-09)."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    before = _database(settings)

    response = split.put(split_url(meeting_id), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert _database(settings) == before
