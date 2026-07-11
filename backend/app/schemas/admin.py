from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole

# All notification types produced by the application. Restricting admin sends
# to this set prevents unknown types from reaching the notification store.
NotificationType = Literal[
    "admin_message",
    "deadline_reminder",
    "application_stale",
    "weekly_summary",
    "high_match_alert",
    "tailor_complete",
    "cover_letter_complete",
    "interview_reminder",
    "upgrade_success",
]


class AdminOverviewStats(BaseModel):
    total_users: int
    premium_users: int
    admin_users: int
    new_users_this_week: int
    total_cvs: int
    total_job_descriptions: int
    total_applications: int
    total_tailor_jobs: int
    tailor_jobs_complete: int
    tailor_jobs_failed: int
    tailor_jobs_pending: int
    total_cover_letters: int


class AdminUserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    subscription_status: str | None
    created_at: datetime
    last_login_at: datetime | None = None
    login_count: int = 0


class AdminUserActivitySummary(BaseModel):
    cvs: int
    tailored_cvs: int
    job_descriptions: int
    applications: int
    saved_jobs: int
    tailor_jobs: int
    tailor_jobs_failed: int
    cover_letters: int
    cover_letters_failed: int
    notifications: int
    unread_notifications: int


class AdminUserAiCosts(BaseModel):
    last_30_days_usd: float
    all_time_usd: float
    all_time_calls: int


class AdminUserProfile(AdminUserRow):
    auth_provider: str | None = None
    avatar_url: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    subscription_ends_at: datetime | None = None
    updated_at: datetime
    daily_tailor_limit_override: int | None = None
    activity: AdminUserActivitySummary
    ai_costs: AdminUserAiCosts


class AdminActivityEvent(BaseModel):
    type: str
    title: str
    status: str | None = None
    timestamp: datetime
    ref_id: uuid.UUID | None = None


class AdminUserActivityResponse(BaseModel):
    items: list[AdminActivityEvent]
    total: int
    page: int
    size: int


class AdminLimitsUpdateRequest(BaseModel):
    # None = role default; 0 = blocked; N = that many tailor runs per day.
    daily_tailor_limit_override: int | None = Field(default=None, ge=0, le=1000)


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRow]
    total: int
    page: int
    size: int


class AdminRoleUpdateRequest(BaseModel):
    role: UserRole


class AdminActiveUpdateRequest(BaseModel):
    is_active: bool


class AdminNotifyRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)
    type: NotificationType = "admin_message"


class AdminBulkNotifyRequest(AdminNotifyRequest):
    audience: Literal["all", "role", "user"] = "all"
    role: UserRole | None = None
    user_id: uuid.UUID | None = None


class AdminBulkNotifyResponse(BaseModel):
    sent_count: int


class PipelineStage(BaseModel):
    name: str
    count: int
    last_run: datetime | None = None
    healthy: bool
    status: str = "unknown"


class SourceHealth(BaseModel):
    source: str
    count: int
    last_run: datetime | None = None
    healthy: bool
    status: str = "unknown"


class PipelineHealthResponse(BaseModel):
    raw_job_postings: PipelineStage
    extracted_keywords: PipelineStage
    job_market_metrics: PipelineStage
    sources: list[SourceHealth] = Field(default_factory=list)


class JobsOverTimePoint(BaseModel):
    date: str
    count: int


class JobsBySourceItem(BaseModel):
    source: str
    count: int


class TopSkillItem(BaseModel):
    skill: str
    count: int


class TopCompanyItem(BaseModel):
    company: str
    count: int


class PipelineMetricsResponse(BaseModel):
    metric_date: date | None = None
    total_jobs_scraped: int | None = None
    remote_percentage: float | None = None
    top_skills: list[TopSkillItem] = Field(default_factory=list)
    top_companies: list[TopCompanyItem] = Field(default_factory=list)


class AdminAiJobRow(BaseModel):
    id: uuid.UUID
    kind: Literal["tailor", "cover_letter"]
    user_id: uuid.UUID
    user_email: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    celery_task_id: str | None = None
    error_message: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    language: str | None = None
    intensity: str | None = None
    tone: str | None = None
    word_count: int | None = None


