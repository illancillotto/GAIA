import os
import runpy
import sys

import pytest
from sqlalchemy import Column, MetaData, Table, Text, create_engine, func, inspect, select, text
from sqlalchemy.dialects import postgresql

from app.models import spatial_types

SHAPES = {
    "point": (spatial_types.POINT_4326, "POINT(1 2)"),
    "line": (spatial_types.LINESTRING_4326, "LINESTRING(0 0,1 1)"),
    "area": (spatial_types.MULTIPOLYGON_4326, "MULTIPOLYGON(((0 0,0 1,1 0,0 0)))"),
}


def spatial_table():
    return Table(
        "test_catasto_shapes",
        MetaData(),
        *(Column(name, kind) for name, (kind, _) in SHAPES.items()),
        prefixes=["TEMPORARY"],
    )


def test_sqlite_stores_all_shapes_as_text():
    engine = create_engine("sqlite://")
    table = spatial_table()
    values = {name: wkt for name, (_, wkt) in SHAPES.items()}
    with engine.begin() as conn:
        table.create(conn)
        assert all(isinstance(col["type"], Text) for col in inspect(conn).get_columns(table.name))
        conn.execute(table.insert().values(values))
        assert dict(conn.execute(select(table)).mappings().one()) == values


def test_text_fallback_when_geoalchemy_is_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "geoalchemy2", None)
    fallback = runpy.run_path(spatial_types.__file__)
    for name in ("POINT_4326", "LINESTRING_4326", "MULTIPOLYGON_4326"):
        assert isinstance(fallback[name].dialect_impl(postgresql.dialect()), Text)


@pytest.mark.postgres
def test_postgis_column_types_srid_and_roundtrip():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    engine = create_engine(url)
    table = spatial_table()
    try:
        with engine.begin() as conn:
            table.create(conn)
            typmods = dict(
                conn.execute(
                    text(
                        "SELECT attname, format_type(atttypid, atttypmod) FROM pg_attribute "
                        "WHERE attrelid = 'pg_temp.test_catasto_shapes'::regclass AND attnum > 0"
                    )
                ).all()
            )
            assert typmods == {
                "point": "geometry(Point,4326)",
                "line": "geometry(LineString,4326)",
                "area": "geometry(MultiPolygon,4326)",
            }
            conn.execute(
                table.insert().values(
                    {name: f"SRID=4326;{wkt}" for name, (_, wkt) in SHAPES.items()}
                )
            )
            for name, (_, wkt) in SHAPES.items():
                geom = table.c[name]
                assert conn.execute(select(func.ST_SRID(geom), func.ST_AsText(geom))).one() == (
                    4326,
                    wkt,
                )
                assert conn.scalar(select(geom)).srid == 4326
            table.drop(conn)
    finally:
        engine.dispose()
