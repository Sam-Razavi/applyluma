# Analytics API — Phase 6 Specification

> **Audience:** Codex (implementor). Read this before touching any `.py` file.
>
> **Claude designed this.** All contracts below are authoritative. Do not change
> response shapes without checking back with Claude.

---

## 1. Overview

### Base URL
```
/api/v1/analytics
```

### Authentication
Every endpoint requires a valid JWT Bearer token:
```
Authorization: Bearer <access_token>
```
Return **401** if the token is missing or invalid.  Use the existing
`get_current_user_id` dependency from `app.core.dependencies`.

### Rate Limiting
Enforced by middleware, not per-endpoint.  Limit: **100 req/min/user**.
Return **429** when exceeded.

### Caching
- Backend: **Redis** (`REDIS_URL` from settings)
- TTL: **3 600 seconds (1 hour)** for all endpoints except `/comparison` (900 s)
- Cache key pattern: `analytics:{endpoint_slug}:{sorted_param_hash}`
- On cache miss → query DB → store result as JSON string → return
- On cache hit → deserialise → return immediately
- Helper: implement `get_redis_client()` in `app.core.dependencies`

### Performance target
Every endpoint must respond in **< 500 ms** (p99) under normal load.
Use the dbt analytics views, **not** `raw_job_postings`, for all Phase 6
queries.  The analytics schema is populated nightly by dbt; data may be up to
24 hours old.

---

## 2. Database Tables (dbt Analytics Schema)

All tables live in the **`analytics`** PostgreSQL schema.

| Table | Description | Key columns |
|---|---|---|
| `analytics.fct_job_postings` | Main fact table, one row per unique job | `job_id`, `job_title`, `normalised_title`, `company_name`, `location`, `salary_min`, `salary_max`, `salary_midpoint`, `employment_type`, `remote_allowed`, `skill_array text[]`, `skill_count`, `scrape_date`, `days_since_posted`, `is_senior_role bool`, `is_junior_role bool`, `is_management_role bool` |
| `analytics.dim_skills` | One row per skill, pre-aggregated | `skill_id`, `skill_name`, `total_job_mentions`, `avg_salary_min`, `avg_salary_max`, `mentions_this_week`, `mentions_last_week`, `trending_score_pct`, `dbt_updated_at` |
| `analytics.agg_salary_insights` | Salary percentiles by dimension | `breakdown_type` ('skill'\|'location'\|'company'\|'employment_type'), `breakdown_value`, `job_count`, `p25_salary`, `p50_salary`, `p75_salary`, `p90_salary`, `avg_salary`, `min_salary_floor`, `max_salary_ceiling` |
| `analytics.fct_daily_metrics` | Aggregated stats per scrape date | `metric_date`, `total_jobs`, `remote_jobs`, `remote_percentage`, `senior_role_count`, `junior_role_count`, `management_role_count`, `avg_salary_midpoint`, `avg_skills_per_job`, `top_10_companies jsonb`, `employment_type_breakdown jsonb`, `top_10_skills jsonb` |
| `analytics.dim_companies` | One row per company, pre-aggregated | `company_id`, `company_name`, `total_jobs_posted`, `remote_jobs`, `remote_percentage`, `avg_salary_min`, `avg_salary_max`, `first_seen_date`, `last_seen_date`, `most_common_employment_type` |

### Application table used by /comparison
| Table | Description | Key columns |
|---|---|---|
| `public.cvs` | User resumes | `id uuid`, `user_id uuid`, `title`, `content text` (parsed text of the CV) |

---

## 3. Standard Response Envelope

Every Phase 6 endpoint wraps its payload in `AnalyticsResponse[T]`:

```json
{
  "success": true,
  "data": [ /* endpoint-specific array or object */ ],
  "metadata": {
    "timestamp": "2026-05-08T14:30:00Z",
    "data_freshness_hours": 24,
    "sample_size": 4217,
    "applied_filters": { "limit": 20 },
    "next_update": "2026-05-09T02:00:00Z"
  },
  "error": null
}
```

**`metadata` construction:**
- `timestamp` — `datetime.utcnow()`
- `data_freshness_hours` — hours since `MAX(dbt_updated_at)` on the primary
  source table (fall back to 24 if the table is empty)
