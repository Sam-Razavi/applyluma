"""Turn the raw run records into the tables of DESIGN.md section 8.

Everything here is a pure function of the cases and the records in results.jsonl,
so the tables can be rebuilt from a stored run without calling any model.

A record is one run of one system on one case or variant:

    {"case": "c01", "variant": null, "variant_type": null, "system": "ai", "run": 1,
     "priority": "consider", "error": null, "output": {...}}
"""

from __future__ import annotations

import csv
import io
import statistics
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from thesis.eval.cases import PRIORITIES, Case

SYSTEMS = ("ai", "rule_based")
SYSTEM_LABEL = {"ai": "AI assessment", "rule_based": "Rule-based matcher"}
PRIORITY_LABEL = {
    "high_priority": "High Priority",
    "consider": "Consider",
    "low_priority": "Low Priority",
    None: "no stable decision",
}
AGREEMENTS = ("exact", "one_step", "opposite", "no_decision")
AGREEMENT_LABEL = {
    "exact": "Same as reference",
    "one_step": "One step away",
    "opposite": "Opposite",
    "no_decision": "No stable decision",
}

Record = dict[str, Any]


# --------------------------------------------------------------------------
# Measures
# --------------------------------------------------------------------------


def case_decision(priorities: list[str]) -> tuple[str | None, float]:
    """The priority most runs gave and the share of runs that gave it.

    A tie for first place gives no decision.
    """
    if not priorities:
        return None, 0.0
    ranked = Counter(priorities).most_common()
    top, count = ranked[0]
    share = count / len(priorities)
    if len(ranked) > 1 and ranked[1][1] == count:
        return None, share
    return top, share


def agreement(decision: str | None, reference: str) -> str:
    if decision is None:
        return "no_decision"
    distance = abs(PRIORITIES.index(decision) - PRIORITIES.index(reference))
    return ("exact", "one_step", "opposite")[distance]


