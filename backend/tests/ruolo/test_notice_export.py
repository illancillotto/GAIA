"""Real PostgreSQL checks from private generation to committed export claim."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from io import BytesIO
from threading import Barrier
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiNoticeNumber, RuoloTributiReminderBatchItem
from app.modules.ruolo.notice_confirmation_models import (
    NoticeExportClaim,
    NoticeExportIdentity,
    NoticeGenerationConfirmation,
    NoticeGenerationExport,
)
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.services import notice_export as service
from app.modules.ruolo.services.notice_draft_review import DraftReviewBlocked, confirm_generation
from app.modules.ruolo.services.notice_revision import GenerationRevisionChanged

from .test_notice_draft_inputs import _generate
from .test_notice_generation_concurrency import _change_eligibility
from .test_notice_revision import generation_engine as generation_engine
from .test_notice_revision import real_revision_engine as real_revision_engine


@pytest.fixture
def confirmed(real_revision_engine, tmp_path, monkeypatch):
    engine = real_revision_engine
    batch_id, avviso_id, document_id, _ = _generate(engine, tmp_path, monkeypatch, batch=True)
    with Session(engine) as db, db.begin():
        confirm_generation(db, batch_id, batch=True, actor_id=1)
    return engine, batch_id, avviso_id, document_id


def test_exact_originals_manifest_and_audited_idempotent_export(confirmed):
    engine, batch_id, _, _ = confirmed
    first = service.export_batch(engine, batch_id, 1)
    assert service.export_batch(engine, batch_id, 1) == first
    with Session(engine) as db:
        drafts = db.scalars(select(NoticeDraft)).all()
        exports = db.scalars(select(NoticeGenerationExport)).all()
        claims = db.scalars(select(NoticeExportClaim)).all()
        assert len(exports) == 1 and len(claims) == 2
        assert exports[0].artifact_sha256 == hashlib.sha256(first).hexdigest()
        assert all(claim.actor_id == 1 for claim in claims)
        with ZipFile(BytesIO(first)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["batch_id"] == str(batch_id)
            assert manifest["authorizes_dispatch"] is False
            for draft in drafts:
                assert archive.read(f"avvisi/{draft.id}.{draft.artifact_format}") == draft.artifact


@pytest.mark.parametrize("change", ["payment", "notification", "step"])
@pytest.mark.parametrize("after_first_export", [False, True])
def test_changed_dependencies_block_new_and_repeated_downloads(
    confirmed, change, after_first_export
):
    engine, batch_id, avviso_id, document_id = confirmed
    if after_first_export:
        service.export_batch(engine, batch_id, 1)
    _change_eligibility(engine, avviso_id, document_id, change)
    with pytest.raises(GenerationRevisionChanged):
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db:
        assert len(db.scalars(select(NoticeExportClaim)).all()) == int(after_first_export)


def test_writer_during_packaging_blocks_claim(confirmed, monkeypatch):
    engine, batch_id, avviso_id, document_id = confirmed
    original = service.build_archive

    def package(snapshot):
        content = original(snapshot)
        _change_eligibility(engine, avviso_id, document_id, "payment")
        return content

    monkeypatch.setattr(service, "build_archive", package)
    with pytest.raises(GenerationRevisionChanged):
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db:
        assert db.scalar(select(NoticeGenerationExport)) is None
        assert db.scalar(select(NoticeExportClaim)) is None


def test_two_simultaneous_exports_share_one_archive(confirmed, monkeypatch):
    engine, batch_id, _, _ = confirmed
    barrier = Barrier(2, timeout=10)
    original = service.build_archive

    def package(snapshot):
        barrier.wait()
        return original(snapshot)

    monkeypatch.setattr(service, "build_archive", package)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.export_batch(engine, batch_id, 1), range(2)))
    assert results[0] == results[1]
    with Session(engine) as db:
        assert len(db.scalars(select(NoticeGenerationExport)).all()) == 1
        assert len(db.scalars(select(NoticeExportClaim)).all()) == 2


@pytest.mark.parametrize(
    "fault",
    [
        "missing_confirmation",
        "digest",
        "basis",
        "identity",
        "number",
        "reservation_state",
        "reservation_identity",
        "reservation_number",
        "missing_reservation",
        "empty_number",
        "bytes",
        "old_date",
        "export_bytes",
        "export_manifest",
    ],
)
def test_invalid_or_tampered_confirmation_never_delivers(confirmed, fault):
    engine, batch_id, _, _ = confirmed
    if fault.startswith("export_"):
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db, db.begin():
        confirmation = db.scalar(select(NoticeGenerationConfirmation))
        reservation = db.scalar(select(RuoloTributiNoticeNumber))
        if fault == "missing_confirmation":
            db.delete(confirmation)
        elif fault == "digest":
            confirmation.review_digest = "f" * 64
        elif fault == "basis":
            confirmation.input_basis = {}
        elif fault == "identity":
            confirmation.identity_keys = []
        elif fault == "number":
            confirmation.notice_numbers = []
        elif fault == "reservation_state":
            reservation.status = "draft"
        elif fault == "reservation_identity":
            reservation.identity_key = "f" * 64
        elif fault == "reservation_number":
            reservation.notice_number = "different"
        elif fault == "missing_reservation":
            db.scalar(select(RuoloTributiReminderBatchItem)).notice_number_id = None
        elif fault == "empty_number":
            record = db.scalar(select(RuoloTributiReminderBatchItem))
            record.payload_json = {**record.payload_json, "notice_number": ""}
            draft = db.scalar(select(NoticeDraft))
            draft.manifest = dict(record.payload_json)
            reservation.notice_number = ""
            confirmation.review_digest = service.review._integrity(
                [record], [draft], expected_status="confirmed"
            )
        elif fault == "bytes":
            db.scalar(select(NoticeDraft)).artifact = b"tampered"
        elif fault == "old_date":
            draft = db.scalar(select(NoticeDraft))
            draft.input_basis = {
                **draft.input_basis,
                "calculation_date": (date.today() - timedelta(days=1)).isoformat(),
            }
        elif fault == "export_bytes":
            db.scalar(select(NoticeGenerationExport)).artifact = b"tampered"
        else:
            db.scalar(select(NoticeGenerationExport)).manifest = {}
    with pytest.raises(DraftReviewBlocked):
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db:
        assert len(db.scalars(select(NoticeExportClaim)).all()) == int(fault.startswith("export_"))


def test_changed_confirmation_between_capture_and_claim(confirmed, monkeypatch):
    engine, batch_id, _, _ = confirmed
    original = service.build_archive

    def package(snapshot):
        archive = original(snapshot)
        with Session(engine) as db, db.begin():
            db.scalar(select(NoticeGenerationConfirmation)).confirmed_at += timedelta(seconds=1)
        return archive

    monkeypatch.setattr(service, "build_archive", package)
    with pytest.raises(DraftReviewBlocked, match="durante"):
        service.export_batch(engine, batch_id, 1)


def test_commit_failure_does_not_return_bytes(confirmed, monkeypatch):
    engine, batch_id, _, _ = confirmed
    original = service._claim

    def claim(db, snapshot, archive, actor):
        original(db, snapshot, archive, actor)
        db.add(NoticeExportClaim(export_id=uuid4(), actor_id=actor))

    monkeypatch.setattr(service, "_claim", claim)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db:
        assert db.scalar(select(NoticeGenerationExport)) is None


@pytest.mark.parametrize("already_exported", [False, True])
def test_regeneration_cannot_export_same_identity_twice(confirmed, already_exported):
    engine, batch_id, _, _ = confirmed
    if already_exported:
        service.export_batch(engine, batch_id, 1)
    with Session(engine) as db, db.begin():
        regenerated = repo.create_reminder_batch(
            db,
            title="Rigenerazione",
            codice_fiscale=[],
            filters={"years": [2022]},
            template_path=None,
            notes=None,
            generated_by=1,
        )
        regenerated_id = regenerated.id
    with Session(engine) as db, db.begin():
        confirm_generation(db, regenerated_id, batch=True, actor_id=1)
    if already_exported:
        with pytest.raises(DraftReviewBlocked, match="rettifica esplicita"):
            service.export_batch(engine, regenerated_id, 1)
    else:
        assert service.export_batch(engine, regenerated_id, 1)
    with Session(engine) as db:
        assert len(db.scalars(select(NoticeGenerationExport)).all()) == 1
        assert len(db.scalars(select(NoticeExportIdentity)).all()) == 1
