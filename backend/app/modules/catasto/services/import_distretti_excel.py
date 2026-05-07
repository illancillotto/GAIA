from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any, Callable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatComune, CatDistretto, CatImportBatch, CatParticella, CatParticellaHistory


REQUIRED_COLUMNS = {"ANNO", "N_DISTRETTO", "DISTRETTO", "COMUNE", "FOGLIO", "PARTIC"}

COMUNE_ALIAS_WITH_SECTION: dict[str, tuple[str, str | None]] = {
    "ORISTANO*ORISTANO": ("ORISTANO", "A"),
    "DONIGALA FENUGHEDU*ORISTANO": ("ORISTANO", "B"),
    "MASSAMA*ORISTANO": ("ORISTANO", "C"),
    "NURAXINIEDDU*ORISTANO": ("ORISTANO", "D"),
    "SILI'*ORISTANO": ("ORISTANO", "E"),
    "SILI’*ORISTANO": ("ORISTANO", "E"),
    "CABRAS": ("CABRAS", "A"),
    "SOLANAS*CABRAS": ("CABRAS", "B"),
    "OLLASTRA SIMAXIS": ("SIMAXIS", "A"),
    "SAN VERO CONGIUS*SIMAXIS": ("SIMAXIS", "B"),
    "SIMAXIS*SIMAXIS": ("SIMAXIS", "A"),
    "SAN NICOLO ARCIDANO": ("SAN NICOLO D'ARCIDANO", None),
}


def _clean_optional_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _normalize_lookup_token(value: Any) -> str | None:
    text = _clean_optional_string(value)
    if text is None:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    compact = text.replace(" ", "")
    if compact.isdigit():
        stripped = compact.lstrip("0")
        return stripped or "0"
    return text.upper()


def _normalize_name(value: Any) -> str | None:
    text = _clean_optional_string(value)
    return text.upper() if text else None


@dataclass
class DistrettoExcelRow:
    row_number: int
    anno_campagna: int | None
    comune_raw: str
    sezione: str | None
    foglio: str
    particella: str
    num_distretto: str
    nome_distretto: str | None
    comune_id: uuid.UUID | None
    comune_nome: str | None


@dataclass
class ResolvedComuneRef:
    comune: CatComune
    derived_sezione: str | None = None


def _normalize_comune_key(value: str) -> str:
    return value.strip().upper()


def _resolve_comune(
    raw_value: str,
    comuni_by_capacitas: dict[int, CatComune],
    comuni_by_catastale: dict[str, CatComune],
    comuni_by_name: dict[str, CatComune],
) -> ResolvedComuneRef | None:
    compact = raw_value.replace(" ", "")
    if compact.isdigit():
        comune = comuni_by_capacitas.get(int(compact))
        if comune is not None:
            return ResolvedComuneRef(comune=comune)

    uppercase = raw_value.upper()
    if len(uppercase) == 4:
        comune = comuni_by_catastale.get(uppercase)
        if comune is not None:
            return ResolvedComuneRef(comune=comune)

    alias = COMUNE_ALIAS_WITH_SECTION.get(_normalize_comune_key(raw_value))
    if alias is not None:
        canonical_name, derived_sezione = alias
        comune = comuni_by_name.get(canonical_name)
        if comune is not None:
            return ResolvedComuneRef(comune=comune, derived_sezione=derived_sezione)

    comune = comuni_by_name.get(uppercase)
    if comune is None:
        return None
    return ResolvedComuneRef(comune=comune)


