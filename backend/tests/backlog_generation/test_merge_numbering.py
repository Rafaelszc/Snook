from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation.merge import merge_backlogs, us_id
from snook.modules.backlog_generation.validation import BacklogResponse, parse_backlog
from snook.modules.meetings import service as meetings
from tests.backlog_generation.helpers import (
    DURATION,
    FakeGenerate,
    backlog,
    count,
    generating,
    parts_ready,
    regenerating,
    stored_stories,
    story,
)
from tests.diarized_transcription.helpers import state


@dataclass(frozen=True)
class _Participant:
    id: int
    name: str


Uow = Callable[[], UnitOfWork]


def _parse(raw: str) -> BacklogResponse:
    return parse_backlog(raw, duration_seconds=DURATION)


def _shape(responses: list[str]) -> list[tuple[str, list[tuple[int, str]]]]:
    epics = merge_backlogs([_parse(raw) for raw in responses], [_Participant(7, "Ana")])
    return [(e.name, [(s.us_number, s.story.name) for s in e.stories]) for e in epics]


def test_same_name_merges_within_and_across_parts() -> None:
    """`backlog-generation` 16, 17: sem caixa e espaços nas pontas; nome da primeira ocorrência;
    US na ordem de chegada."""
    shape = _shape(
        [
            backlog(
                ("Cadastro", [story("A")]), ("Busca", [story("B")]), ("CADASTRO", [story("C")])
            ),
            backlog((" cadastro ", [story("D")])),
        ]
    )

    assert shape == [
        ("Cadastro", [(1, "A"), (3, "C"), (4, "D")]),
        ("Busca", [(2, "B")]),
    ]


def test_numbering_follows_parts_then_response_order() -> None:
    """`backlog-generation` 18: de 1, sem lacunas nem repetição, na ordem das Partes."""
    shape = _shape(
        [
            backlog(("X", [story("A"), story("B")])),
            backlog(("Y", [story("C")]), ("X", [story("D")])),
        ]
    )

    numbers = sorted(n for _, stories in shape for n, _ in stories)
    assert numbers == [1, 2, 3, 4]
    assert shape == [("X", [(1, "A"), (2, "B"), (4, "D")]), ("Y", [(3, "C")])]


def test_us_id_format() -> None:
    """`backlog-generation` 18, 19: `US-01`; da centésima em diante, três dígitos."""
    assert [us_id(n) for n in (1, 9, 99, 100, 123)] == [
        "US-01",
        "US-09",
        "US-99",
        "US-100",
        "US-123",
    ]


def test_epic_without_stories_dropped() -> None:
    """`backlog-generation` 20: Epic sem US não é gravada."""
    assert _shape([backlog(("Vazia", []), ("Cheia", [story("A")]))]) == [("Cheia", [(1, "A")])]


def test_requester_resolved_by_name() -> None:
    """`backlog-generation` 13: solicitante pelo nome; desconhecido fica vazio."""
    epics = merge_backlogs(
        [_parse(backlog(("X", [story("A", requested_by=" ana "), story("B", requested_by="Zé")])))],
        [_Participant(7, "Ana")],
    )

    assert [s.requested_by for s in epics[0].stories] == [7, None]


@pytest.mark.usefixtures("probe", "clock")
def test_empty_generation_done_with_empty_backlog(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 21: geração válida sem US vai a `done` com backlog gravado vazio."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Vazia", []))]

    parts_ready(idle, meeting_id)

    assert state(settings.database_path, meeting_id) == ("done", None, None)
    assert count(settings, "epics") == 0
    with uow() as unit:
        assert meetings.read_flags(unit, meeting_id).has_backlog


@pytest.mark.usefixtures("probe", "clock")
def test_merge_across_parts_stored(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 16 a 18 no banco: uma Epic, US numeradas na ordem das Partes."""
    meeting_id = generating(idle, settings, uow, [(0, 1), (2, 2)])
    generate.replies = [
        backlog(("Cadastro", [story("A"), story("B")])),
        backlog(("cadastro", [story("C")])),
    ]

    parts_ready(idle, meeting_id)

    assert stored_stories(settings, meeting_id) == [
        (1, "Cadastro", "A"),
        (2, "Cadastro", "B"),
        (3, "Cadastro", "C"),
    ]
    regenerating(settings, meeting_id, "run-2")
    generate.replies = [backlog(("Cadastro", [story("D")])), backlog()]
    parts_ready(idle, meeting_id, "run-2")
    assert stored_stories(settings, meeting_id) == [(1, "Cadastro", "D")]
