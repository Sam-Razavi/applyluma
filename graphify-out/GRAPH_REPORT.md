# Graph Report - applyluma  (2026-05-11)

## Corpus Check
- 156 files · ~59,937 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1078 nodes · 1551 edges · 96 communities (81 shown, 15 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `90acaed2`
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
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]

## God Nodes (most connected - your core abstractions)
1. `Market Intelligence Page` - 18 edges
2. `Analytics Dashboard Mobile View` - 18 edges
3. `TailorStatus` - 17 edges
4. `TailorIntensity` - 17 edges
5. `Market Intelligence Page` - 17 edges
6. `Analytics Dashboard - Tablet View Screenshot` - 16 edges
7. `ApplyLuma Production Testing Checklist` - 15 edges
8. `safe_execute()` - 14 edges
9. `useAuthStore` - 14 edges
10. `formatNumber()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Analytics Dashboard Mobile View` --references--> `analytics-colors.ts Color Constants`  [INFERRED]
  phase7-test-screenshots/mobile.png → frontend/src/styles/analytics-colors.ts
- `Airflow Remote Connection Guide` --semantically_similar_to--> `Phase 8: Connect Airflow to Railway PostgreSQL`  [INFERRED] [semantically similar]
  deployment/AIRFLOW_REMOTE.md → CLAUDE.md
- `Analytics Dashboard Mobile View` --implements--> `Analytics.tsx Dashboard Page`  [INFERRED]
  phase7-test-screenshots/mobile.png → frontend/src/pages/Analytics.tsx
- `Mobile Sidebar Navigation Menu` --implements--> `Analytics.tsx Dashboard Page`  [INFERRED]
  phase7-test-screenshots/mobile.png → frontend/src/pages/Analytics.tsx
- `KPI Summary Cards (Total Jobs, Avg Salary, Companies, Growth)` --implements--> `Analytics.tsx Dashboard Page`  [INFERRED]
  phase7-test-screenshots/mobile.png → frontend/src/pages/Analytics.tsx

## Hyperedges (group relationships)
- **End-to-End Data Pipeline: Airflow Scrapes to dbt Transforms to analytics views** — scrape_jobs_dag, raw_job_postings_table, transform_jobs_dag, dbt_transformer, dbt_analytics_views, fct_job_postings, dim_skills, dim_companies, fct_daily_metrics [EXTRACTED 1.00]
- **Production Stack: Railway Backend + Vercel Frontend + PostgreSQL + Redis** — railway_platform, vercel_platform, postgresql_db, redis_cache, fastapi_backend, react_frontend [EXTRACTED 1.00]
- **Analytics API Layer: Pydantic Schemas + SQL Queries + Redis Cache to 12 Endpoints** — analytics_api, pydantic_schemas, analytics_queries_py, redis_caching_strategy, analytics_response_format [EXTRACTED 1.00]
- **Analytics Chart Components** — desktop_trending_skills_chart, desktop_salary_insights_chart, desktop_top_companies_chart, desktop_hiring_patterns_chart, desktop_market_health_panel, desktop_skill_demand_growth_chart, desktop_location_trends_chart, desktop_industry_breakdown_chart, desktop_experience_levels_chart, desktop_job_type_mix_chart, desktop_salary_by_skill_chart, desktop_resume_vs_market_chart [EXTRACTED 1.00]
- **Charts Showing Empty State** — desktop_trending_skills_chart, desktop_salary_insights_chart, desktop_skill_demand_growth_chart, desktop_salary_by_skill_chart, desktop_empty_state [EXTRACTED 1.00]
- **KPI Metric Cards** — desktop_kpi_cards, desktop_market_health_panel, desktop_last_updated_indicator [INFERRED 0.85]
- **Charts Showing Empty/No Data State** — mobile_trending_skills_chart, mobile_salary_insights_chart, mobile_skill_demand_chart, mobile_salary_by_skill_chart [EXTRACTED 1.00]
- **Charts With Visible Data** — mobile_top_companies_chart, mobile_hiring_patterns_chart, mobile_market_health_card, mobile_location_trends_chart [EXTRACTED 1.00]
- **Mobile Single-Column Dashboard Layout System** — mobile_analytics_dashboard, mobile_single_column_layout, mobile_kpi_cards, mobile_navbar, mobile_sidebar_menu [EXTRACTED 1.00]
- **All Analytics Charts Rendered in Tablet Layout** — tablet_trending_skills, tablet_salary_insights, tablet_top_companies, tablet_hiring_patterns, tablet_skill_demand_growth, tablet_location_trends, tablet_industry_breakdown, tablet_experience_levels, tablet_job_type_mix, tablet_salary_by_skill, tablet_resume_vs_market [EXTRACTED 1.00]
- **All Chart Components in Network Error State** — ultrawide_trending_skills_chart, ultrawide_salary_insights_chart, ultrawide_top_companies_chart, ultrawide_market_health_widget, ultrawide_skill_demand_growth_chart, ultrawide_location_trends_chart, ultrawide_industry_breakdown_chart, ultrawide_experience_levels_chart, ultrawide_job_type_mix_chart, ultrawide_salary_by_skill_chart, ultrawide_kpi_cards, ultrawide_network_error_state [EXTRACTED 1.00]
- **Three-Column Chart Grid Layout** — ultrawide_trending_skills_chart, ultrawide_salary_insights_chart, ultrawide_top_companies_chart, ultrawide_skill_demand_growth_chart, ultrawide_location_trends_chart, ultrawide_industry_breakdown_chart, ultrawide_experience_levels_chart, ultrawide_job_type_mix_chart, ultrawide_salary_by_skill_chart, ultrawide_three_col_grid_layout [EXTRACTED 1.00]

