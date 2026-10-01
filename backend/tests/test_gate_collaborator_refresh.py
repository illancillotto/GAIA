from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from sqlalchemy import select
from test_gate_mobile_sync import _build_session, _seed_presenze_daily_record

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeAutoSyncConfig,
    PresenzeCollaborator,
    PresenzeCredential,
    PresenzeSyncJob,
)
from app.modules.presenze.services import gate_collaborator_refresh as service
from app.scripts import gate_collaborator_refresh as polling


@pytest.fixture
def db():
    session = _build_session()
    _seed_presenze_daily_record(session)
    session.get(ApplicationUser, 77).role = "admin"
    for model in (PresenzeCredential, PresenzeAutoSyncConfig):
        model.__table__.create(session.get_bind(), checkfirst=True)
    session.add(
        PresenzeCredential(
            id=1,
            application_user_id=77,
            label="test",
            username="test",
            password_encrypted="encrypted",
            active=True,
        )
    )
    session.add(PresenzeAutoSyncConfig(id=1, credential_id=1))
    session.commit()
    yield session
    session.close()


@pytest.fixture
def action():
    return {
        "id": str(uuid.uuid4()),
        "action_type": service.ACTION_TYPE,
        "target_id": "018f88a2-1797-7365-bf5e-8bb8b7f9d001",
        "payload_json": {
            "gaia_user_id": "77",
            "collaborator_gaia_user_id": "77",
            "collaborator_id": "018f88a2-1797-7365-bf5e-8bb8b7f9d001",
            "month": "2026-07",
        },
    }


def run_poll(db, action, handler):
    async def run():
        async with httpx.AsyncClient(
            base_url="https://gate.test", transport=httpx.MockTransport(handler)
        ) as client:
            await service.process_collaborator_refreshes(
                db, client, {"Authorization": "Bearer test"}
            )

    asyncio.run(run())


def test_enqueue_idempotent_and_complete_with_scoped_punches(db, action):
    calls = []

    def handler(request):
        calls.append((request.url.path, json.loads(request.content) if request.content else None))
        if request.method == "GET":
            assert request.url.params["action_type"] == service.ACTION_TYPE
            return httpx.Response(200, json={"actions": [action]})
        return httpx.Response(200, json={})

    run_poll(db, action, handler)
    run_poll(db, action, handler)
    jobs = db.scalars(select(PresenzeSyncJob)).all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.priority == 0
    assert job.params_json["employee_codes"] == ["P001"]
    assert job.period_start == date(2026, 7, 1) and job.period_end == date(2026, 7, 31)
    job.status = "running"
    db.commit()
    run_poll(db, action, handler)
    assert all(body is None for _, body in calls)
    job.status, job.records_imported = "completed", 1
    job.params_json = {**job.params_json, "checkpoint": {"completed_employee_codes": ["P001"]}}
    db.commit()
    run_poll(db, action, handler)
    posts = [(path, body) for path, body in calls if body is not None]
    assert [path.rsplit("/", 2)[-2:] for path, _ in posts[:2]] == [
        ["giornaliere", "snapshot"],
        ["anomalie", "snapshot"],
    ]
    daily = posts[0][1]
    assert daily["collaborator_id"] == action["target_id"]
    assert len(daily["giornaliere"]) == 1
    assert daily["giornaliere"][0]["detail_punch_rows"] == [
        {"entry_time": "08:00", "exit_time": "15:00"}
    ]
    assert posts[-1][0].endswith("/ack")
    assert posts[-1][1]["gaia_entity_id"] == str(job.id)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_actor",
        "inactive_actor",
        "missing_collaborator",
        "wrong_id",
        "unmapped",
        "wrong_mapping",
        "duplicate_mapping",
        "denied",
        "duplicate_code",
        "bad_month",
        "short_month",
        "invalid_month",
        "missing_payload",
    ],
)
def test_identity_and_access_fail_closed(db, action, monkeypatch, mutation):
    collaborator = db.get(PresenzeCollaborator, uuid.UUID(action["target_id"]))
    actor = db.get(ApplicationUser, 77)
    if mutation == "missing_actor":
        action["payload_json"]["gaia_user_id"] = "999"
    if mutation == "inactive_actor":
        actor.is_active = False
    if mutation == "missing_collaborator":
        action["target_id"] = str(uuid.uuid4())
    if mutation == "wrong_id":
        action["payload_json"]["collaborator_id"] = str(uuid.uuid4())
    if mutation == "unmapped":
        collaborator.application_user_id = None
    if mutation == "wrong_mapping":
        action["payload_json"]["collaborator_gaia_user_id"] = "999"
    if mutation == "duplicate_mapping":
        original = db.scalars

        def scalars(stmt):
            if "application_user_id =" in str(stmt):
                return SimpleNamespace(all=lambda: [collaborator.id, uuid.uuid4()])
            return original(stmt)

        monkeypatch.setattr(db, "scalars", scalars)
    if mutation == "denied":
        monkeypatch.setattr(service, "_can_refresh_collaborator", lambda *_: False)
    if mutation == "duplicate_code":
        db.add(
            PresenzeCollaborator(
                employee_code=collaborator.employee_code, company_code="other", name="Other"
            )
        )
    if mutation == "bad_month":
        action["payload_json"]["month"] = "2026/07"
    if mutation == "short_month":
        action["payload_json"]["month"] = "07"
    if mutation == "invalid_month":
        action["payload_json"]["month"] = "2026-13"
    if mutation == "missing_payload":
        del action["payload_json"]
    db.commit()
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"actions": [action]})
        posts.append(request)
        return httpx.Response(200, json={})

    run_poll(db, action, handler)
    assert len(posts) == 1 and posts[0].url.path.endswith("/fail")
    assert not db.scalars(select(PresenzeSyncJob)).all()


