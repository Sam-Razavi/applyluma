import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.cover_letter_job import CoverLetterStatus, CoverLetterTone


class CoverLetterSubmitRequest(BaseModel):
    cv_id: uuid.UUID
    job_description_id: uuid.UUID | None = None
    raw_job_posting_id: str | None = None
    tone: CoverLetterTone = CoverLetterTone.formal


class CoverLetterJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cv_id: uuid.UUID
    job_description_id: uuid.UUID
    tone: CoverLetterTone
    status: CoverLetterStatus
    language: str | None
    word_count: int | None
    title: str | None
    is_saved: bool
    created_at: datetime


class CoverLetterStatusResponse(BaseModel):
    id: uuid.UUID
    status: CoverLetterStatus
    error_message: str | None


class CoverLetterPreviewResponse(BaseModel):
    id: uuid.UUID
    generated_text: str
    language: str
    word_count: int | None
    tone: CoverLetterTone


class CoverLetterSaveRequest(BaseModel):
    saved_text: str = Field(..., max_length=50_000)
    title: str | None = Field(default=None, max_length=255)


class CoverLetterUsageResponse(BaseModel):
    used_today: int
    daily_limit: int | None
    resets_at: datetime
