from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CatastoCredentialUpsertRequest(BaseModel):
    sister_username: str = Field(min_length=1, max_length=128)
    sister_password: str = Field(min_length=1)
    convenzione: str | None = None
    codice_richiesta: str | None = None
    ufficio_provinciale: str = "ORISTANO Territorio"


class CatastoCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    sister_username: str
    convenzione: str | None
    codice_richiesta: str | None
    ufficio_provinciale: str
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CatastoCredentialStatusResponse(BaseModel):
    configured: bool
    credential: CatastoCredentialResponse | None


class CatastoCredentialTestResponse(BaseModel):
    id: UUID
    status: str
    success: bool | None
    mode: str | None
    reachable: bool | None
    authenticated: bool | None
    message: str | None
    verified_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CatastoComuneUpsertRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    codice_sister: str = Field(min_length=1, max_length=255)
    ufficio: str = "ORISTANO Territorio"


class CatastoComuneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    codice_sister: str
    ufficio: str


class CatastoSingleVisuraCreateRequest(BaseModel):
    comune: str = Field(min_length=1)
    catasto: str = Field(min_length=1)
    sezione: str | None = None
    foglio: str = Field(min_length=1)
    particella: str = Field(min_length=1)
    subalterno: str | None = None
    tipo_visura: str = Field(default="Sintetica", min_length=1)


class CatastoCaptchaSolveRequest(BaseModel):
    text: str = Field(min_length=1, max_length=64)


class CatastoVisuraRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    user_id: int
    row_index: int
    comune: str
    comune_codice: str | None
    catasto: str
    sezione: str | None
    foglio: str
    particella: str
    subalterno: str | None
    tipo_visura: str
    status: str
    current_operation: str | None
    error_message: str | None
    attempts: int
    captcha_image_path: str | None
    captcha_requested_at: datetime | None
    captcha_expires_at: datetime | None
    captcha_skip_requested: bool
    document_id: UUID | None
    created_at: datetime
    processed_at: datetime | None


class CatastoDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    request_id: UUID | None
    batch_id: UUID | None = None
    comune: str
    foglio: str
    particella: str
    subalterno: str | None
    catasto: str
    tipo_visura: str
    filename: str
    file_size: int | None
    codice_fiscale: str | None
    created_at: datetime


class CatastoDocumentBulkDownloadRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1)


class CatastoBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    name: str | None
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    skipped_items: int
    source_filename: str | None
    current_operation: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CatastoBatchDetailResponse(CatastoBatchResponse):
    requests: list[CatastoVisuraRequestResponse]


class CatastoOperationResponse(BaseModel):
    success: bool = True
    message: str
