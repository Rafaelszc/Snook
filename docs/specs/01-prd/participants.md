# 01-prd/participants - PRD do módulo `participants`

> Status: completo. Decisões fechadas: Q9, Q10, Q19, Q26, Q29, Q34, Q35, Q50, Q54, Q55, Q56, Q69.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: `diarized-transcription` (segmentos, speakers, áudio tratado), `llm-providers` (provedor ativo), `meetings` (status e marca de confirmação) e `auth` (rotas). Dependentes: `transcript-split`, `backlog-generation` e `backlog-review`.

## Problem Statement

- Diarização separa vozes só com rótulos anônimos (`SPEAKER_00`, `SPEAKER_01`).
- Backlog com "pedido por SPEAKER_01" não ajuda ninguém.
- Usuário precisa reconhecer cada voz e dar o nome da pessoa antes de a LLM interpretar a reunião.
- Às vezes a diarização divide a mesma pessoa em dois rótulos. Usuário precisa juntá-los.
- Às vezes ele só vê um nome errado depois do backlog.

## Solution

- Reunião em `transcribed`: tela lista cada speaker detectado.
- Por speaker: usuário toca amostra de até 10 s do maior segmento, já tratada, e digita o nome.
- Dois speakers com o mesmo nome viram um só Participante.
- Tela mostra qual provedor ativo será usado.
- Ao confirmar: app grava Participantes, e a Reunião segue sozinha para a geração.
- Sem provedor ativo: confirmação bloqueada, com mensagem que leva à tela de configurações.
- Após a confirmação, nomes só mudam por "Renomear participante", na tela de revisão do backlog (Q55). Regra do nome e da união mora aqui.

## User Stories

1. Como usuário, quero ver todos os speakers detectados numa reunião transcrita, para saber quantas vozes o app encontrou.
2. Como usuário, quero tocar uma amostra curta da voz de cada speaker, para reconhecer quem é.
3. Como usuário, quero digitar o nome de cada speaker, para que a transcrição e o backlog citem as pessoas reais.
4. Como usuário, quero dar o mesmo nome a dois speakers, para juntar a mesma pessoa que a diarização dividiu.
5. Como usuário, quero ser impedido de confirmar enquanto faltar nome para algum speaker, para não gerar backlog com rótulos anônimos.
6. Como usuário, quero ver qual provedor e modelo serão usados na geração, para saber o que vai interpretar a reunião.
7. Como usuário, quero ser levado à tela de configurações quando não tenho provedor ativo, para resolver isso antes de confirmar.
8. Como usuário, quero que a reunião siga sozinha para a geração depois que confirmo os nomes, para não precisar de outro passo.
9. Como usuário, quero que os nomes sejam mantidos em "Tentar novamente" e na regeneração, para não nomear tudo de novo.
10. Como usuário, quero renomear um Participante depois de ver o backlog, e unir dois Participantes quando dou a um o nome do outro, para corrigir o solicitante sem gerar o backlog de novo. (Q55; a ação aparece na tela de `backlog-review`)
11. Como módulo do sistema (`transcript-split`), quero ser avisado quando os nomes de uma Reunião são confirmados, para começar a checagem de tamanho.
12. Como módulo do sistema (`transcript-split`, `backlog-generation`, `backlog-review`), quero ler os Participantes de uma Reunião e saber qual Participante corresponde a cada speaker, para montar o prompt e registrar o solicitante.
13. Como módulo do sistema (`backlog-review`), quero renomear um Participante e saber se ele foi unido a outro, para corrigir o solicitante das User Stories na mesma operação.
14. Como módulo do sistema (`meetings`), quero saber que os nomes de uma Reunião foram confirmados, para marcá-la como interrompida se o backend reiniciar antes da geração começar (Q69).

## Escopo

- Lista de speakers de uma Reunião em `transcribed`, com tempo total de fala.
- Amostra de até 10 s por speaker, do áudio tratado.
- Nomeação de todos os speakers, com junção por nome igual.
- Exibição do provedor ativo; bloqueio sem provedor ativo.
- Gravação dos Participantes e do vínculo speaker → Participante, com registro da confirmação em `meetings`.
- Aviso "Participantes confirmados".
- Consulta dos Participantes e do vínculo com os speakers.
- Interface interna "Renomear Participante", com união por nome igual (Q55).
- Tela de nomeação.

