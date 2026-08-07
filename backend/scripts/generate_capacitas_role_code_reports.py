from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any, Iterable

from sqlalchemy import select


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.materialize_ruolo_from_incass import (
    _configure_database_url_for_host,
    _extract_partite,
    _normalize_comune,
    _normalize_numeric_token,
    _normalize_subalterno,
    _to_decimal,
)

_configure_database_url_for_host()

from app.core.database import SessionLocal
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.modules.ruolo.services.capacitas_role_codes import (
    CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE,
    CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE,
    CAPACITAS_ROLE_KIND_UNCLASSIFIED,
    classify_capacitas_role_code,
    sort_capacitas_role_codes,
)
from app.modules.utenze.models import AnagraficaPaymentNotice


DEFAULT_LIVE_DIR = REPO_ROOT / "reports" / "ana-subjects-capacitas-live-20260806"
DEFAULT_COVERAGE_CSV = (
    REPO_ROOT
    / "reports"
    / "ana-subjects-roles-coverage-20260806"
    / "ana_subjects_role_coverage.csv"
)
DEFAULT_LIVE_CSV = DEFAULT_LIVE_DIR / "ana_subjects_capacitas_live_results.csv"
DEFAULT_OUTDIR = DEFAULT_LIVE_DIR / "role-code-reconstruction"


@dataclass(frozen=True)
class ParcelKey:
    year: int
    comune: str
    foglio: str
    particella: str
    subalterno: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_csv_list(value: object) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def parse_year_set(value: object) -> set[int]:
    years: set[int] = set()
    for item in parse_csv_list(value):
        if item.isdigit():
            years.add(int(item))
    return years


def money_to_decimal(value: object) -> Decimal | None:
    return _to_decimal(value)


def money_to_text(value: Decimal | None) -> str:
    return "" if value is None else f"{value.quantize(Decimal('0.01'))}"


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def load_live_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_coverage_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return {row["subject_id"]: row for row in csv.DictReader(f)}


def load_coverage_years(path: Path) -> set[int]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {
            int(match.group(1))
            for field in (reader.fieldnames or [])
            if (match := re.fullmatch(r"role_(\d{4})", field))
        }


def live_code_payload(row: dict[str, str]) -> tuple[list[int], list[str], list[str], dict[str, int], dict[str, list[str]]]:
    raw_codes = parse_csv_list(row.get("live_years"))
    rows_by_year = json.loads(row.get("live_rows_by_year_json") or "{}")
    avvisi_by_year = json.loads(row.get("live_avvisi_by_year_json") or "{}")
    ordinary_years: set[int] = set()
    special_codes: list[str] = []
    unclassified_codes: list[str] = []
    for code in raw_codes:
        classification = classify_capacitas_role_code(code)
        if classification.is_ordinary_role and classification.ordinary_year is not None:
            ordinary_years.add(classification.ordinary_year)
        elif classification.is_known_special:
            special_codes.append(classification.code)
        elif classification.kind == CAPACITAS_ROLE_KIND_UNCLASSIFIED:
            unclassified_codes.append(classification.code)
    row_counts = {str(key): int(value or 0) for key, value in rows_by_year.items()}
    avvisi = {
        str(key): [str(item) for item in value if item]
        for key, value in avvisi_by_year.items()
        if isinstance(value, list)
    }
    return sorted(ordinary_years), sort_capacitas_role_codes(special_codes), sort_capacitas_role_codes(unclassified_codes), row_counts, avvisi


