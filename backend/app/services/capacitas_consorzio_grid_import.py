from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatCapacitasGridRow,
    CatCapacitasGridSnapshot,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.modules.utenze.services.subject_identity import is_probable_vat_number, normalize_tax_identifier


GRID_REQUIRED_COLUMNS = {
    "CODICE",
    "COMUNE",
    "PVC",
    "COM",
    "CCO",
    "FRA",
    "CCS",
    "FOGLIO",
    "PARTIC",
    "SUB",
    "SUP. CATASTALE",
    "SUP. IRRIGATA",
    "INTESTATARIO",
    "CODICE FISCALE",
    "MANUTENZIONE",
    "DOMANDA",
}
GRID_SOURCE_TYPE = "capacitas_grid"
COMUNE_SWAP_CODES = {
    165: 280,  # Arborea -> Terralba
    280: 165,  # Terralba -> Arborea
}


@dataclass(frozen=True)
class CapacitasGridImportOptions:
    xlsx_path: Path
    snapshot_year: int
    source_file: str
    output_dir: Path
    apply: bool = False


@dataclass(frozen=True)
class GridRow:
    row_number: int
    source_codice_catastale: str
    source_cod_comune_capacitas: int | None
    source_comune_label: str | None
    pvc: str | None
    com: str | None
    cco: str | None
    fra: str | None
    ccs: str | None
    num_distretto: str | None
    distretto: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    sup_catastale_mq: Decimal | None
    sup_irrigata_mq: Decimal | None
    coltura: str | None
    intestatario: str | None
    codice_fiscale: str | None
    manutenzione: int | None
    domanda: int | None
    numdomanda: str | None
    stato: str | None
    note: str | None
    autorinnovo: int | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class UnitResolution:
    source_comune: CatComune | None
    canonical_comune: CatComune | None
    particella: CatParticella | None
    resolution_mode: str
    classification: str


@dataclass
class ImportArtifacts:
    summary_path: Path
    samples_path: Path
    rows_path: Path


@dataclass
class ImportRuntime:
    comuni_by_codice: dict[str, CatComune]
    comuni_by_capacitas_code: dict[int, CatComune]
    particelle_exact: dict[tuple[int, str, str, str], list[CatParticella]]
    particelle_base: dict[tuple[int, str, str], list[CatParticella]]
    units_by_source_key: dict[tuple[str, str | None, str | None, str | None, str | None], CatConsorzioUnit]
    units_by_legacy_key: dict[tuple[str | None, str | None, str | None, str | None], CatConsorzioUnit]
    unit_alias_ids_by_unit_id: dict[uuid.UUID, tuple[uuid.UUID, ...]]
    occupancies_by_key: dict[tuple[uuid.UUID, str, str | None, str | None, str | None, str | None, date, date], CatConsorzioOccupancy]
    subjects_by_tax_id: dict[str, AnagraficaSubject | None]


