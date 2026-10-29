# ADR-0019: Checagem "passou a caber" por `POST /meetings/{id}/split/refresh`

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q14 da rodada de decisões do planner: `POST /split/refresh`, com ajuste no PRD `transcript-split`. Recomendação aceita sem mudança.

## Contexto

- `transcript-split`, critério 43: ao abrir a tela de divisão, se a Transcrição passou a caber, a Reunião segue sozinha para `generating`.
- PRD permite trocar o `GET` que muda estado por checagem disparada pelo frontend, mantendo o que o usuário vê.
- Cookie `SameSite=Lax` vai junto em navegação `GET` de outro site. `GET` que muda estado vira CSRF: site malicioso dispararia geração e gasto na conta de LLM do Usuário.

## Opções consideradas

1. **`GET /meetings/{id}/split` só lê. Frontend chama `POST /meetings/{id}/split/refresh` ao abrir a tela. O `POST` aplica a regra e devolve o mesmo corpo do `GET`.**
   - Prós: `GET` seguro; `POST` coberto pela checagem de `Origin`.
   - Contras: uma rota a mais; texto do critério 43 muda.
2. **`GET` com efeito, como no PRD.**
   - Prós: sem mudança no PRD.
   - Contras: CSRF por navegação; cache e prefetch do navegador podem disparar a geração.

## Decisão

Opção 1. Critérios 43 e 44 passam a citar `POST /meetings/{id}/split/refresh` para a regra, e `GET` para a leitura. Comportamento visto pelo usuário não muda.

## Consequências

- Ajuste no PRD `transcript-split` aprovado pelo usuário em 2026-10-22, entre as mudanças no spec. Aplicado em `01-prd/transcript-split.md` (critérios 43, 44 e 47).
