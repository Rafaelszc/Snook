# 01-prd/llm-providers - PRD do módulo `llm-providers`

> Status: completo. Decisões fechadas: Q15, Q22, Q23, Q33, Q34, Q35, Q43, Q51, Q56, Q60, Q63, Q64.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: `auth`. Dependentes: `participants`, `transcript-split` e `backlog-generation`.

## Problem Statement

- Usuário quer gerar backlog com a conta de LLM que já usa: OpenAI, Anthropic, DeepSeek ou Ollama próprio.
- App precisa da chave dele. Chave é segredo caro: quem vê gasta na conta dele.
- Antes de processar reunião, usuário precisa saber se a configuração funciona e qual provedor será usado.

## Solution

- Tela de configurações lista os quatro provedores.
- Por provedor: chave (ou URL, no Ollama), modelo e janela de contexto. Modelo e janela têm padrão sugerido.
- "Testar conexão" antes de salvar. App só salva configuração que conectou.
- Chave cifrada no SQLite. Tela mostra só máscara.
- Usuário marca um provedor ativo, edita ou remove configurações.
- Para os outros módulos: interface única de geração, estimativa de tokens e janela de contexto do provedor ativo.

## User Stories

1. Como usuário, quero ver os quatro provedores na tela de configurações, cada um com seu estado (não configurado, configurado, ativo), para saber o que já preparei.
2. Como usuário, quero informar a chave de API e o modelo da OpenAI, da Anthropic ou da DeepSeek, para usar minha conta nesses provedores.
3. Como usuário, quero informar a URL e o modelo do meu Ollama, sem chave, para usar um modelo que roda na minha máquina ou na minha rede.
4. Como usuário, quero ver um modelo padrão sugerido para cada provedor, e poder trocá-lo por qualquer nome, para começar rápido sem perder a liberdade de escolha.
5. Como usuário, quero informar a janela de contexto do modelo, com um padrão sugerido, para que o app saiba quando dividir uma reunião longa.
6. Como usuário, quero testar a conexão antes de salvar, para descobrir na hora se a chave, a URL ou o modelo estão errados.
7. Como usuário, quero que o app recuse salvar uma configuração que não conecta, para não descobrir o erro só no meio do processamento de uma reunião.
8. Como usuário, quero ver só a máscara da chave depois de salvá-la, para que ninguém a copie da minha tela.
9. Como usuário, quero que a primeira configuração que eu salvar já fique ativa, para não precisar de um passo extra.
10. Como usuário, quero marcar um provedor como ativo, deixando o anterior inativo, para escolher qual interpreta minhas reuniões.
11. Como usuário, quero trocar o modelo, a janela de contexto ou a chave de um provedor já salvo, sem redigitar a chave quando ela não muda, para acompanhar mudanças na minha conta.
12. Como usuário, quero remover a configuração de um provedor, para que o app não guarde mais a minha chave.
13. Como módulo do sistema (`participants`, `transcript-split`, `backlog-generation`), quero consultar o provedor ativo do usuário, com modelo e janela de contexto, e estimar os tokens de um texto, para exibir o provedor e decidir se a Transcrição cabe numa chamada.
14. Como módulo do sistema, quero enviar System Prompt e conteúdo ao provedor ativo por uma interface única e receber a resposta ou um erro tipado, para não tratar cada provedor de um jeito.

## Escopo

- Tela de Configuração de LLM com os quatro provedores.
- Campos por provedor:
  - OpenAI, Anthropic, DeepSeek: chave, modelo, janela de contexto.
  - Ollama: URL, modelo, janela de contexto, sem chave.
- Padrões sugeridos de modelo e janela por provedor (valores do planner).
- "Testar conexão" sem salvar; validação da conexão ao salvar; limite de tentativas (Q60).
- Regras da URL do Ollama (Q60, Q63).
- Chave cifrada com a chave-mestra do `.env`; exibição só por máscara (Q64).
- Um único provedor ativo por Usuário; primeira configuração salva fica ativa.
- Edição e remoção de configurações.
- Interface única de geração, estimativa de tokens e consulta ao provedor ativo, para uso interno.
- Adapters para OpenAI, Anthropic, DeepSeek e Ollama.

