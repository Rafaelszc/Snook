# 01-prd/backlog-review - PRD do módulo `backlog-review`

> Status: completo. Decisões fechadas: Q11, Q19, Q27, Q29, Q30, Q31, Q37, Q46, Q47, Q48, Q49, Q50, Q54, Q55, Q56, Q57, Q59, Q68, Q69.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: `backlog-generation` (tabelas, "Backlog" e "Próximo número de US"), `transcript-split` ("Preparar geração"), `participants` ("Participantes", "Renomear Participante"), `meetings` (status, título, data, duração, marcas) e `auth` (rotas). Dependentes: nenhum.

## Problem Statement

- LLM entrega rascunho do backlog. Nunca sai perfeito.
- Pode vir: nome de Epic ruim, US faltando, prioridade errada, critério vago, solicitante trocado, histórias repetidas entre Partes.
- Usuário precisa corrigir tudo num lugar, tentar outra interpretação quando o resultado não presta e levar o backlog final para a ferramenta do time.

## Solution

- Tela mostra backlog da Reunião agrupado por Epic, no formato da Q11, com solicitante e instante de cada pedido.
- Usuário edita qualquer campo; cria e exclui Epics, US e critérios; move US entre Epics; renomeia participantes.
- Renomear ou criar Epic com nome já existente na Reunião junta as duas. Mesmo vale para renomear Participante.
- Botão regenera o backlog inteiro, com aviso de que as edições se perdem. Reunião dividida: permite reajustar cortes antes.
- Exportação em Markdown ou JSON.
- Regeneração em andamento ou falha: backlog anterior segue visível e exportável, só leitura.

## User Stories

1. Como usuário, quero ver o backlog da reunião agrupado por Epic, no formato que defini, para revisar por objetivo.
2. Como usuário, quero ver em cada User Story o solicitante e o instante da gravação, para saber a quem perguntar e onde ouvir o pedido.
3. Como usuário, quero editar o nome de uma Epic e, se der o nome de outra existente na mesma reunião, juntar as duas, para organizar o backlog.
4. Como usuário, quero editar os campos de uma User Story (nome, "Como", "Eu quero", "Para", prioridade e story points), para corrigir o que a LLM errou.
5. Como usuário, quero corrigir o solicitante e o instante de uma User Story, para que a origem do pedido fique certa.
6. Como usuário, quero criar, editar e excluir critérios de aceite, para deixar cada história testável.
7. Como usuário, quero criar uma Epic e uma User Story à mão, para incluir pedidos que a LLM não captou; se a Epic já existe na reunião, quero que o app use a existente, para não duplicar.
8. Como usuário, quero excluir uma User Story e uma Epic vazia, para tirar repetições e sobras.
9. Como usuário, quero mover uma User Story para outra Epic, para corrigir o agrupamento.
10. Como usuário, quero renomear um participante e unir dois participantes quando dou o mesmo nome, para corrigir o solicitante em todas as histórias sem gerar de novo.
11. Como usuário, quero regenerar o backlog inteiro, com aviso de que minhas edições se perdem, para tentar outra interpretação.
12. Como usuário, quero escolher, numa reunião dividida, entre regenerar com os mesmos cortes e reajustar os cortes antes, para tentar uma divisão melhor.
13. Como usuário, quero exportar o backlog em Markdown e em JSON, para levá-lo a outra ferramenta.
14. Como usuário, quero continuar vendo e exportando o backlog anterior enquanto uma regeneração roda ou quando ela falha, para não ficar sem nada enquanto resolvo o problema.

## Escopo

- Leitura do backlog de uma Reunião.
- Edição de Epics, US e critérios; criação e exclusão; mover US entre Epics.
- Mesclagem de Epics por nome igual, na renomeação e na criação (Q47, Q57).
- Endpoint e tela de "Renomear participante", com troca do solicitante nas US quando há união (Q55).
- Regeneração via "Preparar geração" de `transcript-split`, modos "mesmos cortes" e "reajustar cortes" (Q50).
- Exportação em Markdown e JSON (Q31).
- Regras de edição por status.
- Tela de revisão do backlog.

