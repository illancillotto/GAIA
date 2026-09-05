import type {
  CapacitasTerrenoRow,
  CatastoCredential,
  CatastoCredentialStatus,
  CatastoCredentialTestResult,
  CatastoCredentialTestWebSocketEvent,
} from "./elaborazioni-base";

export type CapacitasTerreniSearchInput = {
  frazione_id: string;
  sezione?: string;
  foglio?: string;
  particella?: string;
  sub?: string;
  qualita?: string;
  caratura?: string;
  caratura_val?: string;
  in_essere?: boolean;
  in_dom_irr?: boolean;
  limita_risultati?: boolean;
  credential_id?: number | null;
};

export type CapacitasTerreniSearchResult = {
  total: number;
  rows: CapacitasTerrenoRow[];
};

export type CapacitasTerreniBatchItemInput = Omit<CapacitasTerreniSearchInput, "frazione_id"> & {
  label?: string | null;
  comune?: string | null;
  frazione_id?: string;
  foglio: string;
  particella: string;
  fetch_certificati?: boolean;
  fetch_details?: boolean;
};

export type CapacitasTerreniJobCreateInput = {
  items: CapacitasTerreniBatchItemInput[];
  continue_on_error?: boolean;
  credential_id?: number | null;
  fetch_certificati?: boolean;
  fetch_details?: boolean;
  double_speed?: boolean;
  parallel_workers?: number;
  throttle_ms?: number | null;
  auto_resume?: boolean;
};

export type CapacitasTerreniBatchItemResult = {
  label?: string | null;
  search_key: string;
  ok: boolean;
  total_rows: number;
  imported_rows: number;
  imported_certificati: number;
  imported_details: number;
  linked_units: number;
  linked_occupancies: number;
  error?: string | null;
};

export type CapacitasTerreniBatchResult = {
  items: CapacitasTerreniBatchItemResult[];
  processed_items: number;
  failed_items: number;
  total_rows: number;
  imported_rows: number;
  imported_certificati: number;
  imported_details: number;
  linked_units: number;
  linked_occupancies: number;
  total_items?: number;
  current_label?: string | null;
  throttle_ms?: number;
  speed_multiplier?: number;
  parallel_workers?: number;
};

export type CapacitasTerreniJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: Record<string, unknown> | unknown[] | null;
  result_json: CapacitasTerreniBatchResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CapacitasRefetchCertificatiInput = {
  credential_id?: number | null;
  limit?: number;
  throttle_ms?: number;
};

export type CapacitasRefetchCertificatiResult = {
  refetched: number;
  remaining_empty: number;
};

export type CapacitasFrazioneCandidate = {
  frazione_id: string;
  n_rows: number;
  ccos: string[];
  stati: string[];
};

export type CapacitasParticellaAnomalia = {
  id: string;
  comune_id: string | null;
  nome_comune: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  anomaly_type: string;
  candidates: CapacitasFrazioneCandidate[];
  capacitas_last_sync_at: string | null;
  capacitas_last_sync_error: string | null;
};

export type CapacitasResolveFragioneInput = {
  frazione_id: string;
  credential_id?: number | null;
  fetch_certificati?: boolean;
  fetch_details?: boolean;
};

export type CapacitasResolveFragioneResult = {
  ok: boolean;
  total_rows: number;
  imported_certificati: number;
  error: string | null;
};

export type CapacitasParticelleSyncJobCreateInput = {
  credential_id?: number | null;
  only_due?: boolean;
  limit?: number | null;
  fetch_certificati?: boolean;
  fetch_details?: boolean;
  double_speed?: boolean;
  parallel_workers?: number;
  auto_resume?: boolean;
};

export type CapacitasParticelleSyncRecentItem = {
  particella_id: string;
  label: string;
  status: string;
  message: string;
};

export type CapacitasParticelleSyncJobResult = {
  mode: string;
  total_items: number;
  processed_items: number;
  success_items: number;
  failed_items: number;
  skipped_items: number;
  progress_percent: number;
  current_label?: string | null;
  throttle_ms: number;
  aggressive_window: boolean;
  recheck_hours: number;
  speed_multiplier?: number;
  parallel_workers?: number;
  completed_at?: string | null;
  recent_items: CapacitasParticelleSyncRecentItem[];
};

export type CapacitasParticelleSyncJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: Record<string, unknown> | unknown[] | null;
  result_json: CapacitasParticelleSyncJobResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CapacitasInCassSyncJobCreateInput = {
  credential_id?: number | null;
  subject_ids?: string[];
  limit?: number | null;
  include_details?: boolean;
  include_partitario?: boolean;
  include_mailing_list?: boolean;
  download_mailing_receipts?: boolean;
  continue_on_error?: boolean;
  throttle_ms?: number;
};

