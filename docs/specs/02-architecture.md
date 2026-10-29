# 02 - Arquitetura: Snook

> Status: planner, 2026-10-22; frontend e UI atualizados em 2026-10-28 (direção "Ata", ADR-0024, Q74 de `00-overview.md`). Base: `00-overview.md` e `01-prd.md` aprovados (Q1 a Q73; mudanças já aplicadas), mais diretrizes visuais do usuário de 2026-10-22 e 2026-10-28.
> ADR-0001 a ADR-0024 com Status "Aceita". ADR-0006 a ADR-0021 e ADR-0023 aceitos pelo usuário em 2026-10-22 (rodada Q1 a Q17 do planner). ADR-0024 e rodada Q1 a Q7 do planner aceitos em 2026-10-28. Correções da revisão do spec-reviewer aplicadas em 2026-10-22 e 2026-10-28; segunda revisão de 2026-10-28 com Q1 (opção C) e Q2 (opção A) aceitas pelo usuário.
> Mudanças no spec aprovadas em 2026-10-22 (refresh da divisão, prefixo `/api`, aviso de consentimento, `delete-user`, HTTPS na rede, senha até 72 bytes, `expected_speakers` até 20, critério 30 e capacidade global, NFRs de frontend) já aplicadas em `00-overview.md` e `01-prd*` (Q1 a Q73).

## Visão geral

- Monólito modular em Python (FastAPI) com os 9 módulos do capability map ([ADR-0003](adrs/0003-monolito-modular-capability-map.md)).
- Frontend SPA em React + TypeScript + shadcn/ui, servido por nginx na mesma origem da API ([ADR-0015](adrs/0015-frontend-stack-e-testes.md), [ADR-0016](adrs/0016-implantacao-mesma-origem-e-https-na-rede.md)).
- Direção visual "Ata": papel, tinta, linha fina, um acento `--signal`; serif no conteúdo, sans nos controles, mono nos dados; vidro só no painel da gravação, mouse-tracking só na borda da área de upload ([ADR-0024](adrs/0024-direcao-visual-ata.md), que substitui em parte o [ADR-0022](adrs/0022-direcao-visual-e-design-system.md)); orçamento de performance ([ADR-0023](adrs/0023-orcamento-de-performance-do-frontend.md)).
- SQLite num volume Docker ([ADR-0001](adrs/0001-stack-base.md), [ADR-0006](adrs/0006-persistencia-sqlalchemy-unidade-de-trabalho.md)).
- Pipeline assíncrono dentro do processo do backend: barramento de avisos em memória, fila reconstruída do banco no startup, transcrição em subprocessos ([ADR-0007](adrs/0007-pipeline-assincrono-em-processo.md)).
- Whisper e Pyannote locais ([ADR-0002](adrs/0002-transcricao-local-whisper-pyannote.md), [ADR-0014](adrs/0014-tratamento-de-audio-e-modelos.md)).
- Quatro adapters de LLM em `httpx` ([ADR-0012](adrs/0012-adapters-llm-httpx.md)).
- Somente local ([ADR-0004](adrs/0004-somente-local-e-url-ollama.md)).

## Componentes de execução

```
Navegador (Chrome/Edge)
   |  https://<SNOOK_LAN_HOST> (perfil lan, Caddy)  ou  http://127.0.0.1:8080
   v
[caddy]  (só perfil lan; tls internal; HSTS; X-Forwarded-For/Proto)
   |
   v
[frontend]  nginx: build estático do React + proxy /api -> backend:8000
   |
   v
[backend]  uvicorn --workers 1, FastAPI (proxy headers só de TRUSTED_PROXY_IPS)
   |-- rotas HTTP (/api/...)
   |-- EventBus em memória
   |-- TranscriptionDispatcher -> ProcessPoolExecutor (spawn) -> faster-whisper + pyannote + ffmpeg
   |-- TranscriptPreparer (handler de avisos de transcript-split)
   |-- GenerationRunner (threads) -> httpx -> OpenAI | Anthropic | DeepSeek | Ollama
   |
   |-- volume snook-db      -> /data/snook.db, /data/snook.lock
   |-- bind ./audios        -> /audios
   |-- volume snook-models  -> /models
```

