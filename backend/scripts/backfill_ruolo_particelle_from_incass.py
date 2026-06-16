from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
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
    fallback = parsed.set(host="127.0.0.1", port=5434 if parsed.port in (None, 5432) else parsed.port)
    os.environ["DATABASE_URL"] = fallback.render_as_string(hide_password=False)


_configure_database_url_for_host()

from app.core.database import SessionLocal
from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.modules.ruolo.services.catasto_linking import (
    _resolve_comune_codice_for_ruolo,
    _upsert_catasto_parcel,
    resolve_cat_particella_match,
)
from app.modules.ruolo.services.parsing_common import (
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    resolve_section_hint_for_ruolo_comune as _resolve_section_hint_for_ruolo_comune,
)
from app.modules.utenze.models import AnagraficaPaymentNotice


@dataclass(frozen=True)
class ExistingParcelKey:
    partita_id: str
    foglio: str
    particella: str
    subalterno: str


@dataclass
class CandidateParcel:
    notice_id: str
    ruolo_avviso_id: str
    ruolo_partita_id: str
    subject_id: str
    display_name: str
    codice_partita: str
    comune_nome: str
    foglio: str
    particella: str
    subalterno: str
    domanda_irrigua: str | None
    distretto: str | None
    sup_catastale_are: Decimal | None
    sup_irrigata_ha: Decimal | None
    coltura: str | None
    importo_manut: Decimal | None
    importo_irrig: Decimal | None
    importo_ist: Decimal | None


MAX_NUMERIC_10_2 = Decimal("99999999.99")
MAX_NUMERIC_10_4 = Decimal("999999.9999")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill ruolo_particelle dalle particelle partitario inCass già salvate.",
    )
    parser.add_argument("--anno", type=int, default=2025, help="Annualita ruolo/inCass.")
    parser.add_argument("--apply", action="store_true", help="Applica il backfill a DB.")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "exports"),
        help="Directory output report/csv.",
    )
    return parser.parse_args()


def _normalize_spaces(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().upper().split())


def _normalize_partita_code(value: str | None) -> str:
    return _normalize_spaces(value)


def _normalize_comune(value: str | None) -> str:
    if not value:
        return ""
    return _normalize_spaces(_normalize_partita_comune_nome(value))


def _normalize_numeric_token(value: str | None) -> str:
    if not value:
        return ""
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if not digits:
        return ""
    return str(int(digits))


def _normalize_subalterno(value: str | None) -> str:
    return _normalize_spaces(value)


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


def _sup_ha_from_are(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value / Decimal("100")


def _coerce_numeric_10_2(value: Decimal | None, stats: Counter[str], field_name: str) -> float | None:
    if value is None:
        return None
    if abs(value) > MAX_NUMERIC_10_2:
        stats[f"apply_sanitized_{field_name}_out_of_range"] += 1
        return None
    return float(value)


def _coerce_numeric_10_4(value: Decimal | None, stats: Counter[str], field_name: str) -> float | None:
    if value is None:
        return None
    if abs(value) > MAX_NUMERIC_10_4:
        stats[f"apply_sanitized_{field_name}_out_of_range"] += 1
        return None
    return float(value)


def _notice_to_codice_cnc(notice_id: str) -> str:
    if len(notice_id) < 2:
        return notice_id
    core = notice_id[:-1]
    return f"01.{core}"


def _load_existing_partite(db: Session, anno: int) -> dict[tuple[str, str, str], RuoloPartita]:
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


def _load_notice_map(db: Session, anno: int) -> dict[str, RuoloAvviso]:
    notices = db.scalars(select(RuoloAvviso).where(RuoloAvviso.anno_tributario == anno)).all()
    return {_notice_to_codice_cnc_id(avviso.codice_cnc): avviso for avviso in notices}


def _notice_to_codice_cnc_id(codice_cnc: str) -> str:
    normalized = codice_cnc.replace(".", "")
    return normalized[2:] + "0"


def _iter_incass_notice_payloads(db: Session, anno: int):
    notices = db.scalars(
        select(AnagraficaPaymentNotice).where(
            AnagraficaPaymentNotice.source_system == "incass",
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.raw_detail_json.is_not(None),
        )
    ).all()
    for notice in notices:
        payload = notice.raw_detail_json
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("partitario"), dict):
            partite = payload["partitario"].get("partite")
        else:
            partite = payload.get("partite")
        if not isinstance(partite, list):
            continue
        yield notice, partite


