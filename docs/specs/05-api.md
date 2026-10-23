# 05 - API HTTP: Snook

> Status: rascunho do planner, 2026-10-22. Confirma os endpoints sugeridos nos PRDs, com prefixo `/api`.
> Justificativa do arquivo: todos os módulos com rota têm critérios por código HTTP; isolamento e auth são por endpoint.

## Convenções

- Prefixo: toda rota fica sob `/api`. Nos PRDs, `/meetings/{id}` significa `/api/meetings/{id}`.
- Formato: JSON UTF-8, exceto upload (multipart), amostra (`audio/wav`) e exportação Markdown (`text/markdown`).
- Campos em `snake_case`. Instantes em `hh:mm:ss` quando o PRD pede; segundos (`*_seconds`) nos demais.
- Autenticação: cookie `snook_session` ([ADR-0008](adrs/0008-sessao-cookie-servidor.md)).
- Métodos que mudam estado exigem `Origin` em `ALLOWED_ORIGINS` (SEC-04).
- Versionamento: sem versão no caminho na v1. Frontend e backend sobem juntos no mesmo `compose`. Quebra de contrato muda os dois no mesmo PR.
- Edição concorrente em duas abas: último a gravar vence. Sem bloqueio otimista na v1.

## Erros

```json
{
  "error": {
    "code": "meeting_not_found",
    "message": "Reunião não encontrada.",
    "fields": { "title": "Título não pode ser vazio." }
  }
}
```

- `code`: estável, em inglês, para o frontend e os testes.
- `message`: pt-BR, mostrada ao usuário.
- `fields`: só em 422 de validação.
- Recurso de outro Usuário: mesmo 404 e mesmo `code` de recurso inexistente.

| HTTP | Uso |
|---|---|
| 400 | `Host` fora da lista (`invalid_host`) |
| 401 | Sem sessão válida (`not_authenticated`); login com falha (`invalid_credentials`) |
| 403 | `Origin` inválido em método que muda estado (`invalid_origin`) |
| 404 | Inexistente ou de outro Usuário |
| 409 | Conflito de estado (status errado, unicidade no cadastro, Epic com US, último critério) |
| 413 | Corpo ou arquivo acima do limite (`payload_too_large`) |
| 422 | Validação de entrada; teste de conexão que falha no salvar |
| 429 | Limite de tentativas (`rate_limited`), com `Retry-After` |
| 500 | `internal_error`, mensagem genérica |

## Tamanhos máximos de entrada

| Campo | Máximo |
|---|---|
| Corpo JSON | 1 MiB |
| Upload | 524.288.000 bytes ([ADR-0018](adrs/0018-upload-streaming-e-limite.md)) |
| `email` | 254 caracteres |
| `username` | 3 a 30 |
| `password` | 8 caracteres a 72 bytes ([ADR-0021](adrs/0021-politica-de-senha-bcrypt.md)) |
| `title` da Reunião | 200 |
| `original_filename` gravado | 255 (cortado; só metadado) |
| `expected_speakers` | 1 a 20 |
| Chave de LLM | 500 |
| URL do Ollama | 2048 |
| `model` | 200 |
| `context_window` | 1 a 10.000.000 |
| Nome de Participante | 100 |
| Nome de Epic, nome de US | 200 |
| `as_a`, `i_want`, `so_that` | 2000 |
| `given`, `when`, `then` | 1000 |
| Cortes em `PUT /split` | 1 a 500 itens |

Saída da LLM passa pelos mesmos máximos (SEC-18). Valor acima torna a resposta inválida.

## Endpoints

Legenda de auth: **P** = pública; **S** = exige sessão; **S+D** = exige sessão e dono da Reunião (404 caso contrário).

### Sistema

| Método e rota | Auth | Resposta |
|---|---|---|
| `GET /api/health` | P | 200 `{"status":"ok"}` |

### `auth`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `POST /api/auth/register` | P | 201 `{id,email,username}` + cookie | 409 `email_taken`, `username_taken`; 422 |
| `POST /api/auth/login` `{identifier,password}` | P | 200 `{id,email,username}` + cookie | 401 `invalid_credentials`; 429 |
| `POST /api/auth/logout` | S | 204, cookie apagado | 401 |
| `GET /api/auth/me` | S | 200 `{id,email,username}` | 401 |

### `llm-providers`

`{provider}` em `openai`, `anthropic`, `deepseek`, `ollama`. Outro valor: 404.

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `GET /api/llm-configs` | S | 200 lista dos 4: `provider`, `state` (`not_configured`, `configured`, `active`), `model`, `context_window`, `key_mask` ou `base_url`, `key_status`, `default_model`, `default_context_window` | 401 |
| `POST /api/llm-configs/{provider}/test` `{api_key?,base_url?,model?,context_window?}` | S | 200 `{ok:true}` ou 200 `{ok:false,reason,message}` | 422 (`invalid_url_scheme`, `url_with_credentials`, `invalid_url`; chave ou URL ausente sem config salva); 429 |
| `POST /api/llm-configs/{provider}/models` `{api_key?,base_url?}` | S | 200 `{ok:true,models:[id]}` ou `{ok:false,reason,message}`; não grava; usa chave salva se o corpo não traz | 422 (chave ou URL ausente sem config salva); 429 (mesmo limite do teste) |
| `PUT /api/llm-configs/{provider}` | S | 200 configuração (só máscara) | 422 com `reason` do teste; 429 |
| `POST /api/llm-configs/{provider}/activate` | S | 200 | 409 `provider_not_configured` |
| `DELETE /api/llm-configs/{provider}` | S | 204 | 404 |

