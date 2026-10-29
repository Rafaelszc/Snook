"""Cortes da divisão: sempre no fim de um segmento, Partes contíguas (`transcript-split` 8, 9).

Estimativa aditiva por linha (ADR-0011): Parte = soma dos seus segmentos.
"""

from dataclasses import dataclass

Range = tuple[int, int]


@dataclass(frozen=True)
class PartEstimate:
    """Parte por posições (`first` a `last`, inclusivas), `index` a partir de 1."""

    index: int
    first: int
    last: int
    estimated_tokens: int
    fits: bool


def greedy_ranges(tokens: list[int], budget: int) -> list[Range]:
    """Cada Parte leva o maior número de segmentos seguidos que cabe: menor número de Partes
    (9). Segmento que não cabe sozinho fica numa Parte só dele, que não cabe."""
    ranges: list[Range] = []
    first, total = 0, 0
    for position, cost in enumerate(tokens):
        if position > first and total + cost > budget:
            ranges.append((first, position - 1))
            first, total = position, 0
        total += cost
    if tokens:
        ranges.append((first, len(tokens) - 1))
    return ranges


def ranges_from_cuts(cuts: list[int], count: int) -> list[Range]:
    """`cuts`: posição do último segmento de cada Parte, menos a última; já validados."""
    starts = [0, *(cut + 1 for cut in cuts)]
    ends = [*cuts, count - 1]
    return list(zip(starts, ends, strict=True))


def cuts_of(ranges: list[Range]) -> list[int]:
    return [last for _first, last in ranges[:-1]]


def estimate_ranges(ranges: list[Range], tokens: list[int], budget: int) -> list[PartEstimate]:
    """Intervalo, estimativa e se cabe, por Parte (10). Cabe só com orçamento positivo (RT-10)."""
    estimates = []
    for index, (first, last) in enumerate(ranges, start=1):
        total = sum(tokens[first : last + 1])
        estimates.append(
            PartEstimate(index, first, last, total, fits=budget > 0 and total <= budget)
        )
    return estimates
