"""The decision rules: requirement judgements in, recommendation out.

Pure and deterministic. This is the table in thesis/DESIGN.md section 5; any
change bumps RULES_VERSION and gets an entry in thesis/DESIGN_LOG.md.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

RULES_VERSION = "1"

HIGH = "high_priority"
CONSIDER = "consider"
LOW = "low_priority"

# The flag is raised when this share of the mandatory requirements could not
# be judged from the CV.
LIMITED_INFORMATION_SHARE = 1 / 3


@dataclass(frozen=True)
class Decision:
    recommendation: str
    rule: str
    reason: str
    limited_information: bool
    mandatory_total: int
    mandatory_met: int
    mandatory_not_met: int
    mandatory_unknown: int


def decide(requirements: Iterable[Mapping[str, Any]]) -> Decision:
    """Apply the rules to judged requirements (after the quote check).

    Only mandatory requirements decide. Preferred and unclear ones are shown
    to the user but do not change the recommendation.
    """
    mandatory = [r for r in requirements if r.get("importance") == "mandatory"]
    total = len(mandatory)
    met = sum(1 for r in mandatory if r.get("status") == "met")
    not_met = sum(1 for r in mandatory if r.get("status") == "not_met")
    unknown = sum(1 for r in mandatory if r.get("status") == "not_enough_information")

    limited = total == 0 or unknown / total >= LIMITED_INFORMATION_SHARE

    if not_met > 0:
        recommendation, rule = LOW, "R1"
        reason = (
            f"{not_met} of {total} mandatory requirements "
            f"{'is' if not_met == 1 else 'are'} not met."
        )
    elif total > 0 and met == total:
        recommendation, rule = HIGH, "R2"
        reason = f"All {total} mandatory requirements are met."
    elif total == 0:
        recommendation, rule = CONSIDER, "R3"
        reason = "The ad does not state which requirements are mandatory."
    else:
        recommendation, rule = CONSIDER, "R3"
        reason = (
            f"{met} of {total} mandatory requirements are met; none is clearly "
            "not met, but the rest are only partly met or cannot be judged from the CV."
        )

    return Decision(
        recommendation=recommendation,
        rule=rule,
        reason=reason,
        limited_information=limited,
        mandatory_total=total,
        mandatory_met=met,
        mandatory_not_met=not_met,
        mandatory_unknown=unknown,
    )
