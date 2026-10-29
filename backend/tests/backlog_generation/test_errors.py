import logging
import sqlite3
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import messages
from snook.modules.llm_providers.adapters.base import GenerationRequest, ProviderTarget
from snook.modules.llm_providers.service import (
    ContextLimitExceeded,
    CredentialRejected,
    LLMError,
    ModelNotFound,
    ProviderRateLimited,
    ProviderUnreachable,
)
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    count,
    generating,
    parts_ready,
    story,
)
from tests.diarized_transcription.helpers import state
from tests.llm_providers.conftest import API_KEY, save

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
THREE_PARTS = [(0, 0), (1, 1), (2, 2)]

TYPED = [
    (CredentialRejected("http_401"), messages.CREDENTIAL_REJECTED),
    (CredentialRejected("unreadable_key"), messages.KEY_UNREADABLE),
    (ProviderUnreachable("timeout"), messages.PROVIDER_UNREACHABLE),
    (ModelNotFound("http_404"), messages.MODEL_NOT_FOUND),
    (ContextLimitExceeded("http_400"), messages.CONTEXT_LIMIT_EXCEEDED.format(index=2)),
    (ProviderRateLimited("http_429"), messages.PROVIDER_RATE_LIMITED),
]


def _failure(settings: Settings, meeting_id: str) -> str:
    status, stage, message = state(settings.database_path, meeting_id)
    assert (status, stage) == ("failed", "generation")
    return str(message)


def _nothing_saved(settings: Settings) -> None:
    for table in ("epics", "user_stories", "acceptance_criteria"):
        assert count(settings, table) == 0


@pytest.mark.parametrize(("error", "expected"), TYPED, ids=lambda value: str(value)[:30])
def test_typed_error_has_own_message(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    error: LLMError,
    expected: str,
) -> None:
    """`backlog-generation` 26: cada erro tipado vai a `failed` com mensagem própria."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog(("Cadastro", [story()])), error]

    parts_ready(idle, meeting_id)

    assert _failure(settings, meeting_id) == expected
    assert len(generate.calls) == 2
    _nothing_saved(settings)


def test_typed_messages_are_distinct() -> None:
    """`backlog-generation` 26: uma mensagem por tipo; a de credencial aponta Configurações."""
    texts = [expected for _, expected in TYPED]
    assert len(set(texts)) == len(texts)
    assert "Configurações" in messages.CREDENTIAL_REJECTED
    assert "Configurações" in messages.KEY_UNREADABLE


@pytest.mark.parametrize(
    ("reply", "reason"),
    [
        ("não é JSON", messages.RESPONSE_NOT_JSON),
        ('{"epics": "x"}', messages.RESPONSE_OFF_SCHEMA),
    ],
)
def test_invalid_response_cites_part_and_reason(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    reply: str,
    reason: str,
) -> None:
    """`backlog-generation` 15: cita Parte e motivo; nada gravado; sem nova chamada."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog(("Cadastro", [story()])), reply, backlog(("Outra", [story()]))]

    parts_ready(idle, meeting_id)

    assert _failure(settings, meeting_id) == messages.INVALID_RESPONSE.format(
        index=2, reason=reason
    )
    assert len(generate.calls) == 2
    _nothing_saved(settings)


class _FailingAdapter:
    """Adapter real trocado: falha com o erro dado depois de receber a chave."""

    def __init__(self, error: LLMError) -> None:
        self.error = error
        self.keys: list[str | None] = []

    def test_connection(self, target: ProviderTarget) -> None:
        return None

    def list_models(self, target: ProviderTarget) -> list[str]:
        return []

    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        self.keys.append(target.api_key)
        raise self.error


@pytest.mark.parametrize("error", [error for error, _ in TYPED], ids=lambda e: str(e)[:30])
def test_key_never_in_message_log_or_db(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    caplog: pytest.LogCaptureFixture,
    error: LLMError,
) -> None:
    """`backlog-generation` 27; SEC-07, SEC-20: chave fora de mensagem, log e banco."""
    app: FastAPI = idle.app  # type: ignore[assignment]
    adapter = _FailingAdapter(error)
    app.state.llm_adapters = {**app.state.llm_adapters, "openai": adapter}
    app.state.generate_backlog = app.state.generation.run
    meeting_id = generating(idle, settings, uow)
    assert save(idle, model="gpt-4o", context_window=128000).status_code == 200
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE llm_configs SET is_active = (provider = 'openai')")
    caplog.set_level(logging.DEBUG)

    parts_ready(idle, meeting_id)

    assert adapter.keys == [API_KEY]
    assert API_KEY not in _failure(settings, meeting_id)
    assert API_KEY not in caplog.text
    with sqlite3.connect(settings.database_path) as conn:
        assert not any(API_KEY in line for line in conn.iterdump())
