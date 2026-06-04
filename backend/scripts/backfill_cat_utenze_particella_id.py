#!/usr/bin/env python
from __future__ import annotations

"""
Riconcilia `cat_utenze_irrigue.particella_id` verso `cat_particelle`.

Strategia:
- lavora solo su utenze con `particella_id IS NULL`
- richiede `foglio` e `particella`
- prova prima un match esatto su `(comune, foglio, particella)`
- in fallback usa una chiave normalizzata che rimuove zeri iniziali e spazi
- applica solo match univoci
- aggiorna anche i campi catastali dell'utenza e chiude l'anomalia
  `VAL-05-particella_assente`

Uso:
  python backend/scripts/backfill_cat_utenze_particella_id.py
  python backend/scripts/backfill_cat_utenze_particella_id.py --apply
  python backend/scripts/backfill_cat_utenze_particella_id.py --apply --report-csv tmp/utenze_particella_unmatched.csv
"""

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable
from uuid import UUID

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAnomalia, CatParticella, CatUtenzaIrrigua

PARTICELLA_ANOMALIA_TYPE = "VAL-05-particella_assente"
SCRIPT_NOTE = "Collegamento automatico particella da chiave catastale"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill utenze irrigue -> particelle correnti.")
    parser.add_argument("--apply", action="store_true", help="Applica le modifiche. Default: dry-run.")
    parser.add_argument("--limit", type=int, default=None, help="Limita il numero di utenze analizzate.")
    parser.add_argument("--batch-size", type=int, default=2000, help="Dimensione batch commit in apply.")
    parser.add_argument(
        "--report-csv",
        type=Path,
        default=None,
        help="Esporta gli unmatched/ambiguous in CSV.",
    )
    return parser.parse_args()


def _norm_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _norm_catasto(value: str | None) -> str | None:
    stripped = _norm_text(value)
    if stripped is None:
        return None
    upper = stripped.upper()
    if upper.isdigit():
        normalized = upper.lstrip("0")
        return normalized or "0"
    return upper


def _norm_section(value: str | None) -> str | None:
    stripped = _norm_text(value)
    return stripped.upper() if stripped else None


@dataclass(frozen=True)
class ParticellaLite:
    id: UUID
    comune_id: UUID | None
    cod_comune_capacitas: int
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str
    particella: str
    subalterno: str | None


@dataclass(frozen=True)
class UtenzaLite:
    id: UUID
    comune_id: UUID | None
    cod_comune_capacitas: int | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None


@dataclass(frozen=True)
class MatchResult:
    utenza_id: UUID
    particella_id: UUID | None
    strategy: str
    reason: str | None = None


def _raw_key(comune_id: UUID | None, cod_comune_capacitas: int | None, foglio: str | None, particella: str | None) -> tuple[str, str, str] | None:
    foglio_raw = _norm_text(foglio)
    particella_raw = _norm_text(particella)
    if foglio_raw is None or particella_raw is None:
        return None
    comune_token = str(comune_id) if comune_id is not None else f"cap:{cod_comune_capacitas}" if cod_comune_capacitas is not None else None
    if comune_token is None:
        return None
    return comune_token, foglio_raw, particella_raw


def _normalized_key(
    comune_id: UUID | None, cod_comune_capacitas: int | None, foglio: str | None, particella: str | None
) -> tuple[str, str, str] | None:
    foglio_norm = _norm_catasto(foglio)
    particella_norm = _norm_catasto(particella)
    if foglio_norm is None or particella_norm is None:
        return None
    comune_token = str(comune_id) if comune_id is not None else f"cap:{cod_comune_capacitas}" if cod_comune_capacitas is not None else None
    if comune_token is None:
        return None
    return comune_token, foglio_norm, particella_norm


