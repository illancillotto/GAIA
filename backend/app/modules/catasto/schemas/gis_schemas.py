from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GisFilters(BaseModel):
    comune: int | None = None
    codice_catastale: str | None = None
    foglio: str | None = None
    num_distretto: str | None = None
    solo_anomalie: bool = False


class GisSelectRequest(BaseModel):
    geometry: dict[str, Any] = Field(..., description="GeoJSON Geometry object (Polygon o MultiPolygon)")
    filters: GisFilters | None = None

    @field_validator("geometry")
    @classmethod
    def validate_geometry_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        allowed = {"Polygon", "MultiPolygon"}
        geometry_type = value.get("type")
        if geometry_type not in allowed:
            raise ValueError(f"geometry.type deve essere Polygon o MultiPolygon, ricevuto: {geometry_type}")
        return value


class ParticellaGisSummary(BaseModel):
    id: str
    cfm: str | None = None
    cod_comune_capacitas: int | None = None
    cod_comune_istat: int | None = None
    codice_catastale: str | None = None
    nome_comune: str | None = None
    foglio: str | None = None
    particella: str | None = None
    subalterno: str | None = None
    superficie_mq: float | None = None
    superficie_grafica_mq: float | None = None
    num_distretto: str | None = None
    nome_distretto: str | None = None
    ha_anomalie: bool = False

    model_config = ConfigDict(from_attributes=True)


class FoglioAggr(BaseModel):
    foglio: str
    n_particelle: int
    superficie_ha: float


class DistrettoAggr(BaseModel):
    num_distretto: str
    nome_distretto: str | None = None
    n_particelle: int
    superficie_ha: float


class GisSelectResult(BaseModel):
    n_particelle: int
    superficie_ha: float
    per_foglio: list[FoglioAggr] = Field(default_factory=list)
    per_distretto: list[DistrettoAggr] = Field(default_factory=list)
    particelle: list[ParticellaGisSummary] = Field(default_factory=list)
    truncated: bool = False


class AdeWfsSyncBboxRequest(BaseModel):
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    max_tile_km2: float = Field(default=4.0, gt=0, le=10)
    max_tiles: int = Field(default=25, ge=1, le=100)
    count: int = Field(default=1000, ge=1, le=5000)
    max_pages_per_tile: int = Field(default=20, ge=1, le=50)


class AdeWfsSyncBboxResponse(BaseModel):
    run_id: str
    requested_bbox: dict[str, float]
    tiles: int
    features: int
    upserted: int
    with_geometry: int


class AdeAlignmentReportCounters(BaseModel):
    staged_particelle: int
    allineate: int
    nuove_in_ade: int
    geometrie_variate: int
    match_ambiguo: int
    mancanti_in_ade: int


class AdeAlignmentReportSample(BaseModel):
    category: str
    national_cadastral_reference: str | None = None
    codice_catastale: str | None = None
    foglio: str | None = None
    particella: str | None = None
    particella_id: str | None = None
    distance_m: float | None = None


class AdeAlignmentReportResponse(BaseModel):
    run_id: str
    status: str
    requested_bbox: dict[str, float]
    geometry_threshold_m: float
    started_at: datetime
    completed_at: datetime | None = None
    counters: AdeAlignmentReportCounters
    samples: list[AdeAlignmentReportSample] = Field(default_factory=list)
    geojson: dict[str, Any] | None = None


class AdeAlignmentApplyPreviewRequest(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["nuove_in_ade", "geometrie_variate"])
    geometry_threshold_m: float = Field(default=1.0, gt=0, le=25)


class AdeAlignmentApplyPreviewCounters(BaseModel):
    insert_new: int
    update_geometry: int
    suppress_missing: int
    skipped_ambiguous: int
    skipped_not_selected: int


class AdeAlignmentApplyPreviewImpact(BaseModel):
    affected_particelle: int
    utenze_collegate: int
    consorzio_units_collegate: int
    saved_selection_items: int
    ruolo_particelle_collegate: int


class AdeAlignmentApplyPreviewResponse(BaseModel):
    run_id: str
    status: str = "preview"
    selected_categories: list[str]
    geometry_threshold_m: float
    counters: AdeAlignmentApplyPreviewCounters
    impact: AdeAlignmentApplyPreviewImpact
    warnings: list[str] = Field(default_factory=list)
    samples: list[AdeAlignmentReportSample] = Field(default_factory=list)


class AdeAlignmentApplyRequest(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["nuove_in_ade", "geometrie_variate"])
    geometry_threshold_m: float = Field(default=1.0, gt=0, le=25)
    confirm: bool = Field(default=False, description="Deve essere true per eseguire scritture su cat_particelle.")
    allow_suppress_missing: bool = Field(
        default=False,
        description="Abilita la soppressione delle particelle GAIA mancanti in AdE nello scope bbox.",
    )


class AdeAlignmentApplyCounters(BaseModel):
    inserted_new: int
    updated_geometry: int
    suppressed_missing: int
    skipped_ambiguous: int
    skipped_not_selected: int
    skipped_missing_comune: int


