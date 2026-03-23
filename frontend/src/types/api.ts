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
