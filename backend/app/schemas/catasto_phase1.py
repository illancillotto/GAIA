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


class CatCapacitasImportPreviewDiffSummaryResponse(BaseModel):
    nuove: int
    modificate: int
    invariate: int
    rimosse: int


class CatCapacitasImportPreviewDiffItemResponse(BaseModel):
    key: str
    change_type: Literal["new", "changed", "removed"]
    cco: str | None
    cod_comune_capacitas: int | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    codice_fiscale: str | None
    denominazione: str | None
    changed_fields: list[str] = []


class CatCapacitasImportPreviewResponse(BaseModel):
    filename: str
    anno_campagna: int | None
    file_hash: str
    is_exact_duplicate: bool
    duplicate_batch: CatImportBatchResponse | None
    active_batch: CatImportBatchResponse | None
    summary: CatCapacitasImportPreviewDiffSummaryResponse
    preview_items: list[CatCapacitasImportPreviewDiffItemResponse]
    warnings: list[str] = []


class CatImportSummaryResponse(BaseModel):
    tipo: str | None
    totale_batch: int
    processing_batch: int
    completed_batch: int
    failed_batch: int
    replaced_batch: int
    ultimo_completed_at: datetime | None


class CatMeterReadingValidationMessageResponse(BaseModel):
    level: Literal["error", "warning", "info"]
    code: str
    message: str
    field: str | None = None


class CatMeterReadingImportListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    distretto_id: UUID | None
    anno: int
    filename_originale: str
    file_hash: str | None
    stato: str
    totale_righe: int
    righe_importate: int
    righe_con_warning: int
    righe_scartate: int
    uploaded_by: int | None
    uploaded_at: datetime
    processed_at: datetime | None
    error_report: dict | list | None


class CatMeterReadingImportDetailResponse(CatMeterReadingImportListResponse):
    pass


class CatMeterReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    import_id: UUID | None
    distretto_id: UUID | None
    anno: int
    row_number: int | None
    excel_id: str | None
    punto_consegna: str
    matricola: str | None
    sigillo: str | None
    record_type: str | None
    record_kind: str | None
    operational_state: str | None
    tipologia_idrante: str | None
    firmware_version: str | None
    battery_level: str | None
    lettura_iniziale: Decimal | None
    lettura_finale: Decimal | None
    consumo_mc: Decimal | None
    consumo_effettivo_mc: Decimal | None = None
    data_lettura: date | None
    operatore_lettura: str | None
    intervento_da_eseguire: str | None
    intervento_eseguito: str | None
    operatore_intervento: str | None
    data_intervento: date | None
    dui: str | None
    codice_fiscale: str | None
    codice_fiscale_normalizzato: str | None
    subject_id: UUID | None
    subject_display_name: str | None = None
    coltura: str | None
    tariffa: str | None
    fondo_chiuso: str | None
    telefono: str | None
    note: str | None
    validation_status: str
    validation_messages: list[CatMeterReadingValidationMessageResponse] = []
    source: str
    mobile_session_id: str | None
    gps_lat: Decimal | None
    gps_lng: Decimal | None
    photo_url: str | None
    offline_created_at: datetime | None
    synced_at: datetime | None
    sync_status: str | None
    device_id: str | None
    mobile_operator_id: str | None
    manual_corrections: dict[str, Any] | None = None
    manual_override_updated_at: datetime | None = None
    manual_override_updated_by: int | None = None
    manual_audits: list["CatMeterReadingManualAuditResponse"] = []
    created_at: datetime
    updated_at: datetime


class CatMeterReadingListResponse(BaseModel):
    record_tab_counts: dict[str, int] = {}
    operational_counts: dict[str, int] = {}
    validation_counts: dict[str, int] = {}
    items: list[CatMeterReadingResponse]
    total: int
    page: int
    page_size: int


