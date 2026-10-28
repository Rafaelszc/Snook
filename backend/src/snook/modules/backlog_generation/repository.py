from collections.abc import Mapping, Sequence

from sqlalchemy import delete, func, select, update
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

    def epic(self, meeting_id: str, epic_id: int) -> Epic | None:
        """Epic `epic_id` só se for da Reunião (SEC-02)."""
        query = select(Epic).where(Epic.meeting_id == meeting_id, Epic.id == epic_id)
        return self._session.scalar(query)

    def epic_named(self, meeting_id: str, name: str) -> Epic | None:
        """Epic de mesmo nome pela regra de `normalize` (Q57)."""
        query = select(Epic).where(Epic.meeting_id == meeting_id, Epic.name_norm == normalize(name))
        return self._session.scalar(query)

    def add_epic(self, meeting_id: str, name: str) -> Epic:
        """Epic sem US no fim da lista."""
        last = self._session.scalar(
            select(func.max(Epic.position)).where(Epic.meeting_id == meeting_id)
        )
        epic = Epic(
            meeting_id=meeting_id, name=name, name_norm=normalize(name), position=(last or 0) + 1
        )
        self._session.add(epic)
        self._session.flush()
        return epic

    def rename_epic(self, epic: Epic, name: str) -> None:
        epic.name = name
        epic.name_norm = normalize(name)
        self._session.flush()

    def merge_epic(self, source: Epic, target: Epic) -> None:
        """US de `source` vão para o fim de `target`, na ordem; `source` é apagada."""
        last = self._session.scalar(
            select(func.max(UserStory.position)).where(UserStory.epic_id == target.id)
        )
        moved = self._session.scalars(
            select(UserStory).where(UserStory.epic_id == source.id).order_by(UserStory.position)
        )
        for offset, story in enumerate(moved, start=1):
            story.epic_id = target.id
            story.position = (last or 0) + offset
        self._session.flush()
        self.delete_epic(source)

    def has_stories(self, epic: Epic) -> bool:
        query = select(UserStory.id).where(UserStory.epic_id == epic.id).limit(1)
        return self._session.scalar(query) is not None

    def delete_epic(self, epic: Epic) -> None:
        self._session.delete(epic)
        self._session.flush()

    def story(self, meeting_id: str, story_id: int) -> UserStory | None:
        """US `story_id` só se for da Reunião (SEC-02)."""
        query = select(UserStory).where(
            UserStory.meeting_id == meeting_id, UserStory.id == story_id
        )
        return self._session.scalar(query)

    def add_story(
        self,
        epic: Epic,
        fields: Mapping[str, object],
        criteria: Sequence[tuple[str, str, str]],
    ) -> UserStory:
        """US no fim de `epic` com o próximo `us_number` e `criteria` (`given`, `when`, `then`)."""
        story = UserStory(
            meeting_id=epic.meeting_id,
            epic_id=epic.id,
            us_number=self.next_us_number(epic.meeting_id),
            position=self._next_story_position(epic),
            **fields,
        )
        self._session.add(story)
        self._session.flush()
        for given, when, then in criteria:
            self.add_criterion(story, given, when, then)
        return story

    def update_story(self, story: UserStory, changes: Mapping[str, object]) -> None:
        """Grava `changes` (colunas de `UserStory`); `us_number` e Epic não mudam aqui."""
        for column, value in changes.items():
            setattr(story, column, value)
        self._session.flush()

    def move_story(self, story: UserStory, epic: Epic) -> None:
        """US para o fim de `epic`, mesmo `us_number` (`backlog-review` 16)."""
        if story.epic_id == epic.id:
            return
        story.position = self._next_story_position(epic)
        story.epic_id = epic.id
        self._session.flush()

    def delete_story(self, story: UserStory) -> None:
        """Critérios saem em cascata; contador não desce (`backlog-review` 19)."""
        self._session.delete(story)
        self._session.flush()

    def reassign_requester(self, meeting_id: str, old_id: int, new_id: int) -> None:
        """US da Reunião com solicitante `old_id` passam a `new_id` (`backlog-review` 24)."""
        query = (
            update(UserStory)
            .where(UserStory.meeting_id == meeting_id, UserStory.requested_by == old_id)
            .values(requested_by=new_id)
        )
        self._session.execute(query)

    def criterion(self, meeting_id: str, criterion_id: int) -> AcceptanceCriterion | None:
        """Critério `criterion_id` só se a US for da Reunião (SEC-02)."""
        query = (
            select(AcceptanceCriterion)
            .join(UserStory, UserStory.id == AcceptanceCriterion.user_story_id)
            .where(UserStory.meeting_id == meeting_id, AcceptanceCriterion.id == criterion_id)
        )
        return self._session.scalar(query)

    def add_criterion(
        self, story: UserStory, given: str, when: str, then: str
    ) -> AcceptanceCriterion:
        """Critério no fim da US (`backlog-review` 20)."""
        last = self._session.scalar(
            select(func.max(AcceptanceCriterion.position)).where(
                AcceptanceCriterion.user_story_id == story.id
            )
        )
        criterion = AcceptanceCriterion(
            user_story_id=story.id, given=given, when_=when, then_=then, position=(last or 0) + 1
        )
        self._session.add(criterion)
        self._session.flush()
        return criterion

    def update_criterion(self, criterion: AcceptanceCriterion, changes: Mapping[str, str]) -> None:
        """`changes` com `given`, `when`, `then`."""
        columns = {"given": "given", "when": "when_", "then": "then_"}
        for field, value in changes.items():
            setattr(criterion, columns[field], value)
        self._session.flush()

    def criteria_count(self, user_story_id: int) -> int:
        query = select(func.count()).where(AcceptanceCriterion.user_story_id == user_story_id)
        return self._session.scalar(query) or 0

    def delete_criterion(self, criterion: AcceptanceCriterion) -> None:
        self._session.delete(criterion)
        self._session.flush()

    def _next_story_position(self, epic: Epic) -> int:
        last = self._session.scalar(
            select(func.max(UserStory.position)).where(UserStory.epic_id == epic.id)
        )
        return (last or 0) + 1

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
