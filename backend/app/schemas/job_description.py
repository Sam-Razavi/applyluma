import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionCreate(BaseModel):
    company_name: str = Field(..., max_length=255)
    job_title: str = Field(..., max_length=255)
    description: str = Field(..., max_length=100_000)
    url: str | None = Field(default=None, max_length=2048)


class JobDescriptionSummary(BaseModel):
    """List view — excludes the full description text."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    source_raw_job_posting_id: uuid.UUID | None = None
    company_name: str
    job_title: str
    url: str | None
    keywords: list[str]
    starred: bool = False
    notes: str | None = None
    list_name: str | None = None
    created_at: datetime
    updated_at: datetime


class JobDescriptionPublic(JobDescriptionSummary):
    """Detail view — includes full description text."""
    description: str


class ExternalJobBookmarkResponse(JobDescriptionPublic):
    """What the browser extension gets back after saving a job.

    ``raw_job_posting_id`` repeats ``source_raw_job_posting_id`` under the name
    extension 1.0.0 reads: it uses it for the match score, "Track
    application" and AI Tailor, which all did nothing while it was missing.
    """

    raw_job_posting_id: uuid.UUID | None = None


class JobDescriptionUpdate(BaseModel):
    """Partial update for starred, notes, and list_name."""
    starred: bool | None = None
    notes: str | None = None
    list_name: str | None = None


class SaveFromRawJobRequest(BaseModel):
    """Save a raw job posting as a job description."""
    raw_job_posting_id: uuid.UUID
    list_name: str | None = None
    notes: str | None = None
