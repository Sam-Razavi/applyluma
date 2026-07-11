# ApplyLuma AI Context

This file is the project source of truth for AI assistants working in the
ApplyLuma repository.

## Project Overview

- ApplyLuma is an AI-powered job search and resume optimization platform.
- Production frontend: https://applyluma.com
- Production backend: https://applyluma-production.up.railway.app
- Status: All phases through the Admin Control Center & GDPR Fixes (July 2026)
  are live in production on `main`. `dev` is synced with `main` as of 2026-07-11.
- All major features are working, including authentication, resume analysis, job
  search, job description management, the analytics dashboard, AI CV Tailor,
  Swedish job discovery with AI-powered match scoring, the browser extension, and
  the full admin control center (user management, activity timelines, health
  watchdog, database stats).

## Current Phase

- Phase 8: ✅ COMPLETE
- Phase 9: ✅ COMPLETE
- Test Infrastructure: ✅ COMPLETE
- Phase 10A: ✅ COMPLETE — Swedish Job Discovery & AI-Powered Job Matching
- Phase 10B: ✅ COMPLETE — Discover Integrations & Job Alerts
- Mobile UX Enhancement: ✅ COMPLETE — Responsive polish and motion
- Jobs Discovery Gap-fill & Search: ✅ COMPLETE — Search, skill gaps, bookmark API
- Browser Extension: ✅ COMPLETE — MV3 Chrome/Firefox extension
- Admin Dashboard / Pipeline Health: ✅ COMPLETE — /admin pages incl. pipeline health
- Job Sources & Dedupe (July 2026): ✅ COMPLETE — RemoteOK source, dynamic source
  filter, cross-source rolling-window dedupe, "Hide applied jobs" Discover filter
- Structured CV Tailoring & Templates (July 2026): ✅ COMPLETE — OpenAI Structured
  Outputs, Jinja2/WeasyPrint renderer, anti-fabrication hardening
- Admin Control Center & GDPR Fixes (July 2026): ✅ COMPLETE — activity timeline,
  login tracking, health watchdog + `/health?deep=1`, user delete/reset/verify/
  limits, `/admin/database` stats, account-deletion file erasure

Phase 9 delivered the AI CV Tailor feature end-to-end:
  - Celery worker tailors CV sections against a job description using OpenAI.
  - Users review section diffs, accept/reject changes, and save a tailored PDF.
  - Authenticated download endpoints serve PDFs for both uploaded and tailored CVs.
  - Tailored CVs appear in the My CVs tab with working view and download buttons.
  - Daily tailoring limits enforced per user role (user: 1, premium: 10, admin: unlimited).
  - Alembic migrations for tailor_jobs table and user role column included.

Phase 10A delivered Swedish job discovery end-to-end:
  - Airflow scrapes job boards daily at 2 AM UTC. (Sources listed here are
    historical — see the Job Sources & Dedupe section for the current set.)
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

