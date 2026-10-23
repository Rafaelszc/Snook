"""Caminhos sob `/audios` (ADR-0014, ADR-0018) e checagens de SEC-15."""

import logging
import os
import re
import shutil
import uuid
from pathlib import Path

logger = logging.getLogger("snook.files")

TMP_DIR_NAME = ".tmp"
_MEETING_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_FILE_NAME = re.compile(r"^[a-z]+\.[a-z0-9]+$")
_LOGGED_ID_MAX = 100


class UnsafePathError(Exception):
    """Alvo recusado por SEC-15. Quem chama para; não há caminho alternativo."""


def _reject(meeting_id: str, reason: str) -> UnsafePathError:
    extra = {"meeting_id": meeting_id[:_LOGGED_ID_MAX], "reason": reason}
    logger.error("security.path_rejected", extra=extra)
    return UnsafePathError(reason)


def tmp_dir(root: Path) -> Path:
    return root / TMP_DIR_NAME


def new_tmp_path(root: Path) -> Path:
    """Temporário com nome gerado pelo servidor; nome enviado nunca entra no caminho."""
    return tmp_dir(root) / str(uuid.uuid4())


def is_meeting_id(value: str) -> bool:
    return _MEETING_ID.match(value) is not None


def meeting_dir(root: Path, meeting_id: str) -> Path:
    """`/audios/<meeting_id>`, só se o caminho resolvido fica um nível abaixo da raiz."""
    if not is_meeting_id(meeting_id):
        raise _reject(meeting_id, "invalid_meeting_id")
    real_root = Path(os.path.realpath(root))
    target = Path(os.path.realpath(root / meeting_id))
    # Link simbólico para fora, para a raiz ou para o diretório de outra Reunião.
    if target.parent != real_root or target.name != meeting_id:
        raise _reject(meeting_id, "outside_root")
    return target


def _check_tmp_file(root: Path, path: Path) -> Path:
    real = Path(os.path.realpath(path))
    if real.parent != Path(os.path.realpath(tmp_dir(root))):
        raise _reject("", "outside_tmp")
    return real


def move_into_meeting_dir(root: Path, source: Path, meeting_id: str, file_name: str) -> Path:
    """Move um temporário de `/audios/.tmp/` para `/audios/<meeting_id>/<file_name>`."""
    if _FILE_NAME.match(file_name) is None:
        raise _reject(meeting_id, "invalid_file_name")
    real_source = _check_tmp_file(root, source)
    target_dir = meeting_dir(root, meeting_id)
    target_dir.mkdir(exist_ok=True)
    target = target_dir / file_name
    os.replace(real_source, target)  # mesmo volume: atômico (ADR-0018)
    return target


def discard_tmp(root: Path, path: Path) -> None:
    """Apaga um temporário de `/audios/.tmp/`, se ainda existe."""
    _check_tmp_file(root, path).unlink(missing_ok=True)


def remove_meeting_dir(root: Path, meeting_id: str) -> None:
    target = meeting_dir(root, meeting_id)
    if target.exists():
        shutil.rmtree(target)
