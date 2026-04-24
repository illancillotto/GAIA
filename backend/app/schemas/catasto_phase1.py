from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.utenze.schemas import AnagraficaPersonResponse, AnagraficaPersonSnapshotResponse


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


class CatImportSummaryResponse(BaseModel):
    tipo: str | None
    totale_batch: int
    processing_batch: int
    completed_batch: int
    failed_batch: int
    replaced_batch: int
    ultimo_completed_at: datetime | None


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


class CatAnomaliaUpdateInput(BaseModel):
    status: str | None = None
    note_operatore: str | None = None
    assigned_to: int | None = None


class CatParticellaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comune_id: UUID | None
    id: UUID
    national_code: str | None
    cod_comune_capacitas: int
    codice_catastale: str | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str
    particella: str
    subalterno: str | None
    cfm: str | None
    superficie_mq: Decimal | None
    superficie_grafica_mq: Decimal | None
    num_distretto: str | None
    nome_distretto: str | None
    source_type: str
    valid_from: date
    valid_to: date | None
    is_current: bool
    suppressed: bool
    created_at: datetime
    updated_at: datetime
    utenza_cf: str | None = None
    utenza_denominazione: str | None = None


class CatParticellaDetailResponse(CatParticellaResponse):
    fuori_distretto: bool


class CatConsorzioOccupancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    unit_id: UUID
    segment_id: UUID | None
    utenza_id: UUID | None
    cco: str | None
    fra: str | None
    ccs: str | None
    pvc: str | None
    com: str | None
    source_type: str
    relationship_type: str
    valid_from: date | None
    valid_to: date | None
    is_current: bool
    confidence: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CatUtenzaIntestatarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    utenza_id: UUID
    subject_id: UUID | None
    idxana: str | None
    idxesa: str | None
    history_id: str | None
    anno_riferimento: int | None
    data_agg: datetime | None
    at: str | None
    site: str | None
    voltura: str | None
    op: str | None
    sn: str | None
    codice_fiscale: str | None
    partita_iva: str | None
    denominazione: str | None
    data_nascita: date | None
    luogo_nascita: str | None
    residenza: str | None
    comune_residenza: str | None
    cap: str | None
    titoli: str | None
    deceduto: bool
    collected_at: datetime
    person: AnagraficaPersonResponse | None = None
    person_snapshots: list[AnagraficaPersonSnapshotResponse] = []


class CatConsorzioUnitSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    particella_id: UUID | None
    comune_id: UUID | None
    cod_comune_capacitas: int | None
    source_comune_id: UUID | None
    source_cod_comune_capacitas: int | None
    source_codice_catastale: str | None
    source_comune_label: str | None
    comune_resolution_mode: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    descrizione: str | None
    source_first_seen: date | None
    source_last_seen: date | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    comune_label: str | None = None
    source_comune_resolved_label: str | None = None
    occupancies: list[CatConsorzioOccupancyResponse] = []
    intestatari_proprietari: list[CatUtenzaIntestatarioResponse] = []


class CatParticellaConsorzioResponse(BaseModel):
    particella_id: UUID
    units: list[CatConsorzioUnitSummaryResponse]


class CatParticellaHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: UUID
    particella_id: UUID
    comune_id: UUID | None
    national_code: str | None
    cod_comune_capacitas: int
    codice_catastale: str | None
    foglio: str
    particella: str
    subalterno: str | None
    superficie_mq: Decimal | None
    superficie_grafica_mq: Decimal | None
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


class CatSchemaContributoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codice: str
    descrizione: str | None
    tipo_calcolo: str
    attivo: bool


class CatUtenzaIrriguaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    import_batch_id: UUID
    anno_campagna: int
    cco: str | None
    comune_id: UUID | None
    cod_provincia: int | None
    cod_comune_capacitas: int | None
    cod_frazione: int | None
    num_distretto: int | None
    nome_distretto_loc: str | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    particella_id: UUID | None
    sup_catastale_mq: Decimal | None
    sup_irrigabile_mq: Decimal | None
    ind_spese_fisse: Decimal | None
    imponibile_sf: Decimal | None
    esente_0648: bool
    aliquota_0648: Decimal | None
    importo_0648: Decimal | None
    aliquota_0985: Decimal | None
    importo_0985: Decimal | None
    denominazione: str | None
    codice_fiscale: str | None
    codice_fiscale_raw: str | None
    anomalia_superficie: bool
    anomalia_cf_invalido: bool
    anomalia_cf_mancante: bool
    anomalia_comune_invalido: bool
    anomalia_particella_assente: bool
    anomalia_imponibile: bool
    anomalia_importi: bool
    created_at: datetime


class CatIntestatarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codice_fiscale: str
    denominazione: str | None
    tipo: str | None
    cognome: str | None
    nome: str | None
    data_nascita: date | None
    luogo_nascita: str | None
    ragione_sociale: str | None
    source: str | None
    last_verified_at: datetime | None
    deceduto: bool | None


class CatAnagraficaUtenzaSummary(BaseModel):
    id: UUID
    cco: str | None = None
    anno_campagna: int | None = None
    stato: str | None = None
    num_distretto: int | None = None
    nome_distretto: str | None = None
    sup_irrigabile_mq: Decimal | None = None
    denominazione: str | None = None
    codice_fiscale: str | None = None
    ha_anomalie: bool | None = None


class CatAnagraficaMatch(BaseModel):
    particella_id: UUID
    comune_id: UUID | None = None
    comune: str | None = None
    cod_comune_capacitas: int | None = None
    codice_catastale: str | None = None
    foglio: str
    particella: str
    subalterno: str | None = None
    num_distretto: str | None = None
    nome_distretto: str | None = None
    superficie_mq: Decimal | None = None
    superficie_grafica_mq: Decimal | None = None

    utenza_latest: CatAnagraficaUtenzaSummary | None = None
    intestatari: list[CatIntestatarioResponse] = []
    anomalie_count: int = 0
    anomalie_top: list[dict] = []


class CatAnagraficaSearchResponse(BaseModel):
    matches: list[CatAnagraficaMatch]


class CatAnagraficaBulkSearchRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_index: int
    comune: str | None = None
    sezione: str | None = None
    foglio: str | None = None
    particella: str | None = None
    sub: str | None = None
    codice_fiscale: str | None = None
    partita_iva: str | None = None


class CatAnagraficaBulkSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"] | None = None
    rows: list[CatAnagraficaBulkSearchRow]


class CatAnagraficaBulkSearchRowResult(BaseModel):
    row_index: int
    comune_input: str | None = None
    sezione_input: str | None = None
    foglio_input: str | None = None
    particella_input: str | None = None
    sub_input: str | None = None
    codice_fiscale_input: str | None = None
    partita_iva_input: str | None = None
    esito: str
    message: str
    particella_id: UUID | None = None
    match: CatAnagraficaMatch | None = None
    matches: list[CatAnagraficaMatch] | None = None
    matches_count: int | None = None


class CatAnagraficaBulkSearchResponse(BaseModel):
    results: list[CatAnagraficaBulkSearchRowResult]
