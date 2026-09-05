export type AnagraficaStats = {
  total_subjects: number;
  total_persons: number;
  total_companies: number;
  total_unknown: number;
  total_documents: number;
  requires_review: number;
  active_subjects: number;
  inactive_subjects: number;
  documents_unclassified: number;
  deceased_updates_last_24h: number;
  deceased_updates_current_month: number;
  deceased_updates_current_year: number;
  by_letter: Record<string, number>;
};

export type UtenzeStats = AnagraficaStats;

export type AnagraficaDocumentSummaryBucket = {
  doc_type: string;
  count: number;
};

export type UtenzeDocumentSummaryBucket = AnagraficaDocumentSummaryBucket;

export type AnagraficaDocumentSummaryItem = {
  document_id: string;
  subject_id: string;
  subject_display_name: string;
  filename: string;
  doc_type: string;
  classification_source: string;
  created_at: string;
};

export type UtenzeDocumentSummaryItem = AnagraficaDocumentSummaryItem;

export type AnagraficaDocumentSummary = {
  total_documents: number;
  documents_unclassified: number;
  classified_documents: number;
  by_doc_type: AnagraficaDocumentSummaryBucket[];
  recent_unclassified: AnagraficaDocumentSummaryItem[];
};

export type UtenzeDocumentSummary = AnagraficaDocumentSummary;

export type AnagraficaDocument = {
  id: string | null;
  filename: string;
  relative_path: string;
  nas_path: string;
  extension: string | null;
  is_pdf: boolean;
  doc_type: string;
  classification_source: string;
  smart_category: string;
  smart_category_label: string;
  smart_priority: number;
  smart_confidence: number;
  smart_reason: string | null;
  content_classification_status: string;
  content_category: string | null;
  content_category_label: string | null;
  content_confidence: number | null;
  content_reason: string | null;
  content_excerpt: string | null;
  content_classification_source: string | null;
  content_classified_at: string | null;
  content_classification_error: string | null;
  warnings: string[];
};

export type UtenzeDocument = AnagraficaDocument;

export type AnagraficaAuditLog = {
  id: string;
  subject_id: string;
  changed_by_user_id: number | null;
  action: string;
  diff_json: Record<string, unknown> | unknown[] | null;
  changed_at: string;
};

export type UtenzeAuditLog = AnagraficaAuditLog;

export type AnagraficaCatastoDocument = {
  id: string;
  request_id: string | null;
  comune: string;
  foglio: string;
  particella: string;
  subalterno: string | null;
  catasto: string;
  tipo_visura: string;
  filename: string;
  codice_fiscale: string | null;
  created_at: string;
};

export type UtenzeCatastoDocument = AnagraficaCatastoDocument;

