# 00 - Visão geral: Snook

> Status: rascunho aprovado em decisões. Q1 a Q74 fechadas. Nenhuma marca "proposto" de decisão de produto.
> Fontes: briefing do usuário de 2026-10-21, rodadas 1 a 5, decisões Q53 a Q69, Q70 (mudanças do planner aprovadas em 2026-10-22), Q71, Q72 e Q73 (2026-10-22), Q74 (2026-10-28). Repo sem código no momento da escrita.

## Visão

- Snook recebe gravação de reunião e entrega backlog pronto para revisão.
- Entrada: upload de áudio, ou gravação de tela no app (som da tela e microfone do usuário).
- App trata o áudio, separa falas por participante (diarização) e transcreve. Tudo local.
- Usuário ouve amostra de cada voz e dá nome a cada uma.
- Provedor de LLM ativo do usuário extrai Epics e User Stories pedidas na reunião, com prioridade, story points e critérios de aceite.
- Transcrição não cabe na janela de contexto: usuário divide em partes no app. Backlog sai unificado na mesma Reunião.
- Etapa falha: usuário tenta novamente a partir dela.
- Usuário revisa, cria, edita, exclui, regenera e exporta o backlog. Renomeia participantes sem gerar de novo.
- Provedores: OpenAI, Anthropic, DeepSeek e Ollama. Cada usuário informa a própria chave em tela de configurações. App guarda chave cifrada e nunca a mostra de volta.
- App roda somente local: máquina do usuário ou rede confiável, sem exposição à internet (Q60). Na rede, usa HTTPS pelo perfil `lan` (Q70).

## Problema

- Após reunião de levantamento, alguém reouve a gravação, lembra quem pediu o quê e escreve Epics e User Stories à mão.
- Trabalho lento. Perde pedidos.
- Sem saber quem falou cada trecho, perde também o solicitante de cada pedido.

## Usuários

- **Usuário**: pessoa com conta no app. Grava ou envia reunião de levantamento e precisa do backlog. Exemplo do briefing: desenvolvedor de software.
  - Cria conta sozinho na tela inicial. Entra com email ou nome de usuário e senha (Q2, Q20).
  - Vê só as próprias Reuniões (Q19).
  - Configura as próprias chaves de LLM e paga o próprio uso (Q33).
  - Obtém o consentimento dos participantes antes de gravar ou enviar uma reunião. App mostra aviso (LGPD, Q70).
- **Operador**: instala o app na máquina local ou na rede confiável. Preenche o `.env` com `HF_TOKEN` e a chave-mestra que cifra as chaves de LLM (Q17, Q33, Q60). Pode ser o mesmo Usuário.
  - Para uso na rede, sobe o perfil `lan`, que serve o app em HTTPS (Q70, ADR-0016).
  - Exclui a conta de um Usuário pelo comando `python -m snook.cli delete-user <username>` (LGPD, Q70).

## Glossário

Nome em código sugerido entre parênteses. Planner confirma no modelo de dados.