Endpoints sugeridos (planner confirma): `GET /llm-configs`, `PUT /llm-configs/{provider}`, `POST /llm-configs/{provider}/test`, `POST /llm-configs/{provider}/activate`, `DELETE /llm-configs/{provider}`. `{provider}` é um de `openai`, `anthropic`, `deepseek` e `ollama`.

## Fora de escopo

- Provedores além dos quatro (Q15).
- Lista de modelos vinda da API do provedor; modelo é texto livre (Q34).
- Escolha de provedor por geração; geração sempre usa o ativo (Q35).
- Configuração global ou compartilhada entre Usuários (Q33).
- Chaves de LLM no `.env` (Q33).
- URL do Ollama com credenciais embutidas (Q63).
- System Prompt, schema da saída e validação do backlog. Ficam em `backlog-generation`.
- Decidir e fazer a divisão de Reunião longa. Fica em `transcript-split`.
- Controle de custo ou de cota de uso.

## Restrições

| Restrição | Fonte |
|---|---|
| Provedores: OpenAI, Anthropic, DeepSeek e Ollama. | rodada 1, Q15 |
| Chaves nunca expostas. | rodada 1, Q15 |
| Tela de configurações onde o usuário inclui a chave e diz qual provedor fica ativo. | rodada 2, Q22 |
| Ollama externo, com URL e modelo configuráveis na tela. | rodada 2, Q23 |
| Configuração por Usuário no SQLite; chave cifrada com chave-mestra do `.env`; só máscara na UI após salvar. | rodada 3, Q33 |
| Modelo em texto livre com padrão sugerido; "Testar conexão" obrigatório antes de salvar; um único provedor ativo por vez; sem provedor ativo, a geração é bloqueada com mensagem que aponta para a tela de configurações. | rodada 3, Q34 |
| A geração sempre usa o provedor ativo. | rodada 3, Q35 |
| A checagem de Reunião longa compara a Transcrição real com a janela de contexto do modelo ativo. | rodada 4, Q43 |
| Janela de contexto por provedor, em tokens, com padrão sugerido e editável. | rodada 5, Q51 |
| Primeira configuração salva fica ativa automaticamente. | rodada 5, Q51 |
| Editar sem nova chave mantém a chave atual, com novo teste de conexão antes de salvar. | rodada 5, Q51 |
| Remover uma configuração apaga a chave cifrada; remover o provedor ativo deixa o Usuário sem provedor ativo. | rodada 5, Q51 |
| Confirmação antes de remover uma configuração. | Q56 |
| App somente local. URL do Ollama: qualquer host, inclusive rede privada, só `http` ou `https`, sem seguir redirecionamento. Limite de tentativas no "Testar conexão". | Q60 |
| URL do Ollama com credenciais embutidas é recusada. | Q63 |
| Chave com menos de 12 caracteres aparece só como `...`. | Q64 |
| Cada Usuário vê só os próprios dados. | rodada 2, Q19 |
| SQLite num volume Docker nomeado, fora do git. | rodadas 3 e 4, Q33 e Q40 |
| `pytest` sem rede e sem chave real. | rodada 2, Q32 |
| FastAPI, SQLite, Pytest, React + TypeScript + shadcn/ui. | briefing |

## Contrato com outros módulos

Interface interna (nomes do planner):

- **Provedor ativo**: dado o Usuário, devolve provedor, modelo e janela de contexto, ou erro "sem provedor ativo".
- **Estimar tokens**: dado o Usuário e um texto, devolve contagem estimada de tokens para o modelo ativo. Método: planner.
- **Gerar**: dado o Usuário, o System Prompt e o conteúdo, chama o provedor ativo e devolve o texto da resposta. Aceita pedir saída em JSON quando o provedor suporta. Chamadas ao Ollama também não seguem redirecionamento.
- **Erros tipados**, no mínimo: sem provedor ativo; chave ou credencial recusada; provedor inacessível (rede, URL, redirecionamento ou timeout); modelo inexistente; limite de contexto excedido; limite de uso (rate limit) do provedor.
- Chave decifrada existe só dentro do módulo, no momento da chamada. Nenhuma função da interface devolve a chave.