- `sample_size` — total row count of the source table (or result set count)
- `applied_filters` — dict of non-default query-param values
- `next_update` — `timestamp + timedelta(hours=24)` (next dbt run at 03:00 UTC)

**Error envelope:**

```json
{
  "success": false,
  "data": null,
  "metadata": null,
  "error": {
    "code": "INVALID_PARAMS",
    "message": "limit must be between 1 and 100",
    "details": { "limit": "received 200, max is 100" }
  }
}
```

---

## 4. Pydantic Models

All models are in **`app/schemas/analytics.py`** (written by Claude).

Import pattern inside each endpoint module:

```python
from app.schemas.analytics import (
    AnalyticsResponse,
    ResponseMetadata,
    SkillTrend,          # or whichever model the endpoint uses
)
```

---

## 5. Error Codes Reference

| HTTP | code | when |
|---|---|---|
| 400 | `INVALID_PARAMS` | validation failure on query params |
| 401 | `UNAUTHORIZED` | missing / invalid JWT |
| 404 | `NOT_FOUND` | e.g. resume_id does not exist |
| 422 | (FastAPI default) | request body parse error |
| 429 | `RATE_LIMITED` | > 100 req/min |
| 500 | `INTERNAL_ERROR` | unhandled DB / Redis exception |

For 400, include the field name and constraint in `details`.

---

## 6. Shared Implementation Utilities

Create **`app/db/queries/analytics_queries.py`** with helper functions:

```python
async def get_dbt_freshness(db: Session, table: str) -> tuple[int, datetime | None]:
    """Return (hours_since_refresh, next_update_dt) for a dbt table."""
    ...

def build_cache_key(*parts: str) -> str:
    """Deterministic Redis key from endpoint name + sorted params."""
    ...

async def get_or_cache(
    redis,
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Any],
) -> Any:
    """Cache-aside helper: hit → deserialise, miss → fetch → store."""
    ...
```

---

## 7. Endpoint Specifications

---

### 7.1  GET /trending-skills

**File:** `trending_skills.py`  
**Source table:** `analytics.dim_skills`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:trending_skills:{limit}:{min_jobs}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 20 | 1–100 | Max skills to return |
| `min_jobs` | int | 10 | 1–10 000 | Minimum total_job_mentions threshold |

#### SQL Query

```sql
SELECT
    skill_name,
    total_job_mentions                          AS frequency,
    ROUND(
        total_job_mentions * 100.0
        / NULLIF((SELECT SUM(total_job_mentions) FROM analytics.dim_skills), 0),
        2
    )                                           AS frequency_pct,
    avg_salary_min,
    avg_salary_max,
    COALESCE(trending_score_pct, 0)             AS trending_score_pct,
    CASE
        WHEN trending_score_pct >  5 THEN 'up'
        WHEN trending_score_pct < -5 THEN 'down'
        ELSE 'stable'
    END                                         AS trend
FROM analytics.dim_skills
WHERE total_job_mentions >= :min_jobs
ORDER BY total_job_mentions DESC
LIMIT :limit;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "skill": "Python",
      "frequency": 1842,
      "frequency_pct": 43.7,
      "avg_salary_min": 65000,
      "avg_salary_max": 95000,
      "trending_score_pct": 12.5,
      "trend": "up"
    }
  ],
  "metadata": {
    "timestamp": "2026-05-08T14:30:00Z",
    "data_freshness_hours": 18,
    "sample_size": 4217,
    "applied_filters": { "limit": 20, "min_jobs": 10 },
    "next_update": "2026-05-09T03:00:00Z"
  },
  "error": null
}
```

#### Error Responses

- **400** — `limit` outside 1–100 or `min_jobs` outside 1–10000
- **500** — DB / Redis failure

---

### 7.2  GET /salary-insights

**File:** `salary_insights.py`  
**Source tables:** `analytics.agg_salary_insights` (primary), `analytics.fct_job_postings` (for experience_level filter)  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:salary_insights:{location}:{job_title}:{experience_level}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `location` | str \| None | None | max 200 chars | Filter by location substring (ILIKE match) |
| `job_title` | str \| None | None | max 200 chars | Filter by normalised_title substring |
| `experience_level` | ExperienceLevel \| None | None | junior\|mid\|senior\|management | Filter by experience level |