| Termo | Definição |
|---|---|
| Usuário (`User`) | Conta com email, nome de usuário e senha guardada como hash bcrypt. |
| Reunião (`Meeting`) | Gravação enviada ou capturada pelo Usuário e tudo o que deriva dela. Pertence a um único Usuário. Tem título (`title`) editável, pré-preenchido com o nome do arquivo. A data da Reunião é a data de envio (Q53). |
| Status da Reunião (`status`) | Um de `pending`, `processing`, `transcribed`, `needs_split`, `generating`, `done`, `failed` (Q8, Q45). Em `failed`, a Reunião guarda a etapa que falhou (`failed_stage`: `transcription` ou `generation`) e a mensagem. |
| Aviso | Notificação interna, emitida uma única vez por um módulo e consumida pelo módulo seguinte do pipeline, sem que o emissor dependa do consumidor. Avisos existentes: "Reunião criada", "Nova tentativa", "Participantes confirmados" e "Partes prontas". |
| Aviso de consentimento | Texto na tela de upload e na de gravação que lembra o Usuário de obter o consentimento dos participantes antes de gravar ou enviar a reunião (LGPD, Q70). Texto literal fixado pela Q72 (`01-prd/meetings.md`, critério 52). Não é um "Aviso" do pipeline. |
| Tentar novamente | Ação numa Reunião em `failed` que retoma da etapa que falhou. Na etapa `transcription`, reprocessa o áudio. Na etapa `generation`, reaproveita a Transcrição e os nomes e chama a LLM de novo (Q54). |
| Processamento interrompido | Reunião que estava em `processing`, em `generating`, ou em `transcribed` com Participantes confirmados quando o backend parou. Ao subir de novo, ela vai para `failed` com essa mensagem, e "Tentar novamente" fica disponível (Q58, Q69). |
| Gravação de tela | Captura feita no navegador pelo app. Capta o som da aba ou do sistema e o microfone numa trilha só; descarta o vídeo; para sozinha em 1h59m50s; vira uma Reunião (Q36, Q42, Q61). Exige contexto seguro: `http://localhost` ou HTTPS (Q70). |
| Perfil `lan` | Perfil do `docker compose` para uso em rede confiável. Serve o app em HTTPS com certificado de CA local (ADR-0016, Q70). |
| Tratamento de áudio | Edição e ajustes automáticos do áudio antes da diarização e transcrição. O usuário não faz nada manual. |
| Speaker (`speaker_label`) | Rótulo anônimo que a diarização atribui a uma voz, por exemplo `SPEAKER_00`. |
| Amostra de speaker | Trecho de até 10 s do maior segmento de um speaker, já tratado, tocado na UI para o usuário reconhecer a pessoa. |
| Participante (`Participant`) | Pessoa da Reunião, com nome dado pelo usuário. Speakers com o mesmo nome viram um só Participante. Depois da confirmação, o nome só muda por "Renomear participante" (Q55). |
| Renomear participante | Ação na tela de revisão do backlog que troca o nome de um Participante e, com isso, o solicitante exibido em todas as US, sem chamar a LLM. Nome igual ao de outro Participante da Reunião une os dois (Q55). |
| Segmento (`TranscriptSegment`) | Trecho contínuo de fala de um speaker, com início, fim e texto. |
| Transcrição (`Transcript`) | Conjunto ordenado de segmentos de uma Reunião. |
| Janela de contexto (`context_window`) | Limite de tokens do modelo, informado na Configuração de LLM com padrão sugerido (Q43, Q51). |
| Orçamento da Parte | Janela de contexto do modelo ativo menos uma reserva para o System Prompt, a lista de Participantes, os nomes de Epics já criadas e a resposta da LLM. É o limite de tokens para o texto de uma Parte. |
| Parte cabe | A estimativa de tokens do texto da Parte é menor ou igual ao orçamento da Parte. |
| Reunião longa | Reunião cuja Transcrição inteira não cabe no orçamento do modelo ativo. Vai para `needs_split` e é dividida em Partes dentro do app (Q43, Q45). |
| Parte (`TranscriptPart`) | Intervalo contíguo da Transcrição, cortado no fim de um segmento, sem sobreposição. As Partes de uma Reunião cobrem 100% da Transcrição, e cada uma cabe (Q44). Uma Reunião que cabe inteira tem uma Parte única. |
| Cancelar divisão | Ação na tela de divisão que volta uma Reunião de `needs_split` para `done`, sem mudar nada, sempre que ela tem backlog gravado (Q59, Q68). |
| Epic (`Epic`) | Agrupamento de User Stories, no formato "Epic: nome-feature". Pertence a uma única Reunião. O nome é texto livre, sem descrição, e é único só dentro da Reunião: Epics com o mesmo nome (sem diferenciar maiúsculas e espaços nas pontas) na mesma Reunião são mescladas; Reuniões distintas podem ter Epics de mesmo nome (Q47, Q57). |
| User Story (`UserStory`) | Pedido de uma Epic com `US-id`, nome, "Como / Eu quero / Para", prioridade, story points e critérios de aceite. |
| `US-id` | Identificador sequencial por Reunião: `US-01`, `US-02`... Contínuo entre as Partes. Não é renumerado após exclusão. A partir da centésima US, usa três dígitos (`US-100`) (Q27, Q48, Q49, Q56). |
| Prioridade (`priority`) | Low, Medium ou High, exibida em inglês. Sugerida pela LLM, editável pelo usuário. |
| Story Points (`story_points`) | Esforço na escala Fibonacci: 1, 2, 3, 5, 8 ou 13. Sugerido pela LLM, editável pelo usuário. |
| Critério de aceite (`AcceptanceCriterion`) | Condição no formato "Dado / Quando / Então". Uma US tem pelo menos um. |
| Solicitante (`requested_by`) | Único Participante que pediu a User Story, guardado pelo `id` do Participante. Fica vazio quando a LLM não identifica quem pediu. |
| Quando (`requested_at`) | Instante absoluto da fala na gravação (por exemplo `00:42:10`), dentro da duração do áudio. |
| Backlog gravado | Existe quando a Reunião teve ao menos uma geração bem-sucedida. Marca guardada em `meetings` e exposta como `has_backlog`. Pode estar vazio (zero Epics). |
| Provedor de LLM (`LlmProvider`) | OpenAI, Anthropic, DeepSeek ou Ollama. |
| Configuração de LLM (`LlmConfig`) | Configuração de um provedor para um Usuário: chave (ou URL, no Ollama), modelo e janela de contexto, com padrões sugeridos. A chave fica cifrada no SQLite. |
| Chave-mestra | Segredo no `.env` usado para cifrar e decifrar as chaves de LLM guardadas no SQLite. |
| Provedor ativo | O único provedor do Usuário marcado para interpretar os áudios. A geração sempre usa ele. |
| Máscara | Forma exibida de uma chave salva, por exemplo `sk-...abcd`. Chaves com menos de 12 caracteres aparecem só como `...`. A chave completa nunca volta para a UI. |
| System Prompt | Instrução fixa e versionada no código, enviada à LLM para gerar Epics e User Stories. |

