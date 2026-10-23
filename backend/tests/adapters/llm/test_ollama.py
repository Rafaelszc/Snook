import json

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
from snook.modules.llm_providers.adapters.ollama import (
    InvalidBaseUrl,
    OllamaAdapter,
    normalize_base_url,
)
from tests.adapters.llm.conftest import recorded

BASE = "http://host.docker.internal:11434"
MODEL = "llama3.1:8b"
SCHEMA = {"type": "object", "properties": {"epics": {"type": "array"}}}
REQUEST = GenerationRequest(
    system_prompt="Gere o backlog.",
    content="Fulano: precisamos de login.",
    json_schema=SCHEMA,
    max_output_tokens=2048,
)
ADAPTER = OllamaAdapter(read_timeout=300)


def _target(base_url: str = BASE, model: str = MODEL) -> ProviderTarget:
    return ProviderTarget(model=model, base_url=base_url, context_window=8192)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://localhost:11434", "http://localhost:11434"),
        ("http://host.docker.internal:11434/", "http://host.docker.internal:11434"),
        ("https://192.168.0.20:11434", "https://192.168.0.20:11434"),
        ("http://10.0.0.5", "http://10.0.0.5"),
        ("HTTP://ollama.lan:11434", "HTTP://ollama.lan:11434"),
        ("http://[::1]:11434", "http://[::1]:11434"),
    ],
)
def test_accepts_any_host_with_http_or_https(url: str, expected: str) -> None:
    """`llm-providers` 38."""
    assert normalize_base_url(url) == expected


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://host/x", "gopher://host", "localhost:11434", "//host:11434", ""],
)
def test_rejects_other_schemes(url: str) -> None:
    """`llm-providers` 38."""
    with pytest.raises(InvalidBaseUrl) as exc:
        normalize_base_url(url)
    assert exc.value.code == "invalid_url_scheme"


@pytest.mark.parametrize(
    "url",
    ["http://usuario:OutraChave99@host:11434", "http://usuario@host:11434", "https://:x@host"],
)
def test_rejects_embedded_credentials(url: str) -> None:
    """`llm-providers` 40."""
    with pytest.raises(InvalidBaseUrl) as exc:
        normalize_base_url(url)
    assert exc.value.code == "url_with_credentials"
    assert "OutraChave99" not in str(exc.value)
    assert "OutraChave99" not in exc.value.message


@pytest.mark.parametrize("url", ["http://", "http://:11434", "https:///api"])
def test_rejects_empty_host(url: str) -> None:
    with pytest.raises(InvalidBaseUrl) as exc:
        normalize_base_url(url)
    assert exc.value.code == "invalid_url"


def test_invalid_url_errors_carry_pt_br_message() -> None:
    with pytest.raises(InvalidBaseUrl) as exc:
        normalize_base_url("ftp://host")
    assert exc.value.message == "Use uma URL http:// ou https://."


@respx.mock
def test_generate_returns_recorded_text() -> None:
    """`llm-providers` 29."""
    route = respx.post(f"{BASE}/api/chat").mock(return_value=recorded("ollama", "generate_success"))
    text = ADAPTER.generate(_target(BASE + "/"), REQUEST)
    assert json.loads(text) == {"epics": [{"title": "Login", "user_stories": []}]}

    sent = json.loads(route.calls.last.request.content)
    assert sent == {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": REQUEST.system_prompt},
            {"role": "user", "content": REQUEST.content},
        ],
        "stream": False,
        "format": SCHEMA,
        "options": {"num_ctx": 8192, "num_predict": 2048},
    }


@respx.mock
@pytest.mark.parametrize(
    ("case", "error_type"),
    [
        ("model_not_found", ModelNotFound),
        ("context_exceeded", ContextLimitExceeded),
        ("unauthorized", CredentialRejected),
        ("rate_limited", ProviderRateLimited),
        ("server_error", ProviderUnreachable),
    ],
)
def test_recorded_errors_become_typed_errors(case: str, error_type: type[LLMError]) -> None:
    """`llm-providers` 30."""
    respx.post(f"{BASE}/api/chat").mock(return_value=recorded("ollama", case))
    with pytest.raises(error_type):
        ADAPTER.generate(_target(), REQUEST)


@respx.mock
@pytest.mark.parametrize("failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_network_failure_becomes_unreachable(failure: Exception) -> None:
    """`llm-providers` 30."""
    respx.post(f"{BASE}/api/chat").mock(side_effect=failure)
    with pytest.raises(ProviderUnreachable):
        ADAPTER.generate(_target(), REQUEST)


@respx.mock
@pytest.mark.parametrize(
    "body", [{"message": {}}, {"message": {"content": None}}, {"done": True}, [1]]
)
def test_unexpected_success_body_becomes_unreachable(body: object) -> None:
    respx.post(f"{BASE}/api/chat").respond(200, json=body)
    with pytest.raises(ProviderUnreachable) as exc:
        ADAPTER.generate(_target(), REQUEST)
    assert exc.value.reason == "invalid_response"


@respx.mock
def test_generate_redirect_to_metadata_is_not_followed() -> None:
    """`llm-providers` 39. Abuse case: 302 para 169.254.169.254 não é seguido."""
    respx.post(f"{BASE}/api/chat").mock(return_value=recorded("ollama", "redirect"))
    metadata = respx.route(host="169.254.169.254").respond(200)
    with pytest.raises(ProviderUnreachable) as exc:
        ADAPTER.generate(_target(), REQUEST)
    assert exc.value.reason == "redirect"
    assert exc.value.message == "Provedor inacessível (redirecionamento recusado)."
    assert metadata.call_count == 0


@respx.mock
def test_connection_test_redirect_is_not_followed() -> None:
    """`llm-providers` 39."""
    respx.post(f"{BASE}/api/show").mock(return_value=recorded("ollama", "redirect"))
    metadata = respx.route(host="169.254.169.254").respond(200)
    with pytest.raises(ProviderUnreachable) as exc:
        ADAPTER.test_connection(_target())
    assert exc.value.reason == "redirect"
    assert metadata.call_count == 0


@respx.mock
def test_connection_test_shows_the_model() -> None:
    route = respx.post(f"{BASE}/api/show").mock(return_value=recorded("ollama", "show_success"))
    ADAPTER.test_connection(_target())
    request = route.calls.last.request
    assert json.loads(request.content) == {"model": MODEL}
    assert request.extensions["timeout"]["read"] == 20
    assert "authorization" not in request.headers


@respx.mock
def test_connection_test_unknown_model() -> None:
    respx.post(f"{BASE}/api/show").mock(return_value=recorded("ollama", "model_not_found"))
    with pytest.raises(ModelNotFound):
        ADAPTER.test_connection(_target(model="llama-inexistente"))


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://u:p@host", None])
def test_adapter_refuses_invalid_url_without_request(url: str | None) -> None:
    with respx.mock(assert_all_called=False) as mock:
        any_route = mock.route().respond(200)
        with pytest.raises(InvalidBaseUrl):
            ADAPTER.generate(ProviderTarget(model=MODEL, base_url=url), REQUEST)
        with pytest.raises(InvalidBaseUrl):
            ADAPTER.test_connection(ProviderTarget(model=MODEL, base_url=url))
        assert any_route.call_count == 0
