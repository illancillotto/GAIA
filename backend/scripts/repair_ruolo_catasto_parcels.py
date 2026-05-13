#!/usr/bin/env python
"""
Ripara gli agganci Ruolo -> catasto_parcels dopo import con comuni non normalizzati.

Uso:
  DATABASE_URL=... python backend/scripts/repair_ruolo_catasto_parcels.py --apply
"""
from __future__ import annotations

import argparse
from collections import Counter

from sqlalchemy import and_, func, or_, select, text

from app.core.database import SessionLocal
from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.modules.ruolo.services.import_service import (
    _ORISTANO_FRAZIONE_SECTION_HINTS,
    _resolve_comune_codice_for_ruolo,
    _resolve_section_hint_for_ruolo_comune,
    _upsert_catasto_parcel,
    resolve_cat_particella_match,
)
from app.modules.ruolo.services.parser import _normalize_partita_comune_nome


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalizza comuni Ruolo e ricostruisce catasto_parcels mancanti."
    )
    parser.add_argument("--apply", action="store_true", help="Esegue le modifiche. Senza flag fa solo dry-run.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--cleanup-dirty-orphans",
        action="store_true",
        help="Elimina catasto_parcels orfani con foglio/particella non numerici.",
    )
    parser.add_argument(
        "--repair-comune-mismatch",
        action="store_true",
        help="Ricostruisce catasto_parcel_id quando il codice comune risolto non coincide con la partita ruolo.",
    )
    parser.add_argument(
        "--repair-unlinked-matches",
        action="store_true",
        help="Ricalcola cat_particella_id per le righe ancora non collegate ma con catasto_parcel_id presente.",
    )
    parser.add_argument(
        "--repair-oristano-frazione-sections",
        action="store_true",
        help="Ricalcola i match delle frazioni catastali Oristano note usando la sezione corretta.",
    )
    return parser.parse_args()


def normalize_ruolo_partite(*, apply: bool) -> int:
    changed = 0
    with SessionLocal() as db:
        partite = db.scalars(select(RuoloPartita)).all()
        for partita in partite:
            normalized = _normalize_partita_comune_nome(partita.comune_nome)
            if normalized != partita.comune_nome:
                changed += 1
                if apply:
                    partita.comune_nome = normalized
        if apply:
            db.commit()
        else:
            db.rollback()
    return changed


def repair_unresolved_rows(*, apply: bool, batch_size: int, limit: int | None) -> Counter[str]:
    stats: Counter[str] = Counter()
    processed = 0
    last_id = None

    while True:
        remaining = None if limit is None else max(limit - processed, 0)
        if remaining == 0:
            break
        current_batch_size = min(batch_size, remaining) if remaining is not None else batch_size

        with SessionLocal() as db:
            rows = db.execute(
                select(RuoloParticella, RuoloPartita)
                .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
                .where(
                    and_(
                        or_(
                            RuoloParticella.catasto_parcel_id.is_(None),
                            RuoloParticella.cat_particella_match_reason == "catasto_parcel_not_resolved",
                        ),
                        RuoloParticella.id > last_id if last_id is not None else True,
                    )
                )
                .order_by(RuoloParticella.id)
                .limit(current_batch_size)
            ).all()

            if not rows:
                db.rollback()
                break

            for ruolo_particella, ruolo_partita in rows:
                processed += 1
                stats["processed"] += 1
                last_id = ruolo_particella.id

                comune_nome = _normalize_partita_comune_nome(ruolo_partita.comune_nome)
                sezione_hint = _resolve_section_hint_for_ruolo_comune(comune_nome)
                if comune_nome != ruolo_partita.comune_nome:
                    stats["normalized_partita_rows"] += 1
                    if apply:
                        ruolo_partita.comune_nome = comune_nome

                catasto_parcel_id = _upsert_catasto_parcel(
                    db,
                    comune_nome=comune_nome,
                    foglio=ruolo_particella.foglio,
                    particella=ruolo_particella.particella,
                    subalterno=ruolo_particella.subalterno,
                    sup_catastale_are=ruolo_particella.sup_catastale_are,
                    anno=ruolo_particella.anno_tributario,
                )

                if catasto_parcel_id is None:
                    stats["catasto_parcel_not_resolved"] += 1
                    if apply:
                        ruolo_particella.catasto_parcel_id = None
                        ruolo_particella.cat_particella_id = None
                        ruolo_particella.cat_particella_match_status = "unmatched"
                        ruolo_particella.cat_particella_match_confidence = None
                        ruolo_particella.cat_particella_match_reason = "catasto_parcel_not_resolved"
                    continue

                catasto_parcel = db.get(CatastoParcel, catasto_parcel_id)
                if catasto_parcel is None:
                    stats["catasto_parcel_not_loaded"] += 1
                    continue

                (
                    cat_particella_id,
                    match_status,
                    match_confidence,
                    match_reason,
                ) = resolve_cat_particella_match(
                    db,
                    comune_codice=catasto_parcel.comune_codice,
                    foglio=catasto_parcel.foglio,
                    particella=catasto_parcel.particella,
                    subalterno=catasto_parcel.subalterno,
                    sezione_catastale=sezione_hint,
                )

                stats[f"match_status:{match_status}"] += 1
                if match_reason:
                    stats[f"match_reason:{match_reason}"] += 1

                if apply:
                    ruolo_particella.catasto_parcel_id = catasto_parcel_id
                    ruolo_particella.cat_particella_id = cat_particella_id
                    ruolo_particella.cat_particella_match_status = match_status
                    ruolo_particella.cat_particella_match_confidence = match_confidence
                    ruolo_particella.cat_particella_match_reason = match_reason

            if apply:
                db.commit()
            else:
                db.rollback()

            if len(rows) < current_batch_size:
                break

    return stats


