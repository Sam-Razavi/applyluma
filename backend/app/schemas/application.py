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


class DuplicateApplicationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    job_title: str
    status: str
    created_at: datetime


class DuplicateCheckResponse(BaseModel):
    duplicate: bool
    application: DuplicateApplicationInfo | None = None


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
    name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)


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
    company_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    job_url: str | None = Field(default=None, max_length=2048)
    status: ApplicationStatus = "wishlist"
    applied_date: datetime | None = None
    interview_date: datetime | None = None
    deadline: datetime | None = None
    source: str | None = Field(default=None, max_length=100)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=50)
    priority: int = Field(default=1, ge=1, le=3)
    notes: str | None = Field(default=None, max_length=10000)


class ApplicationUpdate(BaseModel):
    job_description_id: uuid.UUID | None = None
    raw_job_posting_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None = None
    company_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    job_url: str | None = Field(default=None, max_length=2048)
    status: ApplicationStatus | None = None
    applied_date: datetime | None = None
    interview_date: datetime | None = None
    deadline: datetime | None = None
    source: str | None = Field(default=None, max_length=100)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=50)
    priority: int | None = Field(default=None, ge=1, le=3)
    notes: str | None = Field(default=None, max_length=10000)


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
    interview_date: datetime | None
    deadline: datetime | None
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
