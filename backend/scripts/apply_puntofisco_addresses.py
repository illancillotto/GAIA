#!/usr/bin/env python
"""Allinea a PuntoFisco (workbook R2) gli indirizzi di persone fisiche e giuridiche.

`addresses` scrive la residenza / sede dell'Agenzia sull'anagrafica GAIA e sugli
avvisi ruolo del soggetto, da cui solleciti e raccomandate leggono l'indirizzo.
I CF sostituiti dall'Agenzia (esito 0001) restano fuori. Ogni soggetto
aggiornato ha un record di audit con i valori precedenti.

`regenerate` rifa con dati attuali i PDF dei solleciti dei soggetti aggiornati,
stesso numero avviso. Salta quelli gia in una spedizione Posta Online attiva.
Il default di entrambi e dry-run.
"""

from __future__ import annotations

import argparse
import csv
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import func, or_, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.modules.ruolo.models import RuoloAvviso  # noqa: E402
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem  # noqa: E402
from app.modules.ruolo.services import notice_pdf_regeneration as regeneration  # noqa: E402
from app.modules.utenze.models import (  # noqa: E402
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
)
from app.modules.utenze.services.person_history_service import (  # noqa: E402
    person_to_snapshot_payload,
    snapshot_person_if_changed,
)

PERSONS_SHEET = "Persone fisiche"
COMPANIES_SHEET = "Persone giuridiche"
AUDIT_ACTION = "puntofisco_address_update"
OK = "0000"
CF_REPLACED = "0001"
REGENERATION_REASON = "Rigenerazione PDF dopo aggiornamento indirizzi PuntoFisco"


@dataclass(frozen=True)
class Address:
    kind: str  # "person" | "company"
    cf: str
    indirizzo: str
    cap: str | None
    comune: str
    provincia: str | None

    @property
    def comune_label(self) -> str:
        return f"{self.comune} ({self.provincia})" if self.provincia else self.comune

    @property
    def avviso_text(self) -> str:
        # Same shape as the role files: "VIA TUVERI 11 09092 ARBOREA OR".
        return " ".join(p for p in (self.indirizzo, self.cap, self.comune, self.provincia) if p)


@dataclass(frozen=True)
class Outcome:
    cf: str
    subject_id: str
    esito: str
    avvisi: int
    prima: str
    dopo: str


def _text(value: object) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return text.upper() or None


def _rows(workbook, sheet: str) -> list[dict[str, object]]:
    rows = workbook[sheet].iter_rows(values_only=True)
    header = [str(cell) for cell in next(rows)]
    return [dict(zip(header, row, strict=False)) for row in rows]


