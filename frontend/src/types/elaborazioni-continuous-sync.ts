export type AutoSyncCredentialSchedule = {
  timezone: "Europe/Rome";
  weekly: Record<string, Array<{ start: string; end: string }>>;
};

export type AutoSyncCredentialProfile = {
  enabled: boolean;
  schedule_enabled: boolean;
  availability_schedule: AutoSyncCredentialSchedule | null;
};

export type CatastoRuoloAutoSyncConfig = {
  enabled: boolean;
  credential_id: string | null;
  credential_ids: string[] | null;
  credential_profiles: Record<string, AutoSyncCredentialProfile> | null;
  primary_enabled: boolean;
  secondary_enabled: boolean;
  role_parcel_refresh_hours: number;
  role_subject_refresh_hours: number;
  consortium_parcel_refresh_hours: number;
  registry_subject_refresh_hours: number;
  batch_size: number;
  source_watermarks: Record<string, unknown> | null;
  last_planner_at: string | null;
  last_source_refresh_at: string | null;
  last_batch_started_at: string | null;
  last_error_message: string | null;
  updated_by_user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type CatastoRuoloAutoSyncConfigUpdateInput = Partial<Pick<
  CatastoRuoloAutoSyncConfig,
  | "enabled"
  | "credential_id"
  | "credential_ids"
  | "credential_profiles"
  | "primary_enabled"
  | "secondary_enabled"
  | "role_parcel_refresh_hours"
  | "role_subject_refresh_hours"
  | "consortium_parcel_refresh_hours"
  | "registry_subject_refresh_hours"
  | "batch_size"
>>;

export type CatastoPerpetualSyncItem = {
  id: string;
  scope: string;
  target_key: string;
  priority: number;
  search_mode: "immobile" | "soggetto" | string;
  comune: string | null;
  foglio: string | null;
  particella: string | null;
  subalterno: string | null;
  subject_kind: string | null;
  subject_identifier: string | null;
  intestazione: string | null;
  status: string;
  attempt_count: number;
  linked_batch_id: string | null;
  linked_request_id: string | null;
  last_error_message: string | null;
  retry_after: string | null;
  next_due_at: string;
  last_enqueued_at: string | null;
  last_completed_at: string | null;
  source_updated_at: string | null;
  updated_at: string;
};

export type CatastoAutoSyncDashboardSummary = {
  period_hours: number;
  batches_total: number;
  batches_active: number;
  batches_completed: number;
  batches_failed: number;
  requests_total: number;
  requests_completed: number;
  requests_failed: number;
  requests_blocked: number;
  documents_downloaded: number;
  completed_per_hour: number;
  average_batch_duration_seconds: number | null;
  last_activity_at: string | null;
};

export type CatastoAutoSyncHourly = {
  hour: string;
  completed: number;
  failed: number;
  documents_downloaded: number;
};

export type CatastoAutoSyncEvent = {
  timestamp: string;
  level: "info" | "warning" | "error" | string;
  title: string;
  detail: string | null;
  batch_id: string;
  request_id: string | null;
};

export type CatastoAutoSyncDashboard = {
  summary: CatastoAutoSyncDashboardSummary;
  hourly: CatastoAutoSyncHourly[];
  recent_batches: import("./catasto-elaborazioni").CatastoBatch[];
  events: CatastoAutoSyncEvent[];
};
