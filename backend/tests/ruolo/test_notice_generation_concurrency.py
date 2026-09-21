"""Concurrent changes may leave private drafts, never published documents.

These tests prove quarantine only, not the future confirmation protocol.
"""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.notice_register_models import NoticeDocument, NoticePosition
from app.modules.ruolo.notice_register_schemas import (
    EvidenceInput,
    NotificationDecision,
    OperatorChange,
    RecoveryDecision,
)
from app.modules.ruolo.services import notice_register as register
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)

from .notice_history_fixtures import seed_verified_history


class StaleGenerationPublished(AssertionError):
    """A concurrent disqualifying change committed before publication."""


def _metadata():
    metadata = MetaData()
    pending = [table for table in Base.metadata.tables.values() if table.name.startswith("ruolo_")]
    pending.extend(
        model.__table__
        for model in (
            ApplicationUser,
            AnagraficaSubject,
            AnagraficaPerson,
            AnagraficaCompany,
            AnagraficaPaymentNotice,
        )
    )
    while pending:
        table = pending.pop()
        if table.key in metadata.tables:
            continue
        table.to_metadata(metadata)
        pending.extend(foreign_key.column.table for foreign_key in table.foreign_keys)
    return metadata


@pytest.fixture
def generation_engine():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato; SQLite non prova questa race")
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    schema = f"notice_generation_race_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(
        url,
        connect_args={
            "options": f"-csearch_path={schema} -clock_timeout=3000 -cstatement_timeout=10000"
        },
    )
    try:
        _metadata().create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def _seed(engine, tmp_path, tax_year):
    with Session(engine) as db:
        db.add(
            ApplicationUser(
                id=1,
                username="generation-race",
                email="generation-race@example.test",
                password_hash="not-used",
                role="admin",
                module_ruolo=True,
                is_active=True,
            )
        )
        subject = AnagraficaSubject(
            source_name_raw="TEST GENERAZIONE",
            nas_folder_path=str(tmp_path),
            nas_folder_letter="T",
        )
        job = RuoloImportJob(anno_tributario=tax_year, filename="race-test", status="completed")
        db.add_all([subject, job])
        db.flush()
        avviso = RuoloAvviso(
            import_job_id=job.id,
            subject_id=subject.id,
            codice_cnc="CNC-RACE",
            anno_tributario=tax_year,
            codice_fiscale_raw="RSSMRA80A01H501Z",
            nominativo_raw="TEST GENERAZIONE",
            codice_utenza="RACE",
            importo_totale_euro=Decimal("100"),
            importo_totale_0648=Decimal("100"),
        )
        db.add(avviso)
        db.flush()
        document = seed_verified_history(db, avviso)
        ids = avviso.id, document.id
        db.commit()
        return ids


def _change_eligibility(engine, avviso_id, document_id, change_kind):
    # This connection commits while the generator's transaction is still open.
    with Session(engine) as db:
        document = db.get(NoticeDocument, document_id)
        change = OperatorChange(
            actor_id=1, reason="Riscontro concorrente", expected_version=document.version
        )
        if change_kind == "payment":
            repo.create_payment(db, avviso=db.get(RuoloAvviso, avviso_id), amount=100, created_by=1)
        elif change_kind == "notification":
            evidence = register.record_evidence(
                db,
                document_id,
                EvidenceInput(
                    source_system="manual",
                    source_key="race-proof",
                    kind="ricevuta",
                    reference="Ricevuta test",
                ),
                change,
            )
            register.assess_notification(
                db,
                document_id,
                NotificationDecision(
                    state="perfezionata", notified_on=date(2024, 6, 29), evidence_id=evidence.id
                ),
                change.model_copy(update={"expected_version": document.version}),
            )
        else:
            position_id = db.scalar(
                select(NoticePosition.id).where(NoticePosition.document_id == document_id)
            )
            register.assess_recovery(
                db,
                document_id,
                position_id,
                RecoveryDecision(
                    state="affidato",
                    verified_on=date.today(),
                    evidence_reference="Report STEP test",
                    case_reference="STEP-RACE",
                ),
                change,
            )
        db.commit()
    with Session(engine) as db:
        assert not repo.get_tributi_avviso(db, avviso_id)["reminder_enabled"]


@pytest.mark.postgres
@pytest.mark.parametrize("tax_year", [2022, 2023])
@pytest.mark.parametrize("mode", ["single", "batch"])
@pytest.mark.parametrize("change_kind", ["payment", "notification", "step"])
@pytest.mark.parametrize(
    "phase",
    ["before", "during", "before_commit"],
)
def test_disqualifying_commit_must_prevent_publication(
    generation_engine, tmp_path, monkeypatch, tax_year, mode, change_kind, phase
):
    avviso_id, document_id = _seed(generation_engine, tmp_path, tax_year)
    rendered = []

    def render(payload, *, output_path):
        rendered.append(payload)
        output_path.write_bytes(b"private draft, not an authorized notice")
        if phase == "during":
            _change_eligibility(generation_engine, avviso_id, document_id, change_kind)

    # Only filesystem/PDF rendering is replaced. Selection, accounting, writers,
    # number reservations, registration and both database commits are real.
    monkeypatch.setattr(repo, "reminder_storage_dir", lambda: tmp_path)
    monkeypatch.setattr(repo, "generate_reminder_docx", render)
    monkeypatch.setattr(repo, "_generate_and_store_batch_reminder_pdf", render)
    with Session(generation_engine) as db:
        assert repo.get_tributi_avviso(db, avviso_id)["reminder_enabled"]
    if phase == "before":
        _change_eligibility(generation_engine, avviso_id, document_id, change_kind)

    with Session(generation_engine) as db:
        try:
            if mode == "single":
                repo.create_generated_reminder(
                    db, avviso=db.get(RuoloAvviso, avviso_id), generated_by=1
                )
            else:
                repo.create_reminder_batch(
                    db,
                    title="Race test",
                    codice_fiscale=["RSSMRA80A01H501Z"],
                    filters={"years": [tax_year]},
                    template_path=None,
                    notes=None,
                    generated_by=1,
                )
            if phase == "before_commit":
                _change_eligibility(generation_engine, avviso_id, document_id, change_kind)
            db.commit()
        except repo.ReminderUnavailableError:
            db.rollback()
        except ValueError as exc:
            assert mode == "batch"
            assert str(exc) == "Nessuna utenza morosa selezionabile per il batch"
            db.rollback()

    with Session(generation_engine) as db:
        assert not repo.get_tributi_avviso(db, avviso_id)["reminder_enabled"]
        drafts = list(db.scalars(select(NoticeDraft)))
        assert len(drafts) == (0 if phase == "before" else 1)
        assert all(draft.state == "review_required" for draft in drafts)
        published = list(
            db.scalars(
                select(NoticeDocument).where(
                    NoticeDocument.source_system.in_(["gaia_reminder", "gaia_batch_item"])
                )
            )
        )
    assert len(rendered) == (0 if phase == "before" else 1)
    if published:
        raise StaleGenerationPublished(
            f"{tax_year}/{mode}: {change_kind} committed in phase {phase}, but document published"
        )
