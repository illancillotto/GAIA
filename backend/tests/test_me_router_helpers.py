from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.me import router
from fastapi import HTTPException


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


def test_resolve_period_bounds_uses_defaults_and_rejects_invalid_range() -> None:
    start, end = router._resolve_period_bounds(None, None)
    assert start.day == 1
    assert end >= start

    with pytest.raises(HTTPException) as exc:
        router._resolve_period_bounds(date(2026, 5, 31), date(2026, 5, 1))

    assert exc.value.status_code == 422


def test_activity_duration_minutes_prefers_calculated_then_declared() -> None:
    calculated = SimpleNamespace(duration_minutes_calculated=90, duration_minutes_declared=30)
    declared = SimpleNamespace(duration_minutes_calculated=None, duration_minutes_declared=45)
    empty = SimpleNamespace(duration_minutes_calculated=None, duration_minutes_declared=None)

    assert router._activity_duration_minutes(calculated) == 90
    assert router._activity_duration_minutes(declared) == 45
    assert router._activity_duration_minutes(empty) == 0


def test_vehicle_session_km_uses_route_end_or_legacy_odometers() -> None:
    route = SimpleNamespace(route_distance_km=12.5, end_odometer_km=None, start_odometer_km=None, km_start=None, km_end=None)
    odometer = SimpleNamespace(route_distance_km=None, end_odometer_km=110.0, start_odometer_km=100.0, km_start=None, km_end=None)
    legacy = SimpleNamespace(route_distance_km=None, end_odometer_km=None, start_odometer_km=None, km_start=20.0, km_end=27.5)
    empty = SimpleNamespace(route_distance_km=None, end_odometer_km=None, start_odometer_km=None, km_start=None, km_end=None)

    assert router._vehicle_session_km(route) == 12.5
    assert router._vehicle_session_km(odometer) == 10.0
    assert router._vehicle_session_km(legacy) == 7.5
    assert router._vehicle_session_km(empty) == 0.0


def test_module_enabled_for_super_admin_and_module_flags() -> None:
    super_admin = ApplicationUser(
        username="root",
        email="root@example.local",
        password_hash="hash",
        role=ApplicationUserRole.SUPER_ADMIN.value,
        module_presenze=False,
    )
    viewer = ApplicationUser(
        username="viewer",
        email="viewer@example.local",
        password_hash="hash",
        role=ApplicationUserRole.VIEWER.value,
        module_presenze=True,
        module_operazioni=False,
    )

    assert router._module_enabled(super_admin, "presenze") is True
    assert router._module_enabled(viewer, "presenze") is True
    assert router._module_enabled(viewer, "operazioni") is False


def test_get_mapped_collaborator_returns_first_match() -> None:
    collaborator = SimpleNamespace(id=uuid.uuid4(), name="Mario Rossi")
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = collaborator

    user = SimpleNamespace(id=7)
    assert router._get_mapped_collaborator(db, user) is collaborator
    db.execute.assert_called_once()


def test_get_mapped_collaborator_or_409_rejects_unmapped_user() -> None:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        router._get_mapped_collaborator_or_409(db, SimpleNamespace(id=7))

    assert exc.value.status_code == 409
    assert exc.value.detail == "Nessun collaboratore Presenze associato all'utente corrente"


def test_convert_xlsx_to_pdf_handles_libreoffice_failures(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    xlsx_path = tmp_path / "straordinari.xlsx"
    xlsx_path.write_bytes(b"xlsx")
    monkeypatch.setattr(router.shutil, "which", lambda _binary: "/usr/bin/libreoffice")
    monkeypatch.setattr(
        router.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="errore conversione", stdout=""),
    )

    with pytest.raises(HTTPException) as exc:
        router._convert_xlsx_to_pdf(xlsx_path, tmp_path)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Conversione PDF fallita: errore conversione"


def test_convert_xlsx_to_pdf_requires_output_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    xlsx_path = tmp_path / "straordinari.xlsx"
    xlsx_path.write_bytes(b"xlsx")
    monkeypatch.setattr(router.shutil, "which", lambda _binary: "/usr/bin/libreoffice")
    monkeypatch.setattr(
        router.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    with pytest.raises(HTTPException) as exc:
        router._convert_xlsx_to_pdf(xlsx_path, tmp_path)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Conversione PDF completata senza file di output"


def test_convert_xlsx_to_pdf_returns_generated_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    xlsx_path = tmp_path / "straordinari.xlsx"
    xlsx_path.write_bytes(b"xlsx")

    def fake_run(*_args, **_kwargs):
        (tmp_path / "straordinari.pdf").write_bytes(b"pdf")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(router.shutil, "which", lambda _binary: "/usr/bin/libreoffice")
    monkeypatch.setattr(router.subprocess, "run", fake_run)

    assert router._convert_xlsx_to_pdf(xlsx_path, tmp_path) == tmp_path / "straordinari.pdf"


def test_get_self_daily_record_or_404_returns_record_or_raises() -> None:
    record = SimpleNamespace(id=uuid.uuid4())
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = record
    user = SimpleNamespace(id=3)

    assert router._get_self_daily_record_or_404(db, record.id, user) is record

    db.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc:
        router._get_self_daily_record_or_404(db, uuid.uuid4(), user)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Daily record not found"


def test_current_month_bounds_and_hours_from_minutes() -> None:
    today = date.today()
    start, end = router._current_month_bounds()

    assert start == today.replace(day=1)
    assert end == today.replace(day=calendar.monthrange(today.year, today.month)[1])
    assert router._hours_from_minutes(90) == 1.5


def test_serialize_assigned_device_uses_resolved_label(monkeypatch: pytest.MonkeyPatch) -> None:
    device = SimpleNamespace(
        id=12,
        ip_address="192.168.1.10",
        hostname="tablet-01",
        display_name="Tablet campo",
        lifecycle_state="active",
        status="online",
        device_type="tablet",
        operating_system="Android",
        asset_label="ASSET-01",
        location_hint="Magazzino",
        last_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(router, "_resolve_device_label", lambda value: ("Tablet campo", "tablet-01"))

    item = router._serialize_assigned_device(device)

    assert item.id == 12
    assert item.resolved_label == "Tablet campo"
    assert item.ip_address == "192.168.1.10"


def test_daily_record_effective_extra_minutes_honors_overrides() -> None:
    record = SimpleNamespace(
        override_straordinario_minutes=15,
        straordinario_minutes=5,
        override_mpe_minutes=10,
        mpe_minutes=3,
    )
    fallback = SimpleNamespace(
        override_straordinario_minutes=None,
        straordinario_minutes=4,
        override_mpe_minutes=None,
        mpe_minutes=6,
    )

    assert router._daily_record_effective_extra_minutes(record) == 25
    assert router._daily_record_effective_extra_minutes(fallback) == 10
