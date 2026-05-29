from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class AdminOverviewStats(BaseModel):
    total_users: int
    premium_users: int
    admin_users: int
    new_users_this_week: int
    total_cvs: int
    total_job_descriptions: int
    total_applications: int
    total_tailor_jobs: int
    tailor_jobs_complete: int
    tailor_jobs_failed: int
    tailor_jobs_pending: int
    total_cover_letters: int


class AdminUserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    subscription_status: str | None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRow]
    total: int
    page: int
    size: int


class AdminRoleUpdateRequest(BaseModel):
    role: UserRole


class AdminActiveUpdateRequest(BaseModel):
    is_active: bool


class AdminNotifyRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    type: str = "admin_message"
