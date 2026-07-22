from __future__ import annotations

from datetime import date, datetime, timezone
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID

_ASPNET_DATE_RE = re.compile(r"^/Date\((-?\d+)(?:[+-]\d+)?\)/$")


def _parse_aspnet_datetime(value: object) -> object:
    if not isinstance(value, str):
        return value
    match = _ASPNET_DATE_RE.match(value.strip())
    if match is None:
        return value
    milliseconds = int(match.group(1))
    if milliseconds < 0:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)


class CapacitasAspNetDateModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _normalize_aspnet_dates(cls, value: object) -> object:
        return _parse_aspnet_datetime(value)


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


class CapacitasStoricoAnagraficaRow(BaseModel):
    history_id: str = Field(alias="ID")
    idxana: str | None = Field(default=None, alias="IDXANA")
    at: str | None = Field(default=None, alias="At")
    data_agg: str | None = Field(default=None, alias="DataAgg")
    denominazione: str | None = Field(default=None, alias="Denominazione")
    codice_fiscale: str | None = Field(default=None, alias="CodFisc")
    partita_iva: str | None = Field(default=None, alias="PIva")
    data_nascita: str | None = Field(default=None, alias="DataNascita")
    luogo_nascita: str | None = Field(default=None, alias="LuogoNascita")
    sesso: str | None = Field(default=None, alias="Sesso")
    anno: str | None = Field(default=None, alias="Anno")
    site: str | None = Field(default=None, alias="Site")
    voltura: str | None = Field(default=None, alias="Voltura")
    op: str | None = Field(default=None, alias="Op")
    sn: str | None = Field(default=None, alias="SN")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasAnagraficaDetail(BaseModel):
    history_id: str | None = None
    idxana: str | None = None
    idxesa: str | None = None
    is_persona_fisica: bool = True
    cognome: str | None = None
    nome: str | None = None
    sesso: str | None = None
    data_nascita: date | None = None
    denominazione: str | None = None
    luogo_nascita: str | None = None
    luogo_nascita_belfiore: str | None = None
    luogo_nascita_provincia: str | None = None
    codice_fiscale: str | None = None
    codice_fiscale_origine: str | None = None
    partita_iva: str | None = None
    partita_iva_origine: str | None = None
    sede_belfiore: str | None = None
    residenza_belfiore: str | None = None
    residenza_provincia: str | None = None
    residenza_localita: str | None = None
    residenza_toponimo: str | None = None
    residenza_indirizzo: str | None = None
    residenza_civico: str | None = None
    residenza_sub: str | None = None
    residenza_cap: str | None = None
    domicilio_belfiore: str | None = None
    domicilio_provincia: str | None = None
    domicilio_localita: str | None = None
    domicilio_toponimo: str | None = None
    domicilio_indirizzo: str | None = None
    domicilio_civico: str | None = None
    domicilio_sub: str | None = None
    domicilio_cap: str | None = None
    email: str | None = None
    pec: str | None = None
    telefono: str | None = None
    fax: str | None = None
    cellulare: str | None = None
    ufficio: str | None = None
    note: list[str] = Field(default_factory=list)
    raw_html: str | None = None


class CapacitasAnagraficaHistoryImportItem(BaseModel):
    subject_id: UUID | None = None
    idxana: str | None = Field(default=None, min_length=1)


class CapacitasAnagraficaHistoryImportRequest(BaseModel):
    items: list[CapacitasAnagraficaHistoryImportItem] = Field(min_length=1)
    credential_id: int | None = None
    continue_on_error: bool = True
    auto_resume: bool = True


class CapacitasAnagraficaHistoryImportItemResult(BaseModel):
    subject_id: str | None = None
    resolved_subject_id: str | None = None
    idxana: str | None = None
    status: str
    history_records_total: int = 0
    imported_records: int = 0
    skipped_records: int = 0
    message: str | None = None
    error: str | None = None


class CapacitasAnagraficaHistoryImportResponse(BaseModel):
    items: list[CapacitasAnagraficaHistoryImportItemResult]
    processed: int
    imported: int
    skipped: int
    failed: int
    snapshot_records_imported: int = 0


class CapacitasAnagraficaHistoryImportJobCreateRequest(CapacitasAnagraficaHistoryImportRequest):
    pass


class CapacitasAnagraficaHistoryImportJobOut(BaseModel):
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


