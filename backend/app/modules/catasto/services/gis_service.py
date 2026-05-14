from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from shapely.geometry import shape
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.orm import Session

from app.modules.catasto.schemas.gis_schemas import (
    DistrettoAggr,
    FoglioAggr,
    GisExportFormat,
    GisFilters,
    GisResolveItemResult,
    GisResolveRefsRequest,
    GisResolveRefsResponse,
    GisSavedSelectionCreate,
    GisSavedSelectionDetail,
    GisSavedSelectionSummary,
    GisSavedSelectionUpdate,
    GisSelectResult,
    ParticellaGisSummary,
    ParticellaPopupAnomalia,
    ParticellaPopupData,
    ParticellaPopupRuoloItem,
    ParticellaPopupRuoloSummary,
    ParticellaPopupSwappedCapacitas,
    ParticellaPopupTitolare,
)
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatComune,
    CatGisSavedSelection,
    CatGisSavedSelectionItem,
    CatParticella,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


SARDINIA_BBOX = {
    "min_lon": 7.8,
    "max_lon": 10.0,
    "min_lat": 38.5,
    "max_lat": 41.5,
}
PREVIEW_LIMIT = 200
MAX_EXPORT_IDS = 10000
ZERO_SHARE_TITLE_RE = re.compile(r"\b0\s*/\s*0\b")
SWAPPED_ARBOREA_TERRALBA_REASON = "swapped_arborea_terralba"


def _norm_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _norm_catasto_num(value: Any) -> str | None:
    """Normalize a catasto foglio/particella: strip whitespace and leading zeros for numeric values."""
    s = _norm_str(value)
    if s is None:
        return None
    try:
        return str(int(s))
    except ValueError:
        return s


def _looks_like_int(value: str) -> bool:
    try:
        int(value)
        return True
    except Exception:
        return False


def _looks_like_codice_catastale(value: str) -> bool:
    normalized = value.strip().upper()
    return len(normalized) == 4 and normalized[0].isalpha() and normalized[1:].isdigit()


def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} non valido") from exc


