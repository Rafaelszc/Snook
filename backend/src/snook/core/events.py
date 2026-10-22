import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, cast

logger = logging.getLogger("snook.events")

Stage = Literal["transcription", "generation"]


@dataclass(frozen=True)
class Event:
    """Todo aviso leva a Reunião e o `run_id` do trabalho. Consumidor compara com o banco."""

    meeting_id: str
    run_id: str


@dataclass(frozen=True)
class MeetingCreated(Event):
    pass


@dataclass(frozen=True)
class RetryRequested(Event):
    stage: Stage


@dataclass(frozen=True)
class ParticipantsConfirmed(Event):
    pass


@dataclass(frozen=True)
class PartsReady(Event):
    pass


E = TypeVar("E", bound=Event)


class EventBus:
    """Barramento em memória, síncrono, tipado por classe do aviso (ADR-0007)."""

    def __init__(self) -> None:
        self._consumers: dict[type[Event], list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: type[E], consumer: Callable[[E], None]) -> None:
        self._consumers[event_type].append(consumer)

    def publish(self, event: Event) -> None:
        for consumer in list(self._consumers.get(type(event), [])):
            try:
                cast(Callable[[Event], None], consumer)(event)
            except Exception:
                logger.exception("event consumer failed: %s", type(event).__name__)
