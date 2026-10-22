# ADR-0011: Estimativa de tokens por linha e cálculo da reserva do orçamento

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q6 da rodada de decisões do planner: heurística aditiva, ajustada após o spike da Task 2. Recomendação aceita sem mudança.

## Contexto

- RT-10: nenhuma chamada recebe texto de Parte acima do orçamento.
- "Estimar tokens" mora em `llm-providers` e usa o modelo ativo.
- Quatro provedores com tokenizadores diferentes. Ollama roda modelos variados.
- `pytest` roda sem rede.
- Tela de divisão recalcula Partes a cada corte movido, em Transcrição de até 2 h.

## Opções consideradas

1. **Heurística conservadora por linha, aditiva: `tokens(linha) = ceil(len(linha) / chars_per_token[provider]) + 1`; texto = soma das linhas.**
   - Prós: offline; determinística; aditiva (cliente soma por segmento e bate com o servidor); rápida.
   - Contras: aproximada; desperdiça parte da janela.
2. **Tokenizador real por provedor (`tiktoken` para OpenAI, API `count_tokens` da Anthropic, `/api/tokenize` inexistente no Ollama).**
   - Prós: precisa onde existe.
   - Contras: Anthropic exige chamada de rede; DeepSeek e Ollama sem tokenizador local confiável; `tiktoken` baixa arquivos na primeira execução.
3. **Heurística global por caractere do texto inteiro.**
   - Prós: mais simples.
   - Contras: não é aditiva; cliente e servidor divergem.

## Decisão

Opção 1.

- `chars_per_token` padrão 3.0 para os quatro provedores (pt-BR fica perto de 4 nos tokenizadores comuns; 3.0 dá folga). Tabela em `modules/llm_providers/tokens.py`.
- "Texto da Parte" monta uma linha por segmento. Logo, `estimativa(Parte) = soma(estimativa(segmento))`. `GET /meetings/{id}/split` devolve a estimativa de cada segmento para o cliente somar.
- Orçamento da Parte = `context_window - reserva`, com:
  - `system_prompt_tokens`: estimativa do System Prompt atual (ADR-0020);
  - `participants_tokens`: estimativa da lista de Participantes da Reunião;
  - `epic_names_reserve`: 1.000 tokens fixos (nomes de Epics a partir da segunda Parte);
  - `output_reserve`: `min(16.000, floor(context_window * 0.25))`, também enviado como limite de saída da chamada;
  - margem de segurança de 5% da janela.
- Orçamento menor ou igual a zero: trata como "segmento sozinho passa do orçamento" (falha com pedido de modelo maior).
- Na geração, se os nomes de Epics reais passam da reserva fixa, a reestimativa da Parte usa o tamanho real e pode falhar (critério 32 de `backlog-generation`).

## Consequências

- Janela aproveitada em cerca de 60% a 70%. Mais Partes que o mínimo teórico.
- Trocar para tokenizador real depois muda só `tokens.py`, se mantiver a soma por linha.
- Spike da Task 2 compara a heurística com a contagem real dos provedores. O ajuste de `chars_per_token` (por provedor, se preciso) fica registrado neste ADR, sem ADR novo. Trocar a heurística por tokenizador real pede ADR novo.