def run_capacitas_consorzio_grid_import(db: Session, options: CapacitasGridImportOptions) -> dict[str, Any]:
    rows = parse_capacitas_grid_xlsx(options.xlsx_path)
    file_hash = compute_file_hash(options.xlsx_path)
    before_counts = collect_guard_counts(db)
    runtime = build_runtime(db)
    counters: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    row_reports: list[dict[str, Any]] = []
    imported_rows = 0
    snapshot: CatCapacitasGridSnapshot | None = None
    existing_snapshot_row_numbers: set[int] = set()

    if options.apply:
        snapshot = db.scalar(
            select(CatCapacitasGridSnapshot).where(
                CatCapacitasGridSnapshot.snapshot_year == options.snapshot_year,
                CatCapacitasGridSnapshot.file_hash == file_hash,
            )
        )
        if snapshot is None:
            snapshot = CatCapacitasGridSnapshot(
                id=uuid.uuid4(),
                snapshot_year=options.snapshot_year,
                source_file=options.source_file,
                file_hash=file_hash,
                rows_total=len(rows),
                rows_imported=0,
                counters_json={},
                imported_at=datetime.now(timezone.utc),
            )
            db.add(snapshot)
            db.flush()
        else:
            existing_snapshot_row_numbers = set(
                db.scalars(
                    select(CatCapacitasGridRow.row_number).where(CatCapacitasGridRow.snapshot_id == snapshot.id)
                ).all()
            )
            counters["snapshot_existing"] += 1

    for row in rows:
        report = process_grid_row(db, row, options=options, counters=counters, runtime=runtime)
        row_reports.append(report)
        classification = report["unit_classification"]
        if len(samples[classification]) < 50:
            samples[classification].append(report)
        occupancy_classification = report["occupancy_classification"]
        if occupancy_classification and len(samples[occupancy_classification]) < 50:
            samples[occupancy_classification].append(report)

        if options.apply and snapshot is not None and row.row_number not in existing_snapshot_row_numbers:
            db.add(_grid_row_model(snapshot.id, row, report))
            imported_rows += 1

    if options.apply and snapshot is not None:
        snapshot.rows_total = len(rows)
        snapshot.rows_imported = int(
            db.scalar(select(func.count(CatCapacitasGridRow.id)).where(CatCapacitasGridRow.snapshot_id == snapshot.id))
            or 0
        )
        snapshot.counters_json = dict(counters)
        db.commit()
    else:
        db.rollback()

    after_counts = collect_guard_counts(db)
    counters["raw_rows_inserted"] = imported_rows
    summary = {
        "mode": "apply" if options.apply else "dry-run",
        "source_file": options.source_file,
        "xlsx_path": str(options.xlsx_path),
        "snapshot_year": options.snapshot_year,
        "file_hash": file_hash,
        "rows_total": len(rows),
        "counters": dict(counters),
        "before_counts": before_counts,
        "after_counts": after_counts,
        "cat_particelle_unchanged": before_counts["cat_particelle"] == after_counts["cat_particelle"],
    }
    artifacts = write_import_artifacts(options.output_dir, summary, samples, row_reports)
    summary["artifacts"] = {
        "summary_path": str(artifacts.summary_path),
        "samples_path": str(artifacts.samples_path),
        "rows_path": str(artifacts.rows_path),
    }
    artifacts.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def parse_capacitas_grid_xlsx(path: Path) -> list[GridRow]:
    dataframe = pd.read_excel(path, sheet_name="Esportazione", dtype=object, engine="openpyxl")
    missing = sorted(GRID_REQUIRED_COLUMNS - {str(column).strip() for column in dataframe.columns})
    if missing:
        raise ValueError(f"Colonne Excel mancanti: {', '.join(missing)}")

    rows: list[GridRow] = []
    for index, item in dataframe.iterrows():
        raw_payload = {
            str(column): _json_safe_value(item[column])
            for column in dataframe.columns
        }
        rows.append(
            GridRow(
                row_number=int(index) + 2,
                source_codice_catastale=_normalize_code(item["CODICE"]),
                source_cod_comune_capacitas=_to_int(item["COM"]),
                source_comune_label=_clean_text(item["COMUNE"]),
                pvc=_normalize_fixed_width(item["PVC"], 3),
                com=_normalize_numeric_text(item["COM"]),
                cco=_normalize_cco(item["CCO"]),
                fra=_normalize_numeric_text(item["FRA"]),
                ccs=_normalize_fixed_width(item["CCS"], 5),
                num_distretto=_normalize_numeric_text(item.get("NUM. DISTR.")),
                distretto=_clean_text(item.get("DISTRETTO")),
                sezione_catastale=_clean_text(item.get("SEZIONE")),
                foglio=_normalize_numeric_text(item["FOGLIO"]),
                particella=_normalize_numeric_text(item["PARTIC"]),
                subalterno=_normalize_sub(item["SUB"]),
                sup_catastale_mq=_to_decimal(item["SUP. CATASTALE"]),
                sup_irrigata_mq=_to_decimal(item["SUP. IRRIGATA"]),
                coltura=_clean_text(item.get("COLTURA")),
                intestatario=_clean_text(item["INTESTATARIO"]),
                codice_fiscale=normalize_tax_identifier(_clean_text(item["CODICE FISCALE"]) or None),
                manutenzione=_to_int(item["MANUTENZIONE"]),
                domanda=_to_int(item["DOMANDA"]),
                numdomanda=_normalize_numeric_text(item.get("NUMDOMANDA")),
                stato=_clean_text(item.get("STATO")),
                note=_clean_text(item.get("NOTE")),
                autorinnovo=_to_int(item.get("AUTORINNOVO")),
                raw_payload=raw_payload,
            )
        )
    return rows


