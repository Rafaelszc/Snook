from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from snook.core.errors import FIELD_MESSAGE_ERROR
from snook.modules.meetings import messages

# Saídas nunca trazem caminho do arquivo nem `file_ext` (`meetings` 21; 03-security, "Never").

TITLE_MAX = 200


class MeetingOut(BaseModel):
    id: str
    title: str
    original_filename: str
    duration_seconds: float
    expected_speakers: int | None
    status: str
    created_at: str


class MeetingSummary(BaseModel):
    """Item da listagem (`meetings` 19)."""

    id: str
    title: str
    created_at: str
    duration_seconds: float
    status: str


class MeetingDetail(MeetingSummary):
    """Detalhe (`meetings` 20). `failed_stage` e `error_message` só preenchidos em `failed`."""

    original_filename: str
    expected_speakers: int | None
    participants_confirmed: bool
    has_backlog: bool
    failed_stage: str | None
    error_message: str | None
    split_reason: str | None


class TitleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.TITLE_REQUIRED)
        if len(value) > TITLE_MAX:
            raise PydanticCustomError(FIELD_MESSAGE_ERROR, messages.TITLE_TOO_LONG)
        return value
