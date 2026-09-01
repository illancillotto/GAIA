from fastapi import HTTPException, status

from app.core.config import settings

EXTERNAL_LAYERS_DISABLED_MESSAGE = (
    "Consultazione territoriale non attiva in questo ambiente."
)
INTERROGAZIONE_DISABLED_MESSAGE = (
    "Interrogazione territoriale non attiva in questo ambiente."
)


def require_external_layers_enabled() -> None:
    if not settings.gis_external_layers_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=EXTERNAL_LAYERS_DISABLED_MESSAGE,
        )


def require_interrogazione_enabled() -> None:
    if not settings.gis_interrogazione_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=INTERROGAZIONE_DISABLED_MESSAGE,
        )
