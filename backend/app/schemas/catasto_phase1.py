from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
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


class CatAnomaliaSummaryBucketResponse(BaseModel):
    tipo: str
    label: str
    severita: str
    count: int


class CatAnomaliaSummaryResponse(BaseModel):
    total: int
    buckets: list[CatAnomaliaSummaryBucketResponse]


class CatAdeStatusScanBucketResponse(BaseModel):
    status: str
    classification: str
    count: int


class CatAdeStatusScanSummaryResponse(BaseModel):
    total_unmatched: int
    pending: int
    last_checked_at: datetime | None
    buckets: list[CatAdeStatusScanBucketResponse]


class CatAdeStatusScanCandidateResponse(BaseModel):
    ruolo_particella_id: UUID
    anno_tributario: int
    comune_nome: str
    comune_codice: str | None
    sezione: str | None
    foglio: str
    particella: str
    subalterno: str | None
    match_reason: str | None
    ade_scan_status: str | None
    ade_scan_classification: str | None
    ade_scan_checked_at: datetime | None
    ade_scan_document_id: UUID | None


class CatAdeStatusScanCandidateListResponse(BaseModel):
    items: list[CatAdeStatusScanCandidateResponse]
    total: int


class CatAdeStatusScanRunInput(BaseModel):
    limit: int = 50


class CatAdeStatusScanRunResponse(BaseModel):
    batch_id: UUID | None
    created: int
    skipped: int


class CatAnomaliaCfWizardItemResponse(BaseModel):
    anomalia_id: UUID
    utenza_id: UUID | None
    particella_id: UUID | None
    anno_campagna: int | None
    tipo: str
    severita: str
    descrizione: str | None
    status: str
    denominazione: str | None
    codice_fiscale: str | None
    codice_fiscale_raw: str | None
    num_distretto: int | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    error_code: str | None
    suggested_codice_fiscale: str | None
    created_at: datetime


class CatAnomaliaCfWizardListResponse(BaseModel):
    items: list[CatAnomaliaCfWizardItemResponse]
    total: int


class CatAnomaliaCfWizardApplyItemInput(BaseModel):
    anomalia_id: UUID
    codice_fiscale: str
    note_operatore: str | None = None


class CatAnomaliaCfWizardApplyInput(BaseModel):
    items: list[CatAnomaliaCfWizardApplyItemInput]


class CatAnomaliaCfWizardApplyResponse(BaseModel):
    applied_count: int
    updated_utenze: int
    closed_anomalies: int


class CatAnomaliaParticellaCandidateResponse(BaseModel):
    id: UUID
    cod_comune_capacitas: int
    codice_catastale: str | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str
    particella: str
    subalterno: str | None
    num_distretto: str | None
    nome_distretto: str | None
    ha_anagrafica: bool = False
    match_score: int


class CatAnomaliaParticellaWizardItemResponse(BaseModel):
    anomalia_id: UUID
    utenza_id: UUID | None
    anno_campagna: int | None
    tipo: str
    severita: str
    descrizione: str | None
    status: str
    denominazione: str | None
    nome_comune: str | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    cod_comune_capacitas: int | None
    num_distretto: int | None
    candidates: list[CatAnomaliaParticellaCandidateResponse]
    created_at: datetime


class CatAnomaliaParticellaWizardListResponse(BaseModel):
    items: list[CatAnomaliaParticellaWizardItemResponse]
    total: int


class CatAnomaliaParticellaWizardApplyItemInput(BaseModel):
    anomalia_id: UUID
    particella_id: UUID
    note_operatore: str | None = None


class CatAnomaliaParticellaWizardApplyInput(BaseModel):
    items: list[CatAnomaliaParticellaWizardApplyItemInput]


class CatAnomaliaParticellaWizardApplyResponse(BaseModel):
    applied_count: int
    updated_utenze: int
    closed_anomalies: int


class CatAnomaliaComuneCandidateResponse(BaseModel):
    id: UUID
    nome_comune: str
    nome_comune_legacy: str | None
    codice_catastale: str | None
    cod_comune_capacitas: int
    codice_comune_formato_numerico: int | None
    codice_comune_numerico_2017_2025: int | None
    sigla_provincia: str | None
    match_score: int


class CatAnomaliaComuneWizardItemResponse(BaseModel):
    anomalia_id: UUID
    utenza_id: UUID | None
    anno_campagna: int | None
    tipo: str
    severita: str
    descrizione: str | None
    status: str
    denominazione: str | None
    nome_comune: str | None
    cod_comune_capacitas: int | None
    source_cod_comune_capacitas: int | None
    num_distretto: int | None
    sezione_catastale: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    candidates: list[CatAnomaliaComuneCandidateResponse]
    created_at: datetime


class CatAnomaliaComuneWizardListResponse(BaseModel):
    items: list[CatAnomaliaComuneWizardItemResponse]
    total: int


class CatAnomaliaComuneWizardApplyItemInput(BaseModel):
    anomalia_id: UUID
    comune_id: UUID
    note_operatore: str | None = None


class CatAnomaliaComuneWizardApplyInput(BaseModel):
    items: list[CatAnomaliaComuneWizardApplyItemInput]


class CatAnomaliaComuneWizardApplyResponse(BaseModel):
    applied_count: int
    updated_utenze: int
    closed_anomalies: int


class CatDistrettiExcelAnalysisItemResponse(BaseModel):
    row_number: int
    comune_input: str | None
    sezione_input: str | None
    foglio_input: str | None
    particella_input: str | None
    sub_input: str | None
    comune_resolved: str | None
    sezione_resolved: str | None
    num_distretto: str | None
    nome_distretto: str | None
    esito: str
    message: str
    particella_ids: list[str]
    current_num_distretti: list[str | None]
    current_nome_distretti: list[str | None]


