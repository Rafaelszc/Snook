import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from snook.core import files
from snook.core.clock import to_iso
from snook.core.errors import AppError
from snook.core.events import MeetingCreated
from snook.core.uow import UnitOfWork
from snook.modules.meetings import messages, repository
from snook.modules.meetings.media_probe import FfprobeProbe as FfprobeProbe
from snook.modules.meetings.media_probe import MediaProbe as MediaProbe
from snook.modules.meetings.models import FILE_EXTENSIONS, STATUS_PENDING, Meeting
from snook.modules.meetings.schemas import MeetingOut

logger = logging.getLogger("snook.meetings")

TITLE_MAX = 200
ORIGINAL_FILENAME_MAX = 255
EXPECTED_SPEAKERS_MIN = 1
EXPECTED_SPEAKERS_MAX = 20
_DIGITS = re.compile(r"^[0-9]{1,3}$")


@dataclass(frozen=True)
class Upload:
    """Arquivo recebido em `/audios/.tmp/<uuid>`; o nome original é só metadado (SEC-16)."""

    tmp_path: Path
    original_filename: str
    size_bytes: int


@dataclass(frozen=True)
class UploadLimits:
    audio_root: Path
    max_audio_seconds: int


def _base_name(filename: str) -> str:
    """Tira qualquer caminho do nome enviado."""
    return re.split(r"[\\/]", filename)[-1].strip()


def _extension(filename: str) -> str:
    return PurePosixPath(filename).suffix.lower().removeprefix(".")


def _title(title: str | None, original_filename: str) -> str:
    cleaned = (title or "").strip()
    if not cleaned:
        return original_filename[:TITLE_MAX]
    if len(cleaned) > TITLE_MAX:
        raise AppError(
            "validation_error",
            messages.INVALID_DATA,
            422,
            fields={"title": messages.TITLE_TOO_LONG},
        )
    return cleaned


def _expected_speakers(raw: str | None) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    if _DIGITS.match(value) and EXPECTED_SPEAKERS_MIN <= int(value) <= EXPECTED_SPEAKERS_MAX:
        return int(value)
    raise AppError(
        "invalid_expected_speakers",
        messages.INVALID_EXPECTED_SPEAKERS,
        422,
        fields={"expected_speakers": messages.INVALID_EXPECTED_SPEAKERS},
    )


def _audio_duration(probe: MediaProbe, upload: Upload, max_audio_seconds: int) -> float:
    result = probe.probe(upload.tmp_path)
    if not result.has_audio or result.duration_seconds is None:
        raise AppError("no_audio", messages.NO_AUDIO, 422)
    if result.duration_seconds > max_audio_seconds:
        raise AppError("too_long", messages.TOO_LONG, 422)
    return result.duration_seconds


def create_meeting(
    uow: UnitOfWork,
    *,
    user_id: str,
    upload: Upload,
    title: str | None,
    expected_speakers: str | None,
    probe: MediaProbe,
    limits: UploadLimits,
    now: datetime,
) -> MeetingOut:
    """Valida o upload e grava a Reunião `pending`. Depois do commit, move o arquivo para
    `/audios/<id>/original.<ext>` e só então publica `MeetingCreated` (ADR-0018)."""
    base_name = _base_name(upload.original_filename)
    ext = _extension(base_name)
    original_filename = base_name[:ORIGINAL_FILENAME_MAX]
    if ext not in FILE_EXTENSIONS:
        raise AppError("unsupported_format", messages.UNSUPPORTED_FORMAT, 422)
    meeting_title = _title(title, original_filename)
    speakers = _expected_speakers(expected_speakers)
    if upload.size_bytes == 0:
        raise AppError("empty_file", messages.EMPTY_FILE, 422)
    duration = _audio_duration(probe, upload, limits.max_audio_seconds)

    stamp = to_iso(now)
    meeting = Meeting(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=meeting_title,
        original_filename=original_filename,
        file_ext=ext,
        duration_seconds=duration,
        size_bytes=upload.size_bytes,
        expected_speakers=speakers,
        status=STATUS_PENDING,
        run_id=str(uuid.uuid4()),
        created_at=stamp,
        updated_at=stamp,
    )
    repository.add_meeting(uow.session, meeting)

    def move_file() -> None:
        files.move_into_meeting_dir(
            limits.audio_root, upload.tmp_path, meeting.id, f"original.{ext}"
        )
        logger.info("meeting.created", extra={"user_id": user_id, "meeting_id": meeting.id})

    uow.after_commit(move_file)
    uow.publish_after_commit(MeetingCreated(meeting_id=meeting.id, run_id=meeting.run_id))
    return _out(meeting)


def _out(meeting: Meeting) -> MeetingOut:
    return MeetingOut(
        id=meeting.id,
        title=meeting.title,
        original_filename=meeting.original_filename,
        duration_seconds=meeting.duration_seconds,
        expected_speakers=meeting.expected_speakers,
        status=meeting.status,
        created_at=meeting.created_at,
    )
