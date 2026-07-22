from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import String, case, cast, desc, func, literal, or_, select
from sqlalchemy.orm import Session

from app.modules.ruolo.enums import (
    RuoloTributiPaymentRecordStatus,
    RuoloTributiPaymentStatus,
)
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloPartita,
    RuoloParticella,
    RuoloTributiAvvisoStatus,
    RuoloTributiNote,
    RuoloTributiPayment,
    RuoloTributiReminder,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.repositories import _get_subject_display_name
from app.modules.ruolo.services.tributi_reminder_service import (
    build_batch_reminder_filename,
    build_reminder_filename,
    build_reminder_payload,
    generate_batch_reminder_pdf,
    generate_reminder_docx,
    reminder_storage_dir,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject


_CURRENCY_ZERO = Decimal("0.00")
DEFAULT_BATCH_TEMPLATE_PATH = str(
    Path(__file__).resolve().parent
    / "templates"
    / "Avviso_Sollecito_22.23_R1_da_mail_ordinarie.docx"
)


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


def _normalise_tax_code(value: str | None) -> str:
    return "".join(ch for ch in (value or "").upper().strip() if ch.isalnum())


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

    query = query.order_by(
        RuoloAvviso.importo_totale_euro.desc().nullslast(),
        RuoloAvviso.anno_tributario.desc(),
        RuoloAvviso.nominativo_raw,
    )
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
    incass_notice = _load_incass_notice_link(
        db,
        avviso,
        preferred_notice_id=status.capacitas_avviso_code if status else None,
    )
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
        "capacitas_url": (status.capacitas_url if status else None) or incass_notice["detail_url"],
        "capacitas_avviso_code": (status.capacitas_avviso_code if status else None) or incass_notice["source_notice_id"],
        "mailing_delivery": incass_notice["mailing_delivery"],
        "display_name": _get_subject_display_name(db, avviso.subject_id),
        "is_linked": avviso.subject_id is not None,
        "notes_count": int(row[4] or 0),
    }


def _load_incass_notice_link(
    db: Session,
    avviso: RuoloAvviso,
    *,
    preferred_notice_id: str | None = None,
) -> dict[str, Any]:
    normalized_tax_code = _normalise_tax_code(avviso.codice_fiscale_raw)
    if not normalized_tax_code:
        return {"detail_url": None, "source_notice_id": None, "mailing_delivery": None}

    normalized_notice_tax = func.upper(
        func.replace(
            func.coalesce(AnagraficaPaymentNotice.codice_fiscale, AnagraficaPaymentNotice.partita_iva, ""),
            " ",
            "",
        )
    )
    base_stmt = (
        select(
            AnagraficaPaymentNotice.source_notice_id,
            AnagraficaPaymentNotice.detail_url,
            AnagraficaPaymentNotice.raw_detail_json,
        )
        .where(
            AnagraficaPaymentNotice.anno == str(avviso.anno_tributario),
            AnagraficaPaymentNotice.source_system == "incass",
            normalized_notice_tax == normalized_tax_code,
            AnagraficaPaymentNotice.detail_url.is_not(None),
        )
    )
    notice_row = None
    if preferred_notice_id:
        notice_row = db.execute(
            base_stmt.where(AnagraficaPaymentNotice.source_notice_id == preferred_notice_id).limit(1)
        ).mappings().first()
    if notice_row is None:
        notice_row = db.execute(
            base_stmt.order_by(desc(AnagraficaPaymentNotice.updated_at)).limit(1)
        ).mappings().first()
    if notice_row is None:
        return {"detail_url": None, "source_notice_id": None, "mailing_delivery": None}
    return {
        "detail_url": notice_row["detail_url"],
        "source_notice_id": notice_row["source_notice_id"],
        "mailing_delivery": _extract_incass_mailing_delivery(
            source_notice_id=notice_row["source_notice_id"],
            raw_detail_json=notice_row["raw_detail_json"],
        ),
    }