export type AnagraficaPerson = {
  subject_id: string;
  cognome: string;
  nome: string;
  codice_fiscale: string;
  anpr_id: string | null;
  stato_anpr: "alive" | "deceased" | "not_found_anpr" | "cancelled_anpr" | "error" | "unknown" | null;
  data_decesso: string | null;
  luogo_decesso_comune: string | null;
  last_anpr_check_at: string | null;
  last_c030_check_at: string | null;
  capacitas_deceduto?: boolean | null;
  capacitas_last_check_at?: string | null;
  data_nascita: string | null;
  comune_nascita: string | null;
  indirizzo: string | null;
  comune_residenza: string | null;
  cap: string | null;
  email: string | null;
  telefono: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type UtenzePerson = AnagraficaPerson;

export type AnagraficaCompany = {
  subject_id: string;
  ragione_sociale: string;
  partita_iva: string;
  codice_fiscale: string | null;
  forma_giuridica: string | null;
  sede_legale: string | null;
  comune_sede: string | null;
  cap: string | null;
  email_pec: string | null;
  telefono: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type UtenzeCompany = AnagraficaCompany;

export type AnagraficaSubjectListItem = {
  id: string;
  subject_type: string;
  status: string;
  source_system: string;
  source_external_id: string | null;
  source_name_raw: string;
  display_name: string;
  codice_fiscale: string | null;
  partita_iva: string | null;
  nas_folder_path: string | null;
  nas_folder_letter: string | null;
  requires_review: boolean;
  imported_at: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type UtenzeSubjectListItem = AnagraficaSubjectListItem;

export type AnagraficaSubjectListResponse = {
  items: AnagraficaSubjectListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type UtenzeSubjectListResponse = AnagraficaSubjectListResponse;

export type AnagraficaSubjectDetail = {
  id: string;
  subject_type: string;
  status: string;
  source_system: string;
  source_external_id: string | null;
  source_name_raw: string;
  nas_folder_path: string | null;
  nas_folder_letter: string | null;
  requires_review: boolean;
  imported_at: string | null;
  created_at: string;
  updated_at: string;
  person: AnagraficaPerson | null;
  company: AnagraficaCompany | null;
  documents: AnagraficaDocument[];
  audit_log: AnagraficaAuditLog[];
  catasto_documents: AnagraficaCatastoDocument[];
};

export type AnagraficaPaymentNoticePdf = {
  filename: string | null;
  url: string;
  label: string | null;
  document_id?: string | null;
  download_url?: string | null;
};

export type AnagraficaPaymentNotice = {
  id: string;
  subject_id: string | null;
  source_system: string;
  source_notice_id: string;
  source_internal_id: string | null;
  codice_fiscale: string | null;
  partita_iva: string | null;
  display_name: string | null;
  anno: string | null;
  stato_code: string | null;
  stato_label: string | null;
  data_scadenza: string | null;
  data_pagamento: string | null;
  tipo_anagrafica: string | null;
  ultimo_invio: string | null;
  lista_id: string | null;
  lista_descrizione: string | null;
  indirizzo: string | null;
  cap: string | null;
  citta: string | null;
  provincia: string | null;
  importo_carico: string | null;
  importo_sgravio: string | null;
  importo_riscosso: string | null;
  importo_residuo: string | null;
  importo_riporto: string | null;
  importo_rateizzato: string | null;
  importo_annullato: string | null;
  payment_status?: "paid" | "partial" | "unpaid" | null;
  detail_url: string | null;
  detail_info_text: string | null;
  pdf_links: AnagraficaPaymentNoticePdf[];
  synced_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type UtenzeSubjectDetail = AnagraficaSubjectDetail;

export type AnagraficaPersonInput = {
  cognome: string;
  nome: string;
  codice_fiscale: string;
  data_nascita?: string | null;
  comune_nascita?: string | null;
  indirizzo?: string | null;
  comune_residenza?: string | null;
  cap?: string | null;
  email?: string | null;
  telefono?: string | null;
  note?: string | null;
  anpr_id?: string | null;
  stato_anpr?: string | null;
  data_decesso?: string | null;
  luogo_decesso_comune?: string | null;
};

export type AnprSubjectStatus = {
  subject_id: string;
  anpr_id: string | null;
  stato_anpr: "alive" | "deceased" | "not_found_anpr" | "cancelled_anpr" | "error" | "unknown" | null;
  data_decesso: string | null;
  luogo_decesso_comune: string | null;
  last_anpr_check_at: string | null;
  last_c030_check_at: string | null;
  capacitas_deceduto?: boolean | null;
  capacitas_last_check_at?: string | null;
};

export type AnprSyncResult = {
  subject_id: string;
  success: boolean;
  esito: string;
  data_decesso: string | null;
  anpr_id: string | null;
  calls_made: number;
  message: string;
};

export type AnprPreviewLookupResponse = {
  success: boolean;
  anpr_id: string | null;
  stato_anpr: string | null;
  data_decesso: string | null;
  luogo_decesso_comune: string | null;
  calls_made: number;
  message: string;
};

export type AnprSyncConfig = {
  max_calls_per_day: number;
  job_enabled: boolean;
  job_cron: string;
  lookback_years: number;
  retry_not_found_days: number;
  updated_at: string | null;
};

export type AnprSyncConfigUpdateInput = {
  max_calls_per_day?: number;
  job_enabled?: boolean;
  job_cron?: string;
  lookback_years?: number;
  retry_not_found_days?: number;
};

export type AnprJobTriggerResult = {
  started_at: string;
  subjects_processed: number;
  deceased_found: number;
  errors: number;
  calls_used: number;
  message: string;
};

export type AnagraficaSubjectCreateInput = {
  subject_type: "person" | "company" | "unknown";
  source_name_raw: string;
  source_external_id?: string | null;
  /** In creazione ignorato dall'API: il path NAS è calcolato lato server. */
  nas_folder_path?: string | null;
  nas_folder_letter?: string | null;
  requires_review?: boolean;
  person?: AnagraficaPersonInput | null;
  company?: Omit<AnagraficaCompany, "subject_id" | "created_at" | "updated_at"> | null;
};

export type UtenzeSubjectCreateInput = AnagraficaSubjectCreateInput;

export type AnagraficaSubjectUpdateInput = {
  source_name_raw?: string;
  status?: "active" | "inactive" | "duplicate";
  nas_folder_path?: string | null;
  nas_folder_letter?: string | null;
  requires_review?: boolean;
  person?: AnagraficaPersonInput | null;
  company?: Omit<AnagraficaCompany, "subject_id" | "created_at" | "updated_at"> | null;
};

export type UtenzeSubjectUpdateInput = AnagraficaSubjectUpdateInput;

export type AnagraficaImportWarning = {
  code: string;
  message: string;
  path: string | null;
};

export type UtenzeImportWarning = AnagraficaImportWarning;

export type AnagraficaCsvImportError = {
  row_number: number;
  message: string;
  codice_fiscale: string | null;
};

export type UtenzeCsvImportError = AnagraficaCsvImportError;

export type AnagraficaCsvImportResult = {
  total_rows: number;
  created_subjects: number;
  updated_subjects: number;
  skipped_rows: number;
  errors: AnagraficaCsvImportError[];
};

export type UtenzeCsvImportResult = AnagraficaCsvImportResult;

export type AnagraficaPreviewSubject = {
  folder_name: string;
  letter: string;
  nas_folder_path: string;
  source_name_raw: string;
  subject_type: string;
  requires_review: boolean;
  confidence: number;
  cognome: string | null;
  nome: string | null;
  codice_fiscale: string | null;
  ragione_sociale: string | null;
  partita_iva: string | null;
  warnings: string[];
  documents: AnagraficaDocument[];
};

export type UtenzePreviewSubject = AnagraficaPreviewSubject;

export type AnagraficaImportPreview = {
  letter: string;
  archive_root: string;
  generated_at: string;
  total_folders: number;
  parsed_subjects: number;
  subjects_requiring_review: number;
  total_documents: number;
  non_pdf_documents: number;
  warnings: AnagraficaImportWarning[];
  errors: AnagraficaImportWarning[];
  subjects: AnagraficaPreviewSubject[];
};

export type UtenzeImportPreview = AnagraficaImportPreview;

export type AnagraficaImportRunResult = {
  job_id: string;
  letter: string;
  status: string;
  total_folders: number;
  imported_ok: number;
  imported_errors: number;
  warning_count: number;
  pending_items: number;
  running_items: number;
  completed_items: number;
  failed_items: number;
  created_subjects: number;
  updated_subjects: number;
  created_documents: number;
  updated_documents: number;
  generated_at: string;
  completed_at: string | null;
  log_json: Record<string, unknown> | unknown[] | null;
};

export type UtenzeImportRunResult = AnagraficaImportRunResult;

export type AnagraficaVisuraRoutingAnomaly = {
  id: string;
  source_path: string;
  filename: string;
  identifier: string | null;
  identifier_kind: string | null;
  reason: string;
  details_json: Record<string, unknown> | unknown[] | null;
  occurrences: number;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UtenzeVisuraRoutingAnomaly = AnagraficaVisuraRoutingAnomaly;

export type AnagraficaVisuraRoutingAnomalyListResponse = {
  items: AnagraficaVisuraRoutingAnomaly[];
  total: number;
  unresolved: number;
  resolved: number;
  page: number;
  page_size: number;
};

export type UtenzeVisuraRoutingAnomalyListResponse = AnagraficaVisuraRoutingAnomalyListResponse;

export type AnagraficaSubjectImportResult = {
  subject_id: string;
  matched_folder_path: string;
  matched_folder_name: string;
  warning_count: number;
  created_documents: number;
  updated_documents: number;
  imported_at: string;
};

export type UtenzeSubjectImportResult = AnagraficaSubjectImportResult;

export type AnagraficaResetResult = {
  cleared_subject_links: number;
  deleted_documents: number;
  deleted_audit_logs: number;
  deleted_import_jobs: number;
  deleted_import_job_items: number;
  deleted_storage_files: number;
};

export type UtenzeResetResult = AnagraficaResetResult;

export type AnagraficaNasFolderCandidate = {
  folder_name: string;
  letter: string | null;
  nas_folder_path: string;
  score: number;
  subject_type: string;
  confidence: number;
  requires_review: boolean;
  codice_fiscale: string | null;
  partita_iva: string | null;
  ragione_sociale: string | null;
  cognome: string | null;
  nome: string | null;
};

export type UtenzeNasFolderCandidate = AnagraficaNasFolderCandidate;

export type AnagraficaSubjectNasImportStatus = {
  can_import_from_nas: boolean;
  missing_in_nas: boolean;
  matched_folder_path: string | null;
  matched_folder_name: string | null;
  total_files_in_nas: number;
  pending_files_in_nas: number;
  message: string;
};

export type UtenzeSubjectNasImportStatus = AnagraficaSubjectNasImportStatus;

export type AnagraficaImportJob = {
  job_id: string;
  requested_by_user_id: number | null;
  letter: string | null;
  status: string;
  total_folders: number;
  imported_ok: number;
  imported_errors: number;
  warning_count: number;
  pending_items: number;
  running_items: number;
  completed_items: number;
  failed_items: number;
  items: AnagraficaImportJobItem[];
  log_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type UtenzeImportJob = AnagraficaImportJob;

export type AnagraficaImportJobItem = {
  id: string;
  subject_id: string | null;
  letter: string | null;
  folder_name: string;
  nas_folder_path: string;
  status: string;
  attempt_count: number;
  warning_count: number;
  documents_created: number;
  documents_updated: number;
  payload_json: Record<string, unknown> | unknown[] | null;
  last_error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UtenzeImportJobItem = AnagraficaImportJobItem;

export type XlsxImportErrorEntry = {
  row: number;
  message: string;
  denominazione: string;
};

export type XlsxImportBatch = {
  id: string;
  requested_by_user_id: number | null;
  filename: string;
  status: "pending" | "running" | "completed" | "failed";
  total_rows: number;
  processed_rows: number;
  inserted: number;
  updated: number;
  unchanged: number;
  anomalies: number;
  errors: number;
  error_log: XlsxImportErrorEntry[] | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type XlsxImportStartResult = {
  batch_id: string;
  status: string;
  message: string;
};

export type AnagraficaSearchResult = {
  items: AnagraficaSubjectListItem[];
  total: number;
};

export type UtenzeSearchResult = AnagraficaSearchResult;

export type NasUser = {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  source_uid: string | null;
  is_active: boolean;
  last_seen_snapshot_id: number | null;
};

export type NasGroup = {
  id: number;
  name: string;
  description: string | null;
  last_seen_snapshot_id: number | null;
};

export type Share = {
  id: number;
  name: string;
  path: string;
  parent_id: number | null;
  sector: string | null;
  description: string | null;
  last_seen_snapshot_id: number | null;
};

export type Review = {
  id: number;
  snapshot_id: number | null;
  nas_user_id: number;
  share_id: number;
  reviewer_user_id: number;
  decision: string;
  note: string | null;
};

export type SyncCapabilities = {
  ssh_configured: boolean;
  host: string;
  port: number;
  username: string;
  timeout_seconds: number;
  supports_live_sync: boolean;
  auth_mode: string;
  retry_strategy: string;
  retry_max_attempts: number;
  retry_base_delay_seconds: number;
  retry_max_delay_seconds: number;
  retry_jitter_enabled: boolean;
  retry_jitter_ratio: number;
  live_sync_profiles: string[];
  default_live_sync_profile: string;
};

export type SyncPreviewRequest = {
  passwd_text: string;
  group_text: string;
  shares_text: string;
  acl_texts: string[];
};

export type ParsedNasSyncUser = {
  username: string;
  source_uid: string;
  full_name: string | null;
  home_directory: string | null;
};

export type ParsedNasSyncGroup = {
  name: string;
  gid: string;
  members: string[];
};

export type ParsedNasSyncShare = {
  name: string;
};

export type ParsedAclEntry = {
  subject: string;
  permissions: string;
  effect: string;
};

export type SyncPreview = {
  users: ParsedNasSyncUser[];
  groups: ParsedNasSyncGroup[];
  shares: ParsedNasSyncShare[];
  acl_entries: ParsedAclEntry[];
};

export type SyncApplyResult = {
  snapshot_id: number;
  snapshot_checksum: string;
  persisted_users: number;
  persisted_groups: number;
  persisted_shares: number;
  persisted_permission_entries: number;
  persisted_effective_permissions: number;
  share_acl_pairs_used: number;
};

export type SyncJob = {
  id: number;
  requested_by_user_id: number;
  profile: string;
  trigger_type: string;
  status: string;
  snapshot_id: number | null;
  persisted_users: number;
  persisted_groups: number;
  persisted_shares: number;
  persisted_permission_entries: number;
  persisted_effective_permissions: number;
  share_acl_pairs_used: number;
  worker_log_path: string | null;
  worker_pid: number | null;
  attempt_count: number;
  max_attempts: number;
  source_label: string | null;
  error_detail: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type SyncRun = {
  id: number;
  snapshot_id: number | null;
  mode: string;
  trigger_type: string;
  status: string;
  attempts_used: number;
  duration_ms: number | null;
  initiated_by: string | null;
  source_label: string | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type EffectivePermission = {
  id: number;
  snapshot_id: number | null;
  nas_user_id: number;
  share_id: number;
  can_read: boolean;
  can_write: boolean;
  is_denied: boolean;
  source_summary: string;
};

export type PermissionUserInput = {
  username: string;
  groups: string[];
};

export type PermissionEntryInput = {
  share_name: string;
  subject_type: string;
  subject_name: string;
  permission_level: string;
  is_deny: boolean;
};

export type EffectivePermissionPreview = {
  username: string;
  share_name: string;
  can_read: boolean;
  can_write: boolean;
  is_denied: boolean;
  source_summary: string;
};
