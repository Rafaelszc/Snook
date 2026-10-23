"""Adapter de OpenAI e DeepSeek: mesma API de chat, URL fixa e campos por provedor (ADR-0012)."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

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
    model_ids,
    raise_for_status,
    send,
)

_CONTEXT_CODE = "context_length_exceeded"
_CONTEXT_TEXT = "maximum context length"
_MODEL_MISSING_TEXT = "model not exist"


@dataclass(frozen=True)
class _Flavor:
    base_url: str
    max_tokens_field: str
    # OpenAI lê o modelo direto; DeepSeek só tem a lista.
    lists_models: bool


_FLAVORS = {
    "openai": _Flavor("https://api.openai.com/v1", "max_completion_tokens", lists_models=False),
    "deepseek": _Flavor("https://api.deepseek.com", "max_tokens", lists_models=True),
}


def _classify(response: ProviderResponse) -> LLMError | None:
    if response.status_code != 400:
        return None
    code, message = response.error_detail()
    text = message.lower()
    if code == _CONTEXT_CODE or _CONTEXT_TEXT in text:
        return ContextLimitExceeded("context_limit")
    # DeepSeek responde 400 "Model Not Exist" em vez de 404.
    if _MODEL_MISSING_TEXT in text:
        return ModelNotFound("model_not_found")
    return None


def _message_content(data: Any) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ProviderUnreachable("invalid_response") from None
    if not isinstance(content, str):
        raise ProviderUnreachable("invalid_response")
    return content


class OpenAICompatAdapter:
    def __init__(self, provider: str, *, read_timeout: float) -> None:
        if provider not in _FLAVORS:
            raise ValueError(f"provedor sem API compatível com OpenAI: {provider}")
        self._provider = provider
        self._flavor = _FLAVORS[provider]
        self._read_timeout = read_timeout

    def _headers(self, target: ProviderTarget) -> dict[str, str]:
        return {"Authorization": f"Bearer {target.api_key or ''}"}

    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        # `json_object` não recebe schema: o formato vem no system prompt.
        body = {
            "model": target.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.content},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            self._flavor.max_tokens_field: request.max_output_tokens,
        }
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "POST",
                f"{self._flavor.base_url}/chat/completions",
                provider=self._provider,
                operation="generate",
                headers=self._headers(target),
                json=body,
            )
        raise_for_status(response, classify=_classify)
        return _message_content(response.json())

    def test_connection(self, target: ProviderTarget) -> None:
        path = "/models" if self._flavor.lists_models else f"/models/{quote(target.model, safe='')}"
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "GET",
                f"{self._flavor.base_url}{path}",
                provider=self._provider,
                operation="test_connection",
                headers=self._headers(target),
                read_timeout=TEST_CONNECTION_READ_TIMEOUT,
            )
        raise_for_status(response, classify=_classify)
        if not self._flavor.lists_models:
            return
        data = response.json()
        models = data.get("data") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise ProviderUnreachable("invalid_response")
        if not any(isinstance(m, dict) and m.get("id") == target.model for m in models):
            raise ModelNotFound("model_not_found")

    def list_models(self, target: ProviderTarget) -> list[str]:
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "GET",
                f"{self._flavor.base_url}/models",
                provider=self._provider,
                operation="list_models",
                headers=self._headers(target),
                read_timeout=TEST_CONNECTION_READ_TIMEOUT,
            )
        raise_for_status(response, classify=_classify)
        return model_ids(response.json(), "data", "id")
