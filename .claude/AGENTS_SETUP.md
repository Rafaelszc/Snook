# Setup de Agentes Locais

Este projeto usa agentes especializados (skills) via Claude Code para manter qualidade em Spec-Driven Development.

## Instalação

Agentes já estão em seu Claude Code. Nenhuma instalação necessária. Rode `/skill-name` no terminal ou no chat.

## Agentes por fase

### Fase 1: Especificação (SDD)

Use **nesta ordem** para mudanças de requisito ou arquitetura:

```bash
/spec-writer      # Escreve docs/specs/00-overview.md e 01-prd.md
/spec-reviewer    # Valida specs contra código
/planner          # Cria tasks/plan.md e ADRs (SÓ com spec aprovado)
/spec-reviewer    # Valida plano e ADRs novos
/task-breaker     # Detalha plano em tasks/todo.md (SÓ com plano aprovado)
```

**Ordem é crítica.** Salte etapas e a próxima pode ter informações incompletas.

### Fase 2: Implementação

```bash
/code-review      # Análise de bugs em PR (antes de merge)
/simplify         # Limpeza: reuso, eficiência, claridade
/web-design-guidelines  # Revisão de telas e UI (checkpoints)
```

Skills de UI por tarefa: veja `tasks/plan.md`, "Skills de frontend por tarefa".

## Fluxo exemplo: adicionar feature nova

1. Identifique no backlog (`docs/specs/01-prd.md`) que precisa novo requisito.
2. Rode `/spec-writer`:
   ```
   Objetivo: adicionar feature X
   Mudanças: Y, Z
   Escopo: módulo W
   ```
3. Rode `/spec-reviewer` apontando para a seção modificada.
4. Ao aprovado, rode `/planner`:
   ```
   Spec aprovado: novo requisito em docs/specs/01-prd.md, seção X
   Módulo: W
   ```
5. Rode `/spec-reviewer` novamente (revisa plano).
6. Ao aprovado, rode `/task-breaker`:
   ```
   Plano aprovado: tasks/plan.md, Fase N
   ```
7. Implemente as tarefas em PRs para `develop`.

## Uso no CLI

Ative agentes direto no terminal Claude Code:

```
# Prompt do Claude Code
/spec-writer

# Aparece interativo. Descreva o que precisa fazer.
```

## Uso no VS Code ou JetBrains

Se tem a extensão Claude Code instalada:

1. Abra painel de Chat da extensão.
2. Digite `/spec-writer` e envie.
3. Agente responde no painel.

## Recomendações

- **Não pule etapas.** `/planner` sem spec aprovado produz plano incompleto.
- **Salve aprove no PR.** Se `spec-reviewer` encontra desvios, corrija a spec antes de rodar `/planner`.
- **Use `/code-review` antes de merge.** Especialmente em tarefas de segurança ou infra.
- **Responda com contexto.** Diga o caminho do arquivo, ID do spec/ADR, ou número da tarefa. Agentes capturam melhor com pistas.

## Troubleshooting

**Agente diz "arquivo não encontrado":**
- Confere o caminho. Relativo a raiz do projeto.
- Exemplo: `docs/specs/02-architecture.md`, não `./02-architecture.md`.

**Agente demora ou trava:**
- Use `/effort` para reduzir a complexidade (low, medium, high).
- Divida em partes menores (uma seção por vez).

**Erro de permissão:**
- Prompt pode pedir acesso a arquivos. Aprove.
- Se repetir, check `.claude/settings.json` ou use `/update-config`.

## Mais informações

- **CONTRIBUTING.md**: fluxo de trabalho completo, GitFlow, regras de código.
- **AGENTS.md**: explicação dos agentes e arquitetura do projeto.
- **docs/specs/**: fonte de verdade; agentes lêem e escrevem aqui.
- **tasks/plan.md** e **tasks/todo.md**: tarefas, critérios, verificação.
