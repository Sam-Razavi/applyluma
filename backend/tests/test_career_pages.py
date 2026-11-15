"""Career-page scraper: each feed format, the Sweden rule, failure handling."""
from __future__ import annotations

from typing import Any

import pytest
import requests

from app.services.job_scrapers.career_pages import CareerPagesClient, place_in_scope

DSN = "postgresql://u:p@localhost/db"

GREENHOUSE = {
    "jobs": [
        {"id": 1, "title": "Backend Engineer", "company_name": "Mentimeter", "location": {"name": "Stockholm"},
         "offices": [], "absolute_url": "https://job-boards.eu.greenhouse.io/mentimeter/jobs/1",
         "content": "&lt;p&gt;Build &lt;b&gt;APIs&lt;/b&gt;&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;",
         "application_deadline": None},
        {"id": 2, "title": "Account Executive", "company_name": "Mentimeter", "location": {"name": "Toronto"},
         "offices": [{"name": "Toronto", "location": "Toronto, Ontario, Canada"}],
         "absolute_url": "https://job-boards.eu.greenhouse.io/mentimeter/jobs/2", "content": "x"},
        {"id": 3, "title": "Support Engineer", "company_name": "Mentimeter", "location": {"name": "Germany (Remote)"},
         "offices": [], "absolute_url": "https://job-boards.eu.greenhouse.io/mentimeter/jobs/3", "content": "x"},
    ]
}

LEVER = [
    {"id": "a", "text": "IT Consultant", "hostedUrl": "https://jobs.lever.co/netlight/a", "country": "SE",
     "workplaceType": "onsite", "categories": {"location": "Stockholm", "commitment": "Full time"},
     "descriptionPlain": "About the role", "lists": [{"text": "You have", "content": "<li>SQL</li>"}],
     "additionalPlain": "Apply now"},
    {"id": "b", "text": "IT Consultant", "hostedUrl": "https://jobs.lever.co/netlight/b", "country": "NL",
     "workplaceType": "onsite", "categories": {"location": "Amsterdam"}, "descriptionPlain": "x"},
]

ASHBY = {
    "jobs": [
        {"id": "u1", "title": "Data Engineer", "location": "London", "isRemote": False, "isListed": True,
         "secondaryLocations": [{"location": "Stockholm"}], "jobUrl": "https://jobs.ashbyhq.com/legora/u1",
         "descriptionPlain": "Pipelines", "employmentType": "FullTime"},
        {"id": "u2", "title": "Hidden", "location": "Stockholm", "isListed": False,
         "jobUrl": "https://jobs.ashbyhq.com/legora/u2", "descriptionPlain": "x"},
        {"id": "u3", "title": "Remote Engineer", "location": "Remote, EMEA", "isRemote": True, "isListed": True,
         "jobUrl": "https://jobs.ashbyhq.com/legora/u3", "descriptionPlain": "x"},
    ]
}

