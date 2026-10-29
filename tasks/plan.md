# Implementation Plan: Snook

> Status: planner, 2026-10-22. Escopo: projeto inteiro (9 módulos). ADR-0001 a ADR-0024 com Status "Aceita"; ADR-0006 a ADR-0021 e ADR-0023 aceitos pelo usuário em 2026-10-22 (rodada Q1 a Q17 do planner). Terceira rodada: correções da revisão do spec-reviewer aplicadas (perfil `lan`, `delete-user`, faixas de critérios, aviso de consentimento). Quarta rodada: correções da segunda revisão aplicadas (checkpoint Fundação só com o que a Fase 0 verifica; cookie e limitador pelo Caddy no checkpoint `auth`; critério transversal 22 no checkpoint `screen-recording`; Windows e Fedora no checklist manual, decisão do usuário de 2026-10-22).
> Quinta rodada (planner, 2026-10-28): Fase 9 "Redesign Ata" (ADR-0024, Aceita; Q74 de `00-overview.md`; rodada Q1 a Q7 aceita pelo usuário em 2026-10-28). Task 51.3 (auditoria WCAG, polimento e medições de NFR) passa para depois da Fase 9.
> Sexta rodada (planner, 2026-10-28): segunda revisão do spec-reviewer da Fase 9; Q1 (opção C) e Q2 (opção A) aceitas pelo usuário em 2026-10-28 ("Aceito"). Task 52 troca as classes de cor de token removido em todo o `src/`; teste estático global passa ao "Checkpoint: Redesign Ata"; `ConsentNotice` sobre `Notice` na Task 52; spotlight só na borda na Task 57; Task 55 depende só da Task 52.
> Spec: `docs/specs/00-overview.md`, `docs/specs/01-prd.md`, `docs/specs/01-prd/*.md` (aprovados). Diretriz visual do usuário de 2026-10-22 (ADR-0022), substituída em parte pela de 2026-10-28 (ADR-0024).
> Tarefas só como títulos. Detalhamento (critérios, arquivos, verificação) fica com o task-breaker, em `tasks/todo.md`.

## Overview

Snook recebe gravação de reunião (upload ou gravação de tela), trata o áudio, diariza e transcreve localmente em pt-BR, deixa o usuário nomear as vozes e gera Epics e User Stories com o provedor de LLM ativo do Usuário. Reunião longa é dividida em Partes no app. Usuário revisa, edita, regenera e exporta. Plano segue a build order aprovada (Q18, Q52), com fatias verticais por módulo, spikes de risco técnico e design system base na Fase 0. Fase 9 troca a camada visual pela direção "Ata" (ADR-0024), uma fatia por tela, sem mudar lógica, rotas nem integrações.

## Documentos de arquitetura

- `docs/specs/02-architecture.md`
- `docs/specs/03-security.md`
- `docs/specs/04-data-model.md`
- `docs/specs/05-api.md`
- `docs/specs/06-integrations.md`
- `docs/specs/07-observability.md`
- `docs/specs/08-deployment.md`
- `docs/specs/adrs/0001` a `0024`

## Architecture Decisions

