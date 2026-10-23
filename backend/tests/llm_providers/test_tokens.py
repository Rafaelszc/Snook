"""Estimar tokens: `llm-providers` 32; ADR-0011 (Task 16.2)."""

import pytest

from snook.modules.llm_providers import service, tokens

PROVIDERS = ("openai", "anthropic", "deepseek", "ollama")
LINE = "Ana: precisamos de login com e-mail e senha."
TEXT = f"{LINE}\nBia: e recuperação de senha também."


@pytest.mark.parametrize("provider", PROVIDERS)
def test_positive_int_for_non_empty_text(provider: str) -> None:
    """`llm-providers` 32."""
    for text in ("a", " ", LINE, TEXT):
        estimate = service.estimate_tokens(provider, "modelo", text)
        assert isinstance(estimate, int)
        assert estimate > 0


def test_empty_text_is_zero() -> None:
    assert service.estimate_tokens("openai", "gpt-5-mini", "") == 0


@pytest.mark.parametrize("provider", PROVIDERS)
def test_containing_text_estimates_more(provider: str) -> None:
    """`llm-providers` 32."""
    assert service.estimate_tokens(provider, "m", TEXT) > service.estimate_tokens(
        provider, "m", LINE
    )
    assert service.estimate_tokens(provider, "m", LINE + " extra") > service.estimate_tokens(
        provider, "m", LINE
    )


def test_sum_by_line_is_additive() -> None:
    """Parte = soma dos segmentos; cliente soma e bate com o servidor (ADR-0011)."""
    lines = [LINE, "Bia: ok.", "Caio: fechado, até amanhã."]
    whole = service.estimate_tokens("anthropic", "m", "\n".join(lines))
    assert whole == sum(service.estimate_tokens("anthropic", "m", line) for line in lines)


def test_line_formula_uses_ceil_plus_one() -> None:
    """`ceil(len(linha) / 3.0) + 1` por linha (ADR-0011)."""
    assert service.estimate_tokens("openai", "m", "abc") == 2
    assert service.estimate_tokens("openai", "m", "abcd") == 3
    assert service.estimate_tokens("openai", "m", "abcd\nab") == 5


def test_chars_per_token_comes_from_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ajuste do spike (Task 2) muda só a tabela de `tokens.py`."""
    assert dict.fromkeys(PROVIDERS, 3.0) == tokens.CHARS_PER_TOKEN
    monkeypatch.setitem(tokens.CHARS_PER_TOKEN, "ollama", 6.0)
    assert service.estimate_tokens("ollama", "m", "a" * 12) == 3
    assert service.estimate_tokens("openai", "m", "a" * 12) == 5
