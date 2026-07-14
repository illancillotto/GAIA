from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.gis.bootstrap import CATASTO_GIS_LAYER_DEFINITIONS, ensure_catasto_gis_catalog
from app.modules.gis.models import GisAuditLog, GisLayer
from app.modules.gis.models import GisLayerPermission


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add_all(
        [
            ApplicationUser(
                username="gis-admin",
                email="gis-admin@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.ADMIN.value,
                is_active=True,
            ),
            ApplicationUser(
                username="gis-viewer",
                email="gis-viewer@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.VIEWER.value,
                is_active=True,
            ),
            ApplicationUser(
                username="gis-editor",
                email="gis-editor@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.OPERATOR.value,
                is_active=True,
            ),
        ]
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_layer(
    headers: dict[str, str],
    *,
    name: str = "cat_particelle_current",
    workspace: str = "catasto",
    title: str = "Particelle Catasto",
    domain_module: str | None = "catasto",
    source_type: str = "postgis",
    official_source: str = "postgis",
    metadata: dict | None = None,
) -> dict:
    response = client.post(
        "/gis/layers",
        headers=headers,
        json={
            "workspace": workspace,
            "name": name,
            "title": title,
            "description": "Layer operativo letto da PostGIS",
            "domain_module": domain_module,
            "source_type": source_type,
            "official_source": official_source,
            "postgis_table": name,
            "geometry_type": "MULTIPOLYGON",
            "martin_layer_id": name,
            "metadata": metadata or {"qgis": {"mode": "read_only"}},
        },
    )
    assert response.status_code == 201
    return response.json()


def seed_catasto_gis_catalog() -> int:
    db = TestingSessionLocal()
    try:
        return ensure_catasto_gis_catalog(db)
    finally:
        db.close()


def user_id(username: str) -> int:
    db = TestingSessionLocal()
    try:
        user = db.scalar(select(ApplicationUser).where(ApplicationUser.username == username))
        assert user is not None
        return user.id
    finally:
        db.close()


def test_gis_layers_require_authentication() -> None:
    response = client.get("/gis/layers")

    assert response.status_code == 401


def test_catasto_bootstrap_layers_are_visible_read_only_for_viewers() -> None:
    assert seed_catasto_gis_catalog() == len(CATASTO_GIS_LAYER_DEFINITIONS)
    viewer_headers = auth_headers("gis-viewer")

    response = client.get("/gis/layers", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    expected_names = {definition["name"] for definition in CATASTO_GIS_LAYER_DEFINITIONS}
    assert payload["total"] == len(expected_names)
    assert {item["name"] for item in payload["items"]} == expected_names
    for item in payload["items"]:
        assert item["workspace"] == "catasto"
        assert item["domain_module"] == "catasto"
        assert item["source_type"] == "postgis"
        assert item["official_source"] == "postgis"
        assert item["postgis_table"] == item["name"]
        assert item["martin_layer_id"] == item["name"]
        assert item["metadata"]["read_only"] is True
        assert item["metadata"]["qgis"] == {"mode": "read_only", "connection": "postgis", "editable": False}
        assert item["metadata"]["tiles"]["provider"] == "martin"
        assert item["effective_access_level"] == "viewer"
        assert item["can_view"] is True
        assert item["can_annotate"] is False
        assert item["can_edit"] is False
        assert item["can_approve"] is False
        assert item["can_manage"] is False

    layer_id = payload["items"][0]["id"]
    blocked_annotation = client.post(
        f"/gis/layers/{layer_id}/annotations",
        headers=viewer_headers,
        json={"title": "Nota", "body": "Non concessa dal seed read-only"},
    )
    blocked_change = client.post(
        f"/gis/layers/{layer_id}/change-requests",
        headers=viewer_headers,
        json={"change_type": "attribute_update", "payload": {"after": {"stato": "test"}}},
    )
    blocked_export = client.post(
        f"/gis/layers/{layer_id}/export-shapefile",
        headers=viewer_headers,
        json={"version_label": "blocked"},
    )
    assert blocked_annotation.status_code == 403
    assert blocked_change.status_code == 403
    assert blocked_export.status_code == 403


def test_catasto_bootstrap_is_idempotent_and_repairs_viewer_permission() -> None:
    assert seed_catasto_gis_catalog() == len(CATASTO_GIS_LAYER_DEFINITIONS)

    db = TestingSessionLocal()
    try:
        layer = db.scalar(select(GisLayer).where(GisLayer.name == "cat_particelle_current"))
        assert layer is not None
        layer.title = "Mutated title"
        permission = db.scalar(
            select(GisLayerPermission).where(
                GisLayerPermission.layer_id == layer.id,
                GisLayerPermission.principal_type == "role",
                GisLayerPermission.principal_key == ApplicationUserRole.VIEWER.value,
            )
        )
        assert permission is not None
        permission.can_edit = True
        permission.can_approve = True
        permission.can_manage = True
        db.commit()
    finally:
        db.close()

    assert seed_catasto_gis_catalog() == 0

    db = TestingSessionLocal()
    try:
        layers = db.scalars(select(GisLayer).where(GisLayer.workspace == "catasto")).all()
        permissions = db.scalars(
            select(GisLayerPermission).join(GisLayer).where(
                GisLayer.workspace == "catasto",
                GisLayerPermission.principal_type == "role",
                GisLayerPermission.principal_key == ApplicationUserRole.VIEWER.value,
            )
        ).all()
        repaired_layer = db.scalar(select(GisLayer).where(GisLayer.name == "cat_particelle_current"))
        repaired_permission = next(item for item in permissions if item.layer_id == repaired_layer.id)
        assert len(layers) == len(CATASTO_GIS_LAYER_DEFINITIONS)
        assert len(permissions) == len(CATASTO_GIS_LAYER_DEFINITIONS)
        assert repaired_layer.title == "Particelle catastali correnti"
        assert repaired_permission.can_view is True
        assert repaired_permission.can_annotate is False
        assert repaired_permission.can_edit is False
        assert repaired_permission.can_approve is False
        assert repaired_permission.can_manage is False
    finally:
        db.close()


def test_catasto_gis_router_remains_registered_separately_from_gis_platform() -> None:
    route_modules = {route.path: route.endpoint.__module__ for route in app.routes if hasattr(route, "endpoint")}

    assert route_modules["/catasto/gis/dui/latest-layer"] == "app.modules.catasto.routes.gis"
    assert route_modules["/catasto/gis/ade-wfs/sync-bbox"] == "app.modules.catasto.routes.gis"
    assert route_modules["/gis/layers"] == "app.modules.gis.router"


def test_admin_creates_lists_filters_and_detects_duplicate_layers() -> None:
    headers = auth_headers("gis-admin")
    layer = create_layer(headers)

    assert layer["workspace"] == "catasto"
    assert layer["official_source"] == "postgis"
    assert layer["effective_access_level"] == "admin"
    assert layer["can_manage"] is True
    assert layer["metadata"] == {"qgis": {"mode": "read_only"}}

    list_response = client.get("/gis/layers", headers=headers)
    workspace_response = client.get("/gis/workspaces/catasto/layers", headers=headers)
    empty_workspace_response = client.get("/gis/workspaces/rete/layers", headers=headers)
    duplicate_response = client.post(
        "/gis/layers",
        headers=headers,
        json={"workspace": "catasto", "name": "cat_particelle_current", "title": "Duplicato"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert workspace_response.json()["items"][0]["id"] == layer["id"]
    assert empty_workspace_response.json() == {"items": [], "total": 0}
    assert duplicate_response.status_code == 409


def test_catalog_filters_and_active_scope_keep_viewers_read_only() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    catasto_layer = create_layer(admin_headers)
    network_layer = create_layer(
        admin_headers,
        name="rete_condotte",
        workspace="rete",
        title="Rete condotte",
        domain_module="network",
        official_source="survey",
    )

    for layer_id in (catasto_layer["id"], network_layer["id"]):
        permission = client.post(
            f"/gis/layers/{layer_id}/permissions",
            headers=admin_headers,
            json={"principal_type": "role", "principal_key": "viewer", "access_level": "viewer"},
        )
        assert permission.status_code == 200

    deactivated = client.post(f"/gis/layers/{network_layer['id']}/deactivate", headers=admin_headers)
    catasto_filtered = client.get(
        "/gis/layers?workspace=catasto&domain_module=catasto&source_type=postgis&official_source=postgis&is_active=true",
        headers=admin_headers,
    )
    inactive_filtered = client.get("/gis/layers?is_active=false&official_source=survey", headers=admin_headers)
    viewer_forced_inactive = client.get("/gis/layers?is_active=false", headers=viewer_headers)

    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert catasto_filtered.status_code == 200
    assert catasto_filtered.json()["total"] == 1
    assert catasto_filtered.json()["items"][0]["id"] == catasto_layer["id"]
    assert inactive_filtered.json()["total"] == 1
    assert inactive_filtered.json()["items"][0]["id"] == network_layer["id"]
    assert viewer_forced_inactive.json()["total"] == 1
    assert viewer_forced_inactive.json()["items"][0]["id"] == catasto_layer["id"]


def test_admin_updates_layer_metadata_with_audit_and_field_guardrails() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    layer = create_layer(admin_headers)

    forbidden = client.patch(
        f"/gis/layers/{layer['id']}/metadata",
        headers=viewer_headers,
        json={"description": "viewer blocked"},
    )
    empty_update = client.patch(f"/gis/layers/{layer['id']}/metadata", headers=admin_headers, json={})
    null_title = client.patch(f"/gis/layers/{layer['id']}/metadata", headers=admin_headers, json={"title": None})
    critical_field = client.patch(
        f"/gis/layers/{layer['id']}/metadata",
        headers=admin_headers,
        json={"workspace": "blocked"},
    )
    updated = client.patch(
        f"/gis/layers/{layer['id']}/metadata",
        headers=admin_headers,
        json={
            "title": "  Catasto pubblicato  ",
            "description": "  Metadati descrittivi aggiornati  ",
            "ogc_service_url": "  https://gis.example.local/wms  ",
            "qgis_project_path": "  /srv/qgis/catasto.qgz  ",
            "nas_export_root": "  /volume1/Backups/GAIA/gis/catasto  ",
            "metadata": {"qgis": {"mode": "read_only"}, "owner": "gis-platform"},
        },
    )

    assert forbidden.status_code == 403
    assert empty_update.status_code == 422
    assert null_title.status_code == 422
    assert critical_field.status_code == 422
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["title"] == "Catasto pubblicato"
    assert payload["description"] == "Metadati descrittivi aggiornati"
    assert payload["ogc_service_url"] == "https://gis.example.local/wms"
    assert payload["qgis_project_path"] == "/srv/qgis/catasto.qgz"
    assert payload["nas_export_root"] == "/volume1/Backups/GAIA/gis/catasto"
    assert payload["metadata"] == {"qgis": {"mode": "read_only"}, "owner": "gis-platform"}
    assert payload["workspace"] == "catasto"
    assert payload["postgis_table"] == "cat_particelle_current"

    db = TestingSessionLocal()
    try:
        audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "layer.metadata_updated"))
        assert audit is not None
        assert audit.payload_json == {
            "changed_fields": [
                "title",
                "description",
                "ogc_service_url",
                "qgis_project_path",
                "nas_export_root",
                "metadata_json",
            ]
        }
    finally:
        db.close()


def test_layer_permissions_gate_visibility_and_annotations() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    layer_id = create_layer(admin_headers)["id"]

    forbidden_detail = client.get(f"/gis/layers/{layer_id}", headers=viewer_headers)
    assert forbidden_detail.status_code == 403
    assert client.get("/gis/layers", headers=viewer_headers).json() == {"items": [], "total": 0}

    viewer_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": "viewer", "access_level": "viewer"},
    )
    assert viewer_permission.status_code == 200
    assert viewer_permission.json()["can_view"] is True
    assert viewer_permission.json()["can_annotate"] is False

    visible_layers = client.get("/gis/layers", headers=viewer_headers).json()
    visible_detail = client.get(f"/gis/layers/{layer_id}", headers=viewer_headers)
    assert visible_layers["total"] == 1
    assert visible_layers["items"][0]["effective_access_level"] == "viewer"
    assert visible_detail.status_code == 200
    assert visible_detail.json()["id"] == layer_id

    read_annotations = client.get(f"/gis/layers/{layer_id}/annotations", headers=viewer_headers)
    blocked_annotation = client.post(
        f"/gis/layers/{layer_id}/annotations",
        headers=viewer_headers,
        json={"title": "Sopralluogo", "body": "Nota separata dal dato ufficiale"},
    )
    blocked_permissions = client.get(f"/gis/layers/{layer_id}/permissions", headers=viewer_headers)
    assert read_annotations.status_code == 200
    assert read_annotations.json() == []
    assert blocked_annotation.status_code == 403
    assert blocked_permissions.status_code == 403
    assert client.get(f"/gis/layers/{layer_id}/permissions", headers=admin_headers).json()[0]["principal_key"] == "viewer"

    annotator_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": "viewer", "access_level": "annotator"},
    )
    annotation = client.post(
        f"/gis/layers/{layer_id}/annotations",
        headers=viewer_headers,
        json={
            "feature_id": "parcel-1",
            "title": "  Marker campo  ",
            "body": "  Verificare confine  ",
            "geometry": {"type": "Point", "coordinates": [8.5, 39.8]},
            "attachment_refs": [{"filename": "foto.jpg", "storage_path": "/nas/foto.jpg"}],
        },
    )
    listed = client.get(f"/gis/layers/{layer_id}/annotations", headers=viewer_headers)

    assert annotator_permission.status_code == 200
    assert annotator_permission.json()["access_level"] == "annotator"
    assert annotation.status_code == 201
    assert annotation.json()["title"] == "Marker campo"
    assert annotation.json()["geometry"]["type"] == "Point"
    assert listed.json()[0]["attachment_refs"][0]["filename"] == "foto.jpg"


