# 01-prd/backlog-generation - PRD do módulo `backlog-generation`

> Status: completo. Decisões fechadas: Q11, Q12, Q16, Q27, Q29, Q35, Q37, Q43, Q46, Q47, Q48, Q50, Q54, Q56, Q57, Q58, Q68.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: `transcript-split` (Partes, texto e orçamento), `llm-providers` ("Provedor ativo", "Gerar"), `participants` (nomes) e `meetings` (status, duração, marca de backlog gravado). Dependente: `backlog-review`.

## Problem Statement

- Transcrição nomeada e dividida em Partes que cabem. Falta o principal: virar Epics e User Stories no formato pedido.
- Cada US precisa de prioridade, story points, critérios de aceite, solicitante e instante do pedido.
- Saída de LLM pode vir incompleta ou fora do formato.
- Usuário não quer backlog pela metade nem perder o backlog que já tinha por causa de falha.

## Solution

- Partes prontas: módulo envia cada Parte, em ordem, ao provedor ativo, com System Prompt fixo e lista de Participantes.
- Antes de cada envio, confere de novo se a Parte cabe.
- A partir da segunda Parte, LLM recebe também nomes das Epics já criadas.
- Cada resposta validada contra o formato do backlog.
- Epics de mesmo nome juntadas. `US-id` numerados na ordem.
- Só com todas as Partes certas: backlog gravado de uma vez; Reunião vai para `done`.
- Qualquer falha: Reunião vai para `failed` com motivo legível. Nada gravado. Backlog anterior não é apagado.

## User Stories

1. Como usuário, quero que a geração comece sozinha quando a reunião fica pronta para a LLM, para não precisar de outro passo.
2. Como usuário, quero receber Epics e User Stories no formato que defini, com "Como / Eu quero / Para", prioridade, story points e critérios "Dado / Quando / Então", para usar o backlog sem reescrever.
3. Como usuário, quero que cada User Story traga quem pediu e em que instante da gravação, para saber a quem recorrer e onde ouvir o pedido.
4. Como usuário, quero que uma reunião dividida gere um backlog único, sem Epics repetidas com o mesmo nome, para revisar tudo num lugar.
5. Como usuário, quero `US-id` em sequência, sem repetição, para referenciar cada história sem ambiguidade.
6. Como usuário, quero que nada seja gravado quando alguma parte falha, para não trabalhar sobre um backlog incompleto.
7. Como usuário, quero ver um motivo legível quando a geração falha (chave recusada, limite de uso, resposta fora do formato, parte grande demais), para saber se corrijo a configuração ou só tento de novo.
8. Como usuário, quero que uma regeneração que falha não apague o backlog que eu já tinha, para não perder o trabalho.
9. Como usuário, quero que o backlog seja escrito em pt-BR, para usá-lo direto com o time.
10. Como módulo do sistema (`backlog-review`), quero ler e alterar o backlog gravado de uma Reunião, para exibir, editar e exportar.

## Escopo

- Consumo do aviso "Partes prontas" de `transcript-split`, só com a Reunião em `generating`.
- System Prompt fixo e versionado no código.
- Cada chamada leva: System Prompt, lista de Participantes, texto da Parte e, a partir da segunda Parte, nomes das Epics já criadas.
- Reestimativa de cada Parte contra o orçamento do provedor lido no início, antes de cada chamada.
- Chamadas em sequência, pela interface "Gerar" de `llm-providers`, com o provedor ativo do dono da Reunião.
- Validação de cada resposta contra o schema do backlog.
- Junção de Epics por nome dentro da Reunião; numeração dos `US-id`; ligação do solicitante ao Participante.
- Gravação tudo ou nada; backlog anterior substituído só no sucesso; registro da marca de backlog gravado em `meetings`.
- Transições `generating` → `done` ou `failed` (etapa `generation`).
- Modelo de dados de Epic, User Story e critério de aceite.

Módulo sem tela e sem endpoint público. Status aparece por `meetings`; backlog, por `backlog-review`.

Campos sugeridos:
- Epic: `id`, `meeting_id`, `name`, `position`. Nome único só dentro da Reunião (Q57).
- User Story: `id`, `meeting_id`, `epic_id`, `us_number` (exibido como `US-01`), `name`, `as_a`, `i_want`, `so_that`, `priority`, `story_points`, `requested_by` (`participant_id`, opcional), `requested_at_seconds` (opcional só em US criada à mão).
- Critério de aceite: `id`, `user_story_id`, `given`, `when`, `then`, `position`.
- Marca de backlog gravado: fica em `meetings` (`backlog_saved_at`), registrada por este módulo. Distingue backlog vazio de ausência de backlog.

