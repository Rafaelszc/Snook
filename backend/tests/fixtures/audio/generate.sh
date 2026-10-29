#!/bin/sh
# Fixtures sintéticas (tom de 440 Hz, sem voz). Rodar nesta pasta: sh generate.sh
set -eu
TONE="-f lavfi -i sine=frequency=440:duration=1:sample_rate=8000"
VIDEO="-f lavfi -i color=c=black:s=16x16:d=1:r=5"
FF="ffmpeg -hide_banner -loglevel error -y -bitexact"
$FF $TONE -ac 1 -c:a libmp3lame -b:a 16k tone.mp3
$FF $TONE -ac 1 -c:a pcm_s16le tone.wav
$FF $TONE -ac 1 -c:a aac -b:a 16k tone.m4a
$FF $TONE -ac 1 -c:a libvorbis tone.ogg
$FF $TONE -ac 1 -c:a libopus -b:a 16k tone.webm
$FF $VIDEO $TONE -map 0:v -map 1:a -c:v mpeg4 -c:a aac -b:a 16k -shortest tone.mp4
$FF $VIDEO -c:v mpeg4 video_only.mp4
# Saída sem seek: o muxer não grava duração nem cues, como o webm do MediaRecorder
# (audio/webm;codecs=opus, 48 kHz). 3 s para medir o erro de duração (screen-recording 25).
$FF -f lavfi -i sine=frequency=440:duration=3:sample_rate=48000 -ac 1 -c:a libopus -b:a 32k \
  -f webm pipe:1 > recorder.webm
printf 'isto e texto, nao audio\n' > text_as.mp3
# Duas vozes sintéticas pt-BR para a suíte models_real (precisa de espeak-ng).
python3 two_voices.py
