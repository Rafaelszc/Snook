# AGENTS.md: Snook

Instruções para agentes de código neste repo. Fonte de verdade: `docs/specs/`. Este arquivo resume; em conflito, vale o spec ou o ADR.

## Projeto

- Snook recebe gravação de reunião (upload ou gravação de tela), trata áudio, diariza e transcreve localmente em pt-BR.
- Usuário nomeia as vozes. LLM ativo do Usuário gera Epics e User Stories com solicitante, prioridade, story points e critérios de aceite.
- Transcrição longa: dividida em Partes no app. Backlog unificado na Reunião. Usuário revisa, edita, regenera e exporta.
- Provedores: OpenAI, Anthropic, DeepSeek, Ollama. Chave por Usuário, cifrada, nunca devolvida.
- Somente local: máquina do usuário ou rede confiável. Na rede, HTTPS pelo perfil `lan`.

## Estado

- Código implementado até a Task 51.1 (README de release). Fases 0 a 7 e Task 50 entregues.
- Pendente: Task 51.2 (checklist de segurança e auditorias), Fase 9 "Redesign Ata" (Tasks 52 a 61, ADR-0024) e, depois dela, Task 51.3 (auditoria WCAG, polimento e medições de NFR).
- Próximo: task-breaker detalha a Fase 9 em `tasks/todo.md`; depois implementar na ordem de `tasks/plan.md`.

## Mapa de docs

| Doc | Conteúdo |
|---|---|
| `docs/specs/00-overview.md` | Visão, escopo, glossário, capability map, decisões Q1 a Q74 |
| `docs/specs/01-prd.md` + `01-prd/<modulo>.md` | Requisitos, User Stories, critérios de aceite numerados, NFRs |
| `docs/specs/02-architecture.md` | Componentes, stack, pastas, fronteiras, fluxos, frontend e UI |
| `docs/specs/03-security.md` | SEC-01..27, OWASP Top 10:2025, ASVS 5.0 L2, LGPD, Always/Ask First/Never |
| `docs/specs/04-data-model.md` | Tabelas, estados, cascatas |
| `docs/specs/05-api.md` | Rotas `/api/...`, contrato de erro |
| `docs/specs/06-integrations.md` | Provedores de LLM, HuggingFace |
| `docs/specs/07-observability.md` | Logs JSON, redação |
| `docs/specs/08-deployment.md` | Compose, perfis `cpu`/`gpu`/`lan`, variáveis de ambiente |
| `docs/specs/adrs/0001..0024` | Decisões, todas Aceita (0022 e 0023 substituídos em parte pelo 0024) |
| `tasks/plan.md` | Fases 0 a 9 e auditoria final, checkpoints, riscos, skills por tarefa |

## Fluxo de trabalho

- Spec-Driven Development: spec → plano → tarefas → código. Sem código fora de tarefa do `tasks/todo.md`.
- Pipeline de agentes: `spec-writer` → `spec-reviewer` → `planner` → `spec-reviewer` → `task-breaker`.
- Mudança de comportamento: atualizar o spec antes do código. Decisão de arquitetura nova: ADR novo.
- TDD: teste falhando primeiro. Um teste por critério de aceite (`tests/<modulo>/test_api_*.py`).
- GitFlow: `main`, `develop`, `release/*`, `feature/*`.
  - `feature/*` → `develop`: PR com squash and merge.
  - `develop` → `release/*`: merge commit (`--no-ff`).
  - `release/*` → `main`: PR com merge commit. Nunca PR direto para `main`.
- PR ao término de cada task mãe (ex.: 5.1 a 5.4 = Task 5 = um PR), não por subtask. Antes: `git pull --rebase` de `develop`.
- Checkpoint: `/security-review` no diff; checkpoint com tela também tem checagem de UI (abaixo).
- Docs em `docs/specs/` e saídas do pipeline em voz caveman, com clareza.

## Stack

