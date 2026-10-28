"""`GenerationRunner`: consome "Partes prontas" e gera o backlog Parte a Parte (ADR-0007)."""

import logging
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from snook.core.events import Event
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import messages
from snook.modules.backlog_generation.merge import epic_names, merge_backlogs
from snook.modules.backlog_generation.repository import BacklogRepository
from snook.modules.backlog_generation.validation import (
    BacklogResponse,
    InvalidBacklogResponse,
    parse_backlog,
)
from snook.modules.llm_providers import service as llm_providers
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.meetings import service as meetings
from snook.modules.participants import service as participants
from snook.modules.participants.schemas import ParticipantOut
from snook.modules.transcript_split import service as transcript_split
from snook.shared.prompts import load_backlog_response_schema, load_backlog_system_prompt

logger = logging.getLogger("snook.backlog_generation")


class Generate(Protocol):
    """ "Gerar" de `llm-providers`, já com cifra e adapters. Testes passam fake."""

    def __call__(
        self,
        *,
        user_id: str,
        provider_snapshot: ActiveProvider,
        system_prompt: str,
        content: str,
        json_schema: dict[str, Any],
        max_output_tokens: int,
    ) -> str: ...


@dataclass(frozen=True)
class _Job:
    """Tudo lido uma vez, no início da geração (`backlog-generation` 5)."""

    user_id: str
    snapshot: ActiveProvider
    duration_seconds: float
    participants: list[ParticipantOut]
    participants_text: str
    parts: list[transcript_split.Part]
    budget: int


class _PartTooLarge(Exception):
    """Parte não cabe no orçamento do modelo lido no início (`backlog-generation` 32)."""


def build_content(participants_text: str, part_text: str, epics: Sequence[str]) -> str:
    """Participantes, Epics já criadas (só a partir da segunda Parte) e o "Texto da Parte" sem
    alteração (`backlog-generation` 3, 4)."""
    sections = [participants_text]
    if epics:
        sections.append("\n".join(["Epics já criadas:", *(f"- {name}" for name in epics)]))
    sections.append(f"Texto da Parte:\n{part_text}")
    return "\n\n".join(sections)


def _provider_message(error: llm_providers.LLMError, index: int) -> str:
    """Mensagem pt-BR própria do tipo (`backlog-generation` 26)."""
    if isinstance(error, llm_providers.CredentialRejected):
        if error.reason == "unreadable_key":
            return messages.KEY_UNREADABLE
        return messages.CREDENTIAL_REJECTED
    if isinstance(error, llm_providers.ProviderUnreachable):
        return messages.PROVIDER_UNREACHABLE
    if isinstance(error, llm_providers.ModelNotFound):
        return messages.MODEL_NOT_FOUND
    if isinstance(error, llm_providers.ContextLimitExceeded):
        return messages.CONTEXT_LIMIT_EXCEEDED.format(index=index)
    if isinstance(error, llm_providers.ProviderRateLimited):
        return messages.PROVIDER_RATE_LIMITED
    return messages.GENERATION_FAILED


