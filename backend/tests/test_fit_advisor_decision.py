"""The decision rules of the fit advisor (pure; thesis/DESIGN.md section 5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.fit_advisor.decision import CONSIDER, HIGH, LOW, decide


def req(importance: str, status: str) -> dict[str, str]:
    return {"importance": importance, "status": status}


def test_all_mandatory_met_is_high_priority() -> None:
    decision = decide([req("mandatory", "met"), req("mandatory", "met"), req("mandatory", "met")])

    assert decision.recommendation == HIGH
    assert decision.rule == "R2"
    assert decision.limited_information is False


def test_one_unmet_mandatory_is_low_priority_whatever_else_is_met() -> None:
    decision = decide(
        [req("mandatory", "met"), req("mandatory", "met"), req("mandatory", "not_met")]
        + [req("preferred", "met")] * 5
    )

    assert decision.recommendation == LOW
    assert decision.rule == "R1"
    assert decision.mandatory_not_met == 1


@pytest.mark.parametrize("status", ["partly_met", "not_enough_information"])
def test_a_mandatory_requirement_neither_met_nor_unmet_is_consider(status: str) -> None:
    decision = decide([req("mandatory", "met"), req("mandatory", status), req("mandatory", "met")])

    assert decision.recommendation == CONSIDER
    assert decision.rule == "R3"


def test_not_met_wins_over_missing_information() -> None:
    decision = decide([req("mandatory", "not_enough_information"), req("mandatory", "not_met")])

    assert decision.recommendation == LOW


def test_preferred_and_unclear_requirements_never_change_the_result() -> None:
    mandatory = [req("mandatory", "met"), req("mandatory", "met")]

    with_unmet_extras = decide(
        mandatory + [req("preferred", "not_met")] * 4 + [req("unclear", "not_met")] * 4
    )

    assert with_unmet_extras.recommendation == HIGH
    assert with_unmet_extras.mandatory_total == 2


def test_ad_without_mandatory_requirements_is_consider_with_limited_information() -> None:
    for requirements in ([], [req("unclear", "met"), req("preferred", "met")]):
        decision = decide(requirements)

        assert decision.recommendation == CONSIDER
        assert decision.limited_information is True
        assert decision.mandatory_total == 0


def test_limited_information_flag_starts_at_a_third_of_mandatory_unknown() -> None:
    one_of_three = decide(
        [req("mandatory", "met"), req("mandatory", "met"), req("mandatory", "not_enough_information")]
    )
    one_of_four = decide(
        [req("mandatory", "met")] * 3 + [req("mandatory", "not_enough_information")]
    )

    assert one_of_three.limited_information is True
    assert one_of_four.limited_information is False
    # The flag informs; it does not change the recommendation.
    assert one_of_three.recommendation == one_of_four.recommendation == CONSIDER


def test_reason_names_the_counts() -> None:
    assert decide([req("mandatory", "met")] * 3).reason == "All 3 mandatory requirements are met."
    assert decide([req("mandatory", "met"), req("mandatory", "not_met")]).reason == (
        "1 of 2 mandatory requirements is not met."
    )
