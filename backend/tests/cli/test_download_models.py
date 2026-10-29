"""Task 26.3: `python -m snook.cli download-models` com bibliotecas falsas."""

import base64
from pathlib import Path

import pytest

from snook import cli
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines.pyannote import SUBMODEL_REVISIONS
from tests.diarized_transcription.fake_libs import GatedRepoError, Hub, install

TOKEN = "hf_segredo_do_operador_123"
WHISPER_REVISION = "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
PYANNOTE_REVISION = "84fd25912480287da0247647c3d2b4853cb3ee5d"


@pytest.fixture
def hub(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, hub_env: None) -> Hub:
    monkeypatch.setenv("SNOOK_MASTER_KEY", base64.urlsafe_b64encode(bytes(range(32))).decode())
    monkeypatch.setenv("MODELS_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snook.db"))
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    monkeypatch.chdir(tmp_path)  # sem `.env` do repo
    return install(monkeypatch, tmp_path)


def test_downloads_both_models_at_fixed_revisions(
    hub: Hub, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`diarized-transcription` 23, SEC-22: repositório e revisão fixos, cache em `/models`."""
    assert cli.main(["download-models"]) == 0
    cache = str(tmp_path / "models" / "hf" / "hub")
    assert hub.whisper == [
        {
            "repo": "dropbox-dash/faster-whisper-large-v3-turbo",
            "local_files_only": False,
            "cache_dir": cache,
            "revision": WHISPER_REVISION,
            "offline_env": None,
        }
    ]
    assert [(d["repo"], d["revision"], d["cache_dir"]) for d in hub.downloads] == [
        ("pyannote/speaker-diarization-3.1", PYANNOTE_REVISION, cache),
        *[(name, rev, cache) for name, rev in SUBMODEL_REVISIONS.items()],
    ]
    assert hub.pipeline is not None and hub.pipeline.calls == []  # só baixa, não diariza
    assert not (tmp_path / "snook.lock").exists()  # não escreve no banco: sem trava
    assert TOKEN not in capsys.readouterr().out


def test_hf_access_denied_is_reported(
    hub: Hub, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    hub.error = GatedRepoError("restricted")
    assert cli.main(["download-models"]) == 1
    err = capsys.readouterr().err
    assert messages.HF_ACCESS_DENIED in err
    assert TOKEN not in err and TOKEN not in caplog.text


def test_offline_mode_refuses_download(
    hub: Hub, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MODELS_OFFLINE", "true")
    assert cli.main(["download-models"]) == 1
    assert "MODELS_OFFLINE" in capsys.readouterr().err
    assert hub.whisper == [] and hub.downloads == []
