from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Service healthcheck")
def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
        "environment": settings.app_env,
    }
