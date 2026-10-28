from typing import Annotated

from fastapi import APIRouter, Depends

from snook.core.deps import get_uow
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.backlog_review import service
from snook.modules.backlog_review.schemas import BacklogOut

router = APIRouter(prefix="/api/meetings")

Uow = Annotated[UnitOfWork, Depends(get_uow)]


@router.get("/{meeting_id}/backlog")
def read_backlog(meeting_id: str, user: CurrentUser, uow: Uow) -> BacklogOut:
    """`backlog-review` 1 a 4, 47."""
    with uow:
        return service.read_backlog(uow, user_id=user.id, meeting_id=meeting_id)
