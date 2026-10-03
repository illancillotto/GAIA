from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.section_permission import Section, UserSectionPermission
from app.modules.dotazioni import custody
from app.modules.dotazioni.models import DotazioneCustody, DotazioneEvent
from app.modules.organigramma.models import OrgAssignment

from .test_api import asset


def deny(context, user, action):
    db = context[1]
    section = db.scalar(select(Section).where(Section.key == f"dotazioni.{action}"))
    db.add(UserSectionPermission(user_id=user.id, section_id=section.id, is_granted=False))
    db.commit()


@pytest.mark.parametrize(
    "action,path", [("view", ""), ("history", "/custody-history"), ("history", "/events")]
)
def test_user_override_denies_read(context, action, path):
    client, _, users, _, active = context
    item = asset(context)
    active["user"] = users["op"]
    deny(context, users["op"], action)
    assert client.get(f"/api/dotazioni/assets/{item['id']}{path}").status_code == 403


def test_reassignment_requires_distinct_permission(context):
    client, db, users, _, active = context
    item = asset(context)
    users["admin"].role = "admin"
    db.commit()
    deny(context, users["admin"], "assign")
    assert (
        client.patch(
            f"/api/dotazioni/assets/{item['id']}", json={"assigned_org_unit_id": None}
        ).status_code
        == 403
    )
    assert (
        client.patch(f"/api/dotazioni/assets/{item['id']}", json={"name": "Radio"}).status_code
        == 200
    )
    assert (
        client.get(f"/api/dotazioni/assets/{item['id']}").json()["assigned_org_unit_id"]
        == item["assigned_org_unit_id"]
    )
    active["user"] = users["op"]
    assert client.post(f"/api/dotazioni/assets/{item['id']}/take", json={}).status_code == 200


@pytest.mark.parametrize(
    "values",
    [
        {"active": False},
        {"valid_from": datetime.now(UTC) + timedelta(days=1)},
        {"valid_to": datetime.now(UTC) - timedelta(days=1)},
    ],
)
def test_expired_future_or_disabled_membership_cannot_take(context, values):
    client, db, users, _, active = context
    item = asset(context)
    assignment = db.scalar(select(OrgAssignment).where(OrgAssignment.user_id == users["op"].id))
    for field, value in values.items():
        setattr(assignment, field, value)
    db.commit()
    active["user"] = users["op"]
    assert client.post(f"/api/dotazioni/assets/{item['id']}/take", json={}).status_code == 403
    assert db.scalar(select(func.count()).select_from(DotazioneCustody)) == 0


def test_server_failure_rolls_back_transfer_and_audit(context, monkeypatch):
    client, db, users, _, _ = context
    item = asset(context)
    path = f"/api/dotazioni/assets/{item['id']}"
    assert client.post(path + "/take", json={"holder_user_id": users["op"].id}).status_code == 200
    previous = client.get(path + "/custody").json()

    def fail_event(*args):
        raise RuntimeError("audit persistence unavailable")

    monkeypatch.setattr(custody, "record_event", fail_event)
    with TestClient(client.app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post(
            path + "/transfer", json={"holder_user_id": users["next"].id}
        )
    assert response.status_code == 500
    db.expire_all()
    assert client.get(path + "/custody").json() == previous
    assert db.scalar(select(func.count()).select_from(DotazioneCustody)) == 1
    assert db.scalar(select(func.count()).select_from(DotazioneEvent)) == 2


def test_persistence_closed_holder_and_history_pagination(context):
    client, db, users, _, _ = context
    item = asset(context)
    path = f"/api/dotazioni/assets/{item['id']}"
    assert client.post(path + "/take", json={"holder_user_id": users["op"].id}).status_code == 200
    users["op"].is_active = False
    db.commit()
    assert client.post(path + "/return", json={}).status_code == 200
    assert client.post(path + "/take", json={"holder_user_id": users["next"].id}).status_code == 200
    first = client.get(path + "/custody-history?page=1&page_size=1").json()
    second = client.get(path + "/custody-history?page=2&page_size=1").json()
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["holder_user_id"] == users["next"].id
    assert second["items"][0]["returned_by_user_id"] == users["admin"].id
    db.expire_all()
    assert client.get(path + "/custody").json()["holder_user_id"] == users["next"].id


@pytest.mark.parametrize(
    "body",
    [
        {"asset_code": "bad code"},
        {"asset_code": 7},
        {"asset_type": False},
        {"asset_type": "bad type"},
        {"name": " "},
        {"status": "in_use"},
        {"network_device_id": -1},
        {"unknown": "value"},
    ],
)
def test_create_rejects_invalid_input_without_writes(context, body):
    client, db, _, _, _ = context
    response = client.post(
        "/api/dotazioni/assets",
        json={"asset_code": "RAD-001", "asset_type": "radio", "name": "Radio", **body},
    )
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(DotazioneEvent)) == 0


def test_code_normalization_and_inactive_unit(context):
    client, db, _, unit, _ = context
    item = asset(context, asset_code=" tel-001 ", asset_type=" PHONE ")
    assert item["asset_code"] == "TEL-001"
    assert item["asset_type"] == "phone"
    assert client.get("/api/dotazioni/assets/by-code/tel-001").json()["id"] == item["id"]
    unit.is_active = False
    db.commit()
    assert (
        client.patch(
            f"/api/dotazioni/assets/{item['id']}", json={"assigned_org_unit_id": str(unit.id)}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/dotazioni/assets/{item['id']}", json={"assigned_org_unit_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert UUID(item["id"])
