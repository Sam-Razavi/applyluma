import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobDescriptionCreate(BaseModel):
    company_name: str
    job_title: str
    description: str
    url: str | None = None


class JobDescriptionUpdate(BaseModel):
    company_name: str | None = None
    job_title: str | None = None
    description: str | None = None
    url: str | None = None


class JobDescriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    job_title: str
    description: str
    url: str | None
    created_at: datetime
    updated_at: datetime
