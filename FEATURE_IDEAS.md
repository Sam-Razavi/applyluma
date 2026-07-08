# Feature Ideas

Small, self-contained features ordered roughly by usefulness.
Tick them off as they get built.

---

## Application Tracking

- [x] **Duplicate application warning**
  `GET /applications/check-duplicate?company=X` reports an existing open
  application (any status except rejected/withdrawn); the add-application
  modal warns once and the second submit ("Add anyway") proceeds.

- [ ] **Follow-up reminder**
  Add an optional `follow_up_date` field to applications. A daily Celery
  Beat task sends a notification (and optionally an email) when the date
  arrives. Surface it as a date-picker in the application drawer.

- [x] **Export applications to CSV**
  Built client-side instead of the backend endpoint: an "Export CSV" button
  on the Applications page generates the file from the loaded list
  (`frontend/src/utils/exportCsv.ts`). Note: exports the applications
  currently loaded, not a server-side stream.

- [x] **Application status timeline**
  Status changes are stored in `ApplicationEvent` and rendered by
  `components/applications/ApplicationTimeline.tsx` in the drawer.

---

## CV & Tailoring

- [x] **CV completeness score**
  Deterministic checklist scoring (contact info, summary, experience,
  education, skills, links, length) in `cv_completeness.py`, English and
  Swedish headings. Progress bar per CV row on the CVs page; clicking it
  expands the checklist with hints (`GET /cvs/{id}/completeness`).

- [ ] **Re-analyse existing CV**
  A button on the CVs page that re-runs AI analysis on an already-uploaded
  CV without requiring a new upload. Useful after the user edits and
  re-uploads the same file.

- [x] **Cover letter generator**
  Built: `cover_letter_service.py`, `endpoints/cover_letters.py`, Celery
  task, and cover-letter history on the AI Tailor page.

- [ ] **Tailor history view**
  A tab on the AI Tailor page (or CVs page) listing past tailor jobs with
  the job title, date, match score at time of tailoring, and a link to
  download the tailored PDF.

---

## Job Discovery & Search

- [x] **"Already applied" filter on Discover**
  Cross-reference `raw_job_posting_id` in `applications` and show a badge
  or hide already-applied jobs from the Discover feed. Adds a toggle in
  JobFilters: "Hide applied jobs".

- [ ] **Copy job link button** (rejected)
  Decided against — `JobCard.test.tsx` intentionally asserts the action is
  not rendered. Kept here so it isn't re-proposed.

- [x] **Recent searches**
  Built in `Discover.tsx`: last 5 searches persisted in `localStorage`
  and shown as quick-chips on the search tab.

- [x] **Keyword tag filtering on Discover**
  Skill pills in the job detail (SkillsBreakdown) are clickable in the
  Discover feed: clicking adds the skill to the keywords filter, closes
  the modal, and reloads the feed.

---

## Notifications & Alerts

- [x] **Mark all notifications as read**
  Built: backend `mark_all_read` route plus the "Mark all read" button in
  `NotificationList.tsx`.

- [ ] **Granular notification preferences**
  Extend the Settings page to let users toggle individual notification
  types on/off (e.g. job alerts, stale application reminders, tailor
  complete). Store as a JSON column on `AlertPreferences`.

---

## Settings & Account

- [x] **Change password**
  A "Change password" form in Settings. Backend endpoint
  `POST /auth/change-password` that verifies the current password before
  updating. Standard flow, no third-party dependency.

- [x] **Delete account**
  A "Delete my account" option in Settings. Soft-delete the user row and
  cascade-delete or anonymise related data. Show a confirmation modal with
  a typed confirmation ("type DELETE to confirm").

- [x] **Dark mode toggle**
  Tailwind's `dark:` classes are already partially used. Add a toggle in
  Settings (or the navbar) that flips a `dark` class on `<html>` and
  persists the preference in `localStorage`.

---

## Developer / Quality

- [x] **Health badge in README**
  A `GET /health` endpoint already exists. Wire the Railway health URL
  into a shields.io badge in the README alongside the CI badges.

- [x] **Rate-limit feedback in UI**
  When the API returns 429 (e.g. tailor limit hit), show a friendly toast
  with the reason and reset time instead of a generic error.

- [x] **Structured error responses**
  Standardise all FastAPI error responses to `{ detail, code, field? }`
  so the frontend can display actionable messages rather than raw strings.
