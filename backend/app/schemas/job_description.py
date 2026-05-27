import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobDescriptionCreate(BaseModel):
    company_name: str
    job_title: str
    description: str
    url: str | None = None


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
