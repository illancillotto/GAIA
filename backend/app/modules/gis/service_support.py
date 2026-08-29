from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.modules.gis.models import GisLayer

DEFAULT_NAS_EXPORT_ROOT = "/volume1/Settore Catasto/ARCHIVIO/Backups/GAIA/gis"


def default_export_path(layer: GisLayer, version_label: str) -> str:
    export_root = (
        layer.nas_export_root
        or settings.gis_nas_health_path.strip()
        or DEFAULT_NAS_EXPORT_ROOT
    )
    return (
        f"{export_root.rstrip('/')}/{layer.workspace}/{layer.name}/{version_label}.zip"
    )


def feature_geometry(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
