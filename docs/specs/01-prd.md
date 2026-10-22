# 01 - PRD: requisitos transversais e índice de módulos

> Status: rascunho aprovado em decisões. Q1 a Q73 fechadas. Todos os PRDs de módulo escritos. Nenhuma marca "proposto" de decisão de produto.
> Visão, glossário, decisões e capability map: `docs/specs/00-overview.md`.
> Cada módulo tem PRD próprio em `docs/specs/01-prd/<id-do-modulo>.md`.

## Convenção de rotas

- Toda rota HTTP fica sob o prefixo `/api` (Q70; `05-api.md`).
- Nos PRDs, rotas aparecem sem o prefixo. `/meetings/{id}` significa `/api/meetings/{id}`, e `POST /auth/login` significa `POST /api/auth/login`.

## Problem Statement

- Após reunião de levantamento, usuário reouve a gravação, lembra quem pediu cada coisa e escreve Epics e User Stories à mão.
- Processo lento. Perde pedidos. Perde vínculo entre pedido e solicitante.

## Solution

- Usuário cria conta e cadastra chave do provedor de LLM preferido (OpenAI, Anthropic, DeepSeek ou Ollama). Marca um como ativo.
- Envia áudio da reunião ou grava no app o som da tela e a própria voz. Dá título à Reunião.
- Snook trata o áudio, separa falas por speaker e transcreve localmente em pt-BR.
- Usuário ouve amostra de cada speaker e dá nome a todos.
- Nomes confirmados: provedor ativo gera Epics e User Stories com prioridade, story points e critérios de aceite.
- Transcrição não cabe no modelo: app sugere cortes, usuário ajusta, backlog sai unificado na mesma Reunião.
- Etapa falha: usuário tenta novamente a partir dela.
- Cada US registra quem pediu, de qual Reunião e quando.
- Usuário revisa, cria, edita, exclui, move, regenera e exporta (Markdown ou JSON). Renomeia participantes sem gerar de novo.
- Tudo local, sem exposição à internet. Na rede, HTTPS pelo perfil `lan`.

## User Stories (fim a fim)

1. Como visitante, quero criar uma conta com email, nome de usuário e senha, para usar o app.
2. Como usuário, quero entrar com email ou nome de usuário e senha, para acessar minhas reuniões.
3. Como usuário, quero que minhas reuniões fiquem invisíveis para outros usuários, para proteger o conteúdo.
4. Como usuário, quero informar a chave de API (ou a URL do Ollama), o modelo e a janela de contexto de cada provedor numa tela de configurações, testar a conexão e escolher qual fica ativo, para usar o provedor que prefiro com a minha conta.
5. Como usuário, quero que a chave salva nunca volte a aparecer inteira, só mascarada, para que ninguém a copie da tela.
6. Como usuário, quero enviar o arquivo de áudio de uma reunião, para não transcrevê-la à mão.
7. Como usuário, quero gravar pelo app o som da tela e a minha própria voz, para não precisar de outra ferramenta e para que meus pedidos também entrem no backlog.
8. Como usuário, quero ser avisado quando faltar o som da tela ou o microfone e escolher se gravo só com o que há, para não perder a reunião.
9. Como usuário, quero dar um título à reunião, já preenchido com o nome do arquivo, e editá-lo depois, para reconhecê-la na lista.
10. Como usuário, quero acompanhar o status do processamento da reunião, para saber quando a transcrição e o backlog ficam prontos.
11. Como usuário, quero tentar novamente uma reunião que falhou, a partir da etapa que falhou, inclusive depois de um reinício do app, para não reenviar o arquivo nem refazer o que já deu certo.
12. Como usuário, quero que o sistema trate o áudio sozinho, para não converter nem editar arquivos antes de enviar.
13. Como usuário, quero ver a transcrição separada por quem falou, para saber quem disse cada trecho.
14. Como usuário, quero ouvir uma amostra da voz de cada speaker e dar nome a ele, para que o backlog cite as pessoas reais.
15. Como usuário, quero que a reunião siga sozinha para o provedor ativo depois que eu confirmar os nomes, para obter Epics e User Stories sem outro passo.
16. Como usuário, quero que o app sugira cortes para uma reunião longa e me deixe ajustá-los, sem reenviar o áudio, para que cada parte caiba no modelo e eu receba um backlog único.
17. Como usuário, quero ver as User Stories agrupadas por Epic, com prioridade, story points e critérios de aceite, para revisar o backlog por objetivo.
18. Como usuário, quero ver em cada User Story quem pediu, de qual reunião e em que instante da gravação, para saber a quem recorrer e onde ouvir o pedido.
19. Como usuário, quero editar Epics, User Stories, prioridade, story points e critérios, para corrigir o que a LLM errou.
20. Como usuário, quero criar e excluir Epics, User Stories e critérios, e mover uma User Story para outra Epic, para completar e organizar o backlog.
21. Como usuário, quero renomear um participante na revisão do backlog, unindo-o a outro quando dou o mesmo nome, para corrigir o solicitante sem gerar o backlog de novo.
22. Como usuário, quero regenerar o backlog, com aviso de que minhas edições se perdem e, numa reunião dividida, com a chance de reajustar os cortes ou cancelar a divisão, para tentar uma nova interpretação.
23. Como usuário, quero exportar o backlog em Markdown e JSON, para levá-lo a outra ferramenta.
24. Como usuário, quero ser lembrado de obter o consentimento dos participantes antes de gravar ou enviar uma reunião, para cumprir a LGPD.
25. Como operador, quero excluir a conta de um Usuário e todos os dados dele por um comando, para atender um pedido de eliminação (LGPD).
26. Como usuário na rede confiável, quero abrir o app em HTTPS, para que a gravação de tela funcione e a sessão não trafegue em texto claro.
27. Como usuário, quero que as telas carreguem e respondam rápido, mesmo com uma Transcrição de 2 h, para trabalhar sem espera.