| Componente | Responsabilidade | Fronteira de confiança |
|---|---|---|
| `frontend` (nginx) | Servir SPA; proxy de `/api`; limite de corpo; headers de segurança; repasse de `X-Forwarded-*` | Recebe tráfego do navegador ou do `caddy` |
| `backend` (FastAPI) | Toda a lógica dos 9 módulos; única escrita no SQLite enquanto roda | Só alcançável pela rede interna do compose |
| CLI do Operador (`python -m snook.cli`) | `download-models`, `rotate-master-key`, `delete-user` | Só o Operador, com acesso ao host. Comandos que escrevem no banco rodam com o backend parado, garantido pela trava `/data/snook.lock` |
| Subprocessos de transcrição | Tratar áudio, diarizar, transcrever. Não tocam o banco | Recebem só caminho de arquivo e parâmetros |
| `caddy` (perfil `lan`) | TLS na rede local, HSTS | Borda da rede confiável. Detalhe em `08-deployment.md`, "Perfil lan" |
| Provedores de LLM | Gerar backlog a partir de texto | Externos (Ollama pode ser interno) |
| HuggingFace Hub | Download inicial dos modelos | Externo, só no download |

## Stack

| Camada | Escolha | ADR |
|---|---|---|
| Linguagem backend | Python 3.12 | 0001, 0017 |
| HTTP | FastAPI, uvicorn (1 worker) | 0001, 0007 |
| Validação | Pydantic v2, `pydantic-settings` | 0006 |
| Banco | SQLite (WAL, FK ligadas) | 0001, 0006 |
| ORM e migração | SQLAlchemy 2 (síncrono), Alembic | 0006 |
| Senha | `bcrypt`, custo 12 | 0021 |
| Cifra | `cryptography` AES-256-GCM | 0009 |
| HTTP de saída | `httpx` (sem redirecionamento) | 0012 |
| Áudio | ffmpeg e ffprobe do sistema | 0014 |
| Transcrição | `faster-whisper`, `large-v3-turbo` | 0014 |
| Diarização | `pyannote.audio` 3.x, `speaker-diarization-3.1` | 0014 |
| Testes backend | Pytest, `TestClient`, `respx` | 0001, 0012 |
| Frontend | Vite, React, TypeScript, shadcn/ui, Tailwind, React Router, TanStack Query | 0015 |
| Design system | tokens Ata em CSS variables com apelidos shadcn; fontes locais Source Serif 4, Geist e Geist Mono; movimento em CSS, sem biblioteca de animação | 0022, 0024 |
| Listas longas | `@tanstack/react-virtual` (aprovada com o ADR-0023) | 0023 |
| Testes frontend | Vitest, React Testing Library, MSW, `vitest-axe` | 0015, 0022 |
| Pacotes | `uv` + `uv.lock`; `npm` + `package-lock.json` | 0017 |
| Orquestração | Docker Compose, perfis `cpu`, `gpu`, `lan` | 0016, `08-deployment.md` |
| TLS na rede | Caddy, `tls internal` (perfil `lan`) | 0016, `08-deployment.md` |
| CI | GitHub Actions, `gitleaks` | 0017 |

## Estrutura de pastas

