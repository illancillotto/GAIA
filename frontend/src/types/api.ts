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
};

export type DashboardSummary = {
  nas_users: number;
  nas_groups: number;
  shares: number;
  reviews: number;
  snapshots: number;
  sync_runs: number;
};

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
  sister_username: string;
  convenzione: string | null;
  codice_richiesta: string | null;
  ufficio_provinciale: string;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CatastoCredentialStatus = {
  configured: boolean;
  credential: CatastoCredential | null;
};

export type CatastoCredentialTestResult = {
  id: string;
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

export type CatastoSingleVisuraPayload = {
  comune: string;
  catasto: string;
  sezione?: string;
  foglio: string;
  particella: string;
  subalterno?: string;
  tipo_visura: string;
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
  | "skipped";

export type CatastoVisuraRequest = {
  id: string;
  batch_id: string;
  user_id: number;
  row_index: number;
  comune: string;
  comune_codice: string | null;
  catasto: string;
  sezione: string | null;
  foglio: string;
  particella: string;
  subalterno: string | null;
  tipo_visura: string;
  status: CatastoRequestStatus;
  current_operation: string | null;
  error_message: string | null;
  attempts: number;
  captcha_image_path: string | null;
  captcha_requested_at: string | null;
  captcha_expires_at: string | null;
  captcha_skip_requested: boolean;
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
  source_filename: string | null;
  current_operation: string | null;
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
  comune: string;
  foglio: string;
  particella: string;
  subalterno: string | null;
  catasto: string;
  tipo_visura: string;
  filename: string;
  file_size: number | null;
  codice_fiscale: string | null;
  created_at: string;
};

export type CatastoOperationResponse = {
  success: boolean;
  message: string;
};

export type CatastoBatchProgressEvent = {
  type: "progress";
  status: string;
  completed: number;
  failed: number;
  skipped: number;
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
