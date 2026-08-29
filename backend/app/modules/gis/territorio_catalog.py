from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.models import GisLayer
from app.modules.gis.schemas import (
    GisTerritorioLayer,
    GisTerritorioLayerGroup,
    GisTerritorioLayerListResponse,
)

THEME_LABELS = {
    "bonifica": "Bonifica e comprensori",
    "colture": "Colture e uso del suolo",
    "pericolosita": "Pericolosita",
    "vincoli": "Vincoli e tutele",
    "idrografia": "Acque e reticolo idrografico",
    "amministrativo": "Confini amministrativi",
    "eventi": "Eventi territoriali",
    "catasto_ufficiale": "Cartografia catastale ufficiale",
    "ortofoto": "Ortofoto storiche",
    "morfologia": "Morfologia del terreno",
}


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _client_layer(layer: GisLayer) -> GisTerritorioLayer:
    metadata = _mapping(layer.metadata_json)
    external = _mapping(metadata.get("external"))
    return GisTerritorioLayer(
        id=layer.id,
        name=layer.name,
        title=layer.title,
        description=layer.description,
        theme=str(metadata["theme"]),
        source=layer.official_source,
        proxy_wms_url=f"/gis/external/{layer.id}/wms",
        legend_url=f"/gis/external/{layer.id}/wms?request=GetLegendGraphic",
        default_opacity=float(metadata.get("default_opacity", 0.65)),
        render_order=int(metadata.get("render_order", 0)),
        queryable=str(external["queryable"]),
        attribution=str(external["attribution"]),
    )


def list_territorio_layers(
    db: Session, current_user: ApplicationUser
) -> GisTerritorioLayerListResponse:
    layers = db.scalars(
        select(GisLayer)
        .where(
            GisLayer.workspace == "territorio",
            GisLayer.is_active.is_(True),
        )
        .order_by(GisLayer.title.asc(), GisLayer.name.asc())
    ).all()
    grouped: dict[str, list[GisTerritorioLayer]] = defaultdict(list)
    for layer in layers:
        if not services._permission_flags(db, layer.id, current_user)["can_view"]:
            continue
        item = _client_layer(layer)
        grouped[item.theme].append(item)

    groups = [
        GisTerritorioLayerGroup(
            theme=theme,
            label=THEME_LABELS.get(theme, theme.replace("_", " ").title()),
            layers=sorted(items, key=lambda item: (item.render_order, item.title)),
        )
        for theme, items in grouped.items()
    ]
    groups.sort(key=lambda group: min(item.render_order for item in group.layers))
    return GisTerritorioLayerListResponse(
        groups=groups,
        total=sum(len(group.layers) for group in groups),
    )
