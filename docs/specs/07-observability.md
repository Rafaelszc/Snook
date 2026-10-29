# 07 - Observabilidade: Snook

> Status: planner, 2026-10-22. Correções da revisão do spec-reviewer aplicadas em 2026-10-22 (evento `operator.user_deleted`).
> Justificativa do arquivo: critério transversal 7 (nenhum segredo em log), SEC-20 (eventos de segurança), pipeline assíncrono que precisa de diagnóstico.

## Logs

- Formato: JSON, uma linha por evento, em stdout. Docker guarda (`json-file`, rotação em `08-deployment.md`).
- Nível padrão: `INFO`. Variável `LOG_LEVEL`.
- Campos fixos: `ts`, `level`, `logger`, `event`, `request_id`. Campos opcionais: `user_id`, `meeting_id`, `run_id`, `provider`, `status`, `duration_ms`, `error_type`.
- `request_id`: UUID por requisição, devolvido no header `X-Request-ID`.
- Exceções: tipo e stack trace só no log, nunca na resposta.

### Nunca em log

- Senha, hash de senha, token de sessão, cookie.
- Chave de LLM (inteira ou parcial), `SNOOK_MASTER_KEY`, `HF_TOKEN`.
- Corpo de requisição ou resposta de provedor.
- Texto da Transcrição, nomes de Participantes, conteúdo do backlog, título da Reunião.
- Email e nome de usuário. Log usa `user_id`.

### Filtro de redação

- `core/logging.py` instala filtro em todos os handlers.
- Troca por `[REDACTED]`: valores atuais de `SNOOK_MASTER_KEY` e `HF_TOKEN`; padrões `sk-[A-Za-z0-9_-]{8,}`, `sk-ant-[A-Za-z0-9_-]{8,}`, `hf_[A-Za-z0-9]{8,}`, `Bearer\s+\S+`; chaves conhecidas registradas durante a requisição (`redaction.register(secret)`).
- Filtro é rede de segurança. Código não loga segredo de propósito.
- Logs de acesso do uvicorn desligados. Middleware próprio loga método, rota (template, sem query), status e duração.
- CLI do Operador usa o mesmo `core/logging.py` (JSON em stdout, mesmo filtro).

## Eventos

| `event` | Nível | Campos |
|---|---|---|
| `auth.register` | INFO | `user_id` |
| `auth.login_succeeded` | INFO | `user_id` |
| `auth.login_failed` | WARNING | `reason` (`bad_credentials`), IP |
| `auth.logout` | INFO | `user_id` |
| `security.rate_limited` | WARNING | `limiter`, `user_id` ou IP |
| `security.access_denied` | WARNING | `user_id`, `resource`, `resource_id` (recurso de outro Usuário) |
| `security.origin_rejected` | WARNING | método, rota |
| `security.host_rejected` | WARNING | host (cortado em 100 caracteres) |
| `security.path_rejected` | ERROR | `meeting_id`, motivo (SEC-15) |
| `llm_config.saved`, `llm_config.deleted`, `llm_config.activated` | INFO | `user_id`, `provider` |
| `llm.call` | INFO | `provider`, `operation`, `status`, `duration_ms`, `error_type` |
| `meeting.created`, `meeting.deleted`, `meeting.retry` | INFO | `user_id`, `meeting_id` |
| `meeting.status_changed` | INFO | `meeting_id`, `run_id`, `from`, `to`, `failed_stage` |
| `meeting.interrupted_marked` | WARNING | quantidade por status |
| `operator.user_deleted` | INFO | `user_id`, `meetings_count` (SEC-20; sem email nem nome de usuário) |
| `operator.master_key_rotated` | INFO | `rotated`, `unreadable` (contagens; sem chave nem chave-mestra, SEC-07) |
| `pipeline.event_ignored` | INFO | evento, `meeting_id`, motivo (`status_mismatch`, `run_id_mismatch`) |
| `transcription.finished` | INFO | `meeting_id`, `duration_ms`, `audio_seconds`, `segments`, `speakers`, `device` |
| `generation.finished` | INFO | `meeting_id`, `parts`, `epics`, `user_stories`, `duration_ms` |
| `startup.completed` | INFO | revisão do schema, `pending_requeued` |

## Métricas

- Sem stack de métricas na v1 (app local, um Operador).
- Tempos de transcrição e geração saem dos eventos `transcription.finished` e `generation.finished`. Spike da Fase 0 usa esses campos.

## Alertas

- N/A na v1. Sem central de monitoramento. Operador lê `docker compose logs backend`.
- Healthcheck do compose usa `GET /api/health`.

## Verificação

- Teste `caplog` com segredos conhecidos em cada fluxo que toca segredo (critério transversal 7).
- Teste que dispara `auth.login_failed`, `security.rate_limited`, `security.access_denied` e confere campos.
- Teste em `tests/cli/` que confere `operator.user_deleted` com `user_id` e `meetings_count`, e que nenhuma linha do log traz o email nem o nome de usuário apagado.
- Teste que nenhum log contém texto de segmento da Transcrição de fixture.