class CatMeterReadingImportPreviewItemResponse(BaseModel):
    row_number: int
    punto_consegna: str | None
    codice_fiscale: str | None
    codice_fiscale_normalizzato: str | None
    subject_id: UUID | None
    subject_display_name: str | None = None
    validation_status: str
    validation_messages: list[CatMeterReadingValidationMessageResponse] = []
    data: dict[str, Any]


class CatMeterReadingImportPreviewResponse(BaseModel):
    anno: int | None
    distretto_id: UUID | None
    distretto_numero: str | None = None
    distretto_nome: str | None = None
    filename: str
    totale_righe: int
    righe_valide: int
    righe_con_warning: int
    righe_con_errori: int
    items: list[CatMeterReadingImportPreviewItemResponse]


class CatMeterReadingImportRunResponse(BaseModel):
    import_id: UUID
    anno: int
    distretto_id: UUID | None
    stato: str
    totale_righe: int
    righe_importate: int
    righe_con_warning: int
    righe_scartate: int


class CatMeterReadingPatchRequest(BaseModel):
    punto_consegna: str | None = None
    matricola: str | None = None
    record_type: str | None = None
    tipologia_idrante: str | None = None
    codice_fiscale: str | None = None
    note: str | None = None
    intervento_da_eseguire: str | None = None
    change_note: str | None = None


class CatMeterReadingManualValidateRequest(BaseModel):
    change_note: str | None = None


class CatMeterReadingDeliveryPointMappingRequest(BaseModel):
    delivery_point_id: UUID
    change_note: str | None = None


class CatMeterReadingDeliveryPointMappingResponse(BaseModel):
    id: UUID
    distretto_code: str
    source_point_code: str
    delivery_point_id: UUID
    change_note: str | None = None
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime
    updated_readings_count: int


class CatDeliveryPointsImportConfigResponse(BaseModel):
    root_path: str | None = None
    expected_with_meter_dir: str
    expected_without_meter_dir: str
    updated_by: str | None = None
    updated_at: datetime | None = None


class CatDeliveryPointsImportConfigUpdateRequest(BaseModel):
    root_path: str | None = None


class CatDeliveryPointsImportRunResponse(BaseModel):
    job_id: UUID | None = None
    status: str = "completed"
    root_path: str
    requested_by: str | None = None
    error_message: str | None = None
    points_processed: int | None = None
    canals_processed: int | None = None
    meter_readings_linked: int | None = None
    meter_readings_unlinked: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CatDeliveryPointsGisCacheRefreshResponse(BaseModel):
    tile_revision: str
    refreshed_at: datetime
    affected_layers: list[str]
    martin_restarted: bool = False
    restart_error: str | None = None
    message: str


class CatMeterReadingManualAuditResponse(BaseModel):
    id: UUID
    meter_reading_id: UUID
    changed_by: int | None = None
    changed_by_display_name: str | None = None
    change_note: str | None = None
    previous_values: dict[str, Any] | list[Any] | None = None
    new_values: dict[str, Any] | list[Any] | None = None
    changed_at: datetime


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
    limit: int | None = None
    match_reasons: list[str] | None = None


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
    page: int
    page_size: int


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
    page: int
    page_size: int


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
    page: int
    page_size: int


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
    segnalazione_id: UUID | None = None


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


class CatIndiceDistrettoSummaryResponse(BaseModel):
    distretto_id: UUID
    num_distretto: str
    nome_distretto: str | None = None
    indice_key: str
    indice_label: str
    hectares_reference: Decimal | None = None


class CatIndiceColturaSummaryResponse(BaseModel):
    coltura: str
    gruppo_coltura: str | None = None
    particelle_count: int
    superficie_irrigata_ha: Decimal
    importo_stimato: Decimal
    importo_ruolo: Decimal = Decimal("0")


class CatIndiceBreakdownSummaryResponse(BaseModel):
    key: str
    label: str
    particelle_count: int
    ruolo_particelle_count: int = 0
    particelle_con_anagrafica_count: int = 0
    superficie_irrigata_ha: Decimal
    importo_stimato: Decimal
    importo_ruolo: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")