def _load_particelle() -> tuple[dict[tuple[str, str, str], list[ParticellaLite]], dict[tuple[str, str, str], list[ParticellaLite]]]:
    with SessionLocal() as db:
        rows = (
            db.execute(
                select(
                    CatParticella.id,
                    CatParticella.comune_id,
                    CatParticella.cod_comune_capacitas,
                    CatParticella.nome_comune,
                    CatParticella.sezione_catastale,
                    CatParticella.foglio,
                    CatParticella.particella,
                    CatParticella.subalterno,
                ).where(CatParticella.is_current.is_(True), CatParticella.suppressed.is_(False))
            )
            .all()
        )

    raw_index: dict[tuple[str, str, str], list[ParticellaLite]] = defaultdict(list)
    normalized_index: dict[tuple[str, str, str], list[ParticellaLite]] = defaultdict(list)

    for row in rows:
        item = ParticellaLite(*row)
        raw_key = _raw_key(item.comune_id, item.cod_comune_capacitas, item.foglio, item.particella)
        if raw_key is not None:
            raw_index[raw_key].append(item)
        normalized_key = _normalized_key(item.comune_id, item.cod_comune_capacitas, item.foglio, item.particella)
        if normalized_key is not None:
            normalized_index[normalized_key].append(item)

    return raw_index, normalized_index


