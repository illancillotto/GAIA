import hashlib
import io
from datetime import date
from zipfile import ZipFile

import pytest
import shapefile
from fastapi import HTTPException

from app.modules.gis import services


def archive_with_components(components: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in components.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def shapefile_components(*, null_only: bool = False, empty: bool = False) -> dict[str, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(
        shp=shp,
        shx=shx,
        dbf=dbf,
        shapeType=shapefile.NULL if null_only else shapefile.POINT,
        encoding="ISO-8859-1",
    )
    writer.field("name", "C", size=30)
    writer.field("amount", "N", size=10, decimal=2)
    writer.field("active", "L")
    writer.field("when", "D")
    if not empty:
        if not null_only:
            writer.point(8.4, 39.9)
            writer.record("città", 12.5, True, date(2026, 7, 14))
        writer.null()
        writer.record("senza geometria", None, False, None)
    writer.close()
    return {
        "Survey/Layer.SHP": shp.getvalue(),
        "Survey/Layer.SHX": shx.getvalue(),
        "Survey/Layer.DBF": dbf.getvalue(),
        "Survey/Layer.PRJ": b'GEOGCS["WGS84",AUTHORITY["EPSG","4326"]]',
        "Survey/Layer.CPG": b"ISO-8859-1",
    }


@pytest.mark.parametrize(
    ("components", "message"),
    [
        ({}, "GIS shapefile import requires exactly one .shp"),
        ({"one.dbf": b""}, "GIS shapefile import requires exactly one .shp"),
        (
            {"one.shp": b"", "two.shp": b""},
            "GIS shapefile import requires exactly one .shp",
        ),
        (
            {"one.shp": b"", "two.shx": b"", "two.dbf": b"", "two.prj": b""},
            "GIS shapefile import missing components: .shx, .dbf, .prj",
        ),
        (
            {"one.shp": b"", "one.dbf": b""},
            "GIS shapefile import missing components: .shx, .prj",
        ),
    ],
)
def test_component_validation_precedes_srid_and_reader_errors(components, message):
    with pytest.raises(HTTPException) as caught:
        services._validate_shapefile_zip(
            archive_with_components(components), encoding="unknown-codec", source_srid="invalid"
        )
    assert caught.value.status_code == 422
    assert caught.value.detail == message


@pytest.mark.parametrize("null_only", [False, True])
def test_real_dbf_and_null_geometries_are_normalized_without_losing_records(null_only):
    archive = archive_with_components(shapefile_components(null_only=null_only))
    result = services._validate_shapefile_zip(archive, encoding=None, source_srid=None)

    assert result.stem == "survey/layer"
    assert result.source_srid == 4326
    assert result.encoding == "ISO-8859-1"
    assert result.checksum_sha256 == hashlib.sha256(archive).hexdigest()
    assert result.fields == [
        {"name": "name", "type": "C", "size": 30, "decimal": 0},
        {"name": "amount", "type": "N", "size": 10, "decimal": 2},
        {"name": "active", "type": "L", "size": 1, "decimal": 0},
        {"name": "when", "type": "D", "size": 8, "decimal": 0},
    ]
    assert result.records[-1] == (
        {"name": "senza geometria", "amount": None, "active": False, "when": None},
        None,
    )
    assert result.feature_count == len(result.records) == (1 if null_only else 2)
    assert result.geometry_type == ("NULL" if null_only else "POINT")
    assert result.bbox == ([0.0, 0.0, 0.0, 0.0] if null_only else [8.4, 39.9, 8.4, 39.9])
    assert result.validation_report == {
        "is_valid": True,
        "component_names": {
            "shp": "Survey/Layer.SHP",
            "shx": "Survey/Layer.SHX",
            "dbf": "Survey/Layer.DBF",
            "prj": "Survey/Layer.PRJ",
        },
        "required_components": [".shp", ".shx", ".dbf", ".prj"],
        "warnings": [],
        "source_srid": 4326,
        "source_srid_source": "prj",
    }
    if not null_only:
        assert result.records[0] == (
            {"name": "città", "amount": 12.5, "active": True, "when": "2026-07-14"},
            {"type": "Point", "coordinates": (8.4, 39.9)},
        )


@pytest.mark.parametrize("failure", ["header", "record_encoding", "unknown_encoding", "empty"])
def test_reader_failures_remain_validation_errors(failure):
    components = shapefile_components(empty=failure == "empty")
    encoding = None
    if failure == "header":
        components["Survey/Layer.SHP"] = b"corrupt"
    elif failure == "record_encoding":
        encoding = "utf-8"
    elif failure == "unknown_encoding":
        encoding = "unknown-codec"

    with pytest.raises(HTTPException) as caught:
        services._validate_shapefile_zip(
            archive_with_components(components), encoding=encoding, source_srid=4326
        )

    assert caught.value.status_code == 422
    if failure == "empty":
        assert caught.value.detail == "GIS shapefile import contains no features"
        assert caught.value.__cause__ is None
    else:
        cause = caught.value.__cause__
        assert isinstance(cause, Exception)
        assert caught.value.detail == f"GIS shapefile validation failed: {cause}"
        if failure == "record_encoding":
            assert isinstance(cause, UnicodeDecodeError)
        elif failure == "unknown_encoding":
            assert isinstance(cause, LookupError)