def test_annotation_lifecycle_filters_updates_permissions_and_audit() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    layer_id = create_layer(admin_headers)["id"]
    other_layer_id = create_layer(admin_headers, name="cat_distretti")["id"]

    permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": "viewer", "access_level": "annotator"},
    )
    assert permission.status_code == 200

    annotation = client.post(
        f"/gis/layers/{layer_id}/annotations",
        headers=viewer_headers,
        json={
            "feature_id": "parcel-1",
            "title": "  Nota campo  ",
            "body": "  Primo testo  ",
            "geometry": {"type": "Point", "coordinates": [8.4, 39.9]},
            "attachment_refs": [{"filename": "prima.jpg"}],
        },
    )
    rejected_source = client.post(
        f"/gis/layers/{layer_id}/annotations",
        headers=viewer_headers,
        json={"feature_id": "parcel-2", "title": "Da rigettare", "body": "Duplicata"},
    )
    annotation_id = annotation.json()["id"]
    rejected_annotation_id = rejected_source.json()["id"]

    assert annotation.status_code == 201
    assert annotation.json()["status"] == "open"

    open_annotations = client.get(f"/gis/layers/{layer_id}/annotations?status=open", headers=viewer_headers)
    feature_annotations = client.get(f"/gis/layers/{layer_id}/annotations?feature_id=parcel-1", headers=viewer_headers)
    invalid_status = client.get(f"/gis/layers/{layer_id}/annotations?status=invalid", headers=viewer_headers)
    missing_update = client.patch(
        f"/gis/layers/{layer_id}/annotations/00000000-0000-0000-0000-000000000003",
        headers=viewer_headers,
        json={"title": "missing"},
    )
    wrong_layer_update = client.patch(
        f"/gis/layers/{other_layer_id}/annotations/{annotation_id}",
        headers=admin_headers,
        json={"title": "wrong layer"},
    )
    empty_update = client.patch(f"/gis/layers/{layer_id}/annotations/{annotation_id}", headers=viewer_headers, json={})
    null_title = client.patch(f"/gis/layers/{layer_id}/annotations/{annotation_id}", headers=viewer_headers, json={"title": None})
    null_body = client.patch(f"/gis/layers/{layer_id}/annotations/{annotation_id}", headers=viewer_headers, json={"body": None})
    updated = client.patch(
        f"/gis/layers/{layer_id}/annotations/{annotation_id}",
        headers=viewer_headers,
        json={
            "title": "  Nota aggiornata  ",
            "body": "  Testo aggiornato  ",
            "geometry": None,
            "attachment_refs": [{"filename": "seconda.jpg", "storage_path": "/nas/seconda.jpg"}],
        },
    )
    in_review = client.post(f"/gis/layers/{layer_id}/annotations/{annotation_id}/in-review", headers=viewer_headers)
    blocked_close = client.post(f"/gis/layers/{layer_id}/annotations/{annotation_id}/close", headers=viewer_headers)
    closed = client.post(f"/gis/layers/{layer_id}/annotations/{annotation_id}/close", headers=admin_headers)
    rejected = client.post(f"/gis/layers/{layer_id}/annotations/{rejected_annotation_id}/reject", headers=admin_headers)
    closed_update = client.patch(
        f"/gis/layers/{layer_id}/annotations/{annotation_id}",
        headers=viewer_headers,
        json={"body": "should be blocked"},
    )
    closed_transition = client.post(f"/gis/layers/{layer_id}/annotations/{annotation_id}/in-review", headers=admin_headers)
    rejected_transition = client.post(f"/gis/layers/{layer_id}/annotations/{rejected_annotation_id}/close", headers=admin_headers)

    assert open_annotations.status_code == 200
    assert open_annotations.json()[0]["status"] == "open"
    assert {item["feature_id"] for item in open_annotations.json()} == {"parcel-1", "parcel-2"}
    assert feature_annotations.status_code == 200
    assert [item["id"] for item in feature_annotations.json()] == [annotation_id]
    assert invalid_status.status_code == 422
    assert missing_update.status_code == 404
    assert wrong_layer_update.status_code == 404
    assert empty_update.status_code == 422
    assert null_title.status_code == 422
    assert null_body.status_code == 422
    assert updated.status_code == 200
    assert updated.json()["title"] == "Nota aggiornata"
    assert updated.json()["body"] == "Testo aggiornato"
    assert updated.json()["geometry"] is None
    assert updated.json()["attachment_refs"][0]["filename"] == "seconda.jpg"
    assert in_review.status_code == 200
    assert in_review.json()["status"] == "in_review"
    assert blocked_close.status_code == 403
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert closed_update.status_code == 409
    assert closed_transition.status_code == 409
    assert rejected_transition.status_code == 409

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "annotation.created" in audit_events
        assert "annotation.updated" in audit_events
        assert "annotation.in_review" in audit_events
        assert "annotation.closed" in audit_events
        assert "annotation.rejected" in audit_events
    finally:
        db.close()


