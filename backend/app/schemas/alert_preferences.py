import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertFrequency = Literal["daily", "weekly"]


class AlertPreferencesPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    enabled: bool
    score_threshold: int
    frequency: str
    last_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AlertPreferencesUpdate(BaseModel):
    enabled: bool | None = None
    score_threshold: int | None = Field(default=None, ge=60, le=95)
    frequency: AlertFrequency | None = None
