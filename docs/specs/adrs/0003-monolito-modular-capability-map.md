# ADR-0003: Monólito modular com os 9 módulos do capability map

- Status: Aceita
- Data: 2026-10-22
- Fonte: Q18, Q52; `00-overview.md`, "Capability map" e "Build order".

## Contexto

Capability map aprovado define 9 módulos, dependências sem ciclo e avisos entre etapas do pipeline. Emissor de aviso não depende do consumidor.

## Decisão

- Um só backend (monólito modular). Cada módulo do map vira um pacote Python em `backend/src/snook/modules/<modulo>/`, nome em snake_case do id (`llm-providers` vira `llm_providers`).
- Cada módulo expõe interface pública num arquivo `service.py`. Outro módulo importa só essa interface, nunca `models.py` nem `repository.py` alheio.
- Imports seguem a coluna "Depende de" do map. Regra checada por `import-linter` no CI (ADR-0017).
- Avisos ("Reunião criada", "Nova tentativa", "Participantes confirmados", "Partes prontas") passam por barramento interno em `core/events.py` (ADR-0007).

## Consequências

- Um deploy, um banco, transação local entre módulos possível (ADR-0006).
- Quebra de fronteira vira erro de CI, não só de revisão.
- Microserviços ficam fora de escopo.