def test_user_editor_change_request_and_admin_approval_workflow() -> None:
    admin_headers = auth_headers("gis-admin")
    editor_headers = auth_headers("gis-editor")
    layer_id = create_layer(admin_headers)["id"]
    editor_id = user_id("gis-editor")

    permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
    )
    change_request = client.post(
        f"/gis/layers/{layer_id}/change-requests",
        headers=editor_headers,
        json={
            "feature_id": "parcel-42",
            "change_type": "attribute_update",
            "payload": {"after": {"coltura": "mais"}},
            "justification": "  richiesta tecnico QGIS  ",
        },
    )

    assert permission.status_code == 200
    assert permission.json()["access_level"] == "editor"
    assert change_request.status_code == 201
    assert change_request.json()["status"] == "submitted"
    assert change_request.json()["justification"] == "richiesta tecnico QGIS"

    change_request_id = change_request.json()["id"]
    blocked_approval = client.post(
        f"/gis/change-requests/{change_request_id}/approve",
        headers=editor_headers,
        json={"review_notes": "ok"},
    )
    approved = client.post(
        f"/gis/change-requests/{change_request_id}/approve",
        headers=admin_headers,
        json={"review_notes": "  validata  "},
    )
    approved_again = client.post(
        f"/gis/change-requests/{change_request_id}/approve",
        headers=admin_headers,
        json={},
    )
    listed_for_editor = client.get("/gis/change-requests?status=approved", headers=editor_headers)

    assert blocked_approval.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["review_notes"] == "validata"
    assert approved_again.status_code == 409
    assert listed_for_editor.json()[0]["id"] == change_request_id


