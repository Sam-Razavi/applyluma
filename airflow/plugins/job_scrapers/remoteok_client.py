from __future__ import annotations

import logging
from typing import Any

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# RemoteOK's public API. Terms require attribution: we store the original job
# URL (linking back to remoteok.com) and display the source label in the UI.
REMOTEOK_API_URL = "https://remoteok.com/api"


class RemoteOKClient(BaseScraper):
    SOURCE_NAME = "remoteok"

    def __init__(self, db_conn_str: str, tags: list[str] | None = None) -> None:
        super().__init__(db_conn_str)
        self._tags = tags

    # ── BaseScraper implementation ────────────────────────────────────────────

    def _fetch_raw(self) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if self._tags:
            params["tags"] = ",".join(self._tags)
        logger.info("Fetching RemoteOK jobs: url=%s params=%s", REMOTEOK_API_URL, params)
        return self._get(REMOTEOK_API_URL, params=params).json()

    def parse_response(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            # The first array element is a legal/attribution notice, not a job.
            job_id = str(item.get("id") or "")
            title = item.get("position") or ""
            if not job_id or not title:
                continue
            jobs.append(
                {
                    "job_id_external": job_id,
                    "title": title,
                    "company": item.get("company") or "",
                    "location": item.get("location") or "Remote",
                    "description": self._html_to_text(item.get("description", "")),
                    "url": item.get("url", ""),
                    "salary_min": self._salary(item.get("salary_min")),
                    "salary_max": self._salary(item.get("salary_max")),
                    "employment_type": None,
                    "remote_allowed": True,
                    "raw_data": item,
                }
            )
        return jobs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _salary(value: Any) -> int | None:
        """RemoteOK reports salaries as ints, with 0 meaning 'not provided'."""
        try:
            salary = int(value)
        except (TypeError, ValueError):
            return None
        return salary if salary > 0 else None