- Monólito modular FastAPI; fronteiras checadas por `import-linter` (ADR-0003, Aceita).
- SQLAlchemy 2 + Alembic; unidade de trabalho única para transação entre módulos; aviso publicado só depois do commit; um escritor só, garantido pela trava `/data/snook.lock` (ADR-0006, Aceita).
- Pipeline dentro do backend: barramento em memória, fila reconstruída no startup, `run_id` contra aviso velho, transcrição em subprocessos (ADR-0007, Aceita).
- Sessão por cookie opaco no servidor, CSRF por `Origin` (ADR-0008, Aceita).
- Chaves de LLM em AES-256-GCM com `SNOOK_MASTER_KEY` (ADR-0005 e ADR-0009, Aceitas).
- Limites: login 5 por identificador e 20 por IP em 15 min; teste de conexão 10 em 10 min; 1 Reunião processando por Usuário, 2 no servidor (ADR-0010, Aceita).
- Estimativa de tokens por linha, aditiva, 3 caracteres por token (ADR-0011, Aceita).
- Adapters `httpx` sem redirecionamento, saída JSON por provedor (ADR-0012, Aceita).
- Modelos padrão de custo baixo e janela por provedor, conferidos na implementação (ADR-0013, Aceita).
- faster-whisper `large-v3-turbo`, Pyannote 3.1, ffmpeg (ADR-0014, Aceita).
- Vite + TanStack Query + Vitest/RTL/MSW/`vitest-axe` (ADR-0015, Aceita).
- Direção visual minimalista, alto contraste, movimento suave com `prefers-reduced-motion`, contraste AA e fallback opaco do vidro (ADR-0022, Aceita; substituído em parte pelo ADR-0024).
- Direção "Ata" (ADR-0024, Aceita, 2026-10-28): paleta papel e tinta com um acento `--signal` (petróleo); apelidos shadcn para tokens Ata; Source Serif 4 + Geist + Geist Mono; raio 4/6/10 e espaço 4 a 64 px também em `components/ui/*`; foco opaco; vidro só no painel da gravação; mouse-tracking só na borda da área de upload; diálogos em `DialogSurface` opaco; controle de tema visível, sem atalho `d`.
- Migração Ata (ADR-0024, Q1 opção C): Task 52 troca, em todo o `src/`, só as classes de cor que dependem de token removido (tabela "Classes de cor a trocar") e os usos de variante e tamanho do `Button` (o `typecheck` exige). Raio, tamanho arbitrário, `transition-colors` e `ring-ring/50` saem na task de cada tela; teste estático global só no "Checkpoint: Redesign Ata".
- Orçamento de performance do frontend e virtualização das listas longas (ADR-0023, Aceita; item de fontes atualizado pelo ADR-0024).
- Mesma origem via nginx; bind em `127.0.0.1`; perfil `lan` com Caddy, `tls internal`, `SNOOK_LAN_HOST` e cabeçalhos `X-Forwarded-*` aceitos só de `TRUSTED_PROXY_IPS` (ADR-0016, Aceita; `08-deployment.md`, "Perfil lan"; SEC-27).
- `uv`, `npm`, GitHub Actions (ADR-0017, Aceita).
- Upload em streaming, limite de 500 MiB (ADR-0018, Aceita).
- Checagem de divisão por `POST /split/refresh` (ADR-0019, Aceita).
- System Prompt e schema em `shared/prompts/` (ADR-0020, Aceita).
- Senha com bcrypt custo 12, até 72 bytes (ADR-0021, Aceita).
- Aviso de consentimento com texto único em `ConsentNotice` (`meetings` critério 52; `screen-recording` critério 26). Na Task 52, `ConsentNotice` passa a renderizar `Notice variant="consent"` com o mesmo texto; Tasks 57 e 61 só posicionam.
- ASVS 5.0 L2 (`03-security.md`).

## Grafo de dependências

```
Fase 0 (fundação, spikes, design system, perfil lan)
   |
auth (Fase 1)
   |---------------------------.
llm-providers (2A)          meetings (2B)
   |                           |------------------------.
   |                     diarized-transcription (3A)  screen-recording (3B)
   |                           |
   '------------> participants (4)
                       |
                 transcript-split (5)
                       |
                 backlog-generation (6)
                       |
                 backlog-review (7)
                       |
                 delete-user e release (8: Tasks 50, 51.1, 51.2)
                       |
                 redesign Ata (9)
                   Task 52 (tokens, primitivos, classes de cor em todo o src)
                       |-------------------------------------------.
                   Task 53 (AppShell + lista de reuniões)     Task 55 (login e cadastro; fora do AppShell)
                       |-----------------------------------.       |
                   Task 54 (revisão do backlog)     Tasks 56 a 61  |
                       '-----------------------------------'-------'
                       |
                 auditoria final (Task 51.3) e checkpoint Complete
```

## Skills de frontend por tarefa

Skills de apoio na implementação das telas. Restrições do ADR-0022 que seguem valendo e do ADR-0024 valem em todas.

| Tarefa | Skills |
|---|---|
| Task 4 (esqueleto do frontend) | `shadcn`, `frontend-ui-engineering` |
| Task 5 (design system base) | `minimalist-ui`, `high-end-visual-design`, `design-taste-frontend`, `frontend-design`, `emil-design-eng`, `emilkowalski-motion`, `animate`, `ui-animation`, `frontend-ui-engineering`, `responsive-design`, `shadcn` |
| Tasks 9 e 10 (telas de cadastro e login; card e spotlight revistos na Task 55) | `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `emil-design-eng`, `ui-animation` |
| Task 17 (tela de configurações de LLM) | `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design` |
| Task 22 (upload, lista e detalhe, com mouse-tracking na área de upload e `ConsentNotice`) | `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design`, `emilkowalski-motion`, `animate` |
| Task 27 (tela da Transcrição, lista virtualizada) | `shadcn`, `frontend-ui-engineering`, `responsive-design` |
| Tasks 28 e 29 (gravação: painel flutuante de vidro, indicador, `ConsentNotice`) | `shadcn`, `high-end-visual-design`, `frontend-ui-engineering`, `ui-animation`, `responsive-design` |
| Task 34 (tela de nomeação) | `shadcn`, `minimalist-ui`, `frontend-ui-engineering`, `responsive-design` |
| Task 38 (tela de divisão, cortes por teclado) | `shadcn`, `design-taste-frontend`, `frontend-ui-engineering`, `ui-animation`, `responsive-design` |
| Task 49 (tela de revisão do backlog) | `shadcn`, `minimalist-ui`, `design-taste-frontend`, `frontend-ui-engineering`, `animate`, `responsive-design` |
| Task 52 (tokens e primitivos Ata) | `minimalist-ui`, `frontend-design`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`, `emil-design-eng`, `responsive-design` |
| Tasks 53 e 54 (AppShell, lista de reuniões, revisão do backlog) | `minimalist-ui`, `design-taste-frontend`, `shadcn`, `frontend-ui-engineering`, `responsive-design`, `animate` |
| Tasks 55 a 61 (demais telas no Ata) | `minimalist-ui`, `shadcn`, `frontend-ui-engineering`, `responsive-design`; Task 61 também `high-end-visual-design` e `ui-animation` (painel de vidro) |
| Checkpoints com tela | `web-design-guidelines` (revisão do diff de UI) |
| Último checkpoint de cada fase com tela | `impeccable-design-polish` |
| Task 51 (release; 51.3 depois da Fase 9) | `impeccable-design-polish`, `web-design-guidelines`, `frontend-ui-engineering` (auditoria WCAG 2.2 AA), `high-end-visual-design` |

