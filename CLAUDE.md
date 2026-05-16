# ApplyLuma AI Context

This file is the project source of truth for AI assistants working in the
ApplyLuma repository.

## Project Overview

- ApplyLuma is an AI-powered job search and resume optimization platform.
- Production frontend: https://applyluma.com
- Production backend: https://applyluma-production.up.railway.app
- Status: Phase 10B implemented on `dev` and ready for PR review. Production
  remains on the last merged release until `dev` is merged to `main`.
- All major features are working, including authentication, resume analysis, job
  search, job description management, the analytics dashboard, AI CV Tailor, and
  Swedish job discovery with AI-powered match scoring.

## Current Phase

- Phase 8: ✅ COMPLETE
- Phase 9: ✅ COMPLETE
- Test Infrastructure: ✅ COMPLETE
- Phase 10A: ✅ COMPLETE — Swedish Job Discovery & AI-Powered Job Matching
- Phase 10B: ✅ IMPLEMENTED ON DEV — Discover Integrations & Job Alerts
- Mobile UX Enhancement: ✅ IMPLEMENTED ON DEV — Responsive polish and motion

Phase 9 delivered the AI CV Tailor feature end-to-end:
  - Celery worker tailors CV sections against a job description using OpenAI.
  - Users review section diffs, accept/reject changes, and save a tailored PDF.
  - Authenticated download endpoints serve PDFs for both uploaded and tailored CVs.
  - Tailored CVs appear in the My CVs tab with working view and download buttons.
  - Daily tailoring limits enforced per user role (user: 1, premium: 10, admin: unlimited).
  - Alembic migrations for tailor_jobs table and user role column included.

Phase 10A delivered Swedish job discovery end-to-end:
  - Airflow scrapes Platsbanken, Jobbsafari, and Indeed.se daily at 2 AM UTC.
  - AI match scoring compares each job against the user's CV (skills, experience,
    salary, education, location) and caches results in Redis (24h TTL).
  - Keyword extraction (technical skills, frameworks, tools, soft skills, languages,
    certifications) stored in extracted_keywords with 7-day cache.
  - Discover page (/discover): filterable, paginated job feed with match score bars.
  - Saved Jobs page (/saved-jobs): bookmark jobs into named collections, star/delete,
    open detail modal, collection tabs filter view.
  - JobFilters sidebar collapses on mobile via chevron toggle.
  - Three new database tables: saved_jobs, extracted_keywords, job_matching_scores.
  - Alembic migration 0008_phase_10a_tables.py applied to Railway.
  - 104 backend tests, 38 frontend tests — all passing.

Phase 10B integrates job discovery with the rest of the app:
  - Discover jobs can be added directly to application tracking via
    `applications.raw_job_posting_id`; the backend hydrates company, title, URL,
    source, salary, location, and remote type from `raw_job_postings`.
  - Discover jobs can launch AI CV Tailor directly. The tailor endpoint accepts
    either `job_description_id` or `raw_job_posting_id`; raw jobs are converted
    into reusable job descriptions with `source_raw_job_posting_id` deduping.
  - Discover job detail now shows structured score and skill breakdowns instead
    of plain explanation text.
  - High-match job alerts are implemented with user alert preferences, sent-job
    dedupe logs, a daily Celery Beat task, notification rows, and email template
    support.
  - Settings page (`/settings`) lets users enable alerts, set threshold, and
    choose daily or weekly frequency.
  - New Alembic chain: `0009_application_raw_job_link.py`,
    `0010_jd_source_raw_job.py`, `0011_user_alert_preferences.py`.
  - `alembic upgrade head` ran successfully through `0011` on 2026-05-16.
  - Validation on 2026-05-16: backend `pytest` 104 passed, frontend `npm test`
    38 passed, `npm run type-check` passed, `npm run build` passed, backend
    `ruff` passed.

