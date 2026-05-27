from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import psycopg2
import psycopg2.extras
import requests

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all job source scrapers."""

    SOURCE_NAME: str = ""
    REQUEST_TIMEOUT: int = 30

    def __init__(self, db_conn_str: str) -> None:
        if not self.SOURCE_NAME:
            raise ValueError("SOURCE_NAME must be set on the subclass")
        self._db_conn_str = db_conn_str
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ApplyLuma Job Scraper/1.0"})

    # ── Public entry point ────────────────────────────────────────────────────

    def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetch, parse, and return a list of normalised job dicts."""
        logger.info("Starting scrape for source=%s", self.SOURCE_NAME)
        try:
            raw = self._fetch_raw()
            jobs = self.parse_response(raw)
            logger.info("Parsed %d jobs from %s", len(jobs), self.SOURCE_NAME)
            return jobs
        except requests.RequestException as exc:
            logger.error("HTTP error scraping %s: %s", self.SOURCE_NAME, exc)
            raise
        except Exception as exc:
            logger.error("Unexpected error scraping %s: %s", self.SOURCE_NAME, exc)
            raise

    def save_to_db(self, jobs: list[dict[str, Any]]) -> int:
        """Upsert jobs into raw_job_postings. Returns number of rows inserted."""
        if not jobs:
            logger.info("No jobs to save for source=%s", self.SOURCE_NAME)
            return 0

        insert_sql = """
            INSERT INTO raw_job_postings (
                source, job_id_external, title, company, location,
                description, url, salary_min, salary_max,
                employment_type, remote_allowed, raw_data
            ) VALUES %s
            ON CONFLICT (source, job_id_external) DO NOTHING
        """
        rows = [
            (
                self.SOURCE_NAME,
                j["job_id_external"],
                j["title"],
                j["company"],
                j.get("location"),
                j["description"],
                j["url"],
                j.get("salary_min"),
                j.get("salary_max"),
                j.get("employment_type"),
                j.get("remote_allowed", False),
                psycopg2.extras.Json(j.get("raw_data", {})),
            )
            for j in jobs
        ]

        conn = psycopg2.connect(self._db_conn_str)
        try:
            with conn, conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, insert_sql, rows)
                inserted = cur.rowcount
            logger.info("Saved %d new rows for source=%s", inserted, self.SOURCE_NAME)
            return inserted
        finally:
            conn.close()

    # ── Abstract / overridable ────────────────────────────────────────────────

    @abstractmethod
    def _fetch_raw(self) -> Any:
        """Make the HTTP request(s) and return raw data for parse_response()."""

    @abstractmethod
    def parse_response(self, raw: Any) -> list[dict[str, Any]]:
        """Convert raw API data into normalised job dicts.

        Each dict must contain at minimum:
            job_id_external, title, company, description, url
        """

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(url, timeout=self.REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
