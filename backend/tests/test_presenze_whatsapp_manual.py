from contextlib import contextmanager
from dataclasses import replace
from datetime import date, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_presenze_whatsapp_admin import _collaborator, _user
from test_presenze_whatsapp_admin import db as db

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import PresenzeDailyPunch, PresenzeDailyRecord
from app.modules.presenze.router.routes import whatsapp_admin as routes
from app.modules.presenze.services import whatsapp_manual_preview as preview
from app.modules.presenze.services import whatsapp_manual_send as sending
from app.modules.presenze.services.whatsapp_config import environment_whatsapp_config
from app.modules.presenze.services.whatsapp_waha import (
    DryRunWhatsAppSender,
    WhatsAppSendError,
    WhatsAppSendResult,
)
from app.modules.presenze.whatsapp_models import PresenzeWhatsAppMessage, PresenzeWhatsAppOptOut


@pytest.fixture
def sample(db, monkeypatch):
    user = _user(db)
    collaborator = _collaborator(db, user.id)
    db.add(OperatorProfile(user_id=user.id, phone="+393331234567", is_active=True))
    record = PresenzeDailyRecord(
        collaborator_id=collaborator.id,
        application_user_id=user.id,
        work_date=date.today() - timedelta(days=10),
        teo_minutes=480,
        validation_status="pending",
    )
    db.add(record)
    db.flush()
    db.add(PresenzeDailyPunch(daily_record_id=record.id, sequence=1, entry_time=time(8)))
    db.commit()
    config = replace(environment_whatsapp_config(), provider="dry_run", min_delay_seconds=25)
    monkeypatch.setattr(preview, "load_whatsapp_config", lambda _: config)
    monkeypatch.setattr(sending, "load_whatsapp_config", lambda _: config)
    monkeypatch.setattr(sending, "is_within_send_window", lambda *args: True)
    return record, collaborator, user


def request(db, record):
    data = preview.manual_preview(db, record.id)
    return sending.ManualSendRequest(fingerprint=data["fingerprint"], reason=data["reason"])


def test_preview_and_simulated_send(db, sample):
    record, _, user = sample
    data = routes.preview_manual_whatsapp(record.id, db, user, user)
    assert "uscita mancante" in data["text"] and "INAZ" in data["text"]
    assert str(record.work_date.year) in data["text"]
    assert db.scalar(select(PresenzeWhatsAppMessage)) is None
    result = routes.send_manual_whatsapp(record.id, request(db, record), db, user, user)
    assert result["status"] == "DRY_RUN"
    message = db.scalar(select(PresenzeWhatsAppMessage))
    assert message.days_json[0]["requested_by_user_id"] == user.id
    assert len(message.days_json) == 1
    with pytest.raises(HTTPException, match="Attendi"):
        sending.send_manual(db, record.id, request(db, record), user.id)


@pytest.mark.parametrize(
    "mutation",
    ["future", "validated", "justified", "inactive", "unmapped", "phone", "stop", "no_anomaly"],
)
def test_ineligible(db, sample, mutation):
    record, collaborator, user = sample
    if mutation == "future":
        record.work_date = date.today() + timedelta(days=1)
    if mutation == "validated":
        record.validation_status = "validated"
    if mutation == "justified":
        record.absence_minutes = 480
    if mutation == "inactive":
        collaborator.is_active = False
    if mutation == "unmapped":
        collaborator.application_user_id = None
    if mutation == "phone":
        db.scalar(select(OperatorProfile)).phone = None
    if mutation == "stop":
        db.add(
            PresenzeWhatsAppOptOut(
                application_user_id=user.id, phone_e164="+393331234567", source="test"
            )
        )
    if mutation == "no_anomaly":
        db.scalar(select(PresenzeDailyPunch)).exit_time = time(17)
    db.commit()
    with pytest.raises(HTTPException):
        preview.manual_preview(db, record.id)


def test_missing_and_anomaly_descriptions(db, sample):
    with pytest.raises(HTTPException) as exc:
        preview.manual_preview(db, uuid4())
    assert exc.value.status_code == 404
    record, _, _ = sample
    db.scalar(select(PresenzeDailyPunch)).exit_time = time(17)
    record.raw_payload_json = {
        "detail_anomalies": [
            {"other": "not a reason"},
            {"Anomalia giornata": "Ore non giustificate"},
            {"col_1": "Verificare orario"},
        ]
    }
    db.commit()
    assert (
        preview.manual_preview(db, record.id)["reason"] == "Ore non giustificate; Verificare orario"
    )
    assert preview.anomaly_reasons([]) == []


