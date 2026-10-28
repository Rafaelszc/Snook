from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from snook.core.errors import FIELD_MESSAGE_ERROR
from snook.modules.backlog_review import messages

EPIC_NAME_MAX = 200


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
