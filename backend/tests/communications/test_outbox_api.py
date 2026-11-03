from uuid import UUID, uuid4

import pytest
from ruolo.test_notice_register_api import _headers
from sqlalchemy import func, select

from app.modules.communications import models, policy, registry
from app.modules.communications.schemas import (
    CHECKS,
)
from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.notice_register_models import NoticeDocument

from .conftest import account_input, approved, create, pdf


def test_complete_preview_approval_queue_and_replay(api):
    message = approved(api)
    base = f"/communications/messages/{message['id']}"
    first = api.client.post(f"{base}/dispatch", json={"expected_version": 1})
    second = api.client.post(f"{base}/dispatch", json={"expected_version": 1})
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert api.client.get(base).json()["state"] == "queued"
    assert len(api.client.get(f"{base}/events").json()) >= 5
    assert api.client.get(f"{base}/receipts").json() == []
    assert (
        api.client.get(f"{base}/attachments").json()[0]["sha256"]
        == message["attachments"][0]["sha256"]
    )
    assert api.client.get("/communications/jobs").status_code == 200
    assert "lease_token" not in api.client.get(f"/communications/jobs/{first.json()['id']}").json()
    assert api.client.get("/communications/messages?channel=pec&state=queued").json()["total"] == 1
    assert (
        api.client.get("/communications/ruolo/candidates?channel=pec").json()["items"][0][
            "message_id"
        ]
        == message["id"]
    )
    assert (
        api.client.post(f"{base}/cancel", json={"expected_version": 1}).json()["state"]
        == "cancelled"
    )
    assert (
        api.client.post(f"{base}/dispatch", json={"expected_version": 1}).status_code == 202
    )  # Same cancelled job; never creates work.


@pytest.mark.parametrize("user,status", [(2, 403), (3, 403), (4, 401), (5, 403)])
def test_operator_mutations_require_real_rbac(api, user, status):
    response = api.client.post(
        "/communications/messages",
        headers=_headers(user),
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "recipient@example.org",
            "subject": "Test",
            "body": "Test",
        },
    )
    assert response.status_code == status
    assert (
        api.client.post(
            "/communications/accounts", json=account_input().model_dump(), headers=_headers(2)
        ).status_code
        == 403
    )


def test_all_writes_reject_viewer_and_no_module_reads(api):
    message = create(api)
    base = f"/communications/messages/{message['id']}"
    for action in ("validate", "approve", "dispatch", "cancel"):
        assert (
            api.client.post(
                f"{base}/{action}", json={"expected_version": 1}, headers=_headers(2)
            ).status_code
            == 403
        )
    assert api.client.patch(base, json={}, headers=_headers(2)).status_code == 403
    assert api.client.get(base, headers=_headers(3)).status_code == 403
    assert api.client.get(base, headers=_headers(2)).status_code == 200


def test_checklist_render_scope_and_stale_versions_are_enforced(api):
    value = create(api)
    base = f"/communications/messages/{value['id']}"
    approval = {"expected_version": 1, "confirmed": True, "checklist": dict.fromkeys(CHECKS, True)}
    assert api.client.post(f"{base}/approve", json=approval).status_code == 409
    assert api.client.post(f"{base}/validate", json={"expected_version": 2}).status_code == 409
    assert api.client.post(f"{base}/validate", json={"expected_version": 1}).status_code == 200
    assert api.client.post(f"{base}/validate", json={"expected_version": 1}).status_code == 200
    assert api.client.post(f"{base}/approve", json=approval).status_code == 409
    assert (
        api.client.post(
            f"{base}/approve", json=approval | {"checklist": {"identity": True}}
        ).status_code
        == 422
    )
    part = value["attachments"][0]
    assert (
        api.client.post(
            f"{base}/attachments/{part['id']}/rendered",
            json={
                "expected_version": 1,
                "review_id": str(uuid4()),
                "pages": 3,
                "sha256": part["sha256"],
            },
        ).status_code
        == 409
    )
    assert api.client.post(f"{base}/dispatch", json={"expected_version": 1}).status_code == 409


