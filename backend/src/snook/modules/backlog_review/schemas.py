from pydantic import BaseModel


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
