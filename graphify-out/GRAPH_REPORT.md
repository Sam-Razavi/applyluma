# Graph Report - .  (2026-05-11)

## Corpus Check
- 155 files · ~56,969 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 650 nodes · 1019 edges · 63 communities (52 shown, 11 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 104 edges (avg confidence: 0.79)
- Token cost: 167,592 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Data Pipeline & Deployment Docs|Data Pipeline & Deployment Docs]]
- [[_COMMUNITY_Analytics API Endpoints|Analytics API Endpoints]]
- [[_COMMUNITY_Frontend API & Routing|Frontend API & Routing]]
- [[_COMMUNITY_Job Scraping & Airflow DAGs|Job Scraping & Airflow DAGs]]
- [[_COMMUNITY_Frontend Page Components|Frontend Page Components]]
- [[_COMMUNITY_Backend Test Fixtures|Backend Test Fixtures]]
- [[_COMMUNITY_Analytics Dashboard UI|Analytics Dashboard UI]]
- [[_COMMUNITY_Pydantic Schemas & Models|Pydantic Schemas & Models]]
- [[_COMMUNITY_SQLAlchemy Models & Routes|SQLAlchemy Models & Routes]]
- [[_COMMUNITY_Analytics Chart Components|Analytics Chart Components]]
- [[_COMMUNITY_Desktop Dashboard Screenshots|Desktop Dashboard Screenshots]]
- [[_COMMUNITY_Mobile Analytics UI|Mobile Analytics UI]]
- [[_COMMUNITY_Ultrawide Dashboard Screenshots|Ultrawide Dashboard Screenshots]]
- [[_COMMUNITY_Analytics Query Layer|Analytics Query Layer]]
- [[_COMMUNITY_Chart Components (HiringJobType)|Chart Components (Hiring/JobType)]]
- [[_COMMUNITY_Tablet Dashboard Screenshots|Tablet Dashboard Screenshots]]
- [[_COMMUNITY_JWT Authentication|JWT Authentication]]
- [[_COMMUNITY_Skill Chart Components|Skill Chart Components]]
- [[_COMMUNITY_CV Upload & Parsing|CV Upload & Parsing]]
- [[_COMMUNITY_KPI Card Components|KPI Card Components]]
- [[_COMMUNITY_Chart Card UI Components|Chart Card UI Components]]
- [[_COMMUNITY_FastAPI Route Config|FastAPI Route Config]]
- [[_COMMUNITY_CV Data Repository|CV Data Repository]]
- [[_COMMUNITY_Security & Password Hash|Security & Password Hash]]
- [[_COMMUNITY_Job Description API|Job Description API]]
- [[_COMMUNITY_Location Treemap Chart|Location Treemap Chart]]
- [[_COMMUNITY_CV Pydantic Schemas|CV Pydantic Schemas]]
- [[_COMMUNITY_Job Description Schemas|Job Description Schemas]]
- [[_COMMUNITY_Job Market Migration|Job Market Migration]]
- [[_COMMUNITY_Initial DB Migration|Initial DB Migration]]
- [[_COMMUNITY_CV Filename Migration|CV Filename Migration]]
- [[_COMMUNITY_JD Keywords Migration|JD Keywords Migration]]
- [[_COMMUNITY_Industry Breakdown Chart|Industry Breakdown Chart]]
- [[_COMMUNITY_App Settings Config|App Settings Config]]
- [[_COMMUNITY_Component Group (__init__.py)|Component Group (__init__.py)]]
- [[_COMMUNITY_Component Group (Make the HTTP request(s) and r)|Component Group (Make the HTTP request(s) and r)]]
- [[_COMMUNITY_Component Group (Convert raw API data into norm)|Component Group (Convert raw API data into norm)]]
- [[_COMMUNITY_Component Group (Minimal HTML tag removal — avo)|Component Group (Minimal HTML tag removal — avo)]]

## God Nodes (most connected - your core abstractions)
1. `Market Intelligence Page` - 18 edges
2. `Analytics Dashboard Mobile View` - 18 edges
3. `Market Intelligence Page` - 17 edges
4. `Analytics Dashboard - Tablet View Screenshot` - 16 edges
5. `safe_execute()` - 14 edges
6. `useAuthStore` - 14 edges
7. `formatNumber()` - 13 edges
8. `FakeDb` - 13 edges
9. `request()` - 13 edges
10. `dbt Data Transformer` - 13 edges

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

## Communities (63 total, 11 thin omitted)

