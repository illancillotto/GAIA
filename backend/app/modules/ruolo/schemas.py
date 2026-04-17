from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ---------------------------------------------------------------------------
# Import Job schemas
# ---------------------------------------------------------------------------

class RuoloImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
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


class RuoloImportUploadResponse(BaseModel):
    job_id: str
    status: str
    anno_tributario: int
    warning_existing: bool = False
    existing_count: int = 0


class RuoloImportYearDetectionResponse(BaseModel):
    detected_year: int | None = None


# ---------------------------------------------------------------------------
# Particella
# ---------------------------------------------------------------------------

class RuoloParticellaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    partita_id: str
    anno_tributario: int
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
    catasto_parcel_id: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Partita
# ---------------------------------------------------------------------------

class RuoloPartitaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    avviso_id: str
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

    id: str
    codice_cnc: str
    anno_tributario: int
    subject_id: str | None = None
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

    id: str
    import_job_id: str
    codice_cnc: str
    anno_tributario: int
    subject_id: str | None = None
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


class RuoloStatsComuneItem(BaseModel):
    comune_nome: str
    anno_tributario: int
    totale_0648: float | None = None
    totale_0985: float | None = None
    totale_0668: float | None = None
    totale_euro: float | None = None
    num_avvisi: int


class RuoloStatsComuneResponse(BaseModel):
    anno_tributario: int
    items: list[RuoloStatsComuneItem]


# ---------------------------------------------------------------------------
# Catasto Parcels
# ---------------------------------------------------------------------------

class CatastoParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
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
