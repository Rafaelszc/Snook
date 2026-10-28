import hashlib
from typing import Any

from fastapi import FastAPI

from snook.shared import prompts

# Snapshot do System Prompt (`backlog-generation` 31): mudar o prompt pede atualizar o hash
# e `BACKLOG_PROMPT_VERSION` no mesmo commit.
PROMPT_SHA256 = "22a0f0d90fc8fdff8aaee9a013db80f81da3ba9a9efb94b7d015c8152162fdbc"


def _schema() -> dict[str, Any]:
    return prompts.load_backlog_response_schema()


def _story() -> dict[str, Any]:
    story: dict[str, Any] = _schema()["properties"]["epics"]["items"]["properties"]["user_stories"][
        "items"
    ]
    return story


def test_prompt_snapshot() -> None:
    """`backlog-generation` 31."""
    text = prompts.load_backlog_system_prompt()

    assert hashlib.sha256(text.encode()).hexdigest() == PROMPT_SHA256
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


def test_schema_closed_with_required_fields() -> None:
    """SEC-18: só os campos do schema; todos obrigatórios."""
    schema = _schema()
    epic = schema["properties"]["epics"]["items"]
    story = _story()
    criterion = story["properties"]["acceptance_criteria"]["items"]

    for node, fields in (
        (schema, ["epics"]),
        (epic, ["name", "user_stories"]),
        (
            story,
            [
                "name",
                "as_a",
                "i_want",
                "so_that",
                "priority",
                "story_points",
                "requested_by",
                "requested_at",
                "acceptance_criteria",
            ],
        ),
        (criterion, ["given", "when", "then"]),
    ):
        assert node["additionalProperties"] is False
        assert node["required"] == fields
        assert list(node["properties"]) == fields


def test_schema_max_lengths_follow_api() -> None:
    """SEC-18: tamanhos máximos de `05-api.md`."""
    epic = _schema()["properties"]["epics"]["items"]
    story = _story()
    criterion = story["properties"]["acceptance_criteria"]["items"]

    assert epic["properties"]["name"]["maxLength"] == 200
    assert story["properties"]["name"]["maxLength"] == 200
    for field in ("as_a", "i_want", "so_that"):
        assert story["properties"][field]["maxLength"] == 2000
    for field in ("given", "when", "then"):
        assert criterion["properties"][field]["maxLength"] == 1000
    assert story["properties"]["requested_by"]["maxLength"] == 100


def test_schema_value_rules() -> None:
    """`backlog-generation` 9, 10, 12: pontos, critério obrigatório e `hh:mm:ss`."""
    story = _story()["properties"]

    assert story["priority"]["enum"] == ["Low", "Medium", "High"]
    assert story["story_points"]["enum"] == [1, 2, 3, 5, 8, 13]
    assert story["requested_at"]["pattern"] == r"^\d{2}:[0-5]\d:[0-5]\d$"
    assert story["acceptance_criteria"]["minItems"] == 1


def test_no_route_exposes_prompt(app: FastAPI) -> None:
    """`backlog-generation` 30."""
    paths = [getattr(route, "path", "") for route in app.routes]

    assert not [path for path in paths if "prompt" in path]