```
backend/
  pyproject.toml, uv.lock, alembic.ini, .python-version
  alembic/versions/
  src/snook/
    main.py                  -> create_app(), lifespan (sequência de subida)
    cli.py                   -> download-models, rotate-master-key, delete-user
    core/
      settings.py            -> Settings (pydantic-settings), lê .env; deriva ALLOWED_HOSTS/ORIGINS de SNOOK_LAN_HOST
      db.py                  -> engine, PRAGMAs
      uow.py                 -> UnitOfWork, publish_after_commit
      events.py              -> EventBus, tipos de aviso
      errors.py              -> AppError(code, message, http_status), handler genérico
      http_security.py       -> headers, TrustedHost, checagem de Origin, limite de corpo, proxies confiáveis
      ratelimit.py           -> SlidingWindowLimiter em memória
      logging.py             -> logs JSON, filtro de redação
      files.py               -> caminhos seguros sob /audios
      runlock.py             -> trava de arquivo /data/snook.lock (fcntl.flock; backend e CLI de escrita)
    shared/prompts/          -> backlog_system_prompt.md, backlog_response.schema.json, loader
    modules/
      auth/                  -> api.py, service.py, deps.py, models.py, repository.py, schemas.py, messages.py
      llm_providers/         -> api.py, service.py, crypto.py, tokens.py, defaults.py, adapters/{base,openai_compat,anthropic,ollama}.py
      meetings/              -> api.py, service.py, state_machine.py, media_probe.py, storage.py, startup.py
      diarized_transcription/-> api.py, service.py, dispatcher.py, pipeline.py, merge.py, engines/{audio,whisper,pyannote,fakes}.py
      participants/          -> api.py, service.py
      transcript_split/      -> api.py, service.py, budget.py, cuts.py, part_text.py
      backlog_generation/    -> service.py, runner.py, validation.py, merge.py
      backlog_review/        -> api.py, service.py, export.py
  tests/
    conftest.py              -> app com SQLite temporário, /audios temporário, fakes
    <modulo>/test_api_*.py   -> um teste por critério de aceite
    cli/                     -> testes dos comandos do Operador (delete-user, rotate-master-key)
    adapters/llm/            -> respx + fixtures gravadas
    models_real/             -> marker models_real (opcional)
    llm_real/                -> marker llm_real (opcional)
    fixtures/audio/          -> áudios curtos por formato, webm do MediaRecorder
frontend/
  package.json, package-lock.json, vite.config.ts, eslint.config.js, .nvmrc, .npmrc
  index.html                 -> meta theme-color igual a --canvas claro e escuro
  public/fonts/              -> fontes variáveis locais, latin e latin-ext: Geist, Source Serif 4, Geist Mono; LICENSE-Geist.txt, LICENSE-SourceSerif4.txt (OFL)
  src/
    app/                     -> rotas, guarda de autenticação, Layout.tsx (sessão, logout e links; compõe AppShell)
    styles/                  -> tokens.css (camada Ata, apelidos shadcn, tipo, raio, sombra, movimento), glass.css, motion.css, spotlight.css (realce só da borda da área de upload, em --signal)
    lib/api/                 -> cliente fetch, tipos, erros
    lib/ui/                  -> usePointerSpotlight, useReducedMotion, useCanHover
    components/ui/           -> componentes shadcn gerados, lendo só tokens; raio 4/6/10 e espaço 4 a 64 px
    components/forms/        -> FormField (erro de campo inline)
    components/surfaces/     -> AppShell, PageHeader, Notice, Skeleton, EmptyState, DialogSurface, ConfirmDialog, ThemeToggle, StatusBadge, GlassPanel (só painel da gravação, com fallback opaco), ConsentNotice/ (componente e messages.ts)
    components/theme-provider.tsx -> tema claro, escuro ou sistema; preferência em localStorage; sem atalho de teclado
    features/<modulo>/       -> telas e hooks por módulo
  src/**/*.test.tsx
deploy/
  nginx.conf, Caddyfile
compose.yaml, .env.example, .gitignore, README.md
.github/workflows/ci.yml
```

## Fronteiras entre módulos

- Cada módulo expõe só `service.py` (interface interna) e `api.py` (rotas). `models.py` e `repository.py` são privados.
- `import-linter` aplica o grafo abaixo. Seta = "pode importar".

```
auth <- llm_providers
auth <- meetings
meetings <- diarized_transcription
auth <- diarized_transcription            (rota da Transcrição)
meetings <- screen-recording (só frontend; chama POST /api/meetings)
diarized_transcription, llm_providers, meetings, auth <- participants
participants, llm_providers, diarized_transcription, meetings, auth <- transcript_split
transcript_split, llm_providers, participants, meetings <- backlog_generation
backlog_generation, transcript_split, participants, meetings, auth <- backlog_review
core, shared <- todos
shared não importa modules
cli e main importam qualquer módulo; nenhum módulo importa cli ou main
```

- `screen-recording` não tem backend. Usa `POST /api/meetings`.
- Nenhum módulo importa módulo à direita dele na build order.
- No frontend, `features/<modulo>` importa só `lib/`, `components/` e `styles/`. Uma feature não importa outra; navegação entre telas por rota. `ConsentNotice` mora em `components/surfaces/` para ser usado por `meetings` e `screen-recording` sem import entre features.
- `components/` não importa `features/`. Aplicado por ESLint (`no-restricted-imports` em `components/**` barra `@/features/*`, `frontend/eslint.config.js`, Task 52). Por isso `AppShell` só desenha; `app/Layout.tsx` lê a sessão (`features/auth`) e passa usuário, links e logout ao `AppShell`.

