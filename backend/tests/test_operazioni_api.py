from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.activities import (
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityAttachment,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gps import GpsTrackSummary


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
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def seed_operazioni_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni-admin",
        email="operazioni-admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers() -> dict[str, str]:
    seed_operazioni_user()
    response = client.post(
        "/auth/login",
        json={"username": "operazioni-admin", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def auth_headers_without_operazioni() -> dict[str, str]:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="no-operazioni",
        email="no-operazioni@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=False,
    )
    db.add(user)
    db.commit()
    db.close()

    response = client.post(
        "/auth/login",
        json={"username": "no-operazioni", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_activity_gps_viewer_extracts_track_points() -> None:
    db = TestingSessionLocal()
    catalog = ActivityCatalog(code="GPS-VIEW", name="GPS viewer activity", category="test")
    db.add(catalog)
    db.flush()

    track = GpsTrackSummary(
        source_type="provider_import",
        provider_name="test_provider",
        provider_track_id="TRACK-001",
        started_at=datetime.fromisoformat("2026-04-09T08:00:00"),
        ended_at=datetime.fromisoformat("2026-04-09T08:45:00"),
        start_latitude=Decimal("39.9031000"),
        start_longitude=Decimal("8.5923000"),
        end_latitude=Decimal("39.9112000"),
        end_longitude=Decimal("8.6014000"),
        total_distance_km=Decimal("6.250"),
        total_duration_seconds=2700,
        raw_payload_json={
            "track": {
                "points": [
                    {
                        "latitude": 39.9031,
                        "longitude": 8.5923,
                        "timestamp": "2026-04-09T08:00:00",
                    },
                    {
                        "latitude": 39.9075,
                        "longitude": 8.5961,
                        "timestamp": "2026-04-09T08:18:00",
                    },
                    {
                        "latitude": 39.9112,
                        "longitude": 8.6014,
                        "timestamp": "2026-04-09T08:45:00",
                    },
                ]
            }
        },
    )
    db.add(track)
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=1,
        started_at=datetime.fromisoformat("2026-04-09T08:00:00"),
        ended_at=datetime.fromisoformat("2026-04-09T08:45:00"),
        status="submitted",
        gps_track_summary_id=track.id,
    )
    db.add(activity)
    db.commit()

    response = client.get(
        f"/operazioni/activities/{activity.id}/gps-viewer",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_mode"] == "track"
    assert payload["point_count"] == 3
    assert payload["uses_raw_payload"] is True
    assert payload["summary"]["provider_track_id"] == "TRACK-001"
    assert payload["points"][1]["latitude"] == pytest.approx(39.9075)
    assert payload["bounds"]["max_longitude"] == pytest.approx(8.6014)

    db.close()


def test_attachment_download_returns_file(tmp_path: Path) -> None:
    db = TestingSessionLocal()
    file_path = tmp_path / "operazioni-note.txt"
    file_path.write_text("contenuto allegato test", encoding="utf-8")

    attachment = Attachment(
        storage_path=str(file_path),
        original_filename="operazioni-note.txt",
        mime_type="text/plain",
        extension="txt",
        attachment_type="note",
        file_size_bytes=file_path.stat().st_size,
        source_context="operator_activity",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    response = client.get(
        f"/operazioni/attachments/{attachment.id}/download",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.text == "contenuto allegato test"
    assert "operazioni-note.txt" in response.headers["content-disposition"]
    assert response.headers["content-type"].startswith("text/plain")

    db.close()


def test_operazioni_module_requires_module_flag() -> None:
    response = client.get(
        "/operazioni/dashboard/summary",
        headers=auth_headers_without_operazioni(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Module access denied"
