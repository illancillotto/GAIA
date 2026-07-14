from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUserRole
from app.modules.gis.models import GisLayer, GisLayerPermission
from app.modules.gis.schemas import GisAccessLevel
from app.modules.gis.services import ACCESS_LEVEL_FLAGS


CATASTO_WORKSPACE = "catasto"
CATASTO_DOMAIN_MODULE = "catasto"


CATASTO_GIS_LAYER_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "cat_particelle_current",
        "title": "Particelle catastali correnti",
        "description": "Vista PostGIS operativa delle particelle Catasto pubblicata come vector tiles Martin.",
        "postgis_table": "cat_particelle_current",
        "geometry_type": "MULTIPOLYGON",
        "minzoom": 13,
        "maxzoom": 20,
        "primary_use": "parcel_lookup",
    },
    {
        "name": "cat_distretti",
        "title": "Distretti Catasto",
        "description": "Poligoni distretto dal dominio Catasto pubblicati come layer Martin.",
        "postgis_table": "cat_distretti",
        "geometry_type": "MULTIPOLYGON",
        "minzoom": 7,
        "maxzoom": 16,
        "primary_use": "district_context",
    },
    {
        "name": "cat_distretti_boundaries",
        "title": "Confini distretti Catasto",
        "description": "Confini distretto derivati dalle viste PostGIS Catasto e pubblicati come layer Martin.",
        "postgis_table": "cat_distretti_boundaries",
        "geometry_type": "MULTILINESTRING",
        "minzoom": 7,
        "maxzoom": 16,
        "primary_use": "district_boundaries",
    },
    {
        "name": "cat_delivery_points_current",
        "title": "Punti di consegna correnti",
        "description": "Punti di consegna Catasto correnti serviti da PostGIS e Martin.",
        "postgis_table": "cat_delivery_points_current",
        "geometry_type": "POINT",
        "minzoom": 11,
        "maxzoom": 20,
        "primary_use": "delivery_points",
    },
    {
        "name": "cat_irrigation_canals_current",
        "title": "Canali irrigui correnti",
        "description": "Canali irrigui Catasto correnti serviti da PostGIS e Martin.",
        "postgis_table": "cat_irrigation_canals_current",
        "geometry_type": "LINESTRING",
        "minzoom": 10,
        "maxzoom": 20,
        "primary_use": "irrigation_network",
    },
    {
        "name": "cat_dui_2026_current",
        "title": "DUI 2026 corrente",
        "description": "Layer DUI 2026 corrente materializzato in PostGIS e pubblicato come layer Martin.",
        "postgis_table": "cat_dui_2026_current",
        "geometry_type": "MULTIPOLYGON",
        "minzoom": 10,
        "maxzoom": 20,
        "primary_use": "dui_overlay",
    },
)


def _catasto_layer_metadata(definition: dict[str, Any]) -> dict[str, Any]:
    martin_layer_id = str(definition["name"])
    return {
        "catalog_seed": "catasto_martin_postgis",
        "read_only": True,
        "official_source": "postgis",
        "qgis": {
            "mode": "read_only",
            "connection": "postgis",
            "editable": False,
        },
        "tiles": {
            "provider": "martin",
            "format": "mvt",
            "layer_id": martin_layer_id,
            "minzoom": definition["minzoom"],
            "maxzoom": definition["maxzoom"],
        },
        "nas": {
            "role": "backup_export_only",
            "is_official_source": False,
        },
        "primary_use": definition["primary_use"],
    }


def _apply_catasto_layer_definition(layer: GisLayer, definition: dict[str, Any]) -> None:
    name = str(definition["name"])
    layer.workspace = CATASTO_WORKSPACE
    layer.name = name
    layer.title = str(definition["title"])
    layer.description = str(definition["description"])
    layer.domain_module = CATASTO_DOMAIN_MODULE
    layer.source_type = "postgis"
    layer.official_source = "postgis"
    layer.postgis_schema = "public"
    layer.postgis_table = str(definition["postgis_table"])
    layer.geometry_column = "geometry"
    layer.geometry_type = str(definition["geometry_type"])
    layer.srid = 4326
    layer.feature_id_column = "id"
    layer.martin_layer_id = name
    layer.ogc_service_url = None
    layer.qgis_project_path = None
    layer.nas_export_root = None
    layer.metadata_json = _catasto_layer_metadata(definition)
    layer.is_active = True


def _ensure_viewer_permission(db: Session, layer: GisLayer) -> None:
    permission = db.scalar(
        select(GisLayerPermission).where(
            GisLayerPermission.layer_id == layer.id,
            GisLayerPermission.principal_type == "role",
            GisLayerPermission.principal_key == ApplicationUserRole.VIEWER.value,
        )
    )
    if permission is None:
        permission = GisLayerPermission(
            layer_id=layer.id,
            principal_type="role",
            principal_key=ApplicationUserRole.VIEWER.value,
        )
        db.add(permission)

    flags = ACCESS_LEVEL_FLAGS[GisAccessLevel.viewer]
    permission.user_id = None
    permission.can_view = flags["can_view"]
    permission.can_annotate = flags["can_annotate"]
    permission.can_edit = flags["can_edit"]
    permission.can_approve = flags["can_approve"]
    permission.can_manage = flags["can_manage"]


def ensure_catasto_gis_catalog(db: Session) -> int:
    created = 0
    for definition in CATASTO_GIS_LAYER_DEFINITIONS:
        layer = db.scalar(
            select(GisLayer).where(
                GisLayer.workspace == CATASTO_WORKSPACE,
                GisLayer.name == definition["name"],
            )
        )
        if layer is None:
            layer = GisLayer(workspace=CATASTO_WORKSPACE, name=str(definition["name"]), title=str(definition["title"]))
            db.add(layer)
            db.flush()
            created += 1
        _apply_catasto_layer_definition(layer, definition)
        _ensure_viewer_permission(db, layer)

    db.commit()
    return created
