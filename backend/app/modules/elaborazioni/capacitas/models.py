from __future__ import annotations

from datetime import date, datetime

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


class CapacitasLookupOption(BaseModel):
    id: str
    display: str

    model_config = ConfigDict(populate_by_name=True)


class CapacitasTerrenoRow(BaseModel):
    external_row_id: str | None = Field(default=None, alias="ID")
    pvc: str | None = Field(default=None, alias="PVC")
    com: str | None = Field(default=None, alias="COM")
    cco: str | None = Field(default=None, alias="CCO")
    fra: str | None = Field(default=None, alias="FRA")
    ccs: str | None = Field(default=None, alias="CCS")
    stato: str | None = Field(default=None, alias="Stato")
    ta_ext: str | None = Field(default=None, alias="Ta_ext")
    tipo: str | None = Field(default=None, alias="Tipo")
    superficie: str | None = Field(default=None, alias="Superficie")
    sez: str | None = Field(default=None, alias="Sez")
    foglio: str | None = Field(default=None, alias="Foglio")
    particella: str | None = Field(default=None, alias="Partic")
    sub: str | None = Field(default=None, alias="Sub")
    bac_descr: str | None = Field(default=None, alias="BacDescr")
    anno: str | None = Field(default=None, alias="Anno")
    voltura: str | None = Field(default=None, alias="Voltura")
    opcode: str | None = Field(default=None, alias="Opcode")
    data_reg: str | None = Field(default=None, alias="DataReg")
    belfiore: str | None = Field(default=None, alias="Belfiore")
    new_cco: str | None = Field(default=None, alias="NEW_CCO")
    new_fra: str | None = Field(default=None, alias="NEW_FRA")
    new_ccs: str | None = Field(default=None, alias="NEW_CCS")
    row_visual_state: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CapacitasTerreniSearchResult(BaseModel):
    total: int
    rows: list[CapacitasTerrenoRow]


class CapacitasTerreniSearchRequest(BaseModel):
    frazione_id: str = Field(min_length=1)
    sezione: str = ""
    foglio: str = ""
    particella: str = ""
    sub: str = ""
    qualita: str = ""
    caratura: str = ""
    caratura_val: str = ""
    in_essere: bool = False
    in_dom_irr: bool = False
    limita_risultati: bool = False
    credential_id: int | None = None


class CapacitasCertificatoTerreno(BaseModel):
    external_row_id: str | None = None
    foglio: str | None = None
    particella: str | None = None
    sub: str | None = None
    superficie_text: str | None = None
    riordino_code: str | None = None
    riordino_maglia: str | None = None
    riordino_lotto: str | None = None


class CapacitasTerrenoCertificato(BaseModel):
    cco: str | None = None
    fra: str | None = None
    ccs: str | None = None
    pvc: str | None = None
    com: str | None = None
    partita_code: str | None = None
    comune_label: str | None = None
    partita_status: str | None = None
    utenza_code: str | None = None
    utenza_status: str | None = None
    ruolo_status: str | None = None
    intestatari: list[str] = Field(default_factory=list)
    terreni: list[CapacitasCertificatoTerreno] = Field(default_factory=list)
    raw_text: str | None = None
    raw_html: str | None = None


class CapacitasTerrenoDetail(BaseModel):
    external_row_id: str | None = None
    foglio: str | None = None
    particella: str | None = None
    sub: str | None = None
    riordino_code: str | None = None
    riordino_maglia: str | None = None
    riordino_lotto: str | None = None
    irridist: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)
    raw_html: str | None = None


class CapacitasTerreniSyncRequest(CapacitasTerreniSearchRequest):
    fetch_certificati: bool = True
    fetch_details: bool = True


class CapacitasTerreniSyncResponse(BaseModel):
    total_rows: int
    imported_rows: int
    imported_certificati: int
    imported_details: int
    linked_units: int
    linked_occupancies: int
    search_key: str


class CapacitasTerreniBatchItem(BaseModel):
    label: str | None = None
    comune: str | None = None
    frazione_id: str | None = None
    sezione: str = ""
    foglio: str = Field(min_length=1)
    particella: str = Field(min_length=1)
    sub: str = ""
    qualita: str = ""
    caratura: str = ""
    caratura_val: str = ""
    in_essere: bool = False
    in_dom_irr: bool = False
    limita_risultati: bool = False
    credential_id: int | None = None
    fetch_certificati: bool | None = None
    fetch_details: bool | None = None


class CapacitasTerreniBatchRequest(BaseModel):
    items: list[CapacitasTerreniBatchItem] = Field(min_length=1)
    continue_on_error: bool = True
    credential_id: int | None = None
    fetch_certificati: bool = True
    fetch_details: bool = True


class CapacitasTerreniBatchItemResult(BaseModel):
    label: str | None = None
    search_key: str
    ok: bool
    total_rows: int = 0
    imported_rows: int = 0
    imported_certificati: int = 0
    imported_details: int = 0
    linked_units: int = 0
    linked_occupancies: int = 0
    error: str | None = None


class CapacitasTerreniBatchResponse(BaseModel):
    items: list[CapacitasTerreniBatchItemResult]
    processed_items: int
    failed_items: int
    total_rows: int
    imported_rows: int
    imported_certificati: int
    imported_details: int
    linked_units: int
    linked_occupancies: int


class CapacitasTerreniJobCreateRequest(CapacitasTerreniBatchRequest):
    pass


class CapacitasTerreniJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int | None
    requested_by_user_id: int | None
    status: str
    mode: str
    payload_json: dict | list | None
    result_json: dict | list | None
    error_detail: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


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
