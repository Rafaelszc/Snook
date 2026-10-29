import json
import logging
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings
from tests.auth.helpers import Users, rows
from tests.meetings.helpers import URL, FakeProbe, set_fields, upload

UNKNOWN_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
SUMMARY_FIELDS = {
    "id",
    "title",
    "created_at",
    "duration_seconds",
    "status",
    "participants_confirmed",
}
DETAIL_FIELDS = SUMMARY_FIELDS | {
    "original_filename",
    "expected_speakers",
    "has_backlog",
    "failed_stage",
    "error_message",
    "split_reason",
}


def _create(client: TestClient, **data: Any) -> str:
    response = upload(client, **data)
    assert response.status_code == 201
    meeting_id: str = response.json()["id"]
    return meeting_id


def _rename(client: TestClient, meeting_id: str, title: Any) -> Any:
    return client.patch(f"{URL}/{meeting_id}", json={"title": title})


def test_list_is_newest_first_with_summary_fields(
    ana: TestClient, probe: FakeProbe, clock: FakeClock
) -> None:
    """`meetings` 19."""
    first = _create(ana, title="Primeira")
    clock.advance(timedelta(minutes=1))
    second = _create(ana, title="Segunda")
    body = ana.get(URL).json()
    assert [m["id"] for m in body] == [second, first]
    assert set(body[0]) == SUMMARY_FIELDS
    assert body[0] == {
        "id": second,
        "title": "Segunda",
        "created_at": "2026-10-23T12:01:00Z",
        "duration_seconds": 60.0,
        "status": "pending",
        "participants_confirmed": False,
    }


def test_list_has_only_own_meetings(users: Users, client: TestClient, probe: FakeProbe) -> None:
    """`meetings` 19, 32."""
    users.use("bia")
    _create(client, title="Da Bia")
    users.use("ana")
    mine = _create(client, title="Da Ana")
    assert [m["id"] for m in client.get(URL).json()] == [mine]


def test_list_is_empty_without_meetings(ana: TestClient) -> None:
    assert ana.get(URL).json() == []


def test_detail_has_listing_fields_and_flags(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 20."""
    meeting_id = _create(ana, title="Daily", expected_speakers="3")
    body = ana.get(f"{URL}/{meeting_id}").json()
    assert set(body) == DETAIL_FIELDS
    assert body["original_filename"] == "reuniao.mp3"
    assert body["expected_speakers"] == 3
    assert body["participants_confirmed"] is False
    assert body["has_backlog"] is False
    assert body["failed_stage"] is None
    assert body["error_message"] is None

    set_fields(
        settings.database_path,
        meeting_id,
        participants_confirmed_at="2026-10-23T12:05:00Z",
        backlog_saved_at="2026-10-23T12:06:00Z",
    )
    body = ana.get(f"{URL}/{meeting_id}").json()
    assert body["participants_confirmed"] is True
    assert body["has_backlog"] is True
    [item] = ana.get(URL).json()
    assert item["participants_confirmed"] is True


def test_detail_in_failed_has_stage_and_message(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 20."""
    meeting_id = _create(ana)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="transcription",
        error_message="Falha ao transcrever.",
    )
    body = ana.get(f"{URL}/{meeting_id}").json()
    assert body["status"] == "failed"
    assert body["failed_stage"] == "transcription"
    assert body["error_message"] == "Falha ao transcrever."


