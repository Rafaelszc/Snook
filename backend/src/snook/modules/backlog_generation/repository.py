from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from snook.core.text import normalize
from snook.modules.backlog_generation.merge import NewEpic
from snook.modules.backlog_generation.models import (
    AcceptanceCriterion,
    BacklogCounter,
    Epic,
    UserStory,
)


class BacklogRepository:
    """Leitura e escrita do backlog da Reunião, na transação de quem chama. Só ORM (SEC-10)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def epics(self, meeting_id: str) -> list[Epic]:
        query = select(Epic).where(Epic.meeting_id == meeting_id).order_by(Epic.position)
        return list(self._session.scalars(query))

    def stories(self, meeting_id: str) -> list[UserStory]:
        """Em ordem de `us_number`."""
        query = (
            select(UserStory)
            .where(UserStory.meeting_id == meeting_id)
            .order_by(UserStory.us_number)
        )
        return list(self._session.scalars(query))

    def criteria(self, user_story_id: int) -> list[AcceptanceCriterion]:
        query = (
            select(AcceptanceCriterion)
            .where(AcceptanceCriterion.user_story_id == user_story_id)
            .order_by(AcceptanceCriterion.position)
        )
        return list(self._session.scalars(query))

    def replace(self, meeting_id: str, epics: Sequence[NewEpic]) -> None:
        """Apaga as Epics (US e critérios em cascata), grava `epics` e põe o contador no maior
        `us_number` gravado: regeneração recomeça em `US-01` (Q50)."""
        self._session.execute(delete(Epic).where(Epic.meeting_id == meeting_id))
        self._session.flush()
        last = 0
        for epic_position, new_epic in enumerate(epics, start=1):
            epic = Epic(
                meeting_id=meeting_id,
                name=new_epic.name,
                name_norm=normalize(new_epic.name),
                position=epic_position,
            )
            self._session.add(epic)
            self._session.flush()
            for story_position, new in enumerate(new_epic.stories, start=1):
                story = UserStory(
                    meeting_id=meeting_id,
                    epic_id=epic.id,
                    us_number=new.us_number,
                    name=new.story.name,
                    as_a=new.story.as_a,
                    i_want=new.story.i_want,
                    so_that=new.story.so_that,
                    priority=new.story.priority,
                    story_points=new.story.story_points,
                    requested_by=new.requested_by,
                    requested_at_seconds=new.story.requested_at_seconds,
                    position=story_position,
                )
                self._session.add(story)
                self._session.flush()
                self._session.add_all(
                    AcceptanceCriterion(
                        user_story_id=story.id,
                        given=criterion.given,
                        when_=criterion.when,
                        then_=criterion.then,
                        position=position,
                    )
                    for position, criterion in enumerate(new.story.acceptance_criteria, start=1)
                )
                last = max(last, new.us_number)
        self._counter(meeting_id).last_us_number = last
        self._session.flush()

    def next_us_number(self, meeting_id: str) -> int:
        """Número depois do maior já usado e o reserva; excluído não volta (`backlog-review` 19)."""
        counter = self._counter(meeting_id)
        existing = self._session.scalar(
            select(func.max(UserStory.us_number)).where(UserStory.meeting_id == meeting_id)
        )
        counter.last_us_number = max(counter.last_us_number, existing or 0) + 1
        self._session.flush()
        return counter.last_us_number

    def _counter(self, meeting_id: str) -> BacklogCounter:
        counter = self._session.get(BacklogCounter, meeting_id)
        if counter is None:
            counter = BacklogCounter(meeting_id=meeting_id, last_us_number=0)
            self._session.add(counter)
        return counter
