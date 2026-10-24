from typing import Annotated

from fastapi import APIRouter, Depends

from snook.core.deps import get_uow
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.diarized_transcription import service
from snook.modules.diarized_transcription.schemas import TranscriptOut

router = APIRouter(prefix="/api/meetings")

Uow = Annotated[UnitOfWork, Depends(get_uow)]


@router.get("/{meeting_id}/transcript")
def get_transcript(meeting_id: str, user: CurrentUser, uow: Uow) -> TranscriptOut:
    """Segmentos em ordem (`diarized-transcription` 18 a 20)."""
    with uow:
        return service.get_transcript(uow, user_id=user.id, meeting_id=meeting_id)