`reason` em `credential_rejected`, `provider_unreachable`, `model_not_found`, `rate_limited`, `context_limit`. Teste usa a chave salva quando `api_key` vem vazio e já há configuração. Campo ausente ou vazio no teste e no salvar: valor salvo, senão o padrão do ADR-0013. `message`: texto pt-BR do motivo. No `PUT`, o 422 do teste traz `code` = `reason`.

### `meetings`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `POST /api/meetings` multipart `file`, `title?`, `expected_speakers?` | S | 201 Reunião | 413; 422 (`unsupported_format`, `no_audio`, `too_long`, `empty_file`, `invalid_expected_speakers`) |
| `GET /api/meetings` | S | 200 lista (mais recente primeiro), cada item com `participants_confirmed` | |
| `GET /api/meetings/{id}` | S+D | 200 detalhe com `participants_confirmed`, `has_backlog`, `failed_stage`, `error_message`, `split_reason` | 404 |
| `PATCH /api/meetings/{id}` `{title}` | S+D | 200 | 404; 422 |
| `POST /api/meetings/{id}/retry` | S+D | 202 | 404; 409 `not_failed` |
| `DELETE /api/meetings/{id}` | S+D | 204 | 404 |

### `diarized-transcription`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `GET /api/meetings/{id}/transcript` | S+D | 200 `{segments:[{id,speaker_label,start_seconds,end_seconds,text}]}` | 404; 409 `transcript_not_ready` |

Frontend junta nomes com `GET /api/meetings/{id}/participants` (opção padrão do PRD).

### `participants`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `GET /api/meetings/{id}/speakers` | S+D | 200 `[{speaker_label,total_seconds}]` | 404; 409 |
| `GET /api/meetings/{id}/speakers/{speaker_label}/sample` | S+D | 200 `audio/wav`, até 10 s | 404 |
| `PUT /api/meetings/{id}/participants` `{names:{SPEAKER_00:"Ana",...}}` | S+D | 200 Participantes | 409 (`no_active_provider`, `invalid_status`, `already_confirmed`); 422 |
| `GET /api/meetings/{id}/participants` | S+D | 200 `[{id,name,speaker_labels}]` | 404 |

### `transcript-split`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `GET /api/meetings/{id}/split` | S+D | 200 estado da divisão (só leitura); inclui `segment_tokens` por segmento | 404; 409 |
| `POST /api/meetings/{id}/split/refresh` | S+D | 200 mesmo corpo do `GET`, depois de aplicar "passou a caber" ([ADR-0019](adrs/0019-checagem-de-divisao-por-post.md)) | 404; 409 |
| `PUT /api/meetings/{id}/split` `{cuts:[segment_id,...]}` | S+D | 202 | 404; 409; 422 (`cut_not_at_segment_end`, `cuts_not_ordered`, `part_too_large` com `part_index` e `estimated_tokens`) |
| `POST /api/meetings/{id}/split/cancel` | S+D | 200 | 404; 409 |

Corte = `id` do último segmento de uma Parte. Último segmento da Transcrição é implícito.

### `backlog-review`

| Método e rota | Auth | Sucesso | Erros |
|---|---|---|---|
| `GET /api/meetings/{id}/backlog` | S+D | 200 `{read_only, last_generation_failed, epics:[...]}` | 404; 409 `no_backlog` |
| `POST /api/meetings/{id}/epics` | S+D | 201 nova ou 200 existente (Q57) | 409 status; 422 |
| `PATCH /api/meetings/{id}/epics/{epic_id}` | S+D | 200 (com `merged_into` quando junta) | 404; 409; 422 |
| `DELETE /api/meetings/{id}/epics/{epic_id}` | S+D | 204 | 404; 409 `epic_not_empty` |
| `POST /api/meetings/{id}/epics/{epic_id}/user-stories` | S+D | 201 | 404; 409; 422 |
| `PATCH /api/meetings/{id}/user-stories/{story_id}` | S+D | 200 | 404; 409; 422 |
| `DELETE /api/meetings/{id}/user-stories/{story_id}` | S+D | 204 | 404; 409 |
| `POST /api/meetings/{id}/user-stories/{story_id}/criteria` | S+D | 201 | 404; 409; 422 |
| `PATCH /api/meetings/{id}/criteria/{criterion_id}` | S+D | 200 | 404; 409; 422 |
| `DELETE /api/meetings/{id}/criteria/{criterion_id}` | S+D | 204 | 404; 409 `last_criterion` |
| `PATCH /api/meetings/{id}/participants/{participant_id}` `{name}` | S+D | 200 `{participant, absorbed_id?}` | 404; 409; 422 |
| `POST /api/meetings/{id}/regenerate` `{mode:"same_cuts"|"adjust_cuts"}` | S+D | 202 | 404; 409; 422 |
| `GET /api/meetings/{id}/export?format=md|json` | S+D | 200 anexo | 404; 409 `no_backlog`; 422 formato |

- `epic_id`, `story_id`, `criterion_id`, `participant_id` de outra Reunião: 404 (SEC-02).
- Nome do arquivo exportado: `<slug-do-titulo>-backlog.md` ou `.json`. Slug: ASCII minúsculo, `[a-z0-9-]`, até 60 caracteres; vazio vira `reuniao`. Header `Content-Disposition: attachment; filename="..."; filename*=UTF-8''...`.

## Polling

- Frontend consulta `GET /api/meetings/{id}` e `GET /api/meetings` a cada 3 s nos status ativos ([ADR-0015](adrs/0015-frontend-stack-e-testes.md)).
- Fora dos status ativos, sem polling.
