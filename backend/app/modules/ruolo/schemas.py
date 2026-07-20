from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ---------------------------------------------------------------------------
# Import Job schemas
# ---------------------------------------------------------------------------

class RuoloImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    anno_tributario: int
    filename: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total_partite: int | None = None
    records_imported: int | None = None
    records_skipped: int | None = None
    records_errors: int | None = None
    error_detail: str | None = None
    triggered_by: int | None = None
    params_json: dict | None = None
    created_at: datetime

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return round((self.finished_at - self.started_at).total_seconds(), 1)
        return None


class RuoloImportJobListResponse(BaseModel):
    items: list[RuoloImportJobResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Particella
# ---------------------------------------------------------------------------

class RuoloParticellaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partita_id: uuid.UUID
    anno_tributario: int
    comune_nome: str | None = None
    comune_codice: str | None = None
    domanda_irrigua: str | None = None
    distretto: str | None = None
    foglio: str
    particella: str
    subalterno: str | None = None
    sup_catastale_are: float | None = None
    sup_catastale_ha: float | None = None
    sup_irrigata_ha: float | None = None
    coltura: str | None = None
    importo_manut: float | None = None
    importo_irrig: float | None = None
    importo_ist: float | None = None
    catasto_parcel_id: uuid.UUID | None = None
    cat_particella_id: uuid.UUID | None = None
    cat_particella_match_status: str | None = None
    cat_particella_match_confidence: str | None = None
    cat_particella_match_reason: str | None = None
    ade_scan_status: str | None = None
    ade_scan_classification: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Partita
# ---------------------------------------------------------------------------

class RuoloPartitaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avviso_id: uuid.UUID
    codice_partita: str
    comune_nome: str
    comune_codice: str | None = None
    contribuente_cf: str | None = None
    co_intestati_raw: str | None = None
    importo_0648: float | None = None
    importo_0985: float | None = None
    importo_0668: float | None = None
    particelle: list[RuoloParticellaResponse] = Field(default_factory=list)
    created_at: datetime


# ---------------------------------------------------------------------------
# Avviso
# ---------------------------------------------------------------------------

class RuoloAvvisoListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codice_cnc: str
    anno_tributario: int
    subject_id: uuid.UUID | None = None
    codice_fiscale_raw: str | None = None
    nominativo_raw: str | None = None
    codice_utenza: str | None = None
    importo_totale_0648: float | None = None
    importo_totale_0985: float | None = None
    importo_totale_0668: float | None = None
    importo_totale_euro: float | None = None
    display_name: str | None = None
    is_linked: bool = False
    created_at: datetime
    updated_at: datetime


class RuoloAvvisoListResponse(BaseModel):
    items: list[RuoloAvvisoListItemResponse]
    total: int
    page: int
    page_size: int


class RuoloAvvisoDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_job_id: uuid.UUID
    codice_cnc: str
    anno_tributario: int
    subject_id: uuid.UUID | None = None
    codice_fiscale_raw: str | None = None
    nominativo_raw: str | None = None
    domicilio_raw: str | None = None
    residenza_raw: str | None = None
    n2_extra_raw: str | None = None
    codice_utenza: str | None = None
    importo_totale_0648: float | None = None
    importo_totale_0985: float | None = None
    importo_totale_0668: float | None = None
    importo_totale_euro: float | None = None
    importo_totale_lire: float | None = None
    n4_campo_sconosciuto: str | None = None
    partite: list[RuoloPartitaResponse] = Field(default_factory=list)
    display_name: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Tributi
# ---------------------------------------------------------------------------

class RuoloTributiPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avviso_id: uuid.UUID
    import_job_id: uuid.UUID | None = None
    codice_cnc_raw: str | None = None
    codice_utenza_raw: str | None = None
    anno_tributario: int | None = None
    paid_at: datetime | None = None
    amount: float
    payment_reference: str | None = None
    payment_method: str | None = None
    source: str
    status: str
    raw_payload_json: dict | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class RuoloTributiPaymentCreateRequest(BaseModel):
    paid_at: datetime | None = None
    amount: float
    payment_reference: str | None = Field(default=None, max_length=160)
    payment_method: str | None = Field(default=None, max_length=80)
    source: str = Field(default="manual", max_length=40)
    status: str = Field(default="valid", max_length=24)
    raw_payload_json: dict[str, Any] | None = None


class RuoloTributiAvvisoStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    avviso_id: uuid.UUID
    payment_status: str
    workflow_status: str | None = None
    saldo_amount: float | None = None
    last_payment_at: datetime | None = None
    capacitas_url: str | None = None
    capacitas_avviso_code: str | None = None
    updated_by: int | None = None
    updated_at: datetime | None = None


class RuoloTributiAvvisoStatusUpdateRequest(BaseModel):
    workflow_status: str | None = Field(default=None, max_length=24)
    capacitas_url: str | None = None
    capacitas_avviso_code: str | None = Field(default=None, max_length=80)


class RuoloTributiNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avviso_id: uuid.UUID
    body: str
    visibility: str
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class RuoloTributiNoteCreateRequest(BaseModel):
    body: str = Field(min_length=1)
    visibility: str = Field(default="internal", max_length=24)


class RuoloTributiAvvisoListItemResponse(BaseModel):
    id: uuid.UUID
    codice_cnc: str
    anno_tributario: int
    subject_id: uuid.UUID | None = None
    codice_fiscale_raw: str | None = None
    nominativo_raw: str | None = None
    codice_utenza: str | None = None
    importo_totale_euro: float | None = None
    paid_amount: float
    saldo_amount: float | None = None
    payment_status: str
    workflow_status: str | None = None
    last_payment_at: datetime | None = None
    capacitas_url: str | None = None
    capacitas_avviso_code: str | None = None
    display_name: str | None = None
    is_linked: bool
    notes_count: int = 0


class RuoloTributiAvvisoListResponse(BaseModel):
    items: list[RuoloTributiAvvisoListItemResponse]
    total: int
    page: int
    page_size: int


class RuoloTributiAvvisoDetailResponse(RuoloTributiAvvisoListItemResponse):
    domicilio_raw: str | None = None
    residenza_raw: str | None = None
    importo_totale_0648: float | None = None
    importo_totale_0985: float | None = None
    importo_totale_0668: float | None = None
    payments: list[RuoloTributiPaymentResponse] = Field(default_factory=list)
    notes: list[RuoloTributiNoteResponse] = Field(default_factory=list)


class RuoloTributiReminderCreateRequest(BaseModel):
    template_id: uuid.UUID | None = None
    notes: str | None = None


class RuoloTributiReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avviso_id: uuid.UUID
    template_id: uuid.UUID | None = None
    status: str
    generated_document_path: str | None = None
    generated_at: datetime | None = None
    generated_by: int | None = None
    payload_json: dict | None = None
    notes: str | None = None
    created_at: datetime
    download_url: str | None = None


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

class RuoloStatsByAnnoResponse(BaseModel):
    anno_tributario: int
    total_avvisi: int
    avvisi_collegati: int
    avvisi_non_collegati: int
    totale_0648: float | None = None
    totale_0985: float | None = None
    totale_0668: float | None = None
    totale_euro: float | None = None


class RuoloStatsResponse(BaseModel):
    items: list[RuoloStatsByAnnoResponse]


class RuoloParticelleSummaryResponse(BaseModel):
    anno_tributario: int | None = None
    total_particelle: int
    collegate_catasto: int
    non_collegate_catasto: int
    soppresse_ade: int


class RuoloStatsComuneItem(BaseModel):
    comune_nome: str
    anno_tributario: int
    totale_0648: float | None = None
    totale_0985: float | None = None
    totale_0668: float | None = None
    totale_euro: float | None = None
    num_avvisi: int
    num_partite: int | None = None
    num_particelle: int | None = None
    non_collegate_catasto: int | None = None


class RuoloStatsComuneResponse(BaseModel):
    anno_tributario: int
    items: list[RuoloStatsComuneItem]


class RuoloStatsAmountBreakdownItem(BaseModel):
    key: str
    label: str
    amount: float


class RuoloStatsCountBreakdownItem(BaseModel):
    key: str
    label: str
    count: int


class RuoloStatsAnalyticsResponse(BaseModel):
    anno_tributario: int
    particelle_summary: RuoloParticelleSummaryResponse
    tributi_breakdown: list[RuoloStatsAmountBreakdownItem]
    match_status_breakdown: list[RuoloStatsCountBreakdownItem]
    match_reason_breakdown: list[RuoloStatsCountBreakdownItem]
    distretto_breakdown: list[RuoloStatsCountBreakdownItem]
    coltura_breakdown: list[RuoloStatsCountBreakdownItem]
    comuni: list[RuoloStatsComuneItem]


class RuoloCapacitasCheckItemResponse(BaseModel):
    tax_code: str
    ruolo_display_name: str | None = None
    capacitas_display_name: str | None = None
    status: str
    diagnosis: str = "allineato"
    ruolo_0648: float = 0
    gaia_0648: float = 0
    excel_0648: float = 0
    delta_0648: float = 0
    delta_gaia_excel_0648: float = 0
    ruolo_0985: float = 0
    gaia_0985: float = 0
    excel_0985: float = 0
    delta_0985: float = 0
    delta_gaia_excel_0985: float = 0
    ruolo_totale_confrontabile: float = 0
    gaia_totale_confrontabile: float = 0
    excel_totale_confrontabile: float = 0
    delta_totale_confrontabile: float = 0
    delta_gaia_excel_totale_confrontabile: float = 0
    anomalous_rows_count: int = 0
    clean_rows_count: int = 0
    anomaly_gap_share: float = 0
    anomaly_driven_case: bool = False


class RuoloCapacitasCheckSummaryResponse(BaseModel):
    anno_tributario: int
    ruolo_positions: int
    capacitas_positions: int
    capacitas_active_batch_id: str | None = None
    matched_positions: int
    only_in_ruolo: int
    only_in_capacitas: int
    ruolo_positions_missing_tax_code: int
    capacitas_positions_missing_tax_code: int
    ruolo_totale_0648: float = 0
    gaia_totale_0648: float = 0
    excel_totale_0648: float = 0
    delta_totale_0648: float = 0
    delta_gaia_excel_totale_0648: float = 0
    ruolo_totale_0985: float = 0
    gaia_totale_0985: float = 0
    excel_totale_0985: float = 0
    delta_totale_0985: float = 0
    delta_gaia_excel_totale_0985: float = 0
    ruolo_totale_0668: float = 0
    ruolo_totale_confrontabile: float = 0
    gaia_totale_confrontabile: float = 0
    excel_totale_confrontabile: float = 0
    delta_totale_confrontabile: float = 0
    delta_gaia_excel_totale_confrontabile: float = 0
    mismatch_positions: int = 0
    diagnosis_ruolo_count: int = 0
    diagnosis_gaia_count: int = 0
    diagnosis_excel_count: int = 0


class RuoloCapacitasCheckResponse(BaseModel):
    summary: RuoloCapacitasCheckSummaryResponse
    items: list[RuoloCapacitasCheckItemResponse]


class RuoloCapacitasCheckComuneItemResponse(BaseModel):
    comune_nome: str
    source_comuni_ruolo: list[str] = Field(default_factory=list)
    source_comuni_capacitas: list[str] = Field(default_factory=list)
    capacitas_active_batch_id: str | None = None
    ruolo_0648: float = 0
    gaia_0648: float = 0
    excel_0648: float = 0
    delta_0648: float = 0
    delta_gaia_excel_0648: float = 0
    ruolo_0985: float = 0
    gaia_0985: float = 0
    excel_0985: float = 0
    delta_0985: float = 0
    delta_gaia_excel_0985: float = 0
    ruolo_totale_confrontabile: float = 0
    gaia_totale_confrontabile: float = 0
    excel_totale_confrontabile: float = 0
    delta_totale_confrontabile: float = 0
    delta_gaia_excel_totale_confrontabile: float = 0


class RuoloCapacitasCheckComuneResponse(BaseModel):
    anno_tributario: int
    items: list[RuoloCapacitasCheckComuneItemResponse]


class RuoloCapacitasCalculationComuneSummaryResponse(BaseModel):
    comune_nome: str
    rows_count: int
    anomalous_rows_count: int = 0
    total_sup_irrigabile_mq: float = 0
    total_imponibile_sf: float = 0
    gaia_total: float = 0
    excel_total: float = 0
    gap_excel_gaia_total: float = 0


class RuoloCapacitasCalculationRowResponse(BaseModel):
    source_filename: str | None = None
    source_row_number: int | None = None
    cco: str | None = None
    cod_provincia: int | None = None
    cod_comune_capacitas: int | None = None
    cod_frazione: int | None = None
    num_distretto: int | None = None
    nome_distretto_loc: str | None = None
    comune_nome: str | None = None
    sezione_catastale: str | None = None
    foglio: str | None = None
    particella: str | None = None
    subalterno: str | None = None
    sup_catastale_mq: float | None = None
    sup_irrigabile_mq: float = 0
    ind_spese_fisse: float | None = None
    imponibile_sf: float = 0
    imponibile_per_mq: float | None = None
    esente_0648: bool = False
    aliquota_0648: float | None = None
    aliquota_0985: float | None = None
    excel_0648: float = 0
    excel_0985: float = 0
    excel_total: float = 0
    gaia_0648: float = 0
    gaia_0985: float = 0
    gaia_total: float = 0
    gap_excel_gaia_total: float = 0
    codice_fiscale_raw: str | None = None
    anomalia_imponibile: bool = False
    anomalia_importi: bool = False
    anomalia_superficie: bool = False
    anomalia_cf_invalido: bool = False
    anomalia_cf_mancante: bool = False
    anomalia_comune_invalido: bool = False
    anomalia_particella_assente: bool = False


class RuoloCapacitasCalculationSummaryResponse(BaseModel):
    anno_tributario: int
    tax_code: str
    display_name: str | None = None
    active_batch_id: str | None = None
    source_filename: str | None = None
    rows_count: int
    anomalous_rows_count: int = 0
    clean_rows_count: int = 0
    total_sup_irrigabile_mq: float = 0
    total_imponibile_sf: float = 0
    gaia_total: float = 0
    excel_total: float = 0
    gap_excel_gaia_total: float = 0
    gaia_total_anomalous_rows: float = 0
    excel_total_anomalous_rows: float = 0
    gaia_total_clean_rows: float = 0
    excel_total_clean_rows: float = 0
    distinct_ind_spese_fisse: list[float] = Field(default_factory=list)
    distinct_imponibile_per_mq: list[float] = Field(default_factory=list)


class RuoloCapacitasCalculationDetailResponse(BaseModel):
    summary: RuoloCapacitasCalculationSummaryResponse
    comuni: list[RuoloCapacitasCalculationComuneSummaryResponse]
    rows: list[RuoloCapacitasCalculationRowResponse]


class RuoloGaiaCalculationItemResponse(BaseModel):
    tax_code: str
    display_name: str | None = None
    ruolo_display_name: str | None = None
    status: str = "matched"
    diagnosis: str = "allineato"
    comuni_count: int = 0
    rows_count: int = 0
    anomalous_rows_count: int = 0
    clean_rows_count: int = 0
    total_sup_irrigabile_mq: float = 0
    total_imponibile_sf: float = 0
    ruolo_0648: float = 0
    gaia_0648: float = 0
    ruolo_0985: float = 0
    gaia_0985: float = 0
    ruolo_totale_confrontabile: float = 0
    gaia_total: float = 0
    excel_0648: float = 0
    excel_0985: float = 0
    excel_total: float = 0
    delta_ruolo_gaia_totale: float = 0
    gap_excel_gaia_total: float = 0
    anomaly_gap_share: float = 0
    anomaly_driven_case: bool = False


class RuoloGaiaCalculationSummaryResponse(BaseModel):
    anno_tributario: int
    active_batch_id: str | None = None
    positions: int = 0
    ruolo_positions: int = 0
    positions_missing_tax_code: int = 0
    ruolo_positions_missing_tax_code: int = 0
    anomalous_positions: int = 0
    anomaly_driven_positions: int = 0
    total_rows: int = 0
    anomalous_rows: int = 0
    clean_rows: int = 0
    total_sup_irrigabile_mq: float = 0
    total_imponibile_sf: float = 0
    ruolo_totale_0648: float = 0
    gaia_totale_0648: float = 0
    ruolo_totale_0985: float = 0
    gaia_totale_0985: float = 0
    ruolo_totale_0668: float = 0
    ruolo_totale_confrontabile: float = 0
    gaia_totale_confrontabile: float = 0
    excel_totale_0648: float = 0
    excel_totale_0985: float = 0
    excel_totale_confrontabile: float = 0
    delta_ruolo_gaia_totale: float = 0
    gap_excel_gaia_totale: float = 0
    mismatch_positions: int = 0
    diagnosis_ruolo_count: int = 0
    diagnosis_gaia_count: int = 0
    diagnosis_excel_count: int = 0


class RuoloGaiaCalculationResponse(BaseModel):
    summary: RuoloGaiaCalculationSummaryResponse
    items: list[RuoloGaiaCalculationItemResponse]


# ---------------------------------------------------------------------------
# Catasto Parcels
# ---------------------------------------------------------------------------

class CatastoParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    comune_codice: str
    comune_nome: str
    foglio: str
    particella: str
    subalterno: str | None = None
    sup_catastale_are: float | None = None
    sup_catastale_ha: float | None = None
    valid_from: int
    valid_to: int | None = None
    source: str
    created_at: datetime
    updated_at: datetime
