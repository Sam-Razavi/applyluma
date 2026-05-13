# Graph Report - applyluma  (2026-05-13)

## Corpus Check
- 163 files · ~62,798 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1050 nodes · 1524 edges · 101 communities (85 shown, 16 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 150 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `60963d9b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]

## God Nodes (most connected - your core abstractions)
1. `useAuthStore` - 25 edges
2. `TailorStatus` - 17 edges
3. `TailorIntensity` - 17 edges
4. `ApplyLuma Production Testing Checklist` - 15 edges
5. `safe_execute()` - 14 edges
6. `formatNumber()` - 14 edges
7. `FakeDb` - 13 edges
8. `request()` - 13 edges
9. `ApplyLuma AI Context` - 13 edges
10. `7. Endpoint Specifications` - 13 edges

## Surprising Connections (you probably didn't know these)
- `get_usage()` --calls--> `TailorUsageResponse`  [INFERRED]
  backend/app/api/v1/endpoints/tailor.py → backend/app/schemas/tailor.py
- `get_preview()` --calls--> `TailorPreviewResponse`  [INFERRED]
  backend/app/api/v1/endpoints/tailor.py → backend/app/schemas/tailor.py
- `TailorCVRequest` --uses--> `User`  [INFERRED]
  backend/app/api/v1/endpoints/ai.py → backend/app/models/user.py
- `TailorCVResponse` --uses--> `User`  [INFERRED]
  backend/app/api/v1/endpoints/ai.py → backend/app/models/user.py
- `get_jobs_over_time()` --calls--> `DailyJobCount`  [INFERRED]
  backend/app/api/v1/endpoints/analytics.py → backend/app/schemas/analytics.py

## Communities (101 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (53): create_access_token(), create_refresh_token(), login(), login_oauth2(), OAuth2-compatible form login — used by the Swagger UI 'Authorize' button., refresh(), delete_cv(), download_cv() (+45 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (31): apiClient, redirectToLogin(), ProtectedRoute(), config, ACTIVITY_EVENTS, useInactivityLogout(), AppLayout(), NAV_LINKS (+23 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (41): get_company_insights(), GET /analytics/company-insights - top companies by hiring volume., get_comparison(), GET /analytics/comparison - compare a resume to market trends., _salary_benchmark(), get_experience_levels(), GET /analytics/experience-levels - jobs by seniority., get_hiring_patterns() (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (22): PreviewStepProps, SelectorProps, SelectStepProps, Step, tailorApi, IntensitySelector(), OPTIONS, Props (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (17): ABC, BaseScraper, extract_skills(), _extract_skills_from_text(), _get_db_conn_str(), scrape_remotive(), scrape_the_muse(), BaseScraper (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (23): Props, JobFormData, jobSchema, KEYWORD_COLORS, aiApi, analyticsApi, CreateJobDescriptionRequest, jobApi (+15 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): EndpointCase, FakeDb, FakeRedis, FakeResult, FakeRow, request(), test_comparison_cache_hit_with_authentication(), test_comparison_db_error_with_authentication() (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (28): AnalyticsHeaderProps, Analytics(), AnalyticsSnapshot, applySettledResult(), chartFallback(), CompanyInsightsChart, emptyAnalyticsSnapshot(), ExperienceLevelsChart (+20 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (29): BaseModel, Enum, ok_response(), AnalyticsResponse, CompanyInsight, DailyJobCount, ErrorDetail, ExperienceLevel (+21 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (18): Props, Props, TreemapTile(), TreemapTileProps, Props, Props, Props, ANALYTICS_COLORS (+10 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (23): 10. Testing Requirements, 1. Overview, 2. Database Tables (dbt Analytics Schema), 3. Standard Response Envelope, 4. Pydantic Models, 5. Error Codes Reference, 6. Shared Implementation Utilities, 8. File Structure Summary (Codex creates) (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (23): code:bash (AIRFLOW_POSTGRES_CONN_HOST=<railway-host>), code:bash (docker-compose down), code:bash (docker-compose up -d), code:bash (docker-compose up -d), code:bash (./docker/start-airflow-railway.sh), code:bash (./docker/verify-railway-connection.sh), code:bash (docker-compose exec airflow-webserver airflow dags trigger s), code:bash (docker-compose exec airflow-webserver airflow dags trigger t) (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (13): Props, Props, Props, ExperienceLevelBreakdown, HiringPatternPoint, SalaryInsightItem, formatCompactCurrency(), formatCurrency() (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (19): ApplyLuma, code:bash (git checkout dev), code:bash (docker-compose up), code:bash (cd backend), code:bash (cd frontend), code:bash (./docker/start-airflow-railway.sh), code:bash (curl https://applyluma-production.up.railway.app/api/v1/anal), code:text (applyluma/) (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (12): Base, Base, TimestampMixin, DeclarativeBase, CV, JobDescription, TailorJob, User (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (17): Before Merging to Main, Branch Strategy, code:bash (git checkout dev), code:bash (git checkout -b feature/your-feature-name), code:bash (git add .), code:bash (git push origin feature/your-feature-name), code:bash (git checkout dev), code:bash (git checkout main) (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (17): code:yaml (AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://user:password@rai), code:sql (SELECT COUNT(*) FROM raw_job_postings;), code:python (schedule_interval = "0 2 * * *"  # 2 AM UTC daily), Connect Airflow to Railway Production Database, Option A: Via Airflow UI, Option B: Via Environment Variable, Overview, Prerequisites (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (15): get_jobs_over_time(), get_overview(), get_recent_jobs(), get_top_companies(), get_top_skills(), Legacy analytics endpoints (Phase 1-5).  These endpoints query raw_job_posting, get_jobs_over_time(), get_overview() (+7 more)

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (12): TailorIntensity, TailorStatus, TailorJobPublic, TailorMeta, TailorPreviewResponse, TailorSaveRequest, TailorSaveResponse, TailorSection (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (16): AI CV Tailoring, Analytics Pipeline, ApplyLuma - Project Instructions, Backend, Backend (`/backend`), Core Tech Stack, Data Engineering (`/airflow`, `/dbt`), Development Workflow (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (16): 1. Visual Design Compliance, 2. Functional Testing, 3. Responsive Design, 4. Performance, 5. Error Handling, 6. Accessibility, 7. Cross-Browser, Console Errors (+8 more)

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (12): cv_data(), FakeDb, request(), test_delete_cv_removes_file_and_record(), test_get_cv_returns_cv_details(), test_get_cv_returns_not_found_for_missing_cv(), test_list_cvs_returns_user_cvs(), test_set_default_cv_calls_crud() (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.12
Nodes (15): code:bash (DATABASE_URL=<from Step 2>), code:bash (alembic upgrade head), code:text (https://your-backend-url.up.railway.app/health), code:json ({"status":"healthy","version":"0.1.0"}), code:text (https://your-backend-url.up.railway.app/docs), Prerequisites, Railway Backend Deployment Guide, Step 1: Create New Railway Project (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (15): AI Resume Analysis, Analytics Dashboard, ApplyLuma Production Testing Checklist, Authentication, Backend Health Checks, Bugs Found, Cross-Browser Testing, Data Pipeline (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (13): AI Development Guidelines, ApplyLuma AI Context, Current Phase, Deployment, Environment Variables, Git Workflow, Key Files, Known Issues (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.31
Nodes (8): FakeDb, jd_data(), request(), test_create_jd_extracts_keywords(), test_delete_jd_calls_crud(), test_get_jd_returns_404_if_missing(), test_list_jds_returns_user_data(), user()

### Community 26 - "Community 26"
Cohesion: 0.21
Nodes (10): formatValue(), ICONS, KPICard(), KPICardProps, KPIFormat, KPIIcon, JobMarketHealthCard(), Props (+2 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (11): Adding a new model, ApplyLuma dbt Project (`applyluma_dw`), code:block1 (public.raw_job_postings  (source)), code:bash (cd dbt), Environment variables, `extract_skills(column_name)`, Macros, Materialisation strategy (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.31
Nodes (5): cv(), FakeDb, request(), test_download_generates_pdf_for_original_cv_without_pdf_file(), test_download_regenerates_missing_tailored_pdf()

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (3): ChartCardProps, EmptyStateProps, ErrorStateProps

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (10): Analytics Tables, API Endpoint Verification, Caveats, Dashboard Verification, Next Steps, Phase 8 Execution Report - Railway Database Population, Production Impact, Scraping Results (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.2
Nodes (9): ApplyLuma Health Check Report, code:bash (airflow connections add postgres_default \), code:bash (docker-compose exec frontend npm install), Commands Run, Critical Issues, Recommendations, Summary, Test Artifacts Created (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.2
Nodes (9): Namecheap DNS Configuration for applyluma.com, Prerequisites, Step 1: Add Domain to Vercel, Step 2: Configure Namecheap DNS, Step 3: Add Vercel DNS Records, Step 4: Wait for Propagation, Step 5: Verify SSL Certificate, Step 6: Configure www Redirect (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.2
Nodes (9): code:bash (VITE_API_URL=https://your-railway-backend-url.up.railway.app), Next: Configure Custom Domain, Prerequisites, Step 1: Import GitHub Repository, Step 2: Configure Build Settings, Step 3: Add Environment Variable, Step 4: Deploy, Step 5: Test Frontend (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (6): _bcrypt_input(), get_password_hash(), verify_password(), authenticate(), create(), get_by_email()

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (3): delete(), _promote_next_default(), Make the oldest remaining CV the default after the previous default was deleted.

### Community 39 - "Community 39"
Cohesion: 0.22
Nodes (8): dagbag(), Ensures that there are no import errors in any of the DAG files., Ensures that the critical pipeline DAGs are actually loaded., Tests that no DAG contains a cycle (which would prevent it from running)., Loads the Airflow DagBag from the dags folder., test_dag_cycle_check(), test_dagbag_no_import_errors(), test_expected_dags_exist()

### Community 40 - "Community 40"
Cohesion: 0.25
Nodes (3): create_job_description(), extract_keywords(), Return the top *max_keywords* words by frequency from *text*.      Strips HTML,

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (5): ACCEPT, CVs(), formatBytes(), cvApi, CV

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (8): 7.12  GET /comparison, code:sql (SELECT), code:block30 (coverage = len(matched_skills) / max(len(resume_skills), 1)), code:json ({), Error Responses, Implementation Steps, Query Parameters, Response Example

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (6): CVPublic, CVSummary, CVUpdate, Returned in detail / upload responses — includes parsed text., Returned in detail / upload responses — includes parsed text., Returned in list responses — omits the large content field.

### Community 44 - "Community 44"
Cohesion: 0.38
Nodes (5): tailor_cv(), TailorCVRequest, TailorCVResponse, analyze_cv_match(), _keyword_match_score()

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (7): 7.4  GET /company-insights, code:sql (SELECT), code:json ({), Error Responses, Query Logic, Query Parameters, Response Example

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (7): 7.11  GET /salary-by-skill, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (7): 7.3  GET /hiring-patterns, code:sql (-- granularity = daily), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (7): 7.5  GET /job-market-health, code:sql (-- Query 1: totals from fct_job_postings), code:json ({), Error Responses, No query parameters., Query Logic, Response Example

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (7): 7.8  GET /industry-breakdown, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), Industry Derivation, No query parameters., Response Example, SQL Query Skeleton

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (6): 7.7  GET /location-trends, 7. Endpoint Specifications, code:json ({), No query parameters., Response Example, SQL Query

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (7): 7.6  GET /skill-demand, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 52 - "Community 52"
Cohesion: 0.29
Nodes (7): 7.1  GET /trending-skills, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (7): 7.2  GET /salary-insights, code:json ({), code:sql (-- Case B query skeleton), Error Responses, Query Logic, Query Parameters, Response Example

### Community 54 - "Community 54"
Cohesion: 0.4
Nodes (5): JobDescriptionCreate, JobDescriptionPublic, JobDescriptionSummary, List view — excludes the full description text., Detail view — includes full description text.

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (6): 7.10  GET /job-type-mix, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), No query parameters., Query Logic, Response Example

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): 7.9  GET /experience-levels, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), No query parameters., Query Logic, Response Example

### Community 57 - "Community 57"
Cohesion: 0.33
Nodes (5): code:bash (sh scripts/start-worker.sh), code:bash (celery -A app.tasks.celery_app worker --loglevel=info), Railway Celery Worker, Required Railway Services, Worker Start Command

### Community 59 - "Community 59"
Cohesion: 0.4
Nodes (3): UserCreate, UserPublic, UserUpdate

## Knowledge Gaps
- **347 isolated node(s):** `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.`, `Make the HTTP request(s) and return raw data for parse_response().`, `Convert raw API data into normalised job dicts.          Each dict must contain` (+342 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `login()` connect `Community 0` to `Community 5`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `TokenPair` connect `Community 5` to `Community 0`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `build_cache_key()` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `str` (e.g. with `extract_skills()` and `.parse_response()`) actually correct?**
  _`str` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `TailorStatus` (e.g. with `Base` and `TimestampMixin`) actually correct?**
  _`TailorStatus` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `TailorIntensity` (e.g. with `Base` and `TimestampMixin`) actually correct?**
  _`TailorIntensity` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.` to the rest of the system?**
  _347 weakly-connected nodes found - possible documentation gaps or missing edges._