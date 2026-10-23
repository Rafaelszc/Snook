"""Executor com um subprocesso `spawn` por trabalho (ADR-0007). O `ProcessPoolExecutor` do
Python 3.12 não tem API pública para matar worker em andamento; aqui cada `Process` é nosso e
`terminate()` é público. Cada trabalho também devolve ao sistema a memória dos modelos.
Subprocesso é `daemon`: não pode criar filho de `multiprocessing` (ffmpeg por `subprocess` pode)."""

import multiprocessing
import threading
from collections.abc import Callable
from concurrent.futures import Executor, Future
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import Any, TypeVar

T = TypeVar("T")
_OK = "ok"
_ERROR = "error"


class WorkerDied(RuntimeError):
    """Subprocesso morreu sem devolver resultado (OOM, sinal, parada)."""


def _child(sender: Connection, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
    try:
        outcome: tuple[str, Any] = (_OK, fn(*args))
    except BaseException as exc:  # a exceção volta ao processo principal
        outcome = (_ERROR, exc)
    try:
        sender.send(outcome)
    except Exception:  # resultado ou exceção que não serializa
        sender.send((_ERROR, RuntimeError(type(outcome[1]).__name__)))
    finally:
        sender.close()


class SpawnExecutor(Executor):
    def __init__(self) -> None:
        self._context = multiprocessing.get_context("spawn")
        self._lock = threading.Lock()
        self._processes: set[BaseProcess] = set()
        self._closed = False

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> "Future[T]":
        if kwargs:
            raise TypeError("SpawnExecutor aceita só argumentos posicionais")
        receiver, sender = self._context.Pipe(duplex=False)
        with self._lock:
            if self._closed:
                raise RuntimeError("executor parado")
            process = self._context.Process(target=_child, args=(sender, fn, args), daemon=True)
            process.start()
            self._processes.add(process)
        sender.close()
        future: Future[T] = Future()
        future.set_running_or_notify_cancel()
        watcher = threading.Thread(
            target=self._watch, args=(process, receiver, future), daemon=True
        )
        watcher.start()
        return future

    def _watch(self, process: BaseProcess, receiver: Connection, future: "Future[Any]") -> None:
        try:
            kind, value = receiver.recv()
        except (EOFError, OSError):
            kind, value = None, None
        finally:
            receiver.close()
        process.join()
        with self._lock:
            self._processes.discard(process)
        if kind == _OK:
            future.set_result(value)
        elif kind == _ERROR:
            future.set_exception(value)
        else:
            future.set_exception(WorkerDied(f"subprocesso saiu com código {process.exitcode}"))

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """`wait=False` mata o que está rodando: a parada não espera a transcrição."""
        with self._lock:
            self._closed = True
            processes = list(self._processes)
        if not wait:
            for process in processes:
                process.terminate()
        for process in processes:
            process.join()
