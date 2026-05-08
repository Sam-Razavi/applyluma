---
## ⚠️ IMPORTANT: Read This First

**Health Check Status:** ✅ **COMPLETE** (May 8, 2026)

**Critical Issues Fixed:**
- ✅ Airflow postgres_default connection created
- ✅ Frontend recharts dependency installed
- ✅ API route compatibility layer added

**Current Phase:** Ready for Phase 6 (Analytics API)

**What's Working:**
- Backend API (FastAPI)
- Database (PostgreSQL with applyluma + airflow_db)
- Resume upload + AI analysis
- Airflow + dbt data pipeline (DAGs operational)
- Frontend (React + Vite)

**Known Minor Issues (Non-Blocking):**
- Scraper API credentials not configured (will add when needed)
- Empty job data (will populate when DAGs run)
- Airflow scheduler healthcheck timeout (cosmetic, doesn't affect functionality)

**You Can Now Proceed with Phase 6!**

---

# ApplyLuma Context Document

> This file is read by both Claude and Codex at the start of each session.
> It contains project context, constraints, and division of labor.
> Update this as the project evolves.

---

## Project Overview

**ApplyLuma** is an AI-powered job search and resume optimization platform.

- **Status:** Phase 5 complete (Airflow + dbt data pipeline)
- **Current Phase:** 6 - Analytics API
- **Tech Stack:** FastAPI, PostgreSQL, React, TypeScript, Airflow, dbt
- **Deployment:** Docker Compose (local), planned cloud deployment

---

## Current Architecture

### Backend Stack
- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 15 (two databases)
  - `applyluma` - application data (resumes, jobs, users)
  - `airflow_db` - Airflow metadata
- **Cache:** Redis (6379)
- **Queue:** Celery + Redis
- **Port:** 8000

### Frontend Stack
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite or Create React App
- **Port:** 3000

### Data Pipeline
- **Orchestration:** Apache Airflow
- **Transformations:** dbt (converts raw job data to analytics)
- **Port:** 8080 (Airflow UI)

### Database Structure (Relevant to Phase 6)

**Raw Tables (from scraping):**
- `raw_job_postings` - Adzuna API response (unprocessed)
- `raw_company_data` - Company info

**dbt Analytics Views (Phase 5 complete):**
- `analytics.job_postings` - Deduplicated, cleaned jobs
- `analytics.skill_frequency` - Top skills by count
- `analytics.salary_by_location` - Salary ranges
- `analytics.company_hiring_patterns` - Hiring trends
- `analytics.job_market_health` - Overall metrics

**Application Tables:**
- `users` - User accounts
- `resumes` - User resumes (multiple per user)
- `saved_jobs` - User-saved job postings

---

## Completed Work (What's Done)

✅ **Phase 1-4:** Core Features
- Job search via Adzuna API (with filters)
- Resume upload & storage
- Claude-powered resume analysis
- Job description management

✅ **Phase 5:** Data Engineering
- Airflow DAGs for daily job scraping
- dbt models for analytics layer
- Data quality framework (dedup, validation)
- Database separation (applyluma vs airflow_db)

---

## Phase 6: Analytics API (Current Focus)

### Goal
Build 12 RESTful endpoints that expose job market intelligence to the frontend.

### Core Requirements

#### 12 Required Endpoints

1. **GET /api/analytics/trending-skills**
   - Top 20 most demanded skills
   - Parameters: `limit=20`, `days_back=30`, `min_jobs=10`
   - Returns skill name, frequency, % of jobs, salary impact, trend

2. **GET /api/analytics/salary-insights**
   - Salary ranges by location and job title
   - Parameters: `location`, `job_title`, `experience_level`
   - Returns: min, max, median, percentiles

3. **GET /api/analytics/hiring-patterns**
   - Hiring trends over time (job postings per day)
   - Parameters: `days_back=90`, `granularity=daily|weekly|monthly`
   - Returns: time series of job count

4. **GET /api/analytics/company-insights**
   - Top 20 companies by hiring volume
   - Parameters: `limit=20`, `location`
   - Returns: company name, job count, avg salary, hiring velocity

5. **GET /api/analytics/job-market-health**
   - Overall market metrics
   - Parameters: none
   - Returns: total jobs, unique companies, avg salary, growth rate

6. **GET /api/analytics/skill-demand**
   - Skills with highest growth rate
   - Parameters: `limit=20`, `min_growth_pct=5`
   - Returns: skill, demand trend, salary trajectory

7. **GET /api/analytics/location-trends**
   - Hiring distribution by geography
   - Parameters: `level=country|state|city`
   - Returns: location, job count, % of total, salary range

8. **GET /api/analytics/industry-breakdown**
   - Jobs by industry/sector
   - Parameters: none
   - Returns: industry, job count, salary range

9. **GET /api/analytics/experience-levels**
   - Distribution of jobs by seniority
   - Parameters: none
   - Returns: level, count, % of total, salary ranges

10. **GET /api/analytics/job-type-mix**
    - Full-time vs contract vs remote breakdown
    - Parameters: none
    - Returns: type, count, % of total

11. **GET /api/analytics/salary-by-skill**
    - Average salary for each top 20 skill
    - Parameters: `limit=20`
    - Returns: skill, avg salary, salary range, job count

12. **GET /api/analytics/comparison**
    - Compare user's resume to market trends
    - Parameters: `resume_id`
    - Returns: skills match, salary benchmark, market demand for user's skills

#### Standard Response Format
```json
{
  "success": true,
  "data": [/* endpoint-specific data */],
  "metadata": {
    "timestamp": "2026-05-08T14:30:00Z",
    "data_freshness_hours": 24,
    "sample_size": 5000,
    "applied_filters": {},
    "next_update": "2026-05-09T02:00:00Z"
  },
  "error": null
}
```

#### Error Response Format
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_PARAMS",
    "message": "limit must be between 1 and 100",
    "details": {"limit": "must be between 1 and 100"}
  }
}
```

---

## Architecture Decisions

### Why Each Decision

**1. Separate Response Format**
- Consistent across all endpoints
- Frontend knows exactly what shape data is
- Easy to add pagination later

**2. Redis Caching (1-hour TTL)**
- Analytics queries are expensive (scan 50k+ rows)
- Data doesn't need to be real-time (1hr stale is OK)
- Adzuna API has rate limits; cache prevents repeated queries
- Saves database load

**3. Pagination on Analytics**
- Future: if trending-skills has 1000+ results
- Currently: limit to top 20-50 (no need for pagination yet)

**4. Authentication Check**
- All endpoints require valid user token
- Rate limiting: 100 requests/min per user
- (Implemented in middleware, not per-endpoint)

**5. SQLAlchemy over Raw SQL**
- Type-safe queries
- Automatic parameterization (prevents SQL injection)
- Easier to refactor later

---

## Database Queries

### Trending Skills (dbt view source)
```sql
-- analytics.skill_frequency (created by dbt in Phase 5)
SELECT 
  skill,
  COUNT(*) as frequency,
  COUNT(*) * 100.0 / (SELECT COUNT(*) FROM analytics.job_postings) as frequency_pct,
  AVG(salary) - (SELECT AVG(salary) FROM analytics.job_postings) as salary_impact,
  -- trend calculation: current 7d avg / previous 7d avg
