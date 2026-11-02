"""Platsbanken (Arbetsförmedlingen) job scraper.

Uses the public JobTech Dev search API — no API key required for basic usage.
Docs: https://jobsearch.api.jobtechdev.se/swagger-ui/

Searches all of Sweden: the whole Data/IT occupation field plus a keyword list
for tech roles filed elsewhere, limited to ads published in the last 30 days.
Re-fetching ads seen on earlier nights is harmless: inserts are
``ON CONFLICT DO NOTHING``.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.job_scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

JOBTECH_SEARCH_URL = "https://jobsearch.api.jobtechdev.se/search"

PAGE_SIZE = 100  # JobTech's maximum ``limit``
MAX_OFFSET = 2000  # JobTech rejects a larger ``offset``

# Whole occupation fields, searched nationwide. Data/IT covers every
# developer, ops, data and IT-support role (~2,500 live ads).
DATA_IT_FIELD = "apaJ_2ja_LuF"
DEFAULT_OCCUPATION_FIELDS: list[str] = [DATA_IT_FIELD]

# Keywords catch tech roles Arbetsförmedlingen files under other fields
# (engineering, research, design, product). Ads already found through the
# occupation field are deduplicated by id.
DEFAULT_KEYWORDS: list[str] = [
    "python", "javascript", "typescript", "java", "backend", "frontend",
    "fullstack", "devops", "cloud", "data engineer", "data scientist",
    "data analyst", "dataanalytiker", "machine learning", "ux designer",
    "product owner", "mjukvaruutvecklare", "systemutvecklare",
]

# Ads older than this are not fetched: retention archives postings after
# 30 days anyway, and the slim archived row keeps them from coming back.
DEFAULT_LOOKBACK_DAYS = 30
# Each occupation-field query covers one window so it stays under MAX_OFFSET.
WINDOW_DAYS = 7
KEYWORD_PAGES = 3


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def publication_windows(
    now: datetime, lookback_days: int = DEFAULT_LOOKBACK_DAYS, window_days: int = WINDOW_DAYS
) -> list[tuple[str, str | None]]:
    """Consecutive (published-after, published-before) windows covering the
    lookback period. The newest window is open-ended so nothing published
    while the run is in progress falls between two runs."""
    windows: list[tuple[str, str | None]] = []
    cursor = now - timedelta(days=lookback_days)
    while cursor < now:
        end = cursor + timedelta(days=window_days)
        windows.append((_fmt(cursor), _fmt(end) if end < now else None))
        cursor = end
    return windows


class PlatsbankenClient(BaseScraper):
    """Scrape Platsbanken nationwide via the JobTech Dev API (no key needed)."""

    SOURCE_NAME = "platsbanken"

    def __init__(
        self,
        db_conn_str: str,
        keywords: list[str] | None = None,
        occupation_fields: list[str] | None = None,
        municipality_ids: list[str] | None = None,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        keyword_pages: int = KEYWORD_PAGES,
        api_key: str | None = None,
    ) -> None:
        super().__init__(db_conn_str)
        self._keywords = DEFAULT_KEYWORDS if keywords is None else keywords
        self._occupation_fields = (
            DEFAULT_OCCUPATION_FIELDS if occupation_fields is None else occupation_fields
        )
        self._municipality_ids = municipality_ids or []
        self._lookback_days = lookback_days
        self._keyword_pages = keyword_pages
        if api_key:
            self._session.headers.update({"api-key": api_key})

    def _queries(self, now: datetime) -> list[tuple[dict[str, Any], int]]:
        """(params, max pages) for every search the run makes."""
        base: dict[str, Any] = {"sort": "pubdate-desc"}
        if self._municipality_ids:
            base["municipality"] = self._municipality_ids
        queries: list[tuple[dict[str, Any], int]] = []
        all_pages = MAX_OFFSET // PAGE_SIZE + 1
        for field in self._occupation_fields:
            for after, before in publication_windows(now, self._lookback_days):
                params = {**base, "occupation-field": field, "published-after": after}
                if before:
                    params["published-before"] = before
                queries.append((params, all_pages))
        since = _fmt(now - timedelta(days=self._lookback_days))
        for keyword in self._keywords:
            queries.append(({**base, "q": keyword, "published-after": since}, self._keyword_pages))
        return queries

    def _run_query(self, params: dict[str, Any], max_pages: int) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for page in range(max_pages):
            resp = self._get(
                JOBTECH_SEARCH_URL, params={**params, "limit": PAGE_SIZE, "offset": page * PAGE_SIZE}
            )
            page_hits = resp.json().get("hits", [])
            hits.extend(page_hits)
            time.sleep(0.5)
            if len(page_hits) < PAGE_SIZE:
                return hits
        if max_pages * PAGE_SIZE > MAX_OFFSET:
            logger.warning("Platsbanken query %s reached the offset cap; older ads skipped", params)
        return hits

    def _fetch_raw(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        succeeded = 0
        last_error: Exception | None = None
        for params, max_pages in self._queries(datetime.now(UTC)):
            try:
                hits = self._run_query(params, max_pages)
            except Exception as exc:
                last_error = exc
                logger.warning("Platsbanken query %s failed: %s", params, exc)
                continue
            succeeded += 1
            for hit in hits:
                job_id = hit.get("id", "")
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    all_jobs.append(hit)

        if not succeeded and last_error is not None:
            # Every request failed: fail the source instead of reporting 0 jobs.
            raise last_error
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
                    "application_deadline": item.get("last_application_date"),
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
