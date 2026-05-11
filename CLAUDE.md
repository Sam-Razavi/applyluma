# ApplyLuma AI Context

This file is the project source of truth for AI assistants working in the
ApplyLuma repository.

## Project Overview

- ApplyLuma is an AI-powered job search and resume optimization platform.
- Production frontend: https://applyluma.com
- Production backend: https://applyluma-production.up.railway.app
- Status: Phase 9 complete. The production application is 100% functional.
- All major features are working, including authentication, resume analysis, job
  search, job description management, the analytics dashboard, and AI CV Tailor.

## Current Phase

- Phase 8: &#9989; COMPLETE
- Phase 9: &#9989; COMPLETE
- Phase 10: Ready to start
- Phase 9 delivered the AI CV Tailor feature end-to-end:
  - Celery worker tailors CV sections against a job description using OpenAI.
  - Users review section diffs, accept/reject changes, and save a tailored PDF.
  - Authenticated download endpoints serve PDFs for both uploaded and tailored CVs.
  - Tailored CVs appear in the My CVs tab with working view and download buttons.
  - Daily tailoring limits enforced per user role (user: 1, premium: 10, admin: unlimited).
  - Alembic migrations for tailor_jobs table and user role column included.

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

## Recent Critical Fixes

- Fixed Railway `$PORT` expansion by changing Docker `CMD` from exec form to
  shell form.
- Removed the conflicting `Procfile`.
- Added/configured `backend/railway.json` to force the Dockerfile builder.
- Populated analytics data in Railway PostgreSQL.
- Fixed analytics dashboard production failures.
- All analytics endpoints now return 200 OK.

## Known Issues

- None. All features are working in production.

## Next Steps

- Start Phase 10 planning.
- Candidate Phase 10 areas: application tracking, mobile polish, monitoring and
  alerting, or premium subscription flow.
- Continue using the `dev` -> `main` workflow.
- Use feature branches for AI collaboration.

## AI Development Guidelines

When working on this project:
- Always work in `dev` or create a feature branch from `dev`.
- Never push directly to `main` unless it is an emergency hotfix.
- Test in `dev` before merging to `main`.
- Use Railway logs to verify backend deployments.
- Check both Railway and Vercel for production status.
- Remember that analytics endpoints require a populated database.
- Airflow runs daily at 2 AM UTC for scraping.
- Airflow/dbt transforms run daily at 3 AM UTC.
- Keep credentials in environment variables only.
- Prefer existing backend, frontend, Airflow, and dbt patterns before adding new
  abstractions.

## Repository Knowledge Graph

This project has a knowledge graph at `graphify-out/` with god nodes, community
structure, and cross-file relationships.

Rules:
- Always read `graphify-out/GRAPH_REPORT.md` before reading source files,
  running searches, or answering codebase questions.
- If `graphify-out/wiki/index.md` exists, navigate it before reading raw files.
- For cross-module relationship questions, prefer `graphify query`,
  `graphify path`, or `graphify explain` over text search.
- After modifying code, run `graphify update .` to keep the graph current.
