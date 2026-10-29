"""Bibliotecas falsas (`torch`, `yaml`, `huggingface_hub`, `pyannote`, `faster_whisper`) em
`sys.modules`: exercitam os loaders reais sem torch, sem rede e sem modelo."""

import json
import os
import sys
import types
from pathlib import Path
from typing import Any

import pytest

CONFIG = {
    "version": "3.1.0",
    "pipeline": {
        "name": "pyannote.audio.pipelines.SpeakerDiarization",
        "params": {
            "embedding": "pyannote/wespeaker-voxceleb-resnet34-LM",
            "segmentation": "pyannote/segmentation-3.0",
            "clustering": "AgglomerativeClustering",
        },
    },
}


class Segment:
    def __init__(self, start: float, end: float) -> None:
        self.start, self.end = start, end


class Annotation:
    def itertracks(self, yield_label: bool) -> list[tuple[Segment, str, str]]:
        assert yield_label
        return [(Segment(0.0, 2.0), "A", "SPEAKER_00"), (Segment(2.5, 4.0), "B", "SPEAKER_01")]


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, audio: dict[str, Any], **options: Any) -> Annotation:
        self.calls.append(options)
        return Annotation()


class RepositoryNotFoundError(Exception):
    pass


class GatedRepoError(RepositoryNotFoundError):
    pass


class LocalEntryNotFoundError(Exception):
    pass


class Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class HfHubHTTPError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"{status_code} for url https://huggingface.co/...")
        self.response = Response(status_code)


class Hub:
    """Registra downloads; `error` faz o download falhar."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.downloads: list[dict[str, Any]] = []
        self.error: Exception | None = None
        self.loaded: list[dict[str, Any]] = []
        self.pipeline: FakePipeline | None = FakePipeline()
        self.whisper: list[dict[str, Any]] = []
        self.safe_globals: list[type] = []
        self.safe_at_load: list[type] = []

    def hf_hub_download(self, repo_id: str, filename: str, **options: Any) -> str:
        self.downloads.append({"repo": repo_id, "file": filename, **options})
        if self.error is not None:
            raise self.error
        path = self.tmp / f"{len(self.downloads)}-{filename}"
        path.write_text(json.dumps(CONFIG))
        return str(path)

    def add_safe_globals(self, classes: list[type]) -> None:
        self.safe_globals.extend(classes)

    def from_pretrained(self, path: Path, use_auth_token: str | None) -> FakePipeline | None:
        self.safe_at_load = list(self.safe_globals)
        self.loaded.append({"config": json.loads(Path(path).read_text()), "token": use_auth_token})
        return self.pipeline

    def download_model(self, size_or_id: str, **options: Any) -> str:
        offline = os.environ.get("HF_HUB_OFFLINE")
        self.whisper.append({"repo": size_or_id, **options, "offline_env": offline})
        return str(self.tmp / "whisper")


class TorchVersion(str):
    pass


class Specifications:
    pass


class Problem:
    pass


class Resolution:
    pass


def install(monkeypatch: pytest.MonkeyPatch, tmp: Path) -> Hub:
    fake = Hub(tmp)
    modules: dict[str, Any] = {
        "torch": types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
        "torch.serialization": types.SimpleNamespace(add_safe_globals=fake.add_safe_globals),
        "torch.torch_version": types.SimpleNamespace(TorchVersion=TorchVersion),
        "yaml": types.SimpleNamespace(safe_load=json.loads, safe_dump=json.dumps),
        "huggingface_hub": types.SimpleNamespace(hf_hub_download=fake.hf_hub_download),
        "huggingface_hub.errors": types.SimpleNamespace(
            LocalEntryNotFoundError=LocalEntryNotFoundError,
            RepositoryNotFoundError=RepositoryNotFoundError,
        ),
        "huggingface_hub.utils": types.SimpleNamespace(HfHubHTTPError=HfHubHTTPError),
        "pyannote": types.SimpleNamespace(),
        "pyannote.audio": types.SimpleNamespace(
            Pipeline=types.SimpleNamespace(from_pretrained=fake.from_pretrained)
        ),
        "pyannote.audio.core.task": types.SimpleNamespace(
            Problem=Problem, Resolution=Resolution, Specifications=Specifications
        ),
        "faster_whisper": types.SimpleNamespace(download_model=fake.download_model),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    return fake
