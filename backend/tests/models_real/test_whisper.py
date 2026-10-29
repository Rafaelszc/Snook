"""Task 26.1, manual: faster-whisper real em pt-BR."""

import pytest

from snook.core.settings import Settings
from snook.modules.diarized_transcription.engines.base import LANGUAGE
from snook.modules.diarized_transcription.service import build_transcriber
from tests.models_real.conftest import FIXTURE, FIXTURE_SECONDS

pytestmark = pytest.mark.models_real


def test_transcribes_portuguese(real_settings: Settings) -> None:
    chunks = build_transcriber(real_settings).transcribe(FIXTURE, LANGUAGE)
    text = " ".join(chunk.text for chunk in chunks).lower()
    assert "relatório" in text or "relatorio" in text
    assert all(0 <= c.start_seconds < c.end_seconds <= FIXTURE_SECONDS + 1 for c in chunks)