def import_distretti_excel(
    db: Session,
    file_bytes: bytes,
    filename: str,
    created_by: int,
    batch_id: uuid.UUID | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> CatImportBatch:
    now = datetime.now(timezone.utc)
    today = date.today()
    dataframe = pd.read_excel(BytesIO(file_bytes), sheet_name=0, dtype=str)
    missing_columns = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing_columns:
        raise ValueError(f"Colonne obbligatorie mancanti: {', '.join(missing_columns)}")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    anno_values = pd.to_numeric(dataframe.get("ANNO"), errors="coerce").dropna()
    anno_campagna = int(anno_values.iloc[0]) if not anno_values.empty else None

    batch = db.get(CatImportBatch, batch_id) if batch_id is not None else None
    if batch is None:
        batch = CatImportBatch(
            id=batch_id or uuid.uuid4(),
            filename=filename,
            tipo="distretti_excel",
            anno_campagna=anno_campagna,
            hash_file=file_hash,
            righe_totali=len(dataframe),
            status="processing",
            created_by=created_by,
            created_at=now,
        )
        db.add(batch)
        db.flush()
    else:
        batch.filename = filename
        batch.tipo = "distretti_excel"
        batch.anno_campagna = anno_campagna
        batch.hash_file = file_hash
        batch.righe_totali = len(dataframe)
        batch.righe_importate = 0
        batch.righe_anomalie = 0
        batch.status = "processing"
        batch.errore = None
        batch.report_json = None

    comuni = db.execute(select(CatComune)).scalars().all()
    comuni_by_capacitas = {item.cod_comune_capacitas: item for item in comuni}
    comuni_by_catastale = {item.codice_catastale.upper(): item for item in comuni if item.codice_catastale}
    comuni_by_name = {item.nome_comune.upper(): item for item in comuni if item.nome_comune}

    row_candidates: dict[tuple[uuid.UUID, str | None, str, str], DistrettoExcelRow] = {}
    duplicate_collapsed = 0
    duplicate_conflicts = 0
    skipped_missing_fields = 0
    skipped_invalid_comune = 0
    preview_anomalies: list[dict[str, Any]] = []
    involved_comuni_ids: set[uuid.UUID] = set()
    comuni_rilevati: set[str] = set()
    distretti_rilevati: set[str] = set()

    for row_index, row in dataframe.iterrows():
        row_number = row_index + 2
        comune_raw = _clean_optional_string(row.get("COMUNE"))
        foglio = _normalize_lookup_token(row.get("FOGLIO"))
        particella = _normalize_lookup_token(row.get("PARTIC"))
        num_distretto = _normalize_lookup_token(row.get("N_DISTRETTO"))
        sezione = _normalize_name(row.get("SEZIONE"))
        nome_distretto = _clean_optional_string(row.get("DISTRETTO"))
        anno_row = pd.to_numeric(pd.Series([row.get("ANNO")]), errors="coerce").iloc[0]

        if not comune_raw or not foglio or not particella or not num_distretto:
            skipped_missing_fields += 1
            if len(preview_anomalies) < 50:
                preview_anomalies.append(
                    {"riga": row_number, "tipo": "DIST-ROW-MISSING", "comune": comune_raw, "foglio": foglio, "particella": particella}
                )
            continue

        resolved_comune = _resolve_comune(comune_raw, comuni_by_capacitas, comuni_by_catastale, comuni_by_name)
        if resolved_comune is None:
            skipped_invalid_comune += 1
            if len(preview_anomalies) < 50:
                preview_anomalies.append({"riga": row_number, "tipo": "DIST-COMUNE-NOT-FOUND", "comune": comune_raw})
            continue
        comune = resolved_comune.comune
        if sezione is None and resolved_comune.derived_sezione is not None:
            sezione = resolved_comune.derived_sezione

        key = (comune.id, sezione, foglio, particella)
        candidate = DistrettoExcelRow(
            row_number=row_number,
            anno_campagna=int(anno_row) if not pd.isna(anno_row) else anno_campagna,
            comune_raw=comune_raw,
            sezione=sezione,
            foglio=foglio,
            particella=particella,
            num_distretto=num_distretto,
            nome_distretto=nome_distretto,
            comune_id=comune.id,
            comune_nome=comune.nome_comune,
        )

        previous = row_candidates.get(key)
        if previous is not None:
            duplicate_collapsed += 1
            if previous.num_distretto != candidate.num_distretto or previous.nome_distretto != candidate.nome_distretto:
                duplicate_conflicts += 1
                if len(preview_anomalies) < 50:
                    preview_anomalies.append(
                        {
                            "riga": row_number,
                            "tipo": "DIST-DUPLICATE-CONFLICT",
                            "comune": comune.nome_comune,
                            "foglio": foglio,
                            "particella": particella,
                            "distretto_prev": previous.num_distretto,
                            "distretto_new": candidate.num_distretto,
                        }
                    )
        row_candidates[key] = candidate
        involved_comuni_ids.add(comune.id)
        comuni_rilevati.add(comune.nome_comune)
        distretti_rilevati.add(num_distretto)

    unique_rows = list(row_candidates.values())
    if log_callback:
        log_callback(f"Righe Excel lette: {len(dataframe):,}; chiavi univoche particella: {len(unique_rows):,}")

    current_particelle = (
        db.execute(
            select(CatParticella).where(
                CatParticella.is_current.is_(True),
                CatParticella.comune_id.in_(involved_comuni_ids),
            )
        )
        .scalars()
        .all()
        if involved_comuni_ids
        else []
    )
    particelle_by_key: dict[tuple[uuid.UUID, str | None, str, str], list[CatParticella]] = {}
    for particella_record in current_particelle:
        if particella_record.comune_id is None:
            continue
        key = (
            particella_record.comune_id,
            _normalize_name(particella_record.sezione_catastale),
            _normalize_lookup_token(particella_record.foglio),
            _normalize_lookup_token(particella_record.particella),
        )
        if key[2] is None or key[3] is None:
            continue
        particelle_by_key.setdefault(key, []).append(particella_record)

    distretti_by_num = {item.num_distretto: item for item in db.execute(select(CatDistretto)).scalars().all()}
    matched_rows = 0
    rows_without_match = 0
    particelle_aggiornate = 0
    particelle_invariate = 0
    history_written = 0
    distretti_creati = 0
    distretti_aggiornati = 0

    total_unique = len(unique_rows)
    for index, row_data in enumerate(unique_rows, start=1):
        key = (row_data.comune_id, row_data.sezione, row_data.foglio, row_data.particella)
        matches = particelle_by_key.get(key) if row_data.comune_id is not None else None
        if not matches:
            rows_without_match += 1
            if len(preview_anomalies) < 50:
                preview_anomalies.append(
                    {
                        "riga": row_data.row_number,
                        "tipo": "DIST-PARTICELLA-NOT-FOUND",
                        "comune": row_data.comune_nome or row_data.comune_raw,
                        "sezione": row_data.sezione,
                        "foglio": row_data.foglio,
                        "particella": row_data.particella,
                    }
                )
        else:
            matched_rows += 1
            distretto = distretti_by_num.get(row_data.num_distretto)
            if distretto is None:
                distretto = CatDistretto(
                    num_distretto=row_data.num_distretto,
                    nome_distretto=row_data.nome_distretto,
                    attivo=True,
                )
                db.add(distretto)
                distretti_by_num[row_data.num_distretto] = distretto
                distretti_creati += 1
            elif row_data.nome_distretto and distretto.nome_distretto != row_data.nome_distretto:
                distretto.nome_distretto = row_data.nome_distretto
                distretti_aggiornati += 1

            for particella_record in matches:
                if (
                    particella_record.num_distretto == row_data.num_distretto
                    and particella_record.nome_distretto == row_data.nome_distretto
                ):
                    particelle_invariate += 1
                    continue

                db.add(
                    CatParticellaHistory(
                        particella_id=particella_record.id,
                        comune_id=particella_record.comune_id,
                        national_code=particella_record.national_code,
                        cod_comune_capacitas=particella_record.cod_comune_capacitas,
                        codice_catastale=particella_record.codice_catastale,
                        foglio=particella_record.foglio,
                        particella=particella_record.particella,
                        subalterno=particella_record.subalterno,
                        superficie_mq=particella_record.superficie_mq,
                        superficie_grafica_mq=particella_record.superficie_grafica_mq,
                        num_distretto=particella_record.num_distretto,
                        geometry=particella_record.geometry,
                        valid_from=particella_record.valid_from,
                        valid_to=today,
                        change_reason="import_distretti_excel",
                    )
                )
                history_written += 1
                particella_record.num_distretto = row_data.num_distretto
                particella_record.nome_distretto = row_data.nome_distretto
                particelle_aggiornate += 1

        batch.righe_importate = index
        if log_callback and (index == total_unique or index == 1 or index % 250 == 0):
            log_callback(f"Aggiornamento distretti Excel: {index:,} / {total_unique:,} chiavi elaborate")

    batch.righe_anomalie = skipped_missing_fields + skipped_invalid_comune + rows_without_match + duplicate_conflicts
    batch.status = "completed"
    batch.completed_at = now
    batch.report_json = {
        "anno_campagna": anno_campagna,
        "righe_totali": len(dataframe),
        "righe_univoche": total_unique,
        "righe_importate": matched_rows,
        "righe_con_anomalie": batch.righe_anomalie,
        "righe_duplicate_collassate": duplicate_collapsed,
        "righe_duplicate_conflitto": duplicate_conflicts,
        "righe_scartate_campi_mancanti": skipped_missing_fields,
        "righe_scartate_comune_non_risolto": skipped_invalid_comune,
        "righe_senza_match_particella": rows_without_match,
        "particelle_aggiornate": particelle_aggiornate,
        "particelle_invariate": particelle_invariate,
        "history_written": history_written,
        "distretti_creati": distretti_creati,
        "distretti_aggiornati": distretti_aggiornati,
        "distretti_rilevati": sorted(distretti_rilevati),
        "comuni_rilevati": sorted(comuni_rilevati),
        "preview_anomalie": preview_anomalies,
    }
    db.commit()
    db.refresh(batch)
    return batch