class AdeAlignmentApplyResponse(BaseModel):
    run_id: str
    status: str = "applied"
    selected_categories: list[str]
    geometry_threshold_m: float
    counters: AdeAlignmentApplyCounters
    warnings: list[str] = Field(default_factory=list)


class GisExportFormat(str, Enum):
    geojson = "geojson"
    csv = "csv"


class ParticellaPopupRuoloItem(BaseModel):
    anno_tributario: int
    domanda_irrigua: str | None = None
    subalterno: str | None = None
    coltura: str | None = None
    sup_catastale_ha: float | None = None
    sup_irrigata_ha: float | None = None
    importo_manut_euro: float | None = None
    importo_irrig_euro: float | None = None
    importo_ist_euro: float | None = None
    importo_totale_euro: float | None = None
    codice_partita: str | None = None
    codice_cnc: str | None = None


class ParticellaPopupRuoloSummary(BaseModel):
    anno_tributario_latest: int
    anno_tributario_richiesto: int | None = None
    n_righe: int
    n_subalterni: int
    sup_catastale_ha_totale: float | None = None
    sup_irrigata_ha_totale: float | None = None
    importo_manut_euro_totale: float | None = None
    importo_irrig_euro_totale: float | None = None
    importo_ist_euro_totale: float | None = None
    importo_totale_euro: float | None = None
    items: list[ParticellaPopupRuoloItem] = Field(default_factory=list)


class ParticellaPopupTitolare(BaseModel):
    codice_fiscale: str | None = None
    partita_iva: str | None = None
    denominazione: str | None = None
    titoli: str | None = None
    source: str = "utenza"


class ParticellaPopupData(BaseModel):
    id: str
    cfm: str | None = None
    cod_comune_capacitas: int | None = None
    cod_comune_istat: int | None = None
    codice_catastale: str | None = None
    nome_comune: str | None = None
    foglio: str | None = None
    particella: str | None = None
    subalterno: str | None = None
    superficie_mq: float | None = None
    superficie_grafica_mq: float | None = None
    num_distretto: str | None = None
    nome_distretto: str | None = None
    n_anomalie_aperte: int = 0
    titolare: ParticellaPopupTitolare | None = None
    ha_ruolo: bool = False
    ruolo_summary: ParticellaPopupRuoloSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class GisParticellaRef(BaseModel):
    comune: str | None = Field(
        default=None,
        description="Nome comune oppure cod_comune_capacitas o codice catastale/Belfiore (es. G286)",
    )
    sezione: str | None = Field(default=None, description="Sezione catastale (opzionale)")
    foglio: str | None = Field(default=None, description="Foglio (obbligatorio)")
    particella: str | None = Field(default=None, description="Particella (obbligatorio)")
    sub: str | None = Field(default=None, description="Subalterno (opzionale)")
    row_index: int | None = Field(default=None, description="Indice riga origine (es. da Excel)")


class GisResolveRefsRequest(BaseModel):
    items: list[GisParticellaRef] = Field(..., description="Lista riferimenti particella (comune/sezione/foglio/particella/sub)")
    include_geometry: bool = Field(default=True, description="Se true ritorna GeoJSON FeatureCollection per i match univoci")
    limit: int = Field(default=2000, ge=1, le=10000, description="Massimo righe accettate in input")


class GisResolveItemResult(BaseModel):
    row_index: int | None = None
    comune_input: str | None = None
    sezione_input: str | None = None
    foglio_input: str | None = None
    particella_input: str | None = None
    sub_input: str | None = None
    esito: str
    message: str
    particella_id: str | None = None


class GisResolveRefsResponse(BaseModel):
    processed: int
    found: int
    not_found: int
    multiple: int
    invalid: int
    results: list[GisResolveItemResult] = Field(default_factory=list)
    geojson: dict[str, Any] | None = Field(default=None, description="FeatureCollection con le particelle trovate (se include_geometry)")


class GisSavedSelectionItemInput(BaseModel):
    particella_id: str
    source_row_index: int | None = None
    source_ref: dict[str, Any] | None = None


class GisSavedSelectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    color: str = Field(default="#10B981", min_length=4, max_length=16)
    source_filename: str | None = Field(default=None, max_length=255)
    import_summary: dict[str, Any] | None = None
    items: list[GisSavedSelectionItemInput] = Field(default_factory=list, max_length=10000)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not value.startswith("#") or len(value) not in {4, 7}:
            raise ValueError("color deve essere un esadecimale CSS (#RGB o #RRGGBB)")
        allowed = "0123456789abcdefABCDEF"
        if any(ch not in allowed for ch in value[1:]):
            raise ValueError("color contiene caratteri non esadecimali")
        return value.upper()


class GisSavedSelectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, min_length=4, max_length=16)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return GisSavedSelectionCreate.validate_color(value)


class GisSavedSelectionSummary(BaseModel):
    id: str
    name: str
    color: str
    source_filename: str | None = None
    n_particelle: int
    n_with_geometry: int
    import_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class GisSavedSelectionDetail(GisSavedSelectionSummary):
    geojson: dict[str, Any] | None = None
