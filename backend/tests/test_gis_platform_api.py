from __future__ import annotations

import json
import zipfile
from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.gis import exporter as gis_exporter
from app.modules.gis import services as gis_services
from app.modules.gis.bootstrap import (
    CATASTO_GIS_LAYER_DEFINITIONS,
    RIORDINO_GIS_LAYER_DEFINITIONS,
    ensure_catasto_gis_catalog,
    ensure_gis_platform_catalog,
    ensure_riordino_gis_catalog,
)
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


def seed_riordino_gis_catalog() -> int:
    db = TestingSessionLocal()
    try:
        return ensure_riordino_gis_catalog(db)
    finally:
        db.close()


def seed_gis_platform_catalog() -> dict[str, int]:
    db = TestingSessionLocal()
    try:
        return ensure_gis_platform_catalog(db)
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


def seed_export_source_table(table_name: str) -> None:
    db = TestingSessionLocal()
    try:
        quoted_table = f'"{table_name}"'
        db.execute(text(f"CREATE TABLE {quoted_table} (id TEXT PRIMARY KEY, coltura TEXT, active INTEGER, geometry TEXT)"))
        db.execute(
            text(f"INSERT INTO {quoted_table} (id, coltura, active, geometry) VALUES (:id, :coltura, :active, :geometry)"),
            [
                {
                    "id": "feature-1",
                    "coltura": "mais",
                    "active": 1,
                    "geometry": json.dumps({"type": "Point", "coordinates": [8.4, 39.9]}),
                },
                {
                    "id": "feature-2",
                    "coltura": "grano",
                    "active": 0,
                    "geometry": json.dumps({"type": "Point", "coordinates": [8.5, 40.0]}),
                },
                {
                    "id": "feature-3",
                    "coltura": "riposo",
                    "active": 0,
                    "geometry": None,
                },
            ],
        )
        db.commit()
    finally:
        db.close()


def seed_catalog_health_fixture_layers() -> None:
    db = TestingSessionLocal()
    try:
        warning_layer = GisLayer(
            workspace="rete",
            name="rete_qgis_warning",
            title="Rete QGIS warning",
            domain_module="network",
            source_type="postgis",
            official_source="postgis",
            postgis_schema="public",
            postgis_table="rete_qgis_warning",
            geometry_column="geometry",
            geometry_type="LINESTRING",
            metadata_json={"qgis": {"editable": True}},
            is_active=True,
        )
        bad_registry = GisLayer(
            workspace="riordino",
            name="riordino_registry_bad_policy",
            title="Registry Riordino senza policy",
            domain_module="riordino",
            source_type="domain_registry",
            official_source="riordino",
            postgis_table="riordino_registry_bad_policy",
            geometry_column=None,
            geometry_type=None,
            metadata_json={},
            is_active=True,
        )
        critical_layer = GisLayer(
            workspace="rete",
            name="rete_broken_postgis",
            title="Rete PostGIS incompleta",
            domain_module="network",
            source_type="postgis",
            official_source="postgis",
            postgis_schema="public",
            postgis_table=None,
            geometry_column=None,
            geometry_type=None,
            metadata_json={},
            is_active=True,
        )
        db.add_all([warning_layer, bad_registry, critical_layer])
        db.flush()
        critical_layer.geometry_column = None
        for layer in (warning_layer, bad_registry):
            db.add(
                GisLayerPermission(
                    layer_id=layer.id,
                    principal_type="role",
                    principal_key=ApplicationUserRole.VIEWER.value,
                    can_view=True,
                    can_annotate=False,
                    can_edit=False,
                    can_approve=False,
                    can_manage=False,
                )
            )
        db.commit()
    finally:
        db.close()


def test_gis_layers_require_authentication() -> None:
    response = client.get("/gis/layers")

    assert response.status_code == 401


def test_gis_catalog_dashboard_requires_authentication() -> None:
    response = client.get("/gis/catalog/dashboard")

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