Checagem de UI em todo checkpoint com tela (abaixo chamada "checagem de UI"):
- revisão com `web-design-guidelines`;
- Vitest + `vitest-axe` sem violação;
- contraste AA em tema claro e escuro; sobre vidro só no painel da gravação, com fallback opaco conferido;
- anel de foco opaco de 2 px, sem alfa (ADR-0024, "Foco");
- `prefers-reduced-motion` desliga movimento e mouse-tracking;
- mouse-tracking sem listener em toque (`pointer: coarse`);
- orçamento do ADR-0023 respeitado.

## Task List

### Phase 0: Fundação, risco técnico e design system

- [ ] Task 1: Spike: medir faster-whisper e Pyannote em CPU com 10 min de áudio pt-BR e registrar tempo e RAM
- [ ] Task 2: Spike: gerar backlog de Transcrição de fixture com o schema proposto nos quatro provedores
- [ ] Task 3: Esqueleto do backend com settings, banco, unidade de trabalho, barramento, erros, trava `/data/snook.lock` (`core/runlock.py`), `/api/health` e Pytest

### Checkpoint: Spikes e backend base

- [ ] `cd backend && uv run pytest` passa
- [ ] Teste da trava: segundo processo que tenta pegar `/data/snook.lock` falha; trava liberada quando o processo morre
- [ ] Resultado dos spikes registrado; ADR-0010, 0011, 0013 e 0014 ajustados se os números pedirem
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

- [ ] Task 4: Esqueleto do frontend com Vite, shadcn/ui, rotas, cliente API e Vitest com MSW e `vitest-axe`
- [ ] Task 5: Design system base: tokens, tipografia local, `GlassPanel` com fallback opaco, tokens de movimento e hooks de movimento reduzido e mouse-tracking

### Checkpoint: Frontend base

- [ ] `cd frontend && npm test -- --run` e `npm run build` passam
- [ ] Checagem de UI
- [ ] `impeccable-design-polish` sobre os tokens e a página de amostra dos componentes
- [ ] `/security-review` sobre o diff

- [ ] Task 6: Compose com perfis `cpu` e `gpu`, nginx com proxy, volumes, `.env.example` e `.gitignore`
- [ ] Task 7: Segurança HTTP base: `Host` permitido, checagem de `Origin`, headers, limite de corpo, proxies confiáveis (`TRUSTED_PROXY_IPS`) e logs JSON com redação
- [ ] Task 6b: Perfil `lan`: serviço `caddy`, `deploy/Caddyfile`, `SNOOK_LAN_HOST` em `ALLOWED_HOSTS` e `ALLOWED_ORIGINS`, repasse de `X-Forwarded-*` pelo nginx e HSTS
- [ ] Task 8: CI no GitHub Actions com lint, tipos, testes, `import-linter`, auditorias, `gitleaks` e limite de bundle

### Checkpoint: Fundação

- [ ] `docker compose up --build` sobe e `http://localhost:8080` responde (critério transversal 1)
- [ ] `docker compose stop backend backend-gpu` conferido com o serviço fora do perfil ativo; se falhar, `08-deployment.md` traz um comando por perfil (Task 6)
- [ ] Perfil `lan`: `curl --cacert snook-lan-ca.crt -sI https://<SNOOK_LAN_HOST>/` responde por HTTPS e mostra `Strict-Transport-Security` (Task 6b)
- [ ] Resolvedor de proxy da Task 7, testado direto ou por rota de teste registrada só na suíte do Pytest:
  - conexão de IP em `TRUSTED_PROXY_IPS` com `X-Forwarded-For` forjado à esquerda: IP do cliente é o primeiro IP fora de `TRUSTED_PROXY_IPS`, da direita para a esquerda;
  - `X-Forwarded-Proto` só vale vindo de IP em `TRUSTED_PROXY_IPS`;
  - conexão de IP fora de `TRUSTED_PROXY_IPS`: cabeçalhos ignorados, vale IP e esquema da conexão.
