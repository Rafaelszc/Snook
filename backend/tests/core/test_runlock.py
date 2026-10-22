import subprocess
import sys
from pathlib import Path

import pytest

from snook.core.runlock import RunLock, RunLockError

_HOLD = """
import sys, time
from snook.core.runlock import RunLock
lock = RunLock(sys.argv[1])
lock.acquire()
print("locked", flush=True)
time.sleep(60)
"""

_TRY = """
import sys
from snook.core.runlock import RunLock, RunLockError
try:
    RunLock(sys.argv[1]).acquire()
except RunLockError as exc:
    print(exc)
    sys.exit(3)
"""


def _spawn_holder(path: Path) -> subprocess.Popen[str]:
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _HOLD, str(path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "locked"
    return proc


def test_second_acquire_in_same_process_fails_with_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "snook.lock"
    first = RunLock(path)
    first.acquire()
    try:
        with pytest.raises(RunLockError, match="snook.lock"):
            RunLock(path).acquire()
    finally:
        first.release()


def test_release_frees_the_lock(tmp_path: Path) -> None:
    path = tmp_path / "snook.lock"
    first = RunLock(path)
    first.acquire()
    first.release()
    second = RunLock(path)
    second.acquire()
    second.release()


def test_context_manager_acquires_and_releases(tmp_path: Path) -> None:
    path = tmp_path / "snook.lock"
    with RunLock(path), pytest.raises(RunLockError):
        RunLock(path).acquire()
    with RunLock(path):
        pass


def test_second_process_fails_while_lock_is_held(tmp_path: Path) -> None:
    path = tmp_path / "snook.lock"
    with RunLock(path):
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", _TRY, str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    assert result.returncode == 3
    assert "snook.lock" in result.stdout


def test_lock_is_released_when_owner_process_dies(tmp_path: Path) -> None:
    path = tmp_path / "snook.lock"
    holder = _spawn_holder(path)
    try:
        with pytest.raises(RunLockError):
            RunLock(path).acquire()
        holder.kill()
        holder.wait(timeout=10)
        lock = RunLock(path)
        lock.acquire()
        lock.release()
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(timeout=10)
        if holder.stdout:
            holder.stdout.close()
