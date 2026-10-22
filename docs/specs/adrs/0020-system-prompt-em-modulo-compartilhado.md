# ADR-0020: System Prompt num módulo compartilhado abaixo da cadeia

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q15 da rodada de decisões do planner: prompts em `shared/prompts/`. Recomendação aceita sem mudança.

## Contexto

- System Prompt é fixo e versionado no código (Q16). Dono do uso: `backlog-generation`.
- `transcript-split` precisa do tamanho do System Prompt para a reserva do orçamento (ADR-0011).
- `transcript-split` vem antes de `backlog-generation` na cadeia. Importar de `backlog-generation` criaria ciclo.

## Opções consideradas

1. **Arquivo `backend/src/snook/shared/prompts/backlog_system_prompt.md` e leitor `shared/prompts/__init__.py` (`load_backlog_system_prompt()`, `BACKLOG_PROMPT_VERSION`). `shared` não importa nenhum módulo.**
   - Prós: sem ciclo; um só texto; snapshot testável.
   - Contras: pacote `shared` a vigiar para não virar depósito.
2. **Prompt em `backlog-generation`; `transcript-split` usa reserva fixa de tokens para o prompt.**
   - Prós: dono único.
   - Contras: reserva fica errada quando o prompt muda; risco de passar do orçamento.
3. **`backlog-generation` registra o tamanho do prompt em `llm-providers` no startup.**
   - Contras: dependência implícita por registro; ordem de inicialização frágil.

## Decisão

Opção 1. Schema JSON da resposta (`backlog_response.schema.json`) mora no mesmo pacote, porque Anthropic e Ollama o recebem na chamada (ADR-0012) e `backlog-generation` o usa na validação.

## Consequências

- `import-linter`: `shared` não importa `modules`.
- Teste de snapshot do prompt (critério 31 de `backlog-generation`) fica em `tests/backlog_generation/`.
