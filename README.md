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