def process_grid_row(
    db: Session,
    row: GridRow,
    *,
    options: CapacitasGridImportOptions,
    counters: Counter[str],
    runtime: ImportRuntime,
) -> dict[str, Any]:
    if not row.source_codice_catastale or not row.foglio or not row.particella:
        counters["row_invalid_key"] += 1
        return _row_report(row, unit=None, occupancy=None, unit_classification="row_invalid_key")

    resolution = resolve_unit_target(row, runtime)
    unit, unit_classification = find_or_create_unit(db, row, resolution, apply=options.apply, runtime=runtime)
    counters[f"unit_action_{unit_classification}"] += 1
    counters[f"unit_resolution_{resolution.classification}"] += 1

    occupancy, occupancy_classification = find_or_create_occupancy(
        db,
        row,
        unit,
        snapshot_year=options.snapshot_year,
        apply=options.apply,
        runtime=runtime,
    )
    if occupancy_classification:
        counters[occupancy_classification] += 1

    return _row_report(
        row,
        unit=unit,
        occupancy=occupancy,
        unit_classification=unit_classification,
        occupancy_classification=occupancy_classification,
        resolution=resolution,
    )


def build_runtime(db: Session) -> ImportRuntime:
    comuni = list(db.scalars(select(CatComune)).all())
    current_particelle = list(db.scalars(select(CatParticella).where(CatParticella.is_current.is_(True))).all())
    units = list(db.scalars(select(CatConsorzioUnit).order_by(CatConsorzioUnit.created_at.asc(), CatConsorzioUnit.id.asc())).all())
    occupancies = list(db.scalars(select(CatConsorzioOccupancy).where(CatConsorzioOccupancy.source_type == GRID_SOURCE_TYPE)).all())
    particelle_exact: dict[tuple[int, str, str, str], list[CatParticella]] = defaultdict(list)
    particelle_base: dict[tuple[int, str, str], list[CatParticella]] = defaultdict(list)
    for particella in current_particelle:
        sub = (particella.subalterno or "").strip()
        exact_key = (
            particella.cod_comune_capacitas,
            (particella.foglio or "").strip(),
            (particella.particella or "").strip(),
            sub,
        )
        base_key = exact_key[:3]
        particelle_exact[exact_key].append(particella)
        particelle_base[base_key].append(particella)

    units_by_source_key: dict[tuple[str, str | None, str | None, str | None, str | None], CatConsorzioUnit] = {}
    units_by_legacy_key: dict[tuple[str | None, str | None, str | None, str | None], CatConsorzioUnit] = {}
    alias_ids_by_unit_id: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    units_grouped_by_source_key: dict[tuple[str, str | None, str | None, str | None, str | None], list[CatConsorzioUnit]] = defaultdict(list)
    units_grouped_by_legacy_key: dict[tuple[str | None, str | None, str | None, str | None], list[CatConsorzioUnit]] = defaultdict(list)
    for unit in units:
        source_key = _unit_source_key(
            unit.source_codice_catastale,
            unit.sezione_catastale,
            unit.foglio,
            unit.particella,
            unit.subalterno,
        )
        if unit.source_codice_catastale and source_key not in units_by_source_key:
            units_by_source_key[source_key] = unit
            units_grouped_by_source_key[source_key].append(unit)
        elif unit.source_codice_catastale:
            units_grouped_by_source_key[source_key].append(unit)
        legacy_key = _unit_legacy_key(unit.sezione_catastale, unit.foglio, unit.particella, unit.subalterno)
        if unit.source_codice_catastale is None and legacy_key not in units_by_legacy_key:
            units_by_legacy_key[legacy_key] = unit
            units_grouped_by_legacy_key[legacy_key].append(unit)
        elif unit.source_codice_catastale is None:
            units_grouped_by_legacy_key[legacy_key].append(unit)

    for grouped_units in list(units_grouped_by_source_key.values()) + list(units_grouped_by_legacy_key.values()):
        alias_ids = {unit.id for unit in grouped_units}
        for unit_id in alias_ids:
            alias_ids_by_unit_id[unit_id].update(alias_ids)

    occupancies_by_key: dict[
        tuple[uuid.UUID, str, str | None, str | None, str | None, str | None, date, date],
        CatConsorzioOccupancy,
    ] = {}
    for occupancy in occupancies:
        if occupancy.valid_from is None or occupancy.valid_to is None:
            continue
        key = _occupancy_key(
            occupancy.unit_id,
            occupancy.cco,
            occupancy.fra,
            occupancy.ccs,
            occupancy.pvc,
            occupancy.com,
            occupancy.valid_from,
            occupancy.valid_to,
        )
        occupancies_by_key.setdefault(key, occupancy)

    return ImportRuntime(
        comuni_by_codice={comune.codice_catastale: comune for comune in comuni},
        comuni_by_capacitas_code={comune.cod_comune_capacitas: comune for comune in comuni},
        particelle_exact=dict(particelle_exact),
        particelle_base=dict(particelle_base),
        units_by_source_key=units_by_source_key,
        units_by_legacy_key=units_by_legacy_key,
        unit_alias_ids_by_unit_id={unit_id: tuple(sorted(alias_ids, key=str)) for unit_id, alias_ids in alias_ids_by_unit_id.items()},
        occupancies_by_key=occupancies_by_key,
        subjects_by_tax_id={},
    )


