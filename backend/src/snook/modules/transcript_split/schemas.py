from pydantic import BaseModel, ConfigDict, Field

# Cortes em `PUT /split`: 1 a 500 (05-api, "Tamanhos máximos"; SEC-09).
CUTS_MAX = 500


class SplitSegmentOut(BaseModel):
    """`tokens`: estimativa do segmento; o cliente soma para a Parte (ADR-0011)."""

    id: int
    start_seconds: float
    end_seconds: float
    participant: str
    text: str
    tokens: int


class SplitPartOut(BaseModel):
    index: int
    first_segment_id: int
    last_segment_id: int
    start_seconds: float
    end_seconds: float
    estimated_tokens: int
    fits: bool


class SplitOut(BaseModel):
    """Corpo de `GET /split` e `POST /split/refresh` (`transcript-split` 7, 10, 43, 44).

    `cuts`: `id` do último segmento de cada Parte, menos a última. Sem provedor ativo: só
    `message`, sem orçamento, segmentos nem cortes. `read_only`: `done` já dividida (11).
    """

    status: str
    split_reason: str | None
    can_cancel: bool
    read_only: bool
    message: str | None
    provider: str | None
    model: str | None
    budget: int | None
    total_tokens: int | None
    segments: list[SplitSegmentOut]
    cuts: list[int]
    parts: list[SplitPartOut]


class SplitCuts(BaseModel):
    """`PUT /split`: `{cuts: [segment_id, ...]}`, corte no fim de cada segmento citado."""

    model_config = ConfigDict(extra="forbid")

    cuts: list[int] = Field(min_length=1, max_length=CUTS_MAX)


class SplitStatusOut(BaseModel):
    status: str