Endpoints sugeridos (planner confirma): `GET /meetings/{id}/speakers`, `GET /meetings/{id}/speakers/{speaker_label}/sample`, `PUT /meetings/{id}/participants`, `GET /meetings/{id}/participants`. Endpoint de renomear fica em `backlog-review` (ver "Onde mora a renomeação").

Campos sugeridos: Participante com `id`, `meeting_id`, `name`; vínculo com `meeting_id`, `speaker_label`, `participant_id`.

## Fora de escopo

- Reconhecer a mesma pessoa entre Reuniões diferentes (não-objetivo).
- Separar um speaker em dois, ou mover segmentos de um speaker para outro.
- Mudar vínculo de um speaker isolado após a confirmação. Renomeação muda o Participante inteiro (Q55).
- Editar o texto da Transcrição.
- Escolher provedor na tela de nomeação; ela só exibe o ativo (Q35).
- Checagem de janela de contexto e divisão em Partes. Ficam em `transcript-split`.
- Atualizar o solicitante das User Stories. Tabela de US não é daqui; `backlog-review` faz isso com o resultado da renomeação.

## Restrições

| Restrição | Fonte |
|---|---|
| Após a transcrição, o usuário ouve um trecho da voz de cada speaker, já tratado, e nomeia cada um; em seguida, a Reunião segue para a LLM. | rodada 1, Q9 e Q10 |
| Amostra de até 10 s do maior segmento. | rodada 2, Q26 |
| Todos os speakers nomeados. | rodada 2, Q26 |
| Mesmo nome junta no mesmo Participante. | rodada 2, Q26 |
| A geração começa sozinha ao confirmar os nomes, sempre com o provedor ativo. | rodadas 2 e 3, Q26 e Q35 |
| A tela de nomeação só exibe qual provedor será usado. | rodada 3, Q35 |
| Sem provedor ativo, a geração é bloqueada com mensagem que aponta para a tela de configurações. | rodada 3, Q34 |
| O solicitante de cada US é um único Participante, ou fica vazio. | rodada 2, Q29 |
| Regeneração e "Tentar novamente" da geração reaproveitam os nomes dos speakers. | Q50 e Q54 |
| "Renomear participante" na tela de revisão do backlog, depois da confirmação; atualiza o solicitante em todas as US sem chamar a LLM nem alterar Epics e US; nome igual ao de outro Participante da mesma Reunião une os dois, com a mesma regra da nomeação. | Q55 |
| Início da amostra, comparação de nomes, sobrevivente na união e bloqueio da renomeação em `generating` (critérios 3, 7, 18 e 21). | Q56 |
| Reunião em `transcribed` com Participantes confirmados vai para `failed` ao subir o backend; a confirmação precisa ficar registrada em `meetings`. | Q69 |
| Cada Usuário vê e altera só as próprias Reuniões. | rodada 2, Q19 |
| FastAPI, SQLite, Pytest, React + TypeScript + shadcn/ui. | briefing |

## Onde mora a renomeação (Q55)

- **Regra e dados em `participants`.** Módulo é dono dos Participantes, dos vínculos e da regra de nome igual (critério 7). Regra em outro lugar = duas cópias.
- **Endpoint e botão em `backlog-review`.** Ação fica na tela de revisão (Q55) e corrige o solicitante das US. Tabelas de US não são daqui. `backlog-review` expõe o endpoint, chama "Renomear Participante" e, na mesma transação, troca o solicitante das US do absorvido pelo sobrevivente.
- **Sem ciclo.** `backlog-review` fica abaixo de `participants` na cadeia (`participants` → `transcript-split` → `backlog-generation` → `backlog-review`). Chamada vai de baixo para cima. `participants` não conhece User Stories.
- Solicitante da US aponta para o `id` do Participante, não para o nome. Renomeação simples aparece em todas as US sem tocar nelas. Só a união troca o `id`.

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Consome** de `diarized-transcription`: "Speakers" (rótulos, tempo total, maior segmento) e "Áudio tratado" (trecho por intervalo).
- **Consome** de `llm-providers`: "Provedor ativo" (provedor, modelo, ou erro "sem provedor ativo").
- **Consome** de `meetings`: status da Reunião e "Registrar Participantes confirmados".
  - Nomeação: só em `transcribed`, sem Participantes confirmados.
  - Renomeação: com Participantes confirmados, em qualquer status, exceto `generating`.