#### Query Logic

**Case A — no `experience_level`, no `job_title`** (location filter only):
Query `analytics.agg_salary_insights WHERE breakdown_type = 'location'`.

**Case B — `experience_level` specified** (or `job_title` specified):
Query `analytics.fct_job_postings` directly, apply CASE filters for experience,
ILIKE filters for location/title, compute percentiles inline.

```sql
-- Case B query skeleton
SELECT
    :dimension_type                                    AS dimension_type,
    :dimension_value                                   AS dimension_value,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary_midpoint)) AS p25_salary,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY salary_midpoint)) AS p50_salary,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary_midpoint)) AS p75_salary,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY salary_midpoint)) AS p90_salary,
    ROUND(AVG(salary_midpoint))                        AS avg_salary,
    ROUND(MIN(salary_min))                             AS min_salary_floor,
    ROUND(MAX(salary_max))                             AS max_salary_ceiling,
    COUNT(DISTINCT job_id)                             AS job_count
FROM analytics.fct_job_postings
WHERE salary_midpoint IS NOT NULL
  AND (:location  IS NULL OR location       ILIKE '%' || :location  || '%')
  AND (:job_title IS NULL OR normalised_title ILIKE '%' || :job_title || '%')
  AND (
        :experience_level IS NULL
        OR (:experience_level = 'senior'     AND is_senior_role)
        OR (:experience_level = 'junior'     AND is_junior_role)
        OR (:experience_level = 'management' AND is_management_role)
        OR (:experience_level = 'mid'        AND NOT is_senior_role
                                             AND NOT is_junior_role
                                             AND NOT is_management_role)
  );
```

If no filters at all, return a single "overall" row (dimension_type='overall',
dimension_value='all').

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "dimension_type": "location",
      "dimension_value": "London",
      "p25_salary": 55000,
      "p50_salary": 72000,
      "p75_salary": 95000,
      "p90_salary": 125000,
      "avg_salary": 74500,
      "min_salary_floor": 30000,
      "max_salary_ceiling": 200000,
      "job_count": 412
    }
  ],
  "metadata": { "..." : "..." },
  "error": null
}
```

#### Error Responses

- **400** — `location` or `job_title` exceeds 200 chars; invalid `experience_level`
- **404** — no salary data matches the filter combination (return empty `data: []`, **not** 404)

---

### 7.3  GET /hiring-patterns

**File:** `hiring_patterns.py`  
**Source table:** `analytics.fct_daily_metrics`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:hiring_patterns:{days_back}:{granularity}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `days_back` | int | 90 | 7–365 | How many days of history to return |
| `granularity` | Granularity | daily | daily\|weekly\|monthly | Time-bucketing level |

#### SQL Query

```sql
-- granularity = daily
SELECT
    metric_date::text                          AS period,
    total_jobs                                 AS job_count,
    remote_jobs                                AS remote_count,
    remote_percentage,
    avg_salary_midpoint                        AS avg_salary
FROM analytics.fct_daily_metrics
WHERE metric_date >= CURRENT_DATE - :days_back
ORDER BY metric_date;

-- granularity = weekly (use DATE_TRUNC)
SELECT
    TO_CHAR(DATE_TRUNC('week', metric_date), 'IYYY-"W"IW') AS period,
    SUM(total_jobs)                            AS job_count,
    SUM(remote_jobs)                           AS remote_count,
    ROUND(AVG(remote_percentage), 1)           AS remote_percentage,
    ROUND(AVG(avg_salary_midpoint))            AS avg_salary
FROM analytics.fct_daily_metrics
WHERE metric_date >= CURRENT_DATE - :days_back
GROUP BY DATE_TRUNC('week', metric_date)
ORDER BY DATE_TRUNC('week', metric_date);

