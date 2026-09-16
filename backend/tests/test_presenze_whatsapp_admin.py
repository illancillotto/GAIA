from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, time
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.router.routes import whatsapp_admin as routes
from app.modules.presenze.services import whatsapp_admin as service
from app.modules.presenze.services import whatsapp_config as config_service
from app.modules.presenze.services.punch_reminders import (
    PunchPair,
    ReminderContact,
    ReminderDayInput,
)
from app.modules.presenze.services.whatsapp_config import environment_whatsapp_config
from app.modules.presenze.services.whatsapp_session import WahaSessionError
from app.modules.presenze.whatsapp_admin_schemas import (
    WhatsAppConfigUpdate,
    WhatsAppMessageQuery,
    WhatsAppPhoneUpdate,
    WhatsAppReconcileRequest,
)
from app.modules.presenze.whatsapp_models import (
    PresenzeWhatsAppConfig,
    PresenzeWhatsAppMessage,
    PresenzeWhatsAppOptOut,
)


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def _user(db: Session, username: str = "mrossi") -> ApplicationUser:
    item = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        full_name="Mario Rossi",
        password_hash="hash",
        role="admin",
        is_active=True,
        module_presenze=True,
    )
    db.add(item)
    db.flush()
    return item


def _collaborator(db: Session, user_id: int | None) -> PresenzeCollaborator:
    item = PresenzeCollaborator(
        application_user_id=user_id,
        employee_code=str(uuid.uuid4())[:8],
        company_code="53",
        name="ROSSI MARIO",
        is_active=True,
    )
    db.add(item)
    db.flush()
    return item


def _message(
    db: Session,
    collaborator: PresenzeCollaborator,
    user_id: int | None,
    status: str,
) -> PresenzeWhatsAppMessage:
    item = PresenzeWhatsAppMessage(
        collaborator_id=collaborator.id,
        application_user_id=user_id,
        phone_e164="+393331234567",
        text_body="Testo promemoria",
        days_json=[
            {"work_date": "2026-09-14", "problem": "missing_exit", "detail": "uscita mancante"}
        ],
        status=status,
        provider="waha",
    )
    db.add(item)
    db.flush()
    return item