## Critérios de aceite

### Listagem

1. `GET /llm-configs` de um Usuário sem nenhuma configuração lista os quatro provedores como não configurados. Cada um vem com o modelo padrão e a janela de contexto padrão sugeridos.
2. `GET /llm-configs` mostra, para cada provedor configurado: modelo, janela de contexto, se está ativo e, nos provedores com chave, só a máscara.
3. A máscara expõe no máximo os 3 primeiros e os 4 últimos caracteres da chave, no formato do exemplo da Q33 (`sk-...abcd`). Chaves com menos de 12 caracteres aparecem só como `...`, sem nenhum caractere da chave (Q64).
4. A URL do Ollama aparece por inteiro, porque não é segredo. Como a URL nunca contém credenciais (critério 40), não há o que mascarar nela.

### Testar conexão

5. `POST /llm-configs/{provider}/test` com chave e modelo válidos responde sucesso e não grava nada no SQLite.
6. O mesmo teste com chave recusada pelo provedor responde falha com o motivo "credencial recusada", e nada é gravado.
7. O teste do Ollama com URL inacessível responde falha com o motivo "provedor inacessível".
8. O teste com modelo inexistente no provedor responde falha com o motivo "modelo inexistente".
9. A chave enviada no teste não aparece na resposta nem nos logs.

### Salvar

10. `PUT /llm-configs/{provider}` refaz o teste de conexão no servidor. Se a conexão falhar, responde HTTP 422 com o motivo, e a configuração anterior (ou a ausência dela) não muda.
11. Com conexão válida, a configuração é gravada e a resposta traz só a máscara da chave.
12. O valor gravado no SQLite para a chave difere da chave enviada, e decifrá-lo com a chave-mestra do `.env` devolve a chave enviada.
13. Primeira configuração do Ollama sem URL, ou primeira configuração de OpenAI, Anthropic ou DeepSeek sem chave, é recusada com HTTP 422.
14. Configuração sem modelo usa o modelo padrão sugerido do provedor.
15. Janela de contexto ausente usa o padrão sugerido do provedor. Valor informado precisa ser inteiro positivo; caso contrário, a configuração é recusada com HTTP 422.
16. A primeira configuração salva por um Usuário fica ativa automaticamente. Salvar uma segunda configuração não muda o provedor ativo.
17. Editar uma configuração salva sem enviar nova chave mantém a chave atual. O teste de conexão no servidor usa a chave atual com os novos campos.
18. Editar uma configuração enviando nova chave substitui a chave cifrada, depois de a conexão com a nova chave passar no teste.

### Provedor ativo

19. `POST /llm-configs/{provider}/activate` num provedor configurado o torna ativo, e o provedor ativo anterior do mesmo Usuário deixa de ser ativo.
20. Em qualquer momento, um Usuário tem no máximo um provedor ativo.
21. Ativar um provedor não configurado é recusado com HTTP 409, e o provedor ativo não muda.
22. A interface "Provedor ativo" devolve o erro "sem provedor ativo" para Usuário sem provedor ativo. Esse erro carrega uma mensagem que aponta para a tela de configurações.

### Remover

23. `DELETE /llm-configs/{provider}` apaga a configuração e a chave cifrada do SQLite.
24. Remover o provedor ativo deixa o Usuário sem provedor ativo. Nenhum outro provedor é ativado sozinho.
25. Remover um provedor não configurado responde HTTP 404.

### Isolamento e segredos

