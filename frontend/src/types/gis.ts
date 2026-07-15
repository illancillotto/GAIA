export type GisCatalogAccessLevel = "viewer" | "annotator" | "editor" | "approver" | "admin";
export type GisCatalogAnnotationStatus = "open" | "in_review" | "closed" | "rejected";
export type GisCatalogChangeRequestStatus = "submitted" | "needs_changes" | "approved" | "rejected" | "applied";
export type GisCatalogChangeRequestType = "attribute_update" | "geometry_update" | "feature_create" | "feature_delete";
export type GisCatalogHealthStatus = "ok" | "warning" | "critical";
export type GisCatalogHealthSeverity = "warning" | "critical";
export type GisShapefileImportStatus = "uploaded" | "validated" | "rejected" | "published" | "failed";

export interface GisCatalogLayer {
  id: string;
  workspace: string;
  name: string;
  title: string;
  description?: string | null;
  domain_module?: string | null;
  source_type: string;
  official_source: string;
  postgis_schema?: string | null;
  postgis_table?: string | null;
  geometry_column?: string | null;
  geometry_type?: string | null;
  srid?: number | null;
  feature_id_column?: string | null;
  martin_layer_id?: string | null;
  ogc_service_url?: string | null;
  qgis_project_path?: string | null;
  nas_export_root?: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
  effective_access_level: GisCatalogAccessLevel;
  can_view: boolean;
  can_annotate: boolean;
  can_edit: boolean;
  can_approve: boolean;
  can_manage: boolean;
  created_at: string;
  updated_at: string;
}

export interface GisCatalogLayerListResponse {
  items: GisCatalogLayer[];
  total: number;
}

export interface GisCatalogWorkspaceSummary {
  workspace: string;
  total_layers: number;
  active_layers: number;
  inactive_layers: number;
  postgis_layers: number;
  domain_registry_layers: number;
  qgis_publishable_layers: number;
  exportable_layers: number;
  issue_count: number;
  health_status: GisCatalogHealthStatus;
}

export interface GisCatalogHealthIssue {
  layer_id: string;
  workspace: string;
  layer_name: string;
  severity: GisCatalogHealthSeverity;
  code: string;
  message: string;
}