## Escopo

1. Cadastro aberto, login e logout.
2. Duas entradas: upload de áudio ou gravação de tela (som da tela e microfone). Ambas com título opcional, pré-preenchido com o nome do arquivo.
3. Arquivo da Reunião em `/audios` (pasta `./audios` do host) até a Reunião ser excluída.
4. Tratamento automático de áudio, diarização (Pyannote) e transcrição (Whisper local, pt-BR).
5. Processamento assíncrono, com status visível.
6. "Tentar novamente" em Reunião que falhou, a partir da etapa que falhou, inclusive após reinício do backend.
7. Amostra de áudio por speaker; usuário nomeia todos os speakers.
8. Tela de Configuração de LLM por Usuário, com "Testar conexão" e provedor ativo.
9. Geração de Epics e User Stories, com prioridade, story points e critérios de aceite, via System Prompt.
10. Cada US registra quem pediu, de qual Reunião e quando.
11. Reunião longa: detecção na geração, divisão da Transcrição em Partes com cortes sugeridos e ajustáveis, backlog unificado na mesma Reunião.
12. Consulta, criação, edição, exclusão, movimentação de US entre Epics e regeneração do backlog.
13. Renomear participante na revisão do backlog, com união por nome igual.
14. Exportação do backlog em Markdown e JSON.
15. Aviso de consentimento dos participantes (LGPD) na tela de upload e na de gravação (Q70, Q72).
16. Comando de Operador `python -m snook.cli delete-user <username>`, que exclui um Usuário e todos os dados dele (LGPD, Q70).
17. Uso em rede confiável por HTTPS, pelo perfil `lan` (Q70, ADR-0016).

## Não-objetivos

Confirmados na Q18, mais itens das rodadas 2 a 5 e das decisões Q53 a Q70:

- Exposição à internet. App roda somente local, na máquina do usuário ou em rede confiável (Q60).
- Outras entradas além de upload de áudio e gravação de tela.
- Transcrição em tempo real durante a reunião. Processamento começa depois que a gravação termina.
- Integração direta com ferramentas de videoconferência (Zoom, Meet, Teams).
- Reuniões em idiomas diferentes de pt-BR na primeira versão.
- Provedores de LLM além de OpenAI, Anthropic, DeepSeek e Ollama.
- Identificar a mesma pessoa entre Reuniões diferentes por voz.
- Treinar ou ajustar (fine-tuning) modelos.
- Recuperação de senha (Q20).
- Troca de senha, edição de perfil, exclusão de conta pela UI e verificação de email (Q39). A exclusão de conta existe só pelo comando de Operador `python -m snook.cli delete-user <username>`, para cobrir a LGPD (Q70).
- Histórico de versões do backlog (Q30).
- Exportação em CSV para o Jira e envio direto ao Jira (Q31).
- Cortar ou reprocessar o áudio para dividir Reunião longa. Divisão é feita sobre a Transcrição (Q43).
- Resumir a Transcrição antes de enviá-la à LLM.
- Gravar som da tela e microfone em trilhas separadas (Q42).
- Dividir por vontade própria Reunião que cabe na janela de contexto (Q45).
- Partes sobrepostas (Q44).
- Gravar resultado parcial quando uma Parte falha (Q46).
- Junção de Epics decidida pela LLM (Q47).
- Remover automaticamente US repetidas entre Partes (Q48).
- Regenerar só uma Parte (Q50).
- Data da reunião diferente da data de envio (Q53).
- Reordenar Epics e User Stories na primeira versão (Q56).
- Retomar sozinho, após reinício, processamento interrompido (Q58, Q69).
- Recusar envio quando o Usuário está no limite de processamento (Q62).

## Restrições

### Stack (fonte: briefing)

- Backend em Python.
- Rotas HTTP com FastAPI.
- Transcrição com Whisper. Diarização com Pyannote.
- Suporte a múltiplos provedores de LLM.
- System Prompt para gerar Epics e User Stories.
- SQLite para armazenar Reuniões, Participantes, Transcrições, Epics e User Stories.
- Frontend em React + TypeScript + shadcn/ui.
- Docker para orquestração.
- Pytest para testes de unidade.

### Metodologia (fonte: briefing)

- GitFlow: `main`, `develop`, `feature/*`.
- Spec-Driven Development: spec aprovada antes do plano; plano antes das tarefas; tarefas antes do código.
- TDD: teste que falha antes do código de produção.

### Implantação (fonte: Q60, Q70)