def _validate_geometry_bbox(geometry: dict[str, Any]) -> None:
    try:
        bounds = shape(geometry).bounds
    except (AttributeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Geometria GeoJSON non valida: {exc}") from exc

    if (
        bounds[0] < SARDINIA_BBOX["min_lon"]
        or bounds[2] > SARDINIA_BBOX["max_lon"]
        or bounds[1] < SARDINIA_BBOX["min_lat"]
        or bounds[3] > SARDINIA_BBOX["max_lat"]
    ):
        raise HTTPException(
            status_code=400,
            detail="La geometria di selezione è fuori dall'area di interesse (Sardegna).",
        )


def _build_where_clause(filters: GisFilters | None, geojson_str: str) -> tuple[str, dict[str, Any]]:
    conditions = [
        "p.is_current = TRUE",
        "ST_Intersects(p.geometry, ST_SetSRID(ST_GeomFromGeoJSON(:geojson_str), 4326))",
    ]
    params: dict[str, Any] = {"geojson_str": geojson_str}

    if filters:
        if filters.comune is not None:
            conditions.append("p.cod_comune_capacitas = :comune")
            params["comune"] = filters.comune
        if filters.codice_catastale:
            conditions.append("p.codice_catastale = :codice_catastale")
            params["codice_catastale"] = filters.codice_catastale.strip().upper()
        if filters.foglio:
            conditions.append("p.foglio = :foglio")
            params["foglio"] = filters.foglio
        if filters.num_distretto:
            conditions.append("p.num_distretto = :num_distretto")
            params["num_distretto"] = filters.num_distretto
        if filters.solo_anomalie:
            conditions.append(
                """
                EXISTS(
                    SELECT 1
                    FROM cat_anomalie a
                    WHERE a.particella_id = p.id
                      AND a.status = 'aperta'
                )
                """
            )

    return " AND ".join(conditions), params


def select_by_geometry(db: Session, geometry: dict[str, Any], filters: GisFilters | None) -> GisSelectResult:
    _validate_geometry_bbox(geometry)
    geojson_str = json.dumps(geometry)
    where_clause, params = _build_where_clause(filters, geojson_str)
    params["preview_limit"] = PREVIEW_LIMIT

    db.execute(text("SET LOCAL statement_timeout = '10000'"))
    sql = text(
        f"""
        WITH selected AS (
            SELECT
                p.id::text,
                p.cfm,
                p.cod_comune_capacitas,
                p.cod_comune_capacitas AS cod_comune_istat,
                p.codice_catastale,
                p.nome_comune,
                p.foglio,
                p.particella,
                p.subalterno,
                p.superficie_mq,
                p.superficie_grafica_mq,
                p.num_distretto,
                p.nome_distretto,
                COALESCE(ST_Area(ST_Transform(p.geometry, 32632)) / 10000.0, 0) AS sup_ha,
                EXISTS(
                    SELECT 1
                    FROM cat_anomalie a
                    WHERE a.particella_id = p.id
                      AND a.status = 'aperta'
                ) AS ha_anomalie
            FROM cat_particelle p
            WHERE {where_clause}
        ),
        totals AS (
            SELECT
                COUNT(*) AS n_totale,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha_totale
            FROM selected
        ),
        per_foglio AS (
            SELECT
                foglio,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE foglio IS NOT NULL
            GROUP BY foglio
            ORDER BY foglio
        ),
        per_distretto AS (
            SELECT
                num_distretto,
                MAX(nome_distretto) AS nome_distretto,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE num_distretto IS NOT NULL
            GROUP BY num_distretto
            ORDER BY num_distretto
        ),
        preview AS (
            SELECT *
            FROM selected
            ORDER BY codice_catastale, foglio, particella, subalterno
            LIMIT :preview_limit
        )
        SELECT
            t.n_totale,
            t.superficie_ha_totale,
            (SELECT json_agg(row_to_json(f)) FROM per_foglio f) AS per_foglio,
            (SELECT json_agg(row_to_json(d)) FROM per_distretto d) AS per_distretto,
            (SELECT json_agg(row_to_json(pr)) FROM preview pr) AS particelle_preview,
            t.n_totale > :preview_limit AS truncated
        FROM totals t
        """
    )

    row = db.execute(sql, params).mappings().first()
    if row is None:
        return GisSelectResult(n_particelle=0, superficie_ha=0.0)

    return GisSelectResult(
        n_particelle=int(row["n_totale"] or 0),
        superficie_ha=round(float(row["superficie_ha_totale"] or 0), 2),
        per_foglio=_parse_foglio_aggr(row["per_foglio"]),
        per_distretto=_parse_distretto_aggr(row["per_distretto"]),
        particelle=_parse_preview(row["particelle_preview"]),
        truncated=bool(row["truncated"]),
    )


def export_particelle(db: Session, id_list: list[str], fmt: GisExportFormat) -> StreamingResponse:
    if not id_list:
        raise HTTPException(status_code=400, detail="Lista ID vuota")
    if len(id_list) > MAX_EXPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Massimo {MAX_EXPORT_IDS} particelle per export")

    if fmt == GisExportFormat.geojson:
        return _export_geojson(db, id_list)
    return _export_csv(db, id_list)


def _to_float(value: Decimal | float | int | None, digits: int | None = None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return round(number, digits) if digits is not None else number


def _is_visible_owner_title(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    if not normalized:
        return True
    return not bool(ZERO_SHARE_TITLE_RE.search(normalized))


def _load_popup_titolare(db: Session, particella_uuid: uuid.UUID) -> ParticellaPopupTitolare | None:
    utenze = (
        db.execute(
            select(CatUtenzaIrrigua)
            .where(CatUtenzaIrrigua.particella_id == particella_uuid)
            .order_by(desc(CatUtenzaIrrigua.anno_campagna), desc(CatUtenzaIrrigua.created_at))
            .limit(25)
        )
        .scalars()
        .all()
    )
    if not utenze:
        return None

    utenza_ids = [utenza.id for utenza in utenze]
    intestatari = (
        db.execute(
            select(CatUtenzaIntestatario)
            .where(CatUtenzaIntestatario.utenza_id.in_(utenza_ids))
            .order_by(
                desc(CatUtenzaIntestatario.anno_riferimento),
                desc(CatUtenzaIntestatario.data_agg),
                desc(CatUtenzaIntestatario.collected_at),
            )
        )
        .scalars()
        .all()
    )
    for intestatario in intestatari:
        if not _is_visible_owner_title(intestatario.titoli):
            continue
        if not (intestatario.denominazione or intestatario.codice_fiscale or intestatario.partita_iva):
            continue
        return ParticellaPopupTitolare(
            codice_fiscale=intestatario.codice_fiscale,
            partita_iva=intestatario.partita_iva,
            denominazione=intestatario.denominazione,
            titoli=intestatario.titoli,
            source="intestatario",
        )

    latest_utenza = utenze[0]
    if latest_utenza.denominazione or latest_utenza.codice_fiscale:
        return ParticellaPopupTitolare(
            codice_fiscale=latest_utenza.codice_fiscale,
            partita_iva=None,
            denominazione=latest_utenza.denominazione,
            titoli=None,
            source="utenza",
        )
    return None


def _ruolo_parcel_match_condition(particella: CatParticella):
    subalterno = _norm_str(particella.subalterno)
    legacy_conditions = [
        CatastoParcel.comune_codice == particella.codice_catastale,
        CatastoParcel.foglio == particella.foglio,
        CatastoParcel.particella == particella.particella,
    ]
    if subalterno:
        legacy_conditions.append(func.coalesce(CatastoParcel.subalterno, "") == subalterno)
    return (RuoloParticella.cat_particella_id == particella.id) | and_(*legacy_conditions)


def _load_particella_ruolo_summary(db: Session, particella: CatParticella) -> ParticellaPopupRuoloSummary | None:
    requested_year = datetime.now().year
    match_condition = _ruolo_parcel_match_condition(particella)
    selected_year = db.scalar(
        select(func.max(RuoloParticella.anno_tributario))
        .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
        .where(match_condition, RuoloParticella.anno_tributario <= requested_year)
    )
    if selected_year is None:
        return None

    rows = db.execute(
        select(
            RuoloParticella,
            RuoloPartita.codice_partita,
            RuoloAvviso.codice_cnc,
        )
        .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(match_condition, RuoloParticella.anno_tributario == selected_year)
        .order_by(
            desc(RuoloParticella.anno_tributario),
            RuoloParticella.subalterno,
            RuoloParticella.coltura,
            RuoloPartita.codice_partita,
        )
    ).all()
    if not rows:
        return None

    items: list[ParticellaPopupRuoloItem] = []
    subalterni: set[str] = set()
    anno_latest = 0
    total_sup_catastale = 0.0
    total_sup_irrigata = 0.0
    total_importo_manut = 0.0
    total_importo_irrig = 0.0
    total_importo_ist = 0.0
    total_importo = 0.0
    has_sup_catastale = False
    has_sup_irrigata = False
    has_importo_manut = False
    has_importo_irrig = False
    has_importo_ist = False
    has_importo = False

    for ruolo_particella, codice_partita, codice_cnc in rows:
        anno_latest = max(anno_latest, int(ruolo_particella.anno_tributario))
        if ruolo_particella.subalterno:
            subalterni.add(ruolo_particella.subalterno)

        sup_catastale_ha = _to_float(ruolo_particella.sup_catastale_ha, 4)
        sup_irrigata_ha = _to_float(ruolo_particella.sup_irrigata_ha, 4)
        importo_manut = _to_float(ruolo_particella.importo_manut, 2)
        importo_irrig = _to_float(ruolo_particella.importo_irrig, 2)
        importo_ist = _to_float(ruolo_particella.importo_ist, 2)
        importo_totale_raw = None
        if importo_manut is not None or importo_irrig is not None or importo_ist is not None:
            importo_totale_raw = (importo_manut or 0) + (importo_irrig or 0) + (importo_ist or 0)
        importo_totale = _to_float(importo_totale_raw, 2)

        if sup_catastale_ha is not None:
            has_sup_catastale = True
            total_sup_catastale += sup_catastale_ha
        if sup_irrigata_ha is not None:
            has_sup_irrigata = True
            total_sup_irrigata += sup_irrigata_ha
        if importo_manut is not None:
            has_importo_manut = True
            total_importo_manut += importo_manut
        if importo_irrig is not None:
            has_importo_irrig = True
            total_importo_irrig += importo_irrig
        if importo_ist is not None:
            has_importo_ist = True
            total_importo_ist += importo_ist
        if importo_totale is not None:
            has_importo = True
            total_importo += importo_totale

        items.append(
            ParticellaPopupRuoloItem(
                anno_tributario=int(ruolo_particella.anno_tributario),
                domanda_irrigua=ruolo_particella.domanda_irrigua,
                subalterno=ruolo_particella.subalterno,
                coltura=ruolo_particella.coltura,
                sup_catastale_ha=sup_catastale_ha,
                sup_irrigata_ha=sup_irrigata_ha,
                importo_manut_euro=importo_manut,
                importo_irrig_euro=importo_irrig,
                importo_ist_euro=importo_ist,
                importo_totale_euro=importo_totale,
                codice_partita=codice_partita,
                codice_cnc=codice_cnc,
            )
        )

    return ParticellaPopupRuoloSummary(
        anno_tributario_latest=anno_latest,
        anno_tributario_richiesto=requested_year,
        n_righe=len(items),
        n_subalterni=len(subalterni),
        sup_catastale_ha_totale=round(total_sup_catastale, 4) if has_sup_catastale else None,
        sup_irrigata_ha_totale=round(total_sup_irrigata, 4) if has_sup_irrigata else None,
        importo_manut_euro_totale=round(total_importo_manut, 2) if has_importo_manut else None,
        importo_irrig_euro_totale=round(total_importo_irrig, 2) if has_importo_irrig else None,
        importo_ist_euro_totale=round(total_importo_ist, 2) if has_importo_ist else None,
        importo_totale_euro=round(total_importo, 2) if has_importo else None,
        items=items,
    )


def _load_popup_swapped_capacitas(db: Session, particella_uuid: uuid.UUID) -> ParticellaPopupSwappedCapacitas | None:
    base_filter = (
        RuoloParticella.cat_particella_id == particella_uuid,
        RuoloParticella.cat_particella_match_reason == SWAPPED_ARBOREA_TERRALBA_REASON,
    )
    n_righe = int(db.scalar(select(func.count(RuoloParticella.id)).where(*base_filter)) or 0)
    if n_righe == 0:
        return None

    row = (
        db.execute(
            select(
                CatastoParcel.comune_codice.label("source_codice_catastale"),
                CatastoParcel.comune_nome.label("source_comune_nome"),
                CatastoParcel.foglio.label("source_foglio"),
                CatastoParcel.particella.label("source_particella"),
                CatastoParcel.subalterno.label("source_subalterno"),
                RuoloParticella.anno_tributario.label("anno_tributario_latest"),
                RuoloParticella.cat_particella_match_confidence.label("match_confidence"),
                RuoloParticella.cat_particella_match_reason.label("match_reason"),
            )
            .join(CatastoParcel, CatastoParcel.id == RuoloParticella.catasto_parcel_id)
            .where(*base_filter)
            .order_by(desc(RuoloParticella.anno_tributario), CatastoParcel.subalterno.nullsfirst())
            .limit(1)
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return ParticellaPopupSwappedCapacitas(
        source_codice_catastale=row["source_codice_catastale"],
        source_comune_nome=row["source_comune_nome"],
        source_foglio=row["source_foglio"],
        source_particella=row["source_particella"],
        source_subalterno=row["source_subalterno"],
        anno_tributario_latest=row["anno_tributario_latest"],
        match_confidence=row["match_confidence"],
        match_reason=row["match_reason"],
        n_righe_ruolo=n_righe,
    )


def _particella_anomalie_condition(particella_uuid: uuid.UUID):
    return or_(
        CatAnomalia.particella_id == particella_uuid,
        CatUtenzaIrrigua.particella_id == particella_uuid,
    )


def _load_popup_anomalie_aperte(db: Session, particella_uuid: uuid.UUID) -> list[ParticellaPopupAnomalia]:
    rows = (
        db.execute(
            select(CatAnomalia)
            .outerjoin(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
            .where(
                _particella_anomalie_condition(particella_uuid),
                CatAnomalia.status == "aperta",
            )
            .order_by(desc(CatAnomalia.created_at))
            .limit(6)
        )
        .scalars()
        .all()
    )
    return [
        ParticellaPopupAnomalia(
            id=str(row.id),
            anno_campagna=row.anno_campagna,
            tipo=row.tipo,
            severita=row.severita,
            descrizione=row.descrizione,
            dati_json=row.dati_json,
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_popup_data(db: Session, particella_id: str) -> ParticellaPopupData:
    particella_uuid = _parse_uuid(particella_id, field_name="particella_id")
    particella = db.get(CatParticella, particella_uuid)
    if particella is None or not particella.is_current:
        raise HTTPException(status_code=404, detail="Particella non trovata")
    if (
        particella.suppressed
        or particella.cod_comune_capacitas <= 0
        or _norm_str(particella.codice_catastale) is None
        or _norm_str(particella.foglio) is None
        or _norm_str(particella.particella) is None
    ):
        raise HTTPException(status_code=404, detail="Particella GIS senza chiave catastale completa")

    n_anomalie_aperte = db.scalar(
        select(func.count(CatAnomalia.id))
        .outerjoin(CatUtenzaIrrigua, CatUtenzaIrrigua.id == CatAnomalia.utenza_id)
        .where(
            _particella_anomalie_condition(particella_uuid),
            CatAnomalia.status == "aperta",
        )
    )
    anomalie_aperte = _load_popup_anomalie_aperte(db, particella_uuid)
    ruolo_summary = _load_particella_ruolo_summary(db, particella)
    titolare = _load_popup_titolare(db, particella_uuid)
    swapped_capacitas = _load_popup_swapped_capacitas(db, particella_uuid)
    return ParticellaPopupData(
        id=str(particella.id),
        cfm=particella.cfm,
        cod_comune_capacitas=particella.cod_comune_capacitas,
        cod_comune_istat=particella.cod_comune_capacitas,
        codice_catastale=particella.codice_catastale,
        nome_comune=particella.nome_comune,
        foglio=particella.foglio,
        particella=particella.particella,
        subalterno=particella.subalterno,
        superficie_mq=float(particella.superficie_mq) if particella.superficie_mq is not None else None,
        superficie_grafica_mq=float(particella.superficie_grafica_mq) if particella.superficie_grafica_mq is not None else None,
        num_distretto=particella.num_distretto,
        nome_distretto=particella.nome_distretto,
        n_anomalie_aperte=int(n_anomalie_aperte or 0),
        titolare=titolare,
        ha_ruolo=ruolo_summary is not None,
        ruolo_summary=ruolo_summary,
        swapped_capacitas=swapped_capacitas,
        anomalie_aperte=anomalie_aperte,
    )


def list_saved_selections(db: Session, user_id: int) -> list[GisSavedSelectionSummary]:
    rows = (
        db.query(CatGisSavedSelection)
        .filter(CatGisSavedSelection.created_by == user_id)
        .order_by(CatGisSavedSelection.updated_at.desc(), CatGisSavedSelection.created_at.desc())
        .all()
    )
    return [_serialize_saved_selection(row) for row in rows]


def create_saved_selection(
    db: Session,
    payload: GisSavedSelectionCreate,
    user_id: int,
) -> GisSavedSelectionDetail:
    deduped_items: list[tuple[uuid.UUID, int | None, dict[str, Any] | None]] = []
    seen: set[uuid.UUID] = set()
    for item in payload.items:
        particella_id = _parse_uuid(item.particella_id, "particella_id")
        if particella_id in seen:
            continue
        seen.add(particella_id)
        deduped_items.append((particella_id, item.source_row_index, item.source_ref))

    if not deduped_items:
        raise HTTPException(status_code=400, detail="La selezione non contiene particelle valide")

    existing_ids = {
        row[0]
        for row in db.query(CatParticella.id)
        .filter(CatParticella.id.in_([item[0] for item in deduped_items]), CatParticella.is_current.is_(True))
        .all()
    }
    if not existing_ids:
        raise HTTPException(status_code=400, detail="Nessuna particella corrente trovata per la selezione")

    selection = CatGisSavedSelection(
        name=payload.name.strip(),
        color=payload.color,
        source_filename=payload.source_filename,
        n_particelle=len(existing_ids),
        n_with_geometry=_count_particelle_with_geometry(db, [str(item_id) for item_id in existing_ids]),
        import_summary=payload.import_summary,
        created_by=user_id,
    )
    db.add(selection)
    db.flush()

    position = 0
    for particella_id, source_row_index, source_ref in deduped_items:
        if particella_id not in existing_ids:
            continue
        selection.items.append(
            CatGisSavedSelectionItem(
                particella_id=particella_id,
                position=position,
                source_row_index=source_row_index,
                source_ref=source_ref,
            )
        )
        position += 1

    db.commit()
    db.refresh(selection)
    return get_saved_selection(db, str(selection.id), user_id)


def get_saved_selection(db: Session, selection_id: str, user_id: int) -> GisSavedSelectionDetail:
    selection = _get_user_saved_selection(db, selection_id, user_id)
    id_list = [str(item.particella_id) for item in selection.items]
    geojson = _build_particelle_feature_collection(db, id_list) if id_list else None
    summary = _serialize_saved_selection(selection)
    return GisSavedSelectionDetail(**summary.model_dump(), geojson=geojson)


def update_saved_selection(
    db: Session,
    selection_id: str,
    payload: GisSavedSelectionUpdate,
    user_id: int,
) -> GisSavedSelectionSummary:
    selection = _get_user_saved_selection(db, selection_id, user_id)
    if payload.name is not None:
        selection.name = payload.name.strip()
    if payload.color is not None:
        selection.color = payload.color
    db.commit()
    db.refresh(selection)
    return _serialize_saved_selection(selection)


def delete_saved_selection(db: Session, selection_id: str, user_id: int) -> None:
    selection = _get_user_saved_selection(db, selection_id, user_id)
    db.delete(selection)
    db.commit()


def _get_user_saved_selection(db: Session, selection_id: str, user_id: int) -> CatGisSavedSelection:
    selection_uuid = _parse_uuid(selection_id, "selection_id")
    selection = (
        db.query(CatGisSavedSelection)
        .filter(CatGisSavedSelection.id == selection_uuid, CatGisSavedSelection.created_by == user_id)
        .first()
    )
    if selection is None:
        raise HTTPException(status_code=404, detail="Selezione GIS non trovata")
    return selection


def _serialize_saved_selection(selection: CatGisSavedSelection) -> GisSavedSelectionSummary:
    return GisSavedSelectionSummary(
        id=str(selection.id),
        name=selection.name,
        color=selection.color,
        source_filename=selection.source_filename,
        n_particelle=selection.n_particelle,
        n_with_geometry=selection.n_with_geometry,
        import_summary=selection.import_summary,
        created_at=selection.created_at,
        updated_at=selection.updated_at,
    )


def _count_particelle_with_geometry(db: Session, id_list: list[str]) -> int:
    if not id_list:
        return 0
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS n
            FROM cat_particelle
            WHERE id::text = ANY(:ids)
              AND is_current = TRUE
              AND geometry IS NOT NULL
            """
        ),
        {"ids": id_list},
    ).mappings().first()
    return int(row["n"] or 0) if row else 0


def _build_particelle_feature_collection(db: Session, id_list: list[str]) -> dict[str, Any]:
    sql = text(
        """
        SELECT
            id::text,
            cfm,
            cod_comune_capacitas,
            cod_comune_capacitas AS cod_comune_istat,
            codice_catastale,
            nome_comune,
            foglio,
            particella,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto,
            ST_AsGeoJSON(geometry)::json AS geometry_json
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY array_position(:ids, id::text)
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()
    features = []
    for row in rows:
        properties = dict(row)
        geometry = properties.pop("geometry_json")
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    return {"type": "FeatureCollection", "features": features}


def _export_geojson(db: Session, id_list: list[str]) -> StreamingResponse:
    sql = text(
        """
        SELECT
            id::text,
            cfm,
            cod_comune_capacitas,
            cod_comune_capacitas AS cod_comune_istat,
            codice_catastale,
            nome_comune,
            foglio,
            particella,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto,
            ST_AsGeoJSON(geometry)::json AS geometry_json
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY codice_catastale, foglio, particella, subalterno
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()
    features = []
    for row in rows:
        properties = dict(row)
        geometry = properties.pop("geometry_json")
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})

    content = json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.geojson"},
    )


def _export_csv(db: Session, id_list: list[str]) -> StreamingResponse:
    sql = text(
        """
        SELECT
            id::text,
            cfm,
            cod_comune_capacitas,
            codice_catastale,
            nome_comune,
            foglio,
            particella,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY codice_catastale, foglio, particella, subalterno
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "cfm",
            "cod_comune_capacitas",
            "codice_catastale",
            "nome_comune",
            "foglio",
            "particella",
            "subalterno",
            "superficie_mq",
            "superficie_grafica_mq",
            "num_distretto",
            "nome_distretto",
        ]
    )
    for row in rows:
        writer.writerow([row[column] for column in row.keys()])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.csv"},
    )


def _parse_foglio_aggr(data: list[dict[str, Any]] | None) -> list[FoglioAggr]:
    if not data:
        return []
    return [
        FoglioAggr(
            foglio=str(row["foglio"]),
            n_particelle=int(row["n_particelle"]),
            superficie_ha=round(float(row["superficie_ha"] or 0), 2),
        )
        for row in data
    ]


def _parse_distretto_aggr(data: list[dict[str, Any]] | None) -> list[DistrettoAggr]:
    if not data:
        return []
    return [
        DistrettoAggr(
            num_distretto=str(row["num_distretto"]),
            nome_distretto=row.get("nome_distretto"),
            n_particelle=int(row["n_particelle"]),
            superficie_ha=round(float(row["superficie_ha"] or 0), 2),
        )
        for row in data
    ]


def _parse_preview(data: list[dict[str, Any]] | None) -> list[ParticellaGisSummary]:
    if not data:
        return []
    return [ParticellaGisSummary(**row) for row in data]


def resolve_particelle_refs(db: Session, body: GisResolveRefsRequest) -> GisResolveRefsResponse:
    items = body.items[: body.limit]
    results: list[GisResolveItemResult] = []
    found_ids: list[str] = []

    for idx, row in enumerate(items):
        comune_norm = _norm_str(row.comune)
        sezione_norm = _norm_str(row.sezione)
        foglio_norm = _norm_catasto_num(row.foglio)
        particella_norm = _norm_catasto_num(row.particella)
        sub_norm = _norm_catasto_num(row.sub)

        if not comune_norm or not foglio_norm or not particella_norm:
            results.append(
                GisResolveItemResult(
                    row_index=row.row_index if row.row_index is not None else idx,
                    comune_input=row.comune,
                    sezione_input=row.sezione,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    sub_input=row.sub,
                    esito="INVALID_ROW",
                    message="Campi obbligatori mancanti (comune/foglio/particella).",
                )
            )
            continue

        query = (
            db.query(CatParticella)
            .outerjoin(CatComune, CatComune.id == CatParticella.comune_id)
            .filter(
                CatParticella.is_current.is_(True),
                CatParticella.foglio == foglio_norm,
                CatParticella.particella == particella_norm,
            )
            .order_by(CatParticella.cod_comune_capacitas, CatParticella.foglio, CatParticella.particella)
        )

        if sezione_norm:
            query = query.filter(CatParticella.sezione_catastale == sezione_norm)
        if sub_norm:
            query = query.filter(CatParticella.subalterno == sub_norm)

        if _looks_like_int(comune_norm):
            query = query.filter(CatParticella.cod_comune_capacitas == int(comune_norm))
        elif _looks_like_codice_catastale(comune_norm):
            codice_catastale_norm = comune_norm.strip().upper()
            query = query.filter(
                func.upper(func.coalesce(CatParticella.codice_catastale, CatComune.codice_catastale, ""))
                == codice_catastale_norm
            )
        else:
            query = query.filter(
                func.lower(func.coalesce(CatParticella.nome_comune, CatComune.nome_comune, "")) == comune_norm.lower()
            )

        matches = query.limit(50).all()
        if len(matches) == 0:
            results.append(
                GisResolveItemResult(
                    row_index=row.row_index if row.row_index is not None else idx,
                    comune_input=row.comune,
                    sezione_input=row.sezione,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    sub_input=row.sub,
                    esito="NOT_FOUND",
                    message="Nessuna particella trovata.",
                )
            )
            continue

        if len(matches) > 1:
            results.append(
                GisResolveItemResult(
                    row_index=row.row_index if row.row_index is not None else idx,
                    comune_input=row.comune,
                    sezione_input=row.sezione,
                    foglio_input=row.foglio,
                    particella_input=row.particella,
                    sub_input=row.sub,
                    esito="MULTIPLE_MATCHES",
                    message=f"Trovate {len(matches)} particelle. Specifica meglio comune/sezione/sub.",
                )
            )
            continue

        pid = str(matches[0].id)
        found_ids.append(pid)
        results.append(
            GisResolveItemResult(
                row_index=row.row_index if row.row_index is not None else idx,
                comune_input=row.comune,
                sezione_input=row.sezione,
                foglio_input=row.foglio,
                particella_input=row.particella,
                sub_input=row.sub,
                esito="FOUND",
                message="OK",
                particella_id=pid,
            )
        )

    geojson: dict[str, Any] | None = None
    if body.include_geometry and found_ids:
        db.execute(text("SET LOCAL statement_timeout = '15000'"))
        sql = text(
            """
            SELECT
                id::text,
                cfm,
                cod_comune_capacitas,
                codice_catastale,
                nome_comune,
                sezione_catastale,
                foglio,
                particella,
                subalterno,
                num_distretto,
                nome_distretto,
                ST_AsGeoJSON(geometry)::json AS geometry_json,
                ST_Extent(geometry) OVER () AS extent_wkb
            FROM cat_particelle
            WHERE id::text = ANY(:ids)
              AND is_current = TRUE
            ORDER BY codice_catastale, foglio, particella, subalterno
            """
        )
        rows = db.execute(sql, {"ids": list(dict.fromkeys(found_ids))}).mappings().all()
        features: list[dict[str, Any]] = []
        for r in rows:
            props = dict(r)
            geometry = props.pop("geometry_json")
            props.pop("extent_wkb", None)
            features.append({"type": "Feature", "geometry": geometry, "properties": props})
        geojson = {"type": "FeatureCollection", "features": features}

    counts = {
        "FOUND": 0,
        "NOT_FOUND": 0,
        "MULTIPLE_MATCHES": 0,
        "INVALID_ROW": 0,
    }
    for r in results:
        counts[r.esito] = counts.get(r.esito, 0) + 1

    return GisResolveRefsResponse(
        processed=len(items),
        found=counts.get("FOUND", 0),
        not_found=counts.get("NOT_FOUND", 0),
        multiple=counts.get("MULTIPLE_MATCHES", 0),
        invalid=counts.get("INVALID_ROW", 0),
        results=results,
        geojson=geojson,
    )
