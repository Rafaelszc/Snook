# 01-prd/transcript-split - PRD do módulo `transcript-split`

> Status: completo. Decisões fechadas: Q34, Q43, Q44, Q45, Q46, Q48, Q50, Q51, Q52, Q54, Q56, Q59, Q65, Q66, Q67, Q68, Q70 (ADR-0019).
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`. Rotas sem o prefixo `/api` (ver `01-prd.md`, "Convenção de rotas").
> Depende de: `participants` (nomes), `llm-providers` (provedor ativo, janela de contexto, estimativa de tokens), `diarized-transcription` (segmentos), `meetings` (status e marcas) e `auth` (rotas). Dependentes: `backlog-generation` e `backlog-review`.

## Problem Statement

- Reunião longa pode gerar Transcrição maior do que o modelo ativo lê numa chamada.
- Mandar assim: provedor recusa ou, no Ollama, corta o texto sem avisar. Backlog sai incompleto.
- Usuário não quer reenviar o áudio nem cortar o arquivo à mão.
- Quer dividir a Transcrição dentro do app, com ajuda, e receber backlog único.

## Solution

- Nomes confirmados: módulo mede a Transcrição contra o orçamento do modelo ativo.
- Cabe: Transcrição inteira vira Parte única; Reunião segue para `generating`.
- Não cabe: Reunião vai para `needs_split`. Tela mostra a Transcrição com cortes sugeridos para cada Parte caber.
- Usuário move, adiciona ou remove cortes, sempre no fim de um segmento, e confirma quando todas as Partes cabem.
- Partes gravadas substituem as anteriores. Reunião segue para `generating`.
- Mesma checagem roda em "Tentar novamente" da geração e na regeneração, porque o provedor ativo pode ter mudado.
- Reunião com backlog gravado pode cancelar a divisão e voltar ao backlog anterior.

## User Stories

1. Como usuário, quero que o app descubra sozinho se a transcrição cabe no modelo, para não ter de calcular nada.
2. Como usuário, quero que uma transcrição que cabe siga direto para a geração, sem tela extra, para não perder tempo.
3. Como usuário, quero entender por que preciso dividir a reunião, vendo o tamanho estimado, o orçamento do modelo e qual provedor e modelo estão ativos, para decidir se divido ou troco de modelo.
4. Como usuário, quero receber cortes já sugeridos que fazem cada parte caber, para dividir com poucos cliques.
5. Como usuário, quero mover, adicionar e remover cortes, sempre no fim de uma fala, para separar a reunião em pontos que façam sentido.
6. Como usuário, quero ver, para cada parte, o intervalo de tempo e se ela cabe no modelo, para saber o que ainda falta ajustar.
7. Como usuário, quero ser impedido de confirmar enquanto alguma parte não couber, para não gerar um backlog incompleto.
8. Como usuário, quero que a reunião siga sozinha para a geração depois que confirmo a divisão, para não precisar de outro passo.
9. Como usuário, quero que "Tentar novamente" e a regeneração refaçam a checagem com o provedor ativo do momento, para não falhar por causa de uma divisão feita para outro modelo.
10. Como usuário, quero poder reajustar os cortes antes de regenerar uma reunião dividida, e cancelar a divisão se mudar de ideia, para tentar uma divisão melhor sem perder o backlog atual.
11. Como usuário, quero que, se eu trocar para um modelo maior enquanto a reunião espera divisão, ela siga sozinha sem dividir, para não fazer trabalho à toa.
12. Como módulo do sistema (`backlog-generation`), quero receber as Partes em ordem, já com o texto que será enviado, e saber o orçamento de cada Parte, para chamar a LLM uma vez por Parte sem passar do limite.

## Escopo

- Consumo dos avisos "Participantes confirmados" (de `participants`) e "Nova tentativa" com etapa `generation` (de `meetings`), só com a Reunião em `transcribed`.
- Pedido de regeneração de `backlog-review`, com ou sem reajuste de cortes (Q50).
- Montagem do texto da Parte, usado na estimativa e no envio.
- Estimativa de tokens pelo modelo ativo; comparação com o orçamento da Parte.
- Parte única quando a Transcrição cabe.
- Status `needs_split`, cortes sugeridos, tela de divisão, validação dos cortes.
- Checagem "passou a caber" ao abrir a tela de divisão, por `POST /meetings/{id}/split/refresh` (Q66, Q70, ADR-0019).
- "Cancelar divisão" quando há backlog gravado (Q59 a, Q68).
- Gravação das Partes, sempre substituindo as anteriores; aviso "Partes prontas" para `backlog-generation`.
- Transições de status do contrato.

Endpoints sugeridos (planner confirma): `GET /meetings/{id}/split` (só leitura), `POST /meetings/{id}/split/refresh` (checagem "passou a caber" ao abrir a tela, ADR-0019), `PUT /meetings/{id}/split`, `POST /meetings/{id}/split/cancel`.

Campos sugeridos da Parte: `id`, `meeting_id`, `index` (ordem, a partir de 1), `first_segment_id`, `last_segment_id`, `start_seconds`, `end_seconds`, `estimated_tokens`. Reunião guarda também a origem do `needs_split` (`split_reason`: `too_long` ou `adjust`), só para exibição (Q68).

## Fora de escopo

- Chamar a LLM, validar a saída e gravar o backlog. Ficam em `backlog-generation`.
- Cortar ou reprocessar o áudio (Q43).
- Cortar no meio de um segmento (Q44).
- Partes sobrepostas (Q44).
- Dividir Reunião que cabe (Q45).
- Resumir a Transcrição.
- Mostrar Partes no backlog ou na exportação (Q48).
- Renomear Participantes. Fica em `participants` e `backlog-review` (Q55).
- Mudar estado em `GET` (ADR-0019).

## Restrições

| Restrição | Fonte |
|---|---|
| Checagem na geração, com a Transcrição real comparada à janela de contexto do modelo ativo; divisão da Transcrição no app, na mesma Reunião; áudio não reprocessado. | rodada 4, Q43 |
| Cortes sugeridos e ajustáveis; sempre no fim de um segmento; sem sobreposição; Partes contíguas cobrindo 100% da Transcrição; confirmação bloqueada enquanto alguma Parte não couber. | rodada 5, Q44 |
| A divisão só aparece quando a Transcrição não cabe; status `needs_split` entre `transcribed` e `generating`. | rodada 5, Q45 |
| Partes enviadas em sequência, na ordem do tempo; a partir da segunda Parte, a LLM recebe os nomes das Epics já criadas. | rodada 5, Q46 |
| "Quando" é o instante absoluto na gravação. | rodada 5, Q48 |
| Na regeneração de uma Reunião dividida, o usuário pode reajustar os cortes antes. | rodada 5, Q50 |
| Janela de contexto por provedor, em tokens, editável. | rodada 5, Q51 |
| Sem provedor ativo, a geração é bloqueada com mensagem que aponta para a tela de configurações. | rodada 3, Q34 |
| "Tentar novamente" da geração reaproveita a Transcrição e os nomes. | Q54 |
| Segmento maior que o orçamento leva a `failed`; cortes pela regra gulosa; Partes anteriores reaproveitadas quando ainda cabem. | Q56 |
| Saídas de `needs_split`: `failed` na confirmação sem provedor ativo ou com segmento maior que o orçamento; Parte única quando a Transcrição passa a caber. | Q59 |
| "Reajustar cortes" com a Transcrição cabendo inteira segue com Parte única, sem tela. | Q65 |
| "Passou a caber, segue sozinha" roda ao abrir a tela de divisão e ao confirmar. | Q66 |
| Ao abrir a tela, a regra roda em `POST /meetings/{id}/split/refresh`, chamado pelo frontend. `GET /meetings/{id}/split` só lê. | Q70 (ADR-0019) |
| Tela de divisão sem provedor ativo mostra só a mensagem que aponta para a tela de configurações. | Q67 |
| "Cancelar divisão" vale sempre que a Reunião tem backlog gravado (`needs_split` → `done`, sem mudar nada); `split_reason` só para exibição. | Q68 |
| Nenhuma chamada à LLM recebe um texto de Parte cuja estimativa passe do orçamento. | 01-prd, RT-10 |
| Cada Usuário vê e altera só as próprias Reuniões. | rodada 2, Q19 |
| Lista de segmentos da tela de divisão virtualizada; INP até 200 ms com Transcrição de 2 h. | Q70 (ADR-0023); 01-prd, NFR-04 e NFR-07 |

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Consome** "Participantes confirmados" e "Nova tentativa" (etapa `generation`). Os dois chamam "Preparar geração" no modo normal. Avisos só agem com a Reunião em `transcribed`; fora disso, ignorados.
- **Preparar geração**: dado `id` da Reunião e modo (`normal` ou `reajustar`), checa e:
  1. sem provedor ativo: Reunião vai para `failed`, etapa `generation`, mensagem que aponta para a tela de configurações;
  2. Transcrição inteira cabe: grava Parte única, Reunião vai para `generating`, emite "Partes prontas". Vale também no modo `reajustar` (Q45, Q59 c, Q65);
  3. modo `normal`, não cabe, mas Partes anteriores existem e todas cabem no orçamento atual: reaproveita, Reunião vai para `generating`, emite "Partes prontas";
  4. um segmento sozinho passa do orçamento: Reunião vai para `failed`, etapa `generation`, mensagem pedindo modelo com janela maior;
  5. demais casos: Reunião vai para `needs_split`; grava `split_reason` `adjust` no modo `reajustar`, `too_long` no modo `normal`.
- `backlog-review` chama "Preparar geração" para regenerar: modo `normal` para "mesmos cortes"; modo `reajustar` para "reajustar cortes antes" (Q50).
- **Texto da Parte**: dado intervalo de segmentos, monta o texto enviado à LLM. Uma linha por segmento: instante absoluto de início, nome atual do Participante, texto. Formato sugerido: `[hh:mm:ss] Nome: texto` (planner pode ajustar). Mesma função serve à estimativa e ao envio: tamanho medido = tamanho enviado. Nome lido a cada montagem; renomeação (Q55) vale na próxima geração.
- **Orçamento da Parte**: dado provedor, modelo e janela, devolve janela menos reserva. Reserva cobre System Prompt, lista de Participantes, nomes de Epics a partir da segunda Parte (Q46) e resposta da LLM. Cálculo da reserva: ADR-0011. `backlog-generation` usa para reestimar cada Parte antes do envio.
- **Partes prontas**: aviso emitido uma única vez por preparação concluída, com o `id`. `backlog-generation` consome.
- **Partes**: dado `id` da Reunião, devolve Partes em ordem, com intervalo e texto.
- **Gravação das Partes**:
  - Toda gravação (Parte única ou confirmação por `PUT`) apaga todas as Partes anteriores da Reunião e grava as novas numa só transação.
  - Reaproveitamento não grava nada.
  - Entrar em `needs_split` não apaga as Partes anteriores. Elas servem de sugestão de cortes no reajuste.
  - Depois de "Cancelar divisão", as Partes anteriores voltam a valer, sem mudança.
- **Backlog gravado**: lido de "Ler marcas" de `meetings`. Decide se "Cancelar divisão" é permitido.
- **Status**, via "Atualizar status" de `meetings`:
  - `transcribed` → `generating`, `needs_split` ou `failed` (etapa `generation`);
  - `needs_split` → `generating` (cortes confirmados, ou Transcrição que passou a caber inteira);
  - `needs_split` → `done` ("Cancelar divisão", com backlog gravado);
  - `needs_split` → `failed` (etapa `generation`, na confirmação);
  - `done` → `generating`, `needs_split` ou `failed` (etapa `generation`), na regeneração.

  Tabela de transições de `meetings` reflete isso.
- **Exclusão**: Partes ligadas à Reunião somem com ela.

## Critérios de aceite

Nos testes, "cabe" significa estimativa de tokens do texto da Parte menor ou igual ao orçamento. Estimativa e janela vêm de fakes.

### Checagem

1. Depois de "Participantes confirmados", numa Reunião cuja Transcrição inteira cabe, o módulo grava uma Parte única que cobre todos os segmentos, leva a Reunião a `generating` e emite "Partes prontas" uma única vez.
2. Depois de "Participantes confirmados", numa Reunião cuja Transcrição não cabe, a Reunião vai para `needs_split`, nenhuma Parte é gravada e nenhum aviso é emitido.
3. Em nenhum dos casos a interface "Gerar" de `llm-providers` é chamada por este módulo.
4. A estimativa usa o texto montado por "Texto da Parte" e o modelo do provedor ativo do Usuário dono da Reunião.
5. Sem provedor ativo no momento da checagem, a Reunião vai para `failed` com etapa `generation` e mensagem que aponta para a tela de configurações.
6. Se um único segmento sozinho passa do orçamento, a Reunião vai para `failed` com etapa `generation` e mensagem pedindo um modelo com janela de contexto maior, porque não há corte possível no fim de segmento.

### Cortes sugeridos

7. `GET /meetings/{id}/split` numa Reunião em `needs_split` devolve:
   - o orçamento;
   - o provedor e o modelo ativos;
   - a estimativa da Transcrição inteira;
   - os segmentos, com instante, Participante e texto;
   - uma lista de cortes sugeridos;
   - se a Reunião permite "Cancelar divisão" (tem backlog gravado);
   - o `split_reason`, só para exibição.
8. Cada corte sugerido fica no fim de um segmento. As Partes resultantes são contíguas, não se sobrepõem, cobrem todos os segmentos e cabem no orçamento.
9. Os cortes sugeridos seguem a regra gulosa: cada Parte recebe o maior número de segmentos seguidos que ainda cabe. Assim, o número de Partes é o menor possível com cortes no fim de segmento.
10. Para cada Parte sugerida, a resposta traz intervalo de tempo, estimativa de tokens e se cabe.
11. `GET /meetings/{id}/split` fora de `needs_split` responde HTTP 409. A exceção é uma Reunião em `done` já dividida: nesse caso, devolve os cortes atuais, só para leitura. `POST /meetings/{id}/split/refresh` fora de `needs_split` responde HTTP 409, e nada muda.

### Confirmação da divisão

12. `PUT /meetings/{id}/split` com cortes válidos numa Reunião em `needs_split` grava as Partes em ordem, leva a Reunião a `generating` e emite "Partes prontas" uma única vez.
13. Um corte que não cai no fim de um segmento da Reunião é recusado com HTTP 422, e nada é gravado.
14. Cortes repetidos ou fora de ordem são recusados com HTTP 422, e nada é gravado.
15. Um conjunto de cortes em que alguma Parte não cabe, com todos os segmentos cabendo sozinhos, é recusado com HTTP 422, com o índice da Parte e a estimativa. Nada é gravado, e a Reunião continua em `needs_split`.
16. A validação usa o provedor ativo no momento do `PUT`. Se o provedor ou a janela mudaram desde o `GET` e uma Parte deixou de caber, o pedido é recusado como no critério 15.
17. `PUT /meetings/{id}/split` numa Reunião fora de `needs_split` responde HTTP 409, e nada muda.
18. As Partes gravadas guardam `start_seconds` e `end_seconds` absolutos na gravação, iguais ao início do primeiro segmento e ao fim do último segmento da Parte.

### Nova tentativa e regeneração

19. "Nova tentativa" da etapa `generation` numa Reunião cuja Transcrição inteira cabe no provedor ativo atual grava uma Parte única e segue para `generating`, mesmo que a Reunião tivesse sido dividida antes.
20. "Nova tentativa" da etapa `generation` numa Reunião que não cabe inteira, mas cujas Partes anteriores ainda cabem todas, reaproveita essas Partes e segue para `generating`, sem tela de divisão.
21. "Nova tentativa" da etapa `generation` numa Reunião que não cabe inteira, e cujas Partes anteriores não cabem mais, leva a Reunião a `needs_split`.
22. "Preparar geração" no modo `reajustar`, numa Reunião em `done` já dividida cuja Transcrição não cabe inteira, leva a Reunião a `needs_split` com `split_reason` igual a `adjust`. Depois disso, `GET /meetings/{id}/split` sugere os cortes atuais, se ainda couberem, ou novos cortes. Se a Transcrição inteira cabe, segue com Parte única, como no critério 19 (Q65).
23. "Preparar geração" no modo `normal`, numa Reunião em `done`, segue as mesmas regras dos critérios 19 a 21.
24. Os Participantes e a Transcrição não mudam em nenhuma checagem.

### Texto da Parte

25. "Texto da Parte" monta uma linha por segmento, na ordem, com o instante absoluto de início em `hh:mm:ss`, o nome do Participante ligado ao speaker do segmento e o texto.
26. O texto de uma Parte que começa no meio da gravação mostra os instantes absolutos, não instantes relativos ao início da Parte.
27. Depois de uma renomeação de Participante, o "Texto da Parte" usa o nome novo.

### Isolamento e autenticação

28. `GET`, `PUT`, `refresh` e `cancel` em `/meetings/{id}/split` com o `id` de uma Reunião de outro Usuário respondem HTTP 404, e nada muda.
29. Requisição sem autenticação às rotas deste módulo recebe HTTP 401.

### Frontend

30. O detalhe de uma Reunião em `needs_split` leva à tela de divisão.
31. A tela explica por que a divisão é necessária. Ela mostra a estimativa da Transcrição, o orçamento, o provedor e o modelo ativos, e um link para a tela de configurações, para quem preferir trocar de modelo.
32. A tela mostra os segmentos em ordem, com instante e nome do Participante, e os cortes sugeridos já marcados.
33. O usuário move um corte para o fim de outro segmento, adiciona um corte no fim de qualquer segmento e remove um corte. A tela não oferece corte no meio de um segmento.
34. A cada mudança, a tela mostra, para cada Parte, o intervalo de tempo, a estimativa de tokens e se cabe.
35. O botão "Confirmar" fica desabilitado enquanto alguma Parte não couber.
36. Depois de confirmar, o frontend leva o usuário ao detalhe da Reunião, onde o status passa a ser acompanhado.

### Substituição das Partes

37. Toda gravação de Partes apaga todas as Partes anteriores da Reunião e grava as novas numa só transação. Vale para a Parte única (critérios 1 e 19) e para o `PUT` (critério 12). Depois da gravação, a interface "Partes" devolve só as Partes novas.
38. Enquanto não há nova gravação, as Partes anteriores continuam gravadas. Entrar em `needs_split` não as apaga, e o reaproveitamento do critério 20 não as regrava.

### Saídas de `needs_split` (Q59, Q68)

39. `POST /meetings/{id}/split/cancel` numa Reunião em `needs_split` com backlog gravado leva a Reunião a `done`, qualquer que seja o `split_reason`. O backlog anterior e as Partes anteriores não mudam, e nenhum aviso é emitido.
40. `POST /meetings/{id}/split/cancel` numa Reunião fora de `needs_split`, ou sem backlog gravado, responde HTTP 409, e nada muda.
41. `PUT /meetings/{id}/split` sem provedor ativo leva a Reunião a `failed` com etapa `generation` e mensagem que aponta para a tela de configurações. Nada é gravado, e nenhum aviso é emitido.
42. `PUT /meetings/{id}/split` em que um segmento sozinho passa do orçamento do provedor ativo atual leva a Reunião a `failed` com etapa `generation` e a mensagem do critério 6. Nada é gravado, e nenhum aviso é emitido.
43. A regra "passou a caber" roda em `POST /meetings/{id}/split/refresh`, que o frontend chama ao abrir a tela de divisão, e em `PUT /meetings/{id}/split`, ao confirmar (Q66, Q70, ADR-0019):
    - Numa Reunião em `needs_split` cuja Transcrição inteira passou a caber no orçamento do provedor ativo atual, os dois gravam uma Parte única, levam a Reunião a `generating` e emitem "Partes prontas" uma única vez.
    - Nesse caso, o `POST .../refresh` responde com o mesmo corpo do `GET`, com o novo status e sem cortes. O `PUT` ignora os cortes enviados.
    - Se a Transcrição ainda não cabe inteira, o `POST .../refresh` não grava nada, não muda o status, não emite aviso e responde como o `GET`.
    - `GET /meetings/{id}/split` só lê: não grava Parte, não muda o status e não emite aviso, mesmo quando a Transcrição passou a caber.
44. `GET /meetings/{id}/split` e `POST /meetings/{id}/split/refresh` sem provedor ativo respondem com a mensagem que aponta para a tela de configurações, sem orçamento e sem cortes sugeridos. Nada muda, e a Reunião continua em `needs_split` (Q67).
45. A tela de divisão mostra o botão "Cancelar divisão" só quando a resposta do `GET` indica que a Reunião tem backlog gravado. Depois de cancelar, o frontend volta à revisão do backlog.

### Avisos fora de hora

46. Um aviso "Participantes confirmados" ou "Nova tentativa" (etapa `generation`) recebido com a Reunião fora de `transcribed` é ignorado: nenhuma checagem roda, nenhuma Parte é gravada, nenhum aviso é emitido e o status não muda.

### Frontend: abertura da tela (Q70, ADR-0019)

47. Ao abrir a tela de divisão de uma Reunião em `needs_split`, o frontend chama `POST /meetings/{id}/split/refresh` antes de mostrar os cortes. Se a resposta traz status `generating`, o frontend leva o usuário ao detalhe da Reunião, como no critério 36, sem mostrar a tela de cortes.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, Reuniões montadas no setup com segmentos, Participantes e marcas fake. Fakes:
  - "Provedor ativo" (com e sem provedor, janelas diferentes);
  - "Estimar tokens", determinístico, por exemplo um token por caractere;
  - consumidores dos avisos.

  Cobre critérios 1 a 29, 37 a 44 e 46, um teste por critério. O critério 43 inclui um teste que chama o `GET` com a Transcrição cabendo e confere que o banco não mudou.
- **Avisos e regeneração:** avisos de entrada e "Preparar geração" disparados no próprio teste.
- **Frontend (critérios 30 a 36, 45 e 47):** Vitest + React Testing Library + MSW. Resolvido: ADR-0015.
- **Performance (01-prd, NFR-04 e NFR-07):** INP e virtualização da lista de segmentos medidos com Transcrição de 2 h de fixture.

## Questões em aberto

1. Respondidas pelo planner:
   - reserva do orçamento: System Prompt, Participantes, 1.000 tokens para nomes de Epics, resposta e margem de 5%. Resolvido: ADR-0011.
   - onde o System Prompt mora, sem ciclo com `backlog-generation`: módulo `shared/prompts`. Resolvido: ADR-0020.
   - estimativa de tokens: heurística aditiva por linha, em `llm-providers`. Resolvido: ADR-0011.
   - desempenho ao mover cortes: `GET /meetings/{id}/split` devolve a estimativa por segmento, e o cliente soma; o `PUT` revalida no servidor. Resolvido: ADR-0011 e `02-architecture.md`, "Divisão".
2. Códigos HTTP 404, 409 e 422 e endpoints são sugestões, não decisões.
