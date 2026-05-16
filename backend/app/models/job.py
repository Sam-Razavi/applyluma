import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RawJobPosting(Base):
    """Maps to the raw_job_postings table created in migration a1b2c3d4e5f6."""

    __tablename__ = "raw_job_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id_external: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    saved_by: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="job", cascade="all, delete-orphan"
    )
    keywords: Mapped[list["ExtractedKeyword"]] = relationship(
        "ExtractedKeyword", back_populates="job", cascade="all, delete-orphan"
    )
    matching_scores: Mapped[list["JobMatchingScore"]] = relationship(
        "JobMatchingScore", back_populates="job", cascade="all, delete-orphan"
    )


class SavedJob(Base, TimestampMixin):
    __tablename__ = "saved_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    list_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="saved_jobs")
    job: Mapped["RawJobPosting"] = relationship("RawJobPosting", back_populates="saved_by")


class ExtractedKeyword(Base):
    __tablename__ = "extracted_keywords"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    keyword_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped["RawJobPosting"] = relationship("RawJobPosting", back_populates="keywords")


class JobMatchingScore(Base):
    __tablename__ = "job_matching_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_job_postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skills_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="matching_scores")
    job: Mapped["RawJobPosting"] = relationship("RawJobPosting", back_populates="matching_scores")
