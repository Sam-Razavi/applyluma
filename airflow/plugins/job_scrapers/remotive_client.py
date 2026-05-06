from __future__ import annotations

import logging
from typing import Any

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

# Categories that map well to software / tech roles
TECH_CATEGORIES = [
    "software-dev",
    "devops-sysadmin",
    "data",
    "qa",
    "product",
    "backend",
    "frontend",
]


class RemotiveClient(BaseScraper):
    SOURCE_NAME = "remotive"

    def __init__(self, db_conn_str: str, category: str | None = None, limit: int = 100) -> None:
        super().__init__(db_conn_str)
        self._category = category
        self._limit = limit

    # ── BaseScraper implementation ────────────────────────────────────────────

    def _fetch_raw(self) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": self._limit}
        if self._category:
            params["category"] = self._category
        logger.info("Fetching Remotive jobs: url=%s params=%s", REMOTIVE_API_URL, params)
        return self._get(REMOTIVE_API_URL, params=params).json()

    def parse_response(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        jobs_raw: list[dict] = raw.get("jobs", [])
        jobs: list[dict[str, Any]] = []
        for item in jobs_raw:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue
            jobs.append(
                {
                    "job_id_external": job_id,
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": item.get("candidate_required_location") or "Remote",
                    "description": self._strip_html(item.get("description", "")),
                    "url": item.get("url", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "employment_type": item.get("job_type"),
                    "remote_allowed": True,
                    "raw_data": item,
                }
            )
        return jobs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """Minimal HTML tag removal — avoids a heavy dependency."""
        import re
        return re.sub(r"<[^>]+>", " ", text).strip()
