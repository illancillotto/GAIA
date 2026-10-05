from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import test_gis_platform_api as platform
from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.models import GisAnnotation, GisAuditLog, GisChangeRequest, GisLayer
from app.modules.gis.schemas import (
    GisAnnotationCreate,
    GisAnnotationStatus,
    GisAnnotationUpdate,
    GisChangeRequestCreate,
    GisChangeRequestReview,
    GisChangeRequestStatus,
    GisChangeRequestType,
    GisChangeRequestUpdate,
    GisLayerCreate,
    GisLayerMetadataUpdate,
)

setup_database = platform.setup_database


@pytest.fixture
def context():
    with platform.TestingSessionLocal() as session:
        admin = session.scalar(
            select(ApplicationUser).where(ApplicationUser.username == "gis-admin")
        )
        viewer = session.scalar(
            select(ApplicationUser).where(ApplicationUser.username == "gis-viewer")
        )
        response = services.create_layer(
            session,
            GisLayerCreate(
                workspace="contract",
                name="features",
                title="Features",
                source_type="postgis",
                postgis_table="contract_features",
                geometry_column="geometry",
                feature_id_column="id",
                metadata={"qgis": {"editable": True, "edit_policy": "controlled"}},
            ),
            admin,
        )
        session.execute(
            text("CREATE TABLE contract_features (id TEXT PRIMARY KEY, name TEXT, geometry TEXT)")
        )
        session.execute(text("INSERT INTO contract_features VALUES ('one', 'Before', NULL)"))
        session.commit()
        try:
            yield SimpleNamespace(
                db=session, admin=admin, viewer=viewer, layer=session.get(GisLayer, response.id)
            )
        finally:
            session.rollback()
            session.execute(text("DROP TABLE IF EXISTS contract_features"))
            session.commit()


def last_audit(context, event):
    return context.db.scalars(
        select(GisAuditLog)
        .where(GisAuditLog.event_type == event)
        .order_by(GisAuditLog.created_at.desc())
    ).first()


def annotation(context):
    response = services.create_annotation(
        context.db,
        context.layer.id,
        GisAnnotationCreate(title="Original", body="Body", feature_id=" one "),
        context.admin,
    )
    return context.db.get(GisAnnotation, response.id)


@pytest.mark.parametrize(
    "updates,expected",
    [
        ({"title": " Original "}, []),
        ({"title": "Changed"}, ["title"]),
        ({"body": " Body "}, []),
        ({"body": "Changed"}, ["body"]),
        ({"geometry": None}, []),
        ({"geometry": {"type": "Point", "coordinates": [1, 2]}}, ["geometry"]),
        ({"attachment_refs": []}, []),
        ({"attachment_refs": [{"document_id": "document"}]}, ["attachment_refs"]),
        ({"attachment_refs": None}, ["attachment_refs"]),
    ],
)
def test_annotation_updates_persist_only_changed_fields_and_audit(context, updates, expected):
    item = annotation(context)
    services.update_annotation(
        context.db, context.layer.id, item.id, GisAnnotationUpdate(**updates), context.admin
    )
    context.db.expire_all()
    saved = context.db.get(GisAnnotation, item.id)
    audit = last_audit(context, "annotation.updated")
    assert audit.payload_json["changed_fields"] == expected
    assert audit.payload_json["feature_id"] == "one"
    if "title" in updates:
        assert saved.title == updates["title"].strip()
    if "body" in updates:
        assert saved.body == updates["body"].strip()
    if "geometry" in updates:
        assert saved.geometry_json == updates["geometry"]
    if "attachment_refs" in updates:
        assert saved.attachment_refs_json == (updates["attachment_refs"] or [])


@pytest.mark.parametrize(
    "updates,message",
    [
        ({}, "At least one annotation field is required"),
        ({"title": None}, "GIS annotation title cannot be null"),
        ({"body": None}, "GIS annotation body cannot be null"),
    ],
)
def test_annotation_invalid_update_leaves_persisted_data_unchanged(context, updates, message):
    item = annotation(context)
    with pytest.raises(HTTPException) as error:
        services.update_annotation(
            context.db, context.layer.id, item.id, GisAnnotationUpdate(**updates), context.admin
        )
    assert (error.value.status_code, error.value.detail) == (422, message)
    context.db.rollback()
    assert context.db.get(GisAnnotation, item.id).title == "Original"
    assert last_audit(context, "annotation.updated") is None


def test_annotation_identity_is_scoped_to_layer(context):
    item = annotation(context)
    with pytest.raises(HTTPException) as error:
        services._get_annotation(context.db, SimpleNamespace(id=uuid4()), item.id)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        services._get_annotation(context.db, context.layer, uuid4())
    assert error.value.status_code == 404


@pytest.mark.parametrize("terminal", [GisAnnotationStatus.closed, GisAnnotationStatus.rejected])
def test_terminal_annotations_reject_both_update_and_status_changes(context, terminal):
    item = annotation(context)
    services.set_annotation_status(context.db, context.layer.id, item.id, terminal, context.admin)
    for operation in [
        lambda: services.update_annotation(
            context.db, context.layer.id, item.id, GisAnnotationUpdate(title="No"), context.admin
        ),
        lambda: services.set_annotation_status(
            context.db, context.layer.id, item.id, GisAnnotationStatus.open, context.admin
        ),
    ]:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 409
    assert context.db.get(GisAnnotation, item.id).status == terminal.value


