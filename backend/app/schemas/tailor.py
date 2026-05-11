import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.tailor_job import TailorIntensity, TailorStatus


class TailorSubmitRequest(BaseModel):
    cv_id: uuid.UUID
    job_description_id: uuid.UUID
    intensity: TailorIntensity = TailorIntensity.medium


class TailorJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cv_id: uuid.UUID
    job_description_id: uuid.UUID
    intensity: TailorIntensity
    status: TailorStatus
    language: str | None
    output_cv_id: uuid.UUID | None
    created_at: datetime


class TailorStatusResponse(BaseModel):
    id: uuid.UUID
    status: TailorStatus
    error_message: str | None
    language: str | None
    output_cv_id: uuid.UUID | None


class TailorSection(BaseModel):
    section_id: str
    section_name: str
    original: str
    tailored: str
    changes: list[str]


class TailorMeta(BaseModel):
    keywords_added: list[str] = []
    keywords_already_present: list[str] = []
    intensity_applied: str


class TailorPreviewResponse(BaseModel):
    job_id: uuid.UUID
    language: str
    sections: list[TailorSection]
    meta: TailorMeta


class TailorSaveRequest(BaseModel):
    accepted_section_ids: list[str] | None = None
    cv_title: str | None = None


class TailorSaveResponse(BaseModel):
    cv_id: uuid.UUID
    title: str
    file_url: str | None


class TailorUsageResponse(BaseModel):
    used_today: int
    daily_limit: int | None
    resets_at: datetime
