"""Legacy boundary cases and register integration, without weakening eligibility."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiCalculationPolicy,
    RuoloTributiPayment,
    RuoloTributiPaymentImportJob,
    RuoloTributiPostaOnlineImportJob,
    RuoloTributiRegisteredMail,
    RuoloTributiReminder,
    RuoloTributiSpecialAllocation,
    RuoloTributiSpecialNotice,
    RuoloTributiYearManager,
)
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.services import registered_mail_association
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)

from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database


def test_unknown_notification_dates_fall_back_to_registered_mail():
    avviso_id = UUID(seed_avviso())
    mail = RuoloTributiRegisteredMail(
        source_shipment_id="DATES",
        recipient_index=0,
        avviso_id=avviso_id,
        raw_payload_json={"received_at": "invalid", "delivered_at": "29/06/2024"},
    )
    assert repo._registered_mail_received_date(mail) == date(2024, 6, 29)
    with TestingSessionLocal() as db:
        db.add(mail)
        db.flush()
        assert repo._notification_interest_start_for_avviso(
            db, avviso_id=avviso_id, mailing_delivery={"delivered_at": "invalid"}
        ) == (date(2024, 6, 29), "registered_mail_received_at")
    assert repo._effective_notification_interest_start(
        avviso_id=avviso_id,
        mailing_delivery={"accepted_at": "invalid"},
        registered_mail_dates={avviso_id: date(2024, 6, 29)},
    ) == (date(2024, 6, 29), "registered_mail_received_at")


def test_import_partial_mapping_and_unrecognised_values():
    assert (
        repo.payment_import_unmatched_items(
            RuoloTributiPaymentImportJob(mapping_json={"unmatched": "invalid", "errors": None})
        )
        == []
    )
    assert repo._resolve_payment_import_mapping(["Amount"], {"extra": "Missing"}) == {}
    assert repo._first_regex("done", r"(missing)?(done)") == "done"
    assert repo._extract_posta_online_city("OR", "09170 ORISTANO (OR)") == "ORISTANO"
    with TestingSessionLocal() as db:
        assert repo._match_payment_import_avviso(
            db, {"codice_utenza": "MISSING", "anno_tributario": 2024}
        ) == (None, "Avviso non trovato con codice CNC o codice utenza/anno")


def test_unbounded_policy_and_manager_year_filters():
    first = UUID(seed_avviso(anno=2024))
    seed_avviso(anno=2025)
    policy = RuoloTributiCalculationPolicy(name="Annualita corrente", year_from=2024, year_to=2024)
    assert repo._calculation_policy_group_key(policy) == "Annualita corrente"
    policy.year_from, policy.year_to = None, None
    with TestingSessionLocal() as db:
        assert (
            len(list(db.scalars(select(RuoloAvviso.id).where(repo._policy_year_filter(policy)))))
            == 2
        )
        db.add(
            RuoloTributiYearManager(
                manager_key="test",
                manager_label="Test",
                year_from=None,
                year_to=2024,
                calculation_policy="internal_gaia",
                is_active=True,
            )
        )
        db.flush()
        assert list(
            db.scalars(select(RuoloAvviso.id).where(*repo._year_filter_for_manager(db, "test")))
        ) == [first]


def test_preferred_incass_document_takes_precedence():
    avviso_id = UUID(seed_avviso())
    with TestingSessionLocal() as db:
        db.add_all(
            [
                AnagraficaPaymentNotice(
                    source_system="incass",
                    source_notice_id=key,
                    anno="2024",
                    codice_fiscale="RSSMRA80A01H501Z",
                    detail_url=f"https://example.test/{key}",
                )
                for key in ("PREFERRED", "NEWER")
            ]
        )
        db.flush()
        result = repo._load_incass_notice_link(
            db, db.get(RuoloAvviso, avviso_id), preferred_notice_id="PREFERRED"
        )
        assert result["source_notice_id"] == "PREFERRED"


def test_voided_payment_does_not_reduce_balance_or_enable_postage_recovery():
    avviso_id = UUID(seed_avviso())
    with TestingSessionLocal() as db:
        db.add(
            RuoloTributiRegisteredMail(
                source_shipment_id="PAYMENT",
                recipient_index=0,
                avviso_id=avviso_id,
                recovery_status="pending",
                raw_payload_json={},
            )
        )
        db.flush()
        payment = repo.create_payment(
            db, avviso=db.get(RuoloAvviso, avviso_id), amount=100, status="voided", created_by=1
        )
        assert payment.status == "voided"
        assert repo.get_tributi_avviso(db, avviso_id)["saldo_amount"] == 100
        assert db.scalar(select(RuoloTributiRegisteredMail.recovery_status)) == "pending"


def test_summary_does_not_count_zero_balance_as_sendable():
    seed_avviso(amount=0)
    with TestingSessionLocal() as db:
        summary = repo.get_tributi_summary(db)
        assert summary["total_count"] == 1
        assert summary["to_send_count"] == summary["sent_count"] == 0


def test_already_voided_allocation_is_idempotent():
    with TestingSessionLocal() as db:
        notice = AnagraficaPaymentNotice(source_system="incass", source_notice_id="SPECIAL")
        db.add(notice)
        db.flush()
        special = RuoloTributiSpecialNotice(
            payment_notice_id=notice.id,
            source_notice_id="SPECIAL",
            codice_ruolo="99",
            kind="special",
            label="Test",
            allocated_amount=0,
        )
        db.add(special)
        db.flush()
        allocation = RuoloTributiSpecialAllocation(
            special_notice_id=special.id,
            amount=10,
            status="voided",
            voided_by=1,
        )
        db.add(allocation)
        db.flush()
        assert (
            repo.void_special_allocation(
                db, special=special, allocation_id=allocation.id, voided_by=2
            )
            is allocation
        )
        assert allocation.voided_by == 1
        assert special.allocated_amount == 0


def test_poste_upsert_updates_same_source_without_duplicates():
    with TestingSessionLocal() as db:
        job = RuoloTributiPostaOnlineImportJob(filename="test.json", status="completed")
        db.add(job)
        db.flush()
        row = {"source_shipment_id": "POSTE", "recipient_index": 0, "raw": {}}
        first = repo._upsert_posta_online_registered_mail(db, job=job, row=row, annualita=[2022])
        repeated = repo._upsert_posta_online_registered_mail(
            db, job=job, row={**row, "tracking_number": "123"}, annualita=[2022]
        )
        assert repeated.id == first.id
        assert repeated.tracking_number == "123"
        assert db.scalar(select(func.count()).select_from(RuoloTributiRegisteredMail)) == 1


def test_registered_mail_manual_association_survives_reimport():
    avviso_id = UUID(seed_avviso(anno=2022, nominativo="DESTINATARIO MANUALE"))
    with TestingSessionLocal() as db:
        job = RuoloTributiPostaOnlineImportJob(filename="manual.json", status="completed")
        db.add(
            RuoloTributiPayment(
                avviso_id=avviso_id,
                amount=Decimal("1.00"),
                source="manual",
                status="valid",
            )
        )
        mail = RuoloTributiRegisteredMail(
            source_shipment_id="MANUAL-1",
            recipient_index=0,
            match_status="unmatched",
            recovery_status="pending",
            raw_payload_json={"candidate_avviso_ids": []},
        )
        db.add_all([job, mail])
        db.flush()
        registered_mail_association.set_manual_association(
            db,
            mail=mail,
            avviso=db.get(RuoloAvviso, avviso_id),
            updated_by=17,
        )

        repeated = repo._upsert_posta_online_registered_mail(
            db,
            job=job,
            row={
                "source_shipment_id": "MANUAL-1",
                "recipient_index": 0,
                "recipient_name": "NESSUN MATCH",
                "recipient_city": "ALTRO COMUNE",
                "raw": {},
            },
            annualita=[2022],
        )

        assert repeated.avviso_id == avviso_id
        assert repeated.match_status == "matched"
        assert repeated.match_score == 100
        assert repeated.recovery_status == "ready_on_payment"
        assert repeated.raw_payload_json[registered_mail_association.MANUAL_ASSOCIATION_KEY]["updated_by"] == 17
        assert repeated.raw_payload_json["candidate_avviso_ids"] == []


def test_registered_mail_multi_association_publishes_cumulative_register():
    with TestingSessionLocal() as db:
        subject = AnagraficaSubject(source_name_raw="CONTRIBUENTE CUMULATIVO")
        other_subject = AnagraficaSubject(source_name_raw="ALTRO CONTRIBUENTE")
        db.add_all([subject, other_subject])
        db.flush()
        job = RuoloTributiPostaOnlineImportJob(filename="multi.json", status="completed")
        db.add(job)
        db.flush()
        avvisi = [
            RuoloAvviso(
                import_job_id=job.id,
                codice_cnc=f"MULTI-{year}",
                anno_tributario=year,
                subject_id=subject.id,
                codice_fiscale_raw="RSSMRA80A01H501Z",
                nominativo_raw="CONTRIBUENTE CUMULATIVO",
            )
            for year in (2022, 2023)
        ]
        other = RuoloAvviso(
            import_job_id=job.id,
            codice_cnc="MULTI-OTHER",
            anno_tributario=2023,
            subject_id=other_subject.id,
        )
        mail = RuoloTributiRegisteredMail(
            source_shipment_id="MULTI-1",
            recipient_index=0,
            match_status="unmatched",
            recovery_status="pending",
            price_amount=Decimal("11.55"),
        )
        db.add_all([*avvisi, other, mail])
        db.flush()

        registered_mail_association.set_manual_association(
            db, mail=mail, avvisi=avvisi, avviso=avvisi[0], updated_by=7
        )
        document = db.scalar(select(NoticeDocument))
        assert document is not None
        assert document.original_json["registered_mail_cost_amount"] == 11.55
        assert len(list(db.scalars(select(NoticePosition)))) == 2
        attempt = db.scalar(select(NoticeAttempt))
        assert attempt is not None and attempt.registered_mail_id == mail.id
        assert mail.raw_payload_json["manual_association"]["avviso_ids"] == [
            str(item.id) for item in avvisi
        ]

        db.add(
            RuoloTributiPayment(
                avviso_id=avvisi[1].id,
                amount=Decimal("3.00"),
                source="manual",
                status="valid",
            )
        )
        db.flush()
        repo.mark_registered_mail_recovery_on_payment(db, avviso_id=avvisi[1].id)
        assert mail.recovery_status == "ready_on_payment"

        replacement = [
            RuoloAvviso(
                import_job_id=job.id,
                codice_cnc=f"MULTI-REPLACED-{year}",
                anno_tributario=year,
                subject_id=subject.id,
                codice_fiscale_raw="RSSMRA80A01H501Z",
                nominativo_raw="CONTRIBUENTE CUMULATIVO",
            )
            for year in (2024, 2025)
        ]
        db.add_all(replacement)
        db.flush()
        registered_mail_association.set_manual_association(
            db, mail=mail, avvisi=replacement, avviso=replacement[0], updated_by=7
        )
        positions = list(
            db.scalars(
                select(NoticePosition)
                .where(NoticePosition.document_id == document.id)
                .order_by(NoticePosition.tax_year)
            )
        )
        assert [(position.tax_year, position.avviso_id) for position in positions] == [
            (2022, None),
            (2023, None),
            (2024, replacement[0].id),
            (2025, replacement[1].id),
        ]

        with pytest.raises(ValueError, match="stesso contribuente"):
            registered_mail_association.set_manual_association(
                db, mail=mail, avvisi=[avvisi[0], other], avviso=avvisi[0], updated_by=7
            )

        registered_mail_association.set_manual_association(db, mail=mail, avviso=None, updated_by=7)
        assert all(position.avviso_id is None for position in db.scalars(select(NoticePosition)))


def test_registered_mail_manual_unlink_and_stale_target_remain_fail_closed():
    with TestingSessionLocal() as db:
        job = RuoloTributiPostaOnlineImportJob(filename="manual-unlink.json", status="completed")
        mail = RuoloTributiRegisteredMail(
            source_shipment_id="MANUAL-UNLINK",
            recipient_index=0,
            match_status="matched",
            recovery_status="pending",
            raw_payload_json={},
        )
        db.add_all([job, mail])
        db.flush()
        registered_mail_association.set_manual_association(db, mail=mail, avviso=None, updated_by=18)

        repeated = repo._upsert_posta_online_registered_mail(
            db,
            job=job,
            row={"source_shipment_id": "MANUAL-UNLINK", "recipient_index": 0, "raw": {}},
            annualita=[2022],
        )
        assert repeated.avviso_id is None
        assert repeated.match_status == "unmatched"
        assert repeated.anomaly_key == "manual_unlinked"
        assert registered_mail_association.manual_match(db, {"avviso_id": "invalid"})["anomaly_key"] == "manual_target_missing"
        assert registered_mail_association.manual_match(db, {"avviso_id": str(uuid4())})["anomaly_key"] == "manual_target_missing"
        assert registered_mail_association.manual_match(db, None) is None
        assert registered_mail_association.manual_association(None) is None
        assert registered_mail_association.manual_association(
            RuoloTributiRegisteredMail(
                source_shipment_id="NO-PAYLOAD",
                recipient_index=0,
                raw_payload_json={registered_mail_association.MANUAL_ASSOCIATION_KEY: {"active": False}},
            )
        ) is None


def test_candidate_invalid_cf_filter_and_missing_manager_label(monkeypatch):
    avviso_id = UUID(seed_avviso())
    monkeypatch.setattr(
        repo,
        "get_year_manager_for_year",
        lambda *_: {
            "manager_key": "internal",
            "manager_label": None,
            "calculation_policy": "internal_gaia",
        },
    )
    with TestingSessionLocal() as db:
        result = repo._collect_reminder_candidates(
            db,
            years=[2024],
            anno_from=None,
            anno_to=None,
            q=None,
            comune=None,
            codice_fiscale=["!!!"],
        )
        assert len(result) == 1
        assert result[0]["annuality_managers"] == []
        assert result[0]["avvisi"][0]["id"] == avviso_id
        assert result[0]["due_amount"] == 100
        assert result[0]["nas_folder_path"] is None
        assert result[0]["has_nas_folder"] is False


@pytest.mark.parametrize("kind", ["person", "company"])
def test_archive_lookup_tolerates_subject_disappearing_between_reads(monkeypatch, kind):
    with TestingSessionLocal() as db:
        subject = AnagraficaSubject(source_name_raw="Test")
        db.add(subject)
        db.flush()
        record = (
            AnagraficaPerson(
                subject_id=subject.id, codice_fiscale="TESTCF", cognome="Test", nome="Persona"
            )
            if kind == "person"
            else AnagraficaCompany(
                subject_id=subject.id,
                codice_fiscale="TESTCF",
                ragione_sociale="Test",
                partita_iva="12345678901",
            )
        )
        db.add(record)
        db.flush()
        original_get = db.get
        monkeypatch.setattr(
            db,
            "get",
            lambda model, key: None if model is AnagraficaSubject else original_get(model, key),
        )
        stale_subject_id = uuid4()
        assert repo._resolve_subject_archive(db, "TESTCF", stale_subject_id) == (
            stale_subject_id,
            None,
        )


def test_unfinished_batch_item_is_not_counted_as_generated_or_failed(tmp_path, monkeypatch):
    subject_id = seed_subject_with_nas(tmp_path)
    seed_avviso(subject_id=subject_id)
    monkeypatch.setattr(repo, "_generate_prepared_batch_item", lambda *_args, **_kwargs: None)
    with TestingSessionLocal() as db:
        batch = repo.create_reminder_batch(
            db,
            title="Pending boundary",
            codice_fiscale=["RSSMRA80A01H501Z"],
            filters={},
            template_path=None,
            notes=None,
            generated_by=1,
        )
        assert batch.items_total == 1
        assert batch.items_generated == batch.items_failed == 0
        assert db.scalar(select(NoticeDocument)) is None


def test_generated_reminder_register_shares_outer_transaction(tmp_path, monkeypatch):
    avviso_id = UUID(seed_avviso(anno=2024, verified_history=True))
    monkeypatch.setattr(repo, "reminder_storage_dir", lambda: tmp_path)
    monkeypatch.setattr(repo, "generate_reminder_docx", lambda *_args, **_kwargs: None)
    with TestingSessionLocal() as db:
        reminder = repo.create_generated_reminder(
            db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1
        )
        document = db.scalar(
            select(NoticeDocument).where(NoticeDocument.source_system == "gaia_reminder")
        )
        assert document.source_key == str(reminder.id)
        assert (
            db.scalar(
                select(NoticePosition.avviso_id).where(NoticePosition.document_id == document.id)
            )
            == avviso_id
        )
        assert db.get(NoticeNotification, document.id).state == "nessuna_evidenza"
        assert db.scalar(select(NoticeAttempt)) is None
        evidence = db.scalar(
            select(NoticeEvidence).where(NoticeEvidence.document_id == document.id)
        )
        assert evidence.kind == "documento_generato"
        assert evidence.reference == reminder.generated_document_path
        assert (
            db.scalar(select(NoticeAudit.actor_id).where(NoticeAudit.document_id == document.id))
            == 1
        )
        document_id = document.id
        db.rollback()
    with TestingSessionLocal() as db:
        assert db.get(NoticeDocument, document_id) is None
        assert db.scalar(select(RuoloTributiReminder)) is None
        assert db.scalar(select(func.count()).select_from(NoticeDocument)) == 1


def test_document_eligibility_reads_real_accounting_and_recorded_attempt_blocks():
    seed_avviso(anno=2022, verified_history=True)
    with TestingSessionLocal() as db:
        document_id = db.scalar(select(NoticeDocument.id))
    url = f"/ruolo/tributi/registro-avvisi/{document_id}"
    headers = auth_headers()
    result = client.get(f"{url}/ammissibilita", headers=headers)
    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["authorizes_dispatch"] is False
    attempt = client.post(
        f"{url}/invii",
        headers=headers,
        json={
            "reason": "Riscontro distinta",
            "expected_version": result.json()["version"],
            "data": {
                "channel": "posta",
                "sent_at": "2024-06-29T10:00:00Z",
                "evidence_reference": "Distinta cartacea",
                "confirmed": True,
            },
        },
    )
    assert attempt.status_code == 201
    result = client.get(f"{url}/ammissibilita", headers=headers).json()
    assert not result["eligible"]
    assert {"invii_non_chiariti", "notifica_da_verificare", "generazione_non_abilitata"} <= set(
        result["reasons"]
    )


def test_changed_historical_review_blocks_generation_after_candidate_selection(
    tmp_path, monkeypatch
):
    avviso_id = UUID(seed_avviso(anno=2022, verified_history=True))
    generated = []
    monkeypatch.setattr(
        repo, "generate_reminder_docx", lambda *args, **kwargs: generated.append(args)
    )
    with TestingSessionLocal() as db:
        assert repo.get_tributi_avviso(db, avviso_id)["reminder_enabled"]
    with TestingSessionLocal() as db:
        recovery = db.scalar(select(NoticeRecovery))
        recovery.state = "da_verificare"
        db.commit()
    with TestingSessionLocal() as db:
        with pytest.raises(repo.ReminderUnavailableError):
            repo.create_generated_reminder(
                db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1
            )
        assert generated == []
        assert db.scalar(select(RuoloTributiReminder)) is None
