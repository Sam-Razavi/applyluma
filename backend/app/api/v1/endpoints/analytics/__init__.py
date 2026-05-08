"""Analytics router package.

Exports a single ``router`` that combines:
  - Legacy routes (Phase 1-5, in legacy.py)
  - Phase 6 routes (one module per endpoint, implemented by Codex)

Import graph (Codex creates the leaf modules):

    analytics/
    ├── __init__.py          ← you are here
    ├── legacy.py            ← Phase 1-5 endpoints (raw table queries)
    ├── trending_skills.py   ← GET /trending-skills
    ├── salary_insights.py   ← GET /salary-insights
    ├── hiring_patterns.py   ← GET /hiring-patterns
    ├── company_insights.py  ← GET /company-insights
    ├── job_market_health.py ← GET /job-market-health
    ├── skill_demand.py      ← GET /skill-demand
    ├── location_trends.py   ← GET /location-trends
    ├── industry_breakdown.py← GET /industry-breakdown
    ├── experience_levels.py ← GET /experience-levels
    ├── job_type_mix.py      ← GET /job-type-mix
    ├── salary_by_skill.py   ← GET /salary-by-skill
    └── comparison.py        ← GET /comparison
"""
from fastapi import APIRouter

from .legacy import router as _legacy_router

# Phase 6 routers — imported once Codex creates these files
from .trending_skills import router as _trending_skills_router
from .salary_insights import router as _salary_insights_router
from .hiring_patterns import router as _hiring_patterns_router
from .company_insights import router as _company_insights_router
from .job_market_health import router as _job_market_health_router
from .skill_demand import router as _skill_demand_router
from .location_trends import router as _location_trends_router
from .industry_breakdown import router as _industry_breakdown_router
from .experience_levels import router as _experience_levels_router
from .job_type_mix import router as _job_type_mix_router
from .salary_by_skill import router as _salary_by_skill_router
from .comparison import router as _comparison_router

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Legacy endpoints (no prefix — they keep their /overview etc. paths)
router.include_router(_legacy_router)

# Phase 6 endpoints
router.include_router(_trending_skills_router)
router.include_router(_salary_insights_router)
router.include_router(_hiring_patterns_router)
router.include_router(_company_insights_router)
router.include_router(_job_market_health_router)
router.include_router(_skill_demand_router)
router.include_router(_location_trends_router)
router.include_router(_industry_breakdown_router)
router.include_router(_experience_levels_router)
router.include_router(_job_type_mix_router)
router.include_router(_salary_by_skill_router)
router.include_router(_comparison_router)