### Interfaces internas (nomes)

| Módulo | Função pública | Uso |
|---|---|---|
| `auth` | `current_user` (dependência FastAPI) | todas as rotas protegidas |
| `auth` | `find_user_by_username(uow, username)` (compara por `username_norm`, Q39), `delete_user(uow, user_id)` | `cli.py` (`delete-user`) |
| `llm_providers` | `get_active_provider(user_id) -> ActiveProvider` | `participants`, `transcript_split`, `backlog_generation` |
| `llm_providers` | `estimate_tokens(provider, model, text) -> int` | `transcript_split`, `backlog_generation` |
| `llm_providers` | `generate(user_id, provider_snapshot, system_prompt, content, json_schema, max_output_tokens) -> str` | `backlog_generation` |
| `llm_providers` | erros `NoActiveProvider`, `CredentialRejected`, `ProviderUnreachable`, `ModelNotFound`, `ContextLimitExceeded`, `ProviderRateLimited` | todos os consumidores |
| `meetings` | `create_meeting(uow, user, upload, title, expected_speakers)` | rota de upload |
| `meetings` | `get_owned_meeting(uow, user_id, meeting_id)` (404 se não é dono) | todas as rotas aninhadas |
| `meetings` | `update_status(uow, meeting_id, new_status, *, failed_stage=None, message=None, split_reason=None)` (`split_reason` só com `needs_split`) | pipeline |
| `meetings` | `mark_participants_confirmed(uow, id)`, `mark_backlog_saved(uow, id)`, `read_flags(uow, id)`, `read_status(uow, id)`, `read_owner(uow, id)` | `participants`, `backlog_generation`, `transcript_split`, `backlog_review` |
| `meetings` | `original_audio_path(meeting_id)`, `meeting_dir(meeting_id)` | `diarized_transcription` |
| `meetings` | `list_meeting_ids_for_user(uow, user_id)`, `remove_meeting_files(meeting_ids)` | `cli.py` (`delete-user`) |
| `diarized_transcription` | `list_segments`, `segment_ids`, `list_speakers`, `treated_audio_clip(meeting_id, start, end) -> bytes` | `participants`, `transcript_split` |
| `participants` | `list_participants`, `participant_for_speaker`, `confirm(uow, ...)`, `rename(uow, meeting_id, participant_id, new_name, before_absorb=None) -> RenameResult` | `transcript_split`, `backlog_generation`, `backlog_review` |
| `transcript_split` | `prepare_generation(uow, meeting_id, mode)`, `list_parts`, `save_parts`, `part_text(uow, meeting_id, first, last)`, `participants_text(uow, meeting_id)`, `owner_provider(uow, meeting_id)`, `estimate_part(uow, snapshot, meeting_id, first, last)`, `part_budget(uow, snapshot, meeting_id)`, `fits(estimate, budget)` | `backlog_generation`, `backlog_review` |
| `backlog_generation` | `BacklogRepository` (leitura e escrita de Epics, US, critérios), `next_us_number(uow, meeting_id)` | `backlog_review` |

- Interfaces que escrevem recebem `uow`. Transação entre módulos = um commit ([ADR-0006](adrs/0006-persistencia-sqlalchemy-unidade-de-trabalho.md)).
- `rename(..., before_absorb)`: na união, `participants` chama `before_absorb(absorbed_id, survivor_id)` antes de apagar o absorvido. `backlog_review` passa função que troca `requested_by` nas US. `participants` não conhece US.

## Fluxo de dados

### Upload até backlog

