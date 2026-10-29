# 04 - Modelo de dados: Snook

> Status: planner, 2026-10-22. ADRs citados aceitos pelo usuário em 2026-10-22. Aguarda revisão do spec-reviewer. Banco: SQLite com `foreign_keys=ON` e WAL ([ADR-0006](adrs/0006-persistencia-sqlalchemy-unidade-de-trabalho.md)).
> Justificativa do arquivo: RT-05 lista 9 entidades persistidas; contratos exigem cascata, unicidade e marcas.

## Convenções

- Chave primária: `id`. `TEXT` UUID v4 em `users`, `meetings`; `INTEGER` autoincremento nas demais.
- Datas: `TEXT` ISO 8601 UTC (`2026-10-22T13:45:00Z`), gravadas pela aplicação.
- Campo `*_norm`: valor para comparação = `strip()` + `casefold()`. Mesmo normalizador em `core/text.py` para email, nome de usuário, nome de Participante e nome de Epic.
- Toda FK para `meetings.id` usa `ON DELETE CASCADE`.
- Dono da tabela: único módulo que escreve nela. Outro módulo usa a interface do dono.
- Regras de negócio que dependem de estado (por exemplo "só Epic vazia sai") ficam na aplicação. FK com `RESTRICT` não é usada, porque a ordem da cascata no SQLite não é garantida.

## Entidades

### `users` (dono: `auth`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | TEXT UUID | PK |
| `email` | TEXT | como digitado, sem espaços nas pontas; até 254 caracteres |
| `email_norm` | TEXT | UNIQUE |
| `username` | TEXT | 3 a 30 caracteres, `[A-Za-z0-9_.-]` |
| `username_norm` | TEXT | UNIQUE |
| `password_hash` | TEXT | bcrypt (`$2b$12$...`) |
| `created_at` | TEXT | |

### `sessions` (dono: `auth`)

| Coluna | Tipo | Regra |
|---|---|---|
| `token_hash` | TEXT | PK, SHA-256 hex do token |
| `user_id` | TEXT | FK `users.id` ON DELETE CASCADE |
| `created_at`, `last_seen_at`, `expires_at` | TEXT | `expires_at` = criação + 7 dias |

Índice: `user_id`.

### `llm_configs` (dono: `llm-providers`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `user_id` | TEXT | FK `users.id` ON DELETE CASCADE |
| `provider` | TEXT | `openai`, `anthropic`, `deepseek`, `ollama` (CHECK) |
| `base_url` | TEXT NULL | só `ollama` |
| `model` | TEXT | até 200 caracteres |
| `context_window` | INTEGER | > 0 (CHECK) |
| `key_ciphertext` | BLOB NULL | AES-GCM com tag; NULL no `ollama` |
| `key_nonce` | BLOB NULL | 12 bytes |
| `key_version` | INTEGER NULL | versão da chave-mestra |
| `key_mask` | TEXT NULL | máscara pronta (`sk-...abcd` ou `...`) |
| `key_status` | TEXT | `ok` ou `unreadable` ([ADR-0009](adrs/0009-cifra-aes-gcm-chave-mestra.md)) |
| `is_active` | INTEGER | 0 ou 1 |
| `created_at`, `updated_at` | TEXT | |

- UNIQUE (`user_id`, `provider`).
- Índice único parcial: (`user_id`) WHERE `is_active = 1`. Garante no máximo um ativo (`llm-providers`, critério 20).

### `meetings` (dono: `meetings`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | TEXT UUID | PK; também nome do diretório em `/audios` |
| `user_id` | TEXT | FK `users.id` ON DELETE CASCADE |
| `title` | TEXT | 1 a 200 caracteres |
| `original_filename` | TEXT | até 255 caracteres; só metadado |
| `file_ext` | TEXT | `mp3`, `wav`, `m4a`, `ogg`, `webm`, `mp4` |
| `duration_seconds` | REAL | 0 < valor <= 7200 |
| `size_bytes` | INTEGER | <= 524288000 |
| `expected_speakers` | INTEGER NULL | 1 a 20 (CHECK). Teto de 20 aprovado pelo usuário em 2026-10-22, entre as mudanças no spec |
| `status` | TEXT | CHECK nos 7 valores |
| `failed_stage` | TEXT NULL | `transcription` ou `generation`; obrigatório quando `status = failed` (CHECK) |
| `error_message` | TEXT NULL | obrigatório quando `status = failed` (CHECK) |
| `split_reason` | TEXT NULL | `too_long` ou `adjust`; só exibição |
| `run_id` | TEXT | UUID do trabalho atual ([ADR-0007](adrs/0007-pipeline-assincrono-em-processo.md)) |
| `participants_confirmed_at` | TEXT NULL | marca; nunca apagada |
| `backlog_saved_at` | TEXT NULL | marca; nunca apagada |
| `created_at`, `updated_at` | TEXT | `created_at` = data da Reunião (Q53) |

Índices: (`user_id`, `created_at` DESC); (`status`, `created_at`).

Caminho do arquivo não é coluna: deriva de `id` e `file_ext` (`/audios/<id>/original.<ext>`). Áudio tratado: `/audios/<id>/treated.flac`.

### `transcript_segments` (dono: `diarized-transcription`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `meeting_id` | TEXT | FK CASCADE |
| `position` | INTEGER | ordem, a partir de 0; UNIQUE (`meeting_id`, `position`) |
| `speaker_label` | TEXT | `SPEAKER_00`... |
| `start_seconds`, `end_seconds` | REAL | `0 <= start < end <= duração` (checado na aplicação) |
| `text` | TEXT | não vazio após `strip()` |

Transcrição = conjunto de segmentos da Reunião. Sem tabela própria.

