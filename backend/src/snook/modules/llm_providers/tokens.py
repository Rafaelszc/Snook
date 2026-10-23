"""Estimativa de tokens: heurística aditiva por linha (ADR-0011)."""

import math

# Ajuste do spike (Task 2) muda só esta tabela e fica registrado no ADR-0011.
CHARS_PER_TOKEN = {
    "openai": 3.0,
    "anthropic": 3.0,
    "deepseek": 3.0,
    "ollama": 3.0,
}


def estimate_tokens(provider: str, model: str, text: str) -> int:
    """`ceil(len(linha) / chars_per_token) + 1` por linha; texto = soma das linhas.

    `model` fica na assinatura para um tokenizador real futuro; a heurística não o usa.
    """
    chars_per_token = CHARS_PER_TOKEN[provider]
    return sum(math.ceil(len(line) / chars_per_token) + 1 for line in text.splitlines())
