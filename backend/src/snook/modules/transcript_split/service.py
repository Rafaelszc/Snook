import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from snook.core.errors import AppError
from snook.core.events import Event, EventBus, ParticipantsConfirmed, PartsReady, RetryRequested
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.llm_providers import service as llm_providers
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.meetings import service as meetings
from snook.modules.meetings.schemas import MeetingDetail
from snook.modules.participants import service as participants
from snook.modules.transcript_split import messages, repository
from snook.modules.transcript_split.budget import compute_budget as compute_budget
from snook.modules.transcript_split.budget import fits as fits
from snook.modules.transcript_split.budget import output_reserve as output_reserve
from snook.modules.transcript_split.cuts import (
    Range,
    cuts_of,
    estimate_ranges,
    greedy_ranges,
    ranges_from_cuts,
)
from snook.modules.transcript_split.models import TranscriptPart
from snook.modules.transcript_split.part_text import format_line as format_line
from snook.modules.transcript_split.part_text import format_timestamp as format_timestamp
from snook.modules.transcript_split.schemas import SplitOut, SplitPartOut, SplitSegmentOut
from snook.shared.prompts import load_backlog_system_prompt

logger = logging.getLogger("snook.transcript_split")

Mode = Literal["normal", "reajustar"]

# "Estimar tokens" de `llm-providers`: `(provider, model, text) -> tokens`. Testes passam fake.
Estimate = Callable[[str, str, str], int]

# --- Interface para outros módulos (`02-architecture.md`, "Interfaces internas") ---


def _speaker_names(uow: UnitOfWork, meeting_id: str) -> dict[str, str]:
    return {
        label: participant.name
        for participant in participants.list_participants(uow, meeting_id)
        for label in participant.speaker_labels
    }


def transcript_lines(uow: UnitOfWork, meeting_id: str) -> list[str]:
    """Uma linha por segmento, na ordem, com o nome atual do Participante (`transcript-split` 27).

    Speaker sem Participante (antes da confirmação) sai com o rótulo.
    """
    names = _speaker_names(uow, meeting_id)
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


# --- Rotas de divisão (`transcript-split` 7 a 17, 39 a 44; ADR-0019) ---


@dataclass(frozen=True)
class _Measure:
    """Medida da Transcrição com o provedor ativo do momento: estimativa por segmento (ADR-0011)."""

    snapshot: ActiveProvider
    budget: int
    tokens: list[int]

    def whole_fits(self) -> bool:
        return fits(sum(self.tokens), self.budget)

    def segment_too_long(self) -> bool:
        return any(not fits(cost, self.budget) for cost in self.tokens)


def _measure(uow: UnitOfWork, meeting_id: str, estimate: Estimate) -> _Measure | None:
    """`None` sem provedor ativo."""
    try:
        snapshot = owner_provider(uow, meeting_id)
    except llm_providers.NoActiveProvider:
        return None
    return _Measure(
        snapshot=snapshot,
        budget=part_budget(uow, snapshot, meeting_id, estimate=estimate),
        tokens=[
            estimate(snapshot.provider, snapshot.model, line)
            for line in transcript_lines(uow, meeting_id)
        ],
    )


def _saved_ranges(uow: UnitOfWork, meeting_id: str) -> list[Range]:
    return [(part.first, part.last) for part in list_parts(uow, meeting_id)]


def _suggested_ranges(uow: UnitOfWork, meeting_id: str, measure: _Measure) -> list[Range]:
    """Cortes atuais, se a Reunião já foi dividida e todas as Partes ainda cabem; senão, regra
    gulosa (`transcript-split` 9, 22)."""
    saved = _saved_ranges(uow, meeting_id)
    if len(saved) > 1 and all(
        part.fits for part in estimate_ranges(saved, measure.tokens, measure.budget)
    ):
        return saved
    return greedy_ranges(measure.tokens, measure.budget)


def _view(
    uow: UnitOfWork, user_id: str, meeting_id: str, *, estimate: Estimate, read_only: bool = False
) -> SplitOut:
    """Sem provedor: só a mensagem (44). Fora de `needs_split` e de leitura: sem cortes (43).
    Relê a Reunião: depois de "passou a caber", mostra o status novo."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    base = {
        "status": meeting.status,
        "split_reason": meeting.split_reason,
        "can_cancel": meeting.status == "needs_split" and meeting.has_backlog,
        "read_only": read_only,
    }
    measure = _measure(uow, meeting.id, estimate)
    if measure is None:
        return SplitOut(
            **base,
            message=messages.NO_ACTIVE_PROVIDER,
            provider=None,
            model=None,
            budget=None,
            total_tokens=None,
            segments=[],
            cuts=[],
            parts=[],
        )
    head = {
        **base,
        "message": None,
        "provider": measure.snapshot.provider,
        "model": measure.snapshot.model,
        "budget": measure.budget,
        "total_tokens": sum(measure.tokens),
    }
    if meeting.status != "needs_split" and not read_only:
        return SplitOut(**head, segments=[], cuts=[], parts=[])
    ranges = (
        _saved_ranges(uow, meeting.id) if read_only else _suggested_ranges(uow, meeting.id, measure)
    )
    segments = transcription.list_segments(uow, meeting.id)
    ids = transcription.segment_ids(uow, meeting.id)
    names = _speaker_names(uow, meeting.id)
    return SplitOut(
        **head,
        segments=[
            SplitSegmentOut(
                id=ids[position],
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                participant=names.get(segment.speaker_label, segment.speaker_label),
                text=segment.text,
                tokens=measure.tokens[position],
            )
            for position, segment in enumerate(segments)
        ],
        cuts=[ids[position] for position in cuts_of(ranges)],
        parts=[
            SplitPartOut(
                index=part.index,
                first_segment_id=ids[part.first],
                last_segment_id=ids[part.last],
                start_seconds=segments[part.first].start_seconds,
                end_seconds=segments[part.last].end_seconds,
                estimated_tokens=part.estimated_tokens,
                fits=part.fits,
            )
            for part in estimate_ranges(ranges, measure.tokens, measure.budget)
        ],
    )


def _owned_in_needs_split(uow: UnitOfWork, user_id: str, meeting_id: str) -> MeetingDetail:
    """Dono conferido (404, SEC-02); fora de `needs_split`: 409 sem mudar nada."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.status != "needs_split":
        raise AppError("split_not_available", messages.SPLIT_NOT_AVAILABLE, 409)
    return meeting


