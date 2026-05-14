import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add dags folder to path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dags")))

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