def test_edits_invalidate_approval_and_free_snapshot(api):
    value = approved(api)
    base = f"/communications/messages/{value['id']}"
    part = value["attachments"][0]
    before = api.client.get(f"{base}/attachments/{part['id']}/preview").content
    response = api.client.patch(
        base,
        json={
            "expected_version": 1,
            "account_id": value["account_id"],
            "recipient": "different@example.org",
            "subject": "Corretto",
            "body": "Nuovo",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2 and response.json()["state"] == "draft"
    assert api.client.get(f"{base}/attachments/{part['id']}/preview").content == before
    assert api.client.post(f"{base}/dispatch", json={"expected_version": 2}).status_code == 409
    with api.session() as db:
        assert db.scalar(select(func.count()).select_from(models.CommunicationAuthorization)) == 1


@pytest.mark.parametrize("change", ["pdf", "payment", "register", "year", "missing", "draft"])
def test_changed_source_is_blocked_before_dispatch(api, change):
    value = approved(api)
    with api.session() as db:
        source = db.get(RuoloTributiReminderBatchItem, api.source_id)
        if change == "pdf":
            from pathlib import Path

            Path(source.generated_document_path).write_bytes(pdf(4))
        elif change == "payment":
            api.summary.update(saldo_amount="0.00", payment_status="paid")
        elif change == "register":
            document = db.scalar(
                select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
            )
            document.version += 1
        elif change == "year":
            source.years_json = [2022]
        elif change == "missing":
            source.generated_document_path = "/does-not-exist.pdf"
        else:
            source.status = "draft"
        db.commit()
    assert (
        api.client.post(
            f"/communications/messages/{value['id']}/dispatch", json={"expected_version": 1}
        ).status_code
        == 409
    )


def test_missing_resources_invalid_headers_and_unknown_fields(api):
    unknown = str(uuid4())
    assert api.client.get(f"/communications/messages/{unknown}").status_code == 404
    assert api.client.get(f"/communications/jobs/{unknown}").status_code == 404
    assert (
        api.client.post(
            f"/communications/messages/{unknown}/validate", json={"expected_version": 1}
        ).status_code
        == 404
    )
    assert (
        api.client.get("/communications/ruolo/candidates?channel=pec&year=2022").status_code == 422
    )
    value = create(api)
    base = f"/communications/messages/{value['id']}"
    assert api.client.get(f"{base}/attachments/{unknown}/preview").status_code == 404
    assert api.client.get(f"{base}/receipts/{unknown}/original").status_code == 404
    assert (
        api.client.patch(
            base,
            json={
                "expected_version": 1,
                "account_id": value["account_id"],
                "recipient": "r@example.org",
                "subject": "bad\nHeader: value",
                "body": "text",
            },
        ).status_code
        == 409
    )


def test_multiaccount_routing_admin_and_no_secret_exposure(api):
    admin = api.client.get("/communications/admin/accounts").json()
    choices = api.client.get("/communications/accounts").json()
    assert "secret_ref" in admin[0] and "secret_ref" not in choices[0]
    assert "smtp_host" not in choices[0]
    assert all("password" not in value for value in admin)
    created = api.client.post(
        "/communications/accounts",
        json=account_input("pec", name="Alternative", is_default=False).model_dump(),
    )
    assert created.status_code == 201
    identity = created.json()["id"]
    payload = account_input("pec", name="Changed", is_default=False).model_dump() | {
        "expected_version": 1
    }
    assert api.client.patch(f"/communications/accounts/{identity}", json=payload).status_code == 200
    assert api.client.patch(f"/communications/accounts/{identity}", json=payload).status_code == 409
    assert api.client.post(f"/communications/accounts/{identity}/test").status_code == 202
    assert api.client.post(f"/communications/accounts/{identity}/reconcile").status_code == 202
    assert api.client.post(
        f"/communications/accounts/{identity}/pause", json={"paused": True}
    ).json()["paused"]
    assert api.client.post("/communications/admin/pause", json={"paused": True}).json()["paused"]
    monitor = api.client.get("/communications/admin/monitor").json()
    assert monitor["paused"] and not monitor["transport_enabled"]
    assert api.client.get("/communications/admin/unmatched-receipts").json() == []
    assert api.client.post(f"/communications/accounts/{uuid4()}/test").status_code == 404
    with api.session() as db:
        routed = registry.route_account(db, "pec", 1)
        assert routed.id == api.account_ids[0]
        routed.default_modules = ["ruolo"]
        assert registry.route_account(db, "pec", 1).id == routed.id
        routed.active = False
        db.flush()
        with pytest.raises(policy.Conflict):
            registry.route_account(db, "pec", 1)
        with pytest.raises(policy.Conflict):
            registry.route_account(db, "pec", 1, routed.id)


def test_templates_are_versions_and_proposals_require_approval(api):
    payload = {
        "code": "ruolo-2021",
        "name": "Proposta",
        "channel": "pec",
        "module": "ruolo",
        "subject": "Avviso {{numero_avviso}}",
        "body": "Gentile {{contribuente_nome}} {{anno_tributario}} {{importo}} {{ente_nome}}",
    }
    first = api.client.post("/communications/templates", json=payload)
    assert first.status_code == 201, first.text
    identity = first.json()["id"]
    assert api.client.get("/communications/templates").json() == []
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "r@example.org",
            "template_id": identity,
        },
    )
    assert response.status_code == 409
    assert api.client.post(f"/communications/templates/{identity}/approve").status_code == 200
    assert api.client.post(f"/communications/templates/{identity}/approve").status_code == 409
    value = create(api, template_id=identity, subject=None, body=None)
    assert value["subject"].startswith("Avviso ")
    assert api.client.post("/communications/templates", json=payload).json()["version"] == 2
    assert len(api.client.get("/communications/admin/templates").json()) == 2
    assert len(api.client.get("/communications/templates").json()) == 1
    assert api.client.post(f"/communications/templates/{uuid4()}/approve").status_code == 404
    for bad in ("{{missing}}", "{{__import__('os')}}", "{% include 'file' %}", "new\nheader"):
        assert (
            api.client.post(
                "/communications/templates", json=payload | {"subject": bad}
            ).status_code
            == 409
        )


