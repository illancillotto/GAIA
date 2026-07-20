from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import String, case, cast, func, literal, or_, select
from sqlalchemy.orm import Session

from app.modules.ruolo.enums import (
    RuoloTributiPaymentRecordStatus,
    RuoloTributiPaymentStatus,
)
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloPartita,
    RuoloTributiAvvisoStatus,
    RuoloTributiNote,
    RuoloTributiPayment,
    RuoloTributiReminder,
)
from app.modules.ruolo.repositories import _get_subject_display_name
from app.modules.ruolo.services.tributi_reminder_service import (
    build_reminder_filename,
    build_reminder_payload,
    generate_reminder_docx,
    reminder_storage_dir,
)


_CURRENCY_ZERO = Decimal("0.00")


def _money(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_or_zero(value: object) -> Decimal:
    return _money(value) or _CURRENCY_ZERO


def _money_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def derive_payment_status(
    *,
    due_amount: object,
    paid_amount: object,
) -> tuple[str, Decimal | None]:
    due = _money(due_amount)
    paid = _money_or_zero(paid_amount)
    if due is None:
        return RuoloTributiPaymentStatus.TO_REVIEW.value, None

    saldo = (due - paid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if paid == _CURRENCY_ZERO:
        return RuoloTributiPaymentStatus.UNPAID.value, saldo
    if paid < due:
        return RuoloTributiPaymentStatus.PARTIAL.value, saldo
    if paid == due:
        return RuoloTributiPaymentStatus.PAID.value, saldo
    return RuoloTributiPaymentStatus.OVERPAID.value, saldo


def _payment_summary_subquery():
    return (
        select(
            RuoloTributiPayment.avviso_id.label("avviso_id"),
            func.coalesce(func.sum(RuoloTributiPayment.amount), 0).label("paid_amount"),
            func.max(RuoloTributiPayment.paid_at).label("last_payment_at"),
        )
        .where(RuoloTributiPayment.status == RuoloTributiPaymentRecordStatus.VALID.value)
        .group_by(RuoloTributiPayment.avviso_id)
        .subquery()
    )


def _notes_summary_subquery():
    return (
        select(
            RuoloTributiNote.avviso_id.label("avviso_id"),
            func.count(RuoloTributiNote.id).label("notes_count"),
        )
        .group_by(RuoloTributiNote.avviso_id)
        .subquery()
    )


def _payment_status_expression(paid_amount_expr: Any):
    return case(
        (RuoloAvviso.importo_totale_euro.is_(None), literal(RuoloTributiPaymentStatus.TO_REVIEW.value)),
        (paid_amount_expr == 0, literal(RuoloTributiPaymentStatus.UNPAID.value)),
        (paid_amount_expr < RuoloAvviso.importo_totale_euro, literal(RuoloTributiPaymentStatus.PARTIAL.value)),
        (paid_amount_expr == RuoloAvviso.importo_totale_euro, literal(RuoloTributiPaymentStatus.PAID.value)),
        else_=literal(RuoloTributiPaymentStatus.OVERPAID.value),
    )


def _base_tributi_query():
    payment_summary = _payment_summary_subquery()
    notes_summary = _notes_summary_subquery()
    paid_amount_expr = func.coalesce(payment_summary.c.paid_amount, 0)
    payment_status_expr = _payment_status_expression(paid_amount_expr).label("derived_payment_status")
    saldo_expr = case(
        (RuoloAvviso.importo_totale_euro.is_(None), None),
        else_=RuoloAvviso.importo_totale_euro - paid_amount_expr,
    ).label("derived_saldo_amount")

    query = (
        select(
            RuoloAvviso,
            RuoloTributiAvvisoStatus,
            paid_amount_expr.label("paid_amount"),
            payment_summary.c.last_payment_at,
            func.coalesce(notes_summary.c.notes_count, 0).label("notes_count"),
            payment_status_expr,
            saldo_expr,
        )
        .outerjoin(payment_summary, payment_summary.c.avviso_id == RuoloAvviso.id)
        .outerjoin(RuoloTributiAvvisoStatus, RuoloTributiAvvisoStatus.avviso_id == RuoloAvviso.id)
        .outerjoin(notes_summary, notes_summary.c.avviso_id == RuoloAvviso.id)
    )
    return query, paid_amount_expr, payment_status_expr


def list_tributi_avvisi(
    db: Session,
    *,
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = None,
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    payment_status: str | None = None,
    workflow_status: str | None = None,
    open_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    query, paid_amount_expr, payment_status_expr = _base_tributi_query()

    if anno is not None:
        query = query.where(RuoloAvviso.anno_tributario == anno)
    if subject_id:
        try:
            query = query.where(RuoloAvviso.subject_id == uuid.UUID(subject_id))
        except ValueError:
            query = query.where(literal(False))
    if q:
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                RuoloAvviso.codice_cnc.ilike(search_term),
                func.coalesce(RuoloAvviso.nominativo_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_fiscale_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_utenza, "").ilike(search_term),
                cast(RuoloAvviso.anno_tributario, String).ilike(search_term),
                RuoloAvviso.id.in_(
                    select(RuoloPartita.avviso_id).where(
                        func.coalesce(RuoloPartita.comune_nome, "").ilike(search_term)
                    )
                ),
            )
        )
    if codice_fiscale:
        query = query.where(func.coalesce(RuoloAvviso.codice_fiscale_raw, "").ilike(f"%{codice_fiscale}%"))
    if comune:
        query = query.where(
            RuoloAvviso.id.in_(
                select(RuoloPartita.avviso_id).where(
                    func.coalesce(RuoloPartita.comune_nome, "").ilike(f"%{comune}%")
                )
            )
        )
    if codice_utenza:
        query = query.where(RuoloAvviso.codice_utenza == codice_utenza)
    if unlinked:
        query = query.where(RuoloAvviso.subject_id.is_(None))
    if payment_status:
        query = query.where(payment_status_expr == payment_status)
    if workflow_status:
        query = query.where(RuoloTributiAvvisoStatus.workflow_status == workflow_status)
    if open_only:
        query = query.where(
            or_(
                RuoloAvviso.importo_totale_euro.is_(None),
                paid_amount_expr < RuoloAvviso.importo_totale_euro,
            )
        )

    query = query.order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.nominativo_raw)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [_row_to_tributi_item(db, row) for row in rows], total


