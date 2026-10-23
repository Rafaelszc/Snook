import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import cast

from snook.core import files
from snook.core.clock import to_iso
from snook.core.errors import AppError
from snook.core.events import MeetingCreated, RetryRequested, Stage
from snook.core.uow import UnitOfWork
from snook.modules.meetings import messages, repository, startup, state_machine
from snook.modules.meetings.media_probe import FfprobeProbe as FfprobeProbe
from snook.modules.meetings.media_probe import MediaProbe as MediaProbe
from snook.modules.meetings.models import FILE_EXTENSIONS, STATUS_FAILED, STATUS_PENDING, Meeting
from snook.modules.meetings.schemas import TITLE_MAX, MeetingDetail, MeetingOut, MeetingSummary
from snook.modules.meetings.state_machine import InvalidStatusUpdate as InvalidStatusUpdate

logger = logging.getLogger("snook.meetings")

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


def _owned(uow: UnitOfWork, user_id: str, meeting_id: str) -> Meeting:
    """404 igual para inexistente e de outro Usuário; o segundo vai ao log (SEC-02, SEC-20)."""
    meeting = (
        repository.get_meeting(uow.session, meeting_id) if files.is_meeting_id(meeting_id) else None
    )
    if meeting is not None and meeting.user_id != user_id:
        logger.warning(
            "security.access_denied",
            extra={"user_id": user_id, "resource": "meeting", "resource_id": meeting_id},
        )
        meeting = None
    if meeting is None:
        raise AppError("meeting_not_found", messages.MEETING_NOT_FOUND, 404)
    return meeting


def get_owned_meeting(uow: UnitOfWork, user_id: str, meeting_id: str) -> MeetingDetail:
    """Interface pública: toda rota aninhada em `/meetings/{id}` chama antes (SEC-02)."""
    return _detail(_owned(uow, user_id, meeting_id))


def list_meetings(uow: UnitOfWork, *, user_id: str) -> list[MeetingSummary]:
    return [_summary(m) for m in repository.list_meetings(uow.session, user_id)]


def rename_meeting(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, title: str, now: datetime
) -> MeetingDetail:
    """Muda só o título, em qualquer status (`meetings` 16, 18)."""
    meeting = _owned(uow, user_id, meeting_id)
    meeting.title = title
    meeting.updated_at = to_iso(now)
    uow.session.flush()
    return _detail(meeting)


def delete_meeting(uow: UnitOfWork, *, user_id: str, meeting_id: str, audio_root: Path) -> None:
    """Apaga a Reunião e derivados num commit; depois dele, o diretório em `/audios` (SEC-24).
    Gravação tardia do pipeline acha a Reunião ausente e descarta o resultado."""
    meeting = _owned(uow, user_id, meeting_id)
    repository.delete_meeting(uow.session, meeting)

    def remove_files() -> None:
        logger.info("meeting.deleted", extra={"user_id": user_id, "meeting_id": meeting_id})
        files.remove_meeting_dir(audio_root, meeting_id)  # checagens de SEC-15

    uow.after_commit(remove_files)


def retry_meeting(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, now: datetime
) -> MeetingDetail:
    """ "Tentar novamente": retoma da etapa que falhou, com `run_id` novo (`meetings` 24 a 27).
    `RetryRequested` sai uma vez, depois do commit."""
    meeting = _owned(uow, user_id, meeting_id)
    if meeting.status != STATUS_FAILED:
        raise AppError("not_failed", messages.NOT_FAILED, 409)
    stage = cast(Stage, meeting.failed_stage)
    run_id = update_status(uow, meeting_id, state_machine.RETRY_TARGET[stage], now=now)

    def log_retry() -> None:
        logger.info(
            "meeting.retry", extra={"user_id": user_id, "meeting_id": meeting_id, "stage": stage}
        )

    uow.after_commit(log_retry)
    uow.publish_after_commit(RetryRequested(meeting_id=meeting_id, run_id=run_id, stage=stage))
    return _detail(meeting)


class MeetingGone(LookupError):
    """Reunião excluída antes da gravação: quem chama descarta o resultado."""


def _existing(uow: UnitOfWork, meeting_id: str) -> Meeting:
    meeting = repository.get_meeting(uow.session, meeting_id)
    if meeting is None:
        raise MeetingGone(meeting_id)
    return meeting


