# 06 - Integrações externas: Snook

> Status: rascunho do planner, 2026-10-22.
> Justificativa do arquivo: quatro provedores de LLM com erros tipados e regras de rede (Q60, Q63); HuggingFace para modelos.
> Endpoints e headers abaixo vêm do conhecimento do planner. Tarefa de cada adapter confere na documentação oficial antes de gravar as fixtures.

## Cliente comum ([ADR-0012](adrs/0012-adapters-llm-httpx.md))

- `httpx.Client(follow_redirects=False)`.
- Timeout: conexão 10 s; escrita 30 s; leitura `LLM_READ_TIMEOUT` (padrão 300 s) na geração, 20 s no teste de conexão.
- Corpo de resposta lido em streaming e cortado em 5 MB.
- Sem retry automático.
- Header de autenticação nunca logado. Exceções do `httpx` viram erro tipado sem o objeto `request`.
- Logs da integração: provedor, operação, status HTTP, duração, tipo de erro. Sem corpo.

## Provedores

| Provedor | URL base | Autenticação | Geração | Teste de conexão |
|---|---|---|---|---|
| `openai` | `https://api.openai.com/v1` (fixa) | `Authorization: Bearer <key>` | `POST /chat/completions`, `response_format: {"type":"json_object"}`, `max_completion_tokens` | `GET /models/{model}` |
| `deepseek` | `https://api.deepseek.com` (fixa) | `Authorization: Bearer <key>` | `POST /chat/completions`, `response_format: {"type":"json_object"}`, `max_tokens` | `GET /models`, modelo na lista |
| `anthropic` | `https://api.anthropic.com/v1` (fixa) | `x-api-key: <key>`, `anthropic-version: 2023-06-01` | `POST /messages`, ferramenta `submit_backlog` com `input_schema`, `tool_choice: {"type":"tool","name":"submit_backlog"}`, `max_tokens` | `GET /models/{model}` |
| `ollama` | URL do Usuário | nenhuma | `POST {base}/api/chat`, `stream:false`, `format:<schema>`, `options.num_ctx=<context_window>`, `options.num_predict=<max_output>` | `POST {base}/api/show` `{model}` |

- `openai` e `deepseek` compartilham `adapters/openai_compat.py`, com URL e nomes de campo por provedor.
- URLs fixas não vêm do Usuário. Só o Ollama aceita URL.

### Validação da URL do Ollama (Q60, Q63)

1. `urllib.parse.urlsplit`; esquema em `http`, `https`; senão 422 `invalid_url_scheme`.
2. `username` ou `password` presentes: 422 `url_with_credentials`.
3. Host não vazio. Qualquer host aceito, inclusive privado.
4. URL guardada sem barra final. Caminho `/api/...` montado pelo adapter.

## Mapa de erros

| Situação | Tipo | Mensagem pt-BR (geração) |
|---|---|---|
| HTTP 401 ou 403 | `CredentialRejected` | "O provedor recusou a chave. Confira em Configurações." |
| HTTP 404 no modelo; erro de modelo desconhecido | `ModelNotFound` | "Modelo não encontrado no provedor." |
| HTTP 400 com código de contexto (`context_length_exceeded` na OpenAI e DeepSeek; texto "prompt is too long" na Anthropic; erro de contexto do Ollama) | `ContextLimitExceeded` | "A parte passou do limite de contexto do modelo." |
| HTTP 429 | `ProviderRateLimited` | "Limite de uso do provedor atingido. Tente mais tarde." |
| HTTP 3xx | `ProviderUnreachable` | "Provedor inacessível (redirecionamento recusado)." |
| Timeout, DNS, conexão recusada, TLS, 5xx, corpo acima de 5 MB | `ProviderUnreachable` | "Provedor inacessível." |
| Sem provedor ativo | `NoActiveProvider` | "Nenhum provedor ativo. Configure em Configurações." |
| Chave ilegível (`key_status = unreadable`) | `CredentialRejected` | "Chave ilegível. Informe a chave de novo em Configurações." |

- Mensagens ficam em `modules/llm_providers/messages.py`.
- Corpo de erro do provedor nunca vai para a mensagem nem para o log.

## Testes dos adapters

- `respx` intercepta `httpx`. Fixtures em `backend/tests/fixtures/llm/<provider>/<caso>.json` (status, headers sem auth, corpo).
- Casos por provedor: sucesso, 401, 404 de modelo, contexto excedido, 429, timeout, 302 (todos), corpo de 6 MB.
- Gravação das fixtures: manual, a partir da documentação oficial e de uma chamada real feita pelo desenvolvedor com chave própria. Chave e IDs de conta removidos antes do commit.
- Suíte `llm_real` (opcional): chaves em `SNOOK_TEST_OPENAI_KEY`, `SNOOK_TEST_ANTHROPIC_KEY`, `SNOOK_TEST_DEEPSEEK_KEY`, `SNOOK_TEST_OLLAMA_URL`.

## HuggingFace Hub

- Uso: download dos modelos do Pyannote e do faster-whisper ([ADR-0014](adrs/0014-tratamento-de-audio-e-modelos.md)).
- Quando: comando `python -m snook.cli download-models` ou primeira transcrição sem cache.
- Autenticação: `HF_TOKEN` do `.env`. Token nunca logado.
- Revisão fixa por modelo (`PYANNOTE_REVISION`, `WHISPER_REVISION`, hash de commit).
- Falha de autenticação ou termos não aceitos: Reunião vai para `failed` com mensagem que cita `HF_TOKEN` e o aceite dos termos (`diarized-transcription`, critério 15).
- Com `MODELS_OFFLINE=true`: `HF_HUB_OFFLINE=1`, nenhuma chamada de rede.

## Ferramentas locais

| Ferramenta | Uso | Falha |
|---|---|---|
| `ffprobe` | duração, trilhas, formato | arquivo vira "arquivo sem áudio" ou erro de formato |
| `ffmpeg` | tratamento, corte de amostra | Reunião vai para `failed` (`transcription`) ou amostra 500 genérico |

- Timeout do `ffprobe`: 60 s. Timeout do `ffmpeg`: `max(600, 2 * duração)` s.