FROM analytics.job_postings
WHERE posted_date >= NOW() - INTERVAL '30 days'
GROUP BY skill
HAVING COUNT(*) >= 10
ORDER BY frequency DESC
LIMIT 20;
```

### Salary by Location & Title
```sql
SELECT 
  location,
  job_title,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary) as p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY salary) as median,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary) as p75
FROM analytics.job_postings
WHERE salary > 0
GROUP BY location, job_title;
```

---

## File Ownership & Workflow

### Claude (Opus 4.7) Owns These Files:
```
backend/
├── api/v1/endpoints/analytics/SPEC.md          ← detailed design
├── api/v1/endpoints/__init__.py                ← route registration
├── models.py                                    ← Pydantic schemas
├── dependencies.py                              ← shared utilities
```

**Claude's Responsibilities:**
- ✅ Design API contracts (request/response shapes)
- ✅ Define Pydantic models for validation
- ✅ Write detailed SPEC.md for each endpoint
- ✅ Plan caching strategy
- ✅ Plan error handling approach
- ✅ Write OpenAPI documentation strings
- ✅ Ensure API follows REST best practices

### Codex (GPT-5.5) Owns These Files:
```
backend/
├── api/v1/endpoints/analytics/
│   ├── trending_skills.py
│   ├── salary_insights.py
│   ├── hiring_patterns.py
│   ├── company_insights.py
│   ├── job_market_health.py
│   ├── skill_demand.py
│   ├── location_trends.py
│   ├── industry_breakdown.py
│   ├── experience_levels.py
│   ├── job_type_mix.py
│   ├── salary_by_skill.py
│   └── comparison.py
├── tests/
│   └── test_analytics_endpoints.py
├── db/queries/
│   └── analytics_queries.py
```

**Codex's Responsibilities:**
- ✅ Implement all 12 endpoints following SPEC.md
- ✅ Write SQLAlchemy queries
- ✅ Implement Redis caching logic
- ✅ Add proper error handling (400, 404, 429, 500)
- ✅ Generate unit tests (5 test cases per endpoint)
- ✅ Test locally before committing
- ✅ Use Pydantic models from models.py

### You Own Everything Else:
- ✅ Code review (does it match SPEC?)
- ✅ Integration testing (do all 12 endpoints work?)
- ✅ Docker build & deployment
- ✅ Performance tuning
- ✅ Database optimization
- ✅ Merging branches
- ✅ Production deployment

---

## Git Workflow

### Branch Structure
```
main                                    # ← Production-ready code
├── claude/phase-6-design              # ← Claude's work (specs + models)
└── codex/phase-6-implementation       # ← Codex's work (implementations)
```

### Workflow Steps

**1. Claude Designs (You: `git checkout claude/phase-6-design`)**
   - Opens Claude Code
   - Reads this CLAUDE.md for context
   - Designs API contracts
   - Writes SPEC.md with examples
   - Defines Pydantic models
   - Commits to claude/phase-6-design branch
   - Signals Codex: "Ready for implementation"

**2. Codex Implements (You: `git checkout codex/phase-6-implementation`)**
   - Opens Codex
   - Reads SPEC.md to understand design
   - Implements all 12 endpoints
   - Generates tests
   - Runs: `pytest backend/tests/`
   - Commits to codex/phase-6-implementation branch
   - Signals You: "Implementation complete, ready for review"

**3. You Merge (You: `git checkout main`)**
   - Reviews both branches
   - Checks for conflicts (should be ZERO)
   - Merges claude/phase-6-design → main
   - Merges codex/phase-6-implementation → main
   - Tests locally: `docker-compose up`
   - Verifies endpoints: `curl http://localhost:8000/api/analytics/trending-skills`
   - Pushes to main
   - Deploys to staging/production

