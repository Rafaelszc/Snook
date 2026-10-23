import json
import logging

import httpx
import pytest
import respx

from snook.modules.llm_providers.adapters.base import (
    ContextLimitExceeded,
    CredentialRejected,
    GenerationRequest,
    LLMError,
    ModelNotFound,
    ProviderRateLimited,
    ProviderTarget,
    ProviderUnreachable,
)
from snook.modules.llm_providers.adapters.openai_compat import OpenAICompatAdapter
from tests.adapters.llm.conftest import FIXTURES, recorded

API_KEY = "sk-TesteChave-0123456789abcdef"  # nome libera no .gitleaks.toml
CHAT_URL = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
}
MODEL = {"openai": "gpt-5-mini", "deepseek": "deepseek-chat"}
PROVIDERS = ["openai", "deepseek"]
REQUEST = GenerationRequest(
    system_prompt="Responda em JSON.",
    content="Fulano: precisamos de login.",
    json_schema={"type": "object"},
    max_output_tokens=4096,
)


def _adapter(provider: str) -> OpenAICompatAdapter:
    return OpenAICompatAdapter(provider, read_timeout=300)


def _target(provider: str, model: str | None = None) -> ProviderTarget:
    return ProviderTarget(model=model or MODEL[provider], api_key=API_KEY)


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
def test_generate_returns_recorded_text(provider: str) -> None:
    """`llm-providers` 29."""
    route = respx.post(CHAT_URL[provider]).mock(return_value=recorded(provider, "generate_success"))
    text = _adapter(provider).generate(_target(provider), REQUEST)
    assert json.loads(text) == {"epics": [{"title": "Login", "user_stories": []}]}

    sent = json.loads(route.calls.last.request.content)
    assert sent["model"] == MODEL[provider]
    assert sent["messages"] == [
        {"role": "system", "content": REQUEST.system_prompt},
        {"role": "user", "content": REQUEST.content},
    ]
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["stream"] is False


@respx.mock
@pytest.mark.parametrize(
    ("provider", "field"), [("openai", "max_completion_tokens"), ("deepseek", "max_tokens")]
)
def test_generate_sends_provider_output_limit_field(provider: str, field: str) -> None:
    route = respx.post(CHAT_URL[provider]).mock(return_value=recorded(provider, "generate_success"))
    _adapter(provider).generate(_target(provider), REQUEST)
    sent = json.loads(route.calls.last.request.content)
    other = ({"max_tokens", "max_completion_tokens"} - {field}).pop()
    assert sent[field] == 4096
    assert other not in sent


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize(
    ("case", "error_type"),
    [
        ("unauthorized", CredentialRejected),
        ("model_not_found", ModelNotFound),
        ("context_exceeded", ContextLimitExceeded),
        ("rate_limited", ProviderRateLimited),
        ("server_error", ProviderUnreachable),
        ("redirect", ProviderUnreachable),
    ],
)
def test_recorded_errors_become_typed_errors(
    provider: str, case: str, error_type: type[LLMError]
) -> None:
    """`llm-providers` 30."""
    respx.post(CHAT_URL[provider]).mock(return_value=recorded(provider, case))
    with pytest.raises(error_type):
        _adapter(provider).generate(_target(provider), REQUEST)


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_network_failure_becomes_unreachable(provider: str, failure: Exception) -> None:
    """`llm-providers` 30."""
    respx.post(CHAT_URL[provider]).mock(side_effect=failure)
    with pytest.raises(ProviderUnreachable):
        _adapter(provider).generate(_target(provider), REQUEST)


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"unexpected": True},
        [1, 2],
    ],
)
def test_unexpected_success_body_becomes_unreachable(provider: str, body: object) -> None:
    respx.post(CHAT_URL[provider]).respond(200, json=body)
    with pytest.raises(ProviderUnreachable) as exc:
        _adapter(provider).generate(_target(provider), REQUEST)
    assert exc.value.reason == "invalid_response"