class CatIndiceGroupSummaryResponse(BaseModel):
    indice_key: str
    indice_label: str
    sort_order: int
    distretti_count: int
    particelle_count: int
    ruolo_particelle_count: int = 0
    particelle_con_anagrafica_count: int = 0
    particelle_senza_ruolo_count: int = 0
    particelle_senza_anagrafica_count: int = 0
    superficie_catastale_mq: Decimal
    superficie_irrigata_ha: Decimal
    importo_stimato: Decimal
    importo_ruolo: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")
    ruolo_metrics_reliable: bool = True
    ruolo_metrics_valid_count: int = 0
    ruolo_metrics_invalid_count: int = 0
    ruolo_metrics_warning: str | None = None
    hectares_reference_total: Decimal | None = None
    distretti: list[CatIndiceDistrettoSummaryResponse] = []
    colture: list[CatIndiceColturaSummaryResponse] = []
    comuni: list[CatIndiceBreakdownSummaryResponse] = []
    distretti_analytics: list[CatIndiceBreakdownSummaryResponse] = []


class CatIndiceRuoloReconciliationReasonResponse(BaseModel):
    key: str
    label: str
    description: str
    righe_ruolo_count: int = 0
    particelle_ruolo_distinte_count: int = 0
    cat_particelle_count: int = 0
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_ruolo: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")


class CatIndiceRuoloReconciliationResponse(BaseModel):
    righe_ruolo_totali_count: int = 0
    particelle_ruolo_totali_count: int = 0
    righe_ruolo_incluse_count: int = 0
    particelle_ruolo_incluse_count: int = 0
    righe_ruolo_escluse_count: int = 0
    particelle_ruolo_escluse_count: int = 0
    importo_ruolo_totale: Decimal = Decimal("0")
    importo_ruolo_incluso: Decimal = Decimal("0")
    importo_ruolo_escluso: Decimal = Decimal("0")
    importo_ruolo_escluso_manutenzione: Decimal = Decimal("0")
    importo_ruolo_escluso_irrigazione: Decimal = Decimal("0")
    importo_ruolo_escluso_istituzionale: Decimal = Decimal("0")
    superficie_irrigata_esclusa_ha: Decimal = Decimal("0")
    coverage_percent: Decimal | None = None
    reasons: list[CatIndiceRuoloReconciliationReasonResponse] = []


class CatIndiceRuoloExcludedParticellaResponse(BaseModel):
    key: str
    reason_key: str
    reason_label: str
    comune_nome: str | None = None
    foglio: str
    particella: str
    subalterno: str | None = None
    righe_ruolo_count: int = 0
    cat_particella_id: UUID | None = None
    catasto_is_current: bool | None = None
    catasto_num_distretto: str | None = None
    superficie_irrigata_ha: Decimal = Decimal("0")
    importo_ruolo: Decimal = Decimal("0")
    importo_ruolo_manutenzione: Decimal = Decimal("0")
    importo_ruolo_irrigazione: Decimal = Decimal("0")
    importo_ruolo_istituzionale: Decimal = Decimal("0")
    avvisi: list[str] = []
    nominativi: list[str] = []
    partite: list[str] = []


class CatIndiceRuoloExcludedParticelleResponse(BaseModel):
    anno_riferimento: int | None = None
    total: int = 0
    items: list[CatIndiceRuoloExcludedParticellaResponse] = []


class CatIndiceRuoloAssignDistrettoRequest(BaseModel):
    cat_particella_id: UUID
    distretto_id: UUID
    note: str | None = None


class CatIndiceRuoloAssignDistrettoResponse(BaseModel):
    cat_particella_id: UUID
    num_distretto: str
    nome_distretto: str | None = None
    updated: bool = False


