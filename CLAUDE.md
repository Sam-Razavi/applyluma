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
  - October 2026 mobile audit moved the remaining overlays onto the scale too:
    Jobs add/delete, CVs delete, Settings delete-account, `VersionHistory`
    (`z-modal`) with `VersionDiffViewer` above it (`z-modal-nested`, it opens
    from inside the history panel), the admin `UserDrawer` and notify modal,
    and `CookieBanner` (was `z-50`, so its buttons sat under MobileNav and
    could not be tapped on app pages). Only `JobDetail.tsx` /
    `SearchJobDetail.tsx` still use `z-50`, on purpose: they clear the nav
    with `pb-24` wrapper padding and keep it visible. Any NEW dialog or
    bottom-fixed bar should use `z-modal` (or `z-modal-nested` if it can be
    opened from inside another dialog) rather than bare `z-50`.
  - Text fields are forced to 16px below `md` (`index.css`), because iOS
    Safari zooms in on focus of any smaller field and never zooms back out.

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
  - Store-release prep (October 2026, v1.0.0, branch
    `claude/extension-store-release`): `scripts/package.sh` validates the
    manifest + JS syntax and builds `dist/applyluma-extension-<ver>.zip` (same
    zip for Chrome Web Store and Firefox AMO); CI `extension` job runs it and
    uploads the zip as an artifact. Listing copy, permission justifications,
    data disclosures and 1280x800 screenshots live in `store/`
    (`STORE_LISTING.md`, regenerate images with `node store/generate-assets.js`).
    `tabs` permission dropped (host permissions already cover `tabs.query`
    on job sites, so no "browsing history" install warning). Manifest carries
    both `background.service_worker` (Chrome) and `background.scripts`
    (Firefox) plus Firefox `data_collection_permissions`. Real "AL" icons
    replaced the placeholder squares. Privacy policy section 5 "Browser
    Extension" discloses what it reads/sends/stores; disconnecting now also
    clears the cached saved/applied URL lists to match that wording.
    Chrome Web Store: 1.0.0 published November 2026.
  - 1.0.1 (November 2026): extraction moved to `content/common.js`, loaded
    before each site script. The popup (and Alt+Shift+S) now asks the active
    tab to extract on demand (`EXTRACT_JOB` message) instead of reading a
    snapshot taken 0.8 s after load, which missed lazily rendered fields and
    could describe another tab. Missing fields fall back to the page's
    schema.org JobPosting JSON-LD (HTML double-decoded: LinkedIn
    entity-escapes it) and, on LinkedIn, the "Title | Company | LinkedIn"
    document title. LinkedIn search/collection panes (`?currentJobId=`) and
    Indeed search panes (`?vjk=`) count as job pages, with canonical
    `/jobs/view/<id>/` and `/viewjob?jk=` URLs. Intensity values are now
    light/medium/aggressive.
  - Server-side compatibility for the released 1.0.0: the bookmark response
    also carries `raw_job_posting_id` (1.0.0 read that name and got
    undefined, so match score, "Track application" and AI Tailor silently did
    nothing), and `TailorSubmitRequest` maps "low"/"high" to light/aggressive.

Job Sources & Dedupe delivered in July 2026:
  - New RemoteOK scraper (then `airflow/plugins/job_scrapers/remoteok_client.py`, now
    `backend/app/services/job_scrapers/remoteok.py`) in the
    `scrape_jobs` DAG. Scrapers in the repo: `remotive`, `the_muse`, `remoteok`
    (scrape_jobs, 02:00 UTC) and `platsbanken`, `jobbsafari`, `indeed_se`
    (scrape_swedish_jobs, 02:30 UTC). Source strings are lowercase in the DB.
  - `GET /api/v1/jobs/sources` returns distinct sources with live posting counts;
    the Discover source filter populates from it (static `JOB_SOURCES` is only a
    fallback). New sources need no frontend changes.
  - Cross-source rolling-window dedupe (now `backend/app/services/job_scrapers/dedupe.py`,
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
    November 2026: the bell had only ever been rendered by the old top
    `Navbar`, which the sidebar layout stopped using, so no notification
    (admin messages, high-match alerts, email suggestions, reminders) was
    visible and the unread dots never lit. `Navbar.tsx`/`navLinks.ts` were
    deleted; `AppLayout` now loads notifications and refreshes them every
    60 s, with a bell in the sidebar header (desktop) and a phone header.
    Clicking a notification opens the page its type is about. Admin
    "Notify" (`POST /admin/users/{id}/notify`) takes `send_email`; a failed
    email returns 502 with the in-app notification already saved.
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
    `crud/admin/users.py`). Rendered in the "Timeline" section of
    `frontend/src/pages/admin/UserDrawer.tsx` (extracted out of `AdminUsers.tsx`
    for size), with "Load more" pagination.
  - Health watchdog: `app/tasks/watchdog.py` (Celery task
    `run_health_watchdog`, beat schedule `*/15` minutes) checks db/redis
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
    currently ends at `0030` (`0030_user_preferred_template.py`).
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

