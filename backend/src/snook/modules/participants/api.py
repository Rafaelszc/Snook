from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from snook.core.deps import get_settings, get_uow
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.participants import service
from snook.modules.participants.schemas import SpeakerOut

router = APIRouter(prefix="/api/meetings")

Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentSettings = Annotated[Settings, Depends(get_settings)]
# Rótulo do Pyannote (`SPEAKER_00`); fora do formato: 422 antes da lógica (SEC-09).
SpeakerLabel = Annotated[str, Path(pattern=r"^[A-Za-z0-9_]{1,32}$")]


@router.get("/{meeting_id}/speakers")
def list_speakers(meeting_id: str, user: CurrentUser, uow: Uow) -> list[SpeakerOut]:
    """`participants` 1."""
    with uow:
        return service.list_speakers(uow, user_id=user.id, meeting_id=meeting_id)


@router.get("/{meeting_id}/speakers/{speaker_label}/sample")
def speaker_sample(
    meeting_id: str,
    speaker_label: SpeakerLabel,
    user: CurrentUser,
    uow: Uow,
    settings: CurrentSettings,
) -> Response:
    """`participants` 2 a 5. Gerada a cada pedido; navegador não guarda."""
    with uow:
        wav = service.speaker_sample(
            uow,
            settings.audio_root,
            user_id=user.id,
            meeting_id=meeting_id,
            speaker_label=speaker_label,
        )
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})