## Fora de escopo

- Checar tamanho e dividir em Partes. Fica em `transcript-split`.
- Exibir, editar, mover, criar, excluir e exportar o backlog. Fica em `backlog-review`.
- Renomear Participantes (Q55).
- System Prompt editável pelo usuário (Q16).
- Vincular US aos segmentos da Transcrição; US guarda só solicitante, Reunião e quando (Q12).
- Juntar Epics por semelhança de sentido ou por decisão da LLM (Q47).
- Juntar Epics de Reuniões diferentes (Q57).
- Remover US repetidas entre Partes (Q48).
- Gravar resultado parcial (Q46).
- Histórico de versões do backlog (Q30).
- Retomar sozinho geração interrompida por reinício; `meetings` leva a Reunião a `failed` (Q58).

## Restrições

| Restrição | Fonte |
|---|---|
| Formato de Epic e User Story, com "Como / Eu quero / Para" e critérios "Dado / Quando / Então"; saída em pt-BR. | rodada 1, Q11 |
| Cada US guarda só quem pediu, de qual Reunião e quando. | rodada 1, Q12 |
| System Prompt fixo e versionado no código, sem edição pelo usuário. | rodada 1, Q16 |
| Nome da Epic em texto livre, sem descrição; `US-id` sequencial por Reunião. | rodada 2, Q27 |
| Um único Participante solicitante, vazio quando não identificado; "quando" é o instante da fala, dentro da duração do áudio. | rodada 2, Q29 |
| A geração sempre usa o provedor ativo. | rodada 3, Q35 |
| Prioridade Low, Medium ou High; story points 1, 2, 3, 5, 8 ou 13; ambos sugeridos pela LLM. | rodada 3, Q37 (substitui a Q28) |
| Partes em sequência, na ordem do tempo, com System Prompt e nomes dos Participantes; a partir da segunda, nomes das Epics já criadas; falha em qualquer Parte: nada é gravado e a Reunião vai para `failed`. | rodada 5, Q46 |
| Epics de mesmo nome, sem diferenciar maiúsculas e espaços nas pontas, viram a mesma Epic, dentro da mesma Reunião. | rodada 5, Q47; Q57 |
| `US-id` na ordem das Partes e, dentro de cada uma, na ordem da LLM; "quando" absoluto; a US não guarda a Parte. | rodada 5, Q48 |
| Na regeneração, os `US-id` recomeçam em `US-01`. | rodada 5, Q50 |
| "Tentar novamente" da geração reaproveita Transcrição e nomes e chama a LLM de novo. | Q54 |
| Backlog anterior substituído só no sucesso; resposta inválida sem nova chamada automática; solicitante desconhecido fica vazio; Epic vazia não é gravada; geração sem US leva a `done`; `US-100` com três dígitos. | Q56 |
| "Cancelar divisão" depende de backlog gravado; a marca precisa existir fora deste módulo. | Q68 |
| Nenhum segredo em respostas da API, logs ou mensagens de erro. | 01-prd, RT-02 |
| Nenhuma chamada recebe Parte cuja estimativa passe do orçamento. | 01-prd, RT-10 |

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Consome** "Partes prontas" de `transcript-split`. Lê Partes em ordem, com texto ("Partes" e "Texto da Parte"). Usa "Orçamento da Parte" para reestimar cada uma.
- **Consome** de `participants`: "Participantes" (nomes e `id`).
- **Consome** de `llm-providers`: "Provedor ativo" (lido uma vez, no início), "Estimar tokens" e "Gerar" (uma chamada por Parte). Trata os erros tipados de `llm-providers`.
- **Consome** de `meetings`: status; duração do áudio; "Atualizar status" para `generating` → `done` e `generating` → `failed` com etapa `generation`; "Registrar backlog gravado", na mesma transação em que grava backlog com sucesso.
- **Backlog**: dado `id` da Reunião, `backlog-review` lê e altera Epics, User Stories e critérios. Tabelas são deste módulo. Regras de edição (Q47, Q49, Q57) no PRD de `backlog-review`.
- **Próximo número de US**: dado `id` da Reunião, devolve o próximo `us_number` depois do maior existente (Q49). `backlog-review` usa na criação manual.
- **Exclusão**: Epics, US e critérios ligados à Reunião somem com ela.

