from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints
from pydantic_core import PydanticCustomError

from snook.core.errors import FIELD_MESSAGE_ERROR
from snook.modules.participants import messages
from snook.modules.participants.models import NAME_MAX

# Mesmo formato do rótulo no caminho da amostra (SEC-09).
SpeakerLabelKey = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{1,32}$")]


def _check_name(value: str) -> str:
    """Aparado; vazio ou só espaços e acima de 100 caracteres: 422 (`participants` 8)."""
    value = value.strip()
    if not value:
        raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.NAME_REQUIRED)
    if len(value) > NAME_MAX:
        raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.NAME_TOO_LONG)
    return value


ParticipantName = Annotated[str, AfterValidator(_check_name)]


class SpeakerOut(BaseModel):
    speaker_label: str
    total_seconds: float


class ParticipantNames(BaseModel):
    """`PUT /participants`: `{names: {SPEAKER_00: "Ana", ...}}`, na ordem informada."""

    model_config = ConfigDict(extra="forbid")

    names: dict[SpeakerLabelKey, ParticipantName]


class ParticipantOut(BaseModel):
    id: int
    name: str
    speaker_labels: list[str]
