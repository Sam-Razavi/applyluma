from pydantic import BaseModel


class FunnelCount(BaseModel):
    status: str
    count: int


class WeeklyApplicationCount(BaseModel):
    week_start: str
    count: int


class SourceCount(BaseModel):
    source: str
    count: int


class SalaryBucketCount(BaseModel):
    bucket: str
    count: int


class ApplicationAnalytics(BaseModel):
    funnel: list[FunnelCount]
    response_rate: float
    offer_rate: float
    average_response_days: float | None
    weekly_counts: list[WeeklyApplicationCount]
    top_sources: list[SourceCount]
    salary_distribution: list[SalaryBucketCount]
