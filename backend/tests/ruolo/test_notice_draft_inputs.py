"""Input provenance through actual generation; no confirmation/export authorization."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiReminder,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.notice_register_models import NoticeDocument
from app.modules.ruolo.notice_revision_models import NoticeGenerationRevision
from app.modules.ruolo.services import notice_draft_inputs as inputs
from app.modules.ruolo.services.notice_draft_review import (
    DraftReviewBlocked,
    _basis,
    check_generation_inputs,
)
from app.modules.ruolo.services.notice_revision import (
    GenerationRevision,
    GenerationRevisionChanged,
    RevisionProtocolUnavailable,
    read_revision,
)

from .test_notice_generation_concurrency import _change_eligibility, _seed
from .test_notice_revision import generation_engine as generation_engine
from .test_notice_revision import real_revision_engine as real_revision_engine


@pytest.fixture
def input_db(monkeypatch):
    engine = create_engine("sqlite://")
    NoticeGenerationRevision.__table__.create(engine)
    revision = GenerationRevision(uuid4(), 4)
    monkeypatch.setattr(inputs, "read_revision", lambda connection: revision)
    with Session(engine) as db:
        db.add(NoticeGenerationRevision(id=1, epoch=revision.epoch))
        db.commit()
        yield db
    engine.dispose()


def test_capture_cleans_cache_is_scoped_and_returns_copy(input_db):
    db = input_db
    row = db.get(NoticeGenerationRevision, 1)
    db.info["ruolo_tributi_has_active_calculation_policies"] = False
    db.info["unrelated"] = "preserved"

    @inputs.capture_inputs
    def generate(db, value, *, option):
        assert "ruolo_tributi_has_active_calculation_policies" not in db.info
        assert db.info["unrelated"] == "preserved"
        basis = inputs.basis_for(db)
        assert basis["epoch"] == str(row.epoch)
        assert basis["revision"] == 4
        basis["revision"] = -1
        assert inputs.basis_for(db)["revision"] == 4
        return value, option

    assert generate(db, 2, option=3) == (2, 3)
    assert inputs.basis_for(db) is None
    assert generate.__name__ == "generate"


@pytest.mark.parametrize("pending", ["new", "dirty", "deleted"])
def test_pending_changes_not_discarded_or_flushed(input_db, pending):
    db = input_db
    row = db.get(NoticeGenerationRevision, 1)
    if pending == "new":
        db.add(NoticeGenerationRevision(id=2, epoch=uuid4()))
    elif pending == "dirty":
        row.revision = 10
    else:
        db.delete(row)

    @inputs.capture_inputs
    def generate(db):
        assert inputs.basis_for(db) is None
        assert len(getattr(db, pending)) == 1

    generate(db)
    assert len(getattr(db, pending)) == 1


def test_unavailable_protocol_keeps_draft_untracked(input_db, monkeypatch):
    def unavailable(connection):
        raise RevisionProtocolUnavailable("test")

    monkeypatch.setattr(inputs, "read_revision", unavailable)
    assert inputs.capture_inputs(inputs.basis_for)(input_db) is None
    assert inputs.basis_for(input_db) is None


@pytest.mark.parametrize("detached", [True, False])
def test_avviso_from_another_or_closed_session_cannot_receive_basis(input_db, detached):
    with Session(input_db.get_bind()) as other:
        row = other.get(NoticeGenerationRevision, 1)
        if detached:
            other.expunge(row)

        @inputs.capture_inputs
        def generate(db, *, avviso):
            assert inputs.basis_for(db) is None

        generate(input_db, avviso=row)


def test_nested_capture_and_exception_cleanup(input_db):
    @inputs.capture_inputs
    def inner(db):
        assert inputs.basis_for(db)
        raise ValueError("render failed")

    @inputs.capture_inputs
    def outer(db):
        basis = inputs.basis_for(db)
        with pytest.raises(ValueError, match="render failed"):
            inner(db)
        assert inputs.basis_for(db) == basis

    outer(input_db)
    assert inputs.basis_for(input_db) is None


@pytest.mark.parametrize("change", ["transaction", "day"])
def test_cross_transaction_or_midnight_loses_capture(input_db, monkeypatch, change):
    @inputs.capture_inputs
    def generate(db):
        if change == "transaction":
            db.commit()
        else:

            class Tomorrow(date):
                @classmethod
                def today(cls):
                    return date.today() + timedelta(days=1)

            monkeypatch.setattr(inputs, "date", Tomorrow)
        assert inputs.basis_for(db) is None

    generate(input_db)


def _render(payload, *, output_path):
    output_path.write_bytes(b"test artifact")


def _generate(engine, tmp_path, monkeypatch, *, batch, mixed=False, render=None, phase=None):
    avviso_id, document_id = _seed(engine, tmp_path, 2022)
    if mixed:
        with Session(engine) as db:
            avviso = db.get(RuoloAvviso, avviso_id)
            db.add(
                RuoloAvviso(
                    import_job_id=avviso.import_job_id,
                    subject_id=avviso.subject_id,
                    codice_cnc="MIXED",
                    anno_tributario=2024,
                    codice_fiscale_raw="BNCLGU80A01H501Y",
                    nominativo_raw="ALTRO",
                    importo_totale_euro=100,
                    importo_totale_0648=100,
                )
            )
            db.commit()
    with engine.connect() as connection:
        before = read_revision(connection)

    def render_and_change(payload, *, output_path):
        (render or _render)(payload, output_path=output_path)
        if phase == "render":
            _change_eligibility(engine, avviso_id, document_id, "payment")

    monkeypatch.setattr(repo, "generate_reminder_docx", render_and_change)
    monkeypatch.setattr(repo, "_generate_and_store_batch_reminder_pdf", render_and_change)
    with Session(engine) as db:
        if batch:
            record = repo.create_reminder_batch(
                db,
                title="Input review",
                codice_fiscale=[],
                filters={"years": [2022, 2024], "input_basis": {"revision": 999}},
                template_path=None,
                notes=None,
                generated_by=1,
            )
        else:
            record = repo.create_generated_reminder(
                db,
                avviso=db.get(RuoloAvviso, avviso_id),
                generated_by=1,
            )
        generation_id = record.id
        if phase == "before_commit":
            _change_eligibility(engine, avviso_id, document_id, "payment")
        db.commit()
    return generation_id, avviso_id, document_id, before


@pytest.mark.parametrize("batch,mixed", [(False, False), (True, False), (True, True)])
def test_real_generation_has_pre_read_basis(
    real_revision_engine, tmp_path, monkeypatch, batch, mixed
):
    generation_id, _, _, before = _generate(
        real_revision_engine,
        tmp_path,
        monkeypatch,
        batch=batch,
        mixed=mixed,
    )
    review = check_generation_inputs(real_revision_engine, generation_id, batch=batch)
    assert review.basis == before
    assert len(review.draft_ids) == (2 if mixed else 1)
    assert len(review.digest) == 64
    assert not review.authorizes_dispatch and not review.confirmation_available
    assert review == check_generation_inputs(real_revision_engine, generation_id, batch=batch)
    with Session(real_revision_engine) as db:
        drafts = list(db.scalars(select(NoticeDraft)))
        assert all(draft.input_basis["revision"] == before.revision for draft in drafts)
        assert all(draft.state == "review_required" for draft in drafts)
        assert (
            db.scalar(select(NoticeDocument).where(NoticeDocument.source_system.like("gaia_%")))
            is None
        )


@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("phase", ["render", "before_commit"])
def test_change_during_generation_never_gets_fresh_token(
    real_revision_engine, tmp_path, monkeypatch, batch, phase
):
    generation_id, _, _, before = _generate(
        real_revision_engine,
        tmp_path,
        monkeypatch,
        batch=batch,
        phase=phase,
    )
    with Session(real_revision_engine) as db:
        draft = db.scalar(select(NoticeDraft))
        assert draft.input_basis["revision"] == before.revision
    with pytest.raises(GenerationRevisionChanged):
        check_generation_inputs(real_revision_engine, generation_id, batch=batch)


def test_caller_stale_orm_and_policy_cache_refreshed(real_revision_engine, tmp_path, monkeypatch):
    avviso_id, _ = _seed(real_revision_engine, tmp_path, 2022)
    monkeypatch.setattr(repo, "generate_reminder_docx", _render)
    with Session(real_revision_engine) as db:
        avviso = db.get(RuoloAvviso, avviso_id)
        assert avviso.importo_totale_euro == 100
        db.info["ruolo_tributi_has_active_calculation_policies"] = True
        with real_revision_engine.begin() as writer:
            writer.execute(
                text(
                    "UPDATE ruolo_avvisi SET importo_totale_euro = 150, importo_totale_0648 = 150 WHERE id = :id"
                ),
                {"id": avviso_id},
            )
        reminder = repo.create_generated_reminder(db, avviso=avviso, generated_by=1)
        assert avviso.importo_totale_euro == 150
        assert "150" in reminder.payload_json["saldo_amount"]
        generation_id = reminder.id
        db.commit()
    assert check_generation_inputs(real_revision_engine, generation_id, batch=False).draft_ids


@pytest.mark.parametrize("change", ["payment", "notification", "step"])
def test_mixed_lot_refuses_whole_review_after_writer(
    real_revision_engine, tmp_path, monkeypatch, change
):
    generation_id, avviso_id, document_id, _ = _generate(
        real_revision_engine,
        tmp_path,
        monkeypatch,
        batch=True,
        mixed=True,
    )
    _change_eligibility(real_revision_engine, avviso_id, document_id, change)
    with pytest.raises(GenerationRevisionChanged):
        check_generation_inputs(real_revision_engine, generation_id, batch=True)
    with Session(real_revision_engine) as db:
        assert all(draft.state == "review_required" for draft in db.scalars(select(NoticeDraft)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_basis", None),
        ("input_basis", {}),
        ("artifact", b"tampered"),
        ("artifact", b""),
        ("artifact_format", "txt"),
        ("manifest", {"tampered": True}),
    ],
)
def test_legacy_and_tampered_drafts_refused(
    real_revision_engine, tmp_path, monkeypatch, field, value
):
    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=False)
    with Session(real_revision_engine) as db:
        setattr(db.scalar(select(NoticeDraft)), field, value)
        db.commit()
    with pytest.raises(DraftReviewBlocked):
        check_generation_inputs(real_revision_engine, generation_id, batch=False)


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "extra",
        "origin",
        "record_state",
        "public_path",
        "count",
        "failed",
        "basis_mismatch",
    ],
)
def test_incomplete_or_inconsistent_batch_refused(
    real_revision_engine, tmp_path, monkeypatch, change
):
    generation_id, _, _, _ = _generate(
        real_revision_engine, tmp_path, monkeypatch, batch=True, mixed=True
    )
    with Session(real_revision_engine) as db:
        parent = db.get(RuoloTributiReminderBatch, generation_id)
        item = db.scalar(select(RuoloTributiReminderBatchItem))
        draft = db.scalar(select(NoticeDraft))
        if change == "missing":
            db.delete(draft)
        elif change == "extra":
            db.add(
                NoticeDraft(
                    source_system="gaia_batch_item",
                    source_id=uuid4(),
                    batch_id=generation_id,
                    actor_id=1,
                    manifest={},
                    artifact=b"extra",
                    artifact_sha256="0" * 64,
                    artifact_format="pdf",
                )
            )
        elif change == "origin":
            draft.source_system = "gaia_reminder"
        elif change == "record_state":
            item.status = "failed"
        elif change == "public_path":
            item.generated_document_path = "/must/not/be/public.pdf"
        elif change == "count":
            parent.items_total += 1
        elif change == "failed":
            parent.items_failed = 1
        else:
            draft.input_basis = {**draft.input_basis, "revision": draft.input_basis["revision"] + 1}
        db.commit()
    with pytest.raises(DraftReviewBlocked):
        check_generation_inputs(real_revision_engine, generation_id, batch=True)


@pytest.mark.parametrize("batch", [True, False])
def test_missing_generation_refused(real_revision_engine, batch):
    with pytest.raises(DraftReviewBlocked, match="non trovat"):
        check_generation_inputs(real_revision_engine, uuid4(), batch=batch)


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", None),
        ("version", True),
        ("version", 2),
        ("revision", True),
        ("revision", -1),
        ("revision", "1"),
        ("epoch", None),
        ("epoch", 1),
        ("epoch", "invalid"),
        ("calculation_date", "2000-01-01"),
    ],
)
def test_malformed_basis_refused(field, value):
    basis = {
        "version": 1,
        "revision": 1,
        "epoch": str(uuid4()),
        "calculation_date": date.today().isoformat(),
    }
    basis[field] = value
    with pytest.raises(DraftReviewBlocked):
        _basis([SimpleNamespace(input_basis=basis)])


def test_missing_epoch_and_review_state_refused():
    from app.modules.ruolo.services.notice_draft_review import _integrity

    basis = {"version": 1, "revision": 0, "calculation_date": date.today().isoformat()}
    with pytest.raises(DraftReviewBlocked, match="Epoch"):
        _basis([SimpleNamespace(input_basis=basis)])
    record = SimpleNamespace(
        id=uuid4(), payload_json={}, status="draft", generated_document_path=None
    )
    draft = SimpleNamespace(state="not_review_required", source_id=record.id)
    with pytest.raises(DraftReviewBlocked, match="Artefatto"):
        _integrity([record], [draft])


def test_untracked_generation_never_backfills_existing_draft(
    real_revision_engine, tmp_path, monkeypatch
):
    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=False)
    with Session(real_revision_engine) as db:
        draft = db.scalar(select(NoticeDraft))
        draft.input_basis = None
        db.commit()
    with pytest.raises(DraftReviewBlocked):
        check_generation_inputs(real_revision_engine, generation_id, batch=False)
    with Session(real_revision_engine) as db:
        assert db.scalar(select(NoticeDraft.input_basis)) is None


def test_generation_failure_leaves_no_capture_or_draft(real_revision_engine, tmp_path, monkeypatch):
    avviso_id, _ = _seed(real_revision_engine, tmp_path, 2022)

    def fail(payload, *, output_path):
        raise RuntimeError("rendering failed")

    monkeypatch.setattr(repo, "generate_reminder_docx", fail)
    with Session(real_revision_engine) as db:
        with pytest.raises(RuntimeError, match="rendering failed"):
            repo.create_generated_reminder(
                db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1
            )
        assert inputs.basis_for(db) is None
        db.rollback()
        assert db.scalar(select(NoticeDraft)) is None
        assert db.scalar(select(RuoloTributiReminder)) is None


@pytest.mark.parametrize("limit", ["MAX_REVIEW_BYTES", "MAX_REVIEW_ITEMS"])
def test_review_budget_refuses_large_lot(real_revision_engine, tmp_path, monkeypatch, limit):
    from app.modules.ruolo.services import notice_draft_review

    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=True)
    monkeypatch.setattr(notice_draft_review, limit, 0)
    with pytest.raises(DraftReviewBlocked, match="oltre i limiti"):
        check_generation_inputs(real_revision_engine, generation_id, batch=True)


@pytest.mark.parametrize("change", ["status", "generated", "empty", "wrong_batch"])
def test_batch_remaining_boundaries(real_revision_engine, tmp_path, monkeypatch, change):
    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=True)
    with Session(real_revision_engine) as db:
        parent = db.get(RuoloTributiReminderBatch, generation_id)
        if change == "status":
            parent.status = "failed"
        elif change == "generated":
            parent.items_generated = 1
        elif change == "empty":
            db.delete(db.scalar(select(NoticeDraft)))
            db.delete(db.scalar(select(RuoloTributiReminderBatchItem)))
        else:
            db.scalar(select(NoticeDraft)).batch_id = None
        db.commit()
    with pytest.raises(DraftReviewBlocked):
        check_generation_inputs(real_revision_engine, generation_id, batch=True)


def test_single_draft_attached_to_batch_is_refused(real_revision_engine, tmp_path, monkeypatch):
    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=False)
    with Session(real_revision_engine) as db:
        parent = RuoloTributiReminderBatch(status="review_required", generated_by=1)
        db.add(parent)
        db.flush()
        db.scalar(select(NoticeDraft)).batch_id = parent.id
        db.commit()
    with pytest.raises(DraftReviewBlocked, match="Provenienza"):
        check_generation_inputs(real_revision_engine, generation_id, batch=False)


def test_migration_preserves_legacy_bytes_without_assigning_revision(
    real_revision_engine, tmp_path, monkeypatch
):
    generation_id, _, _, _ = _generate(real_revision_engine, tmp_path, monkeypatch, batch=False)
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_1900_notice_draft_input_basis.py",
    )
    with real_revision_engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            migration.upgrade()
    with Session(real_revision_engine) as db:
        draft = db.scalar(select(NoticeDraft))
        assert draft.artifact == b"test artifact"
        assert draft.input_basis is None
    with pytest.raises(DraftReviewBlocked, match="Revisione assente"):
        check_generation_inputs(real_revision_engine, generation_id, batch=False)
