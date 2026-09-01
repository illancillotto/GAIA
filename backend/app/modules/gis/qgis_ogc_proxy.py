from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.gis import qgis_project, services
from app.modules.gis.models import GisLayer

_OPERATIONS = {
    "wms": {
        "getcapabilities": "GetCapabilities",
        "getmap": "GetMap",
    },
    "wfs": {
        "getcapabilities": "GetCapabilities",
        "getfeature": "GetFeature",
    },
}
_DEFAULT_VERSIONS = {"wms": "1.3.0", "wfs": "2.0.0"}
_ALLOWED_VERSIONS = {
    "wms": {"1.1.1", "1.3.0"},
    "wfs": {"1.1.0", "2.0.0"},
}
_PARAMS = {
    "GetCapabilities": {
        "acceptversions": "ACCEPTVERSIONS",
        "sections": "SECTIONS",
        "updatesequence": "UPDATESEQUENCE",
        "acceptformats": "ACCEPTFORMATS",
    },
    "GetMap": {
        "bbox": "BBOX",
        "crs": "CRS",
        "srs": "SRS",
        "width": "WIDTH",
        "height": "HEIGHT",
        "styles": "STYLES",
        "format": "FORMAT",
        "transparent": "TRANSPARENT",
        "bgcolor": "BGCOLOR",
        "exceptions": "EXCEPTIONS",
        "dpi": "DPI",
        "map_resolution": "MAP_RESOLUTION",
        "format_options": "FORMAT_OPTIONS",
    },
    "GetFeature": {
        "outputformat": "OUTPUTFORMAT",
        "count": "COUNT",
        "maxfeatures": "MAXFEATURES",
        "startindex": "STARTINDEX",
        "bbox": "BBOX",
        "srsname": "SRSNAME",
        "filter": "FILTER",
        "cql_filter": "CQL_FILTER",
        "propertyname": "PROPERTYNAME",
        "sortby": "SORTBY",
        "resulttype": "RESULTTYPE",
    },
}
_CONTROLLED_PARAMS = {
    "service",
    "version",
    "layers",
    "layer",
    "query_layers",
    "typename",
    "typenames",
    "map",
    "url",
}
_INTEGER_LIMITS = {
    "WIDTH": 4096,
    "HEIGHT": 4096,
    "COUNT": 10_000,
    "MAXFEATURES": 10_000,
    "STARTINDEX": 10_000_000,
}


@dataclass(frozen=True)
class QgisOgcPayload:
    content: bytes
    media_type: str
    status_code: int


def service_layer_name(layer: GisLayer) -> str:
    return f"{layer.workspace}__{layer.name}".replace("-", "_")


def resolve_publishable_layer(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
) -> GisLayer:
    layer = db.get(GisLayer, layer_id)
    if layer is None or not layer.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "GIS layer not found")
    if layer.source_type != "postgis" or not qgis_project.is_project_layer(layer):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Layer non pubblicabile tramite il proxy OGC GAIA.",
        )
    if not services._permission_flags(db, layer.id, current_user)["can_view"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "GIS layer permission denied")
    return layer


def normalize_query(
    layer: GisLayer,
    query_items: Iterable[tuple[str, str]],
) -> tuple[str, str, str, dict[str, str]]:
    values = _parse_query_values(query_items)
    service, operation = _resolve_operation(values)
    version = _pop_version(values, service)
    _validate_requested_layer(values, service, service_layer_name(layer))
    params = _normalize_operation_params(values, operation)
    _validate_required(operation, params)
    return service, operation, version, params


def _parse_query_values(
    query_items: Iterable[tuple[str, str]],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_key, value in query_items:
        key = raw_key.lower()
        if key in values:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Parametro OGC duplicato: {raw_key}",
            )
        if len(value) > 16_384:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Parametro OGC troppo lungo: {raw_key}",
            )
        values[key] = value
    return values


def _resolve_operation(values: dict[str, str]) -> tuple[str, str]:
    service = values.pop("service", "").lower()
    request_name = values.pop("request", "")
    operation = _OPERATIONS.get(service, {}).get(request_name.lower())
    if request_name.lower() == "transaction":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "WFS-T non e abilitato: il proxy OGC GAIA e solo lettura.",
        )
    if operation is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Operazione OGC non consentita.",
        )
    return service, operation


def _pop_version(values: dict[str, str], service: str) -> str:
    version = values.pop("version", _DEFAULT_VERSIONS[service])
    if version not in _ALLOWED_VERSIONS[service]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Versione OGC non supportata.",
        )
    return version


def _validate_requested_layer(
    values: dict[str, str], service: str, expected_layer: str
) -> None:
    controlled_keys = ("layers",) if service == "wms" else ("typename", "typenames")
    for key in controlled_keys:
        supplied = values.pop(key, None)
        if supplied is not None and supplied != expected_layer:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Layer OGC non coerente con layer_id.",
            )


def _normalize_operation_params(
    values: dict[str, str], operation: str
) -> dict[str, str]:
    allowed = _PARAMS[operation]
    params: dict[str, str] = {}
    for key, value in values.items():
        if key in _CONTROLLED_PARAMS or key not in allowed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Parametro OGC non consentito: {key}",
            )
        canonical = allowed[key]
        _validate_integer(canonical, value)
        params[canonical] = value
    return params


