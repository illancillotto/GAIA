"""Conservative eligibility, evaluated from current accounting and reviewed history."""

from decimal import Decimal

from sqlalchemy import func, select

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeDocument,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)

GAIA_SOURCES = ("gaia_reminder", "gaia_batch_item")


def _recovery_blocks(recovery, generated: bool) -> bool:
    # A newly generated draft has no STEP decision of its own yet; historical
    # positions must still be cleared. An explicit later assignment always blocks.
    if generated and recovery is not None and recovery.state == "da_verificare":
        return False
    return recovery is None or recovery.state not in {"non_affidato_verificato", "revocato"}


def _history_reasons(db, avviso) -> list[str]:
    rows = db.execute(
        select(NoticePosition, NoticeDocument, NoticeNotification, NoticeRecovery)
        .join(NoticeDocument, NoticeDocument.id == NoticePosition.document_id)
        .outerjoin(NoticeNotification, NoticeNotification.document_id == NoticeDocument.id)
        .outerjoin(NoticeRecovery, NoticeRecovery.position_id == NoticePosition.id)
        .where(NoticePosition.avviso_id == avviso.id, NoticeDocument.reconciled_into_id.is_(None))
    ).all()
    reasons = []
    historical = False
    for position, document, notification, recovery in rows:
        generated = document.source_system in GAIA_SOURCES
        historical |= not generated
        reasons.extend(_document_reasons(db, document, notification))
        if position.tax_year != avviso.anno_tributario:
            reasons.append("annualita_discordante")
        if (document.tax_code or "").strip().upper() != (
            avviso.codice_fiscale_raw or ""
        ).strip().upper():
            reasons.append("destinatario_discordante")
        if _recovery_blocks(recovery, generated):
            reasons.append("step_non_liberato")
    if not historical:
        reasons.append("storico_non_verificato")
    return reasons


def _document_reasons(db, document, notification) -> list[str]:
    reasons = []
    state = notification.state if notification else "da_verificare"
    if state not in {"nessuna_evidenza", "tentativo_senza_notifica"}:
        reasons.append(f"notifica_{state}")
    attempts = db.scalar(
        select(NoticeAttempt.id).where(NoticeAttempt.document_id == document.id).limit(1)
    )
    if attempts is not None and (
        state != "tentativo_senza_notifica" or notification.evidence_id is None
    ):
        reasons.append("invii_non_chiariti")
    unlinked = db.scalar(
        select(NoticePosition.id)
        .where(
            NoticePosition.document_id == document.id,
            NoticePosition.avviso_id.is_(None),
        )
        .limit(1)
    )
    if unlinked is not None:
        reasons.append("collegamenti_mancanti")
    return reasons


def _ambiguous_history(db, avviso) -> bool:
    linked = (
        select(NoticePosition.id).where(NoticePosition.document_id == NoticeDocument.id).exists()
    )
    unlinked = (
        select(NoticePosition.id)
        .where(
            NoticePosition.document_id == NoticeDocument.id,
            NoticePosition.avviso_id.is_(None),
        )
        .exists()
    )
    # A shared tax code can veto an unsafe decision, never establish a link.
    return (
        db.scalar(
            select(NoticeDocument.id)
            .where(
                NoticeDocument.reconciled_into_id.is_(None),
                func.upper(func.trim(NoticeDocument.tax_code))
                == (avviso.codice_fiscale_raw or "").strip().upper(),
                (~linked | unlinked),
            )
            .limit(1)
        )
        is not None
    )


def _accounting_reasons(item: dict) -> list[str]:
    avviso = item["avviso"]
    reasons = []
    saldo = item.get("saldo_amount")
    if saldo is None or not Decimal(str(saldo)).is_finite():
        reasons.append("saldo_non_verificato")
    elif Decimal(str(saldo)) <= 0 or item["payment_status"] not in {"unpaid", "partial"}:
        reasons.append("saldo_non_esigibile")
    if not (avviso.codice_fiscale_raw or "").strip():
        reasons.append("destinatario_non_verificato")
    if item.get("calculation_policy") != "internal_gaia":
        reasons.append("gestione_esterna")
    if item.get("workflow_status") in {"contestato", "sospeso", "annullato"}:
        reasons.append("posizione_bloccata")
    if item.get("mailing_delivery"):
        reasons.append("invio_incass_da_riconciliare")
    return reasons


def eligibility(db, item: dict) -> dict:
    avviso = item["avviso"]
    reasons = _accounting_reasons(item)
    unregistered = db.scalar(
        select(RuoloTributiRegisteredMail.id)
        .where(
            RuoloTributiRegisteredMail.avviso_id == avviso.id,
            ~select(NoticeAttempt.id)
            .where(
                NoticeAttempt.registered_mail_id == RuoloTributiRegisteredMail.id,
            )
            .exists(),
        )
        .limit(1)
    )
    if unregistered is not None:
        reasons.append("poste_da_importare")
    reasons.extend(_history_reasons(db, avviso))
    if _ambiguous_history(db, avviso):
        reasons.append("storici_da_collegare")
    return {"avviso_id": str(avviso.id), "eligible": not reasons, "reasons": sorted(set(reasons))}


def generation_allowed(db, item: dict, otherwise_allowed: bool) -> bool:
    if not otherwise_allowed:
        return False
    if item["avviso"].anno_tributario not in {2022, 2023}:
        return True
    return eligibility(db, item)["eligible"]