class CapacitasIntestatario(BaseModel):
    idxana: str | None = None
    idxesa: str | None = None
    codice_fiscale: str | None = None
    denominazione: str | None = None
    data_nascita: date | None = None
    luogo_nascita: str | None = None
    residenza: str | None = None
    comune_residenza: str | None = None
    cap: str | None = None
    titoli: str | None = None
    deceduto: bool = False


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
    intestatari: list[CapacitasIntestatario] = Field(default_factory=list)
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
    double_speed: bool = False
    parallel_workers: int = Field(default=1, ge=1, le=2)
    throttle_ms: int | None = Field(default=None, ge=0, le=5000)
    auto_resume: bool = False


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


class CapacitasParticelleSyncJobCreateRequest(BaseModel):
    credential_id: int | None = None
    only_due: bool = True
    limit: int | None = Field(default=None, ge=1, le=5000)
    fetch_certificati: bool = True
    fetch_details: bool = True
    double_speed: bool = False
    parallel_workers: int = Field(default=1, ge=1, le=2)
    auto_resume: bool = True


class CapacitasParticelleSyncJobSpeedPatch(BaseModel):
    double_speed: bool


class CapacitasParticelleSyncJobOut(BaseModel):
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


class CapacitasRefetchCertificatiRequest(BaseModel):
    credential_id: int | None = None
    limit: int = Field(default=100, ge=1, le=2000)
    throttle_ms: int = Field(default=300, ge=0, le=5000)


class CapacitasRefetchCertificatiResponse(BaseModel):
    refetched: int
    remaining_empty: int


class CapacitasFrazioneCandidate(BaseModel):
    frazione_id: str
    n_rows: int
    ccos: list[str]
    stati: list[str]


class CapacitasParticellaAnomaliaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    comune_id: str | None
    nome_comune: str | None
    foglio: str
    particella: str
    subalterno: str | None
    anomaly_type: str
    candidates: list[CapacitasFrazioneCandidate]
    capacitas_last_sync_at: datetime | None
    capacitas_last_sync_error: str | None


class CapacitasResolveFragioneRequest(BaseModel):
    frazione_id: str = Field(min_length=1)
    credential_id: int | None = None
    fetch_certificati: bool = True
    fetch_details: bool = False


class CapacitasResolveFragioneResponse(BaseModel):
    ok: bool
    total_rows: int = 0
    imported_certificati: int = 0
    error: str | None = None


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


class CapacitasInCassNoticePdf(BaseModel):
    label: str | None = None
    filename: str | None = None
    url: str


class CapacitasInCassNoticeRow(BaseModel):
    external_row_id: str | None = Field(default=None, alias="ID")
    avviso: str | None = Field(default=None, alias="Avviso")
    reso: str | None = Field(default=None, alias="Reso")
    anno: str | None = Field(default=None, alias="Anno")
    denominazione: str | None = Field(default=None, alias="Denominaz")
    codice_fiscale: str | None = Field(default=None, alias="CodFisc")
    data_pagamento: str | None = Field(default=None, alias="DataPagamento")
    lista_id: str | None = Field(default=None, alias="IDLista")
    lista_descrizione: str | None = Field(default=None, alias="DescrizioneLista")
    indirizzo: str | None = Field(default=None, alias="Indir")
    civico: str | None = Field(default=None, alias="Civ")
    sub_civico: str | None = Field(default=None, alias="SubCiv")
    cap: str | None = Field(default=None, alias="Cap")
    citta: str | None = Field(default=None, alias="Citta")
    provincia: str | None = Field(default=None, alias="Prov")
    carico: str | None = Field(default=None, alias="Carico")
    sgravio: str | None = Field(default=None, alias="Sgravio")
    riscosso: str | None = Field(default=None, alias="Riscosso")
    differenza: str | None = Field(default=None, alias="Differenza")
    riporto: str | None = Field(default=None, alias="Riporto")
    rateizzato: str | None = Field(default=None, alias="Rateizzato")
    annullato: str | None = Field(default=None, alias="Annullato")
    data_scadenza: str | None = Field(default=None, alias="DataScad")
    tipo_anagrafica: str | None = Field(default=None, alias="TipAna")
    ultimo_invio: str | None = Field(default=None, alias="UltimoInvio")
    rimborsi: str | None = Field(default=None, alias="Rimborsi")
    stato_reso: str | None = Field(default=None, alias="StatoReso")
    ico_minuta: str | None = Field(default=None, alias="IcoMinuta")
    stato_pagamento_code: str | None = Field(default=None, alias="StatoPag")
    pag_post_chiu: str | None = Field(default=None, alias="PagPostChiu")
    reg_post_chiu: str | None = Field(default=None, alias="RegPostChiu")
    stato_pagamento_label: str | None = None
    detail_url: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CapacitasInCassSearchResult(BaseModel):
    total: int
    rows: list[CapacitasInCassNoticeRow]


