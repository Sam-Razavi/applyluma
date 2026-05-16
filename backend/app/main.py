import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

import sentry_sdk
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute
from jose import JWTError, jwt
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.applications import router as applications_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.billing import router as billing_router
from app.api.v1.endpoints.cvs import router as cvs_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.job_search import router as job_search_router
from app.api.v1.endpoints.jobs import router as jobs_discovery_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.saved_jobs import router as saved_jobs_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.dependencies import get_redis_client
from app.core.logging_config import setup_logging

_INSECURE_DEFAULT_KEY = "change-me-in-production"
request_logger = logging.getLogger("app.requests")

setup_logging()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.SECRET_KEY == _INSECURE_DEFAULT_KEY:
        raise RuntimeError(
            "SECRET_KEY is not configured. "
            "Set the SECRET_KEY environment variable to a secure random value "
            "(e.g. openssl rand -hex 32) before starting the server."
        )
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration with Vercel preview URL support
static_origins: list[str] = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=static_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user_id_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(auth.split(" ", 1)[1], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") == "access" and payload.get("sub"):
        return str(payload["sub"])
    return None


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    user_id = _user_id_from_request(request)
    started = time.perf_counter()
    log_extra = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "duration_ms": None,
        "user_id": user_id,
    }
    request_logger.info("request_start", extra=log_extra)

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        request_logger.exception(
            "request_error",
            extra={**log_extra, "duration_ms": duration_ms},
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    request_logger.info(
        "request_end",
        extra={**log_extra, "duration_ms": duration_ms},
    )
    return response


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
app.include_router(applications_router, prefix=settings.API_V1_STR, tags=["applications"])
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(job_search_router, prefix=settings.API_V1_STR, tags=["jobs"])
app.include_router(jobs_discovery_router, prefix=settings.API_V1_STR, tags=["jobs-discovery"])
app.include_router(saved_jobs_router, prefix=settings.API_V1_STR, tags=["saved-jobs"])
app.include_router(billing_router, prefix=settings.API_V1_STR, tags=["billing"])
app.include_router(notifications_router, prefix=settings.API_V1_STR, tags=["notifications"])


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
    return {"status": "ok", "version": settings.VERSION}
