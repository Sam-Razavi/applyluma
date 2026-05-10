# ApplyLuma AI Context

This file is the project source of truth for AI assistants working in the
ApplyLuma repository. Update it as the project evolves.

---

## Current State (Read This First)

**ApplyLuma is LIVE at https://applyluma.com**

- **Current Phase:** 8 — Connect Airflow to Railway PostgreSQL
- **Previous phases completed:** 1–7 (core features, data pipeline, analytics API,
  analytics dashboard) + 7.5 (production deployment)
- **Blocking issue:** Analytics endpoints return 500 errors because the analytics
  data tables are empty. Airflow is local only; it has not yet written scraped
  data into the Railway production database. Phase 8 fixes this.

**What is working in production right now:**
- JWT authentication
- Resume upload and AI CV analysis (OpenAI)
- Job search (Adzuna)
- Job description management
- Analytics dashboard UI (12 charts render; show empty/loading states until data
  arrives)

**What needs Phase 8 to work:**
- Analytics endpoints (currently 500 — expected, not a regression)
- Any chart that depends on scraped job-market data

---

## Project Overview

ApplyLuma is a full-stack AI job search and resume optimization platform.

- **Status:** Phases 1–7.5 complete, Phase 8 starting
- **Tech stack:** FastAPI, PostgreSQL, Redis, React 18, TypeScript, Vite,
  Tailwind CSS, Recharts, Apache Airflow, dbt
- **Local dev:** Docker Compose
- **Production:** Vercel (frontend) + Railway (backend, PostgreSQL, Redis)

---

## Production Architecture

Frontend:
- URL: https://applyluma.com
- Platform: Vercel (free tier)
- Auto-deploys from `main` branch
- Build: `npm run build` in `frontend/`, output `dist/`

Backend:
- URL: https://applyluma-production.up.railway.app
- Platform: Railway (Hobby, ~$5/mo)
- Runtime: Docker, port `8080`
- Auto-deploys from `main` branch

Database:
- Railway PostgreSQL
- `applyluma` — application data (users, resumes, saved jobs, raw analytics)
- `airflow_db` — Airflow metadata only; keep separate from app database

Cache:
- Railway Redis

DNS:
- Registered via Namecheap, pointed to Vercel nameservers
- SSL auto-provisioned by Vercel

---

## Tech Stack

Backend:
- FastAPI 0.104+
- SQLAlchemy + Alembic (ORM and migrations)
- Pydantic schemas for validation
- JWT authentication
- Docker on Railway, port 8080

Frontend:
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS
- Recharts (all analytics charts)
- Axios with auth interceptors
- Dev port: 5173

Data pipeline (local only until Phase 8):
- Apache Airflow — DAG orchestration, job scraping
- dbt — transforms raw data into analytics views

External integrations:
- OpenAI API — CV/resume analysis
- Adzuna API — job search data

---

## Database Structure

Application tables:
- `users` — user accounts
- `resumes` — user resumes (multiple per user)
- `saved_jobs` — user-saved job postings

Raw tables (populated by Airflow scraping):
- `raw_job_postings` — Adzuna API responses (unprocessed)
- `raw_company_data` — company info

dbt analytics views (created by Phase 5 dbt models):
- `analytics.job_postings` — deduplicated, cleaned jobs
- `analytics.skill_frequency` — top skills by count
- `analytics.salary_by_location` — salary ranges
- `analytics.company_hiring_patterns` — hiring trends
- `analytics.job_market_health` — overall metrics

These views are empty in production until Phase 8 connects Airflow to Railway.

---

## Completed Phases

### Phases 1–4: Core Features
- Job search via Adzuna API with filters
- Resume upload and storage
- AI-powered resume analysis (OpenAI)
- Job description management

### Phase 5: Data Engineering
- Airflow DAGs for daily job scraping (`airflow/dags/scrape_jobs.py`)
- dbt models for analytics layer (`dbt/models/marts/`)
- Data quality framework (dedup, validation)
- Two-database separation: `applyluma` and `airflow_db`

### Phase 6: Analytics API — COMPLETE
- 12 RESTful endpoints under `/api/v1/analytics/`
- 11 public + 1 authenticated (comparison, requires resume)
- Redis caching, 1-hour TTL
- Response time 67–121ms (target: <500ms)
- Pydantic models in `backend/app/schemas/analytics.py`
- Query layer in `backend/app/db/queries/analytics_queries.py`
- 60 test cases (55 passed, 5 skipped)