def cleanup_dirty_orphans(*, apply: bool) -> int:
    query = text(
        """
        WITH dirty AS (
            SELECT cp.id
            FROM catasto_parcels cp
            WHERE NOT EXISTS (
                SELECT 1 FROM ruolo_particelle rp WHERE rp.catasto_parcel_id = cp.id
            )
              AND (cp.foglio !~ '^[0-9]+$' OR cp.particella !~ '^[0-9]+$')
        )
        DELETE FROM catasto_parcels cp
        USING dirty
        WHERE cp.id = dirty.id
        RETURNING cp.id
        """
    )
    count_query = text(
        """
        SELECT count(*)
        FROM catasto_parcels cp
        WHERE NOT EXISTS (
            SELECT 1 FROM ruolo_particelle rp WHERE rp.catasto_parcel_id = cp.id
        )
          AND (cp.foglio !~ '^[0-9]+$' OR cp.particella !~ '^[0-9]+$')
        """
    )

    with SessionLocal() as db:
        if apply:
            deleted = len(db.execute(query).all())
            db.commit()
            return deleted
        count = int(db.scalar(count_query) or 0)
        db.rollback()
        return count


def repair_comune_mismatch(*, apply: bool, batch_size: int, limit: int | None) -> Counter[str]:
    stats: Counter[str] = Counter()
    processed = 0
    last_id = None

    while True:
        remaining = None if limit is None else max(limit - processed, 0)
        if remaining == 0:
            break
        current_batch_size = min(batch_size, remaining) if remaining is not None else batch_size

        with SessionLocal() as db:
            rows = db.execute(
                select(RuoloParticella, RuoloPartita, CatastoParcel)
                .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
                .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
                .where(RuoloParticella.id > last_id if last_id is not None else True)
                .order_by(RuoloParticella.id)
                .limit(current_batch_size)
            ).all()

            if not rows:
                db.rollback()
                break

            for ruolo_particella, ruolo_partita, current_parcel in rows:
                processed += 1
                last_id = ruolo_particella.id
                expected_codice = _resolve_comune_codice_for_ruolo(db, ruolo_partita.comune_nome)
                if not expected_codice:
                    stats["expected_comune_not_resolved"] += 1
                    continue
                if current_parcel.comune_codice == expected_codice:
                    stats["already_ok"] += 1
                    continue

                stats["mismatch"] += 1
                sezione_hint = _resolve_section_hint_for_ruolo_comune(ruolo_partita.comune_nome)
                catasto_parcel_id = _upsert_catasto_parcel(
                    db,
                    comune_nome=ruolo_partita.comune_nome,
                    foglio=ruolo_particella.foglio,
                    particella=ruolo_particella.particella,
                    subalterno=ruolo_particella.subalterno,
                    sup_catastale_are=ruolo_particella.sup_catastale_are,
                    anno=ruolo_particella.anno_tributario,
                )
                if catasto_parcel_id is None:
                    stats["catasto_parcel_not_resolved"] += 1
                    continue

                catasto_parcel = db.get(CatastoParcel, catasto_parcel_id)
                if catasto_parcel is None:
                    stats["catasto_parcel_not_loaded"] += 1
                    continue

                (
                    cat_particella_id,
                    match_status,
                    match_confidence,
                    match_reason,
                ) = resolve_cat_particella_match(
                    db,
                    comune_codice=catasto_parcel.comune_codice,
                    foglio=catasto_parcel.foglio,
                    particella=catasto_parcel.particella,
                    subalterno=catasto_parcel.subalterno,
                    sezione_catastale=sezione_hint,
                )

                stats[f"mismatch_match_status:{match_status}"] += 1
                if match_reason:
                    stats[f"mismatch_match_reason:{match_reason}"] += 1

                if apply:
                    ruolo_particella.catasto_parcel_id = catasto_parcel_id
                    ruolo_particella.cat_particella_id = cat_particella_id
                    ruolo_particella.cat_particella_match_status = match_status
                    ruolo_particella.cat_particella_match_confidence = match_confidence
                    ruolo_particella.cat_particella_match_reason = match_reason

            if apply:
                db.commit()
            else:
                db.rollback()

            if len(rows) < current_batch_size:
                break

    stats["processed_for_mismatch"] = processed
    return stats


