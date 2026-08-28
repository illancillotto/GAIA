from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, inspect as sa_inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.models import (
    GisAuditLog,
    GisLayer,
    GisLayerExport,
    GisShapefileImport,
)
from app.modules.gis.schemas import (
    GisAuditLogListResponse,
    GisAuditLogResponse,
    GisLayerExportListResponse,
    GisLayerFeatureListResponse,
    GisLayerFeatureOption,
    GisShapefileImportListResponse,
    GisShapefileImportStatus,
)
from app.modules.gis.service_support import feature_geometry


def _audit_response(item: GisAuditLog) -> GisAuditLogResponse:
    return GisAuditLogResponse(
        id=item.id,
        layer_id=item.layer_id,
        event_type=item.event_type,
        actor_user_id=item.actor_user_id,
        target_type=item.target_type,
        target_id=item.target_id,
        payload=item.payload_json or {},
        created_at=item.created_at,
    )


def _paginated_scalars(
    db: Session,
    query: Any,
    *,
    order_by: tuple[Any, ...],
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(query.order_by(*order_by).limit(limit).offset(offset)).all()
    )
    return items, total


def list_shapefile_imports(
    db: Session,
    current_user: ApplicationUser,
    *,
    import_status: GisShapefileImportStatus | None,
    limit: int,
    offset: int,
) -> GisShapefileImportListResponse:
    query = select(GisShapefileImport)
    if not services.is_gis_admin(current_user):
        query = query.where(
            GisShapefileImport.uploaded_by_user_id == current_user.id
        )
    if import_status is not None:
        query = query.where(GisShapefileImport.status == import_status.value)
    page, total = _paginated_scalars(
        db,
        query,
        order_by=(
            GisShapefileImport.created_at.desc(),
            GisShapefileImport.id.desc(),
        ),
        limit=limit,
        offset=offset,
    )
    return GisShapefileImportListResponse(
        items=[services._shapefile_import_response(item) for item in page],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(page) < total,
    )


def _layer_columns(db: Session, layer: GisLayer) -> list[str]:
    schema = (
        None
        if db.get_bind().dialect.name == "sqlite"
        else layer.postgis_schema or "public"
    )
    return [
        str(column["name"])
        for column in sa_inspect(db.get_bind()).get_columns(
            layer.postgis_table or "", schema=schema
        )
    ]


def _label_columns(
    layer: GisLayer, attribute_columns: list[str], feature_id_column: str
) -> list[str]:
    selector_metadata = services._nested_metadata(
        services._metadata_mapping(layer.metadata_json), "feature_selector"
    )
    configured = selector_metadata.get("label_fields")
    if isinstance(configured, list):
        labels = [str(column) for column in configured if str(column) in attribute_columns]
        if labels:
            return labels
    return [column for column in attribute_columns if column != feature_id_column][:2]


def _feature_selector_columns(
    db: Session, layer: GisLayer, *, include_editable: bool
) -> tuple[list[str], list[str]]:
    columns = _layer_columns(db, layer)
    feature_id_column = services._layer_feature_id_column(layer)
    if feature_id_column not in columns:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GIS layer feature identifier is unavailable",
        )
    geometry_column = layer.geometry_column or "geometry"
    attributes = [column for column in columns if column != geometry_column]
    labels = _label_columns(layer, attributes, feature_id_column)
    visible = (
        attributes
        if include_editable
        else list(dict.fromkeys([feature_id_column, *labels]))
    )
    return visible, labels


def _feature_option(
    row: dict[str, Any],
    *,
    feature_id_column: str,
    label_columns: list[str],
) -> GisLayerFeatureOption:
    feature_id = str(row[feature_id_column])
    geometry = feature_geometry(row.pop("__gaia_geometry", None))
    attributes = {key: services._jsonable_record(value) for key, value in row.items()}
    label_parts = [
        str(attributes[column])
        for column in label_columns
        if attributes.get(column) not in (None, "")
    ]
    label = (
        " - ".join([feature_id, *label_parts])
        if label_parts
        else f"Elemento {feature_id}"
    )
    return GisLayerFeatureOption(
        feature_id=feature_id, label=label, attributes=attributes, geometry=geometry
    )