## Communities (96 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (40): _bcrypt_input(), create_access_token(), create_refresh_token(), get_password_hash(), verify_password(), authenticate(), create(), get_by_email() (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (56): Adzuna API Integration (Job Search), analytics.agg_salary_insights (aggregate table), Apache Airflow DAG Orchestrator, Airflow Remote Connection Guide, Airflow Python Requirements, Alembic Database Migrations, Analytics API (/api/v1/analytics), Analytics Dashboard (12 Charts) (+48 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (41): get_company_insights(), GET /analytics/company-insights - top companies by hiring volume., get_comparison(), GET /analytics/comparison - compare a resume to market trends., _salary_benchmark(), get_experience_levels(), GET /analytics/experience-levels - jobs by seniority., get_hiring_patterns() (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (31): formatValue(), ICONS, KPICard(), KPICardProps, KPIFormat, KPIIcon, Props, Props (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (24): PreviewStepProps, SelectorProps, SelectStepProps, Step, aiApi, tailorApi, IntensitySelector(), OPTIONS (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (17): ABC, BaseScraper, extract_skills(), _extract_skills_from_text(), _get_db_conn_str(), scrape_remotive(), scrape_the_muse(), BaseScraper (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.1
Nodes (17): ProtectedRoute(), NAV_LINKS, Navbar(), Dashboard(), QUICK_ACTIONS, STATS, FormData, Login() (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (16): EndpointCase, FakeDb, FakeRedis, FakeResult, FakeRow, request(), test_comparison_cache_hit_with_authentication(), test_comparison_db_error_with_authentication() (+8 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (28): AnalyticsHeaderProps, Analytics(), AnalyticsSnapshot, applySettledResult(), chartFallback(), CompanyInsightsChart, emptyAnalyticsSnapshot(), ExperienceLevelsChart (+20 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (25): JobMarketHealthCard(), Props, Props, analyticsApi, LoginRequest, RegisterRequest, AnalyticsEnvelope, CompanyInsight (+17 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (24): BaseModel, ok_response(), AnalyticsResponse, CompanyInsight, ErrorDetail, ExperienceLevelBreakdown, HiringPatternPoint, IndustryBreakdown (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (23): 10. Testing Requirements, 1. Overview, 2. Database Tables (dbt Analytics Schema), 3. Standard Response Envelope, 4. Pydantic Models, 5. Error Codes Reference, 6. Shared Implementation Utilities, 8. File Structure Summary (Codex creates) (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (23): code:bash (AIRFLOW_POSTGRES_CONN_HOST=<railway-host>), code:bash (docker-compose down), code:bash (docker-compose up -d), code:bash (docker-compose up -d), code:bash (./docker/start-airflow-railway.sh), code:bash (./docker/verify-railway-connection.sh), code:bash (docker-compose exec airflow-webserver airflow dags trigger s), code:bash (docker-compose exec airflow-webserver airflow dags trigger t) (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (15): Base, Base, TimestampMixin, DeclarativeBase, CV, JobDescription, TailorJob, User (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (15): cv(), FakeDb, jd(), preview_result(), request(), tailor_job(), test_preview_requires_completed_job(), test_preview_returns_completed_result() (+7 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (20): Analytics Dashboard - Desktop Screenshot, Empty State / No Data Available State, Experience Levels Chart, Hiring Patterns Chart, Industry Breakdown Chart, Job Type Mix Chart, KPI Cards Row, Last Updated Timestamp Indicator (+12 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (20): analytics-colors.ts Color Constants, Analytics.tsx Dashboard Page, Analytics Dashboard Mobile View, Empty/No Data Available State Pattern, Experience Levels Chart, Hiring Patterns Chart (Line/Area Chart), Industry Breakdown Chart, Job Type Mix Chart (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (19): ApplyLuma, code:bash (git checkout dev), code:bash (docker-compose up), code:bash (cd backend), code:bash (cd frontend), code:bash (./docker/start-airflow-railway.sh), code:bash (curl https://applyluma-production.up.railway.app/api/v1/anal), code:text (applyluma/) (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (19): Analytics Dashboard - Ultrawide Screenshot, Experience Levels Chart, Hiring Patterns Chart, Industry Breakdown Chart, Job Type Mix Chart, KPI Cards Row (Total Jobs, Avg Salary, Companies, Remote, Growth), Location Trends Chart, Market Health Widget (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (16): get_jobs_over_time(), get_overview(), get_recent_jobs(), get_top_companies(), get_top_skills(), Legacy analytics endpoints (Phase 1-5).  These endpoints query raw_job_posting, get_jobs_over_time(), get_overview() (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (17): Before Merging to Main, Branch Strategy, code:bash (git checkout dev), code:bash (git checkout -b feature/your-feature-name), code:bash (git add .), code:bash (git push origin feature/your-feature-name), code:bash (git checkout dev), code:bash (git checkout main) (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (17): code:yaml (AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://user:password@rai), code:sql (SELECT COUNT(*) FROM raw_job_postings;), code:python (schedule_interval = "0 2 * * *"  # 2 AM UTC daily), Connect Airflow to Railway Production Database, Option A: Via Airflow UI, Option B: Via Environment Variable, Overview, Prerequisites (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (18): Empty/Loading State (No Data - Skeleton Charts), Experience Levels Chart (Tablet), Hiring Patterns Chart (Tablet), Industry Breakdown Chart (Tablet), Job Type Mix Chart (Tablet), KPI Cards Section (Tablet - Loading State), Location Trends Chart (Tablet), Market Intelligence Page Header (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (16): 1. Visual Design Compliance, 2. Functional Testing, 3. Responsive Design, 4. Performance, 5. Error Handling, 6. Accessibility, 7. Cross-Browser, Console Errors (+8 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (15): code:bash (DATABASE_URL=<from Step 2>), code:bash (alembic upgrade head), code:text (https://your-backend-url.up.railway.app/health), code:json ({"status":"healthy","version":"0.1.0"}), code:text (https://your-backend-url.up.railway.app/docs), Prerequisites, Railway Backend Deployment Guide, Step 1: Create New Railway Project (+7 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (15): AI Resume Analysis, Analytics Dashboard, ApplyLuma Production Testing Checklist, Authentication, Backend Health Checks, Bugs Found, Cross-Browser Testing, Data Pipeline (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): AI Development Guidelines, ApplyLuma AI Context, Current Phase, Deployment, Environment Variables, Git Workflow, Key Files, Known Issues (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.37
Nodes (11): TailorIntensity, TailorStatus, TailorJobPublic, TailorMeta, TailorPreviewResponse, TailorSaveRequest, TailorSaveResponse, TailorSection (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (11): Adding a new model, ApplyLuma dbt Project (`applyluma_dw`), code:block1 (public.raw_job_postings  (source)), code:bash (cd dbt), Environment variables, `extract_skills(column_name)`, Macros, Materialisation strategy (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (3): ChartCardProps, EmptyStateProps, ErrorStateProps

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (10): Analytics Tables, API Endpoint Verification, Caveats, Dashboard Verification, Next Steps, Phase 8 Execution Report - Railway Database Population, Production Impact, Scraping Results (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.2
Nodes (6): JobFormData, jobSchema, KEYWORD_COLORS, CreateJobDescriptionRequest, jobApi, JobDescription

### Community 34 - "Community 34"
Cohesion: 0.2
Nodes (9): ApplyLuma Health Check Report, code:bash (airflow connections add postgres_default \), code:bash (docker-compose exec frontend npm install), Commands Run, Critical Issues, Recommendations, Summary, Test Artifacts Created (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.2
Nodes (9): Namecheap DNS Configuration for applyluma.com, Prerequisites, Step 1: Add Domain to Vercel, Step 2: Configure Namecheap DNS, Step 3: Add Vercel DNS Records, Step 4: Wait for Propagation, Step 5: Verify SSL Certificate, Step 6: Configure www Redirect (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.2
Nodes (9): code:bash (VITE_API_URL=https://your-railway-backend-url.up.railway.app), Next: Configure Custom Domain, Prerequisites, Step 1: Import GitHub Repository, Step 2: Configure Build Settings, Step 3: Add Environment Variable, Step 4: Deploy, Step 5: Test Frontend (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (3): delete(), _promote_next_default(), Make the oldest remaining CV the default after the previous default was deleted.

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (3): create_job_description(), extract_keywords(), Return the top *max_keywords* words by frequency from *text*.      Strips HTML,

### Community 39 - "Community 39"
Cohesion: 0.29
Nodes (5): ACCEPT, CVs(), formatBytes(), cvApi, CV

### Community 40 - "Community 40"
Cohesion: 0.25
Nodes (8): 7.12  GET /comparison, code:sql (SELECT), code:block30 (coverage = len(matched_skills) / max(len(resume_skills), 1)), code:json ({), Error Responses, Implementation Steps, Query Parameters, Response Example

### Community 41 - "Community 41"
Cohesion: 0.33
Nodes (6): CVPublic, CVSummary, CVUpdate, Returned in detail / upload responses — includes parsed text., Returned in detail / upload responses — includes parsed text., Returned in list responses — omits the large content field.

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (7): 7.6  GET /skill-demand, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (7): 7.4  GET /company-insights, code:sql (SELECT), code:json ({), Error Responses, Query Logic, Query Parameters, Response Example

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (7): 7.5  GET /job-market-health, code:sql (-- Query 1: totals from fct_job_postings), code:json ({), Error Responses, No query parameters., Query Logic, Response Example

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (7): 7.8  GET /industry-breakdown, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), Industry Derivation, No query parameters., Response Example, SQL Query Skeleton

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (7): 7.1  GET /trending-skills, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (7): 7.11  GET /salary-by-skill, code:sql (SELECT), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (7): 7.3  GET /hiring-patterns, code:sql (-- granularity = daily), code:json ({), Error Responses, Query Parameters, Response Example, SQL Query

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (7): 7.2  GET /salary-insights, code:json ({), code:sql (-- Case B query skeleton), Error Responses, Query Logic, Query Parameters, Response Example

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (6): 7.7  GET /location-trends, 7. Endpoint Specifications, code:json ({), No query parameters., Response Example, SQL Query

### Community 52 - "Community 52"
Cohesion: 0.4
Nodes (5): JobDescriptionCreate, JobDescriptionPublic, JobDescriptionSummary, List view — excludes the full description text., Detail view — includes full description text.

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (6): 7.10  GET /job-type-mix, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), No query parameters., Query Logic, Response Example

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (6): 7.9  GET /experience-levels, code:sql (WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_p), code:json ({), No query parameters., Query Logic, Response Example

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (5): code:bash (sh scripts/start-worker.sh), code:bash (celery -A app.tasks.celery_app worker --loglevel=info), Railway Celery Worker, Required Railway Services, Worker Start Command

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (3): _detect_language(), CV tailoring service: calls OpenAI and returns a structured section-by-section d, tailor_cv()

## Knowledge Gaps
- **368 isolated node(s):** `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.`, `Make the HTTP request(s) and return raw data for parse_response().`, `Convert raw API data into normalised job dicts.          Each dict must contain` (+363 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TokenPair` connect `Community 0` to `Community 9`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `build_cache_key()` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `str` (e.g. with `extract_skills()` and `.parse_response()`) actually correct?**
  _`str` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Market Intelligence Page` (e.g. with `Navigation Bar` and `Three-Column Grid Layout`) actually correct?**
  _`Market Intelligence Page` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Analytics Dashboard Mobile View` (e.g. with `Analytics.tsx Dashboard Page` and `analytics-colors.ts Color Constants`) actually correct?**
  _`Analytics Dashboard Mobile View` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `TailorStatus` (e.g. with `Base` and `TimestampMixin`) actually correct?**
  _`TailorStatus` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.` to the rest of the system?**
  _368 weakly-connected nodes found - possible documentation gaps or missing edges._