class CapacitasInCassNoticeDetail(BaseModel):
    avviso: str
    detail_url: str
    info_html: str | None = None
    info_text: str | None = None
    pdf_links: list[CapacitasInCassNoticePdf] = Field(default_factory=list)
    raw_html: str | None = None


class CapacitasInCassPartitarioParcel(BaseModel):
    domanda_irrigua: str | None = None
    distretto: str | None = None
    foglio: str
    particella: str
    subalterno: str | None = None
    sup_catastale_are: str | None = None
    sup_catastale_ha: str | None = None
    sup_irrigata_ha: str | None = None
    coltura: str | None = None
    importo_manut_euro: str | None = None
    importo_irrig_euro: str | None = None
    importo_ist_euro: str | None = None


class CapacitasInCassPartitarioPartita(BaseModel):
    codice_partita: str
    comune_nome: str
    contribuente: str | None = None
    contribuente_cf: str | None = None
    co_intestati_raw: str | None = None
    importo_0648_euro: str | None = None
    importo_0985_euro: str | None = None
    importo_0668_euro: str | None = None
    particelle: list[CapacitasInCassPartitarioParcel] = Field(default_factory=list)


class CapacitasInCassPartitarioDetail(BaseModel):
    avviso: str
    info_html: str | None = None
    info_text: str | None = None
    partite: list[CapacitasInCassPartitarioPartita] = Field(default_factory=list)
    raw_html: str | None = None


class CapacitasInCassMailingSubjectRow(CapacitasAspNetDateModel):
    external_id: str | None = Field(default=None, alias="strID")
    denominazione: str | None = Field(default=None, alias="strDenominaz")
    luogo_nascita: str | None = Field(default=None, alias="strLuogoNas")
    provincia_nascita: str | None = Field(default=None, alias="strProvNas")
    data_nascita: datetime | None = Field(default=None, alias="dtDatNas")
    codice_fiscale: str | None = Field(default=None, alias="strCodFisc")
    idx_pers: str | None = Field(default=None, alias="strIDXPers")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasInCassMailingContactRow(CapacitasAspNetDateModel):
    external_id: str | None = Field(default=None, alias="strID")
    subject_external_id: str | None = Field(default=None, alias="strIDRubricaSoggetti")
    active_code: int | None = Field(default=None, alias="intAttivo")
    inserted_at: datetime | None = Field(default=None, alias="dtDataIns")
    email: str | None = Field(default=None, alias="strEmail")
    type: str | None = Field(default=None, alias="strTipo")
    consent_type_code: int | None = Field(default=None, alias="intTipoConsenso")
    consent_type_label: str | None = Field(default=None, alias="strTipoConsensoDesc")
    consent_at: datetime | None = Field(default=None, alias="dtDataConsenso")
    last_send_at: datetime | None = Field(default=None, alias="dtDataUltimoInvio")
    last_send_outcome_code: int | None = Field(default=None, alias="intEsitoUltimoInvio")
    last_send_outcome_label: str | None = Field(default=None, alias="strEsitoUltimoInvioDesc")
    revocation_type_code: int | None = Field(default=None, alias="intTipoRevoca")
    revocation_type_label: str | None = Field(default=None, alias="strTipoRevocaDesc")
    revocation_at: datetime | None = Field(default=None, alias="dtDataRevoca")
    notes: str | None = Field(default=None, alias="strNote")
    protocol: str | None = Field(default=None, alias="strProt")
    protocol_at: datetime | None = Field(default=None, alias="dtDataProt")
    phone: str | None = Field(default=None, alias="strTelefono")
    fax: str | None = Field(default=None, alias="strFax")
    mobile: str | None = Field(default=None, alias="strCellulare")
    inipec_validated_at: datetime | None = Field(default=None, alias="dtDataValidazioneIniPEC")
    origin: str | None = Field(default=None, alias="strOrigine")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasInCassMailingShipmentRow(CapacitasAspNetDateModel):
    external_id: str | None = Field(default=None, alias="strID")
    status_code: int = Field(default=0, alias="intStato")
    send_code: int | None = Field(default=None, alias="intCodiceInvio")
    avviso: str | None = Field(default=None, alias="strAvviso")
    codice_fiscale: str | None = Field(default=None, alias="strCodFisc")
    type: str | None = Field(default=None, alias="strTipo")
    direction_code: int | None = Field(default=None, alias="intDirezione")
    event_at: datetime | None = Field(default=None, alias="dtDataEvento")
    sender: str | None = Field(default=None, alias="strMittente")
    recipient: str | None = Field(default=None, alias="strDestinatario")
    recipient_cc: str | None = Field(default=None, alias="strDestinatarioCC")
    subject: str | None = Field(default=None, alias="strOggetto")
    campaign: str | None = Field(default=None, alias="strAccount")
    status_label: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CapacitasInCassMailingReceiptParent(BaseModel):
    parent_id: str = Field(alias="IDParent")
    group: str | None = Field(default=None, alias="Gruppo")
    account: str | None = Field(default=None, alias="Account")
    date: str | None = Field(default=None, alias="Data")

    model_config = ConfigDict(populate_by_name=True)


