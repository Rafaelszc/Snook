"""Validação da resposta da LLM (`backlog-generation` 7 a 12 e 14; SEC-18)."""

import copy
import json
from typing import Any

import pytest

from snook.modules.backlog_generation.validation import InvalidBacklogResponse, parse_backlog

DURATION = 3_600.0


def _story(**overrides: Any) -> dict[str, Any]:
    story: dict[str, Any] = {
        "name": "Cadastrar cliente pessoa física",
        "as_a": "atendente",
        "i_want": "cadastrar um cliente com CPF",
        "so_that": "eu possa abrir pedidos em nome dele",
        "priority": "High",
        "story_points": 5,
        "requested_by": "Ana",
        "requested_at": "00:42:10",
        "acceptance_criteria": [
            {"given": "um CPF válido", "when": "eu salvo o cadastro", "then": "o cliente aparece"},
            {"given": "um CPF inválido", "when": "eu salvo", "then": "vejo um erro"},
        ],
    }
    story.update(overrides)
    return story


def _response(**overrides: Any) -> dict[str, Any]:
    return {"epics": [{"name": "Cadastro de clientes", "user_stories": [_story(**overrides)]}]}


def _parse(payload: Any, duration: float = DURATION) -> Any:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return parse_backlog(raw, duration_seconds=duration)


def test_valid_response_keeps_every_field() -> None:
    """Critério 7: campo a campo, critérios na ordem recebida, instante em segundos."""
    backlog = _parse(_response())

    epic = backlog.epics[0]
    story = epic.user_stories[0]
    assert epic.name == "Cadastro de clientes"
    assert story.name == "Cadastrar cliente pessoa física"
    assert (story.as_a, story.i_want, story.so_that) == (
        "atendente",
        "cadastrar um cliente com CPF",
        "eu possa abrir pedidos em nome dele",
    )
    assert (story.priority, story.story_points) == ("High", 5)
    assert story.requested_by == "Ana"
    assert story.requested_at_seconds == 42 * 60 + 10
    assert [c.given for c in story.acceptance_criteria] == ["um CPF válido", "um CPF inválido"]


def test_empty_epics_is_valid() -> None:
    """Critério 21: geração sem US é válida."""
    assert _parse({"epics": []}).epics == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("high", "High"), ("HIGH", "High"), ("medium", "Medium"), ("lOw", "Low"), (" Low ", "Low")],
)
def test_priority_ignores_case(raw: str, expected: str) -> None:
    """Critério 8."""
    assert _parse(_response(priority=raw)).epics[0].user_stories[0].priority == expected


@pytest.mark.parametrize("points", [1, 2, 3, 5, 8, 13])
def test_story_points_on_scale(points: int) -> None:
    """Critério 9."""
    assert _parse(_response(story_points=points)).epics[0].user_stories[0].story_points == points


def test_requested_by_null_or_missing_is_valid() -> None:
    """Critério 13: solicitante ausente não invalida."""
    assert _parse(_response(requested_by=None)).epics[0].user_stories[0].requested_by is None
    payload = _response()
    del payload["epics"][0]["user_stories"][0]["requested_by"]
    assert _parse(payload).epics[0].user_stories[0].requested_by is None


@pytest.mark.parametrize(
    ("value", "seconds"), [("00:00:00", 0), ("01:00:00", 3_600), ("00:59:59", 3_599)]
)
def test_requested_at_within_duration(value: str, seconds: int) -> None:
    """Critério 12: limites 0 e duração inclusos."""
    story = _parse(_response(requested_at=value)).epics[0].user_stories[0]
    assert story.requested_at_seconds == seconds


def _without(path: tuple[str | int, ...]) -> dict[str, Any]:
    payload = _response()
    node: Any = payload
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return payload


def _with(path: tuple[str | int, ...], value: Any) -> dict[str, Any]:
    payload = copy.deepcopy(_response())
    node: Any = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return payload


STORY = ("epics", 0, "user_stories", 0)
CRITERION = (*STORY, "acceptance_criteria", 0)

