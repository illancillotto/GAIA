from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatMeterReading, CatMeterReadingImport
from app.modules.catasto.services.meter_reading_import_service import import_meter_readings, prepare_meter_readings_import
from app.modules.catasto.services.meter_reading_parser import MeterReadingsParseError
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson
from app.schemas.catasto_phase1 import (
    CatMeterReadingImportDetailResponse,
    CatMeterReadingImportListResponse,
    CatMeterReadingImportPreviewItemResponse,
    CatMeterReadingImportPreviewResponse,
    CatMeterReadingImportRunResponse,
    CatMeterReadingListResponse,
    CatMeterReadingResponse,
    CatMeterReadingValidationMessageResponse,
)

router = APIRouter(prefix="/catasto/meter-readings", tags=["catasto-meter-readings"])


def _subject_preview_map(db: Session, subject_ids: list[UUID]) -> dict[UUID, str]:
    if not subject_ids:
        return {}
    result: dict[UUID, str] = {}
    persons = db.execute(select(AnagraficaPerson).where(AnagraficaPerson.subject_id.in_(subject_ids))).scalars().all()
    companies = db.execute(select(AnagraficaCompany).where(AnagraficaCompany.subject_id.in_(subject_ids))).scalars().all()
    for item in persons:
        result[item.subject_id] = f"{item.cognome} {item.nome}".strip() or item.codice_fiscale
    for item in companies:
        result[item.subject_id] = item.ragione_sociale or item.partita_iva or (item.codice_fiscale or str(item.subject_id))
    return result