---

## Constraints & Gotchas

### Database Constraints
- ❌ Don't run analytics on raw_job_postings (can be 100k+ rows)
- ✅ Use dbt analytics views (pre-aggregated, fast)
- 🔄 Analytics views updated daily by dbt at 3 AM UTC

### API Rate Limits
- Adzuna API: 100 requests/day (handled by Airflow, not Phase 6)
- Your Analytics API: 100 requests/min per user (Redis rate limiter)
- Claude API: Token limits for resume comparison endpoint

### Performance
- Queries must complete in <500ms (API response time)
- If slow: implement caching or pre-compute aggregates
- Avoid COUNT(*) without WHERE clause on big tables

### Data Freshness
- Analytics are updated daily at 3 AM UTC (by dbt/Airflow)
- Users seeing data up to 24 hours old is acceptable
- Update metadata.data_freshness_hours in response

---

## Dependencies & Assumptions

### Must Be Complete Before Phase 6 Starts:
- ✅ PostgreSQL with applyluma DB
- ✅ dbt models creating analytics views
- ✅ Airflow scraping jobs daily (raw_job_postings populated)
- ✅ Redis configured and running
- ✅ FastAPI backend server running

### Env Variables Needed:
```bash
# database
DATABASE_URL=postgresql://user:pass@localhost:5432/applyluma

# cache
REDIS_URL=redis://localhost:6379/0

# rate limiting
RATE_LIMIT_PER_MINUTE=100

# analytics refresh schedule
ANALYTICS_CACHE_TTL_HOURS=1
```

---

## Testing Strategy

### Unit Tests (Codex writes these)
- Each endpoint has 5+ test cases
- Happy path (valid request)
- Invalid parameters
- Empty result set
- Database error handling
- Cache hit verification

**Run tests:**
```bash
pytest backend/tests/test_analytics_endpoints.py -v
```

### Integration Tests (You write these after merging)
- All 12 endpoints working together
- Data consistency across endpoints
- Cache behavior in production
- Rate limiting works

**Run integration tests:**
```bash
docker-compose up
pytest backend/tests/integration/test_analytics.py -v
```

---

## Success Criteria

Phase 6 is complete when:

- [x] 12 endpoints designed (Claude spec)
- [x] 12 endpoints implemented (Codex code)
- [x] All endpoints respond in <500ms
- [x] Unit tests: 100% pass rate
- [x] Integration tests: all pass
- [x] Cache behavior verified (1hr TTL)
- [x] Rate limiting verified (100 req/min)
- [x] Error handling verified (400, 404, 429, 500)
- [x] OpenAPI docs generated (/docs endpoint)
- [x] Merged to main branch
- [x] Ready for Phase 7 (dashboard)

---

## Timeline

- **Day 1:** Claude designs 12 endpoint specs (SPEC.md) - 2 hours
- **Day 1-2:** Codex implements 12 endpoints + tests - 3 hours
- **Day 2:** You review, test locally, merge - 1 hour
- **Total: 6 hours of work across 2 days**

---

## Next Phases (Preview)

### Phase 7: Analytics Dashboard
- Frontend: React dashboard with charts
- Claude designs UI/UX
- Codex builds React components with Recharts

### Phase 8: Resume Tailoring
- Auto-customize resume per job description
- Claude designs algorithm
- Codex builds implementation
- Integrated with Phase 6 analytics (use market data for recommendations)

---

## Questions Before Starting?

If Claude or Codex have questions:
1. Reread relevant section of this document
2. Check SPEC.md (if it exists)
3. Ask in your AI chat - don't deviate from plan

Good luck! 🚀
