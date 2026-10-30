# CONTRIBUTING

Contribuições seguem **Spec-Driven Development** (SDD) com GitFlow. Código só entra via tarefa do `tasks/todo.md`.

## Fluxo SDD

Spec → Plano → Tarefas → Código. Não há exceções.

1. **Spec**: decisão de comportamento → atualiza `docs/specs/`.
2. **Arquitetura**: decisão técnica nova → ADR em `docs/specs/adrs/`.
3. **Plano**: estrutura em `tasks/plan.md`.
4. **Tarefas**: checklist de aceite em `tasks/todo.md`.
5. **Código**: implementa uma tarefa. Fora de tarefa, PR é rejeitado.

Detalhes em `AGENTS.md` e `docs/specs/`.

## Agentes Recomendados

Snook usa agentes especializados para manter a qualidade. Chame pelo nome no Claude Code (`@spec-writer` etc.). `/code-review`, `/simplify` e `/web-design-guidelines` são skills.

### Pipeline de specs (Especificação)

Rode **nesta ordem** se mudando requisitos ou arquitetura:

| Agente | Chamada | Uso |
|---|---|---|
| **spec-writer** | `@spec-writer` | Escreve `00-overview.md` e `01-prd.md` a partir de um briefing fechado. Spec inicial ou mudança de escopo. |
| **spec-reviewer** | `@spec-reviewer` | Revisa specs contra código e ADRs. Use antes do planner. |
| **planner** | `@planner` | Transforma spec aprovado em `tasks/plan.md` e ADRs. Apenas com spec validado. |
| **spec-reviewer** (2ª) | `@spec-reviewer` | Revisa plano e ADRs novos contra specs. Use depois do planner. |
| **task-breaker** | `@task-breaker` | Quebra plano em tarefas no `tasks/todo.md`. Apenas com plano aprovado. |

**Fluxo exemplo:** mudança de requisito → `@spec-writer` → `@spec-reviewer` → `@planner` → `@spec-reviewer` → `@task-breaker`.

### Apoio na implementação

| Skill | Uso |
|---|---|
| `/code-review` | Análise de correctness bugs no diff. Use em PRs críticas ou antes de merge. |
| `/simplify` | Limpeza de reuso/simplificação/eficiência. Código quality apenas. |
| `/web-design-guidelines` | Revisão de telas e UI em checkpoint. |
| `frontend-*` skills | Usar conforme `tasks/plan.md`, "Skills de frontend por tarefa". |

Não siga `@spec-writer` → `@planner` sem aprovação do usuário. Plano precisa validação humana.

## GitFlow

### Setup inicial

```bash
git clone <repo>
cd Snook
git checkout develop          # branch de integração
git pull origin develop
```

### Criar feature

```bash
git checkout develop
git pull origin develop --rebase
git checkout -b feature/descricao-breve

# Trabalhe, commit, push
git push -u origin feature/descricao-breve
```

**Padrão de branch**: `feature/nome-feature` (sem `/` no nome, `-` entre palavras).

### Commits

Boas práticas:

- **Escopo pequeno**: um commit = uma mudança lógica. Não misture refactoring com feature.
- **Primeira linha**: imperativo, ≤50 char, sem ponto, reflete a mudança principal.
- **Body** (opcional mas recomendado): deixe linha em branco, depois explique o **por quê** (não o **quê**, já está no diff).
- **Sempre imperativo**: "Add X", não "Added X" ou "Adds X".
- **Sem floreio**: sem emojis, sem artigos desnecessários.
- **Tarefa rastreável**: commit reflete spec ou tarefa do `tasks/todo.md`. Sem "fix typo in comment" ou "ajusta ordem de imports".
- **Mensagem em inglês**: nomes de código, funções, módulos. Contexto em português se necessário.

Exemplo:

```
add(auth): signup and login routes

Implement signup and login endpoints with bcrypt password hashing
(cost 12, max 72 bytes). Session stored server-side.
Addresses Task 9: auth module foundation.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

**Template mínimo:**

```
<type>(<escopo>): <descrição curta em imperativo, ≤50 char>

<explicação opcional: por quê esta mudança, contexto, dependências>
<linha em branco antes do footer>
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

