from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.participants import service
from tests.auth.helpers import Users
from tests.meetings.helpers import URL, set_fields
from tests.participants.conftest import activate_provider
from tests.participants.helpers import names, stored, transcribed, url

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


@pytest.fixture
def meeting_id(idle: TestClient, settings: Settings) -> str:
    activate_provider(settings)
    return transcribed(idle, settings)


def test_one_name_per_speaker_creates_participants(
    idle: TestClient, settings: Settings, meeting_id: str
) -> None:
    """`participants` 6."""
    response = idle.put(url(meeting_id), json=names())

    assert response.status_code == 200
    body = response.json()
    assert [(p["name"], p["speaker_labels"]) for p in body] == [
        ("Ana", ["SPEAKER_00"]),
        ("Bia", ["SPEAKER_01"]),
        ("Caio", ["SPEAKER_02"]),
    ]
    assert all(isinstance(p["id"], int) for p in body)
    assert stored(settings.database_path) == (
        [("Ana", "ana"), ("Bia", "bia"), ("Caio", "caio")],
        [("SPEAKER_00", "Ana"), ("SPEAKER_01", "Bia"), ("SPEAKER_02", "Caio")],
    )


def test_same_name_joins_speakers_first_spelling_wins(
    idle: TestClient, settings: Settings, meeting_id: str
) -> None:
    """`participants` 7: caixa e espaços nas pontas ignorados; grava o primeiro, aparado."""
    response = idle.put(
        url(meeting_id), json=names(SPEAKER_00="  Ana Souza ", SPEAKER_02="ANA SOUZA")
    )

    assert response.status_code == 200
    assert [(p["name"], p["speaker_labels"]) for p in response.json()] == [
        ("Ana Souza", ["SPEAKER_00", "SPEAKER_02"]),
        ("Bia", ["SPEAKER_01"]),
    ]
    assert stored(settings.database_path)[0] == [("Ana Souza", "ana souza"), ("Bia", "bia")]


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_422_and_nothing_stored(
    idle: TestClient, settings: Settings, meeting_id: str, name: str
) -> None:
    """`participants` 8."""
    response = idle.put(url(meeting_id), json=names(SPEAKER_01=name))

    assert response.status_code == 422
    assert "names.SPEAKER_01" in response.json()["error"]["fields"]
    assert stored(settings.database_path) == ([], [])


def test_missing_speaker_is_422_and_nothing_stored(
    idle: TestClient, settings: Settings, meeting_id: str
) -> None:
    """`participants` 8."""
    body = names()
    del body["names"]["SPEAKER_02"]

    response = idle.put(url(meeting_id), json=body)

    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {"names.SPEAKER_02"}
    assert stored(settings.database_path) == ([], [])


@pytest.mark.parametrize("label", ["SPEAKER_09", "../x"])
def test_unknown_speaker_label_is_422_and_nothing_stored(
    idle: TestClient, settings: Settings, meeting_id: str, label: str
) -> None:
    """`participants` 9; rótulo fora do formato também é 422 (SEC-09)."""
    body = names()
    body["names"][label] = "Davi"

    response = idle.put(url(meeting_id), json=body)

    assert response.status_code == 422
    assert stored(settings.database_path) == ([], [])


def test_name_over_100_is_422(idle: TestClient, settings: Settings, meeting_id: str) -> None:
    """`05-api.md`: nome de Participante com no máximo 100 caracteres."""
    response = idle.put(url(meeting_id), json=names(SPEAKER_00="x" * 101))

    assert response.status_code == 422
    assert stored(settings.database_path) == ([], [])


def test_name_of_100_is_accepted(idle: TestClient, meeting_id: str) -> None:
    assert idle.put(url(meeting_id), json=names(SPEAKER_00="x" * 100)).status_code == 200


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "processing"},
        {"status": "needs_split"},
        {"status": "generating"},
        {"status": "done"},
        {"status": "failed", "failed_stage": "generation", "error_message": "x"},
    ],
)
def test_outside_transcribed_is_409(
    idle: TestClient, settings: Settings, meeting_id: str, fields: dict[str, str]
) -> None:
    """`participants` 12."""
    set_fields(settings.database_path, meeting_id, **fields)

    response = idle.put(url(meeting_id), json=names())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert stored(settings.database_path) == ([], [])


def test_second_put_is_409_and_names_kept(
    idle: TestClient, settings: Settings, meeting_id: str
) -> None:
    """`participants` 13."""
    assert idle.put(url(meeting_id), json=names()).status_code == 200
    before = stored(settings.database_path)

    response = idle.put(url(meeting_id), json=names(SPEAKER_00="Outra"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_confirmed"
    assert stored(settings.database_path) == before


def test_second_put_after_generation_retry_is_409(
    idle: TestClient, settings: Settings, meeting_id: str
) -> None:
    """`participants` 13 (Q54): retry de `generation` volta a `transcribed`; nomes não mudam."""
    assert idle.put(url(meeting_id), json=names()).status_code == 200
    before = stored(settings.database_path)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="x",
    )
    assert idle.post(f"{URL}/{meeting_id}/retry").status_code == 202
    assert idle.get(f"{URL}/{meeting_id}").json()["status"] == "transcribed"

    response = idle.put(url(meeting_id), json=names(SPEAKER_00="Outra"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_confirmed"
    assert stored(settings.database_path) == before


def test_get_lists_participants_with_speaker_labels(idle: TestClient, meeting_id: str) -> None:
    """`participants` 14."""
    created = idle.put(url(meeting_id), json=names(SPEAKER_02="ana")).json()

    response = idle.get(url(meeting_id))

    assert response.status_code == 200
    assert response.json() == created
    assert [(p["name"], p["speaker_labels"]) for p in created] == [
        ("Ana", ["SPEAKER_00", "SPEAKER_02"]),
        ("Bia", ["SPEAKER_01"]),
    ]


def test_get_before_confirmation_is_empty(idle: TestClient, meeting_id: str) -> None:
    assert idle.get(url(meeting_id)).json() == []


def test_participant_for_joined_speakers_is_the_same(
    idle: TestClient, meeting_id: str, uow: Uow
) -> None:
    """`participants` 15."""
    idle.put(url(meeting_id), json=names(SPEAKER_02="Ana"))

    with uow() as unit:
        first = service.participant_for_speaker(unit, meeting_id, "SPEAKER_00")
        second = service.participant_for_speaker(unit, meeting_id, "SPEAKER_02")
        other = service.participant_for_speaker(unit, meeting_id, "SPEAKER_01")
        missing = service.participant_for_speaker(unit, meeting_id, "SPEAKER_09")

    assert first is not None and other is not None
    assert first == second
    assert first.speaker_labels == ["SPEAKER_00", "SPEAKER_02"]
    assert other.id != first.id
    assert missing is None


def test_other_users_meeting_is_404_and_unchanged(
    idle: TestClient, settings: Settings, users: Users, meeting_id: str
) -> None:
    """`participants` 23; SEC-02."""
    activate_provider(settings, "bia")
    users.use("bia")

    put = idle.put(url(meeting_id), json=names())
    get = idle.get(url(meeting_id))

    assert (put.status_code, get.status_code) == (404, 404)
    assert put.json()["error"]["code"] == get.json()["error"]["code"] == "meeting_not_found"
    assert stored(settings.database_path) == ([], [])


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_without_session_is_401(client: TestClient, method: str) -> None:
    """`participants` 24; SEC-01."""
    response = client.request(method, url("00000000-0000-0000-0000-000000000000"), json=names())
    assert response.status_code == 401