def missing_item_flagged(output: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    """Whether an assessment names the item as missing.

    Looks in the missing-information list and in the requirements judged
    "not enough information". The review sheet lets a person check this by eye.
    """
    parts = [str(item) for item in output.get("missing_information") or []]
    for requirement in output.get("requirements") or []:
        if requirement.get("status") == "not_enough_information":
            parts += [str(requirement.get("text") or ""), str(requirement.get("note") or "")]
    haystack = " ".join(parts).casefold()
    return any(keyword.casefold() in haystack for keyword in keywords)


def _group(records: list[Record]) -> dict[tuple[str, str | None, str], list[Record]]:
    grouped: dict[tuple[str, str | None, str], list[Record]] = defaultdict(list)
    for record in records:
        grouped[(record["case"], record.get("variant"), record["system"])].append(record)
    for runs in grouped.values():
        runs.sort(key=lambda r: r["run"])
    return grouped


def _priorities(runs: list[Record]) -> list[str]:
    return [r["priority"] for r in runs if r.get("priority")]


def analyse(cases: list[Case], records: list[Record]) -> dict[str, Any]:
    """Per case and system: the decision, how it compares, and what the variants did."""
    grouped = _group(records)
    rows: list[dict[str, Any]] = []
    for case in cases:
        for system in SYSTEMS:
            runs = grouped.get((case.id, None, system), [])
            if not runs:
                continue
            priorities = _priorities(runs)
            decision, share = case_decision(priorities)
            variants = []
            for variant in case.variants:
                variant_runs = grouped.get((case.id, variant.id, system), [])
                if not variant_runs:
                    continue
                variant_priorities = _priorities(variant_runs)
                variant_decision, _ = case_decision(variant_priorities)
                comparable = decision is not None or variant_decision is not None
                variants.append(
                    {
                        "id": variant.id,
                        "type": variant.type,
                        "decision": variant_decision,
                        "priorities": variant_priorities,
                        "failed": len(variant_runs) - len(variant_priorities),
                        "changed": (variant_decision != decision) if comparable else None,
                        "runs_differing": sum(1 for p in variant_priorities if p != decision),
                    }
                )
            rows.append(
                {
                    "case": case,
                    "system": system,
                    "runs": runs,
                    "priorities": priorities,
                    "failed": len(runs) - len(priorities),
                    "decision": decision,
                    "consistency": share,
                    "agreement": agreement(decision, case.reference),
                    "variants": variants,
                }
            )
    return {"rows": rows, "grouped": grouped}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _table(header: list[str], body: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in body]
    return "\n".join(lines)


def _share(part: int, whole: int) -> str:
    return f"{part} of {whole} ({part / whole:.0%})" if whole else "0 of 0"


def _oneline(text: Any) -> str:
    return " ".join(str(text or "").split()).replace("|", "/")


def _agreement_counts(rows: list[dict[str, Any]]) -> list[str]:
    counts = Counter(row["agreement"] for row in rows)
    return [_share(counts["exact"], len(rows))] + [str(counts[a]) for a in AGREEMENTS[1:]]


def _correctness(rows: list[dict[str, Any]]) -> list[str]:
    out = ["## 1. Correctness: agreement with the reference decision", ""]
    header = ["", "Cases", *[AGREEMENT_LABEL[a] for a in AGREEMENTS]]
    for title, key in (("Overall", None), ("By scenario type", "scenario"), ("By language", "language")):
        body = []
        for system in SYSTEMS:
            mine = [r for r in rows if r["system"] == system]
            groups = sorted({getattr(r["case"], key) for r in mine}) if key else [None]
            for group in groups:
                part = [r for r in mine if key is None or getattr(r["case"], key) == group]
                label = SYSTEM_LABEL[system] + (f", {group}" if group else "")
                body.append([label, len(part), *_agreement_counts(part)])
        out += [f"**{title}**", "", _table(header, body), ""]

    out += [
        "**Per cell** (scenario type, language, reference decision). Thin cells show here.",
        "",
    ]
    cells: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        case = row["case"]
        cells[(case.scenario, case.language, case.reference)][row["system"]].append(row)
    body = []
    for (scenario, language, reference), by_system in sorted(cells.items()):
        cases_in_cell = max(len(v) for v in by_system.values())
        exact = [
            f"{sum(1 for r in by_system.get(system, []) if r['agreement'] == 'exact')} of {len(by_system.get(system, []))}"
            for system in SYSTEMS
        ]
        body.append([scenario, language, PRIORITY_LABEL[reference], cases_in_cell, *exact])
    out += [
        _table(
            ["Scenario", "Language", "Reference", "Cases", "AI same as reference", "Rule-based same as reference"],
            body,
        ),
        "",
    ]
    return out


def _consistency(rows: list[dict[str, Any]]) -> list[str]:
    out = [
        "## 2. Consistency: repeated runs of the same case",
        "",
        "Share of a case's runs that gave its most frequent priority, whether or not that",
        "priority is the correct one.",
        "",
    ]
    body = []
    for system in SYSTEMS:
        mine = [r for r in rows if r["system"] == system and r["priorities"]]
        if not mine:
            continue
        same = sum(1 for r in mine if len(set(r["priorities"])) == 1)
        mean = statistics.mean(r["consistency"] for r in mine)
        body.append([SYSTEM_LABEL[system], len(mine), _share(same, len(mine)), f"{mean:.0%}"])
    out += [_table(["", "Cases", "All runs identical", "Mean share of runs on the most frequent priority"], body), ""]
    unstable = [r for r in rows if len(set(r["priorities"])) > 1]
    if unstable:
        out += ["Cases whose runs differed:", ""]
        out += [
            f"- `{r['case'].id}` ({SYSTEM_LABEL[r['system']]}): "
            + ", ".join(PRIORITY_LABEL[p] for p in r["priorities"])
            for r in unstable
        ]
        out.append("")
    return out


def _robustness(rows: list[dict[str, Any]], variant_types: list[str]) -> list[str]:
    out = [
        "## 3. Robustness: the same case with a change that should not matter",
        "",
        "A variant counts as changed when its decision differs from the decision on the",
        "unchanged case.",
        "",
    ]
    body = []
    changed_list = []
    for system in SYSTEMS:
        for variant_type in variant_types:
            variants = [
                (r, v)
                for r in rows
                if r["system"] == system
                for v in r["variants"]
                if v["type"] == variant_type and v["changed"] is not None
            ]
            if not variants:
                continue
            changed = [(r, v) for r, v in variants if v["changed"]]
            runs = sum(len(v["priorities"]) for _, v in variants)
            differing = sum(v["runs_differing"] for _, v in variants)
            body.append(
                [SYSTEM_LABEL[system], variant_type, len(variants), _share(len(changed), len(variants)), _share(differing, runs)]
            )
            changed_list += [
                f"- `{r['case'].id}` / `{v['id']}` ({SYSTEM_LABEL[system]}): "
                f"{PRIORITY_LABEL[r['decision']]} became {PRIORITY_LABEL[v['decision']]}"
                for r, v in changed
            ]
    if not body:
        return [*out, "No variants in this run.", ""]
    out += [_table(["", "Variant type", "Variants", "Decision changed", "Single runs differing"], body), ""]
    if changed_list:
        out += ["Changed decisions:", "", *changed_list, ""]
    return out


def _ai_outputs(rows: list[dict[str, Any]], grouped: dict[Any, list[Record]]) -> list[dict[str, Any]]:
    """Every successful AI output, variants included."""
    return [
        record["output"]
        for (_, _, system), runs in grouped.items()
        if system == "ai"
        for record in runs
        if record.get("priority")
    ]


def _transparency(outputs: list[dict[str, Any]]) -> list[str]:
    totals: Counter[str] = Counter()
    for output in outputs:
        totals.update(output.get("quote_stats") or {})
    requirements = sum(len(o.get("requirements") or []) for o in outputs)
    return [
        "## 4. Transparency: do the quoted reasons exist in the texts",
        "",
        _table(
            ["Measure", "Result"],
            [
                ["AI assessments", len(outputs)],
                ["Requirements judged", requirements],
                ["Quotes from the ad found in the ad", _share(totals["ad_quotes_found"], totals["ad_quotes"])],
                ["Quotes from the CV found in the CV", _share(totals["cv_quotes_found"], totals["cv_quotes"])],
                ["Judgements set aside because the CV quote was not in the CV", totals["downgraded"]],
            ],
        ),
        "",
        "The rule-based matcher gives one generated line and no quotes. Whether each AI",
        "explanation is supported by the texts is judged by hand in `review_sheet.csv`.",
        "",
    ]


def _missing_information(rows: list[dict[str, Any]]) -> list[str]:
    out = ["## 5. Missing or ambiguous information", ""]
    ai_rows = [r for r in rows if r["system"] == "ai"]
    body = []
    for row in ai_rows:
        outputs = [r["output"] for r in row["runs"] if r.get("priority")]
        for item in row["case"].expected_missing:
            flagged = sum(1 for o in outputs if missing_item_flagged(o, item.keywords))
            body.append([f"`{row['case'].id}`", item.label, _share(flagged, len(outputs))])
    if body:
        out += [_table(["Case", "Information the case lacks", "Runs that flagged it"], body), ""]
    else:
        out += ["No case in this run lists expected missing information.", ""]

    def limited(part: list[dict[str, Any]]) -> str:
        outputs = [r["output"] for row in part for r in row["runs"] if r.get("priority")]
        return _share(sum(1 for o in outputs if o.get("limited_information")), len(outputs))

    with_missing = [r for r in ai_rows if r["case"].expected_missing]
    without = [r for r in ai_rows if not r["case"].expected_missing]
    out += [
        _table(
            ["Runs with the limited-information notice", "Result"],
            [["Cases built to lack information", limited(with_missing)], ["Other cases", limited(without)]],
        ),
        "",
        "The rule-based matcher has no output for missing information.",
        "",
    ]
    return out


def _reliability(records: list[Record], cost_per_mtok: tuple[Decimal, Decimal]) -> list[str]:
    ai = [r for r in records if r["system"] == "ai"]
    ok = [r["output"]["meta"] for r in ai if r.get("priority")]
    failed = [r for r in ai if not r.get("priority")]
    body: list[list[Any]] = [["AI assessments attempted", len(ai)], ["Failed", len(failed)]]
    if ok:
        seconds = [m["latency_ms"] / 1000 for m in ok]
        prompt = sum(m["prompt_tokens"] for m in ok)
        completion = sum(m["completion_tokens"] for m in ok)
        cost = (Decimal(prompt) * cost_per_mtok[0] + Decimal(completion) * cost_per_mtok[1]) / Decimal(1_000_000)
        body += [
            ["Seconds per assessment (median / mean / longest)", f"{statistics.median(seconds):.1f} / {statistics.mean(seconds):.1f} / {max(seconds):.1f}"],
            ["Tokens (input / output)", f"{prompt:,} / {completion:,}"],
            ["Cost in USD (total / per assessment)", f"{cost:.2f} / {cost / len(ok):.4f}"],
        ]
    rule_failed = sum(1 for r in records if r["system"] == "rule_based" and not r.get("priority"))
    body.append(["Rule-based runs failed", rule_failed])
    out = ["## 6. Reliability", "", _table(["Measure", "Result"], body), ""]
    if failed:
        out += ["Failures:", ""]
        out += [f"- `{r['case']}`{'/' + r['variant'] if r.get('variant') else ''} run {r['run']}: {_oneline(r.get('error'))}" for r in failed]
        out.append("")
    return out


def _model_suggestion(rows: list[dict[str, Any]]) -> list[str]:
    """The model's own suggested priority, stored but never shown or used."""
    pairs = [
        (r["output"].get("model_recommendation"), r["priority"], row["case"].reference)
        for row in rows
        if row["system"] == "ai"
        for r in row["runs"]
        if r.get("priority")
    ]
    pairs = [p for p in pairs if p[0]]
    if not pairs:
        return []
    return [
        "## 7. The model's own suggestion against the fixed rules",
        "",
        "The model also suggests a priority. It is stored for this comparison only; the",
        "decision comes from the rules.",
        "",
        _table(
            ["Runs on unchanged cases", "Result"],
            [
                ["Model's suggestion equals the rules' decision", _share(sum(1 for m, d, _ in pairs if m == d), len(pairs))],
                ["Rules' decision equals the reference", _share(sum(1 for _, d, ref in pairs if d == ref), len(pairs))],
                ["Model's suggestion equals the reference", _share(sum(1 for m, _, ref in pairs if m == ref), len(pairs))],
            ],
        ),
        "",
    ]


def _representative(row: dict[str, Any]) -> dict[str, Any] | None:
    """A run that gave the case's decision, else the first successful run."""
    ok = [r for r in row["runs"] if r.get("priority")]
    for record in ok:
        if record["priority"] == row["decision"]:
            return record["output"]
    return ok[0]["output"] if ok else None


def _describe(row: dict[str, Any]) -> list[str]:
    output = _representative(row)
    head = f"**{SYSTEM_LABEL[row['system']]}: {PRIORITY_LABEL[row['decision']]}** ({AGREEMENT_LABEL[row['agreement']].lower()})"
    if output is None:
        return [head, "", "Every run failed.", ""]
    if row["system"] == "rule_based":
        return [
            head,
            "",
            f"- Score {output['overall_score']} (skills part {output['skills_match']})",
            f"- Matched: {', '.join(output['matched_skills']) or 'none'}",
            f"- Missing: {', '.join(output['missing_skills']) or 'none'}",
            f"- Explanation: {_oneline(output['explanation'])}",
            "",
        ]
    lines = [
        head,
        "",
        f"- Runs: {', '.join(PRIORITY_LABEL[p] for p in row['priorities'])}",
        f"- Rule {output['rule']}: {_oneline(output['reason'])}",
        f"- Summary: {_oneline(output['summary'])}",
        f"- Missing information: {'; '.join(_oneline(m) for m in output['missing_information']) or 'none listed'}",
        "",
        _table(
            ["Requirement", "Importance", "Status", "Quote from the CV", "In the CV"],
            [
                [
                    _oneline(q["text"]),
                    q["importance"],
                    q["status"] + (f" (model said {q['model_status']})" if q.get("downgraded") else ""),
                    _oneline(q["cv_quote"]) or "-",
                    {True: "yes", False: "NO", None: "-"}[q["cv_quote_found"]],
                ]
                for q in output["requirements"]
            ],
        ),
        "",
    ]
    return lines


def _failure_cases(rows: list[dict[str, Any]]) -> list[str]:
    out = ["## 8. Cases where a system differs from the reference", ""]
    wrong = sorted({r["case"].id for r in rows if r["agreement"] != "exact"})
    if not wrong:
        return [*out, "None.", ""]
    for case_id in wrong:
        mine = [r for r in rows if r["case"].id == case_id]
        case = mine[0]["case"]
        out += [
            f"### `{case.id}`",
            "",
            f"Reference: **{PRIORITY_LABEL[case.reference]}**. {_oneline(case.rationale)}",
            "",
        ]
        for row in mine:
            out += _describe(row)
    return out


def _per_case(rows: list[dict[str, Any]]) -> list[str]:
    by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[row["case"].id][row["system"]] = row
    body = []
    for case_id, systems in by_case.items():
        case = next(iter(systems.values()))["case"]
        ai, rule = systems.get("ai"), systems.get("rule_based")
        score = (_representative(rule) or {}).get("overall_score", "-") if rule else "-"
        body.append(
            [
                f"`{case_id}`",
                case.scenario,
                case.language,
                PRIORITY_LABEL[case.reference],
                PRIORITY_LABEL[ai["decision"]] if ai else "-",
                f"{ai['consistency']:.0%}" if ai and ai["priorities"] else "-",
                PRIORITY_LABEL[rule["decision"]] if rule else "-",
                score,
            ]
        )
    return [
        "## 9. Every case",
        "",
        _table(["Case", "Scenario", "Language", "Reference", "AI", "AI runs agreeing", "Rule-based", "Score"], body),
        "",
    ]


def summary_markdown(
    cases: list[Case],
    records: list[Record],
    protocol: dict[str, Any],
    run_info: dict[str, Any],
    cost_per_mtok: tuple[Decimal, Decimal],
) -> str:
    analysis = analyse(cases, records)
    rows = analysis["rows"]
    lines = [
        f"# Evaluation run `{run_info['run_id']}`",
        "",
        _table(
            ["", ""],
            [
                ["Cases", f"{len(cases)} from `{run_info['cases_dir']}`"],
                ["Code", f"commit `{run_info['git_commit']}`" + (" with uncommitted changes" if run_info["git_dirty"] else "")],
                ["Model", f"`{run_info['model']}`, temperature {run_info['temperature']}, seed {run_info['seed']}"],
                ["Prompt / rules / protocol version", f"{run_info['prompt_version']} / {run_info['rules_version']} / {protocol['version']}"],
                ["Date given to the model", protocol["reference_date"]],
                ["Runs", f"{protocol['runs_per_case']} per case, {protocol['runs_per_variant']} per variant; rule-based {protocol['rule_based_runs']}"],
                ["Rule-based thresholds", f"High Priority from {protocol['rule_based_thresholds']['high_priority_min']}, Consider from {protocol['rule_based_thresholds']['consider_min']}"],
                ["Started / finished (UTC)", f"{run_info['started_at']} / {run_info.get('finished_at', '-')}"],
            ],
        ),
        "",
        "Built from `results.jsonl` in this folder. Counts are small: read them as counts,",
        "not as rates that would hold for other cases.",
        "",
    ]
    lines += _correctness(rows)
    lines += _consistency(rows)
    lines += _robustness(rows, protocol["variant_types"])
    lines += _transparency(_ai_outputs(rows, analysis["grouped"]))
    lines += _missing_information(rows)
    lines += _reliability(records, cost_per_mtok)
    lines += _model_suggestion(rows)
    lines += _failure_cases(rows)
    lines += _per_case(rows)
    return "\n".join(lines).rstrip() + "\n"


def _csv(header: list[str], body: list[list[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(body)
    return buffer.getvalue()


def summary_csv(cases: list[Case], records: list[Record]) -> str:
    """One line per case, variant and system, for tables and charts in the thesis."""
    body: list[list[Any]] = []
    for row in analyse(cases, records)["rows"]:
        case = row["case"]
        output = _representative(row) or {}
        body.append(
            [
                case.id, "", "", case.scenario, case.language, case.reference, row["system"],
                row["decision"] or "", row["agreement"], len(row["runs"]), row["failed"],
                f"{row['consistency']:.2f}", " ".join(row["priorities"]), output.get("overall_score", ""), "",
            ]
        )
        for variant in row["variants"]:
            body.append(
                [
                    case.id, variant["id"], variant["type"], case.scenario, case.language, case.reference,
                    row["system"], variant["decision"] or "", "", len(variant["priorities"]) + variant["failed"],
                    variant["failed"], "", " ".join(variant["priorities"]), "",
                    "" if variant["changed"] is None else ("yes" if variant["changed"] else "no"),
                ]
            )
    return _csv(
        [
            "case", "variant", "variant_type", "scenario", "language", "reference", "system", "decision",
            "agreement", "runs", "failed", "consistency", "run_priorities", "rule_based_score", "changed_by_variant",
        ],
        body,
    )


def review_sheet_csv(cases: list[Case], records: list[Record]) -> str:
    """The first AI run of every unchanged case, one line per requirement, to judge by hand."""
    grouped = _group(records)
    body: list[list[Any]] = []
    for case in cases:
        first = next((r for r in grouped.get((case.id, None, "ai"), []) if r.get("priority")), None)
        if first is None:
            continue
        output = first["output"]
        body.append(
            [case.id, first["run"], "summary", "", output["recommendation"], output["summary"], "", "",
             "; ".join(output["missing_information"]), "", ""]
        )
        for q in output["requirements"]:
            body.append(
                [
                    case.id, first["run"], q["id"], q["importance"], q["status"], q["text"], q["cv_quote"],
                    {True: "yes", False: "no", None: ""}[q["cv_quote_found"]], q["note"], "", "",
                ]
            )
    return _csv(
        [
            "case", "run", "item", "importance", "status_or_priority", "requirement_or_summary", "cv_quote",
            "quote_found_in_cv", "note_or_missing_information", "supported_by_the_texts (yes/no)", "comment",
        ],
        body,
    )
