"""Load evaluation cases from a folder.

One folder per case:

    cv.md       the CV text
    ad.md       the job ad text
    case.yaml   what the case is for and the reference decision

case.yaml:

    scenario: clear                 # one of protocol.yaml scenario_types
    language: en                    # en or sv
    reference: high_priority        # high_priority, consider or low_priority
    rationale: Why a person reading the CV and the ad decides this.
    remote: false                   # optional; the rule-based score adds 0.5 for remote jobs
    expected_missing:               # optional; information the case was built to lack
      - label: Driving licence
        keywords: [körkort, driving licence]
    variants:                       # optional; changed copies of the same case
      - id: name_swap
        type: name_swap             # one of protocol.yaml variant_types
        cv: cv_name_swap.md         # a file in the case folder; cv, ad or both
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PRIORITIES = ("low_priority", "consider", "high_priority")


class CaseError(Exception):
    """One or more case folders are not usable; the message lists every problem."""


@dataclass(frozen=True)
class ExpectedMissing:
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Variant:
    id: str
    type: str
    cv_text: str
    ad_text: str


@dataclass(frozen=True)
class Case:
    id: str
    scenario: str
    language: str
    reference: str
    rationale: str
    cv_text: str
    ad_text: str
    remote: bool = False
    expected_missing: tuple[ExpectedMissing, ...] = ()
    variants: tuple[Variant, ...] = field(default=())


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise CaseError(f"{path} is not a protocol file")
    return protocol


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read(path: Path, problems: list[str]) -> str:
    if not path.is_file():
        problems.append(f"{path.parent.name}: {path.name} is missing")
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        problems.append(f"{path.parent.name}: {path.name} is empty")
    return text


def _load_case(folder: Path, protocol: dict[str, Any], problems: list[str]) -> Case | None:
    name = folder.name
    before = len(problems)
    cv_text = _read(folder / "cv.md", problems)
    ad_text = _read(folder / "ad.md", problems)

    meta_path = folder / "case.yaml"
    meta: Any = yaml.safe_load(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else None
    if not isinstance(meta, dict):
        problems.append(f"{name}: case.yaml is missing or not a mapping")
        return None

    scenario = meta.get("scenario")
    if scenario not in protocol["scenario_types"]:
        problems.append(f"{name}: scenario must be one of {protocol['scenario_types']}")
    language = meta.get("language")
    if language not in protocol["languages"]:
        problems.append(f"{name}: language must be one of {protocol['languages']}")
    reference = meta.get("reference")
    if reference not in PRIORITIES:
        problems.append(f"{name}: reference must be one of {list(PRIORITIES)}")
    rationale = str(meta.get("rationale") or "").strip()
    if not rationale:
        problems.append(f"{name}: rationale is missing")

    expected: list[ExpectedMissing] = []
    for item in meta.get("expected_missing") or []:
        keywords = item.get("keywords") if isinstance(item, dict) else None
        if not isinstance(item, dict) or not item.get("label") or not keywords:
            problems.append(f"{name}: each expected_missing item needs a label and keywords")
            continue
        expected.append(ExpectedMissing(str(item["label"]), tuple(str(k) for k in keywords)))

    variants: list[Variant] = []
    seen: set[str] = set()
    for item in meta.get("variants") or []:
        if not isinstance(item, dict) or not item.get("id"):
            problems.append(f"{name}: each variant needs an id")
            continue
        variant_id = str(item["id"])
        if variant_id in seen:
            problems.append(f"{name}: variant id {variant_id} is used twice")
        seen.add(variant_id)
        if item.get("type") not in protocol["variant_types"]:
            problems.append(f"{name}/{variant_id}: type must be one of {protocol['variant_types']}")
        if not item.get("cv") and not item.get("ad"):
            problems.append(f"{name}/{variant_id}: give a cv file, an ad file or both")
        variant_cv = _read(folder / str(item["cv"]), problems) if item.get("cv") else cv_text
        variant_ad = _read(folder / str(item["ad"]), problems) if item.get("ad") else ad_text
        if variant_cv == cv_text and variant_ad == ad_text:
            problems.append(f"{name}/{variant_id}: the variant is identical to the case")
        variants.append(Variant(variant_id, str(item.get("type")), variant_cv, variant_ad))

    if len(problems) > before:
        return None
    return Case(
        id=name,
        scenario=str(scenario),
        language=str(language),
        reference=str(reference),
        rationale=rationale,
        cv_text=cv_text,
        ad_text=ad_text,
        remote=bool(meta.get("remote", False)),
        expected_missing=tuple(expected),
        variants=tuple(variants),
    )


def load_cases(root: Path, protocol: dict[str, Any]) -> list[Case]:
    """Every case folder under `root`, in name order. Raises CaseError on any problem."""
    folders = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
    problems: list[str] = []
    cases = [case for folder in folders if (case := _load_case(folder, protocol, problems))]
    if not folders:
        problems.append(f"no case folders in {root}")
    if problems:
        raise CaseError("Cases cannot be used:\n- " + "\n- ".join(problems))
    return cases
