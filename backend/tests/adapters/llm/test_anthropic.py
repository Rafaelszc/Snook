import json
import logging

import httpx
import pytest
import respx

from snook.modules.llm_providers.adapters.anthropic import AnthropicAdapter
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
from tests.adapters.llm.conftest import recorded

API_KEY = "sk-ant-TesteChave-0123456789abcdef"  # nome libera no .gitleaks.toml
MESSAGES_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-5"
SCHEMA = {"type": "object", "properties": {"epics": {"type": "array"}}, "required": ["epics"]}
REQUEST = GenerationRequest(
    system_prompt="Gere o backlog.",
    content="Fulano: precisamos de login.",
    json_schema=SCHEMA,
    max_output_tokens=4096,
)
ADAPTER = AnthropicAdapter(read_timeout=300)


def _target(model: str = MODEL) -> ProviderTarget:
    return ProviderTarget(model=model, api_key=API_KEY)


@respx.mock
def test_generate_returns_tool_input_as_json() -> None:
    """`llm-providers` 29."""
    route = respx.post(MESSAGES_URL).mock(return_value=recorded("anthropic", "generate_success"))
    text = ADAPTER.generate(_target(), REQUEST)
    assert json.loads(text) == {"epics": [{"title": "Login", "user_stories": []}]}

    request = route.calls.last.request
    assert request.headers["anthropic-version"] == "2023-06-01"
    sent = json.loads(request.content)
    assert sent["model"] == MODEL
    assert sent["max_tokens"] == 4096
    assert sent["system"] == REQUEST.system_prompt
    assert sent["messages"] == [{"role": "user", "content": REQUEST.content}]
    assert sent["tools"] == [
        {
            "name": "submit_backlog",
            "description": sent["tools"][0]["description"],
            "input_schema": SCHEMA,
        }
    ]
    assert sent["tool_choice"] == {"type": "tool", "name": "submit_backlog"}


@respx.mock
@pytest.mark.parametrize(
    ("case", "error_type"),
    [
        ("unauthorized", CredentialRejected),
        ("forbidden", CredentialRejected),
        ("model_not_found", ModelNotFound),
        ("context_exceeded", ContextLimitExceeded),
        ("rate_limited", ProviderRateLimited),
        ("overloaded", ProviderUnreachable),
        ("redirect", ProviderUnreachable),
    ],
)
def test_recorded_errors_become_typed_errors(case: str, error_type: type[LLMError]) -> None:
    """`llm-providers` 30."""
    respx.post(MESSAGES_URL).mock(return_value=recorded("anthropic", case))
    with pytest.raises(error_type):
        ADAPTER.generate(_target(), REQUEST)


@respx.mock
@pytest.mark.parametrize("failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_network_failure_becomes_unreachable(failure: Exception) -> None:
    """`llm-providers` 30."""
    respx.post(MESSAGES_URL).mock(side_effect=failure)
    with pytest.raises(ProviderUnreachable):
        ADAPTER.generate(_target(), REQUEST)


@respx.mock
@pytest.mark.parametrize(
    "body",
    [
        {"content": []},
        {"content": [{"type": "text", "text": "sem ferramenta"}]},
        {"content": [{"type": "tool_use", "name": "outra", "input": {}}]},
        {"content": [{"type": "tool_use", "name": "submit_backlog", "input": "texto"}]},
        [1, 2],
    ],
)
def test_response_without_tool_input_becomes_unreachable(body: object) -> None:
    respx.post(MESSAGES_URL).respond(200, json=body)
    with pytest.raises(ProviderUnreachable) as exc:
        ADAPTER.generate(_target(), REQUEST)
    assert exc.value.reason == "invalid_response"


@respx.mock
def test_connection_test_reads_the_model() -> None:
    route = respx.get(f"https://api.anthropic.com/v1/models/{MODEL}").mock(
        return_value=recorded("anthropic", "model_retrieve")
    )
    ADAPTER.test_connection(_target())
    request = route.calls.last.request
    assert request.extensions["timeout"]["read"] == 20
    assert request.headers["x-api-key"] == API_KEY


@respx.mock
@pytest.mark.parametrize(
    ("case", "error_type"),
    [
        ("model_not_found", ModelNotFound),
        ("unauthorized", CredentialRejected),
        ("redirect", ProviderUnreachable),
    ],
)
def test_connection_test_errors(case: str, error_type: type[LLMError]) -> None:
    respx.get(f"https://api.anthropic.com/v1/models/{MODEL}").mock(
        return_value=recorded("anthropic", case)
    )
    with pytest.raises(error_type):
        ADAPTER.test_connection(_target())


@respx.mock
def test_connection_test_quotes_model_in_path() -> None:
    route = respx.get("https://api.anthropic.com/v1/models/a%2F..%2Fb").mock(
        return_value=recorded("anthropic", "model_not_found")
    )
    with pytest.raises(ModelNotFound):
        ADAPTER.test_connection(_target("a/../b"))
    assert route.call_count == 1


@respx.mock
def test_key_goes_only_in_api_key_header() -> None:
    """`llm-providers` 27; SEC-07."""
    route = respx.post(MESSAGES_URL).mock(return_value=recorded("anthropic", "generate_success"))
    ADAPTER.generate(_target(), REQUEST)
    request = route.calls.last.request
    assert request.headers["x-api-key"] == API_KEY
    others = {k: v for k, v in request.headers.items() if k != "x-api-key"}
    assert API_KEY not in str(request.url)
    assert API_KEY not in str(others)
    assert API_KEY.encode() not in request.content


@respx.mock
@pytest.mark.parametrize("case", ["unauthorized", "model_not_found", "context_exceeded"])
def test_key_never_in_error_or_log(case: str, caplog: pytest.LogCaptureFixture) -> None:
    """`llm-providers` 27; SEC-07."""
    respx.post(MESSAGES_URL).mock(return_value=recorded("anthropic", case))
    caplog.set_level(logging.DEBUG)
    with pytest.raises(LLMError) as exc:
        ADAPTER.generate(_target(), REQUEST)
    error = exc.value
    for text in (str(error), repr(error), error.message, str(vars(error))):
        assert API_KEY not in text
    assert API_KEY not in " ".join(str(vars(record)) for record in caplog.records)
