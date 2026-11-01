# Retired: Airflow is no longer used

In November 2026 the nightly job pipeline moved off Astro Cloud Airflow to
Celery on the existing Railway services. Nothing schedules these DAGs any
more, and production does not run Airflow or dbt.

Where the work happens now:

- Task: `backend/app/tasks/job_pipeline.py` (`run_job_pipeline`, beat 02:00 UTC)
- Steps: `backend/app/services/job_pipeline.py`
- Scrapers: `backend/app/services/job_scrapers/` (ported from `plugins/job_scrapers/`)

This folder is kept for reference only. Do not change the scrapers here:
edit the copies under `backend/`. It will be deleted once the Railway
pipeline has run cleanly for a while.
