from __future__ import annotations

from typing import Any

from geoalchemy2.shape import to_shape


def geometry_to_geojson_dict(geometry: Any) -> dict[str, Any] | None:
    shape = _coerce_shape(geometry)
    if shape is not None:
        return dict(shape.__geo_interface__)
    return _parse_wkt_geojson(geometry)


def geometry_type_label(geometry: Any) -> str | None:
    shape = _coerce_shape(geometry)
    if shape is not None:
        return shape.geom_type
    geojson = _parse_wkt_geojson(geometry)
    return geojson.get("type") if geojson else None


def centroid_geojson_dict(geometry: Any) -> dict[str, Any] | None:
    shape = _coerce_shape(geometry)
    if shape is not None:
        return dict(shape.centroid.__geo_interface__)
    geojson = _parse_wkt_geojson(geometry)
    coordinates = _flatten_coordinates(geojson["coordinates"]) if geojson else []
    if not coordinates:
        return None
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    return {
        "type": "Point",
        "coordinates": [sum(xs) / len(xs), sum(ys) / len(ys)],
    }


def _coerce_shape(geometry: Any):
    if geometry is None or isinstance(geometry, str):
        return None
    try:
        return to_shape(geometry)
    except Exception:
        return None


def _parse_wkt_geojson(geometry: Any) -> dict[str, Any] | None:
    if not isinstance(geometry, str):
        return None
    normalized = geometry.strip()
    if not normalized:
        return None
    if normalized.upper().startswith("SRID=") and ";" in normalized:
        normalized = normalized.split(";", 1)[1].strip()
    upper = normalized.upper()
    if upper.startswith("MULTIPOLYGON"):
        body = normalized[len("MULTIPOLYGON"):].strip()
        return {"type": "MultiPolygon", "coordinates": _parse_multipolygon_coords(body)}
    if upper.startswith("POLYGON"):
        body = normalized[len("POLYGON"):].strip()
        return {"type": "Polygon", "coordinates": _parse_polygon_coords(body)}
    return None


def _parse_multipolygon_coords(body: str) -> list[list[list[list[float]]]]:
    trimmed = body.strip()
    if trimmed.startswith("(") and trimmed.endswith(")"):
        trimmed = trimmed[1:-1]
    polygons = _split_top_level(trimmed)
    return [_parse_polygon_coords(polygon) for polygon in polygons]


def _parse_polygon_coords(body: str) -> list[list[list[float]]]:
    trimmed = body.strip()
    if trimmed.startswith("(") and trimmed.endswith(")"):
        trimmed = trimmed[1:-1]
    rings = _split_top_level(trimmed)
    return [_parse_ring_coords(ring) for ring in rings]


def _parse_ring_coords(body: str) -> list[list[float]]:
    trimmed = body.strip()
    if trimmed.startswith("(") and trimmed.endswith(")"):
        trimmed = trimmed[1:-1]
    coordinates: list[list[float]] = []
    for pair in trimmed.split(","):
        parts = [chunk for chunk in pair.strip().split() if chunk]
        if len(parts) < 2:
            continue
        coordinates.append([float(parts[0]), float(parts[1])])
    return coordinates


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _flatten_coordinates(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    if value and isinstance(value[0], (int, float)):
        if len(value) >= 2:
            return [[float(value[0]), float(value[1])]]
        return []
    flattened: list[list[float]] = []
    for item in value:
        flattened.extend(_flatten_coordinates(item))
    return flattened