## Formato do backlog

Fonte: rodada 1, Q11; ajustes seguintes (Q27, Q37 — que substitui a Q28 —, Q47, Q48, Q49, Q56, Q57).

Texto do usuário (Q11), com prioridade e linha de Story Points ajustadas pela Q37 (que substitui a Q28):

```
Epic: nome-feature

US-id: nome
Como <personagem>
Eu quero <desejo>
Para <benefício>

Prioridade: <Low | Medium | High>
Story Points: <1 | 2 | 3 | 5 | 8 | 13>
Critérios de aceitação: (pode haver mais de um)
Dado <situação>
Quando <ação>
Então <resposta>
```

- Epic pertence a uma Reunião e pode ter várias US. Nome em texto livre, sem descrição (Q27).
- Mesma Reunião: Epics com mesmo nome, sem diferenciar maiúsculas e espaços nas pontas, são mescladas; sobrevive a que já tinha o nome. Reuniões distintas podem ter Epics de mesmo nome (Q47, Q57).
- `US-id` sequencial por Reunião: `US-01`, `US-02`... (Q27). A partir da centésima, três dígitos (`US-100`) (Q56).
  - Reunião dividida: numeração segue a ordem das Partes e, dentro de cada Parte, a ordem da LLM (Q48).
  - Sem renumeração após exclusão. US criada à mão recebe o próximo número depois do maior existente (Q49).
  - Regeneração: numeração recomeça em `US-01` (Q50).
- Cada US tem pelo menos um critério de aceite.
- LLM sugere prioridade e story points; usuário edita os dois (Q37).
- Prioridade em inglês: Low, Medium, High (Q37).
- Cada US guarda também (Q12, Q29, Q48):
  - solicitante: um único Participante, ou vazio quando a LLM não identifica;
  - a Reunião;
  - quando: instante absoluto da fala na gravação, em `hh:mm:ss`, dentro da duração do áudio.
- US criada à mão: solicitante e instante opcionais (Q56).
- Solicitante guardado pelo `id` do Participante. Renomeação aparece em todas as US; união troca o `id` nas US do absorvido (Q55).
- Partes não aparecem no backlog nem na exportação (Q48).

## Escopo

- Cadastro aberto, login e logout, com isolamento por Usuário.
- Configuração de LLM por Usuário: chave cifrada, janela de contexto, "Testar conexão", provedor ativo.
- Entrada por upload de áudio ou gravação de tela (som da tela e microfone numa trilha só), com título opcional.
- Aviso de consentimento dos participantes (LGPD) no upload e na gravação.
- Arquivo em `/audios` até a Reunião ser excluída.
- Tratamento de áudio, diarização e transcrição, assíncronos e com status.
- "Tentar novamente" a partir da etapa que falhou, inclusive após reinício.
- Amostra e nomeação de speakers.
- Geração de Epics, US, prioridade, story points e critérios via System Prompt fixo.
- Reunião longa: detecção na geração, cortes sugeridos e ajustáveis, geração por Parte, backlog unificado.
- Criação, edição, exclusão, movimentação, regeneração e exportação (Markdown e JSON).
- Renomear participante na revisão, com união por nome igual.
- Persistência e consulta de Usuários, Configurações de LLM, Reuniões, Participantes, Transcrições, Partes, Epics e User Stories.
- Comando de Operador `python -m snook.cli delete-user <username>`.
- Uso na rede confiável por HTTPS, pelo perfil `lan`.
- NFRs de performance do frontend.

