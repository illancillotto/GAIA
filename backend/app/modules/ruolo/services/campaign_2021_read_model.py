"""Exact-number read-only adapter. No CF fallback, materialisation or ledger updates."""

from sqlalchemy import select
from sqlalchemy.orm import defer

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.services.notice_eligibility import (
    _ambiguous_history,
    _step_assigned_avviso_ids,
)
from app.modules.ruolo.services.notice_import_excel import digest, json_bytes
from app.modules.ruolo.tributi_policy_repository import get_calculation_policy_for_year
from app.modules.utenze.models import AnagraficaPaymentNotice

ACCOUNTING = (
    "importo_carico",
    "importo_residuo",
    "importo_riscosso",
    "importo_sgravio",
    "importo_annullato",
    "importo_rateizzato",
    "importo_riporto",
)
ENGINE = (
    "principal_saldo_amount",
    "paid_amount",
    "surcharge_amount",
    "interest_amount",
    "saldo_amount",
    "adjusted_due_amount",
    "calculation_date",
    "interest_start_date",
    "interest_start_source",
    "payment_status",
    "workflow_status",
    "calculation_policy",
    "capacitas_avviso_code",
)


def history(db, avviso_id) -> list[dict]:
    rows = db.execute(
        select(NoticePosition, NoticeDocument, NoticeNotification, NoticeRecovery)
        .join(NoticeDocument, NoticePosition.document_id == NoticeDocument.id)
        .outerjoin(NoticeNotification, NoticeNotification.document_id == NoticeDocument.id)
        .outerjoin(NoticeRecovery, NoticeRecovery.position_id == NoticePosition.id)
        .where(NoticePosition.avviso_id == avviso_id, NoticeDocument.reconciled_into_id.is_(None))
        .order_by(NoticeDocument.id, NoticePosition.id)
    ).all()
    result = []
    for position, document, notification, recovery in rows:
        evidence = (
            db.get(NoticeEvidence, notification.evidence_id)
            if notification and notification.evidence_id
            else None
        )
        attempts = db.scalars(
            select(NoticeAttempt)
            .where(NoticeAttempt.document_id == document.id)
            .order_by(NoticeAttempt.id)
        ).all()
        result.append(
            {
                "document_id": str(document.id),
                "version": document.version,
                "source": document.source_system,
                "number": document.document_number,
                "tax_code": document.tax_code,
                "year": position.tax_year,
                "notification": notification.state if notification else "da_verificare",
                "notified_on": str(notification.notified_on)
                if notification and notification.notified_on
                else None,
                "evidence": evidence.reference if evidence else None,
                "recovery": recovery.state if recovery else "da_verificare",
                "recovery_reference": recovery.evidence_reference if recovery else None,
                "attempts": [
                    {
                        "id": str(a.id),
                        "channel": a.channel,
                        "tracking": a.tracking_code,
                        "sent_at": str(a.sent_at),
                    }
                    for a in attempts
                ],
            }
        )
    return result


def _partitario_snapshot(db, notice, avviso_id) -> dict:
    detail = notice.raw_detail_json
    partite = repo._partite_payload(db, avviso_id)
    result = {
        "partitario_available": bool(partite)
        or (isinstance(detail, dict) and bool(detail.get("partitario"))),
        "detail_sha256": digest(json_bytes(detail)),
        "partite_sha256": digest(json_bytes(partite)),
    }
    db.expire(notice, ["raw_detail_json"])
    return result


def _matched(db, row, notice, avviso) -> dict:
    # Existing motor is observed at its own calculation date and retained as a snapshot.
    # A mismatch of its selected source is a blocker in reconciliation, never a fallback.
    item = repo.get_tributi_avviso(db, avviso.id)
    policy = get_calculation_policy_for_year(db, 2021)
    result = {
        "number": notice.source_notice_id,
        "avviso_id": str(avviso.id),
        "incass_id": str(notice.id),
        "tax_code": notice.codice_fiscale or notice.partita_iva,
        "name": notice.display_name,
        "ruolo_tax_code": avviso.codice_fiscale_raw,
        "ruolo_name": avviso.nominativo_raw,
        "year": notice.anno,
        "synced_at": str(notice.synced_at) if notice.synced_at else None,
        "source_updated_at": str(notice.updated_at),
        "recipient": {
            key: getattr(avviso, key) for key in ("domicilio_raw", "residenza_raw", "codice_utenza")
        },
        **_partitario_snapshot(db, notice, avviso.id),
        "status": notice.stato_label,
        "last_delivery": notice.ultimo_invio,
        "accounting": {key: getattr(notice, key) for key in ACCOUNTING},
        "engine": {key: str(item[key]) if item[key] is not None else None for key in ENGINE},
        "policy": {c.name: str(getattr(policy, c.name)) for c in policy.__table__.columns}
        if policy
        else None,
        "print_policy": repo._notice_print_policy_payload(db, [2021]),
        "history": history(db, avviso.id),
        "ambiguous_history": _ambiguous_history(db, avviso),
        "step_assigned": avviso.id in _step_assigned_avviso_ids(db),
        "pec_documented": item["incass_notice"].get("documented_pec_delivery", False),
        "mailing_delivery": item["mailing_delivery"],
        "tributes": {
            key: str(getattr(avviso, f"importo_totale_{key}")) for key in ("0648", "0668", "0985")
        },
    }
    return result


def read_positions(db, rows: list[dict]) -> dict[str, dict]:
    numbers = {row["number"] for row in rows}
    notices = db.scalars(
        select(AnagraficaPaymentNotice)
        .options(
            defer(AnagraficaPaymentNotice.raw_detail_json),
            defer(AnagraficaPaymentNotice.detail_info_html),
            defer(AnagraficaPaymentNotice.detail_info_text),
        )
        .where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.source_notice_id.in_(numbers),
        )
    ).all()
    by_number = {notice.source_notice_id: notice for notice in notices}
    avvisi = db.scalars(select(RuoloAvviso).where(RuoloAvviso.anno_tributario == 2021)).all()
    by_prefix = {}
    for avviso in avvisi:
        by_prefix.setdefault(avviso.codice_cnc.removeprefix("01."), []).append(avviso)
    results = {}
    for row in rows:
        notice = by_number.get(row["number"])
        matches = by_prefix.get(row["number"][:-1], [])
        if notice is None or len(matches) != 1:
            result = {
                "match_error": "numero_incass_assente"
                if notice is None
                else "numero_ruolo_assente_o_ambiguo"
            }
        else:
            result = _matched(db, row, notice, matches[0])
        results[row["number"]] = {**result, "sha256": digest(json_bytes(result))}
    return results
