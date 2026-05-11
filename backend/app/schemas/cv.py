import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CVSummary(BaseModel):
    """Returned in list responses — omits the large content field."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    filename: str
    is_default: bool
    is_tailored: bool
    parent_cv_id: uuid.UUID | None
    tailor_job_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CVPublic(CVSummary):
    """Returned in detail / upload responses — includes parsed text."""
    content: str | None
    file_url: str | None


class CVUpdate(BaseModel):
    title: str | None = None
