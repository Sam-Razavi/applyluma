"""One AI-assisted job-fit assessment (thesis component; thesis/DESIGN.md)."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"


class FitAssessment(Base, TimestampMixin):
    __tablename__ = "fit_assessments"
    __table_args__ = (
        Index("ix_fit_assessments_user_posting", "user_id", "raw_job_posting_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    # SET NULL, not CASCADE or RESTRICT: the retention task deletes old
    # postings, and an assessment must neither block that nor vanish with it.
    # The title and company are copied so the row still says what it was about.
    raw_job_posting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_job_postings.id", ondelete="SET NULL"), nullable=True
    )
    job_title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, server_default=STATUS_PENDING)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set by the decision rules; model_recommendation is the model's own
    # suggestion, kept only so the two can be compared.
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    limited_information: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # What produced the result. input_hash covers the CV text, the ad text and
    # the three versions below, so an unchanged request can reuse the row.
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(16))
    rules_version: Mapped[str] = mapped_column(String(16))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