1. `POST /api/meetings` (multipart). nginx e middleware cortam corpo acima do limite ([ADR-0018](adrs/0018-upload-streaming-e-limite.md)).
2. `meetings` copia em blocos para `/audios/.tmp/<uuid>`, roda `ffprobe`, valida formato, trilha de áudio, duração e tamanho.
3. Válido: grava Reunião (`pending`, `run_id` novo), commit, move arquivo para `/audios/<meeting_id>/original.<ext>`, publica `MeetingCreated`.
4. `TranscriptionDispatcher` pega a `pending` mais antiga de Usuário abaixo do limite ([ADR-0010](adrs/0010-limites-de-taxa-e-concorrencia.md)). Muda para `processing` (mesmo `run_id`: mesmo trabalho).
5. Subprocesso: ffmpeg trata para `/audios/.tmp/<uuid>.flac`, Pyannote diariza, Whisper transcreve, `merge.py` junta. Devolve segmentos.
6. Processo principal: numa transação, confere Reunião existente e `run_id`; grava segmentos; muda para `transcribed`. Depois do commit, move `treated.flac` para o diretório da Reunião.
7. Usuário nomeia speakers. `participants.confirm` grava Participantes, vínculos e `participants_confirmed_at` num commit. Publica `ParticipantsConfirmed`.
8. `transcript_split.prepare_generation(mode=normal)`: lê provedor ativo, estima, decide Parte única, reaproveitamento, `needs_split` ou `failed` ([ADR-0011](adrs/0011-estimativa-de-tokens-e-orcamento.md)). Ao entrar em `generating`: novo `run_id`, publica `PartsReady`.
9. `GenerationRunner`: lê provedor ativo uma vez; para cada Parte, reestima, chama `generate`, valida JSON. Tudo certo: numa transação, apaga backlog anterior, grava novo, `backlog_saved_at`, status `done`.
10. Falha em qualquer passo: `failed` com etapa e mensagem pt-BR. Nada parcial.

### Divisão

- `GET /api/meetings/{id}/split` só lê. Tela chama `POST /api/meetings/{id}/split/refresh` ao abrir ([ADR-0019](adrs/0019-checagem-de-divisao-por-post.md)).
- Resposta traz estimativa por segmento. Cliente soma para feedback ao mover cortes. `PUT` revalida no servidor com o provedor ativo do momento.

### Retry e reinício

- `POST /api/meetings/{id}/retry`: `failed/transcription` vai para `pending` e publica `RetryRequested(transcription)`; `failed/generation` vai para `transcribed` e publica `RetryRequested(generation)`. Ambos com `run_id` novo.
- Subida do backend ([ADR-0007](adrs/0007-pipeline-assincrono-em-processo.md)):
  1. pega a trava `/data/snook.lock` (falha se outro processo a tem);
  2. backup do banco, `alembic upgrade head`;
  3. limpa `/audios/.tmp/`;
  4. "Marcar interrompidas" (Q58, Q69);
  5. reenfileira `pending` em ordem de criação;
  6. inicia dispatcher e runners;
  7. aceita requisições.

### Exclusão

- `DELETE /api/meetings/{id}`: uma transação apaga a Reunião. FKs `ON DELETE CASCADE` levam segmentos, Participantes, vínculos, Partes, Epics, US e critérios.
- Depois do commit: `core/files.py` remove `/audios/<meeting_id>/` com as checagens de caminho do `03-security.md` (SEC-15).
- Trabalho em andamento: gravação final falha por Reunião ausente; subprocesso termina e o resultado é descartado; temporário apagado.

### Exclusão de Usuário pelo Operador

- Comando: `python -m snook.cli delete-user <username>`. Critério transversal 21 e US 25 de `01-prd.md`; SEC-24.
- Roda com o backend parado. Ordem:
  1. `docker compose stop backend backend-gpu` (para o serviço do perfil ativo; o outro é ignorado);
  2. `docker compose run --rm backend python -m snook.cli delete-user <username>` (no perfil GPU, troque `backend` por `backend-gpu`);
  3. `docker compose up -d`.
- `cli.py` pega a trava `/data/snook.lock` (`fcntl.flock`, liberada quando o processo morre). Trava ocupada: o comando para com erro e não escreve nada. Garante um escritor só ([ADR-0006](adrs/0006-persistencia-sqlalchemy-unidade-de-trabalho.md)).
- Pede confirmação: o Operador digita o nome de usuário de novo, ou passa `--yes`.
- Passos:
  1. `auth.find_user_by_username`, que normaliza a entrada e compara por `username_norm` (Q39); inexistente: sai com código 1, sem escrever;
  2. `meetings.list_meeting_ids_for_user`;
  3. `auth.delete_user` num commit; FKs `ON DELETE CASCADE` levam sessões, configurações de LLM, Reuniões e derivados;
  4. depois do commit, `meetings.remove_meeting_files(ids)` com as checagens de SEC-15;
  5. log `operator.user_deleted` com `user_id` e `meetings_count`, sem email nem nome de usuário (`07-observability.md`).
