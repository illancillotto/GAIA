export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type CurrentUser = {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  enabled_modules: string[];
};

export type ResolvedSectionPermission = {
  section_key: string;
  section_label: string;
  module: string;
  is_granted: boolean;
  source: string;
};

export type MyPermissionsResponse = {
  sections: ResolvedSectionPermission[];
  granted_keys: string[];
};

export type ApplicationUser = {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  enabled_modules: string[];
  created_at: string;
  updated_at: string;
};

export type ApplicationUserListResponse = {
  items: ApplicationUser[];
  total: number;
};

export type ApplicationUserCreateInput = {
  username: string;
  email: string;
  password: string;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo?: boolean;
};

export type ApplicationUserUpdateInput = {
  email?: string;
  password?: string;
  role?: string;
  is_active?: boolean;
  module_accessi?: boolean;
  module_rete?: boolean;
  module_inventario?: boolean;
  module_catasto?: boolean;
  module_utenze?: boolean;
  module_operazioni?: boolean;
  module_riordino?: boolean;
  module_ruolo?: boolean;
};

export type DashboardSummary = {
  nas_users: number;
  nas_groups: number;
  shares: number;
  reviews: number;
  snapshots: number;
  sync_runs: number;
};

export type NetworkDashboardSummary = {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  open_alerts: number;
  scans_last_24h: number;
  floor_plans: number;
  latest_scan_at: string | null;
};

export type NetworkDevice = {
  id: number;
  last_scan_id: number | null;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  hostname_source: string | null;
  display_name: string | null;
  asset_label: string | null;
  vendor: string | null;
  model_name: string | null;
  device_type: string | null;
  operating_system: string | null;
  dns_name: string | null;
  location_hint: string | null;
  notes: string | null;
  is_known_device: boolean;
  metadata_sources: Record<string, string> | null;
  status: string;
  is_monitored: boolean;
  open_ports: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
  positions: DevicePosition[];
  scan_history: {
    scan_id: number;
    observed_at: string;
    status: string;
    hostname: string | null;
    ip_address: string;
    open_ports: string | null;
  }[];
};

export type NetworkDeviceUpdateInput = {
  display_name?: string | null;
  asset_label?: string | null;
  model_name?: string | null;
  device_type?: string | null;
  operating_system?: string | null;
  location_hint?: string | null;
  notes?: string | null;
  is_known_device?: boolean;
  is_monitored?: boolean;
};

export type NetworkDeviceListResponse = {
  items: NetworkDevice[];
  total: number;
  page: number;
  page_size: number;
};

export type NetworkAlert = {
  id: number;
  device_id: number | null;
  scan_id: number | null;
  alert_type: string;
  severity: string;
  status: string;
  title: string;
  message: string | null;
  created_at: string;
  acknowledged_at: string | null;
};

export type NetworkAlertUpdateInput = {
  status: "open" | "resolved" | "ignored";
};

export type NetworkScanDeltaSummary = {
  new_devices_count: number;
  missing_devices_count: number;
  changed_devices_count: number;
};

export type NetworkScan = {
  id: number;
  network_range: string;
  scan_type: string;
  status: string;
  hosts_scanned: number;
  active_hosts: number;
  discovered_devices: number;
  initiated_by: string | null;
  notes: string | null;
  started_at: string;
  completed_at: string;
  delta: NetworkScanDeltaSummary;
};

export type NetworkScanTriggerResponse = {
  scan: NetworkScan;
  devices_upserted: number;
  alerts_created: number;
};

