from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, get_redis_client
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/health", tags=["health"])


def _check_result(status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "detail": detail, **extra}


def _check_db(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        return _check_result("ok", "Database connection succeeded")
    except Exception as exc:
        return _check_result("unhealthy", "Database check failed", error=str(exc))


def _check_redis(redis_client: Any) -> dict[str, Any]:
    try:
        pong = redis_client.ping()
        if pong:
            return _check_result("ok", "Redis ping succeeded")
        return _check_result("degraded", "Redis ping returned a falsy response")
    except Exception as exc:
        return _check_result("degraded", "Redis check failed", error=str(exc))


def _check_celery() -> dict[str, Any]:
    try:
        inspector = celery_app.control.inspect(timeout=1)
        active_workers = inspector.active() or {}
        if active_workers:
            return _check_result(
                "ok",
                "Celery workers available",
                active_workers=list(active_workers.keys()),
            )
        return _check_result("degraded", "No active Celery workers reported", active_workers=[])
    except Exception as exc:
        return _check_result("degraded", "Celery check failed", error=str(exc))


def _check_adzuna() -> dict[str, Any]:
    configured = bool(settings.ADZUNA_APP_ID)
    if configured:
        return _check_result("ok", "Adzuna app ID is configured", configured=True)
    return _check_result("degraded", "Adzuna app ID is not configured", configured=False)


@router.get("/detailed")
def detailed_health(
    db: Session = Depends(get_db),
    redis_client: Any = Depends(get_redis_client),
) -> dict[str, Any]:
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

    return {
        "status": overall_status,
        "version": settings.VERSION,
        "checks": checks,
    }