- App roda somente local: máquina do usuário ou rede confiável. Não é exposto à internet.
- Mesmo assim: limite de tentativas no login e no "Testar conexão"; limite de Reuniões processando ao mesmo tempo por Usuário. Resolvido: ADR-0010 (valores padrão, configuráveis por `.env`).
- URL do Ollama aceita qualquer host, inclusive rede privada, só com `http` ou `https`, sem seguir redirecionamento.
- Nível ASVS de referência. Resolvido: `03-security.md` (ASVS 5.0, L2).
- Uso na rede exige HTTPS, pelo perfil `lan` (Q70, ADR-0016). Motivo: `getDisplayMedia` e `getUserMedia` só funcionam em contexto seguro (`https://` ou `http://localhost`). Em `http://<ip-da-rede>`, a gravação de tela não funciona.
- Sem o perfil `lan`, a porta do app fica ligada a `127.0.0.1` por padrão. Acesso pela rede em HTTP, sem o perfil, aceita upload, mas não grava tela (ADR-0016).

### Decisões do usuário (fonte: rodadas 1 a 5 e decisões Q53 a Q74)

| Q | Decisão |
|---|---|
| Q1 | Primeira versão com só duas entradas: gravação de tela ou envio de áudio. |
| Q2 | Login simples: email, nome de usuário e senha armazenada no banco com hash bcrypt. |
| Q3 | Whisper transcreve só pt-BR na primeira versão. |
| Q4 | Whisper roda localmente. |
| Q5 | CPU por padrão, GPU NVIDIA opcional via perfil do `docker compose`. |
| Q6 | Formatos aceitos: mp3, wav, m4a, ogg, webm e mp4 (extraindo o áudio). Limites: 2 h e 500 MB. O limite de tamanho foi fixado pela Q70 em 500 MiB (524.288.000 bytes). |
| Q7 | Arquivo da Reunião armazenado na pasta `/audios`. |
| Q8, Q45 | Processamento assíncrono, com status consultado por polling: `pending`, `processing`, `transcribed`, `needs_split`, `generating`, `done`, `failed`. `needs_split` fica entre `transcribed` e `generating`. |
| Q9, Q10 | Após a transcrição, o usuário ouve um trecho da voz de cada speaker (já tratado) e nomeia cada um. Em seguida, a Reunião segue para a LLM. |
| Q11 | Formato de Epic e User Story (ver 01-prd, "Formato do backlog"). Saída em pt-BR. A linha de prioridade (Fibonacci) foi corrigida pela Q28 e detalhada pela Q37. |
| Q12 | Cada User Story guarda só quem pediu, de qual Reunião e quando. Sem vínculo a segmentos da transcrição. |
| Q13 (resposta) | A pergunta original (editar e regenerar Epics e US) foi entendida pelo usuário como pergunta sobre áudio. A resposta virou decisão própria: "o sistema faz todas as edições e tratamentos de áudio necessários". A pergunta original foi refeita como Q30. |
| Q14 | Não respondida na rodada 1. Refeita e substituída pela Q31. |
| Q15 | Provedores: OpenAI, Anthropic, DeepSeek e Ollama. Chaves nunca expostas. A parte "unicamente no `.env`" foi **substituída pela Q33**. |
| Q16 | System Prompt fixo e versionado no código, sem edição pelo usuário. |
| Q17 | `HF_TOKEN` no `.env`; modelos do Pyannote em cache num volume Docker. |
| Q18, Q52 | Capability map aprovado: 8 módulos (Q18) mais `transcript-split` (Q52). Build order e não-objetivos aprovados. |
| Q19 | Cada Usuário vê e altera só as próprias Reuniões. Acesso a Reunião de outro Usuário responde como inexistente. |
| Q20 | Cadastro aberto na tela inicial; login por email ou nome de usuário, ambos únicos; senha com no mínimo 8 caracteres; sem recuperação de senha na primeira versão. |
| Q21 | **Substituída pela Q33.** (Era: tokens do servidor, compartilhados por todos os Usuários.) |
| Q22 | Tela de configurações onde o usuário inclui a chave de API da LLM de sua escolha e diz qual provedor fica ativo. |
| Q23 | Ollama externo, com URL e modelo configuráveis na tela de configuração de LLM. |
| Q24 | **Substituída pela Q36 e pela Q42.** (Era: gravação com "som da tela inteira por enquanto", sem microfone; vídeo, limite e navegadores em aberto.) |
| Q25, Q41 | Arquivo guardado até o Usuário excluir a Reunião; a exclusão apaga o arquivo. `/audios` é mapeado para `./audios` no host, fora do git. |
| Q26, Q35 | Amostra de até 10 s do maior segmento; todos os speakers nomeados; mesmo nome junta no mesmo Participante; campo opcional de número de participantes no upload; geração começa sozinha ao confirmar os nomes, sempre com o provedor ativo; a tela de nomeação só exibe qual provedor será usado. O intervalo do número de participantes foi fixado pela Q70 em 1 a 20. |
| Q27 | Nome da Epic em texto livre, sem descrição; `US-id` sequencial por Reunião (`US-01`, `US-02`...). |
| Q28 | **Substituída pela Q37**, que a detalha. (Era: Fibonacci passa a medir Story Points, e a prioridade passa a ser Low, Medium ou High, corrigindo a Q11.) |
| Q29 | Um único Participante solicitante, vazio quando não identificado; "quando" é o instante da fala na gravação, validado dentro da duração do áudio. |
| Q30, Q50 | Edição manual de Epic, US, prioridade, story points e critérios. Regeneração total com aviso de que as edições se perdem, sem histórico. Numa Reunião dividida, o usuário pode reajustar os cortes antes de regenerar; os `US-id` recomeçam em `US-01`. |
| Q31 | Exportação em Markdown (formato da Q11) e JSON. |
| Q32 | Seam principal de testes: API HTTP via `TestClient`, com `pytest` sem GPU, sem rede e sem token real. |
| Q33 | Configuração de LLM por Usuário, guardada no SQLite com a chave cifrada por uma chave-mestra que fica no `.env`. Depois de salva, a chave só aparece como máscara. Bancos de dados nunca vão para o git e ficam dentro do container. |
| Q34 | Modelo em texto livre com padrão sugerido por provedor; "Testar conexão" obrigatório antes de salvar; um único provedor ativo por vez; sem provedor ativo, a geração é bloqueada com mensagem que aponta para a tela de configurações. |
| Q36 | Gravação capta o som da aba ou do sistema e também a voz do usuário (microfone). Vídeo descartado, só áudio guardado (webm). Limite de 2 h. Suporte oficial em Chrome e Edge. Aceita áudio da aba ou do sistema, conforme o navegador oferecer. |
| Q37 | Story Points na escala Fibonacci (1, 2, 3, 5, 8, 13); prioridade Low, Medium ou High, exibida em inglês. A LLM sugere os dois e o usuário edita os dois. "Story Points" fica logo abaixo de "Prioridade". |
| Q38 | Reunião longa: o áudio fica armazenado e o usuário divide a reunião em pedaços que caibam na LLM. A forma da divisão foi **redefinida pela Q43**. |
| Q39 | Email e nome de usuário únicos sem diferenciar maiúsculas de minúsculas; nome de usuário com 3 a 30 caracteres (letras, dígitos, `_`, `.`, `-`); login automático após o cadastro; sem troca de senha, edição de perfil, exclusão de conta e verificação de email. A Q70 acrescentou a exclusão de conta só pelo comando de Operador. |
| Q40 | SQLite num volume Docker nomeado, fora do git; sobrevive a `docker compose down` e `up` (some só com `down -v`). |
| Q42 | Gravação em uma trilha só, misturada no navegador. Se faltar uma das fontes (som da tela ou microfone), o app avisa e deixa o usuário gravar só com a fonte disponível ou cancelar. Sem nenhuma fonte de áudio, a gravação é recusada com mensagem. |
| Q43 | Opção (c). A checagem acontece na geração, com a Transcrição real comparada à janela de contexto do modelo ativo. Se não couber, o usuário divide a Transcrição por intervalos de tempo dentro do app, na mesma Reunião. A LLM gera por Parte, e o backlog sai unificado na Reunião, com `US-id` contínuo e os nomes de speakers mantidos. O áudio não é reprocessado. |
| Q44 | O app sugere cortes que fazem cada Parte caber, e o usuário pode movê-los ou adicionar outros. Cortes sempre no fim de um segmento; sem sobreposição; Partes contíguas cobrindo 100% da Transcrição; confirmação bloqueada enquanto alguma Parte não couber. |
| Q45 | A divisão só aparece quando a Transcrição não cabe. Status `needs_split` enquanto a Reunião espera a divisão. |
| Q46 | Partes enviadas em sequência, na ordem do tempo, cada uma com o System Prompt e os nomes dos Participantes. A partir da segunda Parte, a LLM recebe os nomes das Epics já criadas. Falha em qualquer Parte: nada é gravado e a Reunião vai para `failed` com o motivo. |
| Q47 | Epics com o mesmo nome, sem diferenciar maiúsculas e espaços nas pontas, viram a mesma Epic. Na revisão, o usuário pode mover uma US para outra Epic. Renomear uma Epic para o nome de outra existente junta as duas. |
| Q48 | `US-id` segue a ordem das Partes e, dentro de cada uma, a ordem devolvida pela LLM. "Quando" é o instante absoluto na gravação. As Partes não aparecem no backlog nem na exportação, e a US não guarda a Parte de origem. US repetidas entre Partes não são removidas automaticamente. |
| Q49 | O usuário cria e exclui Epics, US e critérios. Só Epic vazia pode ser excluída. Os `US-id` não são renumerados após exclusão. US criada à mão recebe o próximo número depois do maior existente. |
| Q51 | Janela de contexto por provedor, em tokens, com padrão sugerido e editável. A primeira configuração salva fica ativa. Editar sem nova chave mantém a chave atual, com novo teste de conexão. O usuário pode remover uma configuração, o que apaga a chave cifrada. Remover o provedor ativo deixa o Usuário sem provedor ativo. |
| Q53 | Campo `title` opcional no upload e na gravação, pré-preenchido com o nome do arquivo e editável depois. A data da Reunião é a data de envio. |
| Q54 | Botão "Tentar novamente" em `failed`, que retoma da etapa que falhou. Falha na transcrição ou diarização reprocessa o áudio. Falha na geração reaproveita a Transcrição e os nomes dos speakers e chama a LLM de novo. |
| Q55 | Ação "Renomear participante" na tela de revisão do backlog, depois da confirmação. Atualiza o nome do solicitante em todas as US, sem chamar a LLM nem alterar Epics e US. Se o novo nome for igual ao de outro Participante da mesma Reunião, os dois são unidos, com a mesma regra da nomeação (Q26). |
| Q56 | Aprovados os itens "proposto" 1 a 34 da revisão dos PRDs, exceto o item 25 (substituído pela Q57). Entre eles: o backlog anterior só é substituído quando a regeneração termina bem; em `failed` da geração, o backlog anterior fica visível e exportável, só para leitura. Os PRDs não carregam mais a marca "proposto" nesses itens. |
| Q57 | Epic pertence a uma Reunião. Nomes de Epic são únicos só dentro da Reunião. Criar uma Epic com nome já existente na mesma Reunião mescla com a existente (mesma regra de comparação da Q47; sobrevive a Epic que já tinha o nome), em vez de recusar. Reuniões distintas podem ter Epics de mesmo nome. |
| Q58 | Ao subir o backend, toda Reunião em `processing` vai para `failed` (etapa `transcription`) e toda Reunião em `generating` vai para `failed` (etapa `generation`), com a mensagem "processamento interrompido". "Tentar novamente" fica disponível. |
| Q59 | Saídas de `needs_split`: (a) cancelar volta a Reunião para `done` com o backlog anterior (ampliado pela Q68); (b) na confirmação da divisão, a Reunião vai para `failed` (etapa `generation`) se não houver provedor ativo ou se um segmento sozinho passar do orçamento; (c) se a Transcrição passar a caber inteira, a Reunião segue sozinha com Parte única. |
| Q60 | O app roda somente local (máquina do usuário ou rede confiável), sem exposição à internet. URL do Ollama: qualquer host, inclusive rede privada, só `http` ou `https`, sem seguir redirecionamento. Limite de tentativas no login e no "Testar conexão"; limite de Reuniões processando ao mesmo tempo por Usuário. Valores e nível ASVS com o planner (resolvido: ADR-0010 e `03-security.md`). A Q70 acrescentou HTTPS na rede, pelo perfil `lan`. |
| Q61 | A gravação de tela para sozinha em 1h59m50s. A leitura de duração em `meetings` funciona com o webm do `MediaRecorder`, cujo cabeçalho não traz a duração. |
| Q62 | Reunião que passa do limite de processamento do Usuário espera em `pending` e começa quando abre vaga, na ordem de criação. Não é recusada no envio. |
| Q63 | URL do Ollama com credenciais embutidas (`http://usuario:senha@host`) é recusada. |
| Q64 | Chave com menos de 12 caracteres aparece só como `...`. |
| Q65 | "Reajustar cortes" numa Reunião cuja Transcrição passou a caber inteira segue direto com Parte única, sem abrir a tela de divisão. |
| Q66 | A regra "passou a caber, segue sozinha" roda ao abrir a tela de divisão e ao confirmar. Pela Q70, ao abrir a tela ela roda em `POST /meetings/{id}/split/refresh`, não no `GET`. |
| Q67 | Abrir a divisão sem provedor ativo mostra a mensagem com link para as configurações, sem orçamento e sem cortes sugeridos. |
| Q68 | "Cancelar divisão" vale sempre que a Reunião tem backlog gravado (`needs_split` → `done`, sem mudar nada), não só quando a divisão veio de "reajustar cortes". `split_reason` fica só para exibição. |
| Q69 | Ao subir o backend, Reunião em `transcribed` com Participantes confirmados (aviso "Participantes confirmados" ou "Nova tentativa" ainda não consumido) vai para `failed` (etapa `generation`) com "processamento interrompido", pela mesma regra da Q58. Reuniões em `pending` após reinício ficaram como questão para o planner (resolvido: ADR-0007, reenfileiradas no startup em ordem de criação). |
| Q70 | Aprovadas as 9 mudanças sugeridas pelo planner em 2026-10-22: (1) a regra "passou a caber" sai do `GET` e vai para `POST /meetings/{id}/split/refresh`, chamado pelo frontend ao abrir a tela de divisão (ADR-0019); (2) toda rota HTTP tem o prefixo `/api`; (3) aviso de consentimento dos participantes (LGPD) antes de gravar ou enviar; (4) comando de Operador `python -m snook.cli delete-user <username>`; (5) uso na rede exige HTTPS, pelo perfil `lan` (ADR-0016); (6) senha acima de 72 bytes recusada com HTTP 422 (ADR-0021); (7) `expected_speakers` de 1 a 20 e limite de tamanho de 500 MiB (524.288.000 bytes) (ADR-0018); (8) o critério 30 de `diarized-transcription` só vale com `TRANSCRIPTION_WORKERS` maior que `TRANSCRIPTION_MAX_PER_USER` (ADR-0010); (9) NFRs de performance do frontend (ADR-0023). |
| Q71 | Aviso de consentimento dos participantes é só texto visível junto de "Gravar reunião" e do botão de envio, sem confirmação obrigatória e sem bloquear a ação (2026-10-22). |
| Q72 | Texto literal do aviso de consentimento (2026-10-22): "Antes de gravar ou enviar, obtenha o consentimento de todos os participantes da reunião (LGPD). O áudio fica só neste servidor; o texto da transcrição vai ao provedor de LLM ativo." O texto vem de uma constante única do frontend, usada na tela de upload e na de gravação (`meetings`, critério 52; `screen-recording`, critério 26). |
| Q73 | LCP (NFR-03) medido na tela de login, a mesma rota do NFR-01 (2026-10-22). |
| Q74 | Aprovada a direção visual "Ata" (2026-10-28; ADR-0024): papel e tinta com acento petróleo (`--signal`); serif + sans + mono (Source Serif 4, Geist, Geist Mono); vidro só no painel flutuante da gravação; mouse-tracking só na borda da área de upload; card de login e cadastro opaco; controle de tema no shell, sem atalho de tecla; escala de espaço 4 a 64 e raios 4, 6 e 10, também nos primitivos. Substitui em parte o ADR-0022 e a fonte única do ADR-0023. Aprovado junto: nenhuma dependência npm nova; fontes locais `.woff2` com licença OFL. |