def _load_target_utenze(limit: int | None) -> list[UtenzaLite]:
    with SessionLocal() as db:
        stmt = select(
            CatUtenzaIrrigua.id,
            CatUtenzaIrrigua.comune_id,
            CatUtenzaIrrigua.cod_comune_capacitas,
            CatUtenzaIrrigua.nome_comune,
            CatUtenzaIrrigua.sezione_catastale,
            CatUtenzaIrrigua.foglio,
            CatUtenzaIrrigua.particella,
            CatUtenzaIrrigua.subalterno,
        ).where(
            CatUtenzaIrrigua.particella_id.is_(None),
            CatUtenzaIrrigua.foglio.is_not(None),
            CatUtenzaIrrigua.particella.is_not(None),
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = db.execute(stmt).all()
    return [UtenzaLite(*row) for row in rows]


def _pick_unique_match(candidates: list[ParticellaLite], *, exact_section: str | None) -> tuple[UUID | None, str, str | None]:
    if not candidates:
        return None, "unmatched", "no_candidate"
    if len(candidates) == 1:
        return candidates[0].id, "matched", None

    if exact_section is not None:
        section_matches = [item for item in candidates if _norm_section(item.sezione_catastale) == exact_section]
        if len(section_matches) == 1:
            return section_matches[0].id, "matched", None

    base_candidates = [item for item in candidates if _norm_text(item.subalterno) is None]
    if len(base_candidates) == 1:
        return base_candidates[0].id, "matched", "base_subalterno_fallback"

    return None, "ambiguous", "multiple_candidates"


def preview_matches(
    *,
    raw_index: dict[tuple[str, str, str], list[ParticellaLite]],
    normalized_index: dict[tuple[str, str, str], list[ParticellaLite]],
    utenze: Iterable[UtenzaLite],
) -> tuple[list[MatchResult], Counter[str]]:
    results: list[MatchResult] = []
    stats: Counter[str] = Counter()

    for utenza in utenze:
        raw_key = _raw_key(utenza.comune_id, utenza.cod_comune_capacitas, utenza.foglio, utenza.particella)
        norm_key = _normalized_key(utenza.comune_id, utenza.cod_comune_capacitas, utenza.foglio, utenza.particella)
        exact_section = _norm_section(utenza.sezione_catastale)

        candidates = raw_index.get(raw_key, []) if raw_key is not None else []
        particella_id, status, reason = _pick_unique_match(candidates, exact_section=exact_section)
        strategy = "raw_key"

        if particella_id is None and status == "unmatched" and norm_key is not None:
            candidates = normalized_index.get(norm_key, [])
            particella_id, status, reason = _pick_unique_match(candidates, exact_section=exact_section)
            strategy = "normalized_key"

        if particella_id is not None:
            stats["matched"] += 1
            stats[f"matched:{strategy}"] += 1
            if reason:
                stats[f"matched_reason:{reason}"] += 1
        else:
            stats[status] += 1
            if reason:
                stats[f"{status}_reason:{reason}"] += 1

        results.append(MatchResult(utenza_id=utenza.id, particella_id=particella_id, strategy=strategy, reason=reason))

    return results, stats


def _export_report(path: Path, utenze: dict[UUID, UtenzaLite], matches: list[MatchResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "utenza_id",
                "cod_comune_capacitas",
                "nome_comune",
                "sezione_catastale",
                "foglio",
                "particella",
                "subalterno",
                "status",
                "strategy",
                "reason",
            ],
        )
        writer.writeheader()
        for result in matches:
            if result.particella_id is not None:
                continue
            utenza = utenze[result.utenza_id]
            writer.writerow(
                {
                    "utenza_id": str(utenza.id),
                    "cod_comune_capacitas": utenza.cod_comune_capacitas,
                    "nome_comune": utenza.nome_comune,
                    "sezione_catastale": utenza.sezione_catastale,
                    "foglio": utenza.foglio,
                    "particella": utenza.particella,
                    "subalterno": utenza.subalterno,
                    "status": "ambiguous" if result.reason == "multiple_candidates" else "unmatched",
                    "strategy": result.strategy,
                    "reason": result.reason,
                }
            )


def _apply_matches(matches: list[MatchResult], *, batch_size: int) -> Counter[str]:
    match_map = {item.utenza_id: item.particella_id for item in matches if item.particella_id is not None}
    if not match_map:
        return Counter()

    stats: Counter[str] = Counter()
    with SessionLocal() as db:
        script_user = db.execute(
            select(ApplicationUser).where(ApplicationUser.username == "admin")
        ).scalar_one_or_none()

        utenze = (
            db.execute(select(CatUtenzaIrrigua).where(CatUtenzaIrrigua.id.in_(list(match_map.keys()))))
            .scalars()
            .all()
        )
        particella_ids = list({pid for pid in match_map.values() if pid is not None})
        particelle = {
            item.id: item
            for item in db.execute(select(CatParticella).where(CatParticella.id.in_(particella_ids))).scalars().all()
        }
        anomalies_by_utenza: dict[UUID, list[CatAnomalia]] = defaultdict(list)
        for anomalia in (
            db.execute(
                select(CatAnomalia).where(
                    CatAnomalia.utenza_id.in_(list(match_map.keys())),
                    CatAnomalia.tipo == PARTICELLA_ANOMALIA_TYPE,
                    CatAnomalia.status == "aperta",
                )
            )
            .scalars()
            .all()
        ):
            if anomalia.utenza_id is not None:
                anomalies_by_utenza[anomalia.utenza_id].append(anomalia)

        pending = 0
        for utenza in utenze:
            particella_id = match_map.get(utenza.id)
            if particella_id is None:
                continue
            particella = particelle.get(particella_id)
            if particella is None:
                stats["missing_particella"] += 1
                continue

            utenza.particella_id = particella.id
            utenza.cod_comune_capacitas = particella.cod_comune_capacitas
            utenza.nome_comune = particella.nome_comune
            utenza.sezione_catastale = particella.sezione_catastale
            utenza.foglio = particella.foglio
            utenza.particella = particella.particella
            utenza.subalterno = particella.subalterno
            utenza.anomalia_particella_assente = False
            db.add(utenza)
            stats["updated_utenze"] += 1

            for anomalia in anomalies_by_utenza.get(utenza.id, []):
                anomalia.particella_id = particella.id
                anomalia.status = "chiusa"
                anomalia.note_operatore = SCRIPT_NOTE
                if script_user is not None:
                    anomalia.assigned_to = script_user.id
                db.add(anomalia)
                stats["closed_anomalies"] += 1

            pending += 1
            if pending >= batch_size:
                db.commit()
                pending = 0

        if pending:
            db.commit()
        else:
            db.rollback()

    return stats


def main() -> None:
    args = parse_args()

    raw_index, normalized_index = _load_particelle()
    utenze = _load_target_utenze(args.limit)
    utenze_by_id = {item.id: item for item in utenze}
    matches, stats = preview_matches(raw_index=raw_index, normalized_index=normalized_index, utenze=utenze)

    print(f"utenze_target={len(utenze)}")
    for key in sorted(stats):
        print(f"{key}={stats[key]}")

    if args.report_csv is not None:
        _export_report(args.report_csv, utenze_by_id, matches)
        print(f"report_csv={args.report_csv}")

    if not args.apply:
        return

    apply_stats = _apply_matches(matches, batch_size=args.batch_size)
    for key in sorted(apply_stats):
        print(f"{key}={apply_stats[key]}")


if __name__ == "__main__":
    main()
