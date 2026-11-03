"""Adapt an approved accounting snapshot to the existing GAIA renderer."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from pypdf import PdfReader
from sqlalchemy import select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.services.campaign_2021_excel import money
from app.modules.ruolo.services.campaign_2021_reconciliation import amount
from app.modules.ruolo.services.notice_preview import marked_pdf
from app.modules.ruolo.services.tributi_reminder_service import (
    GAIA_PROPOSAL_TEMPLATE_KEY,
    generate_batch_reminder_pdf,
    notice_total_amount,
)
from app.modules.utenze.models import AnagraficaPaymentNotice


def build_payload(db, row, facts, approval, approved_at):
    avviso_id = UUID(facts["avviso_id"])
    avviso = db.get(RuoloAvviso, avviso_id)
    notice = db.scalar(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.id == UUID(facts["incass_id"])
        )
    )
    source = row["amounts"]
    engine = facts["engine"]
    selected = (
        source
        if approval.amount_source == "excel"
        else {
            "surcharge": engine["surcharge_amount"],
            "interest": engine["interest_amount"],
            "total": engine["saldo_amount"],
        }
    )
    paid = str(abs(amount(facts["accounting"]["importo_riscosso"])))
    partitario = (notice.raw_detail_json or {}).get("partitario")
    # F-J is kept separate from the actual inCASS receipts, including in the printed table.
    detail = {
        "id": str(avviso_id),
        "codice_cnc": row["number"],
        "anno_tributario": 2021,
        "nominativo_raw": row["name"],
        "domicilio_raw": avviso.domicilio_raw,
        "residenza_raw": avviso.residenza_raw,
        "codice_utenza": avviso.codice_utenza,
        **{f"importo_totale_{k}": source[k] for k in ("0648", "0668", "0985")},
        "paid_amount": paid,
        "saldo_amount": selected["total"],
        "surcharge_amount": selected["surcharge"],
        "interest_amount": selected["interest"],
        "partite": repo._partite_payload(db, avviso_id),
        "partitario": partitario,
    }
    snapshot = {
        "load": source["load"],
        "residual": source["residual"],
        "difference": source["difference"],
        "total": str(money(selected["total"])),
    }
    return {
        **facts["print_policy"],
        "template_path": GAIA_PROPOSAL_TEMPLATE_KEY,
        "codice_fiscale": row["tax_code"],
        "display_name": row["name"],
        "comune": None,
        "years": [2021],
        "notice_number": row["number"],
        "bollettino_causale": row["number"],
        "generated_at": approved_at,
        "notice_reference_years": [2021],
        "due_amount": str(
            money(source["load"]) + money(selected["surcharge"]) + money(selected["interest"])
        ),
        "paid_amount": paid,
        "saldo_amount": selected["total"],
        "surcharge_amount": selected["surcharge"],
        "interest_amount": selected["interest"],
        "notification_amount": approval.notification_fee,
        "avvisi": [detail],
        "taxpayer_portal_access": [],
        "campaign_2021_snapshot": snapshot,
    }


def render_preview(payload: dict) -> bytes:
    with TemporaryDirectory(prefix="gaia_campaign_2021_") as directory:
        path = Path(directory) / "preview.pdf"
        generate_batch_reminder_pdf(payload, output_path=path)
        result = marked_pdf(path.read_bytes())
    # The native renderer and slip must carry exactly the approved total.
    text = " ".join(PdfReader(BytesIO(result)).pages[0].extract_text().split())
    total = (
        f"{notice_total_amount(payload):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    if total not in text or payload["notice_number"] not in text:
        raise ValueError("Totale o numero avviso non riscontrato nel PDF")
    return result
