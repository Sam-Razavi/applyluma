# Phase 8 Execution Report - Railway Database Population

**Execution Date:** 2026-05-10
**Executed By:** Codex
**Branch:** dev
**Status:** API DATA POPULATED, DASHBOARD ROUTE CAVEAT

## Summary

Airflow was started locally with its `postgres_default` connection pointed at
Railway PostgreSQL. The scraping and transform DAGs both completed
successfully, and the production analytics API now returns HTTP 200 for all
public analytics endpoints.

This run fixed the production analytics API failure mode caused by empty
Railway analytics tables. A small dbt model fix was also applied during
execution so dbt uses scraper-provided `extracted_skills` data.

## Scraping Results

- **DAG:** `scrape_jobs`
- **Run ID:** `manual__2026-05-10T19:17:54+00:00`
- **Execution Time:** 33 seconds
- **Status:** Success
- **Jobs Scraped:** 120 raw rows
- **Sources:** 2
  - `remotive`: 20 rows
  - `the_muse`: 100 rows
- **Raw Table:** `raw_job_postings`

## Transformation Results

- **DAG:** `transform_jobs`
- **Primary Run ID:** `manual__2026-05-10T19:31:26+00:00`
- **Follow-up Run ID:** `manual__2026-05-10T19:36:15+00:00`
- **Status:** Success
- **dbt Target:** `prod`
- **Schema Created:** `analytics`

The follow-up transform run was executed after updating
`dbt/models/intermediate/int_jobs_with_skills.sql` to use `extracted_skills`
from the scraper before falling back to regex extraction from descriptions.

## Analytics Tables

| Table | Rows |
| --- | ---: |
| `raw_job_postings` | 120 |
| `analytics.stg_job_postings` | 120 |
| `analytics.fct_job_postings` | 106 |
| `analytics.dim_skills` | 31 |
| `analytics.dim_companies` | 47 |
| `analytics.agg_salary_insights` | 0 |
| `analytics.fct_daily_metrics` | 1 |

## API Endpoint Verification

**Tested:** 11 public analytics endpoints
**Result:** All returned HTTP 200

Endpoints tested:
- `/job-market-health`
- `/trending-skills`
- `/salary-insights`
- `/hiring-patterns`
- `/company-insights`
- `/skill-demand`
- `/location-trends`
- `/industry-breakdown`
- `/experience-levels`
- `/job-type-mix`
- `/salary-by-skill`

Representative production response:
- `job-market-health`: `total_jobs=106`, `unique_companies=47`,
  `remote_percentage=19.8`
- `company-insights`: real company data returned, including Walmart, CVS
  Health, Kroger, DaVita, TikTok, Lemon.io, and Meta.
- `trending-skills?limit=20&min_jobs=1`: real skill data returned, including
  Python, Java, machine learning, LLM, Kubernetes, Azure, AWS, JavaScript, and
  Docker.

## Dashboard Verification

Production frontend checks:
- `https://applyluma.com` redirects to `https://www.applyluma.com/` and loads
  with HTTP 200.
- `https://applyluma.com/analytics` redirects to
  `https://www.applyluma.com/analytics`, which returns HTTP 404 from Vercel.

Dashboard screenshots were not captured in this execution because the in-app
browser automation tool was unavailable in the session, and the direct
production `/analytics` route returned 404 at the hosting layer.

## Caveats

Salary analytics remain empty:
- `analytics.agg_salary_insights`: 0 rows
- Root cause: this scrape produced no rows with `salary_min` or `salary_max`.
- Impact: salary-specific endpoints return HTTP 200 but empty data.

Default trending skills endpoint can be empty:
- `/trending-skills` defaults to `min_jobs=10`.
- With this run's sample, only Python reached 10 mentions.
- The frontend requests `min_jobs=1`, which returns populated skill data.

Dashboard route needs follow-up:
- Direct navigation to `/analytics` returns Vercel 404.
- `frontend/vercel.json` contains an SPA rewrite, but the deployed production
  route is not honoring it for `www.applyluma.com/analytics`.

## Production Impact

Before Phase 8 execution:
- Railway `raw_job_postings` was empty.
- Analytics schema was absent.
- Public analytics endpoints returned 500.

After Phase 8 execution:
- Railway contains raw scraped job data.
- Railway contains dbt analytics tables.
- All 11 public analytics endpoints return 200.
- Several dashboard data sources now contain real production data.

## Next Steps

- Fix Vercel SPA rewrite/direct-route behavior for `/analytics`.
- Consider increasing scraper page limits if a larger initial dataset is
  required.
- Improve salary extraction or add sources that include salary data.
- Keep the dbt skill extraction fix in the Phase 8 branch.
- Decide whether local Airflow should remain running for scheduled daily
  scraping or be started manually when updates are needed.
