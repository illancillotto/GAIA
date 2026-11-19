"""Commit a pending action and its replayable acknowledgement atomically."""

import hashlib
import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileActionReceipt


def apply_once(
    db: Session,
    action: dict[str, Any],
    action_id: str,
    domain_payload: dict[str, Any],
    apply: Callable[[Session, dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    envelope = [action.get("type") or action.get("action_type"), domain_payload]
    digest = hashlib.sha256(json.dumps(envelope, sort_keys=True).encode()).hexdigest()
    receipt = db.get(GateMobileActionReceipt, action_id)
    if receipt is not None:
        if receipt.payload_hash != digest:
            raise ValueError("Contenuto cambiato per una pending action già applicata")
        return receipt.acknowledgement

    # Domain services own their commits when called directly. Bind their Session
    # to this transaction with a savepoint, so those commits and the receipt
    # share one outer commit even if acknowledgement delivery is interrupted.
    # Claim the unique action ID before any domain mutation. It also opens an
    # actual outer write transaction on SQLite before the first savepoint.
    receipt = GateMobileActionReceipt(action_id=action_id, payload_hash=digest, acknowledgement={})
    db.add(receipt)
    db.flush()
    with Session(bind=db.connection(), join_transaction_mode="create_savepoint") as domain:
        result = apply(domain, action)
        domain.commit()
    receipt.acknowledgement = result
    db.commit()
    return result
