from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
import shapefile
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
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
    NETWORK_GIS_LAYER_DEFINITIONS,
    RIORDINO_GIS_LAYER_DEFINITIONS,
    ensure_catasto_gis_catalog,
    ensure_gis_platform_catalog,
    ensure_network_gis_catalog,
    ensure_riordino_gis_catalog,
)
from app.modules.gis.models import GisAuditLog, GisChangeRequest, GisLayer, GisLayerExport, GisShapefileImport
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


def seed_network_gis_catalog() -> int:
    db = TestingSessionLocal()
    try:
        return ensure_network_gis_catalog(db)
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


def build_point_shapefile_zip(
    *,
    include_prj: bool = True,
    include_cpg: bool = True,
    empty: bool = False,
    second_shapefile: bool = False,
    unsafe_name: bool = False,
    cpg_text: str = "UTF-8",
) -> bytes:
    shp = io.BytesIO()
    shx = io.BytesIO()
    dbf = io.BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POINT)
    writer.field("name", "C")
    writer.field("active", "L")
    writer.field("when", "D")
    if not empty:
        writer.point(8.4, 39.9)
        writer.record("feature-1", True, date(2026, 7, 14))
        writer.point(8.5, 40.0)
        writer.record("feature-2", False, date(2026, 7, 15))
    writer.close()

    prefix = "../unsafe/rete" if unsafe_name else "shape/rete"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("shape/", b"")
        archive.writestr(f"{prefix}.shp", shp.getvalue())
        archive.writestr(f"{prefix}.shx", shx.getvalue())
        archive.writestr(f"{prefix}.dbf", dbf.getvalue())
        if include_prj:
            archive.writestr(f"{prefix}.prj", 'GEOGCS["WGS 84"]')
        if include_cpg:
            archive.writestr(f"{prefix}.cpg", cpg_text)
        if second_shapefile:
            archive.writestr("other/alt.shp", shp.getvalue())
            archive.writestr("other/alt.shx", shx.getvalue())
            archive.writestr("other/alt.dbf", dbf.getvalue())
            archive.writestr("other/alt.prj", 'GEOGCS["WGS 84"]')
    return buffer.getvalue()


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


