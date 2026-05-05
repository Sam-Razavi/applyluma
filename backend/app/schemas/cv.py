import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CVCreate(BaseModel):
    title: str
    content: str | None = None
    file_url: str | None = None
    is_default: bool = False


class CVUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    file_url: str | None = None
    is_default: bool | None = None


class CVPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    content: str | None
    file_url: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime
