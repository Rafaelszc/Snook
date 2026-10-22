# 01-prd/diarized-transcription - PRD do módulo `diarized-transcription`

> Status: completo. Decisões fechadas: Q3, Q4, Q5, Q8, Q13, Q17, Q25, Q26, Q43, Q54, Q56, Q58, Q60, Q62.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: `meetings` (avisos, arquivo, status) e `auth` (rota da Transcrição). Dependentes: `participants` e `transcript-split`.

## Problem Statement

- Após enviar a gravação, usuário precisa do texto separado por quem falou, para saber quem pediu cada coisa.
- Fazer à mão leva horas.
- Áudio chega em vários formatos e qualidades. Usuário não quer prepará-lo.
- Áudio é sensível: não deve sair do servidor.

## Solution

- Reunião criada: servidor trata o áudio sozinho, separa vozes com Pyannote e transcreve em pt-BR com Whisper. Tudo local.
- Resultado: Transcrição em segmentos, cada um com speaker, início, fim e texto.
- Status: `pending`, depois `processing`, depois `transcribed`.
- Cada Usuário tem limite de Reuniões processando ao mesmo tempo. As que passam do limite esperam a vez em `pending`.
- Falha: Reunião vai para `failed` com motivo legível. "Tentar novamente" reprocessa o áudio original.
- Tela própria mostra a Transcrição em ordem, com tempo de cada fala.

## User Stories

1. Como usuário, quero que a transcrição comece sozinha depois do envio, para não precisar de outro passo.
2. Como usuário, quero que o áudio seja tratado sem ação minha, para não converter nem limpar o arquivo antes de enviar.
3. Como usuário, quero que as falas sejam separadas por voz, para saber quem disse cada trecho.
4. Como usuário, quero que o número de participantes que informei seja usado na separação das vozes, para melhorar o resultado.
5. Como usuário, quero que a transcrição seja em pt-BR, para que o texto saia certo na língua da reunião.
6. Como usuário, quero que o áudio nunca saia do servidor durante a transcrição, para proteger o conteúdo da reunião.
7. Como usuário, quero ver um motivo legível quando a transcrição falha, para saber se o problema é no arquivo ou na configuração.
8. Como usuário, quero que "Tentar novamente" refaça a transcrição a partir do áudio original, para não reenviar o arquivo.
9. Como usuário, quero ver a transcrição em ordem, com o tempo e o speaker de cada fala, para conferir o que foi dito.
10. Como usuário, quero que minhas reuniões extras esperem a vez quando já tenho reuniões em processamento, para não travar a máquina.
11. Como operador, quero que os modelos fiquem em cache num volume, para não baixá-los a cada reinício e para transcrever sem internet.
12. Como operador, quero usar GPU NVIDIA quando houver, e CPU quando não houver, para rodar em qualquer máquina.
13. Como módulo do sistema (`participants`), quero ler os segmentos e o áudio tratado de uma Reunião, para montar a amostra de cada speaker.
14. Como módulo do sistema (`transcript-split`), quero ler os segmentos de uma Reunião em ordem, para checar o tamanho e montar o texto enviado à LLM.

## Escopo

- Consumo dos avisos "Reunião criada" e "Nova tentativa" (etapa `transcription`) de `meetings`.
- Status: `pending` para `processing`; depois `transcribed` ou `failed` com etapa `transcription`.
- Limite de Reuniões em `processing` ao mesmo tempo por Usuário (Q60), com espera em `pending` (Q62).
- Tratamento automático do áudio (quais tratamentos: planner).
- Diarização com Pyannote; `expected_speakers` como dica quando informado.
- Transcrição com Whisper, idioma fixo pt-BR.
- Junção das saídas em segmentos com speaker, início, fim e texto.
- Persistência da Transcrição e do áudio tratado.
- Consulta da Transcrição pela API e tela da Transcrição.
- Cache dos modelos num volume Docker; CPU por padrão, GPU opcional.

Endpoint sugerido (planner confirma): `GET /meetings/{id}/transcript`.

Campos sugeridos de cada segmento: `id`, `meeting_id`, `speaker_label`, `start_seconds`, `end_seconds`, `text`.

## Fora de escopo

- Nomes dos speakers e amostras de voz. Ficam em `participants`.
- Checagem de janela de contexto e divisão em Partes. Ficam em `transcript-split`.
- Editar o texto da Transcrição.
- Outros idiomas além de pt-BR (Q3).
- Reprocessar áudio de Reunião que não falhou (Q43).
- Retomar sozinho, após reinício, transcrição interrompida. `meetings` leva a Reunião a `failed` ao subir (Q58).
- Recusar envio quando o Usuário já está no limite de processamento (Q62).
- Reconhecer a mesma voz entre Reuniões diferentes.
- Metas de tempo de processamento (ainda não definidas).

## Restrições

| Restrição | Fonte |
|---|---|
| Transcrição com Whisper; diarização com Pyannote. | briefing |
| Whisper transcreve só pt-BR. | rodada 1, Q3 |
| Whisper roda localmente. | rodada 1, Q4 |
| CPU por padrão; GPU NVIDIA opcional via perfil do `docker compose`. | rodada 1, Q5 |
| Processamento assíncrono; status consultado por polling. | rodada 1, Q8 |
| O sistema faz todas as edições e tratamentos de áudio necessários. | rodada 1, Q13 (resposta) |
| `HF_TOKEN` no `.env`; modelos do Pyannote em cache num volume Docker. | rodada 1, Q17 |
| O usuário ouve um trecho da voz de cada speaker já tratado. | rodada 1, Q9 e Q10 |
| Arquivo original guardado até a exclusão da Reunião. | rodada 2, Q25 |
| Número de participantes opcional como dica. | rodada 2, Q26 |
| O áudio não é reprocessado para dividir uma Reunião longa. | rodada 4, Q43 |
| Falha na transcrição ou diarização: "Tentar novamente" reprocessa o áudio. | Q54 |
| Trecho fora de qualquer turno vai para o speaker mais próximo; áudio sem fala leva a `failed`. | Q56 |
| Reinício no meio do processamento: `meetings` leva a Reunião a `failed` (etapa `transcription`). | Q58 |
| Limite de Reuniões processando ao mesmo tempo por Usuário (valor com o planner). | Q60 |
| Reunião acima do limite espera em `pending`, sem recusa. | Q62 |
| O áudio não sai do servidor; com modelos em cache, funciona sem internet. | 01-prd, RT-06 e critério transversal 14 |
| Pytest sem GPU, sem rede e sem modelos, com fakes. | rodada 2, Q32; 01-prd, RT-13 |

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Consome** de `meetings`: "Reunião criada" e "Nova tentativa" com etapa `transcription`. Avisos só agem com a Reunião em `pending`; fora disso, ignorados. Usa "Ler arquivo" para o áudio original. Usa "Atualizar status" para `pending` → `processing`, `processing` → `transcribed` e `processing` → `failed` com etapa `transcription`.
- **Segmentos**: dado o `id` da Reunião, devolve segmentos em ordem de início. Só existe a partir de `transcribed`.
- **Speakers**: dado o `id` da Reunião, devolve rótulos distintos, com tempo total de fala e maior segmento de cada um.
- **Áudio tratado**: dado o `id` da Reunião e um intervalo de tempo, devolve o trecho do áudio tratado. `participants` usa para a amostra de até 10 s.
- **Interfaces de modelo**: tratamento de áudio, diarização e transcrição atrás de interfaces separadas, trocáveis por fakes nos testes (RT-13).
- **Exclusão**: Transcrição, segmentos e áudio tratado ficam ligados à Reunião e somem com ela (exclusão em cascata de `meetings`).

## Critérios de aceite

### Disparo e status

1. Ao receber "Reunião criada", o módulo leva a Reunião a `processing` antes de começar o trabalho e a `transcribed` ao terminar com sucesso.
2. Ao receber "Nova tentativa" com etapa `transcription`, o módulo descarta qualquer dado parcial da tentativa anterior, inclusive de uma tentativa interrompida por reinício, reprocessa a partir do arquivo original e leva a Reunião a `processing` e depois a `transcribed`.
3. Um aviso ("Reunião criada" ou "Nova tentativa") recebido com a Reunião fora de `pending` é ignorado: nenhum processamento começa e o status não muda. Isso cobre aviso repetido e aviso para Reunião já em `processing`.
4. O arquivo original em `/audios` não muda depois do processamento.

### Tratamento de áudio

5. Uma fixture curta de cada formato aceito (mp3, wav, m4a, ogg, webm, mp4) chega a `transcribed` sem ação manual.
6. Depois de `transcribed`, o áudio tratado da Reunião está disponível pela interface "Áudio tratado", e o trecho devolvido para um intervalo tem a duração desse intervalo.

### Diarização e transcrição

7. Com `expected_speakers` informado, a interface de diarização recebe esse número. Sem o campo, a diarização roda sem número fixo.
8. A interface de transcrição recebe sempre o idioma pt-BR, sem detecção automática.
9. Os segmentos gravados vêm da junção das saídas das duas interfaces. Um trecho de fala que cai inteiro dentro do turno de um speaker recebe o rótulo desse speaker.
10. Um trecho de fala fora de qualquer turno da diarização recebe o rótulo do speaker com o turno mais próximo no tempo. Nenhum segmento fica sem speaker.

### Forma da Transcrição

11. Cada segmento tem `speaker_label`, `start_seconds`, `end_seconds` e `text`, com `0 <= start_seconds < end_seconds <= duração do áudio` e `text` não vazio depois de tirar espaços.
12. Os segmentos são devolvidos em ordem crescente de `start_seconds`.
13. A interface "Speakers" devolve exatamente os rótulos presentes nos segmentos, cada um com tempo total de fala e maior segmento.

