"""SEC-15: caminhos sob `/audios`."""

import logging
from pathlib import Path

import pytest

from snook.core import files

MEETING_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
OTHER_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "audios"
    files.tmp_dir(path).mkdir(parents=True)
    return path


def _tmp_file(root: Path, content: bytes = b"audio") -> Path:
    path = files.new_tmp_path(root)
    path.write_bytes(content)
    return path


def test_new_tmp_path_is_uuid_under_tmp(root: Path) -> None:
    path = files.new_tmp_path(root)
    assert path.parent == root / ".tmp"
    assert files.is_meeting_id(path.name)


def test_meeting_dir_is_one_level_below_root(root: Path) -> None:
    assert files.meeting_dir(root, MEETING_ID) == (root / MEETING_ID).resolve()


@pytest.mark.parametrize(
    "meeting_id",
    ["..", "", ".tmp", "../etc", f"{MEETING_ID}/..", MEETING_ID.upper(), "abc", f"/{MEETING_ID}"],
)
def test_forged_meeting_id_is_refused_and_logged(
    root: Path, meeting_id: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR), pytest.raises(files.UnsafePathError):
        files.meeting_dir(root, meeting_id)
    assert "security.path_rejected" in caplog.text


def test_symlink_outside_root_is_refused_and_target_kept(
    root: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("fica")
    (root / MEETING_ID).symlink_to(outside)
    with caplog.at_level(logging.ERROR), pytest.raises(files.UnsafePathError):
        files.remove_meeting_dir(root, MEETING_ID)
    assert (outside / "keep.txt").exists()
    assert "security.path_rejected" in caplog.text


def test_symlink_to_root_is_refused(root: Path) -> None:
    (root / MEETING_ID).symlink_to(root)
    with pytest.raises(files.UnsafePathError):
        files.remove_meeting_dir(root, MEETING_ID)
    assert root.exists()


def test_symlink_to_other_meeting_is_refused(root: Path) -> None:
    (root / OTHER_ID).mkdir()
    (root / OTHER_ID / "original.mp3").write_bytes(b"outra")
    (root / MEETING_ID).symlink_to(root / OTHER_ID)
    with pytest.raises(files.UnsafePathError):
        files.remove_meeting_dir(root, MEETING_ID)
    assert (root / OTHER_ID / "original.mp3").exists()


def test_symlink_to_tmp_is_refused(root: Path) -> None:
    (root / MEETING_ID).symlink_to(root / ".tmp")
    with pytest.raises(files.UnsafePathError):
        files.meeting_dir(root, MEETING_ID)


def test_remove_meeting_dir_removes_only_that_dir(root: Path) -> None:
    for meeting_id in (MEETING_ID, OTHER_ID):
        (root / meeting_id).mkdir()
        (root / meeting_id / "original.mp3").write_bytes(b"x")
    files.remove_meeting_dir(root, MEETING_ID)
    assert not (root / MEETING_ID).exists()
    assert (root / OTHER_ID / "original.mp3").exists()


def test_move_from_tmp_into_meeting_dir(root: Path) -> None:
    source = _tmp_file(root, b"conteudo")
    target = files.move_into_meeting_dir(root, source, MEETING_ID, "original.mp3")
    assert target == (root / MEETING_ID / "original.mp3").resolve()
    assert target.read_bytes() == b"conteudo"
    assert not source.exists()


def test_move_refuses_source_outside_tmp(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "x.mp3"
    outside.write_bytes(b"x")
    with pytest.raises(files.UnsafePathError):
        files.move_into_meeting_dir(root, outside, MEETING_ID, "original.mp3")
    assert outside.exists()
    assert not (root / MEETING_ID).exists()


@pytest.mark.parametrize("name", ["../original.mp3", "original", "a/b.mp3", ".mp3"])
def test_move_refuses_unsafe_file_name(root: Path, name: str) -> None:
    source = _tmp_file(root)
    with pytest.raises(files.UnsafePathError):
        files.move_into_meeting_dir(root, source, MEETING_ID, name)
    assert source.exists()


def test_discard_tmp_removes_temp_file_and_ignores_missing(root: Path) -> None:
    source = _tmp_file(root)
    files.discard_tmp(root, source)
    assert not source.exists()
    files.discard_tmp(root, source)


def test_discard_tmp_refuses_path_outside_tmp(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "keep.mp3"
    outside.write_bytes(b"x")
    with pytest.raises(files.UnsafePathError):
        files.discard_tmp(root, outside)
    assert outside.exists()
