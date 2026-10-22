import fcntl
import os
from pathlib import Path
from types import TracebackType


class RunLockError(Exception):
    pass


class RunLock:
    """Trava exclusiva de arquivo (`flock`). O kernel a solta quando o processo morre."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._fd: int | None = None

    def acquire(self) -> None:
        if self._fd is not None:
            return
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise RunLockError(
                f"{self._path} está em uso: outro processo do Snook (backend ou CLI de escrita) "
                "está rodando. Pare-o antes de continuar."
            ) from None
        except BaseException:
            os.close(fd)
            raise
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