Endpoints:
1. `/trending-skills` — top 20 in-demand skills
2. `/salary-insights` — salary ranges by location/title
3. `/hiring-patterns` — job posting trends over time
4. `/company-insights` — top companies by hiring volume
5. `/job-market-health` — overall market metrics
6. `/skill-demand` — skills with highest growth rate
7. `/location-trends` — geographic job distribution
8. `/industry-breakdown` — jobs by industry/sector
9. `/experience-levels` — jobs by seniority
10. `/job-type-mix` — full-time/contract/remote distribution
11. `/salary-by-skill` — average salary per skill
12. `/comparison` — compare resume to market (AUTH required)

### Phase 7: Analytics Dashboard — COMPLETE
Completed May 9, 2026. Merged to `main`.

**5 KPI cards:** Total Jobs, Average Salary, Growth Rate, Market Health Score,
Active Companies.

**12 interactive charts (Recharts):**
1. Trending Skills — horizontal bar (top 12)
2. Hiring Patterns — area chart with gradient
3. Location Trends — treemap (top 12)
4. Industry Breakdown — donut (top 7 + Other)
5. Job Type Mix — pie chart
6. Job Market Health — metric cards
7. Company Insights — horizontal bar (top 12)
8. Salary by Skill — horizontal bar (top 15)
9. Salary Insights — scatter plot
10. Experience Levels — vertical bar
11. Skill Demand Forecast — line chart
12. Resume Comparison — radar chart

**Design system:**
- Primary: `#6366f1` (indigo-500). No green as accent — green is semantic only
  (positive trends).
- Chart colors: blue `#3b82f6`, purple `#8b5cf6`, cyan `#06b6d4`, pink
  `#ec4899`, teal `#14b8a6`, amber `#f59e0b`
- Color constants centralized in `frontend/src/styles/analytics-colors.ts`
- Responsive: 1 col (mobile <640px), 2 col (tablet 768px), 3 col (desktop
  1024px+)
- Mobile hamburger menu with Escape and click-outside handlers

**Critical bugs fixed during testing (32 tests):**
- Duplicate API requests reduced from 44 → 11 (mount guard + isMounted flag in
  `Analytics.tsx`)
- Color spec mismatches corrected across all chart components
- Mobile menu missing Escape/click-outside handlers (added in `Navbar.tsx`)
- `SalaryBySkillChart` capped at 12 instead of 15 (fixed slice and height)

**Performance:** 0.82s initial load, 1.17s FCP, 11 API requests, no memory
leaks.

**Key files:**
- `frontend/src/pages/Analytics.tsx` — main dashboard, API orchestration
- `frontend/src/api/client.ts` — deduplication logic
- `frontend/src/components/analytics/` — all chart and UI components
- `frontend/src/styles/analytics-colors.ts` — centralized colors

### Phase 7.5: Production Deployment — COMPLETE

**Completed:** May 10, 2026.

What was done:
- FastAPI backend deployed to Railway (Docker, port 8080)
- PostgreSQL and Redis provisioned on Railway
- Alembic migrations run automatically on deploy
- React frontend deployed to Vercel, auto-builds from `main`
- Custom domain `applyluma.com` connected via Namecheap → Vercel DNS
- SSL certificate auto-provisioned by Vercel
- All environment variables set in Railway and Vercel dashboards
- CORS configured to allow `applyluma.com` and Vercel preview URLs
- Auto-deploy from `main` branch working for both services

**Known post-deployment issue (expected):**
- Analytics endpoints return 500. Cause: analytics tables empty, Airflow not yet
  connected to Railway PostgreSQL. Phase 8 resolves this.

---

## Phase 8: Connect Data Pipeline to Production — CURRENT PHASE

**Goal:** Point Airflow at the Railway PostgreSQL `applyluma` database so scraped
job data flows into production, dbt transformations populate the analytics views,
and the analytics dashboard shows real data.

**Tasks:**
1. Configure Airflow to write scraped jobs to Railway PostgreSQL (not local DB).
2. Keep Airflow metadata in `airflow_db`; do not mix with `applyluma`.
3. Run dbt against production data to populate `analytics.*` views.
4. Verify all 12 analytics endpoints return real data (no 500 errors).
5. Confirm analytics dashboard charts populate in production.

**Airflow DAG location:** `airflow/dags/scrape_jobs.py`
**dbt models:** `dbt/models/marts/`

---

## Project Structure