class CatIndiceOverviewResponse(BaseModel):
    anno_riferimento: int | None = None
    total_distretti: int
    total_particelle: int
    available_colture: list[str] = []
    items: list[CatIndiceGroupSummaryResponse]
    ruolo_reconciliation: CatIndiceRuoloReconciliationResponse = CatIndiceRuoloReconciliationResponse()


class CatColturaBreakdownItemResponse(BaseModel):
    key: str
    label: str
    role_particelle_count: int
    meter_readings_count: int
    meter_points_count: int
    superficie_irrigata_ha: Decimal
    importo_totale: Decimal
    consumo_reale_mc: Decimal
    euro_per_ha: Decimal | None = None
    euro_per_mc: Decimal | None = None
    mc_per_ha: Decimal | None = None


class CatColturaYearItemResponse(CatColturaBreakdownItemResponse):
    anno: int


class CatColturaSummaryResponse(BaseModel):
    coltura: str
    gruppo_coltura: str | None = None
    quality_badge: str
    role_particelle_count: int
    meter_readings_count: int
    meter_points_count: int
    distretti_count: int
    indici_count: int
    comuni_count: int
    superficie_irrigata_ha: Decimal
    importo_totale: Decimal
    consumo_reale_mc: Decimal
    euro_per_ha: Decimal | None = None
    euro_per_mc: Decimal | None = None
    mc_per_ha: Decimal | None = None
    distretti: list[CatColturaBreakdownItemResponse] = []
    indici: list[CatColturaBreakdownItemResponse] = []
    comuni: list[CatColturaBreakdownItemResponse] = []
    years: list[CatColturaYearItemResponse] = []


class CatColturaOverviewResponse(BaseModel):
    anno_riferimento: int | None = None
    available_years: list[int] = []
    available_groups: list[str] = []
    available_distretti: list[str] = []
    available_indici: list[str] = []
    available_comuni: list[str] = []
    total_colture: int
    total_role_particelle: int
    total_meter_readings: int
    total_superficie_irrigata_ha: Decimal
    total_importo_totale: Decimal
    total_consumo_reale_mc: Decimal
    items: list[CatColturaSummaryResponse]


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
    indice_key: str | None = None
    indice_label: str | None = None
    indice_hectares_reference: Decimal | None = None
    indice_irriguo_coltura: str | None = None
    indice_irriguo_gruppo_coltura: str | None = None
    indice_irriguo_anno_riferimento: int | None = None
    swapped_capacitas: CatParticellaSwappedCapacitasResponse | None = None


class CatParticellaDetailResponse(CatParticellaResponse):
    fuori_distretto: bool
    indice_irriguo_base: Decimal | None = None
    indice_irriguo_moltiplicatore: Decimal = Decimal("1")
    indice_irriguo_finale: Decimal | None = None
    indice_irriguo_comune_arborea: bool = False
    indice_irriguo_anno_riferimento: int | None = None
    indice_irriguo_coltura: str | None = None
    indice_irriguo_gruppo_coltura: str | None = None
    indice_irriguo_sup_irrigata_ha: Decimal | None = None
    indice_irriguo_euro_mc: Decimal | None = None
    indice_irriguo_importo_stimato: Decimal | None = None


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
    importo_totale_0668: float = 0
    importo_totale_0985: float
    importo_ruolo_totale: float = 0
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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source_filename: str | None = None
    kind: Literal["CF_PIVA_PARTICELLE", "COMUNE_FOGLIO_PARTICELLA_INTESTATARI"]
    status: Literal["pending", "processing", "completed", "failed"]
    skipped_rows: int = 0
    total_rows: int = 0
    processed_rows: int = 0
    current_label: str | None = None
    error_message: str | None = None
    summary: CatAnagraficaBulkJobSummary


class CatAnagraficaBulkJobDetail(CatAnagraficaBulkJobItem):
    results: list[CatAnagraficaBulkSearchRowResult]


class CatAnagraficaBulkJobListResponse(BaseModel):
    items: list[CatAnagraficaBulkJobItem]
