import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from snook.core.events import Event, EventBus, ParticipantsConfirmed, PartsReady, RetryRequested
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.llm_providers import service as llm_providers
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.meetings import service as meetings
from snook.modules.participants import service as participants
from snook.modules.transcript_split import messages, repository
from snook.modules.transcript_split.budget import compute_budget as compute_budget
from snook.modules.transcript_split.budget import fits as fits
from snook.modules.transcript_split.budget import output_reserve as output_reserve
from snook.modules.transcript_split.models import TranscriptPart
from snook.modules.transcript_split.part_text import format_line as format_line
from snook.shared.prompts import load_backlog_system_prompt

logger = logging.getLogger("snook.transcript_split")

Mode = Literal["normal", "reajustar"]

# "Estimar tokens" de `llm-providers`: `(provider, model, text) -> tokens`. Testes passam fake.
Estimate = Callable[[str, str, str], int]

# --- Interface para outros módulos (`02-architecture.md`, "Interfaces internas") ---


def transcript_lines(uow: UnitOfWork, meeting_id: str) -> list[str]:
    """Uma linha por segmento, na ordem, com o nome atual do Participante (`transcript-split` 27).

    Speaker sem Participante (antes da confirmação) sai com o rótulo.
    """
    names = {
        label: participant.name
        for participant in participants.list_participants(uow, meeting_id)
        for label in participant.speaker_labels
    }
    return [
        format_line(
            segment.start_seconds,
            names.get(segment.speaker_label, segment.speaker_label),
            segment.text,
        )
        for segment in transcription.list_segments(uow, meeting_id)
    ]


def part_text(uow: UnitOfWork, meeting_id: str, first: int, last: int) -> str:
    """Interface "Texto da Parte": segmentos de `first` a `last` (posições, inclusivas).

    Mesmo texto na estimativa e no envio: tamanho medido = tamanho enviado.
    """
    return "\n".join(transcript_lines(uow, meeting_id)[first : last + 1])


def participants_text(uow: UnitOfWork, meeting_id: str) -> str:
    """Lista de Participantes enviada à LLM; a mesma entra na reserva do orçamento."""
    names = [p.name for p in participants.list_participants(uow, meeting_id)]
    return "\n".join(["Participantes:", *(f"- {name}" for name in names)])


def owner_provider(uow: UnitOfWork, meeting_id: str) -> ActiveProvider:
    """Provedor ativo do dono da Reunião (`transcript-split` 4). Sem ativo: `NoActiveProvider`."""
    return llm_providers.get_active_provider(uow, user_id=meetings.read_owner(uow, meeting_id))


