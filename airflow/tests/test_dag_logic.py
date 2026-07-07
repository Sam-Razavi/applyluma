import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add dags and plugins folders to path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dags")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins")))

from scrape_jobs import _extract_skills_from_text, TRACKED_SKILLS

def test_extract_skills_from_text():
    text = "We are looking for a FastAPI developer with experience in React and Docker."
    expected = ["fastapi", "react", "docker"]
    assert sorted(_extract_skills_from_text(text)) == sorted(expected)

def test_extract_skills_case_insensitivity():
    text = "PYTHON, django, and PostGreSQL"
    expected = ["python", "django", "postgresql"]
    assert sorted(_extract_skills_from_text(text)) == sorted(expected)

def test_extract_skills_no_match():
    text = "Cooking and Gardening are not in our list."
    assert _extract_skills_from_text(text) == []

def test_extract_skills_substring_avoidance():
    # Should match 'java' but not as a substring of 'javascript' if not careful
    # However, 'java' and 'javascript' are both in TRACKED_SKILLS
    text = "Experience with Javascript"
    skills = _extract_skills_from_text(text)
    assert "javascript" in skills
    assert "java" not in skills # \b handles this

@patch("scrape_jobs.PostgresHook")
def test_get_db_conn_str(mock_hook):
    from scrape_jobs import _get_db_conn_str
    mock_instance = mock_hook.return_value
    mock_instance.get_uri.return_value = "postgres://user:pass@host:5432/db"
    
    conn_str = _get_db_conn_str()
    assert conn_str == "postgresql://user:pass@host:5432/db"

REMOTEOK_FIXTURE = [
    # First element of the RemoteOK payload is a legal notice, not a job
    {"0": "legal notice", "legal": "API Terms of Service: attribution required."},
    {
        "id": 123456,
        "position": "Backend Engineer",
        "company": "Acme Corp",
        "location": "Worldwide",
        "description": "<p>Build <b>APIs</b></p><ul><li>Python</li></ul>",
        "url": "https://remoteok.com/remote-jobs/123456",
        "salary_min": 50000,
        "salary_max": 90000,
        "tags": ["python", "backend"],
    },
    {
        # No position -> must be skipped
        "id": 123457,
        "company": "NoTitle Inc",
        "url": "https://remoteok.com/remote-jobs/123457",
    },
    {
        "id": 123458,
        "position": "Data Engineer",
        "company": "DataCo",
        "description": "ETL pipelines",
        "url": "https://remoteok.com/remote-jobs/123458",
        "salary_min": 0,
        "salary_max": 0,
    },
]

def _remoteok_client():
    from job_scrapers.remoteok_client import RemoteOKClient
    return RemoteOKClient(db_conn_str="postgresql://unused")

def test_remoteok_parse_skips_legal_notice_and_titleless_entries():
    jobs = _remoteok_client().parse_response(REMOTEOK_FIXTURE)
    assert [j["job_id_external"] for j in jobs] == ["123456", "123458"]

def test_remoteok_parse_maps_fields():
    job = _remoteok_client().parse_response(REMOTEOK_FIXTURE)[0]
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme Corp"
    assert job["location"] == "Worldwide"
    assert job["url"] == "https://remoteok.com/remote-jobs/123456"
    assert job["salary_min"] == 50000
    assert job["salary_max"] == 90000
    assert job["remote_allowed"] is True
    assert "<p>" not in job["description"]
    assert "APIs" in job["description"]
    assert job["raw_data"]["tags"] == ["python", "backend"]

def test_remoteok_parse_treats_zero_salary_as_missing():
    job = _remoteok_client().parse_response(REMOTEOK_FIXTURE)[1]
    assert job["salary_min"] is None
    assert job["salary_max"] is None
    assert job["location"] == "Remote"

@patch("transform_jobs.PostgresHook")
def test_calculate_daily_metrics_no_rows(mock_hook):
    from transform_jobs import calculate_daily_metrics
    
    mock_conn = MagicMock()
    mock_hook.return_value.get_conn.return_value = mock_conn
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchall.return_value = []
    
    # This should log a warning and return early
    context = {"ti": MagicMock()}
    calculate_daily_metrics(**context)
    
    mock_cur.execute.assert_called_once()
