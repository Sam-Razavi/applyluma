"""Jobs read straight from employers' own career pages.

Greenhouse, Lever, Ashby and Teamtailor each publish an employer's open jobs
as a public feed, no key needed. Many of these jobs never reach a job board.
Only jobs in Sweden (or remote within Europe) are kept: the boards of
international employers list every office they have.

A board is always fetched whole, so a stored job that is no longer on its
board has been closed, and is archived (see ``save_to_db``).
"""
from __future__ import annotations

import html
import logging
import re
import time
from collections.abc import Callable
from typing import Any
from xml.etree import ElementTree

import psycopg2

from app.services.job_scrapers.base import BaseScraper
from app.services.job_scrapers.career_boards import BOARDS

logger = logging.getLogger(__name__)

SOURCE = "career_pages"

FEEDS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{board}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{board}",
    "teamtailor": "https://{board}.teamtailor.com/jobs.rss",
}

_SWEDEN = re.compile(
    r"\b(sweden|sverige|stockholm|g[oö]teborg|gothenburg|malm[oö]|lund|uppsala|link[oö]ping|"
    r"v[aä]ster[aå]s|ume[aå]|helsingborg|[oö]rebro|norrk[oö]ping|j[oö]nk[oö]ping|skellefte[aå]|"
    r"lule[aå]|boden|kista|solna|sundsvall|karlstad|g[aä]vle|bor[aå]s|v[aä]xj[oö])\b",
    re.I,
)
_REMOTE_EUROPE = re.compile(r"\b(europe|emea|eu|nordics?|worldwide|anywhere|global)\b", re.I)
_TT = "{https://teamtailor.com/locations}"

PAUSE_SECONDS = 0.3


def place_in_scope(primary: str, others: list[str], remote: bool) -> str | None:
    """Where a user in Sweden could do this job, or None if they could not.

    A job counts when one of its locations is in Sweden, or when it is remote
    and its main location says Europe-wide ("Remote, EMEA"); "Germany (Remote)"
    does not. The Swedish location is returned even when it is not the first
    one listed, so the job is not shown as being in London.
    """
    for place in [primary, *others]:
        if place and _SWEDEN.search(place):
            return place
    if remote and _REMOTE_EUROPE.search(primary):
        return primary
    return None


def _job(
    *, system: str, board: str, job_id: Any, title: str, company: str, location: str,
    description: str, url: str, remote: bool, employment_type: str | None = None,
    deadline: str | None = None,
) -> dict[str, Any]:
    return {
        "job_id_external": f"{system}:{board}:{job_id}",
        "title": (title or "").strip()[:255],
        "company": company[:255],
        "location": (location or "Sweden").strip()[:255],
        "description": description,
        "url": url,
        "salary_min": None,
        "salary_max": None,
        "employment_type": employment_type,
        "remote_allowed": remote,
        "application_deadline": deadline,
        "raw_data": {"source": SOURCE, "system": system, "board": board},
    }


