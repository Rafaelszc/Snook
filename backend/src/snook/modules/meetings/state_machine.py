from snook.modules.meetings.models import (
    FAILED_STAGES,
    SPLIT_REASONS,
    STATUS_FAILED,
    STATUSES,
    Meeting,
)

# Tabela de transições de `01-prd/meetings.md`, "Contrato com outros módulos" (`meetings` 23).
# Saída de `failed` depende da etapa; `failed` exige a etapa da origem.
TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"processing"}),
    "processing": frozenset({"transcribed", STATUS_FAILED}),
    "transcribed": frozenset({"generating", "needs_split", STATUS_FAILED}),
    "needs_split": frozenset({"generating", "done", STATUS_FAILED}),
    "generating": frozenset({"done", STATUS_FAILED}),
    "done": frozenset({"generating", "needs_split", STATUS_FAILED}),
    STATUS_FAILED: frozenset({"pending", "transcribed"}),
}
RETRY_TARGET = {"transcription": "pending", "generation": "transcribed"}
_FAILED_STAGE_BY_SOURCE = {"processing": "transcription"}

# Transição que inicia trabalho novo troca o `run_id` (ADR-0007).
_NEW_RUN = {("failed", "pending"), ("failed", "transcribed")}
_NEW_RUN_TARGET = "generating"


class InvalidStatusUpdate(ValueError):
    """Status fora da lista, transição fora da tabela ou `failed` incompleto. Nada é gravado."""


def check(
    meeting: Meeting,
    target: str,
    failed_stage: str | None,
    message: str | None,
    split_reason: str | None = None,
) -> None:
    source = meeting.status
    if target not in STATUSES:
        raise InvalidStatusUpdate(f"status desconhecido: {target!r}")
    if target not in TRANSITIONS[source]:
        raise InvalidStatusUpdate(f"transição recusada: {source} -> {target}")
    if source == STATUS_FAILED and RETRY_TARGET.get(meeting.failed_stage or "") != target:
        raise InvalidStatusUpdate(f"saída de failed/{meeting.failed_stage} recusada: {target}")
    if source == "needs_split" and target == "done" and meeting.backlog_saved_at is None:
        raise InvalidStatusUpdate("needs_split -> done exige backlog gravado")
    if target == STATUS_FAILED:
        expected = _FAILED_STAGE_BY_SOURCE.get(source, "generation")
        if failed_stage not in FAILED_STAGES or failed_stage != expected:
            raise InvalidStatusUpdate(f"etapa recusada para {source}: {failed_stage!r}")
        if not (message or "").strip():
            raise InvalidStatusUpdate("failed exige mensagem")
    elif failed_stage is not None or message is not None:
        raise InvalidStatusUpdate("etapa e mensagem só valem para failed")
    if split_reason is not None and (target != "needs_split" or split_reason not in SPLIT_REASONS):
        raise InvalidStatusUpdate(f"split_reason recusado para {target}: {split_reason!r}")


def starts_new_run(source: str, target: str) -> bool:
    return target == _NEW_RUN_TARGET or (source, target) in _NEW_RUN
