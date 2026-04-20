from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CatImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    tipo: str
    anno_campagna: int | None
    hash_file: str | None
    righe_totali: int
    righe_importate: int
    righe_anomalie: int
    status: str
    report_json: dict | None
    errore: str | None
    created_at: datetime
    completed_at: datetime | None
    created_by: int | None


class CatImportStartResponse(BaseModel):
    batch_id: UUID
    status: str


class CatAnomaliaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    particella_id: UUID | None
    utenza_id: UUID | None
    anno_campagna: int | None
    tipo: str
    severita: str
    descrizione: str | None
    dati_json: dict | None
    status: str
    note_operatore: str | None
    assigned_to: int | None
    segnalazione_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CatAnomaliaListResponse(BaseModel):
    items: list[CatAnomaliaResponse]
    total: int
    page: int
    page_size: int


class CatParticellaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    national_code: str | None
    cod_comune_istat: int
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str
    particella: str
    subalterno: str | None
    cfm: str | None
    superficie_mq: Decimal | None
    num_distretto: str | None
    nome_distretto: str | None
    source_type: str
    valid_from: date
    valid_to: date | None
    is_current: bool
    suppressed: bool
    created_at: datetime
    updated_at: datetime


class CatParticellaDetailResponse(CatParticellaResponse):
    fuori_distretto: bool


class CatParticellaHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: UUID
    particella_id: UUID
    national_code: str | None
    cod_comune_istat: int
    foglio: str
    particella: str
    subalterno: str | None
    superficie_mq: Decimal | None
    num_distretto: str | None
    valid_from: date
    valid_to: date
    changed_at: datetime
    change_reason: str | None


class CatDistrettoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    num_distretto: str
    nome_distretto: str | None
    decreto_istitutivo: str | None
    data_decreto: date | None
    attivo: bool
    note: str | None
    created_at: datetime
    updated_at: datetime


class CatDistrettoKpiResponse(BaseModel):
    distretto_id: UUID
    anno: int | None
    num_distretto: str
    totale_particelle: int
    totale_utenze: int
    totale_anomalie: int
    anomalie_error: int
    importo_totale_0648: Decimal
    importo_totale_0985: Decimal
    superficie_irrigabile_mq: Decimal
