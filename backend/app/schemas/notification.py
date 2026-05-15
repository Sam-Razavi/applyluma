import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    body: str
    related_id: uuid.UUID | None
    related_type: str | None
    is_read: bool
    created_at: datetime
    updated_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationPublic]
    total: int
    unread_count: int
    skip: int
    limit: int