- Teste em `tests/cli/`: inclusive nome com caixa diferente da cadastrada, achado pela comparação por `username_norm`.
- `rotate-master-key` segue a mesma regra de trava e backend parado.

## Avisos

| Aviso | Emissor | Consumidor | Status exigido no consumo |
|---|---|---|---|
| `MeetingCreated` | `meetings` (upload e reenfileiramento do startup) | `diarized_transcription` | `pending` |
| `RetryRequested(transcription)` | `meetings` | `diarized_transcription` | `pending` |
| `RetryRequested(generation)` | `meetings` | `transcript_split` | `transcribed` |
| `ParticipantsConfirmed` | `participants` | `transcript_split` | `transcribed` |
| `PartsReady` | `transcript_split` | `backlog_generation` | `generating` |

- Todos levam `meeting_id` e `run_id`. Consumidor ignora se status ou `run_id` não batem.
- Publicação só depois do commit (`uow.publish_after_commit`).
- "Nova tentativa" de `transcription` descarta segmentos e áudio tratado anteriores antes de reprocessar.

## Frontend e UI

Fonte da direção: diretriz do usuário de 2026-10-22 ([ADR-0022](adrs/0022-direcao-visual-e-design-system.md), Aceita), substituída em parte pela diretriz de 2026-10-28 ([ADR-0024](adrs/0024-direcao-visual-ata.md), Aceita, direção "Ata", Q74 de `00-overview.md`). Orçamento: [ADR-0023](adrs/0023-orcamento-de-performance-do-frontend.md) (Aceita). Implementação na Fase 9 de `tasks/plan.md`.

### Direção visual

- "Ata": papel, tinta, linha fina, um acento `--signal` (petróleo). Hierarquia por régua e espaço; card só no que flutua.
- Exceção: card de login e cadastro, opaco (`--surface`), com régua, sem sombra.
- Três vozes: serif (Source Serif 4) no conteúdo, sans (Geist) nos controles, mono (Geist Mono) tabular em `US-id`, instantes, tokens e cronômetro.
- Escala fixa 12 a 40 px, no máximo três tamanhos por tela.
- Espaço 4 a 64 px e raio 4/6/10 em todo o código, inclusive `components/ui/*`.
- Animações suaves e curtas (120 a 240 ms), só `transform` e `opacity`. Sem `transition-colors` nem `transition: all`.
- Vidro só no painel flutuante da gravação. Mouse-tracking só na borda da área de upload.
- Sem gradiente, exceto o realce radial da borda da área de upload.
- Tokens, apelidos shadcn, estados, contraste, raios, larguras e componentes base: ADR-0024.
- Migração (ADR-0024, Q1): Task 52 troca em todo o `src/` as classes de cor de token removido e os usos do `Button`; raio, tamanho arbitrário, `transition-colors` e anel com alfa saem na task de cada tela.

### Mapa de superfícies

| Tela (módulo) | Vidro | Movimento | Mouse-tracking |
|---|---|---|---|
| Login e cadastro (`auth`) | não (card opaco, régua, sem sombra) | entrada do card por opacidade | não |
| Layout autenticado (`AppShell`) | não (barra opaca) | não | não |
| Configurações de LLM (`llm-providers`) | não (diálogo opaco) | feedback de "Testar conexão" | não |
| Upload, lista e detalhe (`meetings`) | não (diálogos opacos) | troca de status na lista | sim, realce só da borda da área de upload; texto e fundo sem mudança |
| Gravação (`screen-recording`) | painel flutuante da gravação (`fixed` no rodapé, sobre o conteúdo rolável) | pulso do indicador (fixo com movimento reduzido) | não |
| Transcrição (`diarized-transcription`) | não | não | não |
| Nomeação (`participants`) | não | indicação de junção por nome igual | não |
| Divisão (`transcript-split`) | não | feedback ao mover corte | não |
| Revisão (`backlog-review`) | não (diálogos opacos) | abrir e fechar Epic | não |

