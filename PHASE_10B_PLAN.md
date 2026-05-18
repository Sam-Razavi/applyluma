# Phase 10B Implementation Plan

## Context

Phase 10A (Swedish job discovery + AI match scoring + Saved Jobs) is complete: 104 backend tests + 38 frontend tests pass, all features production-deployed. A survey of the codebase found:

- **15 uncommitted files** are pure refactor: 3 constants extracted (`statusMeta.ts`, `defaultFilters.ts`, `navLinks.ts`), `Optional[X] → X | None` modernization, unused imports removed. Zero functional changes — ship as a Phase 10A polish commit before starting 10B.
- **No mid-flight feature work** in source. No `TODO`/`FIXME` markers.

Phase 10B integrates Phase 10A discovery with the rest of the app: Phase 9 tailor pipeline, Phase 8 notifications, and application tracking. Per CLAUDE.md "Next Steps", four candidates are in scope, all chosen:

- **(a) One-click CV tailor from Discover** — bridges Discover (`RawJobPosting`) and Tailor (`JobDescription`). Direction chosen: auto-create a `JobDescription` from the `RawJobPosting` when the user tailors a discovered job.
- **(b) Match score explanation UI polish** — backend already emits `explanation` + sub-scores; frontend currently renders as plain text.
- **(c) Email alerts for high-match jobs** — daily digest of new high-score matches.
- **(d) Discover ↔ application tracking** — link a discovered job to a tracked application and show status badges back in Discover.

Goal: ship as **one PR with four commits**, three Alembic migrations chained `0008 → 0009 → 0010 → 0011`. All migrations are additive (only `add_column` / `create_table` / nullable FKs) — safe Railway rollout.

## Sequencing (one PR, four commits)

1. **Commit 0 (pre-flight)** — commit the existing 15-file refactor as Phase 10A polish (no 10B code in this commit).
2. **Commit 1 — Feature (d)**: applications ↔ raw jobs. Smallest schema delta, no Celery. Establishes the "synthesize from RawJobPosting" pattern (a) reuses.
3. **Commit 2 — Feature (a)**: one-click tailor. Reuses (d)'s pattern; highest UX payoff.
4. **Commit 3 — Feature (b)**: match score UI polish. Pure frontend, zero migration risk.
5. **Commit 4 — Feature (c)**: email alerts. Largest Celery/cron surface; ships last so production rollback path stays clean. Feature-flagged via `enabled=false` default on prefs row.

## Implementation Detail

### Pre-flight: commit existing refactor (Phase 10A polish)

Commit message subject suggestion: `Phase 10A polish: extract constants + modernize Optional types`.
Files already staged in `git status` — no new work.

### Feature (d) — Discover ↔ Applications integration

**Migration**: `backend/alembic/versions/0009_application_raw_job_link.py`
- Pattern: copy revision/down_revision style from `0008_phase_10a_tables.py:14-21`.
- `op.add_column("applications", sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=True))`
- FK to `raw_job_postings.id` with `ondelete="SET NULL"`.
- Composite index `idx_applications_raw_job` on `(user_id, raw_job_posting_id)`.
- Partial unique index `uq_app_user_raw_job` on `(user_id, raw_job_posting_id) WHERE raw_job_posting_id IS NOT NULL` (prevents duplicate "Add to Applications" clicks).

**Backend**:
- `backend/app/models/application.py:26-30` — add `raw_job_posting_id: Mapped[uuid.UUID | None]` (mirror existing `job_description_id` style).
- `backend/app/schemas/application.py` — add field to `ApplicationCreate` and `ApplicationSummary`.
- `backend/app/crud/application.py:33-46` — in `create_application`, when `raw_job_posting_id` is set and other fields are blank, hydrate `company_name`/`job_title`/`job_url` from the `RawJobPosting` row. Extract helper `_hydrate_from_raw_job(db, raw_id)` — Feature (a) reuses it.
- `backend/app/crud/job.py` — extend `list_jobs` and the job-detail query with a LEFT JOIN on `applications` keyed on `(user_id, raw_job_posting_id)`; expose `application_status` and `application_id` in returned dicts.
- `backend/app/schemas/job.py` — extend `JobWithScoreSchema` with `application_status: str | None`, `application_id: uuid.UUID | None`.

