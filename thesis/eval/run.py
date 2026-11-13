"""Run both systems on a folder of cases and write the results.

From the repository root:

    OPENAI_API_KEY=... python -m thesis.eval.run --cases thesis/practice_cases --out thesis/results/practice

    --resume          continue a run that stopped; runs already in results.jsonl are kept
    --report-only     rebuild the tables from an existing results.jsonl, no model calls
    --systems         "ai,rule_based" (default), or one of them

Writes into --out: run.json (what was run), results.jsonl (every run, complete),
summary.md, summary.csv and review_sheet.csv.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
for entry in (str(REPO), str(REPO / "backend")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from app.services import ai_usage  # noqa: E402
from app.services.fit_advisor import llm, prompts, service  # noqa: E402
from app.services.fit_advisor.decision import RULES_VERSION  # noqa: E402
from thesis.eval import report, rule_based_adapter  # noqa: E402
from thesis.eval.cases import Case, load_cases, load_protocol, text_hash  # noqa: E402

AssessFn = Callable[..., dict[str, Any]]


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def run_info(cases: list[Case], cases_dir: Path, protocol: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "cases_dir": str(cases_dir),
        "git_commit": _git("rev-parse", "--short", "HEAD") or "unknown",
        "git_dirty": bool(_git("status", "--porcelain", "--", "backend", "thesis/eval", "thesis/protocol.yaml")),
        "model": llm.MODEL,
        "temperature": llm.TEMPERATURE,
        "seed": llm.SEED,
        "prompt_version": prompts.PROMPT_VERSION,
        "rules_version": RULES_VERSION,
        "protocol": protocol,
        "started_at": _now(),
        "inputs": {
            case.id: {
                "cv": text_hash(case.cv_text),
                "ad": text_hash(case.ad_text),
                "variants": {v.id: {"cv": text_hash(v.cv_text), "ad": text_hash(v.ad_text)} for v in case.variants},
            }
            for case in cases
        },
    }


def _planned(cases: list[Case], protocol: dict[str, Any], systems: list[str]) -> list[dict[str, Any]]:
    """Every run to make, in a fixed order."""
    plan: list[dict[str, Any]] = []
    for case in cases:
        targets = [(None, None, case.cv_text, case.ad_text, protocol["runs_per_case"])]
        targets += [(v.id, v.type, v.cv_text, v.ad_text, protocol["runs_per_variant"]) for v in case.variants]
        for variant_id, variant_type, cv_text, ad_text, ai_runs in targets:
            for system in systems:
                count = ai_runs if system == "ai" else protocol["rule_based_runs"]
                for run in range(1, count + 1):
                    plan.append(
                        {
                            "case": case.id, "variant": variant_id, "variant_type": variant_type,
                            "system": system, "run": run, "cv_text": cv_text, "ad_text": ad_text,
                            "remote": case.remote,
                        }
                    )
    return plan


def _one_run(item: dict[str, Any], protocol: dict[str, Any], assess: AssessFn) -> dict[str, Any]:
    record = {key: item[key] for key in ("case", "variant", "variant_type", "system", "run")}
    try:
        if item["system"] == "ai":
            output = assess(
                item["cv_text"], item["ad_text"], today=date.fromisoformat(str(protocol["reference_date"]))
            )
            priority = output["recommendation"]
        else:
            output = rule_based_adapter.score(item["cv_text"], item["ad_text"], remote=item["remote"])
            priority = rule_based_adapter.priority(output["overall_score"], protocol["rule_based_thresholds"])
    except Exception as exc:  # a failed run is a result, not a reason to stop
        return {**record, "priority": None, "error": f"{type(exc).__name__}: {exc}", "output": None}
    return {**record, "priority": priority, "error": None, "output": output}


def _key(record: dict[str, Any]) -> tuple[str, str | None, str, int]:
    return record["case"], record.get("variant"), record["system"], record["run"]


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_reports(out: Path, cases: list[Case], records: list[dict[str, Any]], info: dict[str, Any]) -> None:
    price = ai_usage.PRICES_PER_MTOK[info["model"]]
    protocol = info["protocol"]
    (out / "summary.md").write_text(report.summary_markdown(cases, records, protocol, info, price), encoding="utf-8")
    (out / "summary.csv").write_text(report.summary_csv(cases, records), encoding="utf-8")
    (out / "review_sheet.csv").write_text(report.review_sheet_csv(cases, records), encoding="utf-8")


def execute(
    cases_dir: Path,
    out: Path,
    protocol_path: Path,
    *,
    systems: list[str],
    resume: bool = False,
    report_only: bool = False,
    assess: AssessFn = service.assess,
    log: Callable[[str], None] = print,
) -> list[dict[str, Any]]:
    results_path = out / "results.jsonl"
    info_path = out / "run.json"

    if report_only or resume:
        if not info_path.is_file():
            raise SystemExit(f"{info_path} not found: nothing to continue or report on")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        protocol = info["protocol"]
        cases = load_cases(cases_dir, protocol)
        current = run_info(cases, cases_dir, protocol, info["run_id"])
        for field in ("inputs", "prompt_version", "rules_version", "model"):
            if current[field] != info[field]:
                raise SystemExit(f"{field} differs from the stored run: start a new run in another folder")
    else:
        if results_path.exists():
            raise SystemExit(f"{results_path} exists: use --resume, or another --out folder")
        protocol = load_protocol(protocol_path)
        cases = load_cases(cases_dir, protocol)
        out.mkdir(parents=True, exist_ok=True)
        info = run_info(cases, cases_dir, protocol, out.name)
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

    records = read_records(results_path)
    if not report_only:
        done = {_key(record) for record in records}
        plan = [item for item in _planned(cases, protocol, systems) if _key(item) not in done]
        log(f"{len(cases)} cases, {len(plan)} runs to make ({len(done)} already stored)")
        with results_path.open("a", encoding="utf-8") as handle:
            for number, item in enumerate(plan, 1):
                record = _one_run(item, protocol, assess)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                records.append(record)
                if item["system"] == "ai":
                    where = item["case"] + (f"/{item['variant']}" if item["variant"] else "")
                    log(f"[{number}/{len(plan)}] {where} run {item['run']}: {record['priority'] or record['error']}")
        info["finished_at"] = _now()
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

    write_reports(out, cases, records, info)
    log(f"Wrote {out / 'summary.md'}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=REPO / "thesis" / "protocol.yaml")
    parser.add_argument("--systems", default="ai,rule_based")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    systems = [name.strip() for name in args.systems.split(",") if name.strip()]
    if not systems or any(name not in report.SYSTEMS for name in systems):
        parser.error(f"--systems takes {', '.join(report.SYSTEMS)}")

    # The runner has no database: token counts are kept in each result instead
    # of the app's usage table.
    llm.ai_usage.record_ai_usage = lambda **_: None  # type: ignore[assignment]

    execute(args.cases, args.out, args.protocol, systems=systems, resume=args.resume, report_only=args.report_only)


if __name__ == "__main__":
    main()