def read_split(
    uow: UnitOfWork,
    *,
    user_id: str,
    meeting_id: str,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> SplitOut:
    """`GET /split`: só lê, nunca grava nem avisa (43). `done` já dividida: cortes atuais, só
    leitura (11)."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.status == "done" and len(list_parts(uow, meeting_id)) > 1:
        return _view(uow, user_id, meeting_id, estimate=estimate, read_only=True)
    _owned_in_needs_split(uow, user_id, meeting_id)
    return _view(uow, user_id, meeting_id, estimate=estimate)


def refresh_split(
    uow: UnitOfWork,
    *,
    user_id: str,
    meeting_id: str,
    now: datetime,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> SplitOut:
    """`POST /split/refresh`: regra "passou a caber" ao abrir a tela (43, ADR-0019). Não cabe ou
    sem provedor: nada muda e responde como o `GET` (44)."""
    _owned_in_needs_split(uow, user_id, meeting_id)
    measure = _measure(uow, meeting_id, estimate)
    if measure is not None and measure.whole_fits():
        save_parts(
            uow, measure.snapshot, meeting_id, [(0, len(measure.tokens) - 1)], estimate=estimate
        )
        _start_generation(uow, meeting_id, now)
    return _view(uow, user_id, meeting_id, estimate=estimate)


def _cut_positions(uow: UnitOfWork, meeting_id: str, cuts: list[int]) -> list[int]:
    """`id` do segmento → posição. Corte no fim do último segmento não divide nada: 422 como
    corte fora do fim de segmento (13). Repetido ou fora de ordem: 422 (14)."""
    ids = transcription.segment_ids(uow, meeting_id)
    position = {segment_id: i for i, segment_id in enumerate(ids[:-1])}
    if any(cut not in position for cut in cuts):
        raise AppError("cut_not_at_segment_end", messages.CUT_NOT_AT_SEGMENT_END, 422)
    positions = [position[cut] for cut in cuts]
    if any(a >= b for a, b in zip(positions, positions[1:], strict=False)):
        raise AppError("cuts_not_ordered", messages.CUTS_NOT_ORDERED, 422)
    return positions


def confirm_split(
    uow: UnitOfWork,
    *,
    user_id: str,
    meeting_id: str,
    cuts: list[int],
    now: datetime,
    estimate: Estimate = llm_providers.estimate_tokens,
) -> str:
    """`PUT /split`: revalida com o provedor ativo do momento (16). Ordem: sem provedor, `failed`
    (41); passou a caber, Parte única, cortes ignorados (43); segmento sozinho acima do orçamento,
    `failed` (42); Parte que não cabe, 422 `part_too_large` (15); senão grava e segue (12).
    Devolve o status novo."""
    _owned_in_needs_split(uow, user_id, meeting_id)
    positions = _cut_positions(uow, meeting_id, cuts)
    measure = _measure(uow, meeting_id, estimate)
    if measure is None:
        return _fail(uow, meeting_id, messages.NO_ACTIVE_PROVIDER, now)
    ranges = (
        [(0, len(measure.tokens) - 1)]
        if measure.whole_fits()
        else ranges_from_cuts(positions, len(measure.tokens))
    )
    if measure.segment_too_long():
        return _fail(uow, meeting_id, messages.SEGMENT_TOO_LONG, now)
    for part in estimate_ranges(ranges, measure.tokens, measure.budget):
        if not part.fits:
            raise AppError(
                "part_too_large",
                messages.PART_TOO_LARGE.format(index=part.index),
                422,
                details={"part_index": part.index, "estimated_tokens": part.estimated_tokens},
            )
    save_parts(uow, measure.snapshot, meeting_id, ranges, estimate=estimate)
    return _start_generation(uow, meeting_id, now)


def cancel_split(uow: UnitOfWork, *, user_id: str, meeting_id: str, now: datetime) -> str:
    """`POST /split/cancel`: `needs_split` → `done` com backlog gravado, qualquer `split_reason`;
    backlog e Partes não mudam, sem aviso (39). Sem backlog: 409 (40)."""
    meeting = _owned_in_needs_split(uow, user_id, meeting_id)
    if not meeting.has_backlog:
        raise AppError("split_cancel_not_allowed", messages.CANCEL_NOT_ALLOWED, 409)
    meetings.update_status(uow, meeting_id, "done", now=now)
    return "done"
