"""Tests for SSRF protection in app/services/url_scraper.py."""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import url_scraper


# ---------------------------------------------------------------------------
# _validate_url — scheme and hostname checks (no DNS needed)
# ---------------------------------------------------------------------------

def test_validate_url_blocks_ftp_scheme() -> None:
    with pytest.raises(ValueError, match="scheme"):
        url_scraper._validate_url("ftp://example.com/job")


def test_validate_url_blocks_javascript_scheme() -> None:
    with pytest.raises(ValueError, match="scheme"):
        url_scraper._validate_url("javascript:alert(1)")


def test_validate_url_blocks_empty_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    # getaddrinfo is never reached when there's no hostname
    with pytest.raises(ValueError, match="hostname"):
        url_scraper._validate_url("https:///path/to/job")


def test_validate_url_allows_http_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    # DNS resolves to a public IP — should pass
    monkeypatch.setattr(
        url_scraper.socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0))],
    )
    url_scraper._validate_url("http://example.com/job")  # Must not raise


# ---------------------------------------------------------------------------
# _validate_url — IP blocking (DNS monkeypatched)
# ---------------------------------------------------------------------------

def _addr(ip: str) -> list:
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


def test_validate_url_blocks_loopback_127(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("127.0.0.1"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://internal.example.com/job")


def test_validate_url_blocks_rfc1918_10(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("10.0.0.1"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://internal.example.com/job")


def test_validate_url_blocks_rfc1918_172_16(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("172.16.0.5"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://internal.example.com/job")


def test_validate_url_blocks_rfc1918_192_168(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("192.168.1.100"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://internal.example.com/job")


def test_validate_url_blocks_link_local_169_254(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("169.254.169.254"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://metadata.internal/latest/meta-data")


def test_validate_url_blocks_shared_address_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("100.64.0.1"))
    with pytest.raises(ValueError, match="private"):
        url_scraper._validate_url("https://carrier.internal/job")


def test_validate_url_allows_public_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("93.184.216.34"))
    url_scraper._validate_url("https://example.com/job")  # Must not raise


def test_validate_url_dns_failure_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """DNS resolution failure is allowed — httpx will surface the network error."""
    monkeypatch.setattr(
        url_scraper.socket,
        "getaddrinfo",
        lambda *a: (_ for _ in ()).throw(socket.gaierror("Name not resolved")),
    )
    url_scraper._validate_url("https://nonexistent.example.invalid/job")  # Must not raise


# ---------------------------------------------------------------------------
# _meta helper
# ---------------------------------------------------------------------------

def test_meta_extracts_og_title() -> None:
    from bs4 import BeautifulSoup
    html = '<html><head><meta property="og:title" content="Senior Dev at Acme"/></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert url_scraper._meta(soup, "og:title") == "Senior Dev at Acme"


def test_meta_falls_back_to_name_attr() -> None:
    from bs4 import BeautifulSoup
    html = '<html><head><meta name="author" content="Acme Corp"/></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert url_scraper._meta(soup, "og:site_name", "author") == "Acme Corp"


def test_meta_returns_empty_when_not_found() -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert url_scraper._meta(soup, "og:title") == ""


# ---------------------------------------------------------------------------
# _body_text helper
# ---------------------------------------------------------------------------

def test_body_text_finds_job_description_class() -> None:
    from bs4 import BeautifulSoup
    html = '<html><body><div class="job-description">We are hiring a backend developer.</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._body_text(soup)
    assert "backend developer" in result


def test_body_text_falls_back_to_main_tag() -> None:
    from bs4 import BeautifulSoup
    html = "<html><body><main>Main content for this job.</main></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._body_text(soup)
    assert "Main content" in result


def test_body_text_falls_back_to_article_tag() -> None:
    from bs4 import BeautifulSoup
    html = "<html><body><article>Article content here.</article></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._body_text(soup)
    assert "Article content" in result


def test_body_text_falls_back_to_body() -> None:
    from bs4 import BeautifulSoup
    html = "<html><body>Plain body text only.</body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._body_text(soup)
    assert "Plain body text" in result


# ---------------------------------------------------------------------------
# _heuristic_extract
# ---------------------------------------------------------------------------

def test_heuristic_extract_returns_structured_dict() -> None:
    html = """<html><head>
        <title>Senior Engineer at Acme</title>
        <meta property="og:site_name" content="Acme Corp"/>
    </head><body>
        <h1>Senior Engineer</h1>
        <article>We are looking for a senior backend engineer with Python experience.</article>
    </body></html>"""
    result = url_scraper._heuristic_extract(html, "https://acme.com/jobs/1")
    assert result["url"] == "https://acme.com/jobs/1"
    assert result["job_title"]
    assert "description" in result
    assert "company_name" in result


# ---------------------------------------------------------------------------
# _openai_clean
# ---------------------------------------------------------------------------

def test_openai_clean_returns_cleaned_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from types import SimpleNamespace

    fake_content = json.dumps({
        "job_title": "Software Engineer",
        "company_name": "Acme Corp",
        "description": "We want a skilled backend developer.",
    })
    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=fake_content))]
    )

    class _FakeOpenAI:
        def __init__(self, **kw):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: fake_completion)
            )

    monkeypatch.setattr(url_scraper, "OpenAI", _FakeOpenAI)

    raw = {
        "url": "https://example.com/job",
        "job_title": "dev",
        "company_name": "co",
        "description": "some text",
    }
    result = url_scraper._openai_clean(raw)
    assert result["job_title"] == "Software Engineer"
    assert result["company_name"] == "Acme Corp"
    assert result["url"] == "https://example.com/job"


# ---------------------------------------------------------------------------
# scrape_job_url (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_job_url_returns_extracted_data(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace as NS

    html = (
        "<html><head><title>Backend Engineer at Acme</title>"
        '<meta property="og:site_name" content="Acme"/></head>'
        "<body><main>We need a Python developer.</main></body></html>"
    )
    fake_response = NS(text=html, raise_for_status=lambda: None)

    class _FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): return fake_response

    monkeypatch.setattr(
        url_scraper.socket,
        "getaddrinfo",
        lambda *a: _addr("93.184.216.34"),
    )
    monkeypatch.setattr(url_scraper.httpx, "AsyncClient", lambda **kw: _FakeAsyncClient())
    monkeypatch.setattr(url_scraper, "_openai_clean", lambda raw: raw)

    result = await url_scraper.scrape_job_url("https://example.com/job/1")
    assert result["url"] == "https://example.com/job/1"
    assert "description" in result
