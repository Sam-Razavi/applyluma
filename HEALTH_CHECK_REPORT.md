# ApplyLuma Health Check Report

Date: 2026-05-08
Project: `C:\Project\Job-App\applyluma`

## Summary

Overall status: **Not deployment-ready**

| Phase | Component | Status | Issues Found |
|-------|-----------|--------|--------------|
| 1 | Backend API | Partial | `/health` passes. Auth works on implemented `/api/v1/auth/*` routes. Checklist routes `/api/auth/*` and `/docs` do not match the app; Swagger is at `/api/v1/docs`. Registration with `test123` fails because password minimum is 8 chars. |
| 1 | Database | Pass | Required tables exist: `users`, `cvs`, `job_descriptions`, `raw_job_postings`, `job_market_metrics`, plus `alembic_version`. |
| 2 | Resume Upload | Pass | Implemented route is `/api/v1/cvs/upload`, not `/api/resumes/upload`. Valid DOCX upload succeeded and row was created in `cvs`. |
| 2 | Claude AI | Partial | `CLAUDE_API_KEY` and `OPENAI_API_KEY` are set, but current backend code uses OpenAI, not Claude. Implemented AI route `/api/v1/ai/tailor-cv` returned structured analysis successfully. Checklist route `/api/resumes/{id}/analyze` does not exist. |
| 3 | Job Search | Fail | `/api/jobs/search?query=python&location=remote` returns `404`; no job search endpoint exists. Scraper imports pass. Remotive/Muse/Adzuna environment variables are empty in Airflow. |
| 4 | Celery | Pass | Worker is running, connected to Redis, and lists `app.tasks.sample.sample_task`. |
| 4 | Redis | Pass | `redis-cli ping` returned `PONG`. |
| 5 | Airflow | Fail | Airflow webserver is healthy and UI responds, but `airflow-scheduler` container is `unhealthy` because Docker healthcheck times out after 10s. |
| 5 | dbt | Partial | `dbt parse` succeeds and `dbt run --models staging --target dev` created `analytics.stg_job_postings`. `dbt debug` confirms database connection but exits failed because `git --help` is blocked for the Airflow user. dbt deprecation warnings are present. |
| 5 | DAGs | Fail | DAGs load with no import errors. `scrape_jobs` and `transform_jobs` are unpaused and triggerable, but pipeline runs do not complete because Airflow connection `postgres_default` is missing. `raw_job_postings` and `job_market_metrics` remain empty. |
| - | Frontend | Fail | App serves on `http://localhost:5173`, not `3000`. CORS preflight from `5173` passes. `npm run type-check` and `npm run build` fail because `recharts` is missing from installed frontend dependencies. |

## Critical Issues

- Airflow connection `postgres_default` is missing. This blocks `scrape_jobs`, `transform_jobs`, and the end-to-end data pipeline.
- Frontend production build fails because `recharts` is not installed in the frontend container volume.
- Job search API is missing. The requested `/api/jobs/search` endpoint returns `404`.
- Airflow scheduler container is marked `unhealthy` due healthcheck timeouts.
- API contract mismatch with checklist/deployment expectations: current routes use `/api/v1/...`, CV routes are `/cvs`, and AI analysis is `/ai/tailor-cv`.

## Warnings

- `raw_job_postings` has 0 rows and `job_market_metrics` has 0 rows, so analytics are structurally present but not populated.
- Scraper credential environment variables are empty in Airflow: `REMOTIVE_API_KEY`, `MUSE_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_API_KEY`.
- dbt reports deprecated usage: `--models` should be replaced with `--select`, and generic test arguments should move under `arguments`.
- `dbt debug` fails a dependency check because `git` is not available or not permitted for the Airflow user, although the database connection itself passes.
- `docker-compose.yml` uses obsolete `version: '3.9'` syntax.
- Celery worker is running as root, which Celery warns is not recommended.
- Backend tests are effectively absent: `pytest` collected 0 tests.
- Browser console inspection could not be performed because the in-app browser execution tool was not exposed in this session; HTTP/CORS checks were used instead.

## Recommendations

1. Create the Airflow Postgres connection:

   ```bash
   airflow connections add postgres_default \
     --conn-type postgres \
     --conn-host postgres \
     --conn-login applyluma \
     --conn-password applyluma \
     --conn-schema applyluma \
     --conn-port 5432
   ```

   Persist this in `airflow-init` or environment-backed Airflow connection config so it survives container rebuilds.

2. Fix the frontend dependency volume:

   ```bash
   docker-compose exec frontend npm install
   docker-compose exec frontend npm ls recharts
   docker-compose exec frontend npm run build
   ```

   If the named Docker volume has stale dependencies, recreate `frontend_node_modules`.

3. Decide and document the public API contract before deployment:

   - Keep `/api/v1/*` and update the checklist/frontend docs, or
   - Add compatibility aliases for `/api/auth/*`, `/api/resumes/*`, `/api/jobs/search`, and `/docs`.

4. Implement or remove the job search deployment requirement:

   - Add `/api/v1/jobs/search` backed by `raw_job_postings` or external APIs, then optionally alias `/api/jobs/search`.
   - Add tests for successful search, empty results, and invalid query parameters.

5. Repair Airflow scheduler health:

   - Increase healthcheck timeout above 10s or optimize Airflow startup/check latency.
   - Fix `scheduler.max_tis_per_query` so it is not greater than `core.parallelism`.

6. Re-run the pipeline after `postgres_default` is fixed:

   - Trigger `scrape_jobs`.
   - Confirm `raw_job_postings` receives rows.
   - Trigger `transform_jobs`.
   - Confirm `job_market_metrics` and analytics marts are populated.

7. Add automated tests before deployment:

   - Backend API tests for auth, CV upload, job descriptions, AI analysis error handling, analytics.
   - Frontend build/type-check in CI.
   - Airflow DAG import tests and dbt parse/run tests.

## Commands Run

- `docker-compose ps`
- `docker-compose exec postgres psql ...`
- `curl http://localhost:8000/health`
- Auth register/login calls against `/api/v1/auth/*`
- CV upload against `/api/v1/cvs/upload`
- AI analysis against `/api/v1/ai/tailor-cv`
- Redis ping
- Celery logs and Celery app import
- Airflow DAG list/import errors/list-runs/task states
- dbt `parse`, `debug`, and staging `run`
- Frontend `npm run type-check`, `npm run build`, `npm ls recharts`
- Backend `pytest`

## Test Artifacts Created

- `backend/test_resume.docx`
- `test_resume.docx`
- `healthcheck_resume_docx/`

dbt also updated files under `dbt/target/` during parse/run.
