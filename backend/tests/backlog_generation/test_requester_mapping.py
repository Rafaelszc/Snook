"""Solicitante por nome de Participante (`backlog-generation` 13; SEC-18)."""

import pytest

from snook.modules.backlog_generation.validation import resolve_requester
from snook.modules.participants.schemas import ParticipantOut

PARTICIPANTS = [
    ParticipantOut(id=1, name="Ana Souza", speaker_labels=["SPEAKER_00"]),
    ParticipantOut(id=2, name="Bruno", speaker_labels=["SPEAKER_01"]),
]


@pytest.mark.parametrize(
    ("requested_by", "expected"),
    [
        ("Ana Souza", 1),
        ("ana souza", 1),
        ("  ANA SOUZA  ", 1),
        ("Bruno", 2),
        ("bruno\n", 2),
    ],
)
def test_known_name_links_participant(requested_by: str, expected: int) -> None:
    """Igual ao nome, sem diferenciar caixa e espaços nas pontas."""
    assert resolve_requester(requested_by, PARTICIPANTS) == expected


@pytest.mark.parametrize(
    "requested_by", [None, "", "   ", "Carlos", "Ana", "Ana  Souza", "Bruno; DROP TABLE x"]
)
def test_unknown_empty_or_missing_leaves_empty(requested_by: str | None) -> None:
    """Desconhecido, vazio ou ausente: solicitante vazio, sem invalidar."""
    assert resolve_requester(requested_by, PARTICIPANTS) is None


def test_no_participants_leaves_empty() -> None:
    assert resolve_requester("Ana Souza", []) is None
