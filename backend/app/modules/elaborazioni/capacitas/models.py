from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CapacitasAnagrafica(BaseModel):
    id: str | None = Field(default=None)
    id_ana: str | None = Field(default=None, alias="IDXANA")
    stato: str | None = Field(default=None, alias="Stato")
    patrimonio: str | None = Field(default=None, alias="Patrimonio")
    prg: str | None = Field(default=None, alias="Prg")
    di: str | None = Field(default=None, alias="Di")
    tp: str | None = Field(default=None, alias="TP")
    ta: str | None = Field(default=None, alias="TA")
    pvc: str | None = Field(default=None, alias="PVC")
    com: str | None = Field(default=None, alias="COM")
    belfiore: str | None = Field(default=None, alias="Belfiore")
    cco: str | None = Field(default=None, alias="CCO")
    fraz: str | None = Field(default=None, alias="Fraz")
    sche: str | None = Field(default=None, alias="Sche")
    comune: str | None = Field(default=None, alias="Comune")
    denominazione: str | None = Field(default=None, alias="Denominazione")
    data_nascita: str | None = Field(default=None, alias="DataNascita")
    luogo_nascita: str | None = Field(default=None, alias="LuogoNascita")
    codice_fiscale: str | None = Field(default=None, alias="CodiceFiscale")
    cert_at: str | None = Field(default=None, alias="CertAT")
    deceduto: str | None = Field(default=None, alias="Deceduto")
    partita_iva: str | None = Field(default=None, alias="PartitaIva")
    titolo1: str | None = Field(default=None, alias="Titolo1")
    titolo_lib1: str | None = Field(default=None, alias="TitoloLib1")
    titolo_lib2: str | None = Field(default=None, alias="TitoloLib2")
    n_terreni: str | None = Field(default=None, alias="NTerreni")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasSearchResult(BaseModel):
    total: int
    rows: list[CapacitasAnagrafica]


class CapacitasCredentialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    active: bool = True
    allowed_hours_start: int = Field(default=0, ge=0, le=23)
    allowed_hours_end: int = Field(default=23, ge=0, le=23)


class CapacitasCredentialUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    active: bool | None = None
    allowed_hours_start: int | None = Field(default=None, ge=0, le=23)
    allowed_hours_end: int | None = Field(default=None, ge=0, le=23)


class CapacitasCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    username: str
    active: bool
    allowed_hours_start: int
    allowed_hours_end: int
    last_used_at: datetime | None
    last_error: str | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class AnagraficaSearchRequest(BaseModel):
    q: str = Field(min_length=1)
    tipo_ricerca: int = Field(default=1)
    solo_con_beni: bool = False
    credential_id: int | None = None