Mobile UX enhancement pass improves frontend responsiveness and interaction polish:
  - Added `framer-motion` and `@use-gesture/react`; `react-dropzone` was already
    present.
  - Consolidated mobile navigation around `MobileNav.tsx` with animated drawer
    and overlay; removed the duplicate inline mobile nav from `Navbar.tsx`.
  - Raised mobile touch targets for nav, global `.input`, CV upload controls, and
    CV list action buttons.
  - Improved CV upload layout on small screens and animated upload progress.
  - Added Discover skeleton cards, staggered job-card entry animation, and
    mobile-stacked Job Detail actions.
  - Added AI Tailor step transitions and animated SectionDiff content with the
    tablet two-column breakpoint moved to `md:`.
  - Added shared animation constants in `frontend/src/lib/animations.ts`,
    reusable `FadeIn`, reusable `SkeletonCard`, and reduced-motion CSS support.
  - Validation on 2026-05-16: frontend `npm run type-check` passed, `npm test`
    38 passed, `npm run build` passed. Bundle gzip increased by about 38.6 kB,
    within the mobile plan target.

## Git Workflow

Branch structure:
- `main`: Production branch. Pushes auto-deploy to Railway and Vercel.
- `dev`: Development and integration testing branch.

Standard workflow:
- Work in `dev` or a feature branch based on `dev`.
- Test thoroughly before production merge.
- Merge to `main` only when ready for production.
- Pushing `main` triggers automatic deployment, usually within about 3 minutes.

Collaboration workflow for Claude Code + Codex:
- Claude creates a feature branch, for example `feature/claude-work`.
- Codex creates a feature branch, for example `feature/codex-work`.
- Both feature branches merge into `dev`.
- Resolve conflicts and test in `dev`.
- Merge `dev` to `main` for production deployment.

Critical rule:
- Never push breaking changes to `main`.

## Tech Stack

Backend:
- FastAPI
- PostgreSQL
- Redis
- Docker on Railway

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS on Vercel
- framer-motion for mobile polish and page/element transitions
- @use-gesture/react is installed for future gesture enhancements

Data:
- Apache Airflow
- dbt
- Daily ETL pipeline

AI:
- OpenAI API for resume analysis

External APIs:
- Adzuna for job search

## Deployment

- Backend: Railway, https://applyluma-production.up.railway.app
- Frontend: Vercel, https://applyluma.com
- Database: Railway PostgreSQL, populated with analytics data.
- Cache: Railway Redis.
- Auto-deploy: push to `main` -> about 3 minutes to production.

## Key Files

- `backend/Dockerfile`: Railway deployment. Uses shell form `CMD` so Railway
  expands `$PORT`.
- `backend/railway.json`: Forces Railway to use the Dockerfile builder.
- `backend/app/main.py`: FastAPI application entrypoint and CORS configuration.
- `frontend/vercel.json`: Vercel configuration with rewrites.
- `airflow/dags/`: Job scraping and dbt transform DAGs.
- `.github/workflows/data-pipeline-tests.yml`: CI for Airflow + dbt tests.

## Environment Variables

Railway:
- `PORT=8080`
- `DATABASE_URL`
- `REDIS_URL`
- API keys and service secrets

Vercel:
- `VITE_API_URL`

Credentials:
- All production credentials are configured in Railway and Vercel dashboards.
- All credentials are documented in the Phase 8 summary.
- Never commit secrets or real `.env` files.

## Test Infrastructure

All tests live alongside the code they test. Run them before merging to `main`.

### Frontend — Vitest + React Testing Library

Location: `frontend/src/`
Run: `cd frontend && npm test`

Files:
- `src/stores/auth.test.ts` — auth store (login, logout, setUser, setLoading)
- `src/pages/Login.test.tsx` — Login page (render, validation, success, error)
- `src/utils/formatters.test.ts` — currency, date, percentage, titleCase formatters
- `src/pages/Discover.test.tsx` — job feed, save flow, empty state, error toast
- `src/pages/SavedJobs.test.tsx` — saved jobs load, star, delete, collection tabs

Setup: `vite.config.ts` has `test: { globals: true, environment: 'jsdom' }`.
The `src/test/setup.ts` imports `@testing-library/jest-dom`.

