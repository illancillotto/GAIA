from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, datetime, timezone
from decimal import Decimal
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatImportBatch, CatParticella, CatUtenzaIrrigua
from app.modules.operazioni.models.reports import FieldReport, FieldReportCategory, FieldReportSeverity
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


shapely_module = types.ModuleType("shapely")
shapely_geometry_module = types.ModuleType("shapely.geometry")
shapely_geometry_module.shape = lambda geometry: geometry
shapely_module.geometry = shapely_geometry_module
sys.modules.setdefault("shapely", shapely_module)
sys.modules.setdefault("shapely.geometry", shapely_geometry_module)

geoalchemy2_module = types.ModuleType("geoalchemy2")
geoalchemy2_shape_module = types.ModuleType("geoalchemy2.shape")
geoalchemy2_shape_module.to_shape = lambda geometry: geometry
geoalchemy2_module.shape = geoalchemy2_shape_module
sys.modules.setdefault("geoalchemy2", geoalchemy2_module)
sys.modules.setdefault("geoalchemy2.shape", geoalchemy2_shape_module)

from app.modules.catasto.routes.gis import read_whitecompany_reports_layer
from app.modules.catasto.services.gis_service import (
    _load_particella_ruolo_summary,
    _search_particelle_by_tax_code,
    get_whitecompany_reports_layer,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _add_particella(
    db,
    *,
    foglio: str,
    particella: str,
    created_at: datetime,
    with_ruolo: bool = False,
) -> str:
    batch_id = uuid.uuid4()
    db.add(
        CatImportBatch(
            id=batch_id,
            filename=f"batch-{foglio}-{particella}.csv",
            tipo="utenze",
            anno_campagna=2025,
            status="completed",
        )
    )
    particella_id = uuid.uuid4()
    db.add(
        CatParticella(
            id=particella_id,
            cod_comune_capacitas=95,
            codice_catastale="A357",
            nome_comune="ARBOREA",
            foglio=foglio,
            particella=particella,
            source_type="test",
            import_batch_id=batch_id,
            valid_from=date(2025, 1, 1),
            is_current=True,
            suppressed=False,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    db.add(
        CatUtenzaIrrigua(
            id=uuid.uuid4(),
            import_batch_id=batch_id,
            anno_campagna=2025,
            particella_id=particella_id,
            codice_fiscale="03122560927",
            created_at=created_at,
        )
    )
    if with_ruolo:
        db.add(
            RuoloParticella(
                id=uuid.uuid4(),
                partita_id=uuid.uuid4(),
                anno_tributario=2025,
                foglio=foglio,
                particella=particella,
                cat_particella_id=particella_id,
            )
        )
    db.flush()
    return str(particella_id)


def test_search_particelle_prioritizes_ruolo_for_tax_code() -> None:
    db = TestingSessionLocal()
    try:
        older_role_id = _add_particella(
            db,
            foglio="1",
            particella="10",
            created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
            with_ruolo=True,
        )
        newest_non_role_id = _add_particella(
            db,
            foglio="2",
            particella="20",
            created_at=datetime(2025, 3, 10, tzinfo=timezone.utc),
            with_ruolo=False,
        )
        middle_non_role_id = _add_particella(
            db,
            foglio="3",
            particella="30",
            created_at=datetime(2025, 2, 10, tzinfo=timezone.utc),
            with_ruolo=False,
        )
        db.commit()

        result_ids = _search_particelle_by_tax_code(db, "03122560927", 3)

        assert result_ids == [
            older_role_id,
            newest_non_role_id,
            middle_non_role_id,
        ]
    finally:
        db.close()


def test_load_particella_ruolo_summary_falls_back_to_subject_comune_match() -> None:
    db = TestingSessionLocal()
    try:
        particella_id = uuid.UUID(
            _add_particella(
                db,
                foglio="9",
                particella="99",
                created_at=datetime(2025, 4, 10, tzinfo=timezone.utc),
                with_ruolo=False,
            )
        )
        avviso_id = uuid.uuid4()
        db.add(
            RuoloAvviso(
                id=avviso_id,
                import_job_id=uuid.uuid4(),
                codice_cnc="01.02025009999999",
                anno_tributario=2025,
                codice_fiscale_raw="03122560927",
                nominativo_raw="LAORE SARDEGNA",
            )
        )
        db.add(
            RuoloPartita(
                id=uuid.uuid4(),
                avviso_id=avviso_id,
                codice_partita="000000402/00000",
                comune_nome="ARBOREA",
                contribuente_cf="03122560927",
                importo_0648=17288.12,
                importo_0985=12346.56,
            )
        )
        db.commit()

        particella = db.get(CatParticella, particella_id)
        assert particella is not None

        summary = _load_particella_ruolo_summary(db, particella)

        assert summary is not None
        assert summary.source_mode == "subject_comune_fallback"
        assert summary.n_righe == 1
        assert summary.importo_manut_euro_totale == 17288.12
        assert summary.importo_ist_euro_totale == 12346.56
        assert summary.importo_totale_euro == 29634.68
        assert summary.items[0].codice_partita == "000000402/00000"
    finally:
        db.close()


def test_whitecompany_reports_layer_filters_counts_and_geojson() -> None:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username="catasto-gis-admin",
            email="catasto-gis-admin@example.local",
            password_hash="hash",
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_catasto=True,
        )
        perdita = FieldReportCategory(code="perdita", name="Perdita condotta", is_active=True)
        sfalcio = FieldReportCategory(code="sfalcio", name="Sfalcio", is_active=True)
        severity = FieldReportSeverity(code="normal", name="Normale", rank_order=10, is_active=True)
        db.add_all([user, perdita, sfalcio, severity])
        db.flush()

        matching_report_id = uuid.uuid4()
        db.add_all(
            [
                FieldReport(
                    id=matching_report_id,
                    report_number="REP-WHITE-1",
                    external_code="W-1",
                    reporter_user_id=user.id,
                    category_id=perdita.id,
                    severity_id=severity.id,
                    title="Perdita condotta",
                    description="Acqua su strada",
                    reporter_name="Mario Rossi",
                    area_code="Distretto 12",
                    latitude=Decimal("39.9123456"),
                    longitude=Decimal("8.6123456"),
                    assigned_responsibles="Squadra A",
                    source_system="white",
                    status="open",
                    created_at=datetime(2026, 7, 10, 9, 30, tzinfo=timezone.utc),
                ),
                FieldReport(
                    id=uuid.uuid4(),
                    report_number="REP-WHITE-2",
                    external_code="W-2",
                    reporter_user_id=user.id,
                    category_id=perdita.id,
                    severity_id=severity.id,
                    title="Perdita senza coordinate",
                    reporter_name="Mario Rossi",
                    source_system="white",
                    status="open",
                    created_at=datetime(2026, 7, 11, 9, 30, tzinfo=timezone.utc),
                ),
                FieldReport(
                    id=uuid.uuid4(),
                    report_number="REP-WHITE-3",
                    external_code="W-3",
                    reporter_user_id=user.id,
                    category_id=sfalcio.id,
                    severity_id=severity.id,
                    title="Sfalcio canale",
                    reporter_name="Luigi Verdi",
                    latitude=Decimal("39.8000000"),
                    longitude=Decimal("8.5000000"),
                    source_system="white",
                    status="open",
                    created_at=datetime(2026, 7, 10, 10, 30, tzinfo=timezone.utc),
                ),
                FieldReport(
                    id=uuid.uuid4(),
                    report_number="REP-GAIA-1",
                    reporter_user_id=user.id,
                    category_id=perdita.id,
                    severity_id=severity.id,
                    title="Segnalazione interna",
                    reporter_name="Mario Rossi",
                    latitude=Decimal("39.7000000"),
                    longitude=Decimal("8.4000000"),
                    source_system="gaia",
                    status="open",
                    created_at=datetime(2026, 7, 10, 11, 30, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()

        result = get_whitecompany_reports_layer(
            db,
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            tipologia="perdita condotta",
            operatore="mario rossi",
            limit=10,
        )

        assert result.stats.total == 2
        assert result.stats.mapped == 1
        assert result.stats.unmapped == 1
        assert result.stats.truncated is False
        assert result.tipologie == ["Perdita condotta", "Sfalcio"]
        assert result.operatori == ["Luigi Verdi", "Mario Rossi"]
        assert result.geojson["type"] == "FeatureCollection"
        assert len(result.geojson["features"]) == 1
        feature = result.geojson["features"][0]
        assert feature["geometry"] == {"type": "Point", "coordinates": [8.6123456, 39.9123456]}
        assert feature["properties"]["id"] == str(matching_report_id)
        assert feature["properties"]["tipologia"] == "Perdita condotta"
        assert feature["properties"]["operatore"] == "Mario Rossi"
        assert feature["properties"]["assigned_responsibles"] == "Squadra A"

        route_result = read_whitecompany_reports_layer(
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            tipologia="Perdita condotta",
            operatore="Mario Rossi",
            limit=10,
            db=db,
            _=user,
        )
        assert route_result.stats.total == result.stats.total
        assert route_result.geojson["features"][0]["properties"]["id"] == str(matching_report_id)
    finally:
        db.close()
