"""Pydantic schemas for all analytics endpoints.

Sections:
  1. Legacy models  — used by /analytics/overview, /top-companies, etc.
  2. Phase 6 shared — AnalyticsResponse wrapper, metadata, errors, enums
  3. Phase 6 models — one model (or small group) per endpoint
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ── 1. Legacy models (Phase 1-5, backward-compatible) ────────────────────────


class AnalyticsOverview(BaseModel):
    total_jobs: int
    remote_percentage: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    top_skill: Optional[str] = None
    last_updated: Optional[datetime] = None


class CompanyStat(BaseModel):
    company: str
    job_count: int


class SkillStat(BaseModel):
    skill: str
    mention_count: int
    trend: str  # "up" | "down" | "stable"


class DailyJobCount(BaseModel):
    date: str  # YYYY-MM-DD
    job_count: int


class RecentJob(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    url: str
    remote_allowed: bool
    employment_type: Optional[str] = None
    extracted_skills: Optional[list[str]] = None
    scraped_at: datetime


# ── 2. Phase 6: Shared wrapper, metadata, errors ─────────────────────────────

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    timestamp: datetime
    data_freshness_hours: int = Field(
        description="Hours since analytics views were last refreshed by dbt"
    )
    sample_size: int = Field(description="Number of job postings included in this result")
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    next_update: Optional[datetime] = None


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code, e.g. INVALID_PARAMS")
    message: str = Field(description="Human-readable description of the error")
    details: Optional[dict[str, Any]] = None


class AnalyticsResponse(BaseModel, Generic[T]):
    """Standard envelope for every Phase 6 analytics response."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    data: Optional[T] = None
    metadata: Optional[ResponseMetadata] = None
    error: Optional[ErrorDetail] = None


# ── 3. Phase 6: Enums ─────────────────────────────────────────────────────────


class TrendDirection(str, Enum):
    up = "up"
    down = "down"
    stable = "stable"


