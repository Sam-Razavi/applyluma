import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "wishlist",
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
]


class ApplicationEventCreate(BaseModel):
    event_type: str
    old_value: str | None = None
    new_value: str | None = None
    description: str | None = None
    event_date: datetime | None = None


class ApplicationEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    old_value: str | None
    new_value: str | None
    description: str | None
    event_date: datetime
    created_at: datetime


class ApplicationContactCreate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None


class ApplicationContactPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    name: str | None
    role: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    notes: str | None
    created_at: datetime


class ApplicationCreate(BaseModel):
    job_description_id: uuid.UUID | None = None
    raw_job_posting_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None = None
    company_name: str | None = None
    job_title: str | None = None
    job_url: str | None = None
    status: ApplicationStatus = "wishlist"
    applied_date: datetime | None = None
    source: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    location: str | None = None
    remote_type: str | None = None
    priority: int = Field(default=1, ge=1, le=3)
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    job_description_id: uuid.UUID | None = None
    raw_job_posting_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None = None
    company_name: str | None = None
    job_title: str | None = None
    job_url: str | None = None
    status: ApplicationStatus | None = None
    applied_date: datetime | None = None
    source: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    location: str | None = None
    remote_type: str | None = None
    priority: int | None = Field(default=None, ge=1, le=3)
    notes: str | None = None


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_description_id: uuid.UUID | None
    raw_job_posting_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None
    company_name: str
    job_title: str
    job_url: str | None
    status: str
    applied_date: datetime | None
    source: str | None
    salary_min: int | None
    salary_max: int | None
    location: str | None
    remote_type: str | None
    priority: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationPublic(ApplicationSummary):
    events: list[ApplicationEventPublic] = Field(default_factory=list)
    contacts: list[ApplicationContactPublic] = Field(default_factory=list)
