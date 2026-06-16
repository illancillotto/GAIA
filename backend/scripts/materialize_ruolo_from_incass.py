from __future__ import annotations

import argparse
import os
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if not (BACKEND_ROOT / "app").exists():
    fallback_backend = SCRIPT_PATH.parents[2] / "backend"
    if (fallback_backend / "app").exists():
        BACKEND_ROOT = fallback_backend
        REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _configure_database_url_for_host() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        return
    try:
        parsed = make_url(db_url)
    except Exception:
        return
    if (parsed.host or "") != "postgres":
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    if Path("/.dockerenv").exists():
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    fallback = parsed.set(host="127.0.0.1", port=5434 if parsed.port in (None, 5432) else parsed.port)
    os.environ["DATABASE_URL"] = fallback.render_as_string(hide_password=False)


_configure_database_url_for_host()

from app.core.database import SessionLocal
from app.modules.elaborazioni.capacitas.apps.incass.parsers import parse_incass_partitario_dialog
from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.services.import_service import (
    _normalize_partita_comune_nome,
    _resolve_comune_codice_for_ruolo,
    _resolve_section_hint_for_ruolo_comune,
    _upsert_catasto_parcel,
    resolve_cat_particella_match,
)
from app.modules.utenze.models import AnagraficaPaymentNotice


MAX_NUMERIC_10_2 = Decimal("99999999.99")
MAX_NUMERIC_10_4 = Decimal("999999.9999")
MAX_NUMERIC_12_2 = Decimal("9999999999.99")
HISTORICAL_COMUNE_ALIASES = {
    "SILI`*ORISTANO": "SILI",
    "ORISTANO*ORISTANO": "ORISTANO",
    "SIMAXIS*SIMAXIS": "SIMAXIS",
    "DONIGALA*ORISTANO": "DONIGALA",
    "DONIGALA FENUGHEDU*ORISTANO": "DONIGALA",
    "MASSAMA*ORISTANO": "MASSAMA",
    "NURAXINIEDDU*ORISTANO": "NURAXINIEDDU",
    "SOLANAS*CABRAS": "CABRAS",
    "SAN VERO CONGIUS*SIMAXIS": "SIMAXIS",
    "SAN VERO CONGIUS": "SIMAXIS",
}


@dataclass(frozen=True)
class ExistingParcelKey:
    partita_id: str
    foglio: str
    particella: str
    subalterno: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materializza lo storico ruolo da ana_payment_notices/inCass.")
    parser.add_argument("--from-year", type=int, required=True)
    parser.add_argument("--to-year", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--replace-year",
        action="store_true",
        help="Svuota completamente il dataset ruolo dell'anno prima della materializzazione da inCASS.",
    )
    parser.add_argument(
        "--purge-only",
        action="store_true",
        help="Esegue solo lo svuotamento dell'anno target. Richiede --replace-year.",
    )
    parser.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Ricostruisce senza svuotare l'anno target. Utile dopo un purge controllato.",
    )
    parser.add_argument("--max-notices", type=int, default=None)
    parser.add_argument("--commit-every", type=int, default=250)
    parser.add_argument("--skip-catasto", action="store_true")
    args = parser.parse_args()
    if args.purge_only and args.rebuild_only:
        parser.error("--purge-only e --rebuild-only sono mutuamente esclusivi")
    if args.purge_only and not args.replace_year:
        parser.error("--purge-only richiede --replace-year")
    return args


def _normalize_spaces(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().upper().split())


def _normalize_partita_code(value: str | None) -> str:
    return _normalize_spaces(value)


def _normalize_comune(value: str | None) -> str:
    if not value:
        return ""
    normalized = _normalize_partita_comune_nome(value)
    normalized = normalized.split(";", maxsplit=1)[0].strip()
    normalized = HISTORICAL_COMUNE_ALIASES.get(normalized.upper(), normalized)
    return _normalize_spaces(normalized)


def _normalize_numeric_token(value: str | None) -> str:
    if not value:
        return ""
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if not digits:
        return ""
    return str(int(digits))


def _normalize_subalterno(value: str | None) -> str:
    return _normalize_spaces(value)


