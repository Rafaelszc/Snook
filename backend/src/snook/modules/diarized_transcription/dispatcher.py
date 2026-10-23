"""`TranscriptionDispatcher` (ADR-0007, ADR-0010): pega a `pending` mais antiga de Usuário abaixo
de `TRANSCRIPTION_MAX_PER_USER`, com até `TRANSCRIPTION_WORKERS` trabalhos ao mesmo tempo."""

import logging
import multiprocessing
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import BrokenExecutor, Executor, Future, ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from snook.core import files
from snook.core.events import MeetingCreated, RetryRequested
from snook.core.uow import Publisher, UnitOfWork
from snook.modules.diarized_transcription import messages, repository
from snook.modules.diarized_transcription.engines.base import EngineFailure, Engines
from snook.modules.diarized_transcription.merge import Segment
from snook.modules.diarized_transcription.pipeline import Job, run_job
from snook.modules.meetings import service as meetings

logger = logging.getLogger("snook.transcription")

TREATED_FILE = "treated.flac"


def process_pool(workers: int) -> Executor:
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))


@dataclass(frozen=True)
class _Claim:
    meeting_id: str
    run_id: str
    job: Job


class TranscriptionDispatcher:
    def __init__(
        self,
        *,
        engines: Engines,
        workers: int,
        max_per_user: int,
        audio_root: Path,
        now: Callable[[], datetime],
        executor_factory: Callable[[int], Executor] = process_pool,
    ) -> None:
        self.engines = engines
        self._workers = workers
        self._max_per_user = max_per_user
        self._audio_root = audio_root
        self._now = now
        self._executor_factory = executor_factory
        self._executor: Executor | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._publish: Publisher = lambda _event: None
        self._running = 0
        self._stopped = False
        self._lock = threading.RLock()
        if workers <= max_per_user:
            # Critério 30 de `diarized-transcription` não vale (ADR-0010).
            logger.warning(
                "transcription.isolation_off",
                extra={"workers": workers, "max_per_user": max_per_user},
            )

    @property
    def running(self) -> int:
        """Trabalhos em andamento agora."""
        return self._running

    def start(self, session_factory: sessionmaker[Session], publish: Publisher) -> None:
        """Passo 6 da subida, depois de reenfileirar (02-architecture, "Retry e reinício")."""
        with self._lock:
            self._session_factory = session_factory
            self._publish = publish
            self._stopped = False
        self.wake()

    def stop(self) -> None:
        """Na parada: nada mais é gravado; a próxima subida marca as interrompidas (Q58)."""
        with self._lock:
            self._stopped = True
            executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    def on_event(self, event: MeetingCreated | RetryRequested) -> None:
        """Aviso só acorda o dispatcher com a Reunião em `pending` e o `run_id` atual."""
        if isinstance(event, RetryRequested) and event.stage != "transcription":
            return
        if self._session_factory is None:
            return  # antes da subida: `start` lê as `pending` do banco
        with self._uow() as uow:
            current = meetings.is_current_run(uow, event.meeting_id, event.run_id, status="pending")
        if current:
            self.wake()

    def wake(self) -> None:
        with self._lock:
            while not self._stopped and self._session_factory is not None:
                if self._running >= self._workers:
                    return
                claim = self._claim()
                if claim is None:
                    return
                self._running += 1
                self._submit(claim)

    def _uow(self) -> UnitOfWork:
        if self._session_factory is None:
            raise RuntimeError("dispatcher antes de start()")
        return UnitOfWork(self._session_factory, self._publish)

    def _claim(self) -> _Claim | None:
        """`pending` -> `processing` num commit, descartando dado de tentativa anterior."""
        root = self._audio_root
        with self._uow() as uow:
            work = meetings.next_pending_for_transcription(
                uow, max_per_user=self._max_per_user, audio_root=root
            )
            if work is None:
                return None
            meeting_id = work.meeting_id
            run_id = meetings.update_status(uow, meeting_id, "processing", now=self._now())
            repository.delete_segments(uow.session, meeting_id)
            uow.after_commit(lambda: files.remove_meeting_file(root, meeting_id, TREATED_FILE))
        job = Job(
            original_path=work.original_path,
            treated_path=files.tmp_dir(root) / f"{uuid.uuid4()}.flac",
            duration_seconds=work.duration_seconds,
            expected_speakers=work.expected_speakers,
        )
        logger.info("transcription.started", extra={"meeting_id": meeting_id})
        return _Claim(meeting_id=meeting_id, run_id=run_id, job=job)

    def _submit(self, claim: _Claim) -> None:
        try:
            if self._executor is None:
                self._executor = self._executor_factory(self._workers)
            future = self._executor.submit(run_job, self.engines, claim.job)
        except Exception as exc:
            if isinstance(exc, BrokenExecutor):
                self._executor = None  # subprocesso morreu: o próximo trabalho cria outro pool
            logger.exception("transcription.submit_failed", extra={"meeting_id": claim.meeting_id})
            failed: Future[list[Segment]] = Future()
            failed.set_exception(exc)
            future = failed
        future.add_done_callback(lambda done: self._done(claim, done))

    def _done(self, claim: _Claim, future: "Future[list[Segment]]") -> None:
        try:
            self._finish(claim, future)
        except Exception:
            logger.exception("transcription.save_failed", extra={"meeting_id": claim.meeting_id})
            self._try_fail(claim)  # nunca status preso em `processing` (SEC-19)
        finally:
            self._discard(claim)
            with self._lock:
                self._running -= 1
            self.wake()

    def _finish(self, claim: _Claim, future: "Future[list[Segment]]") -> None:
        if self._stopped:
            return
        try:
            segments = future.result()
        except EngineFailure as failure:
            self._save_failure(claim, failure.message)
            return
        except Exception:
            logger.exception("transcription.engine_failed", extra={"meeting_id": claim.meeting_id})
            self._save_failure(claim, messages.UNEXPECTED)
            return
        self._save_segments(claim, segments)

    def _is_current(self, uow: UnitOfWork, claim: _Claim) -> bool:
        """Reunião excluída ou com outro `run_id`: o resultado é descartado (`diarized` 17)."""
        current = meetings.is_current_run(uow, claim.meeting_id, claim.run_id, status="processing")
        if not current:
            logger.info("transcription.discarded", extra={"meeting_id": claim.meeting_id})
        return current

    def _save_segments(self, claim: _Claim, segments: list[Segment]) -> None:
        root = self._audio_root
        with self._uow() as uow:
            if not self._is_current(uow, claim):
                return
            repository.add_segments(uow.session, claim.meeting_id, segments)
            meetings.update_status(uow, claim.meeting_id, "transcribed", now=self._now())

            def keep_treated_audio() -> None:
                if files.meeting_dir(root, claim.meeting_id).is_dir():  # sem recriar excluída
                    files.move_into_meeting_dir(
                        root, claim.job.treated_path, claim.meeting_id, TREATED_FILE
                    )
                logger.info(
                    "transcription.done",
                    extra={"meeting_id": claim.meeting_id, "segments": len(segments)},
                )

            uow.after_commit(keep_treated_audio)

    def _save_failure(self, claim: _Claim, message: str) -> None:
        with self._uow() as uow:
            if not self._is_current(uow, claim):
                return
            meetings.update_status(
                uow,
                claim.meeting_id,
                "failed",
                failed_stage="transcription",
                message=message,
                now=self._now(),
            )
        logger.info("transcription.failed", extra={"meeting_id": claim.meeting_id})

    def _try_fail(self, claim: _Claim) -> None:
        try:
            self._save_failure(claim, messages.UNEXPECTED)
        except Exception:
            logger.exception("transcription.fail_failed", extra={"meeting_id": claim.meeting_id})

    def _discard(self, claim: _Claim) -> None:
        try:
            files.discard_tmp(self._audio_root, claim.job.treated_path)
        except Exception:
            logger.exception("transcription.discard_failed", extra={"meeting_id": claim.meeting_id})
