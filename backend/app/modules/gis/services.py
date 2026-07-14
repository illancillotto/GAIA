from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.gis.exporter import export_layer_to_shapefile_zip
from app.modules.gis.models import (
    GisAnnotation,
    GisAuditLog,
    GisChangeRequest,
    GisLayer,
    GisLayerExport,
    GisLayerPermission,
)
from app.modules.gis.schemas import (
    GisAccessLevel,
    GisAnnotationCreate,
    GisAnnotationResponse,
    GisAnnotationStatus,
    GisAnnotationUpdate,
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisChangeRequestReview,
    GisChangeRequestStatus,
    GisChangeRequestType,
    GisChangeRequestUpdate,
    GisLayerCreate,
    GisLayerExportRequest,
    GisLayerExportResponse,
    GisLayerMetadataUpdate,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
    GisLayerResponse,
)


DEFAULT_NAS_EXPORT_ROOT = "/volume1/Backups/GAIA/gis"
GIS_ADMIN_ROLES = {ApplicationUserRole.SUPER_ADMIN.value, ApplicationUserRole.ADMIN.value}
GIS_ROLE_PRINCIPAL_KEYS = {role.value for role in ApplicationUserRole}
ANNOTATION_TERMINAL_STATUSES = {GisAnnotationStatus.closed.value, GisAnnotationStatus.rejected.value}
CHANGE_REQUEST_REVIEWABLE_STATUSES = {
    GisChangeRequestStatus.submitted.value,
    GisChangeRequestStatus.needs_changes.value,
}
CHANGE_REQUEST_TERMINAL_STATUSES = {
    GisChangeRequestStatus.rejected.value,
    GisChangeRequestStatus.applied.value,
}
ChangeRequestValidator = Callable[[GisLayer, GisChangeRequestType, str | None, dict[str, Any]], None]
CHANGE_REQUEST_VALIDATORS: dict[str, ChangeRequestValidator] = {}

