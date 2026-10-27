from pydantic import BaseModel


class SpeakerOut(BaseModel):
    speaker_label: str
    total_seconds: float
