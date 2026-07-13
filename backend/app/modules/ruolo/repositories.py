"""Repository layer per le query del modulo Ruolo."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import String, case, cast, desc, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.catasto import CatastoParcel
from app.models.catasto_phase1 import CatImportBatch, CatUtenzaIrrigua
from app.modules.catasto.services.dashboard_queries import active_capacitas_batch_id
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject
from app.modules.utenze.services.subject_identity import normalize_tax_identifier


# ---------------------------------------------------------------------------
# Import Jobs
# ---------------------------------------------------------------------------

def _parse_incass_amount(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    text = str(value).strip()
    if not text:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return round(float(text), 2)
    except ValueError:
        return 0.0


def _iter_incass_partite(raw_detail_json: dict | list | None) -> list[dict[str, Any]]:
    if not isinstance(raw_detail_json, dict):
        return []
    partitario = raw_detail_json.get("partitario")
    if not isinstance(partitario, dict):
        return []
    partite = partitario.get("partite")
    if not isinstance(partite, list):
        return []
    return [partita for partita in partite if isinstance(partita, dict)]


def _load_ruolo_incass_by_tax(
    db: Session,
    *,
    anno: int,
) -> tuple[dict[str, dict[str, Any]], int]:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        amount_sql = """
            CASE
                WHEN val IS NULL OR btrim(val) = '' THEN 0::numeric
                WHEN val LIKE '%,%' AND val LIKE '%.%' THEN
                    CASE
                        WHEN strpos(reverse(val), ',') < strpos(reverse(val), '.') THEN replace(replace(val, '.', ''), ',', '.')::numeric
                        ELSE replace(val, ',', '')::numeric
                    END
                WHEN val LIKE '%,%' THEN replace(val, ',', '.')::numeric
                ELSE (val)::numeric
            END
        """
        rows = db.execute(
            text(f"""
                SELECT
                    upper(regexp_replace(coalesce(apn.codice_fiscale, apn.partita_iva, ''), '\\s+', '', 'g')) AS tax_code,
                    max(apn.display_name) FILTER (WHERE apn.display_name IS NOT NULL AND btrim(apn.display_name) <> '') AS display_name,
                    COALESCE(sum(
                        {amount_sql.replace("val", "partita.value->>'importo_0648_euro'")}
                    ), 0)::float AS amount_0648,
                    COALESCE(sum(
                        {amount_sql.replace("val", "partita.value->>'importo_0985_euro'")}
                    ), 0)::float AS amount_0985,
                    COALESCE(sum(
                        {amount_sql.replace("val", "partita.value->>'importo_0668_euro'")}
                    ), 0)::float AS amount_0668
                FROM ana_payment_notices apn
                LEFT JOIN LATERAL jsonb_array_elements(
                    CASE
                        WHEN jsonb_typeof((apn.raw_detail_json::jsonb)->'partitario'->'partite') = 'array'
                            THEN (apn.raw_detail_json::jsonb)->'partitario'->'partite'
                        ELSE '[]'::jsonb
                    END
                ) AS partita(value) ON TRUE
                WHERE apn.anno = :anno
                  AND apn.source_system = 'incass'
                GROUP BY 1
            """),
            {"anno": str(anno)},
        ).mappings().all()

        ruolo_by_tax: dict[str, dict[str, Any]] = {}
        ruolo_missing_tax = 0
        for row in rows:
            tax_code = normalize_tax_identifier(row["tax_code"])
            if not tax_code:
                ruolo_missing_tax += 1
                continue
            ruolo_by_tax[tax_code] = {
                "tax_code": tax_code,
                "display_name": row["display_name"],
                "amount_0648": _round_currency(float(row["amount_0648"] or 0)),
                "amount_0985": _round_currency(float(row["amount_0985"] or 0)),
                "amount_0668": _round_currency(float(row["amount_0668"] or 0)),
            }
        return ruolo_by_tax, ruolo_missing_tax

    rows = db.execute(
        select(
            AnagraficaPaymentNotice.codice_fiscale,
            AnagraficaPaymentNotice.partita_iva,
            AnagraficaPaymentNotice.display_name,
            AnagraficaPaymentNotice.raw_detail_json,
        ).where(
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()

    ruolo_by_tax: dict[str, dict[str, Any]] = {}
    ruolo_missing_tax = 0

    for row in rows:
        tax_code = normalize_tax_identifier(row.codice_fiscale or row.partita_iva)
        if not tax_code:
            ruolo_missing_tax += 1
            continue
        current = ruolo_by_tax.get(tax_code)
        if current is None:
            current = {
                "tax_code": tax_code,
                "display_name": row.display_name,
                "amount_0648": 0.0,
                "amount_0985": 0.0,
                "amount_0668": 0.0,
            }
            ruolo_by_tax[tax_code] = current
        elif not current["display_name"] and row.display_name:
            current["display_name"] = row.display_name

        for partita in _iter_incass_partite(row.raw_detail_json):
            current["amount_0648"] = round(
                current["amount_0648"] + _parse_incass_amount(partita.get("importo_0648_euro")),
                2,
            )
            current["amount_0985"] = round(
                current["amount_0985"] + _parse_incass_amount(partita.get("importo_0985_euro")),
                2,
            )
            current["amount_0668"] = round(
                current["amount_0668"] + _parse_incass_amount(partita.get("importo_0668_euro")),
                2,
            )

    return ruolo_by_tax, ruolo_missing_tax


def _load_ruolo_incass_by_comune(
    db: Session,
    *,
    anno: int,
) -> dict[str, dict[str, float | str]]:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        amount_sql = """
            CASE
                WHEN val IS NULL OR btrim(val) = '' THEN 0::numeric
                WHEN val LIKE '%,%' AND val LIKE '%.%' THEN
                    CASE
                        WHEN strpos(reverse(val), ',') < strpos(reverse(val), '.') THEN replace(replace(val, '.', ''), ',', '.')::numeric
                        ELSE replace(val, ',', '')::numeric
                    END
                WHEN val LIKE '%,%' THEN replace(val, ',', '.')::numeric
                ELSE (val)::numeric
            END
        """
        rows = db.execute(
            text(f"""
                SELECT
                    coalesce(nullif(btrim(partita.value->>'comune_nome'), ''), 'N/D') AS comune_nome,
                    COALESCE(sum(
                        {amount_sql.replace("val", "partita.value->>'importo_0648_euro'")}
                    ), 0)::float AS ruolo_0648,
                    COALESCE(sum(
                        {amount_sql.replace("val", "partita.value->>'importo_0985_euro'")}
                    ), 0)::float AS ruolo_0985
                FROM ana_payment_notices apn
                JOIN LATERAL jsonb_array_elements(
                    CASE
                        WHEN jsonb_typeof((apn.raw_detail_json::jsonb)->'partitario'->'partite') = 'array'
                            THEN (apn.raw_detail_json::jsonb)->'partitario'->'partite'
                        ELSE '[]'::jsonb
                    END
                ) AS partita(value) ON TRUE
                WHERE apn.anno = :anno
                  AND apn.source_system = 'incass'
                GROUP BY 1
            """),
            {"anno": str(anno)},
        ).mappings().all()

        return {
            str(row["comune_nome"]): {
                "comune_nome": str(row["comune_nome"]),
                "ruolo_0648": _round_currency(float(row["ruolo_0648"] or 0)),
                "ruolo_0985": _round_currency(float(row["ruolo_0985"] or 0)),
            }
            for row in rows
        }

    rows = db.execute(
        select(AnagraficaPaymentNotice.raw_detail_json).where(
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()

    comuni: dict[str, dict[str, float | str]] = {}
    for row in rows:
        for partita in _iter_incass_partite(row.raw_detail_json):
            key = str(partita.get("comune_nome") or "N/D").strip() or "N/D"
            current = comuni.setdefault(
                key,
                {
                    "comune_nome": key,
                    "ruolo_0648": 0.0,
                    "ruolo_0985": 0.0,
                },
            )
            current["ruolo_0648"] = round(
                float(current["ruolo_0648"]) + _parse_incass_amount(partita.get("importo_0648_euro")),
                2,
            )
            current["ruolo_0985"] = round(
                float(current["ruolo_0985"]) + _parse_incass_amount(partita.get("importo_0985_euro")),
                2,
            )
    return comuni


def _round_currency(value: float) -> float:
    return round(value, 2)


def _compute_gaia_amount(
    imponibile: Decimal | float | int | None,
    aliquota: Decimal | float | int | None,
) -> float:
    if imponibile is None or aliquota is None:
        return 0.0
    return _round_currency(float(imponibile) * float(aliquota))


_COMUNE_ALIAS_BY_NORMALIZED_NAME = {
    "SILI": "ORISTANO",
    "SILI'": "ORISTANO",
    "SAN NICOLO D'ARCIDANO": "SAN NICOLO ARCIDANO",
    "SAN NICOLO DARCIDANO": "SAN NICOLO ARCIDANO",
}


def _normalize_capacitas_check_comune_name(value: object) -> str:
    text_value = str(value or "N/D").strip() or "N/D"
    if "*" in text_value:
        text_value = text_value.rsplit("*", 1)[-1]
    normalized = " ".join(text_value.upper().split())
    return _COMUNE_ALIAS_BY_NORMALIZED_NAME.get(normalized, normalized)


def _classify_capacitas_mismatch(
    *,
    status: str,
    threshold: float,
    ruolo_0648: float,
    ruolo_0985: float,
    gaia_0648: float,
    gaia_0985: float,
    excel_0648: float,
    excel_0985: float,
) -> str:
    material_threshold = max(threshold * 100, 1.0)

    if status == "only_in_capacitas":
        return "problema_ruolo"
    if status == "only_in_ruolo":
        return "problema_snapshot_excel"
    if status != "amount_mismatch":
        return "allineato"

    ruolo_total = ruolo_0648 + ruolo_0985
    gaia_total = gaia_0648 + gaia_0985
    excel_total = excel_0648 + excel_0985
    ruolo_vs_gaia_total = abs(ruolo_total - gaia_total)
    ruolo_vs_excel_total = abs(ruolo_total - excel_total)
    gaia_vs_excel_total = abs(gaia_total - excel_total)

    # GAIA and Excel are effectively aligned: the outlier is the ruolo side.
    if gaia_vs_excel_total <= material_threshold:
        return "problema_ruolo"

    # Ruolo materially matches Excel better than GAIA.
    if ruolo_vs_excel_total + material_threshold < ruolo_vs_gaia_total:
        return "problema_ricalcolo_gaia"

    # Ruolo materially matches GAIA better than the imported Excel snapshot.
    if ruolo_vs_gaia_total + material_threshold < ruolo_vs_excel_total:
        return "problema_snapshot_excel"

    if gaia_vs_excel_total > ruolo_vs_gaia_total:
        return "problema_snapshot_excel"
    return "problema_ruolo"  # pragma: no cover - non-negative amount tie fallback.


def _load_capacitas_snapshot_by_tax(
    db: Session,
    *,
    anno: int,
) -> tuple[dict[str, dict[str, Any]], int, Any | None]:
    active_batch_id = active_capacitas_batch_id(db, anno)
    if active_batch_id is None:
        return {}, 0, None

    rows = db.execute(
        select(
            CatUtenzaIrrigua.codice_fiscale,
            CatUtenzaIrrigua.denominazione,
            CatUtenzaIrrigua.importo_0648,
            CatUtenzaIrrigua.importo_0985,
            CatUtenzaIrrigua.imponibile_sf,
            CatUtenzaIrrigua.aliquota_0648,
            CatUtenzaIrrigua.aliquota_0985,
            CatUtenzaIrrigua.anomalia_imponibile,
            CatUtenzaIrrigua.anomalia_importi,
        ).where(
            CatUtenzaIrrigua.anno_campagna == anno,
            CatUtenzaIrrigua.import_batch_id == active_batch_id,
        )
    ).all()

    snapshot_by_tax: dict[str, dict[str, Any]] = {}
    missing_tax = 0

    def _to_float(value: Decimal | float | int | None) -> float:
        if value is None:
            return 0.0
        return _round_currency(float(value))

    for row in rows:
        tax_code = normalize_tax_identifier(row.codice_fiscale)
        if not tax_code:
            missing_tax += 1
            continue

        current = snapshot_by_tax.get(tax_code)
        if current is None:
            current = {
                "tax_code": tax_code,
                "display_name": row.denominazione,
                "excel_0648": 0.0,
                "excel_0985": 0.0,
                "gaia_0648": 0.0,
                "gaia_0985": 0.0,
                "anomalous_rows_count": 0,
                "clean_rows_count": 0,
                "excel_total_anomalous_rows": 0.0,
                "gaia_total_anomalous_rows": 0.0,
                "excel_total_clean_rows": 0.0,
                "gaia_total_clean_rows": 0.0,
            }
            snapshot_by_tax[tax_code] = current
        elif not current["display_name"] and row.denominazione:
            current["display_name"] = row.denominazione

        excel_0648 = _to_float(row.importo_0648)
        excel_0985 = _to_float(row.importo_0985)
        gaia_0648 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0648)
        gaia_0985 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0985)
        is_anomalous = bool(row.anomalia_imponibile or row.anomalia_importi)

        current["excel_0648"] = _round_currency(current["excel_0648"] + excel_0648)
        current["excel_0985"] = _round_currency(current["excel_0985"] + excel_0985)
        current["gaia_0648"] = _round_currency(current["gaia_0648"] + gaia_0648)
        current["gaia_0985"] = _round_currency(current["gaia_0985"] + gaia_0985)
        if is_anomalous:
            current["anomalous_rows_count"] += 1
            current["excel_total_anomalous_rows"] = _round_currency(
                current["excel_total_anomalous_rows"] + excel_0648 + excel_0985
            )
            current["gaia_total_anomalous_rows"] = _round_currency(
                current["gaia_total_anomalous_rows"] + gaia_0648 + gaia_0985
            )
        else:
            current["clean_rows_count"] += 1
            current["excel_total_clean_rows"] = _round_currency(
                current["excel_total_clean_rows"] + excel_0648 + excel_0985
            )
            current["gaia_total_clean_rows"] = _round_currency(
                current["gaia_total_clean_rows"] + gaia_0648 + gaia_0985
            )

    return snapshot_by_tax, missing_tax, active_batch_id


def _load_capacitas_snapshot_by_comune(
    db: Session,
    *,
    anno: int,
) -> tuple[dict[str, dict[str, float | str]], Any | None]:
    active_batch_id = active_capacitas_batch_id(db, anno)
    if active_batch_id is None:
        return {}, None

    rows = db.execute(
        select(
            func.coalesce(CatUtenzaIrrigua.nome_comune, "N/D").label("comune_nome"),
            CatUtenzaIrrigua.importo_0648,
            CatUtenzaIrrigua.importo_0985,
            CatUtenzaIrrigua.imponibile_sf,
            CatUtenzaIrrigua.aliquota_0648,
            CatUtenzaIrrigua.aliquota_0985,
        ).where(
            CatUtenzaIrrigua.anno_campagna == anno,
            CatUtenzaIrrigua.import_batch_id == active_batch_id,
        )
    ).all()

    comuni: dict[str, dict[str, float | str]] = {}
    for row in rows:
        key = row.comune_nome or "N/D"
        current = comuni.setdefault(
            key,
            {
                "comune_nome": key,
                "excel_0648": 0.0,
                "excel_0985": 0.0,
                "gaia_0648": 0.0,
                "gaia_0985": 0.0,
            },
        )
        current["excel_0648"] = _round_currency(float(current["excel_0648"]) + float(row.importo_0648 or 0))
        current["excel_0985"] = _round_currency(float(current["excel_0985"]) + float(row.importo_0985 or 0))
        current["gaia_0648"] = _round_currency(
            float(current["gaia_0648"]) + _compute_gaia_amount(row.imponibile_sf, row.aliquota_0648)
        )
        current["gaia_0985"] = _round_currency(
            float(current["gaia_0985"]) + _compute_gaia_amount(row.imponibile_sf, row.aliquota_0985)
        )
    return comuni, active_batch_id

def get_job(db: Session, job_id: uuid.UUID) -> RuoloImportJob | None:
    return db.get(RuoloImportJob, job_id)


def list_jobs(
    db: Session,
    anno: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RuoloImportJob], int]:
    q = select(RuoloImportJob)
    if anno is not None:
        q = q.where(RuoloImportJob.anno_tributario == anno)
    q = q.order_by(RuoloImportJob.created_at.desc())

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), total or 0


# ---------------------------------------------------------------------------
# Avvisi
# ---------------------------------------------------------------------------

def get_avviso(db: Session, avviso_id: uuid.UUID) -> RuoloAvviso | None:
    return db.get(RuoloAvviso, avviso_id)


def get_avviso_partite(db: Session, avviso_id: uuid.UUID) -> list[RuoloPartita]:
    return list(
        db.scalars(
            select(RuoloPartita)
            .where(RuoloPartita.avviso_id == avviso_id)
            .order_by(RuoloPartita.comune_nome)
        ).all()
    )


def get_partita_particelle(db: Session, partita_id: uuid.UUID) -> list[RuoloParticella]:
    return list(
        db.scalars(
            select(RuoloParticella)
            .where(RuoloParticella.partita_id == partita_id)
        ).all()
    )


def list_avvisi(
    db: Session,
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = None,
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    query = select(RuoloAvviso)

    if anno is not None:
        query = query.where(RuoloAvviso.anno_tributario == anno)
    if subject_id:
        try:
            sid = uuid.UUID(subject_id)
            query = query.where(RuoloAvviso.subject_id == sid)
        except ValueError:
            pass
    if q:
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                RuoloAvviso.codice_cnc.ilike(search_term),
                func.coalesce(RuoloAvviso.nominativo_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_fiscale_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_utenza, "").ilike(search_term),
                cast(RuoloAvviso.anno_tributario, String).ilike(search_term),
                RuoloAvviso.id.in_(
                    select(RuoloPartita.avviso_id).where(
                        func.coalesce(RuoloPartita.comune_nome, "").ilike(search_term)
                    )
                ),
            )
        )
    if codice_fiscale:
        query = query.where(RuoloAvviso.codice_fiscale_raw.ilike(f"%{codice_fiscale}%"))
    if comune:
        # Filtra per comune tramite join partite
        query = query.where(
            RuoloAvviso.id.in_(
                select(RuoloPartita.avviso_id).where(
                    RuoloPartita.comune_nome.ilike(f"%{comune}%")
                )
            )
        )
    if codice_utenza:
        query = query.where(RuoloAvviso.codice_utenza == codice_utenza)
    if unlinked:
        query = query.where(RuoloAvviso.subject_id.is_(None))

    query = query.order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.nominativo_raw)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    avvisi = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    # Arricchisci con display_name del soggetto
    results = []
    for avviso in avvisi:
        display_name = _get_subject_display_name(db, avviso.subject_id)
        results.append({
            "avviso": avviso,
            "display_name": display_name,
            "is_linked": avviso.subject_id is not None,
        })

    return results, total or 0


def list_avvisi_by_subject(
    db: Session,
    subject_id: uuid.UUID,
) -> list[RuoloAvviso]:
    return list(
        db.scalars(
            select(RuoloAvviso)
            .where(RuoloAvviso.subject_id == subject_id)
            .order_by(RuoloAvviso.anno_tributario.desc())
        ).all()
    )


def search_particelle(
    db: Session,
    anno: int | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    comune: str | None = None,
    match_status: str | None = None,
    match_reason: str | None = None,
    unmatched_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[RuoloParticella], int]:
    q = select(RuoloParticella)

    if anno is not None:
        q = q.where(RuoloParticella.anno_tributario == anno)
    if foglio:
        q = q.where(RuoloParticella.foglio == foglio)
    if particella:
        q = q.where(RuoloParticella.particella == particella)
    if comune:
        q = q.where(
            RuoloParticella.partita_id.in_(
                select(RuoloPartita.id).where(
                    RuoloPartita.comune_nome.ilike(f"%{comune}%")
                )
            )
        )
    if match_status:
        q = q.where(RuoloParticella.cat_particella_match_status == match_status)
    if match_reason:
        q = q.where(RuoloParticella.cat_particella_match_reason == match_reason)
    if unmatched_only:
        q = q.where(RuoloParticella.cat_particella_id.is_(None))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(RuoloParticella.anno_tributario.desc(), RuoloParticella.foglio, RuoloParticella.particella)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total or 0


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

def get_stats(db: Session, anno: int | None = None) -> list[dict]:
    """Aggregati per anno (o tutti gli anni se anno=None)."""
    query = (
        select(
            RuoloAvviso.anno_tributario.label("anno_tributario"),
            func.count(RuoloAvviso.id).label("total_avvisi"),
            func.count(RuoloAvviso.subject_id).label("avvisi_collegati"),
            func.sum(RuoloAvviso.importo_totale_0648).label("totale_0648"),
            func.sum(RuoloAvviso.importo_totale_0985).label("totale_0985"),
            func.sum(RuoloAvviso.importo_totale_0668).label("totale_0668"),
            func.sum(RuoloAvviso.importo_totale_euro).label("totale_euro"),
        )
        .group_by(RuoloAvviso.anno_tributario)
        .order_by(RuoloAvviso.anno_tributario.desc())
    )
    if anno is not None:
        query = query.where(RuoloAvviso.anno_tributario == anno)

    rows = db.execute(query).all()
    return [
        {
            "anno_tributario": row.anno_tributario,
            "total_avvisi": int(row.total_avvisi or 0),
            "avvisi_collegati": int(row.avvisi_collegati or 0),
            "avvisi_non_collegati": int((row.total_avvisi or 0) - (row.avvisi_collegati or 0)),
            "totale_0648": float(row.totale_0648) if row.totale_0648 is not None else None,
            "totale_0985": float(row.totale_0985) if row.totale_0985 is not None else None,
            "totale_0668": float(row.totale_0668) if row.totale_0668 is not None else None,
            "totale_euro": float(row.totale_euro) if row.totale_euro is not None else None,
        }
        for row in rows
    ]


def get_particelle_summary(db: Session, anno: int | None = None) -> dict:
    base_query = select(RuoloParticella)
    if anno is not None:
        base_query = base_query.where(RuoloParticella.anno_tributario == anno)
    base_sq = base_query.subquery()

    total_particelle = db.scalar(select(func.count()).select_from(base_sq)) or 0
    collegate_catasto = db.scalar(
        select(func.count()).select_from(base_sq).where(base_sq.c.cat_particella_id.is_not(None))
    ) or 0
    non_collegate_catasto = total_particelle - collegate_catasto
    soppresse_ade = db.scalar(
        select(func.count()).select_from(base_sq).where(base_sq.c.ade_scan_classification == "suppressed")
    ) or 0
    return {
        "anno_tributario": anno,
        "total_particelle": int(total_particelle),
        "collegate_catasto": int(collegate_catasto),
        "non_collegate_catasto": int(non_collegate_catasto),
        "soppresse_ade": int(soppresse_ade),
    }


def get_stats_comuni(db: Session, anno: int) -> list[dict]:
    """Ripartizione importi per comune per anno."""
    partite_q = (
        select(
            RuoloPartita.comune_nome,
            func.sum(RuoloPartita.importo_0648).label("totale_0648"),
            func.sum(RuoloPartita.importo_0985).label("totale_0985"),
            func.sum(RuoloPartita.importo_0668).label("totale_0668"),
            func.count(RuoloPartita.avviso_id.distinct()).label("num_avvisi"),
            func.count(RuoloPartita.id.distinct()).label("num_partite"),
        )
        .join(RuoloAvviso, RuoloPartita.avviso_id == RuoloAvviso.id)
        .where(RuoloAvviso.anno_tributario == anno)
        .group_by(RuoloPartita.comune_nome)
        .order_by(RuoloPartita.comune_nome)
    )
    particelle_q = (
        select(
            RuoloPartita.comune_nome.label("comune_nome"),
            func.count(RuoloParticella.id).label("num_particelle"),
            func.sum(case((RuoloParticella.cat_particella_id.is_(None), 1), else_=0)).label("non_collegate_catasto"),
        )
        .join(RuoloPartita, RuoloParticella.partita_id == RuoloPartita.id)
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(RuoloPartita.comune_nome)
    )

    partite_rows = db.execute(partite_q).all()
    particelle_rows = db.execute(particelle_q).all()
    particelle_by_comune = {
        row.comune_nome: {
            "num_particelle": int(row.num_particelle or 0),
            "non_collegate_catasto": int(row.non_collegate_catasto or 0),
        }
        for row in particelle_rows
    }

    result = []
    for row in partite_rows:
        t0648 = float(row.totale_0648) if row.totale_0648 else None
        t0985 = float(row.totale_0985) if row.totale_0985 else None
        t0668 = float(row.totale_0668) if row.totale_0668 else None
        parts = [v for v in [t0648, t0985, t0668] if v is not None]
        totale_euro = sum(parts) if parts else None
        particelle_metrics = particelle_by_comune.get(row.comune_nome, {})
        result.append({
            "comune_nome": row.comune_nome,
            "anno_tributario": anno,
            "totale_0648": t0648,
            "totale_0985": t0985,
            "totale_0668": t0668,
            "totale_euro": totale_euro,
            "num_avvisi": int(row.num_avvisi or 0),
            "num_partite": int(row.num_partite or 0),
            "num_particelle": int(particelle_metrics.get("num_particelle", 0)),
            "non_collegate_catasto": int(particelle_metrics.get("non_collegate_catasto", 0)),
        })
    return result


def get_stats_analytics(db: Session, anno: int) -> dict[str, Any]:
    stats_by_anno = get_stats(db, anno=anno)
    if not stats_by_anno:
        return {
            "anno_tributario": anno,
            "particelle_summary": get_particelle_summary(db, anno=anno),
            "tributi_breakdown": [],
            "match_status_breakdown": [],
            "match_reason_breakdown": [],
            "distretto_breakdown": [],
            "coltura_breakdown": [],
            "comuni": [],
        }

    stats = stats_by_anno[0]
    tributi_breakdown = [
        {"key": "0648", "label": "0648 Manutenzione", "amount": float(stats["totale_0648"] or 0)},
        {"key": "0985", "label": "0985 Irrigazione", "amount": float(stats["totale_0985"] or 0)},
        {"key": "0668", "label": "0668 Istituzionale", "amount": float(stats["totale_0668"] or 0)},
    ]

    status_expr = func.coalesce(RuoloParticella.cat_particella_match_status, "unknown")
    reason_expr = func.coalesce(RuoloParticella.cat_particella_match_reason, "unspecified")
    distretto_expr = func.coalesce(RuoloParticella.distretto, "N/D")
    coltura_expr = func.coalesce(RuoloParticella.coltura, "N/D")

    status_rows = db.execute(
        select(
            status_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(status_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
    ).all()

    reason_rows = db.execute(
        select(
            reason_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(
            RuoloParticella.anno_tributario == anno,
            RuoloParticella.cat_particella_id.is_(None),
        )
        .group_by(reason_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    distretto_rows = db.execute(
        select(
            distretto_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(distretto_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    coltura_rows = db.execute(
        select(
            coltura_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(coltura_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    return {
        "anno_tributario": anno,
        "particelle_summary": get_particelle_summary(db, anno=anno),
        "tributi_breakdown": tributi_breakdown,
        "match_status_breakdown": [
            {"key": row.key, "label": row.key.replace("_", " "), "count": int(row.count or 0)}
            for row in status_rows
        ],
        "match_reason_breakdown": [
            {"key": row.key, "label": row.key.replace("_", " "), "count": int(row.count or 0)}
            for row in reason_rows
        ],
        "distretto_breakdown": [
            {"key": row.key, "label": row.key, "count": int(row.count or 0)}
            for row in distretto_rows
        ],
        "coltura_breakdown": [
            {"key": row.key, "label": row.key, "count": int(row.count or 0)}
            for row in coltura_rows
        ],
        "comuni": get_stats_comuni(db, anno=anno),
    }


def get_capacitas_check(
    db: Session,
    *,
    anno: int,
    min_delta: float = 0.01,
    limit: int = 50,
) -> dict[str, Any]:
    threshold = abs(float(min_delta))
    ruolo_by_tax, ruolo_missing_tax = _load_ruolo_incass_by_tax(db, anno=anno)
    capacitas_by_tax, capacitas_missing_tax, active_batch_id = _load_capacitas_snapshot_by_tax(db, anno=anno)

    items: list[dict[str, Any]] = []
    mismatch_positions = 0
    all_tax_codes = sorted(set(ruolo_by_tax) | set(capacitas_by_tax))
    for tax_code in all_tax_codes:
        ruolo_entry = ruolo_by_tax.get(tax_code)
        capacitas_entry = capacitas_by_tax.get(tax_code)
        ruolo_0648 = ruolo_entry["amount_0648"] if ruolo_entry else 0.0
        ruolo_0985 = ruolo_entry["amount_0985"] if ruolo_entry else 0.0
        gaia_0648 = capacitas_entry["gaia_0648"] if capacitas_entry else 0.0
        gaia_0985 = capacitas_entry["gaia_0985"] if capacitas_entry else 0.0
        excel_0648 = capacitas_entry["excel_0648"] if capacitas_entry else 0.0
        excel_0985 = capacitas_entry["excel_0985"] if capacitas_entry else 0.0
        delta_0648 = round(ruolo_0648 - gaia_0648, 2)
        delta_0985 = round(ruolo_0985 - gaia_0985, 2)
        delta_gaia_excel_0648 = round(gaia_0648 - excel_0648, 2)
        delta_gaia_excel_0985 = round(gaia_0985 - excel_0985, 2)
        ruolo_totale_confrontabile = round(ruolo_0648 + ruolo_0985, 2)
        gaia_totale_confrontabile = round(gaia_0648 + gaia_0985, 2)
        excel_totale_confrontabile = round(excel_0648 + excel_0985, 2)
        delta_totale_confrontabile = round(ruolo_totale_confrontabile - gaia_totale_confrontabile, 2)
        delta_gaia_excel_totale_confrontabile = round(gaia_totale_confrontabile - excel_totale_confrontabile, 2)
        anomaly_gap = round(
            float(capacitas_entry["excel_total_anomalous_rows"] - capacitas_entry["gaia_total_anomalous_rows"]),
            2,
        ) if capacitas_entry else 0.0
        anomaly_gap_share = 0.0
        if delta_gaia_excel_totale_confrontabile != 0:
            anomaly_gap_share = round(
                abs(anomaly_gap) / abs(delta_gaia_excel_totale_confrontabile) * 100,
                1,
            )
        anomaly_driven_case = bool(
            capacitas_entry
            and capacitas_entry["anomalous_rows_count"] > 0
            and anomaly_gap_share >= 95.0
        )

        if ruolo_entry and capacitas_entry:
            status = "matched"
            if abs(delta_0648) >= threshold or abs(delta_0985) >= threshold:
                status = "amount_mismatch"
                mismatch_positions += 1
        elif ruolo_entry:
            status = "only_in_ruolo"
            mismatch_positions += 1
        else:
            status = "only_in_capacitas"
            mismatch_positions += 1

        if status == "matched":
            continue

        diagnosis = _classify_capacitas_mismatch(
            status=status,
            threshold=threshold,
            ruolo_0648=ruolo_0648,
            ruolo_0985=ruolo_0985,
            gaia_0648=gaia_0648,
            gaia_0985=gaia_0985,
            excel_0648=excel_0648,
            excel_0985=excel_0985,
        )

        items.append(
            {
                "tax_code": tax_code,
                "ruolo_display_name": ruolo_entry["display_name"] if ruolo_entry else None,
                "capacitas_display_name": capacitas_entry["display_name"] if capacitas_entry else None,
                "status": status,
                "diagnosis": diagnosis,
                "ruolo_0648": ruolo_0648,
                "gaia_0648": gaia_0648,
                "excel_0648": excel_0648,
                "delta_0648": delta_0648,
                "delta_gaia_excel_0648": delta_gaia_excel_0648,
                "ruolo_0985": ruolo_0985,
                "gaia_0985": gaia_0985,
                "excel_0985": excel_0985,
                "delta_0985": delta_0985,
                "delta_gaia_excel_0985": delta_gaia_excel_0985,
                "ruolo_totale_confrontabile": ruolo_totale_confrontabile,
                "gaia_totale_confrontabile": gaia_totale_confrontabile,
                "excel_totale_confrontabile": excel_totale_confrontabile,
                "delta_totale_confrontabile": delta_totale_confrontabile,
                "delta_gaia_excel_totale_confrontabile": delta_gaia_excel_totale_confrontabile,
                "anomalous_rows_count": int(capacitas_entry["anomalous_rows_count"]) if capacitas_entry else 0,
                "clean_rows_count": int(capacitas_entry["clean_rows_count"]) if capacitas_entry else 0,
                "anomaly_gap_share": anomaly_gap_share,
                "anomaly_driven_case": anomaly_driven_case,
            }
        )

    items.sort(
        key=lambda item: (
            abs(item["delta_totale_confrontabile"]),
            abs(item["delta_0648"]) + abs(item["delta_0985"]),
            item["tax_code"],
        ),
        reverse=True,
    )

    ruolo_totale_0648 = round(sum(item["amount_0648"] for item in ruolo_by_tax.values()), 2)
    ruolo_totale_0985 = round(sum(item["amount_0985"] for item in ruolo_by_tax.values()), 2)
    ruolo_totale_0668 = round(sum(item["amount_0668"] for item in ruolo_by_tax.values()), 2)
    gaia_totale_0648 = round(sum(float(item["gaia_0648"]) for item in capacitas_by_tax.values()), 2)
    gaia_totale_0985 = round(sum(float(item["gaia_0985"]) for item in capacitas_by_tax.values()), 2)
    excel_totale_0648 = round(sum(float(item["excel_0648"]) for item in capacitas_by_tax.values()), 2)
    excel_totale_0985 = round(sum(float(item["excel_0985"]) for item in capacitas_by_tax.values()), 2)
    diagnosis_ruolo_count = sum(1 for item in items if item["diagnosis"] == "problema_ruolo")
    diagnosis_gaia_count = sum(1 for item in items if item["diagnosis"] == "problema_ricalcolo_gaia")
    diagnosis_excel_count = sum(1 for item in items if item["diagnosis"] == "problema_snapshot_excel")

    return {
        "summary": {
            "anno_tributario": anno,
            "ruolo_positions": len(ruolo_by_tax),
            "capacitas_positions": len(capacitas_by_tax),
            "capacitas_active_batch_id": str(active_batch_id) if active_batch_id is not None else None,
            "matched_positions": sum(1 for tax_code in all_tax_codes if tax_code in ruolo_by_tax and tax_code in capacitas_by_tax),
            "only_in_ruolo": sum(1 for tax_code in all_tax_codes if tax_code in ruolo_by_tax and tax_code not in capacitas_by_tax),
            "only_in_capacitas": sum(1 for tax_code in all_tax_codes if tax_code in capacitas_by_tax and tax_code not in ruolo_by_tax),
            "ruolo_positions_missing_tax_code": ruolo_missing_tax,
            "capacitas_positions_missing_tax_code": capacitas_missing_tax,
            "ruolo_totale_0648": ruolo_totale_0648,
            "gaia_totale_0648": gaia_totale_0648,
            "excel_totale_0648": excel_totale_0648,
            "delta_totale_0648": round(ruolo_totale_0648 - gaia_totale_0648, 2),
            "delta_gaia_excel_totale_0648": round(gaia_totale_0648 - excel_totale_0648, 2),
            "ruolo_totale_0985": ruolo_totale_0985,
            "gaia_totale_0985": gaia_totale_0985,
            "excel_totale_0985": excel_totale_0985,
            "delta_totale_0985": round(ruolo_totale_0985 - gaia_totale_0985, 2),
            "delta_gaia_excel_totale_0985": round(gaia_totale_0985 - excel_totale_0985, 2),
            "ruolo_totale_0668": ruolo_totale_0668,
            "ruolo_totale_confrontabile": round(ruolo_totale_0648 + ruolo_totale_0985, 2),
            "gaia_totale_confrontabile": round(gaia_totale_0648 + gaia_totale_0985, 2),
            "excel_totale_confrontabile": round(excel_totale_0648 + excel_totale_0985, 2),
            "delta_totale_confrontabile": round((ruolo_totale_0648 + ruolo_totale_0985) - (gaia_totale_0648 + gaia_totale_0985), 2),
            "delta_gaia_excel_totale_confrontabile": round((gaia_totale_0648 + gaia_totale_0985) - (excel_totale_0648 + excel_totale_0985), 2),
            "mismatch_positions": mismatch_positions,
            "diagnosis_ruolo_count": diagnosis_ruolo_count,
            "diagnosis_gaia_count": diagnosis_gaia_count,
            "diagnosis_excel_count": diagnosis_excel_count,
        },
        "items": items[: max(limit, 0)],
    }


def get_capacitas_check_comuni(
    db: Session,
    *,
    anno: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    raw_ruolo_comuni = _load_ruolo_incass_by_comune(db, anno=anno)
    capacitas_comuni, active_batch_id = _load_capacitas_snapshot_by_comune(db, anno=anno)

    comuni: dict[str, dict[str, Any]] = {}

    for source_key, item in raw_ruolo_comuni.items():
        key = _normalize_capacitas_check_comune_name(source_key)
        current = comuni.setdefault(
            key,
            {
                "comune_nome": key,
                "ruolo_0648": 0.0,
                "ruolo_0985": 0.0,
                "gaia_0648": 0.0,
                "gaia_0985": 0.0,
                "excel_0648": 0.0,
                "excel_0985": 0.0,
                "source_comuni_ruolo": set(),
                "source_comuni_capacitas": set(),
            },
        )
        current["ruolo_0648"] = round(float(current["ruolo_0648"]) + float(item["ruolo_0648"]), 2)
        current["ruolo_0985"] = round(float(current["ruolo_0985"]) + float(item["ruolo_0985"]), 2)
        current["source_comuni_ruolo"].add(source_key)

    for source_key, snapshot in capacitas_comuni.items():
        key = _normalize_capacitas_check_comune_name(source_key)
        current = comuni.setdefault(
            key,
            {
                "comune_nome": key,
                "ruolo_0648": 0.0,
                "ruolo_0985": 0.0,
                "gaia_0648": 0.0,
                "gaia_0985": 0.0,
                "excel_0648": 0.0,
                "excel_0985": 0.0,
                "source_comuni_ruolo": set(),
                "source_comuni_capacitas": set(),
            },
        )
        current["gaia_0648"] = round(float(current["gaia_0648"]) + float(snapshot["gaia_0648"]), 2)
        current["gaia_0985"] = round(float(current["gaia_0985"]) + float(snapshot["gaia_0985"]), 2)
        current["excel_0648"] = round(float(current["excel_0648"]) + float(snapshot["excel_0648"]), 2)
        current["excel_0985"] = round(float(current["excel_0985"]) + float(snapshot["excel_0985"]), 2)
        current["source_comuni_capacitas"].add(source_key)

    items: list[dict[str, Any]] = []
    for item in comuni.values():
        ruolo_0648 = float(item["ruolo_0648"])
        ruolo_0985 = float(item["ruolo_0985"])
        gaia_0648 = float(item["gaia_0648"])
        gaia_0985 = float(item["gaia_0985"])
        excel_0648 = float(item["excel_0648"])
        excel_0985 = float(item["excel_0985"])
        delta_0648 = round(ruolo_0648 - gaia_0648, 2)
        delta_0985 = round(ruolo_0985 - gaia_0985, 2)
        delta_gaia_excel_0648 = round(gaia_0648 - excel_0648, 2)
        delta_gaia_excel_0985 = round(gaia_0985 - excel_0985, 2)
        ruolo_totale_confrontabile = round(ruolo_0648 + ruolo_0985, 2)
        gaia_totale_confrontabile = round(gaia_0648 + gaia_0985, 2)
        excel_totale_confrontabile = round(excel_0648 + excel_0985, 2)
        items.append(
            {
                "comune_nome": item["comune_nome"],
                "source_comuni_ruolo": sorted(item["source_comuni_ruolo"]),
                "source_comuni_capacitas": sorted(item["source_comuni_capacitas"]),
                "capacitas_active_batch_id": str(active_batch_id) if active_batch_id is not None else None,
                "ruolo_0648": ruolo_0648,
                "gaia_0648": gaia_0648,
                "excel_0648": excel_0648,
                "delta_0648": delta_0648,
                "delta_gaia_excel_0648": delta_gaia_excel_0648,
                "ruolo_0985": ruolo_0985,
                "gaia_0985": gaia_0985,
                "excel_0985": excel_0985,
                "delta_0985": delta_0985,
                "delta_gaia_excel_0985": delta_gaia_excel_0985,
                "ruolo_totale_confrontabile": ruolo_totale_confrontabile,
                "gaia_totale_confrontabile": gaia_totale_confrontabile,
                "excel_totale_confrontabile": excel_totale_confrontabile,
                "delta_totale_confrontabile": round(ruolo_totale_confrontabile - gaia_totale_confrontabile, 2),
                "delta_gaia_excel_totale_confrontabile": round(gaia_totale_confrontabile - excel_totale_confrontabile, 2),
            }
        )

    items.sort(key=lambda item: abs(item["delta_totale_confrontabile"]), reverse=True)
    return items[: max(limit, 0)]


def get_capacitas_calculation_detail(
    db: Session,
    *,
    anno: int,
    tax_code: str,
) -> dict[str, Any] | None:
    normalized_tax_code = normalize_tax_identifier(tax_code)
    if not normalized_tax_code:
        return None

    active_batch_id = active_capacitas_batch_id(db, anno)
    if active_batch_id is None:
        return None
    active_batch = db.get(CatImportBatch, active_batch_id)
    source_filename = active_batch.filename if active_batch is not None else None

    rows = db.execute(
        select(
            CatUtenzaIrrigua.id,
            CatUtenzaIrrigua.cco,
            CatUtenzaIrrigua.cod_provincia,
            CatUtenzaIrrigua.cod_comune_capacitas,
            CatUtenzaIrrigua.cod_frazione,
            CatUtenzaIrrigua.num_distretto,
            CatUtenzaIrrigua.nome_distretto_loc,
            CatUtenzaIrrigua.codice_fiscale,
            CatUtenzaIrrigua.codice_fiscale_raw,
            CatUtenzaIrrigua.denominazione,
            CatUtenzaIrrigua.nome_comune,
            CatUtenzaIrrigua.sezione_catastale,
            CatUtenzaIrrigua.foglio,
            CatUtenzaIrrigua.particella,
            CatUtenzaIrrigua.subalterno,
            CatUtenzaIrrigua.sup_catastale_mq,
            CatUtenzaIrrigua.sup_irrigabile_mq,
            CatUtenzaIrrigua.ind_spese_fisse,
            CatUtenzaIrrigua.imponibile_sf,
            CatUtenzaIrrigua.esente_0648,
            CatUtenzaIrrigua.aliquota_0648,
            CatUtenzaIrrigua.importo_0648,
            CatUtenzaIrrigua.aliquota_0985,
            CatUtenzaIrrigua.importo_0985,
            CatUtenzaIrrigua.anomalia_superficie,
            CatUtenzaIrrigua.anomalia_cf_invalido,
            CatUtenzaIrrigua.anomalia_cf_mancante,
            CatUtenzaIrrigua.anomalia_comune_invalido,
            CatUtenzaIrrigua.anomalia_particella_assente,
            CatUtenzaIrrigua.anomalia_imponibile,
            CatUtenzaIrrigua.anomalia_importi,
        ).where(
            CatUtenzaIrrigua.anno_campagna == anno,
            CatUtenzaIrrigua.import_batch_id == active_batch_id,
        ).order_by(CatUtenzaIrrigua.created_at.asc(), CatUtenzaIrrigua.id.asc())
    ).all()

    matched_rows = [
        (source_row_number, row) for source_row_number, row in enumerate(rows, start=2)
        if normalize_tax_identifier(row.codice_fiscale) == normalized_tax_code
    ]
    if not matched_rows:
        return None

    display_name = next((row.denominazione for _, row in matched_rows if row.denominazione), None)
    detail_rows: list[dict[str, Any]] = []
    comune_buckets: dict[str, dict[str, Any]] = {}
    distinct_ind_spese_fisse: set[float] = set()
    distinct_imponibile_per_mq: set[float] = set()

    total_sup_irrigabile_mq = 0.0
    total_imponibile_sf = 0.0
    gaia_total = 0.0
    excel_total = 0.0
    anomalous_rows_count = 0
    gaia_total_anomalous_rows = 0.0
    excel_total_anomalous_rows = 0.0
    gaia_total_clean_rows = 0.0
    excel_total_clean_rows = 0.0

    for source_row_number, row in matched_rows:
        sup_catastale_mq = _round_currency(float(row.sup_catastale_mq)) if row.sup_catastale_mq is not None else None
        sup_irrigabile_mq = _round_currency(float(row.sup_irrigabile_mq or 0))
        imponibile_sf = _round_currency(float(row.imponibile_sf or 0))
        ind_spese_fisse = _round_currency(float(row.ind_spese_fisse)) if row.ind_spese_fisse is not None else None
        aliquota_0648 = _round_currency(float(row.aliquota_0648)) if row.aliquota_0648 is not None else None
        aliquota_0985 = _round_currency(float(row.aliquota_0985)) if row.aliquota_0985 is not None else None
        excel_0648 = _round_currency(float(row.importo_0648 or 0))
        excel_0985 = _round_currency(float(row.importo_0985 or 0))
        gaia_0648 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0648)
        gaia_0985 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0985)
        excel_total_row = _round_currency(excel_0648 + excel_0985)
        gaia_total_row = _round_currency(gaia_0648 + gaia_0985)
        gap_excel_gaia_total = _round_currency(excel_total_row - gaia_total_row)
        imponibile_per_mq = _round_currency(imponibile_sf / sup_irrigabile_mq) if sup_irrigabile_mq > 0 else None
        has_anomaly = bool(row.anomalia_imponibile or row.anomalia_importi)
        comune_nome = row.nome_comune or "N/D"

        total_sup_irrigabile_mq = _round_currency(total_sup_irrigabile_mq + sup_irrigabile_mq)
        total_imponibile_sf = _round_currency(total_imponibile_sf + imponibile_sf)
        gaia_total = _round_currency(gaia_total + gaia_total_row)
        excel_total = _round_currency(excel_total + excel_total_row)
        if ind_spese_fisse is not None:
            distinct_ind_spese_fisse.add(ind_spese_fisse)
        if imponibile_per_mq is not None:
            distinct_imponibile_per_mq.add(imponibile_per_mq)

        if has_anomaly:
            anomalous_rows_count += 1
            gaia_total_anomalous_rows = _round_currency(gaia_total_anomalous_rows + gaia_total_row)
            excel_total_anomalous_rows = _round_currency(excel_total_anomalous_rows + excel_total_row)
        else:
            gaia_total_clean_rows = _round_currency(gaia_total_clean_rows + gaia_total_row)
            excel_total_clean_rows = _round_currency(excel_total_clean_rows + excel_total_row)

        bucket = comune_buckets.setdefault(
            comune_nome,
            {
                "comune_nome": comune_nome,
                "rows_count": 0,
                "anomalous_rows_count": 0,
                "total_sup_irrigabile_mq": 0.0,
                "total_imponibile_sf": 0.0,
                "gaia_total": 0.0,
                "excel_total": 0.0,
                "gap_excel_gaia_total": 0.0,
            },
        )
        bucket["rows_count"] += 1
        if has_anomaly:
            bucket["anomalous_rows_count"] += 1
        bucket["total_sup_irrigabile_mq"] = _round_currency(float(bucket["total_sup_irrigabile_mq"]) + sup_irrigabile_mq)
        bucket["total_imponibile_sf"] = _round_currency(float(bucket["total_imponibile_sf"]) + imponibile_sf)
        bucket["gaia_total"] = _round_currency(float(bucket["gaia_total"]) + gaia_total_row)
        bucket["excel_total"] = _round_currency(float(bucket["excel_total"]) + excel_total_row)
        bucket["gap_excel_gaia_total"] = _round_currency(float(bucket["gap_excel_gaia_total"]) + gap_excel_gaia_total)

        detail_rows.append(
            {
                "source_filename": source_filename,
                "source_row_number": source_row_number,
                "cco": row.cco,
                "cod_provincia": row.cod_provincia,
                "cod_comune_capacitas": row.cod_comune_capacitas,
                "cod_frazione": row.cod_frazione,
                "num_distretto": row.num_distretto,
                "nome_distretto_loc": row.nome_distretto_loc,
                "comune_nome": comune_nome,
                "sezione_catastale": row.sezione_catastale,
                "foglio": row.foglio,
                "particella": row.particella,
                "subalterno": row.subalterno,
                "sup_catastale_mq": sup_catastale_mq,
                "sup_irrigabile_mq": sup_irrigabile_mq,
                "ind_spese_fisse": ind_spese_fisse,
                "imponibile_sf": imponibile_sf,
                "imponibile_per_mq": imponibile_per_mq,
                "esente_0648": bool(row.esente_0648),
                "aliquota_0648": aliquota_0648,
                "aliquota_0985": aliquota_0985,
                "excel_0648": excel_0648,
                "excel_0985": excel_0985,
                "excel_total": excel_total_row,
                "gaia_0648": gaia_0648,
                "gaia_0985": gaia_0985,
                "gaia_total": gaia_total_row,
                "gap_excel_gaia_total": gap_excel_gaia_total,
                "codice_fiscale_raw": row.codice_fiscale_raw,
                "anomalia_imponibile": bool(row.anomalia_imponibile),
                "anomalia_importi": bool(row.anomalia_importi),
                "anomalia_superficie": bool(row.anomalia_superficie),
                "anomalia_cf_invalido": bool(row.anomalia_cf_invalido),
                "anomalia_cf_mancante": bool(row.anomalia_cf_mancante),
                "anomalia_comune_invalido": bool(row.anomalia_comune_invalido),
                "anomalia_particella_assente": bool(row.anomalia_particella_assente),
            }
        )

    detail_rows.sort(key=lambda item: abs(float(item["gap_excel_gaia_total"])), reverse=True)
    comuni = list(comune_buckets.values())
    comuni.sort(key=lambda item: abs(float(item["gap_excel_gaia_total"])), reverse=True)

    return {
        "summary": {
            "anno_tributario": anno,
            "tax_code": normalized_tax_code,
            "display_name": display_name,
            "active_batch_id": str(active_batch_id),
            "source_filename": source_filename,
            "rows_count": len(detail_rows),
            "anomalous_rows_count": anomalous_rows_count,
            "clean_rows_count": len(detail_rows) - anomalous_rows_count,
            "total_sup_irrigabile_mq": total_sup_irrigabile_mq,
            "total_imponibile_sf": total_imponibile_sf,
            "gaia_total": gaia_total,
            "excel_total": excel_total,
            "gap_excel_gaia_total": _round_currency(excel_total - gaia_total),
            "gaia_total_anomalous_rows": gaia_total_anomalous_rows,
            "excel_total_anomalous_rows": excel_total_anomalous_rows,
            "gaia_total_clean_rows": gaia_total_clean_rows,
            "excel_total_clean_rows": excel_total_clean_rows,
            "distinct_ind_spese_fisse": sorted(distinct_ind_spese_fisse),
            "distinct_imponibile_per_mq": sorted(distinct_imponibile_per_mq),
        },
        "comuni": comuni,
        "rows": detail_rows,
    }


def get_gaia_role_calculation(
    db: Session,
    *,
    anno: int,
    limit: int = 100,
    tax_code: str | None = None,
    anomalous_only: bool = False,
) -> dict[str, Any]:
    normalized_filter = normalize_tax_identifier(tax_code) if tax_code else None
    threshold = 0.01
    ruolo_by_tax, ruolo_missing_tax = _load_ruolo_incass_by_tax(db, anno=anno)
    active_batch_id = active_capacitas_batch_id(db, anno)
    if active_batch_id is None:
        return {
            "summary": {
                "anno_tributario": anno,
                "active_batch_id": None,
                "positions": 0,
                "ruolo_positions": len(ruolo_by_tax),
                "positions_missing_tax_code": 0,
                "ruolo_positions_missing_tax_code": ruolo_missing_tax,
                "anomalous_positions": 0,
                "anomaly_driven_positions": 0,
                "total_rows": 0,
                "anomalous_rows": 0,
                "clean_rows": 0,
                "total_sup_irrigabile_mq": 0.0,
                "total_imponibile_sf": 0.0,
                "ruolo_totale_0648": _round_currency(sum(item["amount_0648"] for item in ruolo_by_tax.values())),
                "gaia_totale_0648": 0.0,
                "ruolo_totale_0985": _round_currency(sum(item["amount_0985"] for item in ruolo_by_tax.values())),
                "gaia_totale_0985": 0.0,
                "ruolo_totale_0668": _round_currency(sum(item["amount_0668"] for item in ruolo_by_tax.values())),
                "ruolo_totale_confrontabile": _round_currency(
                    sum(item["amount_0648"] + item["amount_0985"] for item in ruolo_by_tax.values())
                ),
                "gaia_totale_confrontabile": 0.0,
                "excel_totale_0648": 0.0,
                "excel_totale_0985": 0.0,
                "excel_totale_confrontabile": 0.0,
                "delta_ruolo_gaia_totale": _round_currency(
                    sum(item["amount_0648"] + item["amount_0985"] for item in ruolo_by_tax.values())
                ),
                "gap_excel_gaia_totale": 0.0,
                "mismatch_positions": 0,
                "diagnosis_ruolo_count": 0,
                "diagnosis_gaia_count": 0,
                "diagnosis_excel_count": 0,
            },
            "items": [],
        }

    rows = db.execute(
        select(
            CatUtenzaIrrigua.codice_fiscale,
            CatUtenzaIrrigua.denominazione,
            CatUtenzaIrrigua.nome_comune,
            CatUtenzaIrrigua.sup_irrigabile_mq,
            CatUtenzaIrrigua.imponibile_sf,
            CatUtenzaIrrigua.aliquota_0648,
            CatUtenzaIrrigua.aliquota_0985,
            CatUtenzaIrrigua.importo_0648,
            CatUtenzaIrrigua.importo_0985,
            CatUtenzaIrrigua.anomalia_imponibile,
            CatUtenzaIrrigua.anomalia_importi,
        ).where(
            CatUtenzaIrrigua.anno_campagna == anno,
            CatUtenzaIrrigua.import_batch_id == active_batch_id,
        )
    ).all()

    items_by_tax: dict[str, dict[str, Any]] = {}
    missing_tax = 0
    total_rows = 0
    anomalous_rows = 0
    clean_rows = 0
    total_sup_irrigabile_mq = 0.0
    total_imponibile_sf = 0.0
    gaia_totale_0648 = 0.0
    gaia_totale_0985 = 0.0
    excel_totale_0648 = 0.0
    excel_totale_0985 = 0.0
    ruolo_totale_0648 = _round_currency(sum(item["amount_0648"] for item in ruolo_by_tax.values()))
    ruolo_totale_0985 = _round_currency(sum(item["amount_0985"] for item in ruolo_by_tax.values()))
    ruolo_totale_0668 = _round_currency(sum(item["amount_0668"] for item in ruolo_by_tax.values()))

    for row in rows:
        tax_key = normalize_tax_identifier(row.codice_fiscale)
        if not tax_key:
            missing_tax += 1
            continue
        if normalized_filter and tax_key != normalized_filter:
            continue

        current = items_by_tax.get(tax_key)
        if current is None:
            current = {
                "tax_code": tax_key,
                "display_name": row.denominazione,
                "comuni": set(),
                "rows_count": 0,
                "anomalous_rows_count": 0,
                "clean_rows_count": 0,
                "total_sup_irrigabile_mq": 0.0,
                "total_imponibile_sf": 0.0,
                "gaia_0648": 0.0,
                "gaia_0985": 0.0,
                "excel_0648": 0.0,
                "excel_0985": 0.0,
                "gaia_total_anomalous_rows": 0.0,
                "excel_total_anomalous_rows": 0.0,
                "gaia_total_clean_rows": 0.0,
                "excel_total_clean_rows": 0.0,
            }
            items_by_tax[tax_key] = current
        elif not current["display_name"] and row.denominazione:
            current["display_name"] = row.denominazione

        sup_irrigabile_mq = _round_currency(float(row.sup_irrigabile_mq or 0))
        imponibile_sf = _round_currency(float(row.imponibile_sf or 0))
        gaia_0648 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0648)
        gaia_0985 = _compute_gaia_amount(row.imponibile_sf, row.aliquota_0985)
        excel_0648 = _round_currency(float(row.importo_0648 or 0))
        excel_0985 = _round_currency(float(row.importo_0985 or 0))
        gaia_total = _round_currency(gaia_0648 + gaia_0985)
        excel_total = _round_currency(excel_0648 + excel_0985)
        has_anomaly = bool(row.anomalia_imponibile or row.anomalia_importi)

        total_rows += 1
        total_sup_irrigabile_mq = _round_currency(total_sup_irrigabile_mq + sup_irrigabile_mq)
        total_imponibile_sf = _round_currency(total_imponibile_sf + imponibile_sf)
        gaia_totale_0648 = _round_currency(gaia_totale_0648 + gaia_0648)
        gaia_totale_0985 = _round_currency(gaia_totale_0985 + gaia_0985)
        excel_totale_0648 = _round_currency(excel_totale_0648 + excel_0648)
        excel_totale_0985 = _round_currency(excel_totale_0985 + excel_0985)
        if has_anomaly:
            anomalous_rows += 1
        else:
            clean_rows += 1

        current["rows_count"] += 1
        if row.nome_comune:
            current["comuni"].add(row.nome_comune)
        if has_anomaly:
            current["anomalous_rows_count"] += 1
        else:
            current["clean_rows_count"] += 1
        current["total_sup_irrigabile_mq"] = _round_currency(current["total_sup_irrigabile_mq"] + sup_irrigabile_mq)
        current["total_imponibile_sf"] = _round_currency(current["total_imponibile_sf"] + imponibile_sf)
        current["gaia_0648"] = _round_currency(current["gaia_0648"] + gaia_0648)
        current["gaia_0985"] = _round_currency(current["gaia_0985"] + gaia_0985)
        current["excel_0648"] = _round_currency(current["excel_0648"] + excel_0648)
        current["excel_0985"] = _round_currency(current["excel_0985"] + excel_0985)
        if has_anomaly:
            current["gaia_total_anomalous_rows"] = _round_currency(current["gaia_total_anomalous_rows"] + gaia_total)
            current["excel_total_anomalous_rows"] = _round_currency(current["excel_total_anomalous_rows"] + excel_total)
        else:
            current["gaia_total_clean_rows"] = _round_currency(current["gaia_total_clean_rows"] + gaia_total)
            current["excel_total_clean_rows"] = _round_currency(current["excel_total_clean_rows"] + excel_total)

    items: list[dict[str, Any]] = []
    for item in items_by_tax.values():
        ruolo_entry = ruolo_by_tax.get(item["tax_code"])
        gaia_total = _round_currency(item["gaia_0648"] + item["gaia_0985"])
        excel_total = _round_currency(item["excel_0648"] + item["excel_0985"])
        gap_excel_gaia_total = _round_currency(excel_total - gaia_total)
        ruolo_0648 = _round_currency(float(ruolo_entry["amount_0648"])) if ruolo_entry else 0.0
        ruolo_0985 = _round_currency(float(ruolo_entry["amount_0985"])) if ruolo_entry else 0.0
        ruolo_totale_confrontabile = _round_currency(ruolo_0648 + ruolo_0985)
        delta_ruolo_gaia_totale = _round_currency(ruolo_totale_confrontabile - gaia_total)
        anomaly_gap = _round_currency(item["excel_total_anomalous_rows"] - item["gaia_total_anomalous_rows"])
        anomaly_gap_share = 0.0
        if gap_excel_gaia_total != 0:
            anomaly_gap_share = round(abs(anomaly_gap) / abs(gap_excel_gaia_total) * 100, 1)
        anomaly_driven_case = item["anomalous_rows_count"] > 0 and anomaly_gap_share >= 95.0
        if ruolo_entry and abs(delta_ruolo_gaia_totale) <= threshold and abs(gap_excel_gaia_total) <= threshold:
            status = "matched"
        elif ruolo_entry is None:
            status = "only_in_capacitas"
        elif abs(delta_ruolo_gaia_totale) <= threshold:
            status = "matched"
        else:
            status = "amount_mismatch"
        diagnosis = _classify_capacitas_mismatch(
            status=status,
            threshold=threshold,
            ruolo_0648=ruolo_0648,
            ruolo_0985=ruolo_0985,
            gaia_0648=item["gaia_0648"],
            gaia_0985=item["gaia_0985"],
            excel_0648=item["excel_0648"],
            excel_0985=item["excel_0985"],
        )

        if anomalous_only and not anomaly_driven_case:
            continue

        items.append(
            {
                "tax_code": item["tax_code"],
                "display_name": item["display_name"],
                "ruolo_display_name": ruolo_entry["display_name"] if ruolo_entry else None,
                "status": status,
                "diagnosis": diagnosis,
                "comuni_count": len(item["comuni"]),
                "rows_count": item["rows_count"],
                "anomalous_rows_count": item["anomalous_rows_count"],
                "clean_rows_count": item["clean_rows_count"],
                "total_sup_irrigabile_mq": item["total_sup_irrigabile_mq"],
                "total_imponibile_sf": item["total_imponibile_sf"],
                "ruolo_0648": ruolo_0648,
                "gaia_0648": item["gaia_0648"],
                "ruolo_0985": ruolo_0985,
                "gaia_0985": item["gaia_0985"],
                "ruolo_totale_confrontabile": ruolo_totale_confrontabile,
                "gaia_total": gaia_total,
                "excel_0648": item["excel_0648"],
                "excel_0985": item["excel_0985"],
                "excel_total": excel_total,
                "delta_ruolo_gaia_totale": delta_ruolo_gaia_totale,
                "gap_excel_gaia_total": gap_excel_gaia_total,
                "anomaly_gap_share": anomaly_gap_share,
                "anomaly_driven_case": anomaly_driven_case,
            }
        )

    items.sort(key=lambda item: abs(item["gap_excel_gaia_total"]), reverse=True)

    anomalous_positions = sum(1 for item in items_by_tax.values() if item["anomalous_rows_count"] > 0)
    anomaly_driven_positions = sum(
        1
        for item in items
        if item["anomaly_driven_case"]
    )
    mismatch_positions = sum(1 for item in items if item["status"] != "matched")
    diagnosis_ruolo_count = sum(1 for item in items if item["diagnosis"] == "problema_ruolo")
    diagnosis_gaia_count = sum(1 for item in items if item["diagnosis"] == "problema_ricalcolo_gaia")
    diagnosis_excel_count = sum(1 for item in items if item["diagnosis"] == "problema_snapshot_excel")

    return {
        "summary": {
            "anno_tributario": anno,
            "active_batch_id": str(active_batch_id),
            "positions": len(items_by_tax),
            "ruolo_positions": len(ruolo_by_tax),
            "positions_missing_tax_code": missing_tax,
            "ruolo_positions_missing_tax_code": ruolo_missing_tax,
            "anomalous_positions": anomalous_positions,
            "anomaly_driven_positions": anomaly_driven_positions,
            "total_rows": total_rows,
            "anomalous_rows": anomalous_rows,
            "clean_rows": clean_rows,
            "total_sup_irrigabile_mq": total_sup_irrigabile_mq,
            "total_imponibile_sf": total_imponibile_sf,
            "ruolo_totale_0648": ruolo_totale_0648,
            "gaia_totale_0648": gaia_totale_0648,
            "ruolo_totale_0985": ruolo_totale_0985,
            "gaia_totale_0985": gaia_totale_0985,
            "ruolo_totale_0668": ruolo_totale_0668,
            "ruolo_totale_confrontabile": _round_currency(ruolo_totale_0648 + ruolo_totale_0985),
            "gaia_totale_confrontabile": _round_currency(gaia_totale_0648 + gaia_totale_0985),
            "excel_totale_0648": excel_totale_0648,
            "excel_totale_0985": excel_totale_0985,
            "excel_totale_confrontabile": _round_currency(excel_totale_0648 + excel_totale_0985),
            "delta_ruolo_gaia_totale": _round_currency(
                (ruolo_totale_0648 + ruolo_totale_0985) - (gaia_totale_0648 + gaia_totale_0985)
            ),
            "gap_excel_gaia_totale": _round_currency(
                (excel_totale_0648 + excel_totale_0985) - (gaia_totale_0648 + gaia_totale_0985)
            ),
            "mismatch_positions": mismatch_positions,
            "diagnosis_ruolo_count": diagnosis_ruolo_count,
            "diagnosis_gaia_count": diagnosis_gaia_count,
            "diagnosis_excel_count": diagnosis_excel_count,
        },
        "items": items[: max(limit, 0)],
    }


# ---------------------------------------------------------------------------
# Catasto Parcels
# ---------------------------------------------------------------------------

def list_catasto_parcels(
    db: Session,
    comune_codice: str | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CatastoParcel], int]:
    q = select(CatastoParcel)
    if comune_codice:
        q = q.where(CatastoParcel.comune_codice == comune_codice)
    if foglio:
        q = q.where(CatastoParcel.foglio == foglio)
    if particella:
        q = q.where(CatastoParcel.particella == particella)
    if active_only:
        q = q.where(CatastoParcel.valid_to.is_(None))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(CatastoParcel.comune_nome, CatastoParcel.foglio, CatastoParcel.particella, CatastoParcel.valid_from)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total or 0


def get_catasto_parcel_history(
    db: Session,
    comune_codice: str,
    foglio: str,
    particella: str,
    subalterno: str | None = None,
) -> list[CatastoParcel]:
    q = select(CatastoParcel).where(
        CatastoParcel.comune_codice == comune_codice,
        CatastoParcel.foglio == foglio,
        CatastoParcel.particella == particella,
    )
    if subalterno is not None:
        q = q.where(CatastoParcel.subalterno == subalterno)
    return list(db.scalars(q.order_by(CatastoParcel.valid_from)).all())


# ---------------------------------------------------------------------------
# Utility: display_name soggetto
# ---------------------------------------------------------------------------

def _get_subject_display_name(db: Session, subject_id: uuid.UUID | None) -> str | None:
    if subject_id is None:
        return None
    person = db.scalar(
        select(AnagraficaPerson).where(AnagraficaPerson.subject_id == subject_id)
    )
    if person is not None:
        return f"{person.cognome} {person.nome}".strip()
    company = db.scalar(
        select(AnagraficaCompany).where(AnagraficaCompany.subject_id == subject_id)
    )
    if company is not None:
        return company.ragione_sociale
    return None