Endpoints sugeridos (planner confirma):
- `GET /meetings/{id}/backlog`
- `POST /meetings/{id}/epics`, `PATCH /meetings/{id}/epics/{epic_id}`, `DELETE /meetings/{id}/epics/{epic_id}`
- `POST /meetings/{id}/epics/{epic_id}/user-stories`, `PATCH /meetings/{id}/user-stories/{story_id}` (inclui mover, com `epic_id`), `DELETE /meetings/{id}/user-stories/{story_id}`
- `POST /meetings/{id}/user-stories/{story_id}/criteria`, `PATCH /meetings/{id}/criteria/{criterion_id}`, `DELETE /meetings/{id}/criteria/{criterion_id}`
- `PATCH /meetings/{id}/participants/{participant_id}` (renomear)
- `POST /meetings/{id}/regenerate` (modo `same_cuts` ou `adjust_cuts`)
- `GET /meetings/{id}/export?format=md` e `GET /meetings/{id}/export?format=json`

## Fora de escopo

- Gerar backlog e validar resposta da LLM. Fica em `backlog-generation`.
- Regenerar só uma Parte (Q50).
- Histórico de versões ou desfazer (Q30).
- Exportação em CSV para o Jira e envio direto ao Jira (Q31).
- Remover US repetidas de forma automática (Q48).
- Juntar Epics por semelhança de sentido (Q47).
- Juntar Epics de Reuniões diferentes (Q57).
- Reordenar Epics e US (Q56).
- Mudar vínculo de um speaker isolado (Q55 muda o Participante inteiro).
- "Cancelar divisão" e tela de divisão. Ficam em `transcript-split` (Q59, Q68).

## Restrições

| Restrição | Fonte |
|---|---|
| Formato de Epic e User Story, com "Como / Eu quero / Para", prioridade, story points e critérios "Dado / Quando / Então"; pt-BR. | rodada 1, Q11; rodada 3, Q37 |
| Cada US guarda só quem pediu, de qual Reunião e quando. | rodada 1, Q12 |
| Cada Usuário vê e altera só as próprias Reuniões. | rodada 2, Q19 |
| Nome da Epic em texto livre, sem descrição; `US-id` sequencial por Reunião. | rodada 2, Q27 |
| Solicitante é um único Participante ou vazio; "quando" dentro da duração do áudio. | rodada 2, Q29 |
| Edição manual de Epic, US, prioridade, story points e critérios; regeneração total com aviso de que as edições se perdem; sem histórico. | rodada 2, Q30; rodada 3, Q37 |
| Exportação em Markdown (formato da Q11) e JSON. | rodada 2, Q31 |
| Markdown exportado como documento de Product Backlog: cabeçalho com totais, tabelas de visão geral, prioridade e Epic, US agrupadas por Epic, considerações derivadas dos dados; prioridade em pt-BR; projeto = título da Reunião; arquivo `backlog_<slug>_<data>.md`. | Q75 |
| Prioridade Low, Medium ou High, exibida em inglês; story points 1, 2, 3, 5, 8 ou 13. | rodada 3, Q37 |
| Tudo ou nada na geração; backlog anterior mantido quando a regeneração falha. | rodada 5, Q46; Q56 |
| Mover US entre Epics; renomear uma Epic para o nome de outra junta as duas. | rodada 5, Q47 |
| Partes não aparecem no backlog nem na exportação. | rodada 5, Q48 |
| Criar e excluir Epics, US e critérios; só Epic vazia é excluída; `US-id` não renumerado; US manual recebe o próximo número depois do maior. | rodada 5, Q49 |
| Na regeneração de uma Reunião dividida, o usuário pode reajustar os cortes antes; `US-id` recomeça em `US-01`. | rodada 5, Q50 |
| "Tentar novamente" da geração reaproveita Transcrição e nomes. | Q54 |
| "Renomear participante" na tela de revisão, sem chamar a LLM nem alterar Epics e US; nome igual une os dois. | Q55 |
| Backlog anterior só para leitura e exportável em `failed`; sobrevive a Epic que já tinha o nome; solicitante e instante editáveis e opcionais em US manual; último critério não sai; cabeçalho e linhas extras no Markdown; exportação de backlog vazio; sem reordenação. | Q56 |
| Epic pertence a uma Reunião; nome único só dentro dela; criar Epic com nome existente na mesma Reunião mescla. | Q57 |
| "Cancelar divisão" vale sempre que há backlog gravado. | Q68 |
| Reinício com nomes confirmados leva `transcribed` a `failed`; antes disso, a Reunião pode ficar em `transcribed` com backlog gravado. | Q69 |
| INP da tela de revisão até 200 ms, medido com backlog de fixture de 30 Epics e 200 US. | Q70 (ADR-0023); 01-prd, NFR-04 |
| FastAPI, SQLite, Pytest, React + TypeScript + shadcn/ui. | briefing |