CV Templates & Tailor UX batch (July 2026, PR #134 + follow-up branch
`claude/app-improvements-templates-l0gy4a`):
  - Two new CV template families alongside nordic/classic: `modern` (violet
    accents, skill chips) and `executive` (centered serif, formal small-caps),
    each with a matching cover-letter template. Registered in
    `cv_render/renderer.py` TEMPLATES/COVER_TEMPLATES; endpoints validate
    against those dicts, so adding a template needs no endpoint changes.
  - Template preview with real data: `POST /tailor/{job_id}/preview-html`
    returns the Jinja2-rendered CV HTML (no WeasyPrint needed, works after
    save too; 409 for pre-structured legacy jobs). Frontend
    `TemplatePreviewModal.tsx` shows it in a sandboxed iframe (`z-modal`) with
    in-modal template switching, opened from the AI Tailor review step.
  - Preferred template: `users.preferred_template` (migration `0030`),
    exposed on `UserPublic`/`UserUpdate` (validated against TEMPLATES),
    "Default CV template" select in Settings, used as the AI Tailor starting
    template (`resolveTemplate` narrows unknown values to nordic).
  - Password policy: shared `app/core/password_policy.py` (min 8 + letter +
    digit + common-password blocklist) wired into register/change/reset
    schemas; `PasswordStrengthMeter.tsx` extracted from Register and reused
    on Reset Password and Settings change-password.

Atlas & Compact CV templates (July 2026, branch `claude/cv-templates-scope-r92q4w`):
  - Two more template families, bringing the total to six: `atlas` (two-column
    with an emerald sidebar for skills/education/certifications; float-based
    layout because WeasyPrint cannot fragment flex containers across page
    breaks) and `compact` (dense single-column, ~11mm margins / 9pt type, for
    fitting more into the 2-page limit), each with a matching cover-letter
    template. Atlas fixes column assignment by block kind (raw/unknown blocks
    fall through to the main column) and only follows `section_order` within
    each column. Backend needed just the dict entries + 4 HTML files; the
    parametrized `test_cv_render.py` tests auto-cover new templates. Frontend
    additions when adding a template: `CvTemplateId` union (`types/tailor.ts`),
    `TEMPLATE_OPTIONS` (`templateOptions.ts`), a thumb in `TemplatePicker.tsx`,
    and the `TEMPLATE_IDS` narrowing array in `AITailor.tsx`.
  - Photo/image templates were considered and deliberately deferred: they
    require a whole photo-upload pipeline (endpoint, resize, storage under
    `cvs/{user_id}/`, GDPR erasure), not just a template — treat as a
    separate feature.

Multi-provider login (July 2026, branch `claude/app-improvements-templates-l0gy4a`):
  - LinkedIn OAuth (OIDC, `auth_linkedin.py`) and GitHub OAuth
    (`auth_github.py`, with `/user/emails` fallback for null public emails)
    alongside Google. Shared plumbing (state store/consume, auth cookies,
    success/failure redirects) extracted to `endpoints/oauth_common.py`;
    generalized `crud_user.upsert_oauth_user` (google/linkedin/github id
    columns; `upsert_google_user` is now a thin wrapper). Migration
    `0032` does not exist yet — chain ends at `0031_oauth_provider_ids.py`
    (`users.linkedin_id` / `users.github_id`).
  - Magic-link email sign-in (existing accounts only, enumeration-safe):
    `POST /auth/magic-link` (Redis `magic_login:{token}`, 15 min, single
    use, rate-limited 3/min) + `POST /auth/magic-link/verify` (returns
    TokenPair + cookies like password login, marks user verified);
    `/magic-login` frontend route consumes the emailed link.
  - `GET /auth/providers` reports which methods are configured
    (client IDs / RESEND_API_KEY); `useAuthProviders` hook +
    `OAuthButtons.tsx` render only enabled buttons on Login/Register
    (Google-only fallback if the fetch fails). `GoogleLoginButton.tsx`
    was removed.
  - New Railway env vars when enabling: `LINKEDIN_CLIENT_ID/SECRET/
    REDIRECT_URI`, `GITHUB_CLIENT_ID/SECRET/REDIRECT_URI` (redirect URIs
    point at `/api/v1/auth/{provider}/callback`). Code ships dark (501 +
    hidden button) until set.

