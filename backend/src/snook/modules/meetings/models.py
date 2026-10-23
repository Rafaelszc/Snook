from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base

STATUSES = ("pending", "processing", "transcribed", "needs_split", "generating", "done", "failed")
STATUS_PENDING = "pending"
STATUS_FAILED = "failed"
FAILED_STAGES = ("transcription", "generation")
FILE_EXTENSIONS = ("mp3", "wav", "m4a", "ogg", "webm", "mp4")


class Meeting(Base):
    """Reunião. Caminho do arquivo não é coluna: deriva de `id` e `file_ext` (04-data-model)."""

    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'transcribed', 'needs_split', "
            "'generating', 'done', 'failed')",
            name="ck_meetings_status",
        ),
        CheckConstraint(
            "file_ext IN ('mp3', 'wav', 'm4a', 'ogg', 'webm', 'mp4')", name="ck_meetings_file_ext"
        ),
        CheckConstraint(
            "failed_stage IS NULL OR failed_stage IN ('transcription', 'generation')",
            name="ck_meetings_failed_stage",
        ),
        CheckConstraint(
            "status != 'failed' OR (failed_stage IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_meetings_failed_fields",
        ),
        CheckConstraint(
            "split_reason IS NULL OR split_reason IN ('too_long', 'adjust')",
            name="ck_meetings_split_reason",
        ),
        CheckConstraint(
            "expected_speakers IS NULL OR expected_speakers BETWEEN 1 AND 20",
            name="ck_meetings_expected_speakers",
        ),
        CheckConstraint(
            "duration_seconds > 0 AND duration_seconds <= 7200", name="ck_meetings_duration"
        ),
        CheckConstraint("size_bytes <= 524288000", name="ck_meetings_size"),
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_meetings_title"),
        Index("ix_meetings_user_created", "user_id", "created_at"),
        Index("ix_meetings_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_ext: Mapped[str] = mapped_column(String)
    duration_seconds: Mapped[float] = mapped_column(Float)
    size_bytes: Mapped[int]
    expected_speakers: Mapped[int | None]
    status: Mapped[str] = mapped_column(String)
    failed_stage: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(String)
    split_reason: Mapped[str | None] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String)
    participants_confirmed_at: Mapped[str | None] = mapped_column(String)
    backlog_saved_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
