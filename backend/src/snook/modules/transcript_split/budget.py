"""Orçamento da Parte: janela menos reserva (ADR-0011)."""

import math

EPIC_NAMES_RESERVE = 1_000
OUTPUT_RESERVE_MAX = 16_000
OUTPUT_RESERVE_RATIO = 0.25
SAFETY_MARGIN_RATIO = 0.05


def output_reserve(context_window: int) -> int:
    """Também vai como limite de saída da chamada."""
    return min(OUTPUT_RESERVE_MAX, math.floor(context_window * OUTPUT_RESERVE_RATIO))


def compute_budget(
    context_window: int, *, system_prompt_tokens: int, participants_tokens: int
) -> int:
    """Pode dar zero ou negativo: janela menor que a reserva. Quem chama trata como "não cabe"."""
    reserve = (
        system_prompt_tokens
        + participants_tokens
        + EPIC_NAMES_RESERVE
        + output_reserve(context_window)
        + math.ceil(context_window * SAFETY_MARGIN_RATIO)
    )
    return context_window - reserve


def fits(estimate: int, budget: int) -> bool:
    """RT-10: cabe só com orçamento positivo e estimativa até ele."""
    return budget > 0 and estimate <= budget
