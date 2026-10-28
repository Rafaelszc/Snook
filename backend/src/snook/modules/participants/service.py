import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from snook.core.errors import AppError
from snook.core.events import ParticipantsConfirmed
from snook.core.text import normalize
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.llm_providers import service as llm_providers
from snook.modules.meetings import service as meetings
from snook.modules.participants import messages, repository
from snook.modules.participants.models import NAME_MAX, Participant
from snook.modules.participants.schemas import ParticipantOut, SpeakerOut

logger = logging.getLogger("snook.participants")

SAMPLE_MAX_SECONDS = 10.0


def _ensure_transcribed(uow: UnitOfWork, user_id: str, meeting_id: str) -> None:
    """Dono conferido (404). Antes de `transcribed`, ou `failed` na transcrição: 409."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.status in {"pending", "processing"} or (
        meeting.status == "failed" and meeting.failed_stage == "transcription"
    ):
        raise AppError("speakers_not_ready", messages.SPEAKERS_NOT_READY, 409)


def list_speakers(uow: UnitOfWork, *, user_id: str, meeting_id: str) -> list[SpeakerOut]:
    """Cada rótulo uma vez, com tempo total de fala (`participants` 1)."""
    _ensure_transcribed(uow, user_id, meeting_id)
    return [
        SpeakerOut(speaker_label=s.speaker_label, total_seconds=s.total_seconds)
        for s in transcription.list_speakers(uow, meeting_id)
    ]


def speaker_sample(
    uow: UnitOfWork, audio_root: Path, *, user_id: str, meeting_id: str, speaker_label: str
) -> bytes:
    """WAV de até 10 s do início do maior segmento; empate: o que começa antes (`participants`
    2 a 5). Sob demanda, sem cache. Rótulo ausente, ou áudio tratado indisponível: 404."""
    meetings.get_owned_meeting(uow, user_id, meeting_id)
    speaker = next(
        (
            s
            for s in transcription.list_speakers(uow, meeting_id)
            if s.speaker_label == speaker_label
        ),
        None,
    )
    if speaker is None:
        raise AppError("speaker_not_found", messages.SPEAKER_NOT_FOUND, 404)
    start = speaker.longest.start_seconds
    end = min(speaker.longest.end_seconds, start + SAMPLE_MAX_SECONDS)
    try:
        return transcription.treated_audio_clip(audio_root, meeting_id, start, end)
    except transcription.AudioClipError:
        raise AppError("sample_unavailable", messages.SAMPLE_UNAVAILABLE, 404) from None


def confirm(
    uow: UnitOfWork, *, user_id: str, meeting_id: str, names: dict[str, str], now: datetime
) -> list[ParticipantOut]:
    """Grava Participantes, vínculos e a marca de `meetings` num commit; aviso depois dele
    (`participants` 6 a 13). `names` já aparados, na ordem informada."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.participants_confirmed:
        raise AppError("already_confirmed", messages.ALREADY_CONFIRMED, 409)
    if meeting.status != "transcribed":
        raise AppError("invalid_status", messages.INVALID_STATUS, 409)
    _check_labels(uow, meeting_id, names)
    try:
        llm_providers.get_active_provider(uow, user_id=user_id)
    except llm_providers.NoActiveProvider:
        raise AppError("no_active_provider", messages.NO_ACTIVE_PROVIDER, 409) from None

    by_norm: dict[str, Participant] = {}
    for label, name in names.items():
        norm = normalize(name)
        participant = by_norm.get(norm)
        if participant is None:
            # Primeiro nome informado vence a grafia (`participants` 7).
            participant = repository.add_participant(uow.session, meeting_id, name, norm)
            by_norm[norm] = participant
        repository.link_speaker(uow.session, meeting_id, label, participant.id)
    run_id = meetings.mark_participants_confirmed(uow, meeting_id, now=now)
    uow.publish_after_commit(ParticipantsConfirmed(meeting_id=meeting_id, run_id=run_id))
    logger.info(
        "participants.confirmed",
        extra={"meeting_id": meeting_id, "participants_count": len(by_norm)},
    )
    return list_participants(uow, meeting_id)


def _check_labels(uow: UnitOfWork, meeting_id: str, names: dict[str, str]) -> None:
    """Todo speaker da Transcrição com nome, e nenhum rótulo de fora (`participants` 8, 9)."""
    labels = {s.speaker_label for s in transcription.list_speakers(uow, meeting_id)}
    fields = {f"names.{label}": messages.NAME_REQUIRED for label in sorted(labels - names.keys())}
    fields |= {
        f"names.{label}": messages.SPEAKER_NOT_FOUND for label in sorted(names.keys() - labels)
    }
    if fields:
        raise AppError("validation_error", messages.NAMES_INVALID, 422, fields=fields)


