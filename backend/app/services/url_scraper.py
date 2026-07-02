from __future__ import annotations

import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from app.core.config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,sv;q=0.8",
}

_MAX_CHARS = 12_000

# RFC-1918 / loopback / link-local / metadata ranges blocked for SSRF prevention.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",  # link-local / AWS metadata endpoint
        "100.64.0.0/10",   # shared address space (RFC 6598)
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
]

# Per-site CSS selectors, mirroring the browser extension content scripts.
# Keys are matched against the URL hostname (exact or suffix).
_SITE_SELECTORS: dict[str, dict[str, list[str]]] = {
    "linkedin.com": {
        "title": [
            "h1.t-24",
            "h1[class*='job-title']",
            ".job-details-jobs-unified-top-card__job-title h1",
            ".jobs-unified-top-card__job-title",
        ],
        "company": [
            ".job-details-jobs-unified-top-card__company-name a",
            ".job-details-jobs-unified-top-card__company-name",
            ".jobs-unified-top-card__company-name a",
            ".jobs-unified-top-card__company-name",
            "[data-test-id='job-detail-company-name']",
        ],
        "description": [
            ".jobs-description__content",
            "#job-details",
            ".jobs-box__html-content",
            ".description__text",
        ],
    },
    "indeed.com": {
        "title": [
            "[data-testid='jobsearch-JobInfoHeader-title']",
            "h1.jobsearch-JobInfoHeader-title",
            "h1[class*='JobInfoHeader']",
            "h1",
        ],
        "company": [
            "[data-testid='inlineHeader-companyName']",
            ".jobsearch-InlineCompanyRating-companyHeader",
            "[data-company-name='true']",
        ],
        "description": [
            "#jobDescriptionText",
            "[data-testid='jobDescriptionText']",
            ".jobsearch-jobDescriptionText",
        ],
    },
    "glassdoor.com": {
        "title": [
            "[data-test='job-title']",
            ".job-title",
            "h1[class*='title']",
            "h1",
        ],
        "company": [
            "[data-test='employer-name']",
            ".employer-name",
            "[class*='EmployerProfile_employerName']",
        ],
        "description": [
            "[data-test='jobDescriptionContent']",
            ".jobDescriptionContent",
            "[class*='JobDetails_jobDescription']",
            "#JobDescriptionContainer",
        ],
    },
    "arbetsformedlingen.se": {
        "title": [
            "[class*='JobAd_title']",
            "[class*='job-title']",
            "h1[class*='heading']",
            "h1",
        ],
        "company": [
            "[class*='JobAd_employer']",
            "[class*='employer-name']",
            "[class*='company-name']",
            "[data-testid='employer-name']",
        ],
        "description": [
            "[class*='JobAd_description']",
            "[class*='job-description']",
            "[class*='JobDescription']",
            "article",
        ],
    },
}

# Phrases that indicate an authentication wall rather than a job page.
_LOGIN_SIGNALS = [
    "sign in to view",
    "log in to view",
    "please sign in",
    "join linkedin",
    "sign in to apply",
    "create an account",
    "authwall",
    "please log in",
]


def _validate_url(url: str) -> None:
    """Block non-http(s) schemes and URLs that resolve to private infrastructure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme {parsed.scheme!r} is not allowed")
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("URL has no hostname")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return  # Let httpx surface the network error with a generic message
    for *_, sockaddr in infos:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or any(ip in net for net in _BLOCKED_NETWORKS)
        ):
            raise ValueError("URL resolves to a private or reserved address")


def _meta(soup: BeautifulSoup, *attrs: str) -> str:
    for attr in attrs:
        tag = soup.find("meta", attrs={"property": attr}) or soup.find(
            "meta", attrs={"name": attr}
        )
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return ""


def _body_text(soup: BeautifulSoup) -> str:
    for selector in [
        {"class": re.compile(r"job[_-]?desc", re.I)},
        {"class": re.compile(r"description", re.I)},
        {"id": re.compile(r"job[_-]?desc", re.I)},
    ]:
        el = soup.find(attrs=selector)
        if el:
            return el.get_text(separator="\n", strip=True)

    for tag_name in ["article", "main"]:
        el = soup.find(tag_name)
        if el:
            return el.get_text(separator="\n", strip=True)

    body = soup.find("body")
    return body.get_text(separator="\n", strip=True) if body else ""


def _heuristic_extract(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    job_title = (
        _meta(soup, "og:title")
        or (h1.get_text(strip=True) if h1 else "")
        or (soup.title.get_text(strip=True) if soup.title else "")
    )
    # Avoid using og:site_name as company — it returns the platform name (e.g. "LinkedIn"),
    # not the hiring company. Fall back to "author" only, or leave empty for OpenAI to fill.
    company_name = _meta(soup, "author")
    description = _body_text(soup)

    return {
        "job_title": job_title[:200],
        "company_name": company_name[:200],
        "description": description[:_MAX_CHARS],
        "url": url,
    }


def _extract_json_ld(soup: BeautifulSoup) -> dict[str, str] | None:
    """Extract JobPosting schema.org structured data from JSON-LD script tags."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                continue
            title = str(item.get("title", "")).strip()
            hiring_org = item.get("hiringOrganization", {})
            company = str(hiring_org.get("name", "")).strip() if isinstance(hiring_org, dict) else ""
            description = str(item.get("description", "")).strip()
            # Strip inline HTML that some sites embed in the description field.
            if description and "<" in description:
                description = BeautifulSoup(description, "html.parser").get_text(
                    separator="\n", strip=True
                )
            if title:
                return {
                    "job_title": title[:200],
                    "company_name": company[:200],
                    "description": description[:_MAX_CHARS],
                }
    return None


