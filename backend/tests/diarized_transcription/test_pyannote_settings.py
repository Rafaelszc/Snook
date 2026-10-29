"""Task 26.2: Pyannote com revisão fixa, `expected_speakers` como dica e erro de `HF_TOKEN`.
Bibliotecas trocadas por módulos falsos: sem torch, sem rede, sem modelo."""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from snook.core.settings import Settings, SettingsError, load_settings
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines.base import EngineFailure, Turn
from snook.modules.diarized_transcription.engines.pyannote import (
    SUBMODEL_REVISIONS,
    PyannoteDiarizer,
    pin_config,
)
from snook.modules.diarized_transcription.service import build_diarizer
from tests.diarized_transcription.fake_libs import (
    CONFIG,
    Annotation,
    FakePipeline,
    GatedRepoError,
    HfHubHTTPError,
    Hub,
    LocalEntryNotFoundError,
    Problem,
    RepositoryNotFoundError,
    Resolution,
    Specifications,
    TorchVersion,
    install,
)

pytestmark = pytest.mark.usefixtures("hub_env")

AUDIO = Path("/audios/.tmp/a.flac")
TOKEN = "hf_segredo_do_operador_123"
PIPELINE_REVISION = "84fd25912480287da0247647c3d2b4853cb3ee5d"


def diarizer(settings: Settings, pipeline: FakePipeline) -> PyannoteDiarizer:
    real = build_diarizer(settings)
    return PyannoteDiarizer(
        source=real.source,
        token=real.token,
        load=lambda _source, _token: pipeline,
        decode=lambda _audio: {"waveform": None, "sample_rate": 16000},
    )


def test_expected_speakers_is_passed(settings: Settings) -> None:
    """`diarized-transcription` 7: `expected_speakers` vira `num_speakers`."""
    pipeline = FakePipeline()
    turns = diarizer(settings, pipeline).diarize(AUDIO, 3)
    assert pipeline.calls == [{"num_speakers": 3}]
    assert turns == [Turn("SPEAKER_00", 0.0, 2.0), Turn("SPEAKER_01", 2.5, 4.0)]


def test_without_expected_speakers_runs_without_number(settings: Settings) -> None:
    pipeline = FakePipeline()
    diarizer(settings, pipeline).diarize(AUDIO, None)
    assert pipeline.calls == [{}]


def test_pipeline_error_is_diarization_failure(settings: Settings) -> None:
    class Broken(FakePipeline):
        def __call__(self, audio: dict[str, Any], **options: Any) -> Annotation:
            raise RuntimeError("tensor")

    with pytest.raises(EngineFailure) as caught:
        diarizer(settings, Broken()).diarize(AUDIO, None)
    assert caught.value.message == messages.DIARIZATION_FAILED


def test_pin_config_fixes_every_submodel() -> None:
    """SEC-22: os submodelos do `config.yaml` também ficam em revisão fixa."""
    pinned = pin_config(json.loads(json.dumps(CONFIG)))["pipeline"]["params"]
    assert (
        pinned["segmentation"]
        == "pyannote/segmentation-3.0@" + SUBMODEL_REVISIONS["pyannote/segmentation-3.0"]
    )
    assert pinned["embedding"].endswith("@837717ddb9ff5507820346191109dc79c958d614")


def test_pin_config_refuses_unknown_submodel() -> None:
    config = json.loads(json.dumps(CONFIG))
    config["pipeline"]["params"]["embedding"] = "outro/modelo"
    with pytest.raises(ValueError):
        pin_config(config)


@pytest.mark.parametrize("value", ["main", "3.1", ""])
def test_settings_require_commit_hash(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, value: str
) -> None:
    if value == "":
        with pytest.raises(ValueError, match="hash de commit"):
            Settings(snook_master_key=settings.snook_master_key, pyannote_revision="")
        return
    monkeypatch.setenv("PYANNOTE_REVISION", value)
    with pytest.raises(SettingsError, match="PYANNOTE_REVISION"):
        load_settings(env_file=None)