def test_permission_revoke_role_validation_audit_and_user_override_precedence() -> None:
    admin_headers = auth_headers("gis-admin")
    editor_headers = auth_headers("gis-editor")
    viewer_headers = auth_headers("gis-viewer")
    layer_id = create_layer(admin_headers)["id"]
    other_layer_id = create_layer(admin_headers, name="cat_distretti")["id"]
    editor_id = user_id("gis-editor")

    invalid_role = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": "unknown-role", "access_level": "viewer"},
    )
    role_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": ApplicationUserRole.OPERATOR.value, "access_level": "approver"},
    )
    updated_role_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "role", "principal_key": ApplicationUserRole.OPERATOR.value, "access_level": "admin"},
    )
    user_override = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "viewer"},
    )

    assert invalid_role.status_code == 422
    assert role_permission.status_code == 200
    assert role_permission.json()["access_level"] == "approver"
    assert updated_role_permission.status_code == 200
    assert updated_role_permission.json()["access_level"] == "admin"
    assert updated_role_permission.json()["id"] == role_permission.json()["id"]
    assert user_override.status_code == 200

    overridden_detail = client.get(f"/gis/layers/{layer_id}", headers=editor_headers)
    blocked_change = client.post(
        f"/gis/layers/{layer_id}/change-requests",
        headers=editor_headers,
        json={"change_type": "attribute_update", "payload": {"after": {"stato": "blocked-by-user-override"}}},
    )
    blocked_revoke = client.delete(
        f"/gis/layers/{layer_id}/permissions/{user_override.json()['id']}",
        headers=viewer_headers,
    )
    wrong_layer_revoke = client.delete(
        f"/gis/layers/{other_layer_id}/permissions/{user_override.json()['id']}",
        headers=admin_headers,
    )
    missing_revoke = client.delete(
        f"/gis/layers/{layer_id}/permissions/00000000-0000-0000-0000-000000000002",
        headers=admin_headers,
    )
    revoked = client.delete(
        f"/gis/layers/{layer_id}/permissions/{user_override.json()['id']}",
        headers=admin_headers,
    )
    role_detail_after_revoke = client.get(f"/gis/layers/{layer_id}", headers=editor_headers)
    allowed_change = client.post(
        f"/gis/layers/{layer_id}/change-requests",
        headers=editor_headers,
        json={"change_type": "attribute_update", "payload": {"after": {"stato": "role-restored"}}},
    )
    permissions_after_revoke = client.get(f"/gis/layers/{layer_id}/permissions", headers=admin_headers)

    assert overridden_detail.status_code == 200
    assert overridden_detail.json()["effective_access_level"] == "viewer"
    assert overridden_detail.json()["can_edit"] is False
    assert blocked_change.status_code == 403
    assert blocked_revoke.status_code == 403
    assert wrong_layer_revoke.status_code == 404
    assert missing_revoke.status_code == 404
    assert revoked.status_code == 204
    assert role_detail_after_revoke.json()["effective_access_level"] == "admin"
    assert role_detail_after_revoke.json()["can_manage"] is True
    assert allowed_change.status_code == 201
    assert [item["id"] for item in permissions_after_revoke.json()] == [role_permission.json()["id"]]

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "permission.granted" in audit_events
        assert "permission.updated" in audit_events
        assert "permission.revoked" in audit_events
        revoke_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "permission.revoked"))
        assert revoke_audit is not None
        assert revoke_audit.payload_json == {
            "principal_type": "user",
            "principal_key": str(editor_id),
            "access_level": "viewer",
        }
    finally:
        db.close()


