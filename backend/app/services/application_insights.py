"""Personal job-search insights, computed from a user's own applications.

Pure functions over plain dicts (no database access) so every rule can be
unit-tested. ``crud.application.get_insights`` loads the rows.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from app.schemas.application_analytics import (
    ApplicationInsights,
    CvPerformance,
    LabelCount,
    SourcePerformance,
    StageReach,
    UpcomingItem,
)

# Statuses in pipeline order; "reached" a stage means at or beyond it.
STAGES = ("applied", "phone_screen", "interview", "offer")
_STAGE_RANK = {stage: index for index, stage in enumerate(STAGES)}
RESPONSE_STATUSES = {"phone_screen", "interview", "offer", "rejected"}
CLOSED_STATUSES = {"rejected", "withdrawn"}
AWAITING_REPLY_DAYS = 14
UPCOMING_WINDOW_DAYS = 14
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
WORK_MODE_LABELS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "onsite": "On-site",
    "on-site": "On-site",
    "on_site": "On-site",
}


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _rate(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def _top(counter: Counter[str], limit: int = 5) -> list[LabelCount]:
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))
    return [LabelCount(label=label, count=count) for label, count in ordered[:limit]]


def _clean(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _reached_ranks(app: Mapping[str, Any], events: Mapping[str, set[str]]) -> set[str]:
    """Stages an application has ever been in (current status plus history)."""
    seen = set(events.get(str(app["id"]), set()))
    seen.add(str(app["status"]))
    return seen


def compute_insights(
    applications: Iterable[Mapping[str, Any]],
    status_history: Mapping[str, set[str]],
    cv_titles: Mapping[str, str],
    now: datetime | None = None,
) -> ApplicationInsights:
    """Build the insights payload.

    ``applications``: dicts with id, status, created_at, applied_date,
    interview_date, deadline, source, location, remote_type, company_name,
    job_title, cv_id, salary_min, salary_max.
    ``status_history``: application id -> every status it has ever had.
    """
    now = _aware(now) or datetime.now(UTC)
    apps = list(applications)

    submitted_apps = [a for a in apps if a["status"] != "wishlist"]
    submitted = len(submitted_apps)

    def reached(app: Mapping[str, Any]) -> set[str]:
        return _reached_ranks(app, status_history)

    # --- stage reach (how far did applications get?) ----------------------
    stage_reach: list[StageReach] = []
    for stage in STAGES:
        rank = _STAGE_RANK[stage]
        count = 0
        for app in submitted_apps:
            history = reached(app)
            if any(_STAGE_RANK.get(s, -1) >= rank for s in history):
                count += 1
        stage_reach.append(StageReach(stage=stage, count=count, rate=_rate(count, submitted)))
    interview_count = next(s.count for s in stage_reach if s.stage == "interview")

    # --- recent volume ----------------------------------------------------
    def added(app: Mapping[str, Any]) -> datetime:
        return _aware(app.get("applied_date")) or _aware(app["created_at"]) or now

    week_ago, two_weeks_ago, month_ago = (now - timedelta(days=d) for d in (7, 14, 30))
    applied_last_7d = sum(1 for a in submitted_apps if added(a) >= week_ago)
    applied_prev_7d = sum(1 for a in submitted_apps if two_weeks_ago <= added(a) < week_ago)
    applied_last_30d = sum(1 for a in submitted_apps if added(a) >= month_ago)

    # --- waiting on a reply ----------------------------------------------
    cutoff = now - timedelta(days=AWAITING_REPLY_DAYS)
    awaiting_reply = sum(1 for a in apps if a["status"] == "applied" and added(a) <= cutoff)

    # --- breakdowns -------------------------------------------------------
    modes: Counter[str] = Counter()
    locations: Counter[str] = Counter()
    companies: Counter[str] = Counter()
    for app in apps:
        mode = _clean(app.get("remote_type"))
        if mode:
            modes[WORK_MODE_LABELS.get(mode.lower(), mode.title())] += 1
        location = _clean(app.get("location"))
        if location:
            locations[location] += 1
        company = _clean(app.get("company_name"))
        if company:
            companies[company] += 1

    weekday_counter: Counter[int] = Counter(added(a).weekday() for a in submitted_apps)
    weekday_counts = [
        LabelCount(label=name, count=weekday_counter.get(index, 0))
        for index, name in enumerate(WEEKDAYS)
    ]

    # --- performance by source and by CV ---------------------------------
    by_source: dict[str, list[int]] = {}
    by_cv: dict[str | None, list[int]] = {}
    for app in submitted_apps:
        responded = 1 if reached(app) & RESPONSE_STATUSES else 0
        source = _clean(app.get("source")) or "unknown"
        bucket = by_source.setdefault(source, [0, 0])
        bucket[0] += 1
        bucket[1] += responded
        cv_id = str(app["cv_id"]) if app.get("cv_id") else None
        cv_bucket = by_cv.setdefault(cv_id, [0, 0])
        cv_bucket[0] += 1
        cv_bucket[1] += responded

    source_performance = [
        SourcePerformance(
            source=source,
            applications=total,
            responses=responses,
            response_rate=_rate(responses, total),
        )
        for source, (total, responses) in sorted(
            by_source.items(), key=lambda item: (-item[1][0], item[0])
        )[:6]
    ]
    cv_performance = [
        CvPerformance(
            cv_id=cv_id,
            title=cv_titles.get(cv_id, "Deleted CV") if cv_id else "No CV attached",
            applications=total,
            responses=responses,
            response_rate=_rate(responses, total),
        )
        for cv_id, (total, responses) in sorted(
            by_cv.items(), key=lambda item: (-item[1][0], str(item[0]))
        )[:5]
    ]

    # --- upcoming interviews and deadlines -------------------------------
    horizon = now + timedelta(days=UPCOMING_WINDOW_DAYS)
    upcoming: list[UpcomingItem] = []
    for app in apps:
        if app["status"] in CLOSED_STATUSES:
            continue
        for kind, key in (("interview", "interview_date"), ("deadline", "deadline")):
            when = _aware(app.get(key))
            # A deadline for something already applied to no longer matters.
            if kind == "deadline" and app["status"] != "wishlist":
                continue
            if when is not None and now - timedelta(hours=12) <= when <= horizon:
                upcoming.append(
                    UpcomingItem(
                        application_id=str(app["id"]),
                        company_name=str(app["company_name"]),
                        job_title=str(app["job_title"]),
                        kind=kind,
                        date=when.isoformat(),
                        days_away=max(0, (when - now).days),
                    )
                )
    upcoming.sort(key=lambda item: item.date)

    # --- salary -----------------------------------------------------------
    midpoints: list[int] = []
    for app in apps:
        low, high = app.get("salary_min"), app.get("salary_max")
        values = [v for v in (low, high) if v]
        if values:
            midpoints.append(int(sum(values) / len(values)))

    return ApplicationInsights(
        total=len(apps),
        submitted=submitted,
        active=sum(
            1 for a in apps if a["status"] in {"applied", "phone_screen", "interview", "offer"}
        ),
        closed=sum(1 for a in apps if a["status"] in CLOSED_STATUSES),
        wishlist=sum(1 for a in apps if a["status"] == "wishlist"),
        applied_last_7d=applied_last_7d,
        applied_prev_7d=applied_prev_7d,
        applied_last_30d=applied_last_30d,
        interview_rate=_rate(interview_count, submitted),
        awaiting_reply=awaiting_reply,
        awaiting_reply_days=AWAITING_REPLY_DAYS,
        stage_reach=stage_reach,
        work_modes=_top(modes),
        top_locations=_top(locations),
        # Only companies applied to more than once: a list of ones says nothing.
        top_companies=_top(Counter({c: n for c, n in companies.items() if n > 1})),
        weekday_counts=weekday_counts,
        source_performance=source_performance,
        cv_performance=cv_performance,
        upcoming=upcoming[:8],
        salary_median=int(median(midpoints)) if midpoints else None,
        salary_min=min(midpoints) if midpoints else None,
        salary_max=max(midpoints) if midpoints else None,
        salary_sample=len(midpoints),
    )
