import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.tailor_job import TailorIntensity, TailorStatus


class TailorSubmitRequest(BaseModel):
    cv_id: uuid.UUID
    job_description_id: uuid.UUID | None = None
    raw_job_posting_id: uuid.UUID | None = None
    intensity: TailorIntensity = TailorIntensity.medium

    @model_validator(mode="after")
    def validate_single_job_source(self) -> "TailorSubmitRequest":
        has_jd = self.job_description_id is not None
        has_raw_job = self.raw_job_posting_id is not None
        if has_jd == has_raw_job:
            raise ValueError("Set exactly one of job_description_id or raw_job_posting_id")
        return self


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
