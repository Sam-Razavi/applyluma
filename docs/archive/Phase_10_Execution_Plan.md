# ApplyLuma Phase 10 Execution Plan

**Status:** Ready to Execute  
**Timeline:** 14 Weeks  
**Branch:** `claude/phase-10-execution-plan-3MFmx` → merge to `dev` → `main`

---

## How to Use This Document

1. Open a **new Claude Chat** session for each section.
2. Copy the **Detailed Prompt** block.
3. Paste it and say: `"Implement this section."`
4. Receive code, paste it into the codebase.
5. Run tests, confirm success criteria.
6. Return here for the next section.

Dependencies are noted per section — complete sections in order unless marked as **parallelizable**.

---

## Phase 10 Sections Overview

| # | Section | Weeks | Depends On |
|---|---------|-------|------------|
| 1 | Application Tracking System (Backend) | 1–2 | None |
| 2 | Application Kanban Board (Frontend) | 3–4 | Section 1 |
| 3 | Job Discovery via Adzuna | 5–6 | Section 1 |
| 4 | Premium Subscription (Stripe) | 7–8 | Section 1 |
| 5 | Smart Notifications System | 9–10 | Sections 1 & 4 |
| 6 | Resume Version History | 6–7 | None (parallel with 3–4) |
| 7 | Personal Application Analytics | 11–12 | Sections 1 & 2 |
| 8 | Mobile Responsive Polish | 13 | Sections 2 & 3 |
| 9 | Monitoring & Observability | 14 | All |

---

---

# Section 1: Application Tracking System (Backend)

**Weeks 1–2 | Foundation Layer**

## 1.1 Architecture Design

The application tracker is the core Phase 10 feature. It lets users record every job they've applied to, track statuses through a hiring pipeline, log contacts, and attach notes and timeline events.

### Database Schema

```sql
-- applications: one row per job application
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE SET NULL,
    cv_id           UUID REFERENCES cvs(id) ON DELETE SET NULL,
    company_name    VARCHAR(255) NOT NULL,
    job_title       VARCHAR(255) NOT NULL,
    job_url         TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'wishlist',
    -- statuses: wishlist | applied | phone_screen | interview | offer | rejected | withdrawn
    applied_date    TIMESTAMP WITH TIME ZONE,
    source          VARCHAR(100),          -- linkedin, indeed, referral, company_site, other
    salary_min      INTEGER,               -- annual, in pence/cents or local currency units
    salary_max      INTEGER,
    location        VARCHAR(255),
    remote_type     VARCHAR(50),           -- remote | hybrid | onsite
    priority        SMALLINT DEFAULT 1,    -- 1=low, 2=medium, 3=high
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- application_events: immutable timeline log
CREATE TABLE application_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type      VARCHAR(100) NOT NULL,
    -- types: status_changed | note_added | contact_added | interview_scheduled | offer_received | follow_up
    old_value       TEXT,
    new_value       TEXT,
    description     TEXT,
    event_date      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- application_contacts: people involved in the process
CREATE TABLE application_contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    name            VARCHAR(255),
    role            VARCHAR(100),   -- recruiter | hiring_manager | interviewer | other
    email           VARCHAR(255),
    phone           VARCHAR(50),
    linkedin_url    TEXT,
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_applications_user_id   ON applications(user_id);
CREATE INDEX idx_applications_status    ON applications(status);
CREATE INDEX idx_app_events_app_id      ON application_events(application_id);
CREATE INDEX idx_app_contacts_app_id    ON application_contacts(application_id);
```

### File Interaction Diagram

```
Alembic migration
      ↓
models/application.py  ←──────────────────────────────────┐
models/application_event.py                                │
models/application_contact.py                             │
      ↓                                                    │
crud/application.py ─────────────── schemas/application.py
      ↓
api/v1/endpoints/applications.py
      ↓
main.py (router registration)
      ↓
backend/tests/test_application_endpoints.py
```

### Status State Machine

```
wishlist → applied → phone_screen → interview → offer → (accepted/withdrawn)
                                              → rejected
                 → rejected
         → withdrawn
```

---

## 1.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| CREATE | `backend/alembic/versions/xxxx_add_applications_tables.py` | 80 |
| CREATE | `backend/app/models/application.py` | 70 |
| CREATE | `backend/app/models/application_event.py` | 35 |
| CREATE | `backend/app/models/application_contact.py` | 40 |
| MODIFY | `backend/app/models/__init__.py` | +3 lines |
| CREATE | `backend/app/schemas/application.py` | 120 |
| CREATE | `backend/app/crud/application.py` | 150 |
| CREATE | `backend/app/api/v1/endpoints/applications.py` | 200 |
| MODIFY | `backend/app/main.py` | +4 lines (router import + include) |
| CREATE | `backend/tests/test_application_endpoints.py` | 200 |

**Total: ~900 lines new, ~7 lines modified**

---

## 1.3 Dependencies

- **Requires:** Nothing new — builds on existing `users`, `cvs`, `job_descriptions` tables.
- **Blocks:** Section 2 (Kanban UI), Section 5 (Notifications), Section 7 (Analytics).
- **Alembic note:** Run `alembic revision --autogenerate -m "add applications tables"` then `alembic upgrade head`.

---

## 1.4 Detailed Prompt for Claude Chat

> **Context:** You are working on ApplyLuma, an AI-powered job search and resume optimization platform. The backend is FastAPI + PostgreSQL + SQLAlchemy 2.x + Alembic. The project follows a strict layered pattern: `models/` → `crud/` → `schemas/` → `api/v1/endpoints/`. All tests use `httpx.AsyncClient` with ASGI transport and `app.dependency_overrides` to inject a `FakeDb` stub — no real database. The existing models are in `backend/app/models/` (user.py, cv.py, job_description.py, tailor_job.py). The existing CRUD files are in `backend/app/crud/`. The main router is registered in `backend/app/main.py`. Test files live in `backend/tests/`.
>
> **Task:** Implement the Application Tracking backend for Phase 10. Create three new database tables: `applications`, `application_events`, and `application_contacts`. An `Application` belongs to a `User`, optionally links to a `JobDescription` and a `CV`. Statuses follow a pipeline: `wishlist → applied → phone_screen → interview → offer → rejected/withdrawn`. Every status change must automatically insert an `ApplicationEvent` row. The `ApplicationContact` table stores recruiters/interviewers linked to an application.
>
> **Create these files exactly:**
> 1. `backend/alembic/versions/0005_add_applications_tables.py` — Alembic migration adding all three tables with the indexes listed above. Use `op.create_table` and `op.create_index`.
> 2. `backend/app/models/application.py` — SQLAlchemy model for `Application` with all columns, relationships to `User`, `CV`, `JobDescription`, `ApplicationEvent` (cascade), `ApplicationContact` (cascade).
> 3. `backend/app/models/application_event.py` — SQLAlchemy model for `ApplicationEvent`.
> 4. `backend/app/models/application_contact.py` — SQLAlchemy model for `ApplicationContact`.
> 5. `backend/app/schemas/application.py` — Pydantic schemas: `ApplicationCreate`, `ApplicationUpdate`, `ApplicationPublic` (includes nested `events` and `contacts` lists), `ApplicationSummary` (no nested lists), `ApplicationEventCreate`, `ApplicationContactCreate`, `ApplicationContactPublic`.
> 6. `backend/app/crud/application.py` — CRUD functions: `create_application(db, user_id, data)` which also inserts an initial `ApplicationEvent(event_type="status_changed", new_value=status)`; `get_applications(db, user_id, status_filter, skip, limit)`; `get_application(db, id, user_id)`; `update_application(db, id, user_id, data)` which auto-inserts an event when status changes; `delete_application(db, id, user_id)`; `add_contact(db, application_id, user_id, data)`; `delete_contact(db, contact_id, application_id, user_id)`.
> 7. `backend/app/api/v1/endpoints/applications.py` — FastAPI router with: `POST /applications`, `GET /applications` (with optional `?status=` filter), `GET /applications/{id}`, `PATCH /applications/{id}`, `DELETE /applications/{id}`, `POST /applications/{id}/contacts`, `DELETE /applications/{id}/contacts/{contact_id}`, `GET /applications/stats` (returns count by status for the current user).
> 8. `backend/app/main.py` — Add import and `app.include_router(applications_router, prefix="/api/v1", tags=["applications"])`.
> 9. `backend/tests/test_application_endpoints.py` — pytest tests covering: create application, list applications with status filter, get single application, update status (verify event created), delete application, add contact, delete contact, get stats. Follow the existing test pattern from `test_cv_endpoints.py`.
>
> **Success Criteria:** `cd backend && pytest tests/test_application_endpoints.py -v` passes all tests. No import errors. The router registers cleanly and appears in `/api/v1/docs`.

