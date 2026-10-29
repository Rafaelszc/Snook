import logging

import httpx
import pytest
import respx

from snook.modules.llm_providers.adapters.base import (
    MAX_RESPONSE_BYTES,
    ContextLimitExceeded,
    CredentialRejected,
    LLMError,
    ModelNotFound,
    NoActiveProvider,
    ProviderRateLimited,
    ProviderResponse,
    ProviderUnreachable,
    build_client,
    raise_for_status,
    send,
)

URL = "https://llm.test/v1/chat"
API_KEY = "sk-TesteChave-0123456789abcdef"  # nome libera no .gitleaks.toml


def _send(**kwargs: object) -> ProviderResponse:
    with build_client(read_timeout=5) as client:
        return send(
            client,
            "POST",
            URL,
            provider="openai",
            operation="generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"q": 1},
            **kwargs,  # type: ignore[arg-type]
        )


def test_client_does_not_follow_redirects_and_uses_adr_timeouts() -> None:
    with build_client(read_timeout=300) as client:
        assert client.follow_redirects is False
        assert client.timeout == httpx.Timeout(connect=10, read=300, write=30, pool=10)


@respx.mock
@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_becomes_unreachable_without_following(status: int) -> None:
    """`llm-providers` 39; SEC-17."""
    route = respx.post(URL).respond(status, headers={"Location": "http://169.254.169.254/"})
    metadata = respx.get("http://169.254.169.254/").respond(200)
    with pytest.raises(ProviderUnreachable) as exc:
        _send()
    assert exc.value.reason == "redirect"
    assert exc.value.message == "Provedor inacessível (redirecionamento recusado)."
    assert route.call_count == 1
    assert metadata.call_count == 0


@respx.mock
def test_body_over_5mb_is_cut_and_becomes_unreachable() -> None:
    """SEC-17."""
    respx.post(URL).respond(200, content=b"x" * (6 * 1024 * 1024))
    with pytest.raises(ProviderUnreachable) as exc:
        _send()
    assert exc.value.reason == "body_too_large"


@respx.mock
def test_body_at_5mb_is_accepted() -> None:
    respx.post(URL).respond(200, content=b"x" * MAX_RESPONSE_BYTES)
    assert len(_send().body) == MAX_RESPONSE_BYTES


@respx.mock
def test_read_timeout_becomes_unreachable() -> None:
    """SEC-17."""
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("timed out"))
    with pytest.raises(ProviderUnreachable) as exc:
        _send()
    assert exc.value.reason == "timeout"


@respx.mock
@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("refused"), httpx.ConnectTimeout("slow"), httpx.RemoteProtocolError("x")],
)
def test_network_failure_becomes_unreachable(failure: Exception) -> None:
    respx.post(URL).mock(side_effect=failure)
    with pytest.raises(ProviderUnreachable):
        _send()


@respx.mock
def test_read_timeout_override_applies_to_request() -> None:
    route = respx.post(URL).respond(200, json={})
    _send(read_timeout=20)
    assert route.calls.last.request.extensions["timeout"]["read"] == 20


@pytest.mark.parametrize(
    ("status", "error_type", "reason"),
    [
        (401, CredentialRejected, "unauthorized"),
        (403, CredentialRejected, "unauthorized"),
        (404, ModelNotFound, "model_not_found"),
        (429, ProviderRateLimited, "rate_limited"),
        (500, ProviderUnreachable, "server_error"),
        (503, ProviderUnreachable, "server_error"),
        (400, ProviderUnreachable, "http_400"),
    ],
)
def test_status_maps_to_typed_error(status: int, error_type: type[LLMError], reason: str) -> None:
    with pytest.raises(error_type) as exc:
        raise_for_status(ProviderResponse(status, b'{"error": "corpo cru"}'))
    assert exc.value.reason == reason


def test_classifier_runs_before_generic_mapping() -> None:
    def classify(response: ProviderResponse) -> LLMError | None:
        return ContextLimitExceeded("context_limit") if response.status_code == 400 else None

    with pytest.raises(ContextLimitExceeded):
        raise_for_status(ProviderResponse(400, b"{}"), classify=classify)


def test_success_status_passes() -> None:
    raise_for_status(ProviderResponse(200, b"{}"))


def test_invalid_json_becomes_unreachable() -> None:
    with pytest.raises(ProviderUnreachable) as exc:
        ProviderResponse(200, b"<html>").json()
    assert exc.value.reason == "invalid_response"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            NoActiveProvider("no_active_provider"),
            "Nenhum provedor ativo. Configure em Configurações.",
        ),
        (
            CredentialRejected("unauthorized"),
            "O provedor recusou a chave. Confira em Configurações.",
        ),
        (
            CredentialRejected("unreadable_key"),
            "Chave ilegível. Informe a chave de novo em Configurações.",
        ),
        (ModelNotFound("model_not_found"), "Modelo não encontrado no provedor."),
        (ContextLimitExceeded("context_limit"), "A parte passou do limite de contexto do modelo."),
        (
            ProviderRateLimited("rate_limited"),
            "Limite de uso do provedor atingido. Tente mais tarde.",
        ),
        (ProviderUnreachable("timeout"), "Provedor inacessível."),
    ],
)
def test_error_carries_kind_reason_and_message(error: LLMError, message: str) -> None:
    """`llm-providers` 27: tipo e motivo, sem corpo."""
    assert error.message == message
    assert str(error) == f"{error.kind}: {error.reason}"


@respx.mock
@pytest.mark.parametrize(
    "mock",
    [
        {"side_effect": httpx.ConnectError(f"refused Bearer {API_KEY}")},
        {"return_value": httpx.Response(401, json={"error": f"bad key {API_KEY}"})},
    ],
)
def test_error_and_log_never_carry_body_headers_or_key(
    mock: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    """`llm-providers` 27; SEC-17."""
    respx.post(URL).mock(**mock)  # type: ignore[arg-type]
    caplog.set_level(logging.DEBUG)
    with pytest.raises(LLMError) as exc:
        response = _send()
        raise_for_status(response)
    error = exc.value
    assert error.__suppress_context__ or error.__context__ is None
    assert error.__cause__ is None
    for text in (str(error), repr(error), error.message, str(vars(error))):
        assert API_KEY not in text
        assert "Bearer" not in text
    logged = " ".join(str(vars(record)) for record in caplog.records)
    assert API_KEY not in logged


@respx.mock
def test_request_is_logged_without_body(caplog: pytest.LogCaptureFixture) -> None:
    """06-integrations: provedor, operação, status, duração, tipo de erro."""
    respx.post(URL).respond(200, json={"segredo": "texto da transcrição"})
    caplog.set_level(logging.INFO, logger="snook.llm")
    _send()
    (record,) = [r for r in caplog.records if r.name == "snook.llm"]
    assert record.getMessage() == "llm.request"
    assert record.provider == "openai"
    assert record.operation == "generate"
    assert record.status == 200
    assert isinstance(record.duration_ms, float)
    assert "texto da transcrição" not in str(vars(record))


@respx.mock
def test_failed_request_logs_error_type(caplog: pytest.LogCaptureFixture) -> None:
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("timed out"))
    caplog.set_level(logging.INFO, logger="snook.llm")
    with pytest.raises(ProviderUnreachable):
        _send()
    (record,) = [r for r in caplog.records if r.name == "snook.llm"]
    assert record.error_type == "ProviderUnreachable"
    assert record.reason == "timeout"
