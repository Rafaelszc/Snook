from pydantic import BaseModel


class SegmentOut(BaseModel):
    id: int
    speaker_label: str
    start_seconds: float
    end_seconds: float
    text: str


class TranscriptOut(BaseModel):
    segments: list[SegmentOut]
