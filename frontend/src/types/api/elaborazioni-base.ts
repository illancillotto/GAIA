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
  schedule_enabled: boolean;
  availability_schedule: SisterCredentialAvailabilitySchedule | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
};
export type SisterCredentialAvailabilityWindow = {
  start: string;
  end: string;
};

export type SisterCredentialNthWeekdayException = {
  kind: "nth_weekday_of_month";
  weekday: number;
  occurrence: number;
  windows: SisterCredentialAvailabilityWindow[];
};

export type SisterCredentialAvailabilitySchedule = {
  timezone: "Europe/Rome";
  weekly: Record<string, SisterCredentialAvailabilityWindow[]>;
  exceptions?: SisterCredentialNthWeekdayException[];
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

export type PostaOnlineCredential = {
  id: number;
  label: string;
  username: string;
  active: boolean;
  allowed_hours_start: number;
  allowed_hours_end: number;
  min_delay_ms: number;
  max_delay_ms: number;
  last_used_at: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
};

export type PostaOnlineCredentialCreateInput = {
  label: string;
  username: string;
  password: string;
  active?: boolean;
  allowed_hours_start?: number;
  allowed_hours_end?: number;
  min_delay_ms?: number;
  max_delay_ms?: number;
};

export type PostaOnlineCredentialUpdateInput = {
  label?: string;
  username?: string;
  password?: string;
  active?: boolean;
  allowed_hours_start?: number;
  allowed_hours_end?: number;
  min_delay_ms?: number;
  max_delay_ms?: number;
};

export type PostaOnlineCredentialTestInput = {
  min_delay_ms?: number;
  max_delay_ms?: number;
};

export type PostaOnlineRegisteredMailSyncJobCreateInput = {
  credential_id?: number | null;
  annualita?: number[];
  include_contacts?: boolean;
  include_details?: boolean;
  max_pages?: number | null;
  max_details?: number | null;
  min_delay_ms?: number | null;
  max_delay_ms?: number | null;
  continue_on_error?: boolean;
};

export type PostaOnlineRegisteredMailSyncJobResult = {
  ok?: boolean;
  error?: string | null;
  checked_at?: string;
  started_at?: string;
  completed_at?: string;
  tributi_import_job_id?: string;
  archive_ids?: string[];
  details_scraped?: number;
  contacts_scraped?: number;
  scrape_errors?: Array<Record<string, unknown>>;
  records_total?: number;
  records_imported?: number;
  records_matched?: number;
  records_ambiguous?: number;
  records_unmatched?: number;
  records_errors?: number;
};

export type PostaOnlineRegisteredMailSyncJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: "registered_mails" | "credential_test" | string;
  payload_json: PostaOnlineRegisteredMailSyncJobCreateInput | Record<string, unknown> | unknown[] | null;
  result_json: PostaOnlineRegisteredMailSyncJobResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
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

export type GateMobileSyncRunResponse = {
  id: string;
  trigger_source: string;
  status: string;
  requested_tasks_count: number;
  operators_pushed: number;
  duration_ms: number | null;
  requested_tasks: Array<Record<string, unknown>>;
  error_kind: string | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

export type GateMobileSyncStatusResponse = {
  sync_enabled: boolean;
  gateway_base_url: string | null;
  gateway_configured: boolean;
  token_configured: boolean;
  timeout_seconds: number;
  outbound_scope: string[];
  internal_connector_api: {
    path_prefix: string;
    auth_header: string;
  };
  last_run: GateMobileSyncRunResponse | null;
  recent_runs: GateMobileSyncRunResponse[];
};

export type GateMobileSyncRunTriggerResponse = {
  job: GateMobileSyncRunResponse;
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

export type CapacitasAnagraficaHistoryImportItemInput = {
  subject_id?: string | null;
  idxana?: string | null;
};

export type CapacitasAnagraficaHistoryImportInput = {
  items: CapacitasAnagraficaHistoryImportItemInput[];
  credential_id?: number | null;
  continue_on_error?: boolean;
  auto_resume?: boolean;
};

export type CapacitasAnagraficaHistoryImportItemResult = {
  subject_id?: string | null;
  resolved_subject_id?: string | null;
  idxana?: string | null;
  status: string;
  history_records_total: number;
  imported_records: number;
  skipped_records: number;
  message?: string | null;
  error?: string | null;
};

export type CapacitasAnagraficaHistoryImportResult = {
  items: CapacitasAnagraficaHistoryImportItemResult[];
  processed: number;
  imported: number;
  skipped: number;
  failed: number;
  snapshot_records_imported: number;
};

export type CapacitasAnagraficaHistoryImportJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: Record<string, unknown> | unknown[] | null;
  result_json: CapacitasAnagraficaHistoryImportResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CapacitasDomandeIrrigueAnagraficaSearchInput = {
  q: string;
  tipo_ricerca?: number;
  solo_con_beni?: boolean;
};

export type CapacitasDomandeIrrigueSyncJobCreateInput = {
  credential_id?: number | null;
  searches: CapacitasDomandeIrrigueAnagraficaSearchInput[];
  include_details?: boolean;
  continue_on_error?: boolean;
  run_anomaly_checks?: boolean;
  deduplicate_contexts?: boolean;
  throttle_ms?: number;
  auto_resume?: boolean;
};

export type CapacitasDomandeIrrigueSyncRecentItem = {
  status: string;
  label?: string | null;
  source_row_id?: string | null;
  cco?: string | null;
  com?: string | null;
  pvc?: string | null;
  fra?: string | null;
  ccs?: string | null;
  total_domande?: number;
  error?: string | null;
};

export type CapacitasDomandeIrrigueSyncJobResult = {
  mode: string;
  total_searches: number;
  searches_completed: number;
  source_rows: number;
  skipped_duplicate_contexts: number;
  total_rows: number;
  processed_rows: number;
  records_with_domande: number;
  domande_seen: number;
  domande_inserted: number;
  domande_updated: number;
  particelle_inserted: number;
  linked_utenze: number;
  linked_occupancies: number;
  linked_particelle: number;
  anomalies_opened: number;
  anomalies_updated: number;
  failed_items: number;
  progress_percent: number;
  current_label?: string | null;
  completed_at?: string | null;
  recent_items: CapacitasDomandeIrrigueSyncRecentItem[];
};

export type CapacitasDomandeIrrigueSyncJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: CapacitasDomandeIrrigueSyncJobCreateInput | Record<string, unknown> | unknown[] | null;
  result_json: CapacitasDomandeIrrigueSyncJobResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CapacitasLookupOption = {
  id: string;
  display: string;
};

export type CapacitasTerrenoRow = {
  ID?: string | null;
  PVC?: string | null;
  COM?: string | null;
  CCO?: string | null;
  FRA?: string | null;
  CCS?: string | null;
  Stato?: string | null;
  Ta_ext?: string | null;
  Tipo?: string | null;
  Superficie?: string | null;
  Sez?: string | null;
  Foglio?: string | null;
  Partic?: string | null;
  Sub?: string | null;
  BacDescr?: string | null;
  Anno?: string | null;
  Voltura?: string | null;
  Opcode?: string | null;
  DataReg?: string | null;
  Belfiore?: string | null;
  NEW_CCO?: string | null;
  NEW_FRA?: string | null;
  NEW_CCS?: string | null;
  row_visual_state?: string | null;
};