def get_tributi_avviso(db: Session, avviso_id: uuid.UUID) -> dict[str, Any] | None:
    query, _, _ = _base_tributi_query()
    row = db.execute(query.where(RuoloAvviso.id == avviso_id)).one_or_none()
    if row is None:
        return None
    item = _row_to_tributi_item(db, row)
    item["payments"] = list_payments(db, avviso_id)
    item["notes"] = list_notes(db, avviso_id)
    return item


def _row_to_tributi_item(db: Session, row: Any) -> dict[str, Any]:
    avviso: RuoloAvviso = row[0]
    status: RuoloTributiAvvisoStatus | None = row[1]
    paid_amount = _money_or_zero(row[2])
    derived_status, saldo = derive_payment_status(
        due_amount=avviso.importo_totale_euro,
        paid_amount=paid_amount,
    )
    return {
        "avviso": avviso,
        "paid_amount": _money_float(paid_amount) or 0.0,
        "saldo_amount": _money_float(saldo),
        "payment_status": derived_status,
        "workflow_status": status.workflow_status if status else None,
        "last_payment_at": row[3],
        "capacitas_url": status.capacitas_url if status else None,
        "capacitas_avviso_code": status.capacitas_avviso_code if status else None,
        "display_name": _get_subject_display_name(db, avviso.subject_id),
        "is_linked": avviso.subject_id is not None,
        "notes_count": int(row[4] or 0),
    }


def list_payments(db: Session, avviso_id: uuid.UUID) -> list[RuoloTributiPayment]:
    return list(
        db.scalars(
            select(RuoloTributiPayment)
            .where(RuoloTributiPayment.avviso_id == avviso_id)
            .order_by(RuoloTributiPayment.paid_at.desc().nullslast(), RuoloTributiPayment.created_at.desc())
        ).all()
    )


def list_notes(db: Session, avviso_id: uuid.UUID) -> list[RuoloTributiNote]:
    return list(
        db.scalars(
            select(RuoloTributiNote)
            .where(RuoloTributiNote.avviso_id == avviso_id)
            .order_by(RuoloTributiNote.created_at.desc())
        ).all()
    )


def create_payment(
    db: Session,
    *,
    avviso: RuoloAvviso,
    amount: float,
    paid_at: Any = None,
    payment_reference: str | None = None,
    payment_method: str | None = None,
    source: str = "manual",
    status: str = RuoloTributiPaymentRecordStatus.VALID.value,
    raw_payload_json: dict[str, Any] | None = None,
    created_by: int | None = None,
) -> RuoloTributiPayment:
    payment = RuoloTributiPayment(
        avviso_id=avviso.id,
        codice_cnc_raw=avviso.codice_cnc,
        codice_utenza_raw=avviso.codice_utenza,
        anno_tributario=avviso.anno_tributario,
        paid_at=paid_at,
        amount=amount,
        payment_reference=payment_reference,
        payment_method=payment_method,
        source=source,
        status=status,
        raw_payload_json=raw_payload_json,
        created_by=created_by,
    )
    db.add(payment)
    db.flush()
    refresh_avviso_status_summary(db, avviso, updated_by=created_by)
    return payment


def add_note(
    db: Session,
    *,
    avviso_id: uuid.UUID,
    body: str,
    visibility: str = "internal",
    created_by: int | None = None,
) -> RuoloTributiNote:
    note = RuoloTributiNote(
        avviso_id=avviso_id,
        body=body,
        visibility=visibility,
        created_by=created_by,
    )
    db.add(note)
    db.flush()
    return note