def seed_apply_source_table(table_name: str) -> None:
    db = TestingSessionLocal()
    try:
        quoted_table = f'"{table_name}"'
        db.execute(text(f"CREATE TABLE {quoted_table} (id TEXT PRIMARY KEY, name TEXT, diameter INTEGER, geometry TEXT)"))
        db.execute(
            text(f"INSERT INTO {quoted_table} (id, name, diameter, geometry) VALUES (:id, :name, :diameter, :geometry)"),
            [
                {
                    "id": "pipe-1",
                    "name": "Condotta 1",
                    "diameter": 120,
                    "geometry": json.dumps({"type": "LineString", "coordinates": [[8.4, 39.9], [8.5, 40.0]]}),
                },
                {
                    "id": "pipe-delete",
                    "name": "Da rimuovere",
                    "diameter": 90,
                    "geometry": json.dumps({"type": "LineString", "coordinates": [[8.6, 40.1], [8.7, 40.2]]}),
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


def test_catalog_dashboard_handles_empty_visible_catalog() -> None:
    viewer_headers = auth_headers("gis-viewer")

    response = client.get("/gis/catalog/dashboard", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["health_status"] == "ok"
    assert payload["total_layers"] == 0
    assert payload["latest_exports"] == []
    assert payload["workspaces"] == []


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


def test_gis_platform_bootstrap_registers_riordino_registry_and_network_controlled_edit_layer() -> None:
    assert seed_gis_platform_catalog() == {
        "catasto": len(CATASTO_GIS_LAYER_DEFINITIONS),
        "riordino": len(RIORDINO_GIS_LAYER_DEFINITIONS),
        "rete": len(NETWORK_GIS_LAYER_DEFINITIONS),
    }
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    operator_headers = auth_headers("gis-editor")

    all_layers = client.get("/gis/layers", headers=viewer_headers)
    riordino_response = client.get("/gis/layers?workspace=riordino&domain_module=riordino", headers=viewer_headers)
    network_viewer_response = client.get("/gis/layers?workspace=rete&domain_module=network", headers=viewer_headers)
    network_operator_response = client.get("/gis/layers?workspace=rete&domain_module=network", headers=operator_headers)

    assert all_layers.status_code == 200
    assert all_layers.json()["total"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert riordino_response.status_code == 200
    payload = riordino_response.json()
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

    assert network_viewer_response.status_code == 200
    network_viewer_layer = network_viewer_response.json()["items"][0]
    assert network_viewer_layer["workspace"] == "rete"
    assert network_viewer_layer["name"] == "rete_condotte"
    assert network_viewer_layer["domain_module"] == "network"
    assert network_viewer_layer["source_type"] == "postgis"
    assert network_viewer_layer["official_source"] == "network"
    assert network_viewer_layer["postgis_schema"] == "network"
    assert network_viewer_layer["postgis_table"] == "rete_condotte"
    assert network_viewer_layer["geometry_type"] == "MULTILINESTRING"
    assert network_viewer_layer["metadata"]["qgis"] == {
        "mode": "controlled_edit",
        "connection": "postgis",
        "editable": True,
        "edit_policy": "controlled",
    }
    assert network_viewer_layer["metadata"]["export"] == {"shapefile": True, "reason": "versioned_backup_allowed"}
    assert network_viewer_layer["effective_access_level"] == "viewer"
    assert network_viewer_layer["can_edit"] is False
    assert network_operator_response.json()["items"][0]["effective_access_level"] == "editor"
    assert network_operator_response.json()["items"][0]["can_edit"] is True

    governance = client.get("/gis/qgis/governance", headers=admin_headers)
    blocked_export = client.post(
        f"/gis/layers/{layer['id']}/export-shapefile",
        headers=admin_headers,
        json={"version_label": "riordino-registry"},
    )

    assert governance.status_code == 200
    assert {item["workspace"] for item in governance.json()["layers"]} == {"catasto", "rete"}
    network_grant = next(item for item in governance.json()["layers"] if item["workspace"] == "rete")
    assert network_grant["editable"] is True
    assert network_grant["edit_role"] == "gaia_gis_qgis_editor"
    assert network_grant["edit_reason"] == "controlled_edit_enabled"
    assert "riordino_gis_links" not in governance.json()["sql"]
    assert 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "network"."rete_condotte" TO "gaia_gis_qgis_editor";' in governance.json()["sql"]
    assert blocked_export.status_code == 422
    assert blocked_export.json()["detail"] == "GIS shapefile export requires a PostGIS geometry layer"


def test_catalog_dashboard_reports_ok_for_seeded_platform_catalog() -> None:
    seed_gis_platform_catalog()
    admin_headers = auth_headers("gis-admin")

    response = client.get("/gis/catalog/dashboard", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["health_status"] == "ok"
    assert payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert payload["active_layers"] == payload["total_layers"]
    assert payload["inactive_layers"] == 0
    assert payload["workspace_count"] == 3
    assert payload["source_type_counts"] == {"domain_registry": 1, "postgis": len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)}
    assert payload["official_source_counts"] == {"network": 1, "postgis": len(CATASTO_GIS_LAYER_DEFINITIONS), "riordino": 1}
    assert payload["qgis_publishable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert payload["exportable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert payload["issues"] == []
    assert payload["latest_exports"] == []
    assert {item["workspace"]: item["health_status"] for item in payload["workspaces"]} == {
        "catasto": "ok",
        "rete": "ok",
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
    assert viewer_payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS) + 2
    assert viewer_payload["workspace_count"] == 3
    assert viewer_payload["qgis_publishable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS) + 1
    assert viewer_payload["exportable_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS) + 1
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
    assert admin_payload["total_layers"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(RIORDINO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS) + 3
    assert admin_payload["source_type_counts"] == {"domain_registry": 2, "postgis": len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS) + 2}
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


def test_qgis_project_download_includes_only_visible_publishable_postgis_layers() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    visible_layer = create_layer(
        admin_headers,
        name="rete_condotte",
        workspace="rete",
        title="Rete condotte",
        domain_module="network",
        metadata={"qgis": {"mode": "read_only"}},
    )
    not_published_layer = create_layer(
        admin_headers,
        name="rete_upload",
        workspace="rete",
        title="Rete upload",
        domain_module="network",
        metadata={"qgis": {"mode": "not_published"}},
    )
    staging_layer = create_layer(
        admin_headers,
        name="rete_staging",
        workspace="rete",
        title="Rete staging",
        domain_module="network",
        source_type="postgis_staging",
        metadata={"qgis": {"mode": "not_published"}},
    )
    hidden_layer = create_layer(
        admin_headers,
        name="rete_riservata",
        workspace="rete",
        title="Rete riservata",
        domain_module="network",
        metadata={"qgis": {"mode": "read_only"}},
    )
    for layer in (visible_layer, not_published_layer, staging_layer):
        permission_response = client.post(
            f"/gis/layers/{layer['id']}/permissions",
            headers=admin_headers,
            json={"principal_type": "role", "principal_key": "viewer", "access_level": "viewer"},
        )
        assert permission_response.status_code == 200

    response = client.get("/gis/qgis/project", headers=viewer_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.qgis.qgisproject+zip"
    assert response.headers["x-gis-qgis-layer-count"] == "1"
    assert response.headers["content-disposition"] == 'attachment; filename="gaia-gis-platform.qgz"'
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"README_QGIS.txt", "gaia-gis-platform.qgs", "manifest.json"}
        project_xml = archive.read("gaia-gis-platform.qgs").decode("utf-8")
        manifest = json.loads(archive.read("manifest.json"))
        readme = archive.read("README_QGIS.txt").decode("utf-8")

    assert "service='gaia_gis'" in project_xml
    assert "Rete condotte" in project_xml
    assert "rete_upload" not in project_xml
    assert "rete_staging" not in project_xml
    assert hidden_layer["name"] not in project_xml
    assert manifest["connection_service"] == "gaia_gis"
    assert manifest["policy"]["excluded"] == ["postgis_staging", "domain_registry", "qgis.mode=not_published"]
    assert [layer["name"] for layer in manifest["layers"]] == ["rete_condotte"]
    assert "Layer inclusi: 1" in readme


def test_qgis_project_download_requires_visible_publishable_layers() -> None:
    viewer_headers = auth_headers("gis-viewer")

    response = client.get("/gis/qgis/project", headers=viewer_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "No QGIS publishable layers visible for this user"


def test_qgis_project_geometry_kind_mapping_covers_common_shapes() -> None:
    assert gis_services._qgis_geometry_kind(GisLayer(geometry_type="POINT")) == "Point"  # noqa: SLF001
    assert gis_services._qgis_geometry_kind(GisLayer(geometry_type="MULTILINESTRING")) == "Line"  # noqa: SLF001
    assert gis_services._qgis_geometry_kind(GisLayer(geometry_type=None)) == "UnknownGeometry"  # noqa: SLF001


def test_ogc_poc_lists_visible_read_only_layers_without_wfs_transactions() -> None:
    seed_gis_platform_catalog()
    viewer_headers = auth_headers("gis-viewer")

    response = client.get("/gis/ogc/poc", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "read_only_poc"
    assert payload["recommended_server"] == "qgis_server"
    assert payload["proxy_path"] == "/gis/ogc/"
    assert payload["auth_policy"] == "gaia_auth_or_vpn_required"
    assert payload["qgis_project_endpoint"] == "/gis/qgis/project"
    assert payload["publishable_layer_count"] == len(CATASTO_GIS_LAYER_DEFINITIONS) + len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert {layer["workspace"] for layer in payload["layers"]} == {"catasto", "rete"}
    assert all(layer["wms_enabled"] is True for layer in payload["layers"])
    assert all(layer["wfs_enabled"] is True for layer in payload["layers"])
    assert all(layer["wfs_transactional"] is False for layer in payload["layers"])
    network_layer = next(layer for layer in payload["layers"] if layer["workspace"] == "rete")
    assert network_layer["service_layer_name"] == "rete__rete_condotte"
    assert network_layer["source_table"] == "network.rete_condotte"
    assert "WFS-T disabled" in payload["warnings"][0]
    assert "QGIS_SERVER_PROJECT_FILE=/srv/qgis/gaia-gis-platform.qgs" in payload["config_snippets"]["qgis_server_env"]
    assert "proxy_pass http://qgis-server:8080/" in payload["config_snippets"]["reverse_proxy"]
    assert "read-only" in payload["config_snippets"]["rollout_note"]


def test_ogc_poc_handles_users_without_publishable_layers() -> None:
    viewer_headers = auth_headers("gis-viewer")

    response = client.get("/gis/ogc/poc", headers=viewer_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["publishable_layer_count"] == 0
    assert payload["layers"] == []
    assert payload["warnings"] == ["No visible OGC publishable layers for this user."]
    assert "Publish 0 read-only layer(s)" in payload["config_snippets"]["rollout_note"]


def test_admin_imports_valid_shapefile_to_staging_and_rejects_it() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    zip_bytes = build_point_shapefile_zip(cpg_text="ISO-8859-1")

    forbidden = client.post(
        "/gis/imports/shapefile",
        headers=viewer_headers,
        data={
            "workspace": "rete",
            "domain_module": "network",
            "target_layer_name": "rete_condotte_upload",
            "target_layer_title": "Rete condotte upload",
            "official_source": "survey",
            "source_srid": "4326",
            "encoding": "utf-8",
        },
        files={"file": ("rete.zip", zip_bytes, "application/zip")},
    )
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": " rete ",
            "domain_module": " network ",
            "target_layer_name": " rete_condotte_upload ",
            "target_layer_title": " Rete condotte upload ",
            "official_source": " survey ",
            "source_srid": "4326",
            "encoding": "utf-8",
        },
        files={"file": ("rete.zip", zip_bytes, "application/zip")},
    )

    assert forbidden.status_code == 403
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "validated"
    assert payload["workspace"] == "rete"
    assert payload["domain_module"] == "network"
    assert payload["target_layer_name"] == "rete_condotte_upload"
    assert payload["official_source"] == "survey"
    assert payload["source_srid"] == 4326
    assert payload["feature_count"] == 2
    assert payload["geometry_type"] == "POINT"
    assert payload["bbox"] == [8.4, 39.9, 8.5, 40.0]
    assert {field["name"] for field in payload["fields"]} == {"name", "active", "when"}
    assert payload["validation_report"]["is_valid"] is True
    assert payload["validation_report"]["warnings"] == ["encoding_overridden"]
    assert payload["validation_report"]["staging"]["mode"] == "postgis_staging_table"
    assert payload["staging_schema"] is None
    assert payload["staging_table"].startswith("gis_staging_import_")

    import_id = payload["id"]
    db = TestingSessionLocal()
    try:
        count = db.execute(text(f"SELECT COUNT(*) FROM \"{payload['staging_table']}\"")).scalar_one()
        sample = db.execute(text(f"SELECT attributes_json, geometry_json, source_srid FROM \"{payload['staging_table']}\" ORDER BY feature_seq LIMIT 1")).one()
        assert count == 2
        assert json.loads(sample.attributes_json)["when"] == "2026-07-14"
        assert json.loads(sample.geometry_json)["type"] == "Point"
        assert sample.source_srid == 4326
    finally:
        db.close()

    blocked_get = client.get(f"/gis/imports/{import_id}", headers=viewer_headers)
    fetched = client.get(f"/gis/imports/{import_id}", headers=admin_headers)
    assert blocked_get.status_code == 403
    assert fetched.status_code == 200
    assert fetched.json()["id"] == import_id
    blocked_preview = client.get(f"/gis/imports/{import_id}/preview", headers=viewer_headers)
    preview = client.get(f"/gis/imports/{import_id}/preview?limit=1", headers=admin_headers)
    preview_next = client.get(f"/gis/imports/{import_id}/preview?limit=1&offset=1", headers=admin_headers)
    assert blocked_preview.status_code == 403
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["import_id"] == import_id
    assert preview_payload["staging_table"] == payload["staging_table"]
    assert preview_payload["feature_count"] == 2
    assert preview_payload["returned_count"] == 1
    assert preview_payload["limit"] == 1
    assert preview_payload["offset"] == 0
    assert preview_payload["has_more"] is True
    assert {field["name"] for field in preview_payload["fields"]} == {"name", "active", "when"}
    assert preview_payload["features"][0]["feature_seq"] == 1
    assert preview_payload["features"][0]["attributes"] == {"active": True, "name": "feature-1", "when": "2026-07-14"}
    assert preview_payload["features"][0]["geometry"]["type"] == "Point"
    assert preview_payload["features"][0]["geometry_type"] == "Point"
    assert preview_payload["features"][0]["source_srid"] == 4326
    assert preview_next.status_code == 200
    assert preview_next.json()["has_more"] is False
    assert preview_next.json()["features"][0]["attributes"]["name"] == "feature-2"
    assert client.post(f"/gis/imports/{import_id}/validate", headers=viewer_headers).status_code == 403
    assert client.post(f"/gis/imports/{import_id}/reject", headers=viewer_headers).status_code == 403

    db = TestingSessionLocal()
    try:
        item = db.get(GisShapefileImport, UUID(import_id))
        assert item is not None
        item.status = "uploaded"
        item.validated_at = None
        db.commit()
    finally:
        db.close()

    preview_uploaded = client.get(f"/gis/imports/{import_id}/preview", headers=admin_headers)
    revalidated = client.post(f"/gis/imports/{import_id}/validate", headers=admin_headers)
    rejected = client.post(f"/gis/imports/{import_id}/reject", headers=admin_headers)
    rejected_again = client.post(f"/gis/imports/{import_id}/reject", headers=admin_headers)
    validate_rejected = client.post(f"/gis/imports/{import_id}/validate", headers=admin_headers)
    preview_rejected = client.get(f"/gis/imports/{import_id}/preview", headers=admin_headers)

    assert preview_uploaded.status_code == 409
    assert revalidated.status_code == 200
    assert revalidated.json()["status"] == "validated"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejected_at"] is not None
    assert rejected_again.status_code == 200
    assert validate_rejected.status_code == 409
    assert preview_rejected.status_code == 409

    db = TestingSessionLocal()
    try:
        table_exists = db.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = :name"),
            {"name": payload["staging_table"]},
        ).scalar_one_or_none()
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert table_exists is None
        assert "shapefile_import.uploaded" in audit_events
        assert "shapefile_import.validated" in audit_events
        assert "shapefile_import.rejected" in audit_events
    finally:
        db.close()


def test_shapefile_import_rejects_invalid_archives_and_tracks_warnings() -> None:
    admin_headers = auth_headers("gis-admin")

    def post_zip(zip_bytes: bytes, *, source_srid: str = "4326") -> int:
        response = client.post(
            "/gis/imports/shapefile",
            headers=admin_headers,
            data={
                "workspace": "rete",
                "target_layer_name": "rete_upload",
                "target_layer_title": "Rete upload",
                "source_srid": source_srid,
            },
            files={"file": ("upload.zip", zip_bytes, "application/zip")},
        )
        return response.status_code

    cpg_missing = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": "rete",
            "target_layer_name": "rete_upload_no_cpg",
            "target_layer_title": "Rete upload no cpg",
            "source_srid": "4326",
        },
        files={"file": ("upload.zip", build_point_shapefile_zip(include_cpg=False), "application/zip")},
    )

    assert cpg_missing.status_code == 201
    assert cpg_missing.json()["validation_report"]["warnings"] == ["cpg_missing"]
    assert post_zip(b"not-a-zip") == 422
    assert post_zip(build_point_shapefile_zip(), source_srid="0") == 422
    assert post_zip(build_point_shapefile_zip(include_prj=False)) == 422
    assert post_zip(build_point_shapefile_zip(second_shapefile=True)) == 422
    assert post_zip(build_point_shapefile_zip(unsafe_name=True)) == 422
    assert post_zip(build_point_shapefile_zip(empty=True)) == 422
    assert post_zip(build_point_shapefile_zip(include_prj=False, include_cpg=False), source_srid="-1") == 422

    corrupt = io.BytesIO()
    with zipfile.ZipFile(corrupt, "w") as archive:
        archive.writestr("shape/rete.shp", b"bad")
        archive.writestr("shape/rete.shx", b"bad")
        archive.writestr("shape/rete.dbf", b"bad")
        archive.writestr("shape/rete.prj", 'GEOGCS["WGS 84"]')
    assert post_zip(corrupt.getvalue()) == 422

    missing_target = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": " ",
            "target_layer_name": "rete_upload",
            "target_layer_title": "Rete upload",
            "source_srid": "4326",
        },
        files={"file": ("upload.zip", build_point_shapefile_zip(), "application/zip")},
    )
    missing_import = client.get("/gis/imports/00000000-0000-0000-0000-000000000000", headers=admin_headers)

    assert missing_target.status_code == 422
    assert missing_import.status_code == 404


def test_shapefile_import_preview_reports_missing_staging_table() -> None:
    admin_headers = auth_headers("gis-admin")
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": "rete",
            "target_layer_name": "rete_missing_preview",
            "target_layer_title": "Rete missing preview",
            "source_srid": "4326",
        },
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
    )
    assert created.status_code == 201
    payload = created.json()

    db = TestingSessionLocal()
    try:
        db.execute(text(f"DROP TABLE \"{payload['staging_table']}\""))
        db.commit()
    finally:
        db.close()

    preview = client.get(f"/gis/imports/{payload['id']}/preview", headers=admin_headers)

    assert preview.status_code == 409
    assert preview.json()["detail"] == "GIS shapefile import staging table is not available"


def test_create_change_requests_from_shapefile_import_targets_official_layer() -> None:
    admin_headers = auth_headers("gis-admin")
    target_layer = create_layer(
        admin_headers,
        name="rete_condotte",
        workspace="rete",
        title="Rete condotte ufficiali",
        domain_module="network",
        metadata={"qgis": {"mode": "read_only"}},
    )
    normal_change_request = client.post(
        f"/gis/layers/{target_layer['id']}/change-requests",
        headers=admin_headers,
        json={
            "change_type": "feature_create",
            "payload": {"geometry": {"type": "Point", "coordinates": [8.4, 39.9]}, "properties": {"name": "manuale"}},
            "justification": "Richiesta manuale",
        },
    )
    assert normal_change_request.status_code == 201
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
        data={
            "workspace": "rete",
            "target_layer_name": "rete_condotte",
            "target_layer_title": "Rete condotte import",
            "source_srid": "4326",
            "domain_module": "network",
            "official_source": "survey",
        },
    )
    assert created.status_code == 201
    import_payload = created.json()

    first_batch = client.post(
        f"/gis/imports/{import_payload['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": target_layer["id"], "justification": "Import rilievo campo", "limit": 1, "offset": 0},
    )
    repeated_first_batch = client.post(
        f"/gis/imports/{import_payload['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": target_layer["id"], "justification": "Import rilievo campo", "limit": 1, "offset": 0},
    )
    with TestingSessionLocal() as db:
        db.execute(text(f"UPDATE \"{import_payload['staging_table']}\" SET geometry_json = NULL WHERE feature_seq = 2"))
        db.commit()
    skipped_second_batch = client.post(
        f"/gis/imports/{import_payload['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": target_layer["id"], "limit": 1, "offset": 1},
    )

    assert first_batch.status_code == 200
    first_payload = first_batch.json()
    assert first_payload["created_count"] == 1
    assert first_payload["existing_count"] == 0
    assert first_payload["returned_count"] == 1
    assert first_payload["skipped_count"] == 0
    assert first_payload["has_more"] is True
    change_request = first_payload["change_requests"][0]
    assert change_request["layer_id"] == target_layer["id"]
    assert change_request["change_type"] == "feature_create"
    assert change_request["status"] == "submitted"
    assert change_request["justification"] == "Import rilievo campo"
    assert change_request["payload"]["source_import"]["import_id"] == import_payload["id"]
    assert change_request["payload"]["source_import"]["feature_seq"] == 1
    assert change_request["payload"]["source_import"]["checksum_sha256"] == import_payload["checksum_sha256"]
    assert change_request["payload"]["properties"]["name"] == "feature-1"
    assert change_request["payload"]["geometry"]["type"] == "Point"

    assert repeated_first_batch.status_code == 200
    repeated_payload = repeated_first_batch.json()
    assert repeated_payload["created_count"] == 0
    assert repeated_payload["existing_count"] == 1
    assert repeated_payload["change_requests"][0]["id"] == change_request["id"]

    assert skipped_second_batch.status_code == 200
    skipped_payload = skipped_second_batch.json()
    assert skipped_payload["created_count"] == 0
    assert skipped_payload["skipped_count"] == 1
    assert skipped_payload["returned_count"] == 0
    assert skipped_payload["has_more"] is False

    with TestingSessionLocal() as db:
        audit = db.scalars(
            select(GisAuditLog).where(GisAuditLog.event_type == "change_request.submitted")
        ).all()
        import_audit = [item for item in audit if (item.payload_json or {}).get("source_import_id") == import_payload["id"]]
        assert len(import_audit) == 1
        assert import_audit[0].payload_json["feature_seq"] == 1