class CareerPagesClient(BaseScraper):
    SOURCE_NAME = SOURCE

    def __init__(self, db_conn_str: str, boards: list[tuple[str, str, str]] | None = None) -> None:
        super().__init__(db_conn_str)
        self._boards = BOARDS if boards is None else boards
        # (system, board) of every board that answered this run.
        self.fetched_boards: list[tuple[str, str]] = []

    # Fetch

    def _fetch_raw(self) -> list[tuple[str, str, str, Any]]:
        fetched: list[tuple[str, str, str, Any]] = []
        last_error: Exception | None = None
        for company, system, board in self._boards:
            try:
                resp = self._get(FEEDS[system].format(board=board))
                payload: Any = resp.text if system == "teamtailor" else resp.json()
            except Exception as exc:
                last_error = exc
                logger.warning("Career page %s (%s) failed: %s", company, system, exc)
                continue
            fetched.append((company, system, board, payload))
            self.fetched_boards.append((system, board))
            time.sleep(PAUSE_SECONDS)
        if self._boards and not fetched and last_error is not None:
            raise last_error  # every board failed: fail the source
        logger.info("Fetched %d of %d career pages", len(fetched), len(self._boards))
        return fetched

    # Parse

    def parse_response(self, raw: list[tuple[str, str, str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        parsers: dict[str, Callable[[str, str, Any], list[dict[str, Any]]]] = {
            "greenhouse": self._greenhouse, "lever": self._lever,
            "ashby": self._ashby, "teamtailor": self._teamtailor,
        }
        for company, system, board, payload in raw:
            try:
                found = parsers[system](company, board, payload)
            except Exception as exc:
                # One odd feed must not lose the others; nor may its jobs be
                # read as closed.
                logger.warning("Career page %s (%s) could not be read: %s", company, system, exc)
                if (system, board) in self.fetched_boards:
                    self.fetched_boards.remove((system, board))
                continue
            jobs.extend(job for job in found if job["title"] and job["url"])
        return jobs

    def _greenhouse(self, company: str, board: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        jobs = []
        for item in payload.get("jobs", []):
            primary = str((item.get("location") or {}).get("name") or "")
            offices = [str(o.get("location") or o.get("name") or "") for o in item.get("offices") or []]
            remote = "remote" in primary.lower()
            location = place_in_scope(primary, offices, remote)
            if location is None:
                continue
            jobs.append(
                _job(
                    system="greenhouse", board=board, job_id=item.get("id"), title=item.get("title", ""),
                    company=item.get("company_name") or company, location=location,
                    description=self._html_to_text(html.unescape(item.get("content") or "")),
                    url=item.get("absolute_url", ""), remote=remote,
                    deadline=item.get("application_deadline") or None,
                )
            )
        return jobs

    def _lever(self, company: str, board: str, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs = []
        for item in payload:
            categories = item.get("categories") or {}
            locations = [str(categories.get("location") or ""), *map(str, categories.get("allLocations") or [])]
            remote = item.get("workplaceType") == "remote"
            location = place_in_scope(
                locations[0], [*locations[1:], "Sweden" if item.get("country") == "SE" else ""], remote
            )
            if location is None:
                continue
            parts = [item.get("descriptionPlain") or ""]
            for block in item.get("lists") or []:
                parts.append(f"{block.get('text', '')}\n{self._html_to_text(block.get('content') or '')}")
            parts.append(item.get("additionalPlain") or "")
            jobs.append(
                _job(
                    system="lever", board=board, job_id=item.get("id"), title=item.get("text", ""),
                    company=company, location=location,
                    description="\n\n".join(p.strip() for p in parts if p and p.strip()),
                    url=item.get("hostedUrl", ""), remote=remote,
                    employment_type=categories.get("commitment"),
                )
            )
        return jobs

    def _ashby(self, company: str, board: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        jobs = []
        for item in payload.get("jobs", []):
            if item.get("isListed") is False:
                continue
            address = ((item.get("address") or {}).get("postalAddress") or {})
            primary = str(item.get("location") or "")
            others = [str(s.get("location") or "") for s in item.get("secondaryLocations") or []]
            if str(address.get("addressCountry") or "").lower() in {"sweden", "sverige", "se"}:
                others.append(f"{primary}, Sweden" if primary else "Sweden")
            remote = bool(item.get("isRemote"))
            location = place_in_scope(primary, others, remote)
            if location is None:
                continue
            # "Stockholm HQ, Sweden" came from the address: show the office name.
            location = primary if location.startswith(primary) and primary else location
            jobs.append(
                _job(
                    system="ashby", board=board, job_id=item.get("id"), title=item.get("title", ""),
                    company=company, location=location,
                    description=(item.get("descriptionPlain") or "").strip()
                    or self._html_to_text(item.get("descriptionHtml") or ""),
                    url=item.get("jobUrl", ""), remote=remote, employment_type=item.get("employmentType"),
                )
            )
        return jobs

    def _teamtailor(self, company: str, board: str, payload: str) -> list[dict[str, Any]]:
        if "<!DOCTYPE" in payload or "<!ENTITY" in payload:
            raise ValueError("unexpected document type in feed")
        jobs = []
        for item in ElementTree.fromstring(payload).iter("item"):
            remote = (item.findtext("remoteStatus") or "").strip().lower() == "fully"
            spots = [
                ", ".join(part for part in (loc.findtext(f"{_TT}city"), loc.findtext(f"{_TT}country")) if part)
                for loc in item.iter(f"{_TT}location")
            ]
            location = place_in_scope(spots[0] if spots else "", spots[1:], remote)
            if location is None:
                continue
            jobs.append(
                _job(
                    system="teamtailor", board=board,
                    job_id=item.findtext("guid") or item.findtext("link"),
                    title=item.findtext("title") or "", company=company,
                    location=location.removesuffix(", Sweden"),
                    description=self._html_to_text(item.findtext("description") or ""),
                    url=(item.findtext("link") or "").strip(), remote=remote,
                )
            )
        return jobs

    # Save

    def save_to_db(self, jobs: list[dict[str, Any]]) -> int:
        """Insert new jobs, then archive stored ones their board no longer lists."""
        inserted = super().save_to_db(jobs)
        if not self.fetched_boards:
            return inserted
        listed = [job["job_id_external"] for job in jobs]
        prefixes = [f"{system}:{board}:%" for system, board in self.fetched_boards]
        conn = psycopg2.connect(self._db_conn_str)
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE raw_job_postings
                    SET archived_at = now()
                    WHERE source = %s
                      AND archived_at IS NULL
                      AND job_id_external LIKE ANY(%s)
                      AND NOT (job_id_external = ANY(%s))
                    """,
                    (SOURCE, prefixes, listed),
                )
                logger.info("Archived %d career-page jobs that were taken down", cur.rowcount)
        finally:
            conn.close()
        return inserted