ACCESS_LEVEL_FLAGS: dict[GisAccessLevel, dict[str, bool]] = {
    GisAccessLevel.viewer: {
        "can_view": True,
        "can_annotate": False,
        "can_edit": False,
        "can_approve": False,
        "can_manage": False,
    },
    GisAccessLevel.annotator: {
        "can_view": True,
        "can_annotate": True,
        "can_edit": False,
        "can_approve": False,
        "can_manage": False,
    },
    GisAccessLevel.editor: {
        "can_view": True,
        "can_annotate": True,
        "can_edit": True,
        "can_approve": False,
        "can_manage": False,
    },
    GisAccessLevel.approver: {
        "can_view": True,
        "can_annotate": True,
        "can_edit": True,
        "can_approve": True,
        "can_manage": False,
    },
    GisAccessLevel.admin: {
        "can_view": True,
        "can_annotate": True,
        "can_edit": True,
        "can_approve": True,
        "can_manage": True,
    },
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def register_change_request_validator(scope: str, validator: ChangeRequestValidator) -> None:
    CHANGE_REQUEST_VALIDATORS[_clean(scope) or scope] = validator


def is_gis_admin(user: ApplicationUser) -> bool:
    return user.role in GIS_ADMIN_ROLES


def _admin_flags() -> dict[str, bool]:
    return ACCESS_LEVEL_FLAGS[GisAccessLevel.admin].copy()


def _flags_to_access_level(flags: dict[str, bool]) -> GisAccessLevel:
    for level in (
        GisAccessLevel.admin,
        GisAccessLevel.approver,
        GisAccessLevel.editor,
        GisAccessLevel.annotator,
    ):
        expected = ACCESS_LEVEL_FLAGS[level]
        if all(flags[key] == expected[key] for key in expected):
            return level
    return GisAccessLevel.viewer


def _empty_flags() -> dict[str, bool]:
    return {key: False for key in ACCESS_LEVEL_FLAGS[GisAccessLevel.admin]}


def _merge_permission_rows(rows: list[GisLayerPermission]) -> dict[str, bool]:
    flags = _empty_flags()
    for row in rows:
        flags["can_view"] = flags["can_view"] or row.can_view
        flags["can_annotate"] = flags["can_annotate"] or row.can_annotate
        flags["can_edit"] = flags["can_edit"] or row.can_edit
        flags["can_approve"] = flags["can_approve"] or row.can_approve
        flags["can_manage"] = flags["can_manage"] or row.can_manage
    return flags


def _permission_flags(db: Session, layer_id: UUID, user: ApplicationUser) -> dict[str, bool]:
    if is_gis_admin(user):
        return _admin_flags()

    if user.id is not None:
        user_rows = db.scalars(
            select(GisLayerPermission).where(
                GisLayerPermission.layer_id == layer_id,
                GisLayerPermission.principal_type == "user",
                GisLayerPermission.principal_key == str(user.id),
            )
        ).all()
        if user_rows:
            return _merge_permission_rows(list(user_rows))

    role_rows = db.scalars(
        select(GisLayerPermission).where(
            GisLayerPermission.layer_id == layer_id,
            GisLayerPermission.principal_type == "role",
            GisLayerPermission.principal_key == user.role,
        )
    ).all()
    return _merge_permission_rows(list(role_rows))


def _ensure_layer_permission(db: Session, layer: GisLayer, user: ApplicationUser, capability: str) -> dict[str, bool]:
    flags = _permission_flags(db, layer.id, user)
    if not flags[capability]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GIS layer permission denied")
    return flags


def _get_layer(db: Session, layer_id: UUID) -> GisLayer:
    layer = db.get(GisLayer, layer_id)
    if layer is None or not layer.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS layer not found")
    return layer


def _get_manageable_layer(db: Session, layer_id: UUID, current_user: ApplicationUser) -> GisLayer:
    if not is_gis_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GIS admin role required")
    layer = db.get(GisLayer, layer_id)
    if layer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS layer not found")
    return layer


def _layer_response(layer: GisLayer, flags: dict[str, bool]) -> GisLayerResponse:
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
        effective_access_level=_flags_to_access_level(flags),
        **flags,
        created_at=layer.created_at,
        updated_at=layer.updated_at,
    )


def _annotation_response(annotation: GisAnnotation) -> GisAnnotationResponse:
    return GisAnnotationResponse(
        id=annotation.id,
        layer_id=annotation.layer_id,
        feature_id=annotation.feature_id,
        title=annotation.title,
        body=annotation.body,
        geometry=annotation.geometry_json,
        attachment_refs=annotation.attachment_refs_json or [],
        status=annotation.status,
        created_by_user_id=annotation.created_by_user_id,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


def _change_request_response(change_request: GisChangeRequest) -> GisChangeRequestResponse:
    return GisChangeRequestResponse(
        id=change_request.id,
        layer_id=change_request.layer_id,
        feature_id=change_request.feature_id,
        change_type=change_request.change_type,
        status=change_request.status,
        payload=change_request.payload_json,
        justification=change_request.justification,
        requested_by_user_id=change_request.requested_by_user_id,
        reviewed_by_user_id=change_request.reviewed_by_user_id,
        review_notes=change_request.review_notes,
        reviewed_at=change_request.reviewed_at,
        created_at=change_request.created_at,
        updated_at=change_request.updated_at,
    )


def _export_response(export: GisLayerExport) -> GisLayerExportResponse:
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


def _permission_response(permission: GisLayerPermission) -> GisLayerPermissionResponse:
    flags = {
        "can_view": permission.can_view,
        "can_annotate": permission.can_annotate,
        "can_edit": permission.can_edit,
        "can_approve": permission.can_approve,
        "can_manage": permission.can_manage,
    }
    return GisLayerPermissionResponse(
        id=permission.id,
        layer_id=permission.layer_id,
        principal_type=permission.principal_type,
        principal_key=permission.principal_key,
        access_level=_flags_to_access_level(flags),
        **flags,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


def _write_audit(
    db: Session,
    *,
    event_type: str,
    actor: ApplicationUser,
    layer_id: UUID | None,
    target_type: str | None,
    target_id: UUID | None,
    payload: dict | None = None,
) -> None:
    db.add(
        GisAuditLog(
            event_type=event_type,
            actor_user_id=actor.id,
            layer_id=layer_id,
            target_type=target_type,
            target_id=target_id,
            payload_json=payload,
        )
    )


def _get_annotation(db: Session, layer: GisLayer, annotation_id: UUID) -> GisAnnotation:
    annotation = db.get(GisAnnotation, annotation_id)
    if annotation is None or annotation.layer_id != layer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS annotation not found")
    return annotation


def _get_change_request(db: Session, change_request_id: UUID) -> GisChangeRequest:
    change_request = db.get(GisChangeRequest, change_request_id)
    if change_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS change request not found")
    return change_request


def _require_feature_id(feature_id: str | None, change_type: GisChangeRequestType) -> None:
    if feature_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GIS change request {change_type.value} requires feature_id",
        )


def _require_payload_object(payload: dict[str, Any], key: str, change_type: GisChangeRequestType) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict) or not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GIS change request {change_type.value} requires payload.{key}",
        )
    return value


