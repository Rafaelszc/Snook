# 01-prd/auth - PRD do módulo `auth`

> Status: completo. Decisões fechadas: Q2, Q19, Q20, Q39, Q56, Q60.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`.
> Depende de: nenhum módulo. Dependentes: todos os módulos com rota (`llm-providers`, `meetings`, `diarized-transcription`, `participants`, `transcript-split`, `backlog-review`).

## Problem Statement

- App guarda gravações, transcrições, backlogs e chaves de LLM de cada pessoa.
- Sem contas, qualquer um com acesso ao servidor vê e usa tudo de todos.
- Cada pessoa precisa de espaço próprio, protegido por senha.

## Solution

- Visitante cria conta na tela inicial: email, nome de usuário, senha. Já entra autenticado.
- Login por email ou nome de usuário, mais senha. Logout quando quiser.
- Senha só como hash bcrypt. Tentativas de login limitadas.
- Demais rotas exigem login. Cada Usuário vê só os próprios dados.

## User Stories

1. Como visitante, quero criar uma conta com email, nome de usuário e senha, para usar o app.
2. Como visitante, quero ver por que meu cadastro foi recusado (email inválido, email ou nome de usuário já usado, nome de usuário fora da regra, senha curta), para corrigir e tentar de novo.
3. Como visitante, quero já estar autenticado ao concluir o cadastro, para não digitar os dados de novo no login.
4. Como usuário, quero entrar com meu email e senha, para acessar minhas reuniões.
5. Como usuário, quero entrar com meu nome de usuário e senha, para não precisar digitar o email.
6. Como usuário, quero sair da conta, para que outra pessoa no mesmo navegador não use minha sessão.
7. Como usuário, quero ser levado à tela de login quando abro uma página protegida sem estar autenticado, para não ver telas vazias ou erros.
8. Como usuário, quero que o app limite tentativas seguidas de login, para dificultar que alguém adivinhe minha senha.
9. Como módulo do sistema (`meetings`, `llm-providers` e outros), quero obter o Usuário autenticado de cada requisição, para filtrar e gravar dados em nome dele.

## Escopo

- Cadastro aberto, com login automático ao concluir (Q20, Q39).
- Login por email ou nome de usuário, mais senha (Q20).
- Limite de tentativas de login (Q60).
- Logout.
- Consulta do Usuário autenticado.
- Proteção de todas as rotas, exceto cadastro e login (RT-03).
- Contrato de identidade para demais módulos (seção abaixo).
- Telas de cadastro e login; redirecionamento ao login.

Endpoints sugeridos (planner confirma): `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.

## Fora de escopo

- Recuperação de senha (Q20).
- Troca de senha, edição de perfil, exclusão de conta, verificação de email (Q39).
- Papéis e permissões (admin, operador). Todo Usuário tem os mesmos direitos sobre os próprios dados.
- Exposição à internet (Q60).

## Restrições

| Restrição | Fonte |
|---|---|
| Conta com email, nome de usuário e senha. | rodada 1, Q2 |
| Senha armazenada no banco só como hash bcrypt. | rodada 1, Q2 |
| Cadastro aberto na tela inicial. | rodada 2, Q20 |
| Login por email ou nome de usuário; email e nome de usuário únicos. | rodada 2, Q20 |
| Senha com no mínimo 8 caracteres. | rodada 2, Q20 |
| Sem recuperação de senha na primeira versão. | rodada 2, Q20 |
| Cada Usuário vê só os próprios dados; recurso de outro Usuário responde como inexistente. | rodada 2, Q19 |
| Unicidade de email e nome de usuário sem diferenciar maiúsculas de minúsculas. | rodada 3, Q39 |
| Nome de usuário com 3 a 30 caracteres: letras, dígitos, `_`, `.` e `-`. | rodada 3, Q39 |
| Login automático após o cadastro. | rodada 3, Q39 |
| Login sem diferenciar maiúsculas no email e no nome de usuário. | Q56 |
| Banco SQLite dentro do container e fora do git. | rodada 3, Q33 |
| App somente local; limite de tentativas no login (valores com o planner). | Q60 |
| FastAPI, SQLite, Pytest, React + TypeScript + shadcn/ui. | briefing |

## Contrato com outros módulos

- `auth` entrega, a cada requisição autenticada, o Usuário atual (no mínimo `id`). No FastAPI: dependência reutilizável (nome do planner).
- Rota protegida sem autenticação válida: HTTP 401, antes de qualquer lógica do módulo.
- Cada módulo dono de dados grava o `id` do Usuário e filtra por ele. Teste de isolamento (HTTP 404 para recurso de outro Usuário) fica no PRD de cada módulo.

## Critérios de aceite

### Cadastro

