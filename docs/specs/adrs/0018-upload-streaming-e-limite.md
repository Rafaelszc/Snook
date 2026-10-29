# ADR-0018: Upload em streaming e limite de 500 MiB

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q13 da rodada de decisões do planner: limite de 500 MiB, com recepção em streaming. Recomendação aceita sem mudança.

## Contexto

- Q6: máximo de 500 MB. Spec deixava aberto se é decimal ou binário. Resolvido por este ADR: binário.
- Receber até 500 MB sem carregar o arquivo inteiro na memória.
- Arquivo recusado não deixa resto em `/audios` (`meetings`, critérios 9 a 15).

## Opções consideradas

### Definição do limite

1. **500 MiB = 524.288.000 bytes.**
   - Prós: arquivo que qualquer sistema operacional mostra como "500 MB" passa (Windows mostra MiB com o rótulo MB).
   - Contras: 4,8% acima de 500 MB decimais.
2. **500 MB = 500.000.000 bytes.**
   - Prós: SI exato.
   - Contras: arquivo que o Windows mostra como 480 a 500 MB pode ser recusado.

### Recepção

1. **Limite de corpo no nginx e num middleware ASGI, mais cópia em blocos de 1 MiB para `/audios/.tmp/<uuid>` contando bytes.**
   - Prós: memória constante; corta cedo.
   - Contras: arquivo temporário a limpar.
2. **`UploadFile` padrão, checagem de tamanho depois.**
   - Contras: arquivo inteiro já em disco ou memória antes da recusa.

## Decisão

- Limite: opção 1 (500 MiB). Variável `UPLOAD_MAX_BYTES=524288000`. Mensagem diz "500 MB".
- Recepção: opção 1.
  - nginx: `client_max_body_size 510m` só em `POST /api/meetings`; 1m nas demais rotas.
  - Recepção (`meetings/storage.py`): `Content-Length` acima do limite mais 1 MiB de envelope multipart responde HTTP 413 antes de ler o corpo. O `BodyLimitMiddleware` de 1 MiB não vale nessa rota.
  - Parser: `python-multipart`, só o parser de streaming sobre `request.stream()`; arquivo vai direto ao temporário. Dependência aprovada pelo usuário em 2026-10-23.
  - Cópia em blocos; passou do limite, apaga o temporário e responde HTTP 413.
  - Validação (`ffprobe`) roda no temporário. Só depois do commit da Reunião, o arquivo vai para `/audios/<meeting_id>/original.<ext>` (`os.replace` no mesmo volume).
  - Qualquer recusa apaga o temporário. Startup apaga sobras de `/audios/.tmp/`.
- Frontend recusa antes do envio com o mesmo limite (`meetings`, critério 37).

## Consequências

- Mesmo volume para `.tmp` e destino, para `os.replace` ser atômico.
