"""The decision rules of the fit advisor (pure; thesis/DESIGN.md section 5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.fit_advisor.decision import CONSIDER, HIGH, LOW, decide


def req(importance: str, status: str, *, verified: bool | None = True) -> dict[str, object]:
    """A judged requirement. verified=None leaves out the ad-quote check entirely."""
    item: dict[str, object] = {"importance": importance, "status": status}
    if verified is not None:
        item["ad_quote_found"] = verified
    return item


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


# ---- rules version 2: requirements whose wording was not found in the ad ------


def test_an_invented_mandatory_requirement_cannot_make_it_low() -> None:
    """Scenario 11: an unmet requirement the ad does not contain."""
    decision = decide([req("mandatory", "met"), req("mandatory", "not_met", verified=False)])

    assert decision.recommendation == CONSIDER
    assert decision.rule == "R4"
    assert decision.mandatory_not_met == 0 and decision.mandatory_unverified == 1


@pytest.mark.parametrize("status", ["met", "partly_met", "not_enough_information", "not_met"])
def test_an_unverified_mandatory_requirement_blocks_high_whatever_its_status(status: str) -> None:
    """Scenario 12: verified matches plus one unverified requirement, even one judged met."""
    decision = decide([req("mandatory", "met")] * 3 + [req("mandatory", status, verified=False)])

    assert decision.recommendation == CONSIDER
    assert decision.rule == "R4"
    assert decision.limited_information is True
    assert decision.reason == (
        "The wording of 1 mandatory requirement could not be found in the ad, so it cannot be "
        "verified and the assessment cannot be firm. 3 of the 3 verified mandatory requirements are met."
    )


def test_a_verified_failure_is_low_even_beside_an_unverified_requirement() -> None:
    """Scenario 13."""
    decision = decide(
        [req("mandatory", "met"), req("mandatory", "not_met"), req("mandatory", "met", verified=False)]
    )

    assert decision.recommendation == LOW
    assert decision.rule == "R1"
    assert decision.reason == (
        "1 of 2 mandatory requirements is not met. "
        "The wording of 1 other mandatory requirement could not be found in the ad."
    )
    assert (decision.mandatory_total, decision.mandatory_not_met, decision.mandatory_unverified) == (2, 1, 1)


def test_only_unverified_mandatory_requirements_is_consider_with_limited_information() -> None:
    """Scenario 14."""
    decision = decide([req("mandatory", "met", verified=False), req("mandatory", "met", verified=False)])

    assert decision.recommendation == CONSIDER
    assert decision.rule == "R4"
    assert decision.limited_information is True
    assert decision.mandatory_total == 0 and decision.mandatory_unverified == 2
    assert decision.reason == (
        "The wording of 2 mandatory requirements could not be found in the ad, so they cannot be "
        "verified and the assessment cannot be firm."
    )


def test_an_unverified_preferred_requirement_does_not_take_away_high() -> None:
    """Scenario 15."""
    decision = decide(
        [req("mandatory", "met"), req("mandatory", "met"), req("preferred", "not_met", verified=False),
         req("unclear", "not_enough_information", verified=False)]
    )

    assert decision.recommendation == HIGH
    assert decision.rule == "R2"
    assert decision.mandatory_unverified == 0


def test_a_requirement_without_the_ad_check_counts_as_unverified() -> None:
    """Fails closed: missing verification metadata never gives a definitive priority."""
    assert decide([req("mandatory", "met", verified=None)] * 2).rule == "R4"
    assert decide([req("mandatory", "not_met", verified=None)]).recommendation == CONSIDER
    # Anything but a real True counts as unverified.
    assert decide([{"importance": "mandatory", "status": "met", "ad_quote_found": "yes"}]).rule == "R4"


def test_r4_raises_limited_information_below_the_one_third_share() -> None:
    """Scenario 17: one unverified of six is under a third, but R4 always flags it."""
    decision = decide([req("mandatory", "met")] * 5 + [req("mandatory", "met", verified=False)])

    assert decision.rule == "R4" and decision.limited_information is True


def test_counts_cover_verified_mandatory_requirements_only() -> None:
    """Scenario 17: the counts match the rule that fired."""
    decision = decide(
        [req("mandatory", "met"), req("mandatory", "partly_met"), req("mandatory", "not_enough_information"),
         req("mandatory", "not_met", verified=False), req("preferred", "met")]
    )

    assert (
        decision.mandatory_total, decision.mandatory_met, decision.mandatory_not_met,
        decision.mandatory_unknown, decision.mandatory_unverified,
    ) == (3, 1, 0, 1, 1)
    assert decision.recommendation == CONSIDER and decision.rule == "R4"


def test_low_beside_unverified_requirements_counts_them_as_unknown_for_the_flag() -> None:
    one_unverified_of_three = decide(
        [req("mandatory", "not_met"), req("mandatory", "met"), req("mandatory", "met", verified=False)]
    )
    one_unverified_of_four = decide(
        [req("mandatory", "not_met")] + [req("mandatory", "met")] * 2 + [req("mandatory", "met", verified=False)]
    )

    assert one_unverified_of_three.limited_information is True
    assert one_unverified_of_four.limited_information is False