## Fora de escopo

Ver "Não-objetivos" em `00-overview.md`.

## Restrições

| Restrição | Fonte |
|---|---|
| Backend em Python, rotas em FastAPI. | briefing |
| Transcrição com Whisper; diarização com Pyannote. | briefing |
| Geração de Epics e User Stories guiada por System Prompt. | briefing |
| Persistência em SQLite. | briefing |
| Frontend em React + TypeScript + shadcn/ui. | briefing |
| Orquestração com Docker. | briefing |
| Testes de unidade com Pytest. | briefing |
| GitFlow (`main`, `develop`, `feature/*`), Spec-Driven Development e TDD. | briefing |
| Entrada só por gravação de tela ou envio de áudio. | rodada 1, Q1 |
| Login com email, nome de usuário e senha; senha no banco só como hash bcrypt. | rodada 1, Q2 |
| Whisper local, idioma pt-BR. | rodada 1, Q3 e Q4 |
| CPU por padrão; GPU NVIDIA opcional via perfil do `docker compose`. | rodada 1, Q5 |
| Formatos mp3, wav, m4a, ogg, webm e mp4; máximo de 2 h e 500 MiB (524.288.000 bytes). | rodada 1, Q6; Q70 (ADR-0018) |
| Arquivo da Reunião em `/audios`, mapeado para `./audios` no host, fora do git; apagado junto com a Reunião. | rodada 1, Q7; rodada 2, Q25; rodada 4, Q41 |
| Status: `pending`, `processing`, `transcribed`, `needs_split`, `generating`, `done`, `failed`, consultados por polling. | rodada 1, Q8; rodada 5, Q45 |
| Provedores: OpenAI, Anthropic, DeepSeek e Ollama. | rodada 1, Q15 |
| System Prompt fixo e versionado no código. | rodada 1, Q16 |
| `HF_TOKEN` no `.env`; modelos do Pyannote em cache num volume Docker. | rodada 1, Q17 |
| Cada Usuário vê só os próprios dados; recurso de outro Usuário responde como inexistente. | rodada 2, Q19 |
| Cadastro aberto; login por email ou nome de usuário, ambos únicos; senha mínima de 8 caracteres; sem recuperação de senha. | rodada 2, Q20 |
| Ollama externo, com URL e modelo configuráveis na tela. | rodada 2, Q23 |
| Configuração de LLM por Usuário no SQLite; chave cifrada com chave-mestra do `.env`; só máscara na UI após salvar. | rodada 3, Q33 |
| Bancos de dados nunca vão para o git e ficam dentro do container. | rodada 3, Q33 |
| SQLite num volume Docker nomeado, que sobrevive à recriação do container. | rodada 4, Q40 |
| Modelo em texto livre com padrão sugerido; "Testar conexão" antes de salvar; um provedor ativo por vez. | rodada 3, Q34 |
| Janela de contexto editável com padrão; primeira configuração ativa; edição mantém a chave; remoção apaga a chave. | rodada 5, Q51 |
| A geração sempre usa o provedor ativo; a tela de nomeação só o exibe. | rodada 3, Q35 |
| Gravação de tela com som da aba ou do sistema e microfone; vídeo descartado; Chrome e Edge. | rodada 3, Q36 (substitui a Q24) |
| Gravação em trilha única; fonte ausente gera aviso e escolha; sem fonte nenhuma, recusa. | rodada 4, Q42 |
| Gravação para sozinha em 1h59m50s; a leitura de duração aceita o webm do `MediaRecorder`. | Q61 |
| Story points 1, 2, 3, 5, 8, 13; prioridade Low, Medium, High; ambos sugeridos pela LLM e editáveis. | rodada 3, Q37 (substitui a Q28) |
| Reunião longa: checagem na geração pela Transcrição real; divisão da Transcrição no app; backlog unificado com `US-id` contínuo; nomes mantidos; áudio não reprocessado. | rodada 4, Q43 (redefine a Q38) |
| Cortes sugeridos e ajustáveis, no fim de segmento, sem sobreposição, cobrindo 100%; confirmação só com todas as Partes cabendo. | rodada 5, Q44 |
| Partes em sequência; nomes das Epics já criadas enviados a partir da segunda Parte; tudo ou nada. | rodada 5, Q46 |
| Junção de Epics por nome; mover US; renomear para nome existente junta. | rodada 5, Q47 |
| Numeração por ordem das Partes; "quando" absoluto; Partes invisíveis no backlog; sem deduplicação automática. | rodada 5, Q48 |
| Criar e excluir Epics, US e critérios; só Epic vazia é excluída; sem renumerar. | rodada 5, Q49 |
| Regeneração total, com reajuste opcional de cortes; `US-id` recomeça em `US-01`. | rodada 5, Q50 |
| Unicidade sem diferenciar maiúsculas de minúsculas; regra de nome de usuário; login automático após cadastro. | rodada 3, Q39 |
| Título opcional no upload e na gravação, pré-preenchido com o nome do arquivo, editável depois; data da Reunião é a data de envio. | Q53 |
| "Tentar novamente" em `failed`, a partir da etapa que falhou. | Q54 |
| "Renomear participante" na revisão do backlog, sem chamar a LLM nem alterar Epics e US; nome igual une os dois. | Q55 |
| Itens "proposto" 1 a 34 da revisão aprovados, exceto o 25. | Q56 |
| Epic pertence à Reunião; nome único só dentro dela; criar com nome existente mescla. | Q57 |
| Ao subir o backend, `processing` e `generating` vão para `failed` com "processamento interrompido". | Q58 |
| Saídas de `needs_split`: cancelar, `failed` na confirmação, Parte única quando passa a caber. | Q59 |
| Somente local, sem exposição à internet; limites de tentativas e de processamento simultâneo; regras da URL do Ollama. | Q60 |
| Reunião acima do limite espera em `pending`; URL do Ollama com credenciais recusada; chave curta só como `...`. | Q62, Q63, Q64 |
| "Reajustar cortes" que passou a caber segue com Parte única; "passou a caber" roda ao abrir e ao confirmar a divisão; divisão sem provedor ativo mostra só a mensagem. | Q65, Q66, Q67 |
| "Cancelar divisão" vale sempre que há backlog gravado; `split_reason` só para exibição. | Q68 |
| Ao subir o backend, `transcribed` com Participantes confirmados vai para `failed` com "processamento interrompido". | Q69 |
| "Passou a caber" ao abrir a divisão roda em `POST /meetings/{id}/split/refresh`; `GET /meetings/{id}/split` só lê. | Q70 (ADR-0019) |
| Toda rota HTTP sob o prefixo `/api`. | Q70 (`05-api.md`) |
| Aviso de consentimento dos participantes (LGPD) antes de gravar ou enviar. | Q70 (`03-security.md`, LGPD) |
| Aviso de consentimento só em texto, sem confirmação obrigatória e sem bloquear a ação. | Q71 |
| Texto literal do aviso de consentimento, numa constante única do frontend (`meetings`, critério 52). | Q72 |
| Exclusão de conta só pelo comando de Operador `python -m snook.cli delete-user <username>`. | Q70 (`03-security.md`, LGPD) |
| Uso na rede exige HTTPS, pelo perfil `lan`; `getDisplayMedia` exige contexto seguro. | Q70 (ADR-0016) |
| Senha de 8 caracteres a 72 bytes em UTF-8; acima de 72 bytes, HTTP 422. | Q70 (ADR-0021) |
| `expected_speakers` de 1 a 20. | Q70 (`05-api.md`) |
| Critério 30 de `diarized-transcription` só vale com `TRANSCRIPTION_WORKERS` maior que `TRANSCRIPTION_MAX_PER_USER`. | Q70 (ADR-0010) |
| NFRs de performance do frontend (seção "NFRs de performance do frontend"). | Q70 (ADR-0023) |