def resolve_unit_target(row: GridRow, runtime: ImportRuntime) -> UnitResolution:
    source_comune = _find_source_comune(row, runtime)
    canonical_comune = source_comune
    particella, match_state = _find_official_particella(row, source_comune, runtime)
    resolution_mode = "source_match" if particella is not None else "source_only"
    classification = "unit_unmatched_official"

    if particella is not None:
        classification = "unit_existing_exact"
        canonical_comune = particella.comune or source_comune
        return UnitResolution(source_comune, canonical_comune, particella, resolution_mode, classification)

    if match_state == "sub_mismatch":
        classification = "unit_sub_mismatch"
    elif match_state == "ambiguous":
        classification = "unit_ambiguous"

    if source_comune is not None and source_comune.cod_comune_capacitas in COMUNE_SWAP_CODES:
        alternate = runtime.comuni_by_capacitas_code.get(COMUNE_SWAP_CODES[source_comune.cod_comune_capacitas])
        swapped_particella, swapped_state = _find_official_particella(row, alternate, runtime)
        if swapped_particella is not None:
            return UnitResolution(
                source_comune=source_comune,
                canonical_comune=swapped_particella.comune or alternate,
                particella=swapped_particella,
                resolution_mode="swapped_arborea_terralba",
                classification="unit_swapped_arborea_terralba",
            )
        if swapped_state == "ambiguous":
            classification = "unit_ambiguous"

    return UnitResolution(source_comune, canonical_comune, None, resolution_mode, classification)


def find_or_create_unit(
    db: Session,
    row: GridRow,
    resolution: UnitResolution,
    *,
    apply: bool,
    runtime: ImportRuntime,
) -> tuple[CatConsorzioUnit | None, str]:
    existing = _find_existing_unit(row, runtime)
    if existing is not None:
        classification = (
            "unit_swapped_arborea_terralba"
            if existing.comune_resolution_mode == "swapped_arborea_terralba"
            else "unit_existing_exact"
        )
        if apply:
            _update_unit(existing, row, resolution)
        return existing, classification

    if not apply:
        return None, "unit_created"

    unit = CatConsorzioUnit(
        id=uuid.uuid4(),
        particella_id=resolution.particella.id if resolution.particella else None,
        comune_id=resolution.canonical_comune.id if resolution.canonical_comune else None,
        cod_comune_capacitas=resolution.canonical_comune.cod_comune_capacitas if resolution.canonical_comune else None,
        source_comune_id=resolution.source_comune.id if resolution.source_comune else None,
        source_cod_comune_capacitas=row.source_cod_comune_capacitas,
        source_codice_catastale=row.source_codice_catastale,
        source_comune_label=row.source_comune_label,
        comune_resolution_mode=resolution.resolution_mode,
        sezione_catastale=row.sezione_catastale,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=row.subalterno,
        descrizione=f"Capacitas grid {row.foglio}/{row.particella}" + (f"/{row.subalterno}" if row.subalterno else ""),
        source_first_seen=date.today(),
        source_last_seen=date.today(),
        is_active=True,
    )
    db.add(unit)
    db.flush()
    runtime.units_by_source_key[_unit_source_key(
        unit.source_codice_catastale,
        unit.sezione_catastale,
        unit.foglio,
        unit.particella,
        unit.subalterno,
    )] = unit
    return unit, "unit_created"


