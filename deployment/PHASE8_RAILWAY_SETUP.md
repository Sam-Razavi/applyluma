# Phase 8: Airflow Railway PostgreSQL Connection

## Overview

This guide explains how to run local Airflow DAGs against the Railway production
application database instead of the local application database.

The goal is to populate production analytics data so the production backend and
dashboard can read the same data that Airflow scrapes and dbt transforms.

## Security

Do not commit Railway credentials.

The real Railway PostgreSQL credentials live only in `.env.railway`, which is
ignored by git. This documentation intentionally uses placeholders instead of
the production password.

Required `.env.railway` shape:

```bash
AIRFLOW_POSTGRES_CONN_HOST=<railway-host>
AIRFLOW_POSTGRES_CONN_PORT=<railway-port>
AIRFLOW_POSTGRES_CONN_LOGIN=<railway-user>
AIRFLOW_POSTGRES_CONN_PASSWORD=<railway-password>
AIRFLOW_POSTGRES_CONN_SCHEMA=<railway-database>

DBT_DB_HOST=<railway-host>
DBT_DB_PORT=<railway-port>
POSTGRES_USER=<railway-user>
POSTGRES_PASSWORD=<railway-password>
POSTGRES_DB=<railway-database>
```

## Environment Variable Separation

ApplyLuma uses two separate PostgreSQL databases:

1. **Airflow Metadata** (always local)
   - Database: `airflow_db` on the local Docker postgres container.
   - Stores: DAG runs, task instances, scheduler state, and Airflow users.
   - Credentials: `AIRFLOW_METADATA_USER` / `AIRFLOW_METADATA_PASSWORD`.
   - Connection: `postgres:5432/airflow_db`.

2. **Application Data** (Railway in production, local in development)
   - Database: `railway` on Railway PostgreSQL, or `applyluma` locally.
   - Stores: jobs, resumes, raw scrape data, and analytics tables.
   - Credentials: `POSTGRES_USER` / `POSTGRES_PASSWORD`.
   - Connection: Railway or local depending on which startup command is used.

Why separate them:
- Airflow metadata must stay local and should not be written to Railway.
- Application analytics data must go to Railway so the production backend can
  read it.
- Reusing `POSTGRES_USER` and `POSTGRES_PASSWORD` for both databases causes
  authentication conflicts when `.env.railway` is loaded.

## Files Modified

- `.env.railway` - Railway credentials, created locally and not committed.
- `.gitignore` - Ignores `.env.railway`.
- `docker-compose.yml` - Adds Railway env var support with local defaults.
- `docker/airflow-init-connection.sh` - Recreates `postgres_default` from the
  current environment on Airflow init.
- `airflow/dags/transform_jobs.py` - Runs dbt with `--target prod`.
- `airflow/dags/job_scraping_dag.py.disabled` - Disables duplicate DAG.
- `docker/start-airflow-railway.sh` - Starts Docker Compose with Railway env.
- `docker/verify-railway-connection.sh` - Verifies Railway connectivity.

## Local Development

Default local development still uses local PostgreSQL:

```bash
docker-compose up -d
```

With no `.env.railway` passed, DAGs default to `postgres:5432/applyluma`.
Airflow metadata stays local in `airflow_db`.

## Production Scraping

Start Airflow with Railway database environment variables:

```bash
./docker/start-airflow-railway.sh
```

Verify the Railway connection:

```bash
./docker/verify-railway-connection.sh
```

Trigger job scraping:

```bash
docker-compose exec airflow-webserver airflow dags trigger scrape_jobs
```

Trigger dbt transformations:

```bash
docker-compose exec airflow-webserver airflow dags trigger transform_jobs
```

## Expected DAGs

Active DAGs:
- `scrape_jobs`
- `transform_jobs`

Disabled duplicate:
- `job_scraping_dag.py.disabled`

## What The DAGs Do

`scrape_jobs`:
- Scrapes configured job boards.
- Writes raw postings to Railway PostgreSQL.
- Extracts skills into `extracted_skills`.
- Marks duplicates.

`transform_jobs`:
- Runs dbt with `--target prod`.
- Creates or updates the `analytics` schema.
- Builds staging and marts models from production data.
- Runs dbt tests against the production target.

## Verification

Check analytics tables:

```bash
docker-compose exec airflow-webserver airflow dags test transform_jobs
```

Or inspect with `psql` using credentials from `.env.railway`:

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$DBT_DB_HOST" \
  -p "$DBT_DB_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics';"
```

Test the production analytics endpoint:

```bash
curl https://applyluma-production.up.railway.app/api/v1/analytics/job-market-health
```

Expected result after successful scrape and transform:
- HTTP 200
- Real analytics data
- No empty-table 500 errors

## Troubleshooting

Connection refused:
- Check the Railway PostgreSQL service is running.
- Confirm the host and port in `.env.railway`.

Authentication failed:
- Re-copy credentials from the Railway dashboard into `.env.railway`.
- Do not update committed files with credentials.

Analytics schema missing:
- Run the `transform_jobs` DAG.
- Confirm dbt logs show `target: prod`.

Empty analytics tables:
- Check `raw_job_postings` row count.
- If raw data is empty, run `scrape_jobs`.
- Then run `transform_jobs`.

DAG fails with missing relation:
- Check dbt model dependencies.
- Inspect the `transform_jobs` DAG logs.
- Re-run `transform_jobs` after raw data exists.

## Rollback To Local

Stop Railway-connected services:

```bash
docker-compose down
```

Start normal local services:

```bash
docker-compose up -d
```

Without `--env-file .env.railway`, DAGs return to local PostgreSQL defaults.