- [ ] `.gitignore` cobre `.env`, `*.db`, `audios/` (achado 1 do 03-security resolvido)
- [ ] CI verde no PR para `develop`
- [ ] SEC-04, SEC-08, SEC-13, SEC-14, SEC-19, SEC-20, SEC-21, SEC-23, SEC-25 (corpo JSON até 1 MiB) e SEC-27 (resolvedor) com testes de base
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 1: `auth`

- [ ] Task 9: Cadastro com validação e login automático (API e tela)
- [ ] Task 10: Login, logout e `/auth/me` com sessão em cookie (API, tela e redirecionamento ao login)
- [ ] Task 11: Limite de tentativas de login

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

### Phase 2A: `llm-providers` (paralela à 2B)

- [ ] Task 12: Cifra de chaves com AES-GCM, chave-mestra, rotação e chave ilegível
- [ ] Task 13: Adapter OpenAI-compatível (OpenAI e DeepSeek) com fixtures gravadas e erros tipados
- [ ] Task 14: Adapters Anthropic e Ollama, com regras da URL e sem redirecionamento

### Checkpoint: Cifra e adapters

- [ ] Critérios 29, 30, 38 a 40 de `01-prd/llm-providers.md` passam
- [ ] SEC-07, SEC-17 verificados
- [ ] `/security-review` sobre o diff

- [ ] Task 15: Rotas de configuração (listar, testar, salvar, ativar, remover) com máscara e limite de tentativas
- [ ] Task 16: Interfaces internas de provedor ativo, estimativa de tokens e geração
- [ ] Task 17: Tela de configurações de LLM

### Checkpoint: `llm-providers`

- [ ] Critérios 1 a 41 de `01-prd/llm-providers.md` cobertos
- [ ] SEC-06, SEC-26 verificados
- [ ] Checagem de UI; `impeccable-design-polish` na tela de configurações
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 2B: `meetings` (paralela à 2A)

- [ ] Task 18: Upload com validação por `ffprobe`, recepção em streaming e gravação em `/audios`
- [ ] Task 19: Listagem, detalhe, edição de título e exclusão segura em cascata
- [ ] Task 20: Máquina de estados, marcas e avisos com `run_id`

### Checkpoint: Upload e estados

- [ ] Critérios 1 a 23, 28 a 33 e 51 de `01-prd/meetings.md` passam
- [ ] SEC-02, SEC-11, SEC-15, SEC-16 verificados
- [ ] `/security-review` sobre o diff

- [ ] Task 21: Tentar novamente, marcar interrompidas e reenfileirar `pending` no startup
- [ ] Task 22: Telas de upload, lista e detalhe com polling e aviso de consentimento (`ConsentNotice` em `components/surfaces/`, texto em constante única)

### Checkpoint: `meetings`

- [ ] Critérios 1 a 46 e 49 a 52 de `01-prd/meetings.md` cobertos (34 manual); 47 e 48 ficam no checkpoint `screen-recording`
- [ ] Critério 52: `ConsentNotice` mostra o texto exato da constante junto do botão de envio
- [ ] Checagem de UI; `impeccable-design-polish` nas telas de upload, lista e detalhe
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 3A: `diarized-transcription` (paralela à 3B)

- [ ] Task 23: Dispatcher de transcrição com fakes, limite por Usuário e status até `transcribed`
- [ ] Task 24: Junção de turnos de diarização e trechos de transcrição em segmentos
- [ ] Task 25: Tratamento de áudio com ffmpeg e interface de áudio tratado

### Checkpoint: Pipeline de transcrição com fakes

- [ ] Critérios 1 a 17 e 28 a 30 de `01-prd/diarized-transcription.md` passam (18 a 20 no checkpoint `diarized-transcription`, depois da rota `GET /transcript`)
- [ ] Exclusão durante processamento não recria dados
- [ ] `/security-review` sobre o diff

- [ ] Task 26: Engines reais faster-whisper e Pyannote, cache de modelos, perfil GPU e suíte `models_real`
- [ ] Task 27: Rota e tela da Transcrição

### Checkpoint: `diarized-transcription`

- [ ] Critérios 18 a 20 de `01-prd/diarized-transcription.md` passam pela rota `GET /transcript`
- [ ] Critérios 21 a 24 na suíte `models_real`, rodada à mão; critério 22 com rede do container bloqueada; critério 24 manual com GPU NVIDIA
- [ ] Critérios 25 a 27 e 31 cobertos por Vitest
- [ ] SEC-22 verificado: download de modelo exige repositório e revisão fixos
- [ ] Checagem de UI com Transcrição de 2 h de fixture (NFR-04, NFR-07); `impeccable-design-polish` na tela da Transcrição
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 3B: `screen-recording` (paralela à 3A; depende das Tasks 18 e 22)

- [ ] Task 28: Captura de tela e microfone, checagem de contexto seguro e de fontes, e mistura em trilha única
- [ ] Task 29: Tempo decorrido, parada automática, envio com título, reenvio, aviso de navegador e `ConsentNotice` reaproveitado da Task 22
- [ ] Task 30: Fixture webm do `MediaRecorder` e leitura da duração no servidor

