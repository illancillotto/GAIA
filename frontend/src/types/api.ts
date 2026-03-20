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