@respx.mock
def test_openai_connection_test_reads_the_model() -> None:
    route = respx.get("https://api.openai.com/v1/models/gpt-5-mini").mock(
        return_value=recorded("openai", "model_retrieve")
    )
    _adapter("openai").test_connection(_target("openai"))
    assert route.calls.last.request.extensions["timeout"]["read"] == 20


@respx.mock
def test_openai_connection_test_quotes_model_in_path() -> None:
    route = respx.get("https://api.openai.com/v1/models/a%2F..%2Fb").mock(
        return_value=recorded("openai", "model_not_found")
    )
    with pytest.raises(ModelNotFound):
        _adapter("openai").test_connection(_target("openai", "a/../b"))
    assert route.call_count == 1


@respx.mock
def test_openai_connection_test_unknown_model() -> None:
    respx.get("https://api.openai.com/v1/models/gpt-inexistente").mock(
        return_value=recorded("openai", "model_not_found")
    )
    with pytest.raises(ModelNotFound):
        _adapter("openai").test_connection(_target("openai", "gpt-inexistente"))


@respx.mock
def test_deepseek_connection_test_finds_model_in_list() -> None:
    route = respx.get("https://api.deepseek.com/models").mock(
        return_value=recorded("deepseek", "models_list")
    )
    _adapter("deepseek").test_connection(_target("deepseek"))
    assert route.calls.last.request.extensions["timeout"]["read"] == 20


@respx.mock
def test_deepseek_connection_test_model_missing_from_list() -> None:
    respx.get("https://api.deepseek.com/models").mock(
        return_value=recorded("deepseek", "models_list")
    )
    with pytest.raises(ModelNotFound):
        _adapter("deepseek").test_connection(_target("deepseek", "deepseek-inexistente"))


@respx.mock
@pytest.mark.parametrize(
    ("provider", "url"),
    [
        ("openai", "https://api.openai.com/v1/models/gpt-5-mini"),
        ("deepseek", "https://api.deepseek.com/models"),
    ],
)
@pytest.mark.parametrize(
    ("case", "error_type"),
    [("unauthorized", CredentialRejected), ("redirect", ProviderUnreachable)],
)
def test_connection_test_errors(
    provider: str, url: str, case: str, error_type: type[LLMError]
) -> None:
    respx.get(url).mock(return_value=recorded(provider, case))
    with pytest.raises(error_type):
        _adapter(provider).test_connection(_target(provider))


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError):
        OpenAICompatAdapter("anthropic", read_timeout=300)


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
def test_key_goes_only_in_authorization_header(provider: str) -> None:
    """`llm-providers` 9, 27; SEC-07."""
    route = respx.post(CHAT_URL[provider]).mock(return_value=recorded(provider, "generate_success"))
    _adapter(provider).generate(_target(provider), REQUEST)
    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    others = {k: v for k, v in request.headers.items() if k != "authorization"}
    assert API_KEY not in str(request.url)
    assert API_KEY not in str(others)
    assert API_KEY.encode() not in request.content


@respx.mock
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("case", ["unauthorized", "model_not_found", "context_exceeded"])
def test_key_never_in_error_or_log(
    provider: str, case: str, caplog: pytest.LogCaptureFixture
) -> None:
    """`llm-providers` 27; SEC-07. Erro leva tipo e motivo, sem corpo do provedor."""
    respx.post(CHAT_URL[provider]).mock(return_value=recorded(provider, case))
    caplog.set_level(logging.DEBUG)
    with pytest.raises(LLMError) as exc:
        _adapter(provider).generate(_target(provider), REQUEST)
    error = exc.value
    for text in (str(error), repr(error), error.message, str(vars(error))):
        assert API_KEY not in text
        assert "cdef" not in text  # pedaço da chave que o provedor ecoa no corpo
    assert API_KEY not in " ".join(str(vars(record)) for record in caplog.records)


def test_target_repr_hides_key() -> None:
    assert API_KEY not in repr(_target("openai"))


def test_fixtures_never_contain_the_key() -> None:
    """`llm-providers` 27; SEC-07."""
    for path in FIXTURES.rglob("*.json"):
        text = path.read_text()
        assert API_KEY not in text, path
        assert "authorization" not in text.lower(), path