def test_create_change_requests_from_shapefile_import_rejects_invalid_states_and_targets() -> None:
    admin_headers = auth_headers("gis-admin")
    target_layer = create_layer(admin_headers, name="rete_condotte", workspace="rete", title="Rete condotte", domain_module="network")
    staging_target = create_layer(
        admin_headers,
        name="rete_staging",
        workspace="rete",
        title="Rete staging",
        domain_module="network",
        source_type="postgis_staging",
        metadata={"qgis": {"mode": "not_published"}},
    )
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
        data={
            "workspace": "rete",
            "target_layer_name": "rete_condotte",
            "target_layer_title": "Rete condotte import",
            "source_srid": "4326",
        },
    )
    assert created.status_code == 201
    import_payload = created.json()

    invalid_target = client.post(
        f"/gis/imports/{import_payload['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": staging_target["id"]},
    )
    with TestingSessionLocal() as db:
        db.execute(text(f"DROP TABLE \"{import_payload['staging_table']}\""))
        db.commit()
    missing_staging = client.post(
        f"/gis/imports/{import_payload['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": target_layer["id"]},
    )

    rejected_import = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
        data={
            "workspace": "rete",
            "target_layer_name": "rete_condotte_rejected",
            "target_layer_title": "Rete condotte rejected",
            "source_srid": "4326",
        },
    )
    assert rejected_import.status_code == 201
    rejected_payload = client.post(f"/gis/imports/{rejected_import.json()['id']}/reject", headers=admin_headers)
    rejected_change_request = client.post(
        f"/gis/imports/{rejected_import.json()['id']}/change-requests",
        headers=admin_headers,
        json={"target_layer_id": target_layer["id"]},
    )

    assert invalid_target.status_code == 422
    assert invalid_target.json()["detail"] == "GIS import change request requires an official PostGIS target layer"
    assert missing_staging.status_code == 409
    assert missing_staging.json()["detail"] == "GIS shapefile import staging table is not available"
    assert rejected_payload.status_code == 200
    assert rejected_change_request.status_code == 409
    assert rejected_change_request.json()["detail"] == "GIS shapefile import must be validated before change request"