class GenerationRunner:
    """Pool de threads (`GENERATION_WORKERS`); cada geração chama "Gerar" em sequência."""

    def __init__(
        self,
        workers: int,
        *,
        uow_factory: Callable[[], UnitOfWork],
        generate: Generate,
        estimate: transcript_split.Estimate,
        now: Callable[[], datetime],
    ) -> None:
        self._workers = workers
        self._uow = uow_factory
        self._generate = generate
        self._estimate = estimate
        self._now = now
        self._executor: Executor | None = None
        self._running: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def start(self) -> None:
        self._executor = ThreadPoolExecutor(self._workers, thread_name_prefix="generation")

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    def submit(self, event: Event) -> None:
        if self._executor is None:
            logger.warning("generation.not_started", extra={"meeting_id": event.meeting_id})
            return
        self._executor.submit(self.run, event)

    def run(self, event: Event) -> None:
        """Uma geração por aviso. Aviso repetido com a mesma geração em curso é ignorado (33)."""
        key = (event.meeting_id, event.run_id)
        with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            self._run(event)
        finally:
            with self._lock:
                self._running.discard(key)

    def _run(self, event: Event) -> None:
        """Só com a Reunião em `generating` e o `run_id` do aviso. Qualquer falha leva a
        `failed` etapa `generation` sem gravar nada (22; SEC-19)."""
        index = 0
        try:
            job = self._load(event)
            if job is None:
                return
            responses: list[BacklogResponse] = []
            for part in job.parts:
                index = part.index
                responses.append(self._generate_part(job, part, responses))
            self._save(event, job, responses)
        except _PartTooLarge:
            self._fail(event, messages.PART_TOO_LARGE.format(index=index))
        except llm_providers.NoActiveProvider:
            self._fail(event, messages.NO_ACTIVE_PROVIDER)
        except InvalidBacklogResponse as error:
            self._fail(event, messages.INVALID_RESPONSE.format(index=index, reason=error.message))
        except llm_providers.LLMError as error:
            logger.warning(
                "generation.provider_error",
                extra={"meeting_id": event.meeting_id, "reason": error.reason},
            )
            self._fail(event, _provider_message(error, index))
        except Exception:
            logger.exception("generation.failed", extra={"meeting_id": event.meeting_id})
            self._fail(event, messages.UNEXPECTED)

    def _load(self, event: Event) -> _Job | None:
        meeting_id = event.meeting_id
        with self._uow() as uow:
            if not meetings.is_current_run(uow, meeting_id, event.run_id, status="generating"):
                return None
            user_id = meetings.read_owner(uow, meeting_id)
            snapshot = transcript_split.owner_provider(uow, meeting_id)
            return _Job(
                user_id=user_id,
                snapshot=snapshot,
                duration_seconds=meetings.get_owned_meeting(
                    uow, user_id, meeting_id
                ).duration_seconds,
                participants=participants.list_participants(uow, meeting_id),
                participants_text=transcript_split.participants_text(uow, meeting_id),
                parts=transcript_split.list_parts(uow, meeting_id),
                budget=transcript_split.part_budget(
                    uow, snapshot, meeting_id, estimate=self._estimate
                ),
            )

    def _generate_part(
        self, job: _Job, part: transcript_split.Part, previous: Sequence[BacklogResponse]
    ) -> BacklogResponse:
        """Reestima a Parte antes de chamar (32; RT-10)."""
        tokens = self._estimate(job.snapshot.provider, job.snapshot.model, part.text)
        if not transcript_split.fits(tokens, job.budget):
            raise _PartTooLarge
        raw = self._generate(
            user_id=job.user_id,
            provider_snapshot=job.snapshot,
            system_prompt=load_backlog_system_prompt(),
            content=build_content(job.participants_text, part.text, epic_names(previous)),
            json_schema=load_backlog_response_schema(),
            max_output_tokens=transcript_split.output_reserve(job.snapshot.context_window),
        )
        return parse_backlog(raw, duration_seconds=job.duration_seconds)

    def _save(self, event: Event, job: _Job, responses: Sequence[BacklogResponse]) -> None:
        """Uma transação: substitui o backlog, registra a marca e leva a `done` (23, 25, 34).
        Reunião excluída ou trabalho trocado: nada é gravado."""
        meeting_id = event.meeting_id
        with self._uow() as uow:
            if not meetings.is_current_run(uow, meeting_id, event.run_id, status="generating"):
                return
            BacklogRepository(uow.session).replace(
                meeting_id, merge_backlogs(responses, job.participants)
            )
            now = self._now()
            meetings.mark_backlog_saved(uow, meeting_id, now=now)
            meetings.update_status(uow, meeting_id, "done", now=now)

    def _fail(self, event: Event, message: str) -> None:
        try:
            with self._uow() as uow:
                if meetings.is_current_run(
                    uow, event.meeting_id, event.run_id, status="generating"
                ):
                    meetings.update_status(
                        uow,
                        event.meeting_id,
                        "failed",
                        failed_stage="generation",
                        message=message,
                        now=self._now(),
                    )
        except Exception:
            logger.exception("generation.fail_not_saved", extra={"meeting_id": event.meeting_id})
