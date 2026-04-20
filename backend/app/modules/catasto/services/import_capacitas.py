from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatAnomalia,
    CatAliquota,
    CatDistretto,
    CatDistrettoCoefficiente,
    CatImportBatch,
    CatParticella,
    CatSchemaContributo,
    CatUtenzaIrrigua,
)
from app.modules.catasto.services.validation import (
    validate_codice_fiscale,
    validate_comune,
    validate_imponibile,
    validate_importo_0648,
    validate_importo_0985,
    validate_superficie,
)


COLUMN_MAPPING = {
    "ANNO": "anno_campagna",
    "PVC": "cod_provincia",
    "COM": "cod_comune_istat",
    "CCO": "cco",
    "FRA": "cod_frazione",
    "DISTRETTO": "num_distretto",
    "Unnamed: 7": "nome_distretto_loc",
    "COMUNE": "nome_comune",
    "SEZIONE": "sezione_catastale",
    "FOGLIO": "foglio",
    "PARTIC": "particella",
    "SUB": "subalterno",
    "SUP.CATA.": "sup_catastale_mq",
    "SUP.IRRIGABILE": "sup_irrigabile_mq",
    "Ind. Spese Fisse": "ind_spese_fisse",
    "Imponibile s.f.": "imponibile_sf",
    "ESENTE 0648": "esente_0648",
    "ALIQUOTA 0648": "aliquota_0648",
    "IMPORTO 0648": "importo_0648",
    "ALIQUOTA 0985": "aliquota_0985",
    "IMPORTO 0985": "importo_0985",
    "DENOMINAZIONE": "denominazione",
    "CODICE FISCALE": "codice_fiscale",
}

ANOMALIA_TYPES = {
    "VAL-01-sup_eccede": "Sup. irrigabile eccede catastale",
    "VAL-02-cf_invalido": "Codice fiscale non valido",
    "VAL-03-cf_mancante": "Codice fiscale mancante",
    "VAL-04-comune_invalido": "Comune ISTAT non valido",
    "VAL-05-particella_assente": "Particella assente in anagrafica",
    "VAL-06-imponibile": "Imponibile incoerente",
    "VAL-07-importi": "Importi incoerenti",
}


class CapacitasImportDuplicateError(ValueError):
    pass


def _clean_optional_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


def _clean_bool(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "si", "sì", "yes", "y", "x"}


