from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.config import settings
from app.modules.gis.models import GisLayer

PROJECT_FILENAME = "gaia-gis-platform.qgs"
ARCHIVE_FILENAME = "gaia-gis-platform.qgz"
CONNECTION_SERVICE = "gaia_gis"


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def is_project_layer(layer: GisLayer) -> bool:
    metadata = _mapping(layer.metadata_json)
    if layer.source_type in {"wms_external", "wfs_external"}:
        return (
            layer.is_active
            and layer.workspace == "territorio"
            and bool(_mapping(metadata.get("external")))
        )
    qgis = _mapping(metadata.get("qgis"))
    return (
        layer.is_active
        and layer.source_type == "postgis"
        and bool(layer.postgis_table or layer.name)
        and bool(layer.geometry_column)
        and qgis.get("mode") != "not_published"
    )


def layer_id(layer: GisLayer) -> str:
    return f"gaia_{layer.workspace}_{layer.name}_{str(layer.id).replace('-', '')}"


def geometry_kind(layer: GisLayer) -> str:
    geometry_type = (layer.geometry_type or "").lower()
    if "point" in geometry_type:
        return "Point"
    if "line" in geometry_type:
        return "Line"
    if "polygon" in geometry_type:
        return "Polygon"
    return "UnknownGeometry"


def _quote(value: str | int | None) -> str:
    return str(value or "").replace("\\", "\\\\").replace("'", "\\'")


def _external_datasource(layer: GisLayer, proxy_base_url: str) -> str:
    url = f"{proxy_base_url.rstrip('/')}/gis/external/{layer.id}/qgis-wms"
    return urlencode(
        {
            "authcfg": "gaia_oauth",
            "contextualWMSLegend": "0",
            "crs": f"EPSG:{layer.srid or 4326}",
            "format": "image/png",
            "layers": layer.name,
            "styles": "",
            "url": url,
        }
    )


def _postgis_datasource(layer: GisLayer) -> str:
    schema = _quote(layer.postgis_schema or "public")
    table = _quote(layer.postgis_table or layer.name)
    geometry_column = _quote(layer.geometry_column or "geometry")
    feature_id_column = _quote(layer.feature_id_column or "id")
    geometry_type = _quote(layer.geometry_type or "")
    return f"service='{CONNECTION_SERVICE}' key='{feature_id_column}' srid={layer.srid or 4326} type='{geometry_type}' table=\"{schema}\".\"{table}\" ({geometry_column}) sql="


def datasource(layer: GisLayer, proxy_base_url: str = "http://localhost:8000") -> str:
    if layer.source_type in {"wms_external", "wfs_external"}:
        return _external_datasource(layer, proxy_base_url)
    return _postgis_datasource(layer)


def manifest(
    layers: list[GisLayer], generated_at: datetime, proxy_base_url: str
) -> dict[str, Any]:
    return {
        "project": "GAIA GIS Platform",
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "connection_service": CONNECTION_SERVICE,
        "proxy_base_url": proxy_base_url,
        "policy": {
            "source": "postgis_and_gaia_proxy",
            "mode": "visible_read_only_layers",
            "excluded": ["postgis_staging", "domain_registry", "qgis.mode=not_published"],
        },
        "layers": [
            {
                "id": str(layer.id),
                "workspace": layer.workspace,
                "name": layer.name,
                "title": layer.title,
                "domain_module": layer.domain_module,
                "source_type": layer.source_type,
                "postgis_schema": layer.postgis_schema or "public",
                "postgis_table": layer.postgis_table or layer.name,
                "geometry_column": layer.geometry_column,
                "geometry_type": layer.geometry_type,
                "srid": layer.srid,
                "feature_id_column": layer.feature_id_column or "id",
            }
            for layer in layers
        ],
    }


