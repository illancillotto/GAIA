from app.modules.gis.models import GisLayerExport, GisShapefileImport
from app.modules.gis.schemas import (
    GisLayerExportResponse,
    GisShapefileImportResponse,
    GisShapefileImportStatus,
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