def test_publish_validated_shapefile_import_creates_read_only_staging_layer() -> None:
    admin_headers = auth_headers("gis-admin")
    viewer_headers = auth_headers("gis-viewer")
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": "rete",
            "domain_module": "network",
            "target_layer_name": "rete_pubblicata",
            "target_layer_title": "Rete pubblicata",
            "official_source": "survey",
            "source_srid": "4326",
        },
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
    )
    assert created.status_code == 201
    import_id = created.json()["id"]

    blocked_publish = client.post(f"/gis/imports/{import_id}/publish", headers=viewer_headers)
    published = client.post(f"/gis/imports/{import_id}/publish", headers=admin_headers)
    published_again = client.post(f"/gis/imports/{import_id}/publish", headers=admin_headers)
    validate_published = client.post(f"/gis/imports/{import_id}/validate", headers=admin_headers)
    reject_published = client.post(f"/gis/imports/{import_id}/reject", headers=admin_headers)

    assert blocked_publish.status_code == 403
    assert published.status_code == 200
    payload = published.json()
    assert payload["status"] == "published"
    assert payload["published_layer_id"] is not None
    assert payload["published_at"] is not None
    assert published_again.status_code == 200
    assert published_again.json()["published_layer_id"] == payload["published_layer_id"]
    assert validate_published.status_code == 200
    assert validate_published.json()["status"] == "published"
    assert reject_published.status_code == 409

    layer_response = client.get(f"/gis/layers/{payload['published_layer_id']}", headers=viewer_headers)
    blocked_export = client.post(
        f"/gis/layers/{payload['published_layer_id']}/export-shapefile",
        headers=admin_headers,
        json={"version_label": "staging-export"},
    )
    assert layer_response.status_code == 200
    layer = layer_response.json()
    assert layer["workspace"] == "rete"
    assert layer["name"] == "rete_pubblicata"
    assert layer["title"] == "Rete pubblicata"
    assert layer["domain_module"] == "network"
    assert layer["source_type"] == "postgis_staging"
    assert layer["official_source"] == "survey"
    assert layer["postgis_table"] == payload["staging_table"]
    assert layer["geometry_column"] == "geometry_json"
    assert layer["feature_id_column"] == "feature_seq"
    assert layer["effective_access_level"] == "viewer"
    assert layer["metadata"]["read_only"] is True
    assert layer["metadata"]["qgis"]["mode"] == "not_published"
    assert layer["metadata"]["export"]["shapefile"] is False
    assert layer["metadata"]["import"]["import_id"] == import_id
    assert blocked_export.status_code == 422

    dashboard = client.get("/gis/catalog/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    workspace = next(item for item in dashboard.json()["workspaces"] if item["workspace"] == "rete")
    assert workspace["total_layers"] == 1
    assert workspace["qgis_publishable_layers"] == 0
    assert workspace["exportable_layers"] == 0

    db = TestingSessionLocal()
    try:
        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "shapefile_import.published" in audit_events
        assert "layer.created_from_shapefile_import" in audit_events
    finally:
        db.close()


def test_publish_shapefile_import_requires_validated_unique_target() -> None:
    admin_headers = auth_headers("gis-admin")
    existing = create_layer(admin_headers, name="rete_duplicate", workspace="rete", title="Rete duplicate", domain_module="network")
    created = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": "rete",
            "target_layer_name": "rete_duplicate",
            "target_layer_title": "Rete duplicate import",
            "source_srid": "4326",
        },
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
    )
    assert created.status_code == 201
    duplicate_publish = client.post(f"/gis/imports/{created.json()['id']}/publish", headers=admin_headers)
    assert duplicate_publish.status_code == 409
    assert duplicate_publish.json()["detail"] == "GIS layer target already exists"

    db = TestingSessionLocal()
    try:
        item = db.get(GisShapefileImport, UUID(created.json()["id"]))
        assert item is not None
        item.status = "uploaded"
        db.commit()
    finally:
        db.close()
    not_validated = client.post(f"/gis/imports/{created.json()['id']}/publish", headers=admin_headers)
    assert not_validated.status_code == 409

    rejected = client.post(
        "/gis/imports/shapefile",
        headers=admin_headers,
        data={
            "workspace": "rete",
            "target_layer_name": "rete_rejected",
            "target_layer_title": "Rete rejected",
            "source_srid": "4326",
        },
        files={"file": ("rete.zip", build_point_shapefile_zip(), "application/zip")},
    )
    assert rejected.status_code == 201
    assert client.post(f"/gis/imports/{rejected.json()['id']}/reject", headers=admin_headers).status_code == 200
    rejected_publish = client.post(f"/gis/imports/{rejected.json()['id']}/publish", headers=admin_headers)
    assert rejected_publish.status_code == 409

    assert client.get(f"/gis/layers/{existing['id']}", headers=admin_headers).status_code == 200