def test_export_shapefile_creates_nas_metadata_contract_and_audit_log() -> None:
    admin_headers = auth_headers("gis-admin")
    layer_id = create_layer(admin_headers)["id"]

    export = client.post(
        f"/gis/layers/{layer_id}/export-shapefile",
        headers=admin_headers,
        json={
            "version_label": "v2026-07-13",
            "checksum_sha256": "a" * 64,
            "metadata": {"trigger": "manual"},
        },
    )

    assert export.status_code == 202
    assert export.json()["status"] == "requested"
    assert export.json()["version_label"] == "v2026-07-13"
    assert export.json()["nas_path"].endswith("/catasto/cat_particelle_current/v2026-07-13.zip")
    assert export.json()["metadata"] == {"format": "shapefile", "source": "postgis", "trigger": "manual"}

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "layer.created" in audit_events
        assert "export.requested" in audit_events
    finally:
        db.close()


def test_unknown_layer_and_change_request_return_not_found() -> None:
    admin_headers = auth_headers("gis-admin")
    missing_id = "00000000-0000-0000-0000-000000000001"

    assert client.get(f"/gis/layers/{missing_id}", headers=admin_headers).status_code == 404
    assert client.patch(f"/gis/layers/{missing_id}/metadata", headers=admin_headers, json={"description": "missing"}).status_code == 404
    assert client.post(f"/gis/layers/{missing_id}/activate", headers=admin_headers).status_code == 404
    assert client.post(
        f"/gis/change-requests/{missing_id}/approve",
        headers=admin_headers,
        json={},
    ).status_code == 404


