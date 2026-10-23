"""Adapter da Anthropic: URL fixa, saída JSON por ferramenta forçada (ADR-0012)."""

import json
from typing import Any
from urllib.parse import quote

from snook.modules.llm_providers.adapters.base import (
    TEST_CONNECTION_READ_TIMEOUT,
    ContextLimitExceeded,
    GenerationRequest,
    LLMError,
    ProviderResponse,
    ProviderTarget,
    ProviderUnreachable,
    build_client,
    model_ids,
    raise_for_status,
    send,
)

BASE_URL = "https://api.anthropic.com/v1"
API_VERSION = "2023-06-01"
TOOL_NAME = "submit_backlog"
_TOOL_DESCRIPTION = "Entrega o backlog extraído da transcrição."
_CONTEXT_TEXT = "prompt is too long"


def _classify(response: ProviderResponse) -> LLMError | None:
    if response.status_code != 400:
        return None
    _, message = response.error_detail()
    if _CONTEXT_TEXT in message.lower():
        return ContextLimitExceeded("context_limit")
    return None


def _tool_input(data: Any) -> str:
    blocks = data.get("content") if isinstance(data, dict) else None
    for block in blocks if isinstance(blocks, list) else []:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == TOOL_NAME
            and isinstance(block.get("input"), dict)
        ):
            return json.dumps(block["input"], ensure_ascii=False)
    raise ProviderUnreachable("invalid_response")


class AnthropicAdapter:
    provider = "anthropic"

    def __init__(self, *, read_timeout: float) -> None:
        self._read_timeout = read_timeout

    def _headers(self, target: ProviderTarget) -> dict[str, str]:
        return {"x-api-key": target.api_key or "", "anthropic-version": API_VERSION}

    def generate(self, target: ProviderTarget, request: GenerationRequest) -> str:
        body = {
            "model": target.model,
            "max_tokens": request.max_output_tokens,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.content}],
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": _TOOL_DESCRIPTION,
                    "input_schema": request.json_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        }
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "POST",
                f"{BASE_URL}/messages",
                provider=self.provider,
                operation="generate",
                headers=self._headers(target),
                json=body,
            )
        raise_for_status(response, classify=_classify)
        return _tool_input(response.json())

    def test_connection(self, target: ProviderTarget) -> None:
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "GET",
                f"{BASE_URL}/models/{quote(target.model, safe='')}",
                provider=self.provider,
                operation="test_connection",
                headers=self._headers(target),
                read_timeout=TEST_CONNECTION_READ_TIMEOUT,
            )
        raise_for_status(response)

    def list_models(self, target: ProviderTarget) -> list[str]:
        with build_client(self._read_timeout) as client:
            response = send(
                client,
                "GET",
                f"{BASE_URL}/models?limit=1000",
                provider=self.provider,
                operation="list_models",
                headers=self._headers(target),
                read_timeout=TEST_CONNECTION_READ_TIMEOUT,
            )
        raise_for_status(response)
        return model_ids(response.json(), "data", "id")