## Regras por status

"Backlog gravado" existe quando a Reunião teve ao menos uma geração bem-sucedida (marca em `meetings`). Pode estar vazio (zero Epics).

| Situação da Reunião | Backlog | Editar, criar, excluir, mover Epics, US e critérios | Renomear participante | Regenerar | Exportar |
|---|---|---|---|---|---|
| `done` | visível (pode estar vazio) | permitido | permitido | permitido | permitido |
| `transcribed`, `generating` ou `needs_split`, com backlog gravado | anterior visível, só leitura | bloqueado | bloqueado em `generating`; permitido em `transcribed` e `needs_split` | bloqueado (em `needs_split`, "Cancelar divisão" de `transcript-split`) | permitido |
| `failed` com etapa `generation`, com backlog gravado | anterior visível, só leitura, com aviso de que a última geração falhou | bloqueado | permitido | pelo "Tentar novamente" de `meetings` | permitido |
| sem backlog gravado, com Participantes confirmados (`transcribed`, `needs_split`, `failed` da geração) | não há backlog | bloqueado | permitido | bloqueado | bloqueado |
| demais situações | não há backlog | bloqueado | bloqueado | bloqueado | bloqueado |

Por que só leitura em `failed`:
- **Q46:** falha não apaga o backlog anterior. Esconder deixaria o usuário sem nada.
- **Q54:** "Tentar novamente" chama a LLM de novo e, se der certo, substitui o backlog.
- **Q30:** substituição apaga as edições.

Edição liberada em `failed` = usuário editaria backlog que a próxima tentativa apagaria em silêncio. Por isso: só leitura e exportação até a tentativa terminar. "Tentar novamente" mostra o mesmo aviso da regeneração (Q30). Renomear participante segue liberado: não edita texto das US, e o nome novo vale na próxima geração (`participants`, critério 21).

## Contrato com outros módulos

- **Consome** de `backlog-generation`: "Backlog" (leitura e escrita das tabelas de Epic, US e critério) e "Próximo número de US".
- **Consome** de `participants`: "Participantes" (exibir e escolher solicitante) e "Renomear Participante". Na união, troca o `requested_by` das US do absorvido para o sobrevivente, na mesma transação.
- **Consome** de `transcript-split`: "Preparar geração", modo `normal` para `same_cuts` e modo `reajustar` para `adjust_cuts`.
- **Consome** de `meetings`: status, título, data de envio, duração e "Ler marcas" (backlog gravado, Participantes confirmados).
- Módulo não emite avisos e não muda status direto. Regeneração muda status por `transcript-split`.

## Critérios de aceite

### Leitura

1. `GET /meetings/{id}/backlog` numa Reunião em `done` devolve as Epics em ordem. Cada Epic traz o nome e as US em ordem. Cada US traz `US-id`, nome, `as_a`, `i_want`, `so_that`, prioridade, story points, solicitante (`id` e nome, ou vazio), quando em `hh:mm:ss` (ou vazio, em US manual) e critérios em ordem.
2. A resposta não traz nenhuma informação de Parte.
3. Numa Reunião em `failed` com etapa `generation` que tem backlog gravado, `GET /meetings/{id}/backlog` devolve esse backlog e um indicador de que a última geração falhou. Em `transcribed`, `generating` ou `needs_split` com backlog gravado, devolve o backlog anterior e um indicador de só leitura.
4. Numa Reunião sem backlog gravado, `GET /meetings/{id}/backlog` responde HTTP 409.

### Epics

5. `PATCH` de uma Epic com nome novo grava o nome, sem espaços nas pontas.
6. `PATCH` de uma Epic com o nome de outra Epic da mesma Reunião, sem diferenciar maiúsculas e espaços nas pontas, junta as duas. Sobrevive a Epic que já tinha o nome, e as US da renomeada passam para ela, depois das que já existiam.
7. `POST` de Epic com nome não vazio, que não existe na Reunião, cria a Epic, sem US, no fim da lista, e responde HTTP 201.
8. `POST` de Epic com nome igual ao de uma Epic da mesma Reunião, pela regra do critério 6, não cria uma segunda Epic: responde HTTP 200 com a Epic existente, que sobrevive sem mudanças (Q57). Uma Epic de mesmo nome em outra Reunião do mesmo Usuário não impede a criação, e a resposta é HTTP 201.
9. Nome de Epic vazio ou só de espaços é recusado com HTTP 422.
10. `DELETE` de uma Epic sem US a remove. `DELETE` de uma Epic com US é recusado com HTTP 409, e nada muda (Q49).