def _feature_geometry_sql(db: Session, layer: GisLayer) -> str:
    geometry_column = layer.geometry_column or "geometry"
    if geometry_column not in _layer_columns(db, layer):
        return "NULL"
    quoted = services._quote_identifier(geometry_column)
    return quoted if db.get_bind().dialect.name == "sqlite" else f"ST_AsGeoJSON({quoted})"


def _feature_filter(
    query: str | None, feature_id_column: str, label_columns: list[str]
) -> tuple[str, dict[str, Any]]:
    search_value = services._clean(query)
    if not search_value:
        return "", {}
    columns = list(dict.fromkeys([feature_id_column, *label_columns]))
    comparisons = [
        f"LOWER(CAST({services._quote_identifier(column)} AS TEXT)) LIKE :query"
        for column in columns
    ]
    return f" WHERE {' OR '.join(comparisons)}", {
        "query": f"%{search_value.lower()}%"
    }


def _load_feature_page(
    db: Session,
    layer: GisLayer,
    *,
    can_edit: bool,
    query: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int, str, list[str]]:
    visible, labels = _feature_selector_columns(db, layer, include_editable=can_edit)
    feature_id = services._layer_feature_id_column(layer)
    table = services._layer_table_identifier(db, layer)
    where_sql, search_params = _feature_filter(query, feature_id, labels)
    params = {"limit": limit, "offset": offset, **search_params}
    total = int(
        db.execute(text(f"SELECT COUNT(*) FROM {table}{where_sql}"), params).scalar_one()
    )
    selected = ", ".join(services._quote_identifier(column) for column in visible)
    geometry_sql = _feature_geometry_sql(db, layer)
    rows = (
        db.execute(
            text(
                f"SELECT {selected}, {geometry_sql} AS __gaia_geometry "
                f"FROM {table}{where_sql} "
                f"ORDER BY CAST({services._quote_identifier(feature_id)} AS TEXT) "
                "LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows], total, feature_id, labels


def list_layer_features(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
    *,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> GisLayerFeatureListResponse:
    layer = services._get_layer(db, layer_id)
    flags = services._permission_flags(db, layer.id, current_user)
    if not flags["can_view"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GIS feature selection permission denied",
        )
    if layer.source_type != "postgis" or not layer.postgis_table:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GIS feature selection requires a PostGIS layer",
        )
    try:
        rows, total, feature_id, labels = _load_feature_page(
            db,
            layer,
            can_edit=flags["can_edit"],
            query=query,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GIS layer source is unavailable",
        ) from exc
    items = [
        _feature_option(row, feature_id_column=feature_id, label_columns=labels)
        for row in rows
    ]
    return GisLayerFeatureListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


def list_shapefile_exports(
    db: Session,
    current_user: ApplicationUser,
    *,
    layer_id: UUID | None,
    export_status: str | None,
    limit: int,
    offset: int,
) -> GisLayerExportListResponse:
    visible_layer_ids = {item.id for item in services.list_layers(db, current_user)}
    if layer_id is not None and layer_id not in visible_layer_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GIS layer not found",
        )
    query = select(GisLayerExport).where(GisLayerExport.layer_id.in_(visible_layer_ids))
    if layer_id is not None:
        query = query.where(GisLayerExport.layer_id == layer_id)
    if export_status:
        query = query.where(GisLayerExport.status == services._clean(export_status))
    page, total = _paginated_scalars(
        db,
        query,
        order_by=(GisLayerExport.created_at.desc(), GisLayerExport.id.desc()),
        limit=limit,
        offset=offset,
    )
    return GisLayerExportListResponse(
        items=[services._export_response(item) for item in page],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(page) < total,
    )


def list_audit_logs(
    db: Session,
    current_user: ApplicationUser,
    *,
    layer_id: UUID | None,
    event_type: str | None,
    limit: int,
    offset: int,
) -> GisAuditLogListResponse:
    if not services.is_gis_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GIS admin role required",
        )
    query = select(GisAuditLog)
    if layer_id is not None:
        query = query.where(GisAuditLog.layer_id == layer_id)
    if event_type:
        query = query.where(GisAuditLog.event_type == services._clean(event_type))
    page, total = _paginated_scalars(
        db,
        query,
        order_by=(GisAuditLog.created_at.desc(), GisAuditLog.id.desc()),
        limit=limit,
        offset=offset,
    )
    return GisAuditLogListResponse(
        items=[_audit_response(item) for item in page],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(page) < total,
    )
