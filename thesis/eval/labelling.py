"""The second labeller's blind labelling sheet, and a comparison of the two labels.

From the repository root:

    python -m thesis.eval.labelling sheet --cases thesis/cases --out ../labelling
    python -m thesis.eval.labelling compare --cases thesis/cases \\
        --key ../labelling/labelling_key.csv --answers ../labelling/labelling_answers.xlsx

`sheet` writes into --out:

    labelling_sheet.html    the cases to read, numbered in a shuffled order. Only the CV
                            and the ad: no folder names, labels, rationales or variants.
    labelling_answers.csv   the form the second labeller fills in (and an .xlsx copy
                            when openpyxl is installed)
    labelling_key.csv       which number is which case folder. Keep it to yourself.

If the cases folder has a CRITERIA.md (the criteria for reference decisions, written
for a human reader), the sheet starts with it.

`compare` reads the filled-in form (.csv or .xlsx) and prints the author's label next
to the second labeller's for every case, and the `second_label:` line to add to each
case.yaml. Disagreements are discussed and settled before either system runs.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import random
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from thesis.eval.cases import PRIORITIES, Case, CaseError, load_cases, load_protocol  # noqa: E402
from thesis.eval.xlsx import write_xlsx  # noqa: E402

LABELS = {"high_priority": "High Priority", "consider": "Consider", "low_priority": "Low Priority"}
ANSWER_HEADER = ["Case", "Decision (High Priority, Consider or Low Priority)", "Reason"]
KEY_HEADER = ["Case", "Folder"]

# What a labeller may write, after lower-casing, removing accents and dropping
# spaces, underscores and hyphens. Swedish included, in case the labeller writes it.
_DECISION_WORDS = {
    "highpriority": "high_priority", "high": "high_priority", "hogprioritet": "high_priority", "hog": "high_priority",
    "consider": "consider", "overvag": "consider",
    "lowpriority": "low_priority", "low": "low_priority", "lagprioritet": "low_priority", "lag": "low_priority",
}


def parse_decision(text: str) -> str | None:
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().casefold()
    key = "".join(ch for ch in folded if ch.isalnum())
    return _DECISION_WORDS.get(key)


def shuffled(cases: list[Case], seed: int) -> list[Case]:
    """The cases in a fixed random order, so the order says nothing about them."""
    order = list(cases)
    random.Random(seed).shuffle(order)
    return order


def _csv(rows: list[list[Any]]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue()


def _long_date(iso: str) -> str:
    """2026-12-01 as "1 December 2026", which no reader can take for another date."""
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{day.day} {day:%B %Y}"


def sheet_html(order: list[Case], reference_date: str, criteria: str | None) -> str:
    def block(text: str) -> str:
        return f'<div class="text">{html.escape(text)}</div>'

    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Labelling sheet</title>",
        "<style>",
        "body{font:16px/1.5 Georgia,serif;color:#1a1a1a;background:#fff;max-width:46rem;margin:2rem auto;padding:0 1rem}",
        "h1,h2,h3{font-family:Helvetica,Arial,sans-serif;line-height:1.25}",
        "section.case{border-top:2px solid #1a1a1a;margin-top:3rem;padding-top:1rem}",
        ".text{white-space:pre-wrap;background:#f6f6f3;border:1px solid #ddd;padding:1rem;font-size:15px}",
        ".answer{border:1px solid #999;padding:.75rem 1rem;margin-top:1.5rem}",
        "@media print{section.case{break-before:page;border-top:none;margin-top:0}}",
        "</style></head><body>",
        "<h1>Labelling sheet</h1>",
        f"<p>{len(order)} cases. Each is a CV and a job ad. For each case, decide how a job seeker "
        "with this CV should treat this job, as one of three decisions:</p>",
        "<ul>" + "".join(f"<li><b>{LABELS[p]}</b></li>" for p in reversed(PRIORITIES)) + "</ul>",
        f"<p>Read the texts as if today is <b>{html.escape(_long_date(reference_date))}</b>. Write your decision and "
        "a sentence on why in the answer form, on the line with the case's number. Decide each case "
        "on its own, from the two texts only.</p>",
    ]
    if criteria:
        parts += ["<h2>How to decide</h2>", block(criteria)]
    for number, case in enumerate(order, 1):
        parts += [
            f'<section class="case"><h2>Case {number}</h2>',
            "<h3>CV</h3>",
            block(case.cv_text),
            "<h3>Job ad</h3>",
            block(case.ad_text),
            f'<p class="answer">Case {number}: High Priority / Consider / Low Priority, and why. '
            "Write it in the answer form.</p>",
            "</section>",
        ]
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def write_sheet(cases_dir: Path, out: Path, protocol_path: Path, seed: int) -> list[Case]:
    protocol = load_protocol(protocol_path)
    cases = load_cases(cases_dir, protocol)
    criteria_path = cases_dir / "CRITERIA.md"
    criteria = criteria_path.read_text(encoding="utf-8").strip() if criteria_path.is_file() else None
    order = shuffled(cases, seed)
    out.mkdir(parents=True, exist_ok=True)
    (out / "labelling_sheet.html").write_text(
        sheet_html(order, str(protocol["reference_date"]), criteria), encoding="utf-8"
    )
    answers = _csv([ANSWER_HEADER, *[[number, "", ""] for number in range(1, len(order) + 1)]])
    (out / "labelling_answers.csv").write_text(answers, encoding="utf-8")
    write_xlsx(out / "labelling_answers.xlsx", answers)
    key = _csv([KEY_HEADER, *[[number, case.id] for number, case in enumerate(order, 1)]])
    (out / "labelling_key.csv").write_text(key, encoding="utf-8")
    return order


def _read_table(path: Path) -> list[list[str]]:
    if path.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook

        sheet = load_workbook(path, read_only=True, data_only=True).active
        return [["" if v is None else str(v) for v in row] for row in sheet.iter_rows(values_only=True)]
    text = path.read_text(encoding="utf-8-sig")
    # Excel in a Swedish locale saves with ";" between columns.
    delimiter = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def compare(cases: list[Case], key_rows: list[list[str]], answer_rows: list[list[str]]) -> tuple[list[dict[str, Any]], list[str]]:
    """The two labels side by side, and every problem with the filled-in form."""
    folder_of = {row[0].strip(): row[1].strip() for row in key_rows[1:] if len(row) >= 2 and row[0].strip()}
    by_id = {case.id: case for case in cases}
    problems: list[str] = []
    rows: list[dict[str, Any]] = []
    answered: set[str] = set()
    for row in answer_rows[1:]:
        cells = [*row, "", "", ""][:3]
        number = cells[0].strip().removesuffix(".0")
        if not number and not cells[1].strip():
            continue
        folder = folder_of.get(number)
        if folder is None or folder not in by_id:
            problems.append(f"Case {number}: not in the key, or its folder is gone")
            continue
        answered.add(number)
        decision = parse_decision(cells[1])
        if decision is None:
            problems.append(f"Case {number}: decision {cells[1].strip()!r} is not High Priority, Consider or Low Priority")
            continue
        case = by_id[folder]
        rows.append(
            {"number": number, "case": case, "second": decision, "reason": cells[2].strip(),
             "same": decision == case.first_label}
        )
    problems += [f"Case {n}: no answer" for n in folder_of if n not in answered and folder_of[n] in by_id]
    return sorted(rows, key=lambda r: r["case"].id), problems


def _print_comparison(rows: list[dict[str, Any]], problems: list[str]) -> None:
    for row in rows:
        mark = "same" if row["same"] else "DIFFERENT"
        print(f"{row['case'].id} (sheet case {row['number']})  author: {LABELS[row['case'].first_label]:<13}  "
              f"second: {LABELS[row['second']]:<13}  {mark}")
        if not row["same"] and row["reason"]:
            print(f"    second labeller's reason: {row['reason']}")
    same = sum(1 for r in rows if r["same"])
    print(f"\n{same} of {len(rows)} the same.")
    print("\nAdd to each case.yaml (and for a disagreement, after discussing it: set `reference` to the")
    print("settled decision, `first_label` to your own label if it changed, and `resolution`):\n")
    for row in rows:
        print(f"  {row['case'].id}/case.yaml:  second_label: {row['second']}")
    if problems:
        print("\nProblems with the form:\n- " + "\n- ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sheet = commands.add_parser("sheet", help="write the blind labelling sheet")
    sheet.add_argument("--cases", type=Path, required=True)
    sheet.add_argument("--out", type=Path, required=True)
    sheet.add_argument("--seed", type=int, default=1, help="order of the cases on the sheet")
    sheet.add_argument("--protocol", type=Path, default=REPO / "thesis" / "protocol.yaml")
    check = commands.add_parser("compare", help="compare the second labeller's answers with your labels")
    check.add_argument("--cases", type=Path, required=True)
    check.add_argument("--key", type=Path, required=True)
    check.add_argument("--answers", type=Path, required=True)
    check.add_argument("--protocol", type=Path, default=REPO / "thesis" / "protocol.yaml")
    args = parser.parse_args()

    try:
        if args.command == "sheet":
            order = write_sheet(args.cases, args.out, args.protocol, args.seed)
            print(f"Wrote the sheet for {len(order)} cases into {args.out}.")
            print("Give the labeller labelling_sheet.html and labelling_answers.xlsx (or .csv);")
            print("keep labelling_key.csv to yourself.")
            if not (args.cases / "CRITERIA.md").is_file():
                print(f"Note: no {args.cases / 'CRITERIA.md'}, so the sheet has no decision criteria.")
        else:
            cases = load_cases(args.cases, load_protocol(args.protocol))
            rows, problems = compare(cases, _read_table(args.key), _read_table(args.answers))
            _print_comparison(rows, problems)
            if problems:
                sys.exit(1)
    except CaseError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
