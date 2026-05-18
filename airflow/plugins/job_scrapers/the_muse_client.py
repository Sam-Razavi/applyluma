from __future__ import annotations

import logging
from typing import Any

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

THE_MUSE_API_URL = "https://www.themuse.com/api/public/jobs"

# Max results per page (API cap)
PAGE_SIZE = 20


class TheMuseClient(BaseScraper):
    SOURCE_NAME = "the_muse"

    def __init__(self, db_conn_str: str, pages: int = 5) -> None:
        super().__init__(db_conn_str)
        self._pages = pages

    # ── BaseScraper implementation ────────────────────────────────────────────

    def _fetch_raw(self) -> list[dict[str, Any]]:
        all_results: list[dict[str, Any]] = []
        for page in range(self._pages):
            params = {"page": page, "descending": "true"}
            logger.info("Fetching The Muse page %d/%d", page + 1, self._pages)
            try:
                data = self._get(THE_MUSE_API_URL, params=params).json()
                results = data.get("results", [])
                all_results.extend(results)
                # Stop early if the API returned fewer rows than a full page
                if len(results) < PAGE_SIZE:
                    break
            except Exception as exc:
                logger.warning("Failed to fetch page %d from The Muse: %s", page, exc)
                break
        return all_results

    def parse_response(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for item in raw:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue

            # Location: The Muse returns a list of location objects
            locations = item.get("locations", [])
            location = locations[0].get("name") if locations else None

            # Remote flag: location name contains "Flexible" or "Remote"
            remote = any(
                "flexible" in (loc.get("name") or "").lower()
                or "remote" in (loc.get("name") or "").lower()
                for loc in locations
            )

            # Description: prefer body field
            description = item.get("contents") or item.get("short_name") or ""

            # Job URL
            refs = item.get("refs", {})
            url = refs.get("landing_page") or ""

            jobs.append(
                {
                    "job_id_external": job_id,
                    "title": item.get("name", ""),
                    "company": (item.get("company") or {}).get("name", ""),
                    "location": location,
                    "description": self._strip_html(description),
                    "url": url,
                    "salary_min": None,
                    "salary_max": None,
                    "employment_type": item.get("type"),
                    "remote_allowed": remote,
                    "raw_data": item,
                }
            )
        return jobs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        import re
        return re.sub(r"<[^>]+>", " ", text).strip()
