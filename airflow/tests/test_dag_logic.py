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

def test_mark_todays_duplicates_returns_rowcount():
    from job_scrapers.dedupe import mark_todays_duplicates, MARK_TODAYS_DUPLICATES_SQL

    mock_conn = MagicMock()
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.rowcount = 3

    assert mark_todays_duplicates(mock_conn) == 3
    mock_cur.execute.assert_called_once_with(MARK_TODAYS_DUPLICATES_SQL)

def test_dedupe_sql_is_cross_source_rolling_window():
    from job_scrapers.dedupe import DEDUPE_WINDOW_DAYS, MARK_TODAYS_DUPLICATES_SQL

    sql = MARK_TODAYS_DUPLICATES_SQL
    # Rolling window across all sources — no same-day or per-source restriction
    assert f"INTERVAL '{DEDUPE_WINDOW_DAYS} days'" in sql
    assert "source IN" not in sql
    # Normalised match key includes location so per-city postings survive
    assert "lower(trim(title))" in sql
    assert "lower(trim(company))" in sql
    assert "coalesce(lower(trim(location)), '')" in sql
    # Oldest posting wins; only today's rows are ever marked
    assert "ORDER BY scraped_at ASC" in sql
    assert "DATE(scraped_at) = CURRENT_DATE" in sql

def test_keyword_extraction_no_substring_false_positives():
    from job_scrapers.keyword_extraction import extract_keywords_simple

    def matched(text):
        return {kw for kw, _kw_type, _conf, _freq in extract_keywords_simple(text)}

    assert "Go" not in matched("We use Golang and Google Cloud")
    assert "Go" in matched("Experience with Go required")

    assert "Java" not in matched("JavaScript and TypeScript")
    java_and_js = extract_keywords_simple("Java and JavaScript")
    java_and_js_by_kw = {kw: (conf, freq) for kw, _kw_type, conf, freq in java_and_js}
    assert "Java" in java_and_js_by_kw
    assert java_and_js_by_kw["Java"][1] == 1

    assert "SQL" not in matched("PostgreSQL, MySQL and NoSQL stores")
    assert "SQL" in matched("strong SQL skills")


def test_keyword_extraction_symbol_suffixed_keywords():
    from job_scrapers.keyword_extraction import extract_keywords_simple

    matched = {kw for kw, _kw_type, _conf, _freq in extract_keywords_simple("C++ and C# experience")}
    assert "C++" in matched
    assert "C#" in matched


def test_keyword_extraction_multi_word_flexible_separator():
    from job_scrapers.keyword_extraction import extract_keywords_simple

    assert any(kw == "Machine Learning" for kw, *_ in extract_keywords_simple("machine learning"))
    assert any(kw == "Machine Learning" for kw, *_ in extract_keywords_simple("machine-learning"))


def test_keyword_extraction_confidence_by_case():
    from job_scrapers.keyword_extraction import extract_keywords_simple

    exact = {kw: conf for kw, _kw_type, conf, _freq in extract_keywords_simple("We use Python daily")}
    assert exact["Python"] == 1.0

    different_case = {kw: conf for kw, _kw_type, conf, _freq in extract_keywords_simple("We use python daily")}
    assert different_case["Python"] == 0.6


def test_keyword_extraction_empty_input():
    from job_scrapers.keyword_extraction import extract_keywords_simple

    assert extract_keywords_simple("") == []
    assert extract_keywords_simple(None) == []


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
