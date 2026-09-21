"""Snapshot existing Poste rows without trusting historical matching flags."""

import json

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.services.notice_import_excel import MAX_ROWS, digest, json_bytes


def snapshot_poste(db: Session) -> tuple[bytes, list[dict], dict]:
    mails = db.scalars(
        select(RuoloTributiRegisteredMail)
        .order_by(RuoloTributiRegisteredMail.id)
        .limit(MAX_ROWS + 1)
    ).all()
    if not mails or len(mails) > MAX_ROWS:
        raise ValueError("Snapshot Poste vuoto o oltre 10000 record")
    originals, rows = [], []
    for number, mail in enumerate(mails, 1):
        original = json.loads(
            json_bytes(
                {column.key: getattr(mail, column.key) for column in inspect(type(mail)).columns}
            )
        )
        originals.append(original)
        key = str(mail.id)
        payload = {
            "document_number": f"Poste {key}",
            "tax_code": None,
            "positions": [],
            "original": original,
            "registered_mail_id": key,
            "tracking_code": mail.tracking_number,
            "sent_at": original["sent_at"],
            "sheet": "Poste DB",
        }
        rows.append(
            {
                "row_number": number,
                "source_key": key,
                "fingerprint": digest(json_bytes(original)),
                "payload": payload,
                "anomalies": [
                    "posizioni_assenti",
                    "notifica_da_verificare",
                    "step_da_verificare",
                    "poste_da_riconciliare",
                ],
            }
        )
    content = json_bytes(originals)
    if len(content) > 64 * 1024 * 1024:
        raise ValueError("Snapshot Poste oltre 64 MiB")
    return content, rows, {"rows": len(rows), "ignored_non_operational": 0}