def collect_candidates(db: Session, anno: int) -> tuple[list[CandidateParcel], Counter[str]]:
    stats: Counter[str] = Counter()
    notice_map = _load_notice_map(db, anno)
    partite_map = _load_existing_partite(db, anno)
    existing_keys = _load_existing_parcel_keys(db, anno)
    candidates: list[CandidateParcel] = []

    for notice, partite in _iter_incass_notice_payloads(db, anno):
        stats["incass_notices_scanned"] += 1
        if notice.subject_id is None:
            stats["incass_notices_without_subject"] += 1
            continue
        ruolo_avviso = notice_map.get(notice.source_notice_id)
        if ruolo_avviso is None:
            stats["incass_notices_without_ruolo_avviso"] += 1
            continue
        stats["incass_notices_mapped_to_ruolo"] += 1

        for partita_payload in partite:
            if not isinstance(partita_payload, dict):
                continue
            stats["incass_partite_scanned"] += 1
            codice_partita = _normalize_partita_code(partita_payload.get("codice_partita"))
            comune_nome = _normalize_comune(partita_payload.get("comune_nome"))
            partita = partite_map.get((str(ruolo_avviso.id), codice_partita, comune_nome))
            if partita is None:
                stats["incass_partite_without_ruolo_partita"] += 1
                continue
            stats["incass_partite_mapped_to_ruolo"] += 1

            particelle = partita_payload.get("particelle")
            if not isinstance(particelle, list):
                continue

            for parc_payload in particelle:
                if not isinstance(parc_payload, dict):
                    continue
                stats["incass_particelle_scanned"] += 1
                foglio = _normalize_numeric_token(parc_payload.get("foglio"))
                particella = _normalize_numeric_token(parc_payload.get("particella"))
                subalterno = _normalize_subalterno(parc_payload.get("subalterno"))
                if not foglio or not particella:
                    stats["incass_particelle_invalid_key"] += 1
                    continue
                existing_key = ExistingParcelKey(str(partita.id), foglio, particella, subalterno)
                if existing_key in existing_keys:
                    stats["incass_particelle_already_present"] += 1
                    continue
                existing_keys.add(existing_key)
                stats["incass_particelle_missing_in_ruolo"] += 1
                candidates.append(
                    CandidateParcel(
                        notice_id=notice.source_notice_id,
                        ruolo_avviso_id=str(ruolo_avviso.id),
                        ruolo_partita_id=str(partita.id),
                        subject_id=str(notice.subject_id),
                        display_name=notice.display_name or "",
                        codice_partita=codice_partita,
                        comune_nome=comune_nome,
                        foglio=foglio,
                        particella=particella,
                        subalterno=subalterno,
                        domanda_irrigua=(parc_payload.get("domanda_irrigua") or None),
                        distretto=(parc_payload.get("distretto") or None),
                        sup_catastale_are=_to_decimal(parc_payload.get("sup_catastale_are")),
                        sup_irrigata_ha=_to_decimal(parc_payload.get("sup_irrigata_ha")),
                        coltura=(parc_payload.get("coltura") or None),
                        importo_manut=_to_decimal(parc_payload.get("importo_manut_euro")),
                        importo_irrig=_to_decimal(parc_payload.get("importo_irrig_euro")),
                        importo_ist=_to_decimal(parc_payload.get("importo_ist_euro")),
                    )
                )
    return candidates, stats