TEAMTAILOR = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations"><channel><title>Anyfin</title>
<item><title>Backend Developer</title><description>&lt;p&gt;Kotlin &amp;amp; Postgres&lt;/p&gt;</description>
<link>https://career.anyfin.com/jobs/1-backend</link><remoteStatus>none</remoteStatus><guid>g-1</guid>
<tt:locations><tt:location><tt:city>Stockholm</tt:city><tt:country>Sweden</tt:country></tt:location></tt:locations></item>
<item><title>Sales Rep</title><description>x</description><link>https://career.anyfin.com/jobs/2-sales</link>
<remoteStatus>none</remoteStatus><guid>g-2</guid>
<tt:locations><tt:location><tt:city>Helsinki</tt:city><tt:country>Finland</tt:country></tt:location></tt:locations></item>
</channel></rss>"""

BOARDS = [
    ("Mentimeter", "greenhouse", "mentimeter"), ("Netlight", "lever", "netlight"),
    ("Legora", "ashby", "legora"), ("Anyfin", "teamtailor", "anyfin"),
]


class _Resp:
    def __init__(self, data: Any) -> None:
        self._data = data
        self.text = data if isinstance(data, str) else ""

    def json(self) -> Any:
        return self._data


def _client(monkeypatch: pytest.MonkeyPatch, answers: dict[str, Any]) -> CareerPagesClient:
    from app.services.job_scrapers import career_pages

    monkeypatch.setattr(career_pages, "PAUSE_SECONDS", 0)
    client = CareerPagesClient(DSN, boards=BOARDS)

    def fake_get(url: str, **kwargs: Any) -> _Resp:
        for key, value in answers.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return _Resp(value)
        raise AssertionError(f"unexpected request {url}")

    monkeypatch.setattr(client, "_get", fake_get)
    return client


ALL = {"greenhouse.io": GREENHOUSE, "lever.co": LEVER, "ashbyhq.com": ASHBY, "teamtailor.com": TEAMTAILOR}


def test_only_jobs_doable_from_sweden_are_kept_from_every_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = {j["job_id_external"]: j for j in _client(monkeypatch, ALL).fetch_jobs()}

    assert set(jobs) == {
        "greenhouse:mentimeter:1", "lever:netlight:a", "ashby:legora:u1", "ashby:legora:u3",
        "teamtailor:anyfin:g-1",
    }
    greenhouse = jobs["greenhouse:mentimeter:1"]
    assert greenhouse["company"] == "Mentimeter" and greenhouse["location"] == "Stockholm"
    assert "<" not in greenhouse["description"] and "• Python" in greenhouse["description"]
    lever = jobs["lever:netlight:a"]
    assert lever["company"] == "Netlight" and lever["employment_type"] == "Full time"
    assert "About the role" in lever["description"] and "SQL" in lever["description"]
    # Listed under London, but it can be done from Stockholm: shown as Stockholm.
    assert jobs["ashby:legora:u1"]["location"] == "Stockholm"
    assert jobs["ashby:legora:u3"]["remote_allowed"] is True
    teamtailor = jobs["teamtailor:anyfin:g-1"]
    assert teamtailor["location"] == "Stockholm" and teamtailor["url"] == "https://career.anyfin.com/jobs/1-backend"
    assert teamtailor["description"] == "Kotlin & Postgres"


@pytest.mark.parametrize(
    ("primary", "others", "remote", "expected"),
    [
        ("Stockholm", [], False, "Stockholm"),
        ("London", ["Göteborg, Sweden"], False, "Göteborg, Sweden"),
        ("Germany (Remote)", [], True, None),  # remote, but only within Germany
        ("Remote - Europe", [], True, "Remote - Europe"),
        ("Remote - Europe", [], False, None),
        ("Lundby Park, Oslo", [], False, None),  # "Lund" inside another word is not Lund
        ("", [], False, None),
    ],
)
def test_place_in_scope(primary: str, others: list[str], remote: bool, expected: str | None) -> None:
    assert place_in_scope(primary, others, remote) == expected


def test_one_board_failing_is_tolerated_and_its_jobs_are_not_read_as_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch, {**ALL, "lever.co": requests.Timeout("slow")})
    jobs = client.fetch_jobs()
    assert not any(j["job_id_external"].startswith("lever") for j in jobs)
    assert ("lever", "netlight") not in client.fetched_boards
    assert ("greenhouse", "mentimeter") in client.fetched_boards


def test_a_feed_that_cannot_be_read_is_dropped_from_the_fetched_boards(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, {**ALL, "teamtailor.com": "<!DOCTYPE rss [<!ENTITY a 'b'>]><rss/>"})
    jobs = client.fetch_jobs()
    assert ("teamtailor", "anyfin") not in client.fetched_boards
    assert len(jobs) == 4


def test_every_board_failing_fails_the_source(monkeypatch: pytest.MonkeyPatch) -> None:
    down = requests.ConnectionError("down")
    client = _client(monkeypatch, dict.fromkeys(ALL, down))
    with pytest.raises(requests.ConnectionError):
        client.fetch_jobs()


def test_the_employer_list_is_well_formed() -> None:
    from app.services.job_scrapers.career_boards import BOARDS as LISTED
    from app.services.job_scrapers.career_pages import FEEDS

    assert len({(system, board) for _, system, board in LISTED}) == len(LISTED)
    assert all(system in FEEDS and name and board for name, system, board in LISTED)