def _validate_change_request_payload(
    layer: GisLayer,
    change_type: GisChangeRequestType,
    feature_id: str | None,
    payload: dict[str, Any],
) -> None:
    if change_type == GisChangeRequestType.attribute_update:
        _require_feature_id(feature_id, change_type)
        _require_payload_object(payload, "after", change_type)
    elif change_type == GisChangeRequestType.geometry_update:
        _require_feature_id(feature_id, change_type)
        _require_payload_object(payload, "geometry", change_type)
    elif change_type == GisChangeRequestType.feature_create:
        _require_payload_object(payload, "geometry", change_type)
        _require_payload_object(payload, "properties", change_type)
    elif change_type == GisChangeRequestType.feature_delete:
        _require_feature_id(feature_id, change_type)
        _require_payload_object(payload, "before", change_type)

    for scope in (str(layer.id), layer.domain_module, layer.workspace):
        if scope and (validator := CHANGE_REQUEST_VALIDATORS.get(scope)):
            validator(layer, change_type, feature_id, payload)


def _ensure_change_request_open(change_request: GisChangeRequest) -> None:
    if change_request.status in CHANGE_REQUEST_TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS change request is terminal")


def _set_change_request_review(
    db: Session,
    *,
    layer: GisLayer,
    change_request: GisChangeRequest,
    current_user: ApplicationUser,
    next_status: GisChangeRequestStatus,
    review_notes: str | None,
) -> None:
    _ensure_change_request_open(change_request)
    if change_request.status not in CHANGE_REQUEST_REVIEWABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS change request status transition denied")
    previous_status = change_request.status
    change_request.status = next_status.value
    change_request.reviewed_by_user_id = current_user.id
    change_request.review_notes = _clean(review_notes)
    change_request.reviewed_at = datetime.now(UTC)
    audit_payload = {"previous_status": previous_status, "status": change_request.status, "review_notes": change_request.review_notes}
    db.flush()
    _write_audit(
        db,
        event_type=f"change_request.{next_status.value}",
        actor=current_user,
        layer_id=layer.id,
        target_type="change_request",
        target_id=change_request.id,
        payload=audit_payload,
    )


