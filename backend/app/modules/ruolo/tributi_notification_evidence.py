import re
from contextlib import suppress
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiCalculationPolicy, RuoloTributiRegisteredMail
from app.modules.ruolo.services.registered_mail_association import associated_avviso_ids
from app.modules.ruolo.tributi_policy_repository import get_calculation_policy_for_year

RECEIVED_DATE_KEYS = {
    "received_at",
    "delivered_at",
    "delivery_at",
    "delivery_date",
    "data_ricezione",
    "data_consegna",
    "dataricezione",
    "dataconsegna",
}


def parse_policy_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d"):
        with suppress(ValueError):
            return datetime.strptime(text[:19] if "%H" in pattern else text[:10], pattern).date()
    with suppress(ValueError):
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    return None


def has_documented_pec_delivery(raw_detail: object) -> bool:
    if not isinstance(raw_detail, dict):
        return False
    mailing = raw_detail.get("mailing_list")
    if not isinstance(mailing, dict):
        return False
    receipts = mailing.get("receipt_parents_by_shipment_id")
    if not isinstance(receipts, dict):
        return False
    return any(_has_delivery_receipt(parents) for parents in receipts.values())


def _has_delivery_receipt(parents: object) -> bool:
    if not isinstance(parents, list):
        return False
    for parent in parents:
        if not isinstance(parent, dict):
            continue
        if str(parent.get("group", "")).strip().upper() == "CONSEGNA":
            if parse_policy_date(parent.get("date")) is not None:
                return True
    return False


def has_documented_mail_receipt(payload: object) -> bool:
    if isinstance(payload, list):
        return any(has_documented_mail_receipt(item) for item in payload)
    if not isinstance(payload, dict):
        return False
    for key, value in payload.items():
        normalized = re.sub(r"[^a-z0-9_]+", "_", str(key).strip().lower()).strip("_")
        if normalized in RECEIVED_DATE_KEYS and parse_policy_date(value) is not None:
            return True
        if isinstance(value, (dict, list)) and has_documented_mail_receipt(value):
            return True
    return False


def documented_registered_mail_ids(db: Session, avviso_ids: list[UUID]) -> set[UUID]:
    requested = set(avviso_ids)
    notified = set()
    for mail in db.scalars(select(RuoloTributiRegisteredMail)):
        linked = associated_avviso_ids(mail).intersection(requested)
        if linked and has_documented_mail_receipt(mail.raw_payload_json):
            notified.update(linked)
    return notified


def calculation_policy_context(db: Session, avvisi: list) -> tuple[dict, set[UUID]]:
    policies = {
        year: get_calculation_policy_for_year(db, year)
        for year in sorted({avviso.anno_tributario for avviso in avvisi})
    }
    return policies, documented_registered_mail_ids(db, [avviso.id for avviso in avvisi])


def policy_for_notice(
    policy: RuoloTributiCalculationPolicy | None,
    avviso_id: UUID,
    incass_notice: dict,
    notified_mail_ids: set[UUID],
) -> RuoloTributiCalculationPolicy | None:
    if policy is None or not policy.only_unnotified:
        return policy
    if avviso_id in notified_mail_ids or incass_notice.get("documented_pec_delivery", False):
        return None
    return policy
