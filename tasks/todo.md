# Todo: Snook

> Status: task-breaker, 2026-10-22; atualizado em 2026-10-28 com a Fase 9 "Redesign Ata" (ADR-0024). Fonte: `tasks/plan.md` (aprovado), `docs/specs/` (aceitas) e ADRs 0001 a 0024 (todas Aceita).
> Escopo: projeto inteiro, Fases 0 a 9, 9 módulos. Sem id de módulo único.
> Fases 0 a 9 implementadas (tarefas `[x]`). Pendentes: Task 51.2, checkpoints da Fase 9 e Task 51.3.
> Sem issue tracker designado em `AGENTS.md` ou `CLAUDE.md`. Tarefas vivem só neste arquivo.

## Como ler

- "Task N" do plano que pedia quebra virou "Task N.1", "Task N.2"... Task do plano que cabe em S ou M ficou inteira. "Task 6b" é a do plano (perfil `lan`), não subtarefa.
- Ordem = ordem do plano. Checkpoints = checkpoints do plano, com os mesmos itens.
- Critério citado como "`modulo` N" = critério N de `docs/specs/01-prd/<modulo>.md`. "transversal N" = critério N de `docs/specs/01-prd.md`. "SEC-NN" = `docs/specs/03-security.md`.
- Rotas sem prefixo `/api` nos critérios; no código, toda rota fica sob `/api`.

## Convenções (valem para toda tarefa)

- **GitFlow:** uma branch `feature/<slug>` por tarefa, a partir de `develop`. PR para `develop`. Commit curto e imperativo.
- **TDD:** escrever o teste do critério e vê-lo falhar antes do código. Um teste por critério de aceite, em `backend/tests/<modulo>/test_api_*.py` ou em `*.test.tsx` ao lado da tela.
- **Rota nova:** teste de 401 sem sessão e teste de 404 com `id` de outro Usuário (SEC-01, SEC-02). Rota que escreve: teste de 403 sem `Origin` válido (SEC-04). Rota que recebe corpo: teste de 422 com campo extra (SEC-09).
- **Migração:** uma revisão Alembic `NNNN_<modulo>_<mudanca>.py` por tarefa que muda schema, na ordem de `04-data-model.md`, "Migrações". Revisão humana no PR (SEC-22).
- **Mensagem ao usuário** em pt-BR, em `messages.py` do módulo. Código e nomes em inglês.
- **Gate backend** = `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run lint-imports`.
- **Gate frontend** = `cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build`.
- **Teste backend completo** = `cd backend && uv run pytest`. Teste focado = `cd backend && uv run pytest tests/<modulo> -q`.
- **Teste frontend focado** = `cd frontend && npm test -- --run src/features/<modulo>`.
- **Checagem de UI** (checkpoint com tela; direção Ata, ADR-0024): `web-design-guidelines` sobre o diff; Vitest + `vitest-axe` sem violação; contraste AA em tema claro e escuro (sobre vidro só no painel da gravação, com fallback opaco conferido); anel de foco opaco de 2 px, sem alfa; `prefers-reduced-motion` desliga movimento e mouse-tracking; nenhum listener de `pointermove` com `pointer: coarse`; orçamento do ADR-0023.
- **Frontend:** carregar as skills da tarefa antes de implementar a tela. Restrições do ADR-0022 que seguem valendo, as do ADR-0024 (direção Ata, que substitui em parte o ADR-0022) e as do ADR-0023 valem em toda tarefa de tela.
- **Pergunte antes** (AGENTS.md): mudar auth, sessão ou senha; novo dado pessoal; dependência fora dos ADRs; CORS, `ALLOWED_HOSTS`, `ALLOWED_ORIGINS`, `TRUSTED_PROXY_IPS`, CSP, HSTS ou limites padrão no código; cifra; texto do aviso de consentimento. As tarefas abaixo já implementam o que os ADRs aceitos mandam; qualquer desvio para e pergunta.

---

## Phase 0: Fundação, risco técnico e design system

### Task 1: Spike: medir faster-whisper e Pyannote em CPU

**Description:** Script descartável mede tempo e pico de RAM de faster-whisper `large-v3-turbo` int8 e de `pyannote/speaker-diarization-3.1` em CPU com 10 min de áudio pt-BR, e registra os números. Valida o fluxo com `HF_TOKEN`.

**Acceptance criteria:**
- [ ] O script imprime tempo de parede e pico de RAM de cada engine para o áudio de 10 min (risco "CPU lenta" do plano; ADR-0014).
- [ ] Os números, a CPU e a RAM da máquina ficam no `README.md`, seção "Desempenho medido", sem meta de tempo (`02-architecture.md`, "Questões em aberto" 1).
- [ ] A mensagem real do Pyannote sem aceite dos termos ou com `HF_TOKEN` inválido fica anotada no README, para o critério 15 de `diarized-transcription`.

**Verification:**
- [ ] Manual: `uv run --no-project --with faster-whisper --with pyannote.audio python backend/spikes/bench_audio.py <audio-10min.wav>` imprime os dois resultados.
- [ ] `git status` não mostra áudio nem `.env` (SEC-08; áudio fica fora do git).

**Dependencies:** None

**Files likely touched:**
- `backend/spikes/bench_audio.py`
- `README.md`

**Estimated scope:** Small

### Task 2: Spike: backlog de Transcrição de fixture nos quatro provedores

**Description:** Script descartável envia uma Transcrição sintética ao schema proposto em OpenAI, Anthropic, DeepSeek e Ollama (`httpx` puro), valida a saída e compara a heurística de tokens com a contagem real do provedor.

**Acceptance criteria:**
- [ ] A saída de cada provedor é validada contra o schema de `backlog-generation` ("Schema da resposta da LLM"), com taxa de acerto registrada por provedor (risco "saída fora do schema").
- [ ] A razão caracteres por token medida é comparada com `chars_per_token` 3.0 do ADR-0011; se erra para cima demais, a proposta de ajuste vai ao README.
- [ ] A fixture de Transcrição é sintética: sem nome real nem dado pessoal (LGPD, `03-security.md`).

**Verification:**
- [ ] Manual, com chaves em variáveis de ambiente (nunca em arquivo): `uv run --no-project --with httpx --with jsonschema python backend/spikes/llm_backlog_schema.py`.
- [ ] Nenhuma chave aparece na saída do script nem em arquivo versionado (SEC-07, SEC-08): `git grep -n "sk-"` sem achado.

**Dependencies:** None

**Files likely touched:**
- `backend/spikes/llm_backlog_schema.py`
- `backend/spikes/fixtures/transcript_sample.txt`
- `README.md`

**Estimated scope:** Small

### Task 3.1: Projeto Python, settings e relógio

**Description:** Cria o projeto `backend/` com `uv`, ruff, mypy `--strict`, pytest e `import-linter` (contratos de `core`, `shared`, `cli`/`main`), mais `Settings` e o relógio injetável.

**Acceptance criteria:**
- [x] O backend não sobe sem `SNOOK_MASTER_KEY` válida e a mensagem de erro não mostra o valor (SEC-08).
- [x] `Settings` traz os padrões de `08-deployment.md`, "Variáveis de ambiente", e `BCRYPT_ROUNDS` vem de configuração.
- [x] `core/clock.py` expõe um relógio que o teste troca por um falso.

**Verification:**
- [x] Testes: `cd backend && uv run pytest tests/core/test_settings.py -q` (startup sem chave, com chave inválida, padrões, relógio falso).
- [x] Gate backend, com `lint-imports` provando que `shared` não importa `modules`.
- [x] `cd backend && uv sync --frozen` funciona depois do `uv.lock` gerado.

**Dependencies:** None

**Files likely touched:**
- `backend/pyproject.toml`, `backend/.python-version`
- `backend/src/snook/core/settings.py`, `backend/src/snook/core/clock.py`
- `backend/tests/core/test_settings.py`

**Estimated scope:** Medium

### Task 3.2: Erros, fábrica da app e `/api/health`

**Description:** `AppError`, corpo de erro padrão, handler genérico de 500, `create_app()` e `GET /api/health`, mais `conftest.py` com app de teste.

**Acceptance criteria:**
- [x] `GET /api/health` responde 200 `{"status":"ok"}` sem sessão (`01-prd.md` RT-03; transversal 10).
- [x] `AppError(code, message, http_status)` vira `{"error": {"code", "message", "fields"}}` (`05-api.md`, "Erros").
- [x] Exceção não tratada responde 500 `{"error":{"code":"internal_error","message":"erro interno"}}` sem stack trace (SEC-19).

**Verification:**
- [x] Testes: `cd backend && uv run pytest tests/core/test_errors_health.py -q`.
- [x] Gate backend.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/core/errors.py`, `backend/src/snook/main.py`
- `backend/tests/conftest.py`, `backend/tests/core/test_errors_health.py`

**Estimated scope:** Small

### Task 3.3: Banco, unidade de trabalho e Alembic

**Description:** Engine SQLite (WAL, FK ligadas, `busy_timeout`), `UnitOfWork` com `publish_after_commit` e Alembic configurado (ADR-0006).

**Acceptance criteria:**
- [x] Toda conexão sai com `foreign_keys=ON`, `journal_mode=WAL` e `busy_timeout` (`04-data-model.md`, "Convenções").
- [x] Um commit por transação; aviso registrado em `publish_after_commit` só sai depois do commit, e nunca em rollback (`03-security.md`, "Always").
- [x] `alembic upgrade head` roda num banco temporário vazio.

**Verification:**
- [x] Testes: `cd backend && uv run pytest tests/core/test_db_uow.py -q`.
- [x] Gate backend.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/core/db.py`, `backend/src/snook/core/uow.py`
- `backend/alembic.ini`, `backend/alembic/env.py`
- `backend/tests/core/test_db_uow.py`

**Estimated scope:** Medium

### Task 3.4: Barramento de avisos e trava `/data/snook.lock`

**Description:** `EventBus` em memória com tipos de aviso com `run_id`, e `core/runlock.py` com `fcntl.flock` (ADR-0006, ADR-0007).

**Acceptance criteria:**
- [x] Todo aviso leva `meeting_id` e `run_id`; o barramento entrega ao consumidor registrado, e o consumidor pode ignorar `run_id` que não bate.
- [x] Um segundo processo que tenta pegar a trava falha com erro claro (`03-security.md`, "Always": pegar a trava antes de escrever).
- [x] A trava é liberada quando o processo morre.

**Verification:**
- [x] Testes: `cd backend && uv run pytest tests/core/test_events.py tests/core/test_runlock.py -q` (o de trava usa um subprocesso real e mata o dono).
- [x] Gate backend.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/core/events.py`, `backend/src/snook/core/runlock.py`
- `backend/tests/core/test_events.py`, `backend/tests/core/test_runlock.py`

**Estimated scope:** Small

### Task 3.5: Sequência de subida (lifespan)

**Description:** `lifespan` em `main.py` executa a sequência de `02-architecture.md`, "Retry e reinício": trava, backup e `alembic upgrade head`, limpeza de `/audios/.tmp/`. Ganchos para "marcar interrompidas" e "reenfileirar" ficam vazios até a Task 21.2.

**Acceptance criteria:**
- [x] A app pega `/data/snook.lock` na subida; uma segunda app sobre o mesmo caminho falha (SEC-24, A06).
- [x] Antes de migrar, existe `snook.db.bak-<rev>`; fica só o último backup depois de migração bem-sucedida (SEC-22; `03-security.md`, "Backups").
- [x] `/audios/.tmp/` é esvaziado na subida.

**Verification:**
- [x] Testes: `cd backend && uv run pytest tests/core/test_lifespan.py -q`.
- [x] Gate backend.

**Dependencies:** Tasks 3.3, 3.4

**Files likely touched:**
- `backend/src/snook/main.py`, `backend/src/snook/core/db.py`
- `backend/tests/core/test_lifespan.py`

**Estimated scope:** Small

### Checkpoint: Spikes e backend base

- [ ] `cd backend && uv run pytest` passa
- [ ] Teste da trava: segundo processo que tenta pegar `/data/snook.lock` falha; trava liberada quando o processo morre
- [ ] Resultado dos spikes registrado; ADR-0010, 0011, 0013 e 0014 ajustados se os números pedirem (ajuste de ADR aceito passa pelo usuário)
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Task 4.1: Frontend: Vite, TypeScript, Tailwind e shadcn/ui

**Description:** Cria `frontend/` com Vite, React, TypeScript estrito, Tailwind, shadcn/ui inicializado e ESLint com `react/no-danger`.

**Acceptance criteria:**
- [x] `npm ci --ignore-scripts` instala só do lockfile; `.nvmrc` e `.npmrc` fixam a versão do Node e bloqueiam script de instalação (SEC-21).
- [x] `npm run lint`, `npm run typecheck` e `npm run build` passam numa página inicial vazia.
- [x] ESLint falha em `dangerouslySetInnerHTML` (SEC-12; teste com arquivo de amostra).

**Verification:**
- [x] `cd frontend && npm ci --ignore-scripts && npm run lint && npm run typecheck && npm run build`.
- [x] Manual: `grep -R "dangerouslySetInnerHTML" frontend/src` sem achado.

**Dependencies:** None

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`
- `frontend/eslint.config.js`, `frontend/.nvmrc`, `frontend/.npmrc`, `frontend/components.json`

**Estimated scope:** Medium

### Task 4.2: Frontend: Vitest, RTL, MSW e `vitest-axe`

**Description:** Configura Vitest com jsdom, React Testing Library, MSW e `vitest-axe`, mais utilitário de render com providers.

**Acceptance criteria:**
- [x] Um teste de exemplo renderiza um componente, mocka uma rota com MSW e passa `vitest-axe` sem violação (ADR-0015).
- [x] `npm test -- --run` roda sem rede.
- [x] O polling padrão lê `VITE_POLL_INTERVAL_MS` com padrão 3000 (`05-api.md`, "Polling").

**Verification:**
- [x] `cd frontend && npm test -- --run`.
- [x] Gate frontend.

**Dependencies:** Task 4.1

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`, `frontend/src/test/render.tsx`
- `frontend/src/test/example.test.tsx`

**Estimated scope:** Small

### Task 4.3: Frontend: rotas, layout e cliente da API

**Description:** React Router, TanStack Query, layout base e `lib/api/` (cliente `fetch` com `credentials: "same-origin"`, tipos, erro tipado a partir do contrato de `05-api.md`).

**Acceptance criteria:**
- [x] O cliente converte `{"error":{"code","message","fields"}}` em erro tipado que a tela lê.
- [x] O cliente nunca guarda token em `localStorage` nem em `sessionStorage` (`03-security.md`, "Never"; teste com spy no `Storage`).
- [x] Rotas placeholder navegam e o `ConsentNotice` ainda não existe (vem na Task 22.1).

**Verification:**
- [x] `cd frontend && npm test -- --run src/lib`.
- [x] Gate frontend.

**Dependencies:** Task 4.2

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/app/routes.tsx`, `frontend/src/app/Layout.tsx`
- `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/errors.ts`, `frontend/src/lib/api/client.test.ts`

**Estimated scope:** Medium

### Task 5.1: Design system: tokens, tipografia local e movimento

**Description:** `tokens.css` (cores neutras com uma cor de destaque, tema claro e escuro, escala 12 a 40 px, raio, sombra), fonte variável local em `public/fonts/`, `motion.css` (120 a 240 ms, só `transform` e `opacity`).

**Acceptance criteria:**
- [x] Os tokens vêm de CSS variables e o Tailwind os lê; a fonte é local, sem requisição externa (CSP `default-src 'self'`, SEC-13).
- [x] Texto normal em tema claro e escuro tem contraste mínimo de 4,5:1, conferido por teste que calcula a razão dos tokens (ADR-0022).
- [x] Nenhuma transição de `motion.css` anima outra propriedade além de `transform` e `opacity`, e `prefers-reduced-motion: reduce` as desliga (teste que lê o CSS).

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles`.
- [x] Gate frontend.

**Dependencies:** Task 4.1

**Skills:** `minimalist-ui`, `high-end-visual-design`, `design-taste-frontend`, `frontend-design`, `frontend-ui-engineering`, `responsive-design`, `shadcn`

**Files likely touched:**
- `frontend/src/styles/tokens.css`, `frontend/src/styles/motion.css`, `frontend/public/fonts/*`
- `frontend/src/styles/tokens.test.ts`, `frontend/tailwind.config.ts`

**Estimated scope:** Medium

### Task 5.2: `GlassPanel` com fallback opaco

**Description:** Componente único `GlassPanel` e `glass.css`. É o único lugar com `backdrop-filter`.

**Acceptance criteria:**
- [x] Sem suporte (`CSS.supports("backdrop-filter","blur(1px)")` falso), com `prefers-reduced-transparency: reduce` ou `forced-colors: active`, o painel usa fundo opaco (`02-architecture.md`, "Verificação").
- [x] Texto sobre o painel mantém 4,5:1 contra o pior fundo, em tema claro e escuro.
- [x] Teste que varre `src/**/*.css` e `*.tsx` falha se `backdrop-filter` aparece fora de `glass.css` (regra do ADR-0022).

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend.

**Dependencies:** Task 5.1

**Skills:** `high-end-visual-design`, `emil-design-eng`, `ui-animation`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/GlassPanel.tsx`, `frontend/src/styles/glass.css`
- `frontend/src/components/surfaces/GlassPanel.test.tsx`, `frontend/src/styles/no-stray-backdrop.test.ts`

**Estimated scope:** Small

### Task 5.3: Hooks de movimento e mouse-tracking

**Description:** `useReducedMotion`, `useCanHover` e `usePointerSpotlight` em `lib/ui/`.

**Acceptance criteria:**
- [x] `usePointerSpotlight` registra `pointermove` só com `(hover: hover) and (pointer: fine)` e sem movimento reduzido (`02-architecture.md`, "Restrições obrigatórias").
- [x] Com `pointer: coarse` ou movimento reduzido, nenhum listener de `pointermove` é registrado (teste com spy).
- [x] A atualização usa `requestAnimationFrame` e CSS variables, sem re-render React (teste conta renders).

**Verification:**
- [x] `cd frontend && npm test -- --run src/lib/ui`.
- [x] Gate frontend.

**Dependencies:** Task 5.1

**Skills:** `emil-design-eng`, `emilkowalski-motion`, `animate`, `ui-animation`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/lib/ui/usePointerSpotlight.ts`, `frontend/src/lib/ui/useReducedMotion.ts`, `frontend/src/lib/ui/useCanHover.ts`
- `frontend/src/lib/ui/usePointerSpotlight.test.tsx`

**Estimated scope:** Small

### Task 5.4: `StatusBadge` e página de amostra dos componentes

**Description:** `StatusBadge` para os 7 status (com `aria-live` onde muda) e uma página de amostra (rota de desenvolvimento) com tokens, `GlassPanel` e badge.

**Acceptance criteria:**
- [x] `StatusBadge` mostra texto pt-BR para `pending`, `processing`, `transcribed`, `needs_split`, `generating`, `done` e `failed`, sem depender só de cor (WCAG 2.2 AA).
- [x] Mudança de status anuncia em região `aria-live`.
- [x] A página de amostra passa `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components`.
- [x] Gate frontend.

**Dependencies:** Tasks 5.1, 5.2

**Skills:** `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `shadcn`

**Files likely touched:**
- `frontend/src/components/surfaces/StatusBadge.tsx`, `frontend/src/components/surfaces/StatusBadge.test.tsx`
- `frontend/src/app/SamplePage.tsx`, `frontend/src/app/SamplePage.test.tsx`

**Estimated scope:** Small

### Checkpoint: Frontend base

- [x] `cd frontend && npm test -- --run` e `npm run build` passam
- [x] Checagem de UI
- [x] `impeccable-design-polish` sobre os tokens e a página de amostra dos componentes
- [x] `/security-review` sobre o diff

### Task 6.1: Dockerfiles do backend (CPU e GPU)

**Description:** `backend/Dockerfile` (Python 3.12 slim, ffmpeg, torch CPU) e `backend/Dockerfile.gpu` (base CUDA), usuário UID 1000, imagens fixadas por digest.

**Acceptance criteria:**
- [x] As duas imagens constroem e rodam como UID 1000 (SEC-23).
- [x] Imagem base fixada por digest; `uv sync --frozen` no build (SEC-21).
- [x] Nenhum segredo nem `.env` entra na imagem (`.dockerignore`; SEC-08).

**Verification:**
- [x] `docker build -f backend/Dockerfile backend` termina; `docker run --rm <img> id -u` imprime `1000`.
- [x] `docker build -f backend/Dockerfile.gpu backend` termina (execução em GPU fica para a Task 26.4).

**Dependencies:** Task 3.5

**Files likely touched:**
- `backend/Dockerfile`, `backend/Dockerfile.gpu`, `backend/.dockerignore`

**Estimated scope:** Small

### Task 6.2: Dockerfile do frontend e nginx

**Description:** `frontend/Dockerfile` (build Node, runtime nginx) e `deploy/nginx.conf` com proxy de `/api` para `backend:8000`, limite de corpo e headers.

**Acceptance criteria:**
- [x] `location /api/` repassa ao `backend:8000` com `Host`; a SPA volta `index.html` nas rotas do cliente.
- [x] Corpo limitado em 1 MiB nas rotas JSON e em 510m (500 MiB mais folga de multipart, ADR-0018) só no `POST /api/meetings` (SEC-25).
- [x] O container roda como UID 1000 (SEC-23).

**Verification:**
- [x] `docker build -f frontend/Dockerfile .` termina (contexto = raiz, porque a imagem copia `deploy/nginx.conf`).
- [x] `docker run --rm <img> nginx -t -c /etc/nginx/nginx.conf` passa.

**Dependencies:** Tasks 4.3, 6.1

**Files likely touched:**
- `frontend/Dockerfile`, `frontend/Dockerfile.dockerignore`, `deploy/nginx.conf`

**Estimated scope:** Small

### Task 6.3: Compose, `.env.example` e `.gitignore`

**Description:** `compose.yaml` com perfis `cpu` e `gpu`, volumes `snook-db`, `snook-models`, bind `./audios`, sub-rede `172.28.0.0/24`, healthcheck e logs `json-file`; `.env.example` sem segredo; `.gitignore`; README mínimo.

**Acceptance criteria:**
- [x] `docker compose up --build` sobe backend e frontend e `http://localhost:8080` responde (transversal 1).
- [x] `docker compose down` sem `-v` mantém o banco e `./audios` (transversal 2, manual).
- [x] `.gitignore` cobre `.env`, `*.db`, `*.db-*`, `*.db.bak-*`, `audios/`, `models/`, `snook-lan-ca.crt`; `.env.example` não traz valor secreto e mostra o comando que gera `SNOOK_MASTER_KEY` (transversal 8; SEC-08).

**Verification:**
- [x] `docker compose up --build -d`, depois `curl -sI http://localhost:8080/` e `curl -s http://localhost:8080/api/health`.
- [x] `docker compose ps` não mostra porta publicada do backend; `docker compose exec backend id -u` imprime `1000` (SEC-23).
- [x] `docker compose stop backend backend-gpu` com o serviço fora do perfil ativo: se falhar, `08-deployment.md` passa a trazer um comando por perfil (decisão do plano, Task 6). Conferido: sai com 0; um comando só basta.
- [x] `git check-ignore .env audios/x snook.db` lista os três.

**Dependencies:** Tasks 6.1, 6.2

**Files likely touched:**
- `compose.yaml`, `.env.example`, `.gitignore`, `README.md`

**Estimated scope:** Medium

### Task 7.1: Headers de segurança, `Host` permitido e CORS desligado

**Description:** Middleware em `core/http_security.py`: headers de SEC-13 em toda resposta e `TrustedHostMiddleware` com `ALLOWED_HOSTS`. Sem CORS.

**Acceptance criteria:**
- [x] Toda resposta traz CSP, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` e `Cross-Origin-Opener-Policy` exatamente como em SEC-13; nenhum HSTS no backend.
- [x] `Host: evil.example` recebe 400 `invalid_host` (SEC-14; abuse case do threat model).
- [x] Nenhuma resposta traz `Access-Control-Allow-Origin`, mesmo com `Origin` estranho.

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_http_headers_host.py -q`.
- [x] Gate backend. SEC-13, SEC-14.

**Dependencies:** Task 3.2

**Files likely touched:**
- `backend/src/snook/core/http_security.py`, `backend/src/snook/main.py`
- `backend/tests/core/test_http_headers_host.py`

**Estimated scope:** Small

### Task 7.2: Checagem de `Origin` e limite de corpo JSON

**Description:** Middleware que exige `Origin` (ou `Referer`) em `ALLOWED_ORIGINS` nos métodos que mudam estado, e corta corpo JSON acima de 1 MiB.

**Acceptance criteria:**
- [x] `POST`, `PUT`, `PATCH` e `DELETE` sem `Origin` ou com `Origin` estranho recebem 403 `invalid_origin`; com `Origin` válido passam (SEC-04; um teste por método).
- [x] Nenhum `GET` muda o banco (teste de snapshot antes e depois nas rotas existentes; SEC-04).
- [x] Corpo JSON acima de 1 MiB recebe 413 `payload_too_large` (SEC-25).

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_origin_body_limit.py -q`.
- [x] Gate backend. SEC-04, SEC-25.

**Dependencies:** Task 7.1

**Files likely touched:**
- `backend/src/snook/core/http_security.py`
- `backend/tests/core/test_origin_body_limit.py`

**Estimated scope:** Small

### Task 7.3: Resolvedor de proxies confiáveis

**Description:** Função que resolve IP do cliente e esquema a partir de `X-Forwarded-For` e `X-Forwarded-Proto`, só quando a conexão vem de IP em `TRUSTED_PROXY_IPS`. Usa `--forwarded-allow-ips` do uvicorn se a versão travada seguir a regra; senão, middleware próprio. O teste decide (`08-deployment.md`, "Perfil lan").

**Acceptance criteria:**
- [x] Conexão de IP em `TRUSTED_PROXY_IPS` com `X-Forwarded-For: 1.2.3.4, <IP do cliente>` resolve `<IP do cliente>`: primeiro IP fora da lista, da direita para a esquerda (SEC-27).
- [x] `X-Forwarded-Proto: https` só vale vindo de IP em `TRUSTED_PROXY_IPS`.
- [x] Conexão de IP fora da lista: cabeçalhos ignorados; valem IP e esquema da conexão.

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_proxy_resolver.py -q` (direto na função ou por rota de teste registrada só na suíte, nunca na app de produção).
- [x] Gate backend. SEC-27.

**Dependencies:** Task 7.1

**Files likely touched:**
- `backend/src/snook/core/http_security.py`
- `backend/tests/core/test_proxy_resolver.py`

**Estimated scope:** Small

### Task 7.4: Logs JSON com redação

**Description:** `core/logging.py`: logs JSON em stdout, `LOG_LEVEL`, filtro que redige segredos e eventos de segurança (`07-observability.md`).