export interface GisCatalogLatestExport {
  layer_id: string;
  workspace: string;
  layer_name: string;
  version_label: string;
  status: string;
  nas_path: string;
  trigger?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface GisCatalogDashboardResponse {
  generated_at: string;
  total_layers: number;
  active_layers: number;
  inactive_layers: number;
  workspace_count: number;
  source_type_counts: Record<string, number>;
  official_source_counts: Record<string, number>;
  qgis_publishable_layers: number;
  exportable_layers: number;
  health_status: GisCatalogHealthStatus;
  issues: GisCatalogHealthIssue[];
  latest_exports: GisCatalogLatestExport[];
  workspaces: GisCatalogWorkspaceSummary[];
}

export interface GisOgcPocLayer {
  layer_id: string;
  workspace: string;
  layer_name: string;
  title: string;
  service_layer_name: string;
  source_table: string;
  geometry_type?: string | null;
  srid?: number | null;
  wms_enabled: boolean;
  wfs_enabled: boolean;
  wfs_transactional: boolean;
}

export interface GisOgcPocResponse {
  mode: "read_only_poc";
  recommended_server: "qgis_server";
  proxy_path: string;
  auth_policy: string;
  qgis_project_endpoint: string;
  publishable_layer_count: number;
  layers: GisOgcPocLayer[];
  warnings: string[];
  config_snippets: Record<string, string>;
}

export interface GisShapefileImport {
  id: string;
  status: GisShapefileImportStatus;
  original_filename: string;
  workspace: string;
  domain_module?: string | null;
  target_layer_name: string;
  target_layer_title: string;
  official_source: string;
  source_srid: number;
  encoding: string;
  staging_schema?: string | null;
  staging_table: string;
  feature_count: number;
  geometry_type?: string | null;
  bbox?: number[] | null;
  fields: Array<Record<string, unknown>>;
  validation_report: Record<string, unknown>;
  metadata: Record<string, unknown>;
  checksum_sha256: string;
  uploaded_by_user_id?: number | null;
  published_layer_id?: string | null;
  validated_at?: string | null;
  rejected_at?: string | null;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GisShapefileImportPreviewFeature {
  feature_seq: number;
  attributes: Record<string, unknown>;
  geometry?: Record<string, unknown> | null;
  geometry_type?: string | null;
  source_srid: number;
}

export interface GisShapefileImportPreview {
  import_id: string;
  status: GisShapefileImportStatus;
  staging_schema?: string | null;
  staging_table: string;
  feature_count: number;
  returned_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
  fields: Array<Record<string, unknown>>;
  bbox?: number[] | null;
  features: GisShapefileImportPreviewFeature[];
}

export interface GisShapefileImportChangeRequestInput {
  targetLayerId: string;
  justification?: string;
  limit?: number;
  offset?: number;
}

export interface GisShapefileImportChangeRequestResponse {
  import_id: string;
  target_layer_id: string;
  created_count: number;
  existing_count: number;
  returned_count: number;
  skipped_count: number;
  total_features: number;
  limit: number;
  offset: number;
  has_more: boolean;
  change_requests: GisCatalogChangeRequest[];
}

export interface GisShapefileImportCreateInput {
  file: File;
  workspace: string;
  targetLayerName: string;
  targetLayerTitle: string;
  sourceSrid: number;
  domainModule?: string;
  officialSource?: string;
  encoding?: string;
}

export interface GisCatalogLayerPermission {
  id: string;
  layer_id: string;
  principal_type: "role" | "user" | string;
  principal_key: string;
  access_level: GisCatalogAccessLevel;
  can_view: boolean;
  can_annotate: boolean;
  can_edit: boolean;
  can_approve: boolean;
  can_manage: boolean;
  created_at: string;
  updated_at: string;
}

export interface GisCatalogLayerPermissionUpsertInput {
  principalType: "role" | "user";
  principalKey: string;
  accessLevel: GisCatalogAccessLevel;
}

export interface GisCatalogAnnotation {
  id: string;
  layer_id: string;
  feature_id?: string | null;
  title: string;
  body: string;
  geometry?: Record<string, unknown> | null;
  attachment_refs: Array<Record<string, unknown>>;
  status: GisCatalogAnnotationStatus;
  created_by_user_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface GisCatalogAnnotationFilters {
  status?: GisCatalogAnnotationStatus;
  featureId?: string;
}

export interface GisCatalogAnnotationSaveInput {
  featureId?: string;
  title: string;
  body: string;
  geometry?: Record<string, unknown> | null;
  attachmentRefs?: Array<Record<string, unknown>>;
}

export interface GisCatalogAnnotationUpdateInput {
  title?: string;
  body?: string;
  geometry?: Record<string, unknown> | null;
  attachmentRefs?: Array<Record<string, unknown>>;
}

export interface GisCatalogChangeRequest {
  id: string;
  layer_id: string;
  feature_id?: string | null;
  change_type: GisCatalogChangeRequestType;
  status: GisCatalogChangeRequestStatus;
  payload: Record<string, unknown>;
  justification?: string | null;
  requested_by_user_id?: number | null;
  reviewed_by_user_id?: number | null;
  review_notes?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GisCatalogChangeRequestFilters {
  status?: GisCatalogChangeRequestStatus;
  layerId?: string;
}

export interface GisCatalogChangeRequestSaveInput {
  featureId?: string;
  changeType: GisCatalogChangeRequestType;
  payload: Record<string, unknown>;
  justification?: string;
}

export interface GisCatalogChangeRequestUpdateInput {
  featureId?: string;
  changeType?: GisCatalogChangeRequestType;
  payload?: Record<string, unknown>;
  justification?: string;
}

export interface GisCatalogLayerFilters {
  workspace?: string;
  domainModule?: string;
  sourceType?: string;
  officialSource?: string;
  isActive?: boolean;
}

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
  ha_ruolo?: boolean;
  ha_ruolo_inferito?: boolean;
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

export type GisSearchMode = "auto" | "particella" | "codice_fiscale" | "denominazione";

export interface GisSearchRequest {
  query: string;
  mode?: GisSearchMode;
  limit?: number;
}

export interface GisSearchResultItem extends ParticellaGisSummary {
  match_source: GisSearchMode | string;
  match_value?: string | null;
}

export interface GisSearchResponse {
  query: string;
  mode_requested: GisSearchMode;
  mode_resolved: GisSearchMode;
  total: number;
  results: GisSearchResultItem[];
  geojson?: GeoJSON.FeatureCollection | null;
}

export interface DuiLayerStats {
  total_polygons: number;
  in_ruolo_2025: number;
  not_in_ruolo_2025: number;
  with_contatore: number;
  without_contatore: number;
  with_telerilev: number;
}

export type Dui2026LayerStats = DuiLayerStats;

export interface DuiLayerResponse {
  label: string;
  year?: number | null;
  source_path: string;
  source_filename: string;
  source_date: string;
  source_updated_at: string;
  tile_layer?: string | null;
  rendering_mode: "martin_tiles" | "geojson_fallback" | string;
  stats: DuiLayerStats;
  geojson: GeoJSON.FeatureCollection;
}

export type Dui2026LayerResponse = DuiLayerResponse;

export interface DuiDomandaDetailResponse {
  domanda_irrigua: string;
  year?: number | null;
  codice_fiscale?: string | null;
  intestatario?: string | null;
  telefono?: string | null;
  coltura?: string | null;
  tipo_domanda?: string | null;
  data_domanda?: string | null;
  contatore?: string | null;
  telerilev?: string | null;
  operatore?: string | null;
  sup_grafica_mq_totale?: number | null;
  n_poligoni: number;
  x?: number | null;
  y?: number | null;
  in_ruolo_2025: boolean;
  ruolo_2025_match_count: number;
  ruolo_summary?: ParticellaPopupRuoloSummary | null;
  source_filename: string;
  source_date: string;
}

export type Dui2026DomandaDetailResponse = DuiDomandaDetailResponse;

export interface GisOverlayFeatureClick {
  layer_key: string;
  layer_name?: string | null;
  properties: Record<string, unknown>;
  geometry?: GeoJSON.Geometry | null;
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
  status: string;
  progress_phase: string;
  progress_message?: string | null;
  requested_bbox: Record<string, number>;
  tiles: number;
  tiles_completed: number;
  progress_percent: number;
  features: number;
  upserted: number;
  with_geometry: number;
}

export interface AdeWfsRunStatusResponse {
  run_id: string;
  status: string;
  progress_phase: string;
  progress_message?: string | null;
  requested_bbox: Record<string, number>;
  tiles: number;
  tiles_completed: number;
  progress_percent: number;
  features: number;
  upserted: number;
  with_geometry: number;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
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
  source_type?: string | null;
  is_current: boolean;
  suppressed: boolean;
  num_distretto?: string | null;
  nome_distretto?: string | null;
  missing_fields: string[];
  n_anomalie_aperte: number;
  titolare?: ParticellaPopupTitolare | null;
  ha_ruolo: boolean;
  ha_ruolo_inferito: boolean;
  ruolo_summary?: ParticellaPopupRuoloSummary | null;
  swapped_capacitas?: ParticellaPopupSwappedCapacitas | null;
  anomalie_aperte: ParticellaPopupAnomalia[];
}

export interface DeliveryPointPopupData {
  id: string;
  distretto_code: string;
  punto_consegna_code: string;
  tipologia?: string | null;
  tipo?: string | null;
  cod_cont?: string | null;
  photo_ref?: string | null;
  has_meter: boolean;
  source_dataset: string;
  source_file?: string | null;
  source_updated_at?: string | null;
  source_x?: number | null;
  source_y?: number | null;
  linked_meter_readings_count: number;
  source_payload_json?: Record<string, unknown> | null;
}

export interface ParticellaPopupAnomalia {
  id: string;
  anno_campagna?: number | null;
  tipo: string;
  severita: string;
  descrizione?: string | null;
  dati_json?: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

export interface ParticellaPopupSwappedCapacitas {
  source_codice_catastale?: string | null;
  source_comune_nome?: string | null;
  source_foglio?: string | null;
  source_particella?: string | null;
  source_subalterno?: string | null;
  anno_tributario_latest?: number | null;
  match_confidence?: string | null;
  match_reason?: string | null;
  n_righe_ruolo: number;
}

export interface ParticellaPopupTitolare {
  subject_id?: string | null;
  subject_display_name?: string | null;
  cco?: string | null;
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
  source_mode?: string;
  source_note?: string | null;
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
  outlineColor?: string;
  pulse?: boolean;
  pulseUntil?: number;
  opacity?: number;
  outlineOpacity?: number;
  outlineWidth?: number;
  showFill?: boolean;
  showCentroids?: boolean;
  visible: boolean;
  source_filename?: string | null;
  geojson?: GeoJSON.FeatureCollection | null;
}
