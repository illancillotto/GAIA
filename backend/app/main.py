import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging
from app.models.section_permission import Section
from app.modules.gis.bootstrap import ensure_gis_platform_catalog
from app.modules.gis.territorio_bootstrap import ensure_territorio_gis_catalog
from app.scripts.bootstrap_sections import ensure_default_sections
from app.services.bootstrap_admin import ensure_bootstrap_admin

configure_logging()
logger = logging.getLogger(__name__)


def _ensure_gis_catalogs(db):
    created = ensure_gis_platform_catalog(db)
    if settings.gis_external_layers_enabled:
        created["territorio"] = ensure_territorio_gis_catalog(db)
    return created


def _ensure_bootstrap_admin_on_startup() -> None:
    try:
        if not inspect(engine).has_table("application_users"):
            logger.warning("Bootstrap admin skipped: table application_users not available yet")
            return
    except SQLAlchemyError as exc:
        logger.warning("Bootstrap admin skipped while checking schema availability: %s", exc)
        return

    db = SessionLocal()
    try:
        user, created = ensure_bootstrap_admin(db)
        logger.info(
            "Bootstrap admin ready on startup: username=%s created=%s role=%s",
            user.username,
            created,
            user.role,
        )
    finally:
        db.close()


def _ensure_sections_on_startup() -> None:
    try:
        if not inspect(engine).has_table("sections"):
            logger.warning("Sections bootstrap skipped: table sections not available yet")
            return
    except SQLAlchemyError as exc:
        logger.warning("Sections bootstrap skipped while checking schema availability: %s", exc)
        return

    db = SessionLocal()
    try:
        created = ensure_default_sections(db)
        total = db.query(Section).count()
        logger.info(
            "Sections bootstrap ready on startup: created=%s total=%s",
            created,
            total,
        )
    finally:
        db.close()


def _ensure_gis_catalog_on_startup() -> None:
    required_tables = {"gis_layers", "gis_layer_permissions"}
    try:
        inspector = inspect(engine)
        if not all(inspector.has_table(table_name) for table_name in required_tables):
            logger.warning("GIS catalog bootstrap skipped: GIS tables not available yet")
            return
    except SQLAlchemyError as exc:
        logger.warning("GIS catalog bootstrap skipped while checking schema availability: %s", exc)
        return

    db = SessionLocal()
    try:
        created = _ensure_gis_catalogs(db)
        logger.info("GIS catalog bootstrap ready on startup: layers_created=%s", created)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_bootstrap_admin_on_startup()
    _ensure_sections_on_startup()
    _ensure_gis_catalog_on_startup()
    yield

app = FastAPI(
    title=settings.project_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in settings.backend_cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
