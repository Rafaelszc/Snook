# ADR-0017: Ferramentas de build, qualidade e CI

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q12 da rodada de decisões do planner: `uv`, `ruff`, `mypy`, `import-linter`, `pip-audit` no backend; `npm --ignore-scripts`, ESLint, `npm audit` no frontend; GitHub Actions com `gitleaks`. Recomendação aceita sem mudança.

## Contexto

- Spec deixava aberto: comandos, estrutura de pastas, estilo de código e CI. Resolvido por este ADR.
- Repositório remoto no GitHub (`https://github.com/Rafaelszc/Snook`).
- Supply chain: lockfile commitado, auditoria antes de release, scripts de dependência bloqueados.

## Opções consideradas

1. **Backend: `uv` + `uv.lock`, `ruff` (lint e formato), `mypy --strict` nos módulos, `import-linter`, `pip-audit`. Frontend: `npm` + `package-lock.json`, ESLint, Prettier, `tsc --noEmit`, `npm audit`. CI: GitHub Actions.**
   - Prós: `uv` rápido e com lock reprodutível; `npm` já vem com Node; Actions nativo do remoto.
   - Contras: duas toolchains.
2. **Poetry + pnpm.**
   - Prós: maduros.
   - Contras: Poetry mais lento; pnpm é ferramenta a mais.
3. **pip + requirements.txt sem lock de hashes.**
   - Contras: build não reprodutível.

## Decisão

Opção 1.

- Comandos (a partir da raiz):
  - `cd backend && uv sync --frozen`
  - `cd backend && uv run pytest`
  - `cd backend && uv run pytest -m models_real` (suíte opcional, modelos reais)
  - `cd backend && uv run pytest -m llm_real` (suíte opcional, chaves reais)
  - `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run lint-imports`
  - `cd backend && uv run pip-audit`
  - `cd frontend && npm ci --ignore-scripts`
  - `cd frontend && npm test -- --run`
  - `cd frontend && npm run lint && npm run typecheck && npm run build`
  - `cd frontend && npm audit --omit=dev`
  - `docker compose up --build`
- `.npmrc` com `ignore-scripts=true`. Script liberado só com aprovação registrada no README.
- CI (`.github/workflows/ci.yml`) em PR para `develop` e `main`: jobs backend e frontend com os comandos acima, sem as suítes opcionais. Job `secrets` com `gitleaks`. Build das imagens Docker sem push.
- Estilo Python: tipos em todas as funções públicas, nomes em inglês, mensagens ao usuário em pt-BR em `messages.py` de cada módulo.

## Consequências

- Versão do `uv` e do Node fixadas (`.python-version`, `.nvmrc`, `packageManager` no `package.json`).
- Dependência nova fora das aprovadas nos ADRs aceitos passa por "Ask First" do 03-security.
