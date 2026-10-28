import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.meetings.conftest import ana, clock, probe, uow, users  # noqa: F401


@pytest.fixture
def idle(ana: TestClient) -> TestClient:  # noqa: F811
    """Sem consumidor: a Reunião fica como o teste a deixar."""
    app: FastAPI = ana.app  # type: ignore[assignment]
    app.state.transcription.stop()
    return ana


def add_segments(
    settings: Settings, meeting_id: str, segments: list[tuple[str, float, float]]
) -> None:
    """`(speaker_label, início, fim)`, gravados na ordem dada."""
    with sqlite3.connect(settings.database_path) as conn:
        conn.executemany(
            "INSERT INTO transcript_segments "
            "(meeting_id, position, speaker_label, start_seconds, end_seconds, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (meeting_id, position, label, start, end, "Fala.")
                for position, (label, start, end) in enumerate(segments)
            ],
        )


def activate_provider(settings: Settings, username: str = "ana") -> None:
    """ "Provedor ativo" fake: configuração ativa gravada direto, sem chave."""
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            "INSERT INTO llm_configs (user_id, provider, base_url, model, context_window, "
            "key_status, is_active, created_at, updated_at) "
            "SELECT id, 'ollama', 'http://host.docker.internal:11434', 'llama3', 8192, 'ok', 1, "
            "'2026-10-28T12:00:00Z', '2026-10-28T12:00:00Z' FROM users WHERE username = ?",
            (username,),
        )
