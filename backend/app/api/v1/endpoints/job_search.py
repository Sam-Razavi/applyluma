from fastapi import APIRouter, Depends, Query
from redis import Redis

from app.core.config import settings
from app.core.dependencies import get_current_user, get_redis_client
from app.models.user import User
from app.schemas.job_search import JobSearchResponse
from app.services import adzuna_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

_CACHE_TTL_SECONDS = 600


def _cache_key(
    *,
    country: str,
    q: str,
    location: str | None,
    page: int,
    results_per_page: int,
) -> str:
    return f"adzuna:{country}:{q}:{location or ''}:{page}:{results_per_page}"


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    q: str = Query(..., min_length=1),
    location: str | None = None,
    page: int = Query(default=1, ge=1),
    results_per_page: int = Query(default=10, ge=1, le=50),
    country: str | None = None,
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
) -> JobSearchResponse:
    del current_user
    resolved_country = country or settings.ADZUNA_COUNTRY
    if not settings.ADZUNA_APP_ID:
        return JobSearchResponse(results=[], count=0, page=page, total_pages=0)

    key = _cache_key(
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

    response = await adzuna_service.search_jobs(
        q=q,
        location=location,
        page=page,
        results_per_page=results_per_page,
        country=resolved_country,
        app_id=settings.ADZUNA_APP_ID,
        app_key=settings.ADZUNA_API_KEY,
    )

    try:
        redis_client.setex(key, _CACHE_TTL_SECONDS, response.model_dump_json())
    except Exception:
        pass

    return response