def build_ordinary_diff_rows(
    live_rows: list[dict[str, str]],
    coverage_rows: dict[str, dict[str, str]],
    coverage_years: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    subject_rows: list[dict[str, Any]] = []
    year_rows: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    for live in live_rows:
        if live.get("live_status") != "present_live":
            continue
        subject_id = live.get("subject_id") or ""
        coverage = coverage_rows.get(subject_id, {})
        ordinary_years, special_codes, unclassified_codes, row_counts, avvisi_by_year = live_code_payload(live)
        local_years = parse_year_set(live.get("local_years_with_role") or coverage.get("years_with_role"))
        missing_within_coverage = sorted((set(ordinary_years) & coverage_years) - local_years)
        missing_outside_coverage = sorted(set(ordinary_years) - coverage_years)
        missing_years = sorted([*missing_within_coverage, *missing_outside_coverage])
        if not missing_years:
            continue
        stats["subjects_with_ordinary_missing"] += 1
        stats["ordinary_missing_year_rows"] += len(missing_years)
        if missing_within_coverage:
            stats["subjects_with_missing_within_local_coverage"] += 1
            stats["ordinary_missing_within_local_coverage_rows"] += len(missing_within_coverage)
        if missing_outside_coverage:
            stats["subjects_with_live_years_not_in_local_coverage"] += 1
            stats["ordinary_not_in_local_coverage_rows"] += len(missing_outside_coverage)
        for year in missing_years:
            year_scope = "within_local_coverage" if year in coverage_years else "not_in_local_coverage"
            stats[f"missing_year_{year}"] += 1
            stats[f"missing_year_scope_{year_scope}_{year}"] += 1
            year_rows.append(
                {
                    "year": year,
                    "year_scope": year_scope,
                    "subject_id": subject_id,
                    "subject_type": live.get("subject_type") or coverage.get("subject_type", ""),
                    "requires_review": live.get("requires_review") or coverage.get("requires_review", ""),
                    "display_name": live.get("display_name") or coverage.get("display_name", ""),
                    "primary_identifier": live.get("primary_identifier") or coverage.get("primary_identifier", ""),
                    "live_rows_for_year": row_counts.get(str(year), 0),
                    "live_avvisi_for_year": ";".join(avvisi_by_year.get(str(year), [])),
                    "local_years_with_role": ",".join(str(item) for item in sorted(local_years)),
                    "special_codes_present": ",".join(special_codes),
                    "unclassified_codes_present": ",".join(unclassified_codes),
                }
            )
        subject_rows.append(
            {
                "subject_id": subject_id,
                "subject_type": live.get("subject_type") or coverage.get("subject_type", ""),
                "requires_review": live.get("requires_review") or coverage.get("requires_review", ""),
                "display_name": live.get("display_name") or coverage.get("display_name", ""),
                "primary_identifier": live.get("primary_identifier") or coverage.get("primary_identifier", ""),
                "local_years_with_role": ",".join(str(item) for item in sorted(local_years)),
                "live_ordinary_years": ",".join(str(item) for item in ordinary_years),
                "ordinary_years_missing_in_gaia": ",".join(str(item) for item in missing_years),
                "ordinary_years_missing_within_local_coverage": ",".join(
                    str(item) for item in missing_within_coverage
                ),
                "ordinary_years_not_in_local_coverage": ",".join(str(item) for item in missing_outside_coverage),
                "missing_year_count": len(missing_years),
                "special_codes_present": ",".join(special_codes),
                "unclassified_codes_present": ",".join(unclassified_codes),
            }
        )
    return subject_rows, year_rows, stats


def build_special_subject_rows(live_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    for live in live_rows:
        if live.get("live_status") != "present_live":
            continue
        _, special_codes, unclassified_codes, row_counts, avvisi_by_year = live_code_payload(live)
        row_kinds: set[str] = set()
        for code in [*special_codes, *unclassified_codes]:
            classification = classify_capacitas_role_code(code)
            stats[f"live_subject_code_{code}"] += 1
            row_kinds.add(classification.kind)
            rows.append(
                {
                    "subject_id": live.get("subject_id", ""),
                    "subject_type": live.get("subject_type", ""),
                    "requires_review": live.get("requires_review", ""),
                    "display_name": live.get("display_name", ""),
                    "primary_identifier": live.get("primary_identifier", ""),
                    "code": code,
                    "kind": classification.kind,
                    "label": classification.label,
                    "issue_year": classification.issue_year or "",
                    "reference_year": classification.reference_year or "",
                    "default_tribute_code": classification.default_tribute_code or "",
                    "requires_partitario_reconstruction": classification.requires_partitario_reconstruction,
                    "requires_manual_allocation": classification.requires_manual_allocation,
                    "live_rows_for_code": row_counts.get(code, 0),
                    "live_avvisi_for_code": ";".join(avvisi_by_year.get(code, [])),
                }
            )
        for kind in row_kinds:
            stats[f"live_subject_kind_{kind}"] += 1
    return rows, stats


def _notice_paid_amount(notice: AnagraficaPaymentNotice) -> Decimal | None:
    riscosso = money_to_decimal(notice.importo_riscosso)
    return abs(riscosso) if riscosso is not None else None


def _sum_partita_amount(partite: list[dict[str, Any]], field: str) -> Decimal | None:
    values = [money_to_decimal(partita.get(field)) for partita in partite]
    values = [value for value in values if value is not None]
    return sum(values, Decimal("0")) if values else None


def _particelle_from_partite(partite: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for partita in partite:
        particelle = partita.get("particelle")
        if not isinstance(particelle, list):
            continue
        for particella in particelle:
            if isinstance(particella, dict):
                rows.append((partita, particella))
    return rows


def _candidate_years_for_classification(classification) -> list[int]:
    if classification.kind == CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE and classification.reference_year is not None:
        return [classification.reference_year]
    if classification.kind == CAPACITAS_ROLE_KIND_AGGREGATED_NOTICE and classification.issue_year is not None:
        return list(range(2000, classification.issue_year))
    return []


def _build_owner_index(db, years: list[int]) -> dict[ParcelKey, list[dict[str, Any]]]:
    if not years:
        return {}
    rows = db.execute(
        select(
            RuoloParticella.foglio,
            RuoloParticella.particella,
            RuoloParticella.subalterno,
            RuoloPartita.comune_nome,
            RuoloPartita.id,
            RuoloPartita.codice_partita,
            RuoloAvviso.id,
            RuoloAvviso.subject_id,
            RuoloAvviso.codice_fiscale_raw,
            RuoloAvviso.nominativo_raw,
            RuoloAvviso.codice_cnc,
            RuoloAvviso.anno_tributario,
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(RuoloAvviso.anno_tributario.in_(years))
        .order_by(RuoloAvviso.anno_tributario)
    ).all()
    index: dict[ParcelKey, list[dict[str, Any]]] = defaultdict(list)
    for (
        foglio,
        particella,
        subalterno,
        comune_nome,
        partita_id,
        codice_partita,
        avviso_id,
        subject_id,
        codice_fiscale_raw,
        nominativo_raw,
        codice_cnc,
        anno_tributario,
    ) in rows:
        key = ParcelKey(
            year=anno_tributario,
            comune=_normalize_comune(comune_nome),
            foglio=_normalize_numeric_token(foglio),
            particella=_normalize_numeric_token(particella),
            subalterno=_normalize_subalterno(subalterno),
        )
        if not key.comune or not key.foglio or not key.particella:
            continue
        index[key].append(
            {
                "owner_subject_id": str(subject_id or ""),
                "owner_codice_fiscale_raw": codice_fiscale_raw or "",
                "owner_nominativo_raw": nominativo_raw or "",
                "ordinary_avviso_id": str(avviso_id),
                "ordinary_codice_cnc": codice_cnc,
                "ordinary_year": anno_tributario,
                "ordinary_partita_id": str(partita_id),
                "ordinary_codice_partita": codice_partita,
            }
        )
    return index


def _owner_matches(
    owner_index: dict[ParcelKey, list[dict[str, Any]]],
    *,
    candidate_years: list[int],
    partita: dict[str, Any],
    particella: dict[str, Any],
) -> list[dict[str, Any]]:
    comune = _normalize_comune(partita.get("comune_nome"))
    foglio = _normalize_numeric_token(particella.get("foglio"))
    particella_code = _normalize_numeric_token(particella.get("particella"))
    subalterno = _normalize_subalterno(particella.get("subalterno"))
    matches: list[dict[str, Any]] = []
    for year in candidate_years:
        key = ParcelKey(
            year=year,
            comune=comune,
            foglio=foglio,
            particella=particella_code,
            subalterno=subalterno,
        )
        matches.extend(owner_index.get(key, []))
    return matches


def build_special_notice_reconstruction_rows(
    db,
    special_codes: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    owner_indexes: dict[tuple[int, ...], dict[ParcelKey, list[dict[str, Any]]]] = {}
    notices = db.scalars(
        select(AnagraficaPaymentNotice)
        .where(AnagraficaPaymentNotice.source_system == "incass")
        .where(AnagraficaPaymentNotice.anno.in_(special_codes))
        .order_by(AnagraficaPaymentNotice.anno, AnagraficaPaymentNotice.source_notice_id)
    ).all()
    reconstruction_rows: list[dict[str, Any]] = []
    parcel_rows: list[dict[str, Any]] = []
    owner_rows: list[dict[str, Any]] = []
    anomaly_rows: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    for notice in notices:
        classification = classify_capacitas_role_code(notice.anno)
        payload = notice.raw_detail_json if isinstance(notice.raw_detail_json, dict) else {}
        partite = _extract_partite(payload, force_reparse=True) if payload else []
        parcel_pairs = _particelle_from_partite(partite)
        carico = money_to_decimal(notice.importo_carico)
        paid = _notice_paid_amount(notice)
        importo_0668 = _sum_partita_amount(partite, "importo_0668_euro")
        partite_count = len(partite)
        particelle_count = len(parcel_pairs)
        candidate_years = _candidate_years_for_classification(classification)
        stats[f"db_notice_code_{notice.anno}"] += 1
        stats[f"db_notice_kind_{classification.kind}"] += 1
        if notice.raw_detail_json is not None:
            stats[f"db_notice_code_{notice.anno}_with_detail"] += 1
        if partite_count:
            stats[f"db_notice_code_{notice.anno}_with_partite"] += 1
        if particelle_count:
            stats[f"db_notice_code_{notice.anno}_with_particelle"] += 1

        reconstruction_rows.append(
            {
                "source_notice_id": notice.source_notice_id,
                "subject_id": str(notice.subject_id or ""),
                "display_name": notice.display_name or "",
                "identifier": notice.codice_fiscale or notice.partita_iva or "",
                "code": notice.anno or "",
                "kind": classification.kind,
                "label": classification.label,
                "issue_year": classification.issue_year or "",
                "reference_year": classification.reference_year or "",
                "candidate_owner_years": ",".join(str(year) for year in candidate_years),
                "detail_available": notice.raw_detail_json is not None,
                "partite_count": partite_count,
                "particelle_count": particelle_count,
                "importo_carico": money_to_text(carico),
                "importo_riscosso_abs": money_to_text(paid),
                "importo_0668_from_partitario": money_to_text(importo_0668),
                "default_tribute_code": classification.default_tribute_code or "",
                "requires_manual_allocation": classification.requires_manual_allocation,
            }
        )

        if classification.requires_partitario_reconstruction and not partite_count:
            anomaly_rows.append(
                {
                    "severity": "high",
                    "anomaly": f"{classification.kind}_partitario_missing_or_unparsed",
                    "source_notice_id": notice.source_notice_id,
                    "subject_id": str(notice.subject_id or ""),
                    "display_name": notice.display_name or "",
                    "code": notice.anno or "",
                    "kind": classification.kind,
                    "detail_available": notice.raw_detail_json is not None,
                    "message": "Partitario non ricostruibile dai dettagli locali; richiede fetch live mirato o endpoint/documento alternativo.",
                }
            )

        if classification.kind == CAPACITAS_ROLE_KIND_TENANT_TAX_ADVANCE and partite_count:
            if importo_0668 is None:
                anomaly_rows.append(
                    {
                        "severity": "high",
                        "anomaly": "tenant_advance_missing_0668_amount",
                        "source_notice_id": notice.source_notice_id,
                        "subject_id": str(notice.subject_id or ""),
                        "display_name": notice.display_name or "",
                        "code": notice.anno or "",
                        "kind": classification.kind,
                        "detail_available": notice.raw_detail_json is not None,
                        "message": "Anticipo tributi con partitario ma senza importo 0668 ricostruito.",
                    }
                )
            elif carico is not None and carico.quantize(Decimal("0.01")) != importo_0668.quantize(Decimal("0.01")):
                anomaly_rows.append(
                    {
                        "severity": "medium",
                        "anomaly": "tenant_advance_carico_0668_delta",
                        "source_notice_id": notice.source_notice_id,
                        "subject_id": str(notice.subject_id or ""),
                        "display_name": notice.display_name or "",
                        "code": notice.anno or "",
                        "kind": classification.kind,
                        "detail_available": notice.raw_detail_json is not None,
                        "message": f"Carico {money_to_text(carico)} diverso da 0668 ricostruito {money_to_text(importo_0668)}.",
                    }
                )

        for partita, particella in parcel_pairs:
            year_key = tuple(candidate_years)
            if year_key not in owner_indexes:
                owner_indexes[year_key] = _build_owner_index(db, candidate_years)
            matches = _owner_matches(
                owner_indexes[year_key],
                candidate_years=candidate_years,
                partita=partita,
                particella=particella,
            )
            parcel_base = {
                "source_notice_id": notice.source_notice_id,
                "subject_id": str(notice.subject_id or ""),
                "display_name": notice.display_name or "",
                "code": notice.anno or "",
                "kind": classification.kind,
                "candidate_owner_years": ",".join(str(year) for year in candidate_years),
                "codice_partita": partita.get("codice_partita") or "",
                "comune_nome": partita.get("comune_nome") or "",
                "foglio": particella.get("foglio") or "",
                "particella": particella.get("particella") or "",
                "subalterno": particella.get("subalterno") or "",
                "importo_irrig_euro": particella.get("importo_irrig_euro") or "",
                "owner_match_count": len(matches),
            }
            parcel_rows.append(parcel_base)
            if not matches and classification.requires_partitario_reconstruction:
                anomaly_rows.append(
                    {
                        "severity": "medium",
                        "anomaly": "special_parcel_owner_not_matched",
                        "source_notice_id": notice.source_notice_id,
                        "subject_id": str(notice.subject_id or ""),
                        "display_name": notice.display_name or "",
                        "code": notice.anno or "",
                        "kind": classification.kind,
                        "detail_available": notice.raw_detail_json is not None,
                        "message": (
                            f"Nessun proprietario candidato per {partita.get('comune_nome') or ''} "
                            f"F{particella.get('foglio') or ''} P{particella.get('particella') or ''}."
                        ),
                    }
                )
            for match in matches:
                owner_rows.append({**parcel_base, **match})
    return reconstruction_rows, parcel_rows, owner_rows, anomaly_rows, stats


def _counter_prefixed(counter: Counter[str], prefix: str) -> dict[str, int]:
    return {key[len(prefix):]: value for key, value in sorted(counter.items()) if key.startswith(prefix)}


def _year_counter_prefixed(counter: Counter[str], prefix: str) -> dict[str, int]:
    return {
        key[len(prefix):]: value
        for key, value in sorted(counter.items())
        if key.startswith(prefix) and key[len(prefix):].isdigit()
    }


def write_report(
    path: Path,
    *,
    summary: dict[str, Any],
    output_files: dict[str, str],
) -> None:
    special_counts = summary["special_reconstruction"]["db_notice_counts_by_code"]
    missing_within_counts = summary["ordinary_diff"]["missing_within_local_coverage_by_year"]
    not_in_coverage_counts = summary["ordinary_diff"]["not_in_local_coverage_by_year"]
    anomalies = summary["special_reconstruction"]["anomaly_counts_by_type"]
    lines = [
        "# Capacitas role code reconstruction - read-only",
        "",
        f"Generated at: `{summary['generated_at']}`",
        "",
        "## Ordinary role diff",
        "",
        "| Indicatore | Valore |",
        "|---|---:|",
        f"| Soggetti con anni ordinari live mancanti in GAIA | {summary['ordinary_diff']['subjects_with_ordinary_missing']} |",
        f"| Righe soggetto-anno candidate | {summary['ordinary_diff']['ordinary_missing_year_rows']} |",
        f"| Soggetti con mancanti su anni gia coperti localmente | {summary['ordinary_diff']['subjects_with_missing_within_local_coverage']} |",
        f"| Righe candidate su anni gia coperti localmente | {summary['ordinary_diff']['ordinary_missing_within_local_coverage_rows']} |",
        f"| Soggetti con anni live non coperti dal dataset locale | {summary['ordinary_diff']['subjects_with_live_years_not_in_local_coverage']} |",
        f"| Righe su anni non coperti dal dataset locale | {summary['ordinary_diff']['ordinary_not_in_local_coverage_rows']} |",
        "",
        "### Missing rows by year within local coverage",
        "",
        "| Anno | Righe candidate |",
        "|---:|---:|",
    ]
    for year, count in missing_within_counts.items():
        lines.append(f"| {year} | {count} |")
    lines.extend(
        [
            "",
            "### Live ordinary years not in local coverage",
            "",
            "| Anno | Righe candidate |",
            "|---:|---:|",
        ]
    )
    for year, count in not_in_coverage_counts.items():
        lines.append(f"| {year} | {count} |")
    lines.extend(
        [
            "",
            "## Special code reconstruction",
            "",
            "| Codice | Avvisi DB | Con dettaglio | Con partite | Con particelle |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    details_by_code = summary["special_reconstruction"]["db_notice_counts_with_detail_by_code"]
    partite_by_code = summary["special_reconstruction"]["db_notice_counts_with_partite_by_code"]
    particelle_by_code = summary["special_reconstruction"]["db_notice_counts_with_particelle_by_code"]
    for code, count in special_counts.items():
        lines.append(
            f"| {code} | {count} | {details_by_code.get(code, 0)} | "
            f"{partite_by_code.get(code, 0)} | {particelle_by_code.get(code, 0)} |"
        )
    lines.extend(
        [
            "",
            "### Anomalies",
            "",
            "| Tipo | Conteggio |",
            "|---|---:|",
        ]
    )
    for anomaly, count in anomalies.items():
        lines.append(f"| `{anomaly}` | {count} |")
    lines.extend(
        [
            "",
            "## Output files",
            "",
        ]
    )
    for label, file_path in output_files.items():
        lines.append(f"- `{label}`: `{file_path}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_reports(args: argparse.Namespace) -> dict[str, Any]:
    live_csv = Path(args.live_csv)
    coverage_csv = Path(args.coverage_csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    live_rows = load_live_rows(live_csv)
    coverage_rows = load_coverage_rows(coverage_csv)
    coverage_years = load_coverage_years(coverage_csv)
    ordinary_subject_rows, ordinary_year_rows, ordinary_stats = build_ordinary_diff_rows(
        live_rows,
        coverage_rows,
        coverage_years,
    )
    special_subject_rows, special_live_stats = build_special_subject_rows(live_rows)
    special_codes = sort_capacitas_role_codes(
        {
            row["code"]
            for row in special_subject_rows
            if classify_capacitas_role_code(row["code"]).is_known_special
        }
    )

    with SessionLocal() as db:
        (
            reconstruction_rows,
            parcel_rows,
            owner_rows,
            anomaly_rows,
            reconstruction_stats,
        ) = build_special_notice_reconstruction_rows(db, special_codes)

    output_files = {
        "ordinary_subject_candidates": str(outdir / "ordinary_role_missing_subjects.csv"),
        "ordinary_year_candidates": str(outdir / "ordinary_role_missing_by_year.csv"),
        "special_live_subjects": str(outdir / "special_code_subjects.csv"),
        "special_notice_reconstruction": str(outdir / "special_notice_reconstruction.csv"),
        "special_notice_particelle": str(outdir / "special_notice_particelle.csv"),
        "special_notice_owner_candidates": str(outdir / "special_notice_owner_candidates.csv"),
        "special_notice_anomalies": str(outdir / "special_notice_anomalies.csv"),
        "summary": str(outdir / "summary.json"),
        "report": str(outdir / "REPORT_ROLE_CODE_RECONSTRUCTION.md"),
    }

    write_csv(
        Path(output_files["ordinary_subject_candidates"]),
        [
            "subject_id",
            "subject_type",
            "requires_review",
            "display_name",
            "primary_identifier",
            "local_years_with_role",
            "live_ordinary_years",
            "ordinary_years_missing_in_gaia",
            "ordinary_years_missing_within_local_coverage",
            "ordinary_years_not_in_local_coverage",
            "missing_year_count",
            "special_codes_present",
            "unclassified_codes_present",
        ],
        ordinary_subject_rows,
    )
    write_csv(
        Path(output_files["ordinary_year_candidates"]),
        [
            "year",
            "year_scope",
            "subject_id",
            "subject_type",
            "requires_review",
            "display_name",
            "primary_identifier",
            "live_rows_for_year",
            "live_avvisi_for_year",
            "local_years_with_role",
            "special_codes_present",
            "unclassified_codes_present",
        ],
        ordinary_year_rows,
    )
    write_csv(
        Path(output_files["special_live_subjects"]),
        [
            "subject_id",
            "subject_type",
            "requires_review",
            "display_name",
            "primary_identifier",
            "code",
            "kind",
            "label",
            "issue_year",
            "reference_year",
            "default_tribute_code",
            "requires_partitario_reconstruction",
            "requires_manual_allocation",
            "live_rows_for_code",
            "live_avvisi_for_code",
        ],
        special_subject_rows,
    )
    write_csv(
        Path(output_files["special_notice_reconstruction"]),
        [
            "source_notice_id",
            "subject_id",
            "display_name",
            "identifier",
            "code",
            "kind",
            "label",
            "issue_year",
            "reference_year",
            "candidate_owner_years",
            "detail_available",
            "partite_count",
            "particelle_count",
            "importo_carico",
            "importo_riscosso_abs",
            "importo_0668_from_partitario",
            "default_tribute_code",
            "requires_manual_allocation",
        ],
        reconstruction_rows,
    )
    write_csv(
        Path(output_files["special_notice_particelle"]),
        [
            "source_notice_id",
            "subject_id",
            "display_name",
            "code",
            "kind",
            "candidate_owner_years",
            "codice_partita",
            "comune_nome",
            "foglio",
            "particella",
            "subalterno",
            "importo_irrig_euro",
            "owner_match_count",
        ],
        parcel_rows,
    )
    write_csv(
        Path(output_files["special_notice_owner_candidates"]),
        [
            "source_notice_id",
            "subject_id",
            "display_name",
            "code",
            "kind",
            "candidate_owner_years",
            "codice_partita",
            "comune_nome",
            "foglio",
            "particella",
            "subalterno",
            "importo_irrig_euro",
            "owner_match_count",
            "owner_subject_id",
            "owner_codice_fiscale_raw",
            "owner_nominativo_raw",
            "ordinary_avviso_id",
            "ordinary_codice_cnc",
            "ordinary_year",
            "ordinary_partita_id",
            "ordinary_codice_partita",
        ],
        owner_rows,
    )
    write_csv(
        Path(output_files["special_notice_anomalies"]),
        [
            "severity",
            "anomaly",
            "source_notice_id",
            "subject_id",
            "display_name",
            "code",
            "kind",
            "detail_available",
            "message",
        ],
        anomaly_rows,
    )

    summary = {
        "generated_at": now_iso(),
        "inputs": {
            "live_csv": str(live_csv),
            "coverage_csv": str(coverage_csv),
        },
        "ordinary_diff": {
            "local_coverage_years": sorted(coverage_years),
            "subjects_with_ordinary_missing": ordinary_stats["subjects_with_ordinary_missing"],
            "subjects_with_missing_within_local_coverage": ordinary_stats[
                "subjects_with_missing_within_local_coverage"
            ],
            "subjects_with_live_years_not_in_local_coverage": ordinary_stats[
                "subjects_with_live_years_not_in_local_coverage"
            ],
            "ordinary_missing_year_rows": ordinary_stats["ordinary_missing_year_rows"],
            "ordinary_missing_within_local_coverage_rows": ordinary_stats[
                "ordinary_missing_within_local_coverage_rows"
            ],
            "ordinary_not_in_local_coverage_rows": ordinary_stats["ordinary_not_in_local_coverage_rows"],
            "missing_rows_by_year": _year_counter_prefixed(ordinary_stats, "missing_year_"),
            "missing_within_local_coverage_by_year": _counter_prefixed(
                ordinary_stats,
                "missing_year_scope_within_local_coverage_",
            ),
            "not_in_local_coverage_by_year": _counter_prefixed(
                ordinary_stats,
                "missing_year_scope_not_in_local_coverage_",
            ),
        },
        "special_live": {
            "subject_counts_by_code": _counter_prefixed(special_live_stats, "live_subject_code_"),
            "subject_counts_by_kind": _counter_prefixed(special_live_stats, "live_subject_kind_"),
        },
        "special_reconstruction": {
            "db_notice_counts_by_code": _counter_prefixed(reconstruction_stats, "db_notice_code_"),
            "db_notice_counts_by_kind": _counter_prefixed(reconstruction_stats, "db_notice_kind_"),
            "db_notice_counts_with_detail_by_code": _counter_prefixed(
                reconstruction_stats,
                "db_notice_code_",
            ),
            "db_notice_counts_with_partite_by_code": _counter_prefixed(
                reconstruction_stats,
                "db_notice_code_",
            ),
            "db_notice_counts_with_particelle_by_code": _counter_prefixed(
                reconstruction_stats,
                "db_notice_code_",
            ),
            "reconstruction_rows": len(reconstruction_rows),
            "parcel_rows": len(parcel_rows),
            "owner_candidate_rows": len(owner_rows),
            "anomaly_rows": len(anomaly_rows),
            "anomaly_counts_by_type": dict(Counter(row["anomaly"] for row in anomaly_rows)),
        },
    }
    # The prefixed counters above include derived keys; keep exact per-code maps separate.
    summary["special_reconstruction"]["db_notice_counts_by_code"] = _counter_prefixed(
        reconstruction_stats,
        "db_notice_code_",
    )
    summary["special_reconstruction"]["db_notice_counts_with_detail_by_code"] = {
        key.removesuffix("_with_detail"): value
        for key, value in summary["special_reconstruction"]["db_notice_counts_by_code"].items()
        if key.endswith("_with_detail")
    }
    summary["special_reconstruction"]["db_notice_counts_with_partite_by_code"] = {
        key.removesuffix("_with_partite"): value
        for key, value in summary["special_reconstruction"]["db_notice_counts_by_code"].items()
        if key.endswith("_with_partite")
    }
    summary["special_reconstruction"]["db_notice_counts_with_particelle_by_code"] = {
        key.removesuffix("_with_particelle"): value
        for key, value in summary["special_reconstruction"]["db_notice_counts_by_code"].items()
        if key.endswith("_with_particelle")
    }
    summary["special_reconstruction"]["db_notice_counts_by_code"] = {
        key: value
        for key, value in summary["special_reconstruction"]["db_notice_counts_by_code"].items()
        if not key.endswith(("_with_detail", "_with_partite", "_with_particelle"))
    }

    summary_path = Path(output_files["summary"])
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(Path(output_files["report"]), summary=summary, output_files=output_files)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate read-only Capacitas role code reports.")
    parser.add_argument("--live-csv", default=str(DEFAULT_LIVE_CSV))
    parser.add_argument("--coverage-csv", default=str(DEFAULT_COVERAGE_CSV))
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    return parser.parse_args()


if __name__ == "__main__":
    generate_reports(parse_args())
