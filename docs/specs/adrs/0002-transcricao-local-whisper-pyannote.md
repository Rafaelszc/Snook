# ADR-0002: Transcrição e diarização locais com Whisper e Pyannote

- Status: Aceita
- Data: 2026-10-22
- Fonte: briefing; Q3, Q4, Q5, Q17; RT-06; critério transversal 14.

## Contexto

Áudio de reunião é sensível. Usuário decidiu que nada de áudio sai do servidor.

## Decisão

- Whisper roda local, idioma fixo pt-BR, sem detecção automática.
- Pyannote faz a diarização local.
- CPU por padrão. GPU NVIDIA opcional por perfil do `docker compose`.
- `HF_TOKEN` vem só do `.env`. Modelos ficam em cache num volume Docker.
- Só texto vai ao provedor de LLM ativo.

## Consequências

- Imagem do backend fica grande (PyTorch, modelos em volume).
- Primeira execução precisa de internet e `HF_TOKEN` com aceite dos termos do modelo. Depois, roda offline.
- Biblioteca, tamanho do modelo e tratamentos de áudio: ADR-0014.
