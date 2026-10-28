import re
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)
from pydantic_core import PydanticCustomError

from snook.core.errors import FIELD_MESSAGE_ERROR
from snook.modules.backlog_review import messages
from snook.modules.participants.schemas import ParticipantName, ParticipantOut

# `05-api.md`, "Tamanhos máximos de entrada".
EPIC_NAME_MAX = 200
STORY_NAME_MAX = 200
STORY_TEXT_MAX = 2000
CRITERION_TEXT_MAX = 1000

PRIORITIES = ("Low", "Medium", "High")
STORY_POINTS = (1, 2, 3, 5, 8, 13)
_TIMESTAMP = re.compile(r"(\d{2}):([0-5]\d):([0-5]\d)")


class RequesterOut(BaseModel):
    id: int
    name: str


class CriterionOut(BaseModel):
    id: int
    given: str
    when: str
    then: str


class UserStoryOut(BaseModel):
    """`requested_at` em `hh:mm:ss`; vazio em US manual (`backlog-review` 1)."""

    id: int
    us_id: str
    name: str
    as_a: str
    i_want: str
    so_that: str
    priority: str
    story_points: int
    requested_by: RequesterOut | None
    requested_at: str | None
    acceptance_criteria: list[CriterionOut]


class EpicOut(BaseModel):
    id: int
    name: str
    user_stories: list[UserStoryOut]


class BacklogOut(BaseModel):
    """`GET /backlog`. Sem informação de Parte (`backlog-review` 2)."""

    read_only: bool
    last_generation_failed: bool
    epics: list[EpicOut]


class EpicName(BaseModel):
    """Corpo de criar e renomear Epic. Aparado; vazio ou acima do máximo: 422
    (`backlog-review` 5, 9; SEC-09)."""

    model_config = ConfigDict(extra="forbid")

    name: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.EPIC_NAME_REQUIRED)
        if len(value) > EPIC_NAME_MAX:
            raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.EPIC_NAME_TOO_LONG)
        return value


class EpicSummary(BaseModel):
    id: int
    name: str


class EpicRenamed(EpicSummary):
    """Epic que ficou. `merged_into` igual ao `id` quando juntou (`backlog-review` 6)."""

    merged_into: int | None


def _invalid(message: str) -> PydanticCustomError:
    return PydanticCustomError(FIELD_MESSAGE_ERROR, message)


def _text(max_length: int) -> AfterValidator:
    """Aparado; vazio ou acima do máximo: 422 (`backlog-review` 13, 21; SEC-09)."""

    def check(value: str) -> str:
        value = value.strip()
        if not value:
            raise _invalid(messages.FIELD_REQUIRED)
        if len(value) > max_length:
            raise _invalid(messages.TEXT_TOO_LONG.format(max=max_length))
        return value

    return AfterValidator(check)


def _priority(value: str) -> str:
    if value not in PRIORITIES:
        raise _invalid(messages.PRIORITY_INVALID)
    return value


def _story_points(value: int) -> int:
    if value not in STORY_POINTS:
        raise _invalid(messages.STORY_POINTS_INVALID)
    return value


def _timestamp(value: str) -> str:
    if _TIMESTAMP.fullmatch(value) is None:
        raise _invalid(messages.REQUESTED_AT_INVALID)
    return value


def timestamp_seconds(value: str) -> int:
    """`hh:mm:ss` já validado → segundos."""
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


StoryName = Annotated[StrictStr, _text(STORY_NAME_MAX)]
StoryText = Annotated[StrictStr, _text(STORY_TEXT_MAX)]
CriterionText = Annotated[StrictStr, _text(CRITERION_TEXT_MAX)]
Priority = Annotated[StrictStr, AfterValidator(_priority)]
StoryPoints = Annotated[StrictInt, AfterValidator(_story_points)]
Timestamp = Annotated[StrictStr, AfterValidator(_timestamp)]


class _Patch(BaseModel):
    """Só os campos enviados mudam; `null` só onde o campo aceita vazio."""

    model_config = ConfigDict(extra="forbid")

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)

    @staticmethod
    def _not_null(value: object) -> object:
        if value is None:
            raise _invalid(messages.FIELD_REQUIRED)
        return value


class CriterionIn(BaseModel):
    """`backlog-review` 20."""

    model_config = ConfigDict(extra="forbid")

    given: CriterionText
    when: CriterionText
    then: CriterionText


class CriterionPatch(_Patch):
    """`backlog-review` 21."""

    given: CriterionText | None = None
    when: CriterionText | None = None
    then: CriterionText | None = None

    @field_validator("given", "when", "then")
    @classmethod
    def _required(cls, value: object) -> object:
        return cls._not_null(value)


class StoryCreate(BaseModel):
    """`backlog-review` 17, 18: solicitante e instante opcionais."""

    model_config = ConfigDict(extra="forbid")

    name: StoryName
    as_a: StoryText
    i_want: StoryText
    so_that: StoryText
    priority: Priority
    story_points: StoryPoints
    requested_by: StrictInt | None = None
    requested_at: Timestamp | None = None
    acceptance_criteria: Annotated[list[CriterionIn], Field(min_length=1)]

    @field_validator("acceptance_criteria", mode="before")
    @classmethod
    def _some_criteria(cls, value: object) -> object:
        if isinstance(value, list) and not value:
            raise _invalid(messages.CRITERIA_REQUIRED)
        return value


class StoryPatch(_Patch):
    """`backlog-review` 11 a 16. `requested_by` e `requested_at` aceitam `null` (vazio)."""

    name: StoryName | None = None
    as_a: StoryText | None = None
    i_want: StoryText | None = None
    so_that: StoryText | None = None
    priority: Priority | None = None
    story_points: StoryPoints | None = None
    requested_by: StrictInt | None = None
    requested_at: Timestamp | None = None
    epic_id: StrictInt | None = None

    @field_validator("name", "as_a", "i_want", "so_that", "priority", "story_points", "epic_id")
    @classmethod
    def _required(cls, value: object) -> object:
        return cls._not_null(value)


class ParticipantRename(BaseModel):
    """Corpo de renomear Participante; mesma validação de `participants` 8 (SEC-09)."""

    model_config = ConfigDict(extra="forbid")

    name: ParticipantName


class ParticipantRenamed(BaseModel):
    """Participante que ficou; `absorbed_id` só quando houve união (`backlog-review` 24)."""

    participant: ParticipantOut
    absorbed_id: int | None
