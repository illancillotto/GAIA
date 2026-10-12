"""INAZ diagnostics must survive sync independently of GAIA's operational decision."""

import uuid
from datetime import date

import pytest

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.schemas import PresenzeDailyRecordResponse
from app.modules.presenze.services.gate_inaz_details import gate_inaz_detail_values


@pytest.mark.parametrize("raw", [None, [], {}])
def test_missing_source_details_are_explicit_without_manufacturing_ok(raw):
    record = PresenzeDailyRecord(raw_payload_json=raw)
    serialized = PresenzeDailyRecordResponse.model_construct(operational_status="unknown")
    result = gate_inaz_detail_values(record, serialized)
    assert result["inaz_source"] == {}
    assert result["detail_status"] is None
    assert result["detail_anomalies"] == []
    assert result["inaz_detail_punch_rows"] == []
    assert result["operational_status"] == "unknown"
    assert result["has_inaz_anomaly"] is False


def test_full_inaz_details_are_preserved_even_when_matrix_serializer_omits_them():
    raw = {
        "detail_status": "Giornata anomala",
        "detail_title": "Employee selector " * 3000,
        "detail_anomalies": [{"code": "OREM", "description": "Ore mancanti"}],
        "detail_requests": [{"Stato": "ACC", "Descrizione": "P. ORD"}],
        "detail_programmed_schedule": "OPESAB - 07/13.30",
        "detail_effective_schedule": "OPESAB",
        "detail_time_slots": "07:00 - 13:30",
        "detail_theoretical_hours": "06:30",
        "detail_schedule_type": "Rigido",
        "detail_day_totals": {"Ordinarie": "06:30"},
        "detail_punch_rows": [{"Ora": "07:00", "EU": "E", "Term": "Impianto"}],
        "detail_text": "Dettaglio originale",
        "detail_error": None,
    }
    record = PresenzeDailyRecord(raw_payload_json=raw, stato="Giornata anomala")
    serialized = PresenzeDailyRecordResponse.model_construct(
        id=uuid.uuid4(),
        collaborator_id=uuid.uuid4(),
        work_date=date(2026, 10, 3),
        stato=record.stato,
        operational_status="ok",
        operational_expected_minutes=390,
        operational_notes=["INAZ segnala anomalia, ma la formula GAIA quadra le ore"],
    )
    result = gate_inaz_detail_values(record, serialized)
    assert result["operational_status"] == "ok"
    assert result["detail_status"] == "Giornata anomala"
    assert result["detail_requests"] == raw["detail_requests"]
    assert result["detail_anomalies"] == raw["detail_anomalies"]
    assert result["detail_time_slots"] == raw["detail_time_slots"]
    assert result["detail_effective_schedule"] == "OPESAB"
    assert result["detail_day_totals"] == raw["detail_day_totals"]
    assert result["inaz_detail_punch_rows"] == raw["detail_punch_rows"]
    assert result["inaz_source"] == {
        key: value for key, value in raw.items() if key != "detail_title"
    }
    assert "detail_title" not in result
    assert "detail_title" not in result["inaz_source"]
    assert result["has_inaz_anomaly"] is True
    assert result["operational_expected_minutes"] == 390
