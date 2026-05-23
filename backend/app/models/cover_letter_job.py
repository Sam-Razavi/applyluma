import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if False:  # TYPE_CHECKING
    from app.models.job_description import JobDescription
    from app.models.user import User


class CoverLetterTone(enum.StrEnum):
    formal = "formal"
    friendly = "friendly"
    concise = "concise"


class CoverLetterStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class CoverLetterJob(Base, TimestampMixin):
    __tablename__ = "cover_letter_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="CASCADE")
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="CASCADE")
    )
    tone: Mapped[CoverLetterTone] = mapped_column(
        Enum(CoverLetterTone, name="cover_letter_tone"),
        default=CoverLetterTone.formal,
        server_default="formal",
    )
    status: Mapped[CoverLetterStatus] = mapped_column(
        Enum(CoverLetterStatus, name="cover_letter_status"),
        default=CoverLetterStatus.pending,
        server_default="pending",
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    saved_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped["User"] = relationship("User", back_populates="cover_letter_jobs")
    job_description: Mapped["JobDescription"] = relationship("JobDescription")
