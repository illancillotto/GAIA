export interface GisFilters {
  comune?: number;
  codice_catastale?: string;
  foglio?: string;
  num_distretto?: string;
  solo_anomalie?: boolean;
}

export type GisBasemap = "osm" | "satellite" | "google_satellite";

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

export interface AdeWfsSyncBboxRequest {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
  max_tile_km2?: number;
  max_tiles?: number;
  count?: number;
  max_pages_per_tile?: number;
}

export interface AdeWfsSyncBboxResponse {
  run_id: string;
  requested_bbox: Record<string, number>;
  tiles: number;
  features: number;
  upserted: number;
  with_geometry: number;
}

export interface AdeAlignmentReportCounters {
  staged_particelle: number;
  allineate: number;
  nuove_in_ade: number;
  geometrie_variate: number;
  match_ambiguo: number;
  mancanti_in_ade: number;
}

export interface AdeAlignmentReportSample {
  category: string;
  national_cadastral_reference?: string | null;
  codice_catastale?: string | null;
  foglio?: string | null;
  particella?: string | null;
  particella_id?: string | null;
  distance_m?: number | null;
}

export interface AdeAlignmentReportResponse {
  run_id: string;
  status: string;
  requested_bbox: Record<string, number>;
  geometry_threshold_m: number;
  started_at: string;
  completed_at?: string | null;
  counters: AdeAlignmentReportCounters;
  samples: AdeAlignmentReportSample[];
  geojson?: GeoJSON.FeatureCollection | null;
}

export interface AdeAlignmentApplyPreviewRequest {
  categories: string[];
  geometry_threshold_m?: number;
}

export interface AdeAlignmentApplyPreviewCounters {
  insert_new: number;
  update_geometry: number;
  suppress_missing: number;
  skipped_ambiguous: number;
  skipped_not_selected: number;
}

export interface AdeAlignmentApplyPreviewImpact {
  affected_particelle: number;
  utenze_collegate: number;
  consorzio_units_collegate: number;
  saved_selection_items: number;
  ruolo_particelle_collegate: number;
}

export interface AdeAlignmentApplyPreviewResponse {
  run_id: string;
  status: string;
  selected_categories: string[];
  geometry_threshold_m: number;
  counters: AdeAlignmentApplyPreviewCounters;
  impact: AdeAlignmentApplyPreviewImpact;
  warnings: string[];
  samples: AdeAlignmentReportSample[];
}

export interface AdeAlignmentApplyRequest {
  categories: string[];
  geometry_threshold_m?: number;
  confirm: boolean;
  allow_suppress_missing?: boolean;
}

export interface AdeAlignmentApplyCounters {
  inserted_new: number;
  updated_geometry: number;
  suppressed_missing: number;
  skipped_ambiguous: number;
  skipped_not_selected: number;
  skipped_missing_comune: number;
}

export interface AdeAlignmentApplyResponse {
  run_id: string;
  status: string;
  selected_categories: string[];
  geometry_threshold_m: number;
  counters: AdeAlignmentApplyCounters;
  warnings: string[];
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
  titolare?: ParticellaPopupTitolare | null;
  ha_ruolo: boolean;
  ruolo_summary?: ParticellaPopupRuoloSummary | null;
}

export interface ParticellaPopupTitolare {
  codice_fiscale?: string | null;
  partita_iva?: string | null;
  denominazione?: string | null;
  titoli?: string | null;
  source: "intestatario" | "utenza" | string;
}

export interface ParticellaPopupRuoloItem {
  anno_tributario: number;
  domanda_irrigua?: string | null;
  subalterno?: string | null;
  coltura?: string | null;
  sup_catastale_ha?: number | null;
  sup_irrigata_ha?: number | null;
  importo_manut_euro?: number | null;
  importo_irrig_euro?: number | null;
  importo_ist_euro?: number | null;
  importo_totale_euro?: number | null;
  codice_partita?: string | null;
  codice_cnc?: string | null;
}

export interface ParticellaPopupRuoloSummary {
  anno_tributario_latest: number;
  anno_tributario_richiesto?: number | null;
  n_righe: number;
  n_subalterni: number;
  sup_catastale_ha_totale?: number | null;
  sup_irrigata_ha_totale?: number | null;
  importo_manut_euro_totale?: number | null;
  importo_irrig_euro_totale?: number | null;
  importo_ist_euro_totale?: number | null;
  importo_totale_euro?: number | null;
  items: ParticellaPopupRuoloItem[];
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

export interface GisSavedSelectionItemInput {
  particella_id: string;
  source_row_index?: number | null;
  source_ref?: Record<string, unknown> | null;
}

export interface GisSavedSelectionCreate {
  name: string;
  color: string;
  source_filename?: string | null;
  import_summary?: Record<string, unknown> | null;
  items: GisSavedSelectionItemInput[];
}

export interface GisSavedSelectionUpdate {
  name?: string;
  color?: string;
}

export interface GisSavedSelectionSummary {
  id: string;
  name: string;
  color: string;
  source_filename?: string | null;
  n_particelle: number;
  n_with_geometry: number;
  import_summary?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface GisSavedSelectionDetail extends GisSavedSelectionSummary {
  geojson?: GeoJSON.FeatureCollection | null;
}

export interface GisMapOverlayLayer {
  layer_key: string;
  saved_selection_id?: string | null;
  name: string;
  color: string;
  opacity?: number;
  showFill?: boolean;
  visible: boolean;
  source_filename?: string | null;
  geojson?: GeoJSON.FeatureCollection | null;
}
