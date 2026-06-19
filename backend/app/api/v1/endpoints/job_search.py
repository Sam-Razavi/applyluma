import asyncio

from fastapi import APIRouter, Depends, Query
from redis import Redis

from app.core.config import settings
from app.core.dependencies import get_current_user, get_redis_client
from app.models.user import User
from app.schemas.job_search import JobSearchResponse
from app.services import adzuna_service, platsbanken_search_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

_CACHE_TTL_SECONDS = 600


def _cache_key(
    *,
    source: str,
    country: str,
    q: str,
    location: str | None,
    page: int,
    results_per_page: int,
) -> str:
    return f"jobsearch:{source}:{country}:{q}:{location or ''}:{page}:{results_per_page}"


def _merge_responses(
    adzuna: JobSearchResponse | BaseException,
    platsbanken: JobSearchResponse | BaseException,
    page: int,
) -> JobSearchResponse:
    results = []
    count = 0
    max_pages = 0

    if isinstance(adzuna, JobSearchResponse):
        results.extend(adzuna.results)
        count += adzuna.count
        max_pages = max(max_pages, adzuna.total_pages)

    if isinstance(platsbanken, JobSearchResponse):
        results.extend(platsbanken.results)
        count += platsbanken.count
        max_pages = max(max_pages, platsbanken.total_pages)

    return JobSearchResponse(results=results, count=count, page=page, total_pages=max_pages)


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    q: str = Query(..., min_length=1),
    location: str | None = None,
    page: int = Query(default=1, ge=1),
    results_per_page: int = Query(default=10, ge=1, le=50),
    country: str | None = None,
    source: str = Query(default="all", pattern="^(adzuna|platsbanken|all)$"),
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
) -> JobSearchResponse:
    del current_user
    resolved_country = country or settings.ADZUNA_COUNTRY

    key = _cache_key(
        source=source,
        country=resolved_country,
        q=q,
        location=location,
        page=page,
        results_per_page=results_per_page,
    )

    try:
        cached = redis_client.get(key)
        if cached:
            return JobSearchResponse.model_validate_json(cached)
    except Exception:
        cached = None

    if source == "platsbanken":
        response = await platsbanken_search_service.search_jobs(
            q=q, location=location, page=page, results_per_page=results_per_page,
        )
    elif source == "adzuna":
        if not settings.ADZUNA_APP_ID:
            response = JobSearchResponse(results=[], count=0, page=page, total_pages=0)
        else:
            response = await adzuna_service.search_jobs(
                q=q, location=location, page=page, results_per_page=results_per_page,
                country=resolved_country, app_id=settings.ADZUNA_APP_ID,
                app_key=settings.ADZUNA_API_KEY,
            )
    else:
        adzuna_coro = (
            adzuna_service.search_jobs(
                q=q, location=location, page=page, results_per_page=results_per_page,
                country=resolved_country, app_id=settings.ADZUNA_APP_ID,
                app_key=settings.ADZUNA_API_KEY,
            )
            if settings.ADZUNA_APP_ID
            else JobSearchResponse(results=[], count=0, page=page, total_pages=0)
        )
        platsbanken_coro = platsbanken_search_service.search_jobs(
            q=q, location=location, page=page, results_per_page=results_per_page,
        )

        if asyncio.iscoroutine(adzuna_coro):
            adzuna_result, platsbanken_result = await asyncio.gather(
                adzuna_coro, platsbanken_coro, return_exceptions=True,
            )
        else:
            adzuna_result = adzuna_coro
            platsbanken_result = await platsbanken_coro

        response = _merge_responses(adzuna_result, platsbanken_result, page)

    try:
        redis_client.setex(key, _CACHE_TTL_SECONDS, response.model_dump_json())
    except Exception:
        pass

    return response
