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