def test_publish_shapefile_import_translates_integrity_race_to_conflict() -> None:
    import_id = UUID("00000000-0000-0000-0000-000000000914")
    item = GisShapefileImport(
        id=import_id,
        status="validated",
        original_filename="rete.zip",
        workspace="rete",
        target_layer_name="rete_race",
        target_layer_title="Rete race",
        official_source="survey",
        source_srid=4326,
        encoding="utf-8",
        staging_table="gis_staging_import_race",
        feature_count=1,
        geometry_type="POINT",
        checksum_sha256="0" * 64,
    )
    admin = ApplicationUser(id=1, username="admin", email="admin@example.local", password_hash="x", role="admin", is_active=True)

    class _FakeDb:
        def get(self, model, key):  # noqa: ANN001
            return item if model is GisShapefileImport and key == import_id else None

        def scalar(self, statement):  # noqa: ANN001
            return None

        def add(self, obj) -> None:  # noqa: ANN001
            return None

        def flush(self) -> None:
            raise IntegrityError("insert", {}, Exception("duplicate"))

    with pytest.raises(HTTPException) as exc:
        gis_services.publish_shapefile_import(_FakeDb(), import_id, admin)  # type: ignore[arg-type]

    assert exc.value.status_code == 409
    assert exc.value.detail == "GIS layer target already exists"


