"""System Prompt e schema da resposta do backlog (ADR-0020). Não importa `modules`.

O schema é o contrato estrito enviado ao provedor (ADR-0012). Leitura tolerante da resposta
(prioridade sem diferenciar maiúsculas, solicitante desconhecido) fica em `backlog_generation`.
"""

import json
from functools import cache
from importlib.resources import files
from typing import Any

# Sobe junto com o texto do prompt; o snapshot em `tests/shared/test_prompts.py` cobra.
BACKLOG_PROMPT_VERSION = "1"


@cache
def load_backlog_system_prompt() -> str:
    return files(__package__).joinpath("backlog_system_prompt.md").read_text(encoding="utf-8")


def load_backlog_response_schema() -> dict[str, Any]:
    """Cópia nova a cada chamada: quem altera o dict não afeta os outros."""
    raw = files(__package__).joinpath("backlog_response.schema.json").read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(raw)
    return schema
