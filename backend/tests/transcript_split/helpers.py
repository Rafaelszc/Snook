import sqlite3
from collections.abc import Callable

from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import service
from snook.shared.prompts import load_backlog_system_prompt
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields
from tests.participants.conftest import activate_provider

# `(speaker_label, início, fim, texto)`
SEGMENTS = [
    ("SPEAKER_00", 0.0, 4.2, "Bom dia a todos."),
    ("SPEAKER_01", 4.2, 3725.0, "Precisamos de um cadastro de clientes."),
    ("SPEAKER_00", 3725.9, 3730.0, "Com CPF obrigatório."),
]


def confirmed(client: TestClient, settings: Settings) -> str:
    """Reunião em `transcribed` com Ana (SPEAKER_00) e Bia (SPEAKER_01) confirmadas."""
    activate_provider(settings)
    meeting_id = create(client)
    with sqlite3.connect(settings.database_path) as conn:
        conn.executemany(
            "INSERT INTO transcript_segments "
            "(meeting_id, position, speaker_label, start_seconds, end_seconds, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(meeting_id, position, *segment) for position, segment in enumerate(SEGMENTS)],
        )
    set_fields(settings.database_path, meeting_id, status="transcribed")
    response = client.put(
        f"/api/meetings/{meeting_id}/participants",
        json={"names": {"SPEAKER_00": "Ana", "SPEAKER_01": "Bia"}},
    )
    assert response.status_code == 200
    return meeting_id


class FakeEstimate:
    """ "Estimar tokens" fake: um token por caractere; registra cada chamada."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, provider: str, model: str, text: str) -> int:
        self.calls.append((provider, model, text))
        return len(text)


def lines(uow: Callable[[], UnitOfWork], meeting_id: str) -> list[str]:
    with uow() as unit:
        return service.transcript_lines(unit, meeting_id)


def use_budget(
    settings: Settings, uow: Callable[[], UnitOfWork], meeting_id: str, target: int
) -> int:
    """Menor janela de Ana cujo orçamento (um token por caractere) chega a `target`. Devolve o
    orçamento obtido: `target` ou pouco acima."""
    with uow() as unit:
        participants = service.participants_text(unit, meeting_id)
    reserve = {
        "system_prompt_tokens": len(load_backlog_system_prompt()),
        "participants_tokens": len(participants),
    }
    window = 1
    while service.compute_budget(window, **reserve) < target:
        window += 1
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            "UPDATE llm_configs SET context_window = ? "
            "WHERE user_id = (SELECT id FROM users WHERE username = 'ana')",
            (window,),
        )
    return service.compute_budget(window, **reserve)
