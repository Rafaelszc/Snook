# Fixtures de áudio

Todas sintéticas: tom de 440 Hz ou voz de `espeak-ng`. Sem voz de terceiros, sem dado pessoal (SEC-08).

| Arquivo | Uso |
|---|---|
| `tone.{mp3,wav,m4a,ogg,webm,mp4}` | Um formato aceito cada, 1 s (`meetings` 1) |
| `video_only.mp4`, `text_as.mp3` | Sem trilha de áudio (`meetings` 10) |
| `recorder.webm` | Muxing do `MediaRecorder`: `audio/webm;codecs=opus`, 48 kHz, 3 s, sem `format.duration` (`screen-recording` 25; Q61) |
| `two_voices_ptbr.wav` | Duas vozes pt-BR para a suíte `models_real` |

## Regenerar

Precisa de `ffmpeg` com `libopus` e, para `two_voices_ptbr.wav`, `espeak-ng`. Nesta pasta:

```
sh generate.sh
```

Sem `ffmpeg` no host:

```
podman run --rm -v "$PWD":/w:Z -w /w docker.io/library/alpine:3.20 \
  sh -c 'apk add -q ffmpeg && ffmpeg -hide_banner -loglevel error -y -bitexact \
  -f lavfi -i sine=frequency=440:duration=3:sample_rate=48000 -ac 1 -c:a libopus -b:a 32k \
  -f webm pipe:1 > recorder.webm'
```

`recorder.webm` sai por `pipe:1`: sem seek, o muxer não volta ao cabeçalho para gravar duração nem cues, como o gravador do navegador. Conferir:

```
ffprobe -v error -show_entries format=duration -of csv=p=0 recorder.webm   # N/A
```