class CapacitasObjManDocument(CapacitasAspNetDateModel):
    object_id: str = Field(alias="strID")
    parent_id: str | None = Field(default=None, alias="strMetadataIDParent")
    filename: str | None = Field(default=None, alias="strMetadataFileName")
    group: str | None = Field(default=None, alias="strMetadataGroup")
    extension: str | None = Field(default=None, alias="strMetadataFileTypeExtension")
    size_bytes: int | None = Field(default=None, alias="intMetadataFileSize")
    created_at: datetime | None = Field(default=None, alias="dtMetadataFileDateCreation")
    updated_at: datetime | None = Field(default=None, alias="dtMetadataFileDateLastUpdate")
    raw_json: dict | list | None = None

    model_config = ConfigDict(populate_by_name=True)


class CapacitasInCassMailingData(BaseModel):
    subjects: list[CapacitasInCassMailingSubjectRow] = Field(default_factory=list)
    contacts: list[CapacitasInCassMailingContactRow] = Field(default_factory=list)
    shipments: list[CapacitasInCassMailingShipmentRow] = Field(default_factory=list)
    receipt_parents_by_shipment_id: dict[str, list[CapacitasInCassMailingReceiptParent]] = Field(default_factory=dict)
    receipt_documents_by_parent_id: dict[str, list[CapacitasObjManDocument]] = Field(default_factory=dict)


class CapacitasInCassSyncItem(BaseModel):
    subject_id: UUID
    identifier: str | None = None
    display_name: str | None = None


class CapacitasInCassSyncJobCreateRequest(BaseModel):
    credential_id: int | None = None
    subject_ids: list[UUID] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=1000)
    include_details: bool = True
    include_partitario: bool = True
    include_mailing_list: bool = False
    download_mailing_receipts: bool = False
    continue_on_error: bool = True
    throttle_ms: int = Field(default=250, ge=0, le=5000)


class CapacitasInCassRuoloHarvestRequest(BaseModel):
    credential_id: int | None = None
    anno: int | None = Field(default=None, ge=2000, le=2100)
    chunk_size: int = Field(default=100, ge=1, le=500)
    limit_subjects: int | None = Field(default=None, ge=1, le=50000)
    exclude_synced_subjects: bool = False
    include_details: bool = True
    include_partitario: bool = True
    include_mailing_list: bool = False
    download_mailing_receipts: bool = False
    continue_on_error: bool = True
    throttle_ms: int = Field(default=250, ge=0, le=5000)


class CapacitasInCassRuoloHarvestResponse(BaseModel):
    anno: int | None = None
    chunk_size: int
    total_subjects: int
    total_jobs: int
    job_ids: list[int] = Field(default_factory=list)
    credential_id: int | None = None
    exclude_synced_subjects: bool = False


class CapacitasInCassSyncItemResult(BaseModel):
    subject_id: str
    identifier: str | None = None
    display_name: str | None = None
    status: str
    notices_found: int = 0
    notices_synced: int = 0
    mailing_contacts_synced: int = 0
    mailing_shipments_synced: int = 0
    mailing_receipts_downloaded: int = 0
    error: str | None = None


class CapacitasInCassSyncJobResult(BaseModel):
    items: list[CapacitasInCassSyncItemResult]
    processed_subjects: int
    failed_subjects: int
    notices_found: int
    notices_synced: int
    mailing_contacts_synced: int = 0
    mailing_shipments_synced: int = 0
    mailing_receipts_downloaded: int = 0


class CapacitasInCassSyncJobOut(BaseModel):
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
