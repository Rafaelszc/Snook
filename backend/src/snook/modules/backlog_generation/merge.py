"""Junção de Epics e numeração de `US-id` (`backlog-generation` 16 a 21; Q47, Q48, Q57)."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from snook.core.text import normalize
from snook.modules.backlog_generation.validation import (
    BacklogResponse,
    Named,
    UserStory,
    resolve_requester,
)


@dataclass(frozen=True)
class NewStory:
    us_number: int
    story: UserStory
    requested_by: int | None


@dataclass
class NewEpic:
    name: str
    stories: list[NewStory] = field(default_factory=list)


def merge_backlogs(
    responses: Sequence[BacklogResponse], participants: Sequence[Named]
) -> list[NewEpic]:
    """Respostas em ordem das Partes → Epics da Reunião. Mesmo nome sem caixa e espaços nas pontas
    vira uma Epic, com o nome da primeira ocorrência (16); US na ordem de chegada (17), numeradas
    de 1 sem lacuna (18). Epic sem US fica de fora (20)."""
    epics: dict[str, NewEpic] = {}
    number = 0
    for response in responses:
        for epic in response.epics:
            merged = epics.setdefault(normalize(epic.name), NewEpic(name=epic.name))
            for story in epic.user_stories:
                number += 1
                merged.stories.append(
                    NewStory(
                        us_number=number,
                        story=story,
                        requested_by=resolve_requester(story.requested_by, participants),
                    )
                )
    return [epic for epic in epics.values() if epic.stories]


def epic_names(responses: Sequence[BacklogResponse]) -> list[str]:
    """Nomes das Epics já criadas na geração, para a próxima chamada (`backlog-generation` 4)."""
    return [epic.name for epic in merge_backlogs(responses, participants=[])]


def us_id(number: int) -> str:
    """`US-01`; a partir da centésima, três dígitos (`US-100`) (19)."""
    return f"US-{number:02d}"
