"""Exportação do backlog (`backlog-review` 32 a 36; SEC-12; Q75). Sem Parte nem `id` interno."""

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


def filename(title: str, fmt: ExportFormat, date: str) -> str:
    """Markdown `backlog_<slug>_<data>.md` (Q75); JSON `<slug>-backlog.json` (`05-api.md`)."""
    if fmt == "md":
        return f"backlog_{slug(title)}_{date}.md"
    return f"{slug(title)}-backlog.{fmt}"


def content_disposition(name: str) -> str:
    """`name` já é ASCII seguro (`slug`); vai nas duas formas do header."""
    return f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"


def render(fmt: ExportFormat, title: str, date: str, epics: list[EpicOut]) -> str:
    if fmt == "md":
        return _markdown(title, date, epics)
    return json.dumps(_document(title, date, epics), ensure_ascii=False, indent=2) + "\n"


# Markdown: documento de Product Backlog (Q75; `backlog-review` 32, 33, 36).

PRIORITY_PT = {"High": "Alta", "Medium": "Média", "Low": "Baixa"}
LARGE_STORY_POINTS = 13
_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>|])")
_LINE_BREAK = re.compile(r"\s*[\r\n]+\s*")


def _markdown(title: str, date: str, epics: list[EpicOut]) -> str:
    stories = [(epic, story) for epic in epics for story in epic.user_stories]
    blocks = [_header(title, date, epics, stories)]
    if epics:
        blocks.append(_overview(stories))
        blocks.extend(_epic_section(n, epic) for n, epic in enumerate(epics, 1))
        blocks += [_priority_summary(stories), _epic_summary(epics), _considerations(epics)]
    return "\n\n".join(blocks) + "\n"


def _text(value: str) -> str:
    """Uma linha, caracteres de Markdown escapados; conteúdo preservado."""
    return _MD_SPECIAL.sub(r"\\\1", _LINE_BREAK.sub(" ", value).strip())


def _clause(value: str, *prefixes: str) -> str:
    """Tira conectivo repetido no início (ex.: "que" em "para que que") e ponto final."""
    text = _text(value).rstrip(". ")
    for prefix in prefixes:
        if text.lower().startswith(prefix + " "):
            return text[len(prefix) + 1 :]
    return text


def _priority(story: UserStoryOut) -> str:
    return PRIORITY_PT.get(story.priority, story.priority)


def _points(stories: list[UserStoryOut]) -> int:
    return sum(s.story_points for s in stories)


def _table(head: list[str], rows: list[list[str]], numeric: int) -> str:
    """`numeric` últimas colunas alinhadas à direita."""
    align = ["---"] * (len(head) - numeric) + ["---:"] * numeric
    lines = [head, align, *rows]
    return "\n".join("| " + " | ".join(cells) + " |" for cells in lines)


def _header(
    title: str, date: str, epics: list[EpicOut], stories: list[tuple[EpicOut, UserStoryOut]]
) -> str:
    name = _text(title)
    return "\n".join(
        [
            f"# Product Backlog: {name}",
            "",
            f"- **Reunião:** {name}",
            f"- **Data:** {date}",
            f"- **Projeto:** {name}",
            f"- **Épicos:** {len(epics)}",
            f"- **Histórias de usuário:** {len(stories)}",
            f"- **Story Points:** {_points([s for _, s in stories])}",
        ]
    )


def _overview(stories: list[tuple[EpicOut, UserStoryOut]]) -> str:
    rows = [
        [s.us_id, _text(e.name), _text(s.name), _priority(s), str(s.story_points)]
        for e, s in stories
    ]
    table = _table(["ID", "Épico", "História de Usuário", "Prioridade", "Story Points"], rows, 1)
    return f"## 1. Visão Geral do Backlog\n\n{table}"


def _epic_section(number: int, epic: EpicOut) -> str:
    stories = "\n\n".join(_story_markdown(s) for s in epic.user_stories)
    title = f"## 2.{number} Épico: {_text(epic.name)}"
    return f"{title}\n\n{stories}" if stories else title


