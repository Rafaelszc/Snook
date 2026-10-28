import json
import sqlite3
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.events import PartsReady
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.transcript_split import service as transcript_split
from tests.auth.helpers import rows
from tests.meetings.helpers import set_fields
from tests.transcript_split.helpers import FakeEstimate, confirmed

DURATION = 4000.0
SNAPSHOT = ActiveProvider(provider="ollama", model="llama3", context_window=8192)


def story(
    name: str = "Cadastrar cliente",
    *,
    requested_by: str | None = "Ana",
    requested_at: str = "00:00:05",
    criteria: int = 1,
) -> dict[str, Any]:
    return {
        "name": name,
        "as_a": "atendente",
        "i_want": f"{name.lower()} com CPF",
        "so_that": "eu possa abrir pedidos",
        "priority": "high",
        "story_points": 5,
        "requested_by": requested_by,
        "requested_at": requested_at,
        "acceptance_criteria": [
            {"given": f"dado {i}", "when": f"quando {i}", "then": f"então {i}"}
            for i in range(1, criteria + 1)
        ],
    }


def backlog(*epics: tuple[str, list[dict[str, Any]]]) -> str:
    """Resposta crua de "Gerar": `(nome da Epic, US)`."""
    return json.dumps(
        {"epics": [{"name": name, "user_stories": stories} for name, stories in epics]}
    )


class FakeGenerate:
    """ "Gerar" fake: devolve `replies` em ordem (texto ou exceção) e registra cada chamada.
    `on_call` roda antes de responder, como algo que muda durante a geração."""

    def __init__(self) -> None:
        self.replies: list[str | Exception] = []
        self.calls: list[dict[str, Any]] = []
        self.on_call: Callable[[int], None] | None = None

    def __call__(self, **request: Any) -> str:
        self.calls.append(request)
        if self.on_call is not None:
            self.on_call(len(self.calls))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def generating(
    client: TestClient,
    settings: Settings,
    uow: Callable[[], UnitOfWork],
    ranges: list[tuple[int, int]] | None = None,
    *,
    run_id: str = "run-1",
) -> str:
    """Reunião confirmada (Ana e Bia, 3 segmentos) em `generating`, com Partes `ranges`."""
    meeting_id = confirmed(client, settings)
    save_parts(uow, meeting_id, ranges or [(0, 2)])
    set_fields(
        settings.database_path,
        meeting_id,
        status="generating",
        run_id=run_id,
        duration_seconds=DURATION,
    )
    return meeting_id


def save_parts(
    uow: Callable[[], UnitOfWork], meeting_id: str, ranges: list[tuple[int, int]]
) -> None:
    with uow() as unit:
        transcript_split.save_parts(unit, SNAPSHOT, meeting_id, ranges, estimate=FakeEstimate())


def part_texts(uow: Callable[[], UnitOfWork], meeting_id: str) -> list[str]:
    with uow() as unit:
        return [part.text for part in transcript_split.list_parts(unit, meeting_id)]


def parts_ready(client: TestClient, meeting_id: str, run_id: str = "run-1") -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.event_bus.publish(PartsReady(meeting_id=meeting_id, run_id=run_id))


def regenerating(settings: Settings, meeting_id: str, run_id: str) -> None:
    """Reunião de volta a `generating` com trabalho novo, como depois de "Tentar novamente"."""
    set_fields(settings.database_path, meeting_id, status="generating", run_id=run_id)


def stored_stories(settings: Settings, meeting_id: str) -> list[tuple[Any, ...]]:
    """`(us_number, Epic, nome da US)` em ordem de `us_number`."""
    with sqlite3.connect(settings.database_path) as conn:
        return conn.execute(
            "SELECT s.us_number, e.name, s.name FROM user_stories s "
            "JOIN epics e ON e.id = s.epic_id WHERE s.meeting_id = ? ORDER BY s.us_number",
            (meeting_id,),
        ).fetchall()


def count(settings: Settings, table: str) -> int:
    return int(rows(settings.database_path, f"SELECT count(*) FROM {table}")[0][0])  # noqa: S608
