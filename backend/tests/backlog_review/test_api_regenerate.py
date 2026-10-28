from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import service as transcript_split
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    save_parts,
    stored_stories,
    story,
)
from tests.backlog_review.helpers import NOT_DONE, backlog_url, leave_done, with_backlog
from tests.diarized_transcription.helpers import state
from tests.transcript_split.helpers import FakeEstimate

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


class FakePrepare:
    """ "Preparar geração" fake: registra o modo e devolve `generating` sem mudar nada."""

    def __init__(self) -> None:
        self.modes: list[str] = []

    def __call__(self, uow: UnitOfWork, meeting_id: str, mode: str, **_: Any) -> str:
        self.modes.append(mode)
        return "generating"


@pytest.fixture
def prepare(monkeypatch: pytest.MonkeyPatch) -> FakePrepare:
    fake = FakePrepare()
    monkeypatch.setattr(transcript_split, "prepare_generation", fake)
    return fake


def _url(meeting_id: str) -> str:
    return f"/api/meetings/{meeting_id}/regenerate"


def _meeting(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(client, settings, uow, generate, ("Cadastro", [story("Cadastrar")]))


def _split(uow: Uow, meeting_id: str) -> None:
    """Reunião dividida: duas Partes gravadas."""
    save_parts(uow, meeting_id, [(0, 1), (2, 2)])


def test_same_cuts_prepares_in_normal_mode(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, prepare: FakePrepare
) -> None:
    """`backlog-review` 26."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = idle.post(_url(meeting_id), json={"mode": "same_cuts"})

    assert response.status_code == 202
    assert response.json() == {"status": "generating"}
    assert prepare.modes == ["normal"]


def test_adjust_cuts_on_split_meeting_prepares_in_adjust_mode(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, prepare: FakePrepare
) -> None:
    """`backlog-review` 27."""
    meeting_id = _meeting(idle, settings, uow, generate)
    _split(uow, meeting_id)

    response = idle.post(_url(meeting_id), json={"mode": "adjust_cuts"})

    assert response.status_code == 202
    assert prepare.modes == ["reajustar"]


def test_adjust_cuts_on_unsplit_meeting_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, prepare: FakePrepare
) -> None:
    """`backlog-review` 27: Parte única não é Reunião dividida."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = idle.post(_url(meeting_id), json={"mode": "adjust_cuts"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "not_split"
    assert prepare.modes == []
    assert state(settings.database_path, meeting_id)[0] == "done"


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    prepare: FakePrepare,
    status: str,
) -> None:
    """`backlog-review` 28, 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    leave_done(settings, meeting_id, status)

    response = idle.post(_url(meeting_id), json={"mode": "same_cuts"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert prepare.modes == []
    assert state(settings.database_path, meeting_id)[0] == status


@pytest.mark.parametrize("body", [{}, {"mode": "partial"}, {"mode": "same_cuts", "extra": 1}])
def test_invalid_body_is_422(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    prepare: FakePrepare,
    body: dict[str, Any],
) -> None:
    """SEC-09."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = idle.post(_url(meeting_id), json=body)

    assert response.status_code == 422
    assert prepare.modes == []


@pytest.fixture
def estimate(idle: TestClient) -> FakeEstimate:
    app: FastAPI = idle.app  # type: ignore[assignment]
    fake = FakeEstimate()
    app.state.estimate_tokens = fake
    return fake


@pytest.mark.usefixtures("estimate")
def test_previous_backlog_stays_until_new_generation_succeeds(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 29; `backlog-generation` 24: falha mantém o anterior; sucesso troca."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()["epics"]
    during: list[Any] = []
    generate.on_call = lambda _: during.append(
        (state(settings.database_path, meeting_id)[0], stored_stories(settings, meeting_id))
    )
    generate.replies = [RuntimeError("falha")]

    response = idle.post(_url(meeting_id), json={"mode": "same_cuts"})

    assert response.json() == {"status": "generating"}
    assert during == [("generating", [(1, "Cadastro", "Cadastrar")])]
    assert state(settings.database_path, meeting_id)[0] == "failed"
    assert idle.get(backlog_url(meeting_id)).json()["epics"] == before

    leave_done(settings, meeting_id, "done")
    generate.replies = [backlog(("Vendas", [story("Vender")]))]
    idle.post(_url(meeting_id), json={"mode": "same_cuts"})

    assert state(settings.database_path, meeting_id)[0] == "done"
    assert stored_stories(settings, meeting_id) == [(1, "Vendas", "Vender")]


def test_other_users_meeting_is_404(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    prepare: FakePrepare,
    users: Users,
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _meeting(idle, settings, uow, generate)
    users.use("bia")

    response = idle.post(_url(meeting_id), json={"mode": "same_cuts"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert prepare.modes == []


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.post(_url("00000000-0000-0000-0000-000000000000"), json={"mode": "same_cuts"})

    assert response.status_code == 401
