from itertools import groupby

from snook.core.errors import AppError
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import service as backlog_generation
from snook.modules.backlog_generation.models import AcceptanceCriterion, Epic, UserStory
from snook.modules.backlog_review import messages
from snook.modules.backlog_review.schemas import (
    BacklogOut,
    CriterionIn,
    CriterionOut,
    CriterionPatch,
    EpicOut,
    EpicRenamed,
    EpicSummary,
    RequesterOut,
    StoryCreate,
    StoryPatch,
    UserStoryOut,
    timestamp_seconds,
)
from snook.modules.meetings import service as meetings
from snook.modules.meetings.schemas import MeetingDetail
from snook.modules.participants import service as participants
from snook.modules.transcript_split import service as transcript_split


def _with_backlog(uow: UnitOfWork, user_id: str, meeting_id: str) -> MeetingDetail:
    """Reunião do Usuário com backlog gravado; sem ele, 409 (`backlog-review` 4, 31)."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if not meeting.has_backlog:
        raise AppError("no_backlog", messages.NO_BACKLOG, 409)
    return meeting


def require_editable(uow: UnitOfWork, user_id: str, meeting_id: str) -> MeetingDetail:
    """Política das rotas de escrita: só em `done`; fora dele, 409 sem mudar nada
    (`backlog-review`, "Regras por status"; 30)."""
    meeting = _with_backlog(uow, user_id, meeting_id)
    if meeting.status != "done":
        raise AppError("invalid_status", messages.NOT_EDITABLE, 409)
    return meeting


def read_backlog(uow: UnitOfWork, *, user_id: str, meeting_id: str) -> BacklogOut:
    """`backlog-review` 1 a 4, 47. Fora de `done`, backlog anterior só para leitura."""
    meeting = _with_backlog(uow, user_id, meeting_id)
    repo = backlog_generation.backlog(uow)
    names = _participant_names(uow, meeting_id)
    stories = sorted(repo.stories(meeting_id), key=lambda s: (s.epic_id, s.position))
    by_epic = {epic_id: list(group) for epic_id, group in groupby(stories, lambda s: s.epic_id)}
    epics = [
        EpicOut(
            id=epic.id,
            name=epic.name,
            user_stories=[_story_out(repo, story, names) for story in by_epic.get(epic.id, [])],
        )
        for epic in repo.epics(meeting_id)
    ]
    failed = meeting.status == "failed" and meeting.failed_stage == "generation"
    return BacklogOut(
        read_only=meeting.status != "done", last_generation_failed=failed, epics=epics
    )


def _criterion_out(criterion: AcceptanceCriterion) -> CriterionOut:
    return CriterionOut(
        id=criterion.id, given=criterion.given, when=criterion.when_, then=criterion.then_
    )


def _story_out(
    repo: backlog_generation.BacklogRepository, story: UserStory, names: dict[int, str]
) -> UserStoryOut:
    """US no formato do `GET /backlog`; `names`: `id` → nome dos Participantes da Reunião."""
    return UserStoryOut(
        id=story.id,
        us_id=backlog_generation.us_id(story.us_number),
        name=story.name,
        as_a=story.as_a,
        i_want=story.i_want,
        so_that=story.so_that,
        priority=story.priority,
        story_points=story.story_points,
        requested_by=(
            RequesterOut(id=story.requested_by, name=names[story.requested_by])
            if story.requested_by in names
            else None
        ),
        requested_at=(
            transcript_split.format_timestamp(story.requested_at_seconds)
            if story.requested_at_seconds is not None
            else None
        ),
        acceptance_criteria=[_criterion_out(c) for c in repo.criteria(story.id)],
    )


def _participant_names(uow: UnitOfWork, meeting_id: str) -> dict[int, str]:
    return {p.id: p.name for p in participants.list_participants(uow, meeting_id)}


def _owned_epic(uow: UnitOfWork, meeting_id: str, epic_id: int) -> Epic:
    """Epic da Reunião; de outra, 404 (`backlog-review` 37; SEC-02)."""
    epic = backlog_generation.backlog(uow).epic(meeting_id, epic_id)
    if epic is None:
        raise AppError("epic_not_found", messages.EPIC_NOT_FOUND, 404)
    return epic


def create_epic(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, name: str
) -> tuple[EpicSummary, bool]:
    """`backlog-review` 7, 8 (Q57). Devolve a Epic e se foi criada."""
    require_editable(uow, user_id, meeting_id)
    repo = backlog_generation.backlog(uow)
    existing = repo.epic_named(meeting_id, name)
    if existing is not None:
        return EpicSummary(id=existing.id, name=existing.name), False
    epic = repo.add_epic(meeting_id, name)
    return EpicSummary(id=epic.id, name=epic.name), True


def rename_epic(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, epic_id: int, name: str
) -> EpicRenamed:
    """`backlog-review` 5, 6: nome de outra Epic da Reunião junta as duas."""
    require_editable(uow, user_id, meeting_id)
    epic = _owned_epic(uow, meeting_id, epic_id)
    repo = backlog_generation.backlog(uow)
    target = repo.epic_named(meeting_id, name)
    if target is not None and target.id != epic.id:
        repo.merge_epic(epic, target)
        return EpicRenamed(id=target.id, name=target.name, merged_into=target.id)
    repo.rename_epic(epic, name)
    return EpicRenamed(id=epic.id, name=epic.name, merged_into=None)


def delete_epic(uow: UnitOfWork, *, user_id: str, meeting_id: str, epic_id: int) -> None:
    """`backlog-review` 10 (Q49): só Epic sem US."""
    require_editable(uow, user_id, meeting_id)
    epic = _owned_epic(uow, meeting_id, epic_id)
    repo = backlog_generation.backlog(uow)
    if repo.has_stories(epic):
        raise AppError("epic_not_empty", messages.EPIC_NOT_EMPTY, 409)
    repo.delete_epic(epic)


def _owned_story(uow: UnitOfWork, meeting_id: str, story_id: int) -> UserStory:
    """US da Reunião; de outra, 404 (`backlog-review` 37; SEC-02)."""
    story = backlog_generation.backlog(uow).story(meeting_id, story_id)
    if story is None:
        raise AppError("story_not_found", messages.STORY_NOT_FOUND, 404)
    return story


def _owned_criterion(uow: UnitOfWork, meeting_id: str, criterion_id: int) -> AcceptanceCriterion:
    criterion = backlog_generation.backlog(uow).criterion(meeting_id, criterion_id)
    if criterion is None:
        raise AppError("criterion_not_found", messages.CRITERION_NOT_FOUND, 404)
    return criterion


def _field_error(field: str, message: str) -> AppError:
    return AppError("validation_error", message, 422, fields={field: message})


def _origin(
    names: dict[int, str], meeting: MeetingDetail, changes: dict[str, object]
) -> dict[str, object]:
    """`requested_by` e `requested_at` enviados → colunas. Solicitante só da Reunião, instante
    até a duração (`backlog-review` 14, 15)."""
    columns: dict[str, object] = {}
    if "requested_by" in changes:
        requester = changes["requested_by"]
        if requester is not None and requester not in names:
            raise _field_error("requested_by", messages.REQUESTER_INVALID)
        columns["requested_by"] = requester
    if "requested_at" in changes:
        value = changes["requested_at"]
        seconds = timestamp_seconds(value) if isinstance(value, str) else None
        if seconds is not None and seconds > meeting.duration_seconds:
            raise _field_error("requested_at", messages.REQUESTED_AT_AFTER_END)
        columns["requested_at_seconds"] = seconds
    return columns


_STORY_TEXT = ("name", "as_a", "i_want", "so_that", "priority", "story_points")


def create_story(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, epic_id: int, body: StoryCreate
) -> UserStoryOut:
    """`backlog-review` 17, 18: próximo `US-id`, no fim da Epic."""
    meeting = require_editable(uow, user_id, meeting_id)
    epic = _owned_epic(uow, meeting_id, epic_id)
    names = _participant_names(uow, meeting_id)
    sent = body.model_dump(include={"requested_by", "requested_at"})
    fields = {name: getattr(body, name) for name in _STORY_TEXT}
    fields.update(_origin(names, meeting, sent))
    criteria = [(c.given, c.when, c.then) for c in body.acceptance_criteria]
    repo = backlog_generation.backlog(uow)
    return _story_out(repo, repo.add_story(epic, fields, criteria), names)


def update_story(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, story_id: int, body: StoryPatch
) -> UserStoryOut:
    """`backlog-review` 11 a 16. Valida tudo antes de gravar: erro não muda nada."""
    meeting = require_editable(uow, user_id, meeting_id)
    story = _owned_story(uow, meeting_id, story_id)
    changes = body.changes()
    target = _owned_epic(uow, meeting_id, changes["epic_id"]) if "epic_id" in changes else None
    names = _participant_names(uow, meeting_id)
    columns = {name: changes[name] for name in _STORY_TEXT if name in changes}
    columns.update(_origin(names, meeting, changes))
    repo = backlog_generation.backlog(uow)
    repo.update_story(story, columns)
    if target is not None:
        repo.move_story(story, target)
    return _story_out(repo, story, names)


def delete_story(uow: UnitOfWork, *, user_id: str, meeting_id: str, story_id: int) -> None:
    """`backlog-review` 19: critérios juntos; `US-id` não é reusado."""
    require_editable(uow, user_id, meeting_id)
    story = _owned_story(uow, meeting_id, story_id)
    backlog_generation.backlog(uow).delete_story(story)


def add_criterion(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, story_id: int, body: CriterionIn
) -> CriterionOut:
    """`backlog-review` 20: no fim da US."""
    require_editable(uow, user_id, meeting_id)
    story = _owned_story(uow, meeting_id, story_id)
    repo = backlog_generation.backlog(uow)
    return _criterion_out(repo.add_criterion(story, body.given, body.when, body.then))


def update_criterion(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, criterion_id: int, body: CriterionPatch
) -> CriterionOut:
    """`backlog-review` 21."""
    require_editable(uow, user_id, meeting_id)
    criterion = _owned_criterion(uow, meeting_id, criterion_id)
    backlog_generation.backlog(uow).update_criterion(criterion, body.changes())
    return _criterion_out(criterion)


def delete_criterion(uow: UnitOfWork, *, user_id: str, meeting_id: str, criterion_id: int) -> None:
    """`backlog-review` 22: o último critério da US fica."""
    require_editable(uow, user_id, meeting_id)
    criterion = _owned_criterion(uow, meeting_id, criterion_id)
    repo = backlog_generation.backlog(uow)
    if repo.criteria_count(criterion.user_story_id) <= 1:
        raise AppError("last_criterion", messages.LAST_CRITERION, 409)
    repo.delete_criterion(criterion)