### Checkpoint: `screen-recording`

- [ ] Critérios de `01-prd/screen-recording.md` cobertos por Vitest; checklist manual em Chrome e Edge no Windows e no Fedora
- [ ] Critério 26: mesmo `ConsentNotice` e mesmo texto do `meetings` critério 52
- [ ] Critérios 27 e 28: botão desabilitado fora de contexto seguro (Vitest); gravação em `https://` do perfil `lan` (checklist manual)
- [ ] Critério transversal 22 (checagem manual): gravação de tela funciona num cliente da rede que confia na CA local, pelo perfil `lan` (`08-deployment.md`, "Perfil lan")
- [ ] Critérios 47 e 48 de `meetings` passam
- [ ] Checagem de UI (painel de vidro e indicador com movimento reduzido); `impeccable-design-polish` nas telas de gravação
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 4: `participants`

- [ ] Task 31: Lista de speakers e amostra de voz
- [ ] Task 32: Nomeação e confirmação com marca e aviso na mesma transação
- [ ] Task 33: Interface "Renomear Participante" com união por nome igual

### Checkpoint: `participants` API

- [ ] Critérios 1 a 24 de `01-prd/participants.md` passam
- [ ] `/security-review` sobre o diff

- [ ] Task 34: Tela de nomeação

### Checkpoint: `participants`

- [ ] Critérios 25 a 31 cobertos
- [ ] Checagem de UI; `impeccable-design-polish` na tela de nomeação
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 5: `transcript-split`

- [ ] Task 35: System Prompt e schema em `shared`, "Texto da Parte" e "Orçamento da Parte"
- [ ] Task 36: "Preparar geração" e consumo dos avisos
- [ ] Task 37: Rotas de divisão: ler, `refresh`, confirmar cortes e cancelar

### Checkpoint: `transcript-split` API

- [ ] Critérios 1 a 29, 37 a 44 e 46 de `01-prd/transcript-split.md` passam
- [ ] `/security-review` sobre o diff

- [ ] Task 38: Tela de divisão

### Checkpoint: `transcript-split`

- [ ] Critérios 30 a 36, 45 e 47 cobertos
- [ ] Checagem de UI com Transcrição de 2 h (cortes por teclado; NFR-04, NFR-07); `impeccable-design-polish` na tela de divisão
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 6: `backlog-generation`

- [ ] Task 39: Validação da resposta da LLM contra o schema
- [ ] Task 40: Geração sequencial com junção de Epics, numeração e gravação tudo ou nada
- [ ] Task 41: Erros tipados, reestimativa por Parte e idempotência do aviso

### Checkpoint: Geração

- [ ] Critérios 1 a 29 e 32 a 34 de `01-prd/backlog-generation.md` passam
- [ ] SEC-18 verificado
- [ ] `/security-review` sobre o diff

- [ ] Task 42: Snapshot do System Prompt e suíte `llm_real` por provedor

### Checkpoint: `backlog-generation`

- [ ] Critérios 30 e 31 passam; suíte `llm_real` passa à mão nos quatro provedores (critério transversal 3)
- [ ] Fluxo completo upload até `done` funciona com Docker
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 7: `backlog-review`

- [ ] Task 43: Leitura do backlog com regras por status
- [ ] Task 44: Edição, criação, mesclagem e exclusão de Epics
- [ ] Task 45: Edição, criação, exclusão e movimentação de US e critérios

### Checkpoint: Edição

- [ ] Critérios 1 a 22, 30, 37, 38 e 47 de `01-prd/backlog-review.md` passam
- [ ] `/security-review` sobre o diff

- [ ] Task 46: Endpoint de renomear participante com troca de solicitante
- [ ] Task 47: Regenerar com mesmos cortes ou reajuste
- [ ] Task 48: Exportação Markdown e JSON

### Checkpoint: Renomear, regenerar, exportar

- [ ] Critérios 23 a 29 e 31 a 36 passam
- [ ] Critérios 30, 37 e 38 repetidos nas rotas novas das Tasks 46 a 48 (regra de status, 404 com `id` alheio, 401 sem sessão)
- [ ] SEC-12 verificado no export
- [ ] `/security-review` sobre o diff

- [ ] Task 49: Tela de revisão do backlog

### Checkpoint: `backlog-review`

- [ ] Critérios 39 a 46 e 48 cobertos
- [ ] Checagem de UI; `impeccable-design-polish` na tela de revisão
- [ ] INP com backlog de fixture 30 Epics e 200 US (NFR-04)
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Phase 8: Exclusão de Usuário e release

- [ ] Task 50: CLI `delete-user` com trava, confirmação, cascata e remoção de `/audios`, testada em `tests/cli/`

### Checkpoint: `delete-user`