Rules for adding frontend tests:
- Mock `authApi` via `vi.mock('../services/api')` — do not call real endpoints.
- The `TokenPair` type requires `{ access_token, token_type, refresh_token }` —
  all three fields are required in mocks.
- Reset store state in `beforeEach` via `useAuthStore.getState().logout()`.

### Backend — pytest (async, ASGI transport)

Location: `backend/tests/`
Run: `cd backend && pytest`

Files:
- `tests/test_cv_endpoints.py` — CV upload, list, get, update, set-default, delete
- `tests/test_jd_endpoints.py` — job description create, list, get, delete
- `tests/test_tailor_downloads.py` — authenticated PDF download endpoints
- `tests/test_tailor_endpoints.py` — AI tailor job endpoints
- `tests/test_tailor_service.py` — tailor service unit tests
- `tests/test_jobs_endpoints.py` — job discovery list/detail/keywords + all saved-jobs CRUD
- `tests/test_matching_service.py` — CV-to-job match scoring unit tests
- `tests/test_application_endpoints.py` — application tracking CRUD
- `tests/test_application_analytics.py` — application analytics endpoint
- `tests/test_notifications.py` — notification list, mark-read, stale-app task
- `tests/test_billing_endpoints.py` — Stripe checkout, webhook, portal
- `tests/test_health_endpoints.py` — health and detailed health checks
- `tests/test_cv_history_endpoints.py` — CV history tree and diff endpoints
- `tests/test_job_search_endpoints.py` — Adzuna job search + caching
- Phase 10B alert preference endpoints and high-match alert task are implemented;
  add focused endpoint/task tests when extending alert behavior further.

Pattern: tests use `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))`
and `app.dependency_overrides` to inject `FakeDb` and a stub user — no real
database needed. Always clear overrides in an `autouse` fixture.

Rules for adding backend tests:
- Use `monkeypatch.setattr(module, "attr", ...)` to mock CRUD and service calls.
- Patch at the endpoint module level (e.g. `cvs_endpoint.crud_cv`), not the
  source module, so the monkeypatch takes effect where it is used.
- Use `@pytest.mark.asyncio` on every async test function.

### Data Pipeline — pytest + dbt parse

#### Airflow tests

Location: `airflow/tests/`
Run: `PYTHONPATH=$(pwd)/airflow/dags:$(pwd)/airflow/plugins pytest airflow/tests/`

Files:
- `tests/test_dag_integrity.py` — DagBag loads cleanly, expected DAGs present,
  no cycles (`dag.validate()`), required parameters set
- `tests/test_dag_logic.py` — skill extraction regex, DB connection string,
  daily metrics calculation

Rules for adding Airflow tests:
- Always export `PYTHONPATH` to include both `airflow/dags` and `airflow/plugins`
  so plugin imports resolve without the Docker-only `/opt/airflow/plugins` path.
- In CI, install airflow packages individually — do NOT use `airflow/requirements.txt`
  directly because it contains `sqlalchemy>=2.0.0` which conflicts with
  `apache-airflow==2.7.0` (requires SQLAlchemy <2.0).
- Pin `pendulum<3.0` alongside airflow — pendulum 3.x changed `tz.timezone()` to
  a module, breaking `airflow/settings.py` on import.
- Use `dag.validate()` for cycle checks — `dag.test_cycle()` was removed in Airflow 2.x.
- Use `dag.default_args.get("retries", 0)` for retry checks — `dag.retries` does
  not exist on the DAG object; retries are a task-level attribute set via `default_args`.

#### dbt tests

Location: `dbt/tests/` (SQL assertions) and `dbt/` (parse check)
Run: `cd dbt && dbt deps --profiles-dir . && dbt parse --profiles-dir .`

Files:
- `tests/assert_job_title_length.sql`
- `tests/assert_remote_percentage_valid.sql`
- `tests/assert_required_job_fields_present.sql`
- `tests/assert_salary_min_less_than_max.sql`
- `tests/assert_skill_count_positive.sql`
- `tests/assert_valid_job_dates.sql`