export type CapacitasInCassRuoloHarvestInput = {
  credential_id?: number | null;
  anno?: number | null;
  chunk_size?: number;
  limit_subjects?: number | null;
  exclude_synced_subjects?: boolean;
  stale_synced_before?: string | null;
  include_details?: boolean;
  include_partitario?: boolean;
  include_mailing_list?: boolean;
  download_mailing_receipts?: boolean;
  continue_on_error?: boolean;
  throttle_ms?: number;
};

export type CapacitasInCassRuoloHarvestResult = {
  anno: number | null;
  chunk_size: number;
  total_subjects: number;
  total_jobs: number;
  job_ids: number[];
  credential_id: number | null;
  exclude_synced_subjects: boolean;
  stale_synced_before?: string | null;
};

export type CapacitasInCassSyncItemResult = {
  subject_id: string;
  identifier: string | null;
  display_name: string | null;
  status: string;
  notices_found: number;
  notices_synced: number;
  paid_notices?: number;
  partial_notices?: number;
  unpaid_notices?: number;
  payment_status_changed?: number;
  newly_paid_notices?: number;
  mailing_contacts_synced?: number;
  mailing_shipments_synced?: number;
  mailing_receipts_downloaded?: number;
  error: string | null;
};

export type CapacitasInCassSyncJobResult = {
  items: CapacitasInCassSyncItemResult[];
  processed_subjects: number;
  failed_subjects: number;
  notices_found: number;
  notices_synced: number;
  paid_notices?: number;
  partial_notices?: number;
  unpaid_notices?: number;
  payment_status_changed?: number;
  newly_paid_notices?: number;
  mailing_contacts_synced?: number;
  mailing_shipments_synced?: number;
  mailing_receipts_downloaded?: number;
  /** Lunghezza reale di `items` prima dell'eventuale troncamento nella lista. */
  total_items?: number;
  /** Presente e `true` quando `items` è stato troncato nella risposta di lista. */
  items_truncated?: boolean;
};

export type CapacitasInCassSyncJob = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  payload_json: CapacitasInCassSyncJobCreateInput | Record<string, unknown> | unknown[] | null;
  result_json: CapacitasInCassSyncJobResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

/**
 * Riga della lista job avvisi inCASS: `GET .../incass/avvisi/jobs`.
 * Non include `payload_json` e ha `result_json` alleggerito (array `items` troncato,
 * con `total_items`). Per il payload completo usare `getCapacitasInCassSyncJob`.
 */