- [ ] Critério transversal 21 e US 25 de `01-prd.md` cobertos em `tests/cli/`
- [ ] SEC-24: apaga linhas de todas as tabelas e diretórios do Usuário; dados de outro Usuário não mudam; nome inexistente sai com código 1 sem escrever
- [ ] SEC-24: confirmação errada (nome digitado diferente do argumento) sai sem apagar nada (`08-deployment.md`, "CLI de escrita")
- [ ] Abuse case "delete-user com backend no ar": com a trava ocupada, o comando para com erro e nada é apagado
- [ ] `find_user_by_username` compara por `username_norm` (Q39); teste com caixa diferente
- [ ] Evento `operator.user_deleted` com `user_id` e `meetings_count`, sem email nem nome de usuário (SEC-20)
- [ ] `/security-review` sobre o diff

- [ ] Task 51: Checklist de release: README (51.1), verificação do 03-security, auditorias e suítes opcionais (51.2). Auditoria WCAG, polimento visual e medições de NFR (51.3) rodam depois da Fase 9, sobre o visual final

### Checkpoint: Release sem auditoria visual

- [ ] README, verificação do 03-security, auditorias e suítes opcionais registrados no PR
- [ ] `/security-review` sobre o diff

### Phase 9: Redesign Ata (ADR-0024)

Escopo: só camada visual. Lógica, rotas, contratos de API, textos ao usuário e `CONSENT_NOTICE_TEXT` não mudam. Cada task é uma task mãe com PR próprio.

- [ ] Task 52: Tokens e primitivos Ata: camada de cor e apelidos, troca das classes de cor de token removido em todo o `src/` (Q1), fontes com preload e fallback, raio e espaço em `components/ui/*`, foco opaco, `Button` novo com usos de variante e tamanho atualizados em todo o `src/`, `DialogSurface` em todos os diálogos, `Notice`, `ConsentNotice` sobre `Notice variant="consent"`, `Skeleton`, `EmptyState`, `PageHeader`, `ThemeToggle`, remoção do atalho `d`, `theme-color` do `index.html` e regra ESLint `components/**` sem `@/features/*`

### Checkpoint: Tokens e primitivos

- [ ] `cd frontend && npm test -- --run`, `npm run lint`, `npm run typecheck` e `npm run build` passam
- [ ] `tokens.test.ts` com todos os pares de contraste do ADR-0024, nos dois temas; pares marcados "a conferir" confirmados ou fundos `-soft` ajustados
- [ ] Nenhum diálogo renderiza `GlassPanel`; `no-stray-backdrop.test.ts` passa
- [ ] Grep em `components/`, `styles/`, `index.css` e `app/SamplePage.tsx` sem resultado para `highlight|status-(pending|processing|done|failed)|sidebar|chart-` (forma de variável e forma de classe)
- [ ] Usos em `features/` da tabela "Classes de cor a trocar" do ADR-0024 trocados, conferidos linha a linha no PR
- [ ] `ConsentNotice` renderiza `Notice variant="consent"`; teste de igualdade com `CONSENT_NOTICE_TEXT` passa
- [ ] `npm run lint` falha com import de `@/features/*` dentro de `components/**` (conferido com arquivo de teste temporário, fora do commit)
- [ ] `index.html`: `theme-color` claro e escuro iguais a `--canvas` de cada tema
- [ ] `theme-provider` sem listener de `keydown`; `ThemeToggle` operável por teclado
- [ ] Fontes: quatro `.woff2` e licenças em `public/fonts/`; CSP `default-src 'self'` sem mudança; LCP do login (NFR-03) e CLS (NFR-05) medidos; contingência do `h1` aplicada se LCP passar de 2,5 s
- [ ] JS inicial e total dentro de NFR-01 e NFR-02
- [ ] Checagem de UI na página de amostra
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

- [ ] Task 53: AppShell e lista de reuniões no Ata (`app/Layout.tsx` compõe `AppShell`; `StatusBadge` sem pílula)
- [ ] Task 54: Revisão do backlog no Ata (US como linha com régua, Epic com régua forte)

### Checkpoint: Shell, lista e backlog

- [ ] Testes de `meetings`, `backlog-review` e `app/` passam sem mudar critério de aceite
- [ ] Nav com `aria-current="page"` no item ativo; largura `--shell`
- [ ] INP com backlog de fixture 30 Epics e 200 US (NFR-04)
- [ ] Checagem de UI; `impeccable-design-polish` no shell, na lista e na revisão
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

- [ ] Task 55: Login e cadastro no Ata (card opaco sem sombra, sem spotlight, `ThemeToggle`)
- [ ] Task 56: Configurações de LLM no Ata
- [ ] Task 57: Upload e detalhe da Reunião no Ata (spotlight só na borda, em `--signal`; `ConsentNotice` posicionado junto do envio)

### Checkpoint: Auth, configurações, upload e detalhe

- [ ] Critérios de `auth`, `llm-providers` e `meetings` com tela seguem passando
- [ ] Critério 52 de `meetings`: texto do `ConsentNotice` igual a `CONSENT_NOTICE_TEXT`
- [ ] Spotlight do upload: realce só na faixa da borda; fundo e texto do miolo sem mudança com ponteiro sobre a área
- [ ] LCP do login (NFR-03) remedido; mouse-tracking só no upload (NFR-08)
- [ ] Checagem de UI
- [ ] `/security-review` sobre o diff