def _extract_incass_mailing_delivery(
    *,
    source_notice_id: str | None,
    raw_detail_json: dict | list | None,
) -> dict[str, Any] | None:
    if not isinstance(raw_detail_json, dict):
        return None
    mailing_list = raw_detail_json.get("mailing_list")
    if not isinstance(mailing_list, dict):
        return None
    shipments = mailing_list.get("shipments")
    if not isinstance(shipments, list):
        return None
    parents_by_shipment = mailing_list.get("receipt_parents_by_shipment_id")
    if not isinstance(parents_by_shipment, dict):
        parents_by_shipment = {}
    documents_by_parent = mailing_list.get("receipt_documents_by_parent_id")
    if not isinstance(documents_by_parent, dict):
        documents_by_parent = {}

    fallback: dict[str, Any] | None = None
    for shipment in shipments:
        if not isinstance(shipment, dict):
            continue
        shipment_id = str(shipment.get("external_id") or "")
        parents = parents_by_shipment.get(shipment_id) if shipment_id else None
        if not isinstance(parents, list):
            parents = []
        receipt_groups = [
            str(parent.get("group"))
            for parent in parents
            if isinstance(parent, dict) and parent.get("group")
        ]
        delivered_parent = _find_receipt_parent(parents, "CONSEGNA")
        accepted_parent = _find_receipt_parent(parents, "ACCETTAZIONE")
        receipt_documents_count = sum(
            len(documents)
            for parent in parents
            if isinstance(parent, dict)
            for documents in [documents_by_parent.get(parent.get("parent_id"))]
            if isinstance(documents, list)
        )
        status_label = shipment.get("status_label")
        status_text = str(status_label or "")
        payload = {
            "source_notice_id": source_notice_id,
            "pec_recipient": shipment.get("recipient"),
            "delivery_status": status_label,
            "delivered_at": delivered_parent.get("date") if delivered_parent else shipment.get("event_at"),
            "accepted_at": accepted_parent.get("date") if accepted_parent else None,
            "receipt_groups": receipt_groups,
            "receipt_documents_count": receipt_documents_count,
        }
        if delivered_parent or "consegna" in status_text.lower():
            return payload
        fallback = fallback or payload
    return fallback


def _find_receipt_parent(parents: list[object], group: str) -> dict[str, Any] | None:
    for parent in parents:
        if not isinstance(parent, dict):
            continue
        if str(parent.get("group") or "").strip().upper() == group:
            return parent
    return None


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


