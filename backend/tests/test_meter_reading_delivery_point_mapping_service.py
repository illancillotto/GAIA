from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatDeliveryPoint,
    CatDistretto,
    CatMeterReading,
    CatMeterReadingDeliveryPointMapping,
    CatMeterReadingImport,
)
from app.modules.catasto.services.delivery_points_import import resolve_delivery_point_id
from app.modules.catasto.services.meter_reading_delivery_point_mapping_service import (
    apply_all_delivery_point_mappings,
    create_mapping_from_reading,
)


def _build_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _create_tables(engine) -> None:
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            CatDistretto.__table__,
            CatDeliveryPoint.__table__,
            CatMeterReadingImport.__table__,
            CatMeterReading.__table__,
            CatMeterReadingDeliveryPointMapping.__table__,
        ],
    )


def test_create_mapping_from_reading_backfills_same_point_in_same_distretto() -> None:
    engine = _build_engine()
    _create_tables(engine)
    with Session(engine) as db:
        user = ApplicationUser(username="mapper", email="mapper@example.test", password_hash="x")
        distretto = CatDistretto(num_distretto="28", nome_distretto="Distretto 28")
        point = CatDeliveryPoint(
            distretto_code="28_1D_1L",
            punto_consegna_code="14_1_1",
            is_active=True,
            source_dataset="2026_DEF",
        )
        db.add_all([user, distretto, point])
        db.flush()
        reading_a = CatMeterReading(anno=2026, distretto_id=distretto.id, punto_consegna="14_1_1_A", source="excel")
        reading_b = CatMeterReading(anno=2025, distretto_id=distretto.id, punto_consegna="14_1_1_A", source="excel")
        reading_other = CatMeterReading(anno=2026, distretto_id=distretto.id, punto_consegna="14_1_1_B", source="excel")
        db.add_all([reading_a, reading_b, reading_other])
        db.flush()

        mapping, stats = create_mapping_from_reading(
            db,
            reading=reading_a,
            delivery_point=point,
            current_user=user,
            change_note="mapping operativo",
        )

        assert mapping.distretto_code == "28"
        assert mapping.source_point_code == "14_1_1_A"
        assert mapping.delivery_point_id == point.id
        assert stats == {"linked": 2, "untouched": 0}
        assert reading_a.delivery_point_id == point.id
        assert reading_b.delivery_point_id == point.id
        assert reading_other.delivery_point_id is None


def test_resolve_delivery_point_id_prefers_manual_mapping() -> None:
    engine = _build_engine()
    _create_tables(engine)
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="28", nome_distretto="Distretto 28")
        point = CatDeliveryPoint(
            distretto_code="28_1D_2L",
            punto_consegna_code="14_1_1",
            is_active=True,
            source_dataset="2026_DEF",
        )
        db.add_all([distretto, point])
        db.flush()
        db.add(
            CatMeterReadingDeliveryPointMapping(
                distretto_code="28",
                source_point_code="14_1_1_A",
                delivery_point_id=point.id,
            )
        )
        db.commit()

        assert resolve_delivery_point_id(
            db,
            distretto=distretto,
            punto_consegna="14_1_1_A",
            cache={},
        ) == point.id


def test_apply_all_delivery_point_mappings_script_entrypoint(monkeypatch, capsys) -> None:
    engine = _build_engine()
    _create_tables(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        distretto = CatDistretto(num_distretto="293", nome_distretto="Distretto 293")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="293",
            punto_consegna_code="P2.S1_1",
            is_active=True,
            source_dataset="2026_DEF",
        )
        reading = CatMeterReading(anno=2026, distretto_id=distretto.id, punto_consegna="P2.S1_A", source="excel")
        db.add_all([point, reading])
        db.flush()
        db.add(
            CatMeterReadingDeliveryPointMapping(
                distretto_code="293",
                source_point_code="P2.S1_A",
                delivery_point_id=point.id,
            )
        )
        db.commit()
        point_id = point.id

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "backfill_delivery_point_manual_mappings.py"
    spec = importlib.util.spec_from_file_location("backfill_delivery_point_manual_mappings_under_test", script_path)
    assert spec is not None and spec.loader is not None
    script_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script_module)

    monkeypatch.setattr(script_module, "SessionLocal", SessionLocal)
    assert script_module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"linked": 1, "untouched": 0, "mappings": 1}

    with Session(engine) as db:
        linked = db.execute(select(CatMeterReading.delivery_point_id)).scalar_one()
        assert linked == point_id