## Requisitos transversais

- **RT-01 Provedores intercambiáveis.** OpenAI, Anthropic, DeepSeek e Ollama atendem a mesma operação de geração. Trocar o provedor ativo não muda o formato das Epics e User Stories gravadas.
- **RT-02 Segredos nunca expostos.**
  - `HF_TOKEN` e chave-mestra vêm só do `.env`.
  - Chaves de LLM ficam no SQLite, cifradas com a chave-mestra.
  - Chave de LLM salva só volta para a UI como máscara.
  - Nenhum segredo aparece em texto claro em respostas da API, logs, SQLite ou arquivo versionado no git.
- **RT-03 Autenticação.** Todas as rotas exigem Usuário autenticado, exceto `POST /auth/register` (cadastro), `POST /auth/login` (login) e `GET /health` (`03-security.md`, SEC-01; `05-api.md`). Senha no banco só como hash bcrypt.
- **RT-04 Isolamento por Usuário.** Cada Usuário lê e altera só as próprias Configurações de LLM, Reuniões e tudo que deriva delas. Recurso de outro Usuário responde como inexistente.
- **RT-05 Persistência.**
  - Usuários, Configurações de LLM, Reuniões, Participantes, Transcrições, Partes, Epics, User Stories e critérios ficam no SQLite.
  - SQLite num volume Docker nomeado, dentro do container, fora do git.
  - Arquivos de Reunião em `/audios`, mapeado para `./audios` no host, fora do git.