def _clip(value: str | None, length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value)
    return normalized[:length]


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _sum_decimals(values: list[Decimal | None]) -> Decimal | None:
    total = Decimal("0")
    found = False
    for value in values:
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def _coerce_decimal(value: Decimal | None, max_value: Decimal, stats: Counter[str], field_name: str) -> float | None:
    if value is None:
        return None
    if abs(value) > max_value:
        stats[f"sanitized_{field_name}_out_of_range"] += 1
        return None
    return float(value)


def _sup_ha_from_are(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value / Decimal("100")


def _notice_to_codice_cnc(notice_id: str) -> str:
    if len(notice_id) < 2:
        return notice_id
    core = notice_id[:-1]
    return f"01.{core}"


def _build_address(notice: AnagraficaPaymentNotice) -> str | None:
    parts = [
        (notice.indirizzo or "").strip(),
        (notice.cap or "").strip(),
        (notice.citta or "").strip(),
        (notice.provincia or "").strip(),
    ]
    cleaned = " ".join(part for part in parts if part)
    return cleaned or None


def _extract_partite(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("partitario"), dict):
        partitario_payload = payload["partitario"]
        nested = partitario_payload.get("partite")
        if isinstance(nested, list):
            partite = [item for item in nested if isinstance(item, dict)]
            if partite:
                return partite
        reparsed_source = (
            partitario_payload.get("info_text")
            or partitario_payload.get("raw_html")
            or partitario_payload.get("info_html")
            or payload.get("info_text")
            or payload.get("raw_html")
            or payload.get("info_html")
        )
        avviso = str(partitario_payload.get("avviso") or payload.get("avviso") or "")
        if isinstance(reparsed_source, str) and reparsed_source.strip():
            reparsed = parse_incass_partitario_dialog(reparsed_source, avviso=avviso)
            if reparsed is not None:
                return [
                    item.model_dump(mode="json")
                    for item in reparsed.partite
                ]
    nested = payload.get("partite")
    if isinstance(nested, list):
        return [item for item in nested if isinstance(item, dict)]
    return []


def _ensure_import_job(db: Session, anno: int, *, apply: bool) -> uuid.UUID:
    existing = db.scalars(
        select(RuoloImportJob).where(
            RuoloImportJob.anno_tributario == anno,
            RuoloImportJob.filename == f"incass_backfill_{anno}",
        )
    ).first()
    if existing is not None:
        return existing.id
    job_id = uuid.uuid4()
    if apply:
        db.add(
            RuoloImportJob(
                id=job_id,
                anno_tributario=anno,
                filename=f"incass_backfill_{anno}",
                status="completed",
                total_partite=0,
                records_imported=0,
                records_skipped=0,
                records_errors=0,
                error_detail=None,
                triggered_by=None,
                params_json={"source": "ana_payment_notices", "mode": "historical_materialization"},
            )
        )
        db.flush()
    return job_id


def _collect_year_state(db: Session, anno: int) -> dict[str, int]:
    return {
        "avvisi": int(db.scalar(select(func.count(RuoloAvviso.id)).where(RuoloAvviso.anno_tributario == anno)) or 0),
        "partite": int(
            db.scalar(
                select(func.count(RuoloPartita.id))
                .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
                .where(RuoloAvviso.anno_tributario == anno)
            )
            or 0
        ),
        "particelle": int(
            db.scalar(
                select(func.count(RuoloParticella.id))
                .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
                .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
                .where(RuoloAvviso.anno_tributario == anno)
            )
            or 0
        ),
        "jobs": int(db.scalar(select(func.count(RuoloImportJob.id)).where(RuoloImportJob.anno_tributario == anno)) or 0),
    }


def _purge_year(db: Session, anno: int, *, apply: bool) -> dict[str, int]:
    state = _collect_year_state(db, anno)
    if not apply:
        return state

    print(
        f"[purge] anno={anno} avvisi={state['avvisi']} partite={state['partite']} "
        f"particelle={state['particelle']} jobs={state['jobs']}",
        flush=True,
    )
    db.execute(
        text(
            """
            DELETE FROM ruolo_particelle rp
            USING ruolo_partite rpa, ruolo_avvisi ra
            WHERE rp.partita_id = rpa.id
              AND rpa.avviso_id = ra.id
              AND ra.anno_tributario = :anno
            """
        ),
        {"anno": anno},
    )
    db.execute(
        text(
            """
            DELETE FROM ruolo_partite rp
            USING ruolo_avvisi ra
            WHERE rp.avviso_id = ra.id
              AND ra.anno_tributario = :anno
            """
        ),
        {"anno": anno},
    )
    db.execute(
        delete(RuoloAvviso).where(RuoloAvviso.anno_tributario == anno)
    )
    db.execute(
        delete(RuoloImportJob).where(RuoloImportJob.anno_tributario == anno)
    )
    db.flush()
    print(f"[purge] anno={anno} completato", flush=True)
    return state


def _load_notice_map(db: Session, anno: int) -> dict[str, RuoloAvviso]:
    notices = db.scalars(select(RuoloAvviso).where(RuoloAvviso.anno_tributario == anno)).all()
    return {avviso.codice_cnc: avviso for avviso in notices}


def _load_partita_map(db: Session, anno: int) -> dict[tuple[str, str, str], RuoloPartita]:
    rows = db.execute(
        select(RuoloPartita, RuoloAvviso)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(RuoloAvviso.anno_tributario == anno)
    ).all()
    result: dict[tuple[str, str, str], RuoloPartita] = {}
    for partita, avviso in rows:
        key = (
            str(avviso.id),
            _normalize_partita_code(partita.codice_partita),
            _normalize_comune(partita.comune_nome),
        )
        result[key] = partita
    return result


def _load_existing_parcel_keys(db: Session, anno: int) -> set[ExistingParcelKey]:
    rows = db.execute(
        select(RuoloParticella.partita_id, RuoloParticella.foglio, RuoloParticella.particella, RuoloParticella.subalterno)
        .where(RuoloParticella.anno_tributario == anno)
    ).all()
    return {
        ExistingParcelKey(
            partita_id=str(partita_id),
            foglio=_normalize_numeric_token(foglio),
            particella=_normalize_numeric_token(particella),
            subalterno=_normalize_subalterno(subalterno),
        )
        for partita_id, foglio, particella, subalterno in rows
        if _normalize_numeric_token(foglio) and _normalize_numeric_token(particella)
    }


def _iter_notices(db: Session, anno: int, *, max_notices: int | None) -> list[AnagraficaPaymentNotice]:
    query = select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.subject_id.is_not(None),
            AnagraficaPaymentNotice.raw_detail_json.is_not(None),
        ).order_by(AnagraficaPaymentNotice.source_notice_id)
    if max_notices is not None:
        query = query.limit(max_notices)
    return db.scalars(query).all()


