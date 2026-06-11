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
    created_at: datetime
    updated_at: datetime


class JobDescriptionPublic(JobDescriptionSummary):
    """Detail view — includes full description text."""
    description: str
