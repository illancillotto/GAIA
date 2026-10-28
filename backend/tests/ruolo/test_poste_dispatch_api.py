from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.router import router

from .poste_dispatch_fixtures import PDF, dispatch_engine, seed_batch_item
from .test_notice_register_api import _headers, _seed_auth

URL = "/ruolo/tributi/poste-dispatch"


@pytest.fixture
def api(tmp_path):
    engine = dispatch_engine(poolclass=StaticPool, connect_args={"check_same_thread": False})
    app = FastAPI()
    app.include_router(router, prefix="/ruolo")
    with engine.connect() as connection:
        transaction = connection.begin()
        _seed_auth(connection)

        def session():
            return Session(connection, join_transaction_mode="create_savepoint", autoflush=False)

        def database():
            with session() as db:
                yield db

        app.dependency_overrides[get_db] = database
        with session() as db:
            items = [seed_batch_item(db, tmp_path) for _ in range(2)]
            ids = [str(item.id) for item in items]
            db.commit()
        with TestClient(app) as client:
            client.headers.update(_headers())
            yield SimpleNamespace(client=client, ids=ids, session=session)
        transaction.rollback()
    engine.dispose()


def _create(api, ids=None):
    response = api.client.post(
        f"{URL}/lots", json={"title": "Lotto", "batch_item_ids": ids or api.ids[:1]}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_operator_builds_a_lot_from_generated_reminders(api):
    candidates = api.client.get(f"{URL}/candidates", params={"q": "rossi"}).json()
    assert candidates["total"] == 2 and candidates["items"][0]["notice_number"] == "020217801062586"
    lot = _create(api)
    assert (
        lot["counts"] == {"address_pending": 1}
        and lot["active_job"]["mode"] == "poste_dispatch_addresses"
    )
    assert lot["items"][0]["shipment_name"] == "GAIA 020217801062586"
    assert api.client.get(f"{URL}/candidates").json()["total"] == 1
    listed = api.client.get(f"{URL}/lots").json()
    assert listed["total"] == 1 and listed["items"][0]["id"] == lot["id"]
    assert api.client.get(f"{URL}/lots/{lot['id']}").json()["title"] == "Lotto"


def test_lot_conflicts_and_unknown_resources_are_reported(api):
    _create(api)
    duplicate = api.client.post(f"{URL}/lots", json={"title": "Bis", "batch_item_ids": api.ids[:1]})
    assert duplicate.status_code == 409
    missing = api.client.post(f"{URL}/lots", json={"title": "X", "batch_item_ids": [str(uuid4())]})
    assert missing.status_code == 404
    assert api.client.get(f"{URL}/lots/{uuid4()}").status_code == 404
    assert api.client.get(f"{URL}/lots/{uuid4()}/items/{uuid4()}/document").status_code == 404


def test_item_commands_and_document(api):
    lot = _create(api)
    item = lot["items"][0]
    base = f"{URL}/lots/{lot['id']}/items/{item['id']}"
    document = api.client.get(f"{base}/document")
    assert document.content == PDF and document.headers["cache-control"] == "no-store, private"
    fields = item["recipient"] | {"address": "via roma 1"}
    updated = api.client.put(f"{base}/recipient", json=fields)
    assert updated.status_code == 200 and updated.json()["recipient"]["address"] == "VIA ROMA 1"
    assert api.client.post(f"{base}/manual-address").status_code == 409
    assert api.client.post(f"{base}/cancel").json()["status"] == "cancelled"


def test_jobs_are_queued_one_at_a_time(api):
    lot = _create(api)
    busy = api.client.post(f"{URL}/lots/{lot['id']}/jobs", json={"kind": "reconcile"})
    assert busy.status_code == 409 and "in corso" in busy.json()["detail"]
    assert api.client.post(f"{URL}/lots/{lot['id']}/jobs", json={"kind": "send"}).status_code == 422
    with api.session() as db:
        db.execute(update(PostaOnlineRegisteredMailSyncJob).values(status="succeeded"))
        db.commit()
    queued = api.client.post(f"{URL}/lots/{lot['id']}/jobs", json={"kind": "reconcile"})
    assert queued.status_code == 200 and queued.json()["mode"] == "poste_dispatch_reconcile"


@pytest.mark.parametrize("user,status", [(2, 403), (5, 403)])
def test_commands_need_the_manage_permission(api, user, status):
    response = api.client.post(
        f"{URL}/lots", json={"title": "x", "batch_item_ids": api.ids[:1]}, headers=_headers(user)
    )
    assert response.status_code == status


def test_viewers_can_read_lots(api):
    assert api.client.get(f"{URL}/lots", headers=_headers(2)).status_code == 200