### User Stories

11. `PATCH` de uma US grava nome, `as_a`, `i_want`, `so_that`, prioridade e story points enviados, e não muda o `US-id`.
12. Prioridade fora de Low, Medium e High, ou story points fora de 1, 2, 3, 5, 8 e 13, são recusados com HTTP 422.
13. Nome, `as_a`, `i_want` ou `so_that` vazio é recusado com HTTP 422.
14. `PATCH` de uma US aceita trocar o solicitante por outro Participante da mesma Reunião, ou deixá-lo vazio. Um Participante de outra Reunião é recusado com HTTP 422.
15. `PATCH` de uma US aceita trocar o instante, em `hh:mm:ss`, dentro de 0 e a duração do áudio. Fora disso, é recusado com HTTP 422.
16. `PATCH` de uma US com `epic_id` de outra Epic da mesma Reunião move a US para o fim dessa Epic, sem mudar o `US-id`. A Epic de origem pode ficar vazia.
17. `POST` de US numa Epic, com todos os campos obrigatórios e pelo menos um critério, cria a US com o próximo `US-id` depois do maior existente na Reunião (Q49).
18. Numa US criada à mão, o solicitante e o instante são opcionais.
19. `DELETE` de uma US a remove com os critérios dela, e os outros `US-id` não mudam. Uma US criada depois disso não reusa o número excluído, se ele era o maior.

### Critérios de aceite

20. `POST` de critério com `given`, `when` e `then` não vazios adiciona o critério no fim da US.
21. `PATCH` de critério grava os campos enviados. Campo vazio é recusado com HTTP 422.
22. `DELETE` do último critério de uma US é recusado com HTTP 409, porque toda US tem pelo menos um critério.

### Renomear participante (Q55)

23. `PATCH /meetings/{id}/participants/{participant_id}` com nome novo troca o nome, e todas as US desse solicitante passam a mostrar o nome novo.
24. Com o nome de outro Participante da Reunião, os dois são unidos pela regra de `participants`, e as US do Participante absorvido passam a ter o sobrevivente como solicitante. Tudo acontece numa só transação.
25. A renomeação não chama a LLM, não muda o texto das US e não muda as Epics.

### Regeneração

26. `POST /meetings/{id}/regenerate` com `same_cuts` numa Reunião em `done` chama "Preparar geração" no modo `normal`.
27. `POST /meetings/{id}/regenerate` com `adjust_cuts` numa Reunião em `done` já dividida chama "Preparar geração" no modo `reajustar`. Numa Reunião não dividida, `adjust_cuts` é recusado com HTTP 422.
28. Regenerar fora de `done` é recusado com HTTP 409, e nada muda.
29. O backlog anterior só é substituído quando a nova geração termina bem (`backlog-generation`, critério 24).

### Regras por status

30. Em `transcribed`, `generating`, `needs_split` e `failed`, as rotas de escrita de Epics, US e critérios e a de regenerar respondem HTTP 409, e nada muda. A rota de renomear participante segue a regra de `participants` (critério 21): recusa só em `generating` e sem Participantes confirmados.
31. A exportação funciona sempre que existe backlog gravado: em `done`, `transcribed`, `generating`, `needs_split` e `failed`. Sem backlog gravado, responde HTTP 409.

### Exportação