Inbound Email Ingestion (August 2026, first slice):
  - Users forward job mail to `u-{inbox_token}@{INBOUND_EMAIL_DOMAIN}`; an
    inbound-parse vendor accepts SMTP delivery and POSTs the parsed message to
    `POST /api/v1/inbound/email`. Chosen over Gmail/Graph API integration
    because forwarding is provider-agnostic (Hotmail, Gmail, custom domains all
    work with one code path) and avoids Google's restricted-scope security
    assessment.
  - **Scope is deliberately ingest + match + admin view only** — no
    classification, no notifications, no status changes, no `ApplicationEvent`
    writes, no user-facing UI. The open question is whether an arbitrary
    recruiter email can be matched to the right application; everything else
    waits on that answer.
  - Vendor-agnostic adapter in `app/services/inbound_email/`: `base.py`
    (`NormalizedEmail` + `InboundAdapter` Protocol), `generic.py` (HMAC-SHA256
    over the raw body — works with a Cloudflare Email Worker and with `curl`),
    `registry.py`. Adding Postmark/Mailgun/SendGrid means one sibling module
    plus a registry entry; nothing else changes.
  - `matcher.py` is a pure function (`score_email`) with no DB or I/O. Signals:
    job_url domain (90), company-name/sender-domain (80), ATS sender + company
    in subject (75), company in subject (60), ATS + company in body (55).
    Threshold 70; below it the row is stored **unmatched** with the reasoning
    preserved. Matching is on the `From:` header, never the envelope sender —
    forwarding rewrites the envelope to the user's own address.
  - Retention is metadata + a 2000-char snippet, never full bodies. Truncation
    happens in the endpoint **before** enqueueing, because the Celery broker is
    itself durable storage. `ondelete="CASCADE"` on `user_id` handles erasure.
  - Admin view at `/admin/inbound-mail` (`GET /api/v1/admin/inbound-emails`)
    shows what arrived, what it matched to, the confidence, and the reason.
  - Migration `0032_inbound_emails.py` adds the table plus `users.inbox_token`
    (backfilled for existing users). Alembic chain now ends at `0032`.
  - Env vars: `INBOUND_EMAIL_VENDOR`, `INBOUND_EMAIL_DOMAIN`,
    `INBOUND_EMAIL_WEBHOOK_SECRET`. The webhook returns 503 until the secret
    and domain are set, so the feature ships dark.
  - Ops before it can receive mail: MX record for the `in.` subdomain at
    Namecheap (never touch the apex MX), vendor webhook pointed at Railway, and
    `alembic upgrade head` (which runs itself on deploy via
    `scripts/start-web.sh`). Full runbook: `docs/INBOUND_EMAIL.md`.
  - Mailgun adapter (September 2026): `mailgun.py` alongside `generic.py`.
    Mailgun posts a **form** body (multipart, or urlencoded with no
    attachments) and carries its signature **inside the body**, not a header —
    which is why `InboundAdapter.verify` takes raw bytes. Signature is
    `HMAC_SHA256(webhook_signing_key, timestamp + token)`; that key is NOT the
    sending API key. Parses the envelope `recipient` (a BCC'd forwarding
    address appears nowhere in To) and the `from` **header**, prefers
    `stripped-text` over `body-plain`, and skips attachment parts unread. No
    timestamp-freshness check on purpose: Mailgun retries for hours and a
    narrow window would reject real mail, while replay is already neutralised
    by the dedupe key.
  - Address format lives in `address.py` (`build_inbox_address` /
    `parse_inbox_token`) so the webhook and the admin view cannot drift.
    `inbox_address` is exposed on `AdminUserProfile` and rendered with a copy
    button in `UserDrawer.tsx` — **admin-only**, because the token is a bearer
    credential and there is no user-facing privacy copy yet.
  - Suggestions slice (September 2026): `classifier.py` reads what an email
    *says* — rejection / interview / offer / acknowledged — with keyword
    phrases in **English and Swedish** (diacritics folded, so ASCII phrase
    lists match "Tyvärr"). Pure function, no model call: rejections and
    invitations are formulaic enough that keywords cover most real mail, and
    starting here shows how far that gets before paying for an LLM. Ambiguous
    mail returns None rather than guessing. `SUGGEST_THRESHOLD = 70`; bare
    "unfortunately" and acknowledgements score 50 so they are recorded without
    prompting anyone.
  - **Nothing is applied automatically.** A suggestion is raised only when the
    email was *both* matched to an application *and* confidently classified;
    it writes a notification and a `pending` row, and the user confirms on the
    Applications page (`EmailSuggestions.tsx`). Accepting goes through
    `crud_application.update_application`, so the timeline records it exactly
    like a manual change. `suggestion_state` (none/pending/accepted/dismissed)
    is also the guard against one email prompting twice.
  - The evidence sentence is always shown with a suggestion: a prompt whose
    reasoning is invisible is one nobody can sensibly accept ("we'll keep your
    CV on file" is exactly the phrasing that fools a keyword matcher).
  - Migration `0033_inbound_email_suggestions.py`; Alembic chain ends at `0033`.
  - `/applications/email-suggestions` routes are declared **before**
    `/{application_id}` — FastAPI matches in declaration order, and the literal
    path was otherwise parsed as a UUID and 422'd (there is a regression test).
  - User-facing slice (November 2026): `GET /email-forwarding` (+ `/rotate`)
    gives the owner their address, received count, and Gmail's forwarding
    confirmation code/link (Gmail emails it *to* the forwarding address, so the
    user could never read it otherwise); `EmailForwardingCard.tsx` in Settings
    renders it with Gmail/Outlook setup steps. Visible to admins once
    configured, to everyone when `INBOUND_EMAIL_USER_ENABLED=true`.
    Manual forwards are unwrapped (`forwarded.py`: Gmail/Outlook/Apple, English
    and Swedish header blocks) in the webhook before truncation, and the
    Mailgun adapter keeps `body-plain` for forwards, because `stripped-text`
    removes the forwarded part. Confidently classified but unmatched mail is
    offered on the Applications page (`UnmatchedEmails.tsx`,
    `/applications/email-unmatched` list/assign/dismiss); assigning applies the
    status through `update_application`. Privacy policy section 6 covers it.
  - Inbox (November 2026): an "Inbox" tab on Applications (`EmailInbox.tsx`,
    shown when forwarding is enabled for the user) lists the user's own
    forwarded mail via `GET /email-forwarding/messages` (filter matched /
    not matched, paginated, Gmail confirmations excluded) with what was
    detected, what it matched and the suggestion state; `DELETE
    /email-forwarding/messages/{id}` removes one. The Settings card hides
    Gmail's confirmation prompt once later mail has arrived (or the user
    clicks "I've confirmed it"), and its Outlook steps use "Redirect to",
    which keeps the recruiter as `From:`.
  - Extension sign-in: `/extension-auth` opens in a new tab with no in-memory
    token, and a cookie-only POST cannot pass the CSRF check from
    applyluma.com (the `csrf_token` cookie belongs to the API's domain), so
    the page first trades the refresh cookie for an access token
    (`authApi.refresh`). Signed out, it links to `/login?next=/extension-auth`;
    `lib/nextPath.ts` keeps `next` in sessionStorage so Google/LinkedIn/GitHub
    sign-in (via `/auth/callback`) returns there too.
  - New-tab sessions (November 2026): the auth store persists to
    sessionStorage (per tab), so every new tab (extension buttons, bookmarks,
    email links) used to land on the login page despite a valid cookie.
    `lib/session.ts` `restoreSession()` trades the refresh cookie for a
    session, once per page load: `ProtectedRoute` tries it before redirecting
    (and redirects with `?next=`), and `App` tries it at startup when the
    `applyluma_signed_in` localStorage hint (set by the store on login, cleared
    on logout) says this browser has signed in. Settings > Sign out now calls
    `/auth/logout` too; it used to clear only the page, leaving the cookie
    session alive for the next tab to restore.
  - Google sign-in logout loop (November 2026): the API client used to strip
    the bearer token from every `/api/v1/analytics/*` request ("public"),
    but `/analytics/freshness` needs a signed-in user, so it relied on the
    cookie. OAuth callbacks run on `GOOGLE_REDIRECT_URI`'s host
    (`api.applyluma.com`), so Google users' cookies are on that host, not the
    `VITE_API_URL` host the app calls; the dashboard's freshness call 401'd,
    the refresh failed and they were logged out right after signing in. The
    client now always sends the bearer, and `complete_oauth_login` puts the
    refresh token in the callback fragment too (`#token=…&refresh=…`) so OAuth
    sessions renew from memory like password ones. Pointing `VITE_API_URL`
    at `https://api.applyluma.com` would put all cookies on one same-site
    host (also fixing iOS, which blocks railway.app cookies as third-party).
  - Login: `get_by_email` is case-insensitive, and a failed password login on
    an OAuth-only account (no password) says which provider to use instead of
    "Incorrect email or password"; register's 409 says the same.
  - Known gaps, deliberate: `message/rfc822` "forward as attachment" is not unwrapped;
    registrable-domain uses last-two-labels so multi-part suffixes like
    `.co.uk` degrade to a missed match.


Job retention & alert fixes (October 2026, fixes issues #77 and #92):
  - Daily Celery task `app/tasks/job_retention.py` (beat 01:00 UTC):
    archives postings whose deadline passed or that are older than 30 days
    (`raw_job_postings.archived_at`, migration `0034`; Alembic chain ends at
    `0034`), strips archived unreferenced postings' description/raw_data and
    deletes their keywords and match scores, and deletes archived postings
    90 days later. Postings a user saved or applied to keep their content
    and are never deleted while referenced. The slim row is kept 90 days
    because the scrapers insert with `ON CONFLICT DO NOTHING`; deleting an
    ad still listed at its source would let it be re-inserted as new.
  - "Live" for every user-facing job surface is `crud.job._is_live_deadline_clause`
    (not archived AND deadline not passed): Discover, sources, match
    scoring, and high-match alerts all use it.
  - High-match alerts: removed the `computed_at > last_sent_at` filter
    (dedupe is `job_alert_sent_log`; that filter could suppress alerts
    forever), `_is_due` has 1h slack so a run firing a moment early is not
    skipped, and the alert moved to 04:30 UTC, after the 03:30 scoring.
  - Retention runs in committed batches (500 rows, at most 40 per night):
    the first single-transaction run filled the 1 GB volume and crash-looped
    Postgres (volume since resized to 5 GB). The 30-day age rule is skipped
    while scraping is stale (no posting scraped in 2 days), so a stopped
    pipeline cannot empty Discover; expired deadlines are still archived.
  - The Airflow pipeline (Astro Cloud) stopped writing around 2026-09-12;
    by 2026-11-01 retention had archived ~120k of ~126k postings before the
    age-rule pause shipped. The watchdog's permanent "celery" alarm (a solo
    worker cannot answer inspect() while running the watchdog) masked the
    real "pipeline" alert and was removed.

Job pipeline moved to Railway Celery (November 2026, replaces Astro/Airflow):
  - One Celery task, `app.tasks.job_pipeline.run_job_pipeline` (beat 02:00
    UTC, on the existing worker), runs the old four DAGs' work in order:
    scrape (remotive, the_muse, remoteok, platsbanken)
    → `mark_todays_duplicates` → skill tagging (Platsbanken's own skill
    lists, else the `TRACKED_SKILLS` regex) →
    keywords (`extract_keywords_simple`, batches of 500 until done) →
    `job_market_metrics` upsert → salary analytics → queue
    `compute_job_matching_scores(user_id, chain=True)` per active user.
  - Each step is isolated (a failure is logged and the rest still run), and
    each source plus `extracted_keywords`, `transform_jobs` and
    `salary_analytics` writes a `pipeline_run_log` row, which
    `/admin/pipeline` and the watchdog's `pipeline` check read. A source
    whose every request fails now raises instead of reporting 0 jobs.
  - dbt is not run in production: `refresh_salary_analytics` rebuilds the
    only two marts the app reads, `analytics.fct_job_postings` and
    `analytics.agg_salary_insights`, with SQL ported from the dbt models
    (built under `*_build` names and swapped in by rename). Slimmed/archived
    postings drop out via the staging length filter. `dbt/` stays in the
    repo and CI still parses it.
  - `compute_job_matching_scores(chain=True)` keeps chaining 200-posting
    batches until no unscored live posting is left (it used to score only
    the newest 200 per user per day).
  - `POST /admin/pipeline/run` (admin, audit-logged) queues a run; 409 while
    one holds the Redis lock `job_pipeline:lock` (TTL 1h). "Run pipeline now"
    button on `/admin/pipeline`.
  - Jobbsafari was dropped: its RSS feed returns 404 and it has no API.
  - Platsbanken searches all of Sweden (November 2026): the whole Data/IT
    occupation field (concept `apaJ_2ja_LuF`, paged in 7-day publication
    windows to stay under JobTech's 2000 offset cap) plus a keyword list for
    tech roles filed under other fields, limited to ads published in the last
    30 days. Was 17 keywords x 5 municipalities x first 100 hits (~750 ads);
    now ~2,100 ads across ~200 locations, ~2 min per run, ~10 KB per ad.
  - Match scoring fixes (November 2026, found by a full end-to-end run on a
    real database): job skills now come from the same extractor the pipeline
    stores and the job page shows (`keyword_extraction.scored_skills`), counting
    only technical skills/frameworks/tools/certifications, not soft skills or
    spoken languages. `Go`/`Rust`/`Spring` match only in exact case ("go the
    extra mile" was tagged Go on 79 ads). Skill score = coverage x evidence
    (full credit from 5 matched skills; 1/1 no longer scores 100), and a job
    with no recognisable skills scores 30, not 70 (vague ads used to outrank
    real matches). The nightly chained run rescores anything older than 24 h,
    so production picks this up within a night or two with no backfill.
  - One skill vocabulary and one matching rule (November 2026):
    `services/keyword_extractor.py` holds every term, its category,
    `EXACT_CASE_ONLY` (Go, Rust, Spring, REST, Teams, Express, Linear, ...
    count only when capitalised; "engineering teams" was tagged Microsoft
    Teams on 1 in 7 ads) and `match_skill`. The pipeline's job keywords
    (`job_scrapers/keyword_extraction.py`) are a curated 46-term subset of it,
    so job pages stay low-noise. `job_scrapers/skills.py` `TRACKED_SKILLS` is
    deliberately separate: it feeds the salary-by-skill analytics.
  - `hide_applied=true` on `GET /jobs` 500'd on Postgres from 2026-10-20: the
    URL-match NOT EXISTS reused the joined `Application` entity and SQLAlchemy
    correlated every table away. It now uses an alias; a regression test
    compiles the real query for Postgres (FakeDb tests never compile SQL).
  - Indeed SE (via Adzuna, `country=se`) was dropped too: Adzuna has no Sweden
    endpoint, so every call 404s. It never worked under Airflow either — the
    old code swallowed per-query errors and logged "success, 0 jobs"; the
    Railway version raises when every request fails, which surfaced it. As
    the last source to run, its failure also marked the whole scraping stage
    `failed` for the watchdog. The Adzuna key is still used by the web Job
    Search tab (other countries).
  - Scraper errors are redacted (`job_scrapers.base.redact`): requests puts
    the full URL with query string into error messages, so the Adzuna
    `app_key` was being written to Railway logs and `pipeline_run_log` before
    this fix.
  - Fixed while porting: `BaseScraper.save_to_db` reported only the last
    100-row page's inserts (execute_values paging), so busy sources were
    under-counted in the run log.
  - Real-database coverage: `tests/test_job_pipeline_db.py` (opt-in via
    `TEST_DATABASE_URL`, like `test_job_retention.py`).
  - First production run (2026-11-01, manual): 897 new postings, every step
    succeeded, watchdog back to `ok`. Follow-ups: match scoring is queued
    only for active users **with a default CV** (scoring everyone made the
    first catch-up ~9 h of worker time), and the settings read the Adzuna key
    as `ADZUNA_API_KEY` **or** `ADZUNA_APP_KEY` — Railway uses the latter, so
    the app had been calling Adzuna keyless (the health check only looked at
    the app ID, so it reported "configured"; it now requires both).

Analytics page fixes (November 2026):
  - Point-in-time analytics count only live postings: `LIVE_POSTINGS_SQL` in
    `app/db/queries/analytics_queries.py` (not duplicate, not archived, deadline
    not passed; the raw-SQL twin of `crud.job._is_live_deadline_clause`). Used by
    job-market-health, job-type-mix, location-trends, company-insights,
    experience-levels, industry-breakdown and the `total_jobs` of `/freshness`.
    Before this, the ~120k archived slim rows inflated "Total Jobs" and pulled
    "Avg Skills/Job" to 0.0. Time series (hiring-patterns, the week-on-week
    windows) still group by `scraped_at`.
  - job-type-mix merges source spellings in SQL ("Heltid" = "full_time");
    location-trends groups by `lower(btrim(location))`; industry-breakdown
    classifies Swedish titles (matched inside compounds such as
    "systemutvecklare") and has an "IT Support & Operations" sector.
  - `GET /analytics/skill-demand?sort=growth|mentions`: growth ranking is
    dominated by rare skills (4 mentions after 0 is +100%), so the page asks for
    `mentions`.
  - Charts: horizontal bar charts share `CategoryTick` (`charts/chartParts.tsx`,
    one-line labels, every row labelled) and `chartHelpers.tsx`; donuts use
    percentage radii so labels and legends fit on phones; `Legend` needs
    `itemSorter={null}` or Recharts 3 sorts entries alphabetically. The "New this
    week" KPI comes from `utils/weeklyPostings.ts` (daily hiring-patterns series).
  - `tests/test_analytics_live_db.py` runs these queries on a real Postgres.

Thesis baseline (November 2026):
  - ApplyLuma is the case study for Sam's bachelor thesis (SU/DSV, IB015N):
    an AI-assisted job-fit assessment compared with the rule-based matcher.
    `docs/thesis/BASELINE.md` records what existed before the thesis work,
    including the exact rule-based formula; the git tag `pre-thesis-baseline`
    marks the boundary.
  - After that tag, do NOT change the rule-based matcher
    (`matching_service.py`, `keyword_extractor.py`,
    `job_scrapers/keyword_extraction.py`): it is the comparison target. Thesis
    code goes in its own folders, in PRs titled `[thesis] ...`.
  - In production only the skills part of the match score varies (no caller
    passes a required experience or education), so the score is
    `0.4 x skills + 54` (54.5 remote): range 54 to 94.5.
  - `thesis/DESIGN.md` is the design of the AI assessment (two model steps,
    a quote check, then fixed decision rules). Its decisions Q1-Q7 were made
    on 2026-11-13; later changes go in `thesis/DESIGN_LOG.md`. Evaluation
    cases are written by Sam and must stay out of the repo (and out of the
    assistant's view) until the prompts and rules are frozen and tagged.
  - Removed before the baseline: the unused `POST /api/v1/ai/tailor-cv`
    (`endpoints/ai.py`, `services/ai_service.py`). The `cv_analysis` label in
    `AdminAiCosts.tsx` stays, because old usage rows still carry that purpose.
  - Fonts are never inlined by Vite (`build.assetsInlineLimit` in
    `vite.config.ts`): the CSP has `font-src 'self'`, and the inlined `data:`
    subsets were four blocked requests (console errors) on every page.

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
- Nightly job pipeline as a Celery task on Railway (Airflow retired and
  deleted, November 2026)
- dbt models kept for reference and parsed in CI; production rebuilds the two
  marts it reads with plain SQL

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
- `backend/app/tasks/job_pipeline.py` + `backend/app/services/job_pipeline.py` +
  `backend/app/services/job_scrapers/`: the nightly job pipeline (02:00 UTC).
  The retired `airflow/` folder was deleted in November 2026 (it is in git
  history if ever needed).
- `.github/workflows/data-pipeline-tests.yml`: CI for dbt (`dbt parse`).
- `.github/workflows/ci.yml`: CI for backend (ruff, mypy, pytest) and frontend
  (ESLint, `tsc --noEmit`, Vitest, `npm run build`). mypy runs in `strict`
  mode; new modules with untyped decorators (e.g. `@celery_app.task`) must be
  added to `backend/pyproject.toml`'s `[[tool.mypy.overrides]]` list like
  their sibling modules, or CI fails.
- `backend/app/crud/admin/`: admin CRUD split by area (`users`, `pipeline`,
  `ai_costs`, `database`, `operations`); `__init__.py` re-exports everything,
  so `from app.crud import admin as crud_admin` works as before.
- `frontend/src/pages/AITailor.tsx` holds the page state and flow; its steps
  live in `frontend/src/components/tailor/steps/` (Select, Processing, Review,
  Done, History).
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
- `VITE_API_URL`: should be `https://api.applyluma.com` (the Railway custom
  domain), not the raw `*.up.railway.app` host. On the raw host the auth
  cookies are third-party to applyluma.com, so iOS/Safari block them and the
  OAuth callback (which runs on api.applyluma.com) sets them on a different
  host from the one the app calls. `vercel.json`'s CSP `connect-src` allows
  both hosts. `VITE_*` values are baked in at build time: redeploy after a
  change.

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
- `tests/test_inbound_email_matcher.py` — matcher scoring (pure, no DB/HTTP): domain
  signals, ATS routing, suffix-safety, whole-word matching, ambiguity, thresholds
- `tests/test_inbound_email_endpoint.py` — webhook security (valid/bad/missing
  signature, unconfigured secret → 503 without verifying, unknown token → 200,
  oversized body → 413, snippet truncated before enqueue, loop guard)
- `tests/test_inbound_email_task.py` — dedupe (vendor retry + concurrent race),
  unmatched rows still recorded, session always closed
- `tests/test_inbound_email_classifier.py` — classification (pure): English and
  Swedish rejection/interview/offer, diacritic folding, rejection outranking an
  interview invitation, bare "unfortunately" staying below threshold,
  acknowledgements never prompting, evidence extraction and truncation
- `tests/test_email_suggestions.py` — suggestion endpoints: list with evidence,
  already-satisfied suggestions hidden, accept routing through the normal update
  path, dismiss leaving the application untouched, cross-user ids 404, and a
  regression test that `/email-suggestions` is not shadowed by `/{application_id}`
- `tests/test_inbound_email_mailgun.py` — Mailgun adapter: signature accept/reject
  (wrong, empty, tampered, non-hex), multipart + urlencoded bodies, attachments
  skipped, header-sender-not-envelope-sender, stripped-text preference; plus
  forwarding-address build/parse round trip
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

### Data Pipeline — dbt parse

The pipeline's own tests are backend tests: `tests/test_job_scrapers.py`,
`tests/test_job_pipeline.py` and the real-database `tests/test_job_pipeline_db.py`.

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
  - `dbt-tests` job: installs pinned dbt, runs `dbt deps` then `dbt parse`.
- `.github/workflows/ci.yml`:
  - `backend` job (`Backend — lint, type-check, test`): `ruff check app/`,
    `mypy app/` (strict mode — see Key Files note on `[[tool.mypy.overrides]]`),
    `alembic upgrade head` on a Postgres 16 service container, then `pytest`
    with `TEST_DATABASE_URL` set, so the real-database tests
    (`test_job_pipeline_db.py`, `test_job_retention.py`) run instead of
    skipping. Add a real-database test whenever a change is about SQL itself:
    the FakeDb tests never compile it (see the `hide_applied` 500).
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
- `job_market_metrics` freshness depends on the nightly job pipeline's metrics
  step (logged as `transform_jobs`); check `/admin/pipeline` for current status.
- The health watchdog (`app/tasks/watchdog.py`) only fires if Celery **beat**
  runs: either the separate beat service (`backend/railway.beat.json` /
  `scripts/start-beat.sh`) or embedded in the worker via `CELERY_EMBED_BEAT=1`
  (`start-worker.sh` then runs `celery worker -B`; one worker replica only,
  and never alongside the separate beat service or tasks fire twice). None of
  the other scheduled tasks (deadline reminders, weekly summary, high-match
  alerts) fire without beat either.
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
- Railway cost reduction (November 2026): DeskFlow api/worker, Ziafat and
  LoopDog set to sleep. `backend/scripts/compact_database.py` reports table
  bloat and, with `--vacuum`, runs `VACUUM (FULL, ANALYZE)` on the job tables
  retention churns (never deletes rows; locks each table while rewriting, so
  not 01:00-05:00 UTC); `--tune` sets `shared_buffers=128MB` /
  `max_connections=60` (needs a Postgres restart); a busy table is skipped
  after a 10s lock timeout rather than blocking queries. Run it via
  `railway ssh --service applyluma-celery-worker`.
  First run 2026-11-05 (via a temporary `postgres:18-alpine` service with
  `DATABASE_URL=${{Postgres.DATABASE_URL}}`, since the session could not read
  credentials): database 625 MB -> 174 MB in ~8 s, row counts identical
  (`raw_job_postings` 328 -> 129 MB, `job_matching_scores` 280 -> 30 MB).
  Prod already has `shared_buffers=128MB`; `max_connections` is 500 (set by
  the Railway Postgres image, so `ALTER SYSTEM` may not override it), with
  ~7 connections in use. `job_matching_scores` is rewritten by the nightly
  rescoring, so expect it to settle around twice its compacted size.
- Run `scripts/backfill_duplicates.py` once against Railway to mark historical
  cross-source duplicates (see Job Sources & Dedupe section).
- Backlog (verified open as of 2026-07-11): keyword tag filtering on Discover,
  follow-up reminders, granular alert preferences, Platsbanken delisted-ad
  re-check task, additional Phase 10B edge-case tests. `FEATURE_IDEAS.md`
  checkboxes are the authoritative list. NOTE: duplicate-application warning
  (`GET /applications/check-duplicate` + AddApplicationModal banner) and CV
  completeness score (`cv_completeness.py`, `CompletenessBar` on the CVs page)
  are BUILT and live — they were stale here; auth rate limiting also already
  exists (Redis per-IP middlewares in `app/main.py`).
- Run the full test suite (`pytest`, `npm test`) before merging any new feature work.

## AI Development Guidelines

When working on this project:
- Always work in `dev` or create a feature branch from `dev`. `dev` is synced
  with `main` as of 2026-07-11.
- Test in `dev` before merging to `main`. Never push breaking changes to `main`.
- Use Railway logs to verify backend deployments.
- Check both Railway and Vercel for production status.
- Remember that analytics endpoints require a populated database.
- The job pipeline runs daily at 02:00 UTC as a Celery task on Railway (no
  Airflow or dbt in production any more).
- Keep credentials in environment variables only.
- Prefer existing backend, frontend, and dbt patterns before adding new
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