- [ ] Task 58: Transcrição no Ata (fala em serif, instantes em mono, largura `--reading`)
- [ ] Task 59: Nomeação no Ata
- [ ] Task 60: Divisão no Ata

### Checkpoint: Transcrição, nomeação e divisão

- [ ] Critérios de `diarized-transcription`, `participants` e `transcript-split` com tela seguem passando
- [ ] Transcrição de 2 h de fixture: lista virtualizada (NFR-07) e INP da divisão (NFR-04)
- [ ] Checagem de UI
- [ ] `/security-review` sobre o diff

- [ ] Task 61: Gravação no Ata (único `GlassPanel` no painel `fixed` do rodapé; aviso de fontes em `DialogSurface`; `ConsentNotice` posicionado antes de gravar)

### Checkpoint: Redesign Ata

- [ ] Critérios de `screen-recording` com tela seguem passando; critério 26 com o mesmo texto do `meetings` critério 52
- [ ] No máximo 1 `GlassPanel` por tela (ADR-0024; NFR-06 permite ≤3)
- [ ] Grep e teste estático global em `src/`: nenhum `rounded-xl` ou acima, `text-[`, `transition-colors`, `ring-ring/50` ou `outline-ring/50` (ADR-0024, Q1)
- [ ] Checagem de UI em todas as telas, claro e escuro; `impeccable-design-polish` no conjunto
- [ ] `/security-review` sobre o diff
- [ ] Revisão humana antes de seguir

### Fechamento: auditoria final

- [ ] Task 51.3: Auditoria WCAG 2.2 AA de todas as telas, polimento visual e medições de NFR-03 a NFR-06 e NFR-08, sobre o visual Ata

### Checkpoint: Complete

- [ ] Critérios transversais 1 a 22 e NFR-01 a NFR-08 de `01-prd.md` atendidos
- [ ] NFR-03, NFR-04, NFR-05, NFR-06 e NFR-08 com medição registrada no PR de release
- [ ] Todos os SEC-01 a SEC-27 verificados
- [ ] `pip-audit` e `npm audit` sem crítico ou alto alcançável
- [ ] Checagem de UI em todas as telas
- [ ] `/security-review` sobre o diff final
- [ ] Pronto para revisão e tag em `main`

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Whisper + Pyannote em CPU lentos demais para 2 h de áudio, ou RAM insuficiente com 2 workers | High | Task 1 mede cedo; ajustar `WHISPER_MODEL`, `TRANSCRIPTION_WORKERS`; GPU opcional |
| Saída da LLM fora do schema com frequência (sobretudo Ollama pequeno) | High | Task 2 testa cedo; JSON mode por provedor; schema na chamada; mensagem clara em `failed` |
| Licença ou aceite de termos do Pyannote bloqueia download | Med | README; mensagem do critério 15; Task 1 valida o fluxo com `HF_TOKEN` |
| Gravação de tela no Linux só capta áudio de aba | Med | Critério 21 exige só aba; aviso na UI; checklist manual no Windows e no Fedora |
| Gravação de tela quebra em acesso pela rede sem HTTPS | Med | ADR-0016; perfil `lan` na Task 6b, na Fase 0; checagem de contexto seguro na Task 28 |
| `X-Forwarded-*` forjado burla o limite por IP ou marca HTTP como HTTPS | Med | SEC-27: backend confia só em `TRUSTED_PROXY_IPS` (IPs fixos de nginx e Caddy); nginx só repassa `X-Forwarded-Proto` vindo do Caddy; resolvedor testado no checkpoint Fundação; cookie e limitador pelo Caddy no checkpoint `auth` |
| `delete-user` com backend no ar corrompe estado ou deixa arquivo órfão | Med | Trava `/data/snook.lock` desde a Task 3; teste na Task 50 |
| Vidro reduz contraste ou pesa na GPU | Low | ADR-0024: vidro só no painel da gravação; `GlassPanel` único com fallback opaco; teste "nenhum diálogo usa `GlassPanel`" |
| Visual vira exagero (efeitos demais) | Low | ADR-0024 lista onde há vidro, gradiente, movimento e mouse-tracking; revisão `web-design-guidelines` e `impeccable-design-polish` |
| Telas de Transcrição e divisão lentas com 2 h | Med | Virtualização (ADR-0023); estimativa somada no cliente; medição de INP no checkpoint |
| Estimativa heurística erra para cima demais e divide reuniões sem necessidade | Low | Task 2 compara heurística com contagem real; ajustar `chars_per_token` |
| Nomes de modelo padrão desatualizados | Low | Tarefa da Fase 2A confere na documentação; padrão editável |
| Concorrência SQLite entre threads de geração e rotas | Med | Um processo; WAL; `busy_timeout`; transações curtas; gravação final numa transação |
| Aviso velho dispara trabalho duplicado | Med | `run_id` em todo aviso; teste por consumidor |
| Exclusão durante processamento deixa arquivo órfão | Med | Temporário em `.tmp`, movimento só depois do commit, limpeza no startup |
| Webm sem duração no cabeçalho mede errado | Med | Task 30 com fixture real do gravador; leitura pelo último pacote |
| Pesos de modelo com pickle | Low | Revisão fixa de repositório oficial (SEC-22) |
| Fontes novas estouram LCP do login (NFR-03) ou geram CLS (NFR-05) | Med | Task 52 primeiro e medida no checkpoint; preload só de Geist latin e Source Serif 4 latin; fallback com `size-adjust`; contingência: `h1` do auth em Geist |
| Fundos `-soft` do `Notice` ou `--ring` sobre `--surface` abaixo do mínimo de contraste | Med | Valores estimados no ADR-0024; `tokens.test.ts` confere na Task 52; ajuste no fundo, nunca no mínimo |
| Redesign muda comportamento sem querer (texto, rota, foco, `aria-live`) | Med | Escopo só visual; testes de critério de aceite existentes rodam sem mudança de asserção, exceto as listadas no ADR-0024 ("Testes a atualizar") |
| Troca de apelidos quebra componente shadcn que lê nome antigo | Med | Tabela "Apelidos" do ADR-0024; grep por nome removido no checkpoint da Task 52 |
| Classe Tailwind some sem erro quando o token sai (ex.: `text-highlight`, `text-status-done`, `rounded-xl`) | Med | Q1: Task 52 troca em todo o `src/` as classes de cor de token removido (tabela "Classes de cor a trocar" do ADR-0024); grep por forma de classe no checkpoint da Task 52; raio e demais classes conferidos pelo grep global do "Checkpoint: Redesign Ata"; até a task da tela, `rounded-xl` fica sem raio (só visual) |
| Renome de variante ou tamanho do `Button` quebra build em telas ainda não migradas | Med | Task 52 troca todos os usos (22 de `variant` em 17 arquivos, 3 de `size`, ADR-0024 "Componentes"); `npm run typecheck` no checkpoint da Task 52 |
| Texto do aviso de consentimento muda ao migrar para `Notice` | High | Troca para `Notice variant="consent"` só na Task 52, com teste de igualdade com `CONSENT_NOTICE_TEXT` no mesmo PR; Tasks 57 e 61 não mexem no componente, só posicionam; mudar o texto é "Ask First" |

