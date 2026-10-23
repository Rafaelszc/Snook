from pydantic import BaseModel

# Saídas nunca trazem caminho do arquivo nem `file_ext` (`meetings` 21; 03-security, "Never").


class MeetingOut(BaseModel):
    id: str
    title: str
    original_filename: str
    duration_seconds: float
    expected_speakers: int | None
    status: str
    created_at: str