@pytest.mark.parametrize(
    "case", ["lock", "stale", "whitespace", "window", "provider", "sender", "configuration"]
)
def test_send_guards(db, sample, monkeypatch, case):
    record, _, user = sample
    payload = request(db, record)

    @contextmanager
    def locked(_):
        yield False

    if case == "lock":
        monkeypatch.setattr(sending, "_advisory_lock", locked)
    if case == "stale":
        payload.fingerprint = "0" * 64
    if case == "whitespace":
        payload.reason = "     "
    if case == "window":
        monkeypatch.setattr(sending, "is_within_send_window", lambda *a: False)
    if case == "provider":
        monkeypatch.setattr(preview, "load_whatsapp_config", lambda _: SimpleNamespace(provider=""))
    if case == "sender":
        monkeypatch.setattr(sending, "build_whatsapp_sender", lambda _: None)
    if case == "configuration":

        def invalid_config(_):
            raise ValueError("missing credentials")

        monkeypatch.setattr(sending, "build_whatsapp_sender", invalid_config)
    with pytest.raises(HTTPException):
        sending.send_manual(db, record.id, payload, user.id)
    assert db.scalar(select(PresenzeWhatsAppMessage)) is None


@pytest.mark.parametrize("status", ["SENT", "FAILED", "UNKNOWN"])
def test_delivery_outcomes_and_duplicate_block(db, sample, monkeypatch, status):
    record, _, user = sample

    class Sender(DryRunWhatsAppSender):
        provider = "waha"

        def send_text(self, phone, text):
            if status != "SENT":
                raise WhatsAppSendError(
                    "test failure",
                    retryable=True,
                    code="network_error",
                    uncertain=status == "UNKNOWN",
                )
            return WhatsAppSendResult("SENT", "waha", "provider-id")

    monkeypatch.setattr(sending, "build_whatsapp_sender", lambda _: Sender())
    result = sending.send_manual(db, record.id, request(db, record), user.id)
    assert result["status"] == status
    if status in {"SENT", "UNKNOWN"}:
        with pytest.raises(HTTPException, match="gia notificata"):
            preview.manual_preview(db, record.id)


@pytest.mark.parametrize("case", ["missing", "error", "changed"])
def test_preflight(db, sample, monkeypatch, case):
    record, _, user = sample

    class Sender(DryRunWhatsAppSender):
        def check_number(self, phone):
            if case == "error":
                raise WhatsAppSendError("error", retryable=True, code="network_error")
            if case == "changed":
                db.scalar(select(OperatorProfile)).phone = "+393331234568"
                db.commit()
            return case != "missing"

        def send_text(self, *args):
            pytest.fail("must not send")

    monkeypatch.setattr(sending, "build_whatsapp_sender", lambda _: Sender())
    with pytest.raises(HTTPException):
        sending.send_manual(db, record.id, request(db, record), user.id)
    assert db.scalar(select(PresenzeWhatsAppMessage)) is None


def test_manual_http_authorization_and_confirmation(db, sample):
    record, _, user = sample
    user.password_hash = hash_password("secret123")
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        url = f"/presenze/whatsapp/daily/{record.id}"
        assert client.get(url + "/preview").status_code == 401
        assert client.post(url + "/send", json={}).status_code == 401
        login = client.post(
            "/auth/login", json={"username": user.username, "password": "secret123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        data = client.get(url + "/preview", headers=headers).json()
        assert data["record_id"] == str(record.id)
        assert client.post(url + "/send", headers=headers, json={}).status_code == 422
        result = client.post(
            url + "/send",
            headers=headers,
            json={"fingerprint": data["fingerprint"], "reason": "Uscita mancante: verifica INAZ"},
        )
        assert result.status_code == 200 and result.json()["status"] == "DRY_RUN"
        user.role = "user"
        db.commit()
        assert client.get(url + "/preview", headers=headers).status_code == 403
        assert client.post(url + "/send", headers=headers, json={}).status_code == 403
        user.role = "admin"
        user.module_presenze = False
        db.commit()
        assert client.get(url + "/preview", headers=headers).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("state", ["profile_missing", "phone_missing", "phone_invalid"])
def test_phone_recovery_returns_canonical_user_and_creates_profile(db, sample, state):
    record, collaborator, user = sample
    profile = db.scalar(select(OperatorProfile))
    if state == "profile_missing":
        db.delete(profile)
    else:
        profile.phone = None if state == "phone_missing" else "invalid"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        preview.manual_preview(db, record.id)
    detail = exc.value.detail
    assert detail["application_user_id"] == collaborator.application_user_id == user.id
    assert detail["collaborator_name"] == collaborator.name
    assert "Aggiungi" in detail["message"]
    from app.modules.presenze.services.whatsapp_admin import update_phone

    update_phone(db, detail["application_user_id"], "+393331234567")
    assert preview.manual_preview(db, record.id)["phone_e164"] == "+393331234567"
    assert db.scalar(select(PresenzeWhatsAppMessage)) is None