def _story_markdown(story: UserStoryOut) -> str:
    fields = [("ID", story.us_id)]
    if story.requested_by is not None:
        fields.append(("Solicitante", _text(story.requested_by.name)))
    if story.requested_at is not None:
        fields.append(("Horário na reunião", story.requested_at))
    fields += [
        ("Perfil do usuário", _text(story.as_a)),
        ("Prioridade", _priority(story)),
        ("Story Points", str(story.story_points)),
    ]
    narrative = (
        f"Como {_clause(story.as_a, 'como')}, quero {_clause(story.i_want, 'eu quero', 'quero')}, "
        f"para que {_clause(story.so_that, 'para que', 'para', 'que')}."
    )
    criteria = [
        f"{n}. **Dado que** {_clause(c.given, 'dado que', 'dado', 'que')}, "
        f"**quando** {_clause(c.when, 'quando')}, **então** {_clause(c.then, 'então')}."
        for n, c in enumerate(story.acceptance_criteria, 1)
    ]
    return "\n".join(
        [
            f"### {story.us_id} — {_text(story.name)}",
            "",
            *(f"- **{label}:** {value}" for label, value in fields),
            "",
            "**História de usuário**",
            "",
            f"> {narrative}",
            "",
            "**Critérios de aceitação**",
            "",
            *criteria,
        ]
    )


def _priority_summary(stories: list[tuple[EpicOut, UserStoryOut]]) -> str:
    rows = []
    for key, label in PRIORITY_PT.items():
        group = [s for _, s in stories if s.priority == key]
        rows.append([label, str(len(group)), str(_points(group))])
    all_stories = [s for _, s in stories]
    rows.append(["**Total**", f"**{len(all_stories)}**", f"**{_points(all_stories)}**"])
    table = _table(["Prioridade", "Histórias", "Story Points"], rows, 2)
    return f"## 3. Resumo de Priorização\n\n{table}"


def _epic_summary(epics: list[EpicOut]) -> str:
    rows = [[_text(e.name), str(len(e.user_stories)), str(_points(e.user_stories))] for e in epics]
    stories = [s for e in epics for s in e.user_stories]
    rows.append(["**Total**", f"**{len(stories)}**", f"**{_points(stories)}**"])
    table = _table(["Épico", "Histórias", "Story Points"], rows, 2)
    return f"## 4. Resumo por Épico\n\n{table}"


def _ids(stories: list[UserStoryOut]) -> str:
    return ", ".join(s.us_id for s in stories)


def _considerations(epics: list[EpicOut]) -> str:
    """Só a partir dos dados do backlog: nenhuma funcionalidade nova (Q75)."""
    stories = [s for e in epics for s in e.user_stories]
    total = _points(stories)
    items: list[str] = []
    order = [
        f"{label} ({_ids(group)})"
        for key, label in PRIORITY_PT.items()
        if (group := [s for s in stories if s.priority == key])
    ]
    if order:
        items.append(f"**Ordem de implementação:** seguir a prioridade, {' → '.join(order)}.")
    largest = max(epics, key=lambda e: _points(e.user_stories))
    if len(epics) > 1 and total:
        share = round(100 * _points(largest.user_stories) / total)
        items.append(
            f"**Maior esforço:** o épico **{_text(largest.name)}** soma "
            f"{_points(largest.user_stories)} de {total} Story Points ({share}%); "
            "planejar sua capacidade nas sprints."
        )
    if large := [s for s in stories if s.story_points >= LARGE_STORY_POINTS]:
        items.append(
            f"**Refinamento:** {_ids(large)} com {LARGE_STORY_POINTS} Story Points; "
            "avaliar a divisão antes de entrar em sprint."
        )
    if orphan := [s for s in stories if s.requested_by is None]:
        items.append(
            f"**Validação:** {_ids(orphan)} sem solicitante identificado; "
            "confirmar o requisito com o Product Owner."
        )
    if criteria := sum(len(s.acceptance_criteria) for s in stories):
        items.append(
            f"**Testes de aceitação:** usar os {criteria} critérios de aceitação "
            "como base dos testes e da Definição de Pronto de cada história."
        )
    body = "\n".join(f"- {item}" for item in items) or "- Nenhuma história de usuário no backlog."
    return f"## 5. Considerações para o Desenvolvimento\n\n{body}"


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