def find_or_create_occupancy(
    db: Session,
    row: GridRow,
    unit: CatConsorzioUnit | None,
    *,
    snapshot_year: int,
    apply: bool,
    runtime: ImportRuntime,
) -> tuple[CatConsorzioOccupancy | None, str | None]:
    if unit is None or not row.cco:
        return None, None

    valid_from = date(snapshot_year, 1, 1)
    valid_to = date(snapshot_year, 12, 31)
    existing = _find_existing_occupancy(runtime, unit.id, row, valid_from, valid_to)
    if existing is not None:
        return existing, "occupancy_existing_current" if existing.is_current else "occupancy_existing_historical"

    subject = _find_subject_by_tax_identifier(db, row.codice_fiscale, runtime)
    if not apply:
        return None, "occupancy_created"

    occupancy = CatConsorzioOccupancy(
        id=uuid.uuid4(),
        unit_id=unit.id,
        segment_id=None,
        subject_id=subject.id if subject is not None else None,
        utenza_id=None,
        cco=row.cco,
        fra=row.fra,
        ccs=row.ccs,
        pvc=row.pvc,
        com=row.com,
        source_type=GRID_SOURCE_TYPE,
        relationship_type="utilizzatore_reale",
        valid_from=valid_from,
        valid_to=valid_to,
        is_current=True,
        confidence=Decimal("0.85"),
        notes="Occupazione derivata da export grid Capacitas",
    )
    db.add(occupancy)
    db.flush()
    key = _occupancy_key(unit.id, row.cco, row.fra, row.ccs, row.pvc, row.com, valid_from, valid_to)
    runtime.occupancies_by_key[key] = occupancy
    return occupancy, "occupancy_created"


def _find_existing_occupancy(
    runtime: ImportRuntime,
    unit_id: uuid.UUID,
    row: GridRow,
    valid_from: date,
    valid_to: date,
) -> CatConsorzioOccupancy | None:
    alias_ids = runtime.unit_alias_ids_by_unit_id.get(unit_id, (unit_id,))
    for alias_unit_id in alias_ids:
        key = _occupancy_key(alias_unit_id, row.cco, row.fra, row.ccs, row.pvc, row.com, valid_from, valid_to)
        existing = runtime.occupancies_by_key.get(key)
        if existing is not None:
            return existing
    return None


def write_import_artifacts(
    output_dir: Path,
    summary: dict[str, Any],
    samples: dict[str, list[dict[str, Any]]],
    row_reports: list[dict[str, Any]],
) -> ImportArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"capacitas_grid_{summary['snapshot_year']}_{summary['mode']}"
    summary_path = output_dir / f"{prefix}_summary.json"
    samples_path = output_dir / f"{prefix}_samples.json"
    rows_path = output_dir / f"{prefix}_rows.csv"
    samples_path.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(row_reports).to_csv(rows_path, index=False)
    return ImportArtifacts(summary_path=summary_path, samples_path=samples_path, rows_path=rows_path)


def collect_guard_counts(db: Session) -> dict[str, int]:
    return {
        "cat_particelle": int(db.scalar(select(func.count(CatParticella.id))) or 0),
        "cat_consorzio_units": int(db.scalar(select(func.count(CatConsorzioUnit.id))) or 0),
        "cat_consorzio_occupancies": int(db.scalar(select(func.count(CatConsorzioOccupancy.id))) or 0),
        "cat_capacitas_grid_snapshots": int(db.scalar(select(func.count(CatCapacitasGridSnapshot.id))) or 0),
        "cat_capacitas_grid_rows": int(db.scalar(select(func.count(CatCapacitasGridRow.id))) or 0),
    }