- Diálogos de todas as telas usam `DialogSurface` (opaco, sobre `--scrim`). Lista completa no ADR-0024, "Vidro".
- Toast não existe no código. Se vier, nasce opaco.
- Skeleton com respiração de opacidade conta como indicador de progresso; parado com movimento reduzido.

### Restrições obrigatórias

- **Movimento reduzido:** `prefers-reduced-motion: reduce` desliga transições de movimento, pulso, respiração do skeleton e mouse-tracking. Hook `useReducedMotion` e media query em CSS; os dois precisam concordar.
- **Contraste:** pares de token do ADR-0024 testados em `tokens.test.ts`, claro e escuro, contra `--canvas` e `--surface`. Texto 4,5:1; componente de UI 3:1.
- **Foco:** anel opaco de 2 px em `--ring` (= `--signal`), sem alfa.
- **Contraste sobre vidro:** só no painel da gravação. Texto sobre vidro mantém 4,5:1 contra o pior fundo possível. `backdrop-filter` tem fallback opaco em `@supports not`, `prefers-reduced-transparency: reduce` e `forced-colors: active`. Componente único `GlassPanel` aplica a regra; uso de `backdrop-filter` fora dele é proibido (`no-stray-backdrop.test.ts`).
- **Mouse-tracking:** liga só com `(hover: hover) and (pointer: fine)` e sem movimento reduzido. Em toque ou com movimento reduzido, nenhum listener de `pointermove` é registrado. Atualização por `requestAnimationFrame` em CSS variables (`--pointer-x`, `--pointer-y`), sem re-render React. Realce recortado para a borda por `mask-composite`; não muda fundo nem contraste do texto (ADR-0024, "Mouse-tracking").
- **Tema:** controle visível (claro, escuro, sistema) no `AppShell` e no auth (`ThemeToggle`). Sem atalho de uma tecla (WCAG 2.1.4). `theme-color` do `index.html` igual a `--canvas` de cada tema.
- **Performance:** custo do visual dentro do orçamento do ADR-0023 (NFR-01 a NFR-08 do `01-prd.md`). Preload só da Geist latin e da Source Serif 4 latin; fallback com métricas ajustadas.
- **Acessibilidade:** WCAG 2.2 AA. Foco visível, teclado em tudo (inclusive cortes da divisão), `aria-live` nas mudanças de status, alvos de 24 px.
- **Responsivo:** de 360 px a 1920 px; desktop primeiro.
- **Segurança:** fontes e ícones locais (CSP `default-src 'self'`, SEC-13). Preferência de tema em `localStorage` é permitida; sessão nunca.
- **Alertas:** `Notice` só para alerta de bloco ou de página (`info`, `warn`, `error`, `consent`). Erro de campo fica inline no `FormField`.
- **Privacidade:** componente `ConsentNotice` mostra o aviso de consentimento na tela de upload e na área de gravação. Texto exato fixado em `01-prd/meetings.md`, critério 52, e citado por `01-prd/screen-recording.md`, critério 26. O texto mora numa constante única (`CONSENT_NOTICE_TEXT` em `components/surfaces/ConsentNotice/messages.ts`); as duas telas usam o mesmo componente. `ConsentNotice` renderiza `Notice variant="consent"` sem mudar o texto (troca na Task 52; Tasks 57 e 61 só posicionam).
- **Contexto seguro:** a área de gravação checa `window.isSecureContext` antes de habilitar "Gravar reunião" (`screen-recording` critérios 27 e 28).

### Verificação

