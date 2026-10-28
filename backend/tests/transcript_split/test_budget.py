import sqlite3
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.transcript_split import service
from snook.shared.prompts import load_backlog_system_prompt
from tests.transcript_split.helpers import confirmed

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
Call = tuple[str, str, str]


class FakeEstimate:
    """ "Estimar tokens" fake: um token por caractere; registra cada chamada."""

    def __init__(self) -> None:
        self.calls: list[Call] = []

    def __call__(self, provider: str, model: str, text: str) -> int:
        self.calls.append((provider, model, text))
        return len(text)


def test_budget_is_window_minus_reserve() -> None:
    """ADR-0011: prompt, Participantes, 1.000 de Epics, resposta e 5% de margem."""
    assert service.compute_budget(100_000, system_prompt_tokens=500, participants_tokens=20) == (
        100_000 - 500 - 20 - 1_000 - 16_000 - 5_000
    )
    assert service.compute_budget(8_192, system_prompt_tokens=500, participants_tokens=20) == (
        8_192 - 500 - 20 - 1_000 - 2_048 - 410
    )


def test_window_below_reserve_gives_non_positive_budget() -> None:
    """ADR-0011: orçamento ≤ 0 sem erro; nada cabe."""
    budget = service.compute_budget(1_000, system_prompt_tokens=500, participants_tokens=20)

    assert budget <= 0
    assert not service.fits(0, budget)


def test_estimate_above_budget_never_fits() -> None:
    """RT-10."""
    assert service.fits(100, 100)
    assert not service.fits(101, 100)


def test_part_budget_measures_prompt_and_participants(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """ADR-0011: reserva mede o System Prompt atual e a lista de Participantes da Reunião."""
    meeting_id = confirmed(idle, settings)
    estimate = FakeEstimate()
    snapshot = ActiveProvider(provider="ollama", model="llama3", context_window=100_000)
    with uow() as unit:
        budget = service.part_budget(unit, snapshot, meeting_id, estimate=estimate)
        participants = service.participants_text(unit, meeting_id)

    assert participants == "Participantes:\n- Ana\n- Bia"
    assert estimate.calls == [
        ("ollama", "llama3", load_backlog_system_prompt()),
        ("ollama", "llama3", participants),
    ]
    assert budget == service.compute_budget(
        100_000,
        system_prompt_tokens=len(load_backlog_system_prompt()),
        participants_tokens=len(participants),
    )


def test_estimate_uses_part_text_and_owner_provider(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 4."""
    meeting_id = confirmed(idle, settings)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            "INSERT INTO llm_configs (user_id, provider, base_url, model, context_window, "
            "key_status, is_active, created_at, updated_at) "
            "SELECT id, 'openai', NULL, 'gpt-x', 128000, 'ok', 1, "
            "'2026-10-28T12:00:00Z', '2026-10-28T12:00:00Z' FROM users WHERE username = 'bia'"
        )
    estimate = FakeEstimate()
    with uow() as unit:
        snapshot = service.owner_provider(unit, meeting_id)
        tokens = service.estimate_part(unit, snapshot, meeting_id, 1, 2, estimate=estimate)
        text = service.part_text(unit, meeting_id, 1, 2)

    assert snapshot == ActiveProvider(provider="ollama", model="llama3", context_window=8192)
    assert estimate.calls == [("ollama", "llama3", text)]
    assert tokens == len(text)