def _ensure_ruolo_avviso(
    db: Session,
    *,
    anno: int,
    notice: AnagraficaPaymentNotice,
    partite: list[dict[str, Any]],
    import_job_id: uuid.UUID,
    notice_map: dict[str, RuoloAvviso],
    stats: Counter[str],
    apply: bool,
) -> RuoloAvviso:
    codice_cnc = _notice_to_codice_cnc(notice.source_notice_id)
    importo_0648 = _sum_decimals([_to_decimal(item.get("importo_0648_euro")) for item in partite])
    importo_0985 = _sum_decimals([_to_decimal(item.get("importo_0985_euro")) for item in partite])
    importo_0668 = _sum_decimals([_to_decimal(item.get("importo_0668_euro")) for item in partite])
    importo_totale = _sum_decimals([importo_0648, importo_0985, importo_0668])
    address = _build_address(notice)

    avviso = notice_map.get(codice_cnc)
    if avviso is None:
        avviso = RuoloAvviso(
            id=uuid.uuid4(),
            import_job_id=import_job_id,
            codice_cnc=codice_cnc,
            anno_tributario=anno,
            subject_id=notice.subject_id,
            codice_fiscale_raw=_clip(notice.codice_fiscale or notice.partita_iva, 20),
            nominativo_raw=_clip(notice.display_name, 300),
            domicilio_raw=address,
            residenza_raw=address,
            n2_extra_raw=None,
            codice_utenza=_clip(notice.source_internal_id, 30),
            importo_totale_0648=_coerce_decimal(importo_0648, MAX_NUMERIC_12_2, stats, "avviso_importo_totale_0648"),
            importo_totale_0985=_coerce_decimal(importo_0985, MAX_NUMERIC_12_2, stats, "avviso_importo_totale_0985"),
            importo_totale_0668=_coerce_decimal(importo_0668, MAX_NUMERIC_12_2, stats, "avviso_importo_totale_0668"),
            importo_totale_euro=_coerce_decimal(importo_totale, MAX_NUMERIC_12_2, stats, "avviso_importo_totale_euro"),
            importo_totale_lire=None,
            n4_campo_sconosciuto=None,
        )
        notice_map[codice_cnc] = avviso
        stats["created_avvisi"] += 1
        if apply:
            db.add(avviso)
            db.flush()
        return avviso

    changed = False
    if avviso.subject_id is None and notice.subject_id is not None:
        avviso.subject_id = notice.subject_id
        changed = True
    if not avviso.nominativo_raw and notice.display_name:
        avviso.nominativo_raw = notice.display_name
        changed = True
    if not avviso.codice_fiscale_raw and (notice.codice_fiscale or notice.partita_iva):
        avviso.codice_fiscale_raw = _clip(notice.codice_fiscale or notice.partita_iva, 20)
        changed = True
    if changed:
        stats["updated_avvisi"] += 1
        if apply:
            db.flush()
    return avviso