---
---

# Section 2: Application Kanban Board (Frontend)

**Weeks 3–4 | Core UI**

## 2.1 Architecture Design

The Kanban board is the primary UI for the application tracker. Users see their applications as cards in columns (one per status). They can drag cards between columns to change status, click a card to open a detail drawer, and add new applications via a modal form.

### Component Tree

```
pages/Applications.tsx          (route: /applications)
├── components/applications/
│   ├── KanbanBoard.tsx          (renders all columns)
│   │   └── KanbanColumn.tsx     (one per status)
│   │       └── ApplicationCard.tsx  (draggable card)
│   ├── ApplicationDrawer.tsx    (right-side detail panel)
│   │   ├── ApplicationTimeline.tsx  (event log)
│   │   └── ContactsList.tsx     (contacts panel)
│   ├── AddApplicationModal.tsx  (create form)
│   ├── ApplicationStats.tsx     (funnel summary bar)
│   └── ApplicationFilters.tsx   (search + filter bar)
services/applicationsApi.ts      (API calls)
types/application.ts             (TypeScript types)
stores/applications.ts           (Zustand store)
```

### State Flow

```
applicationsStore (Zustand)
  ├── applications: Application[]
  ├── selectedApplication: Application | null
  ├── isLoading: boolean
  ├── filters: { status, search }
  ├── fetchApplications() → GET /api/v1/applications
  ├── createApplication(data) → POST /api/v1/applications
  ├── updateApplication(id, data) → PATCH /api/v1/applications/:id
  └── deleteApplication(id) → DELETE /api/v1/applications/:id
```

### Kanban Columns (left → right)

```
Wishlist | Applied | Phone Screen | Interview | Offer | Rejected | Withdrawn
```

### Drag and Drop

Uses `@dnd-kit/core` + `@dnd-kit/sortable` (already compatible with React 18). On drag-end, calls `updateApplication(id, { status: newColumn })` and optimistically moves the card.

---

## 2.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| CREATE | `frontend/src/pages/Applications.tsx` | 120 |
| CREATE | `frontend/src/components/applications/KanbanBoard.tsx` | 120 |
| CREATE | `frontend/src/components/applications/KanbanColumn.tsx` | 80 |
| CREATE | `frontend/src/components/applications/ApplicationCard.tsx` | 90 |
| CREATE | `frontend/src/components/applications/ApplicationDrawer.tsx` | 180 |
| CREATE | `frontend/src/components/applications/ApplicationTimeline.tsx` | 70 |
| CREATE | `frontend/src/components/applications/ContactsList.tsx` | 80 |
| CREATE | `frontend/src/components/applications/AddApplicationModal.tsx` | 150 |
| CREATE | `frontend/src/components/applications/ApplicationStats.tsx` | 80 |
| CREATE | `frontend/src/services/applicationsApi.ts` | 80 |
| CREATE | `frontend/src/stores/applications.ts` | 80 |
| CREATE | `frontend/src/types/application.ts` | 60 |
| MODIFY | `frontend/src/App.tsx` | +2 lines (route) |
| MODIFY | `frontend/src/components/layout/AppLayout.tsx` | +1 line (nav link) |
| MODIFY | `frontend/package.json` | +2 deps (`@dnd-kit/core`, `@dnd-kit/sortable`) |

**Total: ~1,200 lines new, ~5 lines modified**

---

## 2.3 Dependencies

- **Requires:** Section 1 complete (backend API endpoints live).
- **Blocks:** Section 7 (Personal Analytics — needs application data).
- **npm:** Install `@dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` before implementing.

---

## 2.4 Detailed Prompt for Claude Chat

> **Context:** You are working on ApplyLuma, a React + TypeScript + Vite + Tailwind CSS frontend (Vercel deployment). The app uses React Router v6, Zustand for state, Recharts for charts, and Axios via a custom `api/client.ts`. Protected routes wrap `AppLayout`. Existing pages: Dashboard, CVs, Jobs, AITailor, Analytics. Existing stores: `stores/index.ts` (auth). Existing services: `services/api.ts`, `services/tailorApi.ts`. All pages live in `frontend/src/pages/`. All tests use Vitest + React Testing Library; mocks go in `vi.mock('../services/...')`. The backend API base URL is read from `VITE_API_URL`.
>
> **Task:** Build the Application Tracking Kanban Board UI for Phase 10. The backend API (already implemented) provides: `GET /api/v1/applications`, `POST /api/v1/applications`, `PATCH /api/v1/applications/:id`, `DELETE /api/v1/applications/:id`, `GET /api/v1/applications/stats`. An `Application` has: `id`, `company_name`, `job_title`, `status` (wishlist/applied/phone_screen/interview/offer/rejected/withdrawn), `applied_date`, `source`, `salary_min`, `salary_max`, `location`, `remote_type`, `priority`, `notes`, `events[]`, `contacts[]`. Install `@dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` for drag-and-drop.
>
> **Create these files exactly:**
> 1. `frontend/src/types/application.ts` — TypeScript interfaces: `Application`, `ApplicationEvent`, `ApplicationContact`, `ApplicationCreate`, `ApplicationUpdate`, `ApplicationStats` (count per status), `ApplicationStatus` (union type of all 7 statuses).
> 2. `frontend/src/services/applicationsApi.ts` — Axios calls for all 5 endpoints. Export named functions: `fetchApplications(statusFilter?)`, `createApplication(data)`, `updateApplication(id, data)`, `deleteApplication(id)`, `fetchStats()`.
> 3. `frontend/src/stores/applications.ts` — Zustand store with state (`applications`, `stats`, `selectedApplication`, `isLoading`, `error`, `filters`) and actions (`fetchApplications`, `createApplication`, `updateApplication`, `deleteApplication`, `setSelected`, `setFilters`). Use optimistic updates for status changes.
> 4. `frontend/src/components/applications/ApplicationCard.tsx` — Card showing company, title, priority badge (color-coded), applied date, and a drag handle. Clicking the card calls `setSelected(application)`.
> 5. `frontend/src/components/applications/KanbanColumn.tsx` — A droppable column with status label, count badge, and a scrollable card list. Uses `@dnd-kit/sortable`.
> 6. `frontend/src/components/applications/KanbanBoard.tsx` — DndContext wrapper rendering 7 KanbanColumns. Handles `onDragEnd` to call `updateApplication(id, { status: newColumn })`.
> 7. `frontend/src/components/applications/ApplicationStats.tsx` — Horizontal funnel bar showing count per status with colored segments.
> 8. `frontend/src/components/applications/AddApplicationModal.tsx` — Modal form with fields: company_name (required), job_title (required), status (select, default wishlist), applied_date, source (select), salary_min, salary_max, location, remote_type (select), priority (select), notes. On submit calls `createApplication`.
> 9. `frontend/src/components/applications/ApplicationTimeline.tsx` — Vertical timeline of events showing event_type, description, and date.
> 10. `frontend/src/components/applications/ContactsList.tsx` — List of contacts with name, role, email, phone with an Add Contact form inline.
> 11. `frontend/src/components/applications/ApplicationDrawer.tsx` — Right-side slide-in panel (fixed, 480px wide) showing full application details, editable fields, the timeline, and contacts list. Has a Delete button with confirmation.
> 12. `frontend/src/pages/Applications.tsx` — Page component: renders `ApplicationStats` at top, a search/filter bar, then `KanbanBoard`. A floating Add button opens `AddApplicationModal`. Renders `ApplicationDrawer` when `selectedApplication` is set. Calls `fetchApplications()` on mount.
> 13. Modify `frontend/src/App.tsx`: Add `<Route path="/applications" element={<ProtectedRoute><Applications /></ProtectedRoute>} />`.
> 14. Modify `frontend/src/components/layout/AppLayout.tsx`: Add a "Applications" nav link pointing to `/applications`.
>
> **Style:** Match the existing Tailwind design language — dark sidebar, white cards, indigo/blue accent colors. Status colors: wishlist=gray, applied=blue, phone_screen=yellow, interview=purple, offer=green, rejected=red, withdrawn=slate.
>
> **Success Criteria:** `cd frontend && npm run build` compiles with zero TypeScript errors. `npm test` passes. Visiting `/applications` shows the kanban board with 7 columns. Dragging a card between columns calls the PATCH endpoint. Clicking a card opens the drawer. The Add button opens the form modal.

