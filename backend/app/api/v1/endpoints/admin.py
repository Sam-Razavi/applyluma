from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import admin as crud_admin
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminActiveUpdateRequest,
    AdminNotifyRequest,
    AdminOverviewStats,
    AdminRoleUpdateRequest,
    AdminUserListResponse,
    AdminUserRow,
)
from app.services import notification_service

router = APIRouter(prefix="/admin", tags=["admin"])
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


@router.patch("/users/{user_id}/role", response_model=AdminUserRow)
def update_role(
    user_id: uuid.UUID,
    body: AdminRoleUpdateRequest,
    admin: AdminUser,
    db: DbSession,
) -> AdminUserRow:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = crud_admin.set_user_role(db, user, body.role)
    return AdminUserRow.model_validate(updated)


@router.patch("/users/{user_id}/active", response_model=AdminUserRow)
def update_active(
    user_id: uuid.UUID,
    body: AdminActiveUpdateRequest,
    admin: AdminUser,
    db: DbSession,
) -> AdminUserRow:
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")
    user = crud_admin.get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = crud_admin.set_user_active(db, user, body.is_active)
    return AdminUserRow.model_validate(updated)


@router.post("/users/{user_id}/notify", status_code=status.HTTP_204_NO_CONTENT)
def send_notification(
    user_id: uuid.UUID,
    body: AdminNotifyRequest,
    admin: AdminUser,
    db: DbSession,
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
