"""Adapter do Ollama: URL do Usuário, sem autenticação, sem redirecionamento (Q60, Q63)."""

from typing import Any, ClassVar
from urllib.parse import urlsplit

from snook.modules.llm_providers import messages
from snook.modules.llm_providers.adapters.base import (
    TEST_CONNECTION_READ_TIMEOUT,
    ContextLimitExceeded,
    GenerationRequest,
    LLMError,
    ModelNotFound,
    ProviderResponse,
    ProviderTarget,
    ProviderUnreachable,
    build_client,
    raise_for_status,
    send,
)

_SCHEMES = ("http", "https")
_CONTEXT_TEXT = "context length"
_MODEL_MISSING_TEXT = "not found"


class InvalidBaseUrl(ValueError):
    """URL recusada. Leva só o código; nunca a URL, que pode trazer senha."""

    _messages: ClassVar[dict[str, str]] = {
        "invalid_url_scheme": messages.INVALID_URL_SCHEME,
        "url_with_credentials": messages.URL_WITH_CREDENTIALS,
        "invalid_url": messages.INVALID_URL,
    }

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = self._messages[code]


def normalize_base_url(url: str) -> str:
    """Regras de `06-integrations.md`: esquema `http`/`https`, sem credenciais, host não vazio."""
    try:
        parts = urlsplit(url.strip())
        hostname = parts.hostname
    except ValueError:
        raise InvalidBaseUrl("invalid_url") from None
    if parts.scheme.lower() not in _SCHEMES:
        raise InvalidBaseUrl("invalid_url_scheme")
    # `@` no netloc já é credencial, mesmo com usuário ou senha vazios.
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise InvalidBaseUrl("url_with_credentials")
    if not hostname:
        raise InvalidBaseUrl("invalid_url")
    return url.strip().rstrip("/")


def _classify(response: ProviderResponse) -> LLMError | None:
    _, message = response.error_detail()
    text = message.lower()
    if _CONTEXT_TEXT in text:
        return ContextLimitExceeded("context_limit")
    # Ollama devolve 404 com "model ... not found"; outro 4xx com o mesmo texto também vale.
    if response.status_code < 500 and "model" in text and _MODEL_MISSING_TEXT in text:
        return ModelNotFound("model_not_found")
    return None


def _message_content(data: Any) -> str:
    message = data.get("message") if isinstance(data, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ProviderUnreachable("invalid_response")
    return content


class OllamaAdapter:
    provider = "ollama"

    def __init__(self, *, read_timeout: float) -> None:
        self._read_timeout = read_timeout

    def _base(self, target: ProviderTarget) -> str:
        # Revalida aqui: o adapter nunca chama URL que o salvar recusaria.
        if target.base_url is None:
            raise InvalidBaseUrl("invalid_url")
        return normalize_base_url(target.base_url)

    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        base = self._base(target)
        options: dict[str, int] = {"num_predict": request.max_output_tokens}
        if target.context_window is not None:
            options["num_ctx"] = target.context_window
        body = {
            "model": target.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.content},
            ],
            "stream": False,
            "format": request.json_schema,
            "options": options,
        }
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "POST",
                f"{base}/api/chat",
                provider=self.provider,
                operation="generate",
                json=body,
            )
        raise_for_status(response, classify=_classify)
        return _message_content(response.json())

    def test_connection(self, target: ProviderTarget) -> None:
        base = self._base(target)
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "POST",
                f"{base}/api/show",
                provider=self.provider,
                operation="test_connection",
                json={"model": target.model},
                read_timeout=TEST_CONNECTION_READ_TIMEOUT,
            )
        raise_for_status(response, classify=_classify)
