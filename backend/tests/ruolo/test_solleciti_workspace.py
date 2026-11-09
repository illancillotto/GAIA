"""Operator workspace: canonical notices, account ownership and persistent preparation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services import poste_dispatch, poste_preparation

from .poste_dispatch_fixtures import PDF, payload, seed_account, seed_batch_item
from .test_notice_register_api import _headers
from .test_poste_dispatch_api import api as api

URL = "/ruolo/tributi/solleciti/workspace"


def test_workspace_collapses_batch_copies_and_filters_globally(api, tmp_path):
    with api.session() as db:
        first = db.get(RuoloTributiReminderBatchItem, UUID(api.ids[0]))
        first.created_at = datetime.now(UTC) - timedelta(days=1)
        latest = db.get(RuoloTributiReminderBatchItem, UUID(api.ids[1]))
        latest.display_name = "Copia corrente"
        latest.created_at = datetime.now(UTC)
        seed_batch_item(db, tmp_path, years_json=[2022], payload_json=payload("OTHER"))
        db.commit()
    body = api.client.get(URL).json()
    assert body["total"] == 2
    row = next(r for r in body["items"] if r["notice_number"] == "020217801062586")
    assert row["item_id"] == api.ids[1] and row["can_prepare"]
    assert api.client.get(URL, params={"year": 2021, "page_size": 1}).json()["total"] == 1
    assert api.client.get(URL, params={"page": 3, "page_size": 1}).json()["items"] == []
    assert (
        api.client.get(
            URL, params={"q": " copia ", "account": "none", "stage": "available"}
        ).json()["total"]
        == 1
    )
    assert api.client.get(URL, params={"q": "non trovato"}).json()["groups"] == []
    for params in (
        {"page": 0},
        {"page_size": 101},
        {"account": "bad"},
        {"stage": "cancelled"},
        {"q": "x" * 121},
    ):
        assert api.client.get(URL, params=params).status_code == 422


def test_history_ownership_sent_review_and_cross_account_conflict(api, tmp_path):
    prepared = api.client.post(URL + "/prepare", json={"item_ids": api.ids[:1], "credential_id": 1})
    assert prepared.status_code == 200, prepared.text
    lot = prepared.json()
    with api.session() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, lot["active_job"]["id"])
        assert job.payload_json["prepare_drafts_after_addresses"] is True
        attempt = db.get(PosteDispatchItem, UUID(lot["items"][0]["id"]))
        attempt.status = "sent"
        attempt.poste_draft_id, attempt.tracking_number, attempt.sent_at = (
            "POSTE",
            "TRACK",
            datetime.now(UTC),
        )
        seed_batch_item(
            db, tmp_path, payload_json=None, display_name=None, years_json=None, status="failed"
        )
        db.commit()
    row = api.client.get(URL, params={"account": "1", "stage": "sent"}).json()["items"][0]
    assert row["lot_id"] == lot["id"] and not row["can_prepare"]
    assert row["poste_dispatches"][0]["tracking_number"] == "TRACK"
    assert api.client.get(URL, params={"account": "none", "stage": "review"}).json()["total"] == 1
    assert (
        api.client.post(
            URL + "/prepare", json={"item_ids": api.ids[1:], "credential_id": 1}
        ).status_code
        == 409
    )
    with api.session() as db:
        attempt = db.get(PosteDispatchItem, UUID(lot["items"][0]["id"]))
        attempt.active_key = attempt.active_source_key = None
        seed_account(db, 2, "other-account")
        poste_dispatch.create_lot(
            db,
            title="Historical inconsistency",
            batch_item_ids=[UUID(api.ids[1])],
            credential_id=2,
            actor_id=1,
        )
        db.commit()
    row = api.client.get(URL, params={"stage": "conflict"}).json()["items"][0]
    assert row["account_key"] == "conflict" and row["lot_id"] is None
    assert len(row["poste_dispatches"]) == 2 and not row["can_prepare"]
    with api.session() as db:
        for attempt in db.scalars(select(PosteDispatchItem)):
            attempt.status = "cancelled"
            attempt.active_key = attempt.active_source_key = None
        db.commit()
    assert api.client.get(URL, params={"stage": "available"}).json()["total"] == 1


@pytest.mark.parametrize(
    "status,stage",
    [("draft_priced", "draft"), ("draft_uncertain", "review"), ("address_ok", "processing")],
)
def test_non_final_states_and_legacy_account_remain_visible(api, status, stage):
    lot = api.client.post(
        URL + "/prepare", json={"item_ids": api.ids[:1], "credential_id": 1}
    ).json()
    with api.session() as db:
        attempt = db.get(PosteDispatchItem, UUID(lot["items"][0]["id"]))
        attempt.status = status
        owner = db.get(PosteDispatchLot, UUID(lot["id"]))
        owner.credential_id, owner.poste_username = None, None
        db.commit()
    row = api.client.get(URL, params={"account": "legacy", "stage": stage}).json()["items"][0]
    assert row["account_label"] == "Account storico da associare" and not row["can_prepare"]


def test_preparation_survives_browser_close_and_queues_drafts_once(api):
    lot = api.client.post(
        URL + "/prepare", json={"item_ids": api.ids[:1], "credential_id": 1}
    ).json()
    job_id = lot["active_job"]["id"]
    with api.session() as db:
        item = db.get(PosteDispatchItem, UUID(lot["items"][0]["id"]))
        item.status = "address_ok"
        poste_preparation.finish_job(db, job_id, "succeeded", {"counters": {"found": 1}})
        db.commit()
    with api.session() as db:
        next_job = poste_dispatch.active_job(db, UUID(lot["id"]))
        assert next_job.mode == "poste_dispatch_drafts" and next_job.requested_by_user_id == 1
        poste_preparation.finish_job(db, job_id, "succeeded", {})
        db.commit()
        assert len(list(db.scalars(select(PostaOnlineRegisteredMailSyncJob)))) == 2


@pytest.mark.parametrize(
    "case", ["address_review", "failed", "disabled_account", "incomplete_recipient"]
)
def test_preparation_stops_safely_for_review_failures_and_disabled_accounts(api, case):
    if case == "incomplete_recipient":
        with api.session() as db:
            item = db.get(RuoloTributiReminderBatchItem, UUID(api.ids[0]))
            item.payload_json = {"notice_number": "020210000000001"}
            db.commit()
    response = api.client.post(URL + "/prepare", json={"item_ids": api.ids[:1], "credential_id": 1})
    assert response.status_code == 200, response.text
    lot = response.json()
    if case == "incomplete_recipient":
        assert lot["active_job"] is None and lot["counts"] == {"address_review": 1}
        return
    with api.session() as db:
        item = db.get(PosteDispatchItem, UUID(lot["items"][0]["id"]))
        item.status = "address_review" if case == "address_review" else "address_ok"
        if case == "disabled_account":
            from app.models.posta_online import PostaOnlineCredential

            db.get(PostaOnlineCredential, 1).active = False
        poste_preparation.finish_job(
            db,
            lot["active_job"]["id"],
            "failed" if case == "failed" else "succeeded",
            {"error": "synthetic"} if case == "failed" else {},
        )
        db.commit()
        job = db.get(PostaOnlineRegisteredMailSyncJob, lot["active_job"]["id"])
        assert len(list(db.scalars(select(PostaOnlineRegisteredMailSyncJob)))) == 1
        if case == "disabled_account":
            assert "next_step_error" in job.result_json


def test_workspace_permissions_and_invalid_commands(api):
    api.client.headers.clear()
    assert api.client.get(URL).status_code == 401
    for user, status in ((3, 403), (4, 401), (5, 403)):
        assert api.client.get(URL, headers=_headers(user)).status_code == status
    assert api.client.get(URL, headers=_headers(2)).status_code == 200
    for action, body in [
        ("prepare", {"item_ids": api.ids[:1], "credential_id": 1}),
        ("generate", {"year": 2021, "tax_code": "12345678901"}),
        ("reconcile", {"credential_id": 1, "year": 2021}),
    ]:
        assert (
            api.client.post(URL + "/" + action, headers=_headers(2), json=body).status_code == 403
        )
    for body in (
        {"item_ids": [], "credential_id": 1},
        {"item_ids": api.ids[:1], "credential_id": 0},
    ):
        assert api.client.post(URL + "/prepare", headers=_headers(), json=body).status_code == 422


def test_account_refresh_queues_each_matching_lot_once_and_preserves_external_state(api, tmp_path):
    with api.session() as db:
        seed_account(db, 2, "other-account")
        lots = []
        for index, (year, account, status) in enumerate(
            [
                (2021, 1, "draft_created"),
                (2022, 1, "draft_uncertain"),
                (2021, 2, "draft_priced"),
                (2021, 1, "sent"),
            ]
        ):
            item = seed_batch_item(
                db, tmp_path, years_json=[year], payload_json=payload(f"0202100000000{index:02}")
            )
            lot = poste_dispatch.create_lot(
                db,
                title=f"Lotto {index}",
                batch_item_ids=[item.id],
                credential_id=account,
                actor_id=1,
                read=lambda _item: PDF,
            )
            job = poste_dispatch.active_job(db, lot.id)
            job.status = "succeeded"
            attempt = db.scalar(select(PosteDispatchItem).where(PosteDispatchItem.lot_id == lot.id))
            attempt.status = status
            lots.append(lot.id)
        db.commit()
    response = api.client.post(URL + "/reconcile", json={"credential_id": 1, "year": 2021})
    assert response.status_code == 200, response.text
    assert len(response.json()["queued_jobs"]) == 1 and response.json()["busy_lots"] == 0
    repeated = api.client.post(URL + "/reconcile", json={"credential_id": 1, "year": 2021})
    assert repeated.json() == {"queued_jobs": [], "busy_lots": 1}
    all_years = api.client.post(URL + "/reconcile", json={"credential_id": 1, "year": None})
    assert len(all_years.json()["queued_jobs"]) == 1 and all_years.json()["busy_lots"] == 1
    with api.session() as db:
        queued = list(
            db.scalars(
                select(PostaOnlineRegisteredMailSyncJob).where(
                    PostaOnlineRegisteredMailSyncJob.status == "pending"
                )
            )
        )
        assert {UUID(job.payload_json["lot_id"]) for job in queued} == set(lots[:2])
        assert all(
            job.mode == "poste_dispatch_reconcile" and job.requested_by_user_id == 1
            for job in queued
        )
        assert [
            db.scalar(select(PosteDispatchItem.status).where(PosteDispatchItem.lot_id == lot))
            for lot in lots
        ] == ["draft_created", "draft_uncertain", "draft_priced", "sent"]


def test_refresh_empty_disabled_or_invalid_account_never_creates_a_job(api):
    assert api.client.post(URL + "/reconcile", json={"credential_id": 1}).json() == {
        "queued_jobs": [],
        "busy_lots": 0,
    }
    assert api.client.post(URL + "/reconcile", json={"credential_id": 999}).status_code == 409
    from app.models.posta_online import PostaOnlineCredential

    with api.session() as db:
        db.get(PostaOnlineCredential, 1).active = False
        db.commit()
    assert api.client.post(URL + "/reconcile", json={"credential_id": 1}).status_code == 409
    for fields in (
        {"credential_id": 0},
        {"credential_id": 1, "year": 2020},
        {"credential_id": 1, "year": 2099},
    ):
        assert api.client.post(URL + "/reconcile", json=fields).status_code == 422
    with api.session() as db:
        assert list(db.scalars(select(PostaOnlineRegisteredMailSyncJob))) == []