class CatDistrettiExcelAnalysisResponse(BaseModel):
    items: list[CatDistrettiExcelAnalysisItemResponse]
    total: int
    page: int
    page_size: int
    counters: dict[str, int]
    summary: dict[str, Any]


class CatAnomaliaUpdateInput(BaseModel):
    status: str | None = None
    note_operatore: str | None = None
    assigned_to: int | None = None


class CatParticellaSwappedCapacitasResponse(BaseModel):
    source_codice_catastale: str | None = None
    source_comune_nome: str | None = None
    source_foglio: str | None = None
    source_particella: str | None = None
    source_subalterno: str | None = None
    anno_tributario_latest: int | None = None
    match_confidence: str | None = None
    match_reason: str | None = None
    n_righe_ruolo: int = 0


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
    capacitas_last_sync_at: datetime | None
    capacitas_last_sync_status: str | None
    capacitas_last_sync_error: str | None
    capacitas_last_sync_job_id: int | None
    valid_from: date
    valid_to: date | None
    is_current: bool
    suppressed: bool
    created_at: datetime
    updated_at: datetime
    ha_anagrafica: bool = False
    utenza_cf: str | None = None
    utenza_denominazione: str | None = None
    swapped_capacitas: CatParticellaSwappedCapacitasResponse | None = None


class CatParticellaDetailResponse(CatParticellaResponse):
    fuori_distretto: bool


class CatParticellaCapacitasSyncInput(BaseModel):
    credential_id: int | None = None
    fetch_certificati: bool = True
    fetch_details: bool = True


class CatParticellaCapacitasSyncResponse(BaseModel):
    particella: CatParticellaDetailResponse
    status: str
    message: str
    job_id: int | None


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


class CatDashboardImportSummary(BaseModel):
    latest_import: CatImportBatchResponse | None
    latest_completed: CatImportBatchResponse | None
    processing_batch: int
    failed_batch: int
    completed_batch: int
    latest_imported_anno: int | None


class CatDashboardParticelleSummary(BaseModel):
    totale_correnti: int
    con_geometria: int
    senza_geometria: int
    in_distretto: int
    fuori_distretto: int
    senza_distretto: int
    soppresse: int


class CatDashboardUtenzeSummary(BaseModel):
    anno: int | None
    totale_utenze: int
    particelle_collegate: int
    superficie_irrigabile_mq: float
    importo_totale_0648: float
    importo_totale_0985: float
    importo_totale: float
    cf_mancante: int
    cf_invalido: int
    righe_con_anomalie: int
    utenze_senza_titolare: int


class CatDashboardAnomaliaBucket(BaseModel):
    key: str
    label: str
    count: int


class CatDashboardAnomalieSummary(BaseModel):
    aperte: int
    error: int
    warning: int
    info: int
    by_tipo: list[CatDashboardAnomaliaBucket]


class CatDashboardDistrettoSummary(BaseModel):
    distretto_id: UUID
    num_distretto: str
    nome_distretto: str | None
    attivo: bool
    totale_particelle: int
    totale_utenze: int
    totale_anomalie_aperte: int
    anomalie_error: int
    superficie_irrigabile_mq: float
    importo_totale: float


class CatDashboardAdeAlignmentSummary(BaseModel):
    checked: bool
    has_disallineamenti: bool
    staged_particelle: int
    nuove_in_ade: int
    geometrie_variate: int
    mancanti_in_ade: int
    latest_fetched_at: datetime | None
    message: str


class CatDashboardSummaryResponse(BaseModel):
    anno: int | None
    generated_at: datetime
    imports: CatDashboardImportSummary
    particelle: CatDashboardParticelleSummary
    utenze: CatDashboardUtenzeSummary
    anomalie: CatDashboardAnomalieSummary
    distretti: list[CatDashboardDistrettoSummary]
    ade_alignment: CatDashboardAdeAlignmentSummary


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
    subject_id: UUID | None = None
    subject_display_name: str | None = None
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
    indirizzo: str | None = None
    comune_residenza: str | None = None
    cap: str | None = None
    email: str | None = None
    telefono: str | None = None
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
    unit_id: UUID | None = None
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

    presente_in_catasto_consorzio: bool = False

    utenza_latest: CatAnagraficaUtenzaSummary | None = None
    cert_com: str | None = None
    cert_pvc: str | None = None
    cert_fra: str | None = None
    cert_ccs: str | None = None
    stato_ruolo: str | None = None
    stato_cnc: str | None = None
    intestatari: list[CatIntestatarioResponse] = []
    anomalie_count: int = 0
    anomalie_top: list[dict] = []
    note: str | None = None


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
    include_capacitas_live: bool = False
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


class CatAnagraficaBulkJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_filename: str | None = None
    skipped_rows: int = 0
    payload: CatAnagraficaBulkSearchRequest


class CatAnagraficaBulkJobSaveRequest(CatAnagraficaBulkJobCreateRequest):
    results: list[CatAnagraficaBulkSearchRowResult]


class CatAnagraficaBulkJobSummary(BaseModel):
    total: int
    found: int
    notFound: int
    multiple: int
    invalid: int
    error: int


class CatAnagraficaBulkJobItem(BaseModel):
    id: UUID
    created_at: datetime
    source_filename: str | None = None
    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"]
    skipped_rows: int = 0
    summary: CatAnagraficaBulkJobSummary


class CatAnagraficaBulkJobDetail(CatAnagraficaBulkJobItem):
    results: list[CatAnagraficaBulkSearchRowResult]


class CatAnagraficaBulkJobListResponse(BaseModel):
    items: list[CatAnagraficaBulkJobItem]
