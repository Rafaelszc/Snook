"""`SpawnExecutor`: subprocesso real, `spawn`. Funções da biblioteca padrão atravessam o pickle."""

import json
import operator
import os
import time
from functools import partial

import pytest
from pydantic import SecretStr

from snook.core.logging import setup_logging
from snook.core.settings import Settings
from snook.modules.diarized_transcription.spawn_executor import SpawnExecutor, WorkerDied
from tests.diarized_transcription.boundary_child import log_failure
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


def test_initializer_gives_child_json_logs_with_redaction(
    settings: Settings, capfd: pytest.CaptureFixture[str]
) -> None:
    """Sem logging configurado, o filho perdia o `extra` (tipo do erro) e a redação."""
    token = "hf_" + "a" * 34
    settings = settings.model_copy(update={"hf_token": SecretStr(token)})
    executor = SpawnExecutor(initializer=partial(setup_logging, settings))

    executor.submit(log_failure, token).result(TIMEOUT)
    executor.shutdown()

    lines = [json.loads(line) for line in capfd.readouterr().out.splitlines() if line]
    entry = next(e for e in lines if e["event"] == "pyannote.load_failed")
    assert entry["error"] == "LocalEntryNotFoundError"
    assert entry["detail"] == "[REDACTED]"


def test_dispatcher_pool_configures_child_logging(settings: Settings) -> None:
    from datetime import UTC, datetime

    from snook.modules.diarized_transcription.service import build_dispatcher

    dispatcher = build_dispatcher(settings, lambda: datetime.now(UTC))
    pool = dispatcher._executor_factory(1)
    assert isinstance(pool, SpawnExecutor)
    assert isinstance(pool._initializer, partial)
    assert pool._initializer.func is setup_logging
    assert pool._initializer.args == (settings,)