---
---

# Section 3: Job Discovery via Adzuna Integration

**Weeks 5–6 | Job Search**

## 3.1 Architecture Design

Adzuna is already used by Airflow for daily scraping. This section adds a **real-time search** endpoint so users can search jobs from the frontend and one-click save them to their tracker.

### API Flow

```
Frontend JobSearch page
    ↓ GET /api/v1/jobs/search?q=software+engineer&location=london&page=1
Backend jobs search endpoint
    ↓ GET https://api.adzuna.com/v1/api/jobs/{country}/search/1
Adzuna API (external)
    ↓ returns job listings
Backend transforms + returns to frontend
    ↓
Frontend shows results
    ↓ User clicks "Track Application"
POST /api/v1/applications (pre-filled from job data)
```

### Adzuna Response → Application Mapping

```
Adzuna field          → Application field
title                 → job_title
company.display_name  → company_name
redirect_url          → job_url
location.display_name → location
salary_min            → salary_min
salary_max            → salary_max
description           → (shown in preview, not stored)
contract_type         → remote_type mapping
```

### Caching Strategy

Results are cached in Redis for 10 minutes per `(query, location, page)` key to avoid hammering Adzuna rate limits.

---

## 3.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| CREATE | `backend/app/services/adzuna_service.py` | 100 |
| CREATE | `backend/app/schemas/job_search.py` | 60 |
| CREATE | `backend/app/api/v1/endpoints/job_search.py` | 100 |
| MODIFY | `backend/app/main.py` | +4 lines |
| MODIFY | `backend/app/core/config.py` | +3 lines (ADZUNA_APP_ID, ADZUNA_API_KEY, ADZUNA_COUNTRY) |
| CREATE | `backend/tests/test_job_search_endpoints.py` | 80 |
| CREATE | `frontend/src/pages/JobSearch.tsx` | 200 |
| CREATE | `frontend/src/components/jobs/JobSearchBar.tsx` | 80 |
| CREATE | `frontend/src/components/jobs/JobResultCard.tsx` | 100 |
| CREATE | `frontend/src/components/jobs/JobResultList.tsx` | 60 |
| CREATE | `frontend/src/services/jobSearchApi.ts` | 50 |
| MODIFY | `frontend/src/App.tsx` | +2 lines |
| MODIFY | `frontend/src/components/layout/AppLayout.tsx` | +1 line |

**Total: ~800 lines new, ~10 lines modified**

---

## 3.3 Dependencies

- **Requires:** Section 1 (applications backend — for one-click tracking).
- **Requires:** `ADZUNA_APP_ID` and `ADZUNA_API_KEY` environment variables in Railway.
- **Blocks:** Section 8 (Mobile Polish needs this page to exist).
- **Parallel with:** Section 6 (Resume Version History).

---

## 3.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma backend is FastAPI + PostgreSQL + Redis. The Adzuna API is already used in the Airflow scraping DAG (`airflow/dags/scrape_jobs.py`). The config is in `backend/app/core/config.py` (uses `pydantic_settings.BaseSettings` reading from environment variables). Redis client is obtained via `get_redis_client()` dependency from `backend/app/core/dependencies.py`. The applications backend (POST /api/v1/applications) already exists from Section 1. On the frontend, the app is React + TypeScript + Tailwind + Zustand. New pages are added to `frontend/src/pages/`, new services to `frontend/src/services/`.
>
> **Task:** Add real-time Adzuna job search. Backend: create a `GET /api/v1/jobs/search` endpoint that accepts `q` (query string), `location` (optional), `page` (default 1), `results_per_page` (default 10, max 50), `country` (default from config). The endpoint calls the Adzuna REST API (`https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?app_id=...&app_key=...&what=...&where=...&results_per_page=...`), transforms results into a clean schema, and caches the response in Redis for 10 minutes using a key of `adzuna:{country}:{q}:{location}:{page}:{results_per_page}`. Frontend: create a Job Search page with a search bar, location input, paginated results, and a "Track This Job" button on each card that pre-fills the Add Application modal.
>
> **Create these files exactly:**
> 1. `backend/app/core/config.py` — Add three new settings: `ADZUNA_APP_ID: str = ""`, `ADZUNA_API_KEY: str = ""`, `ADZUNA_COUNTRY: str = "gb"`.
> 2. `backend/app/schemas/job_search.py` — Pydantic schemas: `AdzunaJobResult` (id, title, company_name, location, salary_min, salary_max, contract_type, redirect_url, description, created), `JobSearchResponse` (results: list[AdzunaJobResult], count: int, page: int, total_pages: int).
> 3. `backend/app/services/adzuna_service.py` — Async function `search_jobs(q, location, page, results_per_page, country, app_id, app_key)` using `httpx.AsyncClient` to call Adzuna. Map raw Adzuna fields to `AdzunaJobResult`. Handle `httpx.HTTPError` and return empty results. Do NOT call this if `app_id` is empty (return empty response instead).
> 4. `backend/app/api/v1/endpoints/job_search.py` — Router with `GET /jobs/search`. Check Redis cache first; on miss call `adzuna_service.search_jobs`, cache result as JSON, return. Requires authenticated user (`get_current_user` dependency).
> 5. `backend/app/main.py` — Register the new router at prefix `/api/v1`.
> 6. `backend/tests/test_job_search_endpoints.py` — Tests: search returns results (mock adzuna_service.search_jobs), search returns cached results on second call, search returns empty when ADZUNA_APP_ID is blank, unauthenticated request returns 401. Follow the existing ASGI transport test pattern.
> 7. `frontend/src/services/jobSearchApi.ts` — Axios call `searchJobs(q, location, page)` returning `JobSearchResponse`.
> 8. `frontend/src/components/jobs/JobSearchBar.tsx` — Search input, location input, and Search button. Fires `onSearch(q, location)` callback.
> 9. `frontend/src/components/jobs/JobResultCard.tsx` — Card showing title, company, location, salary range, contract type, description snippet, and a "Track This Job" button that opens the Add Application modal pre-filled.
> 10. `frontend/src/components/jobs/JobResultList.tsx` — List of `JobResultCard` with pagination controls.
> 11. `frontend/src/pages/JobSearch.tsx` — Page: `JobSearchBar` at top, `JobResultList` below. Manages search state locally (no Zustand store needed). Shows loading skeleton and empty state. "Track This Job" passes job data into the `AddApplicationModal` from Section 2 with pre-filled fields.
> 12. Add route `/job-search` and nav link in `AppLayout`.
>
> **Success Criteria:** `cd backend && pytest tests/test_job_search_endpoints.py -v` passes all tests. `cd frontend && npm run build` passes. With valid Adzuna credentials in env, the Job Search page returns and displays results. Clicking "Track This Job" opens the Add Application modal pre-filled with job data.

---
---