def list_reminder_candidates(
    db: Session,
    *,
    anno_from: int | None = None,
    anno_to: int | None = None,
    q: str | None = None,
    comune: str | None = None,
    codice_fiscale: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    candidates = _collect_reminder_candidates(
        db,
        anno_from=anno_from,
        anno_to=anno_to,
        q=q,
        comune=comune,
        codice_fiscale=codice_fiscale,
    )
    total = len(candidates)
    start = (page - 1) * page_size
    return candidates[start : start + page_size], total


def create_reminder_batch(
    db: Session,
    *,
    title: str | None,
    codice_fiscale: list[str],
    filters: dict[str, Any] | None,
    template_path: str | None,
    notes: str | None,
    generated_by: int | None,
) -> RuoloTributiReminderBatch:
    selected_cf = [_normalise_tax_code(value) for value in codice_fiscale if _normalise_tax_code(value)]
    filters = filters or {}
    candidates = _collect_reminder_candidates(
        db,
        anno_from=_int_or_none(filters.get("anno_from")),
        anno_to=_int_or_none(filters.get("anno_to")),
        q=str(filters.get("q") or "").strip() or None,
        comune=str(filters.get("comune") or "").strip() or None,
        codice_fiscale=selected_cf or None,
    )
    if selected_cf:
        selected_set = set(selected_cf)
        candidates = [candidate for candidate in candidates if candidate["codice_fiscale"] in selected_set]
    if not candidates:
        raise ValueError("Nessuna utenza morosa selezionabile per il batch")

    generated_at = datetime.now(timezone.utc)
    batch = RuoloTributiReminderBatch(
        title=title,
        status="running",
        template_path=template_path or DEFAULT_BATCH_TEMPLATE_PATH,
        filters_json=filters,
        items_total=len(candidates),
        items_generated=0,
        items_failed=0,
        generated_by=generated_by,
        generated_at=generated_at,
        notes=notes,
    )
    db.add(batch)
    db.flush()

    for candidate in candidates:
        item = _create_batch_item(
            db,
            batch=batch,
            candidate=candidate,
            template_path=batch.template_path,
            generated_at=generated_at,
        )
        if item.status == "generated":
            batch.items_generated += 1
        elif item.status == "failed":
            batch.items_failed += 1

    if batch.items_failed == 0:
        batch.status = "generated"
    elif batch.items_generated == 0:
        batch.status = "failed"
    else:
        batch.status = "partial_failed"
    db.flush()
    return batch


def list_reminder_batches(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RuoloTributiReminderBatch], int]:
    query = select(RuoloTributiReminderBatch).order_by(RuoloTributiReminderBatch.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def get_reminder_batch(db: Session, batch_id: uuid.UUID) -> RuoloTributiReminderBatch | None:
    return db.get(RuoloTributiReminderBatch, batch_id)


def list_reminder_batch_items(db: Session, batch_id: uuid.UUID) -> list[RuoloTributiReminderBatchItem]:
    return list(
        db.scalars(
            select(RuoloTributiReminderBatchItem)
            .where(RuoloTributiReminderBatchItem.batch_id == batch_id)
            .order_by(
                RuoloTributiReminderBatchItem.display_name,
                RuoloTributiReminderBatchItem.comune_key,
                RuoloTributiReminderBatchItem.codice_fiscale,
            )
        ).all()
    )


def get_reminder_batch_item(db: Session, item_id: uuid.UUID) -> RuoloTributiReminderBatchItem | None:
    return db.get(RuoloTributiReminderBatchItem, item_id)


def reminder_batch_item_document_path(item: RuoloTributiReminderBatchItem) -> Path | None:
    if not item.generated_document_path:
        return None
    path = Path(item.generated_document_path)
    if not path.exists() or not path.is_file():
        return None
    return path


def _collect_reminder_candidates(
    db: Session,
    *,
    anno_from: int | None,
    anno_to: int | None,
    q: str | None,
    comune: str | None,
    codice_fiscale: list[str] | None,
) -> list[dict[str, Any]]:
    query, paid_amount_expr, payment_status_expr = _base_tributi_query()
    query = query.where(func.coalesce(RuoloAvviso.codice_fiscale_raw, "") != "")
    query = query.where(
        or_(
            RuoloAvviso.importo_totale_euro.is_(None),
            paid_amount_expr < RuoloAvviso.importo_totale_euro,
        )
    )
    if anno_from is not None:
        query = query.where(RuoloAvviso.anno_tributario >= anno_from)
    if anno_to is not None:
        query = query.where(RuoloAvviso.anno_tributario <= anno_to)
    if q:
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                func.coalesce(RuoloAvviso.nominativo_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_fiscale_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_utenza, "").ilike(search_term),
                RuoloAvviso.id.in_(
                    select(RuoloPartita.avviso_id).where(
                        func.coalesce(RuoloPartita.comune_nome, "").ilike(search_term)
                    )
                ),
            )
        )
    if comune:
        query = query.where(
            RuoloAvviso.id.in_(
                select(RuoloPartita.avviso_id).where(
                    func.coalesce(RuoloPartita.comune_nome, "").ilike(f"%{comune}%")
                )
            )
        )
    if codice_fiscale:
        cf_values = [_normalise_tax_code(value) for value in codice_fiscale if _normalise_tax_code(value)]
        if cf_values:
            query = query.where(func.upper(RuoloAvviso.codice_fiscale_raw).in_(cf_values))
    query = query.order_by(RuoloAvviso.nominativo_raw, RuoloAvviso.anno_tributario, payment_status_expr)

    grouped: dict[str, dict[str, Any]] = {}
    for row in db.execute(query).all():
        item = _row_to_tributi_item(db, row)
        avviso: RuoloAvviso = item["avviso"]
        tax_code = _normalise_tax_code(avviso.codice_fiscale_raw)
        if not tax_code:
            continue
        group = grouped.setdefault(
            tax_code,
            {
                "codice_fiscale": tax_code,
                "display_name": item["display_name"] or avviso.nominativo_raw,
                "comune": None,
                "years": set(),
                "avvisi_count": 0,
                "due_amount": Decimal("0.00"),
                "paid_amount": Decimal("0.00"),
                "saldo_amount": Decimal("0.00"),
                "subject_id": avviso.subject_id,
                "nas_folder_path": None,
                "has_nas_folder": False,
                "avvisi": [],
            },
        )
        if group["subject_id"] is None and avviso.subject_id is not None:
            group["subject_id"] = avviso.subject_id
        group["years"].add(avviso.anno_tributario)
        group["avvisi_count"] += 1
        group["due_amount"] += _money_or_zero(avviso.importo_totale_euro)
        group["paid_amount"] += _money_or_zero(item["paid_amount"])
        group["saldo_amount"] += _money_or_zero(item["saldo_amount"])
        avviso_comune = _first_avviso_comune(db, avviso.id)
        if group["comune"] is None and avviso_comune:
            group["comune"] = avviso_comune
        group["avvisi"].append(
            {
                "id": avviso.id,
                "codice_cnc": avviso.codice_cnc,
                "anno_tributario": avviso.anno_tributario,
                "nominativo_raw": avviso.nominativo_raw,
                "domicilio_raw": avviso.domicilio_raw,
                "residenza_raw": avviso.residenza_raw,
                "codice_utenza": avviso.codice_utenza,
                "importo_totale_0648": _money_float(_money(avviso.importo_totale_0648)),
                "importo_totale_0985": _money_float(_money(avviso.importo_totale_0985)),
                "importo_totale_0668": _money_float(_money(avviso.importo_totale_0668)),
                "importo_totale_euro": _money_float(_money(avviso.importo_totale_euro)),
                "paid_amount": item["paid_amount"],
                "saldo_amount": item["saldo_amount"],
                "payment_status": item["payment_status"],
                "capacitas_url": item["capacitas_url"],
            }
        )

    candidates = []
    for group in grouped.values():
        subject_id, nas_folder_path = _resolve_subject_archive(db, group["codice_fiscale"], group["subject_id"])
        group["subject_id"] = subject_id
        group["nas_folder_path"] = nas_folder_path
        group["has_nas_folder"] = bool(nas_folder_path)
        group["years"] = sorted(group["years"])
        group["due_amount"] = _money_float(group["due_amount"])
        group["paid_amount"] = _money_float(group["paid_amount"]) or 0.0
        group["saldo_amount"] = _money_float(group["saldo_amount"])
        candidates.append(group)

    candidates.sort(key=lambda value: ((value["display_name"] or "").lower(), (value["comune"] or "").lower(), value["codice_fiscale"]))
    return candidates


