from __future__ import annotations

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


class GisExportFormat(str, Enum):
    geojson = "geojson"
    csv = "csv"


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

    model_config = ConfigDict(from_attributes=True)


class GisParticellaRef(BaseModel):
    comune: str | None = Field(default=None, description="Nome comune oppure cod_comune_capacitas (numero in stringa)")
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
