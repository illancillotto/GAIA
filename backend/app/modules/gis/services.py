from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser, ApplicationUserRole
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
    GisChangeRequestApprove,
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisLayerCreate,
    GisLayerExportRequest,
    GisLayerExportResponse,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
    GisLayerResponse,
)


DEFAULT_NAS_EXPORT_ROOT = "/volume1/Backups/GAIA/gis"
GIS_ADMIN_ROLES = {ApplicationUserRole.SUPER_ADMIN.value, ApplicationUserRole.ADMIN.value}

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


def _permission_flags(db: Session, layer_id: UUID, user: ApplicationUser) -> dict[str, bool]:
    if is_gis_admin(user):
        return _admin_flags()

    principals = [("role", user.role)]
    if user.id is not None:
        principals.append(("user", str(user.id)))

    rows = db.scalars(
        select(GisLayerPermission).where(
            GisLayerPermission.layer_id == layer_id,
            tuple_(GisLayerPermission.principal_type, GisLayerPermission.principal_key).in_(principals),
        )
    ).all()
    flags = {key: False for key in ACCESS_LEVEL_FLAGS[GisAccessLevel.admin]}
    for row in rows:
        flags["can_view"] = flags["can_view"] or row.can_view
        flags["can_annotate"] = flags["can_annotate"] or row.can_annotate
        flags["can_edit"] = flags["can_edit"] or row.can_edit
        flags["can_approve"] = flags["can_approve"] or row.can_approve
        flags["can_manage"] = flags["can_manage"] or row.can_manage
    return flags


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


def list_layers(db: Session, current_user: ApplicationUser, workspace: str | None = None) -> list[GisLayerResponse]:
    query = select(GisLayer).where(GisLayer.is_active.is_(True))
    if workspace:
        query = query.where(GisLayer.workspace == workspace)
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


def list_annotations(db: Session, layer_id: UUID, current_user: ApplicationUser) -> list[GisAnnotationResponse]:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_view")
    annotations = db.scalars(
        select(GisAnnotation)
        .where(GisAnnotation.layer_id == layer_id)
        .order_by(GisAnnotation.created_at.desc(), GisAnnotation.id.desc())
    ).all()
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
    if body.principal_type == "user":
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
        event_type="permission.upserted",
        actor=current_user,
        layer_id=layer.id,
        target_type="permission",
        target_id=permission.id,
        payload={"principal_type": permission.principal_type, "principal_key": permission.principal_key},
    )
    db.commit()
    db.refresh(permission)
    return _permission_response(permission)


def create_change_request(
    db: Session, layer_id: UUID, body: GisChangeRequestCreate, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    layer = _get_layer(db, layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_edit")
    change_request = GisChangeRequest(
        layer_id=layer.id,
        feature_id=_clean(body.feature_id),
        change_type=_clean(body.change_type) or body.change_type,
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
        payload={"feature_id": change_request.feature_id, "change_type": change_request.change_type},
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
    status_filter: str | None = None,
) -> list[GisChangeRequestResponse]:
    query = select(GisChangeRequest)
    if not is_gis_admin(current_user):
        layer_ids = _visible_layer_ids(db, current_user)
        if not layer_ids:
            return []
        query = query.where(GisChangeRequest.layer_id.in_(layer_ids))
    if status_filter:
        query = query.where(GisChangeRequest.status == status_filter)
    change_requests = db.scalars(query.order_by(GisChangeRequest.created_at.desc(), GisChangeRequest.id.desc())).all()
    return [_change_request_response(change_request) for change_request in change_requests]


def approve_change_request(
    db: Session, change_request_id: UUID, body: GisChangeRequestApprove, current_user: ApplicationUser
) -> GisChangeRequestResponse:
    change_request = db.get(GisChangeRequest, change_request_id)
    if change_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS change request not found")
    layer = _get_layer(db, change_request.layer_id)
    _ensure_layer_permission(db, layer, current_user, "can_approve")
    if change_request.status == "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GIS change request already approved")
    change_request.status = "approved"
    change_request.reviewed_by_user_id = current_user.id
    change_request.review_notes = _clean(body.review_notes)
    change_request.reviewed_at = datetime.now(UTC)
    db.flush()
    _write_audit(
        db,
        event_type="change_request.approved",
        actor=current_user,
        layer_id=layer.id,
        target_type="change_request",
        target_id=change_request.id,
        payload={"review_notes": change_request.review_notes},
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
    export = GisLayerExport(
        layer_id=layer.id,
        version_label=version_label,
        status="requested",
        nas_path=nas_path,
        checksum_sha256=_clean(body.checksum_sha256),
        requested_by_user_id=current_user.id,
        metadata_json={"format": "shapefile", "source": "postgis", **body.metadata},
    )
    db.add(export)
    db.flush()
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
    db.refresh(export)
    return _export_response(export)