def _create_batch_item(
    db: Session,
    *,
    batch: RuoloTributiReminderBatch,
    candidate: dict[str, Any],
    template_path: str | None,
    generated_at: datetime,
) -> RuoloTributiReminderBatchItem:
    avviso_ids = [str(avviso["id"]) for avviso in candidate["avvisi"]]
    item = RuoloTributiReminderBatchItem(
        batch_id=batch.id,
        subject_id=candidate["subject_id"],
        codice_fiscale=candidate["codice_fiscale"],
        display_name=candidate["display_name"],
        comune_key=candidate["comune"],
        years_json=candidate["years"],
        avviso_ids_json=avviso_ids,
        due_amount=candidate["due_amount"],
        paid_amount=candidate["paid_amount"],
        saldo_amount=candidate["saldo_amount"],
        nas_folder_path=candidate["nas_folder_path"],
        status="pending",
    )
    db.add(item)
    db.flush()

    if not candidate["nas_folder_path"]:
        item.status = "failed"
        item.error_detail = "Cartella archivio NAS mancante per l'utenza"
        db.flush()
        return item

    filename = build_batch_reminder_filename(codice_fiscale=candidate["codice_fiscale"], years=candidate["years"])
    output_path = Path(candidate["nas_folder_path"]) / "solleciti" / filename
    payload = _build_batch_item_payload(db, candidate, template_path=template_path, generated_at=generated_at)
    item.payload_json = payload
    try:
        generate_batch_reminder_pdf(payload, output_path=output_path)
    except Exception as exc:
        item.status = "failed"
        item.error_detail = str(exc)
    else:
        item.status = "generated"
        item.generated_document_path = str(output_path)
    db.flush()
    return item


