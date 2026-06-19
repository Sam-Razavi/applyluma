import math
from typing import Any

import httpx

from app.schemas.job_search import AdzunaJobResult, JobSearchResponse

JOBTECH_SEARCH_URL = "https://jobsearch.api.jobtechdev.se/search"


def _empty_response(page: int) -> JobSearchResponse:
    return JobSearchResponse(results=[], count=0, page=page, total_pages=0)


def _map_result(hit: dict[str, Any]) -> AdzunaJobResult:
    employer = hit.get("employer") or {}
    workplace = hit.get("workplace_address") or {}

    desc_obj = hit.get("description") or {}
    if isinstance(desc_obj, dict):
        description = desc_obj.get("text") or desc_obj.get("text_formatted") or ""
    elif isinstance(desc_obj, str):
        description = desc_obj
    else:
        description = ""

    location = (
        workplace.get("city")
        or workplace.get("municipality")
        or workplace.get("region")
        or "Sweden"
    )

    job_id = str(hit.get("id", ""))
    webpage_url = hit.get("webpage_url") or (
        f"https://arbetsformedlingen.se/platsbanken/annonser/{job_id}"
        if job_id
        else ""
    )

    return AdzunaJobResult(
        id=job_id,
        title=hit.get("headline") or "Untitled role",
        company_name=employer.get("name") or "Unknown company",
        location=location,
        salary_min=None,
        salary_max=None,
        contract_type=None,
        redirect_url=webpage_url,
        description=description,
        created=hit.get("publication_date"),
        source="platsbanken",
    )


async def search_jobs(
    q: str,
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    offset = (page - 1) * results_per_page
    params: dict[str, Any] = {
        "q": f"{q} {location}".strip() if location else q,
        "limit": results_per_page,
        "offset": offset,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(JOBTECH_SEARCH_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError:
        return _empty_response(page)

    payload = response.json()
    count = int(payload.get("total", {}).get("value", 0))
    results = [
        _map_result(hit)
        for hit in payload.get("hits", [])
        if isinstance(hit, dict)
    ]
    total_pages = math.ceil(count / results_per_page) if count else 0
    return JobSearchResponse(results=results, count=count, page=page, total_pages=total_pages)