def test_duplicate_authorizations_and_account_change_block(api):
    first = approved(api)
    assert (
        api.client.post(
            "/communications/messages",
            json={
                "source_entity_id": str(api.source_id),
                "channel": "email",
                "recipient": "r@example.org",
                "subject": "Test",
                "body": "Test",
            },
        ).status_code
        == 409
    )
    with api.session() as db:
        account = db.get(models.CommunicationAccount, UUID(first["account_id"]))
        account.version += 1
        db.commit()
    assert (
        api.client.post(
            f"/communications/messages/{first['id']}/dispatch", json={"expected_version": 1}
        ).status_code
        == 409
    )


def test_application_registers_communications_without_changing_existing_routes():
    from app.api.router import api_router
    from app.db import base

    paths = {route.path for route in api_router.routes}
    assert "/communications/messages" in paths
    assert "/communications/admin/monitor" in paths
    assert base.CommunicationMessage.__tablename__ == "communication_messages"


def test_worker_grants_refer_only_to_real_tables():
    import re
    from pathlib import Path

    from app.core.database import Base
    from app.db import base

    assert base.CommunicationMessage.__table__ is Base.metadata.tables["communication_messages"]
    sql = (
        Path(__file__).resolve().parents[3] / "deploy/communications/worker-grants.sql"
    ).read_text()
    grants = re.findall(
        r"GRANT (?:SELECT|INSERT, UPDATE|INSERT|UPDATE) ON (.*?) TO communications_worker;",
        sql,
        re.S,
    )
    for group in grants:
        for table in group.split(","):
            assert table.strip() in Base.metadata.tables, table