def _validate_integer(name: str, value: str) -> None:
    limit = _INTEGER_LIMITS.get(name)
    if limit is None:
        return
    try:
        numeric = int(value)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Il parametro OGC {name} deve essere intero.",
        ) from exc
    minimum = 0 if name == "STARTINDEX" else 1
    if not minimum <= numeric <= limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Il parametro OGC {name} supera il limite consentito.",
        )


def _validate_required(operation: str, params: dict[str, str]) -> None:
    if operation != "GetMap":
        return
    if not {"BBOX", "WIDTH", "HEIGHT"}.issubset(params) or not {
        "CRS",
        "SRS",
    }.intersection(params):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "GetMap richiede BBOX, WIDTH, HEIGHT e CRS/SRS.",
        )


def _upstream_params(
    layer: GisLayer,
    service: str,
    operation: str,
    version: str,
    params: dict[str, str],
) -> dict[str, str]:
    upstream = {
        "SERVICE": service.upper(),
        "REQUEST": operation,
        "VERSION": version,
        **params,
    }
    name = service_layer_name(layer)
    if operation == "GetMap":
        upstream["LAYERS"] = name
    elif operation == "GetFeature":
        upstream["TYPENAMES" if version == "2.0.0" else "TYPENAME"] = name
    return upstream


def execute_request(
    layer: GisLayer,
    service: str,
    operation: str,
    version: str,
    params: dict[str, str],
) -> QgisOgcPayload:
    try:
        response = httpx.get(
            settings.gis_qgis_server_internal_url,
            params=_upstream_params(layer, service, operation, version, params),
            timeout=settings.gis_qgis_server_timeout_seconds,
            follow_redirects=False,
        )
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "QGIS Server non raggiungibile; il servizio OGC non e disponibile.",
        ) from exc

    content = response.content
    media_type = response.headers.get("content-type", "application/octet-stream").split(
        ";", 1
    )[0]
    if operation == "GetCapabilities":
        content = filter_capabilities(content, service, service_layer_name(layer), layer.id)
        media_type = "application/xml"
    return QgisOgcPayload(content, media_type, response.status_code)


def proxy_request(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
    query_items: Iterable[tuple[str, str]],
) -> QgisOgcPayload:
    layer = resolve_publishable_layer(db, layer_id, current_user)
    service, operation, version, params = normalize_query(layer, query_items)
    return execute_request(layer, service, operation, version, params)


def reject_write_request(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
) -> None:
    resolve_publishable_layer(db, layer_id, current_user)
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "WFS-T non e abilitato: il proxy OGC GAIA e solo lettura.",
    )


def filter_capabilities(
    content: bytes,
    service: str,
    expected_name: str,
    layer_id: UUID,
) -> bytes:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Capabilities QGIS Server non valide.",
        ) from exc
    matched = (
        _filter_wms_capabilities(root, expected_name)
        if service == "wms"
        else _filter_wfs_capabilities(root, expected_name)
    )
    if not matched:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Il layer richiesto non compare nelle capabilities QGIS Server.",
        )
    _remove_transaction_operations(root)
    endpoint = (
        f"{settings.gis_qgis_proxy_base_url.rstrip('/')}/gis/ogc/layers/{layer_id}"
    )
    _rewrite_online_resources(root, endpoint)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _named_child(element: ET.Element, name: str) -> ET.Element | None:
    return next(
        (child for child in element if _local_name(child) == name),
        None,
    )


def _filter_wms_capabilities(root: ET.Element, expected_name: str) -> bool:
    layers = [element for element in root.iter() if _local_name(element) == "Layer"]
    target = _find_wms_layer(layers, expected_name)
    container = _find_wms_layer_container(layers)
    if target is None or container is None:
        return False
    _remove_children(container, "Layer")
    filtered = copy.deepcopy(target)
    _remove_children(filtered, "Layer")
    container.append(filtered)
    return True


def _find_wms_layer(
    layers: list[ET.Element], expected_name: str
) -> ET.Element | None:
    for element in layers:
        name = _named_child(element, "Name")
        if name is not None and (name.text or "") == expected_name:
            return element
    return None


def _find_wms_layer_container(layers: list[ET.Element]) -> ET.Element | None:
    return next(
        (
            element
            for element in layers
            if any(_local_name(child) == "Layer" for child in element)
        ),
        None,
    )


def _remove_children(element: ET.Element, child_name: str) -> None:
    for child in list(element):
        if _local_name(child) == child_name:
            element.remove(child)


def _filter_wfs_capabilities(root: ET.Element, expected_name: str) -> bool:
    matched = False
    for feature_list in (
        element for element in root.iter() if _local_name(element) == "FeatureTypeList"
    ):
        for feature_type in list(feature_list):
            if _local_name(feature_type) != "FeatureType":
                continue
            name = _named_child(feature_type, "Name")
            if name is not None and (name.text or "").split(":")[-1] == expected_name:
                matched = True
            else:
                feature_list.remove(feature_type)
    return matched


def _remove_transaction_operations(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if _local_name(child) not in {"Operation", "Transaction"}:
                continue
            name = child.attrib.get("name", "")
            if _local_name(child) == "Transaction" or name.lower() == "transaction":
                parent.remove(child)


def _rewrite_online_resources(root: ET.Element, endpoint: str) -> None:
    for element in root.iter():
        for key in list(element.attrib):
            if key.rsplit("}", 1)[-1].lower() == "href":
                element.attrib[key] = endpoint
