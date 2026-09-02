export type SisterPortalTotals = {
  events: number;
  executions: number;
  successes: number;
  errors: number;
  retries: number;
  cooldowns: number;
  success_rate: number;
  average_duration_ms: number | null;
  p95_duration_ms: number | null;
};

export type SisterPortalDownloadTotals = {
  total: number;
  by_visura_type: Record<string, number>;
  by_request_type: Record<string, number>;
};

export type SisterPortalTimelinePoint = {
  bucket: string;
  events: number;
  successes: number;
  errors: number;
  average_duration_ms: number | null;
};

export type SisterPortalStepMetric = {
  step: string;
  events: number;
  successes: number;
  errors: number;
  average_duration_ms: number | null;
  p95_duration_ms: number | null;
};

export type SisterPortalErrorMetric = {
  event_type: string;
  step: string;
  count: number;
  last_seen_at: string;
  http_status: number | null;
};

export type SisterPortalCredentialMetric = {
  credential_id: string | null;
  label: string;
  events: number;
  successes: number;
  errors: number;
  downloads: number;
  success_rate: number;
  last_seen_at: string;
};

export type SisterPortalAlert = {
  id: string;
  severity: "warning" | "critical";
  title: string;
  detail: string;
  active_since: string;
};

export type SisterPortalRecentEvent = {
  id: string;
  occurred_at: string;
  event_type: string;
  step: string;
  outcome: string;
  severity: string;
  duration_ms: number | null;
  http_status: number | null;
  endpoint: string | null;
  attempt: number | null;
  cooldown_seconds: number | null;
  credential_id: string | null;
  credential_label: string | null;
  batch_id: string | null;
  request_id: string | null;
};

export type SisterPortalHealth = {
  generated_at: string;
  window_hours: number;
  status: "healthy" | "degraded" | "critical" | "unknown";
  totals: SisterPortalTotals;
  downloads: SisterPortalDownloadTotals;
  timeline: SisterPortalTimelinePoint[];
  steps: SisterPortalStepMetric[];
  errors: SisterPortalErrorMetric[];
  credentials: SisterPortalCredentialMetric[];
  alerts: SisterPortalAlert[];
  recent_events: SisterPortalRecentEvent[];
};

export type SisterPortalEventList = {
  total: number;
  items: SisterPortalRecentEvent[];
};
