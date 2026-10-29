"""Base dos adapters de LLM: contrato, erros tipados e cliente `httpx` comum (ADR-0012, SEC-17)."""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol

import httpx

from snook.modules.llm_providers import messages

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
CONNECT_TIMEOUT = 10.0
WRITE_TIMEOUT = 30.0
POOL_TIMEOUT = 10.0
TEST_CONNECTION_READ_TIMEOUT = 20.0

logger = logging.getLogger("snook.llm")


class LLMError(Exception):
    """Erro tipado do contrato. Leva só tipo e motivo curto: nunca corpo, header nem chave."""

    kind: ClassVar[str] = "llm_error"
    default_message: ClassVar[str] = messages.PROVIDER_UNREACHABLE
    reason_messages: ClassVar[dict[str, str]] = {}

    def __init__(self, reason: str) -> None:
        super().__init__(f"{self.kind}: {reason}")
        self.reason = reason

    @property
    def message(self) -> str:
        return self.reason_messages.get(self.reason, self.default_message)


class NoActiveProvider(LLMError):
    kind = "no_active_provider"
    default_message = messages.NO_ACTIVE_PROVIDER


class CredentialRejected(LLMError):
    kind = "credential_rejected"
    default_message = messages.CREDENTIAL_REJECTED
    reason_messages = {"unreadable_key": messages.KEY_UNREADABLE}


class ModelNotFound(LLMError):
    kind = "model_not_found"
    default_message = messages.MODEL_NOT_FOUND


class ContextLimitExceeded(LLMError):
    kind = "context_limit_exceeded"
    default_message = messages.CONTEXT_LIMIT_EXCEEDED


class ProviderRateLimited(LLMError):
    kind = "provider_rate_limited"
    default_message = messages.PROVIDER_RATE_LIMITED


class ProviderUnreachable(LLMError):
    kind = "provider_unreachable"
    default_message = messages.PROVIDER_UNREACHABLE
    reason_messages = {"redirect": messages.PROVIDER_REDIRECT}


@dataclass(frozen=True)
class ProviderTarget:
    """Configuração do provedor numa chamada. `api_key` fora do `repr`."""

    model: str
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    context_window: int | None = None


@dataclass(frozen=True)
class GenerationRequest:
    system_prompt: str
    content: str
    json_schema: dict[str, Any]
    max_output_tokens: int


class LLMAdapter(Protocol):
    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        """Texto da resposta (JSON). Validação do backlog fica com quem chama."""
        ...

    def test_connection(self, target: ProviderTarget) -> None:
        """Confere chave e modelo sem gerar texto. Falha vira `LLMError`."""
        ...

    def list_models(self, target: ProviderTarget) -> list[str]:
        """Ids dos modelos que a chave enxerga, ordenados. Falha vira `LLMError`."""
        ...


@dataclass(frozen=True)
class ProviderResponse:
    status_code: int
    body: bytes

    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except ValueError:
            raise ProviderUnreachable("invalid_response") from None

    def error_detail(self) -> tuple[str, str]:
        """(`code`, `message`) do corpo de erro, só para classificar. Nunca sai do adapter."""
        try:
            data = json.loads(self.body)
        except ValueError:
            return "", ""
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            return str(error.get("code") or ""), str(error.get("message") or "")
        if isinstance(error, str):
            return "", error
        return "", ""


def model_ids(data: Any, key: str, id_field: str) -> list[str]:
    """Ids de `data[key][*][id_field]`, únicos e ordenados. Formato inesperado falha."""
    items = data.get(key) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ProviderUnreachable("invalid_response")
    ids = {m[id_field] for m in items if isinstance(m, dict) and isinstance(m.get(id_field), str)}
    return sorted(ids)


def build_client(read_timeout: float) -> httpx.Client:
    return httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(
            connect=CONNECT_TIMEOUT, read=read_timeout, write=WRITE_TIMEOUT, pool=POOL_TIMEOUT
        ),
    )


def _read_capped(response: httpx.Response) -> bytes:
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        raise ProviderUnreachable("body_too_large")
    body = bytearray()
    # Conta depois de descomprimir: gzip pequeno não vira corpo gigante.
    for chunk in response.iter_bytes():
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProviderUnreachable("body_too_large")
    return bytes(body)


def _exchange(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None,
    json_body: Any,
    timeout: httpx.Timeout | None,
) -> ProviderResponse:
    try:
        extra: dict[str, Any] = {} if timeout is None else {"timeout": timeout}
        with client.stream(method, url, headers=headers, json=json_body, **extra) as response:
            if response.is_redirect or 300 <= response.status_code < 400:
                raise ProviderUnreachable("redirect")
            return ProviderResponse(response.status_code, _read_capped(response))
    # `from None`: a exceção do httpx leva o `request`, com o header da chave.
    except httpx.TimeoutException:
        raise ProviderUnreachable("timeout") from None
    except httpx.HTTPError:
        raise ProviderUnreachable("network") from None


def send(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    provider: str,
    operation: str,
    headers: dict[str, str] | None = None,
    json: Any = None,
    read_timeout: float | None = None,
) -> ProviderResponse:
    """Uma chamada ao provedor, sem retry. Falha de transporte, 3xx e corpo > 5 MB viram erro."""
    timeout = None
    if read_timeout is not None:
        timeout = httpx.Timeout(
            connect=CONNECT_TIMEOUT, read=read_timeout, write=WRITE_TIMEOUT, pool=POOL_TIMEOUT
        )
    started = time.perf_counter()
    status: int | None = None
    error: LLMError | None = None
    try:
        response = _exchange(client, method, url, headers=headers, json_body=json, timeout=timeout)
        status = response.status_code
        return response
    except LLMError as exc:
        error = exc
        raise
    finally:
        logger.info(
            "llm.request",
            extra={
                "provider": provider,
                "operation": operation,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "error_type": type(error).__name__ if error else None,
                "reason": error.reason if error else None,
            },
        )


def raise_for_status(
    response: ProviderResponse,
    *,
    classify: Callable[[ProviderResponse], LLMError | None] | None = None,
) -> None:
    """Mapa de erros de `06-integrations.md`. `classify` do adapter roda antes (4xx próprios)."""
    status = response.status_code
    if 200 <= status < 300:
        return
    if classify is not None:
        specific = classify(response)
        if specific is not None:
            raise specific
    if status in (401, 403):
        raise CredentialRejected("unauthorized")
    if status == 404:
        raise ModelNotFound("model_not_found")
    if status == 429:
        raise ProviderRateLimited("rate_limited")
    if status >= 500:
        raise ProviderUnreachable("server_error")
    # 4xx fora do contrato (ex.: 402 sem saldo): falha de chamada, motivo com o status.
    raise ProviderUnreachable(f"http_{status}")
