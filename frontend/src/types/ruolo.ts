// ── Import Jobs ──────────────────────────────────────────────────────────────

export type RuoloImportJobStatus = "pending" | "running" | "completed" | "failed";

export type RuoloImportJobReportItem = {
  codice_cnc: string | null;
  codice_fiscale_raw: string | null;
  nominativo_raw: string | null;
  reason_code: string;
  reason_label: string;
};

export type RuoloImportJobReportSummary = {
  filename: string;
  anno_tributario: number;
  total_partite: number;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
};

export type RuoloImportJobReportPreview = {
  skipped_items: RuoloImportJobReportItem[];
  error_items: RuoloImportJobReportItem[];
  skipped_preview_count: number;
  error_preview_count: number;
  skipped_total_count: number;
  error_total_count: number;
};

export type RuoloImportJobParams = {
  report_summary?: RuoloImportJobReportSummary;
  report_preview?: RuoloImportJobReportPreview;
} & Record<string, unknown>;

export type RuoloImportJobResponse = {
  id: string;
  anno_tributario: number;
  filename: string | null;
  status: RuoloImportJobStatus;
  started_at: string;
  finished_at: string | null;
  total_partite: number | null;
  records_imported: number | null;
  records_skipped: number | null;
  records_errors: number | null;
  error_detail: string | null;
  triggered_by: number | null;
  params_json: RuoloImportJobParams | null;
  created_at: string;
};

export type RuoloImportJobListResponse = {
  items: RuoloImportJobResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type RuoloImportUploadResponse = {
  job_id: string;
  status: RuoloImportJobStatus;
  anno_tributario: number;
  warning_existing: boolean;
  existing_count: number;
};

export type RuoloImportYearDetectionResponse = {
  detected_year: number | null;
};

// ── Avvisi ────────────────────────────────────────────────────────────────────

export type RuoloAvvisoListItemResponse = {
  id: string;
  codice_cnc: string;
  anno_tributario: number;
  subject_id: string | null;
  codice_fiscale_raw: string | null;
  nominativo_raw: string | null;
  codice_utenza: string | null;
  importo_totale_0648: number | null;
  importo_totale_0985: number | null;
  importo_totale_0668: number | null;
  importo_totale_euro: number | null;
  display_name: string | null;
  is_linked: boolean;
  created_at: string;
  updated_at: string;
};

export type RuoloParticellaResponse = {
  id: string;
  partita_id: string;
  anno_tributario: number;
  domanda_irrigua: string | null;
  distretto: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  sup_catastale_are: number | null;
  sup_catastale_ha: number | null;
  sup_irrigata_ha: number | null;
  coltura: string | null;
  importo_manut: number | null;
  importo_irrig: number | null;
  importo_ist: number | null;
  catasto_parcel_id: string | null;
  created_at: string;
};

export type RuoloPartitaResponse = {
  id: string;
  avviso_id: string;
  codice_partita: string | null;
  comune_nome: string | null;
  comune_codice: string | null;
  contribuente_cf: string | null;
  co_intestati_raw: string | null;
  importo_0648: number | null;
  importo_0985: number | null;
  importo_0668: number | null;
  particelle: RuoloParticellaResponse[];
  created_at: string;
};

export type RuoloAvvisoDetailResponse = {
  id: string;
  import_job_id: string;
  codice_cnc: string;
  anno_tributario: number;
  subject_id: string | null;
  codice_fiscale_raw: string | null;
  nominativo_raw: string | null;
  domicilio_raw: string | null;
  residenza_raw: string | null;
  n2_extra_raw: string | null;
  codice_utenza: string | null;
  importo_totale_0648: number | null;
  importo_totale_0985: number | null;
  importo_totale_0668: number | null;
  importo_totale_euro: number | null;
  importo_totale_lire: number | null;
  n4_campo_sconosciuto: string | null;
  partite: RuoloPartitaResponse[];
  display_name: string | null;
  created_at: string;
  updated_at: string;
};

export type RuoloAvvisoListResponse = {
  items: RuoloAvvisoListItemResponse[];
  total: number;
  page: number;
  page_size: number;
};

// ── Stats ─────────────────────────────────────────────────────────────────────

export type RuoloStatsByAnnoResponse = {
  anno_tributario: number;
  total_avvisi: number;
  avvisi_collegati: number;
  avvisi_non_collegati: number;
  totale_0648: number | null;
  totale_0985: number | null;
  totale_0668: number | null;
  totale_euro: number | null;
};

export type RuoloStatsResponse = {
  items: RuoloStatsByAnnoResponse[];
};

export type RuoloStatsComuneItem = {
  comune_nome: string;
  anno_tributario: number;
  totale_0648: number | null;
  totale_0985: number | null;
  totale_0668: number | null;
  totale_euro: number | null;
  num_avvisi: number;
};

export type RuoloStatsComuneResponse = {
  anno_tributario: number;
  items: RuoloStatsComuneItem[];
};