# Section 4: Premium Subscription (Stripe)

**Weeks 7–8 | Monetisation**

## 4.1 Architecture Design

Stripe Checkout handles payment. A webhook updates the user's role to `premium` on successful subscription. The backend validates the Stripe webhook signature. The frontend shows a Plans page and enforces feature gates.

### Subscription Flow

```
User clicks "Upgrade to Premium"
    ↓
POST /api/v1/billing/create-checkout-session
    ↓ Stripe Checkout Session created
Frontend redirects to Stripe hosted page
    ↓ User pays
Stripe sends webhook POST /api/v1/billing/webhook
    ↓ signature verified
Backend sets user.role = 'premium' in DB
    ↓
User redirected to /billing/success
Frontend refreshes user profile (role now premium)
```

### Database Changes

```sql
-- No new tables needed. The existing users.role column supports 'premium'.
-- Add new columns to track subscription state:
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255);
ALTER TABLE users ADD COLUMN subscription_status VARCHAR(50); -- active | canceled | past_due
ALTER TABLE users ADD COLUMN subscription_ends_at TIMESTAMP WITH TIME ZONE;
```

### Stripe Products

- **Free tier:** 1 CV tailor/day, basic analytics, application tracking.
- **Premium tier ($9.99/month):** 10 CV tailors/day, all analytics, priority features.

### Feature Gate Pattern (Frontend)

```tsx
// In any component:
const { user } = useAuthStore();
if (user.role !== 'premium') return <UpgradePrompt />;
```

---

## 4.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| CREATE | `backend/alembic/versions/0006_add_stripe_fields_to_users.py` | 30 |
| CREATE | `backend/app/api/v1/endpoints/billing.py` | 150 |
| CREATE | `backend/app/schemas/billing.py` | 40 |
| MODIFY | `backend/app/schemas/user.py` | +4 fields |
| MODIFY | `backend/app/models/user.py` | +4 columns |
| MODIFY | `backend/app/core/config.py` | +3 lines (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PREMIUM_PRICE_ID) |
| MODIFY | `backend/app/main.py` | +4 lines |
| CREATE | `backend/tests/test_billing_endpoints.py` | 100 |
| CREATE | `frontend/src/pages/Plans.tsx` | 150 |
| CREATE | `frontend/src/pages/BillingSuccess.tsx` | 50 |
| CREATE | `frontend/src/pages/BillingCancel.tsx` | 30 |
| CREATE | `frontend/src/components/billing/PlanCard.tsx` | 80 |
| CREATE | `frontend/src/components/billing/UpgradePrompt.tsx` | 60 |
| CREATE | `frontend/src/services/billingApi.ts` | 40 |
| MODIFY | `frontend/src/App.tsx` | +4 lines |
| MODIFY | `frontend/src/components/layout/AppLayout.tsx` | +1 line (nav item) |
| MODIFY | `frontend/src/stores/index.ts` | +2 fields to User type |

**Total: ~700 lines new, ~15 lines modified**

---

## 4.3 Dependencies

- **Requires:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PREMIUM_PRICE_ID` in Railway environment.
- **Requires:** `stripe` Python package (`pip install stripe`), `stripe` npm package for frontend types.
- **Blocks:** Section 5 (Notifications — triggered on upgrade).
- **Note:** Webhook endpoint must be exempted from JWT auth middleware. Use a raw `Request` body for signature verification.

---

## 4.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma backend is FastAPI + PostgreSQL + SQLAlchemy 2.x. The `users` table has a `role` column (`user | premium | admin`). The `TailorJob` daily limits already check `user.role`. Config is `backend/app/core/config.py` using `pydantic_settings.BaseSettings`. The existing tailor limit logic is in `backend/app/crud/tailor_job.py`. Frontend is React + TypeScript + Tailwind + Zustand auth store (`stores/index.ts` exposes `user: User`). The `User` type is defined in `frontend/src/types/index.ts`.
>
> **Task:** Implement a Stripe subscription billing system. Backend: two endpoints — `POST /api/v1/billing/create-checkout-session` (authenticated, creates a Stripe Checkout Session for the premium monthly plan and returns `{ checkout_url }`) and `POST /api/v1/billing/webhook` (unauthenticated raw body, verifies Stripe signature, handles `checkout.session.completed` to set `user.role = premium` and store `stripe_customer_id` / `stripe_subscription_id`, and `customer.subscription.deleted` to downgrade user back to `user` role). Also add `GET /api/v1/billing/portal` to create a Stripe Customer Portal session for managing billing. Add Alembic migration for new user columns.
>
> **Create these files exactly:**
> 1. `backend/alembic/versions/0006_add_stripe_fields_to_users.py` — Migration adding `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `subscription_ends_at` to `users` table.
> 2. `backend/app/models/user.py` — Add the four new columns.
> 3. `backend/app/schemas/billing.py` — `CheckoutSessionResponse` (`checkout_url: str`), `PortalSessionResponse` (`portal_url: str`).
> 4. `backend/app/schemas/user.py` — Add `stripe_customer_id`, `subscription_status`, `subscription_ends_at` to `UserPublic` schema.
> 5. `backend/app/core/config.py` — Add `STRIPE_SECRET_KEY: str = ""`, `STRIPE_WEBHOOK_SECRET: str = ""`, `STRIPE_PREMIUM_PRICE_ID: str = ""`.
> 6. `backend/app/api/v1/endpoints/billing.py` — Three endpoints as described. For the webhook, read raw body with `await request.body()` before any parsing. Use `stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)`. Return `{"status": "ok"}` on success, 400 on signature failure. Guard all Stripe calls behind `if not settings.STRIPE_SECRET_KEY: raise HTTPException(503)`.
> 7. `backend/app/main.py` — Register billing router. The webhook route must receive raw bytes — ensure it is added before any JSON middleware that would consume the body.
> 8. `backend/tests/test_billing_endpoints.py` — Tests: create-checkout-session returns URL (mock stripe.checkout.Session.create), webhook with valid signature sets user role to premium (mock stripe.Webhook.construct_event), webhook with bad signature returns 400, portal endpoint returns URL. All without real Stripe calls.
> 9. `frontend/src/services/billingApi.ts` — `createCheckoutSession()` and `createPortalSession()`.
> 10. `frontend/src/components/billing/PlanCard.tsx` — Card showing plan name, price, feature list, and CTA button.
> 11. `frontend/src/components/billing/UpgradePrompt.tsx` — Inline CTA component for use inside feature-gated sections.
> 12. `frontend/src/pages/Plans.tsx` — Two-column plan comparison (Free vs Premium) using `PlanCard`. "Upgrade" button calls `createCheckoutSession` then `window.location.href = checkout_url`.
> 13. `frontend/src/pages/BillingSuccess.tsx` — Success confirmation page at `/billing/success`. Calls `authApi.me()` to refresh user and update store, then shows confirmation.
> 14. `frontend/src/pages/BillingCancel.tsx` — Cancelled page at `/billing/cancel`.
> 15. Add all three routes to `App.tsx` and a "Plans" link in `AppLayout`.
>
> **Success Criteria:** `cd backend && pytest tests/test_billing_endpoints.py -v` passes. `cd frontend && npm run build` passes. With test Stripe keys, clicking Upgrade redirects to Stripe Checkout. Webhook test (via Stripe CLI `stripe trigger checkout.session.completed`) upgrades the user role.

---
---

# Section 5: Smart Notifications System

**Weeks 9–10 | Engagement**

## 5.1 Architecture Design

Notifications serve two purposes: in-app alerts (bell icon) and email reminders (via SendGrid). The system is event-driven — backend events trigger notifications, which are stored in a `notifications` table and optionally emailed.

