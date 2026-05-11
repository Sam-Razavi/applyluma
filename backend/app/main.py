from datetime import datetime
from typing import List

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute
from jose import JWTError, jwt

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cvs import router as cvs_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.dependencies import get_redis_client

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS configuration with Vercel preview URL support
static_origins: List[str] = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=static_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def analytics_rate_limit(request: Request, call_next):
    if request.url.path.startswith(("/api/v1/analytics", "/api/analytics")):
        auth = request.headers.get("authorization", "")
        identity = request.client.host if request.client else "unknown"
        if auth.lower().startswith("bearer "):
            try:
                payload = jwt.decode(auth.split(" ", 1)[1], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                if payload.get("type") == "access" and payload.get("sub"):
                    identity = str(payload["sub"])
            except JWTError:
                pass
        try:
            redis_client = get_redis_client()
            key = f"rate_limit:analytics:{identity}:{int(datetime.utcnow().timestamp() // 60)}"
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, 60)
            if count > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "data": None,
                        "metadata": None,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Rate limit exceeded",
                            "details": {"limit_per_minute": settings.RATE_LIMIT_PER_MINUTE},
                        },
                    },
                )
        except Exception:
            # Analytics endpoints are public; a Redis outage should not make
            # read-only market data unavailable.
            pass
    return await call_next(request)

app.include_router(api_router, prefix=settings.API_V1_STR)


compat_router = APIRouter(include_in_schema=False)

# Backwards-compatible aliases for previously documented endpoints. The
# canonical API remains /api/v1/*, but these routes keep older clients and
# health-check scripts working without duplicating endpoint implementations.
compat_router.include_router(auth_router, prefix="/api")
compat_router.include_router(analytics_router, prefix="/api")


def _include_prefixed_route_aliases(
    *,
    source_router: APIRouter,
    target_router: APIRouter,
    source_prefix: str,
    alias_prefix: str,
) -> None:
    for route in source_router.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith(source_prefix):
            continue

        alias_path = f"{alias_prefix}{route.path.removeprefix(source_prefix)}"
        target_router.add_api_route(
            alias_path,
            route.endpoint,
            methods=list(route.methods or []),
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            dependencies=route.dependencies,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            operation_id=route.operation_id,
            response_class=route.response_class,
            name=f"{route.name}_compat",
            callbacks=route.callbacks,
            openapi_extra=route.openapi_extra,
            include_in_schema=False,
        )


_include_prefixed_route_aliases(
    source_router=cvs_router,
    target_router=compat_router,
    source_prefix="/cvs",
    alias_prefix="/api/resumes",
)


@compat_router.get("/docs")
async def docs_alias() -> RedirectResponse:
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")


app.include_router(compat_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": settings.VERSION}
