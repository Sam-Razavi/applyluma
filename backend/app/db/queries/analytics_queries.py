"""Shared query, cache, and response helpers for Phase 6 analytics endpoints."""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.analytics import AnalyticsResponse, ErrorDetail, ResponseMetadata

ANALYTICS_CACHE_TTL_SECONDS = 3_600
COMPARISON_CACHE_TTL_SECONDS = 900

ALLOWED_ANALYTICS_TABLES = {
    "analytics.fct_job_postings",
    "analytics.dim_skills",
    "analytics.agg_salary_insights",
    "analytics.fct_daily_metrics",
    "analytics.dim_companies",
    "public.cvs",
}
_METADATA_CACHE_TTL_SECONDS = 60
_metadata_cache: dict[tuple[str, str], tuple[datetime, ResponseMetadata]] = {}


def build_cache_key(*parts: Any, **params: Any) -> str:
    key_parts = ["analytics"]
    key_parts.extend(str(part) for part in parts if part is not None)
    for name, value in sorted(params.items()):
        key_parts.append(f"{name}={value}")
    return ":".join(key_parts)


def get_or_cache(redis_client: Any, key: str, ttl: int, fetch_fn: Callable[[], Any]) -> Any:
    cached = redis_client.get(key)
    if cached is not None:
        return json.loads(cached)

    value = fetch_fn()
    redis_client.setex(key, ttl, json.dumps(to_jsonable(value)))
    return value


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def rows_to_dicts(rows: Any) -> list[dict[str, Any]]:
    return [to_jsonable(dict(row._mapping)) for row in rows]


def validate_int(value: int, field: str, min_value: int, max_value: int) -> JSONResponse | None:
    if value < min_value or value > max_value:
        return invalid_params(
            f"{field} must be between {min_value} and {max_value}",
            {field: f"received {value}, allowed range is {min_value}-{max_value}"},
        )
    return None


def validate_float(value: float, field: str, min_value: float, max_value: float) -> JSONResponse | None:
    if value < min_value or value > max_value:
        return invalid_params(
            f"{field} must be between {min_value} and {max_value}",
            {field: f"received {value}, allowed range is {min_value}-{max_value}"},
        )
    return None


def validate_optional_text(value: str | None, field: str, max_length: int = 200) -> JSONResponse | None:
    if value is not None and len(value) > max_length:
        return invalid_params(
            f"{field} must be {max_length} characters or fewer",
            {field: f"received {len(value)} characters, max is {max_length}"},
        )
    return None


def invalid_params(message: str, details: dict[str, Any]) -> JSONResponse:
    return error_response(400, "INVALID_PARAMS", message, details)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    envelope = AnalyticsResponse[Any](
        success=False,
        data=None,
        metadata=None,
        error=ErrorDetail(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


def ok_response(data: Any, metadata: ResponseMetadata) -> AnalyticsResponse[Any]:
    return AnalyticsResponse(success=True, data=data, metadata=metadata, error=None)


def safe_execute(fetch_fn: Callable[[], AnalyticsResponse[Any] | JSONResponse]) -> AnalyticsResponse[Any] | JSONResponse:
    try:
        return fetch_fn()
    except SQLAlchemyError:
        return error_response(500, "INTERNAL_ERROR", "Analytics database query failed")
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Analytics request failed")


def get_dbt_freshness(db: Session, table: str) -> tuple[int, datetime | None]:
    if table not in ALLOWED_ANALYTICS_TABLES:
        raise ValueError(f"Unsupported analytics table: {table}")

    if table == "analytics.agg_salary_insights":
        table = "analytics.fct_job_postings"

    column = "dbt_updated_at"
    if table == "public.cvs":
        column = "updated_at"

    updated_at = db.execute(text(f"SELECT MAX({column}) AS updated_at FROM {table}")).scalar()
    if updated_at is None:
        return 24, None

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    return max(0, int((now - updated_at).total_seconds() // 3600)), updated_at


def get_sample_size(db: Session, table: str) -> int:
    if table not in ALLOWED_ANALYTICS_TABLES:
        raise ValueError(f"Unsupported analytics table: {table}")
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)


def build_metadata(
    db: Session,
    source_table: str,
    applied_filters: dict[str, Any],
    sample_size: int | None = None,
) -> ResponseMetadata:
    cache_key = (source_table, json.dumps(to_jsonable(applied_filters), sort_keys=True))
    now = datetime.now(UTC)
    cached = _metadata_cache.get(cache_key)
    if cached and (now - cached[0]).total_seconds() < _METADATA_CACHE_TTL_SECONDS:
        return cached[1]

    freshness_hours, _ = get_dbt_freshness(db, source_table)
    metadata = ResponseMetadata(
        timestamp=now,
        data_freshness_hours=freshness_hours,
        sample_size=sample_size if sample_size is not None else get_sample_size(db, source_table),
        applied_filters=applied_filters,
        next_update=now + timedelta(hours=24),
    )
    _metadata_cache[cache_key] = (now, metadata)
    return metadata


def non_default_filters(values: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None and value != defaults.get(key)}
