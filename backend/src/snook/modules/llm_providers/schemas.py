from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

API_KEY_MAX = 500
BASE_URL_MAX = 2048
MODEL_MAX = 200
CONTEXT_WINDOW_MAX = 10_000_000


class ConfigDraft(BaseModel):
    """Corpo do teste e do salvar. Campo ausente ou vazio: valor salvo, senão o padrão."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(None, max_length=API_KEY_MAX)
    base_url: str | None = Field(None, max_length=BASE_URL_MAX)
    model: str | None = Field(None, max_length=MODEL_MAX)
    # `strict`: "8192", 8192.0 e true não passam como inteiro (`llm-providers` 15).
    context_window: int | None = Field(None, ge=1, le=CONTEXT_WINDOW_MAX, strict=True)

    @field_validator("api_key", "base_url", "model")
    @classmethod
    def _blank_is_absent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ConfigOut(BaseModel):
    provider: str
    state: Literal["not_configured", "configured", "active"]
    model: str | None
    context_window: int | None
    key_mask: str | None
    base_url: str | None
    key_status: str | None
    default_model: str
    default_context_window: int


class ModelList(BaseModel):
    ok: bool
    models: list[str] = []
    reason: str | None = None
    message: str | None = None


class ConnectionResult(BaseModel):
    ok: bool
    reason: str | None = None
    message: str | None = None
