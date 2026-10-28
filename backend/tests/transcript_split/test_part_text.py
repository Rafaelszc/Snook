from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.participants import service as participants
from snook.modules.transcript_split import service
from tests.transcript_split.helpers import confirmed

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _text(uow: Uow, meeting_id: str, first: int, last: int) -> str:
    with uow() as unit:
        return service.part_text(unit, meeting_id, first, last)


def test_one_line_per_segment_in_order(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 25."""
    meeting_id = confirmed(idle, settings)

    assert _text(uow, meeting_id, 0, 2).splitlines() == [
        "[00:00:00] Ana: Bom dia a todos.",
        "[00:00:04] Bia: Precisamos de um cadastro de clientes.",
        "[01:02:05] Ana: Com CPF obrigatório.",
    ]


def test_part_mid_recording_keeps_absolute_time(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 26."""
    meeting_id = confirmed(idle, settings)

    assert _text(uow, meeting_id, 2, 2) == "[01:02:05] Ana: Com CPF obrigatório."


def test_renamed_participant_shows_new_name(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 27."""
    meeting_id = confirmed(idle, settings)
    with uow() as unit:
        bia = next(p for p in participants.list_participants(unit, meeting_id) if p.name == "Bia")
        participants.rename(unit, meeting_id, bia.id, "Beatriz")

    assert _text(uow, meeting_id, 1, 1) == (
        "[00:00:04] Beatriz: Precisamos de um cadastro de clientes."
    )


def test_line_breaks_in_text_stay_on_one_line(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """Uma linha por segmento mesmo com quebra no texto (estimativa aditiva, ADR-0011)."""
    meeting_id = confirmed(idle, settings)
    with uow() as unit:
        lines = service.transcript_lines(unit, meeting_id)

    assert len(lines) == 3
    assert service.format_line(0.0, "Ana", " um\n[00:00:01] Bia:  dois ") == (
        "[00:00:00] Ana: um [00:00:01] Bia: dois"
    )
