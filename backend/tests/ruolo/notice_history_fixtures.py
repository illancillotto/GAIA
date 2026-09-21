"""Explicitly reviewed historical data for reminder integration tests."""

from datetime import date

from sqlalchemy import select

from app.modules.ruolo.notice_register_models import NoticePosition
from app.modules.ruolo.notice_register_schemas import (
    HistoricalDocument,
    NotificationDecision,
    OperatorChange,
    PositionInput,
    RecoveryDecision,
)
from app.modules.ruolo.services import notice_register as register


def seed_verified_history(db, avviso):
    change = OperatorChange(actor_id=1, reason="Verifica storico di test", expected_version=1)
    document = register.create_historical_document(
        db,
        HistoricalDocument(
            document_number=f"STORICO-{avviso.id}",
            tax_code=avviso.codice_fiscale_raw,
            positions=[
                PositionInput(
                    source_namespace="test",
                    source_reference=str(avviso.id),
                    tax_year=avviso.anno_tributario,
                )
            ],
        ),
        change,
    )
    position = db.scalar(select(NoticePosition).where(NoticePosition.document_id == document.id))
    register.link_position(db, document.id, position.id, avviso.id, change)
    register.assess_notification(
        db,
        document.id,
        NotificationDecision(state="nessuna_evidenza"),
        change.model_copy(update={"expected_version": document.version}),
    )
    register.assess_recovery(
        db,
        document.id,
        position.id,
        RecoveryDecision(
            state="non_affidato_verificato",
            verified_on=date.today(),
            evidence_reference="Rapporto STEP di test: posizione non affidata",
        ),
        change.model_copy(update={"expected_version": document.version}),
    )
    return document
