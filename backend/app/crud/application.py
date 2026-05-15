import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_contact import ApplicationContact
from app.models.application_event import ApplicationEvent
from app.schemas.application import ApplicationContactCreate, ApplicationCreate, ApplicationUpdate
from app.schemas.application_analytics import (
    ApplicationAnalytics,
    FunnelCount,
    SalaryBucketCount,
    SourceCount,
    WeeklyApplicationCount,
)

APPLICATION_STATUSES = (
    "wishlist",
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
)
RESPONSE_STATUSES = {"phone_screen", "interview", "offer", "rejected"}
SALARY_BUCKETS = ("<30k", "30-60k", "60-90k", "90-120k", "120k+")


def create_application(db: Session, user_id: uuid.UUID, data: ApplicationCreate) -> Application:
    application = Application(user_id=user_id, **data.model_dump())
    db.add(application)
    db.flush()
    db.add(
        ApplicationEvent(
            application_id=application.id,
            event_type="status_changed",
            new_value=application.status,
        )
    )
    db.commit()
    db.refresh(application)
    return application


def get_applications(
    db: Session,
    user_id: uuid.UUID,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Application]:
    query = db.query(Application).filter(Application.user_id == user_id)
    if status_filter:
        query = query.filter(Application.status == status_filter)
    return query.order_by(Application.updated_at.desc()).offset(skip).limit(limit).all()


def get_application(db: Session, id: uuid.UUID, user_id: uuid.UUID) -> Application | None:
    return db.query(Application).filter(Application.id == id, Application.user_id == user_id).first()


def update_application(
    db: Session,
    id: uuid.UUID,
    user_id: uuid.UUID,
    data: ApplicationUpdate,
) -> Application | None:
    application = get_application(db, id, user_id)
    if not application:
        return None

    updates = data.model_dump(exclude_unset=True)
    old_status = application.status
    for field, value in updates.items():
        setattr(application, field, value)

    if "status" in updates and updates["status"] != old_status:
        db.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="status_changed",
                old_value=old_status,
                new_value=updates["status"],
            )
        )

    db.commit()
    db.refresh(application)
    return application


def delete_application(db: Session, id: uuid.UUID, user_id: uuid.UUID) -> bool:
    application = get_application(db, id, user_id)
    if not application:
        return False
    db.delete(application)
    db.commit()
    return True


