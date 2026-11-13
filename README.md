# ApplyLuma

[![CI](https://github.com/sam-razavi/applyluma/actions/workflows/ci.yml/badge.svg)](https://github.com/sam-razavi/applyluma/actions/workflows/ci.yml)
[![Data Pipeline Tests](https://github.com/sam-razavi/applyluma/actions/workflows/data-pipeline-tests.yml/badge.svg)](https://github.com/sam-razavi/applyluma/actions/workflows/data-pipeline-tests.yml)
[![API](https://img.shields.io/badge/api-railway-brightgreen?logo=railway&logoColor=white)](https://railway.app)
[![Frontend](https://img.shields.io/badge/frontend-vercel-black?logo=vercel&logoColor=white)](https://applyluma.com)
[![Last Commit](https://img.shields.io/github/last-commit/Sam-Razavi/applyluma)](https://github.com/Sam-Razavi/applyluma/commits/main)
[![Python](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-22-green?logo=node.js&logoColor=white)](https://nodejs.org/)

ApplyLuma is a production-deployed AI job-search platform that helps candidates discover matched jobs, tailor CVs, generate cover letters, track applications, and analyze job-market trends from one workspace.

- Production: https://applyluma.com
- Backend API: https://api.applyluma.com
- API docs: https://api.applyluma.com/api/v1/docs
- Browser extension: `applyluma-extension/`

## Product Preview

### Job Discovery and AI CV Tailoring

| Job discovery with CV match scores | AI CV tailoring workflow |
| --- | --- |
| ![Discover jobs with CV match scores and filters](docs/screenshots/discover-jobs.png) | ![AI CV Tailor source selection and tailoring intensity](docs/screenshots/ai-tailor.png) |

### Market Intelligence Dashboard

![ApplyLuma market intelligence dashboard](docs/screenshots/dashboard-desktop.png)

### Analytics Details

| Market KPIs and demand signals | Hiring trend and market health |
| --- | --- |
| ![Market KPIs, trending skills, salary insights, and top companies](docs/screenshots/analytics-kpis-and-skills.png) | ![Hiring patterns chart and market health cards](docs/screenshots/analytics-hiring-and-health.png) |

### Breakdowns and Responsive Layouts

| Market breakdowns | Tablet | Mobile |
| --- | --- | --- |
| ![Location, industry, experience, job type, and salary breakdowns](docs/screenshots/analytics-breakdowns.png) | ![Analytics dashboard tablet layout](docs/screenshots/dashboard-tablet.png) | ![Analytics dashboard mobile layout](docs/screenshots/dashboard-mobile.png) |

## Why This Project Matters

ApplyLuma is built like a real SaaS product rather than a demo app. It combines:

- Full-stack product delivery: React, TypeScript, FastAPI, PostgreSQL, Redis, Celery, Docker, Railway, and Vercel.
- AI workflows: section-by-section CV tailoring, cover letter generation, and job URL extraction.
- Data engineering: scheduled job ingestion, SQL-built analytics marts, analytics APIs, and a production dashboard.
- Security and operations: httpOnly cookie auth, CSRF protection, token denylist, rate limits, SSRF protection, admin audit logging, CI, and deployment docs.
- Recruiter-visible product thinking: responsive UI, onboarding flows, job tracking, billing plans, alert preferences, and browser extension support.

## Core Features

### Candidate Workspace

- Secure sign-up, login, password reset, email verification, and session handling.
- CV upload (PDF, DOCX, and Markdown), parsing, completeness score, version history, and authenticated PDF downloads.
- AI CV Tailor with asynchronous processing, section review, save, and export.
  Tailored output uses OpenAI Structured Outputs and renders through a choice
  of PDF templates (Nordic, Classic, Modern, Executive, Atlas, and Compact)
  via a Jinja2/WeasyPrint pipeline, with
  anti-fabrication checks (self-audit pass, numeric-claim guard) validating
  every claim against the source CV.
- Cover Letter Generator with formal, friendly, and concise tones, rendered in
  the matching template family with the candidate's letterhead.
- Job description manager with URL scraping for publicly accessible job posts.
- Application tracker with status history, contact notes, timeline, and analytics.
- Email/password and Google OAuth sign-in, in-app notification center, and Stripe billing (checkout, customer portal, webhooks) for the premium plan.

### Job Discovery

- Swedish job discovery from Platsbanken, plus remote roles from RemoteOK, Remotive and The Muse.
- International job search through Adzuna.
- Match scoring against the user's CV with matched and missing skill breakdowns. The score is a
  transparent, rule-based weighted formula (skills 40%, experience 30%, salary 15%, education 10%,
  location 5%); it makes no model call.
- AI-assisted fit assessment next to the score (admins only for now): a language model lists the
  ad's requirements and what the CV shows for each, every claim is checked against a quote from
  the CV, and fixed rules turn the result into High Priority, Consider or Low Priority with a list
  of missing information. See [Thesis](#thesis).
- Saved jobs with collections, starring, notes, and detail views.
- One-click actions from discovered jobs: tailor CV, save job, and add to applications.
- Job alert emails for high-match roles with configurable threshold and frequency.

### Analytics and Admin

- Market intelligence dashboard for job volume, salary bands, remote share, growth, top companies, skills, location, seniority, and job-type mix.
- Resume-vs-market comparison for authenticated users with uploaded CVs.
- Admin panel covering user management (activity timeline, delete/password-reset/verify, per-user AI cost and tailor-limit overrides), AI job monitoring with cost/budget tracking, billing overview, contact/feedback inbox, notification center, raw job postings, database table stats, audit logs, and pipeline health.
- Nightly scraping, keyword and analytics pipeline running as Celery tasks on Railway, with PostgreSQL and Redis caching.
- Three-layer monitoring (external uptime pinger, internal health watchdog, Sentry) — see [docs/MONITORING.md](docs/MONITORING.md).

### Browser Extension

- Manifest V3 Chrome/Firefox extension in `applyluma-extension/`.
- One-click save from LinkedIn, Indeed, Glassdoor, and Arbetsformedlingen job pages.
- Badge state for saved/applied URLs and `Alt+Shift+S` quick-save.
- Bearer-token extension auth flow through `/extension-auth`.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Framer Motion, Zustand, Recharts |
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery |
| CV/Cover Letter Rendering | Jinja2 + WeasyPrint (templated PDF generation), legacy ReportLab fallback |
| AI | OpenAI API for CV tailoring, cover letters, and job-ad extraction |
| Data | Celery beat + worker on Railway (nightly job pipeline), Railway PostgreSQL |
| Extension | Manifest V3, content scripts, Chrome/Firefox storage APIs |
| Infrastructure | Railway, Vercel, Docker, Namecheap DNS |
| Payments and Email | Stripe, Resend |
| Quality | Pytest, Vitest, GitHub Actions, ruff, type checks |

## Architecture

```text
applyluma/
|-- backend/               FastAPI API, SQLAlchemy models, schemas, services, tasks, tests
|-- frontend/              React + TypeScript app, pages, components, stores, tests
|-- applyluma-extension/   MV3 browser extension for saving jobs from job boards
|-- dbt/                   dbt models, kept for reference (production builds its marts with SQL)
|-- deployment/            Railway, Vercel, DNS, and test checklists
`-- docs/                  Product and technical documentation
```

## Production Deployment

- Frontend: Vercel, https://applyluma.com
- Backend: Railway, https://api.applyluma.com
- Database: Railway PostgreSQL
- Cache and queue broker: Railway Redis
- Data pipeline: Celery tasks on Railway (`app/tasks/job_pipeline.py`)
- Domain: Namecheap DNS pointing to Vercel

`main` is the production branch and auto-deploys to Railway and Vercel. Railway runs `alembic upgrade head` before starting the backend container.

Deployment guides:

- [Railway Backend Setup](deployment/RAILWAY_SETUP.md)
- [Vercel Frontend Setup](deployment/VERCEL_SETUP.md)
- [DNS Configuration](deployment/DNS_SETUP.md)
- [Testing Checklist](deployment/TESTING_CHECKLIST.md)

## Local Development

Prerequisites:

- Docker Desktop
- Node.js 22+
- Python 3.11+
- Git

Start the full local stack:

```bash
docker-compose up
```

Local URLs:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Manual backend setup:

```bash
cd backend
pip install uv
uv pip install -e ".[dev]" --system
alembic upgrade head
uvicorn app.main:app --reload
```

Manual frontend setup:

```bash
cd frontend
npm install
npm run dev
```

## Testing

ApplyLuma ships with **1,358 automated tests** across the stack, all run in CI on every push and pull request to `main` and `dev`.

| Suite | Tests | Coverage |
| --- | --- | --- |
| Backend — Pytest (async, ASGI transport) | 960 across 72 files, incl. real-Postgres tests in CI | API endpoints, CRUD, services (CV parsing, AI tailoring, cover letters, match scoring, fit assessment, billing), Celery tasks (incl. the health watchdog), admin controls, auth and security |
| Frontend — Vitest + React Testing Library | 391 across 63 files | Pages, Zustand stores, components, and formatters |
| dbt | 7 SQL assertions + `dbt parse` | Data-quality assertions and project validation |

```bash
# Backend — lint, type-check, test
cd backend && ruff check app/ && mypy app/ && python -m pytest

# Frontend — lint, type-check, test, build
cd frontend && npm run lint && npm run type-check && npm test && npm run build

# dbt project validation
cd dbt && dbt deps --profiles-dir . && dbt parse --profiles-dir .
```

## Data Pipeline

The nightly pipeline runs as Celery tasks on the existing Railway beat and
worker services (it moved off Astro Cloud Airflow in November 2026). The
scrapers live in `backend/app/services/job_scrapers/`, the steps in
`backend/app/services/job_pipeline.py`, and the task in
`backend/app/tasks/job_pipeline.py`. Admins can trigger a run from
`/admin/pipeline` ("Run pipeline now").

Schedule:

- 01:00 UTC: job retention (archive / slim / purge old postings)
- 02:00 UTC: job pipeline (scrape Remotive, The Muse, RemoteOK and Platsbanken;
  dedupe; skills; keywords; daily metrics; salary analytics; queue match
  scoring for users with a CV)
- 04:30 UTC: high-match job alerts

Production health check:

```bash
curl https://api.applyluma.com/api/v1/analytics/job-market-health
```

## Environment Variables

Backend variables are configured in Railway. Frontend variables are configured in Vercel.

Key backend variables:

- `PORT=8080`
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `OPENAI_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_API_KEY` (or `ADZUNA_APP_KEY`; either name is read). Used by the web
  Job Search tab; Adzuna has no Sweden endpoint, so the pipeline does not use it.
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PREMIUM_PRICE_ID`
- `RESEND_API_KEY`
- `SENTRY_DSN`
- `ENVIRONMENT=production`

Key frontend variables:

- `VITE_API_URL`
- `VITE_POSTHOG_KEY`
- `VITE_POSTHOG_HOST`
- `VITE_SENTRY_DSN`

Never commit real secrets or production `.env` files.

## Thesis

ApplyLuma is the case study of a bachelor thesis at Stockholm University (DSV), "Designing and
Evaluating an AI-Assisted Decision Support System". The thesis adds an AI-assisted job-fit
assessment and compares it with the rule-based match score on the same controlled cases.

| | Rule-based match score | AI-assisted fit assessment |
| --- | --- | --- |
| Reads | Skills from a fixed vocabulary found in the ad and the CV | The whole ad and the whole CV |
| Decides by | A weighted formula | Fixed rules over a per-requirement judgement from a language model |
| Tells mandatory from preferred | No | Yes |
| Explains with | One generated line | A quote from the CV per requirement, checked against the CV |
| Says when information is missing | No | Yes |
| Shown to | Every user | Admins (a setting) |

- What existed before the thesis: [`docs/thesis/BASELINE.md`](docs/thesis/BASELINE.md), git tag
  `pre-thesis-baseline`.
- Design, decision rules, evaluation design and the change log: [`thesis/`](thesis/).
- The prototype frozen for evaluation: git tag `thesis-prototype-v1`.
- Everything added for the thesis: `git log --oneline pre-thesis-baseline..HEAD`, pull requests
  titled `[thesis]`.

## Current Limitations

- The Discover feed depends on scheduled ingestion, so new jobs can take up to 24 hours to appear.
- AI features require a configured OpenAI API key.
- Match scoring requires at least one uploaded CV.
- Free-tier users have daily limits for CV tailoring and cover-letter generation.
- Job URL scraping works best on public pages without login walls or heavy anti-bot protection.
- Transactional email requires a configured Resend API key and verified sending domain.
- Redis is required for async jobs, match-score caching, job-feed caching, and token denylisting.
- ApplyLuma is a responsive web application; there is no native mobile app.

## License

MIT