def update_avviso_status(
    db: Session,
    *,
    avviso: RuoloAvviso,
    workflow_status: str | None,
    capacitas_url: str | None,
    capacitas_avviso_code: str | None,
    updated_by: int | None = None,
) -> RuoloTributiAvvisoStatus:
    if capacitas_url and not capacitas_url.startswith(("http://", "https://")):
        raise ValueError("capacitas_url deve essere una URL http/https")

    status = db.execute(
        select(RuoloTributiAvvisoStatus).where(RuoloTributiAvvisoStatus.avviso_id == avviso.id)
    ).scalar_one_or_none()
    if status is None:
        status = RuoloTributiAvvisoStatus(avviso_id=avviso.id)
        db.add(status)

    payment_status, saldo = _current_payment_summary(db, avviso)
    status.payment_status = payment_status
    status.saldo_amount = _money_float(saldo)
    status.last_payment_at = _last_valid_payment_at(db, avviso.id)
    status.workflow_status = workflow_status
    status.capacitas_url = capacitas_url
    status.capacitas_avviso_code = capacitas_avviso_code
    status.updated_by = updated_by
    db.flush()
    return status


def refresh_avviso_status_summary(
    db: Session,
    avviso: RuoloAvviso,
    *,
    updated_by: int | None = None,
) -> RuoloTributiAvvisoStatus:
    status = db.execute(
        select(RuoloTributiAvvisoStatus).where(RuoloTributiAvvisoStatus.avviso_id == avviso.id)
    ).scalar_one_or_none()
    if status is None:
        status = RuoloTributiAvvisoStatus(avviso_id=avviso.id)
        db.add(status)

    payment_status, saldo = _current_payment_summary(db, avviso)
    status.payment_status = payment_status
    status.saldo_amount = _money_float(saldo)
    status.last_payment_at = _last_valid_payment_at(db, avviso.id)
    status.updated_by = updated_by
    db.flush()
    return status


def _current_payment_summary(db: Session, avviso: RuoloAvviso) -> tuple[str, Decimal | None]:
    paid_amount = db.scalar(
        select(func.coalesce(func.sum(RuoloTributiPayment.amount), 0)).where(
            RuoloTributiPayment.avviso_id == avviso.id,
            RuoloTributiPayment.status == RuoloTributiPaymentRecordStatus.VALID.value,
        )
    )
    return derive_payment_status(due_amount=avviso.importo_totale_euro, paid_amount=paid_amount)


def _last_valid_payment_at(db: Session, avviso_id: uuid.UUID):
    return db.scalar(
        select(func.max(RuoloTributiPayment.paid_at)).where(
            RuoloTributiPayment.avviso_id == avviso_id,
            RuoloTributiPayment.status == RuoloTributiPaymentRecordStatus.VALID.value,
        )
    )


def list_reminders(db: Session, avviso_id: uuid.UUID) -> list[RuoloTributiReminder]:
    return list(
        db.scalars(
            select(RuoloTributiReminder)
            .where(RuoloTributiReminder.avviso_id == avviso_id)
            .order_by(RuoloTributiReminder.created_at.desc())
        ).all()
    )


def get_reminder(db: Session, reminder_id: uuid.UUID) -> RuoloTributiReminder | None:
    return db.get(RuoloTributiReminder, reminder_id)


def create_generated_reminder(
    db: Session,
    *,
    avviso: RuoloAvviso,
    template_id: uuid.UUID | None = None,
    notes: str | None = None,
    generated_by: int | None = None,
) -> RuoloTributiReminder:
    tributi_item = get_tributi_avviso(db, avviso.id)
    if tributi_item is None:  # pragma: no cover - guarded by caller and DB FK.
        raise ValueError("Avviso tributi non trovato")

    generated_at = datetime.now(timezone.utc)
    payload = build_reminder_payload(
        avviso_id=avviso.id,
        codice_cnc=avviso.codice_cnc,
        anno_tributario=avviso.anno_tributario,
        nominativo=tributi_item["display_name"] or avviso.nominativo_raw,
        codice_fiscale=avviso.codice_fiscale_raw,
        codice_utenza=avviso.codice_utenza,
        domicilio=avviso.domicilio_raw,
        residenza=avviso.residenza_raw,
        importo_totale=avviso.importo_totale_euro,
        paid_amount=tributi_item["paid_amount"],
        saldo_amount=tributi_item["saldo_amount"],
        generated_at=generated_at,
    )
    reminder = RuoloTributiReminder(
        avviso_id=avviso.id,
        template_id=template_id,
        status="generated",
        generated_at=generated_at,
        generated_by=generated_by,
        payload_json=payload,
        notes=notes,
    )
    db.add(reminder)
    db.flush()

    filename = build_reminder_filename(
        codice_cnc=avviso.codice_cnc,
        anno_tributario=avviso.anno_tributario,
        reminder_id=reminder.id,
    )
    output_path = reminder_storage_dir() / filename
    generate_reminder_docx(payload, output_path=output_path)
    reminder.generated_document_path = str(output_path)
    db.flush()
    return reminder


def reminder_document_path(reminder: RuoloTributiReminder) -> Path | None:
    if not reminder.generated_document_path:
        return None
    path = Path(reminder.generated_document_path)
    if not path.exists() or not path.is_file():
        return None
    return path