### Database Schema

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(100) NOT NULL,
    -- types: follow_up_reminder | interview_reminder | application_stale
    --        tailor_complete | upgrade_success | weekly_summary
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    is_read         BOOLEAN DEFAULT FALSE,
    related_id      UUID,          -- application_id or tailor_job_id
    related_type    VARCHAR(50),   -- application | tailor_job
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_unread  ON notifications(user_id, is_read) WHERE is_read = FALSE;
```

### Notification Triggers

| Trigger | Type | Timing |
|---------|------|--------|
| Application moved to `interview` | `interview_reminder` | Immediate + 1-day-before email |
| Application in `applied` > 7 days | `application_stale` | Celery beat daily at 8 AM UTC |
| Tailor job completes | `tailor_complete` | Immediate (in tailor task) |
| User upgrades to premium | `upgrade_success` | Immediate (in billing webhook) |
| Weekly summary | `weekly_summary` | Celery beat Monday 8 AM UTC |

### Email Provider

SendGrid (`sendgrid` Python package). Two email types:
1. **Transactional** — immediate (tailor complete, interview scheduled)
2. **Digest** — weekly summary (application counts, next steps)

---

## 5.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| CREATE | `backend/alembic/versions/0007_add_notifications_table.py` | 40 |
| CREATE | `backend/app/models/notification.py` | 40 |
| CREATE | `backend/app/schemas/notification.py` | 50 |
| CREATE | `backend/app/crud/notification.py` | 60 |
| CREATE | `backend/app/services/email_service.py` | 100 |
| CREATE | `backend/app/services/notification_service.py` | 100 |
| CREATE | `backend/app/api/v1/endpoints/notifications.py` | 100 |
| CREATE | `backend/app/tasks/notifications.py` | 100 |
| MODIFY | `backend/app/tasks/tailor.py` | +5 lines |
| MODIFY | `backend/app/api/v1/endpoints/billing.py` | +5 lines |
| MODIFY | `backend/app/api/v1/endpoints/applications.py` | +5 lines |
| MODIFY | `backend/app/core/config.py` | +2 lines |
| MODIFY | `backend/app/main.py` | +4 lines |
| CREATE | `backend/tests/test_notifications.py` | 80 |
| CREATE | `frontend/src/components/notifications/NotificationBell.tsx` | 80 |
| CREATE | `frontend/src/components/notifications/NotificationList.tsx` | 80 |
| CREATE | `frontend/src/services/notificationsApi.ts` | 40 |
| CREATE | `frontend/src/stores/notifications.ts` | 60 |
| MODIFY | `frontend/src/components/layout/AppLayout.tsx` | +10 lines |

**Total: ~900 lines new, ~30 lines modified**

---

## 5.3 Dependencies

- **Requires:** Section 1 (applications — stale application detection).
- **Requires:** Section 4 (billing webhook — upgrade notification).
- **Requires:** `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL` in Railway environment.
- **Requires:** `sendgrid` Python package (`pip install sendgrid`).

---

## 5.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma backend uses FastAPI, PostgreSQL, Celery with Redis as the broker (configured in `backend/app/tasks/celery_app.py`). The tailor Celery task is in `backend/app/tasks/tailor.py` and calls `notification_service` (to be created) at the end of `run_tailoring()`. The billing webhook is in `backend/app/api/v1/endpoints/billing.py`. The applications PATCH endpoint is in `backend/app/api/v1/endpoints/applications.py`. All Celery tasks import from `backend/app/tasks/celery_app.py`. Celery beat schedule is added by modifying `celery_app.py`. Config uses `pydantic_settings.BaseSettings`.
>
> **Task:** Implement the in-app and email notification system. Create a `notifications` table. All notification creation goes through `notification_service.create_notification(db, user_id, type, title, body, related_id, related_type)` which inserts a row and optionally sends an email via SendGrid. The API exposes: `GET /api/v1/notifications` (paginated, newest first), `PATCH /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/mark-all-read`. Create two Celery beat tasks: `check_stale_applications` (daily 8 AM UTC — finds applications in `applied` status with `applied_date < NOW() - 7 days` and creates `application_stale` notifications) and `send_weekly_summary` (Monday 8 AM UTC — creates `weekly_summary` notifications with application funnel counts). Hook notifications into: tailor task completion, billing webhook upgrade, and application status change to `interview`.
>
> **Create these files exactly:**
> 1. `backend/alembic/versions/0007_add_notifications_table.py` — Migration adding `notifications` table.
> 2. `backend/app/models/notification.py` — SQLAlchemy `Notification` model.
> 3. `backend/app/schemas/notification.py` — `NotificationPublic`, `NotificationList` schemas.
> 4. `backend/app/crud/notification.py` — `create`, `get_for_user` (paginated), `mark_read`, `mark_all_read`.
> 5. `backend/app/services/email_service.py` — `send_email(to_email, subject, html_body)` using SendGrid. Guard with `if not settings.SENDGRID_API_KEY: return` so it is a no-op in tests. Template emails for `tailor_complete`, `interview_reminder`, `application_stale`, `weekly_summary`.
> 6. `backend/app/services/notification_service.py` — `create_notification(db, user_id, type, title, body, related_id=None, related_type=None, send_email=False, email=None)`. Calls `crud_notification.create` then optionally `email_service.send_email`.
> 7. `backend/app/tasks/notifications.py` — Two Celery tasks: `check_stale_applications` and `send_weekly_summary`. Register in `celery_app.py` beat schedule.
> 8. `backend/app/api/v1/endpoints/notifications.py` — Three endpoints as described.
> 9. Modify `backend/app/tasks/tailor.py` — After saving the result, call `notification_service.create_notification(...)` with type `tailor_complete`.
> 10. Modify `backend/app/api/v1/endpoints/billing.py` — After setting role to premium, call `notification_service.create_notification(...)` with type `upgrade_success`.
> 11. Modify `backend/app/api/v1/endpoints/applications.py` — In the PATCH handler, if `new_status == "interview"`, call `notification_service.create_notification(...)` with type `interview_reminder`.
> 12. `backend/tests/test_notifications.py` — Tests: list notifications returns paginated results, mark-read sets is_read, mark-all-read clears all, stale application task creates notification (mock DB query), email_service is a no-op when SENDGRID_API_KEY is empty.
> 13. `frontend/src/services/notificationsApi.ts` — Axios calls for the three endpoints.
> 14. `frontend/src/stores/notifications.ts` — Zustand store with `notifications`, `unreadCount`, `fetchNotifications`, `markRead`, `markAllRead`.
> 15. `frontend/src/components/notifications/NotificationList.tsx` — Dropdown list of notifications with unread styling and "Mark all read" button.
> 16. `frontend/src/components/notifications/NotificationBell.tsx` — Bell icon with unread badge. Clicking toggles `NotificationList` popover. Placed in `AppLayout` header. Polls every 60 seconds.
>
> **Success Criteria:** `cd backend && pytest tests/test_notifications.py -v` passes. `cd frontend && npm run build` passes. Bell icon appears in the app header. Completing a tailor job creates a notification that appears in the bell dropdown.

---
---

# Section 6: Resume Version History

**Weeks 6–7 | CV Management (Parallel with Section 3–4)**

## 6.1 Architecture Design

Every tailored CV is already linked to a parent via `cvs.parent_cv_id`. This section surfaces that history in the UI and adds a diff viewer to compare any two CV versions side-by-side.

### Data Model (No New Tables)

The `cvs` table already has:
- `parent_cv_id` → forms a version tree
- `is_tailored` → true for tailored variants
- `tailor_job_id` → links to the tailoring context

New: a dedicated `GET /api/v1/cvs/{id}/history` endpoint traverses the parent chain and returns the full version tree.

### Version Tree Example

```
CV v1 (original, id: aaa)
├── CV v2 (tailored for Google, id: bbb, parent: aaa)
│   └── CV v3 (tailored for Meta, id: ccc, parent: bbb)
└── CV v4 (tailored for Stripe, id: ddd, parent: aaa)
```

### Section-Level Diff

Tailored CVs store `tailor_job.result_json` which contains the section-by-section diff. Re-expose this as `GET /api/v1/cvs/{id}/diff` to retrieve the original sections and tailored sections for side-by-side comparison.

---

## 6.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| MODIFY | `backend/app/api/v1/endpoints/cvs.py` | +60 lines (2 new endpoints) |
| MODIFY | `backend/app/crud/cv.py` | +40 lines |
| MODIFY | `backend/app/schemas/cv.py` | +30 lines |
| CREATE | `backend/tests/test_cv_history_endpoints.py` | 80 |
| CREATE | `frontend/src/components/cvs/VersionHistory.tsx` | 120 |
| CREATE | `frontend/src/components/cvs/VersionDiffViewer.tsx` | 150 |
| CREATE | `frontend/src/components/cvs/VersionTreeNode.tsx` | 60 |
| MODIFY | `frontend/src/pages/CVs.tsx` | +60 lines (history panel) |
| MODIFY | `frontend/src/services/api.ts` | +3 functions |

**Total: ~450 lines new, ~190 lines modified**

---

## 6.3 Dependencies

- **Requires:** None (builds only on existing `cvs` and `tailor_jobs` tables).
- **Blocks:** Nothing critical. Can be delivered in parallel with Sections 3–4.
- **Note:** `tailor_job.result_json` already stores the diff data from Phase 9.

---

## 6.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma already has a complete CV management system. The `cvs` table has `parent_cv_id` (self-referential FK), `is_tailored`, `tailor_job_id`. The `tailor_jobs` table has `result_json` (a JSON field containing section-by-section diffs produced by `tailor_service.py`). The `result_json` structure is: `{ sections: [{ name: str, original: str, tailored: str, changes: int }] }`. The existing CV endpoints are in `backend/app/api/v1/endpoints/cvs.py`. The existing CV schemas are in `backend/app/schemas/cv.py`. The existing CRUD is in `backend/app/crud/cv.py`. The CV management page is `frontend/src/pages/CVs.tsx` which shows a list of CVs with upload, download, and delete actions.
>
> **Task:** Add resume version history and section-level diff viewing. Backend: two new endpoints on the CVs router — `GET /api/v1/cvs/{id}/history` returns the full version chain (root → descendants) as a tree structure, and `GET /api/v1/cvs/{id}/diff` returns the section diffs from `tailor_job.result_json` for that CV (404 if CV is not tailored or has no tailor job). Frontend: add a "Version History" panel to the existing CVs page that shows the tree of versions for the selected CV, and a diff viewer modal that shows original vs tailored sections side-by-side.
>
> **Create these files exactly:**
> 1. `backend/app/schemas/cv.py` — Add `CVVersionNode` (id, title, is_tailored, created_at, children: list[CVVersionNode]), `CVDiffSection` (name, original, tailored, changes), `CVDiffResponse` (cv_id, sections: list[CVDiffSection]).
> 2. `backend/app/crud/cv.py` — Add `get_version_tree(db, root_cv_id)` which recursively builds the version tree; `get_cv_diff(db, cv_id, user_id)` which fetches the associated tailor_job and returns its result_json parsed as `CVDiffResponse`.
> 3. `backend/app/api/v1/endpoints/cvs.py` — Add `GET /{id}/history` returning `CVVersionNode` tree (finds root by traversing parent_cv_id chain upward, then builds tree downward), and `GET /{id}/diff` returning `CVDiffResponse`.
> 4. `backend/tests/test_cv_history_endpoints.py` — Tests: get history returns tree with root and children, get diff returns section data, get diff on non-tailored CV returns 404, unauthorized returns 401.
> 5. `frontend/src/services/api.ts` — Add `cvApi.getHistory(id)` and `cvApi.getDiff(id)`.
> 6. `frontend/src/components/cvs/VersionTreeNode.tsx` — Renders a single CV in the tree with indentation, name, date, tailored badge, and click to view.
> 7. `frontend/src/components/cvs/VersionHistory.tsx` — Panel that shows the version tree for the selected CV using `VersionTreeNode`. Appears as a slide-in drawer or expandable section on the CVs page.
> 8. `frontend/src/components/cvs/VersionDiffViewer.tsx` — Modal showing the section diff. Left column = original text, right column = tailored text. Changed sections highlighted in yellow. Uses the existing `SectionDiff` component from `frontend/src/components/tailor/SectionDiff.tsx` if possible, or builds a simpler version.
> 9. `frontend/src/pages/CVs.tsx` — Add a "History" button to each tailored CV card. Clicking opens `VersionHistory` drawer. Inside the drawer, clicking a tailored version shows `VersionDiffViewer` modal.
>
> **Success Criteria:** `cd backend && pytest tests/test_cv_history_endpoints.py -v` passes. `cd frontend && npm run build` passes. On the CVs page, clicking History on a tailored CV shows the version tree. Clicking a version shows the section diff modal.

---
---

# Section 7: Personal Application Analytics

**Weeks 11–12 | Insights**

## 7.1 Architecture Design

While the existing Analytics page shows market-wide data (powered by Airflow/dbt), this section adds **personal analytics** — metrics about the user's own application pipeline.

### Metrics to Surface

| Metric | Calculation |
|--------|-------------|
| Application funnel | Count per status |
| Response rate | `(phone_screen + interview + offer) / applied * 100%` |
| Offer rate | `offer / applied * 100%` |
| Average days to response | Mean days from `applied_date` to first status change past `applied` |
| Applications per week | Time series of new applications |
| Top sources | Count of applications by `source` |
| Top companies applied to | Frequency chart |
| Salary range distribution | Histogram of salary_min/max from applications |

### API Endpoint

```
GET /api/v1/applications/analytics
Response: {
  funnel: { wishlist: int, applied: int, phone_screen: int, interview: int, offer: int, rejected: int, withdrawn: int },
  response_rate: float,
  offer_rate: float,
  avg_days_to_response: float | null,
  applications_per_week: [{ week: str, count: int }],
  top_sources: [{ source: str, count: int }],
  salary_distribution: { min: int, max: int, median: int, buckets: [{ range: str, count: int }] }
}
```

### Frontend

A new tab on the existing **Analytics** page (or a sub-section "My Applications" tab within the Applications page). Uses Recharts charts already used in the market analytics dashboard.

---

## 7.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| MODIFY | `backend/app/api/v1/endpoints/applications.py` | +60 lines |
| MODIFY | `backend/app/crud/application.py` | +80 lines |
| CREATE | `backend/app/schemas/application_analytics.py` | 60 |
| CREATE | `backend/tests/test_application_analytics.py` | 60 |
| CREATE | `frontend/src/components/applications/PersonalAnalytics.tsx` | 200 |
| CREATE | `frontend/src/components/applications/FunnelChart.tsx` | 80 |
| CREATE | `frontend/src/components/applications/ResponseRateCard.tsx` | 60 |
| CREATE | `frontend/src/components/applications/ApplicationsOverTimeChart.tsx` | 80 |
| CREATE | `frontend/src/components/applications/SourceBreakdownChart.tsx` | 80 |
| MODIFY | `frontend/src/pages/Applications.tsx` | +30 lines (analytics tab) |
| MODIFY | `frontend/src/services/applicationsApi.ts` | +1 function |

**Total: ~700 lines new, ~90 lines modified**

---

## 7.3 Dependencies

- **Requires:** Section 1 (applications backend) and Section 2 (Kanban UI — Applications page).
- **Blocks:** Nothing. Final feature in the applications cluster.
- **Note:** Queries are user-scoped so no analytics DB (dbt/Airflow) is needed — run directly against `applications` table.

---

## 7.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma has a market analytics page (`frontend/src/pages/Analytics.tsx`) using Recharts. The backend analytics endpoints are in `backend/app/api/v1/endpoints/analytics/`. The application tracker was built in Section 1 — `applications` table with columns: `status`, `applied_date`, `source`, `salary_min`, `salary_max`, `created_at`. The CRUD layer is `backend/app/crud/application.py`. The applications endpoint file is `backend/app/api/v1/endpoints/applications.py`. Frontend applications store is `frontend/src/stores/applications.ts`.
>
> **Task:** Add a personal application analytics endpoint and UI. Backend: add `GET /api/v1/applications/analytics` (authenticated, user-scoped) that runs SQL queries against the user's `applications` rows. Queries: funnel counts by status (GROUP BY status), response_rate and offer_rate as floats, average days from applied_date to first event where new_value != 'applied' (JOIN application_events), weekly application counts for the past 12 weeks, top 5 sources by count, salary distribution (buckets: <30k, 30–60k, 60–90k, 90–120k, 120k+). Frontend: add a "My Stats" tab to the Applications page that renders personal analytics using Recharts charts matching the existing Analytics page style.
>
> **Create these files exactly:**
> 1. `backend/app/schemas/application_analytics.py` — Pydantic schemas for `ApplicationAnalytics` response matching the structure above.
> 2. `backend/app/crud/application.py` — Add `get_analytics(db, user_id)` function running all required queries using SQLAlchemy Core (raw SQL via `text()` is acceptable for complex aggregations).
> 3. `backend/app/api/v1/endpoints/applications.py` — Add `GET /applications/analytics` endpoint. NOTE: register this route before `GET /applications/{id}` to avoid FastAPI treating "analytics" as an ID path parameter.
> 4. `backend/tests/test_application_analytics.py` — Tests: analytics returns correct structure with mocked DB, response_rate is 0 when no applications past applied, endpoint requires authentication.
> 5. `frontend/src/services/applicationsApi.ts` — Add `fetchApplicationAnalytics()` function.
> 6. `frontend/src/components/applications/FunnelChart.tsx` — Recharts `BarChart` showing application counts per status in pipeline order (wishlist → offer). Color-coded bars per status.
> 7. `frontend/src/components/applications/ResponseRateCard.tsx` — KPI card (reuse `KPICard` from analytics components) showing response_rate % and offer_rate % side by side.
> 8. `frontend/src/components/applications/ApplicationsOverTimeChart.tsx` — Recharts `LineChart` showing weekly application count for past 12 weeks.
> 9. `frontend/src/components/applications/SourceBreakdownChart.tsx` — Recharts `PieChart` of top sources.
> 10. `frontend/src/components/applications/PersonalAnalytics.tsx` — Container rendering all four chart components above in a 2×2 grid, with loading skeleton and empty state (same pattern as `frontend/src/components/analytics/LoadingSkeleton.tsx`).
> 11. `frontend/src/pages/Applications.tsx` — Add a tab bar: "Board" (Kanban) and "My Stats" (PersonalAnalytics). Default tab is "Board". Switching to "My Stats" fetches and renders PersonalAnalytics.
>
> **Success Criteria:** `cd backend && pytest tests/test_application_analytics.py -v` passes. `cd frontend && npm run build` passes. On the Applications page, switching to the "My Stats" tab shows the four charts populated with the user's data.

---
---

# Section 8: Mobile Responsive Polish

**Week 13 | UX**

## 8.1 Architecture Design

No backend changes. This section makes every page fully usable on 375px–768px screens. Key challenges:
- Kanban board: collapse to a single-column list view on mobile
- Analytics charts: switch to compact Recharts responsive containers
- Forms and modals: full-screen on mobile
- Navigation: hamburger menu replacing the sidebar

### Responsive Breakpoint Strategy

```
Mobile:  < 768px  (sm in Tailwind)
Tablet:  768–1024px  (md in Tailwind)
Desktop: > 1024px  (lg in Tailwind)
```

### Per-Page Mobile Changes

| Page | Change |
|------|--------|
| AppLayout | Hamburger menu, slide-out sidebar overlay |
| Applications (Kanban) | Horizontal scroll on tablet; single-column list with status badge on mobile |
| Analytics | Charts use `<ResponsiveContainer width="100%" height={200}>` |
| CVs | Cards stack vertically, action buttons collapse to icon-only |
| Jobs | Same as CVs |
| AI Tailor | Step indicator becomes vertical on mobile |
| Modals/Drawers | Full-screen (`w-full h-full`) on mobile |
| Plans | Cards stack vertically |

---

## 8.2 Files to Create / Modify

| Action | Path | Approx Lines Changed |
|--------|------|---------------------|
| MODIFY | `frontend/src/components/layout/AppLayout.tsx` | +60 lines |
| CREATE | `frontend/src/components/layout/MobileNav.tsx` | 80 lines |
| MODIFY | `frontend/src/components/applications/KanbanBoard.tsx` | +40 lines |
| MODIFY | `frontend/src/pages/Applications.tsx` | +20 lines |
| MODIFY | `frontend/src/pages/Analytics.tsx` | +30 lines |
| MODIFY | `frontend/src/pages/CVs.tsx` | +20 lines |
| MODIFY | `frontend/src/pages/Jobs.tsx` | +20 lines |
| MODIFY | `frontend/src/pages/AITailor.tsx` | +20 lines |
| MODIFY | `frontend/src/pages/Plans.tsx` | +10 lines |
| MODIFY | `frontend/src/components/applications/AddApplicationModal.tsx` | +10 lines |
| MODIFY | `frontend/src/components/applications/ApplicationDrawer.tsx` | +15 lines |

**Total: ~80 lines new, ~245 lines modified**

---

## 8.3 Dependencies

- **Requires:** Sections 2, 3, 4 (all pages must exist before polishing).
- **Blocks:** Nothing. Final UI pass before monitoring.

---

## 8.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma frontend is React + TypeScript + Tailwind CSS v3. The app uses a sidebar layout via `frontend/src/components/layout/AppLayout.tsx`. All pages are listed in `frontend/src/App.tsx`. The project uses Tailwind's `sm:`, `md:`, `lg:` responsive prefixes. The app currently has no mobile-specific layout — the sidebar is always visible and charts have fixed pixel heights. Recharts components are wrapped in `<div className="w-full h-[300px]">`. The Kanban board in `frontend/src/components/applications/KanbanBoard.tsx` uses `@dnd-kit` with horizontal columns.
>
> **Task:** Make the entire application mobile-responsive for screens from 375px to 1440px. This is a polish pass — no new features, only responsive adjustments. Every change must use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`). Do not change the desktop layout.
>
> **Modify these files:**
> 1. `frontend/src/components/layout/AppLayout.tsx` — On mobile (`< md`): hide the sidebar, show a hamburger button in the top bar that toggles a full-width overlay nav (`MobileNav`). On `md+`: restore the existing sidebar layout.
> 2. `frontend/src/components/layout/MobileNav.tsx` (new file) — Full-screen overlay nav showing all nav links and a close button. Closes on nav link click. Animates in from left with Tailwind `transition-transform`.
> 3. `frontend/src/components/applications/KanbanBoard.tsx` — On mobile: render a vertical list of application cards grouped by status (accordion-style per status group) instead of horizontal columns. On `md+`: render the existing horizontal Kanban.
> 4. `frontend/src/pages/Analytics.tsx` — Replace all fixed-height `div` wrappers on charts with `<div className="w-full h-48 md:h-72">`. Ensure all Recharts components use `<ResponsiveContainer width="100%" height="100%">`.
> 5. `frontend/src/pages/CVs.tsx` — CV cards: stack action buttons vertically on mobile with `flex-col sm:flex-row`. Title truncates with `truncate`.
> 6. `frontend/src/pages/Jobs.tsx` — Same pattern as CVs.
> 7. `frontend/src/pages/AITailor.tsx` — Step indicator: vertical on mobile (`flex-col sm:flex-row`). Section diff panels: stack vertically on mobile.
> 8. `frontend/src/pages/Plans.tsx` — Plan cards: `flex-col md:flex-row` so they stack on mobile.
> 9. `frontend/src/components/applications/AddApplicationModal.tsx` — Modal: `w-full h-full rounded-none sm:w-[600px] sm:h-auto sm:rounded-lg` so it is full-screen on mobile.
> 10. `frontend/src/components/applications/ApplicationDrawer.tsx` — Drawer: `w-full sm:w-[480px]` and position from bottom on mobile (`bottom-0`) vs right on desktop.
>
> **Success Criteria:** `cd frontend && npm run build` passes with zero TypeScript errors. All pages render without horizontal overflow at 375px viewport width. The sidebar is hidden on mobile and replaced by the hamburger menu. The Kanban board shows a grouped vertical list on mobile.

