from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.ai import router as ai_router
from app.api.v1.endpoints.alert_preferences import router as alert_preferences_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.auth_google import router as auth_google_router
from app.api.v1.endpoints.contact import router as contact_router
from app.api.v1.endpoints.cover_letters import router as cover_letters_router
from app.api.v1.endpoints.cvs import router as cvs_router
from app.api.v1.endpoints.feedback import router as feedback_router
from app.api.v1.endpoints.job_descriptions import router as jd_router
from app.api.v1.endpoints.tailor import router as tailor_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(auth_google_router)
api_router.include_router(cvs_router)
api_router.include_router(jd_router)
api_router.include_router(ai_router)
api_router.include_router(analytics_router)
api_router.include_router(tailor_router)
api_router.include_router(alert_preferences_router)
api_router.include_router(cover_letters_router)
api_router.include_router(admin_router)
api_router.include_router(contact_router)
api_router.include_router(feedback_router)


@api_router.get("/ping", tags=["utils"])
async def ping() -> dict[str, str]:
    return {"message": "pong"}