## Schema da resposta da LLM

LLM devolve JSON. Campos em inglês; conteúdo em pt-BR. Planner pode ajustar nomes e estrutura, desde que os critérios de validação continuem verificáveis.

```json
{
  "epics": [
    {
      "name": "Cadastro de clientes",
      "user_stories": [
        {
          "name": "Cadastrar cliente pessoa física",
          "as_a": "atendente",
          "i_want": "cadastrar um cliente com CPF",
          "so_that": "eu possa abrir pedidos em nome dele",
          "priority": "High",
          "story_points": 5,
          "requested_by": "Ana",
          "requested_at": "00:42:10",
          "acceptance_criteria": [
            { "given": "um CPF válido", "when": "eu salvo o cadastro", "then": "o cliente aparece na lista" }
          ]
        }
      ]
    }
  ]
}
```

## Critérios de aceite

Nos testes, "Gerar" de `llm-providers` é fake: devolve respostas prontas e registra cada chamada.

### Fluxo

1. Ao receber "Partes prontas" de uma Reunião com Parte única e resposta válida, o módulo faz exatamente uma chamada a "Gerar", grava Epics, US e critérios, e leva a Reunião a `done`.
2. Com 3 Partes, o módulo faz 3 chamadas, na ordem das Partes, cada uma só depois da anterior terminar.
3. Cada chamada leva o System Prompt, a lista de nomes dos Participantes e o texto da Parte devolvido por "Texto da Parte", sem alteração.
4. A primeira chamada não leva nomes de Epics. A segunda e as seguintes levam os nomes das Epics criadas pelas respostas anteriores da mesma geração.
5. O provedor ativo e o modelo são lidos uma vez, no início. Todas as chamadas da mesma geração usam o mesmo provedor e modelo, mesmo que o usuário troque o provedor ativo durante a geração.
6. A geração usa a configuração de LLM do Usuário dono da Reunião, nunca a de outro Usuário.

### Validação da resposta

7. Uma resposta válida é gravada campo a campo: nome da Epic, nome da US, `as_a`, `i_want`, `so_that`, prioridade, story points, critérios na ordem recebida, solicitante e instante.
8. A prioridade é aceita sem diferenciar maiúsculas (`high`, `HIGH`) e gravada como `Low`, `Medium` ou `High`. Outro valor torna a resposta inválida. (Regra de leitura tolerante da resposta; o planner pode ampliá-la sem mudar os valores gravados.)
9. Story points fora de 1, 2, 3, 5, 8 e 13 tornam a resposta inválida.
10. Uma US sem critério de aceite, ou com `given`, `when` ou `then` vazio, torna a resposta inválida.
11. Nome de Epic, nome de US, `as_a`, `i_want` ou `so_that` vazio torna a resposta inválida.
12. `requested_at` em `hh:mm:ss` dentro de 0 e a duração do áudio é gravado em segundos. Fora desse intervalo, ou em outro formato, torna a resposta inválida.
13. `requested_by` igual ao nome de um Participante da Reunião, sem diferenciar maiúsculas e espaços nas pontas, liga a US a esse Participante. Nome desconhecido, vazio ou ausente deixa o solicitante vazio, sem invalidar a resposta.
14. Resposta que não é JSON, ou que não segue o schema, é inválida.
15. Uma resposta inválida em qualquer Parte leva a Reunião a `failed`, com etapa `generation` e mensagem que cita a Parte e o motivo. Nada é gravado, e o módulo não faz nova chamada automática.

### Junção e numeração

16. Na mesma Reunião, Epics com o mesmo nome, sem diferenciar maiúsculas e espaços nas pontas, viram uma só Epic, dentro de uma Parte e entre Partes. O nome gravado é o da primeira ocorrência, sem espaços nas pontas. Epics de outras Reuniões, mesmo com o mesmo nome, não são afetadas.
17. As US de Epics juntadas ficam todas na Epic resultante, na ordem em que chegaram.
18. Os `US-id` vão de `US-01` em diante, sem lacunas, na ordem das Partes e, dentro de cada Parte, na ordem da resposta. Não há `US-id` repetido na Reunião.
19. A partir da centésima US, o `US-id` segue com três dígitos (`US-100`).
20. Uma Epic sem nenhuma US não é gravada.
21. Uma geração válida sem nenhuma US leva a Reunião a `done` com backlog gravado e vazio.