---
---

# Section 9: Monitoring & Observability

**Week 14 | Production Health**

## 9.1 Architecture Design

Production monitoring across three layers: error tracking (Sentry), structured logging, and health check endpoints. No new database tables needed.

### Components

```
Sentry (Error Tracking)
├── Backend: sentry_sdk FastAPI integration
│   └── Captures unhandled exceptions + slow queries
└── Frontend: @sentry/react + @sentry/vite-plugin
    └── Captures JS errors + web vitals

Structured Logging (backend)
└── Replace print() with Python logging module
    └── JSON format with request_id, user_id, endpoint, duration

Health Endpoints
├── GET /health (existing — enhance)
└── GET /api/v1/health/detailed (new)
    └── Checks: DB ping, Redis ping, Celery ping, Adzuna reachable
```

### Health Check Response

```json
{
  "status": "healthy | degraded | unhealthy",
  "version": "10.0.0",
  "checks": {
    "database": { "status": "ok", "latency_ms": 12 },
    "redis":    { "status": "ok", "latency_ms": 3 },
    "celery":   { "status": "ok", "active_workers": 1 },
    "adzuna":   { "status": "ok" }
  },
  "timestamp": "2026-05-14T08:00:00Z"
}
```

### Alerting Strategy (Railway)

Railway supports health check URLs — set `RAILWAY_HEALTHCHECK_PATH=/health`. No additional tooling needed; Railway will restart unhealthy instances.

