"""Platsbanken (Arbetsförmedlingen) job scraper.

Uses the public JobTech Dev search API — no API key required for basic usage.
Docs: https://jobsearch.api.jobtechdev.se/swagger-ui/
"""
from __future__ import annotations

import logging
import time
from typing import Any

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

JOBTECH_SEARCH_URL = "https://jobsearch.api.jobtechdev.se/search"

DEFAULT_KEYWORDS: list[str] = [
    "python", "javascript", "typescript", "java", "go", "backend",
    "frontend", "fullstack", "devops", "data engineer", "machine learning",
    "cloud", "api", "mjukvaruutvecklare", "systemutvecklare",
    "backendutvecklare", "frontendutvecklare",
]

# Municipalities covering Stockholm, Gothenburg, Malmö
DEFAULT_MUNICIPALITIES: list[str] = [
    "0180",  # Stockholm
    "1480",  # Gothenburg
    "1280",  # Malmö
    "0182",  # Nacka
    "0181",  # Solna
]


class PlatsbankenClient(BaseScraper):
    """Scrape Platsbanken via the JobTech Dev API."""

    SOURCE_NAME = "platsbanken"

    def __init__(
        self,
        db_conn_str: str,
        keywords: list[str] | None = None,
        municipality_ids: list[str] | None = None,
        limit: int = 100,
        api_key: str | None = None,
    ) -> None:
        super().__init__(db_conn_str)
        self._keywords = keywords or DEFAULT_KEYWORDS
        self._municipality_ids = municipality_ids or DEFAULT_MUNICIPALITIES
        self._limit = limit
        if api_key:
            self._session.headers.update({"api-key": api_key})

    def _fetch_raw(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for keyword in self._keywords:
            params: dict[str, Any] = {
                "q": keyword,
                "limit": min(self._limit, 100),
                "offset": 0,
            }
            if self._municipality_ids:
                params["municipality"] = self._municipality_ids

            try:
                resp = self._get(JOBTECH_SEARCH_URL, params=params)
                data = resp.json()
                hits = data.get("hits", [])
                for hit in hits:
                    job_id = hit.get("id", "")
                    if job_id and job_id not in seen_ids:
                        seen_ids.add(job_id)
                        all_jobs.append(hit)
            except Exception as exc:
                logger.warning("Error fetching keyword=%s: %s", keyword, exc)

            time.sleep(0.5)

        logger.info("Fetched %d unique Platsbanken jobs", len(all_jobs))
        return all_jobs

    def parse_response(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

        for item in raw:
            job_id = item.get("id", "")
            if not job_id:
                continue

            employer = item.get("employer") or {}
            workplace = item.get("workplace_address") or {}
            salary = item.get("salary_type") or {}

            description_parts = []
            desc_obj = item.get("description") or {}
            if isinstance(desc_obj, dict):
                description_parts.append(desc_obj.get("text") or "")
                description_parts.append(desc_obj.get("text_formatted") or "")
            elif isinstance(desc_obj, str):
                description_parts.append(desc_obj)

            description = " ".join(p for p in description_parts if p).strip()

            location = (
                workplace.get("city")
                or workplace.get("municipality")
                or workplace.get("region")
                or "Sweden"
            )

            working_hours = item.get("working_hours_type") or {}
            employment_type = working_hours.get("label") if isinstance(working_hours, dict) else None

            jobs.append(
                {
                    "job_id_external": str(job_id),
                    "title": item.get("headline", ""),
                    "company": employer.get("name", "Unknown"),
                    "location": location,
                    "description": description or item.get("headline", ""),
                    "url": item.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{job_id}",
                    "salary_min": None,
                    "salary_max": None,
                    "employment_type": employment_type,
                    "remote_allowed": bool(item.get("workplace_address", {}).get("municipality") == ""),
                    "raw_data": {
                        "source": "platsbanken",
                        "id": job_id,
                        "occupation": item.get("occupation", {}).get("label"),
                        "employer_org_number": employer.get("organization_number"),
                        "must_have_skills": [
                            s.get("label") for s in item.get("must_have", {}).get("skills", [])
                        ],
                        "nice_to_have_skills": [
                            s.get("label") for s in item.get("nice_to_have", {}).get("skills", [])
                        ],
                        "publication_date": item.get("publication_date"),
                        "last_application_date": item.get("last_application_date"),
                    },
                }
            )

        return jobs