- **RT-06 Áudio local.** Tratamento, diarização e transcrição rodam no servidor. Áudio não vai a serviço externo. Só texto vai ao provedor ativo.
- **RT-07 Tratamento automático.** Todo arquivo em formato aceito passa por tratamento automático antes da diarização. Usuário não converte nem edita o arquivo.
- **RT-08 Idioma.** Entrada transcrita como pt-BR. Epics, US e critérios saem em pt-BR, no formato do backlog.
- **RT-09 Processamento assíncrono.** Upload e gravação respondem antes do fim do processamento. Reunião expõe o status atual.
- **RT-10 Reunião longa.** Nenhuma chamada à LLM recebe texto de Parte com estimativa acima do orçamento da Parte. Transcrição que não cabe: Reunião vai para `needs_split`, usuário divide em Partes no app, sem reprocessar o áudio. Backlog das Partes sai unificado na Reunião.
- **RT-11 Retomada após falha.** Toda falha leva a Reunião a `failed` com etapa (`transcription` ou `generation`) e mensagem legível. Reinício do backend também, para Reuniões em `processing`, `generating` ou `transcribed` com Participantes confirmados (Q58, Q69). "Tentar novamente" retoma da etapa que falhou, sem novo envio do arquivo.
- **RT-12 Orquestração.** Backend, frontend e banco sobem juntos via Docker.
- **RT-13 Testabilidade.** Whisper, Pyannote e cada provedor de LLM ficam atrás de interface que o teste troca por fake.
- **RT-14 Fluxo de trabalho.** Todo código entra por `feature/*` a partir de `develop`, com spec aprovada e teste escrito antes do código.
- **RT-15 Somente local.** App roda na máquina do usuário ou em rede confiável, sem exposição à internet (Q60). Mesmo assim:
  - login e "Testar conexão" têm limite de tentativas;
  - cada Usuário tem limite de Reuniões processando ao mesmo tempo;
  - URL do Ollama só aceita `http` e `https` e não segue redirecionamento;
  - uso na rede exige HTTPS, pelo perfil `lan` (Q70, ADR-0016). `getDisplayMedia` e `getUserMedia` só funcionam em contexto seguro (`https://` ou `http://localhost`).

  Valores dos limites: resolvido no ADR-0010. Nível ASVS: resolvido em `03-security.md` (ASVS 5.0, L2).
- **RT-16 Privacidade (LGPD).** (Q70; `03-security.md`, seção "Privacidade (LGPD)")
  - Tela de upload e tela de gravação mostram aviso de consentimento dos participantes antes de enviar ou gravar, com o texto literal da Q72. Critérios em `meetings` (52) e `screen-recording` (26).
  - Exclusão de conta não existe pela UI (Q39). Operador exclui um Usuário e todos os dados dele com `python -m snook.cli delete-user <username>`.

## Critérios de aceite transversais

