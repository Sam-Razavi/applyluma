# Thesis work

Everything in this folder belongs to the bachelor thesis "Designing and Evaluating an
AI-Assisted Decision Support System" (Stockholm University, DSV, IB015N). It was added
after the `pre-thesis-baseline` tag; what existed before is described in
[`docs/thesis/BASELINE.md`](../docs/thesis/BASELINE.md).

| File | What it is |
|---|---|
| [`DESIGN.md`](DESIGN.md) | Decision problem, objectives, architecture, decision rules and interaction design of the AI-assisted job-fit assessment |
| [`DESIGN_LOG.md`](DESIGN_LOG.md) | Every change to the prompts or rules after design v1, and why |
| [`protocol.yaml`](protocol.yaml) | The evaluation protocol: number of runs, the date given to the model, the thresholds that turn the rule-based score into a priority |
| [`practice_cases/`](practice_cases/) | Fictional cases used while building. Not evaluation cases; nothing measured on them is a result |
| [`eval/`](eval/) | The evaluation runner: both systems on the same cases, then the tables |
| `cases/` | The evaluation cases. Added after the freeze tag `thesis-prototype-v1` |
| `results/` | One folder per evaluation run, committed as produced |

Code of the component, outside this folder:

| Part | Location |
|---|---|
| Assessment logic: model steps, quote check, decision rules | `backend/app/services/fit_advisor/` |
| Storage, background task, API | `backend/app/models/fit_assessment.py`, `backend/app/crud/fit_assessment.py`, `backend/app/tasks/fit_assessment.py`, `backend/app/api/v1/endpoints/fit_assessments.py`, migration `0035` |
| Panel in the app | `frontend/src/components/discover/fit/` |
| Tests | `backend/tests/test_fit_advisor_*.py`, `backend/tests/test_fit_assessment_db.py`, `FitAssessmentPanel.test.tsx` |
| Runner tests, including the proof that the runner scores like production | `backend/tests/test_thesis_eval.py` |

## Running the evaluation

From the repository root, with the backend's Python packages installed and an OpenAI
key in `OPENAI_API_KEY`:

```bash
python -m thesis.eval.run --cases thesis/cases --out thesis/results/run-1
```

Each case is a folder with `cv.md`, `ad.md` and `case.yaml` (format and an example:
[`eval/cases.py`](eval/cases.py), [`practice_cases/`](practice_cases/)). The runner
refuses to start if a case is incomplete and lists every problem.

It writes into the `--out` folder:

| File | Content |
|---|---|
| `run.json` | What was run: code commit, model, seed, prompt, rules and protocol versions, a hash of every input text |
| `results.jsonl` | Every single run of both systems with its complete output |
| `summary.md` | The tables: correctness, consistency, robustness, transparency, missing information, reliability, and every case where a system differs from the reference |
| `summary.csv` | One line per case, variant and system, for tables and charts |
| `review_sheet.csv` | The first AI run of every case, one line per requirement, with empty columns for judging by hand whether each explanation is supported by the texts |

`--resume` continues a run that stopped, without repeating stored runs. `--report-only`
rebuilds the tables from `results.jsonl` without calling the model. Both refuse if the
cases, prompts, rules or model differ from the stored run.

Still to come: the freeze tag, the evaluation cases and the results.
