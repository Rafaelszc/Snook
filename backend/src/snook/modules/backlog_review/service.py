from itertools import groupby

from snook.core.errors import AppError
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import service as backlog_generation
from snook.modules.backlog_review import messages
from snook.modules.backlog_review.schemas import (
    BacklogOut,
    CriterionOut,
    EpicOut,
    RequesterOut,
    UserStoryOut,
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
    names = {p.id: p.name for p in participants.list_participants(uow, meeting_id)}
    stories = sorted(repo.stories(meeting_id), key=lambda s: (s.epic_id, s.position))
    by_epic = {epic_id: list(group) for epic_id, group in groupby(stories, lambda s: s.epic_id)}
    epics = [
        EpicOut(
            id=epic.id,
            name=epic.name,
            user_stories=[
                UserStoryOut(
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
                    acceptance_criteria=[
                        CriterionOut(id=c.id, given=c.given, when=c.when_, then=c.then_)
                        for c in repo.criteria(story.id)
                    ],
                )
                for story in by_epic.get(epic.id, [])
            ],
        )
        for epic in repo.epics(meeting_id)
    ]
    failed = meeting.status == "failed" and meeting.failed_stage == "generation"
    return BacklogOut(
        read_only=meeting.status != "done", last_generation_failed=failed, epics=epics
    )