Mudanças em relação ao briefing e a rodadas anteriores:
- Briefing: usuário fornece o próprio token da LLM. Após idas e vindas (Q15, Q21, Q22), a Q33 confirmou: cada Usuário informa a própria chave na UI; app guarda cifrada.
- Ollama entrou como quarto provedor (Q15).
- Q24 previa gravar só som da tela, sem microfone. Q36 incluiu microfone; Q42 fixou trilha única.
- Q11 trazia prioridade em Fibonacci. Q28 corrigiu: Fibonacci mede Story Points; prioridade é Low, Medium ou High. Q37 fixou valores e quem sugere.
- Q38 previa dividir o áudio fora do app e reenviar pedaços. Q43 (c) trocou por divisão da Transcrição dentro do app, na mesma Reunião.
- Item "criar Epic com nome existente é recusado" virou mesclagem (Q57).
- "Cancelar reajuste" (Q59 a) virou "Cancelar divisão", válido sempre que há backlog gravado (Q68).
- Q6 dizia 500 MB sem definir a unidade. Q70 fixou 500 MiB (524.288.000 bytes).
- Q39 tirava a exclusão de conta. Q70 a devolveu só como comando de Operador, para a LGPD.
- Q66 rodava "passou a caber" no `GET` da divisão. Q70 moveu para `POST /meetings/{id}/split/refresh`.