**Frontend**:
- `frontend/src/types/jobDiscovery.ts` — add `application_status` and `application_id` to `DiscoveredJob`.
- `frontend/src/components/discover/JobDetail.tsx:152-183` — add "Add to Applications" button (Heroicon `BriefcaseIcon`). Render a disabled status pill instead if `application_status` is set.
- `frontend/src/components/discover/JobCard.tsx:62-67` — small status pill alongside the score badge when `application_status` is truthy. Reuse pill styling from `JobDetail.tsx:19-23`.
- `frontend/src/services/applicationsApi.ts` — accept optional `raw_job_posting_id` in `create()`.

### Feature (a) — One-click CV tailor from Discover

**Migration**: `backend/alembic/versions/0010_jd_source_raw_job.py`
- `op.add_column("job_descriptions", sa.Column("source_raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=True))`, FK with `ondelete="SET NULL"`.
- `op.create_unique_constraint("uq_jd_user_raw_job", "job_descriptions", ["user_id", "source_raw_job_posting_id"])` for dedup.

**Backend**:
- `backend/app/models/job_description.py:14-29` — add `source_raw_job_posting_id: Mapped[uuid.UUID | None]`.
- `backend/app/crud/job_description.py` — new helper `get_or_create_from_raw_job(db, user_id, raw_job_posting_id) -> JobDescription`. Looks up by `(user_id, source_raw_job_posting_id)`; if missing, loads `RawJobPosting`, joins `ExtractedKeyword` for keywords, creates JD via existing `create()` (line 26-44).
- `backend/app/schemas/tailor.py` — `TailorSubmitRequest`: make `job_description_id` optional; add `raw_job_posting_id: uuid.UUID | None`. Pydantic `model_validator` enforcing exactly one is set.
- `backend/app/api/v1/endpoints/tailor.py:78-111` — if `raw_job_posting_id` is set, call `crud_jd.get_or_create_from_raw_job(...)`; substitute its id into existing flow (line 101-107 unchanged). Daily rate limit (line 42-51) still applies.

**Frontend**:
- `frontend/src/components/discover/JobDetail.tsx` — add "Tailor CV" button (Heroicon `SparklesIcon`) between Save and Apply. On click: `navigate('/ai-tailor', { state: { rawJobPostingId: job.job_id } })`.
- `frontend/src/pages/AITailor.tsx:46-59` — on mount, read `useLocation().state?.rawJobPostingId`. If present, skip JD selector, fetch `fetchJobDetail(rawJobPostingId)` to show a "Tailoring for [title] @ [company]" banner, submit with `raw_job_posting_id`.
- `frontend/src/services/tailorApi.ts` — `submit()` accepts alternative payload `{ cv_id, raw_job_posting_id, intensity }`.

### Feature (b) — Match score explanation UI polish

Pure frontend. Backend already returns `skills_match`, `experience_match`, `salary_match_score`, `education_match`, `location_match`, `matched_skills`, `missing_skills`, `explanation`.

- `frontend/src/utils/matchScore.ts` (new) — `MATCH_WEIGHTS` constant mirroring `backend/app/services/matching_service.py:29-35` (skills 40, experience 30, salary 15, education 10, location 5).
- `frontend/src/components/discover/ScoreBreakdown.tsx` (new) — collapsible card with 5 horizontal score bars (reuse `ScoreBar` pattern from `JobCard.tsx:12-25`). Each bar labels weight and a band reason (≥80 strong / 60-79 partial / <60 gap).
- `frontend/src/components/discover/SkillsBreakdown.tsx` (new) — "X of Y required skills matched" header. Matched skills as green pills, missing as red pills. Click a missing pill → `navigator.clipboard.writeText` + toast.
- `frontend/src/components/discover/JobDetail.tsx:100-139` — replace with `<ScoreBreakdown />` + `<SkillsBreakdown />`. Add `title` tooltip on overall badge listing weights.

### Feature (c) — Email alerts for high-match jobs

**Migration**: `backend/alembic/versions/0011_user_alert_preferences.py`
- `user_alert_preferences`: `id`, `user_id` FK→`users` CASCADE, `enabled` bool default `false`, `score_threshold` int default 80, `frequency` varchar(16) default `'daily'`, `last_sent_at` timestamptz null, `created_at`/`updated_at`. Unique constraint on `user_id`.
- `job_alert_sent_log`: `id`, `user_id` FK, `raw_job_posting_id` FK, `sent_at` default `now()`, unique `(user_id, raw_job_posting_id)`. Keeps dedup queries indexable (preferred over JSONB on prefs).

