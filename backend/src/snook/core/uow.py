import logging
from collections.abc import Callable
from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("snook.uow")

Publisher = Callable[[object], None]


class UnitOfWork:
    """Uma transação, um commit. Avisos só saem depois do commit; rollback os descarta."""

    def __init__(self, session_factory: sessionmaker[Session], publish: Publisher) -> None:
        self._session_factory = session_factory
        self._publish = publish
        self._session: Session | None = None
        self._pending: list[object] = []

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork fora do bloco with")
        return self._session

    def publish_after_commit(self, event: object) -> None:
        self._pending.append(event)

    def __enter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        self._pending = []
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self.session
        pending, self._pending = self._pending, []
        try:
            if exc_type is None:
                session.commit()
            else:
                session.rollback()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()
            self._session = None
        if exc_type is None:
            self._flush(pending)

    def _flush(self, events: list[object]) -> None:
        for event in events:
            try:
                self._publish(event)
            except Exception:
                logger.exception("event publish failed: %s", type(event).__name__)