export type BonificaUserStaging = {
  id: string;
  wc_id: number;
  username: string | null;
  email: string | null;
  user_type: string | null;
  business_name: string | null;
  first_name: string | null;
  last_name: string | null;
  tax: string | null;
  phone: string | null;
  mobile: string | null;
  role: string | null;
  enabled: boolean;
  wc_synced_at: string | null;
  review_status: string;
  matched_subject_id: string | null;
  matched_subject_display_name: string | null;
  mismatch_fields: Record<string, unknown> | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BonificaUserStagingListResponse = {
  items: BonificaUserStaging[];
  total: number;
  page: number;
  page_size: number;
};

export type BonificaUserStagingBulkApproveResponse = {
  approved: number;
  skipped: number;
  errors: string[];
};

export type NetworkScanDevice = {
  id: number;
  scan_id: number;
  device_id: number | null;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  hostname_source: string | null;
  display_name: string | null;
  asset_label: string | null;
  vendor: string | null;
  model_name: string | null;
  device_type: string | null;
  operating_system: string | null;
  dns_name: string | null;
  location_hint: string | null;
  metadata_sources: Record<string, string> | null;
  status: string;
  open_ports: string | null;
  observed_at: string;
};

export type NetworkScanDetail = NetworkScan & {
  devices: NetworkScanDevice[];
};

export type NetworkScanDiffEntry = {
  key: string;
  before: NetworkScanDevice | null;
  after: NetworkScanDevice | null;
  change_type: string;
};

export type NetworkScanDiff = {
  from_scan_id: number;
  to_scan_id: number;
  summary: NetworkScanDeltaSummary;
  changes: NetworkScanDiffEntry[];
};

export type NetworkFloorPlan = {
  id: number;
  name: string;
  building: string | null;
  floor_label: string;
  svg_content: string | null;
  image_url: string | null;
  width: number | null;
  height: number | null;
  created_at: string;
  updated_at: string;
};

export type DevicePosition = {
  id: number;
  device_id: number;
  floor_plan_id: number;
  x: number;
  y: number;
  label: string | null;
  created_at: string;
  updated_at: string;
};

export type NetworkFloorPlanDetail = NetworkFloorPlan & {
  positions: DevicePosition[];
};

export type NetworkFloorPlanCreateInput = {
  name: string;
  floor_label: string;
  building?: string | null;
  svg_content?: string | null;
  image_url?: string | null;
  width?: number | null;
  height?: number | null;
};

export type DevicePositionUpdateInput = {
  floor_plan_id: number;
  x: number;
  y: number;
  label?: string | null;
};

export type NetworkFloorPlanDevice = {
  position: DevicePosition;
  device: NetworkDevice;
};

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

export type UtenzeSubjectDetail = AnagraficaSubjectDetail;

export type AnagraficaSubjectCreateInput = {
  subject_type: "person" | "company" | "unknown";
  source_name_raw: string;
  nas_folder_path?: string | null;
  nas_folder_letter?: string | null;
  requires_review?: boolean;
  person?: Omit<AnagraficaPerson, "subject_id" | "created_at" | "updated_at"> | null;
  company?: Omit<AnagraficaCompany, "subject_id" | "created_at" | "updated_at"> | null;
};

export type UtenzeSubjectCreateInput = AnagraficaSubjectCreateInput;

export type AnagraficaSubjectUpdateInput = {
  source_name_raw?: string;
  status?: "active" | "inactive" | "duplicate";
  nas_folder_path?: string | null;
  nas_folder_letter?: string | null;
  requires_review?: boolean;
  person?: Omit<AnagraficaPerson, "subject_id" | "created_at" | "updated_at"> | null;
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

export type SyncLiveApplyResult = SyncApplyResult;

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

export type CatastoCredential = {
  id: string;
  user_id: number;
  label: string;
  sister_username: string;
  convenzione: string | null;
  codice_richiesta: string | null;
  ufficio_provinciale: string;
  active: boolean;
  is_default: boolean;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CatastoCredentialStatus = {
  configured: boolean;
  credentials: CatastoCredential[];
  default_credential: CatastoCredential | null;
  credential: CatastoCredential | null;
};

export type CatastoCredentialTestResult = {
  id: string;
  credential_id: string | null;
  status: "pending" | "processing" | "completed" | "failed";
  success: boolean | null;
  mode: string | null;
  reachable: boolean | null;
  authenticated: boolean | null;
  message: string | null;
  verified_at: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type CatastoCredentialTestWebSocketEvent = {
  type: "credentials_test";
  test: CatastoCredentialTestResult;
};

export type CapacitasCredential = {
  id: number;
  label: string;
  username: string;
  active: boolean;
  allowed_hours_start: number;
  allowed_hours_end: number;
  last_used_at: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
};

export type CapacitasCredentialCreateInput = {
  label: string;
  username: string;
  password: string;
  active?: boolean;
  allowed_hours_start?: number;
  allowed_hours_end?: number;
};

export type CapacitasCredentialUpdateInput = {
  label?: string;
  username?: string;
  password?: string;
  active?: boolean;
  allowed_hours_start?: number;
  allowed_hours_end?: number;
};

export type CapacitasCredentialTestResult = {
  ok: boolean;
  token: string | null;
  error: string | null;
};

export type BonificaOristaneseCredential = {
  id: number;
  label: string;
  login_identifier: string;
  remember_me: boolean;
  active: boolean;
  last_used_at: string | null;
  last_authenticated_url: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
};

export type BonificaOristaneseCredentialCreateInput = {
  label: string;
  login_identifier: string;
  password: string;
  remember_me?: boolean;
  active?: boolean;
};

export type BonificaOristaneseCredentialUpdateInput = {
  label?: string;
  login_identifier?: string;
  password?: string;
  remember_me?: boolean;
  active?: boolean;
};

export type BonificaOristaneseCredentialTestResult = {
  ok: boolean;
  authenticated_url: string | null;
  cookies: string | null;
  error: string | null;
};

export type BonificaSyncRunRequest = {
  entities: "all" | string | string[];
  date_from?: string | null;
  date_to?: string | null;
};

export type BonificaSyncJobStart = {
  job_id: string;
  status: string;
  started_at: string;
};

export type BonificaSyncRunResponse = {
  jobs: Record<string, BonificaSyncJobStart>;
};

export type BonificaSyncEntityStatus = {
  job_id: string | null;
  entity: string;
  status: string;
  last_started_at: string | null;
  last_finished_at: string | null;
  records_synced: number | null;
  records_skipped: number | null;
  records_errors: number | null;
  error_detail: string | null;
  params_json: Record<string, unknown> | null;
};

export type BonificaSyncStatusResponse = {
  entities: Record<string, BonificaSyncEntityStatus>;
};

export type CapacitasAnagrafica = {
  id?: string | null;
  IDXANA?: string | null;
  Stato?: string | null;
  Patrimonio?: string | null;
  Prg?: string | null;
  Di?: string | null;
  TP?: string | null;
  TA?: string | null;
  PVC?: string | null;
  COM?: string | null;
  Belfiore?: string | null;
  CCO?: string | null;
  Fraz?: string | null;
  Sche?: string | null;
  Comune?: string | null;
  Denominazione?: string | null;
  DataNascita?: string | null;
  LuogoNascita?: string | null;
  CodiceFiscale?: string | null;
  CertAT?: string | null;
  Deceduto?: string | null;
  PartitaIva?: string | null;
  Titolo1?: string | null;
  TitoloLib1?: string | null;
  TitoloLib2?: string | null;
  NTerreni?: string | null;
};

export type CapacitasSearchInput = {
  q: string;
  tipo_ricerca?: number;
  solo_con_beni?: boolean;
  credential_id?: number | null;
};

export type CapacitasSearchResult = {
  total: number;
  rows: CapacitasAnagrafica[];
};

export type CatastoSingleVisuraPayload = {
  search_mode?: "immobile" | "soggetto";
  comune?: string;
  catasto?: string;
  sezione?: string;
  foglio?: string;
  particella?: string;
  subalterno?: string;
  tipo_visura: string;
  subject_kind?: "PF" | "PNF";
  subject_id?: string;
  request_type?: "ATTUALITA" | "STORICA";
  intestazione?: string;
};

export type CatastoComune = {
  id: number;
  nome: string;
  codice_sister: string;
  ufficio: string;
};

export type CatastoRequestStatus =
  | "pending"
  | "processing"
  | "awaiting_captcha"
  | "completed"
  | "failed"
  | "skipped"
  | "not_found";

export type CatastoVisuraRequest = {
  id: string;
  batch_id: string;
  user_id: number;
  row_index: number;
  search_mode: "immobile" | "soggetto";
  comune: string | null;
  comune_codice: string | null;
  catasto: string | null;
  sezione: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  tipo_visura: string;
  subject_kind: "PF" | "PNF" | null;
  subject_id: string | null;
  request_type: "ATTUALITA" | "STORICA" | null;
  intestazione: string | null;
  status: CatastoRequestStatus;
  current_operation: string | null;
  error_message: string | null;
  attempts: number;
  captcha_image_path: string | null;
  captcha_requested_at: string | null;
  captcha_expires_at: string | null;
  captcha_skip_requested: boolean;
  artifact_dir: string | null;
  document_id: string | null;
  created_at: string;
  processed_at: string | null;
};

export type CatastoBatch = {
  id: string;
  user_id: number;
  name: string | null;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  total_items: number;
  completed_items: number;
  failed_items: number;
  skipped_items: number;
  not_found_items: number;
  source_filename: string | null;
  current_operation: string | null;
  report_json_path: string | null;
  report_md_path: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type CatastoBatchDetail = CatastoBatch & {
  requests: CatastoVisuraRequest[];
};

export type CatastoDocument = {
  id: string;
  user_id: number;
  request_id: string | null;
  batch_id: string | null;
  search_mode: "immobile" | "soggetto";
  comune: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  catasto: string | null;
  tipo_visura: string;
  subject_kind: "PF" | "PNF" | null;
  subject_id: string | null;
  request_type: "ATTUALITA" | "STORICA" | null;
  intestazione: string | null;
  filename: string;
  file_size: number | null;
  codice_fiscale: string | null;
  created_at: string;
};

export type CatastoOperationResponse = {
  success: boolean;
  message: string;
};

export type CatastoCaptchaSummary = {
  processed: number;
  correct: number;
  wrong: number;
};

export type CatastoBatchProgressEvent = {
  type: "progress";
  status: string;
  completed: number;
  failed: number;
  skipped: number;
  not_found?: number;
  total: number;
  current: string | null;
};

export type CatastoBatchCaptchaEvent = {
  type: "captcha_needed";
  request_id: string;
  image_url: string;
};

export type CatastoBatchCompletedEvent = {
  type: "batch_completed";
  status: string;
  ok: number;
  failed: number;
  skipped: number;
  not_found?: number;
};

export type CatastoVisuraCompletedEvent = {
  type: "visura_completed";
  request_id: string;
  document_id: string;
};

export type CatastoBatchWebSocketEvent =
  | CatastoBatchProgressEvent
  | CatastoBatchCaptchaEvent
  | CatastoBatchCompletedEvent
  | CatastoVisuraCompletedEvent;

export type ElaborazioneCredential = CatastoCredential;
export type ElaborazioneCredentialStatus = CatastoCredentialStatus;
export type ElaborazioneCredentialTestResult = CatastoCredentialTestResult;
export type ElaborazioneCredentialTestWebSocketEvent = CatastoCredentialTestWebSocketEvent;
export type ElaborazioneRichiestaCreateInput = CatastoSingleVisuraPayload;
export type ElaborazioneRequestStatus = CatastoRequestStatus;
export type ElaborazioneRichiesta = CatastoVisuraRequest;
export type ElaborazioneBatch = CatastoBatch;
export type ElaborazioneBatchDetail = CatastoBatchDetail;
export type ElaborazioneOperationResponse = CatastoOperationResponse;
export type ElaborazioneCaptchaSummary = CatastoCaptchaSummary;
export type ElaborazioneBatchProgressEvent = CatastoBatchProgressEvent;
export type ElaborazioneBatchCaptchaEvent = CatastoBatchCaptchaEvent;
export type ElaborazioneBatchCompletedEvent = CatastoBatchCompletedEvent;
export type ElaborazioneRichiestaCompletedEvent = CatastoVisuraCompletedEvent;
export type ElaborazioneBatchWebSocketEvent = CatastoBatchWebSocketEvent;