### Community 0 - "Data Pipeline & Deployment Docs"
Cohesion: 0.07
Nodes (58): Adzuna API Integration (Job Search), analytics.agg_salary_insights (aggregate table), Apache Airflow DAG Orchestrator, Airflow Remote Connection Guide, Airflow Python Requirements, Alembic Database Migrations, Analytics API (/api/v1/analytics), Analytics Dashboard (12 Charts) (+50 more)

### Community 1 - "Analytics API Endpoints"
Cohesion: 0.06
Nodes (41): get_company_insights(), GET /analytics/company-insights - top companies by hiring volume., get_comparison(), GET /analytics/comparison - compare a resume to market trends., _salary_benchmark(), get_experience_levels(), GET /analytics/experience-levels - jobs by seniority., get_hiring_patterns() (+33 more)

### Community 2 - "Frontend API & Routing"
Cohesion: 0.07
Nodes (19): apiClient, ProtectedRoute(), config, NAV_LINKS, Navbar(), Dashboard(), QUICK_ACTIONS, STATS (+11 more)

### Community 3 - "Job Scraping & Airflow DAGs"
Cohesion: 0.08
Nodes (17): ABC, BaseScraper, extract_skills(), _extract_skills_from_text(), _get_db_conn_str(), scrape_remotive(), scrape_the_muse(), BaseScraper (+9 more)

### Community 4 - "Frontend Page Components"
Cohesion: 0.09
Nodes (19): ACCEPT, CVs(), formatBytes(), JobFormData, jobSchema, KEYWORD_COLORS, aiApi, analyticsApi (+11 more)

### Community 5 - "Backend Test Fixtures"
Cohesion: 0.12
Nodes (16): EndpointCase, FakeDb, FakeRedis, FakeResult, FakeRow, request(), test_comparison_cache_hit_with_authentication(), test_comparison_db_error_with_authentication() (+8 more)

### Community 6 - "Analytics Dashboard UI"
Cohesion: 0.08
Nodes (28): AnalyticsHeaderProps, Analytics(), AnalyticsSnapshot, applySettledResult(), chartFallback(), CompanyInsightsChart, emptyAnalyticsSnapshot(), ExperienceLevelsChart (+20 more)

### Community 7 - "Pydantic Schemas & Models"
Cohesion: 0.11
Nodes (26): BaseModel, AnalyticsResponse, CompanyInsight, ErrorDetail, ExperienceLevelBreakdown, HiringPatternPoint, IndustryBreakdown, JobMarketHealth (+18 more)

### Community 8 - "SQLAlchemy Models & Routes"
Cohesion: 0.15
Nodes (13): Base, Base, TimestampMixin, DeclarativeBase, tailor_cv(), TailorCVRequest, TailorCVResponse, CV (+5 more)

### Community 9 - "Analytics Chart Components"
Cohesion: 0.14
Nodes (11): Props, Props, Props, Props, ANALYTICS_COLORS, CHART_AXIS_TICK, CHART_TOOLTIP_STYLE, CompanyInsight (+3 more)

### Community 10 - "Desktop Dashboard Screenshots"
Cohesion: 0.13
Nodes (20): Analytics Dashboard - Desktop Screenshot, Empty State / No Data Available State, Experience Levels Chart, Hiring Patterns Chart, Industry Breakdown Chart, Job Type Mix Chart, KPI Cards Row, Last Updated Timestamp Indicator (+12 more)

### Community 11 - "Mobile Analytics UI"
Cohesion: 0.13
Nodes (20): analytics-colors.ts Color Constants, Analytics.tsx Dashboard Page, Analytics Dashboard Mobile View, Empty/No Data Available State Pattern, Experience Levels Chart, Hiring Patterns Chart (Line/Area Chart), Industry Breakdown Chart, Job Type Mix Chart (+12 more)

### Community 12 - "Ultrawide Dashboard Screenshots"
Cohesion: 0.19
Nodes (19): Analytics Dashboard - Ultrawide Screenshot, Experience Levels Chart, Hiring Patterns Chart, Industry Breakdown Chart, Job Type Mix Chart, KPI Cards Row (Total Jobs, Avg Salary, Companies, Remote, Growth), Location Trends Chart, Market Health Widget (+11 more)

### Community 13 - "Analytics Query Layer"
Cohesion: 0.14
Nodes (16): get_jobs_over_time(), get_overview(), get_recent_jobs(), get_top_companies(), get_top_skills(), Legacy analytics endpoints (Phase 1-5).  These endpoints query raw_job_posting, get_jobs_over_time(), get_overview() (+8 more)

