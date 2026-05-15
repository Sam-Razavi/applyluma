from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    file_url: str | None
    created_at: datetime
    updated_at: datetime


class CVPublic(CVSummary):
    """Returned in detail / upload responses — includes parsed text."""
    content: str | None


class CVUpdate(BaseModel):
    title: str | None = None


class CVVersionNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    is_tailored: bool
    created_at: datetime
    children: list[CVVersionNode] = Field(default_factory=list)


class CVDiffSection(BaseModel):
    name: str
    original: str
    tailored: str
    changes: int


class CVDiffResponse(BaseModel):
    cv_id: uuid.UUID
    sections: list[CVDiffSection]
