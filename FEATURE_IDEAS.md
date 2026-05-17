# Feature Ideas

Small, self-contained features ordered roughly by usefulness.
Tick them off as they get built.

---

## Application Tracking

- [ ] **Duplicate application warning**
  When a user adds a new application, warn if an open application for the
  same company already exists. Backend check on `POST /applications` +
  a dismissible modal on the frontend.

- [ ] **Follow-up reminder**
  Add an optional `follow_up_date` field to applications. A daily Celery
  Beat task sends a notification (and optionally an email) when the date
  arrives. Surface it as a date-picker in the application drawer.

- [ ] **Export applications to CSV**
  A `GET /applications/export` endpoint that streams a CSV of all the
  user's applications (company, role, status, dates, salary). A single
  download button on the Applications page.

- [ ] **Application status timeline**
  Store every status change in `ApplicationEvent` (the model already
  exists). Render a vertical timeline inside the application drawer so
  users can see the history at a glance.

---

## CV & Tailoring

- [ ] **CV completeness score**
  Score the uploaded CV against a checklist (contact info, summary,
  experience, education, skills, links). Show a progress bar on the CVs
  page so users know what to improve before tailoring.

- [ ] **Re-analyse existing CV**
  A button on the CVs page that re-runs AI analysis on an already-uploaded
  CV without requiring a new upload. Useful after the user edits and
  re-uploads the same file.

- [ ] **Cover letter generator**
  Extend the AI Tailor flow with an optional step that drafts a cover
  letter from the tailored CV sections and the job description. Reuses
  the existing Celery + OpenAI pattern.

- [ ] **Tailor history view**
  A tab on the AI Tailor page (or CVs page) listing past tailor jobs with
  the job title, date, match score at time of tailoring, and a link to
  download the tailored PDF.

---

## Job Discovery & Search

- [ ] **"Already applied" filter on Discover**
  Cross-reference `raw_job_posting_id` in `applications` and show a badge
  or hide already-applied jobs from the Discover feed. Adds a toggle in
  JobFilters: "Hide applied jobs".

- [ ] **Copy job link button**
  A small copy-to-clipboard icon on each job card and in the job detail
  modal that copies the original job URL. No backend work needed.

- [ ] **Recent searches**
  Persist the last 5 Adzuna search queries in `localStorage` and show them
  as quick-chips under the search bar on the Job Search page.

- [ ] **Keyword tag filtering on Discover**
  Clicking a skill tag inside a job detail should add it as a filter in
  the JobFilters sidebar, narrowing the feed instantly.

---

## Notifications & Alerts

- [ ] **Mark all notifications as read**
  A single "Mark all read" button in the notifications dropdown/page that
  calls `PATCH /notifications/read-all`. One-line backend route, one
  button on the frontend.

- [ ] **Granular notification preferences**
  Extend the Settings page to let users toggle individual notification
  types on/off (e.g. job alerts, stale application reminders, tailor
  complete). Store as a JSON column on `AlertPreferences`.

---

## Settings & Account

- [ ] **Change password**
  A "Change password" form in Settings. Backend endpoint
  `POST /auth/change-password` that verifies the current password before
  updating. Standard flow, no third-party dependency.

- [ ] **Delete account**
  A "Delete my account" option in Settings. Soft-delete the user row and
  cascade-delete or anonymise related data. Show a confirmation modal with
  a typed confirmation ("type DELETE to confirm").

- [ ] **Dark mode toggle**
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
