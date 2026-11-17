"""Archival removes obsolete documents from preparation while retaining history."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiReminderBatchItem as Item
from app.modules.ruolo.services import poste_dispatch, solleciti_workspace
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

from .poste_dispatch_fixtures import PDF, payload, seed_batch_item, seed_user
from .test_poste_dispatch_api import api as api
from .test_poste_dispatch_duplicates_postgres import postgres as postgres

URL = "/ruolo/tributi/solleciti/workspace"


def test_archived_latest_copy_does_not_resurrect_an_older_generated_pdf(api, tmp_path):
    with api.session() as db:
        older, latest = [db.get(Item, UUID(value)) for value in api.ids]
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        latest.created_at = datetime.now(UTC)
        latest.status = "archived"
        path = latest.generated_document_path
        original_payload = latest.payload_json
        unrelated = seed_batch_item(db, tmp_path, payload_json=payload("UNRELATED"))
        unrelated_id = str(unrelated.id)
        db.commit()

    result = api.client.get(URL).json()
    assert result["total"] == 1
    assert [row["item_id"] for row in result["items"]] == [unrelated_id]
    assert sum(group["total"] for group in result["groups"]) == 1
    assert api.client.get(URL, params={"q": "020217801062586"}).json()["total"] == 0
    with api.session() as db:
        archived = db.get(Item, UUID(api.ids[1]))
        assert archived.status == "archived"
        assert archived.payload_json == original_payload
        assert archived.generated_document_path == path
        assert Path(path).read_bytes() == PDF
        assert db.get(Item, UUID(api.ids[0])).status == "generated"


def test_new_current_copy_can_follow_an_archived_document(api):
    with api.session() as db:
        older, latest = [db.get(Item, UUID(value)) for value in api.ids]
        older.created_at = datetime.now(UTC) - timedelta(days=1)
        older.status = "archived"
        latest.created_at = datetime.now(UTC)
        db.commit()
    result = api.client.get(URL).json()
    assert result["total"] == 1
    assert result["items"][0]["item_id"] == api.ids[1]
    assert result["items"][0]["can_prepare"] is True


def test_archiving_one_heir_delivery_preserves_the_other_recipient(api):
    with api.session() as db:
        archived, current = [db.get(Item, UUID(value)) for value in api.ids]
        archived.payload_json = payload(heir_delivery={"reference": "HEIR-A"})
        archived.status = "archived"
        current.payload_json = payload(heir_delivery={"reference": "HEIR-B"})
        db.commit()
    result = api.client.get(URL).json()
    assert result["total"] == 1
    assert result["items"][0]["item_id"] == api.ids[1]


def test_archived_pdf_is_rejected_by_workspace_and_legacy_preparation(api):
    with api.session() as db:
        for value in api.ids:
            db.get(Item, UUID(value)).status = "archived"
        db.commit()
    result = api.client.get(URL).json()
    assert result["total"] == 0 and result["items"] == [] and result["groups"] == []
    rejected = api.client.post(URL + "/prepare", json={"item_ids": api.ids[:1], "credential_id": 1})
    assert rejected.status_code == 409
    with api.session() as db:
        rows, count = poste_dispatch.list_candidates(db, q=None, page=1, page_size=20)
        assert rows == [] and count == 0
        with pytest.raises(DispatchConflict, match="non generato"):
            poste_dispatch.create_lot(
                db,
                title="Archived PDF must not be prepared",
                batch_item_ids=[UUID(api.ids[0])],
                credential_id=1,
                actor_id=1,
                read=lambda _: PDF,
            )


def test_archived_record_without_notice_number_stays_out_of_workspace(api, tmp_path):
    with api.session() as db:
        archived = seed_batch_item(db, tmp_path, status="archived", payload_json=None)
        db.commit()
        assert archived.id not in {item.id for item in solleciti_workspace._items(db)}


@pytest.mark.postgres
@pytest.mark.parametrize("archive_latest", [True, False])
def test_postgres_archive_filter_applies_after_canonical_ranking(
    postgres, tmp_path, archive_latest
):
    with Session(postgres) as db:
        seed_user(db)
        older = seed_batch_item(db, tmp_path, created_at=datetime.now(UTC) - timedelta(days=1))
        latest = seed_batch_item(db, tmp_path, created_at=datetime.now(UTC))
        (latest if archive_latest else older).status = "archived"
        db.commit()
        visible = solleciti_workspace._items(db)
        assert [item.id for item in visible] == ([] if archive_latest else [latest.id])
        assert db.get(Item, older.id) is not None and db.get(Item, latest.id) is not None
