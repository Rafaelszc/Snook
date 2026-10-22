# ADR-0012: Adapters de LLM com `httpx` puro, saída JSON e teste de conexão sem custo

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q7 da rodada de decisões do planner: `httpx` puro, testado com `respx`. Recomendação aceita sem mudança.

## Contexto

- Quatro provedores atrás de uma interface única, com erros tipados (`llm-providers`).
- Ollama não segue redirecionamento. Chave nunca em log nem em erro.
- Adapters testados contra respostas HTTP gravadas, sem rede.
- Spec deixava aberto: SDK ou HTTP, modo JSON, teste de conexão, timeouts, ferramenta de gravação. Resolvido por este ADR.

## Opções consideradas

1. **`httpx` síncrono puro nos quatro adapters, testes com `respx` e respostas gravadas em `tests/fixtures/llm/<provider>/*.json`.**
   - Prós: controle de redirecionamento, timeout e tamanho da resposta igual nos quatro; exceção nunca carrega header com chave; uma dependência.
   - Contras: mapear cada API à mão.
2. **SDKs oficiais (`openai`, `anthropic`, `ollama`).**
   - Prós: menos código; acompanham a API.
   - Contras: retries e redirecionamento implícitos; três dependências; DeepSeek via SDK OpenAI; mensagens de exceção variam.
3. **LiteLLM.**
   - Prós: um cliente para tudo.
   - Contras: dependência grande, muitos transitivos; superfície de supply chain alta.

## Decisão

Opção 1.

- Cliente comum: `httpx.Client(follow_redirects=False, timeout=httpx.Timeout(connect=10, read=LLM_READ_TIMEOUT, write=30, pool=10))`. `LLM_READ_TIMEOUT` padrão 300 s (Ollama em CPU pode pedir mais; configurável). Teste de conexão: 20 s.
- Resposta com mais de 5 MB é cortada e vira "provedor inacessível".
- Resposta 3xx vira "provedor inacessível" nos quatro adapters.
- Nenhum retry automático.
- Saída JSON:
  - OpenAI e DeepSeek: `response_format: {"type": "json_object"}`.
  - Anthropic: ferramenta única com `input_schema` do backlog e `tool_choice` forçado; adapter devolve o JSON do `input`.
  - Ollama: `format` com o JSON Schema do backlog, `stream: false`, `options.num_ctx = context_window`.
  - Validação final sempre em `backlog-generation`, com Pydantic.
- Teste de conexão sem gerar texto:
  - OpenAI: `GET /v1/models/{model}`.
  - DeepSeek: `GET /models`, confere o modelo na lista.
  - Anthropic: `GET /v1/models/{model}`.
  - Ollama: `POST /api/show` com o modelo.
- Mapa de erros: tabela em `06-integrations.md`.

## Consequências

- Mudança de API de provedor exige ajuste manual do adapter. Suíte opcional com chave real detecta.
- `num_ctx` evita o corte silencioso do Ollama.
- Dependências novas aprovadas com este ADR: `httpx` (runtime) e `respx` (teste).
