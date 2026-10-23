"""Modelos e janelas de contexto padrão por provedor (ADR-0013)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDefaults:
    model: str
    context_window: int


DEFAULTS = {
    "openai": ProviderDefaults("gpt-5-mini", 400000),
    "anthropic": ProviderDefaults("claude-sonnet-4-5", 200000),
    "deepseek": ProviderDefaults("deepseek-chat", 128000),
    "ollama": ProviderDefaults("llama3.1:8b", 8192),
}

OLLAMA_DEFAULT_BASE_URL = "http://host.docker.internal:11434"
