"""Diarização com `pyannote/speaker-diarization-3.1` (ADR-0014). Pipeline e os dois submodelos
em revisão fixa (SEC-22): o `config.yaml` da revisão fixa é reescrito com `nome@revisão` antes de
carregar. `HF_TOKEN` nunca vai a log nem à mensagem (SEC-20). Bibliotecas só no subprocesso."""

import logging
import re
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import SecretStr

from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines import hub
from snook.modules.diarized_transcription.engines.base import EngineFailure, Turn

logger = logging.getLogger("snook.transcription.pyannote")

SAMPLE_RATE = 16000
CONFIG_FILE = "config.yaml"
WEIGHTS_FILE = "pytorch_model.bin"
# Submodelos citados pelo `config.yaml` da revisão fixa, cada um com a sua revisão fixa.
SUBMODEL_REVISIONS = {
    "pyannote/segmentation-3.0": "e66f3d3b9eb0873085418a7b813d3b369bf160bb",
    "pyannote/wespeaker-voxceleb-resnet34-LM": "837717ddb9ff5507820346191109dc79c958d614",
}
_SUBMODEL_PARAMS = ("segmentation", "embedding")
# Classe que o `weights_only` recusou: nome qualificado, sem dado do usuário.
_REFUSED_GLOBAL = re.compile(r"GLOBAL ([\w.]+)")


class _Segment(Protocol):
    start: float
    end: float


class _Annotation(Protocol):
    def itertracks(self, yield_label: bool) -> Iterator[tuple[_Segment, Any, Any]]: ...


class _Pipeline(Protocol):
    def __call__(self, audio: dict[str, Any], **options: Any) -> _Annotation: ...


def pin_config(config: dict[str, Any]) -> dict[str, Any]:
    """Troca cada submodelo por `nome@revisão`; submodelo sem revisão conhecida é recusado."""
    params = config["pipeline"]["params"]
    for key in _SUBMODEL_PARAMS:
        name = params[key]
        revision = SUBMODEL_REVISIONS.get(name)
        if revision is None:
            raise ValueError(f"submodelo sem revisão fixa: {key}")
        params[key] = f"{name}@{revision}"
    return config


def _access_failure(exc: Exception) -> EngineFailure:
    """Token ausente, inválido ou sem aceite dos termos: mensagem que cita `HF_TOKEN`
    (`diarized` 15). Offline sem cache: modelos ausentes."""
    from huggingface_hub.errors import LocalEntryNotFoundError, RepositoryNotFoundError
    from huggingface_hub.utils import HfHubHTTPError

    refused = _REFUSED_GLOBAL.search(str(exc))
    extra = {"error": type(exc).__name__}
    if refused is not None:
        extra["refused_global"] = refused.group(1)
    logger.warning("pyannote.load_failed", extra=extra)
    if isinstance(exc, LocalEntryNotFoundError):
        return EngineFailure(messages.MODELS_UNAVAILABLE)
    if isinstance(exc, RepositoryNotFoundError):  # inclui GatedRepoError
        return EngineFailure(messages.HF_ACCESS_DENIED)
    response = getattr(exc, "response", None) if isinstance(exc, HfHubHTTPError) else None
    if response is not None and response.status_code in (401, 403):
        return EngineFailure(messages.HF_ACCESS_DENIED)
    return EngineFailure(messages.DIARIZATION_FAILED)


def allow_checkpoint_classes() -> None:
    """torch >= 2.6 carrega checkpoint com `weights_only=True`. Os do pyannote 3.x trazem estas
    classes; liberar só elas mantém a recusa a qualquer outro objeto no pickle."""
    from pyannote.audio.core.task import Problem, Resolution, Specifications
    from torch.serialization import add_safe_globals
    from torch.torch_version import TorchVersion

    add_safe_globals([TorchVersion, Specifications, Problem, Resolution])


def load_pipeline(source: hub.ModelSource, token: SecretStr | None) -> _Pipeline:
    import torch
    import yaml
    from huggingface_hub import hf_hub_download
    from pyannote.audio import Pipeline

    allow_checkpoint_classes()

    secret = token.get_secret_value() if token is not None else None
    try:
        config_path = hf_hub_download(
            source.repo_id,
            CONFIG_FILE,
            revision=source.revision,
            token=secret,
            cache_dir=str(source.cache_dir),
            local_files_only=source.offline,
        )
        config = pin_config(yaml.safe_load(Path(config_path).read_text()))
        # Submodelo negado dentro do pyannote vira `None` e quebra longe; baixado aqui, o erro
        # de acesso chega tipado. Depois o pyannote só lê do cache.
        for name, revision in SUBMODEL_REVISIONS.items():
            hf_hub_download(
                name,
                WEIGHTS_FILE,
                revision=revision,
                token=secret,
                cache_dir=str(source.cache_dir),
                local_files_only=source.offline,
            )
        with tempfile.TemporaryDirectory() as folder:
            pinned = Path(folder) / CONFIG_FILE
            pinned.write_text(yaml.safe_dump(config))
            pipeline = Pipeline.from_pretrained(pinned, use_auth_token=secret)
    except EngineFailure:
        raise
    except ValueError as exc:
        logger.warning("pyannote.unpinned", extra={"error": str(exc)})
        raise EngineFailure(messages.DIARIZATION_FAILED) from None
    except Exception as exc:
        raise _access_failure(exc) from None
    if pipeline is None:
        raise EngineFailure(messages.HF_ACCESS_DENIED)
    if torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
    loaded: _Pipeline = pipeline
    return loaded


def decode_audio(audio: Path) -> dict[str, Any]:
    """FLAC mono 16 kHz em memória: o pyannote não depende do backend de I/O do torchaudio."""
    import torch
    from faster_whisper import decode_audio as decode

    samples = decode(str(audio), sampling_rate=SAMPLE_RATE)
    return {"waveform": torch.from_numpy(samples)[None, :], "sample_rate": SAMPLE_RATE}


@dataclass(frozen=True)
class PyannoteDiarizer:
    source: hub.ModelSource
    token: SecretStr | None
    load: Callable[[hub.ModelSource, SecretStr | None], _Pipeline] = load_pipeline
    decode: Callable[[Path], dict[str, Any]] = decode_audio

    def download(self) -> None:
        """`download-models`: baixa pipeline e submodelos para o cache."""
        hub.configure(self.source.models_root, self.source.offline)
        self.load(self.source, self.token)

    def diarize(self, audio: Path, num_speakers: int | None) -> list[Turn]:
        hub.configure(self.source.models_root, self.source.offline)
        pipeline = self.load(self.source, self.token)
        # `expected_speakers` é dica: ausente, o pipeline estima o número (`diarized` 7).
        options = {} if num_speakers is None else {"num_speakers": num_speakers}
        try:
            annotation = pipeline(self.decode(audio), **options)
            turns = [
                Turn(str(label), float(segment.start), float(segment.end))
                for segment, _track, label in annotation.itertracks(yield_label=True)
            ]
        except Exception as exc:
            logger.warning("pyannote.failed", extra={"error": type(exc).__name__})
            raise EngineFailure(messages.DIARIZATION_FAILED) from None
        return turns