export type CapacitasInCassSyncJobListItem = {
  id: number;
  credential_id: number | null;
  requested_by_user_id: number | null;
  status: string;
  mode: string;
  subject_count: number | null;
  result_json: CapacitasInCassSyncJobResult | Record<string, unknown> | unknown[] | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CapacitasInCassSyncJobListParams = {
  limit?: number;
  status?: "active" | "terminal" | (string & {});
};

export type CatastoSingleVisuraPayload = import("../catasto-elaborazioni").CatastoSingleVisuraPayload;

export type CatastoComune = import("../catasto-elaborazioni").CatastoComune;

export type CatastoRequestStatus = import("../catasto-elaborazioni").CatastoRequestStatus;

export type CatastoVisuraRequest = import("../catasto-elaborazioni").CatastoVisuraRequest;

export type CatastoBatch = import("../catasto-elaborazioni").CatastoBatch;

export type CatastoBatchDetail = import("../catasto-elaborazioni").CatastoBatchDetail;

export type CatastoBatchCredentialUsage = import("../catasto-elaborazioni").CatastoBatchCredentialUsage;

export type CatastoBatchStatistics = import("../catasto-elaborazioni").CatastoBatchStatistics;

export type CatastoDocument = import("../catasto-elaborazioni").CatastoDocument;

export type CatastoOperationResponse = {
  success: boolean;
  message: string;
};

export type CatastoPerpetualSyncItem = import("../elaborazioni-continuous-sync").CatastoPerpetualSyncItem;

export type CatastoRuoloAutoSyncConfig = import("../elaborazioni-continuous-sync").CatastoRuoloAutoSyncConfig;

export type CatastoRuoloAutoSyncConfigUpdateInput = import("../elaborazioni-continuous-sync").CatastoRuoloAutoSyncConfigUpdateInput;

export type CatastoRuoloAutoSyncItem = {
  id: string;
  user_id: number;
  ruolo_particella_id: string;
  cat_particella_id: string | null;
  comune: string | null;
  comune_codice: string | null;
  catasto: string;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  tipo_visura: string;
  status: "pending" | "queued" | "processing" | "completed" | "blocked_source" | "blocked_runtime" | string;
  last_error_message: string | null;
  attempt_count: number;
  linked_batch_id: string | null;
  linked_request_id: string | null;
  retry_after: string | null;
  last_enqueued_at: string | null;
  last_completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CatastoRuoloAutoSyncStatusCounts = {
  total: number;
  pending: number;
  queued: number;
  processing: number;
  completed: number;
  blocked_source: number;
  blocked_runtime: number;
};

export type CatastoAutoSyncDashboard = import("../elaborazioni-continuous-sync").CatastoAutoSyncDashboard;

export type CatastoRuoloAutoSyncStatus = {
  config: CatastoRuoloAutoSyncConfig;
  counts: CatastoRuoloAutoSyncStatusCounts;
  running_batch: CatastoBatch | null;
  last_batch: CatastoBatch | null;
  error_items: CatastoRuoloAutoSyncItem[];
  recent_items: CatastoRuoloAutoSyncItem[];
  scope_counts: Record<string, Record<string, number>>;
  available_credential_ids: string[];
  perpetual_error_items: CatastoPerpetualSyncItem[];
  perpetual_recent_items: CatastoPerpetualSyncItem[];
  dashboard: CatastoAutoSyncDashboard;
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

export type ElaborazioneRuoloAutoSyncConfig = CatastoRuoloAutoSyncConfig;

export type ElaborazioneRuoloAutoSyncConfigUpdateInput = CatastoRuoloAutoSyncConfigUpdateInput;

export type ElaborazioneRuoloAutoSyncItem = CatastoRuoloAutoSyncItem;

export type ElaborazioneRuoloAutoSyncStatusCounts = CatastoRuoloAutoSyncStatusCounts;

export type ElaborazioneRuoloAutoSyncStatus = CatastoRuoloAutoSyncStatus;

export type ElaborazioneBatchProgressEvent = CatastoBatchProgressEvent;

export type ElaborazioneBatchCaptchaEvent = CatastoBatchCaptchaEvent;

export type ElaborazioneBatchCompletedEvent = CatastoBatchCompletedEvent;

export type ElaborazioneRichiestaCompletedEvent = CatastoVisuraCompletedEvent;

export type ElaborazioneBatchWebSocketEvent = CatastoBatchWebSocketEvent;

export type ElaborazioneRuntimeOperatingWindow = {
  enabled: boolean;
  timezone: string;
  start_hour: number;
  end_hour: number;
  is_within_window: boolean;
  state_label: string;
  next_resume_at: string | null;
};

export type ElaborazioneRuntimeKpiBlock = {
  batches_total: number;
  requests_total: number;
  requests_completed: number;
  requests_failed: number;
  requests_skipped: number;
  requests_not_found: number;
  processed_requests: number;
  success_rate: number | null;
  throughput_per_hour: number | null;
  average_batch_duration_minutes: number | null;
  average_request_duration_seconds: number | null;
  latest_processed_at: string | null;
};

export type ElaborazioneRuntimeDailyMetric = {
  date: string;
  processed_requests: number;
  completed: number;
  failed: number;
  skipped: number;
  not_found: number;
};

export type ElaborazioneRuntimeMetrics = {
  operating_window: ElaborazioneRuntimeOperatingWindow;
  totals: ElaborazioneRuntimeKpiBlock;
  last_24_hours: ElaborazioneRuntimeKpiBlock;
  last_7_days: ElaborazioneRuntimeKpiBlock;
  recent_daily: ElaborazioneRuntimeDailyMetric[];
};

export type ElaborazioneAnprRunItem = {
  id: string;
  run_date: string;
  ruolo_year: number;
  status: string;
  daily_calls_before: number;
  daily_calls_after: number;
  subjects_selected: number;
  subjects_processed: number;
  deceased_found: number;
  errors: number;
  calls_used: number;
  started_at: string;
  completed_at: string | null;
  records: ElaborazioneAnprRunRecordItem[];
};

export type ElaborazioneAnprRunRecordItem = {
  id: string;
  subject_id: string;
  display_name: string;
  codice_fiscale: string;
  data_nascita: string | null;
  last_event_at: string;
  final_esito: string;
  error_detail: string | null;
  calls_made: number;
  call_types: string[];
};

export type ElaborazioneAnprErrorSubjectItem = {
  subject_id: string;
  display_name: string;
  codice_fiscale: string;
  data_nascita: string | null;
  stato_anpr: string;
  last_anpr_check_at: string | null;
  latest_error_at: string | null;
  latest_error_detail: string | null;
  capacitas_deceduto: boolean | null;
  capacitas_last_check_at: string | null;
};

export type ElaborazioneAnprSummary = {
  calls_today: number;
  configured_daily_limit: number;
  hard_daily_limit: number;
  effective_daily_limit: number;
  batch_size: number;
  ruolo_year: number | null;
  total_runs: number;
  total_subjects_selected: number;
  total_subjects_processed: number;
  total_deceased_found: number;
  total_errors: number;
  total_calls_used: number;
  total_error_subjects: number;
  error_subjects: ElaborazioneAnprErrorSubjectItem[];
  recent_runs: ElaborazioneAnprRunItem[];
};

export type ElaborazioneAutoJobControl = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
  detail: string | null;
  management_href: string | null;
  updated_at: string | null;
  updated_by_user_id: number | null;
};
