"""PostGIS geometry columns with a portable text representation on other dialects."""

from sqlalchemy import Text

try:
    from geoalchemy2 import Geometry
except Exception:
    # The optional spatial backend can also fail while loading native libraries.
    Geometry = None


def _geometry_type(shape: str):
    if Geometry is None:
        return Text()
    return Text().with_variant(Geometry(shape, srid=4326), "postgresql")


MULTIPOLYGON_4326 = _geometry_type("MULTIPOLYGON")
POINT_4326 = _geometry_type("POINT")
LINESTRING_4326 = _geometry_type("LINESTRING")