def test_no_response_exposes_internal_path(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 21."""
    meeting_id = _create(ana)
    root = str(settings.audio_root)
    for response in (
        ana.get(URL),
        ana.get(f"{URL}/{meeting_id}"),
        _rename(ana, meeting_id, "Novo"),
    ):
        dumped = json.dumps(response.json())
        assert root not in dumped
        assert "original.mp3" not in dumped
        assert "file_ext" not in dumped


def test_patch_strips_title_and_keeps_other_fields(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 16."""
    meeting_id = _create(ana, title="Antigo", expected_speakers="2")
    before = ana.get(f"{URL}/{meeting_id}").json()
    response = _rename(ana, meeting_id, "  Planejamento Q4  ")
    assert response.status_code == 200
    assert response.json() == {**before, "title": "Planejamento Q4"}
    assert ana.get(f"{URL}/{meeting_id}").json() == {**before, "title": "Planejamento Q4"}
    assert rows(settings.database_path, "SELECT title FROM meetings") == [("Planejamento Q4",)]


@pytest.mark.parametrize("title", ["", "   "])
def test_patch_blank_title_is_422_and_keeps_title(
    ana: TestClient, probe: FakeProbe, title: str
) -> None:
    """`meetings` 17."""
    meeting_id = _create(ana, title="Antigo")
    response = _rename(ana, meeting_id, title)
    assert response.status_code == 422
    assert "title" in response.json()["error"]["fields"]
    assert ana.get(f"{URL}/{meeting_id}").json()["title"] == "Antigo"


@pytest.mark.parametrize("title", ["a" * 201, None, 5])
def test_patch_invalid_title_is_422(ana: TestClient, probe: FakeProbe, title: Any) -> None:
    meeting_id = _create(ana, title="Antigo")
    assert _rename(ana, meeting_id, title).status_code == 422
    assert ana.get(f"{URL}/{meeting_id}").json()["title"] == "Antigo"


def test_patch_title_at_200_chars_is_accepted(ana: TestClient, probe: FakeProbe) -> None:
    meeting_id = _create(ana)
    assert _rename(ana, meeting_id, "a" * 200).json()["title"] == "a" * 200


def test_patch_extra_field_is_422(ana: TestClient, probe: FakeProbe) -> None:
    """SEC-09."""
    meeting_id = _create(ana, title="Antigo")
    response = ana.patch(f"{URL}/{meeting_id}", json={"title": "Novo", "status": "done"})
    assert response.status_code == 422
    assert ana.get(f"{URL}/{meeting_id}").json()["status"] == "pending"


@pytest.mark.parametrize(
    ("status", "extra"),
    [
        ("pending", {}),
        ("processing", {}),
        ("transcribed", {}),
        ("needs_split", {"split_reason": "too_long"}),
        ("generating", {}),
        ("done", {}),
        ("failed", {"failed_stage": "generation", "error_message": "Erro."}),
    ],
)
def test_patch_works_in_any_status(
    ana: TestClient, probe: FakeProbe, settings: Settings, status: str, extra: dict[str, str]
) -> None:
    """`meetings` 18."""
    meeting_id = _create(ana)
    set_fields(settings.database_path, meeting_id, status=status, **extra)
    response = _rename(ana, meeting_id, "Novo")
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert ana.get(f"{URL}/{meeting_id}").json()["title"] == "Novo"


def test_patch_without_origin_is_403(ana: TestClient, probe: FakeProbe, settings: Settings) -> None:
    """SEC-04."""
    meeting_id = _create(ana, title="Antigo")
    response = ana.patch(
        f"{URL}/{meeting_id}", json={"title": "Novo"}, headers={"Origin": "http://evil.example"}
    )
    assert response.status_code == 403
    assert rows(settings.database_path, "SELECT title FROM meetings") == [("Antigo",)]


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_other_users_meeting_is_404_and_unchanged(
    users: Users, client: TestClient, probe: FakeProbe, settings: Settings, method: str
) -> None:
    """`meetings` 31; SEC-02."""
    users.use("bia")
    bias = _create(client, title="Da Bia")
    users.use("ana")
    response = client.request(method, f"{URL}/{bias}", json={"title": "Roubado"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert rows(settings.database_path, "SELECT title FROM meetings") == [("Da Bia",)]


@pytest.mark.parametrize("meeting_id", [UNKNOWN_ID, "nao-e-uuid", "..%2F..%2Fetc"])
def test_unknown_meeting_is_404(ana: TestClient, meeting_id: str) -> None:
    assert ana.get(f"{URL}/{meeting_id}").status_code == 404


def test_access_to_other_users_meeting_is_logged(
    users: Users, client: TestClient, probe: FakeProbe, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20: `security.access_denied` com `user_id`, `resource`, `resource_id`."""
    users.use("bia")
    bias = _create(client)
    users.use("ana")
    caplog.set_level(logging.DEBUG)
    client.get(f"{URL}/{bias}")
    [event] = [r for r in caplog.records if r.getMessage() == "security.access_denied"]
    assert event.resource == "meeting"
    assert event.resource_id == bias
    assert event.user_id != bias


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", URL),
        ("GET", f"{URL}/{UNKNOWN_ID}"),
        ("PATCH", f"{URL}/{UNKNOWN_ID}"),
        ("DELETE", f"{URL}/{UNKNOWN_ID}"),
    ],
)
def test_without_session_is_401(client: TestClient, method: str, path: str) -> None:
    """`meetings` 33; SEC-01."""
    assert client.request(method, path, json={"title": "x"}).status_code == 401