## Parallelization Opportunities

- **Paralelo seguro:**
  - Fase 2A (`llm-providers`) e Fase 2B (`meetings`), depois da Fase 1.
  - Fase 3A (`diarized-transcription`) e Fase 3B (`screen-recording`). 3B depende só das Tasks 18 e 22.
  - Tasks 1 e 2 (spikes) entre si e com as Tasks 3, 4 e 5.
  - Task 5 (design system) em paralelo com a Task 3.
  - Telas (Tasks 17, 22, 27, 34, 38, 49) em paralelo com a tarefa seguinte do backend, depois que o contrato do `05-api.md` da rota estiver pronto.
  - Fase 9: Task 55 em paralelo com a Task 53, depois da Task 52. Tasks 54 e 56 a 61 entre si, depois das Tasks 52 e 53. Cada uma mexe só na pasta da sua feature.
- **Sequencial:**
  - Migrações Alembic: uma revisão por vez, na ordem de `04-data-model.md`.
  - Fases 4 a 7 seguem a build order.
  - Tasks 3, 5, 6, 7 e 6b antes de qualquer tarefa de módulo.
  - Task 6b depois das Tasks 6 e 7 (usa o compose e a checagem de `Host` e de proxies).
  - Task 50 depois da Fase 7: a cascata do `delete-user` cobre todas as tabelas.
  - Task 52 antes de toda tela da Fase 9. Task 53 antes das Tasks 54 e 56 a 61 (essas páginas ficam dentro do `AppShell`). Task 55 depende só da Task 52: login e cadastro ficam fora do `AppShell` e usam só o `ThemeToggle` e os primitivos.
  - Task 51.3 depois da Fase 9.
- **Coordenação:**
  - Interfaces internas (`service.py`) de `meetings` e `llm-providers` definidas antes das fases 3 a 6.
  - Contrato de erro (`05-api.md`) usado por backend e frontend desde a Task 3.
  - Tokens e primitivos da Task 52 (`DialogSurface`, `Notice`, `PageHeader`, `Skeleton`, `EmptyState`, `Button`) usados por todas as telas; mudança neles passa por revisão de UI. `GlassPanel` só no painel da gravação.
  - `ConsentNotice` e a constante do texto (Task 22) usados pela Task 29. Na Fase 9, o componente muda só na Task 52 (`Notice variant="consent"`); Tasks 57 e 61 só posicionam. Mudança no texto vale para as duas telas.

## Open Questions

1. Meta de tempo de processamento: sem meta na v1; Task 1 mede. Não bloqueia o plano.
