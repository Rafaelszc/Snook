from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from snook.core.clock import Clock
from snook.core.deps import get_clock, get_uow
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.backlog_review import service
from snook.modules.backlog_review.schemas import (
    BacklogOut,
    CriterionIn,
    CriterionOut,
    CriterionPatch,
    EpicName,
    EpicRenamed,
    EpicSummary,
    ParticipantRename,
    ParticipantRenamed,
    RegenerateIn,
    RegenerateOut,
    StoryCreate,
    StoryPatch,
    UserStoryOut,
)
from snook.modules.transcript_split import service as transcript_split

router = APIRouter(prefix="/api/meetings")


def get_estimate(request: Request) -> transcript_split.Estimate:
    """ "Estimar tokens" de `llm-providers`; teste troca por fake em `app.state`."""
    estimate: transcript_split.Estimate = request.app.state.estimate_tokens
    return estimate


Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentClock = Annotated[Clock, Depends(get_clock)]
CurrentEstimate = Annotated[transcript_split.Estimate, Depends(get_estimate)]


@router.get("/{meeting_id}/backlog")
def read_backlog(meeting_id: str, user: CurrentUser, uow: Uow) -> BacklogOut:
    """`backlog-review` 1 a 4, 47."""
    with uow:
        return service.read_backlog(uow, user_id=user.id, meeting_id=meeting_id)


@router.post("/{meeting_id}/epics", status_code=status.HTTP_201_CREATED)
def create_epic(
    meeting_id: str, body: EpicName, user: CurrentUser, uow: Uow, response: Response
) -> EpicSummary:
    """`backlog-review` 7 a 9: 201 nova, 200 existente (Q57)."""
    with uow:
        epic, created = service.create_epic(
            uow, user_id=user.id, meeting_id=meeting_id, name=body.name
        )
    if not created:
        response.status_code = status.HTTP_200_OK
    return epic


@router.patch("/{meeting_id}/epics/{epic_id}")
def rename_epic(
    meeting_id: str, epic_id: int, body: EpicName, user: CurrentUser, uow: Uow
) -> EpicRenamed:
    """`backlog-review` 5, 6, 9."""
    with uow:
        return service.rename_epic(
            uow, user_id=user.id, meeting_id=meeting_id, epic_id=epic_id, name=body.name
        )


@router.delete("/{meeting_id}/epics/{epic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_epic(meeting_id: str, epic_id: int, user: CurrentUser, uow: Uow) -> None:
    """`backlog-review` 10."""
    with uow:
        service.delete_epic(uow, user_id=user.id, meeting_id=meeting_id, epic_id=epic_id)


@router.post("/{meeting_id}/epics/{epic_id}/user-stories", status_code=status.HTTP_201_CREATED)
def create_story(
    meeting_id: str, epic_id: int, body: StoryCreate, user: CurrentUser, uow: Uow
) -> UserStoryOut:
    """`backlog-review` 17, 18."""
    with uow:
        return service.create_story(
            uow, user_id=user.id, meeting_id=meeting_id, epic_id=epic_id, body=body
        )


@router.patch("/{meeting_id}/user-stories/{story_id}")
def update_story(
    meeting_id: str, story_id: int, body: StoryPatch, user: CurrentUser, uow: Uow
) -> UserStoryOut:
    """`backlog-review` 11 a 16."""
    with uow:
        return service.update_story(
            uow, user_id=user.id, meeting_id=meeting_id, story_id=story_id, body=body
        )


@router.delete("/{meeting_id}/user-stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(meeting_id: str, story_id: int, user: CurrentUser, uow: Uow) -> None:
    """`backlog-review` 19."""
    with uow:
        service.delete_story(uow, user_id=user.id, meeting_id=meeting_id, story_id=story_id)


@router.post("/{meeting_id}/user-stories/{story_id}/criteria", status_code=status.HTTP_201_CREATED)
def add_criterion(
    meeting_id: str, story_id: int, body: CriterionIn, user: CurrentUser, uow: Uow
) -> CriterionOut:
    """`backlog-review` 20."""
    with uow:
        return service.add_criterion(
            uow, user_id=user.id, meeting_id=meeting_id, story_id=story_id, body=body
        )


@router.patch("/{meeting_id}/criteria/{criterion_id}")
def update_criterion(
    meeting_id: str, criterion_id: int, body: CriterionPatch, user: CurrentUser, uow: Uow
) -> CriterionOut:
    """`backlog-review` 21."""
    with uow:
        return service.update_criterion(
            uow, user_id=user.id, meeting_id=meeting_id, criterion_id=criterion_id, body=body
        )


@router.delete("/{meeting_id}/criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_criterion(meeting_id: str, criterion_id: int, user: CurrentUser, uow: Uow) -> None:
    """`backlog-review` 22."""
    with uow:
        service.delete_criterion(
            uow, user_id=user.id, meeting_id=meeting_id, criterion_id=criterion_id
        )


@router.patch("/{meeting_id}/participants/{participant_id}")
def rename_participant(
    meeting_id: str, participant_id: int, body: ParticipantRename, user: CurrentUser, uow: Uow
) -> ParticipantRenamed:
    """`backlog-review` 23 a 25: um commit com a troca de solicitante."""
    with uow:
        return service.rename_participant(
            uow,
            user_id=user.id,
            meeting_id=meeting_id,
            participant_id=participant_id,
            name=body.name,
        )


@router.post("/{meeting_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
def regenerate(
    meeting_id: str,
    body: RegenerateIn,
    user: CurrentUser,
    uow: Uow,
    clock: CurrentClock,
    estimate: CurrentEstimate,
) -> RegenerateOut:
    """`backlog-review` 26 a 29. "Partes prontas" sai depois do commit."""
    with uow:
        new_status = service.regenerate(
            uow,
            user_id=user.id,
            meeting_id=meeting_id,
            mode=body.mode,
            now=clock.now(),
            estimate=estimate,
        )
    return RegenerateOut(status=new_status)
