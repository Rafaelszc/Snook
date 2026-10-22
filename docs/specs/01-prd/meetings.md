# 01-prd/meetings - PRD do módulo `meetings`

> Status: completo. Decisões fechadas: Q6, Q7, Q8, Q19, Q25, Q26, Q40, Q41, Q45, Q53, Q54, Q56, Q58, Q59, Q60, Q61, Q68, Q69, Q70 (ADR-0018, LGPD), Q71, Q72.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`. Rotas sem o prefixo `/api` (ver `01-prd.md`, "Convenção de rotas").
> Depende de: `auth`. Dependentes: `screen-recording`, `diarized-transcription`, `participants`, `transcript-split`, `backlog-generation` e `backlog-review`.

## Problem Statement

- Usuário tem gravação de reunião e precisa pôr no app para virar backlog.
- Precisa saber na hora se o arquivo serve. Não quer descobrir formato ou tamanho errado só no processamento.
- Depois, precisa:
  - achar reuniões pelo nome dado;
  - ver a etapa de cada uma;
  - tentar de novo quando algo falha;
  - apagar as que não quer mais, inclusive o áudio.

## Solution

- Upload de áudio com título opcional (pré-preenchido com nome do arquivo) e número opcional de participantes.
- Tela de upload lembra o Usuário de obter o consentimento dos participantes (LGPD).
- App confere formato, tamanho e duração na hora. Guarda arquivo em `/audios`. Cria Reunião em `pending`.
- Resposta volta antes do processamento.
- Lista mostra título, data de envio e status, atualizado sozinho.
- Detalhe permite editar título. Em falha, mostra motivo e "Tentar novamente", que retoma da etapa que falhou.
- Backend reinicia no meio do processamento: Reunião vai para `failed` com "processamento interrompido".
- Excluir Reunião apaga arquivo e tudo que derivou dela.

## User Stories

1. Como usuário, quero enviar um arquivo mp3, wav, m4a, ogg, webm ou mp4, para que a reunião seja processada.
2. Como usuário, quero dar um título à reunião no envio, já preenchido com o nome do arquivo, para reconhecê-la depois sem esforço.
3. Como usuário, quero editar o título de uma reunião já enviada, para corrigir ou detalhar o nome.
4. Como usuário, quero informar, de forma opcional, quantas pessoas participaram, para melhorar a separação das vozes.
5. Como usuário, quero saber na hora por que um arquivo foi recusado (formato, tamanho, duração ou arquivo sem áudio), para corrigir e enviar de novo.
6. Como usuário, quero que o envio termine sem esperar a transcrição, para continuar usando o app enquanto a reunião é processada.
7. Como usuário, quero ver a lista das minhas reuniões, mais recentes primeiro, com título, data, duração e status, para achar a que procuro.
8. Como usuário, quero que o status mude na tela sem recarregar a página, para acompanhar o processamento.
9. Como usuário, quero ver o motivo quando uma reunião falha, para saber o que aconteceu.
10. Como usuário, quero tentar novamente uma reunião que falhou, retomando da etapa que falhou, para não reenviar o arquivo nem refazer o que já deu certo.
11. Como usuário, quero que uma reunião interrompida por um reinício do app (transcrevendo, gerando, ou com os nomes já confirmados esperando a geração) apareça como falha, com "Tentar novamente", para não ficar presa num status que nunca muda.
12. Como usuário, quero excluir uma reunião, com confirmação, para apagar o áudio e tudo o que foi gerado a partir dele.
13. Como usuário, quero que outros usuários não vejam nem alterem minhas reuniões, para proteger o conteúdo.
14. Como módulo do sistema (`screen-recording`), quero criar uma Reunião pela mesma regra do upload, para que a gravação de tela siga o mesmo caminho.
15. Como módulo do sistema (`diarized-transcription` e seguintes), quero ser avisado de cada Reunião criada e de cada nova tentativa, e atualizar o status dela, para tocar o processamento.
16. Como módulo do sistema (`transcript-split`, `backlog-review`), quero saber se a Reunião tem Participantes confirmados e backlog gravado, sem depender dos módulos donos desses dados, para aplicar as regras de status.
17. Como usuário, quero ser lembrado na tela de upload de obter o consentimento dos participantes antes de enviar a gravação, para cumprir a LGPD.

## Escopo

- Upload com título opcional e número opcional de participantes (1 a 20).
- Aviso de consentimento dos participantes (LGPD) na tela de upload (Q70, Q72).
- Validação de extensão, conteúdo de áudio, tamanho e duração antes de criar a Reunião, inclusive webm do `MediaRecorder` (Q61).
- Arquivo em `/audios`.
- Listagem, detalhe, edição de título e exclusão das Reuniões do próprio Usuário.
- Status, etapa que falhou e mensagem de erro, com interface interna para os outros módulos atualizarem.
- Marcas de Participantes confirmados e de backlog gravado, registradas pelos módulos donos e expostas no detalhe como `participants_confirmed` e `has_backlog`.
- "Tentar novamente" em `failed` (Q54).
- Marcação de processamentos interrompidos ao subir o backend (Q58, Q69).
- Avisos "Reunião criada" e "Nova tentativa".
- Telas de upload, lista e detalhe.

Endpoints sugeridos (planner confirma): `POST /meetings` (multipart, campos `file`, `title` opcional e `expected_speakers` opcional), `GET /meetings`, `GET /meetings/{id}`, `PATCH /meetings/{id}` (título), `POST /meetings/{id}/retry`, `DELETE /meetings/{id}`.

Campos sugeridos da Reunião: `id`, `user_id`, `title`, `original_filename`, `duration_seconds`, `size_bytes`, `expected_speakers`, `status`, `failed_stage`, `error_message`, `participants_confirmed_at`, `backlog_saved_at`, `created_at`, `updated_at`. Data da Reunião é `created_at`, a data de envio (Q53). Caminho do arquivo é interno e não sai na API. API expõe as marcas só como booleanos: `participants_confirmed` (de `participants_confirmed_at`) e `has_backlog` (de `backlog_saved_at`).

## Fora de escopo

- Gravação de tela. Fica em `screen-recording`, que usa a criação de Reunião deste módulo.
- Tratamento de áudio, diarização e transcrição. Ficam em `diarized-transcription`.
- Limite de Reuniões processando ao mesmo tempo por Usuário. Fica em `diarized-transcription` (Q60, Q62).
- Reprocessar áudio de Reunião que não falhou (Q43).
- Retomar sozinho, após reinício, processamento interrompido (Q58).
- Data da reunião diferente da data de envio (Q53).
- Tocar ou baixar o áudio inteiro pela UI.
- Guardar prova do consentimento dos participantes. O aviso só lembra o Usuário; obter o consentimento cabe a ele (`03-security.md`, "Privacidade (LGPD)").

## Restrições

| Restrição | Fonte |
|---|---|
| Formatos mp3, wav, m4a, ogg, webm e mp4 (do mp4, só o áudio interessa). | rodada 1, Q6 |
| Máximo de 2 h de duração e 500 MiB (524.288.000 bytes) de tamanho. Mensagem ao usuário diz "500 MB". | rodada 1, Q6; Q70 (ADR-0018) |
| Arquivo recebido em streaming, sem carregar o arquivo inteiro na memória. | Q70 (ADR-0018) |
| Arquivo em `/audios`, mapeado para `./audios` no host, fora do git. | rodadas 1, 2 e 4, Q7, Q25 e Q41 |
| Arquivo guardado até a exclusão da Reunião; a exclusão apaga o arquivo. | rodada 2, Q25 |
| Processamento assíncrono, status consultado por polling. | rodada 1, Q8 |
| Status: `pending`, `processing`, `transcribed`, `needs_split`, `generating`, `done`, `failed`. | rodadas 1 e 5, Q8 e Q45 |
| Campo opcional de número de participantes no upload, de 1 a 20. | rodada 2, Q26; Q70 (`05-api.md`) |
| Aviso de consentimento dos participantes (LGPD) na tela de upload, com o texto literal da Q72. | Q70 (`03-security.md`, LGPD); Q72 |
| Campo `title` opcional no upload e na gravação, pré-preenchido com o nome do arquivo, editável depois (em qualquer status); data da Reunião é a data de envio. | Q53, Q56 |
| "Tentar novamente" em `failed`, retomando da etapa que falhou: falha na transcrição ou diarização reprocessa o áudio; falha na geração reaproveita a Transcrição e os nomes dos speakers e chama a LLM de novo. | Q54 |
| Validação no navegador antes do envio e confirmação antes de excluir. | Q56 |
| Ao subir o backend, `processing` vai para `failed` (etapa `transcription`) e `generating` vai para `failed` (etapa `generation`), com "processamento interrompido". | Q58 |
| Ao subir o backend, `transcribed` com Participantes confirmados vai para `failed` (etapa `generation`), com "processamento interrompido". | Q69 |
| Saídas de `needs_split`: `done` ("Cancelar divisão", sempre que há backlog gravado) e `failed` (etapa `generation`), disparadas por `transcript-split`. | Q59, Q68 |
| A leitura de duração funciona com o webm do `MediaRecorder`, cujo cabeçalho não traz a duração. | Q61 |
| Cada Usuário vê e altera só as próprias Reuniões; Reunião de outro Usuário responde como inexistente. | rodada 2, Q19 |
| SQLite num volume Docker nomeado, fora do git. | rodadas 3 e 4, Q33 e Q40 |
| FastAPI, SQLite, Pytest, React + TypeScript + shadcn/ui. | briefing |

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Criar Reunião**: recebe Usuário, arquivo, nome original, `title` opcional e `expected_speakers` opcional. Aplica as validações do upload. Devolve a Reunião ou o motivo da recusa. `POST /meetings` e `screen-recording` usam a mesma função.
- **Reunião criada**: após gravar a Reunião, avisa o pipeline uma única vez, com o `id`. `diarized-transcription` consome. Mecanismo: fila em processo, publicada depois do commit, com `run_id` (ADR-0007).
- **Nova tentativa**: ao aceitar "Tentar novamente", avisa o pipeline uma única vez, com `id` e etapa que falhou. `diarized-transcription` consome etapa `transcription`. `transcript-split` consome etapa `generation`. Aviso evita que `meetings` dependa desses módulos (sem ciclo).
- **Ler arquivo**: dado o `id`, devolve caminho interno do arquivo. Só para módulos de backend.
- **Atualizar status**: dado `id` e status, grava o novo status. Para `failed`, exige etapa (`transcription` ou `generation`) e mensagem. Valor fora da lista ou transição fora da tabela: recusado.
- **Registrar Participantes confirmados**: `participants` chama na mesma transação da confirmação dos nomes. Módulo grava `participants_confirmed_at`. Marca nunca é apagada, exceto com a Reunião.
- **Registrar backlog gravado**: `backlog-generation` chama na mesma transação em que grava backlog com sucesso. Módulo grava `backlog_saved_at`. Marca nunca é apagada, exceto com a Reunião.
- **Ler marcas**: dado o `id`, informa se há Participantes confirmados e se há backlog gravado. `transcript-split` e `backlog-review` usam. Frontend lê as mesmas marcas em `GET /meetings/{id}` (`participants_confirmed`, `has_backlog`). Com as marcas aqui, nenhum módulo depende de quem está mais abaixo na cadeia.
- **Marcar interrompidas**: roda uma vez ao subir o backend, antes de aceitar requisições e antes de qualquer worker consumir avisos. Leva a `failed`, com mensagem "processamento interrompido":
  - toda Reunião em `processing`, com etapa `transcription` (Q58);
  - toda Reunião em `generating`, com etapa `generation` (Q58);
  - toda Reunião em `transcribed` com Participantes confirmados, com etapa `generation` (Q69). Cobre aviso "Participantes confirmados" ou "Nova tentativa" ainda não consumido.
- **Aviso de consentimento**: componente de tela compartilhado com `screen-recording` (`ConsentNotice`, `02-architecture.md`). O texto vem de uma constante única do frontend, usada nas duas telas (Q72).

Transições previstas:

| De | Para | Quem dispara |
|---|---|---|
| `pending` | `processing` | `diarized-transcription` |
| `processing` | `transcribed`, ou `failed` com etapa `transcription` | `diarized-transcription` |
| `processing` | `failed` com etapa `transcription` ("processamento interrompido") | `meetings`, ao subir o backend (Q58) |
| `transcribed` | `generating`, `needs_split`, ou `failed` com etapa `generation` | `transcript-split` |
| `transcribed` com Participantes confirmados | `failed` com etapa `generation` ("processamento interrompido") | `meetings`, ao subir o backend (Q69) |
| `needs_split` | `generating` (cortes confirmados, ou Transcrição que passou a caber inteira, Q59 c) | `transcript-split` |
| `needs_split` com backlog gravado | `done` ("Cancelar divisão", sem mudar nada, Q59 a e Q68) | `transcript-split` |
| `needs_split` | `failed` com etapa `generation` (sem provedor ativo, ou segmento sozinho maior que o orçamento, na confirmação, Q59 b) | `transcript-split` |
| `generating` | `done`, ou `failed` com etapa `generation` | `backlog-generation` |
| `generating` | `failed` com etapa `generation` ("processamento interrompido") | `meetings`, ao subir o backend (Q58) |
| `done` | `generating`, `needs_split`, ou `failed` com etapa `generation` (regeneração, Q50) | `transcript-split`, a pedido de `backlog-review` |
| `failed` (etapa `transcription`) | `pending` | `meetings`, no "Tentar novamente" (Q54) |
| `failed` (etapa `generation`) | `transcribed` | `meetings`, no "Tentar novamente" (Q54); em seguida, `transcript-split` refaz a checagem |

- Tentativa da etapa `generation`: Reunião volta a `transcribed` com Transcrição e Participantes intactos. `transcript-split` refaz a checagem, porque o provedor ativo pode ter mudado. Reaproveitamento das Partes: PRD de `transcript-split`.
- Regeneração também passa por `transcript-split`, que decide entre `generating` e `needs_split`.
- **Exclusão em cascata**: excluir Reunião remove todos os dados derivados de outros módulos (Transcrição, áudio tratado, Participantes, Partes, Epics, User Stories, critérios). Cada módulo dono liga as próprias tabelas à Reunião para a exclusão removê-las.

## Critérios de aceite

### Upload válido

1. `POST /meetings` com um arquivo válido de cada formato (mp3, wav, m4a, ogg, webm, mp4 com trilha de áudio) responde HTTP 201 com `id`, `title`, `original_filename`, `duration_seconds`, `created_at` e `status` igual a `pending`.
2. Após o upload válido, existe um arquivo em `/audios` com o mesmo conteúdo enviado, e a Reunião aponta para ele.
3. O upload com `title` grava o título informado, sem espaços nas pontas.
4. O upload sem `title`, ou com `title` só de espaços, grava como título o nome original do arquivo.
5. O upload com `expected_speakers` inteiro de 1 a 20 grava o valor. Sem o campo, `expected_speakers` fica vazio.
6. O aviso "Reunião criada" é emitido uma única vez por upload válido, com o `id` da Reunião.
7. A resposta do upload chega sem esperar o processamento: com um consumidor fake que nunca termina, `POST /meetings` ainda responde HTTP 201.
8. Um arquivo de exatamente 2 h é aceito.

### Upload recusado

Em todos os casos abaixo: nenhuma Reunião criada, nenhum arquivo fica em `/audios`, nenhum aviso emitido.

9. Arquivo com extensão fora da lista (por exemplo `.flac` ou `.txt`) é recusado com HTTP 422 e mensagem que lista os formatos aceitos.
10. Arquivo com extensão aceita, mas sem trilha de áudio legível (por exemplo um `.mp3` que é texto, ou um `.mp4` só com vídeo), é recusado com HTTP 422 e mensagem "arquivo sem áudio".
11. Arquivo com mais de 2 h é recusado com HTTP 422 e mensagem sobre o limite de duração.
12. Arquivo com mais de 524.288.000 bytes (500 MiB) é recusado com HTTP 413 e mensagem sobre o limite de tamanho, que diz "500 MB". Um arquivo de exatamente 524.288.000 bytes não é recusado por tamanho (ADR-0018).
13. Arquivo vazio é recusado com HTTP 422.
14. `expected_speakers` igual a 0, negativo, maior que 20 ou não inteiro é recusado com HTTP 422.
15. Extensão em maiúsculas (por exemplo `.MP3`) é tratada como a minúscula correspondente.

### Título

16. `PATCH /meetings/{id}` com novo `title` grava o título, sem espaços nas pontas, e não muda o status nem os demais campos.
17. `PATCH /meetings/{id}` com `title` vazio ou só de espaços é recusado com HTTP 422, e o título anterior não muda.
18. O título pode ser editado em qualquer status.

### Listagem e detalhe

19. `GET /meetings` devolve só as Reuniões do Usuário autenticado, da mais recente para a mais antiga, cada uma com `id`, `title`, `created_at`, `duration_seconds` e `status`.
20. `GET /meetings/{id}` devolve os campos da listagem mais `original_filename`, `expected_speakers` e os booleanos `participants_confirmed` e `has_backlog`, verdadeiros quando `participants_confirmed_at` e `backlog_saved_at` estão preenchidos. Quando o status é `failed`, devolve também `failed_stage` e `error_message`.
21. Nenhuma resposta de `/meetings` expõe o caminho interno do arquivo.
22. Depois que outro módulo atualiza o status pela interface "Atualizar status", `GET /meetings/{id}` devolve o novo status.
23. A interface "Atualizar status" recusa um valor fora da lista de status, uma transição fora da tabela do contrato e um `failed` sem etapa ou sem mensagem. Nesses casos, o status gravado não muda.

### Tentar novamente

24. `POST /meetings/{id}/retry` numa Reunião em `failed` com etapa `transcription` leva a Reunião a `pending`, limpa `failed_stage` e `error_message` e emite o aviso "Nova tentativa" com a etapa `transcription`, uma única vez.
25. `POST /meetings/{id}/retry` numa Reunião em `failed` com etapa `generation` leva a Reunião a `transcribed`, limpa `failed_stage` e `error_message`, mantém Transcrição e Participantes intactos e emite o aviso "Nova tentativa" com a etapa `generation`, uma única vez.
26. `POST /meetings/{id}/retry` numa Reunião fora de `failed` é recusado com HTTP 409, e nada muda.
27. Nenhuma das duas tentativas pede novo envio do arquivo, e o arquivo original em `/audios` não muda.

### Exclusão

28. `DELETE /meetings/{id}` responde HTTP 204. Depois disso, `GET /meetings/{id}` responde HTTP 404 e o arquivo não existe mais em `/audios`.
29. A exclusão remove os dados derivados da Reunião: com registros fake de Transcrição e de User Story ligados a ela, nenhum deles resta depois da exclusão.
30. A exclusão funciona em qualquer status. Um processamento em andamento não recria a Reunião, o arquivo nem dados derivados depois da exclusão.

### Isolamento e autenticação

31. `GET`, `PATCH`, `retry` e `DELETE` com o `id` de uma Reunião de outro Usuário respondem HTTP 404, e a Reunião do outro Usuário continua intacta.
32. A listagem de um Usuário não inclui Reuniões de outro Usuário.
33. Requisição sem autenticação a qualquer rota de `/meetings` recebe HTTP 401.

### Persistência

34. Após `docker compose down` (sem `-v`) e `docker compose up`, as Reuniões e os arquivos em `./audios` continuam disponíveis.

### Frontend

35. A tela de upload aceita a escolha de um arquivo, o título e o número opcional de participantes, e mostra que o envio está em andamento.
36. Ao escolher o arquivo, o campo de título é preenchido com o nome do arquivo, e o usuário pode alterá-lo antes de enviar.
37. A tela de upload recusa, antes de enviar, arquivo com extensão fora da lista ou com mais de 524.288.000 bytes, com a mesma mensagem da API.
38. Erros devolvidos pela API no upload aparecem na tela.
39. Após o upload, o frontend leva o usuário ao detalhe da nova Reunião.
40. A lista e o detalhe atualizam o status sozinhos, sem recarregar a página, enquanto a Reunião está em `pending`, `processing` ou `generating`, ou em `transcribed` com `participants_confirmed` igual a verdadeiro.
41. O detalhe permite editar o título.
42. O detalhe de uma Reunião em `failed` mostra a mensagem de erro e um botão "Tentar novamente". O botão não aparece em outros status. Quando `has_backlog` é verdadeiro em `GET /meetings/{id}`, o botão pede confirmação com o mesmo aviso da regeneração: as edições manuais do backlog se perdem se a nova geração terminar bem.
43. Excluir uma Reunião pede confirmação na tela e avisa que o áudio e o backlog serão apagados.

### Reinício (Q58, Q69)

44. Com Reuniões gravadas em `processing` e em `generating` antes de um reinício, ao subir o backend a primeira vai para `failed` com etapa `transcription` e a segunda para `failed` com etapa `generation`, ambas com `error_message` igual a "processamento interrompido".
45. A marcação dos critérios 44 e 49 termina antes de o backend aceitar requisições, e nenhum aviso é emitido por ela.
46. Depois da marcação, `POST /meetings/{id}/retry` funciona nessas Reuniões como nos critérios 24 e 25.

### Webm do `MediaRecorder` (Q61)

47. Um arquivo webm só de áudio, gerado pelo `MediaRecorder` e sem duração no cabeçalho, é aceito, e `duration_seconds` recebe a duração real do áudio, com erro máximo de 1 s.
48. Um webm desse tipo com mais de 2 h é recusado como no critério 11.

### Reinício com nomes confirmados (Q69)

49. Com uma Reunião gravada em `transcribed` e com Participantes confirmados antes de um reinício, ao subir o backend ela vai para `failed` com etapa `generation` e `error_message` igual a "processamento interrompido".
50. Ao subir o backend, Reuniões em `transcribed` sem Participantes confirmados, e Reuniões em `pending`, `needs_split`, `done` e `failed`, não mudam.

### Marcas

51. Depois de "Registrar Participantes confirmados" e de "Registrar backlog gravado", "Ler marcas" informa as duas marcas, e `GET /meetings/{id}` devolve `participants_confirmed` e `has_backlog` iguais a verdadeiro. Elas continuam depois de "Tentar novamente", de uma regeneração e de um reinício.

### Aviso de consentimento (Q70, Q71, Q72, LGPD)

52. A tela de upload mostra o aviso de consentimento dos participantes junto do botão de envio, visível antes de o usuário enviar o arquivo. O aviso exibe exatamente este texto (Q72): "Antes de gravar ou enviar, obtenha o consentimento de todos os participantes da reunião (LGPD). O áudio fica só neste servidor; o texto da transcrição vai ao provedor de LLM ativo." O texto vem de uma constante única do frontend, a mesma usada na tela de gravação (`screen-recording`, critério 26). Os testes das duas telas comparam o texto exibido com essa constante. O aviso é só texto: não pede confirmação nem bloqueia o envio (Q71).

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, pasta `/audios` temporária, consumidores fake dos avisos "Reunião criada" e "Nova tentativa". Cobre critérios 1 a 33 e 44 a 51, um teste por critério.
- **Arquivos de teste:** áudios curtos de cada formato como fixtures (gerados no setup ou versionados, a critério do planner). Critérios 47 e 48 usam fixture webm gravada pelo próprio gravador de `screen-recording`, sem duração no cabeçalho.
- **Limites (critérios 8, 11, 12 e 48):** leitura de duração atrás de interface; teste simula 2 h e 2 h e 1 s sem arquivos grandes. Limite de tamanho testado com arquivo pequeno e limite reduzido por configuração de teste (`UPLOAD_MAX_BYTES`, ADR-0018), no valor exato e um byte acima. Pelo menos um teste usa leitura real de duração com fixture curta.
- **`expected_speakers` (critérios 5 e 14):** valores 1, 20, 0, 21, -1 e `2.5`.
- **Reinício (critérios 44 a 46, 49 e 50):** teste grava Reuniões nos status e marcas iniciais direto no SQLite de teste e sobe o app de novo com `TestClient`.
- **Persistência (critério 34):** verificação manual ou teste de integração com Docker, fora do `pytest` padrão.
- **Frontend (critérios 35 a 43 e 52):** Vitest + React Testing Library + MSW. Resolvido: ADR-0015. Critério 52: o teste da tela de upload compara o texto exibido com a constante do aviso.

## Questões em aberto

1. Q71 fechada em 2026-10-22: aviso é só texto visível, sem confirmação obrigatória. Q72 fechada em 2026-10-22: texto literal do aviso (critério 52).
2. Respondidas pelo planner:
   - mecanismo dos avisos "Reunião criada" e "Nova tentativa": fila em processo, publicada depois do commit. Resolvido: ADR-0007. Concorrência entre Reuniões: ADR-0007 e ADR-0010.
   - Reuniões em `pending` após reinício: reenfileiradas no startup, em ordem de criação. Resolvido: ADR-0007.
   - aviso velho depois de "Marcar interrompidas": fila não durável, e cada aviso leva `run_id`; consumidor ignora `run_id` que não bate. Resolvido: ADR-0007.
   - transação de "Registrar Participantes confirmados" e "Registrar backlog gravado": unidade de trabalho compartilhada, um commit. Resolvido: ADR-0006.
   - processamento em andamento quando a Reunião é excluída (critério 30): gravação final falha por Reunião ausente, e o resultado é descartado. Resolvido: `02-architecture.md`, "Exclusão".
   - nome do arquivo em `/audios`: `/audios/<meeting_id>/original.<ext>`, com `meeting_id` UUID do servidor. Resolvido: ADR-0014 e ADR-0018.
   - leitura de duração e trilhas: `ffprobe`, com leitura do último pacote quando o webm não traz duração. Resolvido: ADR-0014.
   - tamanho máximo do título: 200 caracteres. Resolvido: `05-api.md`.
   - intervalo de polling: 3 s, só nos status ativos (`VITE_POLL_INTERVAL_MS`). Resolvido: ADR-0015.
3. Resolvidas pelo ADR-0018: definição de 500 MB (500 MiB, 524.288.000 bytes) e recepção sem carregar o arquivo inteiro na memória (streaming).
4. Códigos HTTP 201, 204, 404, 409, 413 e 422 e endpoints são sugestões, não decisões. Planner pode ajustar, desde que o critério continue verificável.
