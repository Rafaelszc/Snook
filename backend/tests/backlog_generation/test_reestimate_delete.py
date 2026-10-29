import sqlite3
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import messages, runner
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    count,
    generating,
    part_texts,
    parts_ready,
    story,
)
from tests.diarized_transcription.helpers import state

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
THREE_PARTS = [(0, 0), (1, 1), (2, 2)]
TABLES = ("epics", "user_stories", "acceptance_criteria")


class TooLarge:
    """ "Estimar tokens" fake: um token por caractere; `huge` não cabe em orçamento nenhum."""

    def __init__(self, huge: str | None = None) -> None:
        self.huge = huge
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, provider: str, model: str, text: str) -> int:
        self.calls.append((provider, model, text))
        return 10**9 if text == self.huge else len(text)


def _use(client: TestClient, estimate: TooLarge) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.estimate_tokens = estimate


def test_part_that_no_longer_fits_fails_before_call(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 32; RT-10: Parte 2 não cabe: só a 1 é chamada, nada gravado."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    _use(idle, TooLarge(huge=part_texts(uow, meeting_id)[1]))
    generate.replies = [backlog(("Cadastro", [story()]))] * 3

    parts_ready(idle, meeting_id)

    assert state(settings.database_path, meeting_id) == (
        "failed",
        "generation",
        messages.PART_TOO_LARGE.format(index=2),
    )
    assert len(generate.calls) == 1
    assert [count(settings, table) for table in TABLES] == [0, 0, 0]


def test_reestimate_uses_model_read_at_start(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 32: cada Parte reestimada com o modelo lido no início."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    texts = part_texts(uow, meeting_id)
    estimate = TooLarge()
    _use(idle, estimate)
    generate.replies = [backlog()] * 3

    def change_model(_call: int) -> None:
        with sqlite3.connect(settings.database_path) as conn:
            conn.execute("UPDATE llm_configs SET model = 'outro'")

    generate.on_call = change_model

    parts_ready(idle, meeting_id)

    assert state(settings.database_path, meeting_id) == ("done", None, None)
    part_calls = [call for call in estimate.calls if call[2] in texts]
    assert part_calls == [("ollama", "llama3", text) for text in texts]


def test_window_smaller_than_reserve_fails(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """RT-10: orçamento zero ou negativo é "não cabe"."""
    meeting_id = generating(idle, settings, uow)
    _use(idle, TooLarge())
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE llm_configs SET context_window = 100")

    parts_ready(idle, meeting_id)

    assert state(settings.database_path, meeting_id)[2] == messages.PART_TOO_LARGE.format(index=1)
    assert generate.calls == []


def test_deleted_mid_generation_writes_nothing_after(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 28: excluída na Parte 2, nem backlog nem status voltam ao banco."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog(("A", [story()])), backlog(("B", [story()])), "não é JSON"]

    def delete(call: int) -> None:
        if call == 2:
            assert idle.delete(f"/api/meetings/{meeting_id}").status_code == 204

    generate.on_call = delete

    parts_ready(idle, meeting_id)

    assert count(settings, "meetings") == 0
    assert [count(settings, table) for table in TABLES] == [0, 0, 0]


def test_exception_in_final_save_does_not_stick(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-19: falha na gravação final vai a `failed`, nunca fica em `generating`."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disco cheio")

    monkeypatch.setattr(runner.BacklogRepository, "replace", broken)

    parts_ready(idle, meeting_id)

    assert state(settings.database_path, meeting_id) == (
        "failed",
        "generation",
        messages.UNEXPECTED,
    )
