"""Junção dos turnos da diarização com os trechos da transcrição (ADR-0014)."""

from dataclasses import dataclass

from snook.modules.diarized_transcription.engines.base import Chunk, Turn


@dataclass(frozen=True)
class Segment:
    speaker_label: str
    start_seconds: float
    end_seconds: float
    text: str


def _overlap(chunk: Chunk, turn: Turn) -> float:
    return min(chunk.end_seconds, turn.end_seconds) - max(chunk.start_seconds, turn.start_seconds)


def _distance(chunk: Chunk, turn: Turn) -> float:
    return max(turn.start_seconds - chunk.end_seconds, chunk.start_seconds - turn.end_seconds, 0.0)


def _speaker(chunk: Chunk, turns: list[Turn]) -> str:
    """Maior sobreposição; sem sobreposição, turno mais próximo no tempo."""
    best = max(turns, key=lambda turn: _overlap(chunk, turn))
    if _overlap(chunk, best) > 0:
        return best.speaker_label
    return min(turns, key=lambda turn: _distance(chunk, turn)).speaker_label


def merge(turns: list[Turn], chunks: list[Chunk], duration_seconds: float) -> list[Segment]:
    """Segmentos em ordem de início, com `0 <= start < end <= duração` e texto não vazio."""
    segments: list[Segment] = []
    if not turns:
        return segments
    for chunk in sorted(chunks, key=lambda c: c.start_seconds):
        text = chunk.text.strip()
        start = max(chunk.start_seconds, 0.0)
        end = min(chunk.end_seconds, duration_seconds)
        if not text or start >= end:
            continue
        segments.append(Segment(_speaker(chunk, turns), start, end, text))
    return segments