-- granularity = monthly (same pattern with 'month')
```

#### Response Example

```json
{
  "success": true,
  "data": [
    { "period": "2026-04-01", "job_count": 183, "remote_count": 72, "remote_percentage": 39.3, "avg_salary": 68000 },
    { "period": "2026-04-02", "job_count": 201, "remote_count": 88, "remote_percentage": 43.8, "avg_salary": 71200 }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

#### Error Responses

- **400** — `days_back` outside 7–365; invalid `granularity` value

---

### 7.4  GET /company-insights

**File:** `company_insights.py`  
**Source table:** `analytics.dim_companies`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:company_insights:{limit}:{location_slug}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 20 | 1–100 | Max companies to return |
| `location` | str \| None | None | max 200 chars | Filter companies that have posted in this location |

#### Query Logic

When `location` is provided, filter `analytics.fct_job_postings` to find
`company_name` values that have at least one posting in that location, then
join to `analytics.dim_companies`.

```sql
SELECT
    dc.company_name,
    dc.total_jobs_posted          AS total_jobs,
    dc.remote_jobs,
    dc.remote_percentage,
    dc.avg_salary_min,
    dc.avg_salary_max,
    dc.most_common_employment_type,
    dc.first_seen_date::text,
    dc.last_seen_date::text,
    -- hiring_velocity = total_jobs / weeks_in_window
    ROUND(
        dc.total_jobs_posted::numeric
        / NULLIF(
            EXTRACT(DAY FROM (dc.last_seen_date - dc.first_seen_date)) / 7.0,
            0
        ),
        2
    )                             AS hiring_velocity
FROM analytics.dim_companies dc
WHERE (:location IS NULL
    OR dc.company_name IN (
        SELECT DISTINCT company_name
        FROM analytics.fct_job_postings
        WHERE location ILIKE '%' || :location || '%'
    )
)
ORDER BY dc.total_jobs_posted DESC
LIMIT :limit;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "company_name": "Acme Corp",
      "total_jobs": 87,
      "remote_jobs": 34,
      "remote_percentage": 39.1,
      "avg_salary_min": 60000,
      "avg_salary_max": 90000,
      "most_common_employment_type": "full_time",
      "first_seen_date": "2026-01-10",
      "last_seen_date": "2026-05-07",
      "hiring_velocity": 2.1
    }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

#### Error Responses

- **400** — `limit` outside 1–100; `location` exceeds 200 chars

---

### 7.5  GET /job-market-health

**File:** `job_market_health.py`  
**Source table:** `analytics.fct_job_postings`, `analytics.fct_daily_metrics`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:job_market_health`

#### No query parameters.

#### Query Logic

Run two queries:

```sql
-- Query 1: totals from fct_job_postings
SELECT
    COUNT(DISTINCT job_id)                                           AS total_jobs,
    COUNT(DISTINCT company_name)                                     AS unique_companies,
    ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / COUNT(*), 1)
                                                                     AS remote_percentage,
    ROUND(AVG(salary_midpoint) FILTER (WHERE salary_midpoint IS NOT NULL))
                                                                     AS avg_salary_midpoint,
    ROUND(COUNT(*) FILTER (WHERE is_senior_role)  * 100.0 / COUNT(*), 1) AS senior_role_pct,
    ROUND(COUNT(*) FILTER (WHERE is_junior_role)  * 100.0 / COUNT(*), 1) AS junior_role_pct,
    ROUND(COUNT(*) FILTER (WHERE is_management_role) * 100.0 / COUNT(*), 1) AS management_role_pct,
    ROUND(AVG(skill_count), 1)                                       AS avg_skills_per_job,
    (MAX(scrape_date) - MIN(scrape_date))                            AS data_date_range_days
FROM analytics.fct_job_postings;

-- Query 2: last refresh timestamp
SELECT MAX(dbt_updated_at) AS last_updated FROM analytics.fct_job_postings;
```

Compute `mid_role_pct = 100 - senior - junior - management` in Python.

#### Response Example

```json
{
  "success": true,
  "data": {
    "total_jobs": 4217,
    "unique_companies": 893,
    "remote_percentage": 41.2,
    "avg_salary_midpoint": 72500,
    "senior_role_pct": 28.4,
    "junior_role_pct": 9.1,
    "management_role_pct": 6.3,
    "mid_role_pct": 56.2,
    "avg_skills_per_job": 4.7,
    "data_date_range_days": 120,
    "last_updated": "2026-05-08T03:00:00Z"
  },
  "metadata": { "...": "..." },
  "error": null
}
```

**Note:** `data` is a single **object**, not an array.

#### Error Responses

- **500** — DB or Redis failure

---

### 7.6  GET /skill-demand

**File:** `skill_demand.py`  
**Source table:** `analytics.dim_skills`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:skill_demand:{limit}:{min_growth_pct}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 20 | 1–100 | Max skills to return |
| `min_growth_pct` | float | 5.0 | -100.0–10 000.0 | Minimum `trending_score_pct` threshold |

#### SQL Query

```sql
SELECT
    skill_name                               AS skill,
    total_job_mentions,
    mentions_this_week,
    mentions_last_week,
    COALESCE(trending_score_pct, 0)          AS trending_score_pct,
    avg_salary_min,
    avg_salary_max,
    CASE
        WHEN trending_score_pct >  5 THEN 'up'
        WHEN trending_score_pct < -5 THEN 'down'
        ELSE 'stable'
    END                                      AS trend
FROM analytics.dim_skills
WHERE COALESCE(trending_score_pct, 0) >= :min_growth_pct
ORDER BY trending_score_pct DESC
LIMIT :limit;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "skill": "Rust",
      "total_mentions": 218,
      "mentions_this_week": 44,
      "mentions_last_week": 31,
      "trending_score_pct": 41.9,
      "avg_salary_min": 85000,
      "avg_salary_max": 130000,
      "trend": "up"
    }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

#### Error Responses

- **400** — `limit` outside 1–100; `min_growth_pct` outside valid range

---

### 7.7  GET /location-trends

**File:** `location_trends.py`  
**Source tables:** `analytics.fct_job_postings`, `analytics.agg_salary_insights`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:location_trends`

#### No query parameters.

> **Note:** The data has raw location strings (no structured country/state/city
> hierarchy).  This endpoint returns the top 30 locations by job count.

#### SQL Query

```sql
WITH totals AS (
    SELECT COUNT(*) AS grand_total FROM analytics.fct_job_postings
),
by_location AS (
    SELECT
        location,
        COUNT(*)                                                          AS job_count,
        ROUND(COUNT(*) * 100.0 / (SELECT grand_total FROM totals), 2)    AS pct_of_total,
        ROUND(AVG(salary_midpoint) FILTER (WHERE salary_midpoint IS NOT NULL)) AS avg_salary_midpoint,
        ROUND(
            COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / COUNT(*),
            1
        )                                                                 AS remote_percentage
    FROM analytics.fct_job_postings
    WHERE location IS NOT NULL AND location != 'Unknown'
    GROUP BY location
)
SELECT *
FROM by_location
ORDER BY job_count DESC
LIMIT 30;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "location": "London",
      "job_count": 812,
      "pct_of_total": 19.3,
      "avg_salary_midpoint": 76000,
      "remote_percentage": 38.4
    }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

---

### 7.8  GET /industry-breakdown

**File:** `industry_breakdown.py`  
**Source table:** `analytics.fct_job_postings`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:industry_breakdown`

#### No query parameters.

#### Industry Derivation

There is **no explicit industry column** in the data.  Derive industry from
`normalised_title` using the following CASE logic (match in priority order):

| Industry label | Title keywords (case-insensitive) |
|---|---|
| Software Engineering | engineer, developer, programmer, software, backend, frontend, fullstack |
| Data & Analytics | data, analyst, analytics, scientist, machine learning, ML, AI, NLP |
| DevOps & Infrastructure | devops, cloud, platform, infrastructure, SRE, reliability, kubernetes, docker |
| Product & Design | product manager, product owner, UX, UI, designer, design |
| Management & Leadership | manager, director, head of, VP, CTO, CIO, chief |
| Finance & Legal | finance, accountant, compliance, legal, counsel, risk |
| Sales & Marketing | sales, marketing, growth, SEO, content, social media |
| Other | (everything else) |

#### SQL Query Skeleton

```sql
WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings),
classified AS (
    SELECT
        CASE
            WHEN normalised_title ~* '\m(engineer|developer|programmer|software|backend|frontend|fullstack)\M'
                THEN 'Software Engineering'
            WHEN normalised_title ~* '\m(data|analyst|analytics|scientist|machine learning|ml|ai|nlp)\M'
                THEN 'Data & Analytics'
            WHEN normalised_title ~* '\m(devops|cloud|platform|infrastructure|sre|reliability|kubernetes|docker)\M'
                THEN 'DevOps & Infrastructure'
            WHEN normalised_title ~* '\m(product manager|product owner|ux|ui|designer|design)\M'
                THEN 'Product & Design'
            WHEN normalised_title ~* '\m(manager|director|head of|vp|cto|cio|chief)\M'
                THEN 'Management & Leadership'
            WHEN normalised_title ~* '\m(finance|accountant|compliance|legal|counsel|risk)\M'
                THEN 'Finance & Legal'
            WHEN normalised_title ~* '\m(sales|marketing|growth|seo|content|social media)\M'
                THEN 'Sales & Marketing'
            ELSE 'Other'
        END AS industry,
        salary_min,
        salary_max,
        remote_allowed
    FROM analytics.fct_job_postings
)
SELECT
    industry,
    COUNT(*)                                                              AS job_count,
    ROUND(COUNT(*) * 100.0 / (SELECT n FROM total), 2)                   AS pct_of_total,
    ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL))          AS avg_salary_min,
    ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL))          AS avg_salary_max,
    ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / COUNT(*), 1)  AS remote_percentage
FROM classified
GROUP BY industry
ORDER BY job_count DESC;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "industry": "Software Engineering",
      "job_count": 1842,
      "pct_of_total": 43.7,
      "avg_salary_min": 65000,
      "avg_salary_max": 95000,
      "remote_percentage": 52.1
    }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

---

### 7.9  GET /experience-levels

**File:** `experience_levels.py`  
**Source table:** `analytics.fct_job_postings`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:experience_levels`

#### No query parameters.

#### Query Logic

Use the boolean flags (`is_senior_role`, `is_junior_role`, `is_management_role`)
from `fct_job_postings`.  A job that matches none of the three flags is
classified as "mid".

```sql
WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings),
classified AS (
    SELECT
        CASE
            WHEN is_management_role THEN 'management'
            WHEN is_senior_role     THEN 'senior'
            WHEN is_junior_role     THEN 'junior'
            ELSE                         'mid'
        END                        AS level,
        salary_min,
        salary_max,
        remote_allowed
    FROM analytics.fct_job_postings
)
SELECT
    level,
    COUNT(*)                                                              AS job_count,
    ROUND(COUNT(*) * 100.0 / (SELECT n FROM total), 2)                   AS pct_of_total,
    ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL))          AS avg_salary_min,
    ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL))          AS avg_salary_max,
    ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / COUNT(*), 1)  AS remote_percentage
FROM classified
GROUP BY level
ORDER BY job_count DESC;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    { "level": "mid",        "job_count": 2370, "pct_of_total": 56.2, "avg_salary_min": 55000, "avg_salary_max": 82000, "remote_percentage": 40.1 },
    { "level": "senior",     "job_count": 1198, "pct_of_total": 28.4, "avg_salary_min": 80000, "avg_salary_max": 120000, "remote_percentage": 44.7 },
    { "level": "junior",     "job_count": 384,  "pct_of_total": 9.1,  "avg_salary_min": 30000, "avg_salary_max": 50000, "remote_percentage": 28.9 },
    { "level": "management", "job_count": 265,  "pct_of_total": 6.3,  "avg_salary_min": 90000, "avg_salary_max": 140000, "remote_percentage": 35.1 }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

---

### 7.10  GET /job-type-mix

**File:** `job_type_mix.py`  
**Source table:** `analytics.fct_job_postings`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:job_type_mix`

#### No query parameters.

#### Query Logic

Group by `employment_type` + `remote_allowed` to produce a combined breakdown.

```sql
WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings)
SELECT
    COALESCE(employment_type, 'unknown')       AS job_type,
    CASE
        WHEN remote_allowed THEN 'remote'
        ELSE 'on-site'
    END                                        AS remote_label,
    COUNT(*)                                   AS job_count,
    ROUND(COUNT(*) * 100.0 / (SELECT n FROM total), 2) AS pct_of_total,
    ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL)) AS avg_salary_min,
    ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL)) AS avg_salary_max
FROM analytics.fct_job_postings
GROUP BY employment_type, remote_allowed
ORDER BY job_count DESC;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    { "job_type": "full_time", "remote_label": "on-site", "job_count": 1823, "pct_of_total": 43.2, "avg_salary_min": 58000, "avg_salary_max": 88000 },
    { "job_type": "full_time", "remote_label": "remote",  "job_count": 1102, "pct_of_total": 26.1, "avg_salary_min": 62000, "avg_salary_max": 95000 }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

---

### 7.11  GET /salary-by-skill

**File:** `salary_by_skill.py`  
**Source table:** `analytics.agg_salary_insights`  
**Cache TTL:** 3 600 s  
**Cache key:** `analytics:salary_by_skill:{limit}`

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 20 | 1–100 | Top N skills by job_count |

#### SQL Query

```sql
SELECT
    breakdown_value        AS skill,
    avg_salary,
    p25_salary,
    p50_salary,
    p75_salary,
    p90_salary,
    min_salary_floor,
    max_salary_ceiling,
    job_count
FROM analytics.agg_salary_insights
WHERE breakdown_type = 'skill'
ORDER BY job_count DESC
LIMIT :limit;
```

#### Response Example

```json
{
  "success": true,
  "data": [
    {
      "skill": "Python",
      "avg_salary": 78000,
      "p25_salary": 60000,
      "p50_salary": 75000,
      "p75_salary": 95000,
      "p90_salary": 125000,
      "min_salary_floor": 30000,
      "max_salary_ceiling": 200000,
      "job_count": 1842
    }
  ],
  "metadata": { "...": "..." },
  "error": null
}
```

#### Error Responses

- **400** — `limit` outside 1–100

---

### 7.12  GET /comparison

**File:** `comparison.py`  
**Source tables:** `public.cvs`, `analytics.dim_skills`, `analytics.agg_salary_insights`  
**Cache TTL:** 900 s (15 min — personalised, shorter TTL)  
**Cache key:** `analytics:comparison:{user_id}:{resume_id}`

#### Query Parameters

| Param | Type | Constraints | Description |
|---|---|---|---|
| `resume_id` | UUID str | required | Must belong to the authenticated user |

#### Implementation Steps

1. **Load resume** — `SELECT id, title, content, user_id FROM public.cvs WHERE id = :resume_id`.
   Return **404** if not found, **403** if `user_id != current_user_id`.

2. **Extract resume skills** — tokenise `content` text:
   - Lowercase the text
   - Load all `skill_name` values from `analytics.dim_skills`
   - For each skill, do a case-insensitive substring search in the resume text
   - Return list of matched skill names (resume skills)

3. **Fetch market data for resume skills**:
   ```sql
   SELECT
       skill_name,
       total_job_mentions,
       mentions_this_week,
       mentions_last_week,
       COALESCE(trending_score_pct, 0) AS trending_score_pct,
       avg_salary_min,
       avg_salary_max,
       CASE
           WHEN trending_score_pct >  5 THEN 'up'
           WHEN trending_score_pct < -5 THEN 'down'
           ELSE 'stable'
       END AS trend,
       RANK() OVER (ORDER BY total_job_mentions DESC) AS market_demand_rank
   FROM analytics.dim_skills
   ORDER BY total_job_mentions DESC;
   ```
   Keep all rows for ranking; filter to resume skills for `skill_details`.

4. **Missing high-demand skills** — top 20 skills by `market_demand_rank` that
   are NOT in the resume skills list.

5. **Salary benchmark** — query `agg_salary_insights WHERE breakdown_type = 'skill'`
   for all resume skills, compute weighted average percentiles across those skills
   (weight by `job_count`).

6. **Alignment score** — computed in Python:
   ```
   coverage = len(matched_skills) / max(len(resume_skills), 1)
   demand_score = average of (1 - (rank - 1) / total_skills) for matched skills
   alignment_score = round((coverage * 0.4 + demand_score * 0.6) * 100, 1)
   ```

#### Response Example

```json
{
  "success": true,
  "data": {
    "resume_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "resume_title": "Senior Python Developer CV",
    "resume_skill_count": 14,
    "matched_skills": ["Python", "SQL", "Docker", "AWS"],
    "missing_high_demand_skills": ["TypeScript", "Kubernetes", "Terraform"],
    "skill_details": [
      {
        "skill": "Python",
        "in_resume": true,
        "market_demand_rank": 1,
        "total_market_mentions": 1842,
        "trending_score_pct": 12.5,
        "avg_salary_min": 65000,
        "avg_salary_max": 95000,
        "trend": "up"
      }
    ],
    "market_salary_benchmark": {
      "dimension_type": "skills_blend",
      "dimension_value": "resume_skills",
      "p25_salary": 62000,
      "p50_salary": 78000,
      "p75_salary": 98000,
      "p90_salary": 128000,
      "avg_salary": 79500,
      "min_salary_floor": 35000,
      "max_salary_ceiling": 180000,
      "job_count": 6840
    },
    "skills_market_coverage_pct": 78.6,
    "overall_market_alignment_score": 72.4
  },
  "metadata": { "...": "..." },
  "error": null
}
```

**Note:** `data` is a single **object**, not an array.

#### Error Responses

- **400** — `resume_id` is not a valid UUID
- **403** — resume belongs to a different user (return 403, not 404)
- **404** — resume_id not found
- **500** — DB / Redis failure

---

## 8. File Structure Summary (Codex creates)

```
backend/app/api/v1/endpoints/analytics/
├── SPEC.md                  ← this file (Claude)
├── __init__.py              ← router aggregator (Claude)
├── legacy.py                ← Phase 1-5 endpoints (Claude)
├── trending_skills.py       ← §7.1  (Codex)
├── salary_insights.py       ← §7.2  (Codex)
├── hiring_patterns.py       ← §7.3  (Codex)
├── company_insights.py      ← §7.4  (Codex)
├── job_market_health.py     ← §7.5  (Codex)
├── skill_demand.py          ← §7.6  (Codex)
├── location_trends.py       ← §7.7  (Codex)
├── industry_breakdown.py    ← §7.8  (Codex)
├── experience_levels.py     ← §7.9  (Codex)
├── job_type_mix.py          ← §7.10 (Codex)
├── salary_by_skill.py       ← §7.11 (Codex)
└── comparison.py            ← §7.12 (Codex)

backend/app/db/queries/
└── analytics_queries.py     ← shared helpers (Codex)

backend/tests/
└── test_analytics_endpoints.py  ← unit tests (Codex)
```

## 9. Each Codex Module Template

Every endpoint module must follow this structure:

```python
"""GET /analytics/{endpoint} — {one-line description}."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.analytics import AnalyticsResponse, ResponseMetadata, XxxModel

router = APIRouter()

CACHE_TTL = 3_600  # seconds
CACHE_PREFIX = "analytics:{endpoint_slug}"


@router.get("/{endpoint-path}", response_model=AnalyticsResponse[list[XxxModel]])
def get_{endpoint}(
    # query params here
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cache_key = f"{CACHE_PREFIX}:..."
    # 1. Check Redis cache
    # 2. On miss: run SQL query
    # 3. Store in Redis
    # 4. Return AnalyticsResponse(success=True, data=..., metadata=...)
```

---

## 10. Testing Requirements

Codex must write **`backend/tests/test_analytics_endpoints.py`** with at least
5 test cases per endpoint (60 tests total):

1. **Happy path** — valid request, expects 200 + non-empty data
2. **Param validation** — invalid param value, expects 400
3. **Empty result** — when DB returns no rows, expects 200 + `data: []`
4. **Cache hit** — second identical call uses cache (mock Redis hit)
5. **DB error** — SQLAlchemy raises, expects 500

Use `pytest` + `httpx.AsyncClient` + `pytest-asyncio`.
Mock DB with `unittest.mock.patch` or `pytest-mock`.

---

*End of SPEC.md*
