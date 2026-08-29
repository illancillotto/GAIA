export type CatastoRuoloAutoSyncConfig = {
  enabled: boolean;
  credential_id: string | null;
  credential_ids: string[] | null;
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