def _ensure_ruolo_partita(
    db: Session,
    *,
    avviso: RuoloAvviso,
    partita_payload: dict[str, Any],
    partite_map: dict[tuple[str, str, str], RuoloPartita],
    stats: Counter[str],
    apply: bool,
) -> RuoloPartita | None:
    codice_partita = _normalize_partita_code(partita_payload.get("codice_partita"))
    comune_nome = _normalize_comune(partita_payload.get("comune_nome"))
    if not codice_partita or not comune_nome:
        stats["partite_invalid_key"] += 1
        return None
    key = (str(avviso.id), codice_partita, comune_nome)
    partita = partite_map.get(key)
    if partita is None:
        partita = RuoloPartita(
            id=uuid.uuid4(),
            avviso_id=avviso.id,
            codice_partita=_clip(codice_partita, 30) or codice_partita,
            comune_nome=_clip(comune_nome, 100) or comune_nome,
            comune_codice=_resolve_comune_codice_for_ruolo(db, comune_nome),
            contribuente_cf=_clip(partita_payload.get("contribuente_cf") or None, 20),
            co_intestati_raw=partita_payload.get("co_intestati_raw") or None,
            importo_0648=_coerce_decimal(_to_decimal(partita_payload.get("importo_0648_euro")), MAX_NUMERIC_10_2, stats, "partita_importo_0648"),
            importo_0985=_coerce_decimal(_to_decimal(partita_payload.get("importo_0985_euro")), MAX_NUMERIC_10_2, stats, "partita_importo_0985"),
            importo_0668=_coerce_decimal(_to_decimal(partita_payload.get("importo_0668_euro")), MAX_NUMERIC_10_2, stats, "partita_importo_0668"),
        )
        partite_map[key] = partita
        stats["created_partite"] += 1
        if apply:
            db.add(partita)
            db.flush()
        return partita
    return partita