@pytest.mark.parametrize("kind", ["config_missing", "credential_missing", "inactive"])
def test_missing_credentials(db, action, kind):
    if kind == "config_missing":
        db.delete(db.get(PresenzeAutoSyncConfig, 1))
    if kind == "credential_missing":
        db.get(PresenzeAutoSyncConfig, 1).credential_id = None
    if kind == "inactive":
        db.get(PresenzeCredential, 1).active = False
    db.commit()
    actor, collaborator, month = service._refresh_target(db, action)
    with pytest.raises(ValueError, match="credenziale"):
        service._refresh_job(db, action, actor, collaborator, month)


@pytest.mark.parametrize(
    "state,imported,errors",
    [("failed", 0, 0), ("cancelled", 0, 0), ("completed", 0, 0), ("completed", 1, 1)],
)
def test_never_ack_failed_or_partial_import(db, action, state, imported, errors):
    actor, collaborator, month = service._refresh_target(db, action)
    job = service._refresh_job(db, action, actor, collaborator, month)
    job.status, job.records_imported, job.records_errors = state, imported, errors
    db.commit()
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"actions": [action]})
        posts.append(request.url.path)
        return httpx.Response(200, json={})

    run_poll(db, action, handler)
    assert posts == [f"/api/mobile/connector/presenze/pending-actions/{action['id']}/fail"]


def test_empty_snapshot_and_network_retry(db, action, monkeypatch):
    actor, collaborator, month = service._refresh_target(db, action)
    job = service._refresh_job(db, action, actor, collaborator, month)
    job.status, job.records_imported = "completed", 1
    job.params_json = {**job.params_json, "checkpoint": {"completed_employee_codes": ["P001"]}}
    db.commit()
    monkeypatch.setattr(service, "_scoped_snapshots", lambda *_: ({"giornaliere": []}, {}))
    paths = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"actions": [action]})
        paths.append(request.url.path)
        return httpx.Response(200, json={})

    run_poll(db, action, handler)
    assert paths[-1].endswith("/fail")

    def broken(request):
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        run_poll(db, action, broken)


def test_scoped_snapshot_no_anomalies_or_records(db, action, monkeypatch):
    from app.modules.presenze.services import gate_mobile_record_items

    collaborator = db.get(PresenzeCollaborator, uuid.UUID(action["target_id"]))
    item = {"record_id": "r1"}
    monkeypatch.setattr(
        gate_mobile_record_items,
        "build_presenze_record_items",
        lambda *_a, **_kw: ([item], {"r1": SimpleNamespace(severity="none")}),
    )
    assert service._scoped_snapshots(db, collaborator, "2026-07")[1]["anomalie"] == []
    monkeypatch.setattr(
        gate_mobile_record_items, "build_presenze_record_items", lambda *_a, **_kw: ([], {})
    )
    assert service._scoped_snapshots(db, collaborator, "2026-06")[0]["giornaliere"] == []