**Backend**:
- `backend/app/models/alert_preferences.py` (new) — `UserAlertPreferences`, `JobAlertSentLog`. Mirror `app/models/job.py:53-71` style.
- `backend/app/crud/alert_preferences.py` (new) — `get_or_create_for_user`, `update`, `due_for_alert(db, frequency, now) -> list[user_id]` (filters `enabled=True AND (last_sent_at IS NULL OR last_sent_at < now - interval)`).
- `backend/app/api/v1/endpoints/alert_preferences.py` (new) — `GET /me/alert-preferences`, `PATCH /me/alert-preferences` (`{enabled, score_threshold, frequency}`). Register in `backend/app/api/v1/router.py`.
- `backend/app/tasks/notifications.py` — append `notify_high_match_jobs()`. Pattern: copy `check_stale_applications` (line 22-48). For each due user: query `JobMatchingScore` where `overall_score >= pref.score_threshold AND computed_at > pref.last_sent_at`, LEFT ANTI JOIN `job_alert_sent_log`, top 10 by score; one `notification_service.create_notification(..., send_email=True)` per user; insert log rows + update `pref.last_sent_at` in same transaction (avoids duplicate sends on retry).
- `backend/app/tasks/celery_app.py:24-33` — add `"notify-high-match-jobs-daily"` schedule: `crontab(hour=3, minute=30)` (runs after Airflow scrape at 02:00 UTC and dbt transforms at 03:00 UTC).
- `backend/app/services/email_service.py` — add `high_match_alert` template case if needed (reuses existing `template_email()` interface from `notification_service.py:30`).

**Frontend**:
- `frontend/src/pages/Settings.tsx` (new) — "Job match alerts" card: toggle `enabled`, number input `score_threshold` (60-95, default 80), `<select>` `frequency` (daily | weekly), Save button. Reuse styling from `AITailor.tsx:258-264`. Toast on save success/error. Warning banner if user has no default CV (alerts only fire when matching has scores).
- `frontend/src/services/alertsApi.ts` (new) — `getPreferences()`, `updatePreferences(payload)`.
- App routes — register `/settings`.
- `frontend/src/components/layout/navLinks.ts` (the file from the pre-flight refactor) — add Settings link.

## Files to modify / create

**Migrations (new)**: `backend/alembic/versions/0009_application_raw_job_link.py`, `0010_jd_source_raw_job.py`, `0011_user_alert_preferences.py`

**Backend new**: `app/models/alert_preferences.py`, `app/crud/alert_preferences.py`, `app/api/v1/endpoints/alert_preferences.py`

**Backend modified**: `app/models/application.py`, `app/models/job_description.py`, `app/schemas/application.py`, `app/schemas/job.py`, `app/schemas/tailor.py`, `app/crud/application.py`, `app/crud/job.py`, `app/crud/job_description.py`, `app/api/v1/endpoints/tailor.py`, `app/api/v1/router.py`, `app/tasks/notifications.py`, `app/tasks/celery_app.py`, `app/services/email_service.py`

**Frontend new**: `src/utils/matchScore.ts`, `src/components/discover/ScoreBreakdown.tsx`, `src/components/discover/SkillsBreakdown.tsx`, `src/pages/Settings.tsx`, `src/services/alertsApi.ts`

**Frontend modified**: `src/types/jobDiscovery.ts`, `src/components/discover/JobDetail.tsx`, `src/components/discover/JobCard.tsx`, `src/services/applicationsApi.ts`, `src/services/tailorApi.ts`, `src/pages/AITailor.tsx`, `src/components/layout/navLinks.ts`, app routes

## Reuse existing patterns

- Alembic migration scaffold: `backend/alembic/versions/0008_phase_10a_tables.py:14-21`
- Celery task pattern: `backend/app/tasks/notifications.py:22-48` (`check_stale_applications`)
- Notification + email: `backend/app/services/notification_service.py:create_notification` (already supports `send_email=True`)
- Backend test pattern: `httpx.AsyncClient(transport=ASGITransport(app=app))` + `FakeDb` overrides per CLAUDE.md, modeled on `backend/tests/test_tailor_endpoints.py:31-133`
- Frontend test pattern: `vi.mock('../services/api')` per CLAUDE.md; `TokenPair` mocks need all three fields
- Score bar UI: `frontend/src/components/discover/JobCard.tsx:12-25`
- Pill UI: `frontend/src/components/discover/JobDetail.tsx:19-23`

