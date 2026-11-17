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


class LabelCount(BaseModel):
    label: str
    count: int


class StageReach(BaseModel):
    stage: str
    count: int
    # Share of submitted applications that got at least this far (0-1).
    rate: float


class SourcePerformance(BaseModel):
    source: str
    applications: int
    responses: int
    response_rate: float


class CvPerformance(BaseModel):
    cv_id: str | None
    title: str
    applications: int
    responses: int
    response_rate: float


class UpcomingItem(BaseModel):
    application_id: str
    company_name: str
    job_title: str
    kind: str  # "interview" | "deadline"
    date: str  # ISO 8601
    days_away: int


class ApplicationInsights(BaseModel):
    total: int
    submitted: int
    active: int
    closed: int
    wishlist: int
    applied_last_7d: int
    applied_prev_7d: int
    applied_last_30d: int
    interview_rate: float
    awaiting_reply: int
    awaiting_reply_days: int
    stage_reach: list[StageReach]
    work_modes: list[LabelCount]
    top_locations: list[LabelCount]
    top_companies: list[LabelCount]
    weekday_counts: list[LabelCount]
    source_performance: list[SourcePerformance]
    cv_performance: list[CvPerformance]
    upcoming: list[UpcomingItem]
    salary_median: int | None
    salary_min: int | None
    salary_max: int | None
    salary_sample: int