```
backend/         FastAPI app — routes, models, schemas, migrations, services
frontend/        React + TypeScript app (Vercel)
airflow/         Airflow DAGs (job scraping)
dbt/             dbt analytics project (some docs say dbt_project/ — the actual
                 directory is dbt/)
docker/          Local Docker infrastructure
postgres/        Local PostgreSQL setup
tests/           Project-level tests
```

No `deployment/` directory exists. Deployment config lives in this file, the
README, and Railway/Vercel dashboards.

---

## Key Files

Backend:
- `backend/app/main.py` — FastAPI entrypoint and CORS setup
- `backend/app/api/v1/` — versioned API routes
- `backend/app/api/v1/endpoints/` — endpoint modules
- `backend/app/models/` — SQLAlchemy models
- `backend/app/schemas/` — Pydantic schemas (including `analytics.py`)
- `backend/app/core/` — config, auth, dependencies
- `backend/app/db/` — database session and query utilities
- `backend/app/db/queries/analytics_queries.py` — analytics SQL layer

Frontend:
- `frontend/src/pages/Analytics.tsx` — analytics dashboard page
- `frontend/src/pages/` — all page components
- `frontend/src/components/analytics/` — chart and dashboard components
- `frontend/src/components/layout/Navbar.tsx` — nav with mobile hamburger
- `frontend/src/api/client.ts` — Axios client with deduplication
- `frontend/src/services/` — service wrappers
- `frontend/src/types/` — TypeScript types
- `frontend/src/styles/analytics-colors.ts` — chart color constants

Data:
- `airflow/dags/scrape_jobs.py` — job scraper DAG (local; not yet pointed at
  Railway PostgreSQL)
- `dbt/models/marts/` — dbt analytics marts
- `dbt/dbt_project.yml` — dbt project config

---

## Development Workflow

Branches:
- `main` — production; pushing here auto-deploys to Railway and Vercel
- `dev` — integration testing before merging to main

Local startup:
```bash
docker-compose up -d
```

Database migrations:
```bash
alembic upgrade head
```

Migration rules:
- Always run `alembic upgrade head` after model changes.
- Railway auto-runs migrations on deploy via the Dockerfile CMD.
- If production shows a schema mismatch, check Railway deploy logs before
  changing application code.

Deployment:
- Frontend: Vercel auto-deploys from `main`.
- Backend: Railway auto-deploys from `main`.
- Never commit secrets. Keep all credentials in Railway and Vercel dashboards.

---

## Important Credentials and Config

Do not hardcode credentials. Use environment variables.

Railway backend (set in Railway dashboard):
- `PORT=8080`
- `DATABASE_URL` — Railway PostgreSQL `applyluma` database
- `REDIS_URL` — Railway Redis
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

Vercel frontend (set in Vercel dashboard):
- `VITE_API_URL=https://applyluma-production.up.railway.app`

CORS:
- Config lives in `backend/app/main.py` and related core config.
- Allowed origins include `applyluma.com` and Vercel preview URLs (regex).
- Test CORS against production domain and Vercel preview URLs when touching
  auth, headers, API base URLs, or CORS settings.

Secrets policy:
- Never commit `.env` files with real values.
- Never paste secrets into docs, tests, fixtures, or logs.

---

## Working vs Needs Work

Working in production:
- https://applyluma.com (frontend)
- https://applyluma-production.up.railway.app (backend)
- JWT auth flow (register, login, logout)
- Resume upload and management
- OpenAI CV analysis
- Adzuna job search
- Job description management
- Railway PostgreSQL and Redis
- Vercel and Railway auto-deploy from `main`
- Analytics dashboard UI (renders; shows empty/loading until data arrives)

Needs work (Phase 8):
- Airflow connection to Railway PostgreSQL
- Production analytics data ingestion
- dbt production transformation run
- Analytics endpoints returning real data (currently 500 — expected)
- Persistent production upload storage (currently Railway ephemeral; move to S3
  later)

---

## Architecture Decisions

**Separate analytics response format** — consistent shape across all endpoints;
easy to add pagination later.

**Redis caching (1-hour TTL)** — analytics queries scan large tables; 1-hour
staleness is acceptable; reduces PostgreSQL load.

**SQLAlchemy over raw SQL** — type-safe, parameterized (prevents SQL injection),
easier to refactor.

**Two-database separation** — `applyluma` for app data, `airflow_db` for Airflow
metadata. Do not mix them.

**Vercel + Railway** — free frontend CDN, simple always-on backend, $5/mo total,
auto-deploy from GitHub.

**Indigo brand, no green accents** — green reserved for semantic positive trends
only. Chart palette: blue, purple, cyan, pink, teal, amber.