class AdminAiJobListResponse(BaseModel):
    items: list[AdminAiJobRow]
    total: int
    page: int
    size: int


class PipelineRunLogRow(BaseModel):
    id: int
    pipeline_name: str
    ran_at: datetime
    rows_affected: int
    status: str
    error_message: str | None = None


class PipelineRunLogListResponse(BaseModel):
    items: list[PipelineRunLogRow]
    total: int
    page: int
    size: int


class RawJobAdminRow(BaseModel):
    id: uuid.UUID
    source: str
    job_id_external: str
    title: str
    company: str
    location: str | None = None
    url: str
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str | None = None
    remote_allowed: bool
    is_remote: bool
    is_duplicate: bool
    application_deadline: datetime | None = None
    scraped_at: datetime
    keyword_count: int
    saved_count: int
    matching_score_count: int


class RawJobAdminDetail(RawJobAdminRow):
    description: str
    extracted_skills: dict[str, Any] | None = None
    raw_data: dict[str, Any]
    keywords: list[TopSkillItem] = Field(default_factory=list)


class RawJobAdminListResponse(BaseModel):
    items: list[RawJobAdminRow]
    total: int
    page: int
    size: int


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, dict[str, Any]]


class AdminAuditLogRow(BaseModel):
    id: uuid.UUID
    admin_user_id: uuid.UUID | None = None
    admin_email: str | None = None
    target_user_id: uuid.UUID | None = None
    target_email: str | None = None
    action: str
    details: dict[str, Any]
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogRow]
    total: int
    page: int
    size: int


class AdminNotificationRow(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class AdminNotificationListResponse(BaseModel):
    items: list[AdminNotificationRow]
    total: int
    page: int
    size: int


class AdminBillingSummary(BaseModel):
    total_users: int
    premium_users: int
    active_subscriptions: int
    canceled_subscriptions: int
    past_due_subscriptions: int


class AdminBillingUserRow(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    role: UserRole
    subscription_status: str | None = None
    subscription_ends_at: datetime | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    created_at: datetime


class AdminBillingUserListResponse(BaseModel):
    items: list[AdminBillingUserRow]
    total: int
    page: int
    size: int
    summary: AdminBillingSummary


ContactSubmissionStatus = Literal["new", "read", "replied", "archived"]


class ContactSubmissionRow(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    name: str
    email: str
    subject: str
    message: str
    category: str = "contact"
    source: str = "contact"
    status: str
    remote_ip: str | None = None
    user_agent: str | None = None
    created_at: datetime
    updated_at: datetime


class ContactSubmissionListResponse(BaseModel):
    items: list[ContactSubmissionRow]
    total: int
    page: int
    size: int


class ContactSubmissionStatusUpdate(BaseModel):
    status: ContactSubmissionStatus


class AiCostWindow(BaseModel):
    cost_usd: float
    calls: int
    tokens: int


class AiBudgetInfo(BaseModel):
    monthly_usd: float | None = None
    month_to_date_usd: float
    pct_used: float | None = None


class AiCostsSummary(BaseModel):
    today: AiCostWindow
    last_7_days: AiCostWindow
    last_30_days: AiCostWindow
    all_time: AiCostWindow
    budget: AiBudgetInfo


class AiCostsDailyPoint(BaseModel):
    date: str
    cost_usd: float
    calls: int


class AiCostsBreakdownItem(BaseModel):
    key: str
    cost_usd: float
    calls: int
    tokens: int


class AiCostsUserItem(BaseModel):
    user_id: uuid.UUID | None = None
    email: str | None = None
    cost_usd: float
    calls: int


class AiCostsBreakdown(BaseModel):
    by_purpose: list[AiCostsBreakdownItem]
    by_model: list[AiCostsBreakdownItem]
    top_users: list[AiCostsUserItem]


class AiBudgetUpdate(BaseModel):
    monthly_usd: float | None = Field(default=None, ge=0)


class AdminTableStat(BaseModel):
    table_name: str
    approx_row_count: int
    total_bytes: int
    rows_7d: int | None = None
    rows_30d: int | None = None


class AdminDatabaseStatsResponse(BaseModel):
    database_size_bytes: int
    tables: list[AdminTableStat]
    generated_at: datetime
