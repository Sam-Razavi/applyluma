"""Indeed Sweden job scraper.

Uses the Adzuna API with country="se" to surface Swedish job listings.
Indeed.se results are included in the Adzuna dataset.

Requires:
    ADZUNA_APP_ID  — your Adzuna application ID
    ADZUNA_API_KEY — your Adzuna API key
"""
from __future__ import annotations

import logging
import time
from typing import Any

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/se/search"

DEFAULT_QUERIES: list[str] = [
    "python developer",
    "javascript developer",
    "backend developer",
    "frontend developer",
    "fullstack developer",
    "devops engineer",
    "data engineer",
    "software engineer",
    "mjukvaruutvecklare",
    "systemutvecklare",
]


class IndeedSeClient(BaseScraper):
    """Scrape Swedish jobs from Adzuna (which includes Indeed.se listings)."""

    SOURCE_NAME = "indeed_se"

    def __init__(
        self,
        db_conn_str: str,
        app_id: str,
        api_key: str,
        queries: list[str] | None = None,
        results_per_query: int = 50,
    ) -> None:
        super().__init__(db_conn_str)
        self._app_id = app_id
        self._api_key = api_key
        self._queries = queries or DEFAULT_QUERIES
        self._results_per_query = results_per_query

    def _fetch_raw(self) -> list[dict[str, Any]]:
        if not self._app_id or not self._api_key:
            logger.warning("ADZUNA_APP_ID / ADZUNA_API_KEY not set; skipping Indeed.se scrape")
            return []

        all_results: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for query in self._queries:
            page = 1
            while True:
                params = {
                    "app_id": self._app_id,
                    "app_key": self._api_key,
                    "what": query,
                    "where": "Sweden",
                    "results_per_page": min(self._results_per_query, 50),
                    "content-type": "application/json",
                }
                try:
                    resp = self._get(f"{ADZUNA_BASE_URL}/{page}", params=params)
                    data = resp.json()
                except Exception as exc:
                    logger.warning("Adzuna error q=%s page=%d: %s", query, page, exc)
                    break

                results = data.get("results", [])
                if not results:
                    break

                for job in results:
                    job_id = str(job.get("id", ""))
                    if job_id and job_id not in seen_ids:
                        seen_ids.add(job_id)
                        all_results.append(job)

                # Only fetch first page per query to stay within rate limits
                break

            time.sleep(0.5)

        logger.info("Fetched %d unique Indeed.se jobs via Adzuna", len(all_results))
        return all_results

    def parse_response(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

        for item in raw:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue

            company = item.get("company") or {}
            company_name = company.get("display_name", "Unknown") if isinstance(company, dict) else str(company)

            location = item.get("location") or {}
            location_str = location.get("display_name", "Sweden") if isinstance(location, dict) else str(location)

            salary_min = self._to_int(item.get("salary_min"))
            salary_max = self._to_int(item.get("salary_max"))

            jobs.append(
                {
                    "job_id_external": job_id,
                    "title": item.get("title", ""),
                    "company": company_name,
                    "location": location_str,
                    "description": item.get("description", ""),
                    "url": item.get("redirect_url", ""),
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "employment_type": item.get("contract_type"),
                    "remote_allowed": False,
                    "raw_data": {
                        "source": "indeed_se",
                        "adzuna_id": job_id,
                        "category": (item.get("category") or {}).get("tag"),
                        "created": item.get("created"),
                        "adref": item.get("adref"),
                    },
                }
            )

        return jobs

    @staticmethod
    def _to_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return None