def test_shapefile_staging_helpers_cover_schema_qualified_tables() -> None:
    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _FakeDb:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def get_bind(self) -> _Bind:
            return _Bind()

        def execute(self, statement, params=None):  # noqa: ANN001
            self.statements.append(str(statement))

    fake_db = _FakeDb()
    import_id = UUID("00000000-0000-0000-0000-000000000123")
    schema_name, table_name = gis_services._staging_location(fake_db, import_id)  # noqa: SLF001
    validated = gis_services.GisValidatedShapefile(  # noqa: SLF001
        stem="shape/rete",
        feature_count=1,
        geometry_type="POINT",
        bbox=[8.4, 39.9, 8.4, 39.9],
        fields=[{"name": "name", "type": "C", "size": 50, "decimal": 0}],
        records=[({"name": "feature"}, {"type": "Point", "coordinates": [8.4, 39.9]})],
        validation_report={"is_valid": True},
        checksum_sha256="0" * 64,
    )

    assert schema_name == "gis_staging"
    assert table_name == "import_00000000000000000000000000000123"
    gis_services._create_staging_table(  # noqa: SLF001
        fake_db,
        schema_name=schema_name,
        table_name=table_name,
        validated=validated,
        source_srid=4326,
    )
    gis_services._drop_staging_table(fake_db, schema_name=schema_name, table_name=table_name)  # noqa: SLF001

    assert any('CREATE SCHEMA IF NOT EXISTS "gis_staging"' in statement for statement in fake_db.statements)
    assert any('CREATE TABLE "gis_staging"."import_00000000000000000000000000000123"' in statement for statement in fake_db.statements)
    assert any('DROP TABLE IF EXISTS "gis_staging"."import_00000000000000000000000000000123"' in statement for statement in fake_db.statements)


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
        assert network_apply_audit.payload_json["apply_result"]["reason"] == "controlled edit policy not enabled"
    finally:
        db.close()


def test_controlled_apply_change_requests_write_to_non_catasto_postgis_layer() -> None:
    admin_headers = auth_headers("gis-admin")
    editor_headers = auth_headers("gis-editor")
    table_name = "rete_condotte_apply"
    seed_apply_source_table(table_name)
    layer_id = create_layer(
        admin_headers,
        name=table_name,
        workspace="rete",
        title="Condotte apply",
        domain_module="network",
        official_source="network",
        metadata={"qgis": {"mode": "controlled_edit", "editable": True, "edit_policy": "controlled"}},
    )["id"]
    editor_id = user_id("gis-editor")
    permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
    )
    assert permission.status_code == 200

    def submit_approve_apply(change_type: str, payload: dict, feature_id: str | None = None) -> str:
        submitted = client.post(
            f"/gis/layers/{layer_id}/change-requests",
            headers=editor_headers,
            json={"feature_id": feature_id, "change_type": change_type, "payload": payload, "justification": "rilievo"},
        )
        assert submitted.status_code == 201
        change_request_id = submitted.json()["id"]
        approved = client.post(
            f"/gis/change-requests/{change_request_id}/approve",
            headers=admin_headers,
            json={"review_notes": "validata"},
        )
        applied = client.post(f"/gis/change-requests/{change_request_id}/apply", headers=admin_headers)
        assert approved.status_code == 200
        assert applied.status_code == 200
        assert applied.json()["status"] == "applied"
        return change_request_id

    created_geometry = {"type": "LineString", "coordinates": [[8.1, 39.7], [8.2, 39.8]]}
    updated_geometry = {"type": "LineString", "coordinates": [[8.8, 40.3], [8.9, 40.4]]}
    created_id = submit_approve_apply(
        "feature_create",
        {"geometry": created_geometry, "properties": {"id": "pipe-new", "name": "Nuova condotta", "diameter": 75}},
    )
    attribute_id = submit_approve_apply(
        "attribute_update",
        {"after": {"name": "Condotta aggiornata", "diameter": 160}},
        "pipe-1",
    )
    geometry_id = submit_approve_apply("geometry_update", {"geometry": updated_geometry}, "pipe-1")
    delete_id = submit_approve_apply(
        "feature_delete",
        {"before": {"id": "pipe-delete", "name": "Da rimuovere"}},
        "pipe-delete",
    )

    db = TestingSessionLocal()
    try:
        rows = {
            row["id"]: row
            for row in db.execute(
                text(f'SELECT id, name, diameter, geometry FROM "{table_name}" ORDER BY id')
            ).mappings()
        }
        assert rows["pipe-new"]["name"] == "Nuova condotta"
        assert rows["pipe-new"]["diameter"] == 75
        assert json.loads(rows["pipe-new"]["geometry"]) == created_geometry
        assert rows["pipe-1"]["name"] == "Condotta aggiornata"
        assert rows["pipe-1"]["diameter"] == 160
        assert json.loads(rows["pipe-1"]["geometry"]) == updated_geometry
        assert "pipe-delete" not in rows

        audits = {
            str(audit.target_id): audit.payload_json["apply_result"]
            for audit in db.scalars(
                select(GisAuditLog).where(GisAuditLog.event_type == "change_request.applied")
            ).all()
        }
        assert audits[created_id]["mode"] == "applied"
        assert audits[created_id]["adapter"] == "postgis_controlled_edit"
        assert audits[created_id]["result"]["operation"] == "insert"
        assert audits[attribute_id]["result"]["operation"] == "attribute_update"
        assert audits[attribute_id]["result"]["before"]["diameter"] == 120
        assert audits[attribute_id]["result"]["after"]["diameter"] == 160
        assert audits[geometry_id]["result"]["operation"] == "geometry_update"
        assert json.loads(audits[geometry_id]["result"]["after"]["geometry"]) == updated_geometry
        assert audits[delete_id]["result"]["operation"] == "feature_delete"
        assert audits[delete_id]["result"]["before"]["name"] == "Da rimuovere"
    finally:
        db.close()