Rules for adding dbt tests:
- Always run `dbt deps` before `dbt parse` — `dbt_utils` must be installed first.
- Pin `dbt-postgres` to `>=1.7.0,<1.8.0` in CI — `pip install dbt-postgres`
  without a pin installs beta versions (e.g. 1.12.0-b1) that are incompatible.
- `dbt_utils.recency` is a TABLE-level test. Never place it under a column's
  `tests:` block — dbt injects `column_name` for column-level tests, which the
  `recency` macro does not accept, causing a compilation error.
- Do not run `dbt compile` in CI — it requires a live database connection.
  `dbt parse` alone validates project structure without a DB.

### CI

`.github/workflows/data-pipeline-tests.yml` runs on push/PR to `main` and `dev`:
- `airflow-tests` job: installs pinned packages, runs both airflow test files.
- `dbt-tests` job: installs pinned dbt, runs `dbt deps` then `dbt parse`.

Vercel runs its own TypeScript build check on every PR — all TS errors block merge.

## Recent Critical Fixes

- Fixed Railway `$PORT` expansion by changing Docker `CMD` from exec form to
  shell form.
- Removed the conflicting `Procfile`.
- Added/configured `backend/railway.json` to force the Dockerfile builder.
- Populated analytics data in Railway PostgreSQL.
- Fixed analytics dashboard production failures.
- All analytics endpoints now return 200 OK.
- Added `refresh_token` to `TokenPair` mock in `Login.test.tsx` to fix Vercel
  TypeScript build failure.
- Fixed CI workflow dependency conflicts (sqlalchemy, pendulum, dbt beta).
- Fixed Airflow 2.x API incompatibilities in DAG integrity tests.
- Fixed `dbt_utils.recency` placement from column-level to table-level.
- Fixed alembic `.env` loading: `config.py` now resolves `.env` relative to its
  own file location (project root) rather than CWD, so `alembic upgrade head`
  works from any directory. Use public Railway proxy URL
  (`viaduct.proxy.rlwy.net:38089`) in `.env` DATABASE_URL when running locally
  against Railway — the `.railway.internal` host is only reachable inside Railway.

## Known Issues

- No known Phase 10B code issues after local validation.
- `npm install` reported 2 moderate frontend dependency vulnerabilities; do not
  run `npm audit fix --force` casually because it can introduce breaking
  dependency upgrades.
- GitHub CLI (`gh`) is not installed in the local Codex environment; use the
  GitHub connector or install `gh` for CLI-based PR workflows.

## Next Steps

- PR from `dev` to `main` is open for Phase 10B plus mobile UX enhancements.
- Review CI and mobile behavior, then merge `dev` to `main` when ready for
  production deployment.
- Phase 10C candidate areas: in-app surfacing for high-match notifications,
  Discover filter for jobs already in Applications, richer alert preferences,
  and additional frontend/backend tests for Phase 10B edge cases.
- Continue using the `dev` -> `main` workflow.
- Use feature branches for AI collaboration.
- Run the relevant test suite before merging any future Phase 10C work.

## AI Development Guidelines

When working on this project:
- Always work in `dev` or create a feature branch from `dev`.
- Never push directly to `main` unless it is an emergency hotfix.
- Test in `dev` before merging to `main`.
- Use Railway logs to verify backend deployments.
- Check both Railway and Vercel for production status.
- Remember that analytics endpoints require a populated database.
- Airflow runs daily at 2 AM UTC for scraping.
- Airflow/dbt transforms run daily at 3 AM UTC.
- Keep credentials in environment variables only.
- Prefer existing backend, frontend, Airflow, and dbt patterns before adding new
  abstractions.
- When adding new API endpoints, add a corresponding test in `backend/tests/`.
- When adding new frontend pages or stores, add a corresponding test in
  `frontend/src/`.
- When modifying DAG logic or dbt models, verify tests still pass locally before
  pushing.

## Repository Knowledge Graph

The `graphify-out/` directory exists but all generated output files are
gitignored (`graph.json`, `graph.html`, `GRAPH_REPORT.md`, `wiki/`).

To regenerate locally: `graphify update .`

Do not commit graphify output — these files are large, auto-generated, and
excluded by `.gitignore`.
