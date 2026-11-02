"""Job-board scrapers: parsing (no network), failure handling, skill tagging."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import job_pipeline
from app.services.job_scrapers import platsbanken, the_muse
from app.services.job_scrapers.base import redact
from app.services.job_scrapers.platsbanken import PlatsbankenClient
from app.services.job_scrapers.remoteok import RemoteOKClient
from app.services.job_scrapers.remotive import RemotiveClient
from app.services.job_scrapers.skills import extract_tracked_skills, skills_for_posting
from app.services.job_scrapers.the_muse import TheMuseClient

DSN = "postgresql://u:p@localhost/db"


class _Resp:
    def __init__(self, data: Any) -> None:
        self._data = data

    def json(self) -> Any:
        return self._data


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platsbanken.time, "sleep", lambda s: None)


def test_remotive_parses_and_strips_html() -> None:
    jobs = RemotiveClient(DSN).parse_response(
        {
            "jobs": [
                {
                    "id": 7,
                    "title": "Backend Engineer",
                    "company_name": "Acme",
                    "candidate_required_location": "",
                    "description": "<p>Build <b>APIs</b></p><ul><li>Python</li></ul>",
                    "url": "https://remotive.com/7",
                    "job_type": "full_time",
                },
                {"id": "", "title": "no id"},
            ]
        }
    )
    [job] = jobs
    assert job["job_id_external"] == "7"
    assert job["location"] == "Remote"
    assert job["remote_allowed"] is True
    assert "<" not in job["description"] and "• Python" in job["description"]


def test_the_muse_detects_remote_and_landing_page() -> None:
    [job] = TheMuseClient(DSN).parse_response(
        [
            {
                "id": 1,
                "name": "Data Engineer",
                "company": {"name": "Muse Co"},
                "locations": [{"name": "Flexible / Remote"}],
                "contents": "<p>Pipelines</p>",
                "refs": {"landing_page": "https://themuse.com/1"},
                "type": "external",
            }
        ]
    )
    assert job["remote_allowed"] is True
    assert job["url"] == "https://themuse.com/1"
    assert job["company"] == "Muse Co"


def test_the_muse_fails_when_the_first_page_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TheMuseClient(DSN)

    def boom(url: str, **kwargs: Any) -> Any:
        raise requests.ConnectionError("down")

    monkeypatch.setattr(client, "_get", boom)
    with pytest.raises(requests.ConnectionError):
        client.fetch_jobs()


def test_remoteok_skips_legal_notice_and_zero_salaries() -> None:
    jobs = RemoteOKClient(DSN).parse_response(
        [
            {"legal": "API terms"},
            {"id": 9, "position": "SRE", "company": "Ok", "salary_min": 0, "salary_max": "120000",
             "description": "x", "url": "https://remoteok.com/9"},
        ]
    )
    [job] = jobs
    assert job["salary_min"] is None
    assert job["salary_max"] == 120000


def _platsbanken_hit(job_id: str = "123") -> dict[str, Any]:
    return {
        "id": job_id,
        "headline": "Systemutvecklare",
        "employer": {"name": "Stockholms stad", "organization_number": "212000-0142"},
        "workplace_address": {"city": "", "municipality": "Stockholm"},
        "description": {"text": "Vi söker en utvecklare med Python."},
        "webpage_url": "https://arbetsformedlingen.se/platsbanken/annonser/123",
        "last_application_date": "2026-12-01T23:59:59",
        "must_have": {"skills": [{"label": "Python"}]},
        "nice_to_have": {"skills": [{"label": "Docker"}, {"label": "Python"}]},
        "occupation": {"label": "Mjukvaruutvecklare"},
    }


def test_platsbanken_parses_location_deadline_and_skills() -> None:
    [job] = PlatsbankenClient(DSN).parse_response([_platsbanken_hit()])
    assert job["location"] == "Stockholm"
    assert job["application_deadline"] == "2026-12-01T23:59:59"
    assert job["raw_data"]["must_have_skills"] == ["Python"]
    assert job["description"].startswith("Vi söker")


def test_platsbanken_fails_only_when_every_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PlatsbankenClient(DSN, keywords=["python", "java"], occupation_fields=[])
    calls = {"n": 0}

    def flaky(url: str, **kwargs: Any) -> _Resp:
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.Timeout("slow")
        return _Resp({"hits": [_platsbanken_hit("1")]})

    monkeypatch.setattr(client, "_get", flaky)
    assert len(client.fetch_jobs()) == 1  # one keyword failing is tolerated

    def boom(url: str, **kwargs: Any) -> Any:
        raise requests.Timeout("down")

    monkeypatch.setattr(client, "_get", boom)
    with pytest.raises(requests.Timeout):
        client.fetch_jobs()


def test_publication_windows_cover_the_lookback_without_gaps() -> None:
    now = datetime(2026, 11, 2, 12, 0, 0)
    windows = platsbanken.publication_windows(now, lookback_days=30, window_days=7)
    assert windows[0][0] == "2026-10-03T12:00:00"
    assert windows[-1][1] is None  # newest window is open-ended
    for (_, before), (after, _) in zip(windows, windows[1:], strict=False):
        assert before == after
    assert len(windows) == 5


def test_platsbanken_searches_nationwide_by_field_and_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PlatsbankenClient(DSN, keywords=["python"])
    seen: list[dict[str, Any]] = []

    def fake_get(url: str, params: dict[str, Any], **kwargs: Any) -> _Resp:
        seen.append(params)
        if "occupation-field" in params and params["offset"] == 0 and "published-before" not in params:
            # Newest window: one full page, then a short one.
            return _Resp({"hits": [_platsbanken_hit(f"f{i}") for i in range(platsbanken.PAGE_SIZE)]})
        if "occupation-field" in params and params["offset"] == platsbanken.PAGE_SIZE:
            return _Resp({"hits": [_platsbanken_hit("f0"), _platsbanken_hit("last")]})
        if params.get("q") == "python":
            return _Resp({"hits": [_platsbanken_hit("f1"), _platsbanken_hit("kw")]})
        return _Resp({"hits": []})

    monkeypatch.setattr(client, "_get", fake_get)
    jobs = client.fetch_jobs()

    ids = {j["job_id_external"] for j in jobs}
    assert len(ids) == platsbanken.PAGE_SIZE + 2  # duplicates across queries dropped
    assert {"last", "kw"} <= ids
    assert all("municipality" not in p for p in seen)  # all of Sweden
    assert all(p["limit"] == platsbanken.PAGE_SIZE and p["sort"] == "pubdate-desc" for p in seen)
    assert {p["occupation-field"] for p in seen if "occupation-field" in p} == {platsbanken.DATA_IT_FIELD}
    assert all("published-after" in p for p in seen)
    # The keyword query stops after its first short page.
    assert sum(1 for p in seen if p.get("q") == "python") == 1


def test_platsbanken_pages_stop_at_the_offset_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PlatsbankenClient(DSN, keywords=[], lookback_days=1)
    offsets: list[int] = []

    def always_full(url: str, params: dict[str, Any], **kwargs: Any) -> _Resp:
        offsets.append(params["offset"])
        return _Resp({"hits": [_platsbanken_hit(f"{params['offset']}-{i}") for i in range(platsbanken.PAGE_SIZE)]})

    monkeypatch.setattr(client, "_get", always_full)
    client.fetch_jobs()
    assert max(offsets) == platsbanken.MAX_OFFSET


def test_errors_never_carry_credentials_from_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RemotiveClient(DSN)

    class _Resp:
        status_code = 404

        def raise_for_status(self) -> None:
            raise requests.HTTPError(
                "404 Client Error: Not Found for url: "
                "https://api.example.com/search/1?app_id=abc123&app_key=s3cr3t&what=python"
            )

    monkeypatch.setattr(client._session, "get", lambda *a, **k: _Resp())
    with pytest.raises(requests.HTTPError) as caught:
        client._get("https://api.example.com/search/1")
    message = str(caught.value)
    assert "s3cr3t" not in message and "abc123" not in message
    assert "app_key=***" in message and "what=python" in message


def test_redact_masks_credential_params_only() -> None:
    url = "https://x.test/p?api_key=K&token=T&q=python&key=Z"
    assert redact(url) == "https://x.test/p?api_key=***&token=***&q=python&key=***"


def test_tracked_skills_use_word_boundaries() -> None:
    assert extract_tracked_skills("We use JavaScript and React") == ["react", "javascript"]
    assert "java" in extract_tracked_skills("Java and Kotlin")
    assert extract_tracked_skills("") == []


def test_platsbanken_uses_its_own_skills_and_falls_back_to_the_regex() -> None:
    raw = {"must_have_skills": ["Python"], "nice_to_have_skills": ["Docker", "Python", ""]}
    assert skills_for_posting("platsbanken", "irrelevant", raw) == ["Docker", "Python"]
    assert skills_for_posting("platsbanken", "Vi använder Docker", {}) == ["docker"]
    assert skills_for_posting("remotive", "Python and Django", None) == ["django", "python"]


def test_db_conn_str_normalises_driver_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    for url in ("postgresql+psycopg2://u:p@h/db", "postgres://u:p@h/db", "postgresql://u:p@h/db"):
        monkeypatch.setattr(job_pipeline.settings, "DATABASE_URL", url)
        assert job_pipeline.db_conn_str() == "postgresql://u:p@h/db"


def test_every_listed_source_has_a_scraper() -> None:
    for source in job_pipeline.SOURCES:
        assert job_pipeline.build_scraper(source).SOURCE_NAME == source
    with pytest.raises(ValueError):
        job_pipeline.build_scraper("jobbsafari")
    with pytest.raises(ValueError):
        job_pipeline.build_scraper("indeed_se")  # Adzuna has no Sweden endpoint


def test_the_muse_module_is_the_ported_copy() -> None:
    # Guard against importing the frozen Airflow copy by mistake.
    assert the_muse.__name__ == "app.services.job_scrapers.the_muse"
