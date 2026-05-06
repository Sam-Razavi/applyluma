from fastapi import APIRouter

from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cvs import router as cvs_router
from app.api.v1.endpoints.job_descriptions import router as jd_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(cvs_router)
api_router.include_router(jd_router)
api_router.include_router(ai_router)
api_router.include_router(analytics_router)


@api_router.get("/ping", tags=["utils"])
async def ping() -> dict[str, str]:
    return {"message": "pong"}
