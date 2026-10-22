# ADR-0007: Pipeline assíncrono dentro do backend, com fila reconstruída no startup

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q2 da rodada de decisões do planner: pipeline em processo, reenfileirando `pending` no startup. Recomendação aceita sem mudança.

## Contexto

- Upload responde antes do processamento (RT-09).
- Whisper e Pyannote são pesados e presos à CPU ou GPU. Geração é espera de rede.
- Ao subir, "Marcar interrompidas" roda antes de aceitar requisições e antes de qualquer consumidor (`meetings`, critério 45).
- Reuniões em `pending` após reinício: sem decisão no spec (Q69 deixou para o planner). Resolvido por este ADR.
- Aviso velho ou repetido não pode disparar trabalho (`diarized-transcription` 3, `transcript-split` 46, `backlog-generation` 33).
- Exclusão durante o processamento não pode recriar dados (`meetings` 30).

## Opções consideradas

1. **Barramento em memória no processo do backend + fila reconstruída do banco no startup. Transcrição em pool de subprocessos. `run_id` em cada aviso.**
   - Prós: nenhum serviço extra; startup controla a ordem (marcar, depois reenfileirar, depois consumir); sem aviso velho persistido.
   - Contras: um só processo uvicorn (`--workers 1`); fila some no crash, mas o banco a reconstrói.
2. **Fila durável em tabela SQLite (outbox) + container `worker` separado.**
   - Prós: isola carga pesada; aviso sobrevive a reinício.
   - Contras: dois processos escrevendo no SQLite; coordenação do startup entre containers; aviso velho persistido exige descarte por tentativa.
3. **Celery ou RQ com Redis.**
   - Prós: padrão de mercado; retries prontos.
   - Contras: serviço a mais; overkill para app local de um usuário; mesmo problema de aviso velho.

## Decisão

Opção 1.

- `core/events.py`: `EventBus` em memória, tipado. Eventos: `MeetingCreated`, `RetryRequested(stage)`, `ParticipantsConfirmed`, `PartsReady`. Cada um leva `meeting_id` e `run_id`.
- `meetings.run_id` (UUID) muda em toda transição que inicia trabalho: criação, `failed` para `pending`, `failed` para `transcribed`, entrada em `generating`. Consumidor só age se o status esperado e o `run_id` batem com o banco.
- Consumidores:
  - `diarized-transcription`: `TranscriptionDispatcher` com `ProcessPoolExecutor` (`spawn`), tamanho `TRANSCRIPTION_WORKERS`. Escolhe a Reunião `pending` mais antiga cujo Usuário está abaixo de `TRANSCRIPTION_MAX_PER_USER`. Subprocesso só lê o arquivo e devolve segmentos e caminho do áudio tratado temporário. Processo principal grava.
  - `transcript-split`: handler síncrono em thread do executor de eventos.
  - `backlog-generation`: `GenerationRunner` em pool de threads (`GENERATION_WORKERS`, padrão 2). Chamadas HTTP síncronas.
- Sequência de subida (lifespan do FastAPI), igual à de `02-architecture.md`, "Retry e reinício":
  1. pegar a trava `/data/snook.lock` (ADR-0006); se outro processo a tem, o backend não sobe;
  2. backup do banco e `alembic upgrade head`;
  3. limpar `/audios/.tmp/`;
  4. "Marcar interrompidas" (Q58, Q69), sem emitir aviso;
  5. reenfileirar toda Reunião em `pending`, em ordem de `created_at`, como `MeetingCreated` interno;
  6. iniciar dispatchers e runners;
  7. aceitar requisições.
- Exclusão durante processamento: gravação final roda em transação que confere existência e `run_id` da Reunião. FK com `ON DELETE CASCADE` recusa filho órfão. Arquivo tratado nasce em `/audios/.tmp/` e só vai para o diretório da Reunião depois do commit, se ela ainda existe.

## Consequências

- Backend roda com um só worker uvicorn. Escalar horizontalmente fica fora de escopo.
- Crash do processo não perde trabalho: tudo em andamento vira `failed` com "Tentar novamente"; `pending` volta à fila.
- Crash libera a trava (`fcntl.flock` cai com o processo). Temporário órfão em `/audios/.tmp/` some no passo 3 da subida seguinte.
- Limitador de taxa em memória é suficiente (ADR-0010).
