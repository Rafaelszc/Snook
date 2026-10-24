"""Task 26.1: faster-whisper com idioma fixo, revisão fixa e modo offline, sem modelo."""

import os
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from snook.core.settings import Settings, SettingsError, load_settings
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines import whisper
from snook.modules.diarized_transcription.engines.base import LANGUAGE, EngineFailure
from snook.modules.diarized_transcription.engines.hub import ModelSource
from snook.modules.diarized_transcription.engines.whisper import WhisperTranscriber
from snook.modules.diarized_transcription.service import build_transcriber

pytestmark = pytest.mark.usefixtures("hub_env")

AUDIO = Path("/audios/.tmp/a.flac")


class FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start, self.end, self.text = start, end, text


class FakeModel:
    def __init__(self, segments: list[FakeSegment] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.segments = segments or [FakeSegment(0.0, 1.5, " Bom dia. ")]

    def transcribe(self, audio: str, **options: Any) -> tuple[list[FakeSegment], None]:
        self.calls.append((audio, options))
        return self.segments, None


def transcriber(settings: Settings, model: FakeModel, fetched: list[ModelSource]) -> Any:
    def fetch(source: ModelSource) -> str:
        fetched.append(source)
        return "/models/hf/hub/whisper"

    real = build_transcriber(settings)
    return WhisperTranscriber(
        source=real.source,
        compute_type=real.compute_type,
        fetch=fetch,
        load=lambda _path, _compute: model,
    )


def test_transcribes_in_portuguese_without_detection(settings: Settings) -> None:
    """`diarized-transcription` 8: idioma `pt` sempre informado, VAD ligado."""
    model = FakeModel()
    chunks = transcriber(settings, model, []).transcribe(AUDIO, LANGUAGE)
    assert model.calls == [(str(AUDIO), {"language": "pt", "vad_filter": True})]
    assert [(c.start_seconds, c.end_seconds, c.text) for c in chunks] == [(0.0, 1.5, "Bom dia.")]


def test_other_language_is_refused(settings: Settings) -> None:
    with pytest.raises(ValueError):
        transcriber(settings, FakeModel(), []).transcribe(AUDIO, "en")


def test_blank_chunks_are_dropped(settings: Settings) -> None:
    model = FakeModel([FakeSegment(0.0, 1.0, "  "), FakeSegment(1.0, 2.0, "ok")])
    chunks = transcriber(settings, model, []).transcribe(AUDIO, LANGUAGE)
    assert [c.text for c in chunks] == ["ok"]


def test_model_from_official_repo_and_fixed_revision(settings: Settings) -> None:
    """SEC-22: repositório oficial do faster-whisper e revisão de `WHISPER_REVISION`."""
    fetched: list[ModelSource] = []
    transcriber(settings, FakeModel(), fetched).transcribe(AUDIO, LANGUAGE)
    assert fetched == [
        ModelSource(
            repo_id="dropbox-dash/faster-whisper-large-v3-turbo",
            revision="0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
            models_root=settings.models_root,
            offline=False,
        )
    ]
    assert fetched[0].cache_dir == settings.models_root / "hf" / "hub"


def test_compute_type_from_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "float16")
    assert build_transcriber(load_settings(env_file=None)).compute_type == "float16"
    assert build_transcriber(settings).compute_type == "int8"


@pytest.mark.parametrize(
    "value", ["main", "v1.0", "0a363e91", "0A363E9161CBC7ED1431C9597A8CEAF0C4F78FCF"]
)
def test_settings_require_commit_hash(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, value: str
) -> None:
    """SEC-22: revisão que não é hash de commit derruba o settings, sem mostrar o valor."""
    monkeypatch.setenv("WHISPER_REVISION", value)
    with pytest.raises(SettingsError) as caught:
        load_settings(env_file=None)
    assert "WHISPER_REVISION" in str(caught.value)
    assert value not in str(caught.value)


def test_settings_without_revision_fail(settings: Settings) -> None:
    with pytest.raises(ValueError, match="hash de commit"):
        Settings(snook_master_key=settings.snook_master_key, whisper_revision="")


@pytest.mark.parametrize("value", ["large-v3-turbo", "Systran/faster-whisper-small"])
def test_whisper_model_accepts_alias_or_repo(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, value: str
) -> None:
    monkeypatch.setenv("WHISPER_MODEL", value)
    assert load_settings(env_file=None).whisper_model == value


@pytest.mark.parametrize("value", ["../etc", "https://x/y", "a/b/c", "medium"])
def test_whisper_model_rejects_other_values(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, value: str
) -> None:
    monkeypatch.setenv("WHISPER_MODEL", value)
    with pytest.raises(SettingsError, match="WHISPER_MODEL"):
        load_settings(env_file=None)


def fake_faster_whisper(monkeypatch: pytest.MonkeyPatch, calls: list[dict[str, Any]]) -> None:
    module = types.ModuleType("faster_whisper")

    def download_model(size_or_id: str, **options: Any) -> str:
        calls.append(
            {"repo": size_or_id, **options, "offline_env": os.environ.get("HF_HUB_OFFLINE")}
        )
        return "/models/hf/hub/whisper"

    module.download_model = download_model  # type: ignore[attr-defined]
    module.WhisperModel = lambda *_a, **_k: FakeModel()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", module)


def test_offline_mode_uses_only_local_files(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    """Transversal 14: `MODELS_OFFLINE=true` liga `HF_HUB_OFFLINE=1` e só lê o cache."""
    monkeypatch.setenv("MODELS_OFFLINE", "true")
    calls: list[dict[str, Any]] = []
    fake_faster_whisper(monkeypatch, calls)
    build_transcriber(load_settings(env_file=None)).transcribe(AUDIO, LANGUAGE)
    assert calls == [
        {
            "repo": "dropbox-dash/faster-whisper-large-v3-turbo",
            "local_files_only": True,
            "cache_dir": str(settings.models_root / "hf" / "hub"),
            "revision": settings.whisper_revision,
            "offline_env": "1",
        }
    ]
    assert os.environ["HF_HOME"] == str(settings.models_root / "hf")


def test_online_mode_may_download(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    calls: list[dict[str, Any]] = []
    fake_faster_whisper(monkeypatch, calls)
    build_transcriber(settings).transcribe(AUDIO, LANGUAGE)
    assert calls[0]["local_files_only"] is False
    assert calls[0]["offline_env"] is None


def test_missing_model_fails_with_message(settings: Settings) -> None:
    def fetch(_source: ModelSource) -> str:
        raise OSError("cache vazio")

    engine = WhisperTranscriber(
        source=build_transcriber(settings).source, compute_type="int8", fetch=fetch
    )
    with pytest.raises(EngineFailure) as caught:
        engine.transcribe(AUDIO, LANGUAGE)
    assert caught.value.message == messages.MODELS_UNAVAILABLE


def test_model_error_fails_with_message(settings: Settings) -> None:
    def load(_path: str, _compute: str) -> FakeModel:
        raise RuntimeError("CUDA out of memory")

    engine = WhisperTranscriber(
        source=build_transcriber(settings).source,
        compute_type="int8",
        fetch=lambda _s: "/m",
        load=load,
    )
    with pytest.raises(EngineFailure) as caught:
        engine.transcribe(AUDIO, LANGUAGE)
    assert caught.value.message == messages.TRANSCRIPTION_FAILED


def test_module_does_not_import_library() -> None:
    """Import do engine não carrega o faster-whisper: só o subprocesso carrega."""
    assert whisper.__name__ and "faster_whisper" not in sys.modules