## Capability map (aprovado: Q18 e Q52)

Coluna "Depende de" lista as dependências diretas: interfaces internas chamadas e avisos consumidos.

| Módulo (id) | Responsabilidade | Depende de |
|---|---|---|
| `auth` | Cadastro, login e logout com email, nome de usuário e senha (bcrypt); limite de tentativas de login; identificar o Usuário nas demais rotas. | (nenhum) |
| `llm-providers` | Tela de Configuração de LLM por Usuário (chave ou URL, modelo, janela de contexto, "Testar conexão" com limite de tentativas, provedor ativo); chaves cifradas com a chave-mestra; interface única de geração e de estimativa de tokens para OpenAI, Anthropic, DeepSeek e Ollama; nunca expor chaves. | `auth` |
| `meetings` | Criar Reunião por upload de áudio, com título; validar formato e limites; guardar o arquivo em `/audios`; listar, detalhar, renomear e excluir Reuniões do próprio Usuário; guardar e expor o status; guardar as marcas de Participantes confirmados e de backlog gravado e expô-las no detalhe como `participants_confirmed` e `has_backlog`; "Tentar novamente"; marcar processamentos interrompidos ao subir; emitir os avisos "Reunião criada" e "Nova tentativa". | `auth` |
| `screen-recording` | Gravar o som da tela e o microfone numa trilha só no navegador, parar em 1h59m50s e enviar o resultado, com título, como nova Reunião. | `meetings` |
| `diarized-transcription` | Consumir "Reunião criada" e "Nova tentativa" (etapa `transcription`); respeitar o limite de Reuniões processando por Usuário, com espera em `pending`; tratar o áudio; rodar Pyannote e Whisper (pt-BR, local); unir as saídas em segmentos; persistir a Transcrição e o áudio tratado. | `meetings`, `auth` |
| `participants` | Tocar a amostra de cada speaker; receber o nome de cada um; associar speakers a Participantes; exibir o provedor ativo e bloquear a confirmação sem ele; registrar a confirmação em `meetings` e emitir "Participantes confirmados"; oferecer a interface "Renomear Participante", com união por nome igual (Q55). | `diarized-transcription`, `llm-providers`, `meetings`, `auth` |
| `transcript-split` | Consumir "Participantes confirmados" e "Nova tentativa" (etapa `generation`); atender pedidos de regeneração; checar se a Transcrição cabe no orçamento; gravar Parte única ou levar a Reunião a `needs_split`; sugerir cortes; receber ajustes; "Cancelar divisão"; gravar as Partes; montar o texto de cada Parte; expor o orçamento; emitir "Partes prontas". | `participants`, `llm-providers`, `diarized-transcription`, `meetings`, `auth` |
| `backlog-generation` | Consumir "Partes prontas"; reestimar cada Parte antes de enviá-la; enviar cada Parte, os nomes dos Participantes e o System Prompt ao provedor ativo; validar a saída; juntar Epics de mesmo nome; numerar `US-id`; gravar tudo ou nada; registrar o backlog gravado em `meetings`. | `transcript-split`, `llm-providers`, `participants`, `meetings` |
| `backlog-review` | Exibir o backlog; criar, editar, excluir, mover e mesclar itens; regenerar via `transcript-split`; "Renomear participante" via `participants`; exportar em Markdown e JSON. | `backlog-generation`, `transcript-split`, `participants`, `meetings`, `auth` |

