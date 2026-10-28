import sqlite3

from fastapi.testclient import TestClient

from snook.core.settings import Settings
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
