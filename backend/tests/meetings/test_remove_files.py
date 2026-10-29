import uuid
from pathlib import Path

import pytest

from snook.core.files import UnsafePathError
from snook.modules.meetings import service


def _meeting_dir(root: Path) -> tuple[str, Path]:
    meeting_id = str(uuid.uuid4())
    target = root / meeting_id
    target.mkdir(parents=True)
    (target / "original.mp3").write_bytes(b"x")
    (target / "treated.wav").write_bytes(b"y")
    return meeting_id, target


def test_removes_each_meeting_dir(tmp_path: Path) -> None:
    """SEC-24: diretórios das Reuniões saem; o resto de `/audios` fica."""
    root = tmp_path / "audios"
    first, first_dir = _meeting_dir(root)
    second, second_dir = _meeting_dir(root)
    other, other_dir = _meeting_dir(root)

    service.remove_meeting_files(root, [first, second])

    assert not first_dir.exists()
    assert not second_dir.exists()
    assert other_dir.exists()


def test_missing_dir_is_ignored(tmp_path: Path) -> None:
    """Reunião sem arquivo (falhou antes de mover) não impede a exclusão."""
    root = tmp_path / "audios"
    root.mkdir()

    service.remove_meeting_files(root, [str(uuid.uuid4())])


@pytest.mark.parametrize("bad", [".tmp", "..", "../fora", "nao-e-uuid", ""])
def test_invalid_id_removes_nothing(tmp_path: Path, bad: str) -> None:
    """SEC-15: `id` fora do formato UUID recusa tudo, antes de apagar qualquer coisa."""
    root = tmp_path / "audios"
    valid, valid_dir = _meeting_dir(root)
    (root / ".tmp").mkdir()

    with pytest.raises(UnsafePathError):
        service.remove_meeting_files(root, [valid, bad])

    assert valid_dir.exists()
    assert (root / ".tmp").exists()


def test_symlink_outside_root_is_refused(tmp_path: Path) -> None:
    """SEC-15: `realpath` precisa ficar um nível abaixo de `/audios`."""
    root = tmp_path / "audios"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("fica")
    meeting_id = str(uuid.uuid4())
    (root / meeting_id).symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        service.remove_meeting_files(root, [meeting_id])

    assert (outside / "keep.txt").exists()