**Recharts** — chosen for React 18 compatibility and the chart types required
(bar, area, scatter, treemap, radar, donut, pie, line).

---

## Constraints and Gotchas

Database:
- Never run analytics directly against `raw_job_postings` (can be 100k+ rows).
- Use `analytics.*` dbt views (pre-aggregated).
- Analytics views refresh daily at 3 AM UTC.

Analytics 500 errors:
- If analytics returns 500, first check whether data exists in the analytics
  views before touching endpoint code. The current 500s are a data gap, not an
  application bug.

Performance targets:
- API response: <500ms
- Chart render: <200ms
- Page load: <2s

Mobile:
- All charts must work at 375px minimum width.
- Hamburger menu required below 768px. Touch targets ≥ 44px.

CORS:
- Test with both the production domain and Vercel preview URLs after any change
  to auth, headers, or API base URL config.

---

## File Ownership

Claude (design and specs):
- API contracts and Pydantic schemas
- SPEC.md files for each endpoint
- Caching and error-handling strategy
- Dashboard UI/UX specifications

Codex (implementation):
- Endpoint code under `backend/app/api/v1/endpoints/analytics/`
- SQLAlchemy queries in `backend/app/db/queries/analytics_queries.py`
- Tests in `tests/test_analytics_endpoints.py`
- React dashboard components under `frontend/src/components/analytics/`
- Bug fixes from testing

You (owner):
- Code review
- Integration testing
- Docker build and deployment
- Performance tuning
- Merging branches
- Production deployment and monitoring

---

## Git Workflow

Branch naming:
```
main                         ← production (auto-deploys)
claude/phase-X-design        ← Claude: specs and models
codex/phase-X-implementation ← Codex: implementations
phase-X-testing              ← testing and bug fixes
```

Standard flow:
1. Claude designs on `claude/phase-X-design`.
2. Codex implements on `codex/phase-X-implementation`.
3. Test and fix bugs on `phase-X-testing`.
4. Merge all to `main`, verify locally with `docker-compose up`, push.

---

## Testing Strategy

Backend unit tests:
```bash
pytest backend/tests/test_analytics_endpoints.py -v
```

Frontend tests:
```bash
cd frontend && npm test
```

Integration tests (after merging):
```bash
docker-compose up
pytest backend/tests/integration/ -v
```

Manual checklist before merging to `main`:
- All 12 charts render without errors
- Mobile menu: hamburger, Escape key, click-outside all work
- Refresh button triggers data reload
- Loading, empty, and error states appear correctly
- Network tab: exactly 11 analytics API requests (not 44)
- Colors match spec (indigo primary, no green accents)
- No console errors
- Works at 375px, 768px, and 1440px
- Build passes: `npm run build`

---

## AI Development Guidelines

- Prefer existing patterns in `backend/app/` and `frontend/src/`.
- Use environment variables for all credentials and deployment config.
- Never hardcode Railway, Vercel, OpenAI, Adzuna, JWT, or database secrets.
- Run `alembic upgrade head` after any SQLAlchemy model change.
- Add an Alembic migration file when models change.
- Keep `airflow_db` and `applyluma` databases separate at all times.
- Use Pydantic schemas for backend validation and response shapes.
- Use the Axios client in `frontend/src/api/client.ts` for all API calls
  (deduplication is built in).
- When analytics returns 500, verify data exists in `analytics.*` views before
  changing endpoint code.
- Keep `main` always deployable. Use `dev` for integration testing first.
- Test CORS changes against production domain and Vercel preview URLs.

---

## Quick Orientation for New AI Sessions

1. Run `git status` to confirm branch. Remember `main` is production and
   auto-deploys on push.
2. Check whether the task touches production config, migrations, auth, or CORS —
   those require extra care.
3. For backend work: `backend/app/main.py`, `backend/app/api/v1/`,
   `backend/app/models/`, `backend/app/schemas/`.
4. For frontend work: `frontend/src/pages/`, `frontend/src/api/`,
   `frontend/src/components/`.
5. For analytics data work: `airflow/dags/`, `dbt/models/marts/`,
   `backend/app/db/queries/analytics_queries.py`.
6. If analytics returns 500, check whether `analytics.*` views have data before
   touching endpoint code. The current 500s are a data gap (Phase 8 fix).
7. The analytics dashboard UI is complete. Do not rework chart components unless
   there is a specific bug to fix.

**Strategic priority for Phase 8:** connect Airflow to Railway PostgreSQL,
populate `analytics.*` views, verify all 12 endpoints return real data.
