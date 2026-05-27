from pydantic import BaseModel


class AdzunaJobResult(BaseModel):
    id: str
    title: str
    company_name: str
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    contract_type: str | None = None
    redirect_url: str
    description: str
    created: str | None = None


class JobSearchResponse(BaseModel):
    results: list[AdzunaJobResult]
    count: int
    page: int
    total_pages: int
