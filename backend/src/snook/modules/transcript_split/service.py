from collections.abc import Callable

from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.llm_providers import service as llm_providers
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.meetings import service as meetings
from snook.modules.participants import service as participants
from snook.modules.transcript_split.budget import compute_budget as compute_budget
from snook.modules.transcript_split.budget import fits as fits
from snook.modules.transcript_split.budget import output_reserve as output_reserve
from snook.modules.transcript_split.part_text import format_line as format_line
from snook.shared.prompts import load_backlog_system_prompt

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