def test_controlled_apply_rejects_missing_target_and_invalid_apply_payloads() -> None:
    admin_headers = auth_headers("gis-admin")
    editor_headers = auth_headers("gis-editor")
    table_name = "rete_condotte_apply_guard"
    seed_apply_source_table(table_name)
    layer_id = create_layer(
        admin_headers,
        name=table_name,
        workspace="rete",
        title="Condotte apply guard",
        domain_module="network",
        official_source="network",
        metadata={"qgis": {"mode": "controlled_edit", "editable": True, "edit_policy": "controlled"}},
    )["id"]
    editor_id = user_id("gis-editor")
    permission = client.post(
        f"/gis/layers/{layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
    )
    assert permission.status_code == 200

    def submit_and_approve(payload: dict, feature_id: str = "pipe-1", change_type: str = "attribute_update") -> str:
        submitted = client.post(
            f"/gis/layers/{layer_id}/change-requests",
            headers=editor_headers,
            json={"feature_id": feature_id, "change_type": change_type, "payload": payload},
        )
        assert submitted.status_code == 201
        change_request_id = submitted.json()["id"]
        approved = client.post(f"/gis/change-requests/{change_request_id}/approve", headers=admin_headers, json={})
        assert approved.status_code == 200
        return change_request_id

    missing_target_id = submit_and_approve({"after": {"diameter": 180}}, "missing-pipe")
    missing_target_apply = client.post(f"/gis/change-requests/{missing_target_id}/apply", headers=admin_headers)
    assert missing_target_apply.status_code == 409
    assert missing_target_apply.json()["detail"] == "GIS apply target feature not found"

    missing_geometry_id = submit_and_approve(
        {"geometry": {"type": "LineString", "coordinates": [[8.1, 39.7], [8.2, 39.8]]}},
        "missing-geometry",
        "geometry_update",
    )
    missing_geometry_apply = client.post(f"/gis/change-requests/{missing_geometry_id}/apply", headers=admin_headers)
    assert missing_geometry_apply.status_code == 409
    assert missing_geometry_apply.json()["detail"] == "GIS apply target feature not found"

    missing_delete_id = submit_and_approve(
        {"before": {"id": "missing-delete"}},
        "missing-delete",
        "feature_delete",
    )
    missing_delete_apply = client.post(f"/gis/change-requests/{missing_delete_id}/apply", headers=admin_headers)
    assert missing_delete_apply.status_code == 409
    assert missing_delete_apply.json()["detail"] == "GIS apply target feature not found"

    geometry_only_id = submit_and_approve({"after": {"geometry": {"type": "LineString", "coordinates": []}}})
    geometry_only_apply = client.post(f"/gis/change-requests/{geometry_only_id}/apply", headers=admin_headers)
    assert geometry_only_apply.status_code == 422
    assert geometry_only_apply.json()["detail"] == "GIS apply requires non-geometry attributes"

    empty_after_id = submit_and_approve({"after": {"diameter": 181}})
    db = TestingSessionLocal()
    try:
        change_request = db.get(GisChangeRequest, UUID(empty_after_id))
        assert change_request is not None
        change_request.payload_json = {"after": {}}
        layer = db.get(GisLayer, UUID(layer_id))
        assert layer is not None
        layer.srid = None
        db.commit()

        class PostgreSQLDialect:
            name = "postgresql"

        class PostgreSQLBind:
            dialect = PostgreSQLDialect()

        class PostgreSQLSession:
            def get_bind(self) -> PostgreSQLBind:
                return PostgreSQLBind()

        assert gis_services._geometry_sql_expression(PostgreSQLSession(), layer) == "ST_SetSRID(ST_GeomFromGeoJSON(:geometry_json), 4326)"
    finally:
        db.close()
    empty_after_apply = client.post(f"/gis/change-requests/{empty_after_id}/apply", headers=admin_headers)
    assert empty_after_apply.status_code == 422
    assert empty_after_apply.json()["detail"] == "GIS apply requires attribute updates"

    no_table_layer_id = create_layer(
        admin_headers,
        name="rete_condotte_without_table",
        workspace="rete",
        title="Condotte senza tabella",
        domain_module="network",
        official_source="network",
        metadata={"qgis": {"mode": "controlled_edit", "editable": True, "edit_policy": "controlled"}},
    )["id"]
    no_table_permission = client.post(
        f"/gis/layers/{no_table_layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
    )
    assert no_table_permission.status_code == 200
    feature_create = client.post(
        f"/gis/layers/{no_table_layer_id}/change-requests",
        headers=editor_headers,
        json={
            "change_type": "feature_create",
            "payload": {
                "geometry": {"type": "LineString", "coordinates": [[8.1, 39.7], [8.2, 39.8]]},
                "properties": {"id": "pipe-new"},
            },
        },
    )
    assert feature_create.status_code == 201
    no_table_change_request_id = feature_create.json()["id"]
    no_table_approval = client.post(
        f"/gis/change-requests/{no_table_change_request_id}/approve",
        headers=admin_headers,
        json={},
    )
    assert no_table_approval.status_code == 200
    db = TestingSessionLocal()
    try:
        no_table_layer = db.get(GisLayer, UUID(no_table_layer_id))
        assert no_table_layer is not None
        no_table_layer.postgis_table = None
        db.commit()
    finally:
        db.close()
    no_table_apply = client.post(f"/gis/change-requests/{no_table_change_request_id}/apply", headers=admin_headers)
    assert no_table_apply.status_code == 422
    assert no_table_apply.json()["detail"] == "GIS apply requires a PostGIS table"

    duplicate_create = client.post(
        f"/gis/layers/{layer_id}/change-requests",
        headers=editor_headers,
        json={
            "change_type": "feature_create",
            "payload": {
                "geometry": {"type": "LineString", "coordinates": [[8.1, 39.7], [8.2, 39.8]]},
                "properties": {"id": "pipe-1", "name": "Duplicata"},
            },
        },
    )
    assert duplicate_create.status_code == 201
    duplicate_change_request_id = duplicate_create.json()["id"]
    duplicate_approval = client.post(
        f"/gis/change-requests/{duplicate_change_request_id}/approve",
        headers=admin_headers,
        json={},
    )
    assert duplicate_approval.status_code == 200
    duplicate_apply = client.post(f"/gis/change-requests/{duplicate_change_request_id}/apply", headers=admin_headers)
    assert duplicate_apply.status_code == 409
    assert duplicate_apply.json()["detail"] == "GIS apply violates target constraints"

    missing_table_layer_id = create_layer(
        admin_headers,
        name="rete_condotte_missing_physical_table",
        workspace="rete",
        title="Condotte tabella assente",
        domain_module="network",
        official_source="network",
        metadata={"qgis": {"mode": "controlled_edit", "editable": True, "edit_policy": "controlled"}},
    )["id"]
    missing_table_permission = client.post(
        f"/gis/layers/{missing_table_layer_id}/permissions",
        headers=admin_headers,
        json={"principal_type": "user", "principal_key": str(editor_id), "access_level": "editor"},
    )
    assert missing_table_permission.status_code == 200
    missing_table_create = client.post(
        f"/gis/layers/{missing_table_layer_id}/change-requests",
        headers=editor_headers,
        json={
            "change_type": "feature_create",
            "payload": {
                "geometry": {"type": "LineString", "coordinates": [[8.1, 39.7], [8.2, 39.8]]},
                "properties": {"id": "pipe-new"},
            },
        },
    )
    assert missing_table_create.status_code == 201
    missing_table_change_request_id = missing_table_create.json()["id"]
    missing_table_approval = client.post(
        f"/gis/change-requests/{missing_table_change_request_id}/approve",
        headers=admin_headers,
        json={},
    )
    assert missing_table_approval.status_code == 200
    missing_table_apply = client.post(f"/gis/change-requests/{missing_table_change_request_id}/apply", headers=admin_headers)
    assert missing_table_apply.status_code == 409
    assert missing_table_apply.json()["detail"] == "GIS apply target layer is not available"

    db = TestingSessionLocal()
    try:
        statuses = {
            str(item.id): item.status
            for item in db.scalars(
                select(GisChangeRequest).where(
                    GisChangeRequest.id.in_(
                        [
                            UUID(missing_target_id),
                            UUID(missing_geometry_id),
                            UUID(missing_delete_id),
                            UUID(geometry_only_id),
                            UUID(empty_after_id),
                            UUID(no_table_change_request_id),
                            UUID(duplicate_change_request_id),
                            UUID(missing_table_change_request_id),
                        ]
                    )
                )
            ).all()
        }
        assert set(statuses.values()) == {"approved"}
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