---

## 9.2 Files to Create / Modify

| Action | Path | Approx Lines |
|--------|------|-------------|
| MODIFY | `backend/app/main.py` | +20 lines (Sentry init, request logging middleware) |
| MODIFY | `backend/app/api/v1/endpoints/` (health.py — new) | 80 |
| MODIFY | `backend/app/core/config.py` | +2 lines (SENTRY_DSN) |
| CREATE | `backend/app/core/logging_config.py` | 40 |
| CREATE | `backend/tests/test_health_endpoints.py` | 60 |
| MODIFY | `frontend/vite.config.ts` | +10 lines (Sentry plugin) |
| MODIFY | `frontend/src/main.tsx` | +10 lines (Sentry init) |
| MODIFY | `frontend/package.json` | +2 deps |
| MODIFY | `backend/requirements.txt` | +1 line (sentry-sdk) |

**Total: ~200 lines new, ~45 lines modified**

---

## 9.3 Dependencies

- **Requires:** All sections complete (this is the final production hardening step).
- **Blocks:** Nothing. Delivers to `main` after this.
- **Credentials:** `SENTRY_DSN` (backend + frontend separate DSNs) in Railway and Vercel.
- **Note:** Sentry init must happen before any routes are registered in `main.py`.

---

## 9.4 Detailed Prompt for Claude Chat

