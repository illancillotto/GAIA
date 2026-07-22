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
  comune_nome: string | null;
  comune_codice: string | null;
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
  cat_particella_id: string | null;
  cat_particella_match_status: string | null;
  cat_particella_match_confidence: string | null;
  cat_particella_match_reason: string | null;
  ade_scan_status: string | null;
  ade_scan_classification: string | null;
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

// ── Tributi ──────────────────────────────────────────────────────────────────

export type RuoloTributiPaymentStatus = "unpaid" | "partial" | "paid" | "overpaid" | "to_review";

export type RuoloTributiWorkflowStatus =
  | "moroso"
  | "contestato"
  | "sospeso"
  | "annullato"
  | "non_dovuto"
  | "rateizzato";

export type RuoloTributiPaymentResponse = {
  id: string;
  avviso_id: string;
  import_job_id: string | null;
  codice_cnc_raw: string | null;
  codice_utenza_raw: string | null;
  anno_tributario: number | null;
  paid_at: string | null;
  amount: number;
  payment_reference: string | null;
  payment_method: string | null;
  source: string;
  status: string;
  raw_payload_json: Record<string, unknown> | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export type RuoloTributiPaymentCreateRequest = {
  paid_at?: string | null;
  amount: number;
  payment_reference?: string | null;
  payment_method?: string | null;
  source?: string;
  status?: string;
  raw_payload_json?: Record<string, unknown> | null;
};

export type RuoloTributiNoteResponse = {
  id: string;
  avviso_id: string;
  body: string;
  visibility: string;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export type RuoloTributiNoteCreateRequest = {
  body: string;
  visibility?: string;
};

export type RuoloTributiAvvisoStatusUpdateRequest = {
  workflow_status?: RuoloTributiWorkflowStatus | null;
  capacitas_url?: string | null;
  capacitas_avviso_code?: string | null;
};

export type RuoloTributiAvvisoListItemResponse = {
  id: string;
  codice_cnc: string;
  anno_tributario: number;
  subject_id: string | null;
  codice_fiscale_raw: string | null;
  nominativo_raw: string | null;
  codice_utenza: string | null;
  importo_totale_euro: number | null;
  paid_amount: number;
  saldo_amount: number | null;
  payment_status: RuoloTributiPaymentStatus;
  workflow_status: RuoloTributiWorkflowStatus | null;
  last_payment_at: string | null;
  capacitas_url: string | null;
  capacitas_avviso_code: string | null;
  display_name: string | null;
  is_linked: boolean;
  notes_count: number;
};

export type RuoloTributiAvvisoListResponse = {
  items: RuoloTributiAvvisoListItemResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type RuoloTributiMailingDeliveryResponse = {
  source_notice_id: string | null;
  pec_recipient: string | null;
  delivery_status: string | null;
  delivered_at: string | null;
  accepted_at: string | null;
  receipt_groups: string[];
  receipt_documents_count: number;
};

export type RuoloTributiAvvisoDetailResponse = RuoloTributiAvvisoListItemResponse & {
  domicilio_raw: string | null;
  residenza_raw: string | null;
  importo_totale_0648: number | null;
  importo_totale_0985: number | null;
  importo_totale_0668: number | null;
  mailing_delivery: RuoloTributiMailingDeliveryResponse | null;
  payments: RuoloTributiPaymentResponse[];
  notes: RuoloTributiNoteResponse[];
};

export type RuoloTributiReminderResponse = {
  id: string;
  avviso_id: string;
  template_id: string | null;
  status: string;
  generated_document_path: string | null;
  generated_at: string | null;
  generated_by: number | null;
  payload_json: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  download_url: string | null;
};

export type RuoloTributiReminderCreateRequest = {
  template_id?: string | null;
  notes?: string | null;
};

export type RuoloTributiReminderCandidateAvviso = {
  id: string;
  codice_cnc: string;
  anno_tributario: number;
  importo_totale_euro: number | null;
  paid_amount: number;
  saldo_amount: number | null;
  payment_status: string;
  capacitas_url: string | null;
};

export type RuoloTributiReminderCandidateResponse = {
  codice_fiscale: string;
  display_name: string | null;
  comune: string | null;
  years: number[];
  avvisi_count: number;
  due_amount: number | null;
  paid_amount: number;
  saldo_amount: number | null;
  subject_id: string | null;
  nas_folder_path: string | null;
  has_nas_folder: boolean;
  avvisi: RuoloTributiReminderCandidateAvviso[];
};

export type RuoloTributiReminderCandidateListResponse = {
  items: RuoloTributiReminderCandidateResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type RuoloTributiReminderBatchCreateRequest = {
  title?: string | null;
  codice_fiscale: string[];
  filters?: Record<string, unknown> | null;
  template_path?: string | null;
  notes?: string | null;
};

export type RuoloTributiReminderBatchItemResponse = {
  id: string;
  batch_id: string;
  subject_id: string | null;
  codice_fiscale: string;
  display_name: string | null;
  comune_key: string | null;
  years_json: number[] | null;
  avviso_ids_json: string[] | null;
  due_amount: number | null;
  paid_amount: number;
  saldo_amount: number | null;
  nas_folder_path: string | null;
  generated_document_path: string | null;
  status: string;
  error_detail: string | null;
  payload_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  download_url: string | null;
};

export type RuoloTributiReminderBatchResponse = {
  id: string;
  title: string | null;
  status: string;
  template_path: string | null;
  filters_json: Record<string, unknown> | null;
  items_total: number;
  items_generated: number;
  items_failed: number;
  generated_by: number | null;
  generated_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: RuoloTributiReminderBatchItemResponse[];
};

export type RuoloTributiReminderBatchListResponse = {
  items: RuoloTributiReminderBatchResponse[];
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

export type RuoloParticelleSummaryResponse = {
  anno_tributario: number | null;
  total_particelle: number;
  collegate_catasto: number;
  non_collegate_catasto: number;
  soppresse_ade: number;
};

export type RuoloStatsComuneItem = {
  comune_nome: string;
  anno_tributario: number;
  totale_0648: number | null;
  totale_0985: number | null;
  totale_0668: number | null;
  totale_euro: number | null;
  num_avvisi: number;
  num_partite?: number | null;
  num_particelle?: number | null;
  non_collegate_catasto?: number | null;
};

export type RuoloStatsComuneResponse = {
  anno_tributario: number;
  items: RuoloStatsComuneItem[];
};

export type RuoloStatsAmountBreakdownItem = {
  key: string;
  label: string;
  amount: number;
};

export type RuoloStatsCountBreakdownItem = {
  key: string;
  label: string;
  count: number;
};

export type RuoloStatsAnalyticsResponse = {
  anno_tributario: number;
  particelle_summary: RuoloParticelleSummaryResponse;
  tributi_breakdown: RuoloStatsAmountBreakdownItem[];
  match_status_breakdown: RuoloStatsCountBreakdownItem[];
  match_reason_breakdown: RuoloStatsCountBreakdownItem[];
  distretto_breakdown: RuoloStatsCountBreakdownItem[];
  coltura_breakdown: RuoloStatsCountBreakdownItem[];
  comuni: RuoloStatsComuneItem[];
};

export type RuoloCapacitasCheckStatus =
  | "matched"
  | "amount_mismatch"
  | "only_in_ruolo"
  | "only_in_capacitas";

export type RuoloCapacitasDiagnosis =
  | "allineato"
  | "problema_ruolo"
  | "problema_ricalcolo_gaia"
  | "problema_snapshot_excel";

export type RuoloCapacitasCheckItemResponse = {
  tax_code: string;
  ruolo_display_name: string | null;
  capacitas_display_name: string | null;
  status: RuoloCapacitasCheckStatus;
  diagnosis: RuoloCapacitasDiagnosis;
  ruolo_0648: number;
  gaia_0648: number;
  excel_0648: number;
  delta_0648: number;
  delta_gaia_excel_0648: number;
  ruolo_0985: number;
  gaia_0985: number;
  excel_0985: number;
  delta_0985: number;
  delta_gaia_excel_0985: number;
  ruolo_totale_confrontabile: number;
  gaia_totale_confrontabile: number;
  excel_totale_confrontabile: number;
  delta_totale_confrontabile: number;
  delta_gaia_excel_totale_confrontabile: number;
  anomalous_rows_count: number;
  clean_rows_count: number;
  anomaly_gap_share: number;
  anomaly_driven_case: boolean;
};

export type RuoloCapacitasCheckSummaryResponse = {
  anno_tributario: number;
  ruolo_positions: number;
  capacitas_positions: number;
  capacitas_active_batch_id: string | null;
  matched_positions: number;
  only_in_ruolo: number;
  only_in_capacitas: number;
  ruolo_positions_missing_tax_code: number;
  capacitas_positions_missing_tax_code: number;
  ruolo_totale_0648: number;
  gaia_totale_0648: number;
  excel_totale_0648: number;
  delta_totale_0648: number;
  delta_gaia_excel_totale_0648: number;
  ruolo_totale_0985: number;
  gaia_totale_0985: number;
  excel_totale_0985: number;
  delta_totale_0985: number;
  delta_gaia_excel_totale_0985: number;
  ruolo_totale_0668: number;
  ruolo_totale_confrontabile: number;
  gaia_totale_confrontabile: number;
  excel_totale_confrontabile: number;
  delta_totale_confrontabile: number;
  delta_gaia_excel_totale_confrontabile: number;
  mismatch_positions: number;
  diagnosis_ruolo_count: number;
  diagnosis_gaia_count: number;
  diagnosis_excel_count: number;
};

export type RuoloCapacitasCheckResponse = {
  summary: RuoloCapacitasCheckSummaryResponse;
  items: RuoloCapacitasCheckItemResponse[];
};

export type RuoloCapacitasCheckComuneItemResponse = {
  comune_nome: string;
  source_comuni_ruolo: string[];
  source_comuni_capacitas: string[];
  capacitas_active_batch_id: string | null;
  ruolo_0648: number;
  gaia_0648: number;
  excel_0648: number;
  delta_0648: number;
  delta_gaia_excel_0648: number;
  ruolo_0985: number;
  gaia_0985: number;
  excel_0985: number;
  delta_0985: number;
  delta_gaia_excel_0985: number;
  ruolo_totale_confrontabile: number;
  gaia_totale_confrontabile: number;
  excel_totale_confrontabile: number;
  delta_totale_confrontabile: number;
  delta_gaia_excel_totale_confrontabile: number;
};

export type RuoloCapacitasCheckComuneResponse = {
  anno_tributario: number;
  items: RuoloCapacitasCheckComuneItemResponse[];
};

export type RuoloCapacitasCalculationComuneSummaryResponse = {
  comune_nome: string;
  rows_count: number;
  anomalous_rows_count: number;
  total_sup_irrigabile_mq: number;
  total_imponibile_sf: number;
  ruolo_0648: number;
  ruolo_0985: number;
  ruolo_total: number;
  ruolo_matched_rows_count: number;
  gaia_0648: number;
  gaia_0985: number;
  gaia_total: number;
  excel_0648: number;
  excel_0985: number;
  excel_total: number;
  gap_excel_gaia_total: number;
  delta_ruolo_gaia_total: number;
  delta_ruolo_excel_total: number;
};

export type RuoloCapacitasCalculationRowResponse = {
  source_filename: string | null;
  source_row_number: number | null;
  cco: string | null;
  cod_provincia: number | null;
  cod_comune_capacitas: number | null;
  cod_frazione: number | null;
  num_distretto: number | null;
  nome_distretto_loc: string | null;
  comune_nome: string | null;
  sezione_catastale: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  sup_catastale_mq: number | null;
  sup_irrigabile_mq: number;
  ind_spese_fisse: number | null;
  imponibile_sf: number;
  imponibile_per_mq: number | null;
  esente_0648: boolean;
  aliquota_0648: number | null;
  aliquota_0985: number | null;
  excel_0648: number;
  excel_0985: number;
  excel_total: number;
  gaia_0648: number;
  gaia_0985: number;
  gaia_total: number;
  gap_excel_gaia_total: number;
  ruolo_match_found: boolean;
  ruolo_match_level: string;
  ruolo_partite_count: number;
  ruolo_comuni: string[];
  ruolo_0648: number;
  ruolo_0985: number;
  ruolo_total: number;
  delta_ruolo_gaia_total: number;
  delta_ruolo_excel_total: number;
  codice_fiscale_raw: string | null;
  anomalia_imponibile: boolean;
  anomalia_importi: boolean;
  anomalia_superficie: boolean;
  anomalia_cf_invalido: boolean;
  anomalia_cf_mancante: boolean;
  anomalia_comune_invalido: boolean;
  anomalia_particella_assente: boolean;
};

export type RuoloCapacitasCalculationSummaryResponse = {
  anno_tributario: number;
  tax_code: string;
  display_name: string | null;
  active_batch_id: string | null;
  source_filename: string | null;
  ruolo_avviso_id: string | null;
  codice_cnc: string | null;
  capacitas_url: string | null;
  capacitas_avviso_code: string | null;
  capacitas_link_source: string | null;
  rows_count: number;
  anomalous_rows_count: number;
  clean_rows_count: number;
  total_sup_irrigabile_mq: number;
  total_imponibile_sf: number;
  gaia_total: number;
  excel_total: number;
  gap_excel_gaia_total: number;
  gaia_total_anomalous_rows: number;
  excel_total_anomalous_rows: number;
  gaia_total_clean_rows: number;
  excel_total_clean_rows: number;
  distinct_ind_spese_fisse: number[];
  distinct_imponibile_per_mq: number[];
};

export type RuoloCapacitasCalculationDetailResponse = {
  summary: RuoloCapacitasCalculationSummaryResponse;
  comuni: RuoloCapacitasCalculationComuneSummaryResponse[];
  rows: RuoloCapacitasCalculationRowResponse[];
};

export type RuoloGaiaCalculationItemResponse = {
  tax_code: string;
  display_name: string | null;
  ruolo_display_name: string | null;
  status: RuoloCapacitasCheckStatus;
  diagnosis: RuoloCapacitasDiagnosis;
  comuni_count: number;
  rows_count: number;
  anomalous_rows_count: number;
  clean_rows_count: number;
  total_sup_irrigabile_mq: number;
  total_imponibile_sf: number;
  ruolo_0648: number;
  gaia_0648: number;
  ruolo_0985: number;
  gaia_0985: number;
  ruolo_totale_confrontabile: number;
  gaia_total: number;
  excel_0648: number;
  excel_0985: number;
  excel_total: number;
  delta_ruolo_gaia_totale: number;
  gap_excel_gaia_total: number;
  anomaly_gap_share: number;
  anomaly_driven_case: boolean;
};

export type RuoloGaiaCalculationSummaryResponse = {
  anno_tributario: number;
  active_batch_id: string | null;
  positions: number;
  ruolo_positions: number;
  positions_missing_tax_code: number;
  ruolo_positions_missing_tax_code: number;
  anomalous_positions: number;
  anomaly_driven_positions: number;
  total_rows: number;
  anomalous_rows: number;
  clean_rows: number;
  total_sup_irrigabile_mq: number;
  total_imponibile_sf: number;
  ruolo_totale_0648: number;
  gaia_totale_0648: number;
  ruolo_totale_0985: number;
  gaia_totale_0985: number;
  ruolo_totale_0668: number;
  ruolo_totale_confrontabile: number;
  gaia_totale_confrontabile: number;
  excel_totale_0648: number;
  excel_totale_0985: number;
  excel_totale_confrontabile: number;
  delta_ruolo_gaia_totale: number;
  gap_excel_gaia_totale: number;
  mismatch_positions: number;
  diagnosis_ruolo_count: number;
  diagnosis_gaia_count: number;
  diagnosis_excel_count: number;
};

export type RuoloGaiaCalculationResponse = {
  summary: RuoloGaiaCalculationSummaryResponse;
  items: RuoloGaiaCalculationItemResponse[];
};