Sem ciclos. Cada módulo entrega a API e/ou a tela da própria capacidade, exceto `backlog-generation`, só interno. Avisos são consumidos pelos módulos seguintes, sem que o emissor dependa deles. Marcas de Participantes confirmados e de backlog gravado ficam em `meetings`, para nenhum módulo depender de quem está mais abaixo na cadeia.

Ajustes após a aprovação:
- `participants` passou a depender também de `llm-providers`, para exibir o provedor ativo (Q35) e bloquear sem ele (Q34).
- Regeneração passa por `transcript-split`, chamada por `backlog-review`.
- "Renomear participante": regra em `participants`; endpoint e botão em `backlog-review`. Motivos:
  - `participants` é dono dos nomes e da regra de união;
  - US, cujo solicitante muda na união, são tratadas em `backlog-review`;
  - chamada vai de `backlog-review` para `participants`, de baixo para cima na cadeia, sem ciclo.
- Coluna "Depende de" lista todas as dependências diretas, inclusive `meetings` (status, marcas) e `auth` (Usuário atual).
- Marcas de Participantes confirmados (Q69) e de backlog gravado (Q68) ficam em `meetings`, registradas por `participants` e `backlog-generation`.
- Comando `delete-user` (Q70) apaga dados de `auth`, `llm-providers` e `meetings`, inclusive arquivos em `/audios`. Fica fora dos módulos de rota, como ferramenta de Operador. Resolvido: `02-architecture.md`, "Exclusão de Usuário pelo Operador". Mora em `cli.py`, que importa os módulos; nenhum módulo importa `cli.py`, então não há ciclo.