1. A partir de um clone limpo, com `.env` preenchido, `docker compose up` sobe backend e frontend, e o frontend responde no navegador sem passo manual adicional.
2. Após `docker compose down` (sem `-v`) e `docker compose up`, os dados do SQLite e os arquivos em `./audios` criados antes continuam disponíveis.
3. Com cada um dos quatro provedores configurado como ativo, a geração grava Epics e User Stories no mesmo formato.
4. Sem provedor ativo, o sistema não chama a LLM e mostra uma mensagem que aponta para a tela de configurações.
5. Depois de salvar uma chave de LLM, toda resposta da API sobre essa configuração devolve só a máscara, nunca a chave completa.
6. O valor gravado no SQLite para uma chave de LLM difere da chave original, e só se recupera a chave com a chave-mestra do `.env`.
7. Com segredos de teste conhecidos (chaves de LLM, `HF_TOKEN`, chave-mestra), nenhum desses valores aparece em texto claro em respostas da API, nos logs da aplicação ou no SQLite.
8. O repositório versiona um `.env.example` sem valores secretos. O `.gitignore` cobre o `.env`, arquivos de banco SQLite e `./audios`, e nenhum desses entra em commit.
9. A coluna de senha guarda só hash bcrypt, e nenhuma resposta da API devolve senha ou hash.
10. Requisição sem Usuário autenticado a qualquer rota sob `/api` recebe HTTP 401, exceto `POST /auth/register`, `POST /auth/login` e `GET /health`, que respondem sem sessão (RT-03).
11. Isolamento:
    - Requisição de um Usuário a `/meetings/{id}` de uma Reunião de outro Usuário, ou a qualquer rota aninhada nela (Transcrição, speakers, Participantes, divisão, backlog, exportação, tentar novamente), recebe HTTP 404, e nada muda.
    - As rotas de `/llm-configs/{provider}` sempre leem e alteram a configuração do Usuário autenticado. Nenhuma requisição lê, altera ou usa a configuração de outro Usuário.
12. Toda User Story gerada pela LLM e gravada pertence a uma Epic e tem estes campos:
    - `US-id` e nome;
    - "Como", "Eu quero" e "Para";
    - prioridade Low, Medium ou High;
    - story points em 1, 2, 3, 5, 8 ou 13;
    - pelo menos um critério "Dado / Quando / Então";
    - Reunião e quando.

    O solicitante é um Participante da mesma Reunião, ou fica vazio. Numa US criada à mão, o solicitante e o instante são opcionais (Q56; `backlog-review`, critério 18).
13. Um arquivo em qualquer formato aceito, enviado sem preparo, chega ao status `transcribed` sem ação manual do usuário.
14. Com os modelos já em cache, a transcrição e a diarização funcionam sem acesso à internet.
15. Com um modelo fake de janela de contexto pequena, uma Transcrição que não cabe leva a Reunião a `needs_split` sem chamar a LLM. Depois da divisão, cada chamada recebe um texto de Parte com estimativa menor ou igual ao orçamento da Parte, o áudio em `/audios` não é reprocessado, e os `US-id` da Reunião não se repetem.
16. Uma Reunião que falhou na transcrição chega a `transcribed` depois de "Tentar novamente", sem novo envio. Uma Reunião que falhou na geração chega a `done` depois de "Tentar novamente", com a mesma Transcrição e os mesmos Participantes, sem reprocessar o áudio.
17. Depois de "Renomear participante", todas as US daquele solicitante mostram o nome novo, nenhuma chamada à LLM acontece, e as Epics e o texto das US não mudam.
18. `pytest` roda sem GPU, sem rede e sem chave real, usando fakes para Whisper, Pyannote e provedores de LLM.
19. Cada User Story de PRD de módulo tem pelo menos um teste automatizado que a cobre.
20. Depois de um reinício do backend, nenhuma Reunião fica parada sem trabalho em andamento: todas as que estavam em `processing`, em `generating` ou em `transcribed` com Participantes confirmados aparecem em `failed`, com "processamento interrompido" (Q58, Q69).
21. `python -m snook.cli delete-user <username>` apaga o Usuário e todos os dados dele: sessões, Configurações de LLM (com as chaves cifradas), Reuniões, dados derivados das Reuniões e arquivos em `/audios`. Depois do comando, login com aquele email ou nome de usuário responde HTTP 401, e os dados de outros Usuários não mudam. Com `<username>` inexistente, o comando termina com erro e não apaga nada (Q70).
22. Com o perfil `lan` ativo, o app responde em `https://` na rede confiável. Num cliente da rede que confia na CA local, a gravação de tela funciona como em `http://localhost` (Q70, ADR-0016).

## NFRs de performance do frontend (Q70, ADR-0023)

