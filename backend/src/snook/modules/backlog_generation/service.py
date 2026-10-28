from collections.abc import Callable

from snook.core.events import Event, EventBus, PartsReady
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation.repository import BacklogRepository as BacklogRepository
from snook.modules.backlog_generation.runner import Generate as Generate
from snook.modules.backlog_generation.runner import GenerationRunner as GenerationRunner

# --- Interface para outros módulos (`02-architecture.md`, "Interfaces internas") ---


def backlog(uow: UnitOfWork) -> BacklogRepository:
    """Interface "Backlog": Epics, US e critérios na transação de `uow`."""
    return BacklogRepository(uow.session)


def next_us_number(uow: UnitOfWork, meeting_id: str) -> int:
    """Próximo `us_number` da Reunião, já reservado (`backlog-review` 19)."""
    return backlog(uow).next_us_number(meeting_id)


def subscribe(bus: EventBus, consumer: Callable[[Event], None]) -> None:
    """02-architecture, "Avisos": `backlog_generation` consome `PartsReady` com `generating`."""
    bus.subscribe(PartsReady, consumer)