Nenhum ajuste muda a build order.

### Build order

1. `auth`
2. `llm-providers` e `meetings` (paralelos)
3. `screen-recording` e `diarized-transcription` (paralelos)
4. `participants`
5. `transcript-split`
6. `backlog-generation`
7. `backlog-review`

## Fluxo principal

1. Usuário cria conta (já fica autenticado) ou entra.
2. Usuário cadastra chave (ou URL do Ollama), modelo e janela de contexto de pelo menos um provedor, testa a conexão e marca um provedor ativo.
3. Usuário vê o aviso de consentimento, envia arquivo de áudio ou grava som da tela e microfone, e confere o título. Sistema cria a Reunião em `pending` e guarda o arquivo em `/audios`.
4. Sistema trata o áudio, diariza e transcreve de forma assíncrona (`processing`, depois `transcribed`).
5. Usuário ouve amostra de cada speaker e dá nome a todos. Tela mostra qual provedor ativo será usado.
6. Nomes confirmados: sistema compara a Transcrição com o orçamento do modelo ativo.
7. Cabe: Transcrição inteira vira Parte única; Reunião vai para `generating`.
8. Não cabe: Reunião vai para `needs_split`. App sugere cortes; usuário ajusta e confirma; Reunião vai para `generating`.
9. Sistema envia as Partes em sequência ao provedor ativo e grava Epics, User Stories e critérios, unificados na Reunião (`done`). Qualquer falha leva a `failed` sem gravar nada e sem apagar o backlog anterior.
10. Em `failed`, usuário clica "Tentar novamente". Falha na transcrição volta ao passo 4. Falha na geração volta ao passo 6, com Transcrição e nomes mantidos. Reinício do backend no meio do processamento também leva a `failed`.
11. Usuário revisa, cria, edita, exclui, move, regenera ou exporta o backlog, e renomeia participantes sem gerar de novo.

## Decisões pendentes

Q1 a Q74 fechadas. Nenhuma decisão do usuário em aberto.

Pendências do planner: todas resolvidas. Ver `02-architecture.md`, seção "Respostas às decisões pendentes do spec", que liga cada pendência ao ADR ou documento que a responde. Meta de tempo de processamento: sem meta na v1; o spike da Task 1 mede (`02-architecture.md`, "Questões em aberto").
