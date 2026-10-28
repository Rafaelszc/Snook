from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.participants import service as participants
from snook.modules.transcript_split.part_text import format_line as format_line

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
