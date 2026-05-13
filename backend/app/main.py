from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.batches import router as batches_router
from app.api.routes.configs import router as configs_router
from app.api.routes.extract import router as extract_router
from app.api.routes.graph import router as graph_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.api.routes.qa import router as qa_router
from app.api.routes.schema import router as schema_router
from app.api.routes.sources import router as sources_router
from app.api.routes.triples import router as triples_router
from app.core.database import Base, engine
from app.core.errors import AppError
from app.core.neo4j_client import close_driver
from app.core.sqlite_compat import ensure_sqlite_compatibility
from app.core.settings import settings
from app.models import sqlite_models  # noqa: F401
from app.utils.response_utils import fail


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_compatibility(engine)
    try:
        yield
    finally:
        close_driver()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(request, exc: AppError):
    del request
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.code, exc.message, exc.data),
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(request, exc: HTTPException):
    del request
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.status_code, str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request, exc: RequestValidationError):
    del request
    return JSONResponse(
        status_code=422,
        content=fail(4220, "VALIDATION_ERROR", exc.errors()),
    )


app.include_router(health_router)
app.include_router(configs_router)
app.include_router(projects_router)
app.include_router(batches_router)
app.include_router(extract_router)
app.include_router(sources_router)
app.include_router(triples_router)
app.include_router(schema_router)
app.include_router(graph_router)
app.include_router(qa_router)
