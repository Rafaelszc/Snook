"""`SpawnExecutor`: subprocesso real, `spawn`. Funções da biblioteca padrão atravessam o pickle."""

import operator
import os
import time

import pytest

from snook.modules.diarized_transcription.spawn_executor import SpawnExecutor, WorkerDied
from tests.diarized_transcription.conftest import wait_for

TIMEOUT = 60


@pytest.fixture
def executor() -> SpawnExecutor:
    return SpawnExecutor()


def test_returns_result(executor: SpawnExecutor) -> None:
    assert executor.submit(operator.add, 2, 3).result(TIMEOUT) == 5
    executor.shutdown()


def test_returns_exception(executor: SpawnExecutor) -> None:
    with pytest.raises(ValueError):
        executor.submit(int, "não é número").result(TIMEOUT)
    executor.shutdown()


def test_dead_worker_gives_worker_died(executor: SpawnExecutor) -> None:
    with pytest.raises(WorkerDied):
        executor.submit(os._exit, 3).result(TIMEOUT)
    executor.shutdown()


def test_shutdown_without_wait_kills_running_job(executor: SpawnExecutor) -> None:
    """A parada não espera a transcrição em andamento."""
    future = executor.submit(time.sleep, 60)
    wait_for(lambda: bool(executor._processes), timeout=TIMEOUT)
    started = time.monotonic()

    executor.shutdown(wait=False, cancel_futures=True)

    with pytest.raises(WorkerDied):
        future.result(TIMEOUT)
    assert time.monotonic() - started < 10
    assert not executor._processes


def test_refuses_job_after_shutdown(executor: SpawnExecutor) -> None:
    executor.shutdown()
    with pytest.raises(RuntimeError):
        executor.submit(operator.add, 1, 1)


def test_refuses_keyword_arguments(executor: SpawnExecutor) -> None:
    with pytest.raises(TypeError):
        executor.submit(operator.add, 1, b=1)
    executor.shutdown()