**Acceptance criteria:**
- [x] Log sai em JSON, um objeto por linha, com nível e evento.
- [x] Com senha, token de sessão, chave de LLM, `HF_TOKEN` e chave-mestra de teste conhecidos, nenhum aparece em texto claro no `caplog` (transversal 7; SEC-20), inclusive dentro de mensagem de exceção.
- [x] Texto de Transcrição nunca entra em log (teste com marcador de texto) (SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_logging.py -q`.
- [x] Gate backend. SEC-20.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/core/logging.py`, `backend/src/snook/main.py`
- `backend/tests/core/test_logging.py`

**Estimated scope:** Small

### Task 6b: Perfil `lan` (Caddy, `SNOOK_LAN_HOST`, repasse de `X-Forwarded-*`)

**Description:** Serviço `caddy` no perfil `lan`, `deploy/Caddyfile`, derivação de `ALLOWED_HOSTS` e `ALLOWED_ORIGINS` a partir de `SNOOK_LAN_HOST` e `map` do nginx para `X-Forwarded-Proto` (ADR-0016; `08-deployment.md`, "Perfil lan").

**Acceptance criteria:**
- [x] `SNOOK_LAN_HOST` válido (nome DNS ou IP, sem esquema, porta ou caminho) entra em `ALLOWED_HOSTS` e `ALLOWED_ORIGINS` (`https://<host>`); valor inválido impede a subida com mensagem clara (SEC-14; um teste válido e um inválido).
- [x] O nginx repassa `X-Forwarded-Proto` só quando a conexão vem do Caddy (`172.28.0.11`); senão usa `$scheme` (SEC-27).
- [ ] `curl --cacert snook-lan-ca.crt -sI https://<SNOOK_LAN_HOST>/` responde por HTTPS e mostra `Strict-Transport-Security: max-age=31536000` (SEC-13).

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_settings_lan.py -q`.
- [ ] Manual: `COMPOSE_PROFILES=cpu,lan docker compose up -d`, exportar a CA com `docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./snook-lan-ca.crt`, rodar o `curl` acima.
- [x] Gate backend. SEC-13, SEC-14, SEC-27, SEC-08 (`caddy-data` fora do git).

**Dependencies:** Tasks 6.3, 7.1, 7.3

**Files likely touched:**
- `backend/src/snook/core/settings.py`, `backend/tests/core/test_settings_lan.py`
- `compose.yaml`, `deploy/Caddyfile`, `deploy/nginx.conf`

**Estimated scope:** Medium

### Task 8.1: CI: backend, frontend e imagens

**Description:** `.github/workflows/ci.yml` em `pull_request` para `develop` e `main` e `push` para `develop`, com os jobs `backend`, `frontend` e `images` de `08-deployment.md`, "CI/CD".

**Acceptance criteria:**
- [x] Job `backend`: `uv sync --frozen`, `ruff check`, `ruff format --check`, `mypy src`, `lint-imports`, `pytest`, `pip-audit` (SEC-21).
- [x] Job `frontend`: `npm ci --ignore-scripts`, `npm run lint`, `npm run typecheck`, `npm test -- --run`, `npm run build`, `npm audit --omit=dev` (SEC-21).
- [x] Job `images`: `docker compose build` do perfil `cpu`, sem push. Suítes `models_real` e `llm_real` não rodam.

**Verification:**
- [x] CI verde em PR de teste para `develop`.
- [ ] Manual: `actionlint .github/workflows/ci.yml` (se instalado) sem erro.

**Dependencies:** Tasks 6.3, 4.2

**Files likely touched:**
- `.github/workflows/ci.yml`

**Estimated scope:** Small

### Task 8.2: CI: `gitleaks`, `.gitignore` e limite de bundle

**Description:** Job `secrets` (`gitleaks detect` no diff e checagem de `.gitignore`) e script que falha o build se o JS passar do orçamento (NFR-01 e NFR-02, ADR-0023).

**Acceptance criteria:**
- [ ] `gitleaks` acha um segredo plantado num PR de teste e passa sem ele (SEC-08).
- [x] O job falha se `.gitignore` não cobre `.env`, `*.db`, `audios/` (transversal 8).
- [x] O CI falha se o JS inicial da rota de login passa de 200 KB gzip ou o total de 500 KB gzip (NFR-01, NFR-02).

**Verification:**
- [x] `cd frontend && npm run build && node scripts/check-bundle-size.mjs` passa; com limite reduzido por variável de teste, falha.
- [ ] PR de teste no GitHub: job `secrets` verde e job com segredo plantado vermelho.

**Dependencies:** Task 8.1

**Files likely touched:**
- `.github/workflows/ci.yml`, `frontend/scripts/check-bundle-size.mjs`, `.gitleaks.toml`

**Estimated scope:** Small

### Checkpoint: Fundação

- [ ] `docker compose up --build` sobe e `http://localhost:8080` responde (critério transversal 1)
- [ ] `docker compose stop backend backend-gpu` conferido com o serviço fora do perfil ativo; se falhar, `08-deployment.md` traz um comando por perfil (Task 6.3)
- [ ] Perfil `lan`: `curl --cacert snook-lan-ca.crt -sI https://<SNOOK_LAN_HOST>/` responde por HTTPS e mostra `Strict-Transport-Security` (Task 6b)
- [ ] Resolvedor de proxy da Task 7.3, testado direto ou por rota de teste registrada só na suíte do Pytest:
  - conexão de IP em `TRUSTED_PROXY_IPS` com `X-Forwarded-For` forjado à esquerda: IP do cliente é o primeiro IP fora de `TRUSTED_PROXY_IPS`, da direita para a esquerda;
  - `X-Forwarded-Proto` só vale vindo de IP em `TRUSTED_PROXY_IPS`;
  - conexão de IP fora de `TRUSTED_PROXY_IPS`: cabeçalhos ignorados, vale IP e esquema da conexão.
- [ ] `.gitignore` cobre `.env`, `*.db`, `audios/` (achado 1 do 03-security resolvido)
- [ ] CI verde no PR para `develop`
- [ ] SEC-04, SEC-08, SEC-13, SEC-14, SEC-19, SEC-20, SEC-21, SEC-23, SEC-25 (corpo JSON até 1 MiB) e SEC-27 (resolvedor) com testes de base
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 1: `auth`

### Task 9.1: Usuário: modelo, migração 0001 e hash de senha

**Description:** Tabelas `users` e `sessions` (migração `0001_auth_users_sessions`), repositório e funções de hash/verificação bcrypt (ADR-0021), com `email_norm` e `username_norm` únicos.

**Acceptance criteria:**
- [x] A coluna de senha guarda hash bcrypt e `bcrypt.checkpw` com a senha original é verdadeiro (`auth` 9).
- [x] A unicidade de email e de nome de usuário ignora caixa: `Ana@x.com` e `ana@x.com` colidem; `Ana` e `ana` colidem (`auth` 6).
- [x] O texto da senha não aparece no SQLite (`auth` 10, parte do armazenamento; SEC-05).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth/test_user_storage.py -q` (`BCRYPT_ROUNDS=4` nos testes).
- [x] `cd backend && uv run alembic upgrade head` num banco novo.
- [x] Gate backend. SEC-05.

**Dependencies:** Task 3.5

**Files likely touched:**
- `backend/src/snook/modules/auth/models.py`, `backend/src/snook/modules/auth/repository.py`
- `backend/alembic/versions/0001_auth_users_sessions.py`
- `backend/src/snook/modules/auth/service.py`, `backend/tests/auth/test_user_storage.py`

**Estimated scope:** Medium

### Task 9.2: Rota de cadastro

**Description:** `POST /api/auth/register` com validação por schema, mensagens pt-BR e erros 409/422.

**Acceptance criteria:**
- [x] Cadastro válido responde 201 com `id`, `email` e `username`, sem senha nem hash (`auth` 1, 11).
- [x] Recusas sem criar Usuário: senha de 7 caracteres ou menos (422, `auth` 2); email já usado (409 `email_taken`, `auth` 3); nome já usado (409 `username_taken`, `auth` 4); email inválido (422, `auth` 5); nome de usuário fora de 3 a 30 ou com caractere inválido (422, `auth` 7); caixa diferente colide (409, `auth` 6).
- [x] Senha de 72 bytes é aceita; 73 bytes ASCII e senha acentuada acima de 72 bytes com menos de 72 caracteres são recusadas com 422 e "senha com no máximo 72 bytes" (`auth` 28, SEC-05). A senha não aparece em log (`auth` 10, SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth/test_api_register.py -q`.
- [x] Gate backend. SEC-05, SEC-09, SEC-20.

**Dependencies:** Task 9.1

**Files likely touched:**
- `backend/src/snook/modules/auth/schemas.py`, `backend/src/snook/modules/auth/service.py`, `backend/src/snook/modules/auth/api.py`, `backend/src/snook/modules/auth/messages.py`
- `backend/tests/auth/test_api_register.py`

**Estimated scope:** Medium

### Task 9.3: Sessões, cookie e login automático no cadastro

**Description:** Sessão com token opaco de 32 bytes (só SHA-256 no banco), cookie `snook_session`, dependência `current_user`, expiração por inatividade e máxima, limpeza horária. O cadastro cria sessão (ADR-0008).

**Acceptance criteria:**
- [x] O cookie tem `HttpOnly`, `SameSite=Lax`, `Path=/` e `Secure` quando o esquema resolvido é `https` ou o host é `localhost`; o banco guarda só o hash do token (SEC-03).
- [x] Com relógio falso, a sessão expira com 24 h de inatividade e 7 dias no total; token novo a cada cadastro e login (SEC-03).
- [x] Cadastro responde com `Set-Cookie`, e a sessão criada existe na tabela `sessions` (base de `auth` 8; o `GET /auth/me` do critério 8 fecha na Task 10.1).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth/test_sessions.py -q` (inclui `X-Forwarded-Proto: https` vindo de IP confiável: cookie com `Secure`).
- [x] Gate backend. SEC-03, SEC-27.

**Dependencies:** Tasks 9.2, 7.3

**Files likely touched:**
- `backend/src/snook/modules/auth/deps.py`, `backend/src/snook/modules/auth/service.py`, `backend/src/snook/modules/auth/api.py`
- `backend/src/snook/modules/auth/repository.py`, `backend/tests/auth/test_sessions.py`

**Estimated scope:** Medium

### Task 9.4: Tela de cadastro

**Description:** Tela de cadastro com card, erros da API, e ida à área autenticada após o cadastro. Entregue com card de vidro e mouse-tracking (ADR-0022). Direção Ata (ADR-0024, Q3 e Q2 opção A): card opaco (`--surface`), com régua `--hairline`, sem sombra e sem mouse-tracking; a troca é da Task 55 (55.1 e 55.3). Os critérios abaixo não mudam.

**Acceptance criteria:**
- [x] A tela inicial oferece cadastro e login (`auth` 22).
- [x] Cadastro bem-sucedido leva direto à área autenticada (`auth` 23).
- [x] Erros do cadastro aparecem na tela com a mensagem da API (`auth` 25); `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/auth`.
- [x] Gate frontend.

**Dependencies:** Tasks 9.3, 5.2, 5.3

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `emil-design-eng`, `ui-animation`

**Files likely touched:**
- `frontend/src/features/auth/RegisterPage.tsx`, `frontend/src/features/auth/useRegister.ts`, `frontend/src/features/auth/RegisterPage.test.tsx`
- `frontend/src/app/routes.tsx`

**Estimated scope:** Medium

### Task 10.1: Login, logout e `/auth/me` (API)

**Description:** `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` e a varredura de rotas para SEC-01.

**Acceptance criteria:**
- [x] Login por email, por nome de usuário e por caixa diferente autentica (`auth` 12, 13, 14); senha errada ou conta inexistente responde 401 `invalid_credentials` com a mesma mensagem e tempo parecido (`auth` 15, 16; SEC-05).
- [x] Logout apaga a sessão no servidor e a mesma sessão recebe 401 depois (`auth` 17); `GET /auth/me` responde `id`, `email`, `username` (`auth` 18) e 401 sem sessão (`auth` 19); o cadastro seguido de `GET /auth/me` sem login funciona (`auth` 8).
- [x] Cadastro e login respondem sem sessão (`auth` 20); não existe rota de recuperação, troca de senha, perfil ou exclusão (`auth` 21); teste que percorre `app.routes` falha se rota fora da lista pública não exige sessão (SEC-01, transversal 10).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth -q`.
- [x] Gate backend. SEC-01, SEC-03, SEC-05.

**Dependencies:** Task 9.3

**Files likely touched:**
- `backend/src/snook/modules/auth/api.py`, `backend/src/snook/modules/auth/service.py`, `backend/src/snook/modules/auth/schemas.py`
- `backend/tests/auth/test_api_login.py`, `backend/tests/test_routes_require_session.py`

**Estimated scope:** Medium

### Task 10.2: Tela de login, guarda de rota e logout

**Description:** Tela de login, guarda de autenticação com redirecionamento ao login e botão de sair. Entregue com card de vidro e mouse-tracking (ADR-0022). Direção Ata (ADR-0024, Q3 e Q2 opção A): card opaco (`--surface`), com régua `--hairline`, sem sombra e sem mouse-tracking; a troca é da Task 55 (55.1 e 55.2). Os critérios abaixo não mudam.

**Acceptance criteria:**
- [x] Abrir página protegida sem sessão leva ao login (`auth` 24).
- [x] Erros de login aparecem com a mensagem da API (`auth` 25); depois do logout o frontend volta ao login (`auth` 26).
- [x] Sessão nunca vai a `localStorage` nem `sessionStorage` (`03-security.md`, "Never"); `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/auth src/app`.
- [x] Gate frontend.

**Dependencies:** Tasks 10.1, 9.4

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `emil-design-eng`, `ui-animation`

**Files likely touched:**
- `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/features/auth/useSession.ts`, `frontend/src/features/auth/LoginPage.test.tsx`
- `frontend/src/app/AuthGuard.tsx`, `frontend/src/app/Layout.tsx`

**Estimated scope:** Medium

### Task 11.1: Limitador de janela deslizante

**Description:** `core/ratelimit.py`: `SlidingWindowLimiter` em memória, com relógio injetável (ADR-0010).

**Acceptance criteria:**
- [x] Após N eventos na janela, o seguinte é negado e devolve `Retry-After` em segundos.
- [x] Passada a janela (relógio falso), a contagem libera; contagem por chave é independente.
- [x] Reset explícito de uma chave zera a contagem.

**Verification:**
- [x] `cd backend && uv run pytest tests/core/test_ratelimit.py -q`.
- [x] Gate backend. SEC-06.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/core/ratelimit.py`, `backend/tests/core/test_ratelimit.py`

**Estimated scope:** Small

### Task 11.2: Limite de tentativas de login

**Description:** Login usa o limitador: 5 falhas por identificador e 20 por IP do cliente em 15 min, valores por `.env`.

**Acceptance criteria:**
- [x] Depois de N falhas na janela, as seguintes recebem 429 `rate_limited` com `Retry-After`, mesmo com a senha correta (`auth` 27); login correto antes do limite zera a contagem.
- [x] O IP contado é o do cliente resolvido por SEC-27: `X-Forwarded-For` forjado direto ao backend não muda o IP; 21 falhas a partir de um IP geram 429 (abuse case).
- [x] N e a janela vêm de `LOGIN_MAX_FAILURES`, `LOGIN_MAX_FAILURES_PER_IP`, `LOGIN_WINDOW_SECONDS`; o 429 é registrado em log (SEC-20, sem senha).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth/test_api_login_ratelimit.py -q`.
- [x] Gate backend. SEC-06, SEC-20, SEC-27.

**Dependencies:** Tasks 11.1, 10.1, 7.3

**Files likely touched:**
- `backend/src/snook/modules/auth/service.py`, `backend/src/snook/modules/auth/api.py`
- `backend/tests/auth/test_api_login_ratelimit.py`

**Estimated scope:** Small

### Checkpoint: `auth`

- [ ] Critérios 1 a 28 de `01-prd/auth.md` cobertos por teste
- [ ] SEC-01, SEC-03, SEC-05, SEC-06 verificados
- [ ] Perfil `lan` (`08-deployment.md`, "Perfil lan"; SEC-03, SEC-06, SEC-27):
  - login pelo Caddy devolve `Set-Cookie` com `Secure`;
  - limitador de login conta o IP do cliente da rede, não o IP do Caddy nem do nginx;
  - `X-Forwarded-For` e `X-Forwarded-Proto` forjados direto no nginx não mudam o IP contado pelo limitador; esquema fica `http`.
- [ ] Checagem de UI; `impeccable-design-polish` nas telas de cadastro e login
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 2A: `llm-providers` (paralela à 2B)

### Task 12.1: Cifra AES-256-GCM

**Description:** `crypto.py`: AES-256-GCM com `SNOOK_MASTER_KEY` e AAD por Usuário e provedor (ADR-0009).

**Acceptance criteria:**
- [x] Decifrar o valor cifrado com a chave-mestra devolve a chave original; o valor cifrado difere do original (`llm-providers` 12, transversal 6).
- [x] Valor cifrado copiado para outro Usuário ou outro provedor não decifra (AAD; SEC-07).
- [x] Chave-mestra errada falha com erro tipado, sem texto da chave na mensagem.

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_crypto.py -q`.
- [x] Gate backend. SEC-07.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/crypto.py`, `backend/tests/llm_providers/test_crypto.py`

**Estimated scope:** Small

### Task 12.2: Modelo `llm_configs`, migração 0002 e chave ilegível

**Description:** Tabela `llm_configs` (migração `0002_llm_providers_configs`), repositório que grava a chave cifrada e estado `key_status` quando a chave-mestra mudou sem rotação.

**Acceptance criteria:**
- [x] O valor da chave no SQLite difere da chave enviada e decifra com a chave-mestra (`llm-providers` 12, transversal 6).
- [x] Chave que não decifra (mestra trocada) marca `key_status` ilegível, sem erro 500 e sem vazar valor (ADR-0009).
- [x] `ON DELETE CASCADE` de `users` leva as configurações (`04-data-model.md`).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_storage.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend. SEC-07.

**Dependencies:** Tasks 12.1, 9.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/models.py`, `backend/src/snook/modules/llm_providers/repository.py`
- `backend/alembic/versions/0002_llm_providers_configs.py`, `backend/tests/llm_providers/test_storage.py`

**Estimated scope:** Medium

### Task 12.3: Rotação da chave-mestra (`rotate-master-key`)

**Description:** Comando `python -m snook.cli rotate-master-key` com `SNOOK_MASTER_KEY_PREVIOUS`, trava e backup.

**Acceptance criteria:**
- [x] Depois da rotação, toda chave decifra com a nova chave-mestra e o valor cifrado mudou (ADR-0009).
- [x] Com a trava `/data/snook.lock` ocupada, o comando para com erro e não escreve (SEC-24; ADR-0006).
- [x] Nenhuma chave nem chave-mestra aparece na saída nem no log (SEC-07, SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/cli/test_rotate_master_key.py -q`.
- [x] Gate backend. SEC-07, SEC-24. Não rodar em dado real sem aprovação ("Perguntar antes").

**Dependencies:** Task 12.2

**Files likely touched:**
- `backend/src/snook/cli.py`, `backend/src/snook/modules/llm_providers/service.py`
- `backend/tests/cli/test_rotate_master_key.py`

**Estimated scope:** Small

### Task 13.1: Base dos adapters e erros tipados

**Description:** `adapters/base.py`: interface do adapter, erros tipados (`NoActiveProvider`, `CredentialRejected`, `ProviderUnreachable`, `ModelNotFound`, `ContextLimitExceeded`, `ProviderRateLimited`) e cliente `httpx` com `follow_redirects=False`, timeout de conexão 10 s, corpo cortado em 5 MB (ADR-0012).

**Acceptance criteria:**
- [x] Resposta de redirecionamento vira `ProviderUnreachable`, sem seguir (`llm-providers` 39; SEC-17).
- [x] Corpo de 6 MB é cortado em 5 MB e vira erro tipado; timeout de leitura vira `ProviderUnreachable` (SEC-17, `respx`).
- [x] O erro devolvido traz tipo e motivo, nunca corpo cru nem headers nem a chave (`llm-providers` 27; SEC-17).

**Verification:**
- [x] `cd backend && uv run pytest tests/adapters/llm/test_base.py -q`.
- [x] Gate backend. SEC-17.

**Dependencies:** Task 3.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/adapters/base.py`
- `backend/tests/adapters/llm/test_base.py`

**Estimated scope:** Small

### Task 13.2: Adapter OpenAI-compatível (OpenAI e DeepSeek)

**Description:** `adapters/openai_compat.py` atende OpenAI e DeepSeek com URL fixa, saída JSON, teste de conexão por consulta do modelo e fixtures gravadas em `tests/fixtures/llm/<provider>/`.

**Acceptance criteria:**
- [x] "Gerar" devolve o texto da resposta gravada para OpenAI e para DeepSeek (`llm-providers` 29).
- [x] Respostas gravadas de credencial recusada, modelo inexistente, limite de contexto, rate limit e falha de rede viram os erros tipados certos (`llm-providers` 30).
- [x] A chave aparece só no header de autorização e nunca em erro, log ou fixture (`llm-providers` 9, 27; SEC-07).

**Verification:**
- [x] `cd backend && uv run pytest tests/adapters/llm/test_openai_compat.py -q` (`respx`, sem rede).
- [x] Gate backend. SEC-07, SEC-17.

**Dependencies:** Task 13.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/adapters/openai_compat.py`
- `backend/tests/adapters/llm/test_openai_compat.py`, `backend/tests/fixtures/llm/openai/*.json`, `backend/tests/fixtures/llm/deepseek/*.json`

**Estimated scope:** Medium

### Task 14.1: Adapter Anthropic

**Description:** `adapters/anthropic.py` com URL fixa, saída JSON e teste de conexão.

**Acceptance criteria:**
- [x] "Gerar" devolve o texto da resposta gravada (`llm-providers` 29).
- [x] Erros gravados viram os erros tipados do contrato (`llm-providers` 30).
- [x] Chave nunca aparece em erro, log ou fixture (`llm-providers` 27; SEC-07).

**Verification:**
- [x] `cd backend && uv run pytest tests/adapters/llm/test_anthropic.py -q`.
- [x] Gate backend. SEC-07, SEC-17.

**Dependencies:** Task 13.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/adapters/anthropic.py`
- `backend/tests/adapters/llm/test_anthropic.py`, `backend/tests/fixtures/llm/anthropic/*.json`

**Estimated scope:** Small

### Task 14.2: Adapter Ollama e regras da URL

**Description:** `adapters/ollama.py` com URL do Usuário, regras de esquema e credenciais, sem redirecionamento (Q60, Q63).

**Acceptance criteria:**
- [x] Aceita qualquer host (`localhost`, `host.docker.internal`, rede privada) com `http` ou `https`; recusa `file:` e `ftp:` como erro de validação (`llm-providers` 38).
- [x] Recusa URL com credenciais embutidas (`http://usuario:senha@host`) (`llm-providers` 40).
- [x] Resposta gravada de redirecionamento, no adapter real, vira "provedor inacessível" (`llm-providers` 39); "Gerar" e erros gravados passam (`llm-providers` 29, 30). Abuse case: 302 para `http://169.254.169.254/` não é seguido.

**Verification:**
- [x] `cd backend && uv run pytest tests/adapters/llm/test_ollama.py -q`.
- [x] Gate backend. SEC-17.

**Dependencies:** Task 13.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/adapters/ollama.py`
- `backend/tests/adapters/llm/test_ollama.py`, `backend/tests/fixtures/llm/ollama/*.json`

**Estimated scope:** Small

### Checkpoint: Cifra e adapters

- [x] Critérios 29, 30, 38 a 40 de `01-prd/llm-providers.md` passam (38 e 40 no nível do adapter; a resposta 422 por API fecha na Task 15.2)
- [x] SEC-07, SEC-17 verificados
- [x] `/security-review` sobre o diff

### Task 15.1: `GET /llm-configs`

**Description:** Listagem dos 4 provedores com estado, padrões do ADR-0013 (`defaults.py`), máscara da chave e URL do Ollama.

**Acceptance criteria:**
- [x] Usuário sem configuração vê os 4 como `not_configured`, com modelo e janela padrão (`llm-providers` 1).
- [x] Provedor configurado mostra modelo, janela, ativo e só a máscara (`sk-...abcd`: até 3 primeiros e 4 últimos; chave com menos de 12 caracteres vira `...`) (`llm-providers` 2, 3); URL do Ollama aparece inteira (`llm-providers` 4).
- [x] Configuração de outro Usuário não aparece; sem sessão responde 401 (`llm-providers` 26, 28; SEC-26).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_api_list.py -q`.
- [x] Gate backend. SEC-07, SEC-26.

**Dependencies:** Tasks 12.2, 10.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/api.py`, `backend/src/snook/modules/llm_providers/service.py`, `backend/src/snook/modules/llm_providers/defaults.py`, `backend/src/snook/modules/llm_providers/schemas.py`
- `backend/tests/llm_providers/test_api_list.py`

**Estimated scope:** Medium

### Task 15.2: `POST /llm-configs/{provider}/test`

**Description:** Teste de conexão sem gravar, com adapters trocáveis por fake nos testes.

**Acceptance criteria:**
- [x] Chave e modelo válidos respondem `{ok:true}` e nada é gravado (`llm-providers` 5); credencial recusada, Ollama inacessível e modelo inexistente respondem `{ok:false,reason}` com `credential_rejected`, `provider_unreachable`, `model_not_found` (`llm-providers` 6, 7, 8).
- [x] A chave enviada não aparece em resposta nem em log (`llm-providers` 9, 27; SEC-07); com `api_key` vazio e config existente, usa a chave salva.
- [x] URL do Ollama com esquema estranho ou credencial recebe 422 (`llm-providers` 38, 40); `{provider}` desconhecido recebe 404; adapter de Ollama real recusa redirecionamento (`llm-providers` 39).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_api_test_connection.py -q`.
- [x] Gate backend. SEC-07, SEC-09, SEC-17.

**Dependencies:** Tasks 15.1, 13.2, 14.1, 14.2

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/api.py`, `backend/src/snook/modules/llm_providers/service.py`, `backend/src/snook/modules/llm_providers/schemas.py`
- `backend/tests/llm_providers/test_api_test_connection.py`, `backend/tests/conftest.py`

**Estimated scope:** Medium

### Task 15.3: `PUT /llm-configs/{provider}`

**Description:** Salvar refaz o teste no servidor; grava cifrado; primeira configuração fica ativa; edição mantém ou troca a chave.

**Acceptance criteria:**
- [x] Conexão que falha responde 422 com o motivo e a configuração anterior não muda (`llm-providers` 10); conexão válida grava e devolve só a máscara (`llm-providers` 11, 12).
- [x] Primeira configuração de Ollama sem URL, ou de OpenAI, Anthropic ou DeepSeek sem chave, recebe 422 (`llm-providers` 13); modelo ausente usa o padrão (`llm-providers` 14); janela ausente usa o padrão, valor não inteiro positivo recebe 422 (`llm-providers` 15).
- [x] Primeira configuração fica ativa, a segunda não muda o ativo (`llm-providers` 16); edição sem nova chave mantém a atual e testa com ela (`llm-providers` 17); com nova chave, substitui depois do teste passar (`llm-providers` 18). O evento de salvar vai ao log sem a chave (SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_api_save.py -q`.
- [x] Gate backend. SEC-07, SEC-09, SEC-20, SEC-26.

**Dependencies:** Task 15.2

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/api.py`, `backend/src/snook/modules/llm_providers/service.py`, `backend/src/snook/modules/llm_providers/repository.py`
- `backend/tests/llm_providers/test_api_save.py`

**Estimated scope:** Medium

### Task 15.4: Ativar e remover configuração

**Description:** `POST /llm-configs/{provider}/activate` e `DELETE /llm-configs/{provider}`.

**Acceptance criteria:**
- [x] Ativar um provedor configurado o torna ativo e desativa o anterior; no máximo um ativo por Usuário (`llm-providers` 19, 20); ativar não configurado recebe 409 `provider_not_configured` (`llm-providers` 21).
- [x] Remover apaga a configuração e a chave cifrada do SQLite (`llm-providers` 23); remover o ativo deixa sem ativo, sem ativar outro (`llm-providers` 24); remover não configurado recebe 404 (`llm-providers` 25).
- [x] A remoção vai ao log sem a chave (SEC-20); cada rota nega 404/401 conforme isolamento (`llm-providers` 26, 28).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_api_activate_delete.py -q`.
- [x] Gate backend. SEC-20, SEC-26.

**Dependencies:** Task 15.3

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/api.py`, `backend/src/snook/modules/llm_providers/service.py`
- `backend/tests/llm_providers/test_api_activate_delete.py`

**Estimated scope:** Small

### Task 15.5: Limite de "Testar conexão" e salvar

**Description:** 10 chamadas por Usuário em 10 min, compartilhadas entre teste e salvar (ADR-0010).

**Acceptance criteria:**
- [x] Depois de N chamadas na janela, as seguintes recebem 429 `rate_limited` com `Retry-After` e nenhuma chamada ao provedor é feita (`llm-providers` 41; SEC-06).
- [x] N e a janela vêm de `LLM_TEST_MAX_CALLS` e `LLM_TEST_WINDOW_SECONDS`; o limite é por Usuário (outro Usuário não é afetado).
- [x] O 429 vai ao log sem a chave (SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_api_ratelimit.py -q` (relógio falso).
- [x] Gate backend. SEC-06, SEC-20.

**Dependencies:** Tasks 15.3, 11.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/service.py`
- `backend/tests/llm_providers/test_api_ratelimit.py`

**Estimated scope:** Small

### Task 16.1: Interface "Provedor ativo"

**Description:** `get_active_provider(user_id) -> ActiveProvider` (provedor, modelo, janela) e erro `NoActiveProvider` com mensagem que aponta para a tela de configurações.

**Acceptance criteria:**
- [x] Sem provedor ativo, devolve `NoActiveProvider` com mensagem que aponta para a tela de configurações (`llm-providers` 22; transversal 4).
- [x] Com provedor ativo, devolve provedor, modelo e janela do Usuário pedido, nunca de outro (`llm-providers` 26, 31; SEC-26).
- [x] Nenhuma função da interface devolve a chave decifrada.

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_service_active.py -q`.
- [x] Gate backend (inclui `lint-imports` com `llm_providers` importando só `auth`). SEC-26.

**Dependencies:** Task 15.4

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/service.py`
- `backend/tests/llm_providers/test_service_active.py`, `backend/pyproject.toml`

**Estimated scope:** Small

### Task 16.2: Estimativa de tokens

**Description:** `tokens.py`: `estimate_tokens(provider, model, text) -> int`, heurística aditiva por linha com `chars_per_token` 3.0 (ADR-0011).

**Acceptance criteria:**
- [x] Devolve inteiro positivo para texto não vazio (`llm-providers` 32).
- [x] Um texto que contém outro tem estimativa maior (`llm-providers` 32); a soma por linha é aditiva.
- [x] O parâmetro `chars_per_token` vem de configuração, ajustável pelo resultado do spike (Task 2).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_tokens.py -q`.
- [x] Gate backend.

**Dependencies:** Task 16.1

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/tokens.py`, `backend/tests/llm_providers/test_tokens.py`

**Estimated scope:** Small

### Task 16.3: Interface "Gerar"

**Description:** `generate(user_id, provider_snapshot, system_prompt, content, json_schema, max_output_tokens) -> str` sobre o adapter do provedor ativo.

**Acceptance criteria:**
- [x] Para cada um dos quatro provedores, "Gerar" com o adapter ligado a respostas gravadas devolve o texto (`llm-providers` 29).
- [x] "Gerar" usa o provedor ativo e o modelo salvos do Usuário dono (`llm-providers` 31).
- [x] Erros tipados do contrato sobem sem a chave (`llm-providers` 30, 27; SEC-17).

**Verification:**
- [x] `cd backend && uv run pytest tests/llm_providers/test_service_generate.py -q`.
- [x] Gate backend. SEC-07, SEC-17, SEC-26.

**Dependencies:** Tasks 16.1, 13.2, 14.1, 14.2

**Files likely touched:**
- `backend/src/snook/modules/llm_providers/service.py`
- `backend/tests/llm_providers/test_service_generate.py`

**Estimated scope:** Small

### Task 17.1: Tela de configurações: lista e formulário

**Description:** Tela de configurações com os 4 provedores, estado, máscara, modelo e janela.

**Acceptance criteria:**
- [x] Mostra os 4 provedores com estado, máscara, modelo, janela e indicação do ativo (`llm-providers` 33).
- [x] O campo de chave nunca é pré-preenchido; mostra a máscara como referência e vazio mantém a chave atual (`llm-providers` 36).
- [x] `vitest-axe` sem violação; layout de 360 a 1920 px.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] Gate frontend.

**Dependencies:** Tasks 15.1, 10.2

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/llm-providers/SettingsPage.tsx`, `frontend/src/features/llm-providers/ProviderForm.tsx`, `frontend/src/features/llm-providers/useLlmConfigs.ts`
- `frontend/src/features/llm-providers/SettingsPage.test.tsx`

**Estimated scope:** Medium

### Task 17.2: Tela de configurações: testar, salvar, ativar e remover

**Description:** "Testar conexão", "Salvar" travado até o teste passar, erros, ativar e remover com diálogo de confirmação (diálogo opaco, `DialogSurface`; ADR-0024).

**Acceptance criteria:**
- [x] "Salvar" fica desabilitado até um "Testar conexão" bem-sucedido com os valores atuais do formulário (`llm-providers` 34); erros de teste e gravação aparecem com o motivo da API (`llm-providers` 35).
- [x] Remover pede confirmação antes de chamar a API (`llm-providers` 37).
- [ ] Diálogo de remoção usa `DialogSurface` opaco, sem `GlassPanel` (ADR-0024, "Vidro"; reaberto pela Fase 9, fecha na Task 52.19); feedback de teste respeita movimento reduzido; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] Gate frontend.

**Dependencies:** Tasks 17.1, 15.5, 15.4

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/llm-providers/ProviderForm.tsx`, `frontend/src/features/llm-providers/RemoveDialog.tsx`, `frontend/src/features/llm-providers/useLlmConfigs.ts`
- `frontend/src/features/llm-providers/ProviderForm.test.tsx`

**Estimated scope:** Medium

### Checkpoint: `llm-providers`

- [ ] Critérios 1 a 41 de `01-prd/llm-providers.md` cobertos
- [ ] SEC-06, SEC-26 verificados
- [x] Checagem de UI; `impeccable-design-polish` na tela de configurações
- [x] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 2B: `meetings` (paralela à 2A)

### Task 18.1: Sonda de mídia e caminhos seguros

**Description:** `media_probe.py` (`ffprobe` por `subprocess.run([...], shell=False)`, timeout, caminho do servidor) e `core/files.py` (`/audios/.tmp`, `/audios/<meeting_id>/`, regex de UUID, `realpath` sob `/audios`). Fixtures de áudio curtas por formato.

**Acceptance criteria:**
- [x] `probe` devolve duração e presença de trilha de áudio para mp3, wav, m4a, ogg, webm e mp4 de fixture (`meetings` 1, 10).
- [x] `ffprobe` nunca recebe nome enviado pelo usuário: teste com `"; rm -rf / ;.mp3"` e `-i x.mp3` roda o comando só com caminho gerado (SEC-11).
- [x] Alvo fora de `/audios`, link simbólico para fora, `..`, raiz e `.tmp` são recusados com log (SEC-15).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_media_probe.py tests/core/test_files.py -q`.
- [x] Gate backend. SEC-11, SEC-15.

**Dependencies:** Task 3.5

**Files likely touched:**
- `backend/src/snook/modules/meetings/media_probe.py`, `backend/src/snook/core/files.py`
- `backend/tests/meetings/test_media_probe.py`, `backend/tests/core/test_files.py`, `backend/tests/fixtures/audio/*`

**Estimated scope:** Medium

### Task 18.2: Modelo `meetings` e migração 0003

**Description:** Tabela `meetings` (migração `0003_meetings`), repositório e schemas de saída sem caminho interno.

**Acceptance criteria:**
- [x] Campos de `04-data-model.md` (`status`, `failed_stage`, `error_message`, `participants_confirmed_at`, `backlog_saved_at`, `run_id`, `created_at`, `updated_at`), FK para `users` com `ON DELETE CASCADE`.
- [x] Nenhum schema de saída contém o caminho do arquivo (`meetings` 21; `03-security.md`, "Never").
- [x] `alembic upgrade head` roda sobre o banco da Task 12.2.

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_storage_model.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend.

**Dependencies:** Tasks 9.1, 18.1

**Files likely touched:**
- `backend/src/snook/modules/meetings/models.py`, `backend/src/snook/modules/meetings/repository.py`, `backend/src/snook/modules/meetings/schemas.py`
- `backend/alembic/versions/0003_meetings.py`, `backend/tests/meetings/test_storage_model.py`

**Estimated scope:** Medium

### Task 18.3: Upload válido

**Description:** `POST /api/meetings` multipart com recepção em streaming para `/audios/.tmp/<uuid>`, `ffprobe`, gravação da Reunião `pending` com `run_id`, commit, movimento do arquivo para `/audios/<meeting_id>/original.<ext>` e aviso `MeetingCreated` pós-commit (ADR-0018).

**Acceptance criteria:**
- [x] Cada formato válido responde 201 com `id`, `title`, `original_filename`, `duration_seconds`, `created_at` e `status` `pending`; o arquivo existe em `/audios` com o conteúdo enviado e a Reunião aponta para ele (`meetings` 1, 2).
- [x] Título informado é gravado sem espaços nas pontas; sem título, ou só espaços, usa o nome original; `expected_speakers` de 1 a 20 é gravado, ausente fica vazio (`meetings` 3, 4, 5).
- [x] `MeetingCreated` sai uma vez por upload válido; com consumidor que nunca termina, a resposta ainda é 201 (`meetings` 6, 7); extensão em maiúsculas vale como minúscula (`meetings` 15).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_upload_valid.py -q`.
- [x] Gate backend. SEC-11, SEC-15, SEC-16.

**Dependencies:** Tasks 18.2, 10.1

**Files likely touched:**
- `backend/src/snook/modules/meetings/service.py`, `backend/src/snook/modules/meetings/storage.py`, `backend/src/snook/modules/meetings/api.py`
- `backend/src/snook/modules/meetings/messages.py`, `backend/tests/meetings/test_api_upload_valid.py`

**Estimated scope:** Medium

### Task 18.4: Upload recusado

**Description:** Recusas do upload com 413/422, temporário apagado em toda recusa (SEC-16).

**Acceptance criteria:**
- [x] Extensão fora da lista (422, formatos listados), arquivo sem trilha de áudio (422 "arquivo sem áudio"), mais de 2 h (422), arquivo vazio (422) (`meetings` 9, 10, 11, 13); arquivo de exatamente 2 h é aceito (`meetings` 8).
- [x] Mais de 524.288.000 bytes recebe 413 e a mensagem diz "500 MB"; exatamente 524.288.000 não é recusado (`meetings` 12; testado com `UPLOAD_MAX_BYTES` reduzido, no valor exato e um byte acima).
- [x] `expected_speakers` 0, -1, 21 e `2.5` recebem 422 (`meetings` 14); em toda recusa não fica Reunião, arquivo em `/audios`, `.tmp` nem aviso.

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_upload_refused.py -q`.
- [x] Gate backend. SEC-09, SEC-16, SEC-25.

**Dependencies:** Task 18.3

**Files likely touched:**
- `backend/src/snook/modules/meetings/service.py`, `backend/src/snook/modules/meetings/storage.py`, `backend/src/snook/modules/meetings/messages.py`
- `backend/tests/meetings/test_api_upload_refused.py`

**Estimated scope:** Medium

### Task 19.1: Listagem, detalhe e edição de título

**Description:** `GET /api/meetings`, `GET /api/meetings/{id}`, `PATCH /api/meetings/{id}` e `get_owned_meeting(uow, user_id, meeting_id)`.

**Acceptance criteria:**
- [x] Listagem devolve só as Reuniões do Usuário, da mais recente à mais antiga, com `id`, `title`, `created_at`, `duration_seconds`, `status`; detalhe soma `original_filename`, `expected_speakers`, `participants_confirmed`, `has_backlog` e, em `failed`, `failed_stage` e `error_message` (`meetings` 19, 20, 32); nenhuma resposta expõe o caminho (`meetings` 21).
- [x] `PATCH` grava o título sem espaços nas pontas e não muda status nem outros campos, em qualquer status; título vazio recebe 422 e o anterior fica (`meetings` 16, 17, 18).
- [x] `GET`, `PATCH` com `id` de outro Usuário respondem 404 sem mudar nada; sem sessão, 401 (`meetings` 31, 33; SEC-01, SEC-02).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_list_detail_title.py -q`.
- [x] Gate backend. SEC-02.

**Dependencies:** Task 18.3

**Files likely touched:**
- `backend/src/snook/modules/meetings/api.py`, `backend/src/snook/modules/meetings/service.py`, `backend/src/snook/modules/meetings/schemas.py`
- `backend/tests/meetings/test_api_list_detail_title.py`

**Estimated scope:** Medium

### Task 19.2: Exclusão segura em cascata

**Description:** `DELETE /api/meetings/{id}`: uma transação apaga a Reunião; depois do commit, `core/files.py` remove `/audios/<meeting_id>/` com as checagens de SEC-15.

**Acceptance criteria:**
- [x] Responde 204; `GET` seguinte responde 404 e o arquivo não existe em `/audios` (`meetings` 28); com registros fake de Transcrição e de User Story ligados à Reunião, nenhum resta (`meetings` 29).
- [x] Funciona em qualquer status; um processamento em andamento não recria Reunião, arquivo nem dado derivado depois da exclusão (`meetings` 30).
- [x] `DELETE` com `id` de outro Usuário responde 404 e a Reunião do outro fica intacta (`meetings` 31); sem `.tmp` nem cópia restante (SEC-24); a exclusão vai ao log (SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_delete.py -q` (inclui link simbólico e `meeting_id` forjado: recusa e log).
- [x] Gate backend. SEC-02, SEC-15, SEC-20, SEC-24.

**Dependencies:** Task 19.1

**Files likely touched:**
- `backend/src/snook/modules/meetings/api.py`, `backend/src/snook/modules/meetings/service.py`
- `backend/tests/meetings/test_api_delete.py`

**Estimated scope:** Small

### Task 20.1: Máquina de estados, "Atualizar status" e avisos com `run_id`

**Description:** `state_machine.py` com a tabela de transições do PRD, `update_status(uow, meeting_id, new_status, *, failed_stage=None, message=None)` e helper de `run_id`.

**Acceptance criteria:**
- [x] Depois de `update_status`, `GET /meetings/{id}` devolve o novo status (`meetings` 22).
- [x] A interface recusa status fora da lista, transição fora da tabela e `failed` sem etapa ou sem mensagem, e o status gravado não muda (`meetings` 23; `03-security.md` A06).
- [x] Transição que inicia trabalho novo troca o `run_id`; consumidor tem helper para ignorar `run_id` que não bate (ADR-0007).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_state_machine.py -q` (uma linha da tabela de transições por caso).
- [x] Gate backend. SEC-19.

**Dependencies:** Task 18.3

**Files likely touched:**
- `backend/src/snook/modules/meetings/state_machine.py`, `backend/src/snook/modules/meetings/service.py`
- `backend/tests/meetings/test_state_machine.py`

**Estimated scope:** Small

### Task 20.2: Marcas "Participantes confirmados" e "Backlog gravado"

**Description:** `mark_participants_confirmed(uow, id)`, `mark_backlog_saved(uow, id)` e `read_flags(uow, id)`, expostos no detalhe como booleanos.

**Acceptance criteria:**
- [x] Depois das duas marcas, `read_flags` informa as duas e `GET /meetings/{id}` devolve `participants_confirmed` e `has_backlog` verdadeiros (`meetings` 51).
- [x] As marcas continuam depois de "Tentar novamente", de regeneração e de reinício (teste simula cada um) (`meetings` 51).
- [x] As marcas entram na unidade de trabalho de quem chama, num só commit (ADR-0006).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_flags.py -q`.
- [x] Gate backend.

**Dependencies:** Task 20.1

**Files likely touched:**
- `backend/src/snook/modules/meetings/service.py`, `backend/src/snook/modules/meetings/repository.py`
- `backend/tests/meetings/test_flags.py`

**Estimated scope:** Small

### Checkpoint: Upload e estados

- [ ] Critérios 1 a 23, 28 a 33 e 51 de `01-prd/meetings.md` passam
- [ ] SEC-02, SEC-11, SEC-15, SEC-16 verificados
- [ ] `/security-review` sobre o diff

### Task 21.1: "Tentar novamente"

**Description:** `POST /api/meetings/{id}/retry`: `failed/transcription` vai para `pending`; `failed/generation` vai para `transcribed`; limpa falha, troca `run_id`, emite `RetryRequested`.

**Acceptance criteria:**
- [x] Etapa `transcription`: vai a `pending`, limpa `failed_stage` e `error_message`, emite `RetryRequested(transcription)` uma vez (`meetings` 24).
- [x] Etapa `generation`: vai a `transcribed`, limpa a falha, mantém Transcrição e Participantes, emite `RetryRequested(generation)` uma vez (`meetings` 25).
- [x] Fora de `failed` responde 409 `not_failed` sem mudar nada (`meetings` 26); o arquivo original não muda e nenhum novo envio é pedido (`meetings` 27); `id` de outro Usuário responde 404 (`meetings` 31); o retry vai ao log (SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_retry.py -q`.
- [x] Gate backend. SEC-02, SEC-20.

**Dependencies:** Tasks 20.1, 20.2

**Files likely touched:**
- `backend/src/snook/modules/meetings/api.py`, `backend/src/snook/modules/meetings/service.py`
- `backend/tests/meetings/test_api_retry.py`

**Estimated scope:** Small

### Task 21.2: Marcar interrompidas e reenfileirar no startup

**Description:** `startup.py` roda na subida, antes de aceitar requisições: marca interrompidas (Q58, Q69) e reenfileira `pending` em ordem de criação.

**Acceptance criteria:**
- [x] `processing` vai a `failed` etapa `transcription`, `generating` a `failed` etapa `generation`, ambas com "processamento interrompido" (`meetings` 44); `transcribed` com Participantes confirmados vai a `failed` etapa `generation` com a mesma mensagem (`meetings` 49).
- [x] A marcação termina antes de aceitar requisições e não emite aviso (`meetings` 45); `transcribed` sem confirmação, `pending`, `needs_split`, `done` e `failed` não mudam (`meetings` 50).
- [x] Depois da marcação, o retry funciona como nos critérios 24 e 25 (`meetings` 46); `pending` é reenfileirado em ordem de criação (ADR-0007).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_startup.py -q` (grava no SQLite e sobe a app de novo com `TestClient`).
- [x] Gate backend. SEC-19.

**Dependencies:** Tasks 21.1, 3.5

**Files likely touched:**
- `backend/src/snook/modules/meetings/startup.py`, `backend/src/snook/main.py`
- `backend/tests/meetings/test_startup.py`

**Estimated scope:** Small

### Task 22.1: Componente `ConsentNotice` e constante do texto

**Description:** `ConsentNotice` em `components/surfaces/ConsentNotice/` com `messages.ts` e `CONSENT_NOTICE_TEXT`, só texto (Q71, Q72).

**Acceptance criteria:**
- [x] `CONSENT_NOTICE_TEXT` é exatamente: "Antes de gravar ou enviar, obtenha o consentimento de todos os participantes da reunião (LGPD). O áudio fica só neste servidor; o texto da transcrição vai ao provedor de LLM ativo." (`meetings` 52).
- [x] O componente mostra esse texto, sem checkbox, sem confirmação e sem bloquear nada (Q71).
- [x] O texto existe em um único lugar do código (teste que busca a frase em `src/` e acha só `messages.ts`).

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces/ConsentNotice`.
- [x] Gate frontend. Mudar o texto exige aprovação ("Perguntar antes").

**Dependencies:** Task 5.4

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/ConsentNotice/ConsentNotice.tsx`, `frontend/src/components/surfaces/ConsentNotice/messages.ts`
- `frontend/src/components/surfaces/ConsentNotice/ConsentNotice.test.tsx`

**Estimated scope:** Small

### Task 22.2: Tela de upload

**Description:** Tela de upload com área de soltar arquivo (mouse-tracking), título pré-preenchido, `expected_speakers`, validação no navegador, progresso e `ConsentNotice` junto do botão de envio.

**Acceptance criteria:**
- [x] Aceita arquivo, título e número de participantes e mostra envio em andamento (`meetings` 35); ao escolher o arquivo, o título recebe o nome dele, editável (`meetings` 36).
- [x] Recusa antes de enviar extensão fora da lista ou mais de 524.288.000 bytes, com a mesma mensagem da API (`meetings` 37); erros da API aparecem (`meetings` 38); depois do upload leva ao detalhe (`meetings` 39).
- [x] O aviso mostra exatamente `CONSENT_NOTICE_TEXT` junto do botão de envio (`meetings` 52); o mouse-tracking só liga com `(hover: hover) and (pointer: fine)` e sem movimento reduzido.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [ ] Gate frontend. Manual: quadros do spotlight abaixo de 16 ms no DevTools Performance (NFR-08).

**Dependencies:** Tasks 22.1, 18.4, 5.3, 10.2

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `emilkowalski-motion`, `animate`

**Files likely touched:**
- `frontend/src/features/meetings/UploadPage.tsx`, `frontend/src/features/meetings/useUpload.ts`, `frontend/src/features/meetings/validateFile.ts`
- `frontend/src/features/meetings/UploadPage.test.tsx`

**Estimated scope:** Medium

### Task 22.3: Lista e detalhe com polling e edição de título

**Description:** Lista de Reuniões e detalhe com `StatusBadge`, polling a cada 3 s nos status ativos e edição de título.

**Acceptance criteria:**
- [x] Lista e detalhe atualizam o status sem recarregar enquanto `pending`, `processing`, `generating`, ou `transcribed` com `participants_confirmed` verdadeiro; fora disso não há polling (`meetings` 40).
- [x] O detalhe permite editar o título (`meetings` 41).
- [x] Mudança de status é anunciada em `aria-live`; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings` (relógio falso do Vitest).
- [x] Gate frontend.

**Dependencies:** Tasks 22.2, 19.1

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/meetings/MeetingListPage.tsx`, `frontend/src/features/meetings/MeetingDetailPage.tsx`, `frontend/src/features/meetings/useMeetings.ts`
- `frontend/src/features/meetings/MeetingListPage.test.tsx`, `frontend/src/features/meetings/MeetingDetailPage.test.tsx`

**Estimated scope:** Medium

### Task 22.4: Detalhe: "Tentar novamente" e exclusão

**Description:** Botão "Tentar novamente" em `failed` e diálogo de exclusão com confirmação.

**Acceptance criteria:**
- [x] Em `failed`, mostra o motivo e "Tentar novamente"; o botão não aparece em outro status; com `has_backlog` verdadeiro, pede confirmação com o aviso de que as edições do backlog se perdem se a nova geração terminar bem (`meetings` 42).
- [x] Excluir pede confirmação e avisa que o áudio e o backlog serão apagados (`meetings` 43).
- [ ] Diálogos de nova tentativa e de exclusão usam `DialogSurface` opaco, sem `GlassPanel` (ADR-0024, "Vidro"; reaberto pela Fase 9, fecha na Task 52.16); `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [x] Gate frontend.

**Dependencies:** Tasks 22.3, 21.1, 19.2

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/meetings/RetryButton.tsx`, `frontend/src/features/meetings/DeleteMeetingDialog.tsx`, `frontend/src/features/meetings/MeetingDetailPage.tsx`
- `frontend/src/features/meetings/RetryButton.test.tsx`

**Estimated scope:** Small

### Checkpoint: `meetings`

- [ ] Critérios 1 a 46 e 49 a 52 de `01-prd/meetings.md` cobertos (34 manual: `docker compose down` sem `-v` e `up` mantém Reuniões e `./audios`); 47 e 48 ficam no checkpoint `screen-recording`
- [ ] Critério 52: `ConsentNotice` mostra o texto exato da constante junto do botão de envio
- [ ] Checagem de UI; `impeccable-design-polish` nas telas de upload, lista e detalhe
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 3A: `diarized-transcription` (paralela à 3B)

### Task 23.1: Segmentos, interfaces de engine e fakes

**Description:** Tabela `transcript_segments` (migração `0004_diarized_transcription_segments`), Protocols de tratamento, diarização e transcrição, e fakes configuráveis (`engines/fakes.py`).

**Acceptance criteria:**
- [x] Segmentos têm `speaker_label`, `start_seconds`, `end_seconds`, `text`, `position`, com `ON DELETE CASCADE` a partir da Reunião (`04-data-model.md`).
- [x] Os fakes simulam sucesso, falha, "nenhuma fala" e `HF_TOKEN` inválido, e só terminam quando o teste libera.
- [x] `pytest` roda sem GPU, sem rede e sem modelo (transversal 18, RT-13).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_storage_fakes.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend.

**Dependencies:** Task 20.1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/models.py`, `backend/src/snook/modules/diarized_transcription/repository.py`, `backend/src/snook/modules/diarized_transcription/engines/fakes.py`
- `backend/alembic/versions/0004_diarized_transcription_segments.py`, `backend/tests/diarized_transcription/test_storage_fakes.py`

**Estimated scope:** Medium

### Task 23.2: Dispatcher e pipeline até `transcribed`

**Description:** Consome `MeetingCreated` e `RetryRequested(transcription)`; leva a Reunião a `processing`, roda o pipeline (executor injetável; fake síncrono nos testes) e grava segmentos e `transcribed` numa transação que confere Reunião e `run_id`.

**Acceptance criteria:**
- [x] `pending` vai a `processing` antes do trabalho e a `transcribed` ao fim; "Nova tentativa" descarta dado parcial e reprocessa do original (`diarized-transcription` 1, 2); aviso com a Reunião fora de `pending` é ignorado (`diarized-transcription` 3); o original não muda (`diarized-transcription` 4).
- [x] Falha em qualquer etapa leva a `failed` etapa `transcription` com mensagem pt-BR e nenhum segmento parcial (`diarized-transcription` 14); `HF_TOKEN` ausente ou sem aceite dá mensagem que cita `HF_TOKEN` e o aceite, sem o valor (`diarized-transcription` 15); sem fala dá "nenhuma fala detectada" (`diarized-transcription` 16).
- [x] Reunião excluída durante o processamento: nenhum segmento nem áudio tratado é gravado depois (`diarized-transcription` 17); `expected_speakers` chega à diarização, ausente roda sem número, e o idioma é sempre pt-BR (`diarized-transcription` 7, 8); a exceção no consumidor vira `failed`, nunca status preso (SEC-19).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_api_pipeline.py -q`.
- [x] Gate backend. SEC-19, SEC-20 (sem texto da Transcrição em log).

**Dependencies:** Tasks 23.1, 21.1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/dispatcher.py`, `backend/src/snook/modules/diarized_transcription/pipeline.py`, `backend/src/snook/modules/diarized_transcription/service.py`
- `backend/src/snook/modules/diarized_transcription/messages.py`, `backend/tests/diarized_transcription/test_api_pipeline.py`

**Estimated scope:** Medium

### Task 23.3: Limite por Usuário e capacidade global

**Description:** O dispatcher pega a `pending` mais antiga de Usuário abaixo de `TRANSCRIPTION_MAX_PER_USER`, com `TRANSCRIPTION_WORKERS` de capacidade global (ADR-0010).

**Acceptance criteria:**
- [x] Com limite N, um Usuário nunca tem mais de N Reuniões em `processing` (`diarized-transcription` 28).
- [x] Reunião acima do limite fica em `pending` e começa quando outra do mesmo Usuário sai de `processing`, na ordem de criação (`diarized-transcription` 29).
- [x] Com `TRANSCRIPTION_WORKERS` 2 e `TRANSCRIPTION_MAX_PER_USER` 1, o limite de um Usuário não atrasa o outro (`diarized-transcription` 30).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_api_limits.py -q` (fake que só termina quando o teste libera).
- [x] Gate backend. SEC-25.

**Dependencies:** Task 23.2

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/dispatcher.py`
- `backend/tests/diarized_transcription/test_api_limits.py`

**Estimated scope:** Small

### Task 24: Junção de turnos e trechos em segmentos

**Description:** `merge.py`: maior sobreposição de tempo, turno mais próximo quando não há sobreposição, fusão de trechos seguidos do mesmo speaker com pausa até 1,0 s (ADR-0014); interfaces "Segmentos" e "Speakers".

**Acceptance criteria:**
- [x] Trecho dentro de um turno recebe o speaker dele; trecho fora de qualquer turno recebe o do turno mais próximo; nenhum segmento fica sem speaker (`diarized-transcription` 9, 10).
- [x] Cada segmento cumpre `0 <= start < end <= duração` e `text` não vazio; saem em ordem crescente de `start_seconds` (`diarized-transcription` 11, 12).
- [x] "Speakers" devolve exatamente os rótulos dos segmentos, com tempo total de fala e maior segmento (`diarized-transcription` 13).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_merge.py -q` (tabelas pequenas: dentro, entre, fora de turno).
- [x] Gate backend.

**Dependencies:** Task 23.2

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/merge.py`, `backend/src/snook/modules/diarized_transcription/service.py`
- `backend/tests/diarized_transcription/test_merge.py`

**Estimated scope:** Small

### Task 25.1: Tratamento de áudio com ffmpeg

**Description:** `engines/audio.py`: mono 16 kHz, passa-alta 80 Hz, `loudnorm`, FLAC em `/audios/.tmp/<uuid>.flac`, por `subprocess.run([...], shell=False)` com timeout (ADR-0014).

**Acceptance criteria:**
- [x] Uma fixture curta de cada formato (mp3, wav, m4a, ogg, webm, mp4) é tratada e chega a `transcribed` sem ação manual (`diarized-transcription` 5; transversal 13).
- [x] O comando usa só caminhos do servidor e tem timeout; timeout vira falha de tratamento (SEC-11, SEC-25).
- [x] Saída é FLAC mono 16 kHz, conferido por `ffprobe`.

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_audio_engine.py -q` (ffmpeg real, sem modelos).
- [x] Gate backend. SEC-11, SEC-25.

**Dependencies:** Task 23.2

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/engines/audio.py`
- `backend/tests/diarized_transcription/test_audio_engine.py`

**Estimated scope:** Small

### Task 25.2: Interface "Áudio tratado"

**Description:** `treated_audio_clip(meeting_id, start, end) -> bytes` e movimento do `treated.flac` para o diretório da Reunião depois do commit.

**Acceptance criteria:**
- [x] Depois de `transcribed`, o áudio tratado existe em `/audios/<meeting_id>/treated.flac` e o trecho devolvido para um intervalo tem a duração do intervalo (`diarized-transcription` 6).
- [x] O movimento ocorre só depois do commit; se a Reunião foi excluída, o temporário é apagado e nada fica (`diarized-transcription` 17; `02-architecture.md`, "Exclusão").
- [x] "Nova tentativa" descarta o áudio tratado anterior antes de reprocessar (`diarized-transcription` 2).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_treated_audio.py -q`.
- [x] Gate backend. SEC-15, SEC-24.

**Dependencies:** Task 25.1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/service.py`, `backend/src/snook/modules/diarized_transcription/pipeline.py`
- `backend/tests/diarized_transcription/test_treated_audio.py`

**Estimated scope:** Small

### Checkpoint: Pipeline de transcrição com fakes

- [ ] Critérios 1 a 17 e 28 a 30 de `01-prd/diarized-transcription.md` passam (18 a 20 no checkpoint `diarized-transcription`, depois da rota `GET /transcript`)
- [ ] Exclusão durante processamento não recria dados
- [ ] `/security-review` sobre o diff

### Task 26.1: Engine faster-whisper

**Description:** `engines/whisper.py` com `large-v3-turbo` int8, idioma `pt`, revisão fixa e modelos em `/models`.

**Acceptance criteria:**
- [x] Transcreve sempre em `pt`, sem detecção automática (`diarized-transcription` 8).
- [x] O modelo vem do repositório oficial e da revisão fixa de `WHISPER_REVISION`; sem revisão configurada, o settings falha (SEC-22).
- [x] Com `MODELS_OFFLINE=true`, não faz acesso à rede (transversal 14).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_whisper_settings.py -q` (settings e fábrica; sem modelo).
- [ ] Suíte `models_real` com áudio curto: `cd backend && uv run pytest -m models_real tests/models_real/test_whisper.py` (manual).
- [x] Gate backend. SEC-22.

**Dependencies:** Task 23.2, Task 1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/engines/whisper.py`, `backend/src/snook/core/settings.py`
- `backend/tests/diarized_transcription/test_whisper_settings.py`, `backend/tests/models_real/test_whisper.py`

**Estimated scope:** Small

### Task 26.2: Engine Pyannote

**Description:** `engines/pyannote.py` com `pyannote/speaker-diarization-3.1`, revisão fixa, `expected_speakers` como dica e mensagens de `HF_TOKEN`.

**Acceptance criteria:**
- [x] Recebe `expected_speakers` quando informado e roda sem número fixo quando ausente (`diarized-transcription` 7).
- [x] `HF_TOKEN` ausente, inválido ou sem aceite dos termos vira falha com mensagem que cita `HF_TOKEN` e o aceite, sem o valor (`diarized-transcription` 15; SEC-20).
- [x] Revisão fixa obrigatória em settings (SEC-22); `HF_TOKEN` nunca vai a log.

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_pyannote_settings.py -q`.
- [ ] Manual: `cd backend && uv run pytest -m models_real tests/models_real/test_pyannote.py`.
- [x] Gate backend. SEC-20, SEC-22.

**Dependencies:** Task 26.1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/engines/pyannote.py`, `backend/src/snook/core/settings.py`
- `backend/tests/diarized_transcription/test_pyannote_settings.py`, `backend/tests/models_real/test_pyannote.py`

**Estimated scope:** Small

### Task 26.3: Cache de modelos, `download-models` e subprocessos

**Description:** Comando `python -m snook.cli download-models`, cache em `/models` (volume `snook-models`) e transcrição em `ProcessPoolExecutor` com `spawn` (ADR-0007, ADR-0014).

**Acceptance criteria:**
- [x] O download usa repositório e revisão fixos; modelos ficam em `/models` e a segunda execução não baixa de novo (`diarized-transcription` 23; SEC-22).
- [x] O subprocesso recebe só caminho de arquivo e parâmetros e não toca o banco (`03-security.md`, fronteira 3).
- [x] Durante o processamento, nenhuma chamada de rede envia áudio para fora do servidor (`diarized-transcription` 21; RT-06).

**Verification:**
- [x] `cd backend && uv run pytest tests/cli/test_download_models.py tests/diarized_transcription/test_subprocess_boundary.py -q` (fakes).
- [ ] Manual: `docker compose exec backend python -m snook.cli download-models`; `docker compose down` sem `-v`, `up`, e a segunda execução não baixa (critério 23).
- [x] Gate backend. SEC-22.

**Dependencies:** Tasks 26.2, 6.3

**Files likely touched:**
- `backend/src/snook/cli.py`, `backend/src/snook/modules/diarized_transcription/dispatcher.py`
- `backend/tests/cli/test_download_models.py`, `backend/tests/diarized_transcription/test_subprocess_boundary.py`

**Estimated scope:** Medium

### Task 26.4: Perfil GPU e suíte `models_real`

**Description:** Perfil `gpu` do compose, `Dockerfile.gpu` usado de fato e marker `models_real` com áudio curto pt-BR de duas vozes.

**Acceptance criteria:**
- [ ] Sem o perfil GPU, o processamento roda em CPU; com o perfil na máquina NVIDIA, roda na GPU; a forma da Transcrição é a mesma (`diarized-transcription` 24, manual).
- [ ] Com os modelos em cache e a rede do container bloqueada, a Reunião chega a `transcribed` (`diarized-transcription` 22, manual; transversal 14).
- [x] `uv run pytest` padrão não coleta `models_real` (transversal 18).

**Verification:**
- [ ] `cd backend && uv run pytest` (sem `models_real`); `cd backend && uv run pytest -m models_real` (manual, com modelos).
- [ ] Manual: `COMPOSE_PROFILES=gpu docker compose up -d` e `docker compose exec backend-gpu nvidia-smi`.

**Dependencies:** Tasks 26.3, 6.1

**Files likely touched:**
- `compose.yaml`, `backend/Dockerfile.gpu`, `backend/pyproject.toml`
- `backend/tests/models_real/conftest.py`, `backend/tests/models_real/test_pipeline_real.py`

**Estimated scope:** Medium

### Task 27.1: `GET /meetings/{id}/transcript`

**Description:** Rota da Transcrição, com segmentos em ordem.

**Acceptance criteria:**
- [x] Em `transcribed` ou posterior, devolve os segmentos em ordem com `speaker_label`, `start_seconds`, `end_seconds`, `text` (`diarized-transcription` 18).
- [x] Em `pending`, `processing` ou `failed` etapa `transcription` responde 409 `transcript_not_ready` (`diarized-transcription` 19).
- [x] Reunião de outro Usuário responde 404; sem sessão, 401 (`diarized-transcription` 20; SEC-02).

**Verification:**
- [x] `cd backend && uv run pytest tests/diarized_transcription/test_api_transcript.py -q`.
- [x] Gate backend. SEC-02.

**Dependencies:** Tasks 24, 19.1

**Files likely touched:**
- `backend/src/snook/modules/diarized_transcription/api.py`, `backend/src/snook/modules/diarized_transcription/service.py`
- `backend/tests/diarized_transcription/test_api_transcript.py`

**Estimated scope:** Small

### Task 27.2: Tela da Transcrição com lista virtualizada

**Description:** Tela da Transcrição com `@tanstack/react-virtual`, instante `hh:mm:ss` em mono tabular e status antes de `transcribed`.

**Acceptance criteria:**
- [x] Mostra segmentos em ordem, cada um com instante de início em `hh:mm:ss`, speaker e texto (`diarized-transcription` 25).
- [x] Antes de `transcribed`, mostra o status da Reunião em vez do texto (`diarized-transcription` 27).
- [x] Com Transcrição de 2 h de fixture, mantém no DOM só os segmentos perto da área visível; rolar até o fim mostra o último com instante, speaker e texto (`diarized-transcription` 31; NFR-07). Texto de segmento renderiza escapado (SEC-12).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/diarized-transcription`.
- [x] Gate frontend. SEC-12.

**Dependencies:** Tasks 27.1, 22.3

**Skills:** `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/diarized-transcription/TranscriptPage.tsx`, `frontend/src/features/diarized-transcription/useTranscript.ts`, `frontend/src/features/diarized-transcription/fixtures/transcript-2h.ts`
- `frontend/src/features/diarized-transcription/TranscriptPage.test.tsx`

**Estimated scope:** Medium

### Task 27.3: Nome do Participante na Transcrição

**Description:** A tela junta os segmentos com `GET /meetings/{id}/participants` e mostra o nome atual do Participante.

**Acceptance criteria:**
- [x] Enquanto os speakers não têm nome, mostra o rótulo (`SPEAKER_00`); depois da nomeação, mostra o nome atual do Participante (`diarized-transcription` 26).
- [x] Participante renomeado aparece sem passo extra (nomes lidos na hora; `05-api.md`).
- [x] Resposta sem Participantes (404 ou lista vazia) não quebra a tela.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/diarized-transcription` (MSW). A rota real de Participantes só existe depois da Task 32.2; reconferir no checkpoint `participants`.
- [x] Gate frontend.

**Dependencies:** Task 27.2

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/diarized-transcription/TranscriptPage.tsx`, `frontend/src/features/diarized-transcription/useParticipantNames.ts`
- `frontend/src/features/diarized-transcription/TranscriptPage.test.tsx`

**Estimated scope:** Small

### Checkpoint: `diarized-transcription`

- [ ] Critérios 18 a 20 de `01-prd/diarized-transcription.md` passam pela rota `GET /transcript`
- [ ] Critérios 21 a 24 na suíte `models_real`, rodada à mão; critério 22 com rede do container bloqueada; critério 24 manual com GPU NVIDIA
- [ ] Critérios 25 a 27 e 31 cobertos por Vitest
- [ ] SEC-22 verificado: download de modelo exige repositório e revisão fixos
- [ ] Checagem de UI com Transcrição de 2 h de fixture (NFR-04, NFR-07); `impeccable-design-polish` na tela da Transcrição
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 3B: `screen-recording` (paralela à 3A; depende das Tasks 18 e 22)

### Task 28.1: Interfaces do navegador, fakes e checagens de suporte

**Description:** `DisplayCapture`, `MicCapture`, `Recorder`, `Clock` e `SecureContext` como interfaces com fakes (ADR-0015), mais checagem de `window.isSecureContext`, de `getDisplayMedia` e de `MediaRecorder` com webm.

**Acceptance criteria:**
- [x] Fora de contexto seguro, o botão "Gravar reunião" fica desabilitado com mensagem que diz que a gravação exige HTTPS ou `localhost`, que o Operador pode ativar o perfil `lan` e que o envio de arquivo continua disponível; essa mensagem tem prioridade sobre a do critério 22 (`screen-recording` 27).
- [x] Em `http://localhost` e em `https://`, a checagem de contexto seguro não bloqueia (fake) (`screen-recording` 28).
- [x] Sem `getDisplayMedia` ou sem `MediaRecorder` com webm, o botão fica desabilitado com mensagem que indica Chrome ou Edge e lembra o envio de arquivo (`screen-recording` 22); em navegador com as APIs que não é Chrome nem Edge, avisa sem bloquear (`screen-recording` 23).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Gate frontend.

**Dependencies:** Tasks 4.3, 22.1

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/screen-recording/capture/interfaces.ts`, `frontend/src/features/screen-recording/capture/fakes.ts`, `frontend/src/features/screen-recording/support.ts`
- `frontend/src/features/screen-recording/support.test.ts`

**Estimated scope:** Small

### Task 28.2: Captura de tela e microfone e combinações de fontes

**Description:** Fluxo que pede a tela com áudio antes do microfone, e decide entre gravar, avisar ou recusar conforme as fontes.

**Acceptance criteria:**
- [x] "Gravar reunião" pede compartilhamento de tela ou aba com áudio e acesso ao microfone (`screen-recording` 2); com as duas fontes, grava sem aviso (`screen-recording` 3, parte do fluxo).
- [x] Sem som da tela: aviso nomeia a fonte ausente com "Gravar só com o microfone" e "Cancelar"; sem microfone: aviso com "Gravar só com o som da tela" e "Cancelar"; nada é gravado antes da escolha (`screen-recording` 4, 5).
- [x] Sem nenhuma fonte: recusa com mensagem, não grava e não cria Reunião (`screen-recording` 6); cancelar encerra tela e microfone (`screen-recording` 7).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Gate frontend.

**Dependencies:** Task 28.1

**Skills:** `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/useRecordingSession.ts`, `frontend/src/features/screen-recording/SourceWarningDialog.tsx`
- `frontend/src/features/screen-recording/useRecordingSession.test.tsx`

**Estimated scope:** Medium

### Task 28.3: Mistura em trilha única de áudio

**Description:** Mistura de som da tela e microfone pela Web Audio API numa trilha única, `audio/webm;codecs=opus` a 64 kbps, sem trilha de vídeo (ADR-0015).

**Acceptance criteria:**
- [x] O arquivo final tem só trilha de áudio, sem vídeo, com os dois sons misturados numa trilha (`screen-recording` 3, 9).
- [x] A taxa de 64 kbps mantém 1h59m50s abaixo de 524.288.000 bytes (projeção em teste) (`screen-recording` 24).
- [ ] Em Chrome e Edge, compartilhar uma aba com áudio produz som da aba e microfone (`screen-recording` 21, checklist manual).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording` (fake de `AudioContext` e `Recorder`).
- [ ] Manual: gravar 1 min em Chrome e Edge e conferir `ffprobe` (uma trilha de áudio, nenhuma de vídeo).
- [x] Gate frontend.

**Dependencies:** Task 28.2

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/screen-recording/capture/mixer.ts`, `frontend/src/features/screen-recording/capture/recorder.ts`
- `frontend/src/features/screen-recording/capture/mixer.test.ts`

**Estimated scope:** Small

### Task 29.1: Tempo decorrido, "Parar" e parada automática

**Description:** Tela de gravação com cronômetro (mono tabular), "Parar", parada em 1h59m50s, fim do compartilhamento pelo navegador e confirmação ao sair.

**Acceptance criteria:**
- [x] Mostra o tempo decorrido e o botão "Parar"; ao parar, encerra tela e microfone (`screen-recording` 8, 13).
- [x] Aos 1h59m50s (relógio falso) a gravação para sozinha e segue para o envio com aviso de limite; o arquivo tem no máximo 1h59m50s (`screen-recording` 10).
- [x] Encerrar o compartilhamento pela barra do navegador equivale a "Parar" (`screen-recording` 11); sair ou fechar a página durante a gravação ou antes do envio pede confirmação (`screen-recording` 12).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Gate frontend.

**Dependencies:** Task 28.3

**Skills:** `shadcn`, `frontend-ui-engineering`, `ui-animation`

**Files likely touched:**
- `frontend/src/features/screen-recording/RecordingPanel.tsx`, `frontend/src/features/screen-recording/useElapsed.ts`, `frontend/src/features/screen-recording/useLeaveGuard.ts`
- `frontend/src/features/screen-recording/RecordingPanel.test.tsx`

**Estimated scope:** Medium

### Task 29.2: Tela de envio da gravação e reenvio

**Description:** Nome `gravacao-AAAA-MM-DD-HHhMM.webm` (hora local do início), campo de título, `expected_speakers`, envio por `POST /meetings` e "Tentar de novo".

**Acceptance criteria:**
- [x] O nome do arquivo segue o padrão com data e hora locais do início; o título vem preenchido e editável; há campo opcional de participantes com a validação do upload (`screen-recording` 14, 15, 16).
- [x] O envio cria a Reunião com o título da tela e leva ao detalhe; a Reunião aparece como `pending` (`screen-recording` 17, 20); recusa do servidor aparece com a mensagem da API (`screen-recording` 18).
- [x] Em falha de rede, mostra o erro e "Tentar de novo", que reenvia a mesma gravação sem gravar de novo enquanto a página está aberta (`screen-recording` 19).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording` (MSW).
- [x] Gate frontend.

**Dependencies:** Tasks 29.1, 18.4

**Skills:** `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/SendRecordingPage.tsx`, `frontend/src/features/screen-recording/fileName.ts`, `frontend/src/features/screen-recording/useSendRecording.ts`
- `frontend/src/features/screen-recording/SendRecordingPage.test.tsx`

**Estimated scope:** Medium

### Task 29.3: Painel de vidro, indicador, entrada e `ConsentNotice`

**Description:** Painel flutuante de vidro, indicador com pulso (fixo com movimento reduzido), opção "Gravar reunião" ao lado de "enviar arquivo" e `ConsentNotice` reaproveitado.

**Acceptance criteria:**
- [x] A área autenticada oferece duas entradas: enviar arquivo e "Gravar reunião" (`screen-recording` 1).
- [x] O aviso mostra exatamente `CONSENT_NOTICE_TEXT`, do mesmo `ConsentNotice` da Task 22.1, junto do botão "Gravar reunião", sem pedir confirmação nem bloquear (`screen-recording` 26; teste compara com a constante).
- [x] O pulso para com `prefers-reduced-motion`; o painel usa `GlassPanel` com fallback opaco e conta no máximo 3 vidros por tela (NFR-06).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Gate frontend.

**Dependencies:** Tasks 29.2, 5.2, 22.1

**Skills:** `shadcn`, `high-end-visual-design`, `frontend-ui-engineering`, `ui-animation`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/RecordPage.tsx`, `frontend/src/features/screen-recording/RecordingIndicator.tsx`, `frontend/src/app/routes.tsx`
- `frontend/src/features/screen-recording/RecordPage.test.tsx`

**Estimated scope:** Medium

### Task 30.1: Fixture webm do `MediaRecorder`

**Description:** Fixture webm só de áudio, sem duração no cabeçalho, no formato produzido pela gravação (`audio/webm;codecs=opus`).

**Acceptance criteria:**
- [x] A fixture é gerada a partir do gravador real (Chrome ou Edge) ou reproduz seu muxing, e `ffprobe` não acha `format.duration` no cabeçalho (`screen-recording` 25; Q61).
- [x] A fixture tem uma só trilha de áudio, nenhuma de vídeo, e é curta (poucos segundos), sem voz de terceiros nem dado pessoal.
- [x] Um script documentado registra como regenerá-la.

**Verification:**
- [x] `ffprobe -v error -show_entries format=duration -of csv=p=0 backend/tests/fixtures/audio/recorder.webm` não imprime duração (ou imprime `N/A`).
- [x] `cd backend && uv run pytest tests/meetings/test_fixture_recorder_webm.py -q`.

**Dependencies:** Task 18.1

**Files likely touched:**
- `backend/tests/fixtures/audio/recorder.webm`, `backend/tests/fixtures/audio/README.md`, `backend/tests/meetings/test_fixture_recorder_webm.py`

**Estimated scope:** Small

### Task 30.2: Leitura de duração do webm no servidor

**Description:** `media_probe.py` lê a duração pelo último pacote quando o webm não traz duração no cabeçalho.

**Acceptance criteria:**
- [x] `POST /meetings` aceita o webm da fixture e `duration_seconds` recebe a duração real, com erro máximo de 1 s (`meetings` 47; `screen-recording` 25).
- [x] Um webm desse tipo com mais de 2 h é recusado como no critério 11, sem arquivo grande (leitura de duração atrás de interface) (`meetings` 48).
- [x] O comando de leitura segue sem shell e com caminho do servidor (SEC-11).

**Verification:**
- [x] `cd backend && uv run pytest tests/meetings/test_api_upload_webm.py -q`.
- [x] Gate backend. SEC-11, SEC-16.

**Dependencies:** Tasks 30.1, 18.4

**Files likely touched:**
- `backend/src/snook/modules/meetings/media_probe.py`
- `backend/tests/meetings/test_api_upload_webm.py`

**Estimated scope:** Small

### Checkpoint: `screen-recording`

- [ ] Critérios de `01-prd/screen-recording.md` cobertos por Vitest; checklist manual em Chrome e Edge no Windows e no Fedora
- [x] Critério 26: mesmo `ConsentNotice` e mesmo texto do `meetings` critério 52
- [ ] Critérios 27 e 28: botão desabilitado fora de contexto seguro (Vitest); gravação em `https://` do perfil `lan` (checklist manual)
- [ ] Critério transversal 22 (checagem manual): gravação de tela funciona num cliente da rede que confia na CA local, pelo perfil `lan` (`08-deployment.md`, "Perfil lan")
- [x] Critérios 47 e 48 de `meetings` passam
- [x] Checagem de UI (painel de vidro e indicador com movimento reduzido); `impeccable-design-polish` nas telas de gravação
- [x] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 4: `participants`

### Task 31.1: `GET /meetings/{id}/speakers`

**Description:** Lista de speakers com tempo total de fala.

**Acceptance criteria:**
- [x] Em `transcribed`, devolve cada `speaker_label` uma vez, com o tempo total de fala (`participants` 1).
- [x] Reunião de outro Usuário responde 404; sem sessão, 401 (`participants` 23, 24; SEC-02).
- [x] Fora de `transcribed` e posteriores responde 409 (`05-api.md`).

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_api_speakers.py -q`.
- [x] Gate backend (adiciona `participants` ao grafo do `lint-imports`). SEC-02.

**Dependencies:** Tasks 24, 19.1

**Files likely touched:**
- `backend/src/snook/modules/participants/api.py`, `backend/src/snook/modules/participants/service.py`, `backend/pyproject.toml`
- `backend/tests/participants/test_api_speakers.py`

**Estimated scope:** Small

### Task 31.2: Amostra de voz

**Description:** `GET /meetings/{id}/speakers/{speaker_label}/sample`: `audio/wav` de até 10 s, a partir do maior segmento, sob demanda e sem cache.

**Acceptance criteria:**
- [x] A amostra tem no máximo 10 s e vem do maior segmento do speaker, a partir do áudio tratado (`participants` 2); começa no início do maior segmento, e em empate vale o que começa antes (`participants` 3).
- [x] Segmento menor que 10 s gera amostra com a duração dele (`participants` 4).
- [x] Speaker inexistente responde 404 (`participants` 5); `speaker_label` é validado e nenhum caminho interno vaza (SEC-09, `03-security.md` "Never").

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_api_sample.py -q` (fake de áudio tratado; confere o intervalo pedido e a duração).
- [x] Gate backend. SEC-02, SEC-09.

**Dependencies:** Tasks 31.1, 25.2

**Files likely touched:**
- `backend/src/snook/modules/participants/api.py`, `backend/src/snook/modules/participants/service.py`
- `backend/tests/participants/test_api_sample.py`

**Estimated scope:** Small

### Task 32.1: Modelo de Participantes e migração 0005

**Description:** Tabelas `participants` e `speaker_links` (migração `0005_participants`) com repositório.

**Acceptance criteria:**
- [x] `participants` e `speaker_links` ficam ligados à Reunião com `ON DELETE CASCADE`; um `speaker_label` liga a um só Participante (`04-data-model.md`).
- [x] Nome limitado a 100 caracteres (`05-api.md`).
- [x] `alembic upgrade head` roda sobre as revisões anteriores.

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_storage.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend.

**Dependencies:** Task 31.1

**Files likely touched:**
- `backend/src/snook/modules/participants/models.py`, `backend/src/snook/modules/participants/repository.py`
- `backend/alembic/versions/0005_participants.py`, `backend/tests/participants/test_storage.py`

**Estimated scope:** Small

### Task 32.2: Nomeação: validação, junção por nome e `GET /participants`

**Description:** `PUT /meetings/{id}/participants` valida e grava Participantes e vínculos; `GET /meetings/{id}/participants` lista; interface "Participante de um speaker".

**Acceptance criteria:**
- [x] Um nome por speaker grava Participantes e vínculos e responde com eles (`participants` 6); nomes iguais, sem diferenciar caixa e espaços nas pontas, ligam a um só Participante, e o nome gravado é o primeiro informado aparado (`participants` 7).
- [x] Speaker sem nome, vazio ou só de espaços, e `speaker_label` inexistente recebem 422 sem gravar nada (`participants` 8, 9); `PUT` fora de `transcribed` recebe 409 (`participants` 12); segundo `PUT` com Participantes confirmados recebe 409 e os nomes não mudam, inclusive depois do retry da geração (`participants` 13).
- [x] `GET` devolve `id`, `name` e os `speaker_label` de cada Participante (`participants` 14); "Participante de um speaker" devolve o mesmo Participante para dois speakers juntados (`participants` 15); 404/401 conforme isolamento (`participants` 23, 24).

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_api_participants.py -q`.
- [x] Gate backend. SEC-02, SEC-09.

**Dependencies:** Task 32.1

**Files likely touched:**
- `backend/src/snook/modules/participants/api.py`, `backend/src/snook/modules/participants/service.py`, `backend/src/snook/modules/participants/schemas.py`
- `backend/tests/participants/test_api_participants.py`

**Estimated scope:** Medium

### Task 32.3: Confirmação: provedor ativo, marca e aviso na mesma transação

**Description:** O `PUT` exige provedor ativo, grava nomes e chama `mark_participants_confirmed` no mesmo commit, e publica `ParticipantsConfirmed` só depois do commit.

**Acceptance criteria:**
- [x] Depois da confirmação, o aviso sai uma única vez com o `id` e `read_flags` informa Participantes confirmados; se a gravação falha, a marca não é registrada e nenhum aviso sai (`participants` 10).
- [x] Sem provedor ativo, o pedido recebe 409 `no_active_provider` com mensagem que aponta para a tela de configurações; nada é gravado, nenhum aviso sai e a Reunião continua em `transcribed` (`participants` 11).
- [x] Depois de retry da geração e de regeneração, Participantes e vínculos continuam os mesmos (`participants` 16).

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_api_confirm.py -q` (consumidor fake do aviso; "Provedor ativo" fake).
- [x] Gate backend. SEC-02, SEC-20.

**Dependencies:** Tasks 32.2, 16.1, 20.2

**Files likely touched:**
- `backend/src/snook/modules/participants/service.py`, `backend/src/snook/modules/participants/api.py`
- `backend/tests/participants/test_api_confirm.py`

**Estimated scope:** Small

### Task 33: Interface "Renomear Participante"

**Description:** `rename(uow, meeting_id, participant_id, new_name, before_absorb=None) -> RenameResult` com união por nome igual (Q55).

**Acceptance criteria:**
- [x] Nome novo que não coincide com outro mantém o mesmo `id` e os vínculos e não informa união (`participants` 17); nome igual ao de outro Participante une os dois: sobrevive o que já tinha o nome, os vínculos passam a ele, o renomeado deixa de existir e a interface informa o `id` absorvido (`participants` 18).
- [x] Nome vazio ou só de espaços, e Reunião sem Participantes confirmados, são recusados sem mudar nada (`participants` 19, 20); com confirmados, aceita em `transcribed`, `needs_split`, `done` e `failed` (etapa `generation`) e recusa em `generating` (`participants` 21, um teste por status).
- [x] Não chama `llm_providers`, não emite `ParticipantsConfirmed` e não muda o status (`participants` 22); chama `before_absorb(absorbed_id, survivor_id)` antes de apagar o absorvido.

**Verification:**
- [x] `cd backend && uv run pytest tests/participants/test_rename.py -q`.
- [x] Gate backend. SEC-02, SEC-09.

**Dependencies:** Task 32.3

**Files likely touched:**
- `backend/src/snook/modules/participants/service.py`
- `backend/tests/participants/test_rename.py`

**Estimated scope:** Small

### Checkpoint: `participants` API

- [x] Critérios 1 a 24 de `01-prd/participants.md` passam
- [x] Task 27.3 reconferida contra a rota real `GET /participants`
- [x] `/security-review` sobre o diff

### Task 34.1: Tela de nomeação: speakers, amostra e campos

**Description:** Do detalhe em `transcribed` com `participants_confirmed` falso, vai à tela de nomeação; cada speaker traz botão de tocar amostra, tempo de fala e campo de nome.

**Acceptance criteria:**
- [x] O detalhe de uma Reunião em `transcribed` com `participants_confirmed` falso leva à tela de nomeação (`participants` 25).
- [x] Cada speaker mostra botão para tocar a amostra, o tempo total de fala e um campo de nome (`participants` 26); o botão de confirmar fica desabilitado enquanto algum speaker está sem nome (`participants` 30).
- [x] `vitest-axe` sem violação; foco e teclado funcionam no botão de amostra.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/participants`.
- [x] Gate frontend.

**Dependencies:** Tasks 31.2, 22.3

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/participants/NamingPage.tsx`, `frontend/src/features/participants/SpeakerRow.tsx`, `frontend/src/features/participants/useSpeakers.ts`
- `frontend/src/features/participants/NamingPage.test.tsx`

**Estimated scope:** Medium

### Task 34.2: Tela de nomeação: junção, provedor e confirmação

**Description:** Indicação de junção por nome igual, provedor e modelo ativos, bloqueio sem provedor e confirmação.

**Acceptance criteria:**
- [x] Dois ou mais speakers com o mesmo nome mostram que serão juntados num só Participante (`participants` 27).
- [x] Mostra o provedor ativo e o modelo da geração (`participants` 28); sem provedor ativo, mostra mensagem com link para a tela de configurações e desabilita confirmar (`participants` 29).
- [x] Depois de confirmar, leva ao detalhe, onde o status é acompanhado (`participants` 31).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/participants`.
- [x] Gate frontend.

**Dependencies:** Tasks 34.1, 32.3, 17.1

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/participants/NamingPage.tsx`, `frontend/src/features/participants/useConfirmParticipants.ts`
- `frontend/src/features/participants/NamingPage.test.tsx`

**Estimated scope:** Small

### Checkpoint: `participants`

- [x] Critérios 25 a 31 cobertos
- [x] Checagem de UI; `impeccable-design-polish` na tela de nomeação
- [x] `/security-review` sobre o diff
- [x] Revisão humana antes de seguir

---

## Phase 5: `transcript-split`

### Task 35.1: System Prompt e schema em `shared/prompts`

**Description:** `backlog_system_prompt.md`, `backlog_response.schema.json` e loader, importáveis por `transcript_split` e `backlog_generation` sem ciclo (ADR-0020).

**Acceptance criteria:**
- [x] O prompt pede pt-BR, o schema da resposta, prioridade Low/Medium/High, story points 1/2/3/5/8/13, solicitante entre os nomes fornecidos e instante absoluto `hh:mm:ss` (`backlog-generation` 31).
- [x] O schema segue "Schema da resposta da LLM" com os tamanhos máximos de `05-api.md` (SEC-18).
- [x] `shared` não importa `modules` (`lint-imports`); nenhuma rota lê ou altera o prompt (`backlog-generation` 30).

**Verification:**
- [x] `cd backend && uv run pytest tests/shared/test_prompts.py -q`.
- [x] Gate backend. SEC-18.

**Dependencies:** Task 2

**Files likely touched:**
- `backend/src/snook/shared/prompts/backlog_system_prompt.md`, `backend/src/snook/shared/prompts/backlog_response.schema.json`, `backend/src/snook/shared/prompts/__init__.py`
- `backend/tests/shared/test_prompts.py`

**Estimated scope:** Small

### Task 35.2: "Texto da Parte"

**Description:** `part_text.py`: uma linha por segmento, `[hh:mm:ss] Nome: texto`, instante absoluto, nome atual lido a cada montagem.

**Acceptance criteria:**
- [x] Uma linha por segmento, na ordem, com instante absoluto de início, nome do Participante ligado ao speaker e texto (`transcript-split` 25).
- [x] Parte que começa no meio da gravação mostra instantes absolutos (`transcript-split` 26).
- [x] Depois de renomear um Participante, o texto usa o nome novo (`transcript-split` 27).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_part_text.py -q`.
- [x] Gate backend (adiciona `transcript_split` ao grafo do `lint-imports`).

**Dependencies:** Tasks 33, 24

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/part_text.py`, `backend/src/snook/modules/transcript_split/service.py`, `backend/pyproject.toml`
- `backend/tests/transcript_split/test_part_text.py`

**Estimated scope:** Small

### Task 35.3: "Orçamento da Parte"

**Description:** `budget.py`: janela menos reserva (System Prompt, Participantes, 1.000 tokens para nomes de Epics, resposta e margem de 5%) (ADR-0011).

**Acceptance criteria:**
- [x] O orçamento = janela menos a reserva do ADR-0011; janela menor que a reserva dá orçamento zero ou negativo tratado sem erro.
- [x] A estimativa usa o texto de "Texto da Parte" e o modelo do provedor ativo do dono da Reunião (`transcript-split` 4).
- [x] Nenhuma Parte com estimativa acima do orçamento é considerada "cabe" (RT-10).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_budget.py -q` ("Estimar tokens" fake de um token por caractere).
- [x] Gate backend.

**Dependencies:** Tasks 35.1, 35.2, 16.2

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/budget.py`
- `backend/tests/transcript_split/test_budget.py`

**Estimated scope:** Small

### Task 36.1: Partes: migração 0006 e gravação substitutiva

**Description:** Tabela `transcript_parts` (migração `0006_transcript_split_parts`) e gravação que apaga as Partes anteriores e grava as novas numa só transação.

**Acceptance criteria:**
- [x] Toda gravação (Parte única ou `PUT`) apaga todas as Partes anteriores e grava as novas numa transação; depois, "Partes" devolve só as novas (`transcript-split` 37).
- [x] Sem nova gravação, as Partes anteriores continuam; reaproveitamento não regrava (`transcript-split` 38).
- [x] As Partes guardam `start_seconds` e `end_seconds` absolutos iguais ao início do primeiro e ao fim do último segmento (`transcript-split` 18).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_parts_storage.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend.

**Dependencies:** Task 35.3

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/models.py`, `backend/src/snook/modules/transcript_split/repository.py`
- `backend/alembic/versions/0006_transcript_split_parts.py`, `backend/tests/transcript_split/test_parts_storage.py`

**Estimated scope:** Small

### Task 36.2: "Preparar geração" no modo `normal`: Parte única, `needs_split` e falhas

**Description:** `prepare_generation(uow, meeting_id, "normal")` decide Parte única, `needs_split` ou `failed`.

**Acceptance criteria:**
- [x] Transcrição inteira cabe: grava Parte única, leva a `generating`, novo `run_id` e emite `PartsReady` uma vez (`transcript-split` 1).
- [x] Não cabe: vai a `needs_split` com `split_reason` `too_long`, sem Parte gravada nem aviso (`transcript-split` 2); "Gerar" nunca é chamado (`transcript-split` 3).
- [x] Sem provedor ativo, vai a `failed` etapa `generation` com mensagem que aponta para a tela de configurações (`transcript-split` 5); segmento sozinho acima do orçamento vai a `failed` com mensagem pedindo modelo com janela maior (`transcript-split` 6); Participantes e Transcrição não mudam (`transcript-split` 24).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_prepare_generation.py -q`.
- [x] Gate backend. SEC-19.

**Dependencies:** Task 36.1

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/service.py`, `backend/src/snook/modules/transcript_split/messages.py`
- `backend/tests/transcript_split/test_prepare_generation.py`

**Estimated scope:** Medium

### Task 36.3: "Preparar geração": reaproveitamento e modo `reajustar`

**Description:** Reaproveita Partes anteriores que ainda cabem, segue com Parte única quando passa a caber e grava `split_reason` `adjust` no modo `reajustar`.

**Acceptance criteria:**
- [x] Retry da geração com a Transcrição inteira cabendo grava Parte única e segue a `generating`, mesmo que antes estivesse dividida (`transcript-split` 19); não cabendo inteira mas com Partes anteriores que cabem, reaproveita sem regravar e segue (`transcript-split` 20); Partes anteriores que não cabem levam a `needs_split` (`transcript-split` 21).
- [x] Modo `reajustar` em `done` já dividida e que não cabe inteira leva a `needs_split` com `split_reason` `adjust` (`transcript-split` 22); se cabe inteira, segue com Parte única.
- [x] Modo `normal` em `done` segue as regras 19 a 21 (`transcript-split` 23).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_prepare_generation_modes.py -q`.
- [x] Gate backend.

**Dependencies:** Task 36.2

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/service.py`
- `backend/tests/transcript_split/test_prepare_generation_modes.py`

**Estimated scope:** Small

### Task 36.4: Consumo dos avisos

**Description:** Consome `ParticipantsConfirmed` e `RetryRequested(generation)` e chama "Preparar geração" no modo `normal`.

**Acceptance criteria:**
- [x] Aviso com a Reunião em `transcribed` dispara a checagem uma vez.
- [x] Aviso com a Reunião fora de `transcribed` é ignorado: nenhuma checagem, nenhuma Parte, nenhum aviso, status igual (`transcript-split` 46).
- [x] Aviso com `run_id` que não bate é ignorado (ADR-0007); exceção no consumidor leva a `failed` (SEC-19).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_consumers.py -q`.
- [x] Gate backend. SEC-19.

**Dependencies:** Task 36.3, 32.3, 21.1

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/service.py`, `backend/src/snook/main.py`
- `backend/tests/transcript_split/test_consumers.py`

**Estimated scope:** Small

### Task 37.1: Cortes sugeridos (regra gulosa)

**Description:** `cuts.py`: cortes no fim de segmento, Partes contíguas, regra gulosa, com estimativa por segmento.

**Acceptance criteria:**
- [x] Cada corte cai no fim de um segmento; as Partes são contíguas, sem sobreposição, cobrem todos os segmentos e cabem no orçamento (`transcript-split` 8).
- [x] A regra gulosa dá o menor número de Partes possível com cortes no fim de segmento (`transcript-split` 9).
- [x] Para cada Parte: intervalo de tempo, estimativa e se cabe (`transcript-split` 10).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_cuts.py -q`.
- [x] Gate backend.

**Dependencies:** Task 36.1

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/cuts.py`
- `backend/tests/transcript_split/test_cuts.py`

**Estimated scope:** Small

### Task 37.2: `GET /split` e `POST /split/refresh`

**Description:** `GET` só lê; `refresh` aplica "passou a caber" (ADR-0019).

**Acceptance criteria:**
- [x] `GET` em `needs_split` devolve orçamento, provedor e modelo, estimativa total, segmentos com instante, Participante e texto, cortes sugeridos, se permite "Cancelar divisão" e `split_reason` (`transcript-split` 7); fora de `needs_split` responde 409, exceto `done` já dividida, só leitura; `refresh` fora de `needs_split` responde 409 sem mudar nada (`transcript-split` 11).
- [x] Se a Transcrição passou a caber, `refresh` grava Parte única, vai a `generating`, emite `PartsReady` uma vez e responde como o `GET` com o novo status e sem cortes; se não cabe, não grava, não muda e responde como o `GET` (`transcript-split` 43).
- [x] `GET` não grava Parte, não muda status e não emite aviso, mesmo cabendo (o banco não muda) (`transcript-split` 43); sem provedor ativo, `GET` e `refresh` respondem a mensagem que aponta para a configuração, sem orçamento nem cortes, e a Reunião segue em `needs_split` (`transcript-split` 44).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_api_split_read.py -q`.
- [x] Gate backend. SEC-02, SEC-04 (`refresh` é `POST`), nenhum `GET` muda estado.

**Dependencies:** Tasks 37.1, 36.3

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/api.py`, `backend/src/snook/modules/transcript_split/service.py`, `backend/src/snook/modules/transcript_split/schemas.py`
- `backend/tests/transcript_split/test_api_split_read.py`

**Estimated scope:** Medium

### Task 37.3: `PUT /split`

**Description:** Confirma cortes, revalida com o provedor ativo do momento e grava as Partes.

**Acceptance criteria:**
- [x] Cortes válidos em `needs_split` gravam as Partes em ordem, vão a `generating` e emitem `PartsReady` uma vez (`transcript-split` 12).
- [x] Corte fora do fim de segmento, repetido ou fora de ordem recebe 422 sem gravar (`transcript-split` 13, 14); Parte que não cabe, com todos os segmentos cabendo sozinhos, recebe 422 `part_too_large` com `part_index` e `estimated_tokens` e a Reunião segue em `needs_split` (`transcript-split` 15); a validação usa o provedor ativo do momento do `PUT` (`transcript-split` 16).
- [x] `PUT` fora de `needs_split` recebe 409 (`transcript-split` 17); sem provedor ativo ou com segmento acima do orçamento, vai a `failed` etapa `generation` sem gravar nem avisar (`transcript-split` 41, 42); se passou a caber, grava Parte única e ignora os cortes enviados (`transcript-split` 43). Máximo de 500 cortes (SEC-09).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split/test_api_split_put.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 37.2

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/api.py`, `backend/src/snook/modules/transcript_split/service.py`, `backend/src/snook/modules/transcript_split/schemas.py`
- `backend/tests/transcript_split/test_api_split_put.py`

**Estimated scope:** Medium

### Task 37.4: `POST /split/cancel` e isolamento das rotas de divisão

**Description:** "Cancelar divisão" e a bateria de 401/404 de todas as rotas do módulo.

**Acceptance criteria:**
- [x] Cancelar em `needs_split` com backlog gravado leva a `done` qualquer que seja o `split_reason`, sem mudar backlog nem Partes e sem aviso (`transcript-split` 39); fora de `needs_split`, ou sem backlog gravado, responde 409 sem mudar nada (`transcript-split` 40).
- [x] `GET`, `PUT`, `refresh` e `cancel` com `id` de outro Usuário respondem 404 e nada muda (`transcript-split` 28).
- [x] Sem sessão, as quatro rotas respondem 401 (`transcript-split` 29).

**Verification:**
- [x] `cd backend && uv run pytest tests/transcript_split -q`.
- [x] Gate backend. SEC-01, SEC-02, SEC-04.

**Dependencies:** Task 37.3

**Files likely touched:**
- `backend/src/snook/modules/transcript_split/api.py`, `backend/src/snook/modules/transcript_split/service.py`
- `backend/tests/transcript_split/test_api_split_cancel_isolation.py`

**Estimated scope:** Small

### Checkpoint: `transcript-split` API

- [x] Critérios 1 a 29, 37 a 44 e 46 de `01-prd/transcript-split.md` passam
- [x] `/security-review` sobre o diff

### Task 38.1: Tela de divisão: abertura e lista virtualizada

**Description:** Detalhe em `needs_split` leva à divisão; a tela chama `POST /split/refresh` ao abrir, redireciona se virou `generating`, explica a divisão e lista segmentos virtualizados com cortes sugeridos.

**Acceptance criteria:**
- [x] O detalhe de uma Reunião em `needs_split` leva à tela de divisão (`transcript-split` 30); ao abrir, chama `POST /meetings/{id}/split/refresh` antes de mostrar os cortes, e se a resposta traz `generating` leva ao detalhe sem mostrar a tela (`transcript-split` 47).
- [x] Explica a divisão com estimativa, orçamento, provedor, modelo e link para a configuração (`transcript-split` 31); mostra os segmentos em ordem, com instante e nome, e os cortes sugeridos marcados (`transcript-split` 32).
- [x] Com Transcrição de 2 h de fixture, só os segmentos perto da área visível ficam no DOM (NFR-07).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Gate frontend.

**Dependencies:** Tasks 37.2, 27.2

**Skills:** `shadcn`, `design-taste-frontend`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/transcript-split/SplitPage.tsx`, `frontend/src/features/transcript-split/useSplit.ts`, `frontend/src/features/transcript-split/SegmentList.tsx`
- `frontend/src/features/transcript-split/SplitPage.test.tsx`

**Estimated scope:** Medium

### Task 38.2: Tela de divisão: cortes por teclado e confirmação

**Description:** Mover, adicionar e remover cortes (mouse e teclado), estimativa por Parte somada no cliente, e "Confirmar".

**Acceptance criteria:**
- [x] O usuário move um corte para o fim de outro segmento, adiciona um corte no fim de qualquer segmento e remove um corte; a tela não oferece corte no meio de um segmento; tudo funciona por teclado (`transcript-split` 33).
- [x] A cada mudança, mostra para cada Parte o intervalo, a estimativa e se cabe (`transcript-split` 34); "Confirmar" fica desabilitado enquanto alguma Parte não couber (`transcript-split` 35).
- [x] Depois de confirmar, leva ao detalhe (`transcript-split` 36); INP até 200 ms com Transcrição de 2 h (NFR-04, medição manual no checkpoint); `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Gate frontend.

**Dependencies:** Tasks 38.1, 37.3

**Skills:** `shadcn`, `design-taste-frontend`, `frontend-ui-engineering`, `ui-animation`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/transcript-split/CutControls.tsx`, `frontend/src/features/transcript-split/PartSummary.tsx`, `frontend/src/features/transcript-split/useCuts.ts`
- `frontend/src/features/transcript-split/CutControls.test.tsx`

**Estimated scope:** Medium

### Task 38.3: Tela de divisão: "Cancelar divisão" e sem provedor

**Description:** Botão "Cancelar divisão" condicional e mensagem de falta de provedor.

**Acceptance criteria:**
- [x] O botão aparece só quando a resposta do `GET` indica backlog gravado; depois de cancelar, volta à revisão do backlog (`transcript-split` 45).
- [x] Sem provedor ativo, a tela mostra só a mensagem que aponta para a configuração (`transcript-split` 44; Q67).
- [x] `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Gate frontend.

**Dependencies:** Tasks 38.2, 37.4

**Skills:** `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/transcript-split/SplitPage.tsx`, `frontend/src/features/transcript-split/CancelSplitButton.tsx`
- `frontend/src/features/transcript-split/CancelSplitButton.test.tsx`

**Estimated scope:** Small

### Checkpoint: `transcript-split`

- [ ] Critérios 30 a 36, 45 e 47 cobertos
- [ ] Checagem de UI com Transcrição de 2 h (cortes por teclado; NFR-04, NFR-07); `impeccable-design-polish` na tela de divisão
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 6: `backlog-generation`

### Task 39.1: Validação da resposta da LLM contra o schema

**Description:** `validation.py`: JSON validado por Pydantic estrito com os tamanhos máximos de `05-api.md`.

**Acceptance criteria:**
- [x] Prioridade aceita sem diferenciar caixa (`high`, `HIGH`) e gravada como `Low`, `Medium` ou `High`; outro valor invalida (`backlog-generation` 8); story points fora de 1, 2, 3, 5, 8, 13 invalidam (`backlog-generation` 9).
- [x] US sem critério, ou com `given`, `when` ou `then` vazio, invalida; nome de Epic, nome de US, `as_a`, `i_want` ou `so_that` vazio invalida (`backlog-generation` 10, 11).
- [x] `requested_at` em `hh:mm:ss` entre 0 e a duração do áudio vira segundos, fora disso ou em outro formato invalida (`backlog-generation` 12); resposta que não é JSON ou não segue o schema, e campo acima do tamanho máximo, são inválidas (`backlog-generation` 14; SEC-18).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_validation.py -q` (tabela de respostas fake, uma por regra).
- [x] Gate backend (adiciona `backlog_generation` ao grafo do `lint-imports`). SEC-18.

**Dependencies:** Task 35.1

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/validation.py`, `backend/pyproject.toml`
- `backend/tests/backlog_generation/test_validation.py`

**Estimated scope:** Small

### Task 39.2: Solicitante por nome de Participante

**Description:** Liga `requested_by` ao Participante da Reunião, sem diferenciar caixa e espaços nas pontas.

**Acceptance criteria:**
- [x] `requested_by` igual ao nome de um Participante liga a US a ele (`backlog-generation` 13).
- [x] Nome desconhecido, vazio ou ausente deixa o solicitante vazio, sem invalidar (`backlog-generation` 13).
- [x] Nome nunca vai a SQL, caminho ou comando; só compara texto (SEC-18).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_requester_mapping.py -q`.
- [x] Gate backend. SEC-18.

**Dependencies:** Task 39.1, 32.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/validation.py`
- `backend/tests/backlog_generation/test_requester_mapping.py`

**Estimated scope:** Small

### Task 40.1: Epics, US e critérios: migração 0007 e repositório

**Description:** Tabelas `epics`, `user_stories`, `acceptance_criteria` e `backlog_counters` (migração `0007_backlog_generation_backlog`) e `BacklogRepository`.

**Acceptance criteria:**
- [x] `ON DELETE CASCADE` a partir da Reunião; `requested_by` com `SET NULL` só como rede de segurança (`04-data-model.md`).
- [x] `next_us_number(uow, meeting_id)` devolve o número depois do maior existente e não reusa o excluído se era o maior (`backlog-generation` interfaces; `backlog-review` 19).
- [x] `alembic upgrade head` roda sobre as revisões anteriores; nenhuma consulta monta SQL com dado de entrada (SEC-10).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_backlog_storage.py -q`; `uv run alembic upgrade head`.
- [x] Gate backend (inclui regra `S608`). SEC-10.

**Dependencies:** Tasks 39.2, 19.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/models.py`, `backend/src/snook/modules/backlog_generation/repository.py`
- `backend/alembic/versions/0007_backlog_generation_backlog.py`, `backend/tests/backlog_generation/test_backlog_storage.py`

**Estimated scope:** Medium

### Task 40.2: Runner sequencial por Parte

**Description:** `runner.py` consome `PartsReady`, lê o provedor ativo uma vez e chama "Gerar" Parte a Parte, em sequência.

**Acceptance criteria:**
- [x] Parte única com resposta válida: exatamente uma chamada a "Gerar", grava e leva a `done`; com 3 Partes, 3 chamadas na ordem, cada uma só depois da anterior (`backlog-generation` 1, 2).
- [x] Cada chamada leva o System Prompt, os nomes dos Participantes e o texto devolvido por "Texto da Parte" sem alteração; a primeira não leva nomes de Epics, as seguintes levam os das Epics criadas antes na mesma geração (`backlog-generation` 3, 4).
- [x] Provedor e modelo lidos uma vez, mesmo que o ativo mude durante a geração (`backlog-generation` 5); usa a configuração do Usuário dono (`backlog-generation` 6; SEC-26).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_runner_flow.py -q` ("Gerar" fake registra cada chamada).
- [x] Gate backend. SEC-26.

**Dependencies:** Tasks 40.1, 36.4, 16.3

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/runner.py`, `backend/src/snook/modules/backlog_generation/service.py`
- `backend/tests/backlog_generation/test_runner_flow.py`

**Estimated scope:** Medium

### Task 40.3: Junção de Epics e numeração de `US-id`

**Description:** `merge.py`: junta Epics de mesmo nome na Reunião e numera `US-01...` em ordem das Partes e da LLM.

**Acceptance criteria:**
- [x] Epics com o mesmo nome, sem diferenciar caixa e espaços nas pontas, viram uma só dentro de uma Parte e entre Partes; vale o nome da primeira ocorrência; Epics de outras Reuniões não são afetadas; as US ficam na Epic resultante na ordem de chegada (`backlog-generation` 16, 17).
- [x] `US-id` vai de `US-01`, sem lacunas, em ordem das Partes e da resposta; sem repetição; a partir da centésima, três dígitos (`US-100`) (`backlog-generation` 18, 19).
- [x] Epic sem US não é gravada; geração válida sem nenhuma US vai a `done` com backlog gravado e vazio (`backlog-generation` 20, 21).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_merge_numbering.py -q`.
- [x] Gate backend.

**Dependencies:** Task 40.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/merge.py`
- `backend/tests/backlog_generation/test_merge_numbering.py`

**Estimated scope:** Small

### Task 40.4: Gravação tudo ou nada

**Description:** Uma transação apaga o backlog anterior, grava o novo, chama `mark_backlog_saved` e leva a Reunião a `done`.

**Acceptance criteria:**
- [x] Resposta válida grava campo a campo: nome da Epic e da US, `as_a`, `i_want`, `so_that`, prioridade, story points, critérios na ordem, solicitante e instante (`backlog-generation` 7); toda gravação bem-sucedida, inclusive vazia, registra a marca na mesma transação (`backlog-generation` 34).
- [x] Com 3 Partes, falha na Parte 2 não grava nada das Partes 1 e 2, não chama a 3 e leva a `failed` etapa `generation` (`backlog-generation` 22); erro no meio da gravação não deixa backlog parcial (`backlog-generation` 25).
- [x] Regeneração bem-sucedida substitui o backlog com as edições e recomeça em `US-01` (`backlog-generation` 23); regeneração que falha mantém o anterior intacto e vai a `failed` (`backlog-generation` 24); geração que falha não registra a marca.

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_save_all_or_nothing.py -q`.
- [x] Gate backend. SEC-18, SEC-19.

**Dependencies:** Task 40.3

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/service.py`, `backend/src/snook/modules/backlog_generation/runner.py`, `backend/src/snook/modules/backlog_generation/repository.py`
- `backend/tests/backlog_generation/test_save_all_or_nothing.py`

**Estimated scope:** Medium

### Task 41.1: Erros tipados e resposta inválida

**Description:** Cada erro tipado de "Gerar" e cada resposta inválida levam a Reunião a `failed` etapa `generation` com mensagem pt-BR própria.

**Acceptance criteria:**
- [x] Credencial recusada, provedor inacessível, modelo inexistente, limite de contexto excedido e limite de uso levam a `failed` com mensagem pt-BR própria do tipo; a de credencial recusada aponta para a tela de configurações (`backlog-generation` 26).
- [x] Resposta inválida em qualquer Parte leva a `failed` com mensagem que cita a Parte e o motivo; nada é gravado e não há nova chamada automática (`backlog-generation` 15).
- [x] Nenhuma mensagem, log ou registro gravado contém a chave do provedor (`backlog-generation` 27; SEC-07, SEC-20).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_errors.py -q`.
- [x] Gate backend. SEC-07, SEC-18, SEC-19, SEC-20.

**Dependencies:** Task 40.4

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/runner.py`, `backend/src/snook/modules/backlog_generation/messages.py`
- `backend/tests/backlog_generation/test_errors.py`

**Estimated scope:** Small

### Task 41.2: Reestimativa por Parte e exclusão durante a geração

**Description:** Antes de cada "Gerar", reestima a Parte com o modelo lido no início; e a gravação final falha se a Reunião foi excluída.

**Acceptance criteria:**
- [x] Antes de cada chamada, reestima e compara com "Orçamento da Parte"; Parte que não cabe leva a `failed` com mensagem que cita a Parte e pede dividir de novo ou trocar de modelo; essa Parte e as seguintes não são chamadas e nada é gravado (`backlog-generation` 32; RT-10).
- [x] Reunião excluída durante a geração: nada é gravado depois da exclusão (`backlog-generation` 28).
- [x] A exceção na gravação final não deixa status preso (SEC-19).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_reestimate_delete.py -q`.
- [x] Gate backend. SEC-19.

**Dependencies:** Task 41.1

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/runner.py`
- `backend/tests/backlog_generation/test_reestimate_delete.py`

**Estimated scope:** Small

### Task 41.3: Idempotência do aviso e "Tentar novamente" da geração

**Description:** `PartsReady` fora de `generating` ou repetido é ignorado; retry da geração chega a `done` com a mesma Transcrição.

**Acceptance criteria:**
- [x] `PartsReady` com a Reunião fora de `generating` é ignorado: nenhuma chamada, nada gravado, status igual; um segundo aviso da mesma geração também (`backlog-generation` 33).
- [x] Depois de "Tentar novamente" da etapa `generation`, uma nova geração bem-sucedida leva a `done` com a mesma Transcrição e os mesmos Participantes (`backlog-generation` 29; transversal 16).
- [x] `run_id` velho é ignorado (ADR-0007).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_idempotency_retry.py -q`.
- [x] Gate backend.

**Dependencies:** Task 41.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_generation/service.py`, `backend/src/snook/modules/backlog_generation/runner.py`
- `backend/tests/backlog_generation/test_idempotency_retry.py`

**Estimated scope:** Small

### Checkpoint: Geração

- [x] Critérios 1 a 29 e 32 a 34 de `01-prd/backlog-generation.md` passam
- [x] SEC-18 verificado
- [x] `/security-review` sobre o diff

### Task 42.1: Snapshot do System Prompt

**Description:** Teste de snapshot do texto do prompt, versionado no repo.

**Acceptance criteria:**
- [x] O System Prompt fica num arquivo versionado e nenhuma rota o lê ou altera (`backlog-generation` 30).
- [x] O prompt pede pt-BR, o schema, prioridade em Low/Medium/High, story points na escala, solicitante entre os nomes fornecidos e instante absoluto em `hh:mm:ss` (`backlog-generation` 31).
- [x] O teste de snapshot falha quando o prompt muda sem o snapshot ser atualizado no mesmo commit (`backlog-generation` 31).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_generation/test_prompt_snapshot.py -q`.
- [x] Gate backend. SEC-18.

**Dependencies:** Task 41.3

**Files likely touched:**
- `backend/tests/backlog_generation/test_prompt_snapshot.py`, `backend/tests/backlog_generation/snapshots/system_prompt.md`

**Estimated scope:** Small

### Task 42.2: Suíte `llm_real` por provedor

**Description:** Marker `llm_real` com chaves reais em variáveis de ambiente e Transcrição curta de fixture, para os quatro provedores.

**Acceptance criteria:**
- [ ] Para cada um dos quatro provedores, a resposta passa na validação de `backlog-generation` e o backlog sai no mesmo formato (transversal 3, RT-01).
- [x] `uv run pytest` padrão não coleta `llm_real` (transversal 18); sem chave real no repo (SEC-08).
- [ ] Resultado por provedor vai ao PR de release.

**Verification:**
- [x] `cd backend && uv run pytest` (sem `llm_real`).
- [ ] Manual: `cd backend && uv run pytest -m llm_real` com as chaves em variáveis de ambiente.

**Dependencies:** Task 42.1

**Files likely touched:**
- `backend/tests/llm_real/conftest.py`, `backend/tests/llm_real/test_generate_real.py`, `backend/pyproject.toml`

**Estimated scope:** Small

### Checkpoint: `backlog-generation`

- [ ] Critérios 30 e 31 passam; suíte `llm_real` passa à mão nos quatro provedores (critério transversal 3)
- [ ] Fluxo completo upload até `done` funciona com Docker
- [x] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 7: `backlog-review`

### Task 43: Leitura do backlog com regras por status

**Description:** `GET /api/meetings/{id}/backlog` com `read_only` e `last_generation_failed`, e política de status que as rotas de escrita reutilizam.

**Acceptance criteria:**
- [x] Em `done`, devolve as Epics em ordem, cada uma com US em ordem e todos os campos (US-id, nome, `as_a`, `i_want`, `so_that`, prioridade, story points, solicitante com `id` e nome ou vazio, quando em `hh:mm:ss` ou vazio, critérios), sem informação de Parte (`backlog-review` 1, 2).
- [x] Em `failed` etapa `generation` com backlog devolve o backlog e o indicador de última geração com falha; em `transcribed`, `generating` ou `needs_split` com backlog devolve o anterior com indicador de só leitura (`backlog-review` 3); sem backlog gravado responde 409 `no_backlog` (`backlog-review` 4).
- [x] Em `done` com geração sem nenhuma US, responde 200 com lista de Epics vazia (`backlog-review` 47); 404 para outro Usuário e 401 sem sessão (`backlog-review` 37, 38).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_read.py -q`.
- [x] Gate backend (adiciona `backlog_review` ao grafo do `lint-imports`). SEC-01, SEC-02.

**Dependencies:** Tasks 40.4, 33

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`, `backend/src/snook/modules/backlog_review/schemas.py`, `backend/pyproject.toml`
- `backend/tests/backlog_review/test_api_read.py`

**Estimated scope:** Medium

### Task 44.1: Renomear Epic com mesclagem

**Description:** `PATCH /api/meetings/{id}/epics/{epic_id}`.

**Acceptance criteria:**
- [x] Nome novo é gravado sem espaços nas pontas (`backlog-review` 5); nome de outra Epic da mesma Reunião, sem diferenciar caixa e espaços nas pontas, junta as duas: sobrevive a que já tinha o nome e as US da renomeada passam para ela, depois das existentes; a resposta traz `merged_into` (`backlog-review` 6).
- [x] Nome vazio ou só de espaços recebe 422 (`backlog-review` 9); fora de `done` responde 409 sem mudar nada (`backlog-review` 30, um teste por status).
- [x] `epic_id` de outra Reunião ou Reunião de outro Usuário responde 404; sem sessão, 401 (`backlog-review` 37, 38; SEC-02).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_epic_rename.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 43

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_epic_rename.py`

**Estimated scope:** Small

### Task 44.2: Criar Epic

**Description:** `POST /api/meetings/{id}/epics`.

**Acceptance criteria:**
- [x] Nome não vazio que não existe na Reunião cria a Epic sem US no fim da lista e responde 201 (`backlog-review` 7).
- [x] Nome igual ao de uma Epic da mesma Reunião não cria segunda: responde 200 com a existente; Epic de mesmo nome em outra Reunião do mesmo Usuário não impede, resposta 201 (`backlog-review` 8).
- [x] Nome vazio recebe 422 (`backlog-review` 9); fora de `done` responde 409 (`backlog-review` 30); 404/401 conforme isolamento (`backlog-review` 37, 38).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_epic_create.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 44.1

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_epic_create.py`

**Estimated scope:** Small

### Task 44.3: Excluir Epic vazia

**Description:** `DELETE /api/meetings/{id}/epics/{epic_id}`.

**Acceptance criteria:**
- [x] Epic sem US é removida com 204 (`backlog-review` 10).
- [x] Epic com US recebe 409 `epic_not_empty` e nada muda (`backlog-review` 10).
- [x] Fora de `done` responde 409 (`backlog-review` 30); 404/401 conforme isolamento (`backlog-review` 37, 38).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_epic_delete.py -q`.
- [x] Gate backend. SEC-02, SEC-04.

**Dependencies:** Task 44.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_epic_delete.py`

**Estimated scope:** Small

### Task 45.1: Editar campos de User Story

**Description:** `PATCH /api/meetings/{id}/user-stories/{story_id}` para nome, `as_a`, `i_want`, `so_that`, prioridade e story points.

**Acceptance criteria:**
- [x] Grava os campos enviados e não muda o `US-id` (`backlog-review` 11).
- [x] Prioridade fora de Low/Medium/High e story points fora de 1, 2, 3, 5, 8, 13 recebem 422 (`backlog-review` 12); nome, `as_a`, `i_want` ou `so_that` vazio recebe 422 (`backlog-review` 13); campos acima do máximo recebem 422 (SEC-09).
- [x] Fora de `done` responde 409 (`backlog-review` 30); `story_id` de outra Reunião responde 404 (`backlog-review` 37; SEC-02).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_story_fields.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 44.3

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`, `backend/src/snook/modules/backlog_review/schemas.py`
- `backend/tests/backlog_review/test_api_story_fields.py`

**Estimated scope:** Small

### Task 45.2: Solicitante, instante e mover User Story

**Description:** O mesmo `PATCH` aceita solicitante, instante e `epic_id`.

**Acceptance criteria:**
- [x] Troca o solicitante por outro Participante da mesma Reunião ou o deixa vazio; Participante de outra Reunião recebe 422 (`backlog-review` 14).
- [x] Troca o instante em `hh:mm:ss` entre 0 e a duração; fora disso recebe 422 (`backlog-review` 15).
- [x] `epic_id` de outra Epic da mesma Reunião move a US para o fim dela sem mudar o `US-id`, e a origem pode ficar vazia (`backlog-review` 16); `epic_id` de outra Reunião responde 404 (`backlog-review` 37; SEC-02).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_story_move.py -q`.
- [x] Gate backend. SEC-02, SEC-09.

**Dependencies:** Task 45.1

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/service.py`, `backend/src/snook/modules/backlog_review/schemas.py`
- `backend/tests/backlog_review/test_api_story_move.py`

**Estimated scope:** Small

### Task 45.3: Criar User Story

**Description:** `POST /api/meetings/{id}/epics/{epic_id}/user-stories`.

**Acceptance criteria:**
- [x] Cria a US numa Epic com todos os campos obrigatórios e ao menos um critério, com o próximo `US-id` depois do maior existente na Reunião (`backlog-review` 17).
- [x] Solicitante e instante são opcionais numa US criada à mão (`backlog-review` 18).
- [x] Fora de `done` responde 409 (`backlog-review` 30); 422 para campo faltando, vazio ou acima do máximo; 404/401 conforme isolamento (`backlog-review` 37, 38; SEC-09).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_story_create.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 45.2

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_story_create.py`

**Estimated scope:** Small

### Task 45.4: Excluir User Story

**Description:** `DELETE /api/meetings/{id}/user-stories/{story_id}`.

**Acceptance criteria:**
- [x] Remove a US com seus critérios e os outros `US-id` não mudam (`backlog-review` 19).
- [x] Uma US criada depois não reusa o número excluído, se ele era o maior (`backlog-review` 19).
- [x] Fora de `done` responde 409 (`backlog-review` 30); 404/401 conforme isolamento (`backlog-review` 37, 38).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_story_delete.py -q`.
- [x] Gate backend. SEC-02, SEC-04.

**Dependencies:** Task 45.3

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_story_delete.py`

**Estimated scope:** Small

### Task 45.5: Critérios de aceite: criar, editar e excluir

**Description:** `POST .../user-stories/{story_id}/criteria`, `PATCH` e `DELETE /criteria/{criterion_id}`.

**Acceptance criteria:**
- [x] `POST` com `given`, `when` e `then` não vazios adiciona o critério no fim da US (`backlog-review` 20); `PATCH` grava os campos enviados e campo vazio recebe 422 (`backlog-review` 21).
- [x] `DELETE` do último critério da US recebe 409 `last_criterion` (`backlog-review` 22).
- [x] Fora de `done` responde 409 (`backlog-review` 30); `criterion_id` de outra Reunião responde 404; sem sessão, 401 (`backlog-review` 37, 38; SEC-02, SEC-09).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_criteria.py -q`.
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 45.4

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_criteria.py`

**Estimated scope:** Small

### Checkpoint: Edição

- [ ] Critérios 1 a 22, 30, 37, 38 e 47 de `01-prd/backlog-review.md` passam
- [ ] `/security-review` sobre o diff

### Task 46: Endpoint de renomear participante com troca de solicitante

**Description:** `PATCH /api/meetings/{id}/participants/{participant_id}` chama `participants.rename` com `before_absorb` que troca `requested_by` nas US, tudo numa transação.

**Acceptance criteria:**
- [x] Nome novo troca o nome e todas as US do solicitante mostram o nome novo (`backlog-review` 23); nome de outro Participante da Reunião une os dois e as US do absorvido passam ao sobrevivente, numa só transação (`backlog-review` 24).
- [x] Não chama a LLM e não muda texto das US nem Epics (`backlog-review` 25; transversal 17).
- [x] A regra de status segue `participants` 21: recusa só em `generating` e sem Participantes confirmados (`backlog-review` 30); `participant_id` de outra Reunião responde 404 (`backlog-review` 37); 401 sem sessão (`backlog-review` 38).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_rename_participant.py -q` (implementação real de `participants`).
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Tasks 45.5, 33

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_rename_participant.py`

**Estimated scope:** Small

### Task 47: Regenerar com mesmos cortes ou reajuste

**Description:** `POST /api/meetings/{id}/regenerate` com `mode` `same_cuts` ou `adjust_cuts`.

**Acceptance criteria:**
- [x] `same_cuts` em `done` chama "Preparar geração" no modo `normal` (`backlog-review` 26); `adjust_cuts` em Reunião já dividida chama o modo `reajustar`, e em Reunião não dividida recebe 422 (`backlog-review` 27).
- [x] Regenerar fora de `done` recebe 409 sem mudar nada (`backlog-review` 28, 30); o backlog anterior só é substituído quando a nova geração termina bem (`backlog-review` 29; `backlog-generation` 24).
- [x] 404 com `id` de outro Usuário e 401 sem sessão (`backlog-review` 37, 38; SEC-02, SEC-04).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_regenerate.py -q` ("Preparar geração" fake registra o modo).
- [x] Gate backend. SEC-02, SEC-04, SEC-09.

**Dependencies:** Task 46

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/api.py`, `backend/src/snook/modules/backlog_review/service.py`
- `backend/tests/backlog_review/test_api_regenerate.py`

**Estimated scope:** Small

### Task 48.1: Exportação em Markdown

**Description:** `GET /api/meetings/{id}/export?format=md` como anexo, nome `<slug-do-titulo>-backlog.md`.

**Acceptance criteria:**
- [x] Cada Epic sai como `Epic: <nome>` e cada US no formato da Q11, na ordem `US-id: nome`, "Como", "Eu quero", "Para", "Prioridade", "Story Points" e "Critérios de aceitação" com "Dado / Quando / Então" (`backlog-review` 32); o arquivo começa com título e data da Reunião, e cada US traz "Solicitante" e "Quando" depois de "Para", omitidos se vazios (`backlog-review` 33).
- [x] Sem informação de Parte nem identificador interno além do `US-id`; backlog vazio devolve só o cabeçalho (`backlog-review` 35, 36).
- [x] Resposta com `Content-Disposition: attachment` e nome sanitizado (slug ASCII até 60 caracteres, vazio vira `reuniao`) e `X-Content-Type-Options: nosniff` (SEC-12); sem backlog gravado responde 409 `no_backlog` (`backlog-review` 31).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_export_md.py -q` (snapshot do Markdown de fixture).
- [x] Gate backend. SEC-02, SEC-12.

**Dependencies:** Task 47

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/export.py`, `backend/src/snook/modules/backlog_review/api.py`
- `backend/tests/backlog_review/test_api_export_md.py`, `backend/tests/backlog_review/snapshots/backlog.md`

**Estimated scope:** Small

### Task 48.2: Exportação em JSON

**Description:** `GET /api/meetings/{id}/export?format=json`.

**Acceptance criteria:**
- [x] Devolve Epics com US e critérios, incluindo `US-id`, solicitante (nome), quando (`hh:mm:ss`), título e data da Reunião (`backlog-review` 34); sem Parte nem identificador interno além do `US-id` (`backlog-review` 35).
- [x] Backlog vazio devolve só o cabeçalho; funciona em `done`, `transcribed`, `generating`, `needs_split` e `failed` com backlog gravado, e responde 409 sem backlog (`backlog-review` 31, 36).
- [x] Formato desconhecido recebe 422; `id` de outro Usuário, 404; sem sessão, 401 (`backlog-review` 37, 38); texto com `<script>` sai como dado, anexo e `nosniff` (SEC-12).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review/test_api_export_json.py -q` (snapshot).
- [x] Gate backend. SEC-02, SEC-12.

**Dependencies:** Task 48.1

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/export.py`, `backend/src/snook/modules/backlog_review/api.py`
- `backend/tests/backlog_review/test_api_export_json.py`, `backend/tests/backlog_review/snapshots/backlog.json`

**Estimated scope:** Small

### Checkpoint: Renomear, regenerar, exportar

- [x] Critérios 23 a 29 e 31 a 36 passam
- [x] Critérios 30, 37 e 38 repetidos nas rotas novas das Tasks 46 a 48 (regra de status, 404 com `id` alheio, 401 sem sessão)
- [x] SEC-12 verificado no export
- [x] `/security-review` sobre o diff

### Task 49.1: Tela de revisão: leitura agrupada por Epic

**Description:** Backlog agrupado por Epic com todos os campos, solicitante, instante, banner de só leitura e de última geração com falha.

**Acceptance criteria:**
- [x] Mostra as US agrupadas por Epic com todos os campos do formato, solicitante e instante (`backlog-review` 39); texto de US renderiza escapado, inclusive `<script>` (SEC-12).
- [x] Em `failed` com backlog, mostra só leitura, aviso de que a última geração falhou, o motivo e "Tentar novamente" que repete o aviso de perda das edições; em `transcribed`, `generating` e `needs_split` com backlog, só leitura com o status atual (`backlog-review` 46).
- [ ] Com backlog de fixture de 30 Epics e 200 US, INP até 200 ms (NFR-04, medição manual no checkpoint); abrir e fechar Epic anima só `transform` e `opacity`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Gate frontend. SEC-12.

**Dependencies:** Tasks 43, 22.3

**Skills:** `shadcn`, `minimalist-ui`, `design-taste-frontend`, `frontend-ui-engineering`, `animate`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/ReviewPage.tsx`, `frontend/src/features/backlog-review/EpicSection.tsx`, `frontend/src/features/backlog-review/StoryCard.tsx`, `frontend/src/features/backlog-review/fixtures/backlog-30-200.ts`
- `frontend/src/features/backlog-review/ReviewPage.test.tsx`

**Estimated scope:** Medium

### Task 49.2: Tela de revisão: edição no lugar

**Description:** Cada campo editável na própria tela, com erros da API junto ao campo.

**Acceptance criteria:**
- [x] Cada campo de Epic, US e critério pode ser editado na tela, incluindo prioridade, story points, solicitante e instante (`backlog-review` 40).
- [x] Erros 422 da API aparecem junto ao campo (`backlog-review` 40).
- [x] Teclado em tudo, foco visível e `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Gate frontend.

**Dependencies:** Tasks 49.1, 45.5

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/EditableField.tsx`, `frontend/src/features/backlog-review/useBacklogMutations.ts`
- `frontend/src/features/backlog-review/EditableField.test.tsx`

**Estimated scope:** Medium

### Task 49.3: Tela de revisão: criar, juntar, mover e excluir

**Description:** Criar Epic e US, aviso de junção por nome igual, mover US e excluir com confirmação.

**Acceptance criteria:**
- [x] Renomear ou criar uma Epic, ou renomear um Participante, com nome que já existe na Reunião mostra, antes de salvar, que os dois serão juntados (`backlog-review` 41).
- [x] Excluir US, Epic ou critério pede confirmação; o botão de excluir Epic fica desabilitado enquanto ela tiver US (`backlog-review` 42).
- [x] Mover uma US abre a escolha da Epic de destino entre as da Reunião (`backlog-review` 43).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Gate frontend.

**Dependencies:** Task 49.2, 44.3, 45.2

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `animate`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/ConfirmDeleteDialog.tsx`, `frontend/src/features/backlog-review/MoveStoryDialog.tsx`, `frontend/src/features/backlog-review/MergeNotice.tsx`
- `frontend/src/features/backlog-review/ConfirmDeleteDialog.test.tsx`

**Estimated scope:** Medium

### Task 49.4: Tela de revisão: regenerar, exportar e renomear participante

**Description:** "Regenerar" com aviso, opções para Reunião dividida, botões de exportar e "Renomear participante".

**Acceptance criteria:**
- [x] "Regenerar" avisa que todas as edições serão perdidas antes de confirmar; em Reunião dividida, oferece "mesmos cortes" e "reajustar cortes" (`backlog-review` 44).
- [x] "Exportar Markdown" e "Exportar JSON" baixam o arquivo (`backlog-review` 45).
- [ ] "Renomear participante" aparece também com o backlog só para leitura, nas situações em que a regra por status permite (`backlog-review` 48); os diálogos usam `DialogSurface` opaco, sem `GlassPanel` (ADR-0024, "Vidro"; NFR-06 segue valendo, a tela de revisão tem 0 vidros). Reaberto pela Fase 9, fecha nas Tasks 52.17 e 54.5.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Gate frontend.

**Dependencies:** Tasks 49.3, 48.2, 47, 46

**Skills:** `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `animate`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/RegenerateDialog.tsx`, `frontend/src/features/backlog-review/ExportButtons.tsx`, `frontend/src/features/backlog-review/RenameParticipantDialog.tsx`
- `frontend/src/features/backlog-review/RegenerateDialog.test.tsx`

**Estimated scope:** Medium

### Checkpoint: `backlog-review`

- [ ] Critérios 39 a 46 e 48 cobertos
- [ ] Checagem de UI; `impeccable-design-polish` na tela de revisão
- [ ] INP com backlog de fixture 30 Epics e 200 US (NFR-04)
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

---

## Phase 8: Exclusão de Usuário e release

### Task 50.1: Interfaces de exclusão de Usuário

**Description:** `auth.find_user_by_username` (por `username_norm`), `auth.delete_user(uow, user_id)`, `meetings.list_meeting_ids_for_user` e `meetings.remove_meeting_files(ids)`.

**Acceptance criteria:**
- [x] `find_user_by_username` normaliza a entrada e acha o Usuário com caixa diferente da cadastrada (Q39; SEC-24).
- [x] `delete_user` num commit leva por `ON DELETE CASCADE` sessões, configurações de LLM, Reuniões e derivados (segmentos, Participantes, Partes, Epics, US, critérios) (SEC-24).
- [x] `remove_meeting_files` só age com as checagens de SEC-15 (UUID, `realpath` sob `/audios`, um nível abaixo, não `.tmp`).

**Verification:**
- [x] `cd backend && uv run pytest tests/auth/test_delete_user_service.py tests/meetings/test_remove_files.py -q`.
- [x] Gate backend. SEC-15, SEC-24.

**Dependencies:** Tasks 49.4, 19.2

**Files likely touched:**
- `backend/src/snook/modules/auth/service.py`, `backend/src/snook/modules/meetings/service.py`
- `backend/tests/auth/test_delete_user_service.py`, `backend/tests/meetings/test_remove_files.py`

**Estimated scope:** Small

### Task 50.2: CLI `delete-user`

**Description:** `python -m snook.cli delete-user <username>` com trava, confirmação, `--yes`, cascata, remoção de `/audios` e log. Testado em `tests/cli/`.

**Acceptance criteria:**
- [x] Apaga as linhas de todas as tabelas e os diretórios do Usuário; dados de outro Usuário não mudam; depois, login com aquele email ou nome responde 401 (transversal 21; US 25); nome inexistente sai com código 1 sem escrever (SEC-24).
- [x] Confirmação diferente do argumento sai sem apagar nada; `--yes` pula a confirmação (SEC-24; `08-deployment.md`, "CLI de escrita"); com a trava `/data/snook.lock` ocupada, o comando para com erro e nada é apagado (abuse case "delete-user com backend no ar").
- [x] Evento `operator.user_deleted` com `user_id` e `meetings_count`, sem email nem nome de usuário (SEC-20); o argumento passa pela validação do cadastro (`03-security.md`, superfícies).

**Verification:**
- [x] `cd backend && uv run pytest tests/cli/test_delete_user.py -q` (dois Usuários com Reuniões e arquivos).
- [x] Gate backend. Não rodar em dados reais sem aprovação ("Perguntar antes"). SEC-15, SEC-20, SEC-24.

**Dependencies:** Task 50.1

**Files likely touched:**
- `backend/src/snook/cli.py`
- `backend/tests/cli/test_delete_user.py`

**Estimated scope:** Medium

### Checkpoint: `delete-user`

- [x] Critério transversal 21 e US 25 de `01-prd.md` cobertos em `tests/cli/`
- [x] SEC-24: apaga linhas de todas as tabelas e diretórios do Usuário; dados de outro Usuário não mudam; nome inexistente sai com código 1 sem escrever
- [x] SEC-24: confirmação errada (nome digitado diferente do argumento) sai sem apagar nada (`08-deployment.md`, "CLI de escrita")
- [x] Abuse case "delete-user com backend no ar": com a trava ocupada, o comando para com erro e nada é apagado
- [x] `find_user_by_username` compara por `username_norm` (Q39); teste com caixa diferente
- [x] Evento `operator.user_deleted` com `user_id` e `meetings_count`, sem email nem nome de usuário (SEC-20)
- [x] `/security-review` sobre o diff

### Task 51.1: README de release

**Description:** README com primeira execução, `HF_TOKEN` e aceite dos termos do Pyannote, URL do Ollama alcançável de dentro do container, perfil `lan` e CA, aviso de backup, `mkdir -p audios` e medidas do spike.

**Acceptance criteria:**
- [x] Segue `08-deployment.md`, "Primeira execução" e "Perfil lan", e inclui `docker compose stop backend backend-gpu` e o comando por perfil do `delete-user`.
- [x] Avisa que dado apagado pode seguir no último `snook.db.bak-*` até a próxima migração e mostra como apagá-lo (`03-security.md`, "Backups").
- [ ] Explica a URL padrão do Ollama `http://host.docker.internal:11434` e a tabela de desempenho medido (Task 1).

**Verification:**
- [ ] Manual: seguir o README num clone limpo até `http://localhost:8080` (transversal 1).
- [x] `git grep -nE "hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,}" README.md` sem achado (SEC-08).

**Dependencies:** Task 50.2

**Files likely touched:**
- `README.md`

**Estimated scope:** Small

### Task 51.2: Checklist de release: segurança, auditorias e suítes opcionais

**Description:** Percorrer a tabela "Verificação" de `03-security.md` (SEC-01 a SEC-27), rodar as auditorias e as suítes opcionais e registrar tudo no PR de release.

**Acceptance criteria:**
- [ ] Todos os SEC-01 a SEC-27 verificados com o método da tabela "Verificação" de `03-security.md`; cada um com o resultado anotado no PR de release.
- [ ] `cd backend && uv run pip-audit` e `cd frontend && npm audit --omit=dev` sem achado crítico ou alto alcançável (SEC-21); checklist de `security-and-hardening` percorrido.
- [ ] Suítes `models_real` e `llm_real` rodadas à mão, com o registro no PR (`08-deployment.md`, "CI/CD"); critério transversal 2 (`down` sem `-v`) conferido.

**Verification:**
- [ ] `cd backend && uv run pytest && uv run pip-audit && uv run ruff check . && uv run mypy src && uv run lint-imports`.
- [ ] `cd frontend && npm ci --ignore-scripts && npm test -- --run && npm run build && npm audit --omit=dev`.
- [ ] `docker compose exec backend id -u` imprime `1000`; `docker compose ps` sem porta do backend (SEC-23).

**Dependencies:** Task 51.1

**Files likely touched:**
- `README.md` (seção de release), descrição do PR de release

**Estimated scope:** Small

### Checkpoint: Release sem auditoria visual

- [ ] README, verificação do 03-security, auditorias e suítes opcionais registrados no PR
- [ ] `/security-review` sobre o diff

---

## Phase 9: Redesign Ata (ADR-0024)

**Regras da fase (valem para as Tasks 52 a 61):**

- Escopo: só camada visual. Lógica, rotas, contratos de API, textos ao usuário e `CONSENT_NOTICE_TEXT` não mudam. Mudar o texto do aviso é "Perguntar antes".
- Cada task mãe (52 a 61) = uma branch `feature/redesign-ata-task-NN` e um PR para `develop`, com `git pull --rebase` de `develop` antes. Subtasks (52.1, 52.2...) são passos da mesma branch. Gate frontend ao fim de cada subtask.
- Rastreio: o `01-prd.md` só tem NFR-01 a NFR-08 para o visual (Q74 de `00-overview.md`). Critério visual cita ADR-0024 e `02-architecture.md`, "Frontend e UI". Critério "segue passando" cita o critério do módulo. Teste de critério existente não muda de asserção, exceto os de ADR-0024, "Testes a atualizar".
- Migração (ADR-0024, Q1 opção C): a Task 52 troca só classes de cor de token removido e usos do `Button`. `rounded-xl` e acima, `text-[`, `transition-colors`, `ring-ring/50` e `outline-ring/50` saem na task da tela. Teste estático global só na Task 61.4.
- **Grep local** (usado nas tasks de tela): `git grep -nE "rounded-(xl|2xl|3xl|4xl)|text-\[|transition-colors|ring-ring/50|outline-ring/50" -- <arquivos da task>` sem achado.
- Alerta de bloco ou de página vira `Notice`. Erro de campo fica inline no `FormField`.
- No máximo um `Button` `accent` por tela, no passo que avança o fluxo.
- Largura: `--reading` na Transcrição, nomeação e formulários; `--shell` nas demais páginas. Página não escolhe `max-w-*` própria (ADR-0024, "Forma"). Ver "Questões em aberto" do relatório sobre as páginas que o ADR não lista.
- No máximo três tamanhos de texto por tela, da escala 12, 14, 16, 20, 24, 32, 40 px. Espaço só 4, 8, 12, 16, 24, 32, 48, 64 px.
- Texto vindo de API, banco ou LLM renderiza só pelo escape do React (SEC-12).

### Task 52.1: Camada de cor Ata e apelidos shadcn

**Description:** Em `tokens.css`, acrescenta os tokens Ata (tabela "Tokens") nos dois temas e aponta os apelidos shadcn para eles (tabela "Apelidos"). O `@theme` de `index.css` ganha as cores `--color-*` novas. Os tokens antigos (`--highlight*`, `--status-*`, `--sidebar-*`, `--chart-*`, `--elevation-*`, `--radius`) ficam até a Task 52.30, porque classes de `features/` ainda os leem.

**Acceptance criteria:**
- [x] Os tokens da tabela "Tokens" do ADR-0024 existem nos temas claro e escuro, e o `@theme` expõe `--color-canvas`, `--color-surface`, `--color-sunken`, `--color-hairline`, `--color-ink`, `--color-ink-muted`, `--color-signal`, `--color-signal-ink`, `--color-signal-soft`, `--color-done`, `--color-warn`, `--color-warn-soft`, `--color-failed`, `--color-failed-soft` e `--color-scrim` (ADR-0024, "Cor").
- [x] Os apelidos shadcn da tabela "Apelidos" leem só tokens Ata; `--accent` é fundo de hover (`--sunken`) e `--ring` é `var(--signal)`, sem alfa (ADR-0024, "Apelidos" e "Foco").
- [x] `tokens.test.ts` confere todos os pares das duas tabelas de "Contraste", nos dois temas; par abaixo do mínimo corrige o fundo `-soft`, nunca o mínimo (WCAG 2.2 AA; `02-architecture.md`, "Restrições obrigatórias").

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles`.
- [x] Gate frontend.

**Dependencies:** Checkpoint: Release sem auditoria visual

**Skills:** `minimalist-ui`, `frontend-design`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/styles/tokens.css`, `frontend/src/index.css`
- `frontend/src/styles/tokens.test.ts`

**Estimated scope:** Medium

### Task 52.2: Fontes locais do Ata: serif, mono, preload, fallback

**Description:** Quatro `.woff2` novos (Source Serif 4 latin e latin-ext; Geist Mono latin e latin-ext) e licenças em `frontend/public/fonts/`. `@font-face` com `unicode-range` e `font-display: swap` em `tokens.css`. Fallback local com métricas ajustadas para serif e sans. `--font-heading` e `--font-serif` apontam para Source Serif 4, `--font-sans` para Geist, `--font-mono` para Geist Mono (hoje `index.css:12` aponta `--font-heading` para a sans). Preload só da Geist latin e da Source Serif 4 latin. Arquivos vêm do pacote oficial das fontes, sem dependência npm nova.

**Acceptance criteria:**
- [x] Os quatro `.woff2`, `LICENSE-SourceSerif4.txt` (OFL) e a conferência da cobertura da Geist Mono por `LICENSE-Geist.txt` (se não cobrir, o arquivo da licença dela) estão em `public/fonts/`; nenhuma requisição externa e CSP `default-src 'self'` sem mudança (ADR-0024, "Tipografia"; SEC-13).
- [x] `index.html` tem `<link rel="preload">` só da Geist latin e da Source Serif 4 latin; todas as famílias com `font-display: swap`; fallback com `size-adjust`, `ascent-override`, `descent-override` e `line-gap-override` (NFR-05).
- [x] Teste lê `tokens.css`, `index.css` e `index.html` e confere a família de cada `--font-*`, os dois preloads e a ausência de URL `http`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles`.
- [x] Gate frontend. `cd frontend && npm run build && node scripts/check-bundle-size.mjs` (NFR-01, NFR-02).
- [ ] Manual, Lighthouse na tela de login com CPU 4x mais lenta: LCP (NFR-03) e CLS (NFR-05) anotados no PR. LCP acima de 2,5 s: aplicar a contingência (`h1` do auth em Geist; ADR-0024, "Tipografia"), sem ADR novo.

**Dependencies:** Task 52.1

**Skills:** `minimalist-ui`, `frontend-design`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/public/fonts/*` (4 `.woff2` novos, licenças)
- `frontend/src/styles/tokens.css`, `frontend/src/index.css`, `frontend/index.html`
- `frontend/src/styles/fonts.test.ts`

**Estimated scope:** Medium

### Task 52.3: Forma no `@theme`: raio, sombra, larguras

**Description:** `tokens.css` ganha `--r-4`, `--r-6`, `--r-10`. `@theme` em `index.css`: `--radius-*: initial`, `--radius-sm` = `--r-4`, `--radius-md` = `--r-6`, `--radius-lg` = `--r-10`; `--shadow-*: initial` e só `--shadow-overlay` (= `--overlay-shadow`); larguras `--shell` 72rem e `--reading` 44rem com utilitário para cada uma. Até a task de cada tela, `rounded-xl` e acima ficam sem raio (efeito só visual, aceito na Q1).

**Acceptance criteria:**
- [x] `rounded-sm`, `rounded-md` e `rounded-lg` resolvem a 4, 6 e 10 px; `--radius-xl` a `--radius-4xl` não existem (ADR-0024, "Forma").
- [x] Só `--shadow-overlay` existe no `@theme`; nenhuma classe `shadow-sm` ou `shadow-md` em `src/` (ADR-0024, "Profundidade").
- [x] `--shell` vale 72rem e `--reading` 44rem, e há utilitário de largura para cada uma.

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles` (teste novo lê `index.css` e `tokens.css`).
- [x] `git grep -nE "shadow-(sm|md)\b" -- frontend/src` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `minimalist-ui`, `frontend-design`, `shadcn`

**Files likely touched:**
- `frontend/src/index.css`, `frontend/src/styles/tokens.css`
- `frontend/src/styles/forma.test.ts`

**Estimated scope:** Small

### Task 52.4: Campo `Input` e foco base opacos

**Description:** Base de `index.css` troca `outline-ring/50` por `outline-ring`. `Input` passa a 40 px de altura, raio `--r-6`, borda `--input`, anel `ring-2 ring-ring` opaco com afastamento de 2 px, borda `--failed` opaca quando inválido, espaço da escala e sem `ring-ring/50`.

**Acceptance criteria:**
- [x] Nenhum anel ou contorno de foco usa alfa em `index.css` nem em `input.tsx` (ADR-0024, "Foco"; WCAG 2.2 AA).
- [x] Campo tem 40 px de altura, raio `--r-6` e borda `--input`; campo com `aria-invalid` tem borda `--failed` opaca (ADR-0024, "Forma" e "Foco").
- [x] `vitest-axe` sem violação no campo; foco por teclado mostra o anel de 2 px em `--ring`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components`.
- [x] `git grep -nE "ring-ring/50|outline-ring/50" -- frontend/src/index.css frontend/src/components/ui/input.tsx` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.3

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `emil-design-eng`

**Files likely touched:**
- `frontend/src/index.css`, `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/input.test.tsx`

**Estimated scope:** Small

### Task 52.5: `Button` Ata com nomes antigos transitórios

**Description:** `button.tsx` ganha as variantes `primary`, `accent`, `secondary`, `ghost` e `danger` (tabela do ADR-0024, "Componentes") e os tamanhos `default` 36 px, `sm` 32 px, `icon` 36 px, `icon-sm` 32 px. `link` sai (sem uso). Para o `typecheck` seguir verde enquanto os usos migram, as variantes `default`, `outline`, `destructive` e os tamanhos `xs`, `lg`, `icon-xs`, `icon-lg` ficam como apelidos temporários, removidos na Task 52.9. `defaultVariants` e o padrão `variant = "default"` (linhas 36 a 38 e 45 a 46) passam a `primary`. Sem `transition-colors` nem `ring-ring/50`.

**Acceptance criteria:**
- [x] Cada variante tem o visual da tabela: `primary` fundo `--ink` e texto `--canvas`; `accent` fundo `--signal` e texto `--signal-ink`; `secondary` transparente com borda `--input` e hover `--sunken`; `ghost` sem borda e hover `--sunken`; `danger` texto e borda `--failed` e hover `--failed-soft` (ADR-0024, "Componentes").
- [x] Botão sem `variant` explícito renderiza `primary`; foco por teclado mostra anel opaco de 2 px em `--ring`; hover troca cor sem transição (ADR-0024, "Foco" e "Movimento").
- [x] Espaço e raio seguem a escala (`--r-6`); `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components`.
- [x] `cd frontend && npm run typecheck` passa com os nomes antigos ainda aceitos.
- [x] Gate frontend.

**Dependencies:** Tasks 52.1, 52.3

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `emil-design-eng`

**Files likely touched:**
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/button.test.tsx`

**Estimated scope:** Small

### Task 52.6: Usos do `Button` em `backlog-review`

**Description:** Troca `outline` por `secondary` em 9 usos de 7 arquivos (conferido por grep em 2026-10-28). `ghost` não muda de nome.

**Acceptance criteria:**
- [x] Os 9 usos viram `secondary`: `StoryForm.tsx:207`, `FormDialog.tsx:59`, `ExportButtons.tsx:15` e `:23` (`buttonVariants({ variant })`), `EditableField.tsx:157`, `RenameParticipantDialog.tsx:55`, `CriteriaList.tsx:128`, `RegenerateDialog.tsx:71` e `:76` (ADR-0024, "Componentes").
- [x] `backlog-review` 44, 45 e 48 seguem passando, sem mudar asserção.
- [x] `npm run typecheck` verde.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] `git grep -n 'variant: "outline"\|variant="outline"' -- frontend/src/features/backlog-review` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.5

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/backlog-review/StoryForm.tsx`, `frontend/src/features/backlog-review/FormDialog.tsx`, `frontend/src/features/backlog-review/ExportButtons.tsx`
- `frontend/src/features/backlog-review/EditableField.tsx`, `frontend/src/features/backlog-review/RenameParticipantDialog.tsx`, `frontend/src/features/backlog-review/CriteriaList.tsx`, `frontend/src/features/backlog-review/RegenerateDialog.tsx`

**Estimated scope:** Medium (7 arquivos, troca de uma palavra por uso, guiada pelo `typecheck`)

### Task 52.7: Usos do `Button`: lote 2 (`ProviderForm`, `RemoveDialog`, `ConfirmDialog`, `SourceWarningDialog`, `RecordingPanel`)

**Description:** Troca `outline` por `secondary` e `destructive` por `danger` em 8 usos de 5 arquivos. O `secondary` de `ProviderForm.tsx:291` fica como está.

**Acceptance criteria:**
- [x] `ProviderForm.tsx:226` e `:274`, `RemoveDialog.tsx:39`, `ConfirmDialog.tsx:52` e `SourceWarningDialog.tsx:45` viram `secondary`.
- [x] `RemoveDialog.tsx:42` e `RecordingPanel.tsx:46` viram `danger`; `ConfirmDialog.tsx:56` vira `destructive ? "danger" : "primary"`.
- [x] `llm-providers` 34, 35 e 37, `meetings` 42 e 43 e `screen-recording` 8 e 13 seguem passando.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers src/features/screen-recording src/features/meetings src/components`.
- [x] Gate frontend.

**Dependencies:** Task 52.5

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/llm-providers/ProviderForm.tsx`, `frontend/src/features/llm-providers/RemoveDialog.tsx`
- `frontend/src/components/surfaces/ConfirmDialog.tsx`
- `frontend/src/features/screen-recording/SourceWarningDialog.tsx`, `frontend/src/features/screen-recording/RecordingPanel.tsx`

**Estimated scope:** Medium

### Task 52.8: Usos do `Button`: lote 3 (`CancelSplitButton`, `Layout`, `MeetingListPage`, `TitleEditor`, `SpeakerRow`)

**Description:** Troca `outline` por `secondary` em 4 usos e o ternário de `SpeakerRow` em 1; o tamanho `icon-lg` de `SpeakerRow` passa a `icon`. Com os lotes 1 e 2 fecha os 22 usos de `variant` em 17 arquivos.

**Acceptance criteria:**
- [x] `CancelSplitButton.tsx:24`, `Layout.tsx:42` (o `size="sm"` fica), `MeetingListPage.tsx:87` e `TitleEditor.tsx:57` viram `secondary`.
- [x] `SpeakerRow.tsx:40` vira `playing ? "primary" : "secondary"` e `SpeakerRow.tsx:41` vira `size="icon"`.
- [x] `participants` 26, `transcript-split` 45 e `meetings` 40 e 41 seguem passando.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split src/features/participants src/features/meetings src/app`.
- [x] Gate frontend.

**Dependencies:** Task 52.5

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/transcript-split/CancelSplitButton.tsx`, `frontend/src/app/Layout.tsx`
- `frontend/src/features/meetings/MeetingListPage.tsx`, `frontend/src/features/meetings/TitleEditor.tsx`
- `frontend/src/features/participants/SpeakerRow.tsx`

**Estimated scope:** Medium

### Task 52.9: Remover variantes e tamanhos antigos do `Button`

**Description:** `button.tsx` perde os apelidos transitórios (`default`, `outline`, `destructive`, `xs`, `lg`, `icon-xs`, `icon-lg`). `LoginPage.tsx:72` e `RegisterPage.tsx:85` trocam `size="lg"` por `default` (36 px). O `typecheck` passa a recusar nome antigo.

**Acceptance criteria:**
- [x] O tipo de `variant` aceita só `primary`, `accent`, `secondary`, `ghost` e `danger`; o de `size` só `default`, `sm`, `icon` e `icon-sm` (ADR-0024, "Componentes").
- [x] Nenhum uso antigo resta em `src/` (grep abaixo); os 3 usos de `size` (`LoginPage.tsx:72`, `RegisterPage.tsx:85`, `SpeakerRow.tsx:41`) estão trocados.
- [x] `auth` 22 a 26 seguem passando.

**Verification:**
- [x] `git grep -nE 'variant[=:] ?\{?"(default|outline|destructive|link)"|size="(xs|lg|icon-xs|icon-lg)"' -- frontend/src` sem achado.
- [x] `cd frontend && npm test -- --run src/features/auth src/components` e `npm run typecheck`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.6, 52.7, 52.8

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/ui/button.tsx`
- `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/features/auth/RegisterPage.tsx`

**Estimated scope:** Small

### Task 52.10: Classes de cor Ata no `StatusBadge`

**Description:** Troca as classes de `StatusBadge.tsx:19` a `:25` conforme "Classes de cor a trocar" do ADR-0024. Pílula e rótulo ficam para a Task 53.3.

**Acceptance criteria:**
- [x] `pending` usa `text-ink-muted`; `processing` e `generating` usam `text-signal`; `transcribed` usa `text-ink`; `needs_split` usa `text-warn`; `done` usa `text-done`; `failed` usa `text-failed`.
- [x] Os 7 estados seguem com ícone e texto, nunca só cor (WCAG 2.2 AA; `meetings` 40).
- [x] `StatusBadge.test.tsx` passa sem mudar asserção de critério.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces/StatusBadge`.
- [x] `git grep -nE "highlight|status-(pending|processing|done|failed)" -- frontend/src/components/surfaces/StatusBadge.tsx` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `minimalist-ui`, `shadcn`

**Files likely touched:**
- `frontend/src/components/surfaces/StatusBadge.tsx`
- `frontend/src/components/surfaces/StatusBadge.test.tsx`

**Estimated scope:** Small

### Task 52.11: Classes de cor Ata em `backlog-review`

**Description:** `MergeNotice.tsx:5` e `EditableField.tsx:144` trocam `text-highlight` por `text-signal`.

**Acceptance criteria:**
- [x] As duas linhas usam `text-signal`; a dica do campo mantém `role="status"` (`backlog-review` 41 e 40).
- [x] `backlog-review` 40 e 41 seguem passando.
- [x] Nenhum `highlight` resta nos dois arquivos.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] `git grep -n "highlight" -- frontend/src/features/backlog-review/MergeNotice.tsx frontend/src/features/backlog-review/EditableField.tsx` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/backlog-review/MergeNotice.tsx`, `frontend/src/features/backlog-review/EditableField.tsx`

**Estimated scope:** Small

### Task 52.12: Classes de cor Ata em `transcript-split`

**Description:** `CutControls.tsx:58` troca `border-highlight bg-highlight text-highlight-foreground` por `border-signal bg-signal text-signal-ink`; `CutControls.tsx:71` troca `bg-highlight` por `bg-signal`; `PartSummary.tsx:27` troca `text-status-done` por `text-done` (`text-destructive` segue, é apelido).

**Acceptance criteria:**
- [x] Marcador de corte ativo e linha de corte usam `--signal` (`transcript-split` 33).
- [x] "Parte cabe" usa `text-done`, e a Parte que não cabe segue com `text-destructive` (`transcript-split` 34).
- [x] `transcript-split` 33 e 34 seguem passando.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] `git grep -nE "highlight|status-done" -- frontend/src/features/transcript-split` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/transcript-split/CutControls.tsx`, `frontend/src/features/transcript-split/PartSummary.tsx`

**Estimated scope:** Small

### Task 52.13: Classes de cor Ata em `llm-providers`

**Description:** `ProviderForm.tsx:254`, `:258` e `:260` e `SettingsPage.tsx:14` trocam `text-status-done` por `text-done`.

**Acceptance criteria:**
- [x] Sucesso do teste de conexão, "salvo" e provedor ativo usam `text-done` (`llm-providers` 33 a 35).
- [x] `llm-providers` 33 a 35 seguem passando.
- [x] Nenhum `status-done` resta em `llm-providers`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] `git grep -n "status-" -- frontend/src/features/llm-providers` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/llm-providers/ProviderForm.tsx`, `frontend/src/features/llm-providers/SettingsPage.tsx`

**Estimated scope:** Small

### Task 52.14: `Notice`

**Description:** `components/surfaces/Notice.tsx` com variantes `info`, `warn`, `error` e `consent`. Régua esquerda de 2 px, texto em `--ink`, ícone na cor da variante. Substitui só alerta de bloco ou de página; as telas passam a usá-lo nas suas tasks (53 a 61). Erro de campo fica no `FormField`.

**Acceptance criteria:**
- [x] Fundo e régua por variante: `info` `--signal-soft` e `--signal`; `warn` `--warn-soft` e `--warn`; `error` `--failed-soft` e `--failed`; `consent` `--sunken` e `--ink-muted` (ADR-0024, "Componentes").
- [x] `error` tem `role="alert"`; `info` e `warn` têm `role="status"`; `consent` não tem região viva.
- [x] A mensagem renderiza só como texto React, inclusive com `<script>` (SEC-12); `vitest-axe` sem violação nas quatro variantes.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend. SEC-12.

**Dependencies:** Tasks 52.1, 52.3

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `emil-design-eng`

**Files likely touched:**
- `frontend/src/components/surfaces/Notice.tsx`
- `frontend/src/components/surfaces/Notice.test.tsx`

**Estimated scope:** Small

### Task 52.15: `ConsentNotice` sobre `Notice variant="consent"`

**Description:** `ConsentNotice` passa a renderizar `Notice variant="consent"` com `CONSENT_NOTICE_TEXT` intacto. As Tasks 57.2 e 61.2 só posicionam o componente. Mudar o texto é "Perguntar antes".

**Acceptance criteria:**
- [x] O componente renderiza `Notice variant="consent"` e o texto é igual a `CONSENT_NOTICE_TEXT`, sem checkbox, sem confirmação e sem bloquear nada (`meetings` 52; `screen-recording` 26; Q71).
- [x] O texto continua em um único lugar do código (`messages.ts`); o teste que busca a frase em `src/` acha só esse arquivo (Q72).
- [x] `ConsentNotice.test.tsx` afirma `Notice variant="consent"` e a igualdade com a constante (ADR-0024, "Testes a atualizar").

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces/ConsentNotice`.
- [x] `git diff -- frontend/src/components/surfaces/ConsentNotice/messages.ts` vazio.
- [x] Gate frontend.

**Dependencies:** Task 52.14

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/ConsentNotice/ConsentNotice.tsx`
- `frontend/src/components/surfaces/ConsentNotice/ConsentNotice.test.tsx`

**Estimated scope:** Small

### Task 52.16: `DialogSurface` opaco, aplicado ao `ConfirmDialog`

**Description:** `components/surfaces/DialogSurface.tsx`: superfície opaca de diálogo (`--surface`, `--r-10`, `--overlay-shadow`) sobre `--scrim`, sem `backdrop-filter`. `ConfirmDialog` troca `GlassPanel` por ele, o overlay `bg-black/40` por `bg-scrim`, e o comentário da linha 22. Cobre `meetings/DeleteMeetingDialog`, `meetings/RetryButton`, `backlog-review/RetryButton` e `backlog-review/ConfirmDeleteDialog`, que passam por `ConfirmDialog`.

**Acceptance criteria:**
- [x] `DialogSurface` é opaco (sem `backdrop-filter`), com `--surface`, raio `--r-10` e `--overlay-shadow`; o overlay usa `--scrim` (ADR-0024, "Componentes" e "Vidro").
- [x] `ConfirmDialog` usa `DialogSurface`; `MeetingDetailPage.test.tsx` e `meetings/RetryButton.test.tsx` afirmam `DialogSurface` em vez de `data-slot="glass-panel"`, com as mesmas asserções de `meetings` 42 e 43.
- [x] `vitest-axe` sem violação; foco entra no diálogo e volta ao gatilho.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces src/features/meetings src/features/backlog-review`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.3, 52.5

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `emil-design-eng`

**Files likely touched:**
- `frontend/src/components/surfaces/DialogSurface.tsx`, `frontend/src/components/surfaces/DialogSurface.test.tsx`, `frontend/src/components/surfaces/ConfirmDialog.tsx`
- `frontend/src/features/meetings/MeetingDetailPage.test.tsx`, `frontend/src/features/meetings/RetryButton.test.tsx`

**Estimated scope:** Medium

### Task 52.17: `DialogSurface` em `FormDialog` e `RegenerateDialog`

**Description:** `FormDialog` (e, por ele, `RenameParticipantDialog` e `MoveStoryDialog`) e `RegenerateDialog` trocam `GlassPanel` por `DialogSurface` e o overlay por `bg-scrim`. Comentário de `FormDialog.tsx:21` atualizado.

**Acceptance criteria:**
- [x] Os dois diálogos usam `DialogSurface`, sem `GlassPanel`; `RegenerateDialog.test.tsx` afirma `DialogSurface` em vez de `glass-panel` (ADR-0024, "Testes a atualizar").
- [x] `backlog-review` 43, 44 e 48 seguem passando.
- [x] Nenhum `rounded-xl` nos dois arquivos.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] `git grep -n "GlassPanel" -- frontend/src/features/backlog-review` só acha comentário ou nada (nenhum import).
- [x] Gate frontend.

**Dependencies:** Task 52.16

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/backlog-review/FormDialog.tsx`, `frontend/src/features/backlog-review/RegenerateDialog.tsx`
- `frontend/src/features/backlog-review/RegenerateDialog.test.tsx`

**Estimated scope:** Small

### Task 52.18: `DialogSurface` em `SourceWarningDialog`

**Description:** `SourceWarningDialog` (aviso de fontes da gravação) troca `GlassPanel` por `DialogSurface`.

**Acceptance criteria:**
- [x] O diálogo usa `DialogSurface`, sem `GlassPanel` nem `rounded-xl`.
- [x] `screen-recording` 4, 5 e 7 (aviso de fonte ausente, "Cancelar" encerra a captura) seguem passando.
- [x] `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Gate frontend.

**Dependencies:** Task 52.16

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/screen-recording/SourceWarningDialog.tsx`
- `frontend/src/features/screen-recording/RecordPage.test.tsx`

**Estimated scope:** Small

### Task 52.19: `DialogSurface` em `RemoveDialog`

**Description:** `RemoveDialog` (e, por ele, `ProviderForm`) troca `GlassPanel` por `DialogSurface`. Comentário de `RemoveDialog.tsx:14` atualizado. Fecha o critério reaberto da Task 17.2.

**Acceptance criteria:**
- [x] O diálogo de remoção usa `DialogSurface`; `ProviderForm.test.tsx` afirma `DialogSurface` em vez de `glass-panel` (ADR-0024, "Testes a atualizar").
- [x] "Remover" pede confirmação antes de chamar a API (`llm-providers` 37).
- [x] Nenhum `rounded-xl` no arquivo.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] Gate frontend.

**Dependencies:** Task 52.16

**Skills:** `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/llm-providers/RemoveDialog.tsx`
- `frontend/src/features/llm-providers/ProviderForm.test.tsx`

**Estimated scope:** Small

### Task 52.20: `GlassPanel` com tokens Ata

**Description:** `glass.css` lê `--surface` e `--ink` em vez de `--card` e `--card-foreground` (linhas 5, 6 e 16) e usa `box-shadow: var(--overlay-shadow)` em vez de `var(--elevation-2)` (linha 8). Comentários de `GlassPanel.tsx:11` e `glass.css:1` deixam de citar diálogo. `GlassPanel.test.tsx` passa a `--surface`, `--ink` e `--signal` (linha 145).

**Acceptance criteria:**
- [x] Texto sobre o painel mantém 4,5:1 contra o pior fundo, nos temas claro e escuro, com os tokens novos (ADR-0024, "Vidro"; `02-architecture.md`, "Contraste sobre vidro").
- [x] Fallback opaco continua em `@supports not`, `prefers-reduced-transparency` e `forced-colors`.
- [x] `no-stray-backdrop.test.ts` passa sem mudar regra.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces/GlassPanel src/styles`.
- [x] `git grep -nE "elevation|--card" -- frontend/src/styles/glass.css` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `high-end-visual-design`, `frontend-ui-engineering`, `ui-animation`

**Files likely touched:**
- `frontend/src/styles/glass.css`, `frontend/src/components/surfaces/GlassPanel.tsx`
- `frontend/src/components/surfaces/GlassPanel.test.tsx`

**Estimated scope:** Small

### Task 52.21: Teste: nenhum diálogo renderiza `GlassPanel`

**Description:** Teste estático varre `src/**/*.tsx` (sem testes): todo arquivo que importa `AlertDialog` ou `Dialog` de `radix-ui` importa `DialogSurface` e não importa `GlassPanel`.

**Acceptance criteria:**
- [x] O teste falha se um diálogo importar `GlassPanel` (ADR-0024, "Testes novos"; `02-architecture.md`, "Verificação").
- [x] O teste falha se um diálogo não usar `DialogSurface`.
- [x] O teste passa com os 5 diálogos diretos migrados (`ConfirmDialog`, `FormDialog`, `RegenerateDialog`, `SourceWarningDialog`, `RemoveDialog`).

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.17, 52.18, 52.19

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/dialogs-opaque.test.ts`

**Estimated scope:** Small

### Task 52.22: `PageHeader`

**Description:** `components/surfaces/PageHeader.tsx`: título `h1` em serif, descrição em `--ink-muted`, ações à direita. Sem card.

**Acceptance criteria:**
- [x] Renderiza um `h1` com `font-heading` (Source Serif 4), descrição opcional em `--ink-muted` e área de ações à direita (ADR-0024, "Componentes").
- [x] Usa só tamanhos da escala e espaço da escala; nenhum `text-[`.
- [x] `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.2, 52.3

**Skills:** `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/components/surfaces/PageHeader.tsx`
- `frontend/src/components/surfaces/PageHeader.test.tsx`

**Estimated scope:** Small

### Task 52.23: `Skeleton`

**Description:** `components/surfaces/Skeleton.tsx` único (hoje há cópias nas páginas). Fundo `--sunken`, raio `--r-4`, respiração lenta de opacidade em `motion.css`.

**Acceptance criteria:**
- [x] Anima só `opacity` e fica parado com `prefers-reduced-motion: reduce`; CSS e hook `useReducedMotion` concordam (ADR-0024, "Movimento"; `02-architecture.md`, "Restrições obrigatórias").
- [x] Usa `--sunken` e `--r-4`; o contêiner de carregamento anuncia por `aria-busy` ou região `role="status"`.
- [x] `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces src/styles`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.1, 52.3

**Skills:** `minimalist-ui`, `emil-design-eng`, `ui-animation`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/Skeleton.tsx`, `frontend/src/styles/motion.css`
- `frontend/src/components/surfaces/Skeleton.test.tsx`

**Estimated scope:** Small

### Task 52.24: `EmptyState`

**Description:** `components/surfaces/EmptyState.tsx` único: título, descrição e ação opcional, sem card.

**Acceptance criteria:**
- [x] Mostra título e descrição, e a ação só quando for passada (ADR-0024, "Componentes").
- [x] Sem card, sem sombra e sem raio acima de 10 px; usa espaço da escala.
- [x] `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.3, 52.5

**Skills:** `minimalist-ui`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/EmptyState.tsx`
- `frontend/src/components/surfaces/EmptyState.test.tsx`

**Estimated scope:** Small

### Task 52.25: Remover o atalho de tecla `d` do `theme-provider`

**Description:** `theme-provider.tsx` perde o `keydown` (linhas 160 a 177 hoje). A leitura e a escrita em `localStorage` e a sincronização entre abas ficam.

**Acceptance criteria:**
- [x] O `theme-provider` não registra listener de `keydown`; apertar `d` não muda o tema (WCAG 2.2, critério 2.1.4; ADR-0024, "Tema").
- [x] A preferência de tema segue em `localStorage` e a sessão nunca vai a `localStorage` nem `sessionStorage` (`03-security.md`, "Never").
- [x] O tema escolhido continua aplicado depois de recarregar.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components`.
- [x] `git grep -n "keydown" -- frontend/src/components/theme-provider.tsx` sem achado.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/theme-provider.tsx`
- `frontend/src/components/theme-provider.test.tsx`

**Estimated scope:** Small

### Task 52.26: `ThemeToggle`

**Description:** `components/surfaces/ThemeToggle.tsx` com claro, escuro e sistema, ligado ao `useTheme`. O `AppShell` (Task 53.1) e o auth (Task 55.1) o encaixam.

**Acceptance criteria:**
- [x] Oferece claro, escuro e sistema; o escolhido aparece marcado e é gravado em `localStorage` pelo `theme-provider` (ADR-0024, "Tema").
- [x] Opera por teclado, tem nome acessível e alvo de pelo menos 24 px; sem atalho de tecla.
- [x] `vitest-axe` sem violação nos dois temas.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.5, 52.25

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/ThemeToggle.tsx`
- `frontend/src/components/surfaces/ThemeToggle.test.tsx`

**Estimated scope:** Small

### Task 52.27: `theme-color` do `index.html` igual a `--canvas`

**Description:** `index.html:6-7` troca `#ffffff` e `#0a0a0a` pelo hex equivalente ao `oklch` de `--canvas` claro (`oklch(0.985 0.004 85)`) e escuro (`oklch(0.175 0.009 220)`).

**Acceptance criteria:**
- [x] O `theme-color` claro e o escuro são o hex de `--canvas` de cada tema (ADR-0024, "Tema").
- [x] Teste converte o `oklch` de `tokens.css` (com `src/test/color.ts`) e compara com o `content` de cada meta, com tolerância de um nível por canal.
- [x] O preload de fontes da Task 52.2 segue intacto.

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles`.
- [x] Gate frontend.

**Dependencies:** Task 52.1

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/index.html`
- `frontend/src/styles/theme-color.test.ts`

**Estimated scope:** Small

### Task 52.28: Regra ESLint: `components/**` não importa `@/features/*`

**Description:** `eslint.config.js` ganha `no-restricted-imports` para `src/components/**` barrando `@/features/*`. Hoje não há import desse tipo em `components/` (grep de 2026-10-28), então o lint segue verde.

**Acceptance criteria:**
- [x] `npm run lint` falha com import de `@/features/*` dentro de `components/**` (`AGENTS.md`, "Regras de código"; ADR-0024, "Componentes").
- [x] `npm run lint` passa no repo atual.
- [x] A regra de SEC-12 (`dangerouslySetInnerHTML`) continua ativa.

**Verification:**
- [x] Manual: criar `frontend/src/components/surfaces/tmp-lint.tsx` com `import "@/features/auth/useSession"`, rodar `cd frontend && npx eslint src/components/surfaces/tmp-lint.tsx` e ver `no-restricted-imports`; apagar o arquivo antes do commit.
- [x] `cd frontend && npm run lint`.

**Dependencies:** None (dentro da Task 52)

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/eslint.config.js`

**Estimated scope:** Small

### Task 52.29: `SamplePage` no Ata

**Description:** `app/SamplePage.tsx` refeita: lista os tokens da tabela "Tokens" (linha 20 hoje cita `highlight`), mostra `Button` (cinco variantes), `Notice` (quatro variantes), `StatusBadge` (sete estados), `PageHeader`, `Skeleton`, `EmptyState` e `ThemeToggle`. O vidro aparece só como exemplo do painel da gravação, sem gradiente (a linha 55 hoje usa `bg-gradient-to-br from-highlight to-foreground`; vira `rounded-lg bg-signal`).

**Acceptance criteria:**
- [x] A amostra lista os tokens Ata e usa os componentes novos (ADR-0024, "Testes a atualizar").
- [x] Nenhum `GlassPanel` de diálogo e nenhum gradiente na amostra.
- [x] `SamplePage.test.tsx` passa `vitest-axe` sem violação nos dois temas.

**Verification:**
- [x] `cd frontend && npm test -- --run src/app`.
- [x] `git grep -nE "highlight|gradient" -- frontend/src/app/SamplePage.tsx` sem achado.
- [x] Gate frontend.

**Dependencies:** Tasks 52.14, 52.16, 52.20, 52.22, 52.23, 52.24, 52.26

**Skills:** `minimalist-ui`, `frontend-ui-engineering`, `shadcn`

**Files likely touched:**
- `frontend/src/app/SamplePage.tsx`
- `frontend/src/app/SamplePage.test.tsx`

**Estimated scope:** Small

### Task 52.30: Remover os tokens substituídos e travar com teste

**Description:** `tokens.css` perde `--highlight`, `--highlight-foreground`, `--status-*`, `--sidebar-*`, `--chart-*`, `--elevation-1`, `--elevation-2` e `--radius`. `index.css` perde `--color-highlight*`, `--color-status-*` (linhas 33 a 38), `--color-chart-*` e `--color-sidebar-*` (linhas 43 a 55). `spotlight.css:18` troca `var(--highlight)` por `var(--signal)`. `tokens.test.ts` perde os pares e nomes antigos (linhas 47 a 60 e 93; `--sidebar-foreground` na 52). Teste novo trava o retorno dos nomes.

**Acceptance criteria:**
- [x] Em `components/`, `styles/`, `index.css` e `app/SamplePage.tsx`, nenhum resultado para `highlight|status-(pending|processing|done|failed)|sidebar|chart-`, na forma de variável e na de classe (checkpoint da Task 52).
- [x] Em todo o `src/`, nenhuma das classes da tabela "Classes de cor a trocar" resta (`text-highlight`, `bg-highlight`, `border-highlight`, `text-highlight-foreground`, `text-status-*`).
- [x] `spotlight.css` lê `--signal`; a Task 57.1 recorta o realce para a borda.

**Verification:**
- [x] `cd frontend && npm test -- --run` (teste novo `removed-tokens.test.ts`, que se exclui da própria busca).
- [x] Gate frontend.

**Dependencies:** Tasks 52.10, 52.11, 52.12, 52.13, 52.20, 52.29

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/styles/tokens.css`, `frontend/src/index.css`, `frontend/src/styles/spotlight.css`
- `frontend/src/styles/tokens.test.ts`, `frontend/src/styles/removed-tokens.test.ts`

**Estimated scope:** Medium

### Checkpoint: Tokens e primitivos

- [x] `cd frontend && npm test -- --run`, `npm run lint`, `npm run typecheck` e `npm run build` passam
- [x] `tokens.test.ts` com todos os pares de contraste do ADR-0024, nos dois temas; pares marcados "a conferir" confirmados ou fundos `-soft` ajustados
- [x] Nenhum diálogo renderiza `GlassPanel`; `no-stray-backdrop.test.ts` passa
- [x] Grep em `components/`, `styles/`, `index.css` e `app/SamplePage.tsx` sem resultado para `highlight|status-(pending|processing|done|failed)|sidebar|chart-` (forma de variável e forma de classe)
- [x] Usos em `features/` da tabela "Classes de cor a trocar" do ADR-0024 trocados, conferidos linha a linha no PR
- [x] `git grep -nE 'variant[=:] ?\{?"(default|outline|destructive|link)"|size="(xs|lg|icon-xs|icon-lg)"' -- frontend/src` sem achado (22 usos de `variant` em 17 arquivos e 3 de `size` trocados)
- [x] `ConsentNotice` renderiza `Notice variant="consent"`; teste de igualdade com `CONSENT_NOTICE_TEXT` passa
- [x] `npm run lint` falha com import de `@/features/*` dentro de `components/**` (conferido com arquivo de teste temporário, fora do commit)
- [x] `index.html`: `theme-color` claro e escuro iguais a `--canvas` de cada tema
- [x] `theme-provider` sem listener de `keydown`; `ThemeToggle` operável por teclado
- [ ] Fontes: quatro `.woff2` e licenças em `public/fonts/`; CSP `default-src 'self'` sem mudança; LCP do login (NFR-03) e CLS (NFR-05) medidos; contingência do `h1` aplicada se LCP passar de 2,5 s
- [x] JS inicial e total dentro de NFR-01 e NFR-02
- [ ] Checagem de UI na página de amostra
- [x] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Task 53.1: `AppShell`

**Description:** `components/surfaces/AppShell.tsx` só desenha: barra opaca com marca em serif, nav, nome do usuário, `ThemeToggle`, botão de sair, e a área de conteúdo na largura `--shell`. Recebe links, nome do usuário e `onLogout` por props e não importa `features/`.

**Acceptance criteria:**
- [x] O item ativo da nav tem `aria-current="page"` e sublinhado de 2 px em `--signal`; a nav opera por teclado (ADR-0024, "Componentes").
- [x] A barra é opaca (sem `backdrop-filter`) e o conteúdo tem largura `--shell` (`02-architecture.md`, "Mapa de superfícies").
- [x] `ThemeToggle` presente; `vitest-axe` sem violação nos dois temas.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces src/styles`.
- [x] Gate frontend.

**Dependencies:** Checkpoint: Tokens e primitivos

**Skills:** `minimalist-ui`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/components/surfaces/AppShell.tsx`
- `frontend/src/components/surfaces/AppShell.test.tsx`

**Estimated scope:** Small

### Task 53.2: `app/Layout.tsx` compõe o `AppShell`

**Description:** `Layout` segue em `app/` e guarda sessão (`useSession`), logout e links; passa tudo ao `AppShell` e coloca o `Outlet` como conteúdo.

**Acceptance criteria:**
- [x] Depois do logout o frontend volta ao login (`auth` 26); página protegida sem sessão leva ao login (`auth` 24).
- [x] A nav mostra "Reuniões" e "Configurações", com o item da rota atual marcado por `aria-current="page"`.
- [x] A sessão nunca vai a `localStorage` nem `sessionStorage` (`03-security.md`, "Never"; SEC-03).

**Verification:**
- [x] `cd frontend && npm test -- --run src/app src/features/auth`.
- [x] Gate frontend.

**Dependencies:** Task 53.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/app/Layout.tsx`
- `frontend/src/app/routes.test.tsx`

**Estimated scope:** Small

### Task 53.3: `StatusBadge` sem pílula

**Description:** `StatusBadge` perde a pílula com borda: ícone mais rótulo, com as cores da tabela "Estados" (ícone por estado; rótulo `--ink`, e `--failed` em `failed`). Mantém a região `aria-live` de mudança de status.

**Acceptance criteria:**
- [x] Os 7 estados mostram ícone e texto, sem borda e sem fundo de pílula, com as cores da tabela "Estados" (ADR-0024, "Estados").
- [x] A mudança de status segue anunciada em região `aria-live` (`meetings` 40).
- [x] `vitest-axe` sem violação; contraste do rótulo 4,5:1 nos dois temas.

**Verification:**
- [x] `cd frontend && npm test -- --run src/components/surfaces/StatusBadge`.
- [x] Gate frontend.

**Dependencies:** Checkpoint: Tokens e primitivos

**Skills:** `minimalist-ui`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/components/surfaces/StatusBadge.tsx`
- `frontend/src/components/surfaces/StatusBadge.test.tsx`

**Estimated scope:** Small

### Task 53.4: Lista de reuniões no Ata

**Description:** `MeetingListPage` com `PageHeader`, linhas com régua `--hairline` e régua forte `--ink` no topo da lista (sem card), datas e durações em Geist Mono tabular, `Skeleton`, `EmptyState` e `Notice variant="error"` no lugar da caixa inline (linhas 40 a 41). Polling não muda.

**Acceptance criteria:**
- [x] A lista atualiza o status sem recarregar enquanto a Reunião está em `pending`, `processing`, `generating`, ou `transcribed` com `participants_confirmed` verdadeiro, e não faz polling fora disso (`meetings` 40).
- [x] Linhas separadas por régua, sem card; datas e durações em `font-mono` com algarismos tabulares (ADR-0024, "Profundidade" e "Tipografia").
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [x] Grep local em `MeetingListPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2, 53.3

**Skills:** `minimalist-ui`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`, `responsive-design`, `animate`

**Files likely touched:**
- `frontend/src/features/meetings/MeetingListPage.tsx`, `frontend/src/features/meetings/format.ts`
- `frontend/src/features/meetings/MeetingListPage.test.tsx`

**Estimated scope:** Small

### Task 54.1: Revisão do backlog no Ata: página, avisos e estados

**Description:** `ReviewPage` com `PageHeader`, `Skeleton` e `EmptyState`. A constante `ALERT` (linha 19) e os blocos de erro (linhas 33 e 160) viram `Notice`: `error` para falha, `warn` para a última geração com falha, `info` para só leitura.

**Acceptance criteria:**
- [x] Em `failed` com backlog, a tela mostra só leitura, aviso de que a última geração falhou, o motivo e "Tentar novamente"; em `transcribed`, `generating` e `needs_split` com backlog, só leitura com o status atual (`backlog-review` 46).
- [x] Texto de US e de Epic renderiza escapado, inclusive `<script>` (SEC-12; `backlog-review` 39).
- [x] Grep local em `ReviewPage.tsx` sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Grep local em `ReviewPage.tsx`. SEC-12.
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2, 53.3, 53.4

**Skills:** `minimalist-ui`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/ReviewPage.tsx`
- `frontend/src/features/backlog-review/ReviewPage.test.tsx`

**Estimated scope:** Small

### Task 54.2: Revisão do backlog no Ata: Epic com régua forte

**Description:** `EpicSection` sem card: régua forte em `--ink` no topo de cada Epic, título em serif, abrir e fechar animado só com `transform` e `opacity` (120 a 240 ms).

**Acceptance criteria:**
- [x] A Epic não tem fundo de card nem borda em volta; a régua `--ink` fica no topo (ADR-0024, "Profundidade" e "Componentes").
- [x] Abrir e fechar anima só `transform` e `opacity`, desligado com `prefers-reduced-motion` (ADR-0024, "Movimento").
- [ ] Com backlog de fixture de 30 Epics e 200 US o INP fica até 200 ms (NFR-04; medição manual no checkpoint).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review src/styles`.
- [x] Grep local em `EpicSection.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 54.1

**Skills:** `minimalist-ui`, `design-taste-frontend`, `frontend-ui-engineering`, `animate`

**Files likely touched:**
- `frontend/src/features/backlog-review/EpicSection.tsx`
- `frontend/src/features/backlog-review/ReviewPage.test.tsx`

**Estimated scope:** Small

### Task 54.3: Revisão do backlog no Ata: US como linha com régua

**Description:** `StoryCard` deixa de ser card: linha com régua `--hairline`, nome da US em serif, `US-id` e instante em Geist Mono tabular, demais campos em Geist.

**Acceptance criteria:**
- [x] A US aparece como linha com régua, sem card, com todos os campos do formato, solicitante e instante (`backlog-review` 39).
- [x] `US-id` e instante usam `font-mono` com algarismos tabulares; nome da US usa `font-serif` (ADR-0024, "Tipografia").
- [x] Texto da US renderiza escapado (SEC-12); grep local sem achado.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Grep local em `StoryCard.tsx`. SEC-12.
- [x] Gate frontend.

**Dependencies:** Task 54.2

**Skills:** `minimalist-ui`, `design-taste-frontend`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/StoryCard.tsx`
- `frontend/src/features/backlog-review/ReviewPage.test.tsx`

**Estimated scope:** Small

### Task 54.4: Revisão do backlog no Ata: campos editáveis

**Description:** `EditableField`, `StoryForm`, `CriteriaList` e `NewEpicForm` no Ata: campos de 40 px, foco opaco, erro 422 inline junto do campo (sem `Notice`), espaço e raio da escala, sem `ring-ring/50` nem `text-[`.

**Acceptance criteria:**
- [x] Cada campo de Epic, US e critério segue editável na tela, com prioridade, story points, solicitante e instante; erro 422 aparece junto ao campo (`backlog-review` 40).
- [x] Teclado em tudo e anel de foco opaco de 2 px (ADR-0024, "Foco").
- [x] Grep local sem achado nos quatro arquivos; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Grep local nos quatro arquivos.
- [x] Gate frontend.

**Dependencies:** Task 54.3

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/backlog-review/EditableField.tsx`, `frontend/src/features/backlog-review/StoryForm.tsx`
- `frontend/src/features/backlog-review/CriteriaList.tsx`, `frontend/src/features/backlog-review/NewEpicForm.tsx`
- `frontend/src/features/backlog-review/EditableField.test.tsx`

**Estimated scope:** Medium

### Task 54.5: Revisão do backlog no Ata: diálogos

**Description:** Os diálogos já usam `DialogSurface` (Tasks 52.16 e 52.17). Aqui o conteúdo vai ao Ata: erro de diálogo vira `Notice variant="error"`, `MergeNotice` vira `Notice variant="info"`, e saem as classes proibidas de `RenameParticipantDialog`, `MoveStoryDialog`, `ConfirmDeleteDialog`, `FormDialog` e `RegenerateDialog`.

**Acceptance criteria:**
- [x] Renomear ou criar Epic, ou renomear Participante, com nome que já existe mostra, antes de salvar, que os dois serão juntados (`backlog-review` 41).
- [x] Excluir US, Epic ou critério pede confirmação, e excluir Epic com US fica desabilitado (`backlog-review` 42); mover US abre a escolha de Epic (`backlog-review` 43); regenerar avisa da perda das edições (`backlog-review` 44).
- [x] Grep local sem achado nos arquivos; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Grep local nos arquivos da task.
- [x] Gate frontend.

**Dependencies:** Tasks 52.17, 54.4

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `animate`

**Files likely touched:**
- `frontend/src/features/backlog-review/RenameParticipantDialog.tsx`, `frontend/src/features/backlog-review/MoveStoryDialog.tsx`, `frontend/src/features/backlog-review/ConfirmDeleteDialog.tsx`
- `frontend/src/features/backlog-review/MergeNotice.tsx`
- `frontend/src/features/backlog-review/ConfirmDeleteDialog.test.tsx`

**Estimated scope:** Medium

### Task 54.6: Revisão do backlog no Ata: tentar de novo e exportar

**Description:** `RetryButton` do backlog usa `Notice variant="error"` para o erro; `ExportButtons` sai de classes proibidas, com `secondary` já trocado na Task 52.6.

**Acceptance criteria:**
- [x] "Tentar novamente" repete o aviso de perda das edições (`backlog-review` 46).
- [x] "Exportar Markdown" e "Exportar JSON" baixam o arquivo (`backlog-review` 45).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/backlog-review`.
- [x] Grep local nos dois arquivos.
- [x] Gate frontend.

**Dependencies:** Task 54.5

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/backlog-review/RetryButton.tsx`, `frontend/src/features/backlog-review/ExportButtons.tsx`

**Estimated scope:** Small

### Checkpoint: Shell, lista e backlog

- [ ] Testes de `meetings`, `backlog-review` e `app/` passam sem mudar critério de aceite
- [ ] Nav com `aria-current="page"` no item ativo; largura `--shell`
- [ ] INP com backlog de fixture 30 Epics e 200 US (NFR-04)
- [ ] Checagem de UI; `impeccable-design-polish` no shell, na lista e na revisão
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Task 55.1: `AuthShell` sai do `GlassPanel`: card opaco, sem sombra, sem spotlight

**Description:** `AuthShell` deixa de usar `GlassPanel` e `usePointerSpotlight` (e a classe `spotlight`). Card opaco `--surface`, régua `--hairline`, raio `--r-10`, sem sombra (exceção do card de auth, ADR-0024, Q3), entrada por opacidade, marca e `h1` em serif, `ThemeToggle`. Comentário da linha 12 atualizado. Largura do card `max-w-sm` fica, por ser tela sem shell.

**Acceptance criteria:**
- [x] O card é opaco, sem `backdrop-filter` e sem sombra, com `--surface` e `--hairline` (ADR-0024, "Princípios"; `02-architecture.md`, "Mapa de superfícies").
- [x] Nenhum listener de `pointermove` é registrado no auth e nada importa `GlassPanel` (`01-prd.md`, NFR-08: só o upload tem mouse-tracking).
- [x] `ThemeToggle` visível e operável por teclado; entrada do card só por `opacity`, desligada com `prefers-reduced-motion`; grep local sem achado.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/auth`.
- [x] `git grep -nE "GlassPanel|usePointerSpotlight|spotlight" -- frontend/src/features/auth` sem achado.
- [x] Gate frontend.

**Dependencies:** Checkpoint: Tokens e primitivos

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`, `emil-design-eng`, `ui-animation`

**Files likely touched:**
- `frontend/src/features/auth/AuthShell.tsx`
- `frontend/src/features/auth/LoginPage.test.tsx`

**Estimated scope:** Small

### Task 55.2: Tela de login no Ata

**Description:** `LoginPage` usa `Notice variant="error"` no lugar da caixa inline (linhas 44 a 46), mantém o anúncio `assertive` do erro, e o botão de entrar (`accent`, único da tela) em 36 px.

**Acceptance criteria:**
- [x] Erros do login aparecem com a mensagem da API, anunciados por região viva (`auth` 25).
- [x] Página protegida sem sessão leva ao login (`auth` 24); depois do logout volta ao login (`auth` 26).
- [x] Grep local sem achado; `vitest-axe` sem violação; mensagem renderizada só como texto (SEC-12).

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/auth src/app`.
- [x] Grep local em `LoginPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 55.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/features/auth/LoginPage.test.tsx`

**Estimated scope:** Small

### Task 55.3: Tela de cadastro no Ata

**Description:** `RegisterPage` usa `Notice variant="error"` no lugar da caixa inline (linhas 42 a 44) e o botão de cadastrar (`accent`, único da tela) em 36 px.

**Acceptance criteria:**
- [x] A tela inicial oferece cadastro e login (`auth` 22); cadastro bem-sucedido leva direto à área autenticada (`auth` 23).
- [x] Erros do cadastro aparecem com a mensagem da API (`auth` 25).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/auth`.
- [x] Grep local em `RegisterPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 55.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/auth/RegisterPage.tsx`
- `frontend/src/features/auth/RegisterPage.test.tsx`

**Estimated scope:** Small

### Task 56.1: Configurações de LLM no Ata: página

**Description:** `SettingsPage` com `PageHeader`, provedores em linhas com régua (sem card), provedor ativo com `--done`, `Skeleton` e `Notice variant="error"` no lugar da caixa das linhas 105 a 106.

**Acceptance criteria:**
- [x] Mostra os 4 provedores com estado, máscara, modelo, janela e indicação do ativo (`llm-providers` 33).
- [x] O campo de chave nunca é pré-preenchido e a máscara serve só de referência (`llm-providers` 36; SEC-07).
- [x] Grep local sem achado; `vitest-axe` sem violação; layout de 360 a 1920 px.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] Grep local em `SettingsPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/llm-providers/SettingsPage.tsx`
- `frontend/src/features/llm-providers/SettingsPage.test.tsx`

**Estimated scope:** Small

### Task 56.2: Configurações de LLM no Ata: formulário do provedor

**Description:** `ProviderForm` com `Notice variant="error"` para falha do teste (linhas 263 a 265), mensagens de sucesso em `--done`, "Salvar" como `accent` (único da tela). `ModelSelect` e `RemoveDialog` perdem as classes proibidas.

**Acceptance criteria:**
- [x] "Salvar" fica desabilitado até um "Testar conexão" bem-sucedido com os valores atuais (`llm-providers` 34); erros de teste e gravação aparecem com o motivo da API (`llm-providers` 35).
- [x] Remover pede confirmação antes de chamar a API (`llm-providers` 37); a chave nunca aparece em tela nem em log (SEC-07).
- [x] Grep local sem achado nos três arquivos; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/llm-providers`.
- [x] Grep local em `ProviderForm.tsx`, `ModelSelect.tsx` e `RemoveDialog.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 56.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/llm-providers/ProviderForm.tsx`, `frontend/src/features/llm-providers/ModelSelect.tsx`, `frontend/src/features/llm-providers/RemoveDialog.tsx`
- `frontend/src/features/llm-providers/ProviderForm.test.tsx`

**Estimated scope:** Medium

### Task 57.1: Realce de mouse-tracking só na borda da área de upload

**Description:** `spotlight.css` recorta o `::before` para a faixa da borda com `mask-composite: exclude` (e `-webkit-mask-composite: xor`), em gradiente radial `--signal`, com o miolo transparente. Sem suporte a `mask-composite`, o realce não aparece. Comentário da linha 1 (cita login) atualizado. É o único gradiente permitido.

**Acceptance criteria:**
- [x] O realce cobre só a faixa da borda; o fundo e o texto do miolo não mudam com o ponteiro sobre a área (ADR-0024, "Mouse-tracking").
- [x] O CSS só liga com `(hover: hover) and (pointer: fine)`, fica desligado com `prefers-reduced-motion`, `forced-colors` e sem suporte a `mask-composite` (`02-architecture.md`, "Restrições obrigatórias").
- [x] Teste lê `spotlight.css` e confere `mask-composite`, a cor `--signal`, a ausência de `--highlight` e o comentário sem "login".

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles src/lib/ui`.
- [x] Gate frontend.

**Dependencies:** Checkpoint: Tokens e primitivos

**Skills:** `minimalist-ui`, `emilkowalski-motion`, `animate`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/styles/spotlight.css`
- `frontend/src/styles/spotlight.test.ts`

**Estimated scope:** Small

### Task 57.2: Tela de upload no Ata

**Description:** `UploadPage` com `PageHeader`, área de soltar arquivo com borda fixa `--input` e realce da Task 57.1, foco opaco, `transition-colors` removido (linha 63), `Notice variant="error"` no lugar da caixa das linhas 187 e 188, envio como `accent` (único da tela) e `ConsentNotice` posicionado junto do botão de envio. Não mexe no componente nem no texto.

**Acceptance criteria:**
- [x] A tela aceita arquivo, título e número de participantes, recusa antes de enviar extensão fora da lista ou mais de 524.288.000 bytes, mostra erros da API e leva ao detalhe (`meetings` 35 a 39).
- [x] O aviso mostra exatamente `CONSENT_NOTICE_TEXT` junto do botão de envio (`meetings` 52).
- [x] O mouse-tracking só liga com `(hover: hover) and (pointer: fine)` e sem movimento reduzido, e nenhum listener de `pointermove` entra em toque; grep local sem achado.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [ ] Grep local em `UploadPage.tsx` (feito). Manual pendente: quadros do spotlight abaixo de 16 ms no DevTools Performance (NFR-08).
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2, 57.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`, `emilkowalski-motion`, `animate`

**Files likely touched:**
- `frontend/src/features/meetings/UploadPage.tsx`
- `frontend/src/features/meetings/UploadPage.test.tsx`

**Estimated scope:** Small

### Task 57.3: Detalhe da Reunião no Ata

**Description:** `MeetingDetailPage` com `PageHeader`, `StatusBadge` novo, links `buttonVariants()` (padrão `primary`), `Notice` no lugar das caixas das linhas 58 e 128 a 129, instantes e durações em Geist Mono. `TitleEditor` perde classes proibidas.

**Acceptance criteria:**
- [x] O detalhe atualiza o status sem recarregar enquanto a Reunião está em `pending`, `processing`, `generating`, ou `transcribed` com `participants_confirmed` verdadeiro (`meetings` 40) e permite editar o título (`meetings` 41).
- [x] Mudança de status anunciada em `aria-live`; no máximo um `accent` na tela.
- [x] Grep local sem achado em `MeetingDetailPage.tsx` e `TitleEditor.tsx`; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [x] Grep local nos dois arquivos.
- [x] Gate frontend.

**Dependencies:** Tasks 53.3, 57.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/meetings/MeetingDetailPage.tsx`, `frontend/src/features/meetings/TitleEditor.tsx`
- `frontend/src/features/meetings/MeetingDetailPage.test.tsx`

**Estimated scope:** Small

### Task 57.4: Diálogos do detalhe: tentar de novo, exclusão

**Description:** `RetryButton` e `DeleteMeetingDialog` da pasta `meetings` usam `Notice variant="error"` para o erro de diálogo. Os diálogos já usam `DialogSurface` (Task 52.16).

**Acceptance criteria:**
- [x] Em `failed`, mostra o motivo e "Tentar novamente"; com `has_backlog` verdadeiro, pede confirmação com o aviso de perda das edições (`meetings` 42).
- [x] Excluir pede confirmação e avisa que o áudio e o backlog serão apagados (`meetings` 43).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/meetings`.
- [x] Grep local nos dois arquivos.
- [x] Gate frontend.

**Dependencies:** Task 57.3

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/meetings/RetryButton.tsx`, `frontend/src/features/meetings/DeleteMeetingDialog.tsx`
- `frontend/src/features/meetings/RetryButton.test.tsx`

**Estimated scope:** Small

### Checkpoint: Auth, configurações, upload e detalhe

- [ ] Critérios de `auth`, `llm-providers` e `meetings` com tela seguem passando
- [ ] Critério 52 de `meetings`: texto do `ConsentNotice` igual a `CONSENT_NOTICE_TEXT`
- [ ] Spotlight do upload: realce só na faixa da borda; fundo e texto do miolo sem mudança com ponteiro sobre a área
- [ ] LCP do login (NFR-03) remedido; mouse-tracking só no upload (NFR-08)
- [ ] Checagem de UI
- [ ] `/security-review` sobre o diff

### Task 58: Transcrição no Ata

**Description:** `TranscriptPage` com `PageHeader`, largura `--reading`, fala em Source Serif 4, speaker em Geist, instantes `hh:mm:ss` em Geist Mono tabular, `Skeleton`, e `Notice variant="error"` no lugar da caixa das linhas 92 e 93. Lista virtualizada e `useTranscript` não mudam.

**Acceptance criteria:**
- [x] Mostra segmentos em ordem, cada um com instante, speaker e texto (`diarized-transcription` 25); antes de `transcribed`, mostra o status (`diarized-transcription` 27); mostra o nome do Participante depois da nomeação (`diarized-transcription` 26).
- [x] Com Transcrição de 2 h de fixture, só os segmentos perto da área visível ficam no DOM (`diarized-transcription` 31; NFR-07); texto de segmento renderiza escapado (SEC-12).
- [x] Grep local sem achado; `vitest-axe` sem violação; fala em `font-serif` e instante em `font-mono`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/diarized-transcription`.
- [x] Grep local em `TranscriptPage.tsx`. SEC-12.
- [x] Gate frontend.

**Dependencies:** Tasks 52 (Checkpoint: Tokens e primitivos), 53.1, 53.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/diarized-transcription/TranscriptPage.tsx`
- `frontend/src/features/diarized-transcription/TranscriptPage.test.tsx`

**Estimated scope:** Small

### Task 59.1: Nomeação no Ata: página

**Description:** `NamingPage` com `PageHeader`, largura `--reading`, `Notice` no lugar da constante `ALERT` (linha 21) e dos blocos das linhas 26, 135, 144 e 195 (`error`, e `warn` para falta de provedor), e "Confirmar" como `accent` (único da tela).

**Acceptance criteria:**
- [x] Mostra o provedor ativo e o modelo da geração (`participants` 28); sem provedor ativo, mostra a mensagem com link para configurações e desabilita confirmar (`participants` 29).
- [x] O botão de confirmar fica desabilitado enquanto algum speaker está sem nome (`participants` 30); depois de confirmar, leva ao detalhe (`participants` 31).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/participants`.
- [x] Grep local em `NamingPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/participants/NamingPage.tsx`
- `frontend/src/features/participants/NamingPage.test.tsx`

**Estimated scope:** Small

### Task 59.2: Nomeação no Ata: linha do speaker

**Description:** `SpeakerRow` como linha com régua: botão de amostra (`primary` tocando, `secondary` parado, tamanho `icon`), tempo de fala em Geist Mono, campo de nome de 40 px, erro inline no campo e indicação de junção por nome igual com `transform` e `opacity`.

**Acceptance criteria:**
- [x] Cada speaker mostra o botão para tocar a amostra, o tempo total de fala e um campo de nome (`participants` 26); foco e teclado funcionam no botão de amostra.
- [x] Dois ou mais speakers com o mesmo nome mostram que serão juntados num só Participante (`participants` 27).
- [x] Grep local sem achado; `vitest-axe` sem violação; movimento desligado com `prefers-reduced-motion`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/participants`.
- [x] Grep local em `SpeakerRow.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 59.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/participants/SpeakerRow.tsx`
- `frontend/src/features/participants/NamingPage.test.tsx`

**Estimated scope:** Small

### Task 60.1: Divisão no Ata: página

**Description:** `SplitPage` com `PageHeader`, `Skeleton` e `Notice` no lugar da constante `ALERT` (linha 17) e dos blocos das linhas 24, 93 e 155 (`error`; `warn` para falta de provedor).

**Acceptance criteria:**
- [x] Ao abrir, chama `POST /meetings/{id}/split/refresh` antes de mostrar os cortes, e se a resposta traz `generating` leva ao detalhe (`transcript-split` 47); explica a divisão com estimativa, orçamento, provedor, modelo e link (`transcript-split` 31).
- [x] Sem provedor ativo, mostra só a mensagem que aponta para a configuração (`transcript-split` 44).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Grep local em `SplitPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Tasks 53.1, 53.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/transcript-split/SplitPage.tsx`
- `frontend/src/features/transcript-split/SplitPage.test.tsx`

**Estimated scope:** Small

### Task 60.2: Divisão no Ata: segmentos, cortes e Partes

**Description:** `SegmentList`, `CutControls` e `PartSummary` no Ata: instantes em Geist Mono tabular, corte ativo em `--signal` (já trocado na Task 52.12), "Parte cabe" em `--done`, sem classes proibidas. Virtualização e atalhos de teclado não mudam.

**Acceptance criteria:**
- [x] O usuário move, adiciona e remove cortes por mouse e por teclado, sem corte no meio de um segmento (`transcript-split` 33); cada Parte mostra intervalo, estimativa e se cabe, e "Confirmar" fica desabilitado enquanto alguma Parte não couber (`transcript-split` 34 e 35).
- [x] Com Transcrição de 2 h de fixture, só os segmentos perto da área visível ficam no DOM (NFR-07), e o INP da divisão fica até 200 ms (NFR-04; medição manual no checkpoint).
- [x] Grep local sem achado; `vitest-axe` sem violação; feedback ao mover corte só com `transform` e `opacity`.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Grep local nos três arquivos.
- [x] Gate frontend.

**Dependencies:** Task 60.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/transcript-split/SegmentList.tsx`, `frontend/src/features/transcript-split/CutControls.tsx`, `frontend/src/features/transcript-split/PartSummary.tsx`
- `frontend/src/features/transcript-split/CutControls.test.tsx`

**Estimated scope:** Medium

### Task 60.3: Divisão no Ata: "Cancelar divisão"

**Description:** `CancelSplitButton` usa `Notice variant="error"` para o erro (linha 39) e perde classes proibidas.

**Acceptance criteria:**
- [x] O botão aparece só quando a resposta do `GET` indica backlog gravado, e depois de cancelar volta à revisão do backlog (`transcript-split` 45).
- [x] O botão de cancelar usa `secondary`; no máximo um `accent` na tela da divisão ("Confirmar").
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/transcript-split`.
- [x] Grep local em `CancelSplitButton.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 60.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/features/transcript-split/CancelSplitButton.tsx`
- `frontend/src/features/transcript-split/CancelSplitButton.test.tsx`

**Estimated scope:** Small

### Checkpoint: Transcrição, nomeação e divisão

- [ ] Critérios de `diarized-transcription`, `participants` e `transcript-split` com tela seguem passando
- [ ] Transcrição de 2 h de fixture: lista virtualizada (NFR-07) e INP da divisão (NFR-04)
- [ ] Checagem de UI
- [ ] `/security-review` sobre o diff

### Task 61.1: Gravação no Ata: painel flutuante e indicador

**Description:** `RecordingPanel` segue como único `GlassPanel` do app: `fixed` no rodapé, raio `--r-10`, espaço da escala (sem `px-5`, `gap-0.5`), cronômetro em Geist Mono tabular, botão "Parar" `danger`. `RecordingIndicator` com pulso fixo em movimento reduzido. Comentário da linha 11 atualizado.

**Acceptance criteria:**
- [x] Mostra o tempo decorrido e "Parar"; ao parar, encerra tela e microfone (`screen-recording` 8 e 13).
- [x] O painel é o único elemento com vidro na tela, com fallback opaco e texto com contraste 4,5:1 (ADR-0024, "Vidro"; NFR-06).
- [x] O pulso para com `prefers-reduced-motion`; grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Grep local em `RecordingPanel.tsx` e `RecordingIndicator.tsx`.
- [x] Gate frontend.

**Dependencies:** Tasks 52.20, 53.1, 53.2

**Skills:** `minimalist-ui`, `high-end-visual-design`, `shadcn`, `frontend-ui-engineering`, `ui-animation`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/RecordingPanel.tsx`, `frontend/src/features/screen-recording/RecordingIndicator.tsx`
- `frontend/src/features/screen-recording/RecordingPanel.test.tsx`

**Estimated scope:** Small

### Task 61.2: Gravação no Ata: página, aviso de consentimento e aviso de fontes

**Description:** `RecordPage` com `PageHeader`, `Notice` no lugar das caixas das linhas 116 e 117 (`error`; `warn` para fora de contexto seguro), e `ConsentNotice` posicionado antes de "Gravar reunião", sem mexer no componente nem no texto. `SourceWarningDialog` (já em `DialogSurface`, Task 52.18) perde classes de texto proibidas.

**Acceptance criteria:**
- [x] A área oferece duas entradas, enviar arquivo e "Gravar reunião" (`screen-recording` 1); o aviso mostra exatamente `CONSENT_NOTICE_TEXT` junto de "Gravar reunião", sem confirmação nem bloqueio (`screen-recording` 26).
- [x] Fora de contexto seguro, o botão fica desabilitado com a mensagem do critério 27 (`screen-recording` 27 e 28).
- [x] Grep local sem achado em `RecordPage.tsx` e `SourceWarningDialog.tsx`; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Grep local nos dois arquivos; `git diff -- frontend/src/components/surfaces/ConsentNotice` vazio.
- [x] Gate frontend.

**Dependencies:** Task 61.1

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/RecordPage.tsx`, `frontend/src/features/screen-recording/SourceWarningDialog.tsx`
- `frontend/src/features/screen-recording/RecordPage.test.tsx`

**Estimated scope:** Small

### Task 61.3: Envio da gravação no Ata

**Description:** `SendRecordingPage` com `PageHeader`, largura `--reading`, `Notice variant="error"` no lugar da caixa das linhas 110 e 111, "Enviar" como `accent` (único da tela) e "Tentar de novo" como `secondary`.

**Acceptance criteria:**
- [x] O nome do arquivo segue `gravacao-AAAA-MM-DD-HHhMM.webm`; título vem preenchido e editável; campo opcional de participantes valida como o upload (`screen-recording` 14, 15 e 16).
- [x] O envio cria a Reunião e leva ao detalhe (`screen-recording` 17 e 20); recusa do servidor aparece com a mensagem da API (`screen-recording` 18); em falha de rede, "Tentar de novo" reenvia a mesma gravação (`screen-recording` 19).
- [x] Grep local sem achado; `vitest-axe` sem violação.

**Verification:**
- [x] `cd frontend && npm test -- --run src/features/screen-recording`.
- [x] Grep local em `SendRecordingPage.tsx`.
- [x] Gate frontend.

**Dependencies:** Task 61.2

**Skills:** `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`

**Files likely touched:**
- `frontend/src/features/screen-recording/SendRecordingPage.tsx`
- `frontend/src/features/screen-recording/SendRecordingPage.test.tsx`

**Estimated scope:** Small

### Task 61.4: Teste estático global do Ata

**Description:** O plano exige "grep e teste estático global" no "Checkpoint: Redesign Ata" mas nenhuma task o cria; esta cria. Teste varre `src/**/*.{ts,tsx,css}` (sem `*.test.*`) e falha com `rounded-xl` ou acima, `text-[`, `transition-colors`, `transition: all`, `ring-ring/50`, `outline-ring/50`, e com `GlassPanel` fora de `RecordingPanel.tsx` e de `SamplePage.tsx`.

**Acceptance criteria:**
- [x] O teste falha com cada padrão proibido e passa em `src/` inteiro, depois das Tasks 53 a 61 (ADR-0024, "Testes novos"; `02-architecture.md`, "Verificação").
- [x] No máximo 1 `GlassPanel` por tela (ADR-0024, "Vidro"; NFR-06 permite até 3).
- [x] `backdrop-filter` segue só em `glass.css` (`no-stray-backdrop.test.ts` passa).

**Verification:**
- [x] `cd frontend && npm test -- --run src/styles`.
- [x] `git grep -nE "rounded-(xl|2xl|3xl|4xl)|text-\[|transition-colors|ring-ring/50|outline-ring/50" -- frontend/src` sem achado.
- [x] Gate frontend.

**Dependencies:** Tasks 54.6, 55.3, 56.2, 57.4, 58, 59.2, 60.3, 61.3

**Skills:** `frontend-ui-engineering`

**Files likely touched:**
- `frontend/src/styles/ata-static.test.ts`

**Estimated scope:** Small

### Checkpoint: Redesign Ata

- [ ] Critérios de `screen-recording` com tela seguem passando; critério 26 com o mesmo texto do `meetings` critério 52
- [ ] No máximo 1 `GlassPanel` por tela (ADR-0024; NFR-06 permite ≤3)
- [ ] Grep e teste estático global em `src/` (Task 61.4): nenhum `rounded-xl` ou acima, `text-[`, `transition-colors`, `ring-ring/50` ou `outline-ring/50` (ADR-0024, Q1)
- [ ] Checagem de UI em todas as telas, claro e escuro; `impeccable-design-polish` no conjunto
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Task 62: Exportação Markdown como Product Backlog

**Description:** Troca só o render Markdown de `backlog_review/export.py` pelo documento de Product Backlog da Q75. JSON, geração e leitura do backlog sem mudança. Fonte única: as Epics já gravadas (`EpicOut`), sem chamar a LLM.

**Acceptance criteria:**
- [x] Markdown segue `backlog-review` 32, 33 e 36 (Q75): cabeçalho com totais, visão geral, Epics `2.N`, resumos por prioridade e por Epic, considerações derivadas dos dados.
- [x] Prioridade em pt-BR; campos vazios omitidos; quebra de linha e caracteres de Markdown tratados.
- [x] Arquivo `backlog_<slug>_<data>.md`; JSON segue `<slug>-backlog.json` (`05-api.md`).

**Verification:**
- [x] `cd backend && uv run pytest tests/backlog_review`.
- [x] Gate backend.

**Dependencies:** Task 50

**Skills:** `tdd`

**Files likely touched:**
- `backend/src/snook/modules/backlog_review/{export.py,service.py}`
- `backend/tests/backlog_review/{test_api_export_md.py,test_export_markdown.py,snapshots/}`

**Estimated scope:** Small

---

## Fechamento: auditoria final

### Task 51.3: Auditoria WCAG, polimento visual e medições de NFR

**Description:** Auditoria WCAG 2.2 AA de todas as telas, polimento visual final e medições manuais de NFR-03 a NFR-06 e NFR-08, sobre o visual Ata (ADR-0024). Roda depois da Fase 9, não antes.

**Acceptance criteria:**
- [ ] Todas as telas passam `vitest-axe`, `web-design-guidelines` e revisão manual de contraste em tema claro e escuro, de 360 a 1920 px; `prefers-reduced-motion` desliga movimento e mouse-tracking.
- [ ] Medição registrada no PR: LCP da tela de login até 2,5 s com CPU 4x mais lenta (NFR-03); CLS até 0,1 (NFR-05); no máximo 3 vidros por tela, e o Ata usa 1 (NFR-06); nenhum quadro acima de 16 ms por causa do mouse-tracking, que só existe no upload (NFR-08); INP de divisão e revisão até 200 ms (NFR-04).
- [ ] CI confirma JS inicial até 200 KB gzip e total até 500 KB gzip (NFR-01, NFR-02).

**Verification:**
- [ ] `cd frontend && npm test -- --run && npm run build && node scripts/check-bundle-size.mjs`.
- [ ] Manual: Lighthouse e DevTools Performance conforme `01-prd.md`, "NFRs de performance do frontend".

**Dependencies:** Checkpoint: Redesign Ata, Task 51.1

**Skills:** `impeccable-design-polish`, `web-design-guidelines`, `frontend-ui-engineering`, `high-end-visual-design`

**Files likely touched:**
- `frontend/src/styles/*.css`, `frontend/src/components/**`, descrição do PR de release

**Estimated scope:** Medium

### Checkpoint: Complete

- [ ] Critérios transversais 1 a 22 e NFR-01 a NFR-08 de `01-prd.md` atendidos
- [ ] NFR-03, NFR-04, NFR-05, NFR-06 e NFR-08 com medição registrada no PR de release
- [ ] Todos os SEC-01 a SEC-27 verificados
- [ ] `pip-audit` e `npm audit` sem crítico ou alto alcançável
- [ ] Checagem de UI em todas as telas
- [ ] `/security-review` sobre o diff final
- [ ] Pronto para revisão e tag em `main`
