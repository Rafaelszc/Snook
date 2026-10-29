"""Travas de versão que os testes com bibliotecas falsas não pegam (fake_libs)."""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.mark.parametrize("extra", ["cpu", "gpu"])
def test_av_stays_below_19(extra: str) -> None:
    """`av` 19 removeu `metadata_errors` de `av.open`; `faster_whisper.decode_audio` ainda o
    passa e falha com `TypeError` (faster-whisper 1.2.1 exige só `av>=11`)."""
    extras = tomllib.loads(PYPROJECT.read_text())["project"]["optional-dependencies"]
    assert "av>=11,<19" in extras[extra]