- Backend: Python 3.12, FastAPI, uvicorn 1 worker, Pydantic v2, SQLAlchemy 2 síncrono + Alembic, SQLite (WAL).
- Áudio: ffmpeg, faster-whisper `large-v3-turbo` int8, `pyannote.audio` `speaker-diarization-3.1`.
- LLM: `httpx` puro, sem redirecionamento, sem SDKs. Testes com `respx`.
- Segurança: `bcrypt` custo 12; AES-256-GCM (`cryptography`) com `SNOOK_MASTER_KEY`.
- Frontend: Vite, React, TypeScript, shadcn/ui, Tailwind, React Router, TanStack Query, `@tanstack/react-virtual`.
- Testes frontend: Vitest, React Testing Library, MSW, `vitest-axe`.
- Infra: Docker Compose, nginx (mesma origem), Caddy no perfil `lan`, GitHub Actions + `gitleaks`.

## Estrutura

```
backend/src/snook/{main.py, cli.py, core/, shared/prompts/, modules/<modulo>/}
backend/tests/<modulo>/
frontend/src/{app, styles, lib, components, features/<modulo>}
deploy/{nginx.conf, Caddyfile}
compose.yaml, .env.example
```

Detalhe em `02-architecture.md`, "Estrutura de pastas".

## Comandos

Da raiz:

```
cd backend && uv sync --frozen
cd backend && uv run pytest
cd backend && uv run pytest -m models_real    # opcional, modelos reais
cd backend && uv run pytest -m llm_real       # opcional, chaves reais
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run lint-imports
cd backend && uv run pip-audit
cd frontend && npm ci --ignore-scripts
cd frontend && npm test -- --run
cd frontend && npm run lint && npm run typecheck && npm run build
cd frontend && npm audit --omit=dev
docker compose up --build
```

## Regras de código

- Módulos: os 9 do capability map. Cada um expõe só `service.py` e, quando há rota, `api.py`; `models.py` e `repository.py` privados.
- Grafo de imports em `02-architecture.md`, "Fronteiras entre módulos", aplicado por `import-linter`. Nenhum módulo importa outro à direita na build order. `shared` não importa `modules`.
- Frontend: `features/<modulo>` importa só `lib/`, `components/`, `styles/`. Feature não importa feature. `components/` não importa `features/`, aplicado por ESLint (`no-restricted-imports` em `components/**` barra `@/features/*`, a partir da Task 52).
- Escrita entre módulos recebe `uow`; um commit por transação; aviso do EventBus só depois do commit.
- Erros: `AppError(code, message, http_status)`; corpo `{"error": {"code", "message", "fields"}}`.
- Nomes em inglês. Mensagens ao usuário em pt-BR, em `messages.py` de cada módulo.
- Tipos em toda função pública (`mypy --strict` nos módulos).
- Toda rota sob `/api`. `GET` nunca muda estado.
- Relógio injetável (`core/clock.py`).

## Segurança

Lista completa em `03-security.md`. Resumo:

- **Sempre:** validar entrada na borda; checar dono da Reunião (404 se não é dono); SQL só pelo ORM; subprocesso sem shell; teste de 401 e de isolamento por rota nova; tratar saída da LLM e Transcrição como não confiáveis.
- **Perguntar antes:** mudar auth, sessão ou senha; novo dado pessoal; nova integração ou provedor; dependência fora dos ADRs aceitos; mudar CORS, `ALLOWED_HOSTS`, `ALLOWED_ORIGINS`, `TRUSTED_PROXY_IPS`, CSP, HSTS ou limites padrão no código; expor porta do backend; mudar cifra; rodar `delete-user` ou rotação de chave em dados reais; mudar o texto do aviso de consentimento.
- **Nunca:** commitar `.env`, banco, áudio (exceto fixtures curtas, sintéticas ou geradas pelo gravador, sem voz de terceiros, só em `backend/tests/fixtures/audio/`), modelos, volume `caddy-data` ou segredo; logar senha, token, chave, `HF_TOKEN` ou texto da Transcrição; devolver chave, hash ou caminho interno; sessão em `localStorage` ou `sessionStorage`; `eval`, `dangerouslySetInnerHTML`, `shell=True`; seguir redirecionamento de provedor; stack trace ao usuário; áudio para fora do servidor; CLI de escrita com backend no ar; confiar em `X-Forwarded-*` fora de `TRUSTED_PROXY_IPS`.

