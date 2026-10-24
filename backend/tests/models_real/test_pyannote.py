"""Task 26.2, manual: Pyannote real com e sem `expected_speakers`."""

import pytest

from snook.core.settings import Settings
from snook.modules.diarized_transcription.service import build_diarizer
from tests.models_real.conftest import FIXTURE

pytestmark = pytest.mark.models_real


def test_diarizes_with_expected_speakers(real_settings: Settings) -> None:
    turns = build_diarizer(real_settings).diarize(FIXTURE, 2)
    assert {turn.speaker_label for turn in turns} == {"SPEAKER_00", "SPEAKER_01"}


def test_diarizes_without_number(real_settings: Settings) -> None:
    turns = build_diarizer(real_settings).diarize(FIXTURE, None)
    assert turns and all(turn.start_seconds < turn.end_seconds for turn in turns)