def compute_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_existing_unit(row: GridRow, runtime: ImportRuntime) -> CatConsorzioUnit | None:
    source_key = _unit_source_key(
        row.source_codice_catastale,
        row.sezione_catastale,
        row.foglio,
        row.particella,
        row.subalterno,
    )
    existing = runtime.units_by_source_key.get(source_key)
    if existing is not None:
        return existing
    legacy_key = _unit_legacy_key(row.sezione_catastale, row.foglio, row.particella, row.subalterno)
    return runtime.units_by_legacy_key.get(legacy_key)


def _update_unit(unit: CatConsorzioUnit, row: GridRow, resolution: UnitResolution) -> None:
    if unit.particella_id is None and resolution.particella is not None:
        unit.particella_id = resolution.particella.id
    if unit.comune_id is None and resolution.canonical_comune is not None:
        unit.comune_id = resolution.canonical_comune.id
    if unit.cod_comune_capacitas is None and resolution.canonical_comune is not None:
        unit.cod_comune_capacitas = resolution.canonical_comune.cod_comune_capacitas
    if unit.source_comune_id is None and resolution.source_comune is not None:
        unit.source_comune_id = resolution.source_comune.id
    unit.source_cod_comune_capacitas = unit.source_cod_comune_capacitas or row.source_cod_comune_capacitas
    unit.source_codice_catastale = unit.source_codice_catastale or row.source_codice_catastale
    unit.source_comune_label = unit.source_comune_label or row.source_comune_label
    unit.comune_resolution_mode = unit.comune_resolution_mode or resolution.resolution_mode
    unit.source_last_seen = date.today()
    unit.is_active = True


def _find_source_comune(row: GridRow, runtime: ImportRuntime) -> CatComune | None:
    if row.source_codice_catastale:
        comune = runtime.comuni_by_codice.get(row.source_codice_catastale)
        if comune is not None:
            return comune
    if row.source_cod_comune_capacitas is not None:
        return runtime.comuni_by_capacitas_code.get(row.source_cod_comune_capacitas)
    return None


def _find_official_particella(
    row: GridRow,
    comune: CatComune | None,
    runtime: ImportRuntime,
) -> tuple[CatParticella | None, str]:
    if comune is None or not row.foglio or not row.particella:
        return None, "unmatched"
    subalterno = row.subalterno or ""
    exact_key = (comune.cod_comune_capacitas, row.foglio, row.particella, subalterno)
    exact_matches = runtime.particelle_exact.get(exact_key, [])
    if len(exact_matches) == 1:
        return exact_matches[0], "exact"
    if len(exact_matches) > 1:
        return None, "ambiguous"
    base_matches = runtime.particelle_base.get(exact_key[:3], [])
    if base_matches:
        return None, "sub_mismatch"
    return None, "unmatched"


def _find_subject_by_tax_identifier(
    db: Session,
    codice_fiscale: str | None,
    runtime: ImportRuntime,
) -> AnagraficaSubject | None:
    normalized = normalize_tax_identifier(codice_fiscale)
    if not normalized:
        return None
    if normalized in runtime.subjects_by_tax_id:
        return runtime.subjects_by_tax_id[normalized]
    if is_probable_vat_number(normalized):
        company = db.scalar(
            select(AnagraficaCompany).where(
                or_(AnagraficaCompany.partita_iva == normalized, AnagraficaCompany.codice_fiscale == normalized)
            )
        )
        subject = db.get(AnagraficaSubject, company.subject_id) if company is not None else None
        runtime.subjects_by_tax_id[normalized] = subject
        return subject
    person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == normalized))
    subject = db.get(AnagraficaSubject, person.subject_id) if person is not None else None
    runtime.subjects_by_tax_id[normalized] = subject
    return subject