def list_owned_participants(
    uow: UnitOfWork, *, user_id: str, meeting_id: str
) -> list[ParticipantOut]:
    """`GET /participants` (`participants` 14). Antes da confirmação: lista vazia."""
    meetings.get_owned_meeting(uow, user_id, meeting_id)
    return list_participants(uow, meeting_id)


# --- Interface para outros módulos (`02-architecture.md`, "Interfaces internas") ---


def list_participants(uow: UnitOfWork, meeting_id: str) -> list[ParticipantOut]:
    """Interface "Participantes": `id`, `name` e os `speaker_label` de cada um."""
    labels: dict[int, list[str]] = {}
    for link in repository.list_links(uow.session, meeting_id):
        labels.setdefault(link.participant_id, []).append(link.speaker_label)
    return [
        ParticipantOut(id=p.id, name=p.name, speaker_labels=labels.get(p.id, []))
        for p in repository.list_participants(uow.session, meeting_id)
    ]


def participant_for_speaker(
    uow: UnitOfWork, meeting_id: str, speaker_label: str
) -> ParticipantOut | None:
    """Interface "Participante de um speaker" (`participants` 15). Sem vínculo: `None`."""
    participant = repository.participant_for_speaker(uow.session, meeting_id, speaker_label)
    if participant is None:
        return None
    return _out(uow, meeting_id, participant)


@dataclass(frozen=True)
class RenameResult:
    """Participante resultante; `absorbed_id` só quando houve união (`participants` 18)."""

    participant: ParticipantOut
    absorbed_id: int | None = None


def rename(
    uow: UnitOfWork,
    meeting_id: str,
    participant_id: int,
    new_name: str,
    before_absorb: Callable[[int, int], None] | None = None,
) -> RenameResult:
    """Interface "Renomear Participante" (Q55, `participants` 17 a 22). Entra na transação de
    quem chama; dono já conferido por ele. Nome igual ao de outro Participante une os dois:
    sobrevive o que já tinha o nome, e `before_absorb(absorbed_id, survivor_id)` roda antes de
    apagar o absorvido. Não chama `llm_providers`, não emite aviso, não muda status."""
    if not meetings.read_flags(uow, meeting_id).participants_confirmed:
        raise AppError("not_confirmed", messages.NOT_CONFIRMED, 409)
    if meetings.read_status(uow, meeting_id) == "generating":
        raise AppError("invalid_status", messages.RENAME_WHILE_GENERATING, 409)
    participant = repository.get_participant(uow.session, meeting_id, participant_id)
    if participant is None:
        raise AppError("participant_not_found", messages.PARTICIPANT_NOT_FOUND, 404)
    name = new_name.strip()
    if not name or len(name) > NAME_MAX:
        message = messages.NAME_TOO_LONG if name else messages.NAME_REQUIRED
        raise AppError("validation_error", message, 422, fields={"name": message})

    norm = normalize(name)
    survivor = repository.participant_by_name(uow.session, meeting_id, norm)
    if survivor is None or survivor.id == participant.id:
        participant.name = name
        participant.name_norm = norm
        uow.session.flush()
        logger.info(
            "participants.renamed",
            extra={"meeting_id": meeting_id, "participant_id": participant.id},
        )
        return RenameResult(participant=_out(uow, meeting_id, participant))

    repository.move_links(uow.session, meeting_id, participant.id, survivor.id)
    if before_absorb is not None:
        before_absorb(participant.id, survivor.id)
    absorbed_id = participant.id
    repository.delete_participant(uow.session, participant)
    logger.info(
        "participants.merged",
        extra={"meeting_id": meeting_id, "participant_id": survivor.id, "absorbed_id": absorbed_id},
    )
    return RenameResult(participant=_out(uow, meeting_id, survivor), absorbed_id=absorbed_id)


def _out(uow: UnitOfWork, meeting_id: str, participant: Participant) -> ParticipantOut:
    labels = [
        link.speaker_label
        for link in repository.list_links(uow.session, meeting_id)
        if link.participant_id == participant.id
    ]
    return ParticipantOut(id=participant.id, name=participant.name, speaker_labels=labels)
