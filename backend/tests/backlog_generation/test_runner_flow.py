import sqlite3
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.shared.prompts import load_backlog_response_schema, load_backlog_system_prompt
from tests.auth.helpers import rows
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    generating,
    part_texts,
    parts_ready,
    story,
)
from tests.diarized_transcription.helpers import state
from tests.participants.conftest import activate_provider

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
THREE_PARTS = [(0, 0), (1, 1), (2, 2)]


def test_single_part_one_call_and_done(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 1: Parte única, uma chamada, grava e vai a `done`."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]

    parts_ready(idle, meeting_id)

    assert len(generate.calls) == 1
    assert state(settings.database_path, meeting_id) == ("done", None, None)
    assert rows(settings.database_path, "SELECT count(*) FROM user_stories") == [(1,)]


def test_three_parts_in_order(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 2, 3: uma chamada por Parte, na ordem, com o "Texto da Parte" intacto,
    o System Prompt e os nomes dos Participantes."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog(("Cadastro", [story(str(i))])) for i in range(3)]

    parts_ready(idle, meeting_id)

    texts = part_texts(uow, meeting_id)
    assert len(generate.calls) == 3
    for call, text in zip(generate.calls, texts, strict=True):
        assert call["system_prompt"] == load_backlog_system_prompt()
        assert call["json_schema"] == load_backlog_response_schema()
        assert call["content"].endswith(f"Texto da Parte:\n{text}")
        assert "- Ana\n- Bia" in call["content"]


def test_epic_names_from_second_part(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 4: a primeira chamada não leva Epics; as seguintes, as já criadas."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [
        backlog(("Cadastro", [story("A")])),
        backlog(("cadastro ", [story("B")]), ("Relatórios", [story("C")])),
        backlog(),
    ]

    parts_ready(idle, meeting_id)

    first, second, third = (call["content"] for call in generate.calls)
    assert "Epics já criadas" not in first
    assert "Epics já criadas:\n- Cadastro\n\n" in second
    assert "Epics já criadas:\n- Cadastro\n- Relatórios\n\n" in third


def test_provider_read_once(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 5: troca do modelo ativo durante a geração não muda as chamadas."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog()] * 3

    def change_model(call: int) -> None:
        with sqlite3.connect(settings.database_path) as conn:
            conn.execute("UPDATE llm_configs SET model = 'outro', context_window = 1000")

    generate.on_call = change_model

    parts_ready(idle, meeting_id)

    snapshots = {call["provider_snapshot"] for call in generate.calls}
    assert [(s.model, s.context_window) for s in snapshots] == [("llama3", 8192)]
    assert {call["max_output_tokens"] for call in generate.calls} == {2048}


def test_uses_owner_config(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 6; SEC-26: só a configuração do dono, nunca a de outro Usuário."""
    meeting_id = generating(idle, settings, uow)
    activate_provider(settings, "bia")
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            "UPDATE llm_configs SET model = 'de-bia' "
            "WHERE user_id = (SELECT id FROM users WHERE username = 'bia')"
        )
    [(ana_id,)] = rows(settings.database_path, "SELECT id FROM users WHERE username = 'ana'")
    generate.replies = [backlog()]

    parts_ready(idle, meeting_id)

    [call] = generate.calls
    assert call["user_id"] == ana_id
    assert call["provider_snapshot"].model == "llama3"
