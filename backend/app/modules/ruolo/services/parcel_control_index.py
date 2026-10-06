from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select, text, update

from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.parcel_control_models import ParcelControlIndex, ParcelControlState
from app.modules.ruolo.services.parcel_control_identity import (
    YEARS,
    digest,
    source_identity,
    tax_code_check,
)


def control_state(db, actor_id: int = 0):
    state = db.get(ParcelControlState, 1)
    if state is None:
        state = ParcelControlState(
            id=1, current_year=2025, signatures={}, coverage={}, actor_id=actor_id
        )
        db.add(state)
        db.flush()
    return state


def analysis_lock(db):
    if db.get_bind().dialect.name == "postgresql":
        locked = db.scalar(text("SELECT pg_try_advisory_xact_lock(20251006, 2025)"))
        if not locked:
            raise ValueError("Analisi già in corso: riprovare al termine")


def source_rows(db):
    statement = (
        select(RuoloParticella, RuoloPartita, RuoloAvviso)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(RuoloParticella.anno_tributario.in_(YEARS))
        .order_by(RuoloParticella.id)
        .execution_options(yield_per=500)
    )
    return db.execute(statement)


def occurrence(parcel, partita, avviso) -> dict:
    check = tax_code_check(avviso.codice_fiscale_raw)
    partita_check = tax_code_check(partita.contribuente_cf)
    if (
        all((check["normalized"], partita_check["normalized"]))
        and check["normalized"] != partita_check["normalized"]
    ):
        check = {**check, "anomaly": "inconsistent"}
    return {
        "row_id": str(parcel.id),
        "year": parcel.anno_tributario,
        "avviso_id": str(avviso.id),
        "codice_cnc": avviso.codice_cnc,
        "subject_id": str(avviso.subject_id) if avviso.subject_id else None,
        "name": avviso.nominativo_raw,
        "tax_code": check,
        "partita_tax_code": partita_check,
        "cat_particella_id": str(parcel.cat_particella_id) if parcel.cat_particella_id else None,
        "catasto_status": parcel.ade_scan_classification,
        "match_status": parcel.cat_particella_match_status,
        "source_reference": {
            "comune": partita.comune_nome,
            "comune_codice": partita.comune_codice,
            "foglio": parcel.foglio,
            "particella": parcel.particella,
            "subalterno": parcel.subalterno,
        },
    }


def collect_index(db):
    initial_stamp = source_stamp(db)
    groups = {}
    fingerprints = defaultdict(list)
    for parcel, partita, avviso in source_rows(db):
        identity = source_identity(parcel, partita)
        row = occurrence(parcel, partita, avviso)
        fingerprints[str(parcel.anno_tributario)].append(digest(row))
        group = groups.setdefault(identity["key"], {**identity, "occurrences": []})
        group["occurrences"].append(row)
    headers = db.scalars(
        select(RuoloAvviso).where(RuoloAvviso.anno_tributario.in_(YEARS)).order_by(RuoloAvviso.id)
    )
    for header in headers:
        fingerprints[str(header.anno_tributario)].append(
            digest([header.id, header.import_job_id, header.updated_at, header.codice_fiscale_raw])
        )
    jobs = db.scalars(
        select(RuoloImportJob)
        .where(RuoloImportJob.anno_tributario.in_(YEARS))
        .order_by(RuoloImportJob.id)
    )
    for job in jobs:
        fingerprints[str(job.anno_tributario)].append(
            digest(
                [job.id, job.status, job.records_imported, job.records_skipped, job.records_errors]
            )
        )
    if initial_stamp != source_stamp(db):
        raise ValueError("Dati sorgente cambiati durante l'analisi: ripetere il controllo")
    return groups, {
        **{str(year): digest(fingerprints[str(year)]) for year in YEARS},
        "_stamp": initial_stamp,
    }


def source_stamp(db):
    parcels = db.execute(
        select(func.count(RuoloParticella.id), func.max(RuoloParticella.created_at)).where(
            RuoloParticella.anno_tributario.in_(YEARS)
        )
    ).one()
    headers = db.execute(
        select(func.count(RuoloAvviso.id), func.max(RuoloAvviso.updated_at)).where(
            RuoloAvviso.anno_tributario.in_(YEARS)
        )
    ).one()
    jobs = db.execute(
        select(
            func.count(RuoloImportJob.id),
            func.max(RuoloImportJob.finished_at),
            func.sum(RuoloImportJob.records_imported),
            func.sum(RuoloImportJob.records_errors),
            func.sum(RuoloImportJob.records_skipped),
        ).where(RuoloImportJob.anno_tributario.in_(YEARS))
    ).one()
    return digest([list(parcels), list(headers), list(jobs)])


def refresh_index(db, actor_id: int):
    analysis_lock(db)
    state = control_state(db, actor_id)
    groups, signatures = collect_index(db)
    existing = {item.identity_key: item for item in db.scalars(select(ParcelControlIndex))}
    db.execute(update(ParcelControlIndex).values(active=False))
    for key, group in groups.items():
        item = existing.get(key)
        if item is None:
            item = ParcelControlIndex(identity_key=key)
            db.add(item)
        reference = group["reference"]
        item.label = f"{reference['comune_nome']} · Fg.{reference['foglio']} Part.{reference['particella']} Sub.{reference['subalterno']}"
        item.active = True
        item.original = group
        item.cf_anomaly = any(row["tax_code"]["anomaly"] for row in group["occurrences"])
        item.current_present = any(
            row["year"] == state.current_year for row in group["occurrences"]
        )
    state.signatures = signatures
    state.refreshed_at = datetime.now(UTC)
    state.actor_id = actor_id
    db.flush()
    return {
        "total": len(groups),
        "current_year": state.current_year,
        "refreshed_at": state.refreshed_at,
    }


def certify_year(db, year: int, actor_id: int, reason: str, source: str):
    analysis_lock(db)
    state = control_state(db, actor_id)
    if year not in YEARS or not source.strip():
        raise ValueError("Annualità o fonte non valida")
    _, signatures = collect_index(db)
    if signatures != state.signatures:
        raise ValueError("Dati cambiati: aggiornare l'analisi prima della certificazione")
    jobs = db.scalars(select(RuoloImportJob).where(RuoloImportJob.anno_tributario == year)).all()
    if not jobs or any(
        not all(
            (
                job.status == "completed",
                job.records_errors == 0,
                job.records_skipped == 0,
                job.records_imported is not None,
            )
        )
        for job in jobs
    ):
        raise ValueError("Import mancanti, incompleti o con errori: annualità non certificabile")
    state.coverage = {
        **state.coverage,
        str(year): {
            "signature": signatures[str(year)],
            "source": source,
            "reason": reason,
            "actor_id": actor_id,
            "certified_at": datetime.now(UTC).isoformat(),
        },
    }
