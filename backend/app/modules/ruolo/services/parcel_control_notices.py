from copy import deepcopy
from types import SimpleNamespace

from sqlalchemy import select

from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.modules.ruolo.parcel_control_models import ParcelControlCase, ParcelControlIndex
from app.modules.ruolo.services.parcel_control_cases import audit_command, replay
from app.modules.ruolo.services.parcel_control_identity import (
    YEARS,
    source_identity,
    tax_code_check,
)
from app.modules.ruolo.services.parcel_control_index import occurrence


def notice_view(notice, inconsistent=False):
    check = tax_code_check(notice.codice_fiscale_raw)
    if inconsistent:
        check = {**check, "anomaly": "inconsistent"}
    return {
        "id": str(notice.id),
        "year": notice.anno_tributario,
        "codice_cnc": notice.codice_cnc,
        "name": notice.nominativo_raw,
        "tax_code": check,
        "subject_id": str(notice.subject_id) if notice.subject_id else None,
    }


def incoherent_notice_ids(db):
    rows = db.execute(
        select(RuoloAvviso.id, RuoloAvviso.codice_fiscale_raw, RuoloPartita.contribuente_cf)
        .join(RuoloPartita, RuoloPartita.avviso_id == RuoloAvviso.id)
        .where(RuoloAvviso.anno_tributario.in_(YEARS))
    )
    inconsistent = set()
    for notice_id, header_code, partita_code in rows:
        codes = [str(value or "").strip().upper() for value in (header_code, partita_code)]
        if all(codes) and codes[0] != codes[1]:
            inconsistent.add(notice_id)
    return inconsistent


def anomalous_notices(db, filters):
    inconsistent = incoherent_notice_ids(db)
    notices = db.scalars(
        select(RuoloAvviso)
        .where(RuoloAvviso.anno_tributario.in_(YEARS))
        .order_by(RuoloAvviso.anno_tributario, RuoloAvviso.id)
    )
    values = [
        notice_view(notice, notice.id in inconsistent)
        for notice in notices
        if notice.id in inconsistent or tax_code_check(notice.codice_fiscale_raw)["anomaly"]
    ]
    if filters.search:
        query = filters.search.casefold()
        values = [value for value in values if query in str(value).casefold()]
    offset = (filters.page - 1) * filters.page_size
    return {"items": values[offset : offset + filters.page_size], "total": len(values)}


def notice_parcels(db, notice):
    rows = db.execute(
        select(RuoloParticella, RuoloPartita)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .where(RuoloPartita.avviso_id == notice.id)
    ).all()
    parcels = []
    for parcel, partita in rows:
        reference = source_identity(parcel, partita)
        item = db.scalar(
            select(ParcelControlIndex).where(ParcelControlIndex.identity_key == reference["key"])
        )
        if item is None:
            raise ValueError("Aggiornare l'analisi prima di aprire la pratica dell'avviso")
        if not any(entry["id"] == str(item.id) for entry in parcels):
            parcels.append(
                {
                    "id": str(item.id),
                    "reference": deepcopy(item.original["reference"]),
                    "status": "investigating",
                    "origin": "historical",
                }
            )
    return rows, parcels


def open_notice_case(db, notice_id, actor_id, command):
    notice = db.get(RuoloAvviso, notice_id)
    if notice is None or notice.anno_tributario not in YEARS:
        raise LookupError("Avviso storico non trovato")
    case = db.scalar(select(ParcelControlCase).where(ParcelControlCase.notice_id == notice_id))
    if case is None:
        rows, parcels = notice_parcels(db, notice)
        occurrences = [occurrence(parcel, partita, notice) for parcel, partita in rows]
        case = ParcelControlCase(
            notice_id=notice.id,
            responsible_id=actor_id,
            original={
                "notice": notice_view(notice, notice.id in incoherent_notice_ids(db)),
                "occurrences": occurrences,
            },
            parcels=parcels,
            evidence=[],
            matches=[],
        )
        db.add(case)
        db.flush()
    if not replay(db, case.id, actor_id, "open_notice", command):
        audit_command(db, case.id, actor_id, "open_notice", command)
    return case


def notice_case_index(case):
    notice = case.original["notice"]
    reference = {
        field: ""
        for field in ("comune_nome", "comune_codice", "foglio", "particella", "subalterno")
    }
    reference.update(sezione=None, catasto=None)
    return SimpleNamespace(
        id=case.id,
        label=f"Avviso {notice['codice_cnc']} · {notice['year']}",
        cf_anomaly=bool(notice["tax_code"]["anomaly"]),
        original={"reference": reference, "incomplete": True, "occurrences": []},
    )
