import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.cv import CV
    from app.models.job_description import JobDescription
    from app.models.user import User


class TailorStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class TailorIntensity(enum.StrEnum):
    light = "light"
    medium = "medium"
    aggressive = "aggressive"


class TailorJob(Base, TimestampMixin):
    __tablename__ = "tailor_jobs"

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
    intensity: Mapped[TailorIntensity] = mapped_column(
        Enum(TailorIntensity, name="tailor_intensity"),
        default=TailorIntensity.medium,
        server_default="medium",
    )
    status: Mapped[TailorStatus] = mapped_column(
        Enum(TailorStatus, name="tailor_status"),
        default=TailorStatus.pending,
        server_default="pending",
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    output_cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="tailor_jobs")
    cv: Mapped["CV"] = relationship("CV", foreign_keys=[cv_id])
    job_description: Mapped["JobDescription"] = relationship("JobDescription")
    output_cv: Mapped["CV | None"] = relationship("CV", foreign_keys=[output_cv_id])
