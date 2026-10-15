"""Characterization tests for the Ruolo GAIA role calculation (slice R116).

They pin the per-position status classification of
``get_gaia_role_calculation`` (threshold boundaries, ``only_in_capacitas``,
``anomalous_only`` filtering applied after the status) and the remaining
public branches of ``app.modules.ruolo.repositories``.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto import CatastoParcel
from app.models.catasto_phase1 import CatImportBatch, CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.utenze.models import AnagraficaPaymentNotice

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


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="ruolo-r116",
            email="ruolo-r116@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_ruolo=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "ruolo-r116", "password": "secret123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _active_batch(db: Session, anno: int = 2025) -> CatImportBatch:
    batch = CatImportBatch(
        filename=f"capacitas-r116-{anno}.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=anno,
        status="completed",
        completed_at=datetime.now(UTC),
    )
    db.add(batch)
    db.flush()
    return batch


def _incass_notice(
    notice_id: str,
    tax_code: str | None,
    display_name: str | None,
    amount_0648: str,
    amount_0985: str = "0.00",
    *,
    anno: str = "2025",
    amount_0668: str = "0.00",
) -> AnagraficaPaymentNotice:
    return AnagraficaPaymentNotice(
        source_system="incass",
        source_notice_id=notice_id,
        anno=anno,
        codice_fiscale=tax_code,
        partita_iva=None,
        display_name=display_name,
        raw_detail_json={
            "partitario": {
                "partite": [
                    {
                        "importo_0648_euro": amount_0648,
                        "importo_0985_euro": amount_0985,
                        "importo_0668_euro": amount_0668,
                    }
                ]
            }
        },
    )


def _utenza(
    batch: CatImportBatch,
    tax_code: str,
    excel_0648: float,
    *,
    imponibile_sf: float = 100,
    aliquota_0648: float = 0.1,
    nome_comune: str | None = "ORISTANO",
    anomalous: bool = False,
    **extra: Any,
) -> CatUtenzaIrrigua:
    return CatUtenzaIrrigua(
        import_batch_id=batch.id,
        anno_campagna=batch.anno_campagna,
        codice_fiscale=tax_code,
        denominazione=extra.pop("denominazione", f"CAP {tax_code[:6]}"),
        nome_comune=nome_comune,
        sup_irrigabile_mq=extra.pop("sup_irrigabile_mq", 1000),
        imponibile_sf=imponibile_sf,
        aliquota_0648=aliquota_0648,
        aliquota_0985=0,
        importo_0648=excel_0648,
        importo_0985=0,
        anomalia_imponibile=False,
        anomalia_importi=anomalous,
        **extra,
    )


def test_gaia_calculation_status_boundaries_and_mixed_counts() -> None:
    db = TestingSessionLocal()
    batch = _active_batch(db)
    db.add_all(
        [
            # Two Incass notices for the same position: amounts add up, the first display name stays.
            _incass_notice("R116-MATCH-1", "MTCHAA80A01H501Z", "RUOLO MATCH", "10.00"),
            _incass_notice("R116-MATCH-2", "MTCHAA80A01H501Z", "RUOLO MATCH", "0.01"),
            _incass_notice("R116-MISMATCH", "MSMTCH80A01H501Z", "RUOLO MISMATCH", "10.02"),
            _incass_notice("R116-DELTA", "DLTONL80A01H501Z", "RUOLO DELTA", "10.01"),
            _incass_notice("R116-RUOLO-ONLY", "RLONLY80A01H501Z", "RUOLO ONLY", "5.00"),
            # delta == threshold and gap == threshold -> matched
            _utenza(batch, "MTCHAA80A01H501Z", 10.01),
            # delta == 0.02 > threshold -> amount_mismatch
            _utenza(batch, "MSMTCH80A01H501Z", 10.00),
            # delta == threshold but Excel gap far above threshold -> still matched
            _utenza(batch, "DLTONL80A01H501Z", 30.00),
            # no Incass position at all, and no comune on the row
            _utenza(batch, "CAPONL80A01H501Z", 10.00, nome_comune=None),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/calcolo-gaia?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    by_tax = {item["tax_code"]: item for item in payload["items"]}

    matched = by_tax["MTCHAA80A01H501Z"]
    assert matched["status"] == "matched"
    assert matched["diagnosis"] == "allineato"
    assert matched["ruolo_display_name"] == "RUOLO MATCH"
    assert matched["ruolo_totale_confrontabile"] == 10.01
    assert matched["gaia_total"] == 10.0
    assert matched["delta_ruolo_gaia_totale"] == 0.01
    assert matched["gap_excel_gaia_total"] == 0.01

    mismatch = by_tax["MSMTCH80A01H501Z"]
    assert mismatch["status"] == "amount_mismatch"
    assert mismatch["diagnosis"] == "problema_ruolo"
    assert mismatch["delta_ruolo_gaia_totale"] == 0.02
    assert mismatch["gap_excel_gaia_total"] == 0.0

    delta_only = by_tax["DLTONL80A01H501Z"]
    assert delta_only["status"] == "matched"
    assert delta_only["diagnosis"] == "allineato"
    assert delta_only["delta_ruolo_gaia_totale"] == 0.01
    assert delta_only["gap_excel_gaia_total"] == 20.0

    capacitas_only = by_tax["CAPONL80A01H501Z"]
    assert capacitas_only["status"] == "only_in_capacitas"
    assert capacitas_only["diagnosis"] == "problema_ruolo"
    assert capacitas_only["ruolo_display_name"] is None
    assert capacitas_only["ruolo_totale_confrontabile"] == 0.0
    assert capacitas_only["delta_ruolo_gaia_totale"] == -10.0
    assert capacitas_only["comuni_count"] == 0

    assert "RLONLY80A01H501Z" not in by_tax
    assert payload["items"][0]["tax_code"] == "DLTONL80A01H501Z"

    summary = payload["summary"]
    assert summary["positions"] == 4
    assert summary["ruolo_positions"] == 4
    assert summary["total_rows"] == 4
    assert summary["clean_rows"] == 4
    assert summary["anomalous_rows"] == 0
    assert summary["mismatch_positions"] == 2
    assert summary["diagnosis_ruolo_count"] == 2
    assert summary["diagnosis_gaia_count"] == 0
    assert summary["diagnosis_excel_count"] == 0
    assert summary["ruolo_totale_0648"] == 35.04
    assert summary["gaia_totale_0648"] == 40.0
    assert summary["excel_totale_0648"] == 60.01


def test_gaia_calculation_missing_ruolo_wins_over_zero_delta() -> None:
    db = TestingSessionLocal()
    batch = _active_batch(db)
    # No Incass position and zero imponibile: delta and gap are both 0.0, yet the
    # position must be reported as only_in_capacitas, never as matched.
    db.add(_utenza(batch, "ZEROGA80A01H501Z", 0.00, imponibile_sf=0))
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/calcolo-gaia?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["tax_code"] == "ZEROGA80A01H501Z"
    assert item["gaia_total"] == 0.0
    assert item["delta_ruolo_gaia_totale"] == 0.0
    assert item["gap_excel_gaia_total"] == 0.0
    assert item["status"] == "only_in_capacitas"
    assert item["diagnosis"] == "problema_ruolo"
    assert payload["summary"]["mismatch_positions"] == 1
    assert payload["summary"]["diagnosis_ruolo_count"] == 1


def test_gaia_calculation_anomalous_only_filters_after_status() -> None:
    db = TestingSessionLocal()
    batch = _active_batch(db)
    db.add_all(
        [
            _incass_notice("R116-ANOM", "ANOMDR80A01H501Z", "RUOLO ANOM", "30.00"),
            _incass_notice("R116-ANOMLOW", "ANOMLW80A01H501Z", "RUOLO ANOMLOW", "20.00"),
            _incass_notice("R116-CLEAN", "CLEANP80A01H501Z", "RUOLO CLEAN", "10.00"),
            # Whole Excel/GAIA gap comes from the anomalous row -> anomaly driven.
            _utenza(batch, "ANOMDR80A01H501Z", 10.00),
            _utenza(batch, "ANOMDR80A01H501Z", 20.00, anomalous=True),
            # Anomalous row is aligned, the gap is on the clean row -> not anomaly driven.
            _utenza(batch, "ANOMLW80A01H501Z", 20.00),
            _utenza(batch, "ANOMLW80A01H501Z", 10.00, anomalous=True),
            _utenza(batch, "CLEANP80A01H501Z", 10.00),
        ]
    )
    db.commit()
    db.close()

    full = client.get("/ruolo/stats/calcolo-gaia?anno=2025", headers=auth_headers()).json()
    full_by_tax = {item["tax_code"]: item for item in full["items"]}
    assert full_by_tax["ANOMDR80A01H501Z"]["status"] == "amount_mismatch"
    assert full_by_tax["ANOMDR80A01H501Z"]["anomaly_driven_case"] is True
    assert full_by_tax["ANOMDR80A01H501Z"]["anomaly_gap_share"] == 100.0
    assert full_by_tax["ANOMLW80A01H501Z"]["status"] == "matched"
    assert full_by_tax["ANOMLW80A01H501Z"]["anomaly_driven_case"] is False
    assert full_by_tax["ANOMLW80A01H501Z"]["anomaly_gap_share"] == 0.0
    assert full_by_tax["CLEANP80A01H501Z"]["status"] == "matched"
    assert full["summary"]["mismatch_positions"] == 1
    assert full["summary"]["anomaly_driven_positions"] == 1

    response = client.get(
        "/ruolo/stats/calcolo-gaia?anno=2025&anomalous_only=true", headers=auth_headers()
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["tax_code"] for item in payload["items"]] == ["ANOMDR80A01H501Z"]
    item = payload["items"][0]
    assert item["status"] == "amount_mismatch"
    assert item["diagnosis"] == "problema_ricalcolo_gaia"
    assert item["anomalous_rows_count"] == 1
    assert item["clean_rows_count"] == 1
    assert item["delta_ruolo_gaia_totale"] == 10.0
    assert item["gap_excel_gaia_total"] == 10.0

    summary = payload["summary"]
    assert summary["positions"] == 3
    assert summary["anomalous_positions"] == 2
    assert summary["anomaly_driven_positions"] == 1
    assert summary["mismatch_positions"] == 1
    assert summary["diagnosis_gaia_count"] == 1
    assert summary["total_rows"] == 5
    assert summary["anomalous_rows"] == 2

    filtered = client.get(
        "/ruolo/stats/calcolo-gaia?anno=2025&tax_code=%20anomlw80a01h501z%20",
        headers=auth_headers(),
    ).json()
    assert filtered["summary"]["positions"] == 1
    assert [item["tax_code"] for item in filtered["items"]] == ["ANOMLW80A01H501Z"]
    assert filtered["items"][0]["status"] == "matched"


def test_gaia_calculation_without_active_batch_reports_ruolo_side_only() -> None:
    db = TestingSessionLocal()
    db.add_all(
        [
            _incass_notice(
                "R116-NOBATCH-1",
                "NOBTCH80A01H501Z",
                "RUOLO NOBATCH",
                "12.30",
                "4.20",
                anno="2026",
                amount_0668="1.50",
            ),
            _incass_notice("R116-NOBATCH-2", None, "SENZA CF", "1.00", anno="2026"),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/calcolo-gaia?anno=2026", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    summary = payload["summary"]
    assert summary["active_batch_id"] is None
    assert summary["positions"] == 0
    assert summary["ruolo_positions"] == 1
    assert summary["ruolo_positions_missing_tax_code"] == 1
    assert summary["ruolo_totale_0648"] == 12.3
    assert summary["ruolo_totale_0985"] == 4.2
    assert summary["ruolo_totale_0668"] == 1.5
    assert summary["ruolo_totale_confrontabile"] == 16.5
    assert summary["delta_ruolo_gaia_totale"] == 16.5
    assert summary["mismatch_positions"] == 0


def test_stats_particelle_and_catasto_parcels_without_filters_cover_all_years() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_r116", status="completed")
    db.add(job)
    db.flush()
    avviso_2024 = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-R116-2024",
        anno_tributario=2024,
        nominativo_raw="ROSSI 2024",
        importo_totale_euro=7.0,
    )
    avviso_2025 = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-R116-2025",
        anno_tributario=2025,
        nominativo_raw="ROSSI 2025",
        importo_totale_euro=9.0,
    )
    db.add_all([avviso_2024, avviso_2025])
    db.flush()
    partita = RuoloPartita(
        avviso_id=avviso_2025.id, codice_partita="P-R116", comune_nome="ORISTANO"
    )
    db.add(partita)
    db.flush()
    db.add_all(
        [
            RuoloParticella(
                partita_id=partita.id, anno_tributario=2024, foglio="1", particella="1"
            ),
            RuoloParticella(
                partita_id=partita.id, anno_tributario=2025, foglio="1", particella="2"
            ),
            CatastoParcel(
                comune_codice="A357",
                comune_nome="ARBOREA",
                foglio="5",
                particella="120",
                valid_from=2024,
                valid_to=2024,
                source="ruolo_import",
            ),
            CatastoParcel(
                comune_codice="G113",
                comune_nome="ORISTANO",
                foglio="7",
                particella="12",
                valid_from=2025,
                valid_to=None,
                source="ruolo_import",
            ),
        ]
    )
    db.commit()
    db.close()

    stats = client.get("/ruolo/stats", headers=auth_headers())
    assert stats.status_code == 200
    assert [(item["anno_tributario"], item["totale_euro"]) for item in stats.json()["items"]] == [
        (2025, 9.0),
        (2024, 7.0),
    ]

    particelle = client.get("/ruolo/stats/particelle", headers=auth_headers())
    assert particelle.status_code == 200
    assert particelle.json()["anno_tributario"] is None
    assert particelle.json()["total_particelle"] == 2

    parcels = client.get("/catasto/parcels", headers=auth_headers())
    assert parcels.status_code == 200
    assert [item["comune_nome"] for item in parcels.json()] == ["ARBOREA", "ORISTANO"]


def test_capacitas_check_keeps_first_snapshot_display_name_for_repeated_tax_code() -> None:
    db = TestingSessionLocal()
    batch = _active_batch(db)
    # The snapshot query has no ORDER BY: "PRIMO NOME" being first relies on
    # SQLite returning rows in insertion order.
    db.add_all(
        [
            _utenza(batch, "SNPDUP80A01H501Z", 10.00, denominazione="PRIMO NOME"),
            _utenza(batch, "SNPDUP80A01H501Z", 5.00, denominazione="SECONDO NOME"),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/capacitas-check?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "only_in_capacitas"
    assert items[0]["capacitas_display_name"] == "PRIMO NOME"
    assert items[0]["excel_0648"] == 15.0


def test_capacitas_detail_leaves_ambiguous_ruolo_parcels_unmatched() -> None:
    db = TestingSessionLocal()
    batch = _active_batch(db)
    db.add(
        _utenza(
            batch,
            "AMBIGU80A01H501Z",
            10.00,
            cco="CCO-9",
            foglio="1",
            particella="1",
            sup_irrigabile_mq=0,
            ind_spese_fisse=None,
        )
    )
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_r116_detail", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-R116-AMBIGUO",
        anno_tributario=2025,
        codice_fiscale_raw="AMBIGU80A01H501Z",
        nominativo_raw="AMBIGUO",
    )
    db.add(avviso)
    db.flush()
    partita = RuoloPartita(avviso_id=avviso.id, codice_partita="CCO-9/Q0001", comune_nome="")
    db.add(partita)
    db.flush()
    db.add_all(
        [
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="1",
                particella="1",
                subalterno="A",
                importo_manut=4.0,
                importo_ist=1.0,
            ),
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="1",
                particella="1",
                subalterno="B",
                importo_manut=6.0,
                importo_ist=2.0,
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/stats/capacitas-check/detail?anno=2025&tax_code=AMBIGU80A01H501Z",
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    row = payload["rows"][0]
    assert row["ruolo_match_found"] is False
    assert row["ruolo_match_level"] == "none"
    assert row["ruolo_total"] == 0.0
    assert row["imponibile_per_mq"] is None
    assert row["ind_spese_fisse"] is None
    assert payload["comuni"][0]["ruolo_matched_rows_count"] == 0
    assert payload["comuni"][0]["ruolo_total"] == 0.0
    assert payload["summary"]["distinct_ind_spese_fisse"] == []
    assert payload["summary"]["distinct_imponibile_per_mq"] == []
