from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    date: str  # ISO date string "YYYY-MM-DD"
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