def create_layer(db: Session, body: GisLayerCreate, current_user: ApplicationUser) -> GisLayerResponse:
    if not is_gis_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GIS admin role required")

    layer = GisLayer(
        workspace=_clean(body.workspace) or body.workspace,
        name=_clean(body.name) or body.name,
        title=_clean(body.title) or body.title,
        description=_clean(body.description),
        domain_module=_clean(body.domain_module),
        source_type=_clean(body.source_type) or "postgis",
        official_source=_clean(body.official_source) or "postgis",
        postgis_schema=_clean(body.postgis_schema),
        postgis_table=_clean(body.postgis_table),
        geometry_column=_clean(body.geometry_column),
        geometry_type=_clean(body.geometry_type),
        srid=body.srid,
        feature_id_column=_clean(body.feature_id_column),
        martin_layer_id=_clean(body.martin_layer_id),
        ogc_service_url=_clean(body.ogc_service_url),
        qgis_project_path=_clean(body.qgis_project_path),
        nas_export_root=_clean(body.nas_export_root),
        metadata_json=body.metadata,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(layer)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS layer already exists") from exc
    _write_audit(db, event_type="layer.created", actor=current_user, layer_id=layer.id, target_type="layer", target_id=layer.id)
    db.commit()
    db.refresh(layer)
    return _layer_response(layer, _admin_flags())


def list_layers(
    db: Session,
    current_user: ApplicationUser,
    workspace: str | None = None,
    domain_module: str | None = None,
    source_type: str | None = None,
    official_source: str | None = None,
    is_active: bool | None = None,
) -> list[GisLayerResponse]:
    query = select(GisLayer)
    if not is_gis_admin(current_user):
        query = query.where(GisLayer.is_active.is_(True))
    elif is_active is not None:
        query = query.where(GisLayer.is_active.is_(is_active))
    if workspace:
        query = query.where(GisLayer.workspace == _clean(workspace))
    if domain_module:
        query = query.where(GisLayer.domain_module == _clean(domain_module))
    if source_type:
        query = query.where(GisLayer.source_type == _clean(source_type))
    if official_source:
        query = query.where(GisLayer.official_source == _clean(official_source))
    layers = db.scalars(query.order_by(GisLayer.workspace.asc(), GisLayer.title.asc(), GisLayer.name.asc())).all()
    responses = []
    for layer in layers:
        flags = _permission_flags(db, layer.id, current_user)
        if flags["can_view"]:
            responses.append(_layer_response(layer, flags))
    return responses


def get_layer(db: Session, layer_id: UUID, current_user: ApplicationUser) -> GisLayerResponse:
    layer = _get_layer(db, layer_id)
    flags = _ensure_layer_permission(db, layer, current_user, "can_view")
    return _layer_response(layer, flags)


def update_layer_metadata(
    db: Session,
    layer_id: UUID,
    body: GisLayerMetadataUpdate,
    current_user: ApplicationUser,
) -> GisLayerResponse:
    layer = _get_manageable_layer(db, layer_id, current_user)
    fields = body.model_fields_set
    if not fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one metadata field is required")

    updates: dict[str, Any] = {}
    if "title" in fields:
        cleaned_title = _clean(body.title)
        if cleaned_title is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS layer title cannot be null")
        updates["title"] = cleaned_title
    if "description" in fields:
        updates["description"] = _clean(body.description)
    if "ogc_service_url" in fields:
        updates["ogc_service_url"] = _clean(body.ogc_service_url)
    if "qgis_project_path" in fields:
        updates["qgis_project_path"] = _clean(body.qgis_project_path)
    if "nas_export_root" in fields:
        updates["nas_export_root"] = _clean(body.nas_export_root)
    if "metadata" in fields:
        updates["metadata_json"] = body.metadata

    changed_fields = []
    for field, value in updates.items():
        if getattr(layer, field) != value:
            setattr(layer, field, value)
            changed_fields.append(field)
    layer.updated_by_user_id = current_user.id
    db.flush()
    _write_audit(
        db,
        event_type="layer.metadata_updated",
        actor=current_user,
        layer_id=layer.id,
        target_type="layer",
        target_id=layer.id,
        payload={"changed_fields": changed_fields},
    )
    db.commit()
    db.refresh(layer)
    return _layer_response(layer, _admin_flags())


def set_layer_active(db: Session, layer_id: UUID, is_active: bool, current_user: ApplicationUser) -> GisLayerResponse:
    layer = _get_manageable_layer(db, layer_id, current_user)
    previous_is_active = layer.is_active
    layer.is_active = is_active
    layer.updated_by_user_id = current_user.id
    db.flush()
    _write_audit(
        db,
        event_type="layer.activated" if is_active else "layer.deactivated",
        actor=current_user,
        layer_id=layer.id,
        target_type="layer",
        target_id=layer.id,
        payload={"previous_is_active": previous_is_active, "is_active": layer.is_active},
    )
    db.commit()
    db.refresh(layer)
    return _layer_response(layer, _admin_flags())


def list_annotations(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
    status_filter: GisAnnotationStatus | None = None,
    feature_id: str | None = None,
) -> list[GisAnnotationResponse]:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_view")
    query = select(GisAnnotation).where(GisAnnotation.layer_id == layer_id)
    if status_filter is not None:
        query = query.where(GisAnnotation.status == status_filter.value)
    if feature_id:
        query = query.where(GisAnnotation.feature_id == _clean(feature_id))
    annotations = db.scalars(query.order_by(GisAnnotation.created_at.desc(), GisAnnotation.id.desc())).all()
    return [_annotation_response(annotation) for annotation in annotations]


def create_annotation(
    db: Session, layer_id: UUID, body: GisAnnotationCreate, current_user: ApplicationUser
) -> GisAnnotationResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_annotate")
    annotation = GisAnnotation(
        layer_id=layer.id,
        feature_id=_clean(body.feature_id),
        title=_clean(body.title) or body.title,
        body=_clean(body.body) or body.body,
        geometry_json=body.geometry,
        attachment_refs_json=body.attachment_refs,
        created_by_user_id=current_user.id,
    )
    db.add(annotation)
    db.flush()
    _write_audit(
        db,
        event_type="annotation.created",
        actor=current_user,
        layer_id=layer.id,
        target_type="annotation",
        target_id=annotation.id,
        payload={"feature_id": annotation.feature_id},
    )
    db.commit()
    db.refresh(annotation)
    return _annotation_response(annotation)


def update_annotation(
    db: Session,
    layer_id: UUID,
    annotation_id: UUID,
    body: GisAnnotationUpdate,
    current_user: ApplicationUser,
) -> GisAnnotationResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_annotate")
    annotation = _get_annotation(db, layer, annotation_id)
    if annotation.status in ANNOTATION_TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS annotation is terminal")
    fields = body.model_fields_set
    if not fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one annotation field is required")

    changed_fields = []
    if "title" in fields:
        cleaned_title = _clean(body.title)
        if cleaned_title is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS annotation title cannot be null")
        if annotation.title != cleaned_title:
            annotation.title = cleaned_title
            changed_fields.append("title")
    if "body" in fields:
        cleaned_body = _clean(body.body)
        if cleaned_body is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS annotation body cannot be null")
        if annotation.body != cleaned_body:
            annotation.body = cleaned_body
            changed_fields.append("body")
    if "geometry" in fields and annotation.geometry_json != body.geometry:
        annotation.geometry_json = body.geometry
        changed_fields.append("geometry")
    if "attachment_refs" in fields and annotation.attachment_refs_json != body.attachment_refs:
        annotation.attachment_refs_json = body.attachment_refs or []
        changed_fields.append("attachment_refs")
    db.flush()
    _write_audit(
        db,
        event_type="annotation.updated",
        actor=current_user,
        layer_id=layer.id,
        target_type="annotation",
        target_id=annotation.id,
        payload={"changed_fields": changed_fields, "feature_id": annotation.feature_id},
    )
    db.commit()
    db.refresh(annotation)
    return _annotation_response(annotation)


def set_annotation_status(
    db: Session,
    layer_id: UUID,
    annotation_id: UUID,
    next_status: GisAnnotationStatus,
    current_user: ApplicationUser,
) -> GisAnnotationResponse:
    layer = _get_layer(db, layer_id)
    capability = "can_approve" if next_status in {GisAnnotationStatus.closed, GisAnnotationStatus.rejected} else "can_annotate"
    _ensure_layer_permission(db, layer, current_user, capability)
    annotation = _get_annotation(db, layer, annotation_id)
    if annotation.status in ANNOTATION_TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS annotation is terminal")
    previous_status = annotation.status
    annotation.status = next_status.value
    db.flush()
    _write_audit(
        db,
        event_type=f"annotation.{next_status.value}",
        actor=current_user,
        layer_id=layer.id,
        target_type="annotation",
        target_id=annotation.id,
        payload={"previous_status": previous_status, "status": annotation.status, "feature_id": annotation.feature_id},
    )
    db.commit()
    db.refresh(annotation)
    return _annotation_response(annotation)


def list_permissions(db: Session, layer_id: UUID, current_user: ApplicationUser) -> list[GisLayerPermissionResponse]:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_manage")
    permissions = db.scalars(
        select(GisLayerPermission)
        .where(GisLayerPermission.layer_id == layer_id)
        .order_by(GisLayerPermission.principal_type.asc(), GisLayerPermission.principal_key.asc())
    ).all()
    return [_permission_response(permission) for permission in permissions]


def upsert_permission(
    db: Session, layer_id: UUID, body: GisLayerPermissionUpsert, current_user: ApplicationUser
) -> GisLayerPermissionResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_manage")
    principal_key = _clean(body.principal_key) or body.principal_key
    user_id = None
    if body.principal_type == "role":
        if principal_key not in GIS_ROLE_PRINCIPAL_KEYS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS permission role not recognized")
    else:
        try:
            user_id = int(principal_key)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User principal_key must be an integer id") from exc
        if db.get(ApplicationUser, user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS permission user not found")

    permission = db.scalar(
        select(GisLayerPermission).where(
            GisLayerPermission.layer_id == layer.id,
            GisLayerPermission.principal_type == body.principal_type,
            GisLayerPermission.principal_key == principal_key,
        )
    )
    if permission is None:
        permission = GisLayerPermission(
            layer_id=layer.id,
            principal_type=body.principal_type,
            principal_key=principal_key,
            user_id=user_id,
            granted_by_user_id=current_user.id,
        )
        db.add(permission)
        event_type = "permission.granted"
    else:
        event_type = "permission.updated"
    flags = ACCESS_LEVEL_FLAGS[body.access_level]
    permission.user_id = user_id
    permission.can_view = flags["can_view"]
    permission.can_annotate = flags["can_annotate"]
    permission.can_edit = flags["can_edit"]
    permission.can_approve = flags["can_approve"]
    permission.can_manage = flags["can_manage"]
    db.flush()
    _write_audit(
        db,
        event_type=event_type,
        actor=current_user,
        layer_id=layer.id,
        target_type="permission",
        target_id=permission.id,
        payload={
            "principal_type": permission.principal_type,
            "principal_key": permission.principal_key,
            "access_level": body.access_level.value,
        },
    )
    db.commit()
    db.refresh(permission)
    return _permission_response(permission)


def revoke_permission(
    db: Session,
    layer_id: UUID,
    permission_id: UUID,
    current_user: ApplicationUser,
) -> None:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_manage")
    permission = db.get(GisLayerPermission, permission_id)
    if permission is None or permission.layer_id != layer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS permission not found")
    payload = {
        "principal_type": permission.principal_type,
        "principal_key": permission.principal_key,
        "access_level": _permission_response(permission).access_level.value,
    }
    db.delete(permission)
    _write_audit(
        db,
        event_type="permission.revoked",
        actor=current_user,
        layer_id=layer.id,
        target_type="permission",
        target_id=permission.id,
        payload=payload,
    )
    db.commit()


def create_change_request(
    db: Session, layer_id: UUID, body: GisChangeRequestCreate, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_edit")
    feature_id = _clean(body.feature_id)
    _validate_change_request_payload(layer, body.change_type, feature_id, body.payload)
    change_request = GisChangeRequest(
        layer_id=layer.id,
        feature_id=feature_id,
        change_type=body.change_type.value,
        payload_json=body.payload,
        justification=_clean(body.justification),
        requested_by_user_id=current_user.id,
    )
    db.add(change_request)
    db.flush()
    _write_audit(
        db,
        event_type="change_request.submitted",
        actor=current_user,
        layer_id=layer.id,
        target_type="change_request",
        target_id=change_request.id,
        payload={"feature_id": change_request.feature_id, "change_type": change_request.change_type, "status": change_request.status},
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def update_change_request(
    db: Session,
    change_request_id: UUID,
    body: GisChangeRequestUpdate,
    current_user: ApplicationUser,
) -> GisChangeRequestResponse:
    change_request = _get_change_request(db, change_request_id)
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_edit")
    _ensure_change_request_open(change_request)
    if change_request.status == GisChangeRequestStatus.approved.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS change request already approved")
    fields = body.model_fields_set
    if not fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one change request field is required")

    next_feature_id = _clean(body.feature_id) if "feature_id" in fields else change_request.feature_id
    next_change_type = body.change_type if "change_type" in fields and body.change_type is not None else GisChangeRequestType(change_request.change_type)
    if "change_type" in fields and body.change_type is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS change request type cannot be null")
    next_payload = body.payload if "payload" in fields else change_request.payload_json
    if next_payload is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GIS change request payload cannot be null")
    _validate_change_request_payload(layer, next_change_type, next_feature_id, next_payload)

    changed_fields = []
    if change_request.feature_id != next_feature_id:
        change_request.feature_id = next_feature_id
        changed_fields.append("feature_id")
    if change_request.change_type != next_change_type.value:
        change_request.change_type = next_change_type.value
        changed_fields.append("change_type")
    if change_request.payload_json != next_payload:
        change_request.payload_json = next_payload
        changed_fields.append("payload")
    if "justification" in fields:
        next_justification = _clean(body.justification)
        if change_request.justification != next_justification:
            change_request.justification = next_justification
            changed_fields.append("justification")

    previous_status = change_request.status
    change_request.status = GisChangeRequestStatus.submitted.value
    change_request.reviewed_by_user_id = None
    change_request.review_notes = None
    change_request.reviewed_at = None
    db.flush()
    _write_audit(
        db,
        event_type="change_request.updated",
        actor=current_user,
        layer_id=layer.id,
        target_type="change_request",
        target_id=change_request.id,
        payload={"changed_fields": changed_fields, "previous_status": previous_status, "status": change_request.status},
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def _visible_layer_ids(db: Session, current_user: ApplicationUser) -> list[UUID]:
    return [
        item.id
        for item in db.scalars(select(GisLayer).where(GisLayer.is_active.is_(True))).all()
        if _permission_flags(db, item.id, current_user)["can_view"]
    ]


def list_change_requests(
    db: Session,
    current_user: ApplicationUser,
    status_filter: GisChangeRequestStatus | None = None,
    layer_id: UUID | None = None,
) -> list[GisChangeRequestResponse]:
    query = select(GisChangeRequest)
    if layer_id is not None:
        query = query.where(GisChangeRequest.layer_id == layer_id)
    if not is_gis_admin(current_user):
        layer_ids = _visible_layer_ids(db, current_user)
        if not layer_ids:
            return []
        query = query.where(GisChangeRequest.layer_id.in_(layer_ids))
    if status_filter is not None:
        query = query.where(GisChangeRequest.status == status_filter.value)
    change_requests = db.scalars(query.order_by(GisChangeRequest.created_at.desc(), GisChangeRequest.id.desc())).all()
    return [_change_request_response(change_request) for change_request in change_requests]


def request_change_request_changes(
    db: Session, change_request_id: UUID, body: GisChangeRequestReview, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    change_request = _get_change_request(db, change_request_id)
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    _set_change_request_review(
        db,
        layer=layer,
        change_request=change_request,
        current_user=current_user,
        next_status=GisChangeRequestStatus.needs_changes,
        review_notes=body.review_notes,
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def reject_change_request(
    db: Session, change_request_id: UUID, body: GisChangeRequestReview, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    change_request = _get_change_request(db, change_request_id)
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    _set_change_request_review(
        db,
        layer=layer,
        change_request=change_request,
        current_user=current_user,
        next_status=GisChangeRequestStatus.rejected,
        review_notes=body.review_notes,
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def approve_change_request(
    db: Session, change_request_id: UUID, body: GisChangeRequestReview, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    change_request = _get_change_request(db, change_request_id)
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    _set_change_request_review(
        db,
        layer=layer,
        change_request=change_request,
        current_user=current_user,
        next_status=GisChangeRequestStatus.approved,
        review_notes=body.review_notes,
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def _apply_change_request(layer: GisLayer, change_request: GisChangeRequest) -> dict[str, Any]:
    reason = (
        "catasto domain apply policy not configured"
        if layer.workspace == "catasto" or layer.domain_module == "catasto"
        else "apply adapter not configured"
    )
    return {
        "mode": "no_op",
        "reason": reason,
        "change_type": change_request.change_type,
        "official_source": layer.official_source,
    }


def apply_change_request(
    db: Session, change_request_id: UUID, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    change_request = _get_change_request(db, change_request_id)
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    _ensure_change_request_open(change_request)
    if change_request.status != GisChangeRequestStatus.approved.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS change request must be approved before apply")
    previous_status = change_request.status
    apply_result = _apply_change_request(layer, change_request)
    change_request.status = GisChangeRequestStatus.applied.value
    db.flush()
    _write_audit(
        db,
        event_type="change_request.applied",
        actor=current_user,
        layer_id=layer.id,
        target_type="change_request",
        target_id=change_request.id,
        payload={"previous_status": previous_status, "status": change_request.status, "apply_result": apply_result},
    )
    db.commit()
    db.refresh(change_request)
    return _change_request_response(change_request)


def request_shapefile_export(
    db: Session, layer_id: UUID, body: GisLayerExportRequest, current_user: ApplicationUser
) -> GisLayerExportResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    version_label = _clean(body.version_label) or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    export_root = layer.nas_export_root or DEFAULT_NAS_EXPORT_ROOT
    nas_path = _clean(body.nas_path) or f"{export_root.rstrip('/')}/{layer.workspace}/{layer.name}/{version_label}.zip"
    requested_checksum = _clean(body.checksum_sha256)
    metadata = {"format": "shapefile", "source": "postgis", **body.metadata}
    if requested_checksum:
        metadata["requested_checksum_sha256"] = requested_checksum
    export = GisLayerExport(
        layer_id=layer.id,
        version_label=version_label,
        status="requested",
        nas_path=nas_path,
        requested_by_user_id=current_user.id,
        metadata_json=metadata,
    )
    db.add(export)
    db.flush()
    export_id = export.id
    _write_audit(
        db,
        event_type="export.requested",
        actor=current_user,
        layer_id=layer.id,
        target_type="export",
        target_id=export.id,
        payload={"nas_path": export.nas_path, "version_label": export.version_label},
    )
    db.commit()

    try:
        artifact = export_layer_to_shapefile_zip(
            db,
            layer,
            version_label=version_label,
            nas_path=nas_path,
            metadata=body.metadata,
        )
    except Exception as exc:
        db.rollback()
        export = db.get(GisLayerExport, export_id)
        export.status = "failed"
        export.metadata_json = {
            **metadata,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        _write_audit(
            db,
            event_type="export.failed",
            actor=current_user,
            layer_id=layer.id,
            target_type="export",
            target_id=export.id,
            payload={"nas_path": export.nas_path, "version_label": export.version_label, "error": export.metadata_json["error"]},
        )
        db.commit()
    else:
        export = db.get(GisLayerExport, export_id)
        export.status = "completed"
        export.checksum_sha256 = artifact.checksum_sha256
        export.completed_at = datetime.now(UTC)
        export.metadata_json = {
            **metadata,
            "row_count": artifact.row_count,
            "manifest": artifact.manifest,
            "published_atomically": True,
        }
        _write_audit(
            db,
            event_type="export.completed",
            actor=current_user,
            layer_id=layer.id,
            target_type="export",
            target_id=export.id,
            payload={
                "nas_path": str(artifact.path),
                "version_label": export.version_label,
                "checksum_sha256": export.checksum_sha256,
                "row_count": artifact.row_count,
            },
        )
        db.commit()

    db.refresh(export)
    return _export_response(export)
