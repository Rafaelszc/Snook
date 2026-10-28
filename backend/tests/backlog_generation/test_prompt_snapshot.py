from pathlib import Path

from fastapi import FastAPI

from snook.shared import prompts

# Mudar o prompt pede atualizar este snapshot e `BACKLOG_PROMPT_VERSION` no mesmo commit.
SNAPSHOT = Path(__file__).parent / "snapshots" / "system_prompt.md"


def test_prompt_snapshot() -> None:
    """`backlog-generation` 31."""
    text = prompts.load_backlog_system_prompt()

    assert text == SNAPSHOT.read_text(encoding="utf-8")
    assert prompts.BACKLOG_PROMPT_VERSION == "1"


def test_prompt_asks_for_contract() -> None:
    """`backlog-generation` 31: pt-BR, schema, prioridade, pontos, solicitante e instante."""
    text = prompts.load_backlog_system_prompt()

    for expected in (
        "pt-BR",
        '"epics"',
        '"user_stories"',
        '"acceptance_criteria"',
        "Low",
        "Medium",
        "High",
        "1, 2, 3, 5, 8 ou 13",
        "Participantes",
        "hh:mm:ss",
    ):
        assert expected in text


def test_no_route_exposes_prompt(app: FastAPI) -> None:
    """`backlog-generation` 30."""
    paths = [getattr(route, "path", "") for route in app.routes]

    assert not [path for path in paths if "prompt" in path]
