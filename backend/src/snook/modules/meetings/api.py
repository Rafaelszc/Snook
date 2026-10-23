from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from snook.core import files
from snook.core.clock import Clock
from snook.core.deps import get_clock, get_settings, get_uow
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.meetings import service, storage
from snook.modules.meetings.schemas import MeetingOut

router = APIRouter(prefix="/api/meetings")


def get_media_probe(request: Request) -> service.MediaProbe:
    """Teste troca por fake em `app.state.media_probe`."""
    probe: service.MediaProbe = request.app.state.media_probe
    return probe


Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentSettings = Annotated[Settings, Depends(get_settings)]
CurrentClock = Annotated[Clock, Depends(get_clock)]
Probe = Annotated[service.MediaProbe, Depends(get_media_probe)]


def _create(
    uow: UnitOfWork,
    settings: Settings,
    user_id: str,
    upload: service.Upload,
    received: storage.ReceivedUpload,
    probe: service.MediaProbe,
    clock: Clock,
) -> MeetingOut:
    with uow:
        return service.create_meeting(
            uow,
            user_id=user_id,
            upload=upload,
            title=received.fields.get("title"),
            expected_speakers=received.fields.get("expected_speakers"),
            probe=probe,
            limits=service.UploadLimits(
                audio_root=settings.audio_root, max_audio_seconds=settings.max_audio_seconds
            ),
            now=clock.now(),
        )


@router.post("", status_code=201)
async def upload_meeting(
    request: Request,
    user: CurrentUser,
    uow: Uow,
    settings: CurrentSettings,
    probe: Probe,
    clock: CurrentClock,
) -> MeetingOut:
    """Multipart `file`, `title?`, `expected_speakers?` (`meetings` 1 a 15; ADR-0018)."""
    tmp_path = files.new_tmp_path(settings.audio_root)
    try:
        received = await storage.receive_upload(
            request, tmp_path=tmp_path, max_bytes=settings.upload_max_bytes
        )
        upload = service.Upload(
            tmp_path=tmp_path,
            original_filename=received.original_filename,
            size_bytes=received.size_bytes,
        )
        # ffprobe e SQLite são bloqueantes: fora do loop de eventos.
        return await run_in_threadpool(
            _create, uow, settings, user.id, upload, received, probe, clock
        )
    finally:
        # Toda recusa apaga o temporário; no sucesso ele já foi movido (SEC-16).
        files.discard_tmp(settings.audio_root, tmp_path)
