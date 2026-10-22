from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.elaborazioni.step.models import DEFAULT_STEP_PORTAL_URL

StepJobMode = Literal["sync", "list_only", "archive_import", "relink"]


def _portal_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = value.strip()
    if not url.startswith("https://"):
        raise ValueError("portal_url deve essere un indirizzo https")
    return url


class StepCredentialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    portal_url: str = Field(default=DEFAULT_STEP_PORTAL_URL, max_length=500)
    active: bool = True
    min_delay_ms: int = Field(default=600, ge=600, le=60000)

    _check_url = field_validator("portal_url")(_portal_url)


class StepCredentialUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    portal_url: str | None = Field(default=None, max_length=500)
    active: bool | None = None
    min_delay_ms: int | None = Field(default=None, ge=600, le=60000)

    _check_url = field_validator("portal_url")(_portal_url)


class StepCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    username: str
    portal_url: str
    active: bool
    min_delay_ms: int
    last_used_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class StepSyncJobCreate(BaseModel):
    mode: StepJobMode = "sync"
    credential_id: int | None = None
    max_details: int | None = Field(default=None, ge=1, le=10000)
    force_details: bool = False
    archive_name: str | None = Field(default=None, min_length=5, max_length=255)

    @field_validator("archive_name")
    @classmethod
    def _archive_name(cls, value: str | None) -> str | None:
        if value is not None and (
            "/" in value or "\\" in value or not value.lower().endswith(".zip")
        ):
            raise ValueError(
                "archive_name deve essere il nome di un file .zip nella cartella import STEP"
            )
        return value


class StepSyncJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int | None = None
    requested_by_user_id: int | None = None
    status: str
    mode: str
    payload_json: dict[str, Any] | None = None
    result_json: dict[str, Any] | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StepOverviewOut(BaseModel):
    contribuenti: int
    documenti: int
    tributi: int
    pagamenti: int
    pdf_scaricati: int
    residuo_totale: Decimal
    ultimo_aggiornamento: datetime | None = None
    links: dict[str, int]
    import_archives: list[str]


class StepContribuenteRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cod_ent: str
    codice_fiscale: str
    denominazione: str | None = None
    numero_documenti: int | None = None
    importo: Decimal | None = None
    pagato: Decimal | None = None
    residuo: Decimal | None = None
    stato_documenti: str | None = None
    detail_synced_at: datetime | None = None


class StepContribuentiPage(BaseModel):
    items: list[StepContribuenteRow]
    total: int
    page: int
    page_size: int


class StepRuoloLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    documento_id: uuid.UUID
    reference_key: str
    codice_cnc: str | None = None
    anno_rif: int | None = None
    status: str
    ruolo_avviso_id: uuid.UUID | None = None
    candidate_avviso_ids: list[str] | None = None
    tributi_count: int
    imp_carico: Decimal | None = None
    imp_carico_pagato: Decimal | None = None
    imp_discaricato: Decimal | None = None


class StepTributoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    partita: str | None = None
    cod_tributo: str | None = None
    des_tributo: str | None = None
    tipo_tributo: str | None = None
    anno_rif: int | None = None
    imp_carico: Decimal | None = None
    imp_carico_pagato: Decimal | None = None
    imp_discaricato: Decimal | None = None
    avviso_reference_raw: str | None = None
    codice_cnc: str | None = None


class StepDocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    num_doc: str
    prg_coo: str
    section: str | None = None
    des_doc: str | None = None
    des_trib: str | None = None
    anno_rif: str | None = None
    data_notifica: date | None = None
    tot_dovuto: Decimal | None = None
    imp_carico: Decimal | None = None
    tot_pagato: Decimal | None = None
    residuo: Decimal | None = None
    pdf_status: str
    pdf_original_filename: str | None = None
    tributi: list[StepTributoOut] = Field(default_factory=list)
    links: list[StepRuoloLinkOut] = Field(default_factory=list)


class StepPagamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    num_quietanza: str | None = None
    num_doc: str | None = None
    data_pagamento: date | None = None
    data_accredito: date | None = None
    modalita: str | None = None
    importo: Decimal | None = None
    importo_pagato: Decimal | None = None
    annullato: bool
    stato: str | None = None
    riferimento: str | None = None


class StepContribuenteDetail(StepContribuenteRow):
    anagrafica_json: dict[str, Any] | None = None
    situazione_contabile_json: dict[str, Any] | None = None
    sections_json: list[dict[str, Any]] | None = None
    document_reconciliation_json: dict[str, Any] | None = None
    last_seen_at: datetime
    documenti: list[StepDocumentoOut] = Field(default_factory=list)
    pagamenti: list[StepPagamentoOut] = Field(default_factory=list)


class StepLinkAnomalyOut(StepRuoloLinkOut):
    contribuente_id: uuid.UUID
    codice_fiscale: str
    denominazione: str | None = None
    num_doc: str


class StepLinkAnomaliesPage(BaseModel):
    items: list[StepLinkAnomalyOut]
    total: int
    page: int
    page_size: int


class StepAvvisoLinkOut(BaseModel):
    contribuente_id: uuid.UUID
    codice_fiscale: str
    denominazione: str | None = None
    documento_id: uuid.UUID
    num_doc: str
    data_notifica: date | None = None
    pdf_status: str
    link: StepRuoloLinkOut
