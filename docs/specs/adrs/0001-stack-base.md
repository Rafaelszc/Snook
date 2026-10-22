# ADR-0001: Stack base

- Status: Aceita
- Data: 2026-10-22
- Fonte: briefing do usuário (2026-10-21); `00-overview.md`, "Restrições > Stack".

## Contexto

Briefing fixa linguagem, frameworks, banco, orquestração e testes. Plano não reabre essas escolhas.

## Decisão

- Backend em Python, rotas HTTP com FastAPI.
- Persistência em SQLite.
- Frontend em React + TypeScript + shadcn/ui.
- Orquestração com Docker (`docker compose`).
- Testes de unidade do backend com Pytest.
- Fluxo: GitFlow (`main`, `develop`, `feature/*`), Spec-Driven Development, TDD.

## Consequências

- SQLite aceita um escritor por vez. Arquitetura concentra escritas num só processo (ver ADR-0007).
- Escolhas finas (ORM, bundler, framework de teste do frontend) ficam em ADRs próprios: 0006, 0015, 0017.