### Community 14 - "Chart Components (Hiring/JobType)"
Cohesion: 0.15
Nodes (10): Props, Props, Props, HiringPatternPoint, JobTypeMixItem, SalaryInsightItem, formatCompactCurrency(), formatPeriod() (+2 more)

### Community 15 - "Tablet Dashboard Screenshots"
Cohesion: 0.16
Nodes (18): Empty/Loading State (No Data - Skeleton Charts), Experience Levels Chart (Tablet), Hiring Patterns Chart (Tablet), Industry Breakdown Chart (Tablet), Job Type Mix Chart (Tablet), KPI Cards Section (Tablet - Loading State), Location Trends Chart (Tablet), Market Intelligence Page Header (+10 more)

### Community 16 - "JWT Authentication"
Cohesion: 0.19
Nodes (13): create_access_token(), create_refresh_token(), login(), login_oauth2(), OAuth2-compatible form login — used by the Swagger UI 'Authorize' button., refresh(), Enum, build_cache_key() (+5 more)

### Community 17 - "Skill Chart Components"
Cohesion: 0.16
Nodes (10): Props, Props, CHART_DARK_AXIS_TICK, ErrorDetail, PaginatedResponse, ResponseMetadata, SalaryBySkill, SkillGap (+2 more)

### Community 18 - "CV Upload & Parsing"
Cohesion: 0.19
Nodes (6): _resolve_extension(), upload_cv(), parse_cv(), parse_docx(), parse_pdf(), Parse a CV file and return its text content.      Args:         file_path: Path

### Community 19 - "KPI Card Components"
Cohesion: 0.21
Nodes (11): formatValue(), ICONS, KPICard(), KPICardProps, KPIFormat, KPIIcon, JobMarketHealthCard(), Props (+3 more)

### Community 20 - "Chart Card UI Components"
Cohesion: 0.18
Nodes (3): ChartCardProps, EmptyStateProps, ErrorStateProps

### Community 22 - "CV Data Repository"
Cohesion: 0.25
Nodes (3): delete(), _promote_next_default(), Make the oldest remaining CV the default after the previous default was deleted.

### Community 23 - "Security & Password Hash"
Cohesion: 0.33
Nodes (6): _bcrypt_input(), get_password_hash(), verify_password(), authenticate(), create(), get_by_email()

### Community 24 - "Job Description API"
Cohesion: 0.25
Nodes (3): create_job_description(), extract_keywords(), Return the top *max_keywords* words by frequency from *text*.      Strips HTML,

### Community 25 - "Location Treemap Chart"
Cohesion: 0.29
Nodes (6): Props, TreemapTile(), TreemapTileProps, LOCATION_COLORS, LocationTrend, formatNumber()

### Community 26 - "CV Pydantic Schemas"
Cohesion: 0.4
Nodes (5): CVPublic, CVSummary, CVUpdate, Returned in detail / upload responses — includes parsed text., Returned in list responses — omits the large content field.

### Community 27 - "Job Description Schemas"
Cohesion: 0.4
Nodes (5): JobDescriptionCreate, JobDescriptionPublic, JobDescriptionSummary, List view — excludes the full description text., Detail view — includes full description text.

## Knowledge Gaps
- **145 isolated node(s):** `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.`, `Make the HTTP request(s) and return raw data for parse_response().`, `Convert raw API data into normalised job dicts.          Each dict must contain` (+140 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TokenPair` connect `JWT Authentication` to `Skill Chart Components`, `Frontend Page Components`?**
  _High betweenness centrality (0.226) - this node is a cross-community bridge._
- **Why does `build_cache_key()` connect `JWT Authentication` to `Analytics API Endpoints`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `str` (e.g. with `extract_skills()` and `.parse_response()`) actually correct?**
  _`str` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Market Intelligence Page` (e.g. with `Navigation Bar` and `Three-Column Grid Layout`) actually correct?**
  _`Market Intelligence Page` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Analytics Dashboard Mobile View` (e.g. with `Analytics.tsx Dashboard Page` and `analytics-colors.ts Color Constants`) actually correct?**
  _`Analytics Dashboard Mobile View` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Abstract base class for all job source scrapers.`, `Fetch, parse, and return a list of normalised job dicts.`, `Upsert jobs into raw_job_postings. Returns number of rows inserted.` to the rest of the system?**
  _145 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Data Pipeline & Deployment Docs` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._