def build_xml(
    layers: list[GisLayer],
    generated_at: datetime,
    proxy_base_url: str = "http://localhost:8000",
) -> bytes:
    root = ET.Element(
        "QGIS", attrib={"projectname": "GAIA GIS Platform", "version": "3.34.0"}
    )
    ET.SubElement(root, "title").text = "GAIA GIS Platform"
    ET.SubElement(root, "autotransaction").text = "0"
    ET.SubElement(root, "evaluateDefaultValues").text = "0"
    ET.SubElement(root, "trust", attrib={"active": "0"})
    properties = ET.SubElement(root, "properties")
    ET.SubElement(properties, "GeneratedAt").text = generated_at.astimezone(
        UTC
    ).isoformat()
    ET.SubElement(properties, "ConnectionService").text = CONNECTION_SERVICE
    tree = ET.SubElement(
        root,
        "layer-tree-group",
        attrib={"name": "GAIA GIS Platform", "checked": "Qt::Checked"},
    )
    groups: dict[str, ET.Element] = {}
    for layer in layers:
        group = (
            groups.setdefault(
                layer.workspace,
                ET.SubElement(
                    tree,
                    "layer-tree-group",
                    attrib={"name": layer.workspace, "checked": "Qt::Checked"},
                ),
            )
            if layer.workspace not in groups
            else groups[layer.workspace]
        )
        provider = (
            "wms"
            if layer.source_type in {"wms_external", "wfs_external"}
            else "postgres"
        )
        ET.SubElement(
            group,
            "layer-tree-layer",
            attrib={
                "id": layer_id(layer),
                "name": layer.title,
                "source": datasource(layer, proxy_base_url),
                "providerKey": provider,
                "checked": "Qt::Checked",
            },
        )
    project_layers = ET.SubElement(root, "projectlayers")
    for layer in layers:
        external = layer.source_type in {"wms_external", "wfs_external"}
        map_layer = ET.SubElement(
            project_layers,
            "maplayer",
            attrib={
                "type": "raster" if external else "vector",
                "geometry": "UnknownGeometry" if external else geometry_kind(layer),
                "styleCategories": "AllStyleCategories",
            },
        )
        ET.SubElement(map_layer, "id").text = layer_id(layer)
        ET.SubElement(map_layer, "datasource").text = datasource(layer, proxy_base_url)
        ET.SubElement(map_layer, "layername").text = layer.title
        ET.SubElement(map_layer, "provider", attrib={"encoding": "UTF-8"}).text = (
            "wms" if external else "postgres"
        )
        ET.SubElement(map_layer, "abstract").text = layer.description or ""
        ET.SubElement(
            map_layer, "keywordList"
        ).text = f"{layer.workspace},{layer.domain_module or ''},GAIA"
        srs = ET.SubElement(map_layer, "srs")
        ET.SubElement(srs, "spatialrefsys").text = f"EPSG:{layer.srid or 4326}"
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _readme(layer_count: int, generated_at: datetime) -> str:
    return (
        "GAIA GIS Platform - progetto QGIS unico\n\n"
        f"Generato: {generated_at.astimezone(UTC).isoformat()}\nLayer inclusi: {layer_count}\n"
        f"Connessione PostGIS attesa: service={CONNECTION_SERVICE}\n\n"
        "Configurare in QGIS l'autenticazione gaia_oauth per il proxy HTTPS GAIA. Il progetto non contiene token.\n"
        "I layer territoriali sono WMS in sola lettura e puntano esclusivamente al proxy GAIA.\n"
    )


def build_archive(
    layers: list[GisLayer],
    generated_at: datetime,
    proxy_base_url: str | None = None,
) -> bytes:
    resolved_base_url = proxy_base_url or settings.gis_qgis_proxy_base_url
    buffer = io.BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            PROJECT_FILENAME, build_xml(layers, generated_at, resolved_base_url)
        )
        archive.writestr("README_QGIS.txt", _readme(len(layers), generated_at))
        archive.writestr(
            "manifest.json",
            json.dumps(
                manifest(layers, generated_at, resolved_base_url),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
    return buffer.getvalue()