### Tudo ou nada e regeneração

22. Com 3 Partes, se a chamada da Parte 2 falha, nada das Partes 1 e 2 é gravado. A Parte 3 não é chamada, e a Reunião vai para `failed` com etapa `generation`.
23. Numa regeneração bem-sucedida, o backlog anterior da Reunião, com as edições manuais, é substituído pelo novo, e os `US-id` recomeçam em `US-01` (Q50).
24. Numa regeneração que falha, o backlog anterior permanece intacto, e a Reunião vai para `failed` com etapa `generation`.
25. A gravação de um backlog acontece numa única transação. Um erro no meio da gravação não deixa backlog parcial.

### Erros do provedor

26. Cada erro tipado de "Gerar" (credencial recusada, provedor inacessível, modelo inexistente, limite de contexto excedido, limite de uso) leva a Reunião a `failed` com etapa `generation` e uma mensagem em pt-BR própria do tipo. A mensagem de credencial recusada aponta para a tela de configurações.
27. Nenhuma mensagem de erro, log ou registro gravado contém a chave do provedor.
28. Se a Reunião é excluída durante a geração, nada é gravado depois da exclusão.
29. Depois de "Tentar novamente" da etapa `generation`, uma nova geração bem-sucedida leva a Reunião a `done` com a mesma Transcrição e os mesmos Participantes.

### System Prompt

30. O texto do System Prompt fica num arquivo versionado no repositório. Nenhuma rota da API o lê ou o altera.
31. O System Prompt pede saída em pt-BR, no schema da resposta, com prioridade em Low, Medium ou High, story points na escala do formato, solicitante entre os nomes de Participantes fornecidos e instante absoluto em `hh:mm:ss`. Um teste de snapshot do texto falha quando o prompt muda sem o snapshot ser atualizado no mesmo commit.

### Reestimativa e idempotência

32. Antes de cada chamada a "Gerar", o módulo reestima o texto da Parte com o modelo lido no início da geração e compara com o orçamento desse provedor ("Orçamento da Parte"). Se a Parte não cabe, a Reunião vai para `failed` com etapa `generation` e mensagem que cita a Parte e pede para dividir de novo ou trocar de modelo. Essa Parte e as seguintes não são chamadas, e nada é gravado.
33. Um aviso "Partes prontas" recebido com a Reunião fora de `generating` é ignorado: nenhuma chamada a "Gerar" é feita, nada é gravado e o status não muda. Um segundo aviso para a mesma geração também é ignorado.

### Marca de backlog gravado (Q68)

34. Toda gravação bem-sucedida de backlog, inclusive vazio, chama "Registrar backlog gravado" de `meetings` na mesma transação. Depois disso, "Ler marcas" de `meetings` informa backlog gravado. Uma geração que falha não registra a marca.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** Pytest com SQLite temporário e Reuniões montadas no setup em `generating`, com Participantes e Partes fake. Aviso "Partes prontas" disparado no próprio teste. Status conferido por `GET /meetings/{id}` via `TestClient`; backlog pela interface "Backlog" ou direto no banco. "Gerar", "Provedor ativo" e "Estimar tokens" são fakes. Cobre critérios 1 a 34.
- **Respostas inválidas (critérios 8 a 15):** tabela de respostas fake, uma por regra.
- **Provedores reais:** suíte separada e opcional, fora do `pytest` padrão, com chaves reais em variáveis de ambiente e Transcrição curta de fixture. Confere, para cada um dos quatro provedores, que a resposta passa na validação (critério transversal 3).

## Questões em aberto

1. Para o planner:
   - onde o System Prompt mora, se `transcript-split` precisar do tamanho dele para a reserva do orçamento (sem ciclo);
   - modo JSON ou saída estruturada de cada provedor;
   - timeout por chamada e tempo máximo de geração com várias Partes;
   - como `backlog-review` altera as tabelas deste módulo (repositório compartilhado ou interface);
   - como registrar a geração em andamento para o critério 33 (por exemplo identificador de geração no aviso);
   - transação entre módulos da gravação do backlog com "Registrar backlog gravado" de `meetings` (mesma conexão SQLite, unidade de trabalho compartilhada ou outro mecanismo).
