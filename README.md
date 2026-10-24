# Snook

Recebe gravação de reunião, diariza e transcreve localmente em pt-BR. LLM do Usuário gera Epics e User Stories. Uso só local: máquina do usuário ou rede confiável.

Specs em `docs/specs/`. Regras para agentes em `AGENTS.md`.

## Requisitos

- Docker com Compose v2.
- GPU (opcional): driver NVIDIA e NVIDIA Container Toolkit.
- Conta no HuggingFace com os termos do Pyannote aceitos.

## Primeira execução

1. `cp .env.example .env`.
2. Preencher `SNOOK_MASTER_KEY` (comando no `.env.example`) e `HF_TOKEN`.
3. `mkdir -p audios` (precisa ser gravável pelo UID 1000).
4. `docker compose up -d --build`.
5. Abrir `http://localhost:8080`.

GPU: `COMPOSE_PROFILES=gpu` no `.env`. Rede confiável com HTTPS: `docs/specs/08-deployment.md`, "Perfil lan".

## Modelos

- Whisper `large-v3-turbo` e Pyannote `speaker-diarization-3.1`, em revisão fixa (hash de commit em `WHISPER_REVISION` e `PYANNOTE_REVISION`; SEC-22).
- Aceitar no HuggingFace, com a conta do `HF_TOKEN`, os termos de `pyannote/speaker-diarization-3.1` e `pyannote/segmentation-3.0`.
- Baixar antes (opcional; senão baixa na primeira transcrição): `docker compose exec backend python -m snook.cli download-models` (GPU: `backend-gpu`). Cache no volume `snook-models`; a segunda execução não baixa de novo.
- Sem rede depois do download: `MODELS_OFFLINE=true` no `.env` e `docker compose up -d`.
- Trocar `WHISPER_MODEL` pede trocar `WHISPER_REVISION` junto.

## Dados

- Banco e modelos: volumes `snook-db` e `snook-models`. `docker compose down` mantém; `docker compose down -v` apaga.
- Áudios: `./audios`, fora do git.
- `.env` guarda segredos. Nunca commitar.

## Chave-mestra (`SNOOK_MASTER_KEY`)

Cifra as chaves de LLM dos Usuários (ADR-0009). Backup do banco sem ela não expõe chaves.

Trocar a chave-mestra:

1. No `.env`: chave atual vai para `SNOOK_MASTER_KEY_PREVIOUS`; nova em `SNOOK_MASTER_KEY`.
2. `docker compose stop backend backend-gpu`.
3. `docker compose run --rm backend python -m snook.cli rotate-master-key` (GPU: `backend-gpu`).
4. Conferir a saída. Apagar `SNOOK_MASTER_KEY_PREVIOUS` do `.env` e o backup `snook.db.bak-rotate` do volume.
5. `docker compose up -d`.

Chave-mestra perdida ou trocada sem rotação: chaves ficam ilegíveis. Nada é apagado. Cada Usuário informa a chave de novo em Configurações.

## Desenvolvimento

Comandos de teste e lint em `AGENTS.md`, "Comandos".

- `uv sync` sem extra não instala torch, faster-whisper nem pyannote: testes padrão e CI usam engines falsas.
- Suíte `models_real` (à mão, antes da release): `cd backend && uv sync --extra cpu && uv run pytest -m models_real`. Lê `HF_TOKEN` do `.env`; cache em `MODELS_REAL_ROOT` (padrão `~/.cache/snook/models`). Teste do pipeline pede `ffmpeg` no host.
- Fixture de voz da suíte: `backend/tests/fixtures/audio/two_voices.py` (espeak-ng, vozes sintéticas).