def apply_candidates(db: Session, anno: int, candidates: list[CandidateParcel]) -> Counter[str]:
    stats: Counter[str] = Counter()
    partite = {
        str(item.id): item
        for item in db.scalars(select(RuoloPartita).where(RuoloPartita.id.in_([uuid.UUID(candidate.ruolo_partita_id) for candidate in candidates]))).all()
    }
    for candidate in candidates:
        try:
            with db.begin_nested():
                partita = partite[candidate.ruolo_partita_id]
                comune_nome = _normalize_partita_comune_nome(partita.comune_nome)
                sezione_hint = _resolve_section_hint_for_ruolo_comune(comune_nome)
                catasto_parcel_id = None
                cat_particella_id = None
                cat_particella_match_status = "unmatched"
                cat_particella_match_confidence = None
                cat_particella_match_reason = "catasto_parcel_not_resolved"

                try:
                    catasto_parcel_id = _upsert_catasto_parcel(
                        db,
                        comune_nome=comune_nome,
                        foglio=candidate.foglio,
                        particella=candidate.particella,
                        subalterno=candidate.subalterno or None,
                        sup_catastale_are=candidate.sup_catastale_are,
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
                    stats["apply_match_resolution_errors"] += 1

                sup_catastale_ha = _sup_ha_from_are(candidate.sup_catastale_are)
                row = RuoloParticella(
                    id=uuid.uuid4(),
                    partita_id=uuid.UUID(candidate.ruolo_partita_id),
                    anno_tributario=anno,
                    domanda_irrigua=candidate.domanda_irrigua,
                    distretto=candidate.distretto,
                    foglio=candidate.foglio,
                    particella=candidate.particella,
                    subalterno=candidate.subalterno or None,
                    sup_catastale_are=_coerce_numeric_10_4(candidate.sup_catastale_are, stats, "sup_catastale_are"),
                    sup_catastale_ha=_coerce_numeric_10_4(sup_catastale_ha, stats, "sup_catastale_ha"),
                    sup_irrigata_ha=_coerce_numeric_10_4(candidate.sup_irrigata_ha, stats, "sup_irrigata_ha"),
                    coltura=candidate.coltura,
                    importo_manut=_coerce_numeric_10_2(candidate.importo_manut, stats, "importo_manut"),
                    importo_irrig=_coerce_numeric_10_2(candidate.importo_irrig, stats, "importo_irrig"),
                    importo_ist=_coerce_numeric_10_2(candidate.importo_ist, stats, "importo_ist"),
                    catasto_parcel_id=catasto_parcel_id,
                    cat_particella_id=cat_particella_id,
                    cat_particella_match_status=cat_particella_match_status,
                    cat_particella_match_confidence=cat_particella_match_confidence,
                    cat_particella_match_reason=cat_particella_match_reason,
                )
                db.add(row)
                db.flush()

            stats["applied_rows"] += 1
            stats[f"applied_match_status_{cat_particella_match_status}"] += 1
            if cat_particella_match_confidence:
                stats[f"applied_match_confidence_{cat_particella_match_confidence}"] += 1
            if cat_particella_match_reason:
                stats[f"applied_match_reason_{cat_particella_match_reason}"] += 1
        except Exception:
            stats["apply_row_errors"] += 1
            db.rollback()
            continue
    db.commit()
    return stats


def write_candidates_csv(path: Path, candidates: list[CandidateParcel]) -> None:
    fieldnames = [
        "notice_id",
        "ruolo_avviso_id",
        "ruolo_partita_id",
        "subject_id",
        "display_name",
        "codice_partita",
        "comune_nome",
        "foglio",
        "particella",
        "subalterno",
        "domanda_irrigua",
        "distretto",
        "sup_catastale_are",
        "sup_irrigata_ha",
        "coltura",
        "importo_manut",
        "importo_irrig",
        "importo_ist",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in candidates:
            writer.writerow(
                {
                    "notice_id": item.notice_id,
                    "ruolo_avviso_id": item.ruolo_avviso_id,
                    "ruolo_partita_id": item.ruolo_partita_id,
                    "subject_id": item.subject_id,
                    "display_name": item.display_name,
                    "codice_partita": item.codice_partita,
                    "comune_nome": item.comune_nome,
                    "foglio": item.foglio,
                    "particella": item.particella,
                    "subalterno": item.subalterno,
                    "domanda_irrigua": item.domanda_irrigua,
                    "distretto": item.distretto,
                    "sup_catastale_are": str(item.sup_catastale_are) if item.sup_catastale_are is not None else "",
                    "sup_irrigata_ha": str(item.sup_irrigata_ha) if item.sup_irrigata_ha is not None else "",
                    "coltura": item.coltura,
                    "importo_manut": str(item.importo_manut) if item.importo_manut is not None else "",
                    "importo_irrig": str(item.importo_irrig) if item.importo_irrig is not None else "",
                    "importo_ist": str(item.importo_ist) if item.importo_ist is not None else "",
                }
            )


def write_summary(path: Path, *, anno: int, stats: Counter[str], apply_stats: Counter[str], candidates_path: Path) -> None:
    top_comuni = Counter(item["comune_nome"] for item in csv.DictReader(candidates_path.open("r", encoding="utf-8"))).most_common(20)
    lines = [
        f"# Backfill ruolo_particelle da inCass - {anno}",
        "",
        "## Sintesi",
        "",
        f"- Notice inCass scansionate: `{stats['incass_notices_scanned']}`",
        f"- Notice mappate su `ruolo_avvisi`: `{stats['incass_notices_mapped_to_ruolo']}`",
        f"- Partite inCass scansionate: `{stats['incass_partite_scanned']}`",
        f"- Partite mappate su `ruolo_partite`: `{stats['incass_partite_mapped_to_ruolo']}`",
        f"- Particelle inCass scansionate: `{stats['incass_particelle_scanned']}`",
        f"- Particelle già presenti in `ruolo_particelle`: `{stats['incass_particelle_already_present']}`",
        f"- Candidati backfill: `{stats['incass_particelle_missing_in_ruolo']}`",
        f"- Righe applicate: `{apply_stats.get('applied_rows', 0)}`",
        "",
        "## Top comuni candidati",
        "",
    ]
    lines.extend([f"- `{comune}`: `{count}`" for comune, count in top_comuni] or ["- Nessuno"])
    if apply_stats:
        lines.extend(["", "## Esito apply", ""])
        for key in sorted(apply_stats):
            lines.append(f"- `{key}`: `{apply_stats[key]}`")
    lines.extend(["", "## File generati", "", f"- `{candidates_path.name}`"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        candidates, stats = collect_candidates(db, args.anno)
        candidates_path = output_dir / f"ruolo_particelle_backfill_incass_{args.anno}_candidates.csv"
        write_candidates_csv(candidates_path, candidates)

        apply_stats: Counter[str] = Counter()
        if args.apply and candidates:
            apply_stats = apply_candidates(db, args.anno, candidates)
        elif args.apply:
            db.commit()
    finally:
        db.close()

    summary_path = output_dir / f"ruolo_particelle_backfill_incass_{args.anno}_summary.md"
    write_summary(summary_path, anno=args.anno, stats=stats, apply_stats=apply_stats, candidates_path=candidates_path)

    print(
        f"anno={args.anno} candidates={stats['incass_particelle_missing_in_ruolo']} "
        f"already_present={stats['incass_particelle_already_present']} applied={apply_stats.get('applied_rows', 0)}"
    )
    print(f"summary={summary_path}")
    print(f"candidates_csv={candidates_path}")


if __name__ == "__main__":
    main()