def test_scheduled_shapefile_exports_publish_latest_dashboard_and_apply_retention(tmp_path: Path) -> None:
    admin_headers = auth_headers("gis-admin")
    layer_name = "scheduled_export_source"
    layer_id = create_layer(admin_headers, name=layer_name)["id"]
    seed_export_source_table(layer_name)
    export_root = tmp_path / "scheduled-root"
    retained_manual_path = tmp_path / "manual.zip"
    pruned_existing_path = tmp_path / "old-existing.zip"
    pruned_missing_path = tmp_path / "old-missing.zip"
    retained_manual_path.write_text("manual", encoding="utf-8")
    pruned_existing_path.write_text("old", encoding="utf-8")

    db = TestingSessionLocal()
    try:
        layer = db.get(GisLayer, UUID(layer_id))
        assert layer is not None
        layer.nas_export_root = str(export_root)
        old_completed_at = datetime.now(UTC) - timedelta(days=2)
        db.add_all(
            [
                GisLayerExport(
                    layer_id=layer.id,
                    version_label="manual-keep",
                    status="completed",
                    nas_path=str(retained_manual_path),
                    metadata_json={"trigger": "manual"},
                    completed_at=old_completed_at,
                ),
                GisLayerExport(
                    layer_id=layer.id,
                    version_label="scheduled-old-existing",
                    status="completed",
                    nas_path=str(pruned_existing_path),
                    metadata_json={"trigger": "scheduled"},
                    completed_at=old_completed_at,
                ),
                GisLayerExport(
                    layer_id=layer.id,
                    version_label="scheduled-old-missing",
                    status="completed",
                    nas_path=str(pruned_missing_path),
                    metadata_json={"trigger": "scheduled"},
                    completed_at=old_completed_at - timedelta(hours=1),
                ),
            ]
        )
        db.commit()
        summary = gis_services.run_scheduled_shapefile_exports(
            db,
            retention_count=1,
            max_layers=1,
            now=datetime(2026, 7, 14, 2, 30, tzinfo=UTC),
        )
    finally:
        db.close()

    assert summary.attempted_layers == 1
    assert summary.completed_exports == 1
    assert summary.failed_exports == 0
    assert summary.pruned_exports == 2
    assert retained_manual_path.exists()
    assert not pruned_existing_path.exists()

    db = TestingSessionLocal()
    try:
        exports = db.scalars(select(GisLayerExport).where(GisLayerExport.layer_id == UUID(layer_id))).all()
        scheduled_exports = [item for item in exports if item.metadata_json.get("trigger") == "scheduled"]
        manual_exports = [item for item in exports if item.metadata_json.get("trigger") == "manual"]
        assert len(scheduled_exports) == 1
        assert len(manual_exports) == 1
        scheduled_export = scheduled_exports[0]
        assert scheduled_export.version_label == "scheduled-20260714T023000Z"
        assert scheduled_export.status == "completed"
        assert scheduled_export.requested_by_user_id is None
        assert scheduled_export.metadata_json["retention_count"] == 1
        assert Path(scheduled_export.nas_path).exists()

        audit_events = db.scalars(select(GisAuditLog.event_type).order_by(GisAuditLog.created_at, GisAuditLog.event_type)).all()
        assert "export.scheduled" in audit_events
        assert "export.completed" in audit_events
        assert audit_events.count("export.retention_applied") == 2
        scheduled_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "export.scheduled"))
        assert scheduled_audit is not None
        assert scheduled_audit.actor_user_id is None
        retention_payloads = db.scalars(select(GisAuditLog.payload_json).where(GisAuditLog.event_type == "export.retention_applied")).all()
        assert {item["file_deleted"] for item in retention_payloads} == {True, False}
    finally:
        db.close()

    dashboard = client.get("/gis/catalog/dashboard", headers=admin_headers)
    latest_exports = dashboard.json()["latest_exports"]
    assert dashboard.status_code == 200
    assert latest_exports[0]["layer_id"] == layer_id
    assert latest_exports[0]["trigger"] == "scheduled"
    assert latest_exports[0]["version_label"] == "scheduled-20260714T023000Z"


def test_scheduled_shapefile_exports_continue_after_failures() -> None:
    admin_headers = auth_headers("gis-admin")
    create_layer(admin_headers, name="scheduled_missing_source")

    db = TestingSessionLocal()
    try:
        summary = gis_services.run_scheduled_shapefile_exports(
            db,
            retention_count=2,
            max_layers=0,
            now=datetime(2026, 7, 14, 2, 30, tzinfo=UTC),
        )
        failed_export = db.scalar(select(GisLayerExport).where(GisLayerExport.version_label == "scheduled-20260714T023000Z"))
        failed_audit = db.scalar(select(GisAuditLog).where(GisAuditLog.event_type == "export.failed"))
    finally:
        db.close()

    assert summary.attempted_layers == 1
    assert summary.completed_exports == 0
    assert summary.failed_exports == 1
    assert summary.pruned_exports == 0
    assert failed_export is not None
    assert failed_export.status == "failed"
    assert failed_export.metadata_json["trigger"] == "scheduled"
    assert "scheduled_missing_source" in failed_export.metadata_json["error"]["message"]
    assert failed_audit is not None
    assert failed_audit.actor_user_id is None


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
