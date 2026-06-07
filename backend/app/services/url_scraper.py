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
    "User-Agent": "Mozilla/5.0 (compatible; ApplyLuma/1.0; +https://applyluma.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_MAX_CHARS = 6000

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
    company_name = _meta(soup, "og:site_name", "author")
    description = _body_text(soup)

    return {
        "job_title": job_title[:200],
        "company_name": company_name[:200],
        "description": description[:_MAX_CHARS],
        "url": url,
    }


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
        "- company_name: hiring company (string, empty if not found)\n"
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

    raw = _heuristic_extract(html, url)

    try:
        return _openai_clean(raw)
    except Exception:
        return raw
