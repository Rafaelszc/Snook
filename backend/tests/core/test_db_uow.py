import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, ForeignKey, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from snook.core.db import create_db_engine, create_session_factory, upgrade_database
from snook.core.uow import UnitOfWork


class _TestBase(DeclarativeBase):
    pass


class _Parent(_TestBase):
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)


class _Child(_TestBase):
    __tablename__ = "children"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    eng = create_db_engine(tmp_path / "snook.db")
    _TestBase.metadata.create_all(eng)
    yield eng
    eng.dispose()


class _Recorder:
    """Publicador falso: no instante da chamada, lê o banco por outra conexão."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.events: list[object] = []
        self.parents_seen: list[int] = []

    def __call__(self, event: object) -> None:
        with self.engine.connect() as conn:
            self.parents_seen.append(len(conn.execute(select(_Parent)).all()))
        self.events.append(event)


def test_every_connection_has_pragmas(engine: Engine) -> None:
    with engine.connect() as first, engine.connect() as second:
        for conn in (first, second):
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_foreign_keys_are_enforced(engine: Engine) -> None:
    factory = create_session_factory(engine)
    with pytest.raises(IntegrityError), factory() as session:
        session.add(_Child(id=1, parent_id=99))
        session.commit()


def test_commit_persists_and_publishes_only_after_commit(engine: Engine) -> None:
    recorder = _Recorder(engine)
    with UnitOfWork(create_session_factory(engine), recorder) as uow:
        uow.session.add(_Parent(id=1))
        uow.publish_after_commit("created")
        assert recorder.events == []
    assert recorder.events == ["created"]
    assert recorder.parents_seen == [1]


def test_events_keep_order(engine: Engine) -> None:
    recorder = _Recorder(engine)
    with UnitOfWork(create_session_factory(engine), recorder) as uow:
        uow.publish_after_commit("a")
        uow.publish_after_commit("b")
    assert recorder.events == ["a", "b"]


def test_rollback_discards_data_and_events(engine: Engine) -> None:
    recorder = _Recorder(engine)
    with (
        pytest.raises(RuntimeError, match="falha"),
        UnitOfWork(create_session_factory(engine), recorder) as uow,
    ):
        uow.session.add(_Parent(id=1))
        uow.publish_after_commit("created")
        raise RuntimeError("falha")
    assert recorder.events == []
    with Session(engine) as session:
        assert session.scalars(select(_Parent)).all() == []


def test_failed_commit_publishes_nothing(engine: Engine) -> None:
    recorder = _Recorder(engine)
    with (
        pytest.raises(IntegrityError),
        UnitOfWork(create_session_factory(engine), recorder) as uow,
    ):
        uow.session.add(_Child(id=1, parent_id=99))
        uow.publish_after_commit("created")
    assert recorder.events == []


def test_publisher_failure_does_not_undo_commit(
    engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    seen: list[object] = []

    def flaky(event: object) -> None:
        if event == "boom":
            raise RuntimeError("consumidor quebrou")
        seen.append(event)

    with (
        caplog.at_level(logging.ERROR),
        UnitOfWork(create_session_factory(engine), flaky) as uow,
    ):
        uow.session.add(_Parent(id=1))
        uow.publish_after_commit("boom")
        uow.publish_after_commit("next")
    assert seen == ["next"]
    with Session(engine) as session:
        assert len(session.scalars(select(_Parent)).all()) == 1
    assert "event publish failed" in caplog.text


def test_alembic_upgrade_head_runs_on_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.db"
    upgrade_database(db_path)
    assert db_path.exists()


def test_after_commit_runs_in_order_with_events(engine: Engine) -> None:
    recorder = _Recorder(engine)
    with UnitOfWork(create_session_factory(engine), recorder) as uow:
        uow.session.add(_Parent(id=1))
        uow.after_commit(lambda: recorder.events.append("moved"))
        uow.publish_after_commit("created")
        assert recorder.events == []
    assert recorder.events == ["moved", "created"]


def test_failed_after_commit_stops_later_events(
    engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    recorder = _Recorder(engine)

    def broken() -> None:
        raise OSError("disco cheio")

    with (
        caplog.at_level(logging.ERROR),
        UnitOfWork(create_session_factory(engine), recorder) as uow,
    ):
        uow.session.add(_Parent(id=1))
        uow.after_commit(broken)
        uow.publish_after_commit("created")
    assert recorder.events == []
    assert "after-commit action failed" in caplog.text


def test_rollback_skips_after_commit(engine: Engine) -> None:
    ran: list[str] = []
    with (
        pytest.raises(RuntimeError),
        UnitOfWork(create_session_factory(engine), lambda _e: None) as uow,
    ):
        uow.after_commit(lambda: ran.append("moved"))
        raise RuntimeError("falha")
    assert ran == []
