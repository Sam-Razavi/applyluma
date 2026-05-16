from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RawJobPostingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    title: str
    company: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    remote_allowed: bool
    url: str
    scraped_at: datetime


class RawJobPostingPublic(RawJobPostingSummary):
    description: str
    extracted_skills: dict | None
    is_duplicate: bool
    created_at: datetime


class ExtractedKeywordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_job_posting_id: uuid.UUID
    keyword: str
    keyword_type: str
    confidence_score: float
    frequency: int
    created_at: datetime


class JobMatchingScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    raw_job_posting_id: uuid.UUID
    overall_score: float
    skills_match: float | None
    experience_match: float | None
    salary_match: float | None
    education_match: float | None
    location_match: float | None
    explanation: str | None
    computed_at: datetime
    cached_at: datetime


class SavedJobSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    raw_job_posting_id: uuid.UUID
    list_name: str | None
    notes: str | None
    starred: bool
    created_at: datetime
    updated_at: datetime
    job: RawJobPostingSummary | None = None


class JobWithScoreSchema(BaseModel):
    """Combined job + match score for list/detail endpoints."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    title: str
    company: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    remote_allowed: bool
    url: str
    source: str
    scraped_at: datetime
    match_score: float | None = None
    skills_match: float | None = None
    experience_match: float | None = None
    salary_match_score: float | None = None
    education_match: float | None = None
    location_match: float | None = None
    explanation: str | None = None
    keywords: list[ExtractedKeywordSchema] = Field(default_factory=list)
    is_saved: bool = False
    application_status: str | None = None
    application_id: uuid.UUID | None = None


class JobDetailSchema(JobWithScoreSchema):
    description: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class SaveJobRequest(BaseModel):
    job_id: uuid.UUID
    list_name: str | None = "Saved"
    notes: str | None = None


class UpdateSavedJobRequest(BaseModel):
    list_name: str | None = None
    notes: str | None = None
    starred: bool | None = None


class KeywordsByTypeSchema(BaseModel):
    technical_skills: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