def estimate_part(
    uow: UnitOfWork,
    snapshot: ActiveProvider,
    meeting_id: str,
    first: int,
    last: int,
    *,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> int:
    """Estimativa do "Texto da Parte" com o modelo do snapshot."""
    return estimate(snapshot.provider, snapshot.model, part_text(uow, meeting_id, first, last))


def part_budget(
    uow: UnitOfWork,
    snapshot: ActiveProvider,
    meeting_id: str,
    *,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> int:
    """Interface "Orçamento da Parte" (ADR-0011). Igual para toda Parte: a reserva de nomes de
    Epics é fixa."""
    return compute_budget(
        snapshot.context_window,
        system_prompt_tokens=estimate(
            snapshot.provider, snapshot.model, load_backlog_system_prompt()
        ),
        participants_tokens=estimate(
            snapshot.provider, snapshot.model, participants_text(uow, meeting_id)
        ),
    )


@dataclass(frozen=True)
class Part:
    """Parte gravada: segmentos de `first` a `last` (posições, inclusivas), `index` a partir de 1.
    `text` montado na leitura, com os nomes atuais."""

    index: int
    first: int
    last: int
    start_seconds: float
    end_seconds: float
    estimated_tokens: int
    text: str


def save_parts(
    uow: UnitOfWork,
    snapshot: ActiveProvider,
    meeting_id: str,
    ranges: list[tuple[int, int]],
    *,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> None:
    """Gravação das Partes: apaga as anteriores e grava `ranges` (posições, em ordem) na mesma
    transação (`transcript-split` 37). Instantes absolutos do primeiro e do último segmento (18)."""
    segments = transcription.list_segments(uow, meeting_id)
    ids = transcription.segment_ids(uow, meeting_id)
    lines = transcript_lines(uow, meeting_id)
    repository.replace_parts(
        uow.session,
        meeting_id,
        [
            TranscriptPart(
                meeting_id=meeting_id,
                index=index,
                first_segment_id=ids[first],
                last_segment_id=ids[last],
                start_seconds=segments[first].start_seconds,
                end_seconds=segments[last].end_seconds,
                estimated_tokens=estimate(
                    snapshot.provider, snapshot.model, "\n".join(lines[first : last + 1])
                ),
            )
            for index, (first, last) in enumerate(ranges, start=1)
        ],
    )


def list_parts(uow: UnitOfWork, meeting_id: str) -> list[Part]:
    """Interface "Partes": em ordem, com intervalo e "Texto da Parte"."""
    position = {
        segment_id: i for i, segment_id in enumerate(transcription.segment_ids(uow, meeting_id))
    }
    lines = transcript_lines(uow, meeting_id)
    parts = []
    for part in repository.list_parts(uow.session, meeting_id):
        first, last = position[part.first_segment_id], position[part.last_segment_id]
        parts.append(
            Part(
                index=part.index,
                first=first,
                last=last,
                start_seconds=part.start_seconds,
                end_seconds=part.end_seconds,
                estimated_tokens=part.estimated_tokens,
                text="\n".join(lines[first : last + 1]),
            )
        )
    return parts


def prepare_generation(
    uow: UnitOfWork,
    meeting_id: str,
    mode: Mode,
    *,
    now: datetime,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> str:
    """Interface "Preparar geração" (`transcript-split`, "Contrato"). Decide, nesta ordem: sem
    provedor, `failed`; inteira cabe, Parte única; modo `normal` com Partes anteriores que cabem,
    reaproveita sem regravar; segmento sozinho acima do orçamento, `failed`; senão `needs_split`.
    Nunca chama "Gerar" (3); Participantes e Transcrição não mudam (24). Devolve o status novo."""
    try:
        snapshot = owner_provider(uow, meeting_id)
    except llm_providers.NoActiveProvider:
        return _fail(uow, meeting_id, messages.NO_ACTIVE_PROVIDER, now)
    lines = transcript_lines(uow, meeting_id)
    budget = part_budget(uow, snapshot, meeting_id, estimate=estimate)

    def cost(text: str) -> int:
        return estimate(snapshot.provider, snapshot.model, text)

    if fits(cost("\n".join(lines)), budget):
        save_parts(uow, snapshot, meeting_id, [(0, len(lines) - 1)], estimate=estimate)
        return _start_generation(uow, meeting_id, now)
    previous = list_parts(uow, meeting_id) if mode == "normal" else []
    if previous and all(fits(cost(part.text), budget) for part in previous):
        return _start_generation(uow, meeting_id, now)
    if any(not fits(cost(line), budget) for line in lines):
        return _fail(uow, meeting_id, messages.SEGMENT_TOO_LONG, now)
    reason = "adjust" if mode == "reajustar" else "too_long"
    meetings.update_status(uow, meeting_id, "needs_split", split_reason=reason, now=now)
    return "needs_split"


def _start_generation(uow: UnitOfWork, meeting_id: str, now: datetime) -> str:
    """`generating` com `run_id` novo; "Partes prontas" sai uma vez, depois do commit."""
    run_id = meetings.update_status(uow, meeting_id, "generating", now=now)
    uow.publish_after_commit(PartsReady(meeting_id=meeting_id, run_id=run_id))
    return "generating"


def _fail(uow: UnitOfWork, meeting_id: str, message: str, now: datetime) -> str:
    meetings.update_status(
        uow, meeting_id, "failed", failed_stage="generation", message=message, now=now
    )
    return "failed"


def on_generation_requested(
    event: Event,
    uow_factory: Callable[[], UnitOfWork],
    *,
    now: Callable[[], datetime],
    estimate: Estimate = llm_providers.estimate_tokens,
) -> None:
    """Consome `ParticipantsConfirmed` e `RetryRequested(generation)`: "Preparar geração" no modo
    `normal`, só com a Reunião em `transcribed` e o `run_id` do aviso (`transcript-split` 46,
    ADR-0007). Exceção leva a `failed`, nunca a status preso (SEC-19)."""
    if isinstance(event, RetryRequested) and event.stage != "generation":
        return
    meeting_id = event.meeting_id
    try:
        with uow_factory() as uow:
            if not meetings.is_current_run(uow, meeting_id, event.run_id, status="transcribed"):
                return
            prepare_generation(uow, meeting_id, "normal", now=now(), estimate=estimate)
    except Exception:
        logger.exception("transcript_split.prepare_failed", extra={"meeting_id": meeting_id})
        with uow_factory() as uow:
            if meetings.is_current_run(uow, meeting_id, event.run_id, status="transcribed"):
                _fail(uow, meeting_id, messages.UNEXPECTED, now())


def subscribe(bus: EventBus, consumer: Callable[[Event], None]) -> None:
    """02-architecture, "Avisos": `transcript_split` consome os dois com `transcribed`."""
    bus.subscribe(ParticipantsConfirmed, consumer)
    bus.subscribe(RetryRequested, consumer)
