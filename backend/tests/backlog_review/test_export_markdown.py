"""`backlog-review` 32, 33, 36 (Q75): render Markdown direto, backlog com prioridades variadas."""

from pathlib import Path

from snook.modules.backlog_review import export
from snook.modules.backlog_review.schemas import (
    CriterionOut,
    EpicOut,
    RequesterOut,
    UserStoryOut,
)

SNAPSHOT = Path(__file__).parent / "snapshots" / "backlog_varied.md"


def _story(
    us_id: str,
    name: str,
    priority: str,
    points: int,
    *,
    requester: str | None = "Ana",
    at: str | None = "00:10:00",
    criteria: int = 1,
) -> UserStoryOut:
    return UserStoryOut(
        id=0,
        us_id=us_id,
        name=name,
        as_a="gerente de vendas",
        i_want=f"{name.lower()} no painel",
        so_that="eu acompanhe as metas",
        priority=priority,
        story_points=points,
        requested_by=None if requester is None else RequesterOut(id=1, name=requester),
        requested_at=at,
        acceptance_criteria=[
            CriterionOut(id=i, given=f"contexto {i}", when=f"ação {i}", then=f"resultado {i}")
            for i in range(1, criteria + 1)
        ],
    )


def _varied() -> list[EpicOut]:
    return [
        EpicOut(
            id=1,
            name="Painel",
            user_stories=[
                _story("US-01", "Ver metas", "High", 8, criteria=2),
                _story("US-02", "Filtrar período", "Low", 2, requester=None, at=None),
            ],
        ),
        EpicOut(
            id=2,
            name="Relatórios",
            user_stories=[
                _story("US-03", "Exportar vendas", "Medium", 13, requester="Bia", at="01:02:03"),
                _story("US-04", "Enviar por e-mail", "High", 3),
            ],
        ),
    ]


def test_varied_backlog_matches_snapshot() -> None:
    """Totais, agrupamento por Epic e por prioridade calculados do backlog."""
    text = export.render("md", "Planejamento Q4", "2026-10-30", _varied())

    assert text == SNAPSHOT.read_text(encoding="utf-8")


def test_empty_fields_are_omitted() -> None:
    """`backlog-review` 33: sem solicitante nem horário, as linhas somem."""
    text = export.render("md", "R", "2026-10-30", _varied())
    us02 = text.split("### US-02")[1].split("###")[0]

    assert "Solicitante" not in us02
    assert "Horário" not in us02


def test_special_characters_and_line_breaks_stay_valid() -> None:
    """Quebra de linha vira espaço; `|` e marcação escapados, tabela intacta."""
    story = _story("US-01", "Somar | dividir\n*tudo*", "High", 1).model_copy(
        update={"so_that": "que eu\r\nveja <b>totais</b>."}
    )
    text = export.render("md", "R", "2026-10-30", [EpicOut(id=1, name="A_b", user_stories=[story])])

    assert r"| US-01 | A\_b | Somar \| dividir \*tudo\* | Alta | 1 |" in text
    assert r"para que eu veja \<b\>totais\</b\>." in text


def test_redundant_connectors_are_not_repeated() -> None:
    """Conectivo já trazido pela LLM não se repete ("Dado que que", "para que que")."""
    story = _story("US-01", "X", "Low", 1).model_copy(
        update={
            "so_that": "Para que eu ganhe tempo",
            "acceptance_criteria": [
                CriterionOut(id=1, given="Dado que logado", when="Quando abre", then="Então vê.")
            ],
        }
    )
    text = export.render("md", "R", "2026-10-30", [EpicOut(id=1, name="A", user_stories=[story])])

    assert "para que eu ganhe tempo." in text
    assert "1. **Dado que** logado, **quando** abre, **então** vê." in text


def test_filename_uses_slug_and_date_only_for_markdown() -> None:
    """`05-api.md`; Q75."""
    assert export.filename("Evolutea", "md", "2026-10-30") == "backlog_evolutea_2026-10-30.md"
    assert export.filename("Evolutea", "json", "2026-10-30") == "evolutea-backlog.json"
