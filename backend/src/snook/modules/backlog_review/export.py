"""Exportação do backlog (`backlog-review` 32 a 36; SEC-12). Sem Parte nem `id` interno."""

import json
import re
import unicodedata
from typing import Any, Literal

from snook.modules.backlog_review.schemas import EpicOut, UserStoryOut

ExportFormat = Literal["md", "json"]

MEDIA_TYPES: dict[ExportFormat, str] = {
    "md": "text/markdown; charset=utf-8",
    "json": "application/json",
}

SLUG_MAX = 60
SLUG_EMPTY = "reuniao"


def slug(title: str) -> str:
    """ASCII minúsculo `[a-z0-9-]`, até 60 caracteres; vazio vira `reuniao` (`05-api.md`)."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return value[:SLUG_MAX].rstrip("-") or SLUG_EMPTY


def filename(title: str, fmt: ExportFormat) -> str:
    return f"{slug(title)}-backlog.{fmt}"


def content_disposition(name: str) -> str:
    """`name` já é ASCII seguro (`slug`); vai nas duas formas do header."""
    return f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"


def render(fmt: ExportFormat, title: str, date: str, epics: list[EpicOut]) -> str:
    if fmt == "md":
        return _markdown(title, date, epics)
    return json.dumps(_document(title, date, epics), ensure_ascii=False, indent=2) + "\n"


def _markdown(title: str, date: str, epics: list[EpicOut]) -> str:
    """Formato da Q11 (`01-prd.md`, "Formato do backlog"), com cabeçalho e solicitante/quando
    depois de "Para", omitidos se vazios (`backlog-review` 33)."""
    blocks = [f"# {title}", f"Data: {date}"]
    for epic in epics:
        blocks.append(f"Epic: {epic.name}")
        blocks.extend(_story_markdown(story) for story in epic.user_stories)
    return "\n\n".join(blocks) + "\n"


def _story_markdown(story: UserStoryOut) -> str:
    lines = [
        f"{story.us_id}: {story.name}",
        f"Como {story.as_a}",
        f"Eu quero {story.i_want}",
        f"Para {story.so_that}",
    ]
    if story.requested_by is not None:
        lines.append(f"Solicitante: {story.requested_by.name}")
    if story.requested_at is not None:
        lines.append(f"Quando: {story.requested_at}")
    lines += [
        "",
        f"Prioridade: {story.priority}",
        f"Story Points: {story.story_points}",
        "Critérios de aceitação:",
    ]
    criteria = [
        f"Dado {c.given}\nQuando {c.when}\nEntão {c.then}" for c in story.acceptance_criteria
    ]
    return "\n".join(lines) + "\n" + "\n\n".join(criteria)


def _document(title: str, date: str, epics: list[EpicOut]) -> dict[str, Any]:
    return {
        "title": title,
        "date": date,
        "epics": [
            {"name": epic.name, "user_stories": [_story_json(s) for s in epic.user_stories]}
            for epic in epics
        ],
    }


def _story_json(story: UserStoryOut) -> dict[str, Any]:
    return {
        "us_id": story.us_id,
        "name": story.name,
        "as_a": story.as_a,
        "i_want": story.i_want,
        "so_that": story.so_that,
        "requested_by": story.requested_by.name if story.requested_by is not None else None,
        "requested_at": story.requested_at,
        "priority": story.priority,
        "story_points": story.story_points,
        "acceptance_criteria": [
            {"given": c.given, "when": c.when, "then": c.then} for c in story.acceptance_criteria
        ],
    }