class Granularity(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class ExperienceLevel(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    management = "management"


# ── 4. Endpoint 1: GET /trending-skills ──────────────────────────────────────


class SkillTrend(BaseModel):
    """One entry in the trending-skills response."""

    skill: str
    frequency: int = Field(description="Number of job postings mentioning this skill")
    frequency_pct: float = Field(description="Percentage of all jobs that mention this skill")
    avg_salary_min: Optional[int] = Field(None, description="Average advertised salary floor across jobs with this skill")
    avg_salary_max: Optional[int] = Field(None, description="Average advertised salary ceiling across jobs with this skill")
    trending_score_pct: float = Field(
        description="Week-over-week demand change in percent. Positive = growing demand."
    )
    trend: TrendDirection


# ── 5. Endpoint 2: GET /salary-insights ──────────────────────────────────────


class SalaryInsightItem(BaseModel):
    """Salary percentiles for one filter combination."""

    dimension_type: str = Field(
        description="What dimension was used (e.g. 'location', 'experience_level', 'overall')"
    )
    dimension_value: str = Field(description="The value of the dimension (e.g. 'London', 'senior')")
    p25_salary: Optional[int] = None
    p50_salary: Optional[int] = None
    p75_salary: Optional[int] = None
    p90_salary: Optional[int] = None
    avg_salary: Optional[int] = None
    min_salary_floor: Optional[int] = None
    max_salary_ceiling: Optional[int] = None
    job_count: int


# ── 6. Endpoint 3: GET /hiring-patterns ──────────────────────────────────────


class HiringPatternPoint(BaseModel):
    """One time-series point in the hiring-patterns response."""

    period: str = Field(
        description="Period label. Format: YYYY-MM-DD (daily), YYYY-WXX (weekly), YYYY-MM (monthly)"
    )
    job_count: int
    remote_count: int
    remote_percentage: float
    avg_salary: Optional[int] = None


# ── 7. Endpoint 4: GET /company-insights ─────────────────────────────────────


class CompanyInsight(BaseModel):
    company_name: str
    total_jobs: int
    remote_jobs: int
    remote_percentage: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    most_common_employment_type: Optional[str] = None
    first_seen_date: str = Field(description="YYYY-MM-DD")
    last_seen_date: str = Field(description="YYYY-MM-DD")
    hiring_velocity: float = Field(
        description="Average new job postings per week over the observable window"
    )


# ── 8. Endpoint 5: GET /job-market-health ────────────────────────────────────


class JobMarketHealth(BaseModel):
    total_jobs: int
    unique_companies: int
    remote_percentage: float
    avg_salary_midpoint: Optional[int] = None
    senior_role_pct: float
    junior_role_pct: float
    management_role_pct: float
    mid_role_pct: float
    avg_skills_per_job: float
    data_date_range_days: int = Field(
        description="Number of days covered by the underlying data"
    )
    last_updated: Optional[datetime] = None


# ── 9. Endpoint 6: GET /skill-demand ─────────────────────────────────────────


class SkillDemand(BaseModel):
    skill: str
    total_mentions: int
    mentions_this_week: int
    mentions_last_week: int
    trending_score_pct: float = Field(
        description="Week-over-week change percent. 100.0 means skill is new this week."
    )
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    trend: TrendDirection


# ── 10. Endpoint 7: GET /location-trends ─────────────────────────────────────


class LocationTrend(BaseModel):
    location: str
    job_count: int
    pct_of_total: float
    avg_salary_midpoint: Optional[int] = None
    remote_percentage: Optional[float] = None


# ── 11. Endpoint 8: GET /industry-breakdown ──────────────────────────────────


class IndustryBreakdown(BaseModel):
    """
    Industry is derived from normalised_title keywords since raw data has no
    explicit industry column.  See SPEC.md §8 for the CASE mapping.
    """

    industry: str
    job_count: int
    pct_of_total: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    remote_percentage: float


# ── 12. Endpoint 9: GET /experience-levels ───────────────────────────────────


class ExperienceLevelBreakdown(BaseModel):
    level: ExperienceLevel
    job_count: int
    pct_of_total: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    remote_percentage: float


# ── 13. Endpoint 10: GET /job-type-mix ───────────────────────────────────────


class JobTypeMixItem(BaseModel):
    job_type: str = Field(description="Employment type value from raw data (e.g. 'full_time', 'contract', 'unknown')")
    remote_label: str = Field(description="'remote', 'on-site', or 'hybrid/unknown'")
    job_count: int
    pct_of_total: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None


# ── 14. Endpoint 11: GET /salary-by-skill ────────────────────────────────────


class SalaryBySkill(BaseModel):
    skill: str
    avg_salary: Optional[int] = None
    p25_salary: Optional[int] = None
    p50_salary: Optional[int] = None
    p75_salary: Optional[int] = None
    p90_salary: Optional[int] = None
    min_salary_floor: Optional[int] = None
    max_salary_ceiling: Optional[int] = None
    job_count: int


# ── 15. Endpoint 12: GET /comparison ─────────────────────────────────────────


class SkillGap(BaseModel):
    skill: str
    in_resume: bool
    market_demand_rank: int = Field(description="Rank among all known skills by total job mentions (1 = most in-demand)")
    total_market_mentions: int
    trending_score_pct: float
    avg_salary_min: Optional[int] = None
    avg_salary_max: Optional[int] = None
    trend: TrendDirection


class ResumeComparison(BaseModel):
    resume_id: uuid.UUID
    resume_title: str
    resume_skill_count: int = Field(description="Number of skills extracted from the resume text")
    matched_skills: list[str] = Field(description="Skills present in both the resume and the market top-100")
    missing_high_demand_skills: list[str] = Field(
        description="Top-20 market skills that do not appear in the resume"
    )
    skill_details: list[SkillGap] = Field(
        description="Full detail for each skill extracted from the resume"
    )
    market_salary_benchmark: Optional[SalaryInsightItem] = Field(
        None,
        description="Overall salary percentiles for jobs matching the resume's top skills"
    )
    skills_market_coverage_pct: float = Field(
        description="Percentage of resume skills that appear in market data (0-100)"
    )
    overall_market_alignment_score: float = Field(
        description="Composite score 0-100: how well the resume matches current market demand"
    )