def test_dashboard_summary_counts_and_provider_state(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _user(db)
    collaborator = _collaborator(db, user.id)
    for status in ("SENT", "DELIVERED", "READ", "FAILED", "NOT_ON_WHATSAPP", "SENDING", "UNKNOWN"):
        _message(db, collaborator, user.id, status)
    db.add(PresenzeWhatsAppOptOut(application_user_id=user.id, source="reply"))
    db.commit()

    config = replace(environment_whatsapp_config(), provider="waha")
    monkeypatch.setattr(service, "load_whatsapp_config", lambda db: config)
    monkeypatch.setattr(service, "_session_status", lambda config: ("working", None))
    result = service.dashboard_summary(db, datetime(2026, 9, 15, 8, 0, tzinfo=UTC))
    assert result["provider_enabled"] is True
    assert result["provider"] == "waha"
    assert result["session_status"] == "working"
    assert result["next_run_at"] is not None
    assert result["sent_total"] == 3
    assert result["delivered_total"] == 2
    assert result["read_total"] == 1
    assert result["failed_total"] == 2
    assert result["uncertain_total"] == 2
    assert result["opted_out_total"] == 1
    assert result["send_window"] == "08:00-19:00"

    monkeypatch.setattr(
        service, "load_whatsapp_config", lambda db: replace(config, provider="")
    )
    disabled = service.dashboard_summary(db)
    assert disabled["provider"] is None
    assert disabled["next_run_at"] is None


def test_session_status_covers_configuration_and_waha_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = environment_whatsapp_config()
    assert service._session_status(replace(base, provider="")) == ("disabled", None)
    assert service._session_status(replace(base, provider="dry_run"))[0] == "dry_run"
    custom = replace(base, provider="custom")
    assert service._session_status(custom) == ("unsupported", "Provider custom non supportato")
    assert service._session_status(replace(base, provider="waha", waha_url=""))[0] == "misconfigured"
    configured = replace(base, provider="waha", waha_url="http://waha", waha_api_key="secret")

    def network_error(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(service.httpx, "get", network_error)
    assert service._session_status(configured)[0] == "unavailable"
    monkeypatch.setattr(service.httpx, "get", lambda *args, **kwargs: httpx.Response(503))
    assert service._session_status(configured) == ("unavailable", "WAHA HTTP 503")
    monkeypatch.setattr(
        service.httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(200, content=b"not-json"),
    )
    assert service._session_status(configured)[0] == "invalid_response"
    monkeypatch.setattr(
        service.httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(200, json=[]),
    )
    assert service._session_status(configured)[1] == "Stato sessione WAHA assente"
    monkeypatch.setattr(
        service.httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(200, json={"status": " "}),
    )
    assert service._session_status(configured)[0] == "invalid_response"
    monkeypatch.setattr(
        service.httpx,
        "get",
        lambda url, **kwargs: httpx.Response(200, json={"status": " WORKING "}),
    )
    assert service._session_status(replace(configured, waha_session="")) == ("working", None)


def test_message_history_filters_paginates_and_keeps_deleted_user(db: Session) -> None:
    user = _user(db)
    collaborator = _collaborator(db, user.id)
    sent = _message(db, collaborator, user.id, "SENT")
    _message(db, collaborator, user.id, "FAILED")
    db.commit()

    result = service.list_messages(db, status="SENT", query="Mario", page=1, page_size=1)
    assert result["total"] == 1
    assert result["items"][0]["id"] == sent.id
    assert result["items"][0]["user_label"] == "Mario Rossi"
    assert result["items"][0]["username"] == "mrossi"

    user.full_name = ""
    db.commit()
    fallback = service.list_messages(db, status=None, query="333", page=2, page_size=1)
    assert fallback["total"] == 2
    assert fallback["page"] == 2

    orphan_collaborator = _collaborator(db, None)
    orphan = _message(db, orphan_collaborator, None, "FAILED")
    db.commit()
    orphan_row = service.list_messages(db, status="FAILED", query=None, page=1, page_size=10)
    payload = next(item for item in orphan_row["items"] if item["id"] == orphan.id)
    assert payload["user_label"] == "ROSSI MARIO"
    assert payload["username"] is None


def test_preview_includes_ready_and_skipped(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    ready_id, skipped_id = uuid.uuid4(), uuid.uuid4()
    items = [
        ReminderDayInput(
            ready_id, "ROSSI MARIO", 1, date(2026, 9, 14), (PunchPair(time(8), None),)
        ),
        ReminderDayInput(
            skipped_id, "BIANCHI ANNA", None, date(2026, 9, 14), (PunchPair(time(8), None),)
        ),
    ]
    monkeypatch.setattr(service, "load_reminder_inputs", lambda *_: items)
    monkeypatch.setattr(service, "load_notified_days", lambda *_: frozenset())
    monkeypatch.setattr(service, "blocked_days", lambda *_: frozenset())
    monkeypatch.setattr(service, "load_opted_out_user_ids", lambda *_: frozenset())
    monkeypatch.setattr(
        service,
        "load_reminder_contacts",
        lambda *_: {1: ReminderContact(1, "+39 333 1234567", True)},
    )

    result = service.build_preview(db, datetime(2026, 9, 15, 8, tzinfo=UTC))
    assert result["ready"][0]["ready"] is True
    assert result["ready"][0]["message_text"].startswith("Ciao Mario")
    assert result["skipped"][0]["reason"] == "operator_not_linked"
    assert result["skipped"][0]["message_text"] is None


def test_opt_out_phone_and_removal_management(db: Session) -> None:
    user = _user(db)
    collaborator = _collaborator(db, user.id)
    opt_out = PresenzeWhatsAppOptOut(
        application_user_id=user.id, phone_e164="+393331234567", source="reply"
    )
    db.add(opt_out)
    db.commit()

    rows = service.list_opt_outs(db)
    assert rows[0]["collaborator_name"] == collaborator.name
    assert rows[0]["user_label"] == "Mario Rossi"
    assert service.update_phone(db, 9999, "+39") is None
    assert service.update_phone(db, user.id, " +39 333 ")["phone"] == "+39 333"
    profile = db.query(OperatorProfile).filter_by(user_id=user.id).one()
    assert service.update_phone(db, user.id, "")["phone"] is None
    assert profile.phone is None
    assert service.remove_opt_out(db, 9999) is False
    assert service.remove_opt_out(db, user.id) is True


def test_admin_route_success_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = SimpleNamespace()
    monkeypatch.setattr(routes, "dashboard_summary", lambda db: {"db": db})
    monkeypatch.setattr(routes, "list_messages", lambda db, **kwargs: kwargs)
    monkeypatch.setattr(routes, "build_preview", lambda db: {"preview": db})
    monkeypatch.setattr(routes, "list_opt_outs", lambda db: [{"db": db}])
    monkeypatch.setattr(routes, "load_whatsapp_config", lambda db: "config")
    monkeypatch.setattr(routes, "serialize_whatsapp_config", lambda config: {"value": config})
    monkeypatch.setattr(routes, "update_whatsapp_config", lambda db, payload, user_id: user_id)
    assert routes.get_whatsapp_configuration(fake_db, None, None) == {"value": "config"}
    config_payload = WhatsAppConfigUpdate(
        provider="", waha_url="http://waha:3000", waha_session="default",
        reminder_cron="30 9 * * 1-5", lookback_days=3, include_missing_punches=False,
        max_per_run=40, min_delay_seconds=25, max_delay_seconds=75,
        send_start_hour=8, send_end_hour=19,
    )
    assert routes.put_whatsapp_configuration(
        config_payload, fake_db, SimpleNamespace(id=7), None
    ) == {"value": 7}
    assert routes._session_manager(fake_db).config == "config"
    session_manager = SimpleNamespace(
        status=lambda: {"status": "working"},
        start=lambda: {"status": "starting"},
        qr_code=lambda: {"image_data_url": "data:image/png;base64,cXI="},
        logout=lambda: {"status": "stopped"},
    )
    monkeypatch.setattr(routes, "_session_manager", lambda db: session_manager)
    assert routes.get_whatsapp_session(fake_db, None, None)["status"] == "working"
    assert routes.start_whatsapp_session(fake_db, None, None)["status"] == "starting"
    response = Response()
    assert routes.get_whatsapp_session_qr(response, fake_db, None, None)["image_data_url"]
    assert response.headers["Cache-Control"] == "no-store"
    assert routes.logout_whatsapp_session(fake_db, None, None)["status"] == "stopped"

    def fail_session():
        raise WahaSessionError("WAHA offline", status_code=503)

    with pytest.raises(HTTPException) as session_error:
        routes._session_action(fail_session)
    assert session_error.value.status_code == 503
    monkeypatch.setattr(routes, "remove_opt_out", lambda db, user_id: user_id == 1)
    monkeypatch.setattr(
        routes,
        "update_phone",
        lambda db, user_id, phone: None if user_id == 2 else {"phone": phone},
    )
    assert routes.get_whatsapp_dashboard(fake_db, None, None) == {"db": fake_db}
    query = WhatsAppMessageQuery(status="READ", q="rossi", page=2, page_size=10)
    assert routes.get_whatsapp_messages(fake_db, None, None, query)["page"] == 2
    assert routes.get_whatsapp_preview(fake_db, None, None) == {"preview": fake_db}
    assert routes.get_whatsapp_opt_outs(fake_db, None, None) == [{"db": fake_db}]
    assert routes.delete_whatsapp_opt_out(1, fake_db, None, None).status_code == 204
    with pytest.raises(HTTPException) as missing_stop:
        routes.delete_whatsapp_opt_out(2, fake_db, None, None)
    assert missing_stop.value.status_code == 404
    assert routes.patch_whatsapp_phone(
        1, WhatsAppPhoneUpdate(phone="+39"), fake_db, None, None
    ) == {"phone": "+39"}
    with pytest.raises(HTTPException) as missing_user:
        routes.patch_whatsapp_phone(2, WhatsAppPhoneUpdate(phone="+39"), fake_db, None, None)
    assert missing_user.value.status_code == 404


def test_reconcile_route_translates_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempt_id = uuid.uuid4()
    calls = []
    monkeypatch.setattr(
        routes, "reconcile_uncertain_attempt", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    payload = WhatsAppReconcileRequest(sent=True, evidence="Verificato", provider_message_id="wa-1")
    assert (
        routes.reconcile_whatsapp_message(attempt_id, payload, object(), None, None).status_code
        == 204
    )
    assert calls[0][1]["sent"] is True

    def fail(*args, **kwargs):
        raise ValueError("stato non valido")

    monkeypatch.setattr(routes, "reconcile_uncertain_attempt", fail)
    with pytest.raises(HTTPException) as error:
        routes.reconcile_whatsapp_message(attempt_id, payload, object(), None, None)
    assert error.value.status_code == 409


def test_admin_endpoints_require_and_accept_real_authentication(db: Session) -> None:
    user = _user(db)
    user.password_hash = hash_password("secret123")
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        assert client.get("/presenze/whatsapp/dashboard").status_code == 401
        login = client.post(
            "/auth/login", json={"username": user.username, "password": "secret123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/presenze/whatsapp/dashboard", headers=headers).status_code == 200
        assert client.get("/presenze/whatsapp/configuration", headers=headers).status_code == 403
        assert client.get("/presenze/whatsapp/session", headers=headers).status_code == 403
        user.role = "super_admin"
        db.commit()
        assert client.get("/presenze/whatsapp/configuration", headers=headers).status_code == 200
        payload = {
            "provider": "dry_run", "waha_url": "http://waha:3000/", "waha_session": "default",
            "reminder_cron": "30 9 * * 1-5", "lookback_days": 3,
            "include_missing_punches": False, "max_per_run": 40,
            "min_delay_seconds": 25, "max_delay_seconds": 75,
            "send_start_hour": 8, "send_end_hour": 19,
        }
        saved = client.put("/presenze/whatsapp/configuration", headers=headers, json=payload)
        assert saved.status_code == 200
        assert saved.json()["provider"] == "dry_run"
        assert "waha_api_key" not in saved.json()
        assert client.get("/presenze/whatsapp/messages", headers=headers).json()["total"] == 0
        assert client.get("/presenze/whatsapp/preview", headers=headers).status_code == 200
        assert client.get("/presenze/whatsapp/opt-outs", headers=headers).json() == []
        assert (
            client.patch(
                f"/presenze/whatsapp/users/{user.id}/phone",
                headers=headers,
                json={"phone": "+39 333 1234567"},
            ).status_code
            == 200
        )
        assert client.delete("/presenze/whatsapp/opt-outs/999", headers=headers).status_code == 404
        assert (
            client.post(
                f"/presenze/whatsapp/messages/{uuid.uuid4()}/reconcile",
                headers=headers,
                json={"sent": False, "evidence": "Controllato in WAHA"},
            ).status_code
            == 409
        )
    finally:
        app.dependency_overrides.clear()


def test_configuration_encrypts_secrets_and_validates_activation(db: Session) -> None:
    payload = WhatsAppConfigUpdate(
        provider="dry_run", waha_url="http://waha:3000/", waha_session="default",
        waha_api_key="api-secret", waha_hmac_key="hmac-secret",
        reminder_cron="30 9 * * 1-5", lookback_days=5, include_missing_punches=True,
        max_per_run=20, min_delay_seconds=10, max_delay_seconds=20,
        send_start_hour=8, send_end_hour=18,
    )
    result = config_service.update_whatsapp_config(db, payload, user_id=12)
    row = db.get(PresenzeWhatsAppConfig, 1)
    assert row is not None
    assert row.waha_api_key_encrypted != "api-secret"
    assert result.waha_api_key == "api-secret"
    serialized = config_service.serialize_whatsapp_config(result)
    assert serialized["api_key_configured"] is True
    assert "waha_api_key" not in serialized

    cleared = payload.model_copy(update={
        "provider": "", "waha_api_key": None, "waha_hmac_key": None,
        "clear_api_key": True, "clear_hmac_key": True,
    })
    assert config_service.update_whatsapp_config(db, cleared, user_id=12).waha_api_key == ""
    with pytest.raises(HTTPException) as missing_secret:
        config_service.update_whatsapp_config(
            db, payload.model_copy(update={"provider": "waha", "waha_api_key": None, "waha_hmac_key": None}), user_id=12
        )
    assert missing_secret.value.status_code == 409
    with pytest.raises(HTTPException) as bad_cron:
        config_service.update_whatsapp_config(
            db, payload.model_copy(update={"reminder_cron": "bad cron"}), user_id=12
        )
    assert bad_cron.value.status_code == 422


def test_configuration_schema_rejects_inverted_ranges() -> None:
    values = dict(
        provider="", waha_url="http://waha", waha_session="default",
        reminder_cron="30 9 * * 1-5", lookback_days=3, include_missing_punches=False,
        max_per_run=40, min_delay_seconds=30, max_delay_seconds=20,
        send_start_hour=8, send_end_hour=19,
    )
    with pytest.raises(ValueError, match="pausa massima"):
        WhatsAppConfigUpdate(**values)
    values.update(min_delay_seconds=10, max_delay_seconds=20, send_start_hour=19, send_end_hour=19)
    with pytest.raises(ValueError, match="fine della fascia"):
        WhatsAppConfigUpdate(**values)
    values["send_end_hour"] = 20
    for invalid in (
        {"waha_url": "javascript:alert(1)"},
        {"waha_session": "../admin"},
        {"waha_session": "   "},
    ):
        with pytest.raises(ValueError):
            WhatsAppConfigUpdate(**(values | invalid))
