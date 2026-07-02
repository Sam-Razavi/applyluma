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

# ---------------------------------------------------------------------------
# _extract_json_ld
# ---------------------------------------------------------------------------

def test_extract_json_ld_finds_job_posting() -> None:
    import json
    from bs4 import BeautifulSoup

    data = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Backend Engineer",
        "hiringOrganization": {"@type": "Organization", "name": "Acme Inc"},
        "description": "We are looking for a Python developer.",
    }
    html = f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._extract_json_ld(soup)
    assert result is not None
    assert result["job_title"] == "Backend Engineer"
    assert result["company_name"] == "Acme Inc"
    assert "Python" in result["description"]


def test_extract_json_ld_strips_html_from_description() -> None:
    import json
    from bs4 import BeautifulSoup

    data = {
        "@type": "JobPosting",
        "title": "Dev",
        "hiringOrganization": {"name": "Corp"},
        "description": "<p>Great <strong>role</strong> for you.</p>",
    }
    html = f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._extract_json_ld(soup)
    assert result is not None
    assert "<p>" not in result["description"]
    assert "Great" in result["description"]


def test_extract_json_ld_returns_none_when_no_job_posting() -> None:
    from bs4 import BeautifulSoup

    html = '<html><head><script type="application/ld+json">{"@type": "WebPage"}</script></head></html>'
    soup = BeautifulSoup(html, "html.parser")
    assert url_scraper._extract_json_ld(soup) is None


def test_extract_json_ld_returns_none_on_empty_page() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert url_scraper._extract_json_ld(soup) is None


# ---------------------------------------------------------------------------
# _is_login_wall
# ---------------------------------------------------------------------------

def test_is_login_wall_detects_short_body() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><body>Sign in</body></html>", "html.parser")
    assert url_scraper._is_login_wall(soup) is True


def test_is_login_wall_detects_login_signal_text() -> None:
    from bs4 import BeautifulSoup

    long_filler = "x" * 500
    html = f"<html><body>{long_filler} Please sign in to view this job posting.</body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert url_scraper._is_login_wall(soup) is True


def test_is_login_wall_returns_false_for_real_page() -> None:
    from bs4 import BeautifulSoup

    content = "We are hiring a Python developer. " * 20
    html = f"<html><body><article>{content}</article></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert url_scraper._is_login_wall(soup) is False


# ---------------------------------------------------------------------------
# _site_specific_extract
# ---------------------------------------------------------------------------

def test_site_specific_extract_returns_none_for_unknown_domain() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><body><h1>Job</h1></body></html>", "html.parser")
    result = url_scraper._site_specific_extract(soup, "https://unknown-site.com/job/1")
    assert result is None


def test_site_specific_extract_indeed() -> None:
    from bs4 import BeautifulSoup

    html = """<html><body>
        <h1 data-testid="jobsearch-JobInfoHeader-title">Data Scientist</h1>
        <div data-testid="inlineHeader-companyName">TechCorp</div>
        <div id="jobDescriptionText">Analyse large datasets using Python and SQL.</div>
    </body></html>"""
    soup = BeautifulSoup(html, "html.parser")
    result = url_scraper._site_specific_extract(soup, "https://se.indeed.com/viewjob?jk=abc")
    assert result is not None
    assert result["job_title"] == "Data Scientist"
    assert result["company_name"] == "TechCorp"
    assert "Python" in result["description"]


def test_site_specific_extract_returns_none_when_no_match() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><body><p>Nothing useful here</p></body></html>", "html.parser")
    result = url_scraper._site_specific_extract(soup, "https://www.indeed.com/viewjob?jk=abc")
    assert result is None


# ---------------------------------------------------------------------------
# _get_site_key
# ---------------------------------------------------------------------------

def test_get_site_key_exact_match() -> None:
    assert url_scraper._get_site_key("linkedin.com") == "linkedin.com"


def test_get_site_key_subdomain_match() -> None:
    assert url_scraper._get_site_key("www.linkedin.com") == "linkedin.com"
    assert url_scraper._get_site_key("se.indeed.com") == "indeed.com"


def test_get_site_key_no_match() -> None:
    assert url_scraper._get_site_key("randomsite.org") is None


# ---------------------------------------------------------------------------
# scrape_job_url — login wall raises ValueError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_job_url_raises_on_login_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace as NS

    html = "<html><body>Please sign in to view this job.</body></html>"
    fake_response = NS(text=html, raise_for_status=lambda: None)

    class _FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): return fake_response

    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("93.184.216.34"))
    monkeypatch.setattr(url_scraper.httpx, "AsyncClient", lambda **kw: _FakeAsyncClient())

    with pytest.raises(ValueError, match="login"):
        await url_scraper.scrape_job_url("https://linkedin.com/jobs/view/123")


@pytest.mark.asyncio
async def test_scrape_job_url_prefers_json_ld(monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from types import SimpleNamespace as NS

    ld = {
        "@type": "JobPosting",
        "title": "ML Engineer",
        "hiringOrganization": {"name": "DeepMind"},
        "description": "Work on cutting-edge AI research." * 5,
    }
    body_text = "x" * 500
    html = f"""<html><head>
        <script type="application/ld+json">{json.dumps(ld)}</script>
    </head><body>{body_text}</body></html>"""
    fake_response = NS(text=html, raise_for_status=lambda: None)

    class _FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): return fake_response

    monkeypatch.setattr(url_scraper.socket, "getaddrinfo", lambda *a: _addr("93.184.216.34"))
    monkeypatch.setattr(url_scraper.httpx, "AsyncClient", lambda **kw: _FakeAsyncClient())

    result = await url_scraper.scrape_job_url("https://example.com/jobs/ml-engineer")
    assert result["job_title"] == "ML Engineer"
    assert result["company_name"] == "DeepMind"


# ---------------------------------------------------------------------------
# scrape_job_url (async) — original test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_job_url_returns_extracted_data(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace as NS

    body_content = "We need a Python developer with 5 years of experience. " * 10
    html = (
        "<html><head><title>Backend Engineer at Acme</title>"
        '<meta property="og:site_name" content="Acme"/></head>'
        f"<body><main>{body_content}</main></body></html>"
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
