# ApplyLuma

AI-powered job search and resume optimization platform with production analytics.

## Status

- Production: https://applyluma.com
- Backend API: https://applyluma-production.up.railway.app
- API docs: https://applyluma-production.up.railway.app/docs
- Current status: Phase 10A complete
- Next phase: Phase 10B planning

ApplyLuma is live in production. All major features are working, including the
analytics dashboard, the AI CV Tailor, and the new Swedish job discovery feed
with AI-powered match scoring. Phase 10A delivered end-to-end job discovery:
Airflow scrapes Swedish job boards daily, an AI scoring engine ranks jobs against
each user's CV, and users can browse, filter, save, and star jobs from a
responsive discovery feed.

## Overview

ApplyLuma helps job seekers search jobs, manage resumes, tailor CVs with AI,
discover AI-matched Swedish jobs, and compare their profile against market analytics.

Core capabilities:
- JWT authentication
- Resume upload and AI resume analysis
- AI CV Tailor: async section-by-section CV rewriting against a job description
- Authenticated PDF download for all CVs (uploaded and tailored)
- Swedish job discovery with AI match scoring against your CV
- Saved jobs collection with named lists, starring, and notes
- Job search through Adzuna
- Job description management
- Market analytics dashboard
- Daily Airflow and dbt data pipeline

## Tech Stack

Backend:
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy and Alembic
- Docker on Railway

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- Vercel

Data:
- Apache Airflow for orchestration
- dbt for transformations
- Railway PostgreSQL for production analytics data

AI and external APIs:
- OpenAI API for resume analysis, CV tailoring, and job match scoring
- JobTech Dev API (Platsbanken) for Swedish job data — free, no key required
- Adzuna API for job search
- Celery + Redis for async tailoring jobs
- ReportLab for PDF generation

## Deployment

Production services:
- Frontend: Vercel, https://applyluma.com
- Backend: Railway, https://applyluma-production.up.railway.app
- Database: Railway PostgreSQL
- Cache: Railway Redis
- Domain: Namecheap DNS pointed to Vercel

Deployment flow:
- `main` is production and auto-deploys to Railway and Vercel.
- `dev` is for development and integration testing.
- Pushes to `main` usually reach production in about 3 minutes.

Important deployment files:
- `backend/Dockerfile`: Railway backend deployment
- `backend/railway.json`: Railway Dockerfile builder configuration
- `backend/app/main.py`: FastAPI app and CORS setup
- `frontend/vercel.json`: Vercel routing and rewrites
- `airflow/dags/`: Scraping and transform DAGs

Deployment guides:
- [Railway Backend Setup](deployment/RAILWAY_SETUP.md)
- [Vercel Frontend Setup](deployment/VERCEL_SETUP.md)
- [DNS Configuration](deployment/DNS_SETUP.md)
- [Airflow Remote Connection](deployment/AIRFLOW_REMOTE.md)
- [Testing Checklist](deployment/TESTING_CHECKLIST.md)

## Git Workflow

Branch structure:
- `main`: production branch, auto-deploys on push
- `dev`: development and integration branch

Standard workflow:
```bash
git checkout dev
git checkout -b feature/my-feature

# make changes and test

git checkout dev
git merge feature/my-feature
git push origin dev

# when production-ready
git checkout main
git merge dev
git push origin main
git checkout dev
```

Rules:
- Work in `dev` or a feature branch from `dev`.
- Test before merging to `main`.
- Never push breaking changes to `main`.
- Use feature branches for parallel AI-assisted work.

## Local Development

Prerequisites:
- Docker Desktop
- Node.js 18+
- Python 3.11+
- Git

Start local services:
```bash
docker-compose up
```

Local service URLs:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Airflow: http://localhost:8080

Manual backend setup:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Manual frontend setup:
```bash
cd frontend
npm install
npm run dev
```

## Data Pipeline

Phase 8 is complete. Airflow writes production analytics data to Railway
PostgreSQL, and dbt transforms populate the analytics models used by the API and
dashboard.

Schedule:
- Job scraping: daily at 2 AM UTC
- dbt transforms: daily at 3 AM UTC

Useful commands:
```bash
./docker/start-airflow-railway.sh
./docker/verify-railway-connection.sh
docker-compose exec airflow-webserver airflow dags trigger scrape_jobs
docker-compose exec airflow-webserver airflow dags trigger transform_jobs
```

Production analytics health check:
```bash
curl https://applyluma-production.up.railway.app/api/v1/analytics/job-market-health
```

## Features

Completed:
- User authentication (JWT, refresh tokens)
- Resume upload and parsing
- AI resume analysis
- Job search through Adzuna
- Job description management
- Analytics API and dashboard
- Production deployment on Railway + Vercel
- Production data pipeline (Airflow + dbt, daily at 2–3 AM UTC)
- AI CV Tailor (Phase 9): async rewriting, section review, PDF save and download
- Authenticated CV download for all CVs (uploaded and tailored)
- Swedish job discovery (Phase 10A):
  - Paginated, filterable job feed from Platsbanken, Jobbsafari, and Indeed.se
  - AI match scoring against user's CV (skills, experience, salary, education, location)
  - Keyword extraction with type classification and confidence scores
  - Saved jobs with named collections, starring, notes, and detail modal
  - Mobile-responsive filters (collapsible sidebar)
  - Redis caching: 24h match scores, 7d keywords, 1h job feed

Ready for planning:
- Phase 10B: one-click CV tailoring from discovered jobs, email alerts for
  high-match jobs, application tracking integration with the Discover feed

## Project Structure

```text
applyluma/
|-- backend/      FastAPI application, models, schemas, migrations, services, tests
|-- frontend/     React + TypeScript application and component tests
|-- airflow/      Airflow DAGs for scraping and transforms
|-- dbt/          dbt analytics project
|-- docker/       Local Docker support
|-- deployment/   Deployment and production operation guides
|-- docs/         Feature and deployment documentation
`-- graphify-out/ Knowledge graph for codebase navigation (gitignored)
```

## Environment Variables

Backend variables are configured in Railway. Frontend variables are configured in
Vercel.

Key variables:
- `PORT=8080`
- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `VITE_API_URL`

Never commit real secrets or production `.env` files.

## License

MIT
