# ADR-0006: Persistência com SQLAlchemy 2, Alembic e unidade de trabalho compartilhada

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q1 da rodada de decisões do planner: SQLAlchemy 2 + Alembic com unidade de trabalho. Recomendação aceita sem mudança.

## Contexto

- Vários contratos exigem gravação na mesma transação entre módulos:
  - `participants` grava nomes e chama "Registrar Participantes confirmados" de `meetings`;
  - `backlog-generation` grava backlog e chama "Registrar backlog gravado";
  - `backlog-review` chama "Renomear Participante" e troca `requested_by` das US.
- Aviso só pode sair se a transação confirmou (`participants`, critério 10).
- SQLite: um escritor por vez. Schema muda ao longo das fases.

## Opções consideradas

1. **SQLAlchemy 2 (ORM, modo síncrono) + Alembic, com unidade de trabalho (`UnitOfWork`) passada às interfaces.**
   - Prós: transação real entre módulos; migrações versionadas; FK e `ON DELETE CASCADE`; maduro.
   - Contras: mais camadas; sessão precisa circular nas interfaces.
2. **`sqlite3` puro com SQL escrito à mão, conexão por requisição.**
   - Prós: zero dependência; controle total.
   - Contras: migrações manuais; mais código repetido; risco maior de concatenação de SQL.
3. **SQLModel.**
   - Prós: modelos Pydantic e ORM juntos.
   - Contras: camada a mais sobre SQLAlchemy; acopla schema da API ao do banco.

## Decisão

Opção 1.

- `core/db.py` cria engine SQLite com `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`.
- `core/uow.py` define `UnitOfWork`: abre sessão, faz commit ou rollback, guarda avisos pendentes e os publica só depois do commit (`uow.publish_after_commit(event)`).
- Interfaces internas que escrevem recebem `uow` como parâmetro. Quem abre a unidade é a rota HTTP ou o consumidor do aviso.
- Cada módulo é dono das próprias tabelas e de um `repository.py` privado. Outro módulo nunca importa esse arquivo.
- Alembic com um diretório único de migrações. Migração roda no startup do backend (ver ADR-0007, sequência de subida). Antes de migrar, o startup copia o arquivo do banco para `snook.db.bak-<revisão>`.
- Endpoints e consumidores síncronos (`def`), executados no threadpool do FastAPI. Sem `async` no acesso ao banco.

## Consequências

- Transação entre módulos vira commit único, sem mecanismo distribuído.
- Aviso emitido depois do commit: falha de gravação não emite aviso.
- Só o processo principal do backend escreve no banco. Subprocessos de transcrição devolvem resultado ao processo principal (ADR-0007).
- CLI de escrita (`delete-user`, `rotate-master-key`) roda só com o backend parado, garantida pela trava `/data/snook.lock` (`fcntl.flock`, liberada quando o processo morre). Backend pega a trava no passo 1 da subida (ADR-0007) e a mantém enquanto roda. CLI com a trava ocupada para com erro, sem escrever. Código em `core/runlock.py`. Fonte: correções da revisão do spec-reviewer aceitas pelo usuário em 2026-10-22; já citado em `02-architecture.md` e `03-security.md` (SEC-24).