def repair_unlinked_matches(*, apply: bool, batch_size: int, limit: int | None) -> Counter[str]:
    stats: Counter[str] = Counter()
    processed = 0
    last_id = None

    while True:
        remaining = None if limit is None else max(limit - processed, 0)
        if remaining == 0:
            break
        current_batch_size = min(batch_size, remaining) if remaining is not None else batch_size

        with SessionLocal() as db:
            rows = db.execute(
                select(RuoloParticella, CatastoParcel, RuoloPartita)
                .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
                .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
                .where(
                    and_(
                        RuoloParticella.cat_particella_id.is_(None),
                        RuoloParticella.id > last_id if last_id is not None else True,
                    )
                )
                .order_by(RuoloParticella.id)
                .limit(current_batch_size)
            ).all()

            if not rows:
                db.rollback()
                break

            for ruolo_particella, catasto_parcel, ruolo_partita in rows:
                processed += 1
                last_id = ruolo_particella.id
                stats["processed_unlinked"] += 1
                sezione_hint = _resolve_section_hint_for_ruolo_comune(ruolo_partita.comune_nome)

                (
                    cat_particella_id,
                    match_status,
                    match_confidence,
                    match_reason,
                ) = resolve_cat_particella_match(
                    db,
                    comune_codice=catasto_parcel.comune_codice,
                    foglio=catasto_parcel.foglio,
                    particella=catasto_parcel.particella,
                    subalterno=catasto_parcel.subalterno,
                    sezione_catastale=sezione_hint,
                )

                stats[f"unlinked_match_status:{match_status}"] += 1
                if match_reason:
                    stats[f"unlinked_match_reason:{match_reason}"] += 1

                if apply:
                    ruolo_particella.cat_particella_id = cat_particella_id
                    ruolo_particella.cat_particella_match_status = match_status
                    ruolo_particella.cat_particella_match_confidence = match_confidence
                    ruolo_particella.cat_particella_match_reason = match_reason

            if apply:
                db.commit()
            else:
                db.rollback()

            if len(rows) < current_batch_size:
                break

    return stats


