from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.ruolo.models import (
    RuoloTributiNoticeNumber,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)

MAX_NOTICE_PROGRESSIVE = 99_999


def build_notice_number(
    *, emission_year: int, reference_years: list[int], progressive: int
) -> str:
    years_suffix = "".join(f"{year % 100:02d}" for year in sorted(set(reference_years)))
    return f"1{emission_year}{years_suffix}{progressive:05d}"


def _candidate_identity(
    candidate: dict[str, Any],
    *,
    reference_years: list[int],
) -> tuple[str, tuple[int, ...], tuple[str, ...]]:
    tax_code = _normalise_tax_code(candidate["codice_fiscale"])
    years = tuple(sorted(set(reference_years)))
    avviso_ids = tuple(sorted({str(avviso["id"]) for avviso in candidate["avvisi"]}))
    return tax_code, years, avviso_ids


def _identity_key(
    candidate: dict[str, Any],
    *,
    emission_year: int,
    reference_years: list[int],
) -> str:
    identity = _candidate_identity(candidate, reference_years=reference_years)
    encoded = json.dumps(
        (emission_year, *identity), ensure_ascii=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _normalise_tax_code(value: object) -> str:
    return "".join(
        character
        for character in str(value or "").upper()
        if character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )


def _payload_identity(
    payload: dict[str, Any],
) -> tuple[str, tuple[int, ...], tuple[str, ...]]:
    years = payload.get("years") if isinstance(payload.get("years"), list) else []
    parsed_years = tuple(
        sorted(
            {
                int(year)
                for year in years
                if isinstance(year, int) or str(year).strip().isdigit()
            }
        )
    )
    avvisi = payload.get("avvisi") if isinstance(payload.get("avvisi"), list) else []
    avviso_ids = tuple(
        sorted(
            {
                str(avviso["id"])
                for avviso in avvisi
                if isinstance(avviso, dict) and avviso.get("id")
            }
        )
    )
    return _normalise_tax_code(payload.get("codice_fiscale")), parsed_years, avviso_ids


def _payload_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def find_existing_notice_payload(
    db: Session,
    *,
    emission_year: int,
    candidate: dict[str, Any],
    reference_years: list[int],
) -> dict[str, Any] | None:
    expected_identity = _candidate_identity(candidate, reference_years=reference_years)
    payloads = db.scalars(
        select(RuoloTributiReminderBatchItem.payload_json)
        .join(
            RuoloTributiReminderBatch,
            RuoloTributiReminderBatch.id == RuoloTributiReminderBatchItem.batch_id,
        )
        .order_by(RuoloTributiReminderBatchItem.created_at.desc())
    ).all()
    for payload in payloads:
        if (
            not isinstance(payload, dict)
            or _payload_int(payload, "notice_emission_year") != emission_year
        ):
            continue
        notice_number = str(payload.get("notice_number") or "")
        notice_progressive = _payload_int(payload, "notice_progressive")
        if (
            notice_number
            and notice_progressive is not None
            and _payload_identity(payload) == expected_identity
        ):
            return {
                "notice_number": notice_number,
                "notice_progressive": notice_progressive,
            }
    return None


def next_notice_progressive(db: Session, *, emission_year: int) -> int:
    year_start = datetime(emission_year, 1, 1, tzinfo=timezone.utc)
    year_end = datetime(emission_year + 1, 1, 1, tzinfo=timezone.utc)
    payloads = db.scalars(
        select(RuoloTributiReminderBatchItem.payload_json)
        .join(
            RuoloTributiReminderBatch,
            RuoloTributiReminderBatch.id == RuoloTributiReminderBatchItem.batch_id,
        )
        .where(
            RuoloTributiReminderBatch.generated_at >= year_start,
            RuoloTributiReminderBatch.generated_at < year_end,
        )
    ).all()
    max_progressive = (
        db.scalar(
            select(func.max(RuoloTributiNoticeNumber.progressive)).where(
                RuoloTributiNoticeNumber.emission_year == emission_year
            )
        )
        or 0
    )
    for payload in payloads:
        if (
            not isinstance(payload, dict)
            or _payload_int(payload, "notice_emission_year") != emission_year
        ):
            continue
        max_progressive = max(
            max_progressive, _payload_int(payload, "notice_progressive") or 0
        )
    return max_progressive + 1


def insert_notice_reservation(
    db: Session,
    *,
    emission_year: int,
    progressive: int,
    notice_number: str,
    identity_key: str,
) -> RuoloTributiNoticeNumber | None:
    try:
        with db.begin_nested():
            reservation = RuoloTributiNoticeNumber(
                emission_year=emission_year,
                progressive=progressive,
                notice_number=notice_number,
                identity_key=identity_key,
                status="reserved",
            )
            db.add(reservation)
            db.flush()
        return reservation
    except IntegrityError:
        return None


def _reservation_for_identity(
    db: Session, identity_key: str
) -> RuoloTributiNoticeNumber | None:
    return db.scalar(
        select(RuoloTributiNoticeNumber).where(
            RuoloTributiNoticeNumber.identity_key == identity_key
        )
    )


def reserve_notice_number(
    db: Session,
    *,
    emission_year: int,
    candidate: dict[str, Any],
    reference_years: list[int],
) -> RuoloTributiNoticeNumber:
    identity_key = _identity_key(
        candidate,
        emission_year=emission_year,
        reference_years=reference_years,
    )
    existing = _reservation_for_identity(db, identity_key)
    if existing is not None:
        return existing

    legacy = find_existing_notice_payload(
        db,
        emission_year=emission_year,
        candidate=candidate,
        reference_years=reference_years,
    )
    if legacy is not None:
        adopted = insert_notice_reservation(
            db,
            emission_year=emission_year,
            progressive=legacy["notice_progressive"],
            notice_number=legacy["notice_number"],
            identity_key=identity_key,
        )
        if adopted is not None:
            return adopted
        existing = _reservation_for_identity(db, identity_key)
        if existing is not None:
            return existing

    for _attempt in range(100):
        progressive = next_notice_progressive(db, emission_year=emission_year)
        if progressive > MAX_NOTICE_PROGRESSIVE:
            raise RuntimeError(
                f"Progressivi sollecito esauriti per l'anno {emission_year}"
            )
        reservation = insert_notice_reservation(
            db,
            emission_year=emission_year,
            progressive=progressive,
            notice_number=build_notice_number(
                emission_year=emission_year,
                reference_years=reference_years,
                progressive=progressive,
            ),
            identity_key=identity_key,
        )
        if reservation is not None:
            return reservation
        existing = _reservation_for_identity(db, identity_key)
        if existing is not None:
            return existing
    raise RuntimeError("Impossibile prenotare un progressivo univoco per il sollecito")