@pytest.fixture
def hub(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Hub:
    return install(monkeypatch, tmp_path)


def real_diarizer(settings: Settings, token: str | None = TOKEN) -> PyannoteDiarizer:
    built = build_diarizer(settings)
    return PyannoteDiarizer(
        source=built.source,
        token=SecretStr(token) if token else None,
        decode=lambda _audio: {"waveform": None, "sample_rate": 16000},
    )


def test_downloads_pipeline_and_submodels_at_fixed_revisions(hub: Hub, settings: Settings) -> None:
    """SEC-22: config na revisão de `PYANNOTE_REVISION`, submodelos nas revisões fixas."""
    real_diarizer(settings).diarize(AUDIO, 2)
    cache = str(settings.models_root / "hf" / "hub")
    assert [(d["repo"], d["file"], d["revision"]) for d in hub.downloads] == [
        ("pyannote/speaker-diarization-3.1", "config.yaml", PIPELINE_REVISION),
        *[(name, "pytorch_model.bin", rev) for name, rev in SUBMODEL_REVISIONS.items()],
    ]
    assert {d["cache_dir"] for d in hub.downloads} == {cache}
    assert {d["token"] for d in hub.downloads} == {TOKEN}
    params = hub.loaded[0]["config"]["pipeline"]["params"]
    assert all("@" in params[key] for key in ("segmentation", "embedding"))
    assert hub.pipeline is not None and hub.pipeline.calls == [{"num_speakers": 2}]


def test_checkpoint_classes_allowed_before_load(hub: Hub, settings: Settings) -> None:
    """torch >= 2.6 carrega com `weights_only=True`: os checkpoints do pyannote 3.x trazem
    estas classes e falhavam com `UnpicklingError`. Só elas entram na lista, antes da carga."""
    real_diarizer(settings).diarize(AUDIO, None)
    expected = {TorchVersion, Specifications, Problem, Resolution}
    assert set(hub.safe_globals) == expected
    assert set(hub.safe_at_load) == expected


def test_unpickling_error_logs_refused_class(
    hub: Hub, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """Classe fora da lista: o log diz qual, para incluí-la (nome de classe, sem segredo)."""
    hub.error = RuntimeError(
        "Weights only load failed. Unsupported global: GLOBAL omegaconf.listconfig.ListConfig "
        "was not an allowed global by default."
    )
    with caplog.at_level(logging.WARNING), pytest.raises(EngineFailure):
        real_diarizer(settings).diarize(AUDIO, None)
    record = next(r for r in caplog.records if r.getMessage() == "pyannote.load_failed")
    assert record.__dict__["refused_global"] == "omegaconf.listconfig.ListConfig"


def test_offline_mode_reads_only_cache(
    monkeypatch: pytest.MonkeyPatch, hub: Hub, settings: Settings
) -> None:
    """Transversal 14."""
    monkeypatch.setenv("MODELS_OFFLINE", "true")
    real_diarizer(load_settings(env_file=None)).diarize(AUDIO, None)
    assert {d["local_files_only"] for d in hub.downloads} == {True}


@pytest.mark.parametrize(
    "error",
    [
        GatedRepoError("Access to model is restricted"),
        RepositoryNotFoundError("401"),
        HfHubHTTPError(401),
        HfHubHTTPError(403),
    ],
    ids=["sem-aceite", "repo-negado", "token-invalido", "proibido"],
)
def test_hf_access_errors_cite_token_and_terms(
    hub: Hub, settings: Settings, caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    """`diarized-transcription` 15, SEC-20: mensagem cita `HF_TOKEN` e o aceite, sem o valor."""
    hub.error = error
    caplog.set_level(logging.DEBUG)
    with pytest.raises(EngineFailure) as caught:
        real_diarizer(settings).diarize(AUDIO, None)
    assert caught.value.message == messages.HF_ACCESS_DENIED
    assert "HF_TOKEN" in caught.value.message and "aceite" in caught.value.message
    assert TOKEN not in caught.value.message
    assert TOKEN not in caplog.text


def test_missing_token_fails_with_hf_message(hub: Hub, settings: Settings) -> None:
    """`HF_TOKEN` ausente: o HuggingFace nega o modelo restrito."""
    hub.error = HfHubHTTPError(401)
    with pytest.raises(EngineFailure) as caught:
        real_diarizer(settings, token=None).diarize(AUDIO, None)
    assert caught.value.message == messages.HF_ACCESS_DENIED
    assert {d["token"] for d in hub.downloads} == {None}


def test_pipeline_none_is_access_denied(hub: Hub, settings: Settings) -> None:
    hub.pipeline = None
    with pytest.raises(EngineFailure) as caught:
        real_diarizer(settings).diarize(AUDIO, None)
    assert caught.value.message == messages.HF_ACCESS_DENIED


def test_offline_without_cache_is_models_unavailable(hub: Hub, settings: Settings) -> None:
    hub.error = LocalEntryNotFoundError("cache vazio")
    with pytest.raises(EngineFailure) as caught:
        real_diarizer(settings).diarize(AUDIO, None)
    assert caught.value.message == messages.MODELS_UNAVAILABLE


def test_other_download_error_is_diarization_failure(hub: Hub, settings: Settings) -> None:
    hub.error = HfHubHTTPError(500)
    with pytest.raises(EngineFailure) as caught:
        real_diarizer(settings).diarize(AUDIO, None)
    assert caught.value.message == messages.DIARIZATION_FAILED


def test_token_is_not_in_repr(settings: Settings) -> None:
    """SEC-20: engine em log ou erro não mostra o `HF_TOKEN`."""
    assert TOKEN not in repr(real_diarizer(settings))


def test_token_comes_from_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    token = build_diarizer(load_settings(env_file=None)).token
    assert token is not None and token.get_secret_value() == TOKEN
