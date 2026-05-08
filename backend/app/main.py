from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cvs import router as cvs_router
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


compat_router = APIRouter(include_in_schema=False)

# Backwards-compatible aliases for previously documented endpoints. The
# canonical API remains /api/v1/*, but these routes keep older clients and
# health-check scripts working without duplicating endpoint implementations.
compat_router.include_router(auth_router, prefix="/api")


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