## Frontend e UI

Direção "Ata" (ADR-0024, que substitui em parte o ADR-0022 e o item de fontes do ADR-0023): papel, tinta, linha fina, um acento `--signal` (petróleo); hierarquia por régua e espaço, card só no que flutua; animações suaves. Implementação na Fase 9 de `tasks/plan.md`.

- Tokens: só os de `styles/tokens.css` (ADR-0024). Nomes shadcn são apelidos dos tokens Ata (tabela "Apelidos"). `--accent` do shadcn é fundo de hover, não a cor de destaque.
- Migração (ADR-0024, Q1): Task 52 troca em todo o `src/` as classes de cor de token removido (`*-highlight*`, `*-status-*`) e os usos do `Button`. Raio, `text-[`, `transition-colors` e `ring-ring/50` saem na task de cada tela; teste estático global só no "Checkpoint: Redesign Ata".
- Forma: espaço 4, 8, 12, 16, 24, 32, 48, 64 e raio 4, 6, 10, também em `components/ui/*`; nada de `rounded-xl` ou acima; largura `--shell` ou `--reading`. Sombra só em diálogo, popover e painel de gravação.
- Card de login e cadastro: exceção, opaco, régua, sem sombra.
- Tipografia: Source Serif 4 no conteúdo (título, Epic, nome de US, fala), Geist nos controles, Geist Mono tabular em ids, instantes e tokens. Escala 12 a 40 px, no máximo três tamanhos por tela. Sem tamanho arbitrário (`text-[...]`).
- Foco: anel opaco de 2 px em `--ring`, sem alfa (`ring-ring/50` proibido).
- Movimento: 120 a 240 ms, só `transform` e `opacity`, CSS sem biblioteca de animação. Sem `transition-colors` nem `transition: all`.
- Vidro: só no painel flutuante da gravação, pelo `GlassPanel`, com fallback opaco (`@supports not`, `prefers-reduced-transparency`, `forced-colors`). Diálogos usam `DialogSurface` (opaco). `backdrop-filter` fora de `glass.css` é proibido. Texto sobre vidro com contraste 4,5:1.
- Mouse-tracking: só no realce da borda da área de upload, por `usePointerSpotlight` (`--pointer-x`, `--pointer-y`), em `--signal`, recortado por `mask-composite`; texto e fundo do miolo sem mudança. Liga só com `(hover: hover) and (pointer: fine)` e sem reduced-motion; atualiza CSS variables por `requestAnimationFrame`, sem re-render. Único gradiente permitido.
- Tema: `ThemeToggle` (claro, escuro, sistema) no `AppShell` e no auth; preferência em `localStorage`; sem atalho de tecla; `theme-color` do `index.html` igual a `--canvas`.
- Alertas: `Notice` para bloco ou página; erro de campo inline no `FormField`.
- `prefers-reduced-motion` desliga movimento, pulso, respiração do skeleton e mouse-tracking.
- WCAG 2.2 AA, teclado em tudo, `aria-live` em status, 360 a 1920 px.
- Fontes e ícones locais (CSP `default-src 'self'`).
- Orçamento (ADR-0023): JS inicial ≤200 KB gzip, total ≤500 KB, LCP ≤2,5 s, INP ≤200 ms, CLS ≤0,1, no máximo 3 vidros por tela (Ata usa 1), quadros com mouse-tracking ≤16 ms, listas longas virtualizadas (NFR-01 a NFR-08).
- Aviso de consentimento: `ConsentNotice`, só texto, no upload e antes de gravar (Q71). Texto literal numa constante única (`meetings` critério 52, Q72). Renderiza `Notice variant="consent"` sem mudar o texto; troca feita só na Task 52, com teste de igualdade.
- Skills de apoio por tarefa: tabela em `tasks/plan.md`, "Skills de frontend por tarefa". Carregar antes de implementar a tela.
- Checagem de UI em checkpoint com tela: `web-design-guidelines`, Vitest + `vitest-axe`, contraste claro/escuro, foco opaco, reduced-motion, sem listener em toque, orçamento.