- **Participantes confirmados**: ao gravar os nomes, chama "Registrar Participantes confirmados" de `meetings` na mesma transação e avisa o pipeline uma única vez, com o `id`. `transcript-split` consome. Módulo não muda status; transição seguinte é de `transcript-split`.
- **Participantes**: dado o `id` da Reunião, devolve Participantes (`id`, `name`) e os `speaker_label` de cada um.
- **Participante de um speaker**: dado `id` da Reunião e `speaker_label`, devolve o Participante.
- **Renomear Participante**: dado `id` da Reunião, `id` do Participante e novo nome, aplica a regra de nome. Devolve o Participante resultante e, se houve união, o `id` absorvido. Aceita entrar na transação de quem chama, para `backlog-review` atualizar as US no mesmo commit.
- **Exclusão**: Participantes e vínculos ficam ligados à Reunião e somem com ela (exclusão em cascata de `meetings`).

## Critérios de aceite

### Speakers e amostras

1. `GET /meetings/{id}/speakers` numa Reunião em `transcribed` devolve cada `speaker_label` presente na Transcrição, uma vez, com o tempo total de fala.
2. `GET /meetings/{id}/speakers/{speaker_label}/sample` devolve um áudio de no máximo 10 s, tirado do maior segmento desse speaker, a partir do áudio tratado.
3. A amostra começa no início do maior segmento. Se dois segmentos empatam como maiores, vale o que começa antes.
4. Para um speaker cujo maior segmento dura menos de 10 s, a amostra tem a duração desse segmento.
5. Speaker inexistente na Reunião responde HTTP 404.

### Nomeação e confirmação

6. `PUT /meetings/{id}/participants` com um nome para cada speaker grava os Participantes e os vínculos, e responde com os Participantes criados.
7. Speakers com o mesmo nome ficam ligados a um único Participante. A comparação ignora maiúsculas e espaços nas pontas, como nas Epics (Q47), e o nome gravado é o primeiro informado, sem espaços nas pontas.
8. Um pedido que deixa algum speaker sem nome, ou com nome vazio ou só de espaços, é recusado com HTTP 422, e nada é gravado.
9. Um pedido com `speaker_label` que não existe na Reunião é recusado com HTTP 422, e nada é gravado.
10. Depois de uma confirmação aceita, o aviso "Participantes confirmados" é emitido uma única vez, com o `id` da Reunião, e "Ler marcas" de `meetings` informa Participantes confirmados. Se a gravação falha, a marca não é registrada e nenhum aviso é emitido.
11. Sem provedor ativo, o pedido é recusado com HTTP 409 e mensagem que aponta para a tela de configurações. Nada é gravado, nenhum aviso é emitido e a Reunião continua em `transcribed`.
12. Um pedido numa Reunião fora de `transcribed` é recusado com HTTP 409, e nada muda.
13. Um segundo `PUT /meetings/{id}/participants` numa Reunião que já tem Participantes confirmados é recusado com HTTP 409, e os nomes não mudam. Isso vale também quando "Tentar novamente" da etapa `generation` devolve a Reunião a `transcribed` (Q54). Depois da confirmação, os nomes só mudam por "Renomear Participante" (critérios 17 a 22).

### Consulta e uso pelos outros módulos

14. `GET /meetings/{id}/participants` devolve cada Participante com `id`, `name` e os `speaker_label` ligados a ele.
15. A interface "Participante de um speaker" devolve o mesmo Participante para dois speakers juntados por nome.
16. Depois de "Tentar novamente" da etapa `generation` e de uma regeneração, os Participantes e os vínculos continuam os mesmos.

### Renomear Participante (Q55)

