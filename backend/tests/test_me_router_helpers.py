from __future__ import annotations

from types import SimpleNamespace

from app.modules.me import router


def test_daily_record_has_anomaly_reads_normalized_inaz_detail_payload() -> None:
    record = SimpleNamespace(
        raw_payload_json={
            "detail_status": "Giornata anomala",
            "detail_anomalies": [],
        },
        stato=None,
    )

    assert router._daily_record_has_anomaly(record) is True


def test_daily_record_has_anomaly_falls_back_to_legacy_stato() -> None:
    record = SimpleNamespace(raw_payload_json=None, stato="anomalia")

    assert router._daily_record_has_anomaly(record) is True


def test_daily_record_has_anomaly_returns_false_without_signals() -> None:
    record = SimpleNamespace(raw_payload_json={"detail_status": "ok", "detail_anomalies": []}, stato="validata")

    assert router._daily_record_has_anomaly(record) is False
