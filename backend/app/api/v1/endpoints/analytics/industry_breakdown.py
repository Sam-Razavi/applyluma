"""GET /analytics/industry-breakdown - title-derived industry mix."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_redis_client
from app.db.queries.analytics_queries import (
    ANALYTICS_CACHE_TTL_SECONDS,
    build_cache_key,
    build_metadata,
    get_or_cache,
    ok_response,
    rows_to_dicts,
    safe_execute,
)
from app.schemas.analytics import AnalyticsResponse, IndustryBreakdown

router = APIRouter()


@router.get("/industry-breakdown", response_model=AnalyticsResponse[list[IndustryBreakdown]])
def get_industry_breakdown(
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[IndustryBreakdown]] | JSONResponse:
    def fetch() -> AnalyticsResponse[list[IndustryBreakdown]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings),
                    classified AS (
                        SELECT
                            CASE
                                WHEN normalised_title ~* '\\m(engineer|developer|programmer|software|backend|frontend|fullstack)\\M' THEN 'Software Engineering'
                                WHEN normalised_title ~* '\\m(data|analyst|analytics|scientist|machine learning|ml|ai|nlp)\\M' THEN 'Data & Analytics'
                                WHEN normalised_title ~* '\\m(devops|cloud|platform|infrastructure|sre|reliability|kubernetes|docker)\\M' THEN 'DevOps & Infrastructure'
                                WHEN normalised_title ~* '\\m(product manager|product owner|ux|ui|designer|design)\\M' THEN 'Product & Design'
                                WHEN normalised_title ~* '\\m(manager|director|head of|vp|cto|cio|chief)\\M' THEN 'Management & Leadership'
                                WHEN normalised_title ~* '\\m(finance|accountant|compliance|legal|counsel|risk)\\M' THEN 'Finance & Legal'
                                WHEN normalised_title ~* '\\m(sales|marketing|growth|seo|content|social media)\\M' THEN 'Sales & Marketing'
                                ELSE 'Other'
                            END AS industry,
                            salary_min,
                            salary_max,
                            remote_allowed
                        FROM analytics.fct_job_postings
                    )
                    SELECT
                        industry,
                        COUNT(*) AS job_count,
                        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT n FROM total), 0), 2) AS pct_of_total,
                        ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL)) AS avg_salary_min,
                        ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL)) AS avg_salary_max,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS remote_percentage
                    FROM classified
                    GROUP BY industry
                    ORDER BY job_count DESC
                """)
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("industry_breakdown"), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "analytics.fct_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
