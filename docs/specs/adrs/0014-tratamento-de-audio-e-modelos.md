# ADR-0014: Tratamento de áudio com ffmpeg, faster-whisper e Pyannote 3.1

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q9 da rodada de decisões do planner: faster-whisper `large-v3-turbo` `int8` + Pyannote 3.1, calibrado pelo spike da Task 1. Recomendação aceita sem mudança.

## Contexto

- ADR-0002 (Aceita) fixa Whisper e Pyannote locais.
- Spec deixava aberto: tratamentos, onde guardar o áudio tratado, biblioteca e tamanho do Whisper, versão do Pyannote, regra de junção, leitura de duração. Resolvido por este ADR.
- Whisper e Pyannote querem mono 16 kHz.
- Amostra de speaker sai do áudio tratado.

## Opções consideradas

### Whisper

1. **`faster-whisper` (CTranslate2), modelo `large-v3-turbo`, `int8` em CPU e `float16` em GPU.**
   - Prós: 2 a 4 vezes mais rápido que `openai-whisper` em CPU; menos RAM; bom em pt-BR.
   - Contras: dependência de CTranslate2.
2. **`openai-whisper`.**
   - Prós: referência.
   - Contras: lento em CPU; mais RAM.
3. **`whisper.cpp` via binding.**
   - Prós: muito leve.
   - Contras: binding Python menos maduro; build nativo.

### Tratamento

1. **ffmpeg: converter para mono 16 kHz, filtro passa-alta 80 Hz, normalização de volume `loudnorm` (EBU R128). Sem redução de ruído agressiva.**
   - Prós: ajuda os dois modelos; redução de ruído forte costuma piorar a diarização.
   - Contras: ruído alto passa.
2. **Mesmo, mais `afftdn` (redução de ruído).**
   - Contras: artefatos; mais lento.

## Decisão

- Whisper: opção 1. Variáveis `WHISPER_MODEL` (padrão `large-v3-turbo`), `WHISPER_COMPUTE_TYPE` (padrão `int8`; `float16` no perfil GPU). Idioma fixo `pt`. VAD do faster-whisper ligado.
- Pyannote: `pyannote.audio` 3.x com `pyannote/speaker-diarization-3.1`. Variável `PYANNOTE_PIPELINE`. `expected_speakers` vira `num_speakers`. Versão exata fixada no lockfile da tarefa.
- Tratamento: opção 1.
- Leitura de duração e trilhas: `ffprobe`. Se `format.duration` falta (webm do `MediaRecorder`), lê o último pacote de áudio (`pts_time + duration_time`). Arquivo sem trilha de áudio legível vira "arquivo sem áudio". `ffprobe` roda com `-protocol_whitelist file` e `-format_whitelist` só dos demuxers dos formatos aceitos: playlist ou script concat disfarçado não abre outro arquivo.
- Armazenamento: `/audios/<meeting_id>/original.<ext>` e `/audios/<meeting_id>/treated.flac` (FLAC mono 16 kHz, cerca de 100 MB para 2 h). `meeting_id` é UUID gerado pelo servidor. Nome enviado pelo usuário nunca entra no caminho.
- Amostra: ffmpeg corta o trecho de `treated.flac` e devolve `audio/wav`, gerado sob demanda, sem cache.
- Junção diarização e transcrição: cada trecho do Whisper recebe o speaker com maior sobreposição de tempo. Sem sobreposição: speaker do turno mais próximo. Trechos seguidos do mesmo speaker com pausa até 1,0 s são unidos num segmento.
- Cache de modelos: volume `snook-models` em `/models` (`HF_HOME=/models/hf`). Comando `python -m snook.cli download-models` baixa os dois. Em execução, `HF_HUB_OFFLINE=1` quando `MODELS_OFFLINE=true`.

## Consequências

- Tempo em CPU ainda alto para 2 h de áudio. Spike da Task 1 mede tempo e RAM e calibra `WHISPER_MODEL`, `WHISPER_COMPUTE_TYPE` e `TRANSCRIPTION_WORKERS` (ADR-0010). Ajuste de valor padrão fica registrado neste ADR, sem ADR novo. Troca de biblioteca ou de modelo de diarização pede ADR novo.
- Licença: modelos Pyannote exigem aceite de termos no HuggingFace. Documentar no README.
