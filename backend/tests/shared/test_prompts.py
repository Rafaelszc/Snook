from typing import Any

from snook.shared import prompts


def _schema() -> dict[str, Any]:
    return prompts.load_backlog_response_schema()


def _story() -> dict[str, Any]:
    story: dict[str, Any] = _schema()["properties"]["epics"]["items"]["properties"]["user_stories"][
        "items"
    ]
    return story


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
    # `[0-9]`, não `\d`: `\d` derruba a gramática do Ollama 0.23 (achado da suíte `llm_real`).
    assert story["requested_at"]["pattern"] == "^[0-9]{2}:[0-5][0-9]:[0-5][0-9]$"
    assert story["acceptance_criteria"]["minItems"] == 1