@pytest.mark.parametrize(
    "updates",
    [
        {"description": None},
        {"ogc_service_url": " https://example.test/wms "},
        {"qgis_project_path": " /srv/project.qgs "},
        {"nas_export_root": " /tmp/exports "},
        {"metadata": {"custom": True}},
        {"title": "Features"},
    ],
)
def test_layer_metadata_patch_is_persisted_and_audited(context, updates):
    services.update_layer_metadata(
        context.db, context.layer.id, GisLayerMetadataUpdate(**updates), context.admin
    )
    context.db.expire_all()
    saved = context.db.get(GisLayer, context.layer.id)
    for key, value in updates.items():
        field = "metadata_json" if key == "metadata" else key
        expected = value.strip() if isinstance(value, str) else value
        assert getattr(saved, field) == expected
    assert saved.updated_by_user_id == context.admin.id
    assert last_audit(context, "layer.metadata_updated") is not None


def change_request(context):
    response = services.create_change_request(
        context.db,
        context.layer.id,
        GisChangeRequestCreate(
            feature_id="one",
            change_type=GisChangeRequestType.attribute_update,
            payload={"after": {"name": "After"}},
            justification="Reason",
        ),
        context.admin,
    )
    return context.db.get(GisChangeRequest, response.id)


@pytest.mark.parametrize(
    "updates,changed",
    [
        ({"feature_id": " two "}, ["feature_id"]),
        (
            {
                "change_type": "geometry_update",
                "payload": {"geometry": {"type": "Point", "coordinates": [1, 2]}},
            },
            ["change_type", "payload"],
        ),
        ({"payload": {"after": {"name": "Next"}}}, ["payload"]),
        ({"justification": " Next "}, ["justification"]),
        ({"justification": "Reason"}, []),
    ],
)
def test_change_request_patch_resets_review_and_persists_changed_fields(context, updates, changed):
    item = change_request(context)
    services.request_change_request_changes(
        context.db,
        item.id,
        GisChangeRequestReview(review_notes="Please amend"),
        context.admin,
    )
    services.update_change_request(
        context.db, item.id, GisChangeRequestUpdate(**updates), context.admin
    )
    context.db.expire_all()
    saved = context.db.get(GisChangeRequest, item.id)
    assert saved.status == "submitted"
    assert (
        saved.review_notes is None
        and saved.reviewed_at is None
        and saved.reviewed_by_user_id is None
    )
    assert last_audit(context, "change_request.updated").payload_json["changed_fields"] == changed
    for key, value in updates.items():
        field = "payload_json" if key == "payload" else key
        assert getattr(saved, field) == (value.strip() if isinstance(value, str) else value)


@pytest.mark.parametrize(
    "updates,message",
    [
        ({}, "At least one change request field is required"),
        ({"change_type": None}, "GIS change request type cannot be null"),
        ({"payload": None}, "GIS change request payload cannot be null"),
    ],
)
def test_change_request_invalid_patch_does_not_write_audit(context, updates, message):
    item = change_request(context)
    with pytest.raises(HTTPException) as error:
        services.update_change_request(
            context.db, item.id, GisChangeRequestUpdate(**updates), context.admin
        )
    assert (error.value.status_code, error.value.detail) == (422, message)
    context.db.rollback()
    assert context.db.get(GisChangeRequest, item.id).payload_json == {"after": {"name": "After"}}
    assert last_audit(context, "change_request.updated") is None


def test_approved_request_cannot_be_patched_or_reviewed_again(context):
    item = change_request(context)
    services.approve_change_request(context.db, item.id, GisChangeRequestReview(), context.admin)
    with pytest.raises(HTTPException) as error:
        services.update_change_request(
            context.db, item.id, GisChangeRequestUpdate(justification="No"), context.admin
        )
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        services.reject_change_request(context.db, item.id, GisChangeRequestReview(), context.admin)
    assert error.value.status_code == 409
    assert context.db.get(GisChangeRequest, item.id).status == "approved"


def test_change_request_listing_does_not_leak_hidden_layers(context):
    item = change_request(context)
    assert services.list_change_requests(context.db, context.viewer) == []
    results = services.list_change_requests(
        context.db,
        context.admin,
        status_filter=GisChangeRequestStatus.submitted,
        layer_id=context.layer.id,
    )
    assert [result.id for result in results] == [item.id]


@pytest.mark.parametrize(
    "change_type,payload",
    [
        (
            GisChangeRequestType.geometry_update,
            {"geometry": {"type": "Point", "coordinates": [1, 2]}},
        ),
        (GisChangeRequestType.feature_delete, {"before": {"name": "Before"}}),
    ],
)
def test_apply_missing_feature_preserves_approved_request(context, change_type, payload):
    response = services.create_change_request(
        context.db,
        context.layer.id,
        GisChangeRequestCreate(feature_id="missing", change_type=change_type, payload=payload),
        context.admin,
    )
    services.approve_change_request(
        context.db, response.id, GisChangeRequestReview(), context.admin
    )
    with pytest.raises(HTTPException) as error:
        services.apply_change_request(context.db, response.id, context.admin)
    assert (error.value.status_code, error.value.detail) == (
        409,
        "GIS apply target feature not found",
    )
    context.db.rollback()
    assert context.db.get(GisChangeRequest, response.id).status == "approved"
    assert last_audit(context, "change_request.applied") is None


def test_review_timestamp_and_actor_are_persisted(context):
    item = change_request(context)
    services.reject_change_request(
        context.db, item.id, GisChangeRequestReview(review_notes=" Rejected "), context.admin
    )
    saved = context.db.get(GisChangeRequest, item.id)
    assert saved.review_notes == "Rejected"
    assert saved.reviewed_by_user_id == context.admin.id
    assert saved.reviewed_at.replace(tzinfo=UTC) <= datetime.now(UTC)
