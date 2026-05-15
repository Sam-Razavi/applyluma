"""Jobbsafari job scraper.

Jobbsafari has no public API, so this client scrapes their website
via their RSS feeds (which are publicly available).

RSS feed: https://www.jobbsafari.se/lediga-jobb/rss
"""
from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode

from job_scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

JOBBSAFARI_RSS_URL = "https://www.jobbsafari.se/lediga-jobb/rss"

DEFAULT_QUERIES: list[str] = [
    "python",
    "javascript",
    "typescript",
    "java",
    "backend",
    "frontend",
    "devops",
    "data",
    "mjukvaruutvecklare",
    "systemutvecklare",
]

DEFAULT_CITIES: list[str] = [
    "stockholm",
    "goteborg",
    "malmo",
    "remote",
]


class JobbsafariClient(BaseScraper):
    """Scrape Jobbsafari via RSS feeds."""

    SOURCE_NAME = "jobbsafari"

    def __init__(
        self,
        db_conn_str: str,
        queries: list[str] | None = None,
        cities: list[str] | None = None,
    ) -> None:
        super().__init__(db_conn_str)
        self._queries = queries or DEFAULT_QUERIES
        self._cities = cities or DEFAULT_CITIES
        self._session.headers.update({
            "Accept": "application/rss+xml, application/xml, text/xml",
        })

    def _fetch_raw(self) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for query in self._queries:
            for city in self._cities:
                params = {"q": query, "plats": city}
                url = f"{JOBBSAFARI_RSS_URL}?{urlencode(params)}"

                try:
                    resp = self._get(url)
                    items = self._parse_rss(resp.text)
                    for item in items:
                        link = item.get("url", "")
                        if link and link not in seen_urls:
                            seen_urls.add(link)
                            item["_query"] = query
                            item["_city"] = city
                            all_items.append(item)
                except Exception as exc:
                    logger.warning("Error fetching q=%s city=%s: %s", query, city, exc)

                time.sleep(0.3)

        logger.info("Fetched %d unique Jobbsafari items", len(all_items))
        return all_items

    def parse_response(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

        for item in raw:
            url = item.get("url", "")
            if not url:
                continue

            # Derive a stable external ID from the URL path
            job_id_external = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("/")[-1] or url[-40:])

            jobs.append(
                {
                    "job_id_external": job_id_external,
                    "title": item.get("title", ""),
                    "company": item.get("company", "Unknown"),
                    "location": item.get("location") or item.get("_city", "Sweden"),
                    "description": item.get("description", item.get("title", "")),
                    "url": url,
                    "salary_min": None,
                    "salary_max": None,
                    "employment_type": None,
                    "remote_allowed": "remote" in (item.get("_city") or "").lower(),
                    "raw_data": {
                        "source": "jobbsafari",
                        "pub_date": item.get("pub_date"),
                        "query": item.get("_query"),
                        "city": item.get("_city"),
                    },
                }
            )

        return jobs

    # ------------------------------------------------------------------
    # RSS parsing helper
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_rss(xml_text: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("RSS parse error: %s", exc)
            return items

        ns = {"media": "http://search.yahoo.com/mrss/"}

        for item_el in root.iter("item"):
            def text(tag: str) -> str:
                el = item_el.find(tag)
                return (el.text or "").strip() if el is not None else ""

            title = text("title")
            link = text("link")
            description = re.sub(r"<[^>]+>", " ", text("description")).strip()
            pub_date = text("pubDate")

            # Try to extract company from title pattern "Job Title - Company"
            company = ""
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                company = parts[-1].strip()
                title = parts[0].strip()

            # Try to extract location from the description or title
            location = ""
            loc_match = re.search(r"\b(Stockholm|Gothenburg|Malmö|Göteborg|Remote|Sverige)\b", description, re.IGNORECASE)
            if loc_match:
                location = loc_match.group(0)

            items.append(
                {
                    "title": title,
                    "company": company,
                    "url": link,
                    "description": description,
                    "location": location,
                    "pub_date": pub_date,
                }
            )

        return items
