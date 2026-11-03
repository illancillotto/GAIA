#!/usr/bin/env python
"""Registra in GAIA i decessi restituiti da PuntoFisco (workbook R2).

Aggiorna solo le persone senza data di decesso. Non sovrascrive mai una data
gia presente ne lo stato di chi ANPR ha verificato vivo: quei casi vengono
riportati come conflitti da verificare a mano. Il default e dry-run.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.modules.utenze.models import AnagraficaAuditLog, AnagraficaPerson  # noqa: E402

SHEET_NAME = "Persone fisiche"
AUDIT_ACTION = "puntofisco_death_update"
DECEASED = "DECEDUTO"
PRESUMED = "Decesso presunto per limiti di età"


@dataclass(frozen=True)
class DeathRecord:
    cf_inviato: str
    cf_ade: str
    data_decesso: dt.date


@dataclass(frozen=True)
class Outcome:
    cf_ade: str
    subject_id: str
    esito: str
    dettaglio: str


def _as_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return None


def read_death_records(path: Path) -> tuple[list[DeathRecord], Counter[str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows = workbook[SHEET_NAME].iter_rows(values_only=True)
    header = [str(cell) for cell in next(rows)]
    index = {
        name: header.index(name)
        for name in ("CF_Inviato", "Codice_Fiscale", "STATO", "Data_Decesso")
    }
    # La stessa persona puo essere stata richiesta con CF vecchio e nuovo.
    records: dict[tuple[str, str], DeathRecord] = {}
    skipped: Counter[str] = Counter()
    for row in rows:
        stato = row[index["STATO"]]
        if stato == PRESUMED:
            skipped["decesso_presunto"] += 1
            continue
        if stato != DECEASED:
            continue
        data_decesso = _as_date(row[index["Data_Decesso"]])
        if data_decesso is None:
            skipped["data_decesso_mancante"] += 1
            continue
        cf_ade = str(row[index["Codice_Fiscale"]]).strip().upper()
        cf_inviato = str(row[index["CF_Inviato"]]).strip().upper()
        records[(cf_inviato, cf_ade)] = DeathRecord(
            cf_inviato=cf_inviato,
            cf_ade=cf_ade,
            data_decesso=data_decesso,
        )
    workbook.close()
    return list(records.values()), skipped


def _apply_to_person(
    db, person: AnagraficaPerson, record: DeathRecord, *, source: str, dry_run: bool
) -> Outcome:
    subject_id = str(person.subject_id)
    if person.data_decesso is not None:
        if person.data_decesso == record.data_decesso:
            return Outcome(record.cf_ade, subject_id, "gia_allineato", str(person.data_decesso))
        return Outcome(
            record.cf_ade,
            subject_id,
            "conflitto_data",
            f"GAIA {person.data_decesso} / PuntoFisco {record.data_decesso}",
        )
    if person.stato_anpr == "alive":
        return Outcome(
            record.cf_ade, subject_id, "conflitto_anpr_vivo", f"PuntoFisco {record.data_decesso}"
        )

    esito = "data_aggiunta" if person.stato_anpr == "deceased" else "decesso_registrato"
    before = {"data_decesso": None, "stato_anpr": person.stato_anpr}
    after = {"data_decesso": record.data_decesso.isoformat(), "stato_anpr": "deceased"}
    if not dry_run:
        person.data_decesso = record.data_decesso
        person.stato_anpr = "deceased"
        db.add(
            AnagraficaAuditLog(
                subject_id=person.subject_id,
                changed_by_user_id=None,
                action=AUDIT_ACTION,
                diff_json={
                    "before": before,
                    "after": after,
                    "source": source,
                    "cf_inviato": record.cf_inviato,
                    "cf_ade": record.cf_ade,
                },
            )
        )
    return Outcome(record.cf_ade, subject_id, esito, str(record.data_decesso))


def apply_deaths(db, records: list[DeathRecord], *, source: str, dry_run: bool) -> list[Outcome]:
    outcomes: list[Outcome] = []
    seen: set[str] = set()
    for record in records:
        codes = sorted({record.cf_ade, record.cf_inviato})
        persons = db.scalars(
            select(AnagraficaPerson)
            .where(func.upper(func.trim(AnagraficaPerson.codice_fiscale)).in_(codes))
            .with_for_update()
        ).all()
        if not persons:
            outcomes.append(Outcome(record.cf_ade, "", "non_in_gaia", ", ".join(codes)))
            continue
        for person in persons:
            if str(person.subject_id) in seen:
                continue
            seen.add(str(person.subject_id))
            outcomes.append(_apply_to_person(db, person, record, source=source, dry_run=dry_run))
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return outcomes


def write_report(path: Path, outcomes: list[Outcome]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cf_ade", "subject_id", "esito", "dettaglio"])
        writer.writerows((o.cf_ade, o.subject_id, o.esito, o.dettaglio) for o in outcomes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Anagrafica_puntofisco_*_R2.xlsx")
    parser.add_argument("--report", type=Path, required=True, help="CSV con l'esito per soggetto.")
    parser.add_argument(
        "--source", default="puntofisco_2025-12-17", help="Etichetta fonte nell'audit log."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Scrive su GAIA; il default e dry-run."
    )
    args = parser.parse_args(argv)

    records, skipped = read_death_records(args.workbook)
    with SessionLocal() as db:
        outcomes = apply_deaths(db, records, source=args.source, dry_run=not args.apply)
    write_report(args.report, outcomes)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Decessi PuntoFisco ({mode}): {len(records)} deceduti letti")
    for key, value in sorted(skipped.items()):
        print(f"scartati_{key}: {value}")
    for key, value in sorted(Counter(o.esito for o in outcomes).items()):
        print(f"{key}: {value}")
    print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
