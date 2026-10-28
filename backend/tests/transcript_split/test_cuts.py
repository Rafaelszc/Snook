import itertools

from snook.modules.transcript_split.cuts import (
    cuts_of,
    estimate_ranges,
    greedy_ranges,
    ranges_from_cuts,
)

TOKENS = [4, 3, 5, 2, 6, 1, 3]


def _covers_all(ranges: list[tuple[int, int]], count: int) -> bool:
    expected = 0
    for first, last in ranges:
        if first != expected or last < first:
            return False
        expected = last + 1
    return expected == count


def test_suggested_parts_are_contiguous_cover_all_and_fit() -> None:
    """`transcript-split` 8: corte no fim de segmento, contíguas, sem sobreposição, cabem."""
    ranges = greedy_ranges(TOKENS, budget=9)

    assert _covers_all(ranges, len(TOKENS))
    assert all(part.fits for part in estimate_ranges(ranges, TOKENS, budget=9))
    assert ranges_from_cuts(cuts_of(ranges), len(TOKENS)) == ranges


def test_greedy_gives_fewest_parts() -> None:
    """`transcript-split` 9: nenhuma divisão com cortes no fim de segmento usa menos Partes."""
    budget = 9
    ranges = greedy_ranges(TOKENS, budget)
    positions = range(len(TOKENS) - 1)

    for size in range(len(ranges) - 1):
        for cuts in itertools.combinations(positions, size):
            parts = estimate_ranges(ranges_from_cuts(list(cuts), len(TOKENS)), TOKENS, budget)
            assert not all(part.fits for part in parts)
    assert ranges == [(0, 1), (2, 3), (4, 5), (6, 6)]


def test_each_part_has_range_estimate_and_fit() -> None:
    """`transcript-split` 10: intervalo, estimativa e se cabe."""
    parts = estimate_ranges([(0, 2), (3, 6)], TOKENS, budget=10)

    assert [(p.index, p.first, p.last, p.estimated_tokens, p.fits) for p in parts] == [
        (1, 0, 2, 12, False),
        (2, 3, 6, 12, False),
    ]
    assert estimate_ranges([(0, 6)], TOKENS, budget=0)[0].fits is False


def test_segment_above_budget_stays_alone_and_does_not_fit() -> None:
    parts = estimate_ranges(greedy_ranges([2, 20, 2], budget=5), [2, 20, 2], budget=5)

    assert [(p.first, p.last, p.fits) for p in parts] == [
        (0, 0, True),
        (1, 1, False),
        (2, 2, True),
    ]