- Vitest + `vitest-axe` em cada tela: nenhuma violação de contraste ou de rótulo.
- `tokens.test.ts`: pares das tabelas de contraste do ADR-0024, nos dois temas, inclusive `--ring` contra `--canvas` e `--surface` e fundos `-soft` do `Notice`.
- Teste de `usePointerSpotlight`: sem listener com `pointer: coarse` e com movimento reduzido.
- Teste de `GlassPanel`: classe opaca quando `CSS.supports("backdrop-filter", "blur(1px)")` é falso.
- Teste de diálogos: nenhum diálogo renderiza `GlassPanel`; todos usam `DialogSurface`.
- Teste de tema: `ThemeToggle` operável por teclado; `theme-provider` sem listener de `keydown`.
- Grep do checkpoint da Task 52: em `components/`, `styles/`, `index.css` e `app/SamplePage.tsx`, nenhum `highlight|status-(pending|processing|done|failed)|sidebar|chart-` (variável e classe).
- Teste estático global, a partir do "Checkpoint: Redesign Ata" (`tasks/plan.md`): sem `rounded-xl` ou acima, `transition-colors`, `ring-ring/50`, `outline-ring/50` ou `text-[` em `src/`. Antes desse checkpoint, telas não migradas ainda têm essas classes (ADR-0024, Q1).
- Lint: `npm run lint` acusa import de `@/features/*` em `components/**`.
- Teste de `ConsentNotice`: texto igual a `CONSENT_NOTICE_TEXT`, visível no upload e antes da gravação.
- Teste de contexto seguro: com `isSecureContext` falso, botão de gravar desabilitado e mensagem do critério 27.
- Checkpoint de cada tela: revisão com `web-design-guidelines` e checagem manual de contraste em tema claro e escuro.

## Preocupações transversais

- **Erros:** `AppError(code, message_pt, http_status)`. Corpo: `{"error": {"code": "...", "message": "...", "fields": {...}}}`. Exceção não tratada: HTTP 500 com mensagem genérica; detalhe só no log. Contrato em `05-api.md`.
- **Segurança HTTP:** `TrustedHostMiddleware`, checagem de `Origin` em métodos que mudam estado, headers de segurança, limite de corpo. `03-security.md`.
- **Proxies:** backend lê `X-Forwarded-For` e `X-Forwarded-Proto` só de `TRUSTED_PROXY_IPS` (IPs fixos de nginx e Caddy). IP do cliente: primeiro endereço não confiável da direita para a esquerda. Esquema `https` vindo do Caddy liga `Secure` no cookie (`SESSION_COOKIE_SECURE=auto`). Regra em `08-deployment.md`, "Perfil lan".
- **Logs:** JSON em stdout, filtro de redação. `07-observability.md`.
- **Configuração:** `core/settings.py`, só variáveis de ambiente. Lista em `08-deployment.md`.
- **Tempo:** relógio injetável (`core/clock.py`) para limitador, sessões e testes.

## Respostas às decisões pendentes do spec

Todas resolvidas. ADRs citados com Status "Aceita" em 2026-10-22.

| Pendência (`00-overview.md`) | Onde |
|---|---|
| Tratamentos de áudio e onde guardar o tratado | ADR-0014 |
| Algoritmo de cifra e nome da variável | ADR-0009 |
| Chaves se a chave-mestra mudar ou se perder | ADR-0009 |
| Estimativa de tokens e reserva | ADR-0011 |
| Onde mora o System Prompt | ADR-0020 |
| Padrões de modelo e janela | ADR-0013 |
| Mecanismo dos avisos; `pending` após reinício | ADR-0007 (reenfileirar no startup) |
| Aviso velho após "Marcar interrompidas" | ADR-0007 (fila não durável + `run_id`) |
| Transação entre módulos | ADR-0006 (unidade de trabalho) |
| Valores dos limites | ADR-0010 |
| Nível ASVS | `03-security.md` (L2) |
| Comandos, pastas, estilo, CI | ADR-0017 e esta seção |
| Framework de teste do frontend | ADR-0015 |
| Worker e concorrência | ADR-0007, ADR-0010 |
| Biblioteca Whisper, modelo, Pyannote | ADR-0014 |
| Sessão | ADR-0008 |
| Exclusão de conta pelo Operador (`delete-user`) | Esta seção, "Exclusão de Usuário pelo Operador"; ADR-0006 (trava) |
| HTTPS na rede confiável | ADR-0016; `08-deployment.md`, "Perfil lan" |
| Metas de tempo de processamento | Sem meta na v1. Spike da Task 1 mede e registra no README. Ver "Questões em aberto" |
| Tamanho máximo de campos, polling, nome do export | `05-api.md` |

## Questões em aberto

1. Meta de tempo de processamento: sem meta na v1; spike da Task 1 mede. Usuário pode fixar meta depois. Não bloqueia o plano.
