# Thesis work

Everything in this folder belongs to the bachelor thesis "Designing and Evaluating an
AI-Assisted Decision Support System" (Stockholm University, DSV, IB015N). It was added
after the `pre-thesis-baseline` tag; what existed before is described in
[`docs/thesis/BASELINE.md`](../docs/thesis/BASELINE.md).

| File | What it is |
|---|---|
| [`DESIGN.md`](DESIGN.md) | Decision problem, objectives, architecture, decision rules and interaction design of the AI-assisted job-fit assessment |
| [`DESIGN_LOG.md`](DESIGN_LOG.md) | Every change to the prompts or rules after design v1, and why |

Code of the component, outside this folder:

| Part | Location |
|---|---|
| Assessment logic: model steps, quote check, decision rules | `backend/app/services/fit_advisor/` |
| Storage, background task, API | `backend/app/models/fit_assessment.py`, `backend/app/crud/fit_assessment.py`, `backend/app/tasks/fit_assessment.py`, `backend/app/api/v1/endpoints/fit_assessments.py`, migration `0035` |
| Panel in the app | `frontend/src/components/discover/fit/` |
| Tests | `backend/tests/test_fit_advisor_*.py`, `backend/tests/test_fit_assessment_db.py`, `FitAssessmentPanel.test.tsx` |

Still to come: the practice cases, the evaluation protocol, the runner and the results.