17. "Renomear Participante" com um nome novo, que não coincide com nenhum outro Participante da Reunião, troca o nome, mantém o mesmo `id` e os mesmos vínculos, e não informa união.
18. "Renomear Participante" com um nome que coincide com o de outro Participante da mesma Reunião, pela regra do critério 7, une os dois. Sobrevive o Participante que já tinha o nome. Os vínculos de speaker do Participante renomeado passam para o sobrevivente, o renomeado deixa de existir, e a interface informa o `id` absorvido.
19. Nome vazio ou só de espaços é recusado, e nada muda.
20. A renomeação é recusada numa Reunião sem Participantes confirmados, e nada muda.
21. Com Participantes confirmados, a renomeação é aceita nos status `transcribed`, `needs_split`, `done` e `failed` (etapa `generation`). Ela é recusada só em `generating`, para não mudar nomes no meio de uma chamada à LLM, e nada muda. Em `needs_split`, o nome novo aparece no próximo "Texto da Parte" de `transcript-split`, que lê o nome a cada montagem.
22. A renomeação não chama nenhuma interface de `llm-providers`, não emite "Participantes confirmados" e não muda o status da Reunião.

### Isolamento e autenticação

23. Todas as rotas deste módulo, com o `id` de uma Reunião de outro Usuário, respondem HTTP 404, e nada muda na Reunião do outro Usuário.
24. Requisição sem autenticação a qualquer rota deste módulo recebe HTTP 401.

### Frontend

25. O detalhe de uma Reunião em `transcribed` com `participants_confirmed` igual a falso em `GET /meetings/{id}` leva à tela de nomeação.
26. A tela de nomeação mostra, para cada speaker, um botão para tocar a amostra, o tempo total de fala e um campo de nome.
27. Quando dois ou mais speakers recebem o mesmo nome, a tela indica que eles serão juntados num só Participante.
28. A tela mostra o provedor ativo e o modelo que serão usados na geração.
29. Sem provedor ativo, a tela mostra uma mensagem com link para a tela de configurações, e o botão de confirmar fica desabilitado.
30. O botão de confirmar fica desabilitado enquanto algum speaker estiver sem nome.
31. Depois de confirmar, o frontend leva o usuário ao detalhe da Reunião, onde o status passa a ser acompanhado.

Tela e endpoint de "Renomear participante": PRD de `backlog-review`.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, Reuniões montadas no setup já em `transcribed`, com segmentos fake. Fakes: áudio tratado (trecho sintético de duração conhecida), "Provedor ativo" (com e sem provedor), consumidor do aviso "Participantes confirmados". Cobre critérios 1 a 16, 23 e 24, um teste por critério.
- **Renomear (critérios 17 a 22):** testados aqui pela interface interna; endpoint é de `backlog-review`. Critério 21 roda uma vez por status. PRD de `backlog-review` cobre o mesmo pela API, junto com a troca do solicitante nas US.
- **Amostras (critérios 2 a 4):** teste confere duração do áudio devolvido e intervalo pedido a "Áudio tratado".
- **Frontend (critérios 25 a 31):** Vitest + React Testing Library + MSW. Resolvido: ADR-0015.

## Questões em aberto

1. **Transcrição com nomes.** Resolvido: `05-api.md`. Frontend junta os segmentos de `GET /meetings/{id}/transcript` com `GET /meetings/{id}/participants`. Nomes lidos na hora: renomeação aparece sem passo extra.
2. Respondidas pelo planner:
   - formato da amostra: `audio/wav`, gerado sob demanda, sem cache. Resolvido: ADR-0014.
   - tamanho máximo do nome: 100 caracteres. Resolvido: `05-api.md`.
   - "Renomear Participante" na transação de `backlog-review`: `rename(..., before_absorb)` na mesma unidade de trabalho. Resolvido: ADR-0006 e `02-architecture.md`, "Interfaces internas".
   - transação da confirmação com "Registrar Participantes confirmados": unidade de trabalho compartilhada, um commit. Resolvido: ADR-0006.
3. Códigos HTTP 404, 409 e 422 e endpoints são sugestões, não decisões.
