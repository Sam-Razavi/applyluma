# ApplyLuma dbt Project (`applyluma_dw`)

Transforms raw job-market data scraped by Airflow into clean, analytics-ready
tables in the `analytics` PostgreSQL schema.

## Model lineage

```
public.raw_job_postings  (source)
  └─ stg_job_postings        (view)
       └─ int_jobs_deduplicated   (ephemeral)
            └─ int_jobs_with_skills    (ephemeral)
                 ├─ dim_companies      (table)
                 ├─ dim_skills         (table)
                 ├─ fct_job_postings   (incremental table)
                 │    └─ fct_daily_metrics  (table)
                 └─ (also referenced by fct_job_postings via dim_companies)
```

## Materialisation strategy

| Layer        | Strategy    | Reason                                      |
|--------------|-------------|---------------------------------------------|
| staging      | view        | Always fresh; cheap since source is indexed |
| intermediate | ephemeral   | Inlined as CTEs; no extra table churn       |
| dim_*        | table       | Full-refresh aggregates                     |
| fct_job_postings | incremental | Grows daily; avoid full rescans         |
| fct_daily_metrics | table  | Small; recalculated on every run            |

## Running locally

```bash
cd dbt

# One-time: create the analytics schema
psql $DATABASE_URL -c "CREATE SCHEMA IF NOT EXISTS analytics;"

# Run all models
dbt run --profiles-dir .

# Run only marts
dbt run --select marts --profiles-dir .

# Run tests
dbt test --profiles-dir .

# Full refresh of incremental models
dbt run --full-refresh --profiles-dir .

# Check source freshness
dbt source freshness --profiles-dir .
```

## Environment variables

| Variable          | Default       | Description                        |
|-------------------|---------------|------------------------------------|
| `DBT_DB_HOST`     | `localhost`   | Postgres host                      |
| `DBT_DB_PORT`     | `5433`        | Postgres port (5433 = Docker host) |
| `POSTGRES_USER`   | `applyluma`   | DB user                            |
| `POSTGRES_PASSWORD` | `applyluma` | DB password                        |
| `POSTGRES_DB`     | `applyluma`   | DB name                            |

## Adding a new model

1. Add a `.sql` file in the appropriate layer (`staging/`, `intermediate/`, `marts/`).
2. Reference upstream models with `{{ ref('model_name') }}` and sources with `{{ source('applyluma_raw', 'table') }}`.
3. Document columns in the layer's `schema.yml`.
4. Run `dbt run --select your_model` then `dbt test --select your_model`.

## Macros

### `extract_skills(column_name)`
Emits a PostgreSQL `text[]` of tech skills detected in `column_name` via
word-boundary regex. Extend `macros/extract_skills.sql` to add new skills.
Call it once in a CTE alias so the 36-branch CASE block runs exactly once per row.

## Tests

- **Generic tests** (unique, not_null, accepted_values, relationships) are declared
  in each layer's `schema.yml`.
- **Singular test** `tests/assert_unique_jobs.sql` fails if `fct_job_postings`
  contains rows with the same company + normalised_title + scrape_date.
