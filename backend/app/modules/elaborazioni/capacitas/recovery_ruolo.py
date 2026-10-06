from __future__ import annotations

from collections import Counter

from sqlalchemy import select

from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.modules.ruolo.services.incass_read_model import materialize_incass_notice_header
from app.modules.utenze.models import AnagraficaPaymentNotice
from scripts.materialize_ruolo_from_incass import (
    MAX_NUMERIC_12_2,
    ExistingParcelKey,
    _coerce_decimal,
    _ensure_ruolo_particella,
    _ensure_ruolo_partita,
    _extract_partite,
    _sum_decimals,
    _to_decimal,
)


def _existing_partitario(db, avviso):
    partite = db.scalars(select(RuoloPartita).where(RuoloPartita.avviso_id == avviso.id)).all()
    partita_map = {
        (str(avviso.id), partita.codice_partita, partita.comune_nome): partita
        for partita in partite
    }
    parcels = db.scalars(
        select(RuoloParticella)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .where(RuoloPartita.avviso_id == avviso.id)
    ).all()
    keys = {
        ExistingParcelKey(
            str(parcel.partita_id), parcel.foglio, parcel.particella, parcel.subalterno or ""
        )
        for parcel in parcels
    }
    return partita_map, keys


def _reconcile_totals(avviso, partite, stats):
    totals = []
    for tribute in ("0648", "0985", "0668"):
        total = _sum_decimals([_to_decimal(row.get(f"importo_{tribute}_euro")) for row in partite])
        setattr(
            avviso,
            f"importo_totale_{tribute}",
            _coerce_decimal(total, MAX_NUMERIC_12_2, stats, f"avviso_importo_totale_{tribute}"),
        )
        totals.append(total)
    avviso.importo_totale_euro = _coerce_decimal(
        _sum_decimals(totals), MAX_NUMERIC_12_2, stats, "avviso_importo_totale_euro"
    )


def reconcile_subject_ruolo(db, subject_id):
    notices = db.scalars(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.subject_id == subject_id,
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()
    stats = Counter()
    for notice in notices:
        avviso = materialize_incass_notice_header(db, notice)
        if avviso is None:
            stats["non_ordinary_notices"] += 1
            continue
        partite = _extract_partite(notice.raw_detail_json or {}, force_reparse=True)
        if not partite:
            stats["notices_without_partite"] += 1
            continue
        partita_map, keys = _existing_partitario(db, avviso)
        for payload in partite:
            partita = _ensure_ruolo_partita(
                db,
                avviso=avviso,
                partita_payload=payload,
                partite_map=partita_map,
                stats=stats,
                apply=True,
            )
            if partita is None:
                continue
            for parcel in payload.get("particelle", []):
                _ensure_ruolo_particella(
                    db,
                    anno=avviso.anno_tributario,
                    partita=partita,
                    particella_payload=parcel,
                    existing_keys=keys,
                    stats=stats,
                    apply=True,
                    skip_catasto=False,
                )
        _reconcile_totals(avviso, partite, stats)
        stats["notices_reconciled"] += 1
    db.flush()
    return dict(stats)