INVALID: list[tuple[str, Any]] = [
    # Critério 8: prioridade fora de Low/Medium/High.
    ("priority_unknown", _response(priority="Urgent")),
    ("priority_empty", _response(priority="")),
    ("priority_number", _response(priority=1)),
    # Critério 9: story points fora da escala ou de outro tipo.
    ("points_4", _response(story_points=4)),
    ("points_0", _response(story_points=0)),
    ("points_21", _response(story_points=21)),
    ("points_string", _response(story_points="5")),
    ("points_float", _response(story_points=5.0)),
    ("points_bool", _response(story_points=True)),
    # Critério 10: sem critério ou com parte vazia.
    ("no_criteria", _response(acceptance_criteria=[])),
    ("criteria_missing", _without((*STORY, "acceptance_criteria"))),
    ("given_empty", _with((*CRITERION, "given"), "")),
    ("when_blank", _with((*CRITERION, "when"), "   ")),
    ("then_missing", _without((*CRITERION, "then"))),
    # Critério 11: textos obrigatórios vazios.
    ("epic_name_empty", _with(("epics", 0, "name"), "")),
    ("story_name_blank", _response(name="  ")),
    ("as_a_empty", _response(as_a="")),
    ("i_want_empty", _response(i_want="")),
    ("so_that_missing", _without((*STORY, "so_that"))),
    # Critério 12: instante fora da duração ou de outro formato.
    ("at_after_duration", _response(requested_at="01:00:01")),
    ("at_no_hours", _response(requested_at="42:10")),
    ("at_bad_minutes", _response(requested_at="00:60:00")),
    ("at_seconds_number", _response(requested_at=2530)),
    ("at_missing", _without((*STORY, "requested_at"))),
    ("at_negative", _response(requested_at="-00:00:01")),
    # Critério 14: não é JSON ou não segue o schema.
    ("not_json", "Aqui está o backlog: {epics: []}"),
    ("empty_text", ""),
    ("json_list", []),
    ("no_epics", {}),
    ("extra_top_field", {"epics": [], "notes": "x"}),
    ("extra_story_field", _response(html="<script>alert(1)</script>")),
    ("epics_not_list", {"epics": {"name": "x"}}),
    ("stories_missing", _without(("epics", 0, "user_stories"))),
    ("name_not_string", _response(name=["a"])),
    ("requested_by_number", _response(requested_by=7)),
    # SEC-18: campo acima do tamanho máximo de `05-api.md`.
    ("epic_name_201", _with(("epics", 0, "name"), "x" * 201)),
    ("story_name_201", _response(name="x" * 201)),
    ("as_a_2001", _response(as_a="x" * 2001)),
    ("i_want_2001", _response(i_want="x" * 2001)),
    ("so_that_2001", _response(so_that="x" * 2001)),
    ("given_1001", _with((*CRITERION, "given"), "x" * 1001)),
    ("when_1001", _with((*CRITERION, "when"), "x" * 1001)),
    ("then_1001", _with((*CRITERION, "then"), "x" * 1001)),
    ("requested_by_101", _response(requested_by="x" * 101)),
]


@pytest.mark.parametrize("payload", [p for _, p in INVALID], ids=[name for name, _ in INVALID])
def test_invalid_response(payload: Any) -> None:
    """Critérios 8 a 12 e 14; SEC-18: uma resposta fake por regra."""
    with pytest.raises(InvalidBacklogResponse):
        _parse(payload)


def test_fields_at_max_length_are_valid() -> None:
    """SEC-18: o máximo é inclusivo."""
    payload = _response(
        name="x" * 200,
        as_a="x" * 2000,
        i_want="x" * 2000,
        so_that="x" * 2000,
        requested_by="x" * 100,
    )
    payload["epics"][0]["name"] = "e" * 200
    payload["epics"][0]["user_stories"][0]["acceptance_criteria"] = [
        {"given": "g" * 1000, "when": "w" * 1000, "then": "t" * 1000}
    ]
    assert _parse(payload).epics[0].name == "e" * 200


def test_text_fields_are_stripped() -> None:
    """Espaços nas pontas não contam; nome gravado sem eles (critério 16)."""
    payload = _with(("epics", 0, "name"), "  Cadastro  ")
    assert _parse(payload).epics[0].name == "Cadastro"


def test_error_message_does_not_echo_response() -> None:
    """SEC-18: a mensagem é pt-BR fixa, sem trecho da resposta da LLM."""
    with pytest.raises(InvalidBacklogResponse) as caught:
        _parse(_response(name="<script>segredo</script>" + "x" * 300))

    assert "segredo" not in caught.value.message
    assert "segredo" not in str(caught.value)
