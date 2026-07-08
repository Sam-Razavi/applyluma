from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.health import _check_adzuna, _check_celery, _check_db, _check_redis
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, get_redis_client
from app.crud import admin as crud_admin
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminActiveUpdateRequest,
    AdminAiJobListResponse,
    AdminAiJobRow,
    AdminAuditLogListResponse,
    AdminAuditLogRow,
    AdminBillingSummary,
    AdminBillingUserListResponse,
    AdminBillingUserRow,
    AdminBulkNotifyRequest,
    AdminBulkNotifyResponse,
    AdminNotificationListResponse,
    AdminNotificationRow,
    AdminNotifyRequest,
    AdminOverviewStats,
    AdminRoleUpdateRequest,
    AdminUserListResponse,
    AdminUserProfile,
    AdminUserRow,
    ContactSubmissionListResponse,
    ContactSubmissionRow,
    ContactSubmissionStatusUpdate,
    JobsBySourceItem,
    JobsOverTimePoint,
    PipelineHealthResponse,
    PipelineMetricsResponse,
    PipelineRunLogListResponse,
    PipelineRunLogRow,
    RawJobAdminDetail,
    RawJobAdminListResponse,
    RawJobAdminRow,
    SystemHealthResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)
DbSession = Annotated[Session, Depends(get_db)]


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/stats", response_model=AdminOverviewStats)
def get_stats(admin: AdminUser, db: DbSession) -> AdminOverviewStats:
    stats = crud_admin.get_overview_stats(db)
    return AdminOverviewStats(**stats)


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    admin: AdminUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by email or name"),
    role: UserRole | None = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(25, ge=1, le=100, description="Page size"),
) -> AdminUserListResponse:
    items, total = crud_admin.list_users(db, search=search, role=role, page=page, size=size)
    return AdminUserListResponse(
        items=[AdminUserRow.model_validate(u) for u in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/users/{user_id}", response_model=AdminUserRow)
def get_user(user_id: uuid.UUID, admin: AdminUser, db: DbSession) -> AdminUserRow:
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return AdminUserRow.model_validate(user)


@router.get("/users/{user_id}/profile", response_model=AdminUserProfile)
def get_user_profile(user_id: uuid.UUID, admin: AdminUser, db: DbSession) -> AdminUserProfile:
    profile = crud_admin.get_user_profile_admin(db, user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return AdminUserProfile.model_validate(profile)


@router.patch("/users/{user_id}/role", response_model=AdminUserRow)
def update_role(
    user_id: uuid.UUID,
    body: AdminRoleUpdateRequest,
    admin: AdminUser,
    db: DbSession,
    request: Request,
) -> AdminUserRow:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    previous_role = user.role
    updated = crud_admin.set_user_role(db, user, body.role)
    crud_admin.log_admin_action(
        db,
        admin_user_id=admin.id,
        target_user_id=user_id,
        action="user.role_changed",
        details={"previous_role": str(previous_role), "new_role": str(body.role)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    logger.warning(
        "admin_role_changed",
        extra={
            "admin_id": str(admin.id),
            "target_user_id": str(user_id),
            "previous_role": str(previous_role),
            "new_role": str(body.role),
        },
    )
    return AdminUserRow.model_validate(updated)


@router.patch("/users/{user_id}/active", response_model=AdminUserRow)
def update_active(
    user_id: uuid.UUID,
    body: AdminActiveUpdateRequest,
    admin: AdminUser,
    db: DbSession,
    request: Request,
) -> AdminUserRow:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = crud_admin.set_user_active(db, user, body.is_active)
    crud_admin.log_admin_action(
        db,
        admin_user_id=admin.id,
        target_user_id=user_id,
        action="user.active_changed",
        details={"is_active": body.is_active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    logger.warning(
        "admin_active_changed",
        extra={
            "admin_id": str(admin.id),
            "target_user_id": str(user_id),
            "is_active": body.is_active,
        },
    )
    return AdminUserRow.model_validate(updated)


@router.post("/users/{user_id}/notify", status_code=status.HTTP_204_NO_CONTENT)
def send_notification(
    user_id: uuid.UUID,
    body: AdminNotifyRequest,
    admin: AdminUser,
    db: DbSession,
    request: Request,
) -> None:
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    notification_service.create_notification(
        db,
        user_id=user.id,
        type=body.type,
        title=body.title,
        body=body.body,
    )


@router.post("/notifications/bulk", response_model=AdminBulkNotifyResponse)
def send_bulk_notification(
    body: AdminBulkNotifyRequest,
    admin: AdminUser,
    db: DbSession,
    request: Request,
) -> AdminBulkNotifyResponse:
    if body.audience == "role" and body.role is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="role is required")
    if body.audience == "user" and body.user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id is required")
    sent_count = crud_admin.send_bulk_notification(
        db,
        audience=body.audience,
        role=body.role,
        user_id=body.user_id,
        title=body.title,
        body=body.body,
        notification_type=body.type,
    )
    crud_admin.log_admin_action(
        db,
        admin_user_id=admin.id,
        target_user_id=body.user_id,
        action="notification.bulk_sent",
        details={
            "audience": body.audience,
            "role": str(body.role) if body.role else None,
            "type": body.type,
            "title": body.title,
            "sent_count": sent_count,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return AdminBulkNotifyResponse(sent_count=sent_count)


@router.get("/notifications/admin-messages", response_model=AdminNotificationListResponse)
def list_admin_notifications(
    admin: AdminUser,
    db: DbSession,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> AdminNotificationListResponse:
    items, total = crud_admin.list_admin_notifications(db, search=search, page=page, size=size)
    return AdminNotificationListResponse(
        items=[AdminNotificationRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/ai-jobs", response_model=AdminAiJobListResponse)
def list_ai_jobs(
    admin: AdminUser,
    db: DbSession,
    kind: str | None = Query(None, pattern="^(tailor|cover_letter)$"),
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> AdminAiJobListResponse:
    items, total = crud_admin.list_ai_jobs(
        db,
        kind=kind,
        status=status,
        search=search,
        page=page,
        size=size,
    )
    return AdminAiJobListResponse(
        items=[AdminAiJobRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/pipeline/health", response_model=PipelineHealthResponse)
def pipeline_health(admin: AdminUser, db: DbSession) -> PipelineHealthResponse:
    return PipelineHealthResponse.model_validate(crud_admin.get_pipeline_health(db))


@router.get("/pipeline/jobs-over-time", response_model=list[JobsOverTimePoint])
def pipeline_jobs_over_time(admin: AdminUser, db: DbSession) -> list[JobsOverTimePoint]:
    return [JobsOverTimePoint(**p) for p in crud_admin.get_jobs_over_time(db)]


@router.get("/pipeline/jobs-by-source", response_model=list[JobsBySourceItem])
def pipeline_jobs_by_source(admin: AdminUser, db: DbSession) -> list[JobsBySourceItem]:
    return [JobsBySourceItem(**r) for r in crud_admin.get_jobs_by_source(db)]


@router.get("/pipeline/metrics", response_model=PipelineMetricsResponse)
def pipeline_metrics(admin: AdminUser, db: DbSession) -> PipelineMetricsResponse:
    data = crud_admin.get_latest_market_metrics(db)
    return PipelineMetricsResponse.model_validate(data) if data else PipelineMetricsResponse()


@router.get("/pipeline/runs", response_model=PipelineRunLogListResponse)
def pipeline_runs(
    admin: AdminUser,
    db: DbSession,
    pipeline_name: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> PipelineRunLogListResponse:
    items, total = crud_admin.list_pipeline_runs(
        db,
        pipeline_name=pipeline_name,
        status=status,
        page=page,
        size=size,
    )
    return PipelineRunLogListResponse(
        items=[PipelineRunLogRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/raw-jobs", response_model=RawJobAdminListResponse)
def raw_jobs(
    admin: AdminUser,
    db: DbSession,
    search: str | None = Query(None),
    source: str | None = Query(None),
    duplicate: bool | None = Query(None),
    remote: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> RawJobAdminListResponse:
    items, total = crud_admin.list_raw_jobs_admin(
        db,
        search=search,
        source=source,
        duplicate=duplicate,
        remote=remote,
        page=page,
        size=size,
    )
    return RawJobAdminListResponse(
        items=[RawJobAdminRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/raw-jobs/{job_id}", response_model=RawJobAdminDetail)
def raw_job_detail(job_id: uuid.UUID, admin: AdminUser, db: DbSession) -> RawJobAdminDetail:
    job = crud_admin.get_raw_job_detail_admin(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return RawJobAdminDetail.model_validate(job)


@router.get("/system/health", response_model=SystemHealthResponse)
def system_health(
    admin: AdminUser,
    db: DbSession,
    redis_client: Annotated[object, Depends(get_redis_client)],
) -> SystemHealthResponse:
    checks = {
        "db": _check_db(db),
        "redis": _check_redis(redis_client),
        "celery": _check_celery(),
        "adzuna": _check_adzuna(),
    }
    if checks["db"]["status"] == "unhealthy":
        overall_status = "unhealthy"
    elif any(check["status"] != "ok" for check in checks.values()):
        overall_status = "degraded"
    else:
        overall_status = "ok"
    return SystemHealthResponse(status=overall_status, version=settings.VERSION, checks=checks)


@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def audit_logs(
    admin: AdminUser,
    db: DbSession,
    action: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> AdminAuditLogListResponse:
    items, total = crud_admin.list_audit_logs(
        db,
        action=action,
        user_id=user_id,
        page=page,
        size=size,
    )
    return AdminAuditLogListResponse(
        items=[AdminAuditLogRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/billing/users", response_model=AdminBillingUserListResponse)
def billing_users(
    admin: AdminUser,
    db: DbSession,
    search: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> AdminBillingUserListResponse:
    items, total, summary = crud_admin.list_billing_users(
        db,
        search=search,
        status=status,
        page=page,
        size=size,
    )
    return AdminBillingUserListResponse(
        items=[AdminBillingUserRow.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        summary=AdminBillingSummary.model_validate(summary),
    )


@router.get("/contact-submissions", response_model=ContactSubmissionListResponse)
def contact_submissions(
    admin: AdminUser,
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> ContactSubmissionListResponse:
    items, total = crud_admin.list_contact_submissions(
        db,
        status=status_filter,
        search=search,
        page=page,
        size=size,
    )
    return ContactSubmissionListResponse(
        items=[ContactSubmissionRow.model_validate(item, from_attributes=True) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.patch("/contact-submissions/{submission_id}/status", response_model=ContactSubmissionRow)
def update_contact_submission_status(
    submission_id: uuid.UUID,
    body: ContactSubmissionStatusUpdate,
    admin: AdminUser,
    db: DbSession,
    request: Request,
) -> ContactSubmissionRow:
    updated = crud_admin.set_contact_submission_status(db, submission_id, body.status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact submission not found")
    crud_admin.log_admin_action(
        db,
        admin_user_id=admin.id,
        action="contact.status_changed",
        details={"submission_id": str(submission_id), "status": body.status},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ContactSubmissionRow.model_validate(updated, from_attributes=True)
