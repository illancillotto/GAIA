import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import inspect, text

from app.models.application_user import ApplicationUser
from app.modules.gis import services as gis
from app.modules.gis.models import GisLayer
from app.modules.ruolo.parcel_control_models import ParcelControlIndex
from app.modules.ruolo.services.parcel_control_identity import EXCLUDED_DISTRICTS, digest

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quoted(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError("Identificativo GIS non utilizzabile")
    return f'"{value}"'


def layer_source(db, data, actor_id):
    layer = db.get(GisLayer, UUID(data["layer_id"]))
    if layer is None or not layer.is_active:
        raise ValueError("Layer GIS non disponibile")
    gis._ensure_layer_permission(db, layer, db.get(ApplicationUser, actor_id), "can_view")
    if layer.source_type != "postgis":
        raise ValueError("Occorre un layer poligonale PostGIS pubblicato; WMS non e un poligono")
    schema = layer.postgis_schema or "public"
    relation = f"{quoted(schema)}.{quoted(layer.postgis_table)}"
    geometry = quoted(layer.geometry_column)
    column_names = {
        column["name"] for column in inspect(db.get_bind()).get_columns(layer.postgis_table, schema)
    }
    if layer.geometry_column not in column_names:
        raise ValueError("Geometria del layer non disponibile")
    predicate = feature_selection(data, column_names)
    if data["scope_kind"] == "districts":
        code_column = data.get("district_column", "num_distretto")
        if code_column not in column_names:
            raise ValueError("Specificare la colonna dei codici distretto dello shapefile")
        code = quoted(code_column)
        predicate = f"({predicate}) AND ({code} IS NULL OR btrim({code}::text) = '' OR upper(btrim({code}::text)) NOT IN :excluded)"
    return layer, relation, geometry, predicate


def feature_selection(data, column_names):
    if data["scope_kind"] != "municipality":
        return "TRUE"
    field = data.get("feature_column")
    if field not in column_names or not str(data.get("feature_value", "")).strip():
        raise ValueError("Selezionare esplicitamente il comune tramite campo e valore del layer")
    return f"{quoted(field)}::text = :feature_value"


def parcel_geometry_id(db, case, data):
    parcel_id = UUID(data.get("parcel_id") or str(case.parcel_id))
    allowed = {case.parcel_id, *(UUID(parcel["id"]) for parcel in case.parcels)}
    if parcel_id not in allowed:
        raise ValueError("Particella non appartenente alla pratica")
    item = db.get(ParcelControlIndex, parcel_id)
    identifiers = {
        occurrence["cat_particella_id"]
        for occurrence in item.original["occurrences"]
        if occurrence.get("cat_particella_id")
    }
    if len(identifiers) != 1:
        raise ValueError(
            "Collegamento geometrico mancante o ambiguo: verifica catastale necessaria"
        )
    return parcel_id, UUID(identifiers.pop())


def spatial_check(db, case, data, actor_id):
    scope = data.get("scope_kind")
    if scope not in {"districts", "municipality", "settlements"}:
        raise ValueError("Ambito geometrico non valido")
    if not all(str(data.get(field, "")).strip() for field in ("source_version", "coverage")):
        raise ValueError("Versione e attestazione della copertura sono obbligatorie")
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("Il confronto geometrico richiede PostGIS")
    parcel_id, geometry_id = parcel_geometry_id(db, case, data)
    layer, relation, geometry, predicate = layer_source(db, data, actor_id)
    measurement = measure(db, geometry_id, (relation, geometry, predicate), data)
    evidence = {
        "id": str(uuid4()),
        "kind": "spatial_check",
        "parcel_id": str(parcel_id),
        "geometry_parcel_id": str(geometry_id),
        "actor_id": actor_id,
        "scope": scope,
        "source": layer.title,
        "reference": str(layer.id),
        "version": data["source_version"],
        "coverage": data["coverage"],
        "feature_column": data.get("feature_column") if scope == "municipality" else None,
        "feature_value": data.get("feature_value") if scope == "municipality" else None,
        "layer_updated_at": str(layer.updated_at),
        "excluded_districts": sorted(EXCLUDED_DISTRICTS) if scope == "districts" else [],
        "observed_at": datetime.now(UTC).isoformat(),
        "measurement_srid": 3003,
        **measurement,
    }
    evidence["fingerprint"] = digest(evidence)
    case.evidence = [*case.evidence, evidence]


def measure(db, geometry_id, source, data):
    from sqlalchemy import bindparam

    relation, geometry, predicate = source
    code_quality = "FALSE"
    if data.get("scope_kind") == "districts":
        code = quoted(data.get("district_column", "num_distretto"))
        code_quality = f"({code} IS NULL OR btrim({code}::text) = '')"
    statement = text(f"""
        WITH source AS (
            SELECT {geometry} AS geom, {code_quality} AS invalid_code
            FROM {relation} WHERE {predicate}
        ), quality AS (
            SELECT count(*) AS total,
                count(*) FILTER (WHERE invalid_code OR geom IS NULL OR ST_IsEmpty(geom)
                    OR NOT ST_IsValid(geom) OR ST_SRID(geom) = 0
                    OR ST_GeometryType(geom) NOT IN ('ST_Polygon','ST_MultiPolygon')) AS invalid
            FROM source
        ), boundary AS (
            SELECT ST_UnaryUnion(ST_Collect(ST_Transform(geom,3003))) AS geom
            FROM source CROSS JOIN quality WHERE quality.invalid = 0
        ), parcel AS (
            SELECT geometry AS geom FROM cat_particelle WHERE id = :geometry_id
        ), usable AS (
            SELECT ST_Transform(parcel.geom,3003) AS geom FROM parcel
            WHERE parcel.geom IS NOT NULL AND NOT ST_IsEmpty(parcel.geom)
                AND ST_IsValid(parcel.geom) AND ST_SRID(parcel.geom) > 0
                AND ST_GeometryType(parcel.geom) IN ('ST_Polygon','ST_MultiPolygon')
        )
        SELECT quality.total,quality.invalid,
            ST_Area(usable.geom) AS parcel_area_m2,
            ST_Area(ST_Intersection(usable.geom,boundary.geom)) AS intersection_area_m2,
            ST_Covers(boundary.geom,usable.geom) AS covered,
            ST_Intersects(boundary.geom,usable.geom) AS intersects,
            md5(ST_AsEWKB(boundary.geom)::text) AS boundary_hash,
            md5(ST_AsEWKB(usable.geom)::text) AS parcel_hash
        FROM quality CROSS JOIN boundary LEFT JOIN usable ON TRUE
    """)
    if ":excluded" in predicate:
        statement = statement.bindparams(bindparam("excluded", expanding=True))
    row = (
        db.execute(
            statement,
            {
                "geometry_id": geometry_id,
                "excluded": sorted(EXCLUDED_DISTRICTS),
                "feature_value": data.get("feature_value"),
            },
        )
        .mappings()
        .one()
    )
    return measurement_result(dict(row))


def measurement_result(row):
    area = row["parcel_area_m2"]
    overlap = row["intersection_area_m2"]
    if row["invalid"] or not row["total"] or not area or overlap is None:
        return {**row, "result": "not_verifiable", "intersection_percent": None}
    if row["covered"]:
        result = "inside"
    elif overlap > 0:
        result = "partial"
    else:
        result = "touching" if row["intersects"] else "outside"
    return {**row, "result": result, "intersection_percent": 100 * overlap / area}
