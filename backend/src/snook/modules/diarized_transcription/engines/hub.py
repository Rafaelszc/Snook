"""Cache e modo offline do HuggingFace (ADR-0014). Roda antes de importar `huggingface_hub`,
`faster_whisper` ou `pyannote`: as bibliotecas leem o ambiente no import."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSource:
    """Repositório e revisão fixos de um modelo, mais o cache em `/models`."""

    repo_id: str
    revision: str
    models_root: Path
    offline: bool

    @property
    def cache_dir(self) -> Path:
        return self.models_root / "hf" / "hub"


def configure(models_root: Path, offline: bool) -> None:
    """`HF_HOME=/models/hf`; com `MODELS_OFFLINE=true`, `HF_HUB_OFFLINE=1` (06-integrations)."""
    home = models_root / "hf"
    os.environ["HF_HOME"] = str(home)
    os.environ["HF_HUB_CACHE"] = str(home / "hub")
    os.environ["PYANNOTE_CACHE"] = str(home / "hub")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    else:
        os.environ.pop("HF_HUB_OFFLINE", None)