def test_gis_platform_bootstrap_registers_riordino_domain_registry_without_qgis_or_export() -> None:
    assert seed_gis_platform_catalog() == {
        "catasto": len(CATASTO_GIS_LAYER_DEFINITIONS),
        "riordino": len(RIORDINO_GIS_LAYER_DEFINITIONS),
    }
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")

    all_layers = client.get("/gis/layers", headers=viewer_headers)
    response = client.get("/gis/layers?workspace=riordino&domain_module=riordino", headers=viewer_headers)

    assert all_layers.status_code == 200
    assert all_layers.json()["total"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == len(RIORDINO_GIS_LAYER_DEFINITIONS)
    layer = payload["items"][0]
    assert layer["workspace"] == "riordino"
    assert layer["name"] == "riordino_gis_links"
    assert layer["domain_module"] == "riordino"
    assert layer["source_type"] == "domain_registry"
    assert layer["official_source"] == "riordino"
    assert layer["postgis_schema"] is None
    assert layer["postgis_table"] == "riordino_gis_links"
    assert layer["geometry_column"] is None
    assert layer["geometry_type"] is None
    assert layer["martin_layer_id"] is None
    assert layer["metadata"]["read_only"] is True
    assert layer["metadata"]["registry"] == {
        "kind": "manual_feature_reference",
        "table": "riordino_gis_links",
        "route_pattern": "/riordino/practices/{practice_id}/gis-links",
        "managed_by": "riordino",
    }
    assert layer["metadata"]["qgis"] == {"mode": "not_published", "editable": False}
    assert layer["metadata"]["tiles"] == {"published": False, "reason": "non_geometric_domain_registry"}
    assert layer["metadata"]["export"] == {"shapefile": False, "reason": "non_geometric_domain_registry"}
    assert layer["effective_access_level"] == "viewer"
    assert layer["can_view"] is True
    assert layer["can_edit"] is False
    assert layer["can_approve"] is False

    governance = client.get("/gis/qgis/governance", headers=admin_headers)
    blocked_export = client.post(
        f"/gis/layers/{layer['id']}/export-shapefile",
        headers=admin_headers,
        json={"version_label": "riordino-registry"},
    )

    assert governance.status_code == 200
    assert {item["workspace"] for item in governance.json()["layers"]} == {"catasto"}
    assert "riordino_gis_links" not in governance.json()["sql"]
    assert blocked_export.status_code == 422
    assert blocked_export.json()["detail"] == "GIS shapefile export requires a PostGIS geometry layer"


def test_catalog_dashboard_reports_ok_for_seeded_platform_catalog() -> None:
    seed_gis_platform_catalog()
    admin_headers = auth_headers("gis-admin")

    response = client.get("/gis/catalog/dashboard", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["health_status"] == "ok"
    assert payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS)
    assert payload["active_layers"] == payload["total_layers"]
    assert payload["inactive_layers"] == 0
    assert payload["workspace_count"] == 2
    assert payload["source_type_counts"] == {"domain_registry": 1, "postgis": len(CATASTO_GIS_LAYER_DEFINITIONS)}
    assert payload["official_source_counts"] == {"postgis": len(CATASTO_GIS_LAYER_DEFINITIONS), "riordino": 1}
    assert payload["qgis_publishable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS)
    assert payload["exportable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS)
    assert payload["issues"] == []
    assert {item["workspace"]: item["health_status"] for item in payload["workspaces"]} == {
        "catasto": "ok",
        "riordino": "ok",
    }


def test_catalog_dashboard_reports_health_issues_and_respects_visibility() -> None:
    seed_gis_platform_catalog()
    seed_catalog_health_fixture_layers()
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")

    viewer_response = client.get("/gis/catalog/dashboard", headers=viewer_headers)
    admin_response = client.get("/gis/catalog/dashboard", headers=admin_headers)

    assert viewer_response.status_code == 200
    viewer_payload = viewer_response.json()
    assert viewer_payload["health_status"] == "warning"
    assert viewer_payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + 2
    assert viewer_payload["workspace_count"] == 3
    assert viewer_payload["qgis_publishable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + 1
    assert viewer_payload["exportable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + 1
    assert {item["code"] for item in viewer_payload["issues"]} == {
        "qgis_edit_policy_missing",
        "registry_qgis_policy_missing",
        "registry_export_policy_missing",
    }
    assert {item["severity"] for item in viewer_payload["issues"]} == {"warning"}
    assert {item["workspace"]: item["health_status"] for item in viewer_payload["workspaces"]} == {
        "catasto": "ok",
        "rete": "warning",
        "riordino": "warning",
    }

    assert admin_response.status_code == 200
    admin_payload = admin_response.json()
    assert admin_payload["health_status"] == "critical"
    assert admin_payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + 3
    assert admin_payload["source_type_counts"] == {"domain_registry": 2, "postgis": len(CATASTO_GIS_LAYER_DEFINITIONS) + 2}
    assert {
        "no_view_permission",
        "postgis_table_missing",
        "geometry_column_missing",
        "qgis_edit_policy_missing",
        "registry_qgis_policy_missing",
        "registry_export_policy_missing",
    }.issubset({item["code"] for item in admin_payload["issues"]})
    assert "critical" in {item["severity"] for item in admin_payload["issues"]}
    rete_summary = next(item for item in admin_payload["workspaces"] if item["workspace"] == "rete")
    assert rete_summary["health_status"] == "critical"
    assert rete_summary["issue_count"] == 4


def test_riordino_bootstrap_is_idempotent_and_repairs_viewer_permission() -> None:
    assert seed_riordino_gis_catalog() == len(RIORDINO_GIS_LAYER_DEFINITIONS)

    db = TestingSessionLocal()
    try:
        layer = db.scalar(select(GisLayer).where(GisLayer.workspace == "riordino", GisLayer.name == "riordino_gis_links"))
        assert layer is not None
        layer.title = "Mutated Riordino title"
        layer.source_type = "postgis"
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

    assert seed_riordino_gis_catalog() == 0

    db = TestingSessionLocal()
    try:
        layers = db.scalars(select(GisLayer).where(GisLayer.workspace == "riordino")).all()
        permissions = db.scalars(
            select(GisLayerPermission).join(GisLayer).where(
                GisLayer.workspace == "riordino",
                GisLayerPermission.principal_type == "role",
                GisLayerPermission.principal_key == ApplicationUserRole.VIEWER.value,
            )
        ).all()
        repaired_layer = db.scalar(select(GisLayer).where(GisLayer.workspace == "riordino", GisLayer.name == "riordino_gis_links"))
        repaired_permission = next(item for item in permissions if item.layer_id == repaired_layer.id)
        assert len(layers) == len(RIORDINO_GIS_LAYER_DEFINITIONS)
        assert len(permissions) == len(RIORDINO_GIS_LAYER_DEFINITIONS)
        assert repaired_layer.title == "Link GIS pratiche Riordino"
        assert repaired_layer.source_type == "domain_registry"
        assert repaired_layer.geometry_column is None
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


def test_qgis_governance_generates_read_only_views_and_controlled_edit_sql() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    catasto_layer = create_layer(admin_headers)
    editable_layer = create_layer(
        admin_headers,
        name="rete_condotte",
        workspace="rete",
        title="Rete condotte",
        domain_module="network",
        metadata={"qgis": {"mode": "controlled_edit", "editable": True, "edit_policy": "controlled"}},
    )
    read_only_network_layer = create_layer(
        admin_headers,
        name="rete_valvole",
        workspace="rete",
        title="Rete valvole",
        domain_module="network",
    )
    missing_policy_layer = create_layer(
        admin_headers,
        name="rete_pompe",
        workspace="rete",
        title="Rete pompe",
        domain_module="network",
        metadata={"qgis": {"editable": True}},
    )
    create_layer(
        admin_headers,
        name="archivio_shp",
        workspace="archivio",
        title="Archivio shapefile",
        domain_module="network",
        source_type="shapefile",
        official_source="nas",
    )

    forbidden = client.get("/gis/qgis/governance", headers=viewer_headers)
    governance = client.get("/gis/qgis/governance", headers=admin_headers)

    assert forbidden.status_code == 403
    assert governance.status_code == 200
    payload = governance.json()
    assert payload["schema"] == "gis_qgis"
    assert payload["roles"] == {
        "admin": "gaia_gis_qgis_admin",
        "reader": "gaia_gis_qgis_reader",
        "editor": "gaia_gis_qgis_editor",
    }
    assert payload["connection_policy"]["default_mode"] == "read_only"
    assert payload["connection_policy"]["nas_shapefile_policy"] == "export_backup_only"
    assert {item["layer_id"] for item in payload["layers"]} == {
        catasto_layer["id"],
        editable_layer["id"],
        read_only_network_layer["id"],
        missing_policy_layer["id"],
    }
    catasto_grant = next(item for item in payload["layers"] if item["layer_id"] == catasto_layer["id"])
    editable_grant = next(item for item in payload["layers"] if item["layer_id"] == editable_layer["id"])
    read_only_grant = next(item for item in payload["layers"] if item["layer_id"] == read_only_network_layer["id"])
    missing_policy_grant = next(item for item in payload["layers"] if item["layer_id"] == missing_policy_layer["id"])
    assert catasto_grant["editable"] is False
    assert catasto_grant["edit_role"] is None
    assert catasto_grant["edit_reason"] == "catasto_read_only"
    assert editable_grant["editable"] is True
    assert editable_grant["edit_role"] == "gaia_gis_qgis_editor"
    assert editable_grant["edit_reason"] == "controlled_edit_enabled"
    assert read_only_grant["edit_reason"] == "not_opted_in"
    assert missing_policy_grant["edit_reason"] == "missing_controlled_edit_policy"
    assert 'CREATE SCHEMA IF NOT EXISTS "gis_qgis";' in payload["statements"]
    assert 'CREATE OR REPLACE VIEW "gis_qgis".' in payload["sql"]
    assert 'GRANT SELECT ON "gis_qgis".' in payload["sql"]
    assert 'REVOKE INSERT, UPDATE, DELETE ON TABLE "public"."cat_particelle_current" FROM "gaia_gis_qgis_editor";' in payload["sql"]
    assert 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "public"."rete_condotte" TO "gaia_gis_qgis_editor";' in payload["sql"]
    assert "archivio_shp" not in payload["sql"]


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
    invalid_status = client.get("/gis/change-requests?status=invalid", headers=editor_headers)
    listed_for_layer = client.get(f"/gis/change-requests?layer_id={layer_id}&status=submitted", headers=editor_headers)
    apply_before_approval = client.post(f"/gis/change-requests/{change_request_id}/apply", headers=admin_headers)
    empty_update = client.patch(f"/gis/change-requests/{change_request_id}", headers=editor_headers, json={})
    null_type_update = client.patch(
        f"/gis/change-requests/{change_request_id}",
        headers=editor_headers,
        json={"change_type": None},
    )
    null_payload_update = client.patch(
        f"/gis/change-requests/{change_request_id}",
        headers=editor_headers,
        json={"payload": None},
    )
    needs_changes = client.post(
        f"/gis/change-requests/{change_request_id}/request-changes",
        headers=admin_headers,
        json={"review_notes": "  integra fonte  "},
    )
    updated = client.patch(
        f"/gis/change-requests/{change_request_id}",
        headers=editor_headers,
        json={
            "feature_id": "parcel-43",
            "change_type": "geometry_update",
            "payload": {"geometry": {"type": "Point", "coordinates": [8.4, 39.9]}},
            "justification": "  fonte QGIS integrata  ",
        },
    )
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
    update_approved = client.patch(
        f"/gis/change-requests/{change_request_id}",
        headers=editor_headers,
        json={"justification": "too late"},
    )
    applied = client.post(f"/gis/change-requests/{change_request_id}/apply", headers=admin_headers)
    update_applied = client.patch(
        f"/gis/change-requests/{change_request_id}",
        headers=editor_headers,
        json={"justification": "terminal"},
    )
    listed_for_editor = client.get("/gis/change-requests?status=approved", headers=editor_headers)
    listed_applied = client.get("/gis/change-requests?status=applied", headers=editor_headers)

    assert blocked_approval.status_code == 403
    assert invalid_status.status_code == 422
    assert listed_for_layer.status_code == 200
    assert listed_for_layer.json()[0]["id"] == change_request_id
    assert apply_before_approval.status_code == 409
    assert empty_update.status_code == 422
    assert null_type_update.status_code == 422
    assert null_payload_update.status_code == 422
    assert needs_changes.status_code == 200
    assert needs_changes.json()["status"] == "needs_changes"
    assert needs_changes.json()["review_notes"] == "integra fonte"
    assert updated.status_code == 200
    assert updated.json()["status"] == "submitted"
    assert updated.json()["feature_id"] == "parcel-43"
    assert updated.json()["change_type"] == "geometry_update"
    assert updated.json()["review_notes"] is None
    assert updated.json()["justification"] == "fonte QGIS integrata"
    assert updated.json()["payload"] == {"geometry": {"type": "Point", "coordinates": [8.4, 39.9]}}
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["review_notes"] == "validata"
    assert approved_again.status_code == 409
    assert update_approved.status_code == 409
    assert applied.status_code == 200
    assert applied.json()["status"] == "applied"
    assert update_applied.status_code == 409
    assert listed_for_editor.json() == []
    assert listed_applied.json()[0]["id"] == change_request_id

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "change_request.submitted" in audit_events
        assert "change_request.needs_changes" in audit_events
        assert "change_request.updated" in audit_events
        assert "change_request.approved" in audit_events
        assert "change_request.applied" in audit_events
        apply_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "change_request.applied"))
        assert apply_audit is not None
        assert apply_audit.payload_json["apply_result"] == {
            "mode": "no_op",
            "reason": "catasto domain apply policy not configured",
            "change_type": "geometry_update",
            "official_source": "postgis",
        }
    finally:
        db.close()


def test_change_request_payload_validation_reject_and_pluggable_validator() -> None:
    admin_headers = auth_headers("gis-admin")
    editor_headers = auth_headers("gis-editor")
    catasto_layer_id = create_layer(admin_headers)["id"]
    network_layer_id = create_layer(
        admin_headers,
        name="rete_condotte",
        workspace="rete",
        title="Rete condotte",
        domain_module="network",
        official_source="survey",
    )["id"]
    editor_id = user_id("gis-editor")

    for layer_id in (catasto_layer_id, network_layer_id):
        permission = client.post(
            f"/gis/layers/{layer_id}/permissions",
            headers=admin_headers,
            json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
        )
        assert permission.status_code == 200

    missing_feature = client.post(
        f"/gis/layers/{catasto_layer_id}/change-requests",
        headers=editor_headers,
        json={"change_type": "attribute_update", "payload": {"after": {"coltura": "mais"}}},
    )
    missing_geometry = client.post(
        f"/gis/layers/{catasto_layer_id}/change-requests",
        headers=editor_headers,
        json={"feature_id": "parcel-1", "change_type": "geometry_update", "payload": {"geometry": {}}},
    )
    geometry = client.post(
        f"/gis/layers/{catasto_layer_id}/change-requests",
        headers=editor_headers,
        json={
            "feature_id": "parcel-1",
            "change_type": "geometry_update",
            "payload": {"geometry": {"type": "Point", "coordinates": [8.4, 39.9]}},
        },
    )
    created = client.post(
        f"/gis/layers/{catasto_layer_id}/change-requests",
        headers=editor_headers,
        json={
            "change_type": "feature_create",
            "payload": {
                "geometry": {"type": "Point", "coordinates": [8.4, 39.9]},
                "properties": {"coltura": "mais"},
            },
        },
    )
    deleted = client.post(
        f"/gis/layers/{catasto_layer_id}/change-requests",
        headers=editor_headers,
        json={"feature_id": "parcel-2", "change_type": "feature_delete", "payload": {"before": {"coltura": "grano"}}},
    )

    assert missing_feature.status_code == 422
    assert missing_geometry.status_code == 422
    assert geometry.status_code == 201
    assert created.status_code == 201
    assert deleted.status_code == 201

    rejected = client.post(
        f"/gis/change-requests/{deleted.json()['id']}/reject",
        headers=admin_headers,
        json={"review_notes": "  duplicata  "},
    )
    terminal_approval = client.post(
        f"/gis/change-requests/{deleted.json()['id']}/approve",
        headers=admin_headers,
        json={"review_notes": "too late"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["review_notes"] == "duplicata"
    assert terminal_approval.status_code == 409

    def network_validator(layer: GisLayer, change_type, feature_id, payload) -> None:  # type: ignore[no-untyped-def]
        if payload.get("after", {}).get("locked") is True:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{layer.workspace}:{change_type.value}:{feature_id}",
            )

    gis_services.register_change_request_validator("network", network_validator)
    try:
        blocked_by_plugin = client.post(
            f"/gis/layers/{network_layer_id}/change-requests",
            headers=editor_headers,
            json={"feature_id": "pipe-1", "change_type": "attribute_update", "payload": {"after": {"locked": True}}},
        )
        network_change = client.post(
            f"/gis/layers/{network_layer_id}/change-requests",
            headers=editor_headers,
            json={"feature_id": "pipe-1", "change_type": "attribute_update", "payload": {"after": {"locked": False}}},
        )
    finally:
        gis_services.CHANGE_REQUEST_VALIDATORS.clear()

    assert blocked_by_plugin.status_code == 422
    assert network_change.status_code == 201

    approved = client.post(
        f"/gis/change-requests/{network_change.json()['id']}/approve",
        headers=admin_headers,
        json={"review_notes": "ok"},
    )
    applied = client.post(f"/gis/change-requests/{network_change.json()['id']}/apply", headers=admin_headers)
    assert approved.status_code == 200
    assert applied.status_code == 200

    db = TestingSessionLocal()
    try:
        network_apply_audit = db.scalar(
            select(GisAuditLog)
            .where(GisAuditLog.event_type == "change_request.applied", GisAuditLog.layer_id == UUID(network_layer_id))
            .order_by(GisAuditLog.created_at.desc())
        )
        assert network_apply_audit is not None
        assert network_apply_audit.payload_json["apply_result"]["reason"] == "apply adapter not configured"
    finally:
        db.close()


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
        json={"feature_id": "parcel-99", "change_type": "attribute_update", "payload": {"after": {"stato": "role-restored"}}},
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


def test_export_shapefile_creates_zip_manifest_checksum_and_audit_log(tmp_path: Path) -> None:
    admin_headers = auth_headers("gis-admin")
    layer_name = "cat_export_source"
    layer_id = create_layer(admin_headers, name=layer_name)["id"]
    seed_export_source_table(layer_name)
    nas_path = tmp_path / "gis" / "catasto" / "cat_export_source" / "v2026-07-13.zip"

    export = client.post(
        f"/gis/layers/{layer_id}/export-shapefile",
        headers=admin_headers,
        json={
            "version_label": "v2026-07-13",
            "checksum_sha256": "a" * 64,
            "nas_path": str(nas_path),
            "metadata": {"trigger": "manual"},
        },
    )

    assert export.status_code == 202
    payload = export.json()
    assert payload["status"] == "completed"
    assert payload["version_label"] == "v2026-07-13"
    assert payload["nas_path"] == str(nas_path)
    assert len(payload["checksum_sha256"]) == 64
    assert payload["checksum_sha256"] != "a" * 64
    assert payload["completed_at"] is not None
    assert payload["metadata"]["format"] == "shapefile"
    assert payload["metadata"]["source"] == "postgis"
    assert payload["metadata"]["trigger"] == "manual"
    assert payload["metadata"]["requested_checksum_sha256"] == "a" * 64
    assert payload["metadata"]["row_count"] == 3
    assert payload["metadata"]["published_atomically"] is True
    assert payload["metadata"]["manifest"]["field_mapping"] == {
        "id": "ID",
        "coltura": "COLTURA",
        "active": "ACTIVE",
    }
    assert nas_path.exists()

    with zipfile.ZipFile(nas_path) as archive:
        names = set(archive.namelist())
        assert names == {
            "cat_export_source.shp",
            "cat_export_source.shx",
            "cat_export_source.dbf",
            "cat_export_source.cpg",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["row_count"] == 3
    assert manifest["layer_name"] == layer_name
    assert manifest["metadata"] == {"trigger": "manual"}

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "layer.created" in audit_events
        assert "export.requested" in audit_events
        assert "export.completed" in audit_events
        completed_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "export.completed"))
        assert completed_audit is not None
        assert completed_audit.payload_json["checksum_sha256"] == payload["checksum_sha256"]
        assert completed_audit.payload_json["row_count"] == 3
    finally:
        db.close()


def test_export_shapefile_handles_empty_source_table(tmp_path: Path) -> None:
    admin_headers = auth_headers("gis-admin")
    layer_name = "empty_export_source"
    layer_id = create_layer(admin_headers, name=layer_name)["id"]
    db = TestingSessionLocal()
    try:
        db.execute(text(f'CREATE TABLE "{layer_name}" (geometry TEXT)'))
        db.commit()
    finally:
        db.close()
    nas_path = tmp_path / "empty.zip"

    export = client.post(
        f"/gis/layers/{layer_id}/export-shapefile",
        headers=admin_headers,
        json={"version_label": "empty", "nas_path": str(nas_path)},
    )

    assert export.status_code == 202
    payload = export.json()
    assert payload["status"] == "completed"
    assert payload["metadata"]["row_count"] == 0
    assert payload["metadata"]["manifest"]["field_mapping"] == {"_gaia_empty": "GAIA_EMPTY"}
    assert nas_path.exists()


def test_exporter_helper_edges_are_stable() -> None:
    layer = GisLayer(
        workspace="rete",
        name="pipe_export",
        title="Pipe export",
        postgis_schema="network",
        postgis_table="pipe-table",
        geometry_column="geom",
    )
    query, geometry_column, geometry_alias = gis_exporter._source_query(layer, "postgresql")
    assert str(query) == 'SELECT *, ST_AsGeoJSON("geom") AS __geometry_geojson FROM "network"."pipe-table"'
    assert geometry_column == "geom"
    assert geometry_alias == "__geometry_geojson"
    assert gis_exporter._load_geometry(None) is None
    assert gis_exporter._load_geometry({"type": "Point", "coordinates": [1, 2]}) == {"type": "Point", "coordinates": [1, 2]}
    with pytest.raises(gis_exporter.GisExportError):
        gis_exporter._load_geometry(42)

    used_names: set[str] = set()
    first_field = gis_exporter._field_name("field-name", used_names)
    second_field = gis_exporter._field_name("field name", used_names)
    assert first_field == "FIELD_NAME"
    assert second_field != first_field
    assert gis_exporter._record_value(None) == ""
    assert gis_exporter._record_value(True) == "true"
    assert gis_exporter._record_value({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert gis_exporter._shape_from_geometry(None) is None


def test_export_shapefile_marks_failures_without_publishing_zip(tmp_path: Path) -> None:
    admin_headers = auth_headers("gis-admin")
    layer_id = create_layer(admin_headers, name="missing_export_source")["id"]
    nas_path = tmp_path / "missing.zip"

    export = client.post(
        f"/gis/layers/{layer_id}/export-shapefile",
        headers=admin_headers,
        json={"version_label": "missing", "nas_path": str(nas_path)},
    )

    assert export.status_code == 202
    payload = export.json()
    assert payload["status"] == "failed"
    assert payload["checksum_sha256"] is None
    assert payload["completed_at"] is None
    assert "missing_export_source" in payload["metadata"]["error"]["message"]
    assert not nas_path.exists()

    db = TestingSessionLocal()
    try:
        failed_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "export.failed"))
        assert failed_audit is not None
        assert failed_audit.payload_json["version_label"] == "missing"
        assert "missing_export_source" in failed_audit.payload_json["error"]["message"]
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
