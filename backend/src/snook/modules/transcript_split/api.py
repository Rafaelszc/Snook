from typing import Annotated

from fastapi import APIRouter, Depends, Request

from snook.core.clock import Clock
from snook.core.deps import get_clock, get_uow
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.transcript_split import service
from snook.modules.transcript_split.schemas import SplitCuts, SplitOut, SplitStatusOut

router = APIRouter(prefix="/api/meetings")


def get_estimate(request: Request) -> service.Estimate:
    """ "Estimar tokens" de `llm-providers`; teste troca por fake em `app.state`."""
    estimate: service.Estimate = request.app.state.estimate_tokens
    return estimate


Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentClock = Annotated[Clock, Depends(get_clock)]
CurrentEstimate = Annotated[service.Estimate, Depends(get_estimate)]


@router.get("/{meeting_id}/split")
def read_split(meeting_id: str, user: CurrentUser, uow: Uow, estimate: CurrentEstimate) -> SplitOut:
    """`transcript-split` 7, 10, 11, 43, 44. Só lê (ADR-0019)."""
    with uow:
        return service.read_split(uow, user_id=user.id, meeting_id=meeting_id, estimate=estimate)


@router.post("/{meeting_id}/split/refresh")
def refresh_split(
    meeting_id: str, user: CurrentUser, uow: Uow, clock: CurrentClock, estimate: CurrentEstimate
) -> SplitOut:
    """`transcript-split` 11, 43, 44. "Partes prontas" sai depois do commit."""
    with uow:
        return service.refresh_split(
            uow, user_id=user.id, meeting_id=meeting_id, now=clock.now(), estimate=estimate
        )


@router.put("/{meeting_id}/split", status_code=202)
def confirm_split(
    meeting_id: str,
    body: SplitCuts,
    user: CurrentUser,
    uow: Uow,
    clock: CurrentClock,
    estimate: CurrentEstimate,
) -> SplitStatusOut:
    """`transcript-split` 12 a 17, 41 a 43."""
    with uow:
        status = service.confirm_split(
            uow,
            user_id=user.id,
            meeting_id=meeting_id,
            cuts=body.cuts,
            now=clock.now(),
            estimate=estimate,
        )
    return SplitStatusOut(status=status)


@router.post("/{meeting_id}/split/cancel")
def cancel_split(
    meeting_id: str, user: CurrentUser, uow: Uow, clock: CurrentClock
) -> SplitStatusOut:
    """`transcript-split` 39, 40."""
    with uow:
        status = service.cancel_split(uow, user_id=user.id, meeting_id=meeting_id, now=clock.now())
    return SplitStatusOut(status=status)