### Falhas

14. Uma falha no tratamento, na diarização ou na transcrição leva a Reunião a `failed` com etapa `transcription` e uma mensagem legível em pt-BR. Nenhum segmento parcial fica gravado.
15. Com `HF_TOKEN` ausente, inválido ou sem aceite dos termos do modelo no HuggingFace, a Reunião vai para `failed` com mensagem que cita o `HF_TOKEN` e o aceite dos termos. A mensagem não contém o valor do token.
16. Um áudio sem fala detectada leva a Reunião a `failed` com etapa `transcription` e mensagem "nenhuma fala detectada".
17. Se a Reunião é excluída durante o processamento, o módulo não grava segmentos nem áudio tratado depois da exclusão.

### Consulta

18. `GET /meetings/{id}/transcript` numa Reunião em `transcribed` ou em status posterior devolve os segmentos em ordem, com `speaker_label`, `start_seconds`, `end_seconds` e `text`.
19. `GET /meetings/{id}/transcript` numa Reunião em `pending`, `processing` ou `failed` com etapa `transcription` responde HTTP 409.
20. `GET /meetings/{id}/transcript` de Reunião de outro Usuário responde HTTP 404. Sem autenticação, responde HTTP 401.

### Local, offline e hardware

21. Durante o processamento, nenhuma chamada de rede envia o áudio, nem trechos dele, para fora do servidor.
22. Com os modelos do Whisper e do Pyannote já em cache, uma Reunião chega a `transcribed` com o acesso à internet do container bloqueado.
23. Os modelos ficam num volume Docker que sobrevive a `docker compose down` (sem `-v`) e `up`. A segunda execução não baixa os modelos de novo.
24. Sem o perfil de GPU, o processamento roda em CPU. Com o perfil de GPU numa máquina com NVIDIA, roda na GPU. A forma da Transcrição é a mesma nos dois casos.

### Frontend

25. A tela da Transcrição mostra os segmentos em ordem, cada um com o instante de início em `hh:mm:ss`, o speaker e o texto.
26. Enquanto os speakers não têm nome, a tela mostra o rótulo (`SPEAKER_00`). Depois da nomeação em `participants`, mostra o nome atual do Participante.
27. Antes de `transcribed`, a tela da Transcrição mostra o status atual da Reunião em vez do texto.

### Limite de processamento por Usuário (Q60, Q62)

28. Com o limite configurado em N, um Usuário nunca tem mais de N Reuniões em `processing` ao mesmo tempo.
29. Uma Reunião que chega ao limite não é recusada. Ela fica em `pending` e começa quando uma Reunião do mesmo Usuário sai de `processing`, na ordem de criação.
30. O limite de um Usuário não atrasa as Reuniões de outro Usuário.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, pasta `/audios` temporária, fakes nas interfaces de tratamento, diarização e transcrição. Avisos de `meetings` disparados no próprio teste; processamento síncrono. Cobre critérios 1 a 4, 7 a 20 e 28 a 30, um teste por critério. Critérios 28 a 30 usam fake de transcrição que só termina quando o teste libera.
- **Junção (critérios 9 a 13):** turnos fake de diarização e trechos fake de transcrição, em tabelas pequenas: trecho dentro de um turno, entre turnos, fora de qualquer turno.
- **Tratamento (critérios 5 e 6):** suíte com ferramenta real de áudio e fixtures curtas, sem modelos de IA.
- **Modelos reais (critérios 21 a 24):** suíte separada e opcional, fora do `pytest` padrão, com áudio curto em pt-BR de duas vozes. Critério 22 roda com rede do container bloqueada. Critério 24 roda manualmente em máquina com NVIDIA.
- **Frontend (critérios 25 a 27):** framework não decidido. Questão para o planner.

## Questões em aberto

1. Cache dos modelos do Whisper fica no mesmo volume do Pyannote. Q17 fala só do Pyannote; critério transversal 14 (offline com modelos em cache) exige os dois.
2. Critério 26 junta, no frontend, os segmentos deste módulo com o vínculo de `GET /meetings/{id}/participants`. Se o planner preferir rota de Transcrição já com nomes, ela fica em `participants`, para não criar dependência deste módulo em `participants`.
3. Para o planner:
   - quais tratamentos de áudio (conversão de formato e taxa de amostragem, normalização, redução de ruído);
   - onde e em que formato guardar o áudio tratado;
   - biblioteca do Whisper (por exemplo `openai-whisper` ou `faster-whisper`) e tamanho do modelo;
   - versão e modelo do Pyannote;
   - regra de junção entre turnos e trechos (por exemplo maior sobreposição) e granularidade dos segmentos;
   - worker, concorrência entre Reuniões e valor do limite por Usuário;
   - Reuniões em `pending` após reinício (fila durável ou novo aviso);
   - metas de tempo de processamento em CPU e GPU.
4. Código HTTP 409 e endpoint são sugestões, não decisões.
