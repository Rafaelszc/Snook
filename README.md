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

## Desenvolvimento

Comandos de teste e lint em `AGENTS.md`, "Comandos".
