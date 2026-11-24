"""The thesis evaluation runner (thesis/eval): cases, tables, and the baseline adapter.

The adapter test at the end needs a real Postgres (CI sets TEST_DATABASE_URL): it
proves the runner scores a case exactly as production scores a posting. The posting
has no location, as a case has none; a location only adds "Location: ..." to the
explanation line and never changes a score.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from thesis.eval import labelling, report, rule_based_adapter, run  # noqa: E402
from thesis.eval.cases import CaseError, load_cases, load_protocol  # noqa: E402

PROTOCOL_PATH = REPO / "thesis" / "protocol.yaml"
PRACTICE = REPO / "thesis" / "practice_cases"
THRESHOLDS = {"high_priority_min": 86, "consider_min": 70}


def _output(priority: str, **extra: Any) -> dict[str, Any]:
    return {
        "recommendation": priority,
        "rule": "R1",
        "reason": "reason",
        "limited_information": False,
        "model_recommendation": priority,
        "summary": "summary",
        "missing_information": [],
        "requirements": [
            {
                "id": "R1", "text": "Python", "importance": "mandatory", "status": "met",
                "model_status": "met", "cv_quote": "Python", "cv_quote_found": True,
                "ad_quote_found": True, "downgraded": False, "note": "",
            }
        ],
        "quote_stats": {"ad_quotes": 1, "ad_quotes_found": 1, "cv_quotes": 1, "cv_quotes_found": 1, "downgraded": 0},
        "meta": {"latency_ms": 1000, "prompt_tokens": 1000, "completion_tokens": 100},
        **extra,
    }


def _write_case(root: Path, name: str, meta: str, extra: dict[str, str] | None = None) -> None:
    folder = root / name
    folder.mkdir()
    (folder / "cv.md").write_text("Skills\nPython, SQL, Git", encoding="utf-8")
    (folder / "ad.md").write_text("Python is required. SQL and Git too.", encoding="utf-8")
    (folder / "case.yaml").write_text(meta, encoding="utf-8")
    for filename, text in (extra or {}).items():
        (folder / filename).write_text(text, encoding="utf-8")


GOOD = "scenario: clear\nlanguage: en\nreference: high_priority\nrationale: All there.\n"


# ---- protocol and cases ----------------------------------------------------


def test_protocol_matches_the_design_decisions() -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    assert (protocol["runs_per_case"], protocol["runs_per_variant"]) == (5, 3)
    assert protocol["rule_based_thresholds"] == THRESHOLDS


def test_practice_cases_load() -> None:
    cases = load_cases(PRACTICE, load_protocol(PROTOCOL_PATH))
    assert [c.id for c in cases] == [
        "p1_clear_match_en", "p2_clear_mismatch_sv", "p3_missing_info_sv", "p4_instruction_in_ad_en",
        "p5_experience_short_en", "p6_experience_close_sv", "p7_experience_enough_en",
    ]
    assert {v.type for v in cases[0].variants} == {"name_swap", "irrelevant_text_in_ad"}
    assert len(cases[2].expected_missing) == 2


def test_case_problems_are_all_reported(tmp_path: Path) -> None:
    _write_case(tmp_path, "a", "scenario: nonsense\nlanguage: en\nreference: maybe\n")
    _write_case(
        tmp_path, "b", GOOD + "variants:\n  - id: v\n    type: name_swap\n    cv: missing.md\n"
    )
    with pytest.raises(CaseError) as error:
        load_cases(tmp_path, load_protocol(PROTOCOL_PATH))
    message = str(error.value)
    for expected in ("a: scenario", "a: reference", "a: rationale", "b: missing.md is missing"):
        assert expected in message


def test_an_unedited_copy_of_the_template_is_rejected(tmp_path: Path) -> None:
    """A copied template whose placeholders were never replaced must not be run."""
    import shutil

    shutil.copytree(REPO / "thesis" / "cases" / "_template", tmp_path / "c01_copy")
    case_yaml = tmp_path / "c01_copy" / "case.yaml"
    # Even with the variants block deleted, as the template tells you to.
    case_yaml.write_text(case_yaml.read_text(encoding="utf-8").split("variants:")[0], encoding="utf-8")
    with pytest.raises(CaseError) as error:
        load_cases(tmp_path, load_protocol(PROTOCOL_PATH))
    message = str(error.value)
    for expected in ("cv.md still has the template", "ad.md still has the template", "rationale is missing"):
        assert expected in message


def test_the_runner_lists_case_problems_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_case(tmp_path, "a", "scenario: nonsense\nlanguage: en\nreference: maybe\n")
    monkeypatch.setattr(sys, "argv", ["run", "--cases", str(tmp_path), "--out", str(tmp_path / "out")])
    with pytest.raises(SystemExit) as stopped:
        run.main()
    assert "a: scenario" in str(stopped.value.code)
    assert not (tmp_path / "out").exists()


def test_variant_identical_to_the_case_is_rejected(tmp_path: Path) -> None:
    _write_case(
        tmp_path, "a", GOOD + "variants:\n  - id: v\n    type: name_swap\n    cv: same.md\n",
        {"same.md": "Skills\nPython, SQL, Git"},
    )
    with pytest.raises(CaseError, match="identical"):
        load_cases(tmp_path, load_protocol(PROTOCOL_PATH))


# ---- measures --------------------------------------------------------------


def test_case_decision_is_the_most_frequent_and_a_tie_is_no_decision() -> None:
    assert report.case_decision(["consider"] * 4 + ["high_priority"]) == ("consider", 0.8)
    assert report.case_decision(["consider", "consider", "low_priority", "low_priority", "high_priority"])[0] is None
    assert report.case_decision([]) == (None, 0.0)


def test_agreement_separates_one_step_from_opposite() -> None:
    assert report.agreement("high_priority", "high_priority") == "exact"
    assert report.agreement("consider", "high_priority") == "one_step"
    assert report.agreement("low_priority", "high_priority") == "opposite"
    assert report.agreement(None, "consider") == "no_decision"


@pytest.mark.parametrize(
    ("score", "expected"),
    [(94.0, "high_priority"), (86.0, "high_priority"), (85.9, "consider"), (70.0, "consider"), (69.9, "low_priority"), (66.0, "low_priority")],
)
def test_rule_based_priority_thresholds(score: float, expected: str) -> None:
    assert rule_based_adapter.priority(score, THRESHOLDS) == expected


def test_missing_item_is_found_in_the_list_or_in_an_unknown_requirement() -> None:
    listed = _output("consider", missing_information=["Whether you hold a B-körkort"])
    assert report.missing_item_flagged(listed, ("körkort",))
    unknown = _output("consider")
    unknown["requirements"][0].update(status="not_enough_information", text="Driving licence")
    assert report.missing_item_flagged(unknown, ("driving licence",))
    assert not report.missing_item_flagged(_output("consider"), ("körkort",))


# ---- the runner end to end, with a stand-in for the model ------------------


def _run(tmp_path: Path, assess: Any, **kwargs: Any) -> tuple[Path, list[dict[str, Any]]]:
    cases_dir = tmp_path / "cases"
    if not cases_dir.exists():
        cases_dir.mkdir()
        _write_case(
            cases_dir, "c1",
            GOOD + "variants:\n  - id: swap\n    type: name_swap\n    cv: cv2.md\n",
            {"cv2.md": "Another Name\nSkills\nPython, SQL, Git"},
        )
        _write_case(cases_dir, "c2", GOOD.replace("high_priority", "low_priority"))
    out = tmp_path / "out"
    records = run.execute(
        cases_dir, out, PROTOCOL_PATH, systems=["ai", "rule_based"], assess=assess, log=lambda _: None, **kwargs
    )
    return out, records


def test_runner_makes_every_run_and_writes_the_tables(tmp_path: Path) -> None:
    seen: list[str] = []

    def assess(cv_text: str, ad_text: str, *, today: Any) -> dict[str, Any]:
        seen.append(today.isoformat())
        # The name-swapped CV flips the result, so robustness has something to report.
        return _output("consider" if "Another Name" in cv_text else "high_priority")

    out, records = _run(tmp_path, assess)

    ai = [r for r in records if r["system"] == "ai"]
    assert len(ai) == 5 + 3 + 5 and set(seen) == {"2026-12-01"}
    assert len([r for r in records if r["system"] == "rule_based"]) == 2 * 3
    assert len((out / "results.jsonl").read_text().splitlines()) == len(records)

    summary = (out / "summary.md").read_text()
    assert "| AI assessment | 2 | 1 of 2 (50%) | 0 | 1 | 0 |" in summary  # c2: high against low
    assert "| AI assessment | name_swap | 1 | 1 of 1 (100%) | 3 of 3 (100%) |" in summary
    assert "| Rule-based matcher | name_swap | 1 | 0 of 1 (0%) | 0 of 2 (0%) |" in summary
    assert "### `c2`" in summary and "### `c1`" not in summary.split("## 8.")[1].split("## 9.")[0].replace("c1`/", "")

    rows = (out / "summary.csv").read_text().splitlines()
    assert rows[0].startswith("case,variant,variant_type")
    assert any(row.startswith("c1,swap,name_swap") and row.endswith(",yes") for row in rows)
    assert (out / "review_sheet.csv").read_text().count("\nc1,1,") == 2  # summary line + one requirement

    info = json.loads((out / "run.json").read_text())
    assert info["prompt_version"] and info["protocol"]["runs_per_case"] == 5 and "finished_at" in info


def test_a_failed_run_is_recorded_and_resume_does_not_repeat_stored_runs(tmp_path: Path) -> None:
    calls = {"n": 0}

    def flaky(cv_text: str, ad_text: str, *, today: Any) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("model unavailable")
        return _output("high_priority")

    out, records = _run(tmp_path, flaky)
    failed = [r for r in records if r["error"]]
    assert len(failed) == 1 and failed[0]["priority"] is None
    assert "| Failed | 1 |" in (out / "summary.md").read_text()

    with pytest.raises(SystemExit):  # a second run into the same folder must not overwrite
        _run(tmp_path, flaky)

    before = calls["n"]
    _, again = _run(tmp_path, flaky, resume=True)
    assert calls["n"] == before and len(again) == len(records)


def test_resume_refuses_changed_cases(tmp_path: Path) -> None:
    out, _ = _run(tmp_path, lambda *a, **k: _output("high_priority"))
    (tmp_path / "cases" / "c2" / "cv.md").write_text("A different CV", encoding="utf-8")
    with pytest.raises(SystemExit, match="inputs differs"):
        _run(tmp_path, lambda *a, **k: _output("high_priority"), report_only=True)


def test_cost_uses_the_price_table() -> None:
    lines = report._reliability(
        [{"case": "c", "variant": None, "system": "ai", "run": 1, "priority": "consider", "output": _output("consider")}],
        (Decimal("2.50"), Decimal("10.00")),
    )
    assert any("0.00 / 0.0035" in line for line in lines)


# ---- the baseline adapter against the production path ----------------------


def test_adapter_job_data_has_the_production_keys() -> None:
    assert set(rule_based_adapter.job_data("x")) == {
        "description", "title", "salary_min", "salary_max", "location", "remote_allowed",
    }


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL")
@pytest.mark.parametrize("remote", [False, True])
def test_adapter_scores_exactly_like_production(remote: bool) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.main  # noqa: F401  (registers every model)
    from app.models.cv import CV
    from app.models.job import RawJobPosting
    from app.models.user import User
    from app.services.matching_service import MatchingService

    db = sessionmaker(bind=create_engine(os.environ["TEST_DATABASE_URL"]))()
    tag = uuid.uuid4().hex[:10]
    user = User(email=f"thesis-eval-{tag}@example.com", hashed_password="x")
    db.add(user)
    db.flush()
    try:
        cases = load_cases(PRACTICE, load_protocol(PROTOCOL_PATH))
        scores = set()
        for case in cases:
            db.query(CV).filter(CV.user_id == user.id).delete()
            db.add(CV(user_id=user.id, title="cv", filename="cv.md", content=case.cv_text, is_default=True))
            posting = RawJobPosting(
                source="thesis-test", job_id_external=uuid.uuid4().hex, raw_data={}, url=f"https://example.com/{tag}/{case.id}/{remote}",
                title="Any title", company="Any company", description=case.ad_text, remote_allowed=remote,
            )
            db.add(posting)
            db.flush()

            production = MatchingService(db).batch_compute_scores([user.id], [posting.id])[0]
            production.pop("user_id")
            production.pop("job_id")
            assert rule_based_adapter.score(case.cv_text, case.ad_text, remote=remote) == production
            scores.add(production["overall_score"])
        assert len(scores) > 1  # the cases really exercise different scores
    finally:
        db.rollback()
        db.close()


def test_excel_copy_keeps_swedish_text_and_every_cell(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    table = 'case,note\nc01,"Körkort saknas, kan ej bedömas"\nc02,"two\nlines"\n'
    assert run.write_xlsx(tmp_path / "review_sheet.xlsx", table)
    sheet = openpyxl.load_workbook(tmp_path / "review_sheet.xlsx").active
    assert [[c.value for c in row] for row in sheet.iter_rows()] == [
        ["case", "note"], ["c01", "Körkort saknas, kan ej bedömas"], ["c02", "two\nlines"],
    ]



# ---- the second labeller -----------------------------------------------------


def test_second_label_loads_and_differing_labels_need_a_resolution(tmp_path: Path) -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    _write_case(tmp_path, "c1", GOOD + "second_label: high_priority\n")
    _write_case(tmp_path, "c2", GOOD + "second_label: consider\n")
    _write_case(tmp_path, "c3", GOOD + "first_label: consider\n")
    _write_case(tmp_path, "c4", GOOD + "second_label: perhaps\n")
    with pytest.raises(CaseError) as error:
        load_cases(tmp_path, protocol)
    message = str(error.value)
    assert "c1" not in message
    assert "c2: the labels differ, so resolution" in message
    assert "c3: the labels differ, so resolution" in message
    assert "c4: second_label must be one of" in message

    for name in ("c2", "c3", "c4"):
        shutil.rmtree(tmp_path / name)
    _write_case(
        tmp_path, "c2",
        GOOD + "first_label: consider\nsecond_label: high_priority\nresolution: The degree is finished.\n",
    )
    first, second = load_cases(tmp_path, protocol)
    assert (first.first_label, first.second_label, first.resolution) == ("high_priority", "high_priority", "")
    assert (second.first_label, second.second_label, second.reference) == ("consider", "high_priority", "high_priority")


def test_cohen_kappa() -> None:
    assert report.cohen_kappa([("consider", "consider"), ("low_priority", "low_priority")]) == 1.0
    pairs = [("high_priority", "high_priority"), ("consider", "low_priority")]
    assert round(report.cohen_kappa(pairs) or 0, 2) == 0.33
    assert report.cohen_kappa([("consider", "consider")] * 3) is None  # one label only: undefined
    assert report.cohen_kappa([]) is None


def test_summary_shows_labeller_agreement_and_every_combination(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    _write_case(cases_dir, "c1", GOOD + "second_label: high_priority\n")
    _write_case(
        cases_dir, "c2",
        GOOD.replace("high_priority", "low_priority")
        + "first_label: consider\nsecond_label: low_priority\nresolution: SQL is a must, and it is missing.\n",
    )
    out, _ = _run(tmp_path, lambda *a, **k: _output("high_priority"))
    summary = (out / "summary.md").read_text()

    labellers = summary.split("## Reference decisions")[1].split("## 1.")[0]
    assert "| Cases with a second label | 2 of 2 (100%) |" in labellers
    assert "| Same label | 1 of 2 (50%) |" in labellers
    assert "| One step apart | 1 |" in labellers and "| Cohen's kappa | 0.33 |" in labellers
    assert "| Consider | 0 | 0 | 1 |" in labellers  # author Consider, second labeller Low
    assert "`c2`: author Consider, second labeller Low Priority; reference Low Priority." in labellers

    assert "2 of 18 combinations have a case." in summary
    assert "| clear | en | High Priority | 1 | 1 of 1 |" in summary
    assert "| unclear_or_missing | sv | Low Priority | 0 | - | - |" in summary
    assert "| clear | en | Low Priority | 1 | 0 of 1 |" in summary


def test_summary_says_when_no_case_has_a_second_label() -> None:
    cases = load_cases(PRACTICE, load_protocol(PROTOCOL_PATH))
    assert "No case has a second label." in report._labellers(cases)


def _labelling_cases(root: Path) -> None:
    for name, cv in (("c01_clear_match_en", "CV of Ada <script>"), ("c02_clear_mismatch_sv", "CV of Bo"),
                     ("c03_missing_info_en", "CV of Cy")):
        _write_case(
            root, name,
            GOOD.replace("All there.", "SECRET RATIONALE")
            + "variants:\n  - id: swap\n    type: name_swap\n    cv: cv2.md\n",
            {"cv2.md": "VARIANT TEXT"},
        )
        (root / name / "cv.md").write_text(cv, encoding="utf-8")


def test_labelling_sheet_shows_only_the_texts_and_the_key_matches_it(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    _labelling_cases(cases_dir)
    (cases_dir / "CRITERIA.md").write_text("Mandatory requirements weigh most.", encoding="utf-8")
    out = tmp_path / "labelling"
    labelling.write_sheet(cases_dir, out, PROTOCOL_PATH, seed=1)

    sheet = (out / "labelling_sheet.html").read_text(encoding="utf-8")
    for hidden in ("c01_", "clear_match", "SECRET RATIONALE", "VARIANT TEXT", "high_priority", "<script>"):
        assert hidden not in sheet
    assert "CV of Ada &lt;script&gt;" in sheet and "1 December 2026" in sheet
    assert "Mandatory requirements weigh most." in sheet

    key = labelling._read_table(out / "labelling_key.csv")
    assert key[0] == labelling.KEY_HEADER and len(key) == 4
    for number, folder in key[1:]:
        section = sheet.split(f"<h2>Case {number}</h2>")[1].split("</section>")[0]
        assert (cases_dir / folder / "cv.md").read_text(encoding="utf-8").replace("<", "&lt;").replace(">", "&gt;") in section
    answers = labelling._read_table(out / "labelling_answers.csv")
    assert answers == [labelling.ANSWER_HEADER, ["1", "", ""], ["2", "", ""], ["3", "", ""]]
    # The same seed gives the same order.
    again = tmp_path / "again"
    labelling.write_sheet(cases_dir, again, PROTOCOL_PATH, seed=1)
    assert (again / "labelling_key.csv").read_text() == (out / "labelling_key.csv").read_text()


@pytest.mark.parametrize(
    ("written", "expected"),
    [("High Priority", "high_priority"), ("high_priority", "high_priority"), (" consider ", "consider"),
     ("Låg prioritet", "low_priority"), ("Överväg", "consider"), ("LOW", "low_priority"), ("maybe", None), ("", None)],
)
def test_parse_decision(written: str, expected: str | None) -> None:
    assert labelling.parse_decision(written) == expected


def test_compare_reads_a_swedish_excel_csv_and_lists_every_problem(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    _labelling_cases(cases_dir)
    cases = load_cases(cases_dir, load_protocol(PROTOCOL_PATH))
    key = [labelling.KEY_HEADER, ["1", "c02_clear_mismatch_sv"], ["2", "c01_clear_match_en"],
           ["3", "c03_missing_info_en"]]
    form = tmp_path / "answers.csv"
    form.write_text(
        "Case;Decision;Reason\n1;Consider;Has most of it\n2;high priority;\n3;perhaps;\n9;Low;\n",
        encoding="utf-8-sig",
    )
    rows, problems = labelling.compare(cases, key, labelling._read_table(form))
    assert [(r["case"].id, r["second"], r["same"]) for r in rows] == [
        ("c01_clear_match_en", "high_priority", True), ("c02_clear_mismatch_sv", "consider", False),
    ]
    assert rows[1]["reason"] == "Has most of it"
    assert problems == [
        "Case 3: decision 'perhaps' is not High Priority, Consider or Low Priority",
        "Case 9: not in the key, or its folder is gone",
    ]

    form.write_text("Case,Decision,Reason\n1,Consider,\n", encoding="utf-8")
    _, problems = labelling.compare(cases, key, labelling._read_table(form))
    assert problems == ["Case 2: no answer", "Case 3: no answer"]
