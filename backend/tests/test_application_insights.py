from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.application_insights import compute_insights, resolve_timezone

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def app(status: str = "applied", days_ago: int = 1, **extra: Any) -> dict[str, Any]:
    when = NOW - timedelta(days=days_ago)
    base: dict[str, Any] = {
        "id": uuid.uuid4(),
        "status": status,
        "created_at": when,
        "applied_date": when,
        "interview_date": None,
        "deadline": None,
        "source": "linkedin",
        "location": "Stockholm",
        "remote_type": "remote",
        "company_name": "Acme",
        "job_title": "Dev",
        "cv_id": None,
        "salary_min": None,
        "salary_max": None,
    }
    base.update(extra)
    return base


def test_empty_user_returns_zeros() -> None:
    result = compute_insights([], {}, {}, NOW)
    assert result.total == 0
    assert result.interview_rate == 0
    assert result.salary_median is None
    assert [s.count for s in result.stage_reach] == [0, 0, 0, 0]


def test_stage_reach_counts_history_not_just_current_status() -> None:
    interviewed_then_rejected = app("rejected")
    plain_applied = app("applied")
    history = {str(interviewed_then_rejected["id"]): {"applied", "interview", "rejected"}}
    result = compute_insights([interviewed_then_rejected, plain_applied], history, {}, NOW)
    reach = {s.stage: s.count for s in result.stage_reach}
    assert reach == {"applied": 2, "phone_screen": 1, "interview": 1, "offer": 0}
    assert result.interview_rate == 0.5


def test_wishlist_is_not_submitted() -> None:
    result = compute_insights([app("wishlist"), app("applied")], {}, {}, NOW)
    assert (result.total, result.submitted, result.wishlist, result.active) == (2, 1, 1, 1)


def test_recent_volume_windows() -> None:
    apps = [app(days_ago=2), app(days_ago=6), app(days_ago=9), app(days_ago=20), app(days_ago=60)]
    result = compute_insights(apps, {}, {}, NOW)
    assert result.applied_last_7d == 2
    assert result.applied_prev_7d == 1
    assert result.applied_last_30d == 4


def test_awaiting_reply_only_counts_old_applied() -> None:
    apps = [app("applied", days_ago=20), app("applied", days_ago=3), app("interview", days_ago=40)]
    result = compute_insights(apps, {}, {}, NOW)
    assert result.awaiting_reply == 1


def test_breakdowns_and_repeat_companies_only() -> None:
    apps = [
        app(company_name="Acme", remote_type="hybrid", location="Malmö"),
        app(company_name="Acme", remote_type="on-site", location="Malmö"),
        app(company_name="Beta", remote_type=None, location=None),
    ]
    result = compute_insights(apps, {}, {}, NOW)
    assert [(c.label, c.count) for c in result.top_companies] == [("Acme", 2)]
    assert {c.label for c in result.work_modes} == {"Hybrid", "On-site"}
    assert result.top_locations[0].label == "Malmö"


def test_source_and_cv_performance() -> None:
    cv = uuid.uuid4()
    a1 = app("interview", source="linkedin", cv_id=cv)
    a2 = app("applied", source="linkedin", cv_id=cv)
    a3 = app("rejected", source=None)
    result = compute_insights([a1, a2, a3], {}, {str(cv): "Main CV"}, NOW)
    linkedin = next(s for s in result.source_performance if s.source == "linkedin")
    assert (linkedin.applications, linkedin.responses, linkedin.response_rate) == (2, 1, 0.5)
    assert any(s.source == "unknown" for s in result.source_performance)
    titles = {c.title: c for c in result.cv_performance}
    assert titles["Main CV"].responses == 1
    assert "No CV attached" in titles


def test_upcoming_interviews_and_wishlist_deadlines_only() -> None:
    soon = app("interview", interview_date=NOW + timedelta(days=3))
    far = app("interview", interview_date=NOW + timedelta(days=40))
    wish_deadline = app("wishlist", deadline=NOW + timedelta(days=5))
    applied_deadline = app("applied", deadline=NOW + timedelta(days=5))
    closed = app("rejected", interview_date=NOW + timedelta(days=2))
    result = compute_insights([soon, far, wish_deadline, applied_deadline, closed], {}, {}, NOW)
    assert [(u.kind, u.days_away) for u in result.upcoming] == [("interview", 3), ("deadline", 5)]


def test_salary_median_uses_midpoints() -> None:
    apps = [
        app(salary_min=40000, salary_max=60000),
        app(salary_min=70000, salary_max=None),
        app(salary_min=None, salary_max=None),
    ]
    result = compute_insights(apps, {}, {}, NOW)
    assert (result.salary_sample, result.salary_min, result.salary_max) == (2, 50000, 70000)
    assert result.salary_median == 60000


def test_naive_datetimes_are_treated_as_utc() -> None:
    naive = app(days_ago=1)
    naive["created_at"] = naive["created_at"].replace(tzinfo=None)
    naive["applied_date"] = None
    assert compute_insights([naive], {}, {}, NOW).applied_last_7d == 1


def test_insights_route_is_declared_before_the_id_route() -> None:
    # FastAPI matches in declaration order; "/insights" after "/{application_id}"
    # would be parsed as a UUID and 422.
    from app.api.v1.endpoints.applications import router

    paths = [getattr(route, "path", "") for route in router.routes]
    assert paths.index("/applications/insights") < paths.index("/applications/{application_id}")


def test_daily_counts_cover_the_last_seven_days_oldest_first() -> None:
    apps = [
        app(days_ago=0),
        app(days_ago=0),
        app(days_ago=1),
        app(days_ago=6),
        app(days_ago=7),  # outside the window
        app("wishlist", days_ago=0),  # not sent
    ]
    result = compute_insights(apps, {}, {}, NOW)
    assert [d.date for d in result.daily_counts][0] == "2026-11-11"
    assert [d.date for d in result.daily_counts][-1] == "2026-11-17"
    assert [d.count for d in result.daily_counts] == [1, 0, 0, 0, 0, 1, 2]


def test_daily_counts_read_applied_date_as_a_calendar_date() -> None:
    # Midnight UTC on the 16th is "the 16th" for everyone, even in timezones
    # where that instant falls on the 15th.
    tz = resolve_timezone("America/Los_Angeles")
    midnight = datetime(2026, 11, 16, tzinfo=UTC)
    result = compute_insights([app(applied_date=midnight)], {}, {}, NOW, tz=tz)
    counts = {d.date: d.count for d in result.daily_counts}
    assert counts["2026-11-16"] == 1
    assert counts["2026-11-15"] == 0


def test_daily_counts_fall_back_to_created_at_in_the_callers_timezone() -> None:
    # 23:30 UTC on the 16th is already the 17th in Stockholm.
    late = datetime(2026, 11, 16, 23, 30, tzinfo=UTC)
    card = app(applied_date=None, created_at=late)
    stockholm = compute_insights([card], {}, {}, NOW, tz=resolve_timezone("Europe/Stockholm"))
    utc = compute_insights([card], {}, {}, NOW)
    assert {d.date: d.count for d in stockholm.daily_counts}["2026-11-17"] == 1
    assert {d.date: d.count for d in utc.daily_counts}["2026-11-16"] == 1


def test_resolve_timezone_falls_back_to_utc() -> None:
    assert resolve_timezone(None) is UTC
    assert resolve_timezone("Not/AZone") is UTC
    assert str(resolve_timezone("Europe/Stockholm")) == "Europe/Stockholm"
