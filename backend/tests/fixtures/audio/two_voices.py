"""Fixture `models_real`: duas vozes sintéticas do espeak-ng em pt-BR, sem voz de pessoa.
Rodar nesta pasta: python3 two_voices.py (precisa de espeak-ng)."""

import subprocess  # noqa: S404
import tempfile
import wave
from pathlib import Path

VOICES = {
    "A": ["-v", "pt-br+m3", "-p", "30", "-s", "150"],
    "B": ["-v", "pt-br+f4", "-p", "75", "-s", "160"],
}
LINES = [
    ("A", "Bom dia a todos. Hoje vamos revisar o relatório de vendas do trimestre."),
    ("B", "Bom dia. Eu preciso que o relatório tenha um gráfico por região."),
    ("A", "Combinado. Vou incluir o gráfico até sexta-feira."),
    ("B", "Ótimo. Depois envie o arquivo para a equipe financeira."),
]
PAUSE_SECONDS = 0.8
TARGET = Path("two_voices_ptbr.wav")


def main() -> None:
    with tempfile.TemporaryDirectory() as folder, wave.open(str(TARGET), "wb") as out:
        for index, (voice, text) in enumerate(LINES):
            part = Path(folder) / f"{index}.wav"
            subprocess.run(["espeak-ng", *VOICES[voice], "-w", str(part), text], check=True)  # noqa: S603, S607
            with wave.open(str(part), "rb") as source:
                if index == 0:
                    out.setparams(source.getparams())
                silence = b"\0" * int(source.getframerate() * PAUSE_SECONDS) * source.getsampwidth()
                out.writeframes(source.readframes(source.getnframes()) + silence)


if __name__ == "__main__":
    main()