def _ensure_ruolo_particella(
    db: Session,
    *,
    anno: int,
    partita: RuoloPartita,
    particella_payload: dict[str, Any],
    existing_keys: set[ExistingParcelKey],
    stats: Counter[str],
    apply: bool,
    skip_catasto: bool,
) -> None:
    foglio = _normalize_numeric_token(particella_payload.get("foglio"))
    particella = _normalize_numeric_token(particella_payload.get("particella"))
    subalterno = _normalize_subalterno(particella_payload.get("subalterno"))
    if not foglio or not particella:
        stats["particelle_invalid_key"] += 1
        return
    key = ExistingParcelKey(str(partita.id), foglio, particella, subalterno)
    if key in existing_keys:
        stats["existing_particelle"] += 1
        return

    sup_catastale_are = _to_decimal(particella_payload.get("sup_catastale_are"))
    sup_catastale_ha = _sup_ha_from_are(sup_catastale_are)
    sup_irrigata_ha = _to_decimal(particella_payload.get("sup_irrigata_ha"))
    importo_manut = _to_decimal(particella_payload.get("importo_manut_euro"))
    importo_irrig = _to_decimal(particella_payload.get("importo_irrig_euro"))
    importo_ist = _to_decimal(particella_payload.get("importo_ist_euro"))

    catasto_parcel_id = None
    cat_particella_id = None
    cat_particella_match_status = "unmatched"
    cat_particella_match_confidence = None
    cat_particella_match_reason = "catasto_skipped" if skip_catasto else "catasto_parcel_not_resolved"

    if not skip_catasto:
        comune_nome = _normalize_partita_comune_nome(partita.comune_nome)
        sezione_hint = _resolve_section_hint_for_ruolo_comune(comune_nome)
        try:
            catasto_parcel_id = _upsert_catasto_parcel(
                db,
                comune_nome=comune_nome,
                foglio=foglio,
                particella=particella,
                subalterno=subalterno or None,
                sup_catastale_are=sup_catastale_are,
                anno=anno,
            )
            catasto_parcel = db.get(CatastoParcel, catasto_parcel_id) if catasto_parcel_id else None
            if catasto_parcel is not None:
                (
                    cat_particella_id,
                    cat_particella_match_status,
                    cat_particella_match_confidence,
                    cat_particella_match_reason,
                ) = resolve_cat_particella_match(
                    db,
                    comune_codice=catasto_parcel.comune_codice,
                    foglio=catasto_parcel.foglio,
                    particella=catasto_parcel.particella,
                    subalterno=catasto_parcel.subalterno,
                    sezione_catastale=sezione_hint,
                )
        except Exception:
            stats["particella_match_resolution_errors"] += 1

    else:
        stats["particella_catasto_skipped"] += 1

    existing_keys.add(key)
    stats["created_particelle"] += 1
    stats[f"match_status_{cat_particella_match_status}"] += 1
    if cat_particella_match_reason:
        stats[f"match_reason_{cat_particella_match_reason}"] += 1

    if not apply:
        return

    db.add(
        RuoloParticella(
            id=uuid.uuid4(),
            partita_id=partita.id,
            anno_tributario=anno,
            domanda_irrigua=particella_payload.get("domanda_irrigua") or None,
            distretto=_clip(particella_payload.get("distretto") or None, 10),
            foglio=_clip(foglio, 10) or foglio,
            particella=_clip(particella, 20) or particella,
            subalterno=_clip(subalterno or None, 10),
            sup_catastale_are=_coerce_decimal(sup_catastale_are, MAX_NUMERIC_10_4, stats, "sup_catastale_are"),
            sup_catastale_ha=_coerce_decimal(sup_catastale_ha, MAX_NUMERIC_10_4, stats, "sup_catastale_ha"),
            sup_irrigata_ha=_coerce_decimal(sup_irrigata_ha, MAX_NUMERIC_10_4, stats, "sup_irrigata_ha"),
            coltura=_clip(particella_payload.get("coltura") or None, 50),
            importo_manut=_coerce_decimal(importo_manut, MAX_NUMERIC_10_2, stats, "importo_manut"),
            importo_irrig=_coerce_decimal(importo_irrig, MAX_NUMERIC_10_2, stats, "importo_irrig"),
            importo_ist=_coerce_decimal(importo_ist, MAX_NUMERIC_10_2, stats, "importo_ist"),
            catasto_parcel_id=catasto_parcel_id,
            cat_particella_id=cat_particella_id,
            cat_particella_match_status=cat_particella_match_status,
            cat_particella_match_confidence=cat_particella_match_confidence,
            cat_particella_match_reason=cat_particella_match_reason,
        )
    )
    db.flush()


def _flush_job_stats(db: Session, import_job_id: uuid.UUID, stats: Counter[str]) -> None:
    job = db.get(RuoloImportJob, import_job_id)
    if job is None:
        return
    job.total_partite = stats["partite_scanned"]
    job.records_imported = stats["created_avvisi"] + stats["created_partite"] + stats["created_particelle"]
    job.records_skipped = stats["existing_particelle"]
    job.records_errors = stats["notice_errors"]