def import_capacitas_excel(
    db: Session,
    file_bytes: bytes,
    filename: str,
    created_by: int,
    force: bool = False,
    batch_id: uuid.UUID | None = None,
) -> CatImportBatch:
    now = datetime.now(timezone.utc)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing_batch = db.execute(
        select(CatImportBatch).where(CatImportBatch.hash_file == file_hash, CatImportBatch.status == "completed")
    ).scalar_one_or_none()
    if existing_batch and not force:
        raise CapacitasImportDuplicateError(
            f"File già importato (batch {existing_batch.id}). Usa force=True per reimportare."
        )
    if existing_batch and force:
        existing_batch.status = "replaced"

    all_sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=str)
    sheet_name = next((name for name in all_sheets if name.lower().startswith("ruoli")), None)
    if not sheet_name:
        raise ValueError("Sheet 'Ruoli ANNO' non trovato nel file Excel.")
    dataframe = all_sheets[sheet_name].rename(columns={key: value for key, value in COLUMN_MAPPING.items() if key in all_sheets[sheet_name].columns})

    for column in ("foglio", "particella"):
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].fillna("").astype(str).str.strip()

    for column in ("subalterno", "sezione_catastale", "codice_fiscale", "nome_comune", "denominazione", "nome_distretto_loc"):
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].apply(_clean_optional_string)

    for column in ("anno_campagna", "cod_provincia", "cod_comune_istat", "cod_frazione", "num_distretto"):
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    for column in (
        "sup_catastale_mq",
        "sup_irrigabile_mq",
        "ind_spese_fisse",
        "imponibile_sf",
        "aliquota_0648",
        "importo_0648",
        "aliquota_0985",
        "importo_0985",
    ):
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    anno = int(dataframe["anno_campagna"].dropna().iloc[0]) if "anno_campagna" in dataframe.columns and not dataframe["anno_campagna"].dropna().empty else None
    batch = db.get(CatImportBatch, batch_id) if batch_id is not None else None
    if batch is None:
        batch = CatImportBatch(
            id=batch_id or uuid.uuid4(),
            filename=filename,
            tipo="capacitas_ruolo",
            anno_campagna=anno,
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
        batch.tipo = "capacitas_ruolo"
        batch.anno_campagna = anno
        batch.hash_file = file_hash
        batch.righe_totali = len(dataframe)
        batch.status = "processing"
        batch.errore = None

    comuni = [int(value) for value in dataframe.get("cod_comune_istat", pd.Series(dtype=float)).dropna().unique().tolist()]
    particelle = (
        db.execute(select(CatParticella).where(CatParticella.cod_comune_istat.in_(comuni), CatParticella.is_current.is_(True))).scalars().all()
        if comuni
        else []
    )
    particelle_idx = {
        (part.cod_comune_istat, part.foglio, part.particella, part.subalterno): part.id for part in particelle
    }
    distretti = {item.num_distretto: item for item in db.execute(select(CatDistretto)).scalars().all()}
    schemi = {item.codice: item for item in db.execute(select(CatSchemaContributo)).scalars().all()}

    utenze_mappings: list[dict[str, Any]] = []
    anomalie_mappings: list[dict[str, Any]] = []
    anomalie_count = {key: 0 for key in ANOMALIA_TYPES}
    preview_anomalie: list[dict[str, Any]] = []
    coefficienti_values: dict[tuple[str, int], list[float]] = {}
    aliquote_values: dict[tuple[str, int], set[float]] = {}

    def _flush_chunks() -> None:
        if not utenze_mappings:
            return
        db.bulk_insert_mappings(CatUtenzaIrrigua, utenze_mappings, render_nulls=True)
        if anomalie_mappings:
            db.bulk_insert_mappings(CatAnomalia, anomalie_mappings, render_nulls=True)
        utenze_mappings.clear()
        anomalie_mappings.clear()

    for row_index, row in dataframe.iterrows():
        row_get = lambda key: None if key not in dataframe.columns or pd.isna(row.get(key)) else row.get(key)
        cf_raw = _clean_optional_string(row_get("codice_fiscale"))
        cf_result = validate_codice_fiscale(cf_raw)
        cf_normalizzato = cf_result["cf_normalizzato"]
        comune_value = int(row_get("cod_comune_istat")) if row_get("cod_comune_istat") is not None else None
        foglio = str(row_get("foglio") or "")
        particella_value = str(row_get("particella") or "")
        subalterno = _clean_optional_string(row_get("subalterno"))

        lookup_key = (comune_value, foglio, particella_value, subalterno)
        particella_id = particelle_idx.get(lookup_key) if comune_value is not None else None

        v_superficie = validate_superficie(row_get("sup_irrigabile_mq"), row_get("sup_catastale_mq"))
        v_comune = validate_comune(comune_value)
        v_imponibile = validate_imponibile(row_get("imponibile_sf"), row_get("sup_irrigabile_mq"), row_get("ind_spese_fisse"))
        v_648 = validate_importo_0648(row_get("importo_0648"), row_get("imponibile_sf"), row_get("aliquota_0648"))
        v_985 = validate_importo_0985(row_get("importo_0985"), row_get("imponibile_sf"), row_get("aliquota_0985"))

        utenza_id = uuid.uuid4()
        utenza_anno = int(row_get("anno_campagna")) if row_get("anno_campagna") is not None else anno or now.year
        distretto_num = int(row_get("num_distretto")) if row_get("num_distretto") is not None else None
        ind_sf = row_get("ind_spese_fisse")
        aliquota_0648 = row_get("aliquota_0648")
        aliquota_0985 = row_get("aliquota_0985")

        utenza_mapping = {
            "id": utenza_id,
            "import_batch_id": batch.id,
            "anno_campagna": utenza_anno,
            "cco": _clean_optional_string(row_get("cco")),
            "cod_provincia": int(row_get("cod_provincia")) if row_get("cod_provincia") is not None else None,
            "cod_comune_istat": comune_value,
            "cod_frazione": int(row_get("cod_frazione")) if row_get("cod_frazione") is not None else None,
            "num_distretto": distretto_num,
            "nome_distretto_loc": _clean_optional_string(row_get("nome_distretto_loc")),
            "nome_comune": _clean_optional_string(row_get("nome_comune")),
            "sezione_catastale": _clean_optional_string(row_get("sezione_catastale")),
            "foglio": foglio or None,
            "particella": particella_value or None,
            "subalterno": subalterno,
            "particella_id": particella_id,
            "sup_catastale_mq": row_get("sup_catastale_mq"),
            "sup_irrigabile_mq": row_get("sup_irrigabile_mq"),
            "ind_spese_fisse": ind_sf,
            "imponibile_sf": row_get("imponibile_sf"),
            "esente_0648": _clean_bool(row_get("esente_0648")),
            "aliquota_0648": aliquota_0648,
            "importo_0648": row_get("importo_0648"),
            "aliquota_0985": aliquota_0985,
            "importo_0985": row_get("importo_0985"),
            "denominazione": _clean_optional_string(row_get("denominazione")),
            "codice_fiscale": cf_normalizzato if isinstance(cf_normalizzato, str) else None,
            "codice_fiscale_raw": cf_raw,
            "anomalia_superficie": not bool(v_superficie["ok"]),
            "anomalia_cf_invalido": bool(cf_result["tipo"] != "MANCANTE" and not cf_result["is_valid"]),
            "anomalia_cf_mancante": bool(cf_result["tipo"] == "MANCANTE"),
            "anomalia_comune_invalido": not bool(v_comune["is_valid"]),
            "anomalia_particella_assente": bool(particella_id is None and comune_value is not None),
            "anomalia_imponibile": not bool(v_imponibile["ok"]),
            "anomalia_importi": not bool(v_648["ok"]) or not bool(v_985["ok"]),
            "created_at": now,
        }
        utenze_mappings.append(utenza_mapping)

        for tipo, should_add, payload in (
            ("VAL-01-sup_eccede", not bool(v_superficie["ok"]), {"delta_mq": v_superficie["delta_mq"], "delta_pct": v_superficie["delta_pct"]}),
            ("VAL-02-cf_invalido", bool(cf_result["tipo"] != "MANCANTE" and not cf_result["is_valid"]), {"cf_raw": cf_raw, "cf_norm": cf_normalizzato, "error_code": cf_result["error_code"]}),
            ("VAL-03-cf_mancante", bool(cf_result["tipo"] == "MANCANTE"), {}),
            ("VAL-04-comune_invalido", not bool(v_comune["is_valid"]), {"cod_istat": comune_value}),
            ("VAL-05-particella_assente", bool(particella_id is None and comune_value is not None), {"foglio": foglio, "particella": particella_value, "subalterno": subalterno}),
            ("VAL-06-imponibile", not bool(v_imponibile["ok"]), v_imponibile),
            ("VAL-07-importi", not bool(v_648["ok"]) or not bool(v_985["ok"]), {"v07_648": v_648, "v07_985": v_985}),
        ):
            if not should_add:
                continue
            anomalie_count[tipo] += 1
            if len(preview_anomalie) < 50:
                preview_anomalie.append({"riga": row_index + 2, "tipo": tipo, **payload})
            anomalie_mappings.append(
                {
                    "id": uuid.uuid4(),
                    "utenza_id": utenza_id,
                    "particella_id": particella_id,
                    "anno_campagna": utenza_anno,
                    "tipo": tipo,
                    "severita": "error" if tipo in {"VAL-01-sup_eccede", "VAL-02-cf_invalido"} else "warning",
                    "descrizione": ANOMALIA_TYPES[tipo],
                    "dati_json": payload,
                    "status": "aperta",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        if distretto_num is not None and ind_sf is not None and anno is not None:
            coefficienti_values.setdefault((str(distretto_num), anno), []).append(float(ind_sf))
        if anno is not None:
            if aliquota_0648 is not None:
                aliquote_values.setdefault(("0648", anno), set()).add(float(aliquota_0648))
            if aliquota_0985 is not None:
                aliquote_values.setdefault(("0985", anno), set()).add(float(aliquota_0985))

        if len(utenze_mappings) >= 5000:
            _flush_chunks()

    _flush_chunks()

    # Upsert coefficienti distretto per anno: scegliamo il valore più frequente nel file (fallback: max)
    if anno is not None and coefficienti_values:
        for (num_distretto, coeff_anno), values in coefficienti_values.items():
            distretto = distretti.get(num_distretto)
            if distretto is None:
                continue
            chosen: float
            if values:
                counts: dict[float, int] = {}
                for v in values:
                    counts[v] = counts.get(v, 0) + 1
                chosen = sorted(counts.items(), key=lambda x: (-x[1], -x[0]))[0][0]
            else:
                continue

            coefficiente = db.execute(
                select(CatDistrettoCoefficiente).where(
                    CatDistrettoCoefficiente.distretto_id == distretto.id,
                    CatDistrettoCoefficiente.anno == coeff_anno,
                )
            ).scalar_one_or_none()
            if coefficiente is None:
                db.add(
                    CatDistrettoCoefficiente(
                        distretto_id=distretto.id,
                        anno=coeff_anno,
                        ind_spese_fisse=chosen,
                    )
                )
            else:
                coefficiente.ind_spese_fisse = chosen

    # Upsert aliquote (0648/0985) se il file contiene un valore coerente per schema+anno
    for (schema_codice, aliq_anno), values in aliquote_values.items():
        if len(values) != 1:
            # valori multipli -> non upsert automatico
            continue
        schema = schemi.get(schema_codice)
        if schema is None:
            continue
        aliquota_value = list(values)[0]
        existing = db.execute(
            select(CatAliquota).where(CatAliquota.schema_id == schema.id, CatAliquota.anno == aliq_anno)
        ).scalar_one_or_none()
        if existing is None:
            db.add(CatAliquota(schema_id=schema.id, anno=aliq_anno, aliquota=aliquota_value))
        else:
            existing.aliquota = aliquota_value

    batch.righe_importate = int(
        db.execute(
            select(func.count()).select_from(CatUtenzaIrrigua).where(CatUtenzaIrrigua.import_batch_id == batch.id)
        ).scalar_one()
    )
    righe_con_anomalie = int(
        db.execute(
            select(func.count())
            .select_from(CatUtenzaIrrigua)
            .where(
                CatUtenzaIrrigua.import_batch_id == batch.id,
                or_(
                    CatUtenzaIrrigua.anomalia_superficie.is_(True),
                    CatUtenzaIrrigua.anomalia_cf_invalido.is_(True),
                    CatUtenzaIrrigua.anomalia_cf_mancante.is_(True),
                    CatUtenzaIrrigua.anomalia_comune_invalido.is_(True),
                    CatUtenzaIrrigua.anomalia_particella_assente.is_(True),
                    CatUtenzaIrrigua.anomalia_imponibile.is_(True),
                    CatUtenzaIrrigua.anomalia_importi.is_(True),
                ),
            )
        ).scalar_one()
    )
    batch.righe_anomalie = righe_con_anomalie
    batch.status = "completed"
    batch.completed_at = now
    batch.report_json = {
        "anno_campagna": anno,
        "righe_totali": len(dataframe),
        "righe_importate": batch.righe_importate,
        "righe_con_anomalie": righe_con_anomalie,
        "anomalie": {key: {"count": value} for key, value in anomalie_count.items()},
        "preview_anomalie": preview_anomalie,
        "distretti_rilevati": [int(value) for value in dataframe.get("num_distretto", pd.Series(dtype=float)).dropna().unique().tolist()],
        "comuni_rilevati": sorted({_clean_optional_string(value) for value in dataframe.get("nome_comune", pd.Series(dtype=str)).tolist()} - {None}),
    }
    db.commit()
    db.refresh(batch)
    return batch