def read_addresses(path: Path) -> tuple[list[Address], Counter[str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    persons = _rows(workbook, PERSONS_SHEET)
    companies = _rows(workbook, COMPANIES_SHEET)
    workbook.close()
    # Both the old and the new code of a replaced CF stay out, whatever row they are on.
    replaced = {
        _text(row[key])
        for row in persons
        if row["Esito"] == CF_REPLACED
        for key in ("CF_Inviato", "Codice_Fiscale")
    }
    sources = [("person", row, "Indirizzo_Residenza_AdE", "Com_Residenza") for row in persons] + [
        ("company", row, "Indirizzo_Sede", "Comune_Sede") for row in companies
    ]
    addresses: dict[str, Address] = {}
    skipped: Counter[str] = Counter()
    for kind, row, address_key, city_key in sources:
        cf = _text(row["Codice_Fiscale"])
        if cf in replaced or _text(row["CF_Inviato"]) in replaced:
            skipped["cf_anomalo"] += 1
            continue
        if row["Esito"] != OK:
            skipped[f"esito_{row['Esito']}"] += 1
            continue
        indirizzo, comune = _text(row[address_key]), _text(row[city_key])
        if not indirizzo or not comune:
            skipped["indirizzo_mancante"] += 1
            continue
        addresses[cf] = Address(kind, cf, indirizzo, _text(row["CAP"]), comune, _text(row["PR"]))
    return list(addresses.values()), skipped


def _find_subject(db, address: Address):
    if address.kind == "person":
        return db.scalar(
            select(AnagraficaPerson)
            .where(func.upper(func.trim(AnagraficaPerson.codice_fiscale)) == address.cf)
            .with_for_update()
        )
    return db.scalar(
        select(AnagraficaCompany)
        .where(
            or_(
                func.upper(func.trim(AnagraficaCompany.partita_iva)) == address.cf,
                func.upper(func.trim(AnagraficaCompany.codice_fiscale)) == address.cf,
            )
        )
        .with_for_update()
    )


def _current(entity) -> tuple[str | None, str | None, str | None]:
    if isinstance(entity, AnagraficaPerson):
        return entity.indirizzo, entity.cap, entity.comune_residenza
    return entity.sede_legale, entity.cap, entity.comune_sede


def _write(db, entity, address: Address, source: str) -> None:
    if isinstance(entity, AnagraficaPerson):
        new_data = {
            **person_to_snapshot_payload(entity),
            "indirizzo": address.indirizzo,
            "cap": address.cap,
            "comune_residenza": address.comune_label,
        }
        snapshot_person_if_changed(
            db, entity, new_data, source_system="puntofisco", source_ref=source
        )
        entity.indirizzo, entity.comune_residenza = address.indirizzo, address.comune_label
    else:
        entity.sede_legale, entity.comune_sede = address.indirizzo, address.comune_label
    entity.cap = address.cap


def _apply_one(db, entity, address: Address, *, source: str, dry_run: bool) -> Outcome:
    before = _current(entity)
    after = (address.indirizzo, address.cap, address.comune_label)
    avvisi = [
        avviso
        for avviso in db.scalars(
            select(RuoloAvviso).where(RuoloAvviso.subject_id == entity.subject_id).with_for_update()
        )
        if avviso.residenza_raw != address.avviso_text
        or avviso.domicilio_raw != address.avviso_text
    ]
    changed = before != after
    esito = "aggiornato" if changed else ("solo_avvisi" if avvisi else "gia_allineato")
    if not dry_run and (changed or avvisi):
        db.add(
            AnagraficaAuditLog(
                subject_id=entity.subject_id,
                changed_by_user_id=None,
                action=AUDIT_ACTION,
                diff_json={
                    "before": dict(zip(("indirizzo", "cap", "comune"), before, strict=True)),
                    "after": dict(zip(("indirizzo", "cap", "comune"), after, strict=True)),
                    "avvisi_before": [
                        [str(a.id), a.residenza_raw, a.domicilio_raw] for a in avvisi
                    ],
                    "source": source,
                },
            )
        )
        if changed:
            _write(db, entity, address, source)
        for avviso in avvisi:
            avviso.residenza_raw = avviso.domicilio_raw = address.avviso_text
    return Outcome(
        address.cf,
        str(entity.subject_id),
        esito,
        len(avvisi),
        " ".join(p for p in before if p),
        " ".join(after_part for after_part in after if after_part),
    )


def apply_addresses(db, addresses: list[Address], *, source: str, dry_run: bool) -> list[Outcome]:
    outcomes: list[Outcome] = []
    seen: set[str] = set()
    for address in addresses:
        entity = _find_subject(db, address)
        if entity is None:
            outcomes.append(Outcome(address.cf, "", "non_in_gaia", 0, "", address.avviso_text))
            continue
        if str(entity.subject_id) in seen:
            continue
        seen.add(str(entity.subject_id))
        outcomes.append(_apply_one(db, entity, address, source=source, dry_run=dry_run))
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return outcomes


def _updated_tax_codes(db) -> set[str]:
    subject_ids = set(
        db.scalars(
            select(AnagraficaAuditLog.subject_id).where(AnagraficaAuditLog.action == AUDIT_ACTION)
        )
    )
    codes = {
        code.strip().upper()
        for subject_id in subject_ids
        for entity in (db.get(AnagraficaPerson, subject_id), db.get(AnagraficaCompany, subject_id))
        if entity is not None
        for code in (
            [entity.codice_fiscale]
            if isinstance(entity, AnagraficaPerson)
            else [entity.partita_iva, entity.codice_fiscale]
        )
        if code
    }
    return codes


def _in_dispatch(db, item_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(PosteDispatchItem.id).where(
                PosteDispatchItem.batch_item_id == item_id,
                PosteDispatchItem.active_key.is_not(None),
            )
        )
        is not None
    )


def regenerate_pdfs(db, *, actor_id: int | None, dry_run: bool) -> list[Outcome]:
    codes = _updated_tax_codes(db)
    items, _ = regeneration.regeneration_targets(db, None)
    outcomes: list[Outcome] = []
    for item in items:
        if item.codice_fiscale.strip().upper() not in codes:
            continue
        label = item.display_name or ""
        if _in_dispatch(db, item.id):
            outcomes.append(
                Outcome(item.codice_fiscale, str(item.id), "in_spedizione", 0, label, "")
            )
            continue
        if dry_run:
            outcomes.append(
                Outcome(item.codice_fiscale, str(item.id), "da_rigenerare", 0, label, "")
            )
            continue
        try:
            regeneration.regenerate_batch_item(
                db, item, regeneration.RECOMPUTE, actor_id=actor_id, reason=REGENERATION_REASON
            )
        except (regeneration.RegenerationSkipped, regeneration.RegenerationFailed) as exc:
            db.rollback()
            esito = "saltato" if isinstance(exc, regeneration.RegenerationSkipped) else "errore"
            outcomes.append(Outcome(item.codice_fiscale, str(item.id), esito, 0, label, str(exc)))
            continue
        db.commit()
        outcomes.append(
            Outcome(
                item.codice_fiscale,
                str(item.id),
                "rigenerato",
                0,
                label,
                item.generated_document_path,
            )
        )
    return outcomes


def write_report(path: Path, outcomes: list[Outcome]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cf", "id", "esito", "avvisi_aggiornati", "prima", "dopo"])
        writer.writerows((o.cf, o.subject_id, o.esito, o.avvisi, o.prima, o.dopo) for o in outcomes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    addresses_cmd = commands.add_parser("addresses", help="Aggiorna anagrafica e avvisi.")
    addresses_cmd.add_argument("workbook", type=Path, help="Anagrafica_puntofisco_*_R2.xlsx")
    addresses_cmd.add_argument(
        "--source", default="puntofisco_2025-12-17", help="Etichetta fonte nell'audit log."
    )
    regenerate_cmd = commands.add_parser(
        "regenerate", help="Rigenera i PDF dei soggetti aggiornati."
    )
    regenerate_cmd.add_argument("--actor-id", type=int, help="Utente GAIA a cui intestare l'audit.")
    for command in (addresses_cmd, regenerate_cmd):
        command.add_argument("--report", type=Path, required=True, help="CSV con l'esito.")
        command.add_argument(
            "--apply", action="store_true", help="Scrive su GAIA; il default e dry-run."
        )
    args = parser.parse_args(argv)
    if args.command == "regenerate" and args.apply and args.actor_id is None:
        parser.error("--actor-id e obbligatorio con --apply")

    skipped: Counter[str] = Counter()
    with SessionLocal() as db:
        if args.command == "addresses":
            addresses, skipped = read_addresses(args.workbook)
            outcomes = apply_addresses(db, addresses, source=args.source, dry_run=not args.apply)
        else:
            outcomes = regenerate_pdfs(db, actor_id=args.actor_id, dry_run=not args.apply)
    write_report(args.report, outcomes)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"PuntoFisco {args.command} ({mode}): {len(outcomes)} righe")
    for key, value in sorted(skipped.items()):
        print(f"scartati_{key}: {value}")
    for key, value in sorted(Counter(o.esito for o in outcomes).items()):
        print(f"{key}: {value}")
    print(f"avvisi_aggiornati: {sum(o.avvisi for o in outcomes)}")
    print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
