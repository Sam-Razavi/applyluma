"""Repair of text whose UTF-8 bytes were read as Latin-1 (seen in RemoteOK data)."""

from __future__ import annotations

import pytest

from app.services.job_scrapers.remoteok import RemoteOKClient
from app.services.job_scrapers.text_repair import fix_mojibake


def _damage(text: str) -> str:
    return text.encode("utf-8").decode("latin-1")


@pytest.mark.parametrize(
    "clean",
    [
        "Senior Software Engineer — Kubernetes Control Plane",
        "Sotheby’s",
        "ML Inference Engineer – Terminal-Bench",
        "Développeur à Montréal",
        "Rocket 🚀 team",
    ],
)
def test_damaged_text_is_restored(clean: str) -> None:
    assert _damage(clean) != clean
    assert fix_mojibake(_damage(clean)) == clean


@pytest.mark.parametrize(
    "text",
    [
        "Backend-utvecklare på Göteborgs Stad, Malmö och Åre",
        "Plain ASCII title (C#/.NET)",
        "Café — already correct ’ text 🚀",
        "",
    ],
)
def test_correct_text_is_left_alone(text: str) -> None:
    assert fix_mojibake(text) == text


def test_mixed_text_repairs_only_the_damaged_part() -> None:
    assert fix_mojibake("Göteborg " + _damage("— remote")) == "Göteborg — remote"


def test_none_becomes_empty() -> None:
    assert fix_mojibake(None) == ""


def test_remoteok_parse_repairs_title_company_and_description() -> None:
    client = RemoteOKClient(db_conn_str="postgresql://unused")
    jobs = client.parse_response(
        [
            {"legal": "notice"},
            {
                "id": 1,
                "position": _damage("Engineer — Platform"),
                "company": _damage("Sotheby’s"),
                "location": "Worldwide",
                "description": "<p>" + _damage("We’re hiring") + "</p>",
                "url": "https://remoteok.com/1",
            },
        ]
    )
    assert jobs[0]["title"] == "Engineer — Platform"
    assert jobs[0]["company"] == "Sotheby’s"
    assert jobs[0]["description"] == "We’re hiring"
