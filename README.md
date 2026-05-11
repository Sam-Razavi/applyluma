# ApplyLuma

AI-powered job search and resume optimization platform with production analytics.

## Status

- Production: https://applyluma.com
- Backend API: https://applyluma-production.up.railway.app
- API docs: https://applyluma-production.up.railway.app/docs
- Current status: Phase 8 complete
- Next phase: Phase 9 planning

ApplyLuma is live in production. All major features are working, including the
analytics dashboard. The Phase 8 production data pipeline work is complete:
analytics endpoints that previously returned 500 errors now return 200 OK with
data from Railway PostgreSQL.

## Overview

ApplyLuma helps job seekers search jobs, manage resumes, analyze job
descriptions, and compare their profile against market analytics.

Core capabilities:
- JWT authentication
- Resume upload and AI resume analysis
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
- OpenAI API for resume analysis
- Adzuna API for job search

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
- User authentication
- Resume upload and parsing
- AI resume analysis
- Job search
- Job description management
- Analytics API
- Analytics dashboard
- Production deployment
- Production data pipeline

Ready for planning:
- Phase 9 AI features
- Application tracking improvements
- Mobile polish
- Monitoring and alerting

## Project Structure

```text
applyluma/
|-- backend/      FastAPI application, models, schemas, migrations, services
|-- frontend/     React and TypeScript application
|-- airflow/      Airflow DAGs for scraping and transforms
|-- dbt/          dbt analytics project
|-- docker/       Local Docker support
|-- deployment/   Deployment and production operation docs
`-- graphify-out/ Knowledge graph for codebase navigation
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