1. Cadastro com email válido, nome de usuário livre e dentro da regra, e senha de 8 ou mais caracteres cria o Usuário e responde com `id`, `email` e `username`.
2. Cadastro com senha de 7 caracteres ou menos é recusado com HTTP 422 e mensagem sobre o tamanho mínimo, e nenhum Usuário é criado.
3. Cadastro com email já usado por outro Usuário é recusado com HTTP 409 e mensagem sobre o email, e nenhum Usuário é criado.
4. Cadastro com nome de usuário já usado é recusado com HTTP 409 e mensagem sobre o nome de usuário, e nenhum Usuário é criado.
5. Cadastro com email em formato inválido é recusado com HTTP 422, e nenhum Usuário é criado.
6. A unicidade de email e de nome de usuário não diferencia maiúsculas de minúsculas. Com `Ana@x.com` cadastrado, o cadastro de `ana@x.com` é recusado com HTTP 409. Com `Ana` cadastrado, o cadastro de `ana` é recusado com HTTP 409.
7. Nome de usuário com menos de 3 ou mais de 30 caracteres, ou com caractere fora de letras, dígitos, `_`, `.` e `-`, é recusado com HTTP 422, e nenhum Usuário é criado.
8. Após o cadastro bem-sucedido, a mesma sessão já acessa `GET /auth/me` sem passar pelo login.

### Senha

9. A coluna de senha do Usuário guarda um hash bcrypt, e `bcrypt.checkpw` com a senha original retorna verdadeiro.
10. O texto da senha não aparece no SQLite, nos logs da aplicação nem em nenhuma resposta da API.
11. Nenhuma resposta da API devolve o hash da senha.

### Login e logout

12. Login com email cadastrado e senha correta autentica o Usuário.
13. Login com nome de usuário cadastrado e senha correta autentica o Usuário.
14. Login com email ou nome de usuário em caixa diferente da cadastrada (por exemplo `ANA@X.COM`) e senha correta autentica o Usuário.
15. Login com senha errada responde HTTP 401 e não autentica.
16. Login com email ou nome de usuário inexistente responde HTTP 401 e não autentica.
17. Após o logout, a mesma sessão recebe HTTP 401 em rota protegida.

### Rotas protegidas

18. `GET /auth/me` com Usuário autenticado responde `id`, `email` e `username` desse Usuário, sem senha nem hash.
19. `GET /auth/me` sem autenticação responde HTTP 401.
20. Cadastro e login respondem sem exigir autenticação.
21. Não existe rota nem tela de recuperação de senha, troca de senha, edição de perfil ou exclusão de conta.

### Frontend

22. A tela inicial oferece cadastro e login.
23. Após o cadastro bem-sucedido, o frontend leva o usuário direto à área autenticada.
24. Ao abrir uma página protegida sem autenticação, o frontend leva o usuário à tela de login.
25. Erros de cadastro e login aparecem na tela com a mensagem devolvida pela API.
26. Após o logout, o frontend volta à tela de login.

### Limite de tentativas (Q60)

27. Depois de N tentativas de login com falha dentro de uma janela de tempo, as tentativas seguintes recebem HTTP 429 até a janela passar, mesmo com a senha correta. N e a janela vêm de configuração (valores com o planner). Um login correto antes do limite zera a contagem.

## Estratégia de testes (seam confirmado na Q32)

- **Seam:** API HTTP via `TestClient` no Pytest, SQLite temporário. Cobre critérios 1 a 21 e 27, um teste por critério. Critério 27 usa limite pequeno e relógio falso por configuração de teste.
- **Senha:** critério 9 lê o registro direto no SQLite de teste e confere com `bcrypt.checkpw`. Critério 10 captura logs (`caplog`) e busca o texto da senha.
- **Isolamento:** dependência de Usuário atual testada aqui (401). O 404 entre Usuários fica em cada módulo dono de dados.
- **Frontend (critérios 22 a 26):** framework não decidido. Questão para o planner.
- Custo do bcrypt pode cair nos testes para suíte rápida. Decisão do planner.

## Questões em aberto

1. Para o planner (02-architecture e 03-security):
   - mecanismo de sessão (cookie ou JWT) e duração;
   - mensagem genérica de login, para não revelar se o email existe;
   - valores do limite de tentativas e chave da contagem (conta, IP ou ambos);
   - custo do bcrypt;
   - tamanho máximo da senha (bcrypt usa só os primeiros 72 bytes);
   - nível ASVS de referência (Q60).
2. Para o 03-security: HTTP 409 do cadastro (critérios 3 e 4) revela email ou nome de usuário existente. Risco aceito: app roda somente local, sem exposição à internet (Q60). Se a implantação mudar, rever.
3. Códigos HTTP 409, 422 e 429 seguem padrão FastAPI e REST. Planner pode ajustar, desde que o critério continue verificável.
