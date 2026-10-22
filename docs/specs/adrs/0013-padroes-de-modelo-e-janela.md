# ADR-0013: Modelos e janelas de contexto padrão por provedor

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q8 da rodada de decisões do planner: modelos de custo baixo, conferidos na implementação. Recomendação aceita sem mudança.

## Contexto

- Modelo é texto livre com padrão sugerido (Q34). Janela de contexto tem padrão editável (Q51).
- Nomes de modelo mudam rápido. Valores abaixo vêm do conhecimento do planner e precisam de conferência na documentação do provedor na tarefa que os grava.

## Opções consideradas

1. **Modelo intermediário de custo baixo por provedor, janela anunciada pelo provedor; Ollama com janela pequena.**
   - Prós: custo baixo por reunião; Ollama não estoura RAM.
   - Contras: qualidade menor que o topo de linha.
2. **Modelo topo de linha por provedor.**
   - Prós: melhor extração.
   - Contras: custo alto para o Usuário por padrão.
3. **Sem padrão (campo obrigatório).**
   - Contras: contradiz Q34 e Q51.

## Decisão

Opção 1. Valores em `modules/llm_providers/defaults.py`.

| Provedor | Modelo padrão | Janela padrão (tokens) |
|---|---|---|
| `openai` | `gpt-5-mini` | 400000 |
| `anthropic` | `claude-sonnet-4-5` | 200000 |
| `deepseek` | `deepseek-chat` | 128000 |
| `ollama` | `llama3.1:8b` | 8192 |

URL padrão sugerida do Ollama: `http://host.docker.internal:11434`.

## Consequências

- Ollama com 8192 tokens divide quase toda reunião longa. Usuário aumenta se a máquina aguenta.
- Tarefa da Fase 2A confere cada nome na documentação oficial e ajusta esta tabela se algum nome não existir mais. Ajuste de nome ou janela fica registrado neste ADR, sem ADR novo, desde que o critério "custo baixo" se mantenha.