**Tipos comuns**: `add` (feature), `fix` (bug), `refactor` (sem mudança de comportamento), `test` (testes), `docs` (documentação), `chore` (build, infra, deps).

### Pull Request

PR de feature segue `feature/*` → `develop`. Para `main`, só via `release/*` (seção "Release e estratégia de merge").

- **Título**: < 70 char, imperativo. Exemplo: `Implement auth module foundation`
- **Descrição**: 
  - Qual tarefa do `tasks/todo.md` você implementou? (ID e título).
  - Quais critérios de aceite você verificou?
  - Mudança de comportamento ou arquitetura? Aponta para ADR novo ou spec alterado.
  - Checklist de UI (se tela): contraste AA, reduced-motion, orçamento.

Exemplo:

```
## Summary
- Task 4: esqueleto do frontend e rota raiz
- Configura Vite, React Router, TanStack Query, shadcn/ui
- Testa LCP ≤2.5s e bundle ≤200KB gzip (ADR-0023)

## Test Plan
- [ ] Build local: `cd frontend && npm ci && npm run build`
- [ ] Tela carrega em < 2.5s (Chrome DevTools)
- [ ] Bundle é ≤200KB gzip (`npm run build` relata size)
- [ ] Sem violações de acessibilidade em vitest + vitest-axe
- [ ] Funciona em 360px (mobile) e 1920px (desktop)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### Review checklist

- [ ] Código está em tarefa do `tasks/todo.md`?
- [ ] Critérios de aceite da tarefa? Todos verificados.
- [ ] Nenhuma mudança fora do escopo da tarefa?
- [ ] Tests passam: `pytest`, `npm test -- --run`, lint, typecheck?
- [ ] Segurança: checou `CONTRIBUTING.md`, "Regras essenciais"?
- [ ] UI (se tela): contraste AA, reduced-motion, orçamento respeitado?
- [ ] Commits descrevem a mudança?
- [ ] Sem `.env`, segredos, banco, áudio ou volumes no git?

### Release e estratégia de merge

| Origem → destino | Como | Merge |
|---|---|---|
| `feature/*` → `develop` | PR | `Squash and merge` (um commit por PR) |
| `develop` → `release/*` | branch `release/*` criada a partir de `develop` | `Create a merge commit` |
| `release/*` → `main` | PR | `Create a merge commit` |

Nunca PR direto de `develop` ou `feature/*` para `main`.

```bash
git checkout develop
git pull origin develop --rebase
git checkout -b release/x.y.z
git merge --no-ff develop     # se release/* já existe e precisa de develop atualizado
git push -u origin release/x.y.z
# PR release/x.y.z → main com "Create a merge commit"
```

**Padrão de branch**: `release/x.y.z` (versão semântica).

## Setup local

### Prerequisites

- Python 3.12, uv
- Node.js na versão do `frontend/.nvmrc`, npm
- Docker Compose
- ffmpeg

### Backend

```bash
cd backend
uv sync --frozen
uv run pytest                    # testes rápidos
uv run pytest -m models_real     # com modelos reais (opcional, lento)
uv run pytest -m llm_real        # com chaves reais (opcional)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run lint-imports
uv run pip-audit
```

### Frontend

```bash
cd frontend
npm ci --ignore-scripts
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

### Rodar localmente

```bash
docker compose up --build
# Acessa em http://localhost:8080 (nginx) ou https://<SNOOK_LAN_HOST> (perfil lan, Caddy)
```

## Estrutura de código

```
backend/src/snook/
├── main.py, cli.py
├── core/                  # settings, db, UoW, eventos, erros, relógio (clock.py), logs, arquivos
├── shared/
│   └── prompts/          # system prompts, schemas
└── modules/<modulo>/
    ├── service.py         # lógica; exposto só ele
    ├── api.py             # rotas (se houver)
    ├── models.py          # SQLAlchemy (privado)
    └── repository.py      # acesso a dados (privado)

frontend/src/
├── app/                  # rotas, layout, guarda de autenticação
├── styles/               # Tailwind, variáveis CSS
├── lib/                  # utilitários, hooks
├── components/           # atoms e moléculas
└── features/<modulo>/    # páginas e smart components
```

Grafo de importação em `docs/specs/02-architecture.md`. Nenhum módulo importa outro à direita na build order. Verificado por `import-linter`.

## Regras essenciais

### Validação de entrada

- [ ] Toda rota valida entrada (Pydantic no backend; no frontend, validação própria sem lib nova fora dos ADRs).
- [ ] GET nunca muda estado.
- [ ] Reunião: check se usuário é dono (404 se não).

### Queries

- [ ] SQL só pelo ORM (SQLAlchemy).
- [ ] Sem f-strings ou string concat em queries.
- [ ] Sem `select *`; lista colunas.

### Subprocessos

- [ ] Sem `shell=True`.
- [ ] Sem user input diretamente em cmd; valida antes.

### Criptografia e auth

- [ ] Senha: bcrypt custo 12, até 72 bytes.
- [ ] Chaves de LLM: AES-256-GCM com `SNOOK_MASTER_KEY`.
- [ ] Sessão: cookie opaco no servidor, CSRF por Origin.

### Saídas não confiáveis

- [ ] Transcrição (do Whisper) tratada como não confiável.
- [ ] Saída de LLM tratada como não confiável.
- [ ] Frontend: `dangerouslySetInnerHTML` proibido.

### Logs

- [ ] Sem senha, token, chave, `HF_TOKEN` ou Transcrição.
- [ ] JSON, uma linha por evento, com `ts`, `level`, `logger`, `event`, `request_id` (`07-observability.md`).

### Segurança de rede

- [ ] Sem redirecionamento de provedor (httpx sem `follow_redirects`).
- [ ] `X-Forwarded-*` só com `TRUSTED_PROXY_IPS`.
- [ ] Sem stack trace ao usuário em erro.

### Frontend

- [ ] Teclado: toda funcionalidade acessível.
- [ ] `aria-live` em status, `aria-label` em botões sem texto.
- [ ] Contraste WCAG 2.2 AA (4.5:1 min).
- [ ] Animações desligam com `prefers-reduced-motion`.
- [ ] Mouse-tracking só com `(hover: hover) and (pointer: fine)`, sem `reduced-motion`.
- [ ] Orçamento ADR-0023: JS inicial ≤200 KB gzip, total ≤500 KB, LCP ≤2.5s, INP ≤200ms, CLS ≤0.1.

### Dados sensíveis

- [ ] Sem `.env`, chaves ou segredos no git.
- [ ] Sem banco, áudio ou volumes em commit.
- [ ] Volume `caddy-data` e `snook-lan-ca.crt` fora do git (`.gitignore`).

Listagem completa: `docs/specs/03-security.md`.

## Tipos

Backend: `mypy --strict` em todo módulo novo.

```bash
cd backend && uv run mypy src --strict --check-untyped-defs
```

Frontend: TypeScript `strict: true`.

## Testes

### Backend

Um teste por critério de aceite. Padrão: `backend/tests/<modulo>/test_api_*.py`.

```python
def test_auth_signup_creates_user(db_session, client):
    resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "x" * 20})
    assert resp.status_code == 201
    assert resp.json()["id"]

def test_auth_signup_invalid_email(client):
    resp = client.post("/api/auth/signup", json={"email": "invalid", "password": "x" * 20})
    assert resp.status_code == 422
```

### Frontend

Vitest + React Testing Library. Padrão: `src/**/*.test.tsx`.

```typescript
it("renders login form", () => {
  const { getByRole } = render(<LoginForm />);
  expect(getByRole("textbox", { name: /email/i })).toBeInTheDocument();
});

it("disables submit when form invalid", () => {
  const { getByRole } = render(<LoginForm />);
  expect(getByRole("button", { name: /submit/i })).toBeDisabled();
});
```

Execute:

```bash
cd frontend && npm test -- --run
# Gera coverage em coverage/
```

## Documentação

Specs em `docs/specs/` com voz caveman (breve, sem floreio). Comentário no código só quando informa algo que o nome não diz (regra LGPD, por exemplo). Não remover comentário existente sem pedido.

## Perguntas?

- **SDD e planeamento**: leia `AGENTS.md` e `docs/specs/`.
- **Regras de código e segurança**: leia `docs/specs/02-architecture.md` até `08-deployment.md`.
- **ADRs**: `docs/specs/adrs/`.
- **CLI do Claude Code**: `/help` ou https://github.com/anthropics/claude-code/issues.