32. `GET /meetings/{id}/export?format=md` devolve um documento de Product Backlog em GitHub Flavored Markdown (Q75), nesta ordem: cabeçalho; "1. Visão Geral do Backlog" (tabela ID, Épico, História de Usuário, Prioridade, Story Points, com todas as US); uma seção `## 2.N Épico: <nome>` por Epic, com cada US em `### <US-id> — <nome>`; "3. Resumo de Priorização" (tabela Prioridade, Histórias, Story Points, linhas Alta, Média, Baixa e Total); "4. Resumo por Épico" (tabela Épico, Histórias, Story Points e Total); "5. Considerações para o Desenvolvimento". Epics e US na ordem do backlog. Prioridade traduzida: High = Alta, Medium = Média, Low = Baixa. Totais calculados do backlog.
33. O cabeçalho traz título, data, projeto (= título da Reunião), total de Epics, total de US e soma de Story Points. Cada US traz ID, solicitante, horário na Reunião, perfil (`as_a`), prioridade e Story Points em lista; a história em "Como <perfil>, quero <desejo>, para que <benefício>."; e os critérios numerados em "Dado que <given>, quando <when>, então <then>.". Solicitante e horário vazios são omitidos. Quebras de linha viram espaço e caracteres de Markdown e `|` são escapados, sem alterar o texto. As considerações saem só dos dados do backlog (ordem de prioridade, Epic de maior esforço, US de 13 pontos, US sem solicitante, número de critérios), sem LLM e sem requisito novo.
34. `GET /meetings/{id}/export?format=json` devolve as Epics com as US e os critérios, incluindo `US-id`, solicitante (nome), quando (`hh:mm:ss`), título e data da Reunião.
35. Nenhuma exportação traz informação de Parte nem identificadores internos do banco além do `US-id`.
36. Com backlog gravado e vazio, a exportação Markdown devolve só o cabeçalho, com totais zerados, sem Epics; a JSON devolve a lista de Epics vazia.

### Isolamento e autenticação

37. Todas as rotas deste módulo, com o `id` de uma Reunião de outro Usuário, ou com `id` de Epic, US, critério ou Participante de outra Reunião, respondem HTTP 404, e nada muda.
38. Requisição sem autenticação a qualquer rota deste módulo recebe HTTP 401.

### Frontend

39. A tela de revisão mostra as US agrupadas por Epic, com todos os campos do formato, o solicitante e o instante.
40. Cada campo pode ser editado na própria tela. Erros da API aparecem junto ao campo.
41. Renomear ou criar uma Epic, ou renomear um Participante, com um nome que já existe na Reunião mostra, antes de salvar, que os dois serão juntados.
42. Excluir US, Epic ou critério pede confirmação. O botão de excluir Epic fica desabilitado enquanto ela tiver US.
43. Mover uma US abre a escolha da Epic de destino entre as Epics da Reunião.
44. O botão "Regenerar" avisa que todas as edições serão perdidas antes de confirmar. Numa Reunião dividida, oferece "mesmos cortes" e "reajustar cortes".
45. Os botões "Exportar Markdown" e "Exportar JSON" baixam o arquivo.
46. Em `failed` com backlog gravado, a tela mostra o backlog só para leitura, com aviso de que a última geração falhou, o motivo e o botão "Tentar novamente" de `meetings`, que repete o aviso de perda das edições. Em `transcribed`, `generating` e `needs_split` com backlog gravado, a tela mostra o backlog só para leitura, com o status atual.

### Backlog vazio

47. Numa Reunião em `done` cuja geração bem-sucedida não produziu nenhuma US, `GET /meetings/{id}/backlog` responde HTTP 200 com a lista de Epics vazia. A criação de Epics e US funciona, e a exportação funciona como no critério 36.
48. Na tela de revisão, a ação "Renomear participante" aparece também quando o backlog está só para leitura, nas situações em que a regra por status a permite.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, Reuniões montadas no setup com backlog, Participantes, marcas e status de cada caso. "Preparar geração" de `transcript-split` é fake que registra o modo. "Renomear Participante" usa a implementação real de `participants`, para testar a transação da união. Cobre critérios 1 a 38 e 47, um teste por critério. Critério 30 roda uma vez por status.
- **Exportação (critérios 32 a 36):** snapshot do Markdown e do JSON para um backlog de fixture.
- **Frontend (critérios 39 a 46 e 48):** Vitest + React Testing Library + MSW. Resolvido: ADR-0015.
- **Performance (01-prd, NFR-04):** INP da tela de revisão medido no DevTools Performance com backlog de fixture de 30 Epics e 200 US, no checkpoint manual.

## Questões em aberto

1. Respondidas pelo planner:
   - nome do arquivo exportado: `backlog_<slug-do-titulo>_<data>.md` (Q75) ou `<slug-do-titulo>-backlog.json`. Resolvido: `05-api.md`.
   - como este módulo escreve nas tabelas de `backlog-generation`: interface `BacklogRepository` e `next_us_number`. Resolvido: `02-architecture.md`, "Interfaces internas".
   - edição concorrente em duas abas: último a gravar vence, sem bloqueio otimista na v1. Resolvido: `05-api.md`.
2. Códigos HTTP 200, 201, 404, 409 e 422 e endpoints são sugestões, não decisões.
