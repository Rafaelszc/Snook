from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from snook.core.deps import get_uow
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.backlog_review import service
from snook.modules.backlog_review.schemas import BacklogOut, EpicName, EpicRenamed, EpicSummary

router = APIRouter(prefix="/api/meetings")

Uow = Annotated[UnitOfWork, Depends(get_uow)]


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