def _serialize_reading(item: CatMeterReading, subject_display_name: str | None = None) -> CatMeterReadingResponse:
    raw_messages = item.validation_messages if isinstance(item.validation_messages, list) else []
    return CatMeterReadingResponse(
        id=item.id,
        import_id=item.import_id,
        distretto_id=item.distretto_id,
        anno=item.anno,
        row_number=item.row_number,
        excel_id=item.excel_id,
        punto_consegna=item.punto_consegna,
        matricola=item.matricola,
        sigillo=item.sigillo,
        record_type=item.record_type,
        record_kind=item.record_kind,
        operational_state=item.operational_state,
        tipologia_idrante=item.tipologia_idrante,
        firmware_version=item.firmware_version,
        battery_level=item.battery_level,
        lettura_iniziale=item.lettura_iniziale,
        lettura_finale=item.lettura_finale,
        consumo_mc=item.consumo_mc,
        data_lettura=item.data_lettura,
        operatore_lettura=item.operatore_lettura,
        intervento_da_eseguire=item.intervento_da_eseguire,
        intervento_eseguito=item.intervento_eseguito,
        operatore_intervento=item.operatore_intervento,
        data_intervento=item.data_intervento,
        dui=item.dui,
        codice_fiscale=item.codice_fiscale,
        codice_fiscale_normalizzato=item.codice_fiscale_normalizzato,
        subject_id=item.subject_id,
        subject_display_name=subject_display_name,
        coltura=item.coltura,
        tariffa=item.tariffa,
        fondo_chiuso=item.fondo_chiuso,
        telefono=item.telefono,
        note=item.note,
        validation_status=item.validation_status,
        validation_messages=[CatMeterReadingValidationMessageResponse(**message) for message in raw_messages if isinstance(message, dict)],
        source=item.source,
        mobile_session_id=item.mobile_session_id,
        gps_lat=item.gps_lat,
        gps_lng=item.gps_lng,
        photo_url=item.photo_url,
        offline_created_at=item.offline_created_at,
        synced_at=item.synced_at,
        sync_status=item.sync_status,
        device_id=item.device_id,
        mobile_operator_id=item.mobile_operator_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/import/validate", response_model=CatMeterReadingImportPreviewResponse)
def validate_meter_readings_import(
    file: UploadFile = File(...),
    anno: int | None = Query(None),
    distretto_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatMeterReadingImportPreviewResponse:
    try:
        prepared = prepare_meter_readings_import(
            db,
            file_bytes=file.file.read(),
            filename=file.filename or "meter-readings.xlsx",
            anno=anno,
            distretto_id=distretto_id,
        )
    except MeterReadingsParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CatMeterReadingImportPreviewResponse(
        anno=prepared.anno,
        distretto_id=prepared.distretto.id if prepared.distretto else None,
        distretto_numero=prepared.distretto.num_distretto if prepared.distretto else None,
        distretto_nome=prepared.distretto.nome_distretto if prepared.distretto else None,
        filename=prepared.filename,
        totale_righe=len(prepared.items),
        righe_valide=sum(1 for item in prepared.items if item.validation_status == "valid"),
        righe_con_warning=sum(1 for item in prepared.items if item.validation_status == "warning"),
        righe_con_errori=sum(1 for item in prepared.items if item.validation_status == "error"),
        items=[
            CatMeterReadingImportPreviewItemResponse(
                row_number=item.row_number,
                punto_consegna=item.payload.get("punto_consegna"),
                codice_fiscale=item.payload.get("codice_fiscale"),
                codice_fiscale_normalizzato=item.payload.get("codice_fiscale_normalizzato"),
                subject_id=item.payload.get("subject_id"),
                subject_display_name=item.subject_display_name,
                validation_status=item.validation_status,
                validation_messages=[CatMeterReadingValidationMessageResponse(**message.__dict__) for message in item.validation_messages],
                data=item.payload,
            )
            for item in prepared.items
        ],
    )


@router.post("/import", response_model=CatMeterReadingImportRunResponse, status_code=status.HTTP_201_CREATED)
def run_meter_readings_import(
    file: UploadFile = File(...),
    anno: int | None = Query(None),
    distretto_id: UUID | None = Query(None),
    mode: str = Query("upsert", pattern="^(import|upsert|replace)$"),
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_active_user),
) -> CatMeterReadingImportRunResponse:
    try:
        import_record, prepared = import_meter_readings(
            db,
            file_bytes=file.file.read(),
            filename=file.filename or "meter-readings.xlsx",
            uploaded_by=current_user.id,
            mode=mode,  # type: ignore[arg-type]
            anno=anno,
            distretto_id=distretto_id,
        )
    except MeterReadingsParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CatMeterReadingImportRunResponse(
        import_id=import_record.id,
        anno=prepared.anno or import_record.anno,
        distretto_id=import_record.distretto_id,
        stato=import_record.stato,
        totale_righe=import_record.totale_righe,
        righe_importate=import_record.righe_importate,
        righe_con_warning=import_record.righe_con_warning,
        righe_scartate=import_record.righe_scartate,
    )


@router.get("/imports", response_model=list[CatMeterReadingImportListResponse])
def list_meter_reading_imports(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatMeterReadingImport]:
    return list(
        db.execute(select(CatMeterReadingImport).order_by(CatMeterReadingImport.uploaded_at.desc())).scalars().all()
    )


@router.get("/imports/{import_id}", response_model=CatMeterReadingImportDetailResponse)
def get_meter_reading_import(
    import_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatMeterReadingImport:
    item = db.get(CatMeterReadingImport, import_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Import letture non trovato")
    return item


@router.get("", response_model=CatMeterReadingListResponse)
def list_meter_readings(
    anno: int | None = Query(None),
    distretto_id: UUID | None = Query(None),
    codice_fiscale: str | None = Query(None),
    punto_consegna: str | None = Query(None),
    matricola: str | None = Query(None),
    subject_id: UUID | None = Query(None),
    has_warnings: bool | None = Query(None),
    intervento_da_eseguire: bool | None = Query(None),
    source: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatMeterReadingListResponse:
    query = select(CatMeterReading)
    if anno is not None:
        query = query.where(CatMeterReading.anno == anno)
    if distretto_id is not None:
        query = query.where(CatMeterReading.distretto_id == distretto_id)
    if codice_fiscale:
        like = f"%{codice_fiscale.strip().upper()}%"
        query = query.where(
            or_(
                func.upper(func.coalesce(CatMeterReading.codice_fiscale, "")).like(like),
                func.upper(func.coalesce(CatMeterReading.codice_fiscale_normalizzato, "")).like(like),
            )
        )
    if punto_consegna:
        query = query.where(CatMeterReading.punto_consegna.ilike(f"%{punto_consegna.strip()}%"))
    if matricola:
        query = query.where(CatMeterReading.matricola.ilike(f"%{matricola.strip()}%"))
    if subject_id is not None:
        query = query.where(CatMeterReading.subject_id == subject_id)
    if has_warnings is True:
        query = query.where(CatMeterReading.validation_status == "warning")
    if intervento_da_eseguire is True:
        query = query.where(func.coalesce(CatMeterReading.intervento_da_eseguire, "") != "")
    if source:
        query = query.where(CatMeterReading.source == source)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(CatMeterReading.anno.desc(), CatMeterReading.punto_consegna.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    preview_map = _subject_preview_map(db, [item.subject_id for item in rows if item.subject_id is not None])
    return CatMeterReadingListResponse(
        items=[_serialize_reading(item, preview_map.get(item.subject_id) if item.subject_id else None) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/by-subject/{subject_id}", response_model=list[CatMeterReadingResponse])
def get_meter_readings_by_subject(
    subject_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> list[CatMeterReadingResponse]:
    rows = db.execute(
        select(CatMeterReading)
        .where(CatMeterReading.subject_id == subject_id)
        .order_by(CatMeterReading.anno.desc(), CatMeterReading.punto_consegna.asc())
    ).scalars().all()
    preview_map = _subject_preview_map(db, [subject_id])
    return [_serialize_reading(item, preview_map.get(subject_id)) for item in rows]


@router.get("/{reading_id}", response_model=CatMeterReadingResponse)
def get_meter_reading(
    reading_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_active_user),
) -> CatMeterReadingResponse:
    item = db.get(CatMeterReading, reading_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Lettura contatore non trovata")
    preview_map = _subject_preview_map(db, [item.subject_id] if item.subject_id else [])
    return _serialize_reading(item, preview_map.get(item.subject_id) if item.subject_id else None)