def _unit_source_key(
    source_codice_catastale: str | None,
    sezione_catastale: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    return (
        source_codice_catastale or "",
        sezione_catastale or None,
        foglio or None,
        particella or None,
        subalterno or None,
    )


def _unit_legacy_key(
    sezione_catastale: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    return (
        sezione_catastale or None,
        foglio or None,
        particella or None,
        subalterno or None,
    )


def _occupancy_key(
    unit_id: uuid.UUID,
    cco: str,
    fra: str | None,
    ccs: str | None,
    pvc: str | None,
    com: str | None,
    valid_from: date,
    valid_to: date,
) -> tuple[uuid.UUID, str, str | None, str | None, str | None, str | None, date, date]:
    return (
        unit_id,
        cco,
        fra or None,
        ccs or None,
        pvc or None,
        com or None,
        valid_from,
        valid_to,
    )


def _grid_row_model(snapshot_id: uuid.UUID, row: GridRow, report: dict[str, Any]) -> CatCapacitasGridRow:
    return CatCapacitasGridRow(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        row_number=row.row_number,
        unit_id=_uuid_or_none(report.get("unit_id")),
        occupancy_id=_uuid_or_none(report.get("occupancy_id")),
        source_codice_catastale=row.source_codice_catastale,
        source_cod_comune_capacitas=row.source_cod_comune_capacitas,
        source_comune_label=row.source_comune_label,
        cco=row.cco,
        fra=row.fra,
        ccs=row.ccs,
        pvc=row.pvc,
        sezione_catastale=row.sezione_catastale,
        foglio=row.foglio,
        particella=row.particella,
        subalterno=row.subalterno,
        sup_catastale_mq=row.sup_catastale_mq,
        sup_irrigata_mq=row.sup_irrigata_mq,
        coltura=row.coltura,
        intestatario=row.intestatario,
        codice_fiscale=row.codice_fiscale,
        manutenzione=row.manutenzione,
        domanda=row.domanda,
        numdomanda=row.numdomanda,
        stato=row.stato,
        note=row.note,
        autorinnovo=row.autorinnovo,
        classification=report["unit_classification"],
        raw_payload_json=row.raw_payload,
    )


def _uuid_or_none(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _row_report(
    row: GridRow,
    *,
    unit: CatConsorzioUnit | None,
    occupancy: CatConsorzioOccupancy | None,
    unit_classification: str,
    occupancy_classification: str | None = None,
    resolution: UnitResolution | None = None,
) -> dict[str, Any]:
    return {
        "row_number": row.row_number,
        "source_codice_catastale": row.source_codice_catastale,
        "source_cod_comune_capacitas": row.source_cod_comune_capacitas,
        "source_comune_label": row.source_comune_label,
        "foglio": row.foglio,
        "particella": row.particella,
        "subalterno": row.subalterno,
        "cco": row.cco,
        "fra": row.fra,
        "ccs": row.ccs,
        "pvc": row.pvc,
        "codice_fiscale": row.codice_fiscale,
        "intestatario": row.intestatario,
        "unit_id": str(unit.id) if unit is not None else None,
        "occupancy_id": str(occupancy.id) if occupancy is not None else None,
        "particella_id": str(resolution.particella.id) if resolution is not None and resolution.particella is not None else None,
        "comune_resolution_mode": resolution.resolution_mode if resolution is not None else None,
        "unit_classification": unit_classification,
        "occupancy_classification": occupancy_classification,
    }


def _normalize_code(value: Any) -> str:
    return _clean_text(value).upper()


def _normalize_cco(value: Any) -> str | None:
    normalized = _normalize_numeric_text(value)
    return normalized.zfill(9) if normalized and normalized.isdigit() else normalized


def _normalize_fixed_width(value: Any, width: int) -> str | None:
    normalized = _normalize_numeric_text(value)
    return normalized.zfill(width) if normalized and normalized.isdigit() else normalized


def _normalize_sub(value: Any) -> str | None:
    normalized = _normalize_numeric_text(value)
    return normalized or None


def _normalize_numeric_text(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if re.fullmatch(r"\d+\\.0+", text):
        text = text.split(".", 1)[0]
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits and digits == text.replace(" ", ""):
        return str(int(digits))
    return text


def _clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    text = "".join(ch for ch in unicodedata.normalize("NFKC", text))
    return " ".join(text.split())


def _to_int(value: Any) -> int | None:
    text = _normalize_numeric_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_decimal(value: Any) -> Decimal | None:
    text = _clean_text(value)
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".") if "," in text else text
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _json_safe_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)
