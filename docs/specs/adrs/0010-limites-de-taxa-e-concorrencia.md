# ADR-0010: Valores dos limites de tentativas e de processamento

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q5 da rodada de decisões do planner: limites abaixo, em memória e configuráveis por `.env`. Recomendação aceita sem mudança.

## Contexto

- Q60 pede limite no login, no "Testar conexão" e de Reuniões processando por Usuário. Valores com o planner.
- Login correto antes do limite zera a contagem (`auth`, critério 27).
- Limite de um Usuário não atrasa Reuniões de outro (`diarized-transcription`, critério 30).
- Backend roda num só processo (ADR-0007).

## Opções consideradas

1. **Limitador em memória (janela deslizante), chaves por identificador e por IP no login, por Usuário no teste de conexão.**
   - Prós: simples; correto com um só processo.
   - Contras: zera no reinício; quebra se um dia houver vários processos.
2. **Limitador em tabela SQLite.**
   - Prós: sobrevive a reinício; pronto para vários processos.
   - Contras: escrita a cada tentativa; mais código.
3. **Biblioteca `slowapi` com backend Redis.**
   - Prós: pronto.
   - Contras: Redis a mais.

## Decisão

Opção 1, com valores em configuração (`.env`).

| Limite | Chave | Valor padrão | Variável |
|---|---|---|---|
| Login com falha | email ou nome de usuário normalizado | 5 falhas em 15 min | `LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_SECONDS` |
| Login com falha | IP do cliente | 20 falhas em 15 min | `LOGIN_MAX_FAILURES_PER_IP` |
| "Testar conexão" e salvar | `user_id` | 10 chamadas em 10 min | `LLM_TEST_MAX_CALLS`, `LLM_TEST_WINDOW_SECONDS` |
| Reuniões em `processing` | `user_id` | 1 | `TRANSCRIPTION_MAX_PER_USER` |
| Transcrições simultâneas no servidor | global | 2 | `TRANSCRIPTION_WORKERS` |
| Gerações simultâneas no servidor | global | 2 | `GENERATION_WORKERS` |

- Login correto zera só a contagem do identificador.
- IP do cliente: lido de `X-Forwarded-For` só quando a requisição vem do proxy do frontend (`TRUSTED_PROXY_IPS`). Fora disso, IP da conexão.
- HTTP 429 traz `Retry-After`.
- Critério 30 de `diarized-transcription` só vale com `TRANSCRIPTION_WORKERS` maior que `TRANSCRIPTION_MAX_PER_USER`. Com valores que não cumprem isso, o backend sobe e grava aviso no log. A nota sobre essa relação no PRD foi aprovada pelo usuário em 2026-10-22, entre as mudanças no spec.

## Consequências

- Reinício zera contagens. Aceitável: app local, reinício é ação do operador.
- Limite por identificador permite que alguém bloqueie o login de outro por 15 min. Aceitável em rede confiável.
- Em CPU, 2 transcrições em paralelo pedem bastante RAM. Valor real medido no spike da Task 1. Operador com pouca RAM pode usar `TRANSCRIPTION_WORKERS=1`, aceitando que um Usuário espere o outro.
- Ajuste de valor padrão depois do spike fica registrado neste ADR. Troca de opção pede ADR novo.