def test_non_admin_cannot_create_layers_or_invalid_user_permission() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    layer_id = create_layer(admin_headers)["id"]

    create_response = client.post(
        "/gis/layers",
        headers=viewer_headers,
        json={"workspace": "catasto", "name": "blocked", "title": "Blocked"},
    )
    invalid_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": "not-int", "access_level": "viewer"},
    )
    missing_user_permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": "999999", "access_level": "viewer"},
    )

    assert create_response.status_code == 403
    assert invalid_permission.status_code == 422
    assert missing_user_permission.status_code == 404
    assert client.get("/gis/change-requests", headers=viewer_headers).json() == []


def test_admin_can_toggle_inactive_layers_while_viewers_do_not_see_them() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    layer_id = UUID(create_layer(admin_headers)["id"])

    blocked = client.post(f"/gis/layers/{layer_id}/deactivate", headers=viewer_headers)
    deactivated = client.post(f"/gis/layers/{layer_id}/deactivate", headers=admin_headers)
    inactive_catalog = client.get("/gis/layers?is_active=false", headers=admin_headers)
    active_catalog = client.get("/gis/layers?is_active=true", headers=admin_headers)
    viewer_catalog = client.get("/gis/layers", headers=viewer_headers)

    assert blocked.status_code == 403
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get(f"/gis/layers/{layer_id}", headers=admin_headers).status_code == 404
    assert inactive_catalog.json()["total"] == 1
    assert inactive_catalog.json()["items"][0]["id"] == str(layer_id)
    assert active_catalog.json() == {"items": [], "total": 0}
    assert viewer_catalog.json() == {"items": [], "total": 0}

    reactivated = client.post(f"/gis/layers/{layer_id}/activate", headers=admin_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "layer.deactivated" in audit_events
        assert "layer.activated" in audit_events
    finally:
        db.close()