def add_contact(
    db: Session,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ApplicationContactCreate,
) -> ApplicationContact | None:
    application = get_application(db, application_id, user_id)
    if not application:
        return None
    contact = ApplicationContact(application_id=application_id, **data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(
    db: Session,
    contact_id: uuid.UUID,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    application = get_application(db, application_id, user_id)
    if not application:
        return False
    contact = (
        db.query(ApplicationContact)
        .filter(
            ApplicationContact.id == contact_id,
            ApplicationContact.application_id == application_id,
        )
        .first()
    )
    if not contact:
        return False
    db.delete(contact)
    db.commit()
    return True


def get_stats(db: Session, user_id: uuid.UUID) -> dict[str, int]:
    stats = dict.fromkeys(APPLICATION_STATUSES, 0)
    rows = (
        db.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == user_id)
        .group_by(Application.status)
        .all()
    )
    for status, count in rows:
        stats[status] = count
    return stats


def get_analytics(db: Session, user_id: uuid.UUID) -> ApplicationAnalytics:
    params = {"user_id": user_id}

    funnel_rows = _execute_mappings(
        db,
        """
        SELECT status, COUNT(*) AS count
        FROM applications
        WHERE user_id = :user_id
        GROUP BY status
        """,
        params,
    )
    funnel_counts = dict.fromkeys(APPLICATION_STATUSES, 0)
    for row in funnel_rows:
        status = str(_row_value(row, "status"))
        if status in funnel_counts:
            funnel_counts[status] = int(_row_value(row, "count") or 0)

    submitted_count = sum(
        count for status, count in funnel_counts.items() if status != "wishlist"
    )
    response_count = sum(funnel_counts[status] for status in RESPONSE_STATUSES)
    offer_count = funnel_counts["offer"]
    response_rate = response_count / submitted_count if submitted_count else 0.0
    offer_rate = offer_count / submitted_count if submitted_count else 0.0

    average_response_days = _average_response_days(db, params)
    weekly_counts = _weekly_counts(db, params)
    top_sources = _top_sources(db, params)
    salary_distribution = _salary_distribution(db, params)

    return ApplicationAnalytics(
        funnel=[
            FunnelCount(status=status, count=funnel_counts[status])
            for status in APPLICATION_STATUSES
        ],
        response_rate=response_rate,
        offer_rate=offer_rate,
        average_response_days=average_response_days,
        weekly_counts=weekly_counts,
        top_sources=top_sources,
        salary_distribution=salary_distribution,
    )


def _average_response_days(db: Session, params: dict[str, Any]) -> float | None:
    rows = _execute_mappings(
        db,
        """
        SELECT AVG(EXTRACT(EPOCH FROM (responses.first_event_date - a.applied_date)) / 86400.0)
            AS average_response_days
        FROM applications a
        JOIN (
            SELECT application_id, MIN(event_date) AS first_event_date
            FROM application_events
            WHERE new_value IS NOT NULL AND new_value != 'applied'
            GROUP BY application_id
        ) responses ON responses.application_id = a.id
        WHERE a.user_id = :user_id
          AND a.applied_date IS NOT NULL
        """,
        params,
    )
    if not rows:
        return None
    value = _row_value(rows[0], "average_response_days")
    return float(value) if value is not None else None


def _weekly_counts(db: Session, params: dict[str, Any]) -> list[WeeklyApplicationCount]:
    rows = _execute_mappings(
        db,
        """
        WITH weeks AS (
            SELECT generate_series(
                date_trunc('week', now()) - interval '11 weeks',
                date_trunc('week', now()),
                interval '1 week'
            ) AS week_start
        )
        SELECT to_char(weeks.week_start::date, 'YYYY-MM-DD') AS week_start,
               COUNT(a.id) AS count
        FROM weeks
        LEFT JOIN applications a
          ON date_trunc('week', a.created_at) = weeks.week_start
         AND a.user_id = :user_id
        GROUP BY weeks.week_start
        ORDER BY weeks.week_start
        """,
        params,
    )
    return [
        WeeklyApplicationCount(
            week_start=str(_row_value(row, "week_start")),
            count=int(_row_value(row, "count") or 0),
        )
        for row in rows
    ]


def _top_sources(db: Session, params: dict[str, Any]) -> list[SourceCount]:
    rows = _execute_mappings(
        db,
        """
        SELECT COALESCE(NULLIF(source, ''), 'unknown') AS source, COUNT(*) AS count
        FROM applications
        WHERE user_id = :user_id
        GROUP BY COALESCE(NULLIF(source, ''), 'unknown')
        ORDER BY count DESC, source ASC
        LIMIT 5
        """,
        params,
    )
    return [
        SourceCount(
            source=str(_row_value(row, "source") or "unknown"),
            count=int(_row_value(row, "count") or 0),
        )
        for row in rows
    ]


def _salary_distribution(db: Session, params: dict[str, Any]) -> list[SalaryBucketCount]:
    rows = _execute_mappings(
        db,
        """
        WITH salary_values AS (
            SELECT COALESCE(salary_max, salary_min) AS salary
            FROM applications
            WHERE user_id = :user_id
              AND COALESCE(salary_max, salary_min) IS NOT NULL
        )
        SELECT
            CASE
                WHEN salary < 30000 THEN '<30k'
                WHEN salary < 60000 THEN '30-60k'
                WHEN salary < 90000 THEN '60-90k'
                WHEN salary < 120000 THEN '90-120k'
                ELSE '120k+'
            END AS bucket,
            COUNT(*) AS count
        FROM salary_values
        GROUP BY bucket
        """,
        params,
    )
    counts = dict.fromkeys(SALARY_BUCKETS, 0)
    for row in rows:
        bucket = str(_row_value(row, "bucket"))
        if bucket in counts:
            counts[bucket] = int(_row_value(row, "count") or 0)
    return [SalaryBucketCount(bucket=bucket, count=counts[bucket]) for bucket in SALARY_BUCKETS]


def _execute_mappings(db: Session, query: str, params: dict[str, Any]) -> Sequence[Any]:
    result = db.execute(text(query), params)
    if hasattr(result, "mappings"):
        return result.mappings().all()
    return result.all()


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    if hasattr(row, key):
        return getattr(row, key)
    try:
        return row[key]
    except (KeyError, TypeError):
        return None