## Verification

**Migrations**:
- `cd backend && alembic upgrade head` (run locally against Railway proxy URL per CLAUDE.md). Verify three new revisions applied. Confirm `alembic downgrade -3` runs cleanly (all three are additive).

**Backend tests** (`cd backend && pytest`):
- `tests/test_application_endpoints.py` — new cases: `test_create_application_hydrates_from_raw_job_posting`, `test_create_application_raw_job_id_not_found_404`.
- `tests/test_jobs_endpoints.py` — new: `test_list_jobs_includes_application_status`.
- `tests/test_tailor_endpoints.py` — new: `test_submit_with_raw_job_posting_id_creates_jd`, `test_submit_rejects_both_jd_and_raw_job_ids` (expects 422).
- `tests/test_alert_preferences.py` (new file) — `test_get_creates_defaults`, `test_patch_updates_threshold`, `test_patch_validates_threshold_range`.
- `tests/test_notifications.py` — new: `test_notify_high_match_jobs_skips_already_sent`, `test_notify_high_match_jobs_respects_threshold`, `test_notify_high_match_jobs_no_matches_no_email`.

**Frontend tests** (`cd frontend && npm test`):
- `pages/Discover.test.tsx` — new: `test_application_status_badge_renders_when_present`.
- `components/discover/JobDetail.test.tsx` (new) — Tailor CV navigation; Add-to-Applications POST with `raw_job_posting_id`; status pill replaces button when already applied.
- `components/discover/ScoreBreakdown.test.tsx`, `SkillsBreakdown.test.tsx` (new) — render + interaction.
- `pages/Settings.test.tsx` (new) — load prefs, save patches, toast on success.
- `pages/AITailor.test.tsx` (new) — route state with `rawJobPostingId` skips selector and submits with raw id.

**Manual end-to-end (against `dev` env)**:
1. Discover → click a high-score job → "Tailor CV" → confirm tailor job runs and the JD shows up in My Job Descriptions with the right company/title.
2. Discover → "Add to Applications" → confirm row in `/applications` and status badge appears on Discover card.
3. Settings → enable alerts at threshold 80 → wait for Celery beat (or trigger `notify_high_match_jobs.apply()` manually) → confirm email + `notifications` row + `job_alert_sent_log` row; trigger again → confirm no duplicate.
4. Re-tailor the same RawJobPosting → confirm `get_or_create_from_raw_job` reuses the JD (no duplicate JDs).

**CI**: confirm `data-pipeline-tests.yml` still passes (no DAG changes), Vercel build passes (TypeScript), backend tests pass.

## Risks and edge cases

- **RawJobPosting deleted after Tailor**: JD survives via `ondelete=SET NULL`; tailor history preserved.
- **Same RawJobPosting tailored twice**: `uq_jd_user_raw_job` + `get_or_create_from_raw_job` ensures dedup. Daily tailor rate limit still applies.
- **Airflow scrape fails**: no new scores → empty digest → skip send (do not email "0 matches"). Test case covers this.
- **User opts in with no default CV**: matching service requires `cv.is_default`, so no scores exist → empty digest, no error. Settings page shows a warning.
- **Concurrent Celery retries**: do `update prefs.last_sent_at` and insert `job_alert_sent_log` rows in the same transaction.
- **Duplicate "Add to Applications" clicks**: partial unique index + frontend disabling the button when `application_status` is set.

## Out of scope (defer to Phase 10C)

- LLM-generated explanations (current deterministic text is presentable after (b)).
- Surfacing high-match notifications in an in-app navbar bell (row already written by (c)).
- Auto-create an Application when a job is starred (conflates user intent).
- Discover filter "Already in Applications".
- Per-source alert thresholds, SMS/push channels.
- Backfilling `source_raw_job_posting_id` on existing Phase 9 JDs (forward-looking column).
- Renaming/unifying `job_url`/`url` fields across `Application`/`JobDescription`/`RawJobPosting`.
- Timezone-aware notification scheduling.