def test_poll_thread_configuration_run_stop_and_retry(monkeypatch):
    monkeypatch.setattr(
        polling,
        "settings",
        SimpleNamespace(gate_mobile_gateway_base_url="", gate_mobile_connector_token=""),
    )
    stop = Mock()
    assert polling.start_refresh_polling(stop) is None
    monkeypatch.setattr(
        polling,
        "settings",
        SimpleNamespace(
            gate_mobile_gateway_base_url="https://gate.test", gate_mobile_connector_token="test"
        ),
    )
    thread = Mock()
    factory = Mock(return_value=thread)
    monkeypatch.setattr(polling.threading, "Thread", factory)
    assert polling.start_refresh_polling(stop) is thread
    thread.start.assert_called_once()

    def failed():
        raise RuntimeError("temporary")

    monkeypatch.setattr(polling, "_poll_once", failed)
    stop.is_set.return_value = False
    stop.wait.return_value = True
    polling._run(stop)
    stop.wait.assert_called_with(3)
    stop.is_set.side_effect = [False, True]
    stop.wait.return_value = False

    async def success():
        pass

    monkeypatch.setattr(polling, "_poll_once", success)
    polling._run(stop)


def test_poll_once_opens_own_session_and_client(monkeypatch):
    db = Mock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock()
    monkeypatch.setattr(polling, "SessionLocal", lambda: db)
    from unittest.mock import AsyncMock

    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    monkeypatch.setattr(polling.httpx, "AsyncClient", lambda **_: client)
    process = AsyncMock()
    monkeypatch.setattr(polling, "process_collaborator_refreshes", process)
    asyncio.run(polling._poll_once())
    process.assert_awaited_once()


def test_refresh_team_scope_and_own_identity(db, action):
    actor, collaborator, _ = service._refresh_target(db, action)
    start, end = date(2026, 7, 1), date(2026, 7, 31)
    actor.role = "reviewer"
    assert service._can_refresh_collaborator(db, actor, collaborator, start, end)
    collaborator.application_user_id = 88
    assert service._can_refresh_collaborator(db, actor, collaborator, start, end)
    from app.modules.presenze.models import OrganizationTeamSupervisorAssignment

    db.query(OrganizationTeamSupervisorAssignment).delete()
    db.commit()
    assert not service._can_refresh_collaborator(db, actor, collaborator, start, end)


def test_fast_poll_never_consumes_other_action_types(db):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"actions": [{"action_type": "patch_daily_record"}]})

    run_poll(db, None, handler)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "progress,completed", [({"failed_collaborators": 1}, ["P001"]), ({}, []), ({}, ["OTHER"])]
)
def test_completed_worker_with_scrape_failure_or_wrong_checkpoint_is_not_acked(
    db, action, progress, completed
):
    actor, collaborator, month = service._refresh_target(db, action)
    job = service._refresh_job(db, action, actor, collaborator, month)
    job.status, job.records_imported = "completed", 1
    job.params_json = {
        **job.params_json,
        "progress": progress,
        "checkpoint": {"completed_employee_codes": completed},
    }
    db.commit()
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"actions": [action]})
        posts.append(request.url.path)
        return httpx.Response(200, json={})

    run_poll(db, action, handler)
    assert posts == [f"/api/mobile/connector/presenze/pending-actions/{action['id']}/fail"]


@pytest.mark.parametrize("invalid", [True, "77.0", 77.5, 0, -77])
def test_actor_namespace_rejects_noncanonical_ids(db, action, invalid):
    action["payload_json"]["gaia_user_id"] = invalid
    with pytest.raises(ValueError):
        service._refresh_target(db, action)


def test_network_failure_after_daily_push_retries_same_job_without_early_ack(db, action):
    actor, collaborator, month = service._refresh_target(db, action)
    job = service._refresh_job(db, action, actor, collaborator, month)
    job.status, job.records_imported = "completed", 1
    job.params_json = {**job.params_json, "checkpoint": {"completed_employee_codes": ["P001"]}}
    db.commit()
    requests = []
    failed = True

    def handler(request):
        nonlocal failed
        if request.method == "GET":
            return httpx.Response(200, json={"actions": [action]})
        requests.append(request.url.path)
        if request.url.path.endswith("/anomalie/snapshot") and failed:
            failed = False
            return httpx.Response(503)
        return httpx.Response(200, json={})

    with pytest.raises(httpx.HTTPStatusError):
        run_poll(db, action, handler)
    assert not any(path.endswith("/ack") for path in requests)
    run_poll(db, action, handler)
    assert requests[-1].endswith("/ack")
    assert db.scalars(select(PresenzeSyncJob)).all() == [job]