def repair_oristano_frazione_sections(*, apply: bool, batch_size: int, limit: int | None) -> Counter[str]:
    stats: Counter[str] = Counter()
    processed = 0
    last_id = None
    frazioni = tuple(_ORISTANO_FRAZIONE_SECTION_HINTS.keys())

    while True:
        remaining = None if limit is None else max(limit - processed, 0)
        if remaining == 0:
            break
        current_batch_size = min(batch_size, remaining) if remaining is not None else batch_size

        with SessionLocal() as db:
            rows = db.execute(
                select(RuoloParticella, CatastoParcel, RuoloPartita)
                .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
                .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
                .where(
                    and_(
                        func.upper(func.trim(RuoloPartita.comune_nome)).in_(frazioni),
                        RuoloParticella.id > last_id if last_id is not None else True,
                    )
                )
                .order_by(RuoloParticella.id)
                .limit(current_batch_size)
            ).all()

            if not rows:
                db.rollback()
                break

            for ruolo_particella, catasto_parcel, ruolo_partita in rows:
                processed += 1
                last_id = ruolo_particella.id
                stats["processed_oristano_frazioni"] += 1
                sezione_hint = _resolve_section_hint_for_ruolo_comune(ruolo_partita.comune_nome)

                (
                    cat_particella_id,
                    match_status,
                    match_confidence,
                    match_reason,
                ) = resolve_cat_particella_match(
                    db,
                    comune_codice=catasto_parcel.comune_codice,
                    foglio=catasto_parcel.foglio,
                    particella=catasto_parcel.particella,
                    subalterno=catasto_parcel.subalterno,
                    sezione_catastale=sezione_hint,
                )

                changed = (
                    ruolo_particella.cat_particella_id != cat_particella_id
                    or ruolo_particella.cat_particella_match_status != match_status
                    or ruolo_particella.cat_particella_match_confidence != match_confidence
                    or ruolo_particella.cat_particella_match_reason != match_reason
                )
                stats[f"oristano_frazioni_match_status:{match_status}"] += 1
                if match_reason:
                    stats[f"oristano_frazioni_match_reason:{match_reason}"] += 1
                if changed:
                    stats["oristano_frazioni_changed"] += 1

                if apply and changed:
                    ruolo_particella.cat_particella_id = cat_particella_id
                    ruolo_particella.cat_particella_match_status = match_status
                    ruolo_particella.cat_particella_match_confidence = match_confidence
                    ruolo_particella.cat_particella_match_reason = match_reason

            if apply:
                db.commit()
            else:
                db.rollback()

            if len(rows) < current_batch_size:
                break

    return stats


def print_status() -> None:
    with SessionLocal() as db:
        status_rows = db.execute(
            select(
                RuoloParticella.cat_particella_match_status,
                RuoloParticella.cat_particella_match_reason,
                func.count(),
            )
            .group_by(RuoloParticella.cat_particella_match_status, RuoloParticella.cat_particella_match_reason)
            .order_by(func.count().desc())
        ).all()
        print("match_status")
        for status, reason, count in status_rows:
            print(f"  {status or '-'} | {reason or '-'} | {count}")


def main() -> None:
    args = parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"mode={mode}")

    changed_partite = normalize_ruolo_partite(apply=args.apply)
    print(f"ruolo_partite_normalizzate={changed_partite}")

    stats = repair_unresolved_rows(
        apply=args.apply,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    if args.repair_comune_mismatch:
        stats.update(
            repair_comune_mismatch(
                apply=args.apply,
                batch_size=args.batch_size,
                limit=args.limit,
            )
        )
    if args.repair_unlinked_matches:
        stats.update(
            repair_unlinked_matches(
                apply=args.apply,
                batch_size=args.batch_size,
                limit=args.limit,
            )
        )
    if args.repair_oristano_frazione_sections:
        stats.update(
            repair_oristano_frazione_sections(
                apply=args.apply,
                batch_size=args.batch_size,
                limit=args.limit,
            )
        )
    for key in sorted(stats):
        print(f"{key}={stats[key]}")

    if args.cleanup_dirty_orphans:
        dirty_orphans = cleanup_dirty_orphans(apply=args.apply)
        label = "catasto_parcels_orfani_sporchi_eliminati" if args.apply else "catasto_parcels_orfani_sporchi_eliminabili"
        print(f"{label}={dirty_orphans}")

    print_status()


if __name__ == "__main__":
    main()
