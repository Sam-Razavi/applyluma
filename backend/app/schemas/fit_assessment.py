import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FitAssessmentRequest(BaseModel):
    raw_job_posting_id: uuid.UUID
    # Run again even when an assessment of the same CV and ad exists.
    force: bool = False


class FitAssessmentStatus(BaseModel):
    enabled: bool
    daily_limit: int | None = None
    used_today: int = 0


class FitAssessmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_job_posting_id: uuid.UUID | None
    job_title: str
    company: str
    status: str
    error_message: str | None
    recommendation: str | None
    limited_information: bool | None
    # The full result: rule, reason, summary, requirements with quotes,
    # missing information and quote statistics. None until complete.
    result: dict[str, Any] | None = None
    model: str
    prompt_version: str
    rules_version: str
    created_at: datetime