def process_year(
    db: Session,
    anno: int,
    *,
    apply: bool,
    replace_year: bool,
    purge_only: bool,
    rebuild_only: bool,
    max_notices: int | None,
    commit_every: int,
    skip_catasto: bool,
) -> Counter[str]:
    stats: Counter[str] = Counter()
    should_purge = replace_year and not rebuild_only
    if should_purge:
        purged = _purge_year(db, anno, apply=apply)
        stats["purged_avvisi"] = purged["avvisi"]
        stats["purged_partite"] = purged["partite"]
        stats["purged_particelle"] = purged["particelle"]
        stats["purged_jobs"] = purged["jobs"]
        if apply:
            db.commit()
    if purge_only:
        if not apply:
            db.rollback()
        return stats

    notices = _iter_notices(db, anno, max_notices=max_notices)
    if should_purge and not apply:
        notice_map = {}
        partite_map = {}
        existing_keys = set()
    else:
        notice_map = _load_notice_map(db, anno)
        partite_map = _load_partita_map(db, anno)
        existing_keys = _load_existing_parcel_keys(db, anno)
    import_job_id = _ensure_import_job(db, anno, apply=apply)

    stats["notices_total"] = len(notices)
    stats["existing_avvisi_before"] = len(notice_map)
    stats["existing_partite_before"] = len(partite_map)
    stats["existing_particelle_before"] = len(existing_keys)

    for index, notice in enumerate(notices, start=1):
        if index == 1:
            print(f"[rebuild] anno={anno} notices={len(notices)} apply={apply}", flush=True)
        payload = notice.raw_detail_json
        if not isinstance(payload, dict):
            stats["notices_without_payload_dict"] += 1
            continue
        partite = _extract_partite(payload)
        if not partite:
            stats["notices_without_partite"] += 1
            continue
        try:
            with db.begin_nested():
                avviso = _ensure_ruolo_avviso(
                    db,
                    anno=anno,
                    notice=notice,
                    partite=partite,
                    import_job_id=import_job_id,
                    notice_map=notice_map,
                    stats=stats,
                    apply=apply,
                )
                for partita_payload in partite:
                    stats["partite_scanned"] += 1
                    partita = _ensure_ruolo_partita(
                        db,
                        avviso=avviso,
                        partita_payload=partita_payload,
                        partite_map=partite_map,
                        stats=stats,
                        apply=apply,
                    )
                    if partita is None:
                        continue
                    particelle = partita_payload.get("particelle")
                    if not isinstance(particelle, list):
                        continue
                    for particella_payload in particelle:
                        if not isinstance(particella_payload, dict):
                            continue
                        stats["particelle_scanned"] += 1
                        _ensure_ruolo_particella(
                            db,
                            anno=anno,
                            partita=partita,
                            particella_payload=particella_payload,
                            existing_keys=existing_keys,
                            stats=stats,
                            apply=apply,
                            skip_catasto=skip_catasto,
                        )
                stats["notices_processed"] += 1
        except Exception:
            stats["notice_errors"] += 1
            continue

        if apply and commit_every > 0 and index % commit_every == 0:
            _flush_job_stats(db, import_job_id, stats)
            db.commit()
            print(
                f"[rebuild] anno={anno} processed={stats['notices_processed']}/{len(notices)} "
                f"created_avvisi={stats['created_avvisi']} created_partite={stats['created_partite']} "
                f"created_particelle={stats['created_particelle']} errors={stats['notice_errors']}",
                flush=True,
            )

    if apply:
        _flush_job_stats(db, import_job_id, stats)
        db.commit()
    else:
        db.rollback()
    return stats


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        for anno in range(args.from_year, args.to_year + 1):
            stats = process_year(
                db,
                anno,
                apply=args.apply,
                replace_year=args.replace_year,
                purge_only=args.purge_only,
                rebuild_only=args.rebuild_only,
                max_notices=args.max_notices,
                commit_every=args.commit_every,
                skip_catasto=args.skip_catasto,
            )
            print(
                f"anno={anno} notices={stats['notices_total']} processed={stats['notices_processed']} "
                f"purged_avvisi={stats['purged_avvisi']} purged_partite={stats['purged_partite']} "
                f"purged_particelle={stats['purged_particelle']} purged_jobs={stats['purged_jobs']} "
                f"created_avvisi={stats['created_avvisi']} created_partite={stats['created_partite']} "
                f"created_particelle={stats['created_particelle']} existing_particelle={stats['existing_particelle']} "
                f"errors={stats['notice_errors']}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