> **Context:** ApplyLuma backend is FastAPI running on Railway. `backend/app/main.py` creates the FastAPI app, registers middleware (rate limiting), and includes all routers. The existing `GET /health` endpoint returns `{ status: "ok", version: "..." }`. Config is in `backend/app/core/config.py`. Frontend is a React Vite app deployed on Vercel. The entry point is `frontend/src/main.tsx`. The Vite config is `frontend/vite.config.ts`. Backend Python packages are listed in `backend/requirements.txt`.
>
> **Task:** Add production monitoring across the stack. Backend: integrate `sentry-sdk` with FastAPI integration, configure structured JSON logging with request IDs, and add a detailed health check endpoint. Frontend: integrate `@sentry/react` with source maps. Do not break any existing tests.
>
> **Create/modify these files exactly:**
> 1. `backend/app/core/config.py` — Add `SENTRY_DSN: str = ""` and `LOG_LEVEL: str = "INFO"`.
> 2. `backend/app/core/logging_config.py` — Configure Python `logging` module: JSON formatter outputting `{ timestamp, level, message, request_id, path, method, duration_ms, user_id }`. Export `setup_logging()` function.
> 3. `backend/app/main.py` — At startup: call `setup_logging()`, then `sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FastApiIntegration()], traces_sample_rate=0.1)` guarded by `if settings.SENTRY_DSN`. Add a middleware that generates a `request_id` UUID per request, logs request start/end with duration.
> 4. `backend/app/api/v1/endpoints/health.py` — New file with `GET /health/detailed` endpoint. Checks: DB (run `SELECT 1`), Redis (run `PING`), Celery (inspect active workers via `celery_app.control.inspect().active()`), Adzuna (check if `settings.ADZUNA_APP_ID` is configured, do not make HTTP call). Returns the structured response above. Sets overall status to `degraded` if any non-critical check fails, `unhealthy` if DB fails. Requires no auth.
> 5. `backend/app/main.py` — Register health router at prefix `/api/v1`.
> 6. `backend/requirements.txt` — Add `sentry-sdk[fastapi]>=2.0.0`.
> 7. `backend/tests/test_health_endpoints.py` — Tests: `/health` returns 200, `/api/v1/health/detailed` returns valid structure with mocked DB/Redis/Celery, status is `degraded` when Redis fails, status is `unhealthy` when DB fails.
> 8. `frontend/package.json` — Add `@sentry/react` and `@sentry/vite-plugin`.
> 9. `frontend/vite.config.ts` — Add `sentryVitePlugin({ org: ..., project: ... })` wrapped in `if (process.env.SENTRY_AUTH_TOKEN)` guard so local builds without the token still work.
> 10. `frontend/src/main.tsx` — Add `Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN, integrations: [Sentry.browserTracingIntegration()], tracesSampleRate: 0.1 })` guarded by `if (import.meta.env.VITE_SENTRY_DSN)`.
>
> **Success Criteria:** `cd backend && pytest tests/test_health_endpoints.py -v` passes. `cd frontend && npm run build` passes. `GET /api/v1/health/detailed` returns JSON with all four check results. With real Sentry DSN set, errors are captured in the Sentry dashboard. The `/health` endpoint is registered as the Railway health check URL.

---
---

## Final Integration Checklist

After all 9 sections are complete, run the full integration on `dev` branch:

```bash
# Backend
cd backend
alembic upgrade head
pytest -v

# Frontend
cd frontend
npm install
npm run build
npm test

# Data Pipeline
PYTHONPATH=$(pwd)/airflow/dags:$(pwd)/airflow/plugins pytest airflow/tests/
cd dbt && dbt deps --profiles-dir . && dbt parse --profiles-dir .
```

### Environment Variables to Add Before Deployment

| Variable | Service | Section |
|----------|---------|---------|
| `ADZUNA_APP_ID` | Railway | 3 |
| `ADZUNA_API_KEY` | Railway | 3 |
| `ADZUNA_COUNTRY` | Railway | 3 |
| `STRIPE_SECRET_KEY` | Railway | 4 |
| `STRIPE_WEBHOOK_SECRET` | Railway | 4 |
| `STRIPE_PREMIUM_PRICE_ID` | Railway | 4 |
| `SENDGRID_API_KEY` | Railway | 5 |
| `SENDGRID_FROM_EMAIL` | Railway | 5 |
| `SENTRY_DSN` (backend) | Railway | 9 |
| `VITE_SENTRY_DSN` (frontend) | Vercel | 9 |

### Deployment Sequence

```
1. Merge dev → main only after ALL tests pass
2. Railway auto-deploys backend (~3 min)
3. Vercel auto-deploys frontend (~2 min)
4. Run alembic upgrade head on Railway (via Railway CLI or one-off container)
5. Verify /api/v1/health/detailed returns healthy
6. Verify Sentry receives a test error
7. Smoke test each new feature end-to-end in production
```

---

*Document version: Phase 10 initial plan — 2026-05-14*
