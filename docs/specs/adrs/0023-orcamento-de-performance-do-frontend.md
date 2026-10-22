# ADR-0023: Orçamento de performance do frontend

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q17 da rodada de decisões do planner: orçamento de performance aprovado, junto com a dependência `@tanstack/react-virtual`. Recomendação aceita sem mudança. Rota do LCP (NFR-03) fixada pela Q73 (2026-10-22); fixture do NFR-04 na tela de revisão fixada no `01-prd.md`.

## Contexto

- Diretriz do usuário (ADR-0022): custo de performance do visual precisa caber nos NFRs do `01-prd.md`.
- Fato na data da proposta: o `01-prd.md` não tinha NFR de performance de frontend. Requisitos transversais RT-01 a RT-15 e critérios 1 a 20 não citavam tempo de carga, resposta da UI nem tamanho de bundle.
- Telas densas: Transcrição de 2 h (milhares de segmentos), divisão com recálculo a cada corte, revisão do backlog.
- Vidro e blur custam GPU; mouse-tracking dispara a cada quadro.

## Opções consideradas

1. **Orçamento explícito, medido em build e em teste manual, com virtualização das listas longas.**
   - Prós: verificável; protege o visual de pesar.
   - Contras: `@tanstack/react-virtual` é dependência nova ("Ask First").
2. **Sem orçamento; ajustar se ficar lento.**
   - Prós: zero trabalho agora.
   - Contras: diretriz pede caber em NFR; sem número, não há como verificar.
3. **Orçamento sem virtualização (paginação das listas).**
   - Prós: sem dependência.
   - Contras: tela de divisão precisa ver a Transcrição contínua para mover cortes; paginação piora a tarefa.

## Decisão

Opção 1. NFRs de frontend abaixo, com o ID usado no `01-prd.md`. Inclusão no `01-prd.md` aprovada pelo usuário em 2026-10-22, entre as mudanças no spec.

Fonte única das metas e da forma de medir: `01-prd.md`, NFR-01 a NFR-08. A tabela abaixo resume aquele texto. Em divergência, vale o `01-prd.md`.

| NFR | Métrica | Meta | Como medir |
|---|---|---|---|
| NFR-01 | JS inicial (rota de login) | até 200 KB gzip | relatório do `vite build` no CI |
| NFR-02 | JS total da app | até 500 KB gzip | idem |
| NFR-03 | LCP em `localhost`, perfil de CPU 4x mais lenta no DevTools; rota medida: tela de login, a mesma do NFR-01 (Q73) | até 2,5 s | Lighthouse manual no checkpoint |
| NFR-04 | INP nas telas de divisão e de revisão do backlog | até 200 ms | DevTools Performance. Tela de divisão: Transcrição de 2 h de fixture. Tela de revisão: backlog de fixture com 30 Epics e 200 US |
| NFR-05 | CLS | até 0,1 | Lighthouse |
| NFR-06 | Elementos com `backdrop-filter` visíveis | no máximo 3 | revisão de código e de tela |
| NFR-07 | Listas da Transcrição e da divisão | virtualizadas | teste de componente com Transcrição de 2 h de fixture |
| NFR-08 | Quadros com mouse-tracking ativo | sem quadro acima de 16 ms por causa do efeito | DevTools Performance |

- Listas da Transcrição e da divisão virtualizadas com `@tanstack/react-virtual` (NFR-07).
- Rotas carregadas sob demanda (`React.lazy`) por módulo.
- Fonte variável única, subset latino, `font-display: swap`.

## Consequências

- Dependência nova `@tanstack/react-virtual` aprovada com este ADR ("Ask First" cumprido em 2026-10-22).
- Job do CI falha se o bundle passar dos limites de tamanho (NFR-01 e NFR-02).
- NFR-03 a NFR-06 e NFR-08 têm medição registrada no PR de release (`tasks/plan.md`, checkpoint "Complete").
- Seção de NFRs de frontend no `01-prd.md`: mudança aprovada no spec. Aplicado em `01-prd.md` (NFR-01 a NFR-08).
