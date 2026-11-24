"""The decision rules: requirement judgements in, recommendation out.

Pure and deterministic. This is the table in thesis/DESIGN.md section 5; any
change bumps RULES_VERSION and gets an entry in thesis/DESIGN_LOG.md.

Version 2 (2026-11-24): a mandatory requirement counts only when its quote was
found in the ad. One whose quote was not found (or whose check is missing)
cannot make the result Low or High: it may be invented or misread, so it gives
Consider unless a verified requirement is clearly not met.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

RULES_VERSION = "2"

HIGH = "high_priority"
CONSIDER = "consider"
LOW = "low_priority"

# The flag is raised when this share of the mandatory requirements could not
# be judged, from the CV or (unverified ones) from the ad.
LIMITED_INFORMATION_SHARE = 1 / 3


@dataclass(frozen=True)
class Decision:
    recommendation: str
    rule: str
    reason: str
    limited_information: bool
    # Counts of the verified mandatory requirements: the ones the rules use.
    mandatory_total: int
    mandatory_met: int
    mandatory_not_met: int
    mandatory_unknown: int
    # Mandatory requirements whose wording was not found in the ad.
    mandatory_unverified: int = 0


def is_verified(requirement: Mapping[str, Any]) -> bool:
    """True only when the quote check found the requirement's wording in the ad.

    Fails closed: a requirement without the check counts as unverified, so
    missing metadata can never give a definitive priority. A found quote shows
    the words are in the ad, not that the requirement was read correctly (for
    example as mandatory rather than preferred); that is left to manual review.
    """
    return requirement.get("ad_quote_found") is True


def _requirements(n: int, kind: str = "mandatory") -> str:
    return f"{n} {kind} requirement{'' if n == 1 else 's'}"


def decide(requirements: Iterable[Mapping[str, Any]]) -> Decision:
    """Apply the rules to judged requirements (after both quote checks).

    Only mandatory requirements decide. Preferred and unclear ones are shown
    to the user but do not change the recommendation. In order:

    R1  a verified mandatory requirement is not_met       -> Low Priority
    R4  otherwise, any unverified mandatory requirement   -> Consider
    R2  otherwise, every mandatory requirement is met     -> High Priority
    R3  anything else                                     -> Consider
    """
    mandatory = [r for r in requirements if r.get("importance") == "mandatory"]
    verified = [r for r in mandatory if is_verified(r)]
    unverified = len(mandatory) - len(verified)

    total = len(verified)
    met = sum(1 for r in verified if r.get("status") == "met")
    not_met = sum(1 for r in verified if r.get("status") == "not_met")
    unknown = sum(1 for r in verified if r.get("status") == "not_enough_information")

    unverified_note = (
        f" The wording of {_requirements(unverified, 'other mandatory')} could not be found in the ad."
        if unverified
        else ""
    )

    if not_met > 0:
        # A verified failure is enough on its own, whatever else is uncertain.
        recommendation, rule = LOW, "R1"
        reason = (
            f"{not_met} of {total} mandatory requirements "
            f"{'is' if not_met == 1 else 'are'} not met.{unverified_note}"
        )
    elif unverified > 0:
        recommendation, rule = CONSIDER, "R4"
        reason = (
            f"The wording of {_requirements(unverified)} could not be found in the ad, "
            f"so {'it' if unverified == 1 else 'they'} cannot be verified and the assessment "
            "cannot be firm."
        )
        if total:
            reason += f" {met} of the {total} verified mandatory requirements are met."
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

    if rule == "R4":
        # An unverified mandatory requirement is itself missing information.
        limited = True
    else:
        judged_over = total + unverified
        limited = judged_over == 0 or (unknown + unverified) / judged_over >= LIMITED_INFORMATION_SHARE

    return Decision(
        recommendation=recommendation,
        rule=rule,
        reason=reason,
        limited_information=limited,
        mandatory_total=total,
        mandatory_met=met,
        mandatory_not_met=not_met,
        mandatory_unknown=unknown,
        mandatory_unverified=unverified,
    )
