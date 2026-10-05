from __future__ import annotations

import io
from typing import Any

import shapefile
from fastapi import HTTPException, status

SHAPEFILE_REQUIRED_SUFFIXES = (".shp", ".shx", ".dbf", ".prj")


def require_shapefile_stem(components: dict[tuple[str, str], tuple[str, bytes]]) -> str:
    stems = {stem for stem, suffix in components if suffix == ".shp"}
    if len(stems) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GIS shapefile import requires exactly one .shp",
        )
    stem = next(iter(stems))
    missing = [suffix for suffix in SHAPEFILE_REQUIRED_SUFFIXES if (stem, suffix) not in components]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GIS shapefile import missing components: {', '.join(missing)}",
        )
    return stem


def jsonable_record(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def read_shapefile(
    components: dict[tuple[str, str], tuple[str, bytes]], stem: str, encoding: str
) -> tuple[
    shapefile.Reader, list[dict[str, Any]], list[tuple[dict[str, Any], dict[str, Any] | None]]
]:
    try:
        reader = shapefile.Reader(
            shp=io.BytesIO(components[(stem, ".shp")][1]),
            shx=io.BytesIO(components[(stem, ".shx")][1]),
            dbf=io.BytesIO(components[(stem, ".dbf")][1]),
            encoding=encoding,
        )
        shape_records = list(reader.iterShapeRecords())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GIS shapefile validation failed: {exc}",
        ) from exc
    if not shape_records:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GIS shapefile import contains no features",
        )

    fields = [
        {"name": field[0], "type": field[1], "size": field[2], "decimal": field[3]}
        for field in reader.fields[1:]
    ]
    records: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for item in shape_records:
        attributes = {key: jsonable_record(value) for key, value in item.record.as_dict().items()}
        geometry = (
            None if item.shape.shapeType == shapefile.NULL else dict(item.shape.__geo_interface__)
        )
        records.append((attributes, geometry))
    return reader, fields, records
