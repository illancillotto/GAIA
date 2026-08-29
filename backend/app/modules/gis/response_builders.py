from app.modules.gis.models import GisLayer, GisLayerExport, GisShapefileImport
from app.modules.gis.schemas import (
    GisAccessLevel,
    GisLayerExportResponse,
    GisLayerResponse,
    GisShapefileImportResponse,
    GisShapefileImportStatus,
)


def layer_response(
    layer: GisLayer,
    flags: dict[str, bool],
    effective_access_level: GisAccessLevel,
) -> GisLayerResponse:
    return GisLayerResponse(
        id=layer.id,
        workspace=layer.workspace,
        name=layer.name,
        title=layer.title,
        description=layer.description,
        domain_module=layer.domain_module,
        source_type=layer.source_type,
        official_source=layer.official_source,
        postgis_schema=layer.postgis_schema,
        postgis_table=layer.postgis_table,
        geometry_column=layer.geometry_column,
        geometry_type=layer.geometry_type,
        srid=layer.srid,
        feature_id_column=layer.feature_id_column,
        martin_layer_id=layer.martin_layer_id,
        ogc_service_url=layer.ogc_service_url,
        qgis_project_path=layer.qgis_project_path,
        nas_export_root=layer.nas_export_root,
        metadata=layer.metadata_json or {},
        is_active=layer.is_active,
        effective_access_level=effective_access_level,
        **flags,
        created_at=layer.created_at,
        updated_at=layer.updated_at,
    )


def export_response(export: GisLayerExport) -> GisLayerExportResponse:
    return GisLayerExportResponse(
        id=export.id,
        layer_id=export.layer_id,
        version_label=export.version_label,
        status=export.status,
        nas_path=export.nas_path,
        checksum_sha256=export.checksum_sha256,
        requested_by_user_id=export.requested_by_user_id,
        completed_at=export.completed_at,
        metadata=export.metadata_json or {},
        created_at=export.created_at,
    )


def shapefile_import_response(
    item: GisShapefileImport,
) -> GisShapefileImportResponse:
    return GisShapefileImportResponse(
        id=item.id,
        status=GisShapefileImportStatus(item.status),
        original_filename=item.original_filename,
        workspace=item.workspace,
        domain_module=item.domain_module,
        target_layer_name=item.target_layer_name,
        target_layer_title=item.target_layer_title,
        official_source=item.official_source,
        source_srid=item.source_srid,
        encoding=item.encoding,
        staging_schema=item.staging_schema,
        staging_table=item.staging_table,
        feature_count=item.feature_count,
        geometry_type=item.geometry_type,
        bbox=item.bbox_json,
        fields=item.field_schema_json or [],
        validation_report=item.validation_report_json or {},
        metadata=item.metadata_json or {},
        checksum_sha256=item.checksum_sha256,
        uploaded_by_user_id=item.uploaded_by_user_id,
        published_layer_id=item.published_layer_id,
        validated_at=item.validated_at,
        rejected_at=item.rejected_at,
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