def _get_site_key(hostname: str) -> str | None:
    """Return the matching key in _SITE_SELECTORS for the given hostname."""
    for site in _SITE_SELECTORS:
        if hostname == site or hostname.endswith("." + site):
            return site
    return None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for sel in selectors:
        try:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if text:
                    return text
        except Exception:
            continue
    return ""


def _site_specific_extract(soup: BeautifulSoup, url: str) -> dict[str, str] | None:
    """Use per-site CSS selectors to extract structured job data."""
    hostname = urlparse(url).hostname or ""
    site_key = _get_site_key(hostname)
    if not site_key:
        return None
    selectors = _SITE_SELECTORS[site_key]
    title = _first_text(soup, selectors["title"])
    company = _first_text(soup, selectors["company"])
    description = _first_text(soup, selectors["description"])
    if title or description:
        return {
            "job_title": title[:200],
            "company_name": company[:200],
            "description": description[:_MAX_CHARS],
        }
    return None


def _is_login_wall(soup: BeautifulSoup) -> bool:
    """Return True if the page appears to be an authentication wall."""
    body = soup.find("body")
    if body and len(body.get_text(strip=True)) < 200:
        return True
    page_text = soup.get_text(separator=" ").lower()
    return any(signal in page_text for signal in _LOGIN_SIGNALS)


def _openai_clean(raw: dict[str, str]) -> dict[str, str]:
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
    prompt = (
        "You are a job posting parser. Extract structured information from this page.\n\n"
        f"URL: {raw['url']}\n"
        f"Detected title: {raw['job_title']}\n"
        f"Detected company: {raw['company_name']}\n"
        f"Page text (truncated):\n{raw['description'][:_MAX_CHARS]}\n\n"
        "Return JSON with:\n"
        "- job_title: clean job title (string)\n"
        "- company_name: hiring company name — never the platform (e.g. never 'LinkedIn', 'Indeed', 'Glassdoor') (string, empty if not found)\n"
        "- description: full job description text with requirements and responsibilities (string)"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content or "{}")
    return {
        "job_title": str(result.get("job_title", raw["job_title"]))[:200],
        "company_name": str(result.get("company_name", raw["company_name"]))[:200],
        "description": str(result.get("description", raw["description"])),
        "url": raw["url"],
    }


async def scrape_job_url(url: str) -> dict[str, str]:
    _validate_url(url)
    async with httpx.AsyncClient(
        headers=_HEADERS, follow_redirects=True, timeout=10
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    if _is_login_wall(soup):
        raise ValueError(
            "This page requires a login to view job details. "
            "Try using the browser extension while signed in, or paste the job description manually."
        )

    # 1. JSON-LD structured data — most reliable, no JS required
    json_ld = _extract_json_ld(soup)
    if json_ld and json_ld["job_title"] and json_ld["description"]:
        return {"url": url, **json_ld}

    # 2. Per-site CSS selectors (mirrors browser extension content scripts)
    site = _site_specific_extract(soup, url)
    if site and site["job_title"] and site["description"]:
        return {"url": url, **site}

    # 3. Generic heuristic fallback
    raw = _heuristic_extract(html, url)

    # 4. OpenAI cleanup / correction
    try:
        return _openai_clean(raw)
    except Exception:
        return raw