def update_status(
    uow: UnitOfWork,
    meeting_id: str,
    new_status: str,
    *,
    failed_stage: str | None = None,
    message: str | None = None,
    now: datetime,
) -> str:
    """Interface "Atualizar status" (`meetings` 22, 23). Devolve o `run_id` atual, novo quando a
    transição inicia trabalho (ADR-0007). Recusa com `InvalidStatusUpdate` sem mudar nada."""
    meeting = _existing(uow, meeting_id)
    state_machine.check(meeting, new_status, failed_stage, message)
    if state_machine.starts_new_run(meeting.status, new_status):
        meeting.run_id = str(uuid.uuid4())
    meeting.status = new_status
    meeting.failed_stage = failed_stage
    meeting.error_message = message.strip() if message is not None else None
    meeting.updated_at = to_iso(now)
    uow.session.flush()
    logger.info(
        "meeting.status_changed",
        extra={"meeting_id": meeting_id, "status": new_status, "failed_stage": failed_stage},
    )
    return meeting.run_id


def is_current_run(
    uow: UnitOfWork, meeting_id: str, run_id: str, *, status: str | None = None
) -> bool:
    """Consumidor de aviso só age se a Reunião existe e `run_id` (e status, se dado) batem."""
    meeting = repository.get_meeting(uow.session, meeting_id)
    if meeting is None or meeting.run_id != run_id:
        return False
    return status is None or meeting.status == status


def mark_interrupted(uow: UnitOfWork, *, now: datetime) -> None:
    """ "Marcar interrompidas" (`meetings` 44, 45, 49): na subida, antes de aceitar requisições."""
    for meeting in startup.mark_interrupted(uow.session, now):
        logger.info(
            "meeting.interrupted",
            extra={"meeting_id": meeting.id, "failed_stage": meeting.failed_stage},
        )


def requeue_pending(uow: UnitOfWork) -> None:
    """Reenfileira `pending` em ordem de criação, como `MeetingCreated` interno (ADR-0007)."""
    for meeting in startup.pending_in_creation_order(uow.session):
        uow.publish_after_commit(MeetingCreated(meeting_id=meeting.id, run_id=meeting.run_id))


@dataclass(frozen=True)
class MeetingFlags:
    """Interface "Ler marcas" (`meetings` 51)."""

    participants_confirmed: bool
    has_backlog: bool


def mark_participants_confirmed(uow: UnitOfWork, meeting_id: str, *, now: datetime) -> None:
    """`participants` chama na transação da confirmação. Marca nunca é apagada (ADR-0006)."""
    meeting = _existing(uow, meeting_id)
    if meeting.participants_confirmed_at is None:
        meeting.participants_confirmed_at = to_iso(now)
        uow.session.flush()


def mark_backlog_saved(uow: UnitOfWork, meeting_id: str, *, now: datetime) -> None:
    """`backlog-generation` chama na transação que grava o backlog. Marca nunca é apagada."""
    meeting = _existing(uow, meeting_id)
    if meeting.backlog_saved_at is None:
        meeting.backlog_saved_at = to_iso(now)
        uow.session.flush()


def read_flags(uow: UnitOfWork, meeting_id: str) -> MeetingFlags:
    return _flags(_existing(uow, meeting_id))


def _flags(meeting: Meeting) -> MeetingFlags:
    return MeetingFlags(
        participants_confirmed=meeting.participants_confirmed_at is not None,
        has_backlog=meeting.backlog_saved_at is not None,
    )


def _summary(meeting: Meeting) -> MeetingSummary:
    return MeetingSummary(
        id=meeting.id,
        title=meeting.title,
        created_at=meeting.created_at,
        duration_seconds=meeting.duration_seconds,
        status=meeting.status,
        participants_confirmed=_flags(meeting).participants_confirmed,
    )


def _detail(meeting: Meeting) -> MeetingDetail:
    failed = meeting.status == STATUS_FAILED
    flags = _flags(meeting)
    return MeetingDetail(
        **_summary(meeting).model_dump(),
        original_filename=meeting.original_filename,
        expected_speakers=meeting.expected_speakers,
        has_backlog=flags.has_backlog,
        failed_stage=meeting.failed_stage if failed else None,
        error_message=meeting.error_message if failed else None,
        split_reason=meeting.split_reason,
    )
