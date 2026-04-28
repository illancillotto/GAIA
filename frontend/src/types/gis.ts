export interface GisFilters {
  comune?: number;
  codice_catastale?: string;
  foglio?: string;
  num_distretto?: string;
  solo_anomalie?: boolean;
}

export interface GisSelectRequest {
  geometry: GeoJSON.Geometry;
  filters?: GisFilters;
}

export interface ParticellaGisSummary {
  id: string;
  cfm?: string | null;
  cod_comune_capacitas?: number | null;
  cod_comune_istat?: number | null;
  codice_catastale?: string | null;
  nome_comune?: string | null;
  foglio?: string | null;
  particella?: string | null;
  subalterno?: string | null;
  superficie_mq?: number | null;
  superficie_grafica_mq?: number | null;
  num_distretto?: string | null;
  nome_distretto?: string | null;
  utenza_cf?: string | null;
  utenza_denominazione?: string | null;
  ha_anomalie: boolean;
}

export interface FoglioAggr {
  foglio: string;
  n_particelle: number;
  superficie_ha: number;
}

export interface DistrettoAggr {
  num_distretto: string;
  nome_distretto?: string | null;
  n_particelle: number;
  superficie_ha: number;
}

export interface GisSelectResult {
  n_particelle: number;
  superficie_ha: number;
  per_foglio: FoglioAggr[];
  per_distretto: DistrettoAggr[];
  particelle: ParticellaGisSummary[];
  truncated: boolean;
}

export interface ParticellaPopupData {
  id: string;
  cfm?: string | null;
  cod_comune_capacitas?: number | null;
  cod_comune_istat?: number | null;
  codice_catastale?: string | null;
  nome_comune?: string | null;
  foglio?: string | null;
  particella?: string | null;
  subalterno?: string | null;
  superficie_mq?: number | null;
  superficie_grafica_mq?: number | null;
  num_distretto?: string | null;
  nome_distretto?: string | null;
  n_anomalie_aperte: number;
}

export interface GisParticellaRef {
  comune?: string | null;
  sezione?: string | null;
  foglio?: string | null;
  particella?: string | null;
  sub?: string | null;
  row_index?: number | null;
}

export interface GisResolveItemResult {
  row_index?: number | null;
  comune_input?: string | null;
  sezione_input?: string | null;
  foglio_input?: string | null;
  particella_input?: string | null;
  sub_input?: string | null;
  esito: "FOUND" | "NOT_FOUND" | "MULTIPLE_MATCHES" | "INVALID_ROW" | string;
  message: string;
  particella_id?: string | null;
}

export interface GisResolveRefsResponse {
  processed: number;
  found: number;
  not_found: number;
  multiple: number;
  invalid: number;
  results: GisResolveItemResult[];
  geojson?: GeoJSON.FeatureCollection | null;
}
