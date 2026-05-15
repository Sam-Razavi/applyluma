import math

import httpx

from app.schemas.job_search import AdzunaJobResult, JobSearchResponse

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


def _empty_response(page: int) -> JobSearchResponse:
    return JobSearchResponse(results=[], count=0, page=page, total_pages=0)


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _map_result(raw: dict) -> AdzunaJobResult:
    company = raw.get("company") if isinstance(raw.get("company"), dict) else {}
    location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    return AdzunaJobResult(
        id=str(raw.get("id", "")),
        title=str(raw.get("title") or "Untitled role"),
        company_name=str(company.get("display_name") or "Unknown company"),
        location=str(location.get("display_name") or ""),
        salary_min=_to_int(raw.get("salary_min")),
        salary_max=_to_int(raw.get("salary_max")),
        contract_type=raw.get("contract_type"),
        redirect_url=str(raw.get("redirect_url") or ""),
        description=str(raw.get("description") or ""),
        created=raw.get("created"),
    )


async def search_jobs(
    q: str,
    location: str | None,
    page: int,
    results_per_page: int,
    country: str,
    app_id: str,
    app_key: str,
) -> JobSearchResponse:
    if not app_id or not app_key:
        return _empty_response(page)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{ADZUNA_BASE_URL}/{country}/search/{page}",
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": q,
                    "where": location or "",
                    "results_per_page": results_per_page,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return _empty_response(page)

    payload = response.json()
    count = int(payload.get("count") or 0)
    results = [
        _map_result(item)
        for item in payload.get("results", [])
        if isinstance(item, dict)
    ]
    total_pages = math.ceil(count / results_per_page) if count else 0
    return JobSearchResponse(results=results, count=count, page=page, total_pages=total_pages)
