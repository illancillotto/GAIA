from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.dotazioni.custody import close_custody
from app.modules.dotazioni.models import DotazioneCustody, DotazioneEvent
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.vehicles import Vehicle


def asset(context, **values):
    client, _, _, unit, _ = context
    response = client.post(
        "/api/dotazioni/assets",
        json={
            "asset_code": "TEL-001",
            "asset_type": "phone",
            "name": "Samsung",
            "assigned_org_unit_id": str(unit.id),
            **values,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_lifecycle_and_audit(context):
    client, db, users, unit, active = context
    item = asset(context)
    identifier = item["id"]
    assert client.get("/api/dotazioni/assets/by-code/tel-001").json()["id"] == identifier
    assert client.get(f"/api/dotazioni/assets/{identifier}/custody").json() is None
    assert client.get("/api/dotazioni/lookups").json()["permissions"] == [
        f"dotazioni.{action}" for action in ("view", "manage", "assign", "custody", "history")
    ]
    active["user"] = users["op"]
    taken = client.post(f"/api/dotazioni/assets/{identifier}/take", json={"notes": "presa"})
    assert taken.status_code == 200
    assert taken.json()["effective_status"] == "in_use"
    assert client.get(f"/api/dotazioni/operators/{users['op'].id}/assets").json()["total"] == 1
    assert client.get(f"/api/dotazioni/org-units/{unit.id}/assets").json()["total"] == 1
    transferred = client.post(
        f"/api/dotazioni/assets/{identifier}/transfer",
        json={"holder_user_id": users["next"].id, "notes": "passaggio"},
    )
    assert transferred.status_code == 200
    rows = client.get(f"/api/dotazioni/assets/{identifier}/custody-history").json()["items"]
    assert rows[0]["taken_at"] == rows[1]["returned_at"]
    assert rows[0]["handover_from_user_id"] == users["op"].id
    assert rows[0]["handover_from_name"] == (users["op"].full_name or users["op"].username)
    assert rows[1]["handover_from_name"] is None
    users["op"].full_name = "Mario Rossi"
    users["op"].is_active = False
    db.commit()
    rows = client.get(f"/api/dotazioni/assets/{identifier}/custody-history").json()["items"]
    assert rows[0]["handover_from_name"] == "Mario Rossi"
    active["user"] = users["next"]
    assert (
        client.post(f"/api/dotazioni/assets/{identifier}/return", json={"notes": "fine"}).json()[
            "effective_status"
        ]
        == "available"
    )
    active["user"] = users["admin"]
    assert (
        client.patch(
            f"/api/dotazioni/assets/{identifier}",
            json={"name": "Telefono", "assigned_org_unit_id": None, "is_active": False},
        ).status_code
        == 200
    )
    events = client.get(f"/api/dotazioni/assets/{identifier}/events").json()
    assert events["total"] == 7
    assert db.scalars(select(DotazioneEvent)).all()
    assert client.get("/api/dotazioni/assets?active=false&search=Telefono").json()["total"] == 1


@pytest.mark.parametrize("operation", ["return", "transfer"])
def test_no_open_custody(context, operation):
    item = asset(context)
    body = {"holder_user_id": context[2]["next"].id} if operation == "transfer" else {}
    assert (
        context[0].post(f"/api/dotazioni/assets/{item['id']}/{operation}", json=body).status_code
        == 409
    )


def test_conflicts_and_permissions(context):
    client, _, users, _, active = context
    item = asset(context)
    path = f"/api/dotazioni/assets/{item['id']}"
    assert (
        client.post(
            "/api/dotazioni/assets",
            json={"asset_code": "TEL-001", "asset_type": "phone", "name": "Duplicate"},
        ).status_code
        == 409
    )
    active["user"] = users["viewer"]
    assert client.post(path + "/take", json={}).status_code == 403
    assert (
        client.post(
            "/api/dotazioni/assets", json={"asset_code": "X", "asset_type": "tool", "name": "X"}
        ).status_code
        == 403
    )
    active["user"] = users["outsider"]
    assert client.post(path + "/take", json={}).status_code == 403
    active["user"] = users["op"]
    assert client.post(path + "/take", json={"holder_user_id": users["next"].id}).status_code == 403
    assert client.post(path + "/take", json={}).status_code == 200
    assert client.post(path + "/take", json={}).status_code == 409
    assert (
        client.post(path + "/transfer", json={"holder_user_id": users["op"].id}).status_code == 409
    )
    assert (
        client.post(path + "/transfer", json={"holder_user_id": users["outsider"].id}).status_code
        == 403
    )
    active["user"] = users["outsider"]
    assert client.post(path + "/return", json={}).status_code == 403
    active["user"] = users["admin"]
    assert client.patch(path, json={"is_active": False}).status_code == 409
    assert client.patch(path, json={"status": "retired"}).status_code == 409
    assert client.patch(path, json={"status": "damaged"}).status_code == 200
    assert client.get(path).json()["effective_status"] == "damaged"
    assert client.post(path + "/return", json={}).json()["status"] == "damaged"
    assert client.post(path + "/take", json={}).status_code == 409


def test_links_and_validation(context):
    client, db, users, _, _ = context
    network = NetworkDevice(ip_address="10.0.0.1", assigned_user_id=users["op"].id)
    vehicle = Vehicle(code="V-1", name="Mezzo", vehicle_type="truck", plate_number="AA123BB")
    db.add_all([network, vehicle])
    db.commit()
    item = asset(context, network_device_id=network.id)
    assert item["current_custody"] is None
    assert client.get("/api/dotazioni/lookups").json()["network_devices"][0]["name"] == "10.0.0.1"
    path = f"/api/dotazioni/assets/{item['id']}"
    assert client.patch(path, json={"vehicle_id": str(vehicle.id)}).status_code == 422
    assert (
        client.patch(path, json={"asset_type": "vehicle", "vehicle_id": str(vehicle.id)}).json()[
            "plate_number"
        ]
        == "AA123BB"
    )
    assert client.post(path + "/take", json={}).status_code == 409
    vehicle.is_active = False
    db.commit()
    assert client.patch(path, json={"vehicle_id": str(vehicle.id)}).status_code == 422
    for values in (
        {"assigned_org_unit_id": str(uuid4())},
        {"network_device_id": 9999},
        {"vehicle_id": None},
        {"name": None},
        {"asset_code": "CHANGED"},
    ):
        assert client.patch(path, json=values).status_code == 422


def test_missing_inactive_and_history(context):
    client, db, users, _, active = context
    missing = str(uuid4())
    for suffix in ("", "/custody-history", "/events"):
        assert client.get(f"/api/dotazioni/assets/{missing}{suffix}").status_code == 404
    assert client.get("/api/dotazioni/assets/by-code/MISSING").status_code == 404
    assert client.get("/api/dotazioni/operators/9999/assets").status_code == 404
    assert client.get(f"/api/dotazioni/org-units/{missing}/assets").status_code == 404
    item = asset(context)
    path = f"/api/dotazioni/assets/{item['id']}"
    assert client.post(path + "/take", json={"holder_user_id": 9999}).status_code == 422
    users["next"].is_active = False
    db.commit()
    assert client.post(path + "/take", json={"holder_user_id": users["next"].id}).status_code == 422
    active["user"] = users["viewer"]
    users["viewer"].module_dotazioni = False
    db.commit()
    assert client.get("/api/dotazioni/assets").status_code == 403
    active["user"] = users["admin"]
    assert client.patch(path, json={"name": "Samsung"}).status_code == 200
    assert client.patch(path, json={"is_active": False}).status_code == 200
    assert client.post(path + "/take", json={}).status_code == 409


def test_filters_and_database_constraint(context):
    client, db, users, unit, _ = context
    item = asset(context)
    path = f"/api/dotazioni/assets/{item['id']}"
    assert (
        client.get(
            f"/api/dotazioni/assets?asset_type=phone&status=available&org_unit_id={unit.id}&active=true"
        ).json()["total"]
        == 1
    )
    assert client.post(path + "/take", json={"holder_user_id": users["op"].id}).status_code == 200
    assert client.get("/api/dotazioni/assets?status=available").json()["total"] == 0
    assert client.get("/api/dotazioni/assets?status=in_use").json()["total"] == 1
    current = db.scalar(select(DotazioneCustody))
    with pytest.raises(HTTPException):
        close_custody(current, users["admin"], datetime.now(UTC) - timedelta(days=1), None)
    db.add(
        DotazioneCustody(
            asset_id=current.asset_id,
            holder_user_id=users["next"].id,
            taken_at=datetime.now(UTC),
            recorded_by_user_id=users["admin"].id,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    assert client.patch(path, json={"status": "maintenance"}).status_code == 200
    assert client.get("/api/dotazioni/assets?status=maintenance").json()["total"] == 1
