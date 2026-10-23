"""`TranscriptionDispatcher` (ADR-0007, ADR-0010): pega a `pending` mais antiga de Usuário abaixo
de `TRANSCRIPTION_MAX_PER_USER`, com até `TRANSCRIPTION_WORKERS` trabalhos ao mesmo tempo."""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Executor, Future
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
from snook.modules.diarized_transcription.spawn_executor import SpawnExecutor
from snook.modules.meetings import service as meetings

logger = logging.getLogger("snook.transcription")

TREATED_FILE = "treated.flac"
CLAIM_RETRY_SECONDS = 5.0


def process_pool(_workers: int) -> Executor:
    """Um subprocesso `spawn` por trabalho; o dispatcher limita a `TRANSCRIPTION_WORKERS`."""
    return SpawnExecutor()


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
        claim_retry_seconds: float = CLAIM_RETRY_SECONDS,
    ) -> None:
        self.engines = engines
        self._workers = workers
        self._max_per_user = max_per_user
        self._audio_root = audio_root
        self._now = now
        self._executor_factory = executor_factory
        self._claim_retry_seconds = claim_retry_seconds
        self._executor: Executor | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._publish: Publisher = lambda _event: None
        self._running = 0
        self._stopped = False
        self._waking = False
        self._wake_requested = False
        self._lock = threading.Lock()
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
            executor.shutdown(wait=False, cancel_futures=True)  # mata subprocesso em andamento

    def on_event(self, event: MeetingCreated | RetryRequested) -> None:
        """Aviso só acorda o dispatcher; ele escolhe no banco a `pending` certa, então aviso
        repetido ou de Reunião fora de `pending` não começa nada (`diarized` 3)."""
        if isinstance(event, RetryRequested) and event.stage != "transcription":
            return
        self.wake()

    def wake(self) -> None:
        """Uma thread enche os workers por vez; pedido durante o enchimento repete o laço, sem
        recursão (executor síncrono chama `_done` dentro do `submit`)."""
        with self._lock:
            self._wake_requested = True
            if self._waking:
                return
            self._waking = True
        try:
            while True:
                with self._lock:
                    if not self._wake_requested:
                        self._waking = False
                        return
                    self._wake_requested = False
                self._fill()
        except BaseException:
            with self._lock:
                self._waking = False
            raise

    def _fill(self) -> None:
        while True:
            with self._lock:
                if self._stopped or self._session_factory is None:
                    return
                if self._running >= self._workers:
                    return
            try:
                claim = self._claim()
            except Exception:
                # Banco ocupado ou falha passageira: a fila não para (SEC-19).
                logger.exception("transcription.claim_failed")
                self._retry_later()
                return
            if claim is None:
                return
            with self._lock:
                self._running += 1
            self._submit(claim)

    def _retry_later(self) -> None:
        timer = threading.Timer(self._claim_retry_seconds, self.wake)
        timer.daemon = True
        timer.start()

    def _uow(self) -> UnitOfWork:
        if self._session_factory is None:
            raise RuntimeError("dispatcher antes de start()")
        return UnitOfWork(self._session_factory, self._publish)

    def _claim(self) -> _Claim | None:
        """`pending` -> `processing` num commit, descartando dado de tentativa anterior.
        Original indisponível vai a `failed` no mesmo commit, e a escolha segue para a próxima."""
        while True:
            claim, unavailable = self._claim_one()
            if not unavailable:
                return claim

    def _claim_one(self) -> tuple[_Claim | None, bool]:
        root = self._audio_root
        now = self._now()
        with self._uow() as uow:
            work = meetings.next_pending_for_transcription(
                uow, max_per_user=self._max_per_user, audio_root=root, now=now
            )
            if work is None:
                return None, False
            meeting_id = work.meeting_id
            run_id = meetings.update_status(uow, meeting_id, "processing", now=now)
            if work.original_path is None:
                meetings.update_status(
                    uow,
                    meeting_id,
                    "failed",
                    failed_stage="transcription",
                    message=messages.ORIGINAL_UNAVAILABLE,
                    now=now,
                )
                logger.warning(
                    "transcription.original_unavailable", extra={"meeting_id": meeting_id}
                )
                return None, True
            repository.delete_segments(uow.session, meeting_id)
            uow.after_commit(lambda: files.remove_meeting_file(root, meeting_id, TREATED_FILE))
            original_path = work.original_path
        job = Job(
            original_path=original_path,
            treated_path=files.new_tmp_path(root).with_suffix(".flac"),
            duration_seconds=work.duration_seconds,
            expected_speakers=work.expected_speakers,
        )
        logger.info("transcription.started", extra={"meeting_id": meeting_id})
        return _Claim(meeting_id=meeting_id, run_id=run_id, job=job), False

    def _submit(self, claim: _Claim) -> None:
        try:
            with self._lock:
                if self._executor is None:
                    self._executor = self._executor_factory(self._workers)
                executor = self._executor
            future = executor.submit(run_job, self.engines, claim.job)
        except Exception as exc:
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
        with self._uow() as uow:
            if not self._is_current(uow, claim):
                return
            repository.add_segments(uow.session, claim.meeting_id, segments)
            meetings.update_status(uow, claim.meeting_id, "transcribed", now=self._now())
            uow.after_commit(lambda: self._keep_treated_audio(claim))
        logger.info(
            "transcription.done",
            extra={"meeting_id": claim.meeting_id, "segments": len(segments)},
        )

    def _keep_treated_audio(self, claim: _Claim) -> None:
        """Move sem recriar diretório de Reunião excluída; se a exclusão chega logo depois do
        move, apaga o que sobrou (`diarized` 17, SEC-24)."""
        root = self._audio_root
        try:
            files.move_into_meeting_dir(
                root, claim.job.treated_path, claim.meeting_id, TREATED_FILE, create_dir=False
            )
        except FileNotFoundError:
            logger.info("transcription.discarded", extra={"meeting_id": claim.meeting_id})
            return
        with self._uow() as uow:
            exists = meetings.meeting_exists(uow, claim.meeting_id)
        if not exists:
            files.remove_meeting_dir(root, claim.meeting_id)
            logger.info("transcription.discarded", extra={"meeting_id": claim.meeting_id})

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
