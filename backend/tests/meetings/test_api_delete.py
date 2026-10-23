import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.auth.helpers import Users, rows
from tests.meetings.helpers import URL, FakeProbe, set_fields, stored_files, upload


def _create(client: TestClient) -> str:
    response = upload(client)
    assert response.status_code == 201
    meeting_id: str = response.json()["id"]
    return meeting_id


def _add_fake_derived(db: Path, meeting_id: str) -> None:
    """Tabelas fake no lugar de segmentos e User Stories: mesma FK com cascata."""
    with sqlite3.connect(db) as conn:
        for table in ("fake_segments", "fake_user_stories"):
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "id INTEGER PRIMARY KEY, "
                "meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE)"
            )
            conn.execute(f"INSERT INTO {table} (meeting_id) VALUES (?)", (meeting_id,))  # noqa: S608


def test_delete_is_204_then_404_and_file_gone(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 28; SEC-24."""
    meeting_id = _create(ana)
    assert (settings.audio_root / meeting_id / "original.mp3").exists()
    response = ana.delete(f"{URL}/{meeting_id}")
    assert response.status_code == 204
    assert response.content == b""
    assert ana.get(f"{URL}/{meeting_id}").status_code == 404
    assert stored_files(settings.audio_root) == []
    assert rows(settings.database_path, "SELECT COUNT(*) FROM meetings") == [(0,)]


def test_delete_removes_derived_records(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 29."""
    meeting_id = _create(ana)
    other = _create(ana)
    _add_fake_derived(settings.database_path, meeting_id)
    _add_fake_derived(settings.database_path, other)
    assert ana.delete(f"{URL}/{meeting_id}").status_code == 204
    for table in ("fake_segments", "fake_user_stories"):
        assert rows(settings.database_path, f"SELECT meeting_id FROM {table}") == [(other,)]  # noqa: S608


@pytest.mark.parametrize(
    ("status", "extra"),
    [
        ("pending", {}),
        ("processing", {}),
        ("transcribed", {}),
        ("needs_split", {"split_reason": "adjust"}),
        ("generating", {}),
        ("done", {}),
        ("failed", {"failed_stage": "transcription", "error_message": "Erro."}),
    ],
)
def test_delete_works_in_any_status(
    ana: TestClient, probe: FakeProbe, settings: Settings, status: str, extra: dict[str, str]
) -> None:
    """`meetings` 30."""
    meeting_id = _create(ana)
    set_fields(settings.database_path, meeting_id, status=status, **extra)
    assert ana.delete(f"{URL}/{meeting_id}").status_code == 204
    assert ana.get(f"{URL}/{meeting_id}").status_code == 404
    assert stored_files(settings.audio_root) == []


def test_late_write_after_delete_does_not_recreate(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 30: gravação tardia do pipeline acha a Reunião ausente e não grava nada."""
    meeting_id = _create(ana)
    set_fields(settings.database_path, meeting_id, status="processing")
    assert ana.delete(f"{URL}/{meeting_id}").status_code == 204
    set_fields(settings.database_path, meeting_id, status="transcribed")
    assert rows(settings.database_path, "SELECT COUNT(*) FROM meetings") == [(0,)]
    assert not (settings.audio_root / meeting_id).exists()


def test_delete_other_users_meeting_is_404_and_intact(
    users: Users, client: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 31; SEC-02."""
    users.use("bia")
    bias = _create(client)
    users.use("ana")
    assert client.delete(f"{URL}/{bias}").status_code == 404
    assert rows(settings.database_path, "SELECT id FROM meetings") == [(bias,)]
    assert (settings.audio_root / bias / "original.mp3").exists()
    users.use("bia")
    assert client.get(f"{URL}/{bias}").status_code == 200


def test_delete_without_origin_is_403(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """SEC-04."""
    meeting_id = _create(ana)
    response = ana.delete(f"{URL}/{meeting_id}", headers={"Origin": "http://evil.example"})
    assert response.status_code == 403
    assert rows(settings.database_path, "SELECT id FROM meetings") == [(meeting_id,)]


def test_delete_is_logged(
    ana: TestClient, probe: FakeProbe, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20: `meeting.deleted` com `user_id` e `meeting_id`."""
    meeting_id = _create(ana)
    caplog.set_level(logging.DEBUG)
    ana.delete(f"{URL}/{meeting_id}")
    [event] = [r for r in caplog.records if r.getMessage() == "meeting.deleted"]
    assert event.meeting_id == meeting_id
    assert event.user_id


def test_symlinked_dir_is_refused_and_logged(
    ana: TestClient,
    probe: FakeProbe,
    settings: Settings,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SEC-15: diretório trocado por link para fora; nada fora de `/audios` é apagado."""
    meeting_id = _create(ana)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("fica")
    meeting_dir = settings.audio_root / meeting_id
    (meeting_dir / "original.mp3").unlink()
    meeting_dir.rmdir()
    meeting_dir.symlink_to(outside, target_is_directory=True)
    caplog.set_level(logging.DEBUG)
    assert ana.delete(f"{URL}/{meeting_id}").status_code == 204
    assert (outside / "keep.txt").read_text() == "fica"
    [event] = [r for r in caplog.records if r.getMessage() == "security.path_rejected"]
    assert event.meeting_id == meeting_id


@pytest.mark.parametrize(
    "forged", ["..", "nao-e-uuid", "%2E%2E", "3F2B8C1E-5D4A-4B6C-9E7F-0A1B2C3D4E5F"]
)
def test_forged_id_is_404_and_deletes_nothing(
    ana: TestClient, probe: FakeProbe, settings: Settings, forged: str
) -> None:
    """SEC-15: `meeting_id` forjado nunca chega ao disco."""
    meeting_id = _create(ana)
    assert ana.delete(f"{URL}/{forged}").status_code in {404, 405}
    assert (settings.audio_root / meeting_id / "original.mp3").exists()
    assert rows(settings.database_path, "SELECT id FROM meetings") == [(meeting_id,)]
