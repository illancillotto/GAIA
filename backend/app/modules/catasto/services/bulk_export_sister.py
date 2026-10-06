from __future__ import annotations

import json

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoSisterExtraction, CatastoSisterOwner, CatastoSisterParcel


def _sister_export_parcel_key(parcel: CatastoSisterParcel) -> tuple[str, str, str, str]:
    return (
        (parcel.comune_nome or "").strip().casefold(),
        *(
            (getattr(parcel, field) or "").strip()
            for field in ("foglio", "particella", "subalterno")
        ),
    )


def _sister_export_row_key(row: dict[str, object]) -> tuple[str, str, str, str]:
    return (
        str(row.get("comune") or "").strip().casefold(),
        *(str(row.get(field) or "").strip() for field in ("foglio", "particella", "sub")),
    )


def _write_sister_export_columns(
    row: dict[str, object],
    data: list[dict[str, object]] | None,
    history: dict[str, object] | None,
) -> None:
    row["sister_dati_presenti"] = "si" if data or history else ""
    for column, payload in (("sister_dati", data), ("sister_storico", history)):
        row[column] = json.dumps(payload, ensure_ascii=False, sort_keys=True) if payload else ""


def _completed_sister_export_query(statement: Select) -> Select:
    return (
        statement.join(
            CatastoSisterExtraction, CatastoSisterExtraction.id == CatastoSisterParcel.extraction_id
        )
        .where(CatastoSisterExtraction.status == "completed")
        .order_by(CatastoSisterExtraction.observed_at.desc().nullslast())
    )


def _attach_sister_data(db: Session, rows: list[dict[str, object]]) -> None:
    sister_by_key: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    sister_history_by_key: dict[tuple[str, str, str, str], dict[str, object]] = {}
    latest_extraction_by_key: dict[tuple[str, str, str, str], object] = {}
    parcel_rows = db.execute(
        _completed_sister_export_query(
            select(CatastoSisterParcel, CatastoSisterOwner, CatastoSisterExtraction).join(
                CatastoSisterOwner, CatastoSisterParcel.id == CatastoSisterOwner.sister_parcel_id
            )
        )
    ).all()
    for parcel, owner, _extraction in parcel_rows:
        key = _sister_export_parcel_key(parcel)
        extraction_id = parcel.extraction_id
        current_extraction_id = latest_extraction_by_key.get(key)
        if current_extraction_id not in (None, extraction_id):
            continue
        latest_extraction_by_key[key] = extraction_id
        sister_by_key.setdefault(key, []).append(
            {
                "codice_fiscale": owner.codice_fiscale,
                "denominazione": owner.denominazione,
                "diritto": owner.diritto,
                "quota": owner.quota,
                "data_nascita": owner.data_nascita.isoformat() if owner.data_nascita else None,
                "luogo_nascita": owner.luogo_nascita,
            }
        )
    history_rows = db.execute(
        _completed_sister_export_query(select(CatastoSisterParcel, CatastoSisterExtraction))
    ).all()
    for parcel, extraction in history_rows:
        key = _sister_export_parcel_key(parcel)
        if key not in sister_history_by_key:
            sister_history_by_key[key] = {
                "eventi": extraction.payload_json.get("history_events", []),
                "particelle_collegate": extraction.payload_json.get("related_parcels", []),
            }
    for row in rows:
        key = _sister_export_row_key(row)
        data = sister_by_key.get(key)
        history = sister_history_by_key.get(key)
        _write_sister_export_columns(row, data, history)