### `participants` e `speaker_links` (dono: `participants`)

`participants`:

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `meeting_id` | TEXT | FK CASCADE |
| `name` | TEXT | 1 a 100 caracteres, sem espaços nas pontas |
| `name_norm` | TEXT | UNIQUE (`meeting_id`, `name_norm`) |

`speaker_links`:

| Coluna | Tipo | Regra |
|---|---|---|
| `meeting_id` | TEXT | FK CASCADE |
| `speaker_label` | TEXT | PK composta (`meeting_id`, `speaker_label`) |
| `participant_id` | INTEGER | FK `participants.id` ON DELETE CASCADE |

### `transcript_parts` (dono: `transcript-split`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `meeting_id` | TEXT | FK CASCADE |
| `index` | INTEGER | a partir de 1; UNIQUE (`meeting_id`, `index`) |
| `first_segment_id`, `last_segment_id` | INTEGER | FK `transcript_segments.id` ON DELETE CASCADE |
| `start_seconds`, `end_seconds` | REAL | absolutos |
| `estimated_tokens` | INTEGER | estimativa no momento da gravação |

### `epics`, `user_stories`, `acceptance_criteria`, `backlog_counters` (dono: `backlog-generation`)

`epics`:

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `meeting_id` | TEXT | FK CASCADE |
| `name` | TEXT | 1 a 200 caracteres |
| `name_norm` | TEXT | UNIQUE (`meeting_id`, `name_norm`) (Q57) |
| `position` | INTEGER | ordem de exibição |

`user_stories`:

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `meeting_id` | TEXT | FK CASCADE |
| `epic_id` | INTEGER | FK `epics.id` ON DELETE CASCADE; aplicação recusa excluir Epic com US (Q49) |
| `us_number` | INTEGER | UNIQUE (`meeting_id`, `us_number`); exibido `US-01`, `US-100` |
| `name` | TEXT | 1 a 200 |
| `as_a`, `i_want`, `so_that` | TEXT | 1 a 2000 cada |
| `priority` | TEXT | `Low`, `Medium`, `High` (CHECK) |
| `story_points` | INTEGER | 1, 2, 3, 5, 8, 13 (CHECK) |
| `requested_by` | INTEGER NULL | FK `participants.id` ON DELETE SET NULL |
| `requested_at_seconds` | INTEGER NULL | 0 a duração |
| `position` | INTEGER | ordem dentro da Epic |

`acceptance_criteria`:

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER | PK |
| `user_story_id` | INTEGER | FK CASCADE |
| `given`, `when_`, `then_` | TEXT | 1 a 1000 cada (nomes de coluna evitam palavras reservadas) |
| `position` | INTEGER | |

`backlog_counters`:

| Coluna | Tipo | Regra |
|---|---|---|
| `meeting_id` | TEXT | PK, FK CASCADE |
| `last_us_number` | INTEGER | maior número já usado; não desce na exclusão (`backlog-review`, critério 19); volta a 0 na regeneração (Q50) |

- União de Participantes: `before_absorb` troca `requested_by` antes de apagar o absorvido. `SET NULL` só age se algo escapar dessa ordem; teste cobre que não acontece.
- Regeneração bem-sucedida: numa transação, apaga as Epics da Reunião (US e critérios em cascata), zera o contador, grava o novo backlog e grava `backlog_saved_at`.

## Diagrama de relações

```
users 1--N sessions
users 1--N llm_configs
users 1--N meetings
meetings 1--N transcript_segments
meetings 1--N participants 1--N speaker_links
meetings 1--N transcript_parts
meetings 1--N epics 1--N user_stories 1--N acceptance_criteria
meetings 1--1 backlog_counters
participants 1--N user_stories (requested_by, opcional)
```

## Retenção

| Dado | Some quando |
|---|---|
| Reunião e tudo que deriva dela (linhas e `/audios/<id>/`) | Usuário exclui a Reunião |
| Sessão | Logout, inatividade de 24 h ou 7 dias; limpeza a cada hora |
| Configuração de LLM e chave cifrada | Usuário remove a configuração |
| Usuário, com sessões, configurações de LLM, Reuniões e `/audios/<id>/` de cada Reunião | Operador roda `python -m snook.cli delete-user <username>`. Exclusão de conta pelo próprio Usuário segue fora de escopo na v1 (Q39). Comando aprovado pelo usuário em 2026-10-22, entre as mudanças no spec |
| Temporários `/audios/.tmp/` | Fim da requisição ou do trabalho; limpeza no startup |
| Backup `snook.db.bak-<rev>` | Próxima migração bem-sucedida (fica só o último) |

- `delete-user`: um commit apaga a linha de `users`. FKs `ON DELETE CASCADE` levam `sessions`, `llm_configs`, `meetings` e tudo que deriva de cada Reunião. Depois do commit, remove `/audios/<meeting_id>/` de cada Reunião listada antes do commit, com as checagens de SEC-15.
- Backup `snook.db.bak-<rev>` anterior ao comando ainda guarda o Usuário até a próxima migração. README avisa.

## Migrações

- Alembic, uma revisão por tarefa que muda schema. Nome: `NNNN_<modulo>_<mudanca>.py`.
- Startup: backup, `alembic upgrade head`. Falha na migração: backend não sobe e loga o erro.
- Só migração para frente. Rollback = restaurar o backup (`08-deployment.md`).
- Ordem prevista das revisões, por fase do plano:
  1. `users`, `sessions`
  2. `llm_configs`
  3. `meetings`
  4. `transcript_segments`
  5. `participants`, `speaker_links`
  6. `transcript_parts`
  7. `epics`, `user_stories`, `acceptance_criteria`, `backlog_counters`