| Id | Métrica | Meta | Como medir |
|---|---|---|---|
| NFR-01 | JS inicial (rota de login) | até 200 KB gzip | relatório do build do frontend no CI |
| NFR-02 | JS total da app | até 500 KB gzip | relatório do build do frontend no CI |
| NFR-03 | LCP em `localhost`, com CPU 4x mais lenta no DevTools (rota medida: tela de login, mesma do NFR-01; Q73) | até 2,5 s | Lighthouse manual no checkpoint |
| NFR-04 | INP nas telas de divisão e de revisão do backlog | até 200 ms | DevTools Performance. Tela de divisão: Transcrição de 2 h de fixture. Tela de revisão: backlog de fixture com 30 Epics e 200 US. |
| NFR-05 | CLS | até 0,1 | Lighthouse |
| NFR-06 | Elementos com vidro (`backdrop-filter`) visíveis ao mesmo tempo | no máximo 3 | revisão de código e de tela |
| NFR-07 | Listas da tela da Transcrição e da tela de divisão | virtualizadas: só os itens perto da área visível ficam no DOM | teste de componente com Transcrição de 2 h de fixture |
| NFR-08 | Quadros com mouse-tracking ativo | nenhum quadro acima de 16 ms por causa do efeito | DevTools Performance, checkpoint manual |

- NFR-01 e NFR-02: o CI falha se o build passar dos limites (ADR-0023).
- NFR-07 cobre `diarized-transcription` (tela da Transcrição) e `transcript-split` (tela de divisão).
- NFR-08 cobre as telas com mouse-tracking: card de login e cadastro (`auth`) e área de upload (`meetings`) (`02-architecture.md`, "Mapa de superfícies").

## Estratégia de testes (confirmada na Q32)

- **Seam principal:** API HTTP do FastAPI via `TestClient` no Pytest, SQLite temporário, pasta de áudio temporária, fakes nas interfaces de Whisper, Pyannote e LLM. Um teste por critério de aceite de módulo, do request à resposta e ao estado no banco.
- **Adapters externos:** cada adapter de LLM testado contra respostas HTTP gravadas, sem rede. Adapters de Whisper e Pyannote testados com áudio curto de fixture, em suíte separada e opcional (exige modelos).
- **Frontend e gravação de tela:** Vitest + React Testing Library + MSW. Resolvido: ADR-0015. Seam da gravação: interfaces sobre as APIs do navegador, com fakes (ver `01-prd/screen-recording.md`).
- **Comando `delete-user` (critério 21):** Pytest chama a função do comando com SQLite e pasta de áudio temporários, dois Usuários com Reuniões e arquivos, e confere o banco e a pasta depois.
- **Perfil `lan` (critério 22):** checagem manual, fora do `pytest` padrão.
- **NFRs (NFR-01 a NFR-08):** NFR-01 e NFR-02 no CI; NFR-03 a NFR-06 e NFR-08 em checagem manual a cada checkpoint de tela; NFR-07 em teste de componente do frontend.

## Índice de módulos

| Módulo | PRD | Status | Bloqueado por |
|---|---|---|---|
| `auth` | `01-prd/auth.md` | escrito | nenhum |
| `llm-providers` | `01-prd/llm-providers.md` | escrito | nenhum |
| `meetings` | `01-prd/meetings.md` | escrito | nenhum |
| `screen-recording` | `01-prd/screen-recording.md` | escrito | nenhum |
| `diarized-transcription` | `01-prd/diarized-transcription.md` | escrito | nenhum |
| `participants` | `01-prd/participants.md` | escrito | nenhum |
| `transcript-split` | `01-prd/transcript-split.md` | escrito | nenhum |
| `backlog-generation` | `01-prd/backlog-generation.md` | escrito | nenhum |
| `backlog-review` | `01-prd/backlog-review.md` | escrito | nenhum |

Build order e dependências: `00-overview.md`, seção "Capability map".

## Questões em aberto

1. Nenhuma decisão de produto pendente. Q1 a Q73 fechadas.
2. Pendências do planner: todas resolvidas. Ver `02-architecture.md`, "Respostas às decisões pendentes do spec". Inclui onde mora o comando `delete-user`, sem ciclo entre módulos (`02-architecture.md`, "Exclusão de Usuário pelo Operador").
3. **Rota do LCP (NFR-03).** Resolvido (Q73): tela de login, a mesma rota do NFR-01.
