"""Leitura da resposta da LLM (`backlog-generation` 7 a 14; SEC-18).

Pydantic estrito com os máximos de `05-api.md`. Única leitura tolerante: prioridade sem
diferenciar maiúsculas (critério 8) e solicitante desconhecido vazio (critério 13).
Saída só como dado: nunca vira SQL, caminho, comando nem HTML.
"""

import re
from collections.abc import Sequence
from typing import Annotated, Literal, Protocol

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    ValidationError,
)

from snook.core.text import normalize
from snook.modules.backlog_generation import messages

# `05-api.md`, "Tamanhos máximos de entrada".
NAME_MAX = 200
STORY_TEXT_MAX = 2000
CRITERION_TEXT_MAX = 1000
REQUESTER_MAX = 100

STORY_POINTS = (1, 2, 3, 5, 8, 13)
_REQUESTED_AT = re.compile(r"(\d{2}):([0-5]\d):([0-5]\d)")

Priority = Literal["Low", "Medium", "High"]


def _priority(value: object) -> object:
    """`high`, `HIGH` → `High`; outro valor segue para o `Literal` e falha."""
    if isinstance(value, str):
        return value.strip().capitalize()
    return value


def _story_points(value: int) -> int:
    if value not in STORY_POINTS:
        raise ValueError("story_points")
    return value


def _check_requested_at(value: str) -> str:
    if _REQUESTED_AT.fullmatch(value) is None:
        raise ValueError("requested_at")
    return value


def _seconds(value: str) -> int:
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def _text(max_length: int) -> StringConstraints:
    # Espaços nas pontas não contam; só espaço é vazio (critérios 10 e 11).
    return StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class AcceptanceCriterion(_Strict):
    given: Annotated[str, _text(CRITERION_TEXT_MAX)]
    when: Annotated[str, _text(CRITERION_TEXT_MAX)]
    then: Annotated[str, _text(CRITERION_TEXT_MAX)]


class UserStory(_Strict):
    name: Annotated[str, _text(NAME_MAX)]
    as_a: Annotated[str, _text(STORY_TEXT_MAX)]
    i_want: Annotated[str, _text(STORY_TEXT_MAX)]
    so_that: Annotated[str, _text(STORY_TEXT_MAX)]
    priority: Annotated[Priority, BeforeValidator(_priority)]
    story_points: Annotated[StrictInt, AfterValidator(_story_points)]
    requested_by: Annotated[str, StringConstraints(max_length=REQUESTER_MAX)] | None = None
    requested_at: Annotated[str, AfterValidator(_check_requested_at)]
    acceptance_criteria: Annotated[list[AcceptanceCriterion], Field(min_length=1)]

    @property
    def requested_at_seconds(self) -> int:
        return _seconds(self.requested_at)


class Epic(_Strict):
    name: Annotated[str, _text(NAME_MAX)]
    user_stories: list[UserStory]


class BacklogResponse(_Strict):
    epics: list[Epic]


class InvalidBacklogResponse(Exception):
    """Resposta fora do schema. `message` em pt-BR, sem trecho da resposta (critério 15)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_backlog(raw: str, *, duration_seconds: float) -> BacklogResponse:
    """Valida a resposta crua de "Gerar". `requested_at` entre 0 e a duração (critério 12)."""
    try:
        backlog = BacklogResponse.model_validate_json(raw)
    except ValidationError as error:
        if any(item["type"] == "json_invalid" for item in error.errors()):
            raise InvalidBacklogResponse(messages.RESPONSE_NOT_JSON) from None
        raise InvalidBacklogResponse(messages.RESPONSE_OFF_SCHEMA) from None
    for epic in backlog.epics:
        for story in epic.user_stories:
            if story.requested_at_seconds > duration_seconds:
                raise InvalidBacklogResponse(messages.REQUESTED_AT_OUT_OF_RANGE)
    return backlog


class _Named(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def name(self) -> str: ...


def resolve_requester(requested_by: str | None, participants: Sequence[_Named]) -> int | None:
    """`id` do Participante de mesmo nome, sem caixa e espaços nas pontas (critério 13).

    Só compara texto: o nome nunca vai a SQL, caminho ou comando (SEC-18).
    """
    if requested_by is None or not requested_by.strip():
        return None
    wanted = normalize(requested_by)
    for participant in participants:
        if normalize(participant.name) == wanted:
            return participant.id
    return None
