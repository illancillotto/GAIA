import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas.models import (
    CapacitasInCassMailingContactRow,
    CapacitasInCassMailingReceiptParent,
    CapacitasInCassMailingShipmentRow,
    CapacitasInCassMailingSubjectRow,
    CapacitasInCassNoticePdf,
    CapacitasInCassNoticeRow,
    CapacitasInCassPartitarioDetail,
    CapacitasInCassSearchResult,
    CapacitasInCassSyncJobCreateRequest,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson
from app.services import elaborazioni_capacitas_incass as incass


def test_job_payload_subject_counts_and_non_dictionary_results() -> None:
    assert incass._incass_payload_subject_count(None) is None
    assert incass._incass_payload_subject_count({}) is None
    assert incass._incass_payload_subject_count({"subject_ids": "not-list"}) is None
    assert incass._incass_payload_subject_count({"subject_ids": []}) == 0
    assert incass._incass_payload_subject_count({"subject_ids": ["one", "two"]}) == 2
    assert incass._slim_incass_result_json(None) is None
    assert incass._slim_incass_result_json([]) == []
    assert incass._slim_incass_result_json({"items": None}) == {"items": None}
    assert incass._slim_incass_result_json({"items": [1]}) == {"items": [1], "total_items": 1}


def test_job_list_result_is_slim_without_mutating_persistent_items() -> None:
    now = datetime.now(UTC)
    items = [{"subject_id": str(index)} for index in range(20)]
    job = CapacitasInCassSyncJob(
        id=1,
        status="pending",
        mode="subjects_sync",
        payload_json={"subject_ids": ["one", "two"]},
        result_json={"items": items, "processed": 20},
        created_at=now,
        updated_at=now,
    )
    result = incass.serialize_incass_sync_job_list_item(job)
    assert result.subject_count == 2
    assert result.result_json["items"] == items[:15]
    assert result.result_json["total_items"] == 20
    assert result.result_json["items_truncated"] is True
    assert job.result_json["items"] == items


def test_list_job_status_filter_and_limit_are_bounded() -> None:
    statements = []

    def scalars(statement):
        statements.append(statement.compile(dialect=postgresql.dialect()))
        return SimpleNamespace(all=lambda: [])

    db = SimpleNamespace(scalars=scalars)
    assert incass.list_incass_sync_jobs(db, limit=0, statuses={"pending"}) == []
    assert incass.list_incass_sync_jobs(db, limit=5000) == []
    assert list(statements[0].params.values()) == [["pending"], 1]
    assert list(statements[1].params.values()) == [1000]


def test_optional_harvest_and_subject_limits() -> None:
    db = Mock()
    db.scalars.return_value.all.return_value = []
    db.execute.return_value.all.return_value = []
    assert (
        incass.load_incass_ruolo_subject_ids(
            db, anno=None, limit_subjects=None, exclude_synced_subjects=False
        )
        == []
    )
    assert incass._resolve_subjects(db, CapacitasInCassSyncJobCreateRequest()) == []
    statement = db.execute.call_args.args[0]
    assert statement.compile().params == {}


def test_recovery_without_result_dictionary_and_stale_terminal_jobs() -> None:
    db = Mock()
    job = SimpleNamespace(id=1, status="processing", result_json=None, error_detail=None)
    db.scalars.return_value.all.return_value = [job]
    assert incass.prepare_incass_sync_jobs_for_recovery(db) == [1]
    assert job.status == "queued_resume"
    terminal = SimpleNamespace(status="succeeded")
    db.scalars.return_value.all.return_value = [terminal]
    incass.expire_stale_incass_sync_jobs(db)
    assert terminal.status == "succeeded"
    db.reset_mock()
    db.scalars.return_value.all.return_value = []
    incass.expire_stale_incass_sync_jobs(db)
    db.commit.assert_not_called()


def test_subject_error_can_continue_to_next_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    subject = SimpleNamespace(id=uuid.uuid4())
    job = CapacitasInCassSyncJob(
        mode="subjects_sync",
        requested_by_user_id=1,
        payload_json=CapacitasInCassSyncJobCreateRequest(continue_on_error=True).model_dump(
            mode="json"
        ),
    )
    monkeypatch.setattr(incass, "_resolve_subjects", lambda *args: [(subject, "CF", "Name")])
    monkeypatch.setattr(
        incass, "_sync_incass_subject", AsyncMock(side_effect=ValueError("source error"))
    )
    db = Mock()
    result = asyncio.run(
        incass.run_incass_sync_job(db, SimpleNamespace(warmup_search_page=AsyncMock()), job)
    )
    assert result.status == "completed_with_errors"
    assert result.result_json["failed_subjects"] == 1
    db.rollback.assert_called_once()


@pytest.mark.parametrize("partitario", [None, CapacitasInCassPartitarioDetail(avviso="X")])
def test_partitario_can_be_missing_or_empty_without_sync_status(
    monkeypatch: pytest.MonkeyPatch, partitario: object
) -> None:
    client = SimpleNamespace(
        search_notices=AsyncMock(
            return_value=CapacitasInCassSearchResult(
                total=1, rows=[CapacitasInCassNoticeRow(avviso="X")]
            )
        ),
        fetch_notice_partitario=AsyncMock(return_value=partitario),
    )
    monkeypatch.setattr(incass, "_find_payment_notice_for_upsert", lambda *args, **kwargs: None)
    upsert = Mock(return_value=None)
    monkeypatch.setattr(incass, "_upsert_payment_notice", upsert)
    result = asyncio.run(
        incass._sync_incass_subject(
            client=client,
            db=Mock(),
            subject_id=uuid.uuid4(),
            identifier="CF",
            display_name="Name",
            include_details=False,
            include_partitario=True,
            include_details_for_new_notices=False,
            include_partitario_for_new_notices=False,
            include_mailing_list=False,
            download_mailing_receipts=False,
            throttle_ms=0,
        )
    )
    assert result.notices_synced == 1
    assert upsert.call_args.kwargs["detail_info_text"] is None


def test_unstored_notice_pdf_is_not_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(incass, "_find_notice_pdf_document", lambda *args, **kwargs: None)
    monkeypatch.setattr(incass, "_store_notice_pdf_document", lambda *args, **kwargs: None)
    result, count = asyncio.run(
        incass._download_notice_pdfs(
            client=SimpleNamespace(download_notice_pdf=AsyncMock(return_value=b"PDF")),
            db=Mock(),
            subject_id=uuid.uuid4(),
            row=CapacitasInCassNoticeRow(avviso="X"),
            pdf_links=[CapacitasInCassNoticePdf(url="https://example.org/a.pdf")],
            referer="https://example.org/notice",
        )
    )
    assert len(result) == 1
    assert count == 0


def test_mailing_missing_shipment_id_and_unstored_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shipment = CapacitasInCassMailingShipmentRow(status_code=32)
    parent = CapacitasInCassMailingReceiptParent(parent_id="P")
    client = SimpleNamespace(
        warmup_mailing_list_page=AsyncMock(),
        search_mailing_subjects=AsyncMock(
            return_value=[CapacitasInCassMailingSubjectRow(external_id="S")]
        ),
        fetch_mailing_contacts=AsyncMock(
            return_value=[CapacitasInCassMailingContactRow(email="mail@example.org")]
        ),
        fetch_mailing_shipments=AsyncMock(return_value=[shipment]),
        fetch_mailing_receipt_parents=AsyncMock(return_value=[parent]),
        fetch_objman_documents=AsyncMock(return_value=[SimpleNamespace(object_id="D")]),
        download_objman_document=AsyncMock(return_value=b"receipt"),
    )
    monkeypatch.setattr(incass, "_apply_mailing_contact_to_subject", lambda *args, **kwargs: None)
    monkeypatch.setattr(incass, "_store_mailing_receipt_document", lambda *args, **kwargs: False)
    data, count = asyncio.run(
        incass._sync_incass_mailing_data(
            client=client,
            db=Mock(),
            subject_id=uuid.uuid4(),
            identifier="CF",
            download_receipts=True,
            throttle_ms=0,
        )
    )
    assert count == 0
    assert data.receipt_parents_by_shipment_id == {}
    client.download_objman_document.assert_awaited_once()


@pytest.mark.parametrize("kind", ["person", "company", "absent"])
def test_existing_contact_values_are_not_overwritten(kind: str) -> None:
    person = AnagraficaPerson(email="old@example.org", telefono="123") if kind == "person" else None
    company = (
        AnagraficaCompany(email_pec="old@example.org", telefono="123")
        if kind == "company"
        else None
    )
    db = Mock()
    db.get.side_effect = [person, company]
    incass._apply_mailing_contact_to_subject(
        db,
        subject_id=uuid.uuid4(),
        contact=CapacitasInCassMailingContactRow(email="new@example.org", type="Email"),
    )
    if person is not None:
        assert person.email == "old@example.org"
    if company is not None:
        assert company.email_pec == "old@example.org"


@pytest.mark.parametrize(
    "upload", [incass._upload_notice_pdf_to_nas, incass._upload_receipt_to_nas]
)
def test_existing_nas_file_without_close_method(
    monkeypatch: pytest.MonkeyPatch, upload: object
) -> None:
    connector = SimpleNamespace(
        ensure_directory=Mock(), path_exists=Mock(return_value=True), upload_file=Mock()
    )
    monkeypatch.setattr(incass, "get_nas_client", lambda: connector)
    result = upload(SimpleNamespace(nas_folder_path="/archive"), "existing.pdf", b"data")
    assert result.endswith("/existing.pdf")
    connector.upload_file.assert_not_called()


def test_incass_autosync_defers_without_resolving_subjects(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Mock()
    job = CapacitasInCassSyncJob(requested_by_user_id=None, payload_json={})
    monkeypatch.setattr(incass, "is_incass_autosync_within_operation_window", lambda: False)
    resolver = Mock(side_effect=AssertionError("subjects must not be resolved outside window"))
    monkeypatch.setattr(incass, "_resolve_subjects", resolver)

    result = asyncio.run(incass.run_incass_sync_job(db, Mock(), job))

    assert result is job
    assert job.status == "queued_resume"
    assert job.started_at is None
    assert job.completed_at is None
    assert job.error_detail.startswith("Autosync inCASS fuori finestra oraria")
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(job)
    resolver.assert_not_called()


def test_incass_autosync_policy_overrides_requested_details() -> None:
    job = CapacitasInCassSyncJob(requested_by_user_id=None)
    payload = CapacitasInCassSyncJobCreateRequest(include_mailing_list=True)

    result = incass._apply_autosync_status_refresh_policy(job, payload)

    assert result is not payload
    assert result.include_details == incass.settings.capacitas_incass_autosync_include_details
    assert result.include_partitario == incass.settings.capacitas_incass_autosync_include_partitario
    assert result.include_mailing_list is False
    assert result.download_mailing_receipts is False
    assert payload.include_mailing_list is True


def test_incass_amount_with_one_decimal_separator() -> None:
    assert incass._parse_notice_amount("123.45") == 123.45


def test_pending_notice_search_continues_after_a_different_notice() -> None:
    other = AnagraficaPaymentNotice(source_system="other", source_notice_id="different")
    target = AnagraficaPaymentNotice(source_system="incass", source_notice_id="target")
    db = SimpleNamespace(new=[other, target])

    assert incass._find_pending_payment_notice(
        db, source_system="incass", source_notice_id="target"
    ) is target
