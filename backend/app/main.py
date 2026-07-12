import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

import sentry_sdk
from fastapi import APIRouter, FastAPI, Query
from fastapi.exceptions import HTTPException as FastAPIHTTPException
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
from app.api.v1.endpoints.health import _check_db
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.job_bookmark import router as job_bookmark_router
from app.api.v1.endpoints.job_search import router as job_search_router
from app.api.v1.endpoints.jobs import router as jobs_discovery_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.saved_jobs import router as saved_jobs_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.dependencies import get_redis_client
from app.core.logging_config import setup_logging
from app.db.session import SessionLocal

_INSECURE_DEFAULT_KEY = "change-me-in-production"

_HTTP_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
}
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

@app.exception_handler(FastAPIHTTPException)
async def structured_http_exception_handler(request: Request, exc: FastAPIHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": _HTTP_ERROR_CODES.get(exc.status_code, "ERROR"),
        },
        headers=getattr(exc, "headers", None),
    )


# CORS configuration with Vercel preview URL support
static_origins: list[str] = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=static_origins,
    allow_origin_regex=r"https://applyluma-[a-z0-9][a-z0-9-]*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token", "X-Requested-With"],
    expose_headers=["X-Request-ID", "Retry-After"],
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
            request_logger.error("Redis error in analytics_rate_limit", exc_info=True)
    return await call_next(request)

# Per-IP rate limits (requests per minute) for unauthenticated auth endpoints.
# Keyed by exact path; compat aliases share the same limits.
_AUTH_RATE_LIMITS: dict[str, int] = {
    "/api/v1/auth/login": 10,
    "/api/v1/auth/token": 10,
    "/api/v1/auth/register": 5,
    "/api/v1/auth/resend-verification": 3,
    "/api/v1/auth/forgot-password": 5,
    "/api/v1/auth/reset-password": 10,
    "/api/v1/auth/refresh": 30,
    "/api/v1/auth/magic-link": 3,
    "/api/v1/auth/magic-link/verify": 10,
    "/api/auth/login": 10,
    "/api/auth/token": 10,
    "/api/auth/register": 5,
    "/api/auth/resend-verification": 3,
    "/api/auth/forgot-password": 5,
    "/api/auth/reset-password": 10,
    "/api/auth/refresh": 30,
    "/api/auth/magic-link": 3,
    "/api/auth/magic-link/verify": 10,
}


@app.middleware("http")
async def auth_rate_limit(request: Request, call_next):
    if request.method == "POST":
        limit = _AUTH_RATE_LIMITS.get(request.url.path)
        if limit is not None:
            ip = request.client.host if request.client else "unknown"
            minute = int(datetime.utcnow().timestamp() // 60)
            endpoint = request.url.path.rsplit("/", 1)[-1]
            key = f"rate_limit:auth:{endpoint}:{ip}:{minute}"
            try:
                redis_client = get_redis_client()
                count = redis_client.incr(key)
                if count == 1:
                    redis_client.expire(key, 60)
                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please try again later.",
                            "code": "TOO_MANY_REQUESTS",
                        },
                        headers={"Retry-After": "60"},
                    )
            except Exception:
                # fail open: a Redis outage must never lock users out
                request_logger.error("Redis error in auth_rate_limit", exc_info=True)
    return await call_next(request)


# Per-user rate limits for endpoints that trigger expensive operations (AI
# calls, file processing, external HTTP fetches).  Keyed by exact path; limits
# are per user ID when authenticated, falling back to client IP.
_EXPENSIVE_RATE_LIMITS: dict[str, int] = {
    "/api/v1/cvs/upload": 20,
    "/api/v1/tailor/submit": 5,
    "/api/v1/job-descriptions/scrape-url": 10,
    "/api/v1/cover-letters/generate": 5,
    "/api/v1/auth/change-password": 10,
    "/api/v1/auth/extension-token": 20,
    # Unauthenticated and sends two emails per request (one to a
    # caller-supplied address) — keep this tight.
    "/api/v1/contact": 3,
}


@app.middleware("http")
async def expensive_endpoint_rate_limit(request: Request, call_next):
    if request.method == "POST":
        limit = _EXPENSIVE_RATE_LIMITS.get(request.url.path)
        if limit is not None:
            identity = _user_id_from_request(request) or (
                request.client.host if request.client else "unknown"
            )
            minute = int(datetime.utcnow().timestamp() // 60)
            endpoint = request.url.path.rsplit("/", 1)[-1]
            key = f"rate_limit:expensive:{endpoint}:{identity}:{minute}"
            try:
                redis_client = get_redis_client()
                count = redis_client.incr(key)
                if count == 1:
                    redis_client.expire(key, 60)
                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please slow down.",
                            "code": "TOO_MANY_REQUESTS",
                        },
                        headers={"Retry-After": "60"},
                    )
            except Exception:
                request_logger.error("Redis error in expensive_endpoint_rate_limit", exc_info=True)
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["X-XSS-Protection"] = "0"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(applications_router, prefix=settings.API_V1_STR, tags=["applications"])
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(job_search_router, prefix=settings.API_V1_STR, tags=["jobs"])
app.include_router(jobs_discovery_router, prefix=settings.API_V1_STR, tags=["jobs-discovery"])
app.include_router(saved_jobs_router, prefix=settings.API_V1_STR, tags=["saved-jobs"])
app.include_router(billing_router, prefix=settings.API_V1_STR, tags=["billing"])
app.include_router(notifications_router, prefix=settings.API_V1_STR, tags=["notifications"])
app.include_router(job_bookmark_router, prefix=settings.API_V1_STR, tags=["job-bookmark"])


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


@app.get("/health", tags=["health"], response_model=None)
async def health_check(deep: bool = Query(False)) -> dict[str, str] | JSONResponse:
    if not deep:
        return {"status": "ok", "version": settings.VERSION}

    db = SessionLocal()
    try:
        check = _check_db(db)
    finally:
        db.close()

    if check["status"] != "ok":
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "version": settings.VERSION, "checks": {"db": check}},
        )
    return {"status": "ok", "version": settings.VERSION}
