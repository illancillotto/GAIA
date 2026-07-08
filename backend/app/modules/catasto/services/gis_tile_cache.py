from __future__ import annotations

from datetime import datetime, timezone


DELIVERY_POINTS_TILE_LAYER = "cat_delivery_points_current"
IRRIGATION_CANALS_TILE_LAYER = "cat_irrigation_canals_current"


def generate_gis_tile_cache_revision() -> dict[str, object]:
    refreshed_at = datetime.now(timezone.utc)
    revision = refreshed_at.strftime("%Y%m%d%H%M%S%f")
    return {
        "tile_revision": revision,
        "refreshed_at": refreshed_at,
        "affected_layers": [DELIVERY_POINTS_TILE_LAYER, IRRIGATION_CANALS_TILE_LAYER],
        "message": "Cache GIS aggiornata. Ricaricare la mappa se e gia aperta.",
    }
