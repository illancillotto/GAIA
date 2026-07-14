from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUserRole
from app.modules.gis.models import GisLayer, GisLayerPermission
from app.modules.gis.schemas import GisAccessLevel
from app.modules.gis.services import ACCESS_LEVEL_FLAGS


CATASTO_WORKSPACE = "catasto"
CATASTO_DOMAIN_MODULE = "catasto"
RIORDINO_WORKSPACE = "riordino"
RIORDINO_DOMAIN_MODULE = "riordino"


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

RIORDINO_GIS_LAYER_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "riordino_gis_links",
        "title": "Link GIS pratiche Riordino",
        "description": (
            "Registro dominio Riordino che collega le pratiche a riferimenti layer/feature GIS esterni; "
            "non e un layer geometrico pubblicato."
        ),
        "registry_table": "riordino_gis_links",
        "primary_use": "practice_gis_reference",
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


def _riordino_layer_metadata(definition: dict[str, Any]) -> dict[str, Any]:
    registry_table = str(definition["registry_table"])
    return {
        "catalog_seed": "riordino_domain_registry",
        "read_only": True,
        "official_source": "riordino",
        "domain_boundary": "Riordino owns link CRUD; GIS Platform owns catalog visibility and permissions.",
        "registry": {
            "kind": "manual_feature_reference",
            "table": registry_table,
            "route_pattern": "/riordino/practices/{practice_id}/gis-links",
            "managed_by": "riordino",
        },
        "qgis": {
            "mode": "not_published",
            "editable": False,
        },
        "tiles": {
            "published": False,
            "reason": "non_geometric_domain_registry",
        },
        "export": {
            "shapefile": False,
            "reason": "non_geometric_domain_registry",
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


def _apply_riordino_layer_definition(layer: GisLayer, definition: dict[str, Any]) -> None:
    name = str(definition["name"])
    layer.workspace = RIORDINO_WORKSPACE
    layer.name = name
    layer.title = str(definition["title"])
    layer.description = str(definition["description"])
    layer.domain_module = RIORDINO_DOMAIN_MODULE
    layer.source_type = "domain_registry"
    layer.official_source = "riordino"
    layer.postgis_schema = None
    layer.postgis_table = str(definition["registry_table"])
    layer.geometry_column = None
    layer.geometry_type = None
    layer.srid = None
    layer.feature_id_column = "id"
    layer.martin_layer_id = None
    layer.ogc_service_url = None
    layer.qgis_project_path = None
    layer.nas_export_root = None
    layer.metadata_json = _riordino_layer_metadata(definition)
    layer.is_active = True


def _ensure_role_permission(db: Session, layer: GisLayer, role: ApplicationUserRole, access_level: GisAccessLevel) -> None:
    permission = db.scalar(
        select(GisLayerPermission).where(
            GisLayerPermission.layer_id == layer.id,
            GisLayerPermission.principal_type == "role",
            GisLayerPermission.principal_key == role.value,
        )
    )
    if permission is None:
        permission = GisLayerPermission(
            layer_id=layer.id,
            principal_type="role",
            principal_key=role.value,
        )
        db.add(permission)

    flags = ACCESS_LEVEL_FLAGS[access_level]
    permission.user_id = None
    permission.can_view = flags["can_view"]
    permission.can_annotate = flags["can_annotate"]
    permission.can_edit = flags["can_edit"]
    permission.can_approve = flags["can_approve"]
    permission.can_manage = flags["can_manage"]


def _ensure_layer_catalog(
    db: Session,
    *,
    workspace: str,
    definitions: tuple[dict[str, Any], ...],
    apply_definition: Callable[[GisLayer, dict[str, Any]], None],
) -> int:
    created = 0
    for definition in definitions:
        layer = db.scalar(
            select(GisLayer).where(
                GisLayer.workspace == workspace,
                GisLayer.name == definition["name"],
            )
        )
        if layer is None:
            layer = GisLayer(workspace=workspace, name=str(definition["name"]), title=str(definition["title"]))
            db.add(layer)
            db.flush()
            created += 1
        apply_definition(layer, definition)
        _ensure_role_permission(db, layer, ApplicationUserRole.VIEWER, GisAccessLevel.viewer)

    db.commit()
    return created


def ensure_catasto_gis_catalog(db: Session) -> int:
    return _ensure_layer_catalog(
        db,
        workspace=CATASTO_WORKSPACE,
        definitions=CATASTO_GIS_LAYER_DEFINITIONS,
        apply_definition=_apply_catasto_layer_definition,
    )


def ensure_riordino_gis_catalog(db: Session) -> int:
    return _ensure_layer_catalog(
        db,
        workspace=RIORDINO_WORKSPACE,
        definitions=RIORDINO_GIS_LAYER_DEFINITIONS,
        apply_definition=_apply_riordino_layer_definition,
    )


def ensure_gis_platform_catalog(db: Session) -> dict[str, int]:
    return {
        CATASTO_WORKSPACE: ensure_catasto_gis_catalog(db),
        RIORDINO_WORKSPACE: ensure_riordino_gis_catalog(db),
    }