Mobile modal/drawer buttons hidden behind MobileNav — root-caused and fixed for
good in July 2026 (PR branch `fix/applications-mobile-modal-buttons`), after an
earlier partial fix (commit `24c8ac8`, "stop card overflow and unreachable
buttons") left it recurring on the Applications page:
  - Root cause: every Headless UI `Dialog` in the app used `z-50`, but
    `MobileNav` (`fixed bottom-0`) is `z-[100]`. Any bottom-anchored dialog
    footer (e.g. `ApplicationDrawer`'s Save/Delete row) sits in the same
    screen region as the nav and rendered underneath it — invisible and
    untappable — on phones.
  - Fix: added a semantic `zIndex` scale in `tailwind.config.js` —
    `z-nav` (100, matches `MobileNav`), `z-modal` (110, any Dialog that must
    sit above the nav), `z-modal-nested` (120, confirm dialogs opened from
    inside another modal, e.g. delete confirmation inside a drawer). Applied
    to `MobileNav.tsx`, `ApplicationDrawer.tsx`, `AddApplicationModal.tsx`,
    and the shared `ConfirmDialog.tsx`. Footers also gained
    `padding-bottom: max(1rem, env(safe-area-inset-bottom))` so buttons clear
    the home-indicator/gesture-bar area on notched phones, and close (X)
    buttons got a visible background chip + larger icon for contrast.
  - Verified with real DOM measurement at a true 390×844 mobile viewport
    (`elementFromPoint` hit-testing on the Save/Delete/Close buttons — see
    "iframe-at-390px verification trick" for how to get a real mobile
    viewport when `resize_window` fails on a maximized Chrome window).
  - Other `z-50` dialogs in the app (Settings, CVs, Jobs, AdminUsers,
    VersionDiffViewer) were left untouched — they either use a different,
    already-working clearance strategy (`pb-24` wrapper padding, e.g.
    `JobDetail.tsx`/`SearchJobDetail.tsx`) or haven't been reported broken.
    Any NEW bottom-anchored dialog should use `z-modal` (or `z-modal-nested`
    if it can be opened from inside another dialog) rather than bare `z-50`.

Jobs Discovery Gap-fill & Search delivered in June 2026:
  - Backend `search` param on `GET /api/v1/jobs` (title/company ILIKE, debounced 350ms).
  - Skill-gap analysis in job detail: `matched_skills` / `missing_skills` populated via
    KeywordExtractor against the user's default CV.
  - `POST /api/v1/jobs/bookmark` and `GET /api/v1/jobs/bookmark/saved-urls` endpoints.
  - `GET /api/v1/auth/extension-token` — mints bearer TokenPair for cookie-authenticated
    users (extension can't access httpOnly cookies directly).
  - `GET /api/v1/applications/applied-urls` — list of job URLs already tracked.
  - Production backfill: 808/810 jobs have `extracted_keywords`; 810 `job_matching_scores`
    for the primary account.
  - Data sources in `JOB_SOURCES` / `SOURCE_LABELS` updated to match actual DB values:
    `JobSearch API`, `the_muse`, `remotive`.
  - Prominent full-width debounced search bar added to Discover page (above filters).
  - 3 new backend test files (see Test Infrastructure section).

Browser Extension delivered in June 2026 (`applyluma-extension/`):
  - MV3 Chrome/Firefox extension with popup, background service worker, and per-site
    content scripts for LinkedIn, Indeed SE (`se.indeed.com`), Glassdoor, and
    Arbetsformedlingen.
  - Bearer token auth stored in `chrome.storage.local` with automatic refresh on 401.
  - 30-minute alarm refreshes saved/applied URL sets; badge text shows saved-job count.
  - `Alt+Shift+S` quick-save keyboard shortcut bookmarks the current job without popup.
  - `/extension-auth` page in the web app mints a bearer token and auto-copies to clipboard.
  - JOB_SITE_PATTERNS covers `se.indeed.com`, `arbetsformedlingen.se`, and
    `www.arbetsformedlingen.se`.

Job Sources & Dedupe delivered in July 2026:
  - New RemoteOK scraper (`airflow/plugins/job_scrapers/remoteok_client.py`) in the
    `scrape_jobs` DAG. Scrapers in the repo: `remotive`, `the_muse`, `remoteok`
    (scrape_jobs, 02:00 UTC) and `platsbanken`, `jobbsafari`, `indeed_se`
    (scrape_swedish_jobs, 02:30 UTC). Source strings are lowercase in the DB.
  - `GET /api/v1/jobs/sources` returns distinct sources with live posting counts;
    the Discover source filter populates from it (static `JOB_SOURCES` is only a
    fallback). New sources need no frontend changes.
  - Cross-source rolling-window dedupe (`airflow/plugins/job_scrapers/dedupe.py`,
    used by both scrape DAGs): a posting scraped today is marked `is_duplicate`
    when a live posting with the same normalised title+company+location exists
    within the last 14 days, regardless of source. Oldest posting wins; only
    today's rows are ever marked by the daily run.
  - `scripts/backfill_duplicates.py` applies the same rule to historical rows
    (dry run by default, `--apply` to mark). Run once against Railway.
  - "Hide applied jobs" filter: `hide_applied` param on `GET /api/v1/jobs`
    (filters on the user-scoped Application join) plus a checkbox in the
    Discover filters sidebar.

Structured CV Tailoring & Templates delivered in July 2026 (branch
`feature/structured-cv-templates`):
  - The tailor call now uses OpenAI Structured Outputs (strict `json_schema`,
    still `gpt-4o`): the model returns typed content (`header`, `summary`,
    `skills.groups`, `experience[]`, `projects[]`, `education[]`,
    `certifications`, `additional_sections[]`, `section_order`) instead of
    free-text section blobs. Schema lives in
    `backend/app/services/cv_render/structure.py`.
  - `result_json` now carries both `structured_cv` (for rendering) and the
    derived legacy `sections` list, so the diff-review UI works unchanged.
    Old jobs without `structured_cv` still save via the legacy ReportLab path.
  - New renderer package `backend/app/services/cv_render/`: Jinja2 HTML
    templates rendered to PDF with WeasyPrint. Two templates: `nordic`
    (navy/teal Scandinavian design, default) and `classic` (monochrome ATS).
    `POST /tailor/{id}/save` accepts optional `template_id`.
  - Rejected/overridden sections render as raw text blocks inside the same
    template, so mixed accept/reject output still looks consistent.
  - Page-length enforcement: after generation the worker renders a probe PDF;
    if it exceeds 2 pages, one compress retry is sent to the model and the
    shorter result wins (`_COMPRESS_PROMPT` in `tailor_service.py`).
  - Fabricated-skill validation now checks structured `skills.groups` and
    project `stack` items with token-ngram matching ("Java" no longer matches
    inside "JavaScript"; "Node js" still matches "Node.js"). Header
    email/phone/links are validated against the source CV and dropped if absent.
  - Anti-fabrication (July 2026 hardening): `temperature=0.2` on the tailor
    call (0.3 for cover letters); a mandatory second "self-audit" GPT pass
    (`_VERIFY_PROMPT`) re-checks every claim against the source CV; and a
    deterministic numeric guard (`_remove_unsupported_numbers`) drops any
    bullet or summary sentence containing a number that appears nowhere in
    the source CV. Every tailor job therefore makes at least 2 OpenAI calls
    (3 with the compress retry).
  - `get_or_create_from_raw_job` recovers from the `uq_jd_user_raw_job`
    unique-index race (CV tailor + cover letter submitted in parallel for the
    same Discover job used to 500 with "Failed to start" on first click).
  - WeasyPrint needs native Pango libs: installed in `backend/Dockerfile`
    (also `fonts-inter`); NOT available on Windows dev machines, where
    `cv_render.is_available()` is False and everything falls back to the
    legacy ReportLab renderer. The 2 real-PDF tests skip locally and were
    verified inside the Docker image.
  - Template picker UI: `TemplatePicker.tsx` in the AI Tailor review step
    (mini CSS thumbnails, `CvTemplateId` type); the choice is sent as
    `template_id` on CV save and as the `?template=` query param on cover
    letter download.
  - Cover letters render through the matching template family
    (`cover_nordic.html` / `cover_classic.html`) with the candidate
    letterhead extracted from the CV contact block;
    `GET /cover-letters/{id}/download?template=` falls back to the legacy
    ReportLab renderer when WeasyPrint or a contact block is missing.

Also shipped and easy to miss (verified 2026-07-08):
  - Stripe billing: checkout, webhook, and customer-portal endpoints
    (`endpoints/billing.py`) with Plans / BillingSuccess / BillingCancel pages.
  - Google OAuth login (`endpoints/auth_google.py`, `/auth/callback` page).
  - In-app notifications UI: `NotificationBell` + `NotificationList` with
    mark-one/mark-all-read; high-match alert task writes notification rows.
  - Cover letter generator: `cover_letter_service.py`, `endpoints/cover_letters.py`,
    Celery task, history on the AI Tailor page.
  - Application status timeline (`ApplicationEvent` rows rendered by
    `ApplicationTimeline.tsx`) and client-side CSV export
    (`frontend/src/utils/exportCsv.ts`) on the Applications page.
  - Expired jobs (deadline passed — Platsbanken has deadline data) are hidden
    from the Discover feed via `_is_live_deadline_clause` (migration `0024`).
  - Feedback & contact inbox (July 2026): the public Contact form persists to
    `contact_submissions` (migration 0026), and the authenticated in-app
    feedback form (`POST /api/v1/feedback`, `/feedback` page, category
    bug/feature/question/other) stores into the same table with
    `source='in_app'` + `user_id` (migration 0027) and emails
    `CONTACT_RECIPIENT_EMAIL`. Admins triage everything at `/admin/contact`
    (status new/read/replied/archived, category filter, audit-logged), with a
    new-message count badge on the admin sidebar. On mobile the feedback form
    is reached via Profile -> Settings -> "Send feedback".
  - AI cost tracking (July 2026): every OpenAI call records tokens + computed
    USD cost into `ai_usage_logs` (`services/ai_usage.py`; recording never
    raises and never blocks the AI feature). Prices per model live in
    `PRICES_PER_MTOK`. Admin dashboard at `/admin/ai-costs` (stat cards, daily
    chart, by-feature breakdown, top users) with an admin-configurable monthly
    budget (`app_settings` KV table) that emails CONTACT_RECIPIENT_EMAIL once
    at 80% and once at 100% per month. Migration `0028_ai_usage_logs.py`.

Admin Control Center & GDPR Fixes delivered in July 2026 (merged via PR #127,
branches `claude/admin-panel-review-4f5992` + earlier GDPR-fix work):
  - Login tracking: `users.last_login_at` / `users.login_count`, updated on
    password login, the OAuth2-form login endpoint, and Google OAuth callback
    (`crud_user.record_login`). Surfaced in `/admin/users` (Last Login column)
    and the user profile drawer.
  - Per-user activity timeline: `GET /admin/users/{id}/activity` builds a
    chronological feed via a SQL `UNION ALL` across CVs, applications,
    application events, tailor jobs, cover letters, saved jobs, job
    descriptions, and contact submissions (`crud_admin.get_user_activity`,
    `crud/admin.py`). Rendered in the "Timeline" section of
    `frontend/src/pages/admin/UserDrawer.tsx` (extracted out of `AdminUsers.tsx`
    for size), with "Load more" pagination.
  - Health watchdog: `app/tasks/watchdog.py` (Celery task
    `run_health_watchdog`, beat schedule `*/15` minutes) checks db/redis/celery
    (reusing `endpoints/health.py` probes), pipeline freshness, and an AI
    tailor/cover-letter failure spike (`WATCHDOG_FAILURE_SPIKE_THRESHOLD`,
    default 5/hour). State persisted in `app_settings` key
    `health_watchdog_state`; emails `CONTACT_RECIPIENT_EMAIL` only on a state
    transition (mirrors the AI budget alert throttle pattern), never on repeat
    degraded runs. `GET /health?deep=1` added for external uptime monitors
    (returns 503 on a real DB check failure; plain `/health` stays instant for
    Railway's own health probe). Live red/amber status banner
    (`AdminStatusBanner.tsx`, polls every 60s) mounted in `AdminRoute.tsx`
    above all `/admin/*` pages. Full setup guide: `docs/MONITORING.md`
    (three layers — UptimeRobot external pinger, the watchdog, and Sentry;
    Sentry's `ErrorBoundary.tsx` gap for caught render errors was also closed).
  - User management additions in `endpoints/admin.py` /
    `frontend/src/pages/admin/UserDrawer.tsx`, all audit-logged: `DELETE
    /admin/users/{id}` (Postgres FK cascades handle child rows; blocks
    self-delete and deleting other admins; requires typing the user's email in
    a `ConfirmDialog` with the new `requireText` prop); `POST
    /admin/users/{id}/password-reset` (reuses `crud_user.create_password_reset_token`
    + the existing reset-email flow); `PATCH /admin/users/{id}/verify`;
    `PATCH /admin/users/{id}/limits` sets `users.daily_tailor_limit_override`
    (nullable int: `None` = role default, `0` = blocked, N = that many/day),
    read via `tailor.py`'s `effective_daily_limit(user)`; per-user AI spend
    (30d/all-time) added to the profile response.
  - `GET /admin/database/stats` + `/admin/database` page: per-table row counts
    (`pg_class.reltuples`), sizes (`pg_total_relation_size`), and 7/30-day
    growth for tables with a `created_at`/`scraped_at` column — read-only,
    fixed SQL only, no client-controlled table/column names.
  - Migration `0029_admin_user_controls.py` adds `users.last_login_at`,
    `users.login_count`, `users.daily_tailor_limit_override`. Alembic chain
    currently ends at `0029`.
  - GDPR fix bundled into the same PR: `DELETE /api/v1/auth/me` (self-service
    account deletion) now erases the user's `cvs/{user_id}/` and
    `cover_letters/{user_id}/` subtrees under `STORAGE_DIR` after the DB
    commit (`crud_user.delete` → `_remove_user_files`, disk errors logged and
    swallowed, never block deletion). `delete_user_admin` (the admin-delete
    path above) calls the same helper so both delete paths leave no orphaned
    files. Register page now shows a terms/privacy agreement notice.
  - Validation: backend `pytest` 570 passed, `ruff check` and `mypy app/`
    clean; frontend `npm test` 245 passed, `npm run type-check` and
    `npm run build` passed. CI (`.github/workflows/ci.yml`) also runs ESLint
    and mypy — mypy caught one real gap during this work (the new
    `app.tasks.watchdog` module wasn't in `pyproject.toml`'s
    `[[tool.mypy.overrides]]` exemption list that every other Celery task
    module uses for the untyped `@celery_app.task` decorator; fixed by adding
    it, matching the sibling task modules).

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
- `.github/workflows/ci.yml`: CI for backend (ruff, mypy, pytest) and frontend
  (ESLint, `tsc --noEmit`, Vitest, `npm run build`). mypy runs in `strict`
  mode; new modules with untyped decorators (e.g. `@celery_app.task`) must be
  added to `backend/pyproject.toml`'s `[[tool.mypy.overrides]]` list like
  their sibling modules, or CI fails.
- `docs/MONITORING.md`: three-layer monitoring setup (UptimeRobot external
  pinger, internal health watchdog, Sentry) — read before touching
  `app/tasks/watchdog.py` or `/health`.

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

29 test files as of 2026-07-11 (245 tests); representative files, not exhaustive
— run `find frontend/src -name '*.test.ts*'` for the full current list:
- `src/stores/auth.test.ts` — auth store (login, logout, setUser, setLoading)
- `src/pages/Login.test.tsx` — Login page (render, validation, success, error)
- `src/utils/formatters.test.ts` — currency, date, percentage, titleCase formatters
- `src/pages/Discover.test.tsx` — job feed, save flow, empty state, error toast
- `src/pages/SavedJobs.test.tsx` — saved jobs load, star, delete, collection tabs
- `src/pages/admin/AdminAiCosts.test.tsx` — stat cards, budget save/validation, top users
- `src/pages/admin/AdminPipeline.test.tsx` — pipeline health cards and charts
- `src/pages/admin/AdminUsers.test.tsx` — last-login column, drawer timeline/AI-spend,
  delete-requires-typed-email, tailor-limit save/clear
- `src/pages/admin/AdminDatabase.test.tsx` — table stats rendering, error state
- `src/components/layout/AdminStatusBanner.test.tsx` — hidden when healthy, red/amber
  banner on unhealthy/degraded, 60s poll (fake timers)
- `src/components/ui/ConfirmDialog.test.tsx` — default behavior unchanged,
  `requireText` gating, clears typed value on cancel
- `src/components/ui/ErrorBoundary.test.tsx` — fallback UI, chunk-load reload,
  Sentry `captureException` reporting

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

45 test files as of 2026-07-11 (570 tests); representative files, not exhaustive
— run `ls backend/tests/*.py` for the full current list:
- `tests/test_cv_endpoints.py` — CV upload, list, get, update, set-default, delete
- `tests/test_jd_endpoints.py` — job description create, list, get, delete
- `tests/test_tailor_downloads.py` — authenticated PDF download endpoints
- `tests/test_tailor_endpoints.py` — AI tailor job endpoints, including
  `effective_daily_limit` (admin override vs. role default) coverage
- `tests/test_tailor_service.py` — tailor service unit tests (structured outputs contract)
- `tests/test_tailor_regression.py` — tailoring regressions: dropped data, fabricated skills
- `tests/test_cv_render.py` — structured CV renderer: context, HTML templates, PDF (skips
  the 2 real-PDF tests where WeasyPrint native libs are missing, e.g. Windows)
- `tests/test_jobs_endpoints.py` — job discovery list/detail/keywords + all saved-jobs CRUD
- `tests/test_matching_service.py` — CV-to-job match scoring unit tests
- `tests/test_application_endpoints.py` — application tracking CRUD
- `tests/test_application_analytics.py` — application analytics endpoint
- `tests/test_notifications.py` — notification list, mark-read, stale-app task
- `tests/test_billing_endpoints.py` — Stripe checkout, webhook, portal
- `tests/test_health_endpoints.py` — health/detailed-health checks + `/health?deep=1`
  (instant on plain, 503 on real DB failure)
- `tests/test_cv_history_endpoints.py` — CV history tree and diff endpoints
- `tests/test_job_search_endpoints.py` — Adzuna job search + caching
- `tests/test_job_crud.py` — `_compute_skill_gap` unit tests (matched/missing, no-CV, no-keywords)
- `tests/test_job_bookmark_endpoint.py` — bookmark creation, idempotency, scoring, notes, saved-urls (14 tests)
- `tests/test_extension_support.py` — extension-token and applied-urls endpoints (4 tests)
- `tests/test_admin_endpoints.py` — core admin endpoints (stats, users list/role/active,
  ai-jobs, pipeline, raw-jobs, system health, audit logs, billing, contact, ai-costs)
- `tests/test_admin_user_controls.py` — activity timeline, delete (incl. GDPR file
  erasure via `crud_admin.delete_user_admin`), password-reset, verify, tailor-limit
  override, `/admin/database/stats`
- `tests/test_watchdog.py` — health watchdog state transitions (ok→degraded emails
  once, repeat-degraded silent, new failing check re-emails, recovery email)
- `tests/test_auth_security.py` — token revocation, refresh edge cases, forgot/reset
  password, login-records-last-login, account-deletion file erasure (GDPR)
- `tests/test_auth_google.py` — Google OAuth login/callback flow + login tracking
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

Two workflows run on push/PR to `main` and `dev`:

- `.github/workflows/data-pipeline-tests.yml`:
  - `airflow-tests` job: installs pinned packages, runs both airflow test files.
  - `dbt-tests` job: installs pinned dbt, runs `dbt deps` then `dbt parse`.
- `.github/workflows/ci.yml`:
  - `backend` job (`Backend — lint, type-check, test`): `ruff check app/`,
    `mypy app/` (strict mode — see Key Files note on `[[tool.mypy.overrides]]`),
    then `pytest`.
  - `frontend` job (`Frontend — lint, type-check, test`): `npm run lint`
    (ESLint), `npm run type-check` (`tsc --noEmit`), `npm test` (Vitest),
    `npm run build`.

Vercel runs its own TypeScript build check and preview deploy on every PR — all
TS errors block merge.

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

- 570 backend tests and 245 frontend tests passing as of 2026-07-11.
- `npm install` reported 2 moderate frontend dependency vulnerabilities; do not
  run `npm audit fix --force` casually because it can introduce breaking
  dependency upgrades.
- GitHub CLI (`gh`) is not installed in the local Codex environment; use the
  GitHub connector or install `gh` for CLI-based PR workflows.
- `job_market_metrics` freshness depends on the `transform_jobs` DAG running in
  Airflow. The aggregation code has no per-source coupling (verified 2026-07-08),
  so any staleness is operational, not a code defect — check `/admin/pipeline`
  for current status.
- The health watchdog (`app/tasks/watchdog.py`) only fires if a Celery **beat**
  service is deployed separately from the web/worker services (see
  `backend/railway.beat.json` / `scripts/start-beat.sh`) — verify that service
  exists in Railway, since none of the other scheduled tasks (deadline
  reminders, weekly summary, high-match alerts) fire without it either.
- Verify an external uptime pinger (e.g. UptimeRobot) is configured against
  `/health?deep=1` — it's the only monitoring layer that catches a total
  process crash; see `docs/MONITORING.md` for setup steps.

## Next Steps

- Resume the standard `dev → feature branch → dev → main` workflow for all new work.
- Admin Dashboard / Pipeline Health has shipped: `/admin/pipeline` health panel plus
  charts, backed by read-only endpoints under `/api/v1/admin/pipeline/`.
- Admin Control Center has shipped (see July 2026 phase entry above): activity
  timeline, login tracking, health watchdog, `/admin/database`, and the
  delete/password-reset/verify/tailor-limit user controls.
- Post-deploy follow-ups from the Admin Control Center work: confirm
  `alembic upgrade head` applied migration `0029` on Railway; confirm a
  Celery beat service is running so the watchdog and other scheduled tasks
  actually fire; set up an external uptime pinger per `docs/MONITORING.md`;
  verify `SENTRY_DSN` (backend) and `VITE_SENTRY_DSN` (frontend) are set.
- Run `scripts/backfill_duplicates.py` once against Railway to mark historical
  cross-source duplicates (see Job Sources & Dedupe section).
- Backlog (verified open as of 2026-07-08): keyword tag filtering on Discover,
  duplicate-application warning (same-company check), CV completeness score,
  follow-up reminders, granular alert preferences, Platsbanken delisted-ad
  re-check task, additional Phase 10B edge-case tests. `FEATURE_IDEAS.md`
  checkboxes are the authoritative list — several items were confirmed built
  and ticked on 2026-07-08.
- Run the full test suite (`pytest`, `npm test`) before merging any new feature work.

## AI Development Guidelines

When working on this project:
- Always work in `dev` or create a feature branch from `dev`. `dev` is synced
  with `main` as of 2026-07-11.
- Test in `dev` before merging to `main`. Never push breaking changes to `main`.
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
