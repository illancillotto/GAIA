from __future__ import annotations

from collections.abc import Generator
import sys
import types

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if "geoalchemy2" not in sys.modules:
    geoalchemy2_module = types.ModuleType("geoalchemy2")
    geoalchemy2_shape = types.ModuleType("geoalchemy2.shape")
    geoalchemy2_shape.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.catasto.services.dui_2026_overlay import Dui2026DependencyUnavailableError


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "catasto-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        db.add(
            ApplicationUser(
                username="catasto-admin",
                email="catasto-admin@example.local",
                password_hash=hash_password("secret123"),
                role=ApplicationUserRole.ADMIN.value,
                is_active=True,
                module_catasto=True,
            )
        )
        db.commit()


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_dui_2026_latest_layer_endpoint_returns_live_overlay(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.catasto.routes.gis.get_dui_2026_latest_layer",
        lambda db: {
            "label": "DUI 2026 live",
            "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
            "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
            "source_date": "2026-06-25",
            "source_updated_at": "2026-06-26T07:43:00",
            "stats": {
                "total_polygons": 2,
                "in_ruolo_2025": 1,
                "not_in_ruolo_2025": 1,
                "with_contatore": 1,
                "without_contatore": 1,
                "with_telerilev": 0,
            },
            "geojson": {"type": "FeatureCollection", "features": []},
        },
    )

    response = client.get("/catasto/gis/dui-2026/latest-layer", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "DUI 2026 live"
    assert payload["source_date"] == "2026-06-25"
    assert payload["stats"]["in_ruolo_2025"] == 1


def test_dui_2026_domanda_detail_endpoint_returns_role_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.catasto.routes.gis.get_dui_2026_domanda_detail",
        lambda db, domanda_irrigua: {
            "domanda_irrigua": domanda_irrigua,
            "codice_fiscale": "RSSMRA80A01H501U",
            "intestatario": "Rossi Mario",
            "telefono": "3400000000",
            "coltura": "OLIVO",
            "tipo_domanda": "NW",
            "data_domanda": "2026-06-25",
            "contatore": "SI",
            "telerilev": "NO",
            "operatore": "DDF",
            "sup_grafica_mq_totale": 2337,
            "n_poligoni": 1,
            "x": 1459603.748,
            "y": 4421548.212,
            "in_ruolo_2025": True,
            "ruolo_2025_match_count": 1,
            "ruolo_summary": {
                "anno_tributario_latest": 2025,
                "anno_tributario_richiesto": 2025,
                "source_mode": "dui_domanda",
                "source_note": "Dettaglio ruolo 2025 aggregato per domanda irrigua.",
                "n_righe": 1,
                "n_subalterni": 1,
                "sup_catastale_ha_totale": 0.3,
                "sup_irrigata_ha_totale": 0.2337,
                "importo_manut_euro_totale": 10,
                "importo_irrig_euro_totale": 20,
                "importo_ist_euro_totale": 3,
                "importo_totale_euro": 33,
                "items": [],
            },
            "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
            "source_date": "2026-06-25",
        },
    )

    response = client.get("/catasto/gis/dui-2026/domande/16", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["domanda_irrigua"] == "16"
    assert payload["in_ruolo_2025"] is True
    assert payload["ruolo_summary"]["source_mode"] == "dui_domanda"


def test_dui_2026_latest_layer_endpoint_returns_503_when_osgeo_is_unavailable(monkeypatch) -> None:
    def raise_dependency_error(_db):
        raise Dui2026DependencyUnavailableError(
            "Layer DUI 2026 non disponibile: installare GDAL/OSGeo oppure pyshp+pyproj nel backend."
        )

    monkeypatch.setattr(
        "app.modules.catasto.routes.gis.get_dui_2026_latest_layer",
        raise_dependency_error,
    )

    response = client.get("/catasto/gis/dui-2026/latest-layer", headers=auth_headers())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Layer DUI 2026 non disponibile: installare GDAL/OSGeo oppure pyshp+pyproj nel backend."
    }