def _build_batch_item_payload(
    db: Session,
    candidate: dict[str, Any],
    *,
    template_path: str | None,
    generated_at: datetime,
) -> dict[str, Any]:
    avvisi_payload = []
    for avviso_summary in candidate["avvisi"]:
        avviso_id = avviso_summary["id"]
        avvisi_payload.append(
            {
                **{key: str(value) if isinstance(value, uuid.UUID) else value for key, value in avviso_summary.items()},
                "partite": _partite_payload(db, avviso_id),
            }
        )
    return {
        "codice_fiscale": candidate["codice_fiscale"],
        "display_name": candidate["display_name"],
        "comune": candidate["comune"],
        "years": candidate["years"],
        "due_amount": _format_money_for_payload(candidate["due_amount"]),
        "paid_amount": _format_money_for_payload(candidate["paid_amount"]),
        "saldo_amount": _format_money_for_payload(candidate["saldo_amount"]),
        "template_path": template_path,
        "generated_at": generated_at.isoformat(),
        "avvisi": avvisi_payload,
    }


def _partite_payload(db: Session, avviso_id: uuid.UUID) -> list[dict[str, Any]]:
    partite = db.scalars(
        select(RuoloPartita).where(RuoloPartita.avviso_id == avviso_id).order_by(RuoloPartita.comune_nome, RuoloPartita.codice_partita)
    ).all()
    return [
        {
            "codice_partita": partita.codice_partita,
            "comune_nome": partita.comune_nome,
            "contribuente_cf": partita.contribuente_cf,
            "importo_0648": _format_money_for_payload(partita.importo_0648),
            "importo_0985": _format_money_for_payload(partita.importo_0985),
            "importo_0668": _format_money_for_payload(partita.importo_0668),
            "particelle": [
                {
                    "domanda_irrigua": particella.domanda_irrigua,
                    "distretto": particella.distretto,
                    "foglio": particella.foglio,
                    "particella": particella.particella,
                    "subalterno": particella.subalterno,
                    "sup_catastale_ha": _decimal_string(particella.sup_catastale_ha),
                    "sup_irrigata_ha": _decimal_string(particella.sup_irrigata_ha),
                    "coltura": particella.coltura,
                    "importo_manut": _format_money_for_payload(particella.importo_manut),
                    "importo_irrig": _format_money_for_payload(particella.importo_irrig),
                    "importo_ist": _format_money_for_payload(particella.importo_ist),
                }
                for particella in db.scalars(
                    select(RuoloParticella)
                    .where(RuoloParticella.partita_id == partita.id)
                    .order_by(RuoloParticella.foglio, RuoloParticella.particella)
                ).all()
            ],
        }
        for partita in partite
    ]


def _resolve_subject_archive(
    db: Session,
    codice_fiscale: str,
    subject_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, str | None]:
    if subject_id is not None:
        subject = db.get(AnagraficaSubject, subject_id)
        if subject is not None and subject.nas_folder_path:
            return subject.id, subject.nas_folder_path

    person_subject_id = db.scalar(
        select(AnagraficaPerson.subject_id).where(func.upper(AnagraficaPerson.codice_fiscale) == codice_fiscale)
    )
    if person_subject_id is not None:
        subject = db.get(AnagraficaSubject, person_subject_id)
        if subject is not None:
            return subject.id, subject.nas_folder_path

    company_subject_id = db.scalar(
        select(AnagraficaCompany.subject_id).where(
            or_(
                func.upper(AnagraficaCompany.codice_fiscale) == codice_fiscale,
                func.upper(AnagraficaCompany.partita_iva) == codice_fiscale,
            )
        )
    )
    if company_subject_id is not None:
        subject = db.get(AnagraficaSubject, company_subject_id)
        if subject is not None:
            return subject.id, subject.nas_folder_path
    return subject_id, None


def _first_avviso_comune(db: Session, avviso_id: uuid.UUID) -> str | None:
    return db.scalar(
        select(RuoloPartita.comune_nome).where(RuoloPartita.avviso_id == avviso_id).order_by(RuoloPartita.comune_nome).limit(1)
    )


def _format_money_for_payload(value: Any) -> str | None:
    amount = _money(value)
    if amount is None:
        return None
    return f"{amount} EUR"


def _decimal_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def reminder_document_path(reminder: RuoloTributiReminder) -> Path | None:
    if not reminder.generated_document_path:
        return None
    path = Path(reminder.generated_document_path)
    if not path.exists() or not path.is_file():
        return None
    return path