26. A configuração de um Usuário não aparece, não muda e não é usada nas requisições de outro Usuário.
27. Com chaves de teste conhecidas, nenhuma resposta da API, nenhum log da aplicação e nenhuma coluna do SQLite contém a chave em texto claro, inclusive quando o provedor responde erro.
28. Requisição sem autenticação a qualquer rota de `/llm-configs` recebe HTTP 401.

### Interface de geração

29. Para cada um dos quatro provedores, "Gerar" com o adapter ligado a respostas HTTP gravadas devolve o texto da resposta do provedor.
30. Cada adapter traduz para os erros tipados do contrato as respostas gravadas de credencial recusada, modelo inexistente, limite de contexto, rate limit e falha de rede.
31. "Gerar" sempre usa o provedor ativo do Usuário, com o modelo salvo na configuração dele.
32. "Estimar tokens" devolve um inteiro positivo para texto não vazio, e um valor maior para um texto que contém outro.

### Frontend

33. A tela de configurações mostra os quatro provedores, com estado, máscara da chave, modelo, janela de contexto e indicação do ativo.
34. O botão "Salvar" fica desabilitado até um "Testar conexão" bem-sucedido com os valores atuais do formulário.
35. Erros de teste e de gravação aparecem na tela com o motivo devolvido pela API.
36. O campo de chave nunca é pré-preenchido com a chave salva. Ele mostra a máscara como referência, e deixá-lo vazio na edição mantém a chave atual.
37. Remover uma configuração pede confirmação na tela antes de chamar a API.

### URL do Ollama e limites (Q60, Q63)

38. A URL do Ollama aceita qualquer host, inclusive `localhost`, `host.docker.internal` e endereços de rede privada, desde que o esquema seja `http` ou `https`. Outro esquema (por exemplo `file:` ou `ftp:`) é recusado com HTTP 422 no teste e no salvar.
39. O teste de conexão, o salvar e o "Gerar" do Ollama não seguem redirecionamento. Uma resposta de redirecionamento vira falha com o motivo "provedor inacessível", e nada é gravado.
40. URL do Ollama com credenciais embutidas (`http://usuario:senha@host`) é recusada com HTTP 422 no teste e no salvar, para que a URL exibida nunca carregue segredo (Q63).
41. Depois de N chamadas a "Testar conexão" ou a salvar (que também testa) dentro de uma janela de tempo, as seguintes recebem HTTP 429 até a janela passar, e nenhuma chamada ao provedor é feita. N e a janela vêm de configuração (valores com o planner).

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário, chave-mestra de teste. Adapters trocados por fake configurável (sucesso, credencial recusada, inacessível, modelo inexistente, redirecionamento). Cobre critérios 1 a 28, 31 e 38 a 41.
- **Adapters (critérios 29, 30 e 32):** cada adapter roda contra respostas HTTP gravadas, sem rede e sem chave real. Ferramenta de gravação: planner. Critério 39 também roda no adapter real do Ollama, com resposta gravada de redirecionamento.
- **Segredos (critérios 12 e 27):** teste lê SQLite direto e captura logs (`caplog`), buscando o texto da chave de teste.
- **Frontend (critérios 33 a 37):** framework não decidido. Questão para o planner.

## Questões em aberto

1. Para o planner (02-architecture e 03-security):
   - algoritmo de cifra e nome da variável da chave-mestra;
   - destino das chaves salvas se a chave-mestra mudar ou se perder;
   - método de estimativa de tokens por provedor;
   - padrões de modelo e de janela de contexto por provedor;
   - como o teste de conexão valida cada provedor (por exemplo listagem de modelos ou chamada mínima);
   - timeout das chamadas;
   - valores do limite de "Testar conexão" e chave da contagem;
   - ferramenta de gravação de respostas HTTP;
   - nível ASVS (Q60).
2. Códigos HTTP 404, 409, 422 e 429 e endpoints são sugestões, não decisões. Planner pode ajustar, desde que o critério continue verificável.
3. Rede do Ollama: URL precisa ser alcançável de dentro do container (por exemplo `host.docker.internal`, não `localhost`). Fica para o planner e o README.
