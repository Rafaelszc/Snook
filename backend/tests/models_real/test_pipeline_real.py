"""Task 26.4, manual: pipeline real no subprocesso `spawn`; offline com a rede bloqueada
(`diarized-transcription` 21, 22; transversal 14)."""

import shutil
from pathlib import Path

import pytest

from snook.core.settings import Settings
from snook.modules.diarized_transcription.dispatcher import process_pool
from snook.modules.diarized_transcription.pipeline import Job, run_job
from snook.modules.diarized_transcription.service import build_engines, download_models
from tests.diarized_transcription import boundary_child
from tests.models_real.conftest import FIXTURE, FIXTURE_SECONDS

pytestmark = [pytest.mark.models_real, pytest.mark.usefixtures("requires_ffmpeg", "hub_env")]


def job(tmp_path: Path) -> Job:
    original = tmp_path / "meeting" / "original.wav"
    original.parent.mkdir()
    shutil.copyfile(FIXTURE, original)
    return Job(
        original_path=original,
        treated_path=tmp_path / "treated.flac",
        duration_seconds=FIXTURE_SECONDS,
        expected_speakers=2,
    )


def test_pipeline_reaches_two_speakers(real_settings: Settings, tmp_path: Path) -> None:
    pool = process_pool(1)
    try:
        segments = pool.submit(run_job, build_engines(real_settings), job(tmp_path)).result()
    finally:
        pool.shutdown()
    assert {s.speaker_label for s in segments} == {"SPEAKER_00", "SPEAKER_01"}
    starts = [s.start_seconds for s in segments]
    assert starts == sorted(starts)
    assert all(0 <= s.start_seconds < s.end_seconds <= FIXTURE_SECONDS for s in segments)


def test_offline_with_network_blocked(real_settings: Settings, tmp_path: Path) -> None:
    """Modelos em cache, `MODELS_OFFLINE=true` e rede bloqueada no subprocesso."""
    download_models(real_settings)
    offline = real_settings.model_copy(update={"models_offline": True})
    pool = process_pool(1)
    try:
        result = pool.submit(
            boundary_child.run_guarded, build_engines(offline), job(tmp_path)
        ).result()
    finally:
        pool.shutdown()
    assert result["segments"] > 0
    assert result["network_attempts"] == 0
