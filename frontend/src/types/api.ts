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
  module_inaz: boolean;
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
  full_name: string | null;
  office_location: string | null;
  phone_extension: string | null;
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
  module_inaz: boolean;
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
  full_name?: string | null;
  office_location?: string | null;
  phone_extension?: string | null;
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
  module_inaz?: boolean;
};

export type ApplicationUserUpdateInput = {
  email?: string;
  full_name?: string | null;
  office_location?: string | null;
  phone_extension?: string | null;
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
  module_inaz?: boolean;
};

export type InazCollaborator = {
  id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  kint: string | null;
  kkint: string | null;
  employee_code: string;
  company_code: string | null;
  company_label: string | null;
  name: string;
  birth_date: string | null;
  is_active: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type InazCollaboratorListResponse = {
  items: InazCollaborator[];
  total: number;
  page: number;
  page_size: number;
};

export type InazDailyPunch = {
  id: string;
  daily_record_id: string;
  sequence: number;
  entry_time: string | null;
  exit_time: string | null;
  terminal_label: string | null;
};

export type InazDailyRecord = {
  id: string;
  collaborator_id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  work_date: string;
  schedule_code: string | null;
  teo_minutes: number | null;
  ordinary_minutes: number | null;
  absence_minutes: number | null;
  justified_minutes: number | null;
  maggiorazione_minutes: number | null;
  mpe_minutes: number | null;
  straordinario_minutes: number | null;
  km_value: number | null;
  override_straordinario_minutes: number | null;
  override_mpe_minutes: number | null;
  manual_note: string | null;
  request_type: string | null;
  request_description: string | null;
  request_status: string | null;
  request_authorized_by: string | null;
  resolved_absence_cause: string | null;
  effective_straordinario_minutes: number | null;
  effective_mpe_minutes: number | null;
  effective_extra_minutes: number | null;
  stato: string | null;
  evidenze: string | null;
  raw_weekday: string | null;
  detail_title: string | null;
  detail_status: string | null;
  detail_programmed_schedule: string | null;
  detail_effective_schedule: string | null;
  detail_time_slots: string | null;
  detail_schedule_type: string | null;
  detail_theoretical_hours: string | null;
  detail_absence_hours: string | null;
  detail_day_summary: Record<string, string>;
  detail_day_totals: Record<string, string>;
  detail_requests: Array<Record<string, string>>;
  detail_anomalies: Array<Record<string, string>>;
  detail_text: string | null;
  detail_error: string | null;
  special_day: boolean | null;
  raw_payload_json: Record<string, unknown> | unknown[] | null;
  source_job_id: string | null;
  created_at: string;
  updated_at: string;
  punches: InazDailyPunch[];
};

export type InazDailyRecordManualUpdateInput = {
  km_value?: number | null;
  override_straordinario_minutes?: number | null;
  override_mpe_minutes?: number | null;
  manual_note?: string | null;
};

export type InazDailyRecordListResponse = {
  items: InazDailyRecord[];
  total: number;
  page: number;
  page_size: number;
};

export type InazEventSummary = {
  id: string;
  collaborator_id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  period_start: string;
  period_end: string;
  event_code: string | null;
  description: string;
  valid_from: string | null;
  valid_to: string | null;
  spettante_minutes: number | null;
  fruito_minutes: number | null;
  residuo_prec_minutes: number | null;
  saldo_minutes: number | null;
  autorizzato_minutes: number | null;
  pianificato_minutes: number | null;
  richiesto_minutes: number | null;
  saldo_totale_minutes: number | null;
  unitamisura: string | null;
  raw_payload_json: Record<string, unknown> | unknown[] | null;
  source_job_id: string | null;
  created_at: string;
  updated_at: string;
};

export type InazHoliday = {
  id: number;
  holiday_date: string;
  label: string;
  company_code: string | null;
  is_workday_override: boolean;
  created_at: string;
  updated_at: string;
};

export type InazHolidayCreateInput = {
  holiday_date: string;
  label: string;
  company_code?: string | null;
  is_workday_override?: boolean;
};

export type InazHolidayUpdateInput = Partial<InazHolidayCreateInput>;

export type InazScheduleRule = {
  id: number;
  template_id: number;
  label: string | null;
  weekday: number | null;
  recurrence_kind: string;
  week_of_month: number | null;
  interval_weeks: number | null;
  anchor_date: string | null;
  start_time: string;
  end_time: string;
  season_start_month: number | null;
  season_start_day: number | null;
  season_end_month: number | null;
  season_end_day: number | null;
  applies_on_holiday: boolean;
  ordinary_label: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type InazScheduleTemplate = {
  id: number;
  code: string;
  label: string;
  company_code: string | null;
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  rules: InazScheduleRule[];
};

export type InazScheduleTemplateCreateInput = {
  code: string;
  label: string;
  company_code?: string | null;
  is_active?: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  notes?: string | null;
};

export type InazScheduleTemplateUpdateInput = Partial<InazScheduleTemplateCreateInput>;

export type InazScheduleRuleCreateInput = {
  label?: string | null;
  weekday?: number | null;
  recurrence_kind?: string;
  week_of_month?: number | null;
  interval_weeks?: number | null;
  anchor_date?: string | null;
  start_time: string;
  end_time: string;
  season_start_month?: number | null;
  season_start_day?: number | null;
  season_end_month?: number | null;
  season_end_day?: number | null;
  applies_on_holiday?: boolean;
  ordinary_label?: string | null;
  sort_order?: number;
};

export type InazScheduleRuleUpdateInput = Partial<InazScheduleRuleCreateInput>;

export type InazCollaboratorScheduleAssignment = {
  id: number;
  collaborator_id: string;
  template_id: number;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  template: InazScheduleTemplate | null;
};

export type InazCollaboratorScheduleAssignmentCreateInput = {
  template_id: number;
  valid_from?: string | null;
  valid_to?: string | null;
  notes?: string | null;
};

export type InazCollaboratorCalendarResponse = {
  collaborator: InazCollaborator;
  date_from: string;
  date_to: string;
  items: InazDailyRecord[];
};

export type InazCollaboratorSummaryResponse = {
  collaborator: InazCollaborator;
  period_start: string;
  period_end: string;
  items: InazEventSummary[];
};

export type InazImportPreviewCollaborator = {
  employee_code: string;
  company_code: string | null;
  name: string;
  application_user_id: number | null;
  total_daily_rows: number;
  total_summary_rows: number;
  period_start: string;
  period_end: string;
};

export type InazImportPreviewResponse = {
  total_collaborators: number;
  total_daily_rows: number;
  total_summary_rows: number;
  collaborators: InazImportPreviewCollaborator[];
  errors: string[];
};

export type InazImportJob = {
  id: string;
  status: string;
  filename: string | null;
  requested_by_user_id: number;
  target_user_id: number | null;
  date_from: string | null;
  date_to: string | null;
  total_records: number;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
  error_detail: string | null;
  params_json: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type InazImportJobListResponse = {
  items: InazImportJob[];
  total: number;
};

export type InazCredential = {
  id: number;
  application_user_id: number;
  label: string;
  username: string;
  active: boolean;
  last_used_at: string | null;
  last_authenticated_url: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
};

export type InazCredentialCreateInput = {
  label: string;
  username: string;
  password: string;
  active: boolean;
};

export type InazCredentialUpdateInput = {
  label?: string;
  username?: string;
  password?: string;
  active?: boolean;
};

export type InazCredentialTestResult = {
  ok: boolean;
  authenticated_url: string | null;
  cookies: string | null;
  error: string | null;
};

export type InazSyncJobCreateInput = {
  year: number;
  month: number;
  credential_id: number;
  collaborator_limit?: number | null;
};

export type InazSyncJobProgress = {
  state?: string;
  job_id?: string;
  attempt_count?: number;
  started_at?: string;
  finished_at?: string;
  completed_collaborators?: number;
  failed_collaborators?: number;
  total_collaborators?: number;
  last_event?: string;
  last_event_at?: string;
  error_count?: number;
  resumed?: boolean;
  pending_collaborators?: number;
  index?: number;
  total?: number;
  employee_code?: string;
  name?: string;
  elapsed_seconds?: number;
  daily_rows?: number;
  summary_rows?: number;
  error?: string;
};

export type InazSyncJob = {
  id: string;
  status: string;
  requested_by_user_id: number;
  credential_id: number | null;
  import_job_id: string | null;
  period_start: string;
  period_end: string;
  collaborator_limit: number | null;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
  json_artifact_path: string | null;
  worker_log_path: string | null;
  worker_pid: number | null;
  attempt_count: number;
  max_attempts: number;
  error_detail: string | null;
  params_json: {
    progress?: InazSyncJobProgress;
    [key: string]: unknown;
  } | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type InazSyncJobListResponse = {
  items: InazSyncJob[];
  total: number;
};

export type InazImportJsonResponse = {
  job: InazImportJob;
  preview: InazImportPreviewResponse;
};

export type DashboardSummary = {
  nas_users: number;
  nas_groups: number;
  shares: number;
  reviews: number;
  snapshots: number;
  sync_runs: number;
};

export type WikiToolAuditLog = {
  id: string;
  username: string;
  role: string;
  intent: string;
  mode: string;
  tool_name: string;
  module_key: string | null;
  conversation_id: string | null;
  question_hash: string;
  question_preview: string;
  context_article: string | null;
  entity_key: string | null;
  entity_label: string | null;
  response_excerpt: string | null;
  fallback_reason: string | null;
  success: boolean;
  found: boolean;
  latency_ms: number;
  docs_source_count: number;
  evidence_count: number;
  created_at: string;
};

export type WikiToolAuditLogListResponse = {
  items: WikiToolAuditLog[];
  total: number;
  page: number;
  page_size: number;
};

export type WikiAuditCount = {
  key: string;
  count: number;
};

export type WikiAuditLatencyByMode = {
  mode: string;
  avg_latency_ms: number;
};

export type WikiAuditDailyCount = {
  day: string;
  total: number;
  denied: number;
};

export type WikiToolAuditSummary = {
  total: number;
  success_count: number;
  denied_count: number;
  no_match_count: number;
  docs_only_count: number;
  live_count: number;
  logic_count: number;
  hybrid_count: number;
  avg_latency_ms: number;
  top_tools: WikiAuditCount[];
  top_modules: WikiAuditCount[];
  top_intents: WikiAuditCount[];
  top_denied_tools: WikiAuditCount[];
  latency_by_mode: WikiAuditLatencyByMode[];
  daily_counts: WikiAuditDailyCount[];
};

export type WikiToolAuditLogDetailResponse = {
  item: WikiToolAuditLog;
};

export type WikiToolAuditLogRelatedResponse = {
  items: WikiToolAuditLog[];
};

export type WikiTelemetryCount = {
  key: string;
  count: number;
};

export type WikiTelemetrySeriesPoint = {
  metric_date: string;
  period_label: string;
  total: number;
  denied_count: number;
  no_match_count: number;
  docs_only_count: number;
  live_count: number;
  logic_count: number;
  hybrid_count: number;
  avg_latency_ms: number;
};

export type WikiTelemetrySummary = {
  total: number;
  success_count: number;
  denied_count: number;
  no_match_count: number;
  docs_only_count: number;
  live_count: number;
  logic_count: number;
  hybrid_count: number;
  avg_latency_ms: number;
  top_tools: WikiTelemetryCount[];
  top_modules: WikiTelemetryCount[];
  top_modes: WikiTelemetryCount[];
  top_fallback_reasons: WikiTelemetryCount[];
};

export type WikiTelemetrySeriesResponse = {
  dimension_type: string;
  dimension_key: string | null;
  days: number;
  granularity: string;
  items: WikiTelemetrySeriesPoint[];
};

export type WikiTelemetryRefreshResponse = {
  status: string;
  days: number;
};

export type WikiTelemetrySchedule = {
  enabled: boolean;
  cron: string;
  timezone: string;
  lookback_days: number;
};

export type WikiTelemetryRetention = {
  audit_retention_days: number;
  daily_retention_days: number;
  period_retention_days: number;
};

export type WikiTelemetryPruneResponse = {
  status: string;
  deleted_audit_rows: number;
  deleted_daily_rows: number;
  deleted_period_rows: number;
};

export type WikiConversationMetricCount = {
  key: string;
  count: number;
};

export type WikiConversationContextLink = {
  href: string | null;
  resolved: boolean;
  resolution_kind: string;
};

export type WikiConversationGovernanceConfig = {
  fallback_heavy_threshold: number;
  no_match_repeated_threshold: number;
  high_latency_ms_threshold: number;
  data_complete_from: string | null;
  last_backfill_at: string | null;
  updated_by: string | null;
  updated_at: string | null;
};

export type WikiConversationMetricsBackfillJob = {
  id: string;
  parent_job_id: string | null;
  retry_count: number;
  status: string;
  requested_by: string;
  start_date: string;
  end_date: string;
  data_complete_from: string | null;
  progress_total_days: number;
  progress_completed_days: number;
  progress_percent: number;
  progress_message: string | null;
  error_detail: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  queue_position: number | null;
  is_latest_attempt: boolean;
};

export type WikiConversationMetricsBackfillJobChain = {
  root_job_id: string;
  chain_status: string;
  retry_count_total: number;
  has_active_retry: boolean;
  oldest_created_at: string;
  latest_job: WikiConversationMetricsBackfillJob;
  items: WikiConversationMetricsBackfillJob[];
};

export type WikiConversationMetricsBackfillJobChainListResponse = {
  items: WikiConversationMetricsBackfillJobChain[];
};

export type WikiConversationMetricsBackfillJobChainSummary = {
  total_chains: number;
  failed_chains: number;
  chains_with_active_retry: number;
  completed_chains: number;
  avg_retries_per_chain: number;
  oldest_active_chain_created_at: string | null;
};

export type WikiConversationMetricsBackfillJobChainDetail = {
  root_job_id: string;
  chain_status: string;
  retry_count_total: number;
  has_active_retry: boolean;
  oldest_created_at: string;
  latest_job: WikiConversationMetricsBackfillJob;
  items: WikiConversationMetricsBackfillJob[];
};

export type WikiConversationMetricsBackfillJobPruneResponse = {
  deleted_count: number;
};

export type WikiConversationMetricsSummary = {
  total_threads: number;
  created_count: number;
  closed_count: number;
  open_count: number;
  in_review_count: number;
  waiting_user_count: number;
  resolved_count: number;
  high_priority_count: number;
  needs_review_count: number;
  review_entered_count: number;
  reassigned_count: number;
  reopened_count: number;
  avg_time_to_review_hours: number;
  avg_time_to_resolve_hours: number;
  avg_open_to_review_hours: number;
  avg_review_to_resolve_hours: number;
  avg_waiting_user_hours: number;
  data_complete_from: string | null;
  last_backfill_at: string | null;
  top_statuses: WikiConversationMetricCount[];
  top_priorities: WikiConversationMetricCount[];
  top_owners: WikiConversationMetricCount[];
  top_review_reasons: WikiConversationMetricCount[];
  top_event_types: WikiConversationMetricCount[];
};

export type WikiConversationMetricsSeriesPoint = {
  metric_date: string;
  period_label: string;
  created_count: number;
  closed_count: number;
  open_count: number;
  in_review_count: number;
  waiting_user_count: number;
  resolved_count: number;
  high_priority_count: number;
  needs_review_count: number;
  denied_threads_count: number;
  fallback_threads_count: number;
  no_match_threads_count: number;
  review_entered_count: number;
  reassigned_count: number;
  reopened_count: number;
  avg_time_to_review_hours: number;
  avg_time_to_resolve_hours: number;
  avg_open_to_review_hours: number;
  avg_review_to_resolve_hours: number;
  avg_waiting_user_hours: number;
};

export type WikiConversationMetricsSeriesResponse = {
  dimension_type: string;
  dimension_key: string | null;
  days: number;
  granularity: string;
  items: WikiConversationMetricsSeriesPoint[];
};

export type NetworkDashboardSummary = {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  open_alerts: number;
  firewalls_online: number;
  scans_last_24h: number;
  floor_plans: number;
  latest_scan_at: string | null;
};

export type NetworkStatisticsCountItem = {
  key: string;
  label: string;
  count: number;
};

export type NetworkStatisticsTrafficItem = {
  label: string;
  ip_address: string | null;
  device_id: number | null;
  events_count: number;
  bytes_in: number;
  bytes_out: number;
  bytes_total: number;
  tracked_subject_id: number | null;
};

export type NetworkStatisticsTimelinePoint = {
  bucket: string;
  events_count: number;
  bytes_in: number;
  bytes_out: number;
};

export type NetworkStatisticsSummary = {
  window_hours: number;
  generated_at: string;
  total_devices: number;
  active_devices: number;
  retired_devices: number;
  online_devices: number;
  offline_devices: number;
  known_devices: number;
  unknown_devices: number;
  monitored_devices: number;
  assigned_devices: number;
  unassigned_devices: number;
  placeholder_profiles: number;
  devices_with_traffic: number;
  firewall_count: number;
  open_alerts: number;
  total_events: number;
  allowed_events: number;
  blocked_events: number;
  bytes_in: number;
  bytes_out: number;
  unique_external_peers: number;
  unique_domains: number;
  top_device_types: NetworkStatisticsCountItem[];
  top_vendors: NetworkStatisticsCountItem[];
  top_offices: NetworkStatisticsCountItem[];
  top_assignees: NetworkStatisticsCountItem[];
  severity_breakdown: NetworkStatisticsCountItem[];
  protocol_breakdown: NetworkStatisticsCountItem[];
  top_event_types: NetworkStatisticsCountItem[];
  top_firewall_rules: NetworkStatisticsCountItem[];
  top_domains: NetworkStatisticsTrafficItem[];
  top_destinations: NetworkStatisticsTrafficItem[];
  top_source_devices: NetworkStatisticsTrafficItem[];
  hourly_timeline: NetworkStatisticsTimelinePoint[];
};

export type NetworkAssignedUserSummary = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  full_name: string | null;
  office_location: string | null;
  phone_extension: string | null;
  is_placeholder_profile: boolean;
};

export type NetworkTrackedSubjectActivityEvent = {
  id: number;
  firewall_id: number;
  device_id: number | null;
  event_type: string;
  severity: string;
  protocol: string | null;
  src_ip: string | null;
  src_device_label: string | null;
  dst_ip: string | null;
  dst_device_label: string | null;
  domain: string | null;
  url: string | null;
  bytes_in: number;
  bytes_out: number;
  matched_on: string;
  matched_value: string;
  observed_at: string;
};

export type NetworkTrackedSubjectActivitySummary = {
  window_hours: number;
  total_events: number;
  allowed_events: number;
  blocked_events: number;
  bytes_in: number;
  bytes_out: number;
  last_observed_at: string | null;
  recent_events: NetworkTrackedSubjectActivityEvent[];
};

export type NetworkTrackedSubject = {
  id: number;
  entity_type: "device" | "ip" | "domain" | "url";
  normalized_value: string;
  value: string;
  label: string | null;
  resolved_label: string;
  notes: string | null;
  is_active: boolean;
  device_id: number | null;
  device_label: string | null;
  created_by_user_id: number | null;
  created_by_username: string | null;
  created_at: string;
  updated_at: string;
  activity_summary: NetworkTrackedSubjectActivitySummary | null;
  scan_history: {
    scan_id: number;
    observed_at: string;
    status: string;
    hostname: string | null;
    ip_address: string;
    open_ports: string | null;
  }[];
};

export type NetworkDevice = {
  id: number;
  last_scan_id: number | null;
  assigned_user_id: number | null;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  hostname_source: string | null;
  display_name: string | null;
  resolved_label: string;
  label_source: string;
  lifecycle_state: "active" | "retired";
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
  retired_at: string | null;
  assigned_user: NetworkAssignedUserSummary | null;
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
    resolved_label: string | null;
    label_source: string | null;
    assigned_user_label: string | null;
    open_ports: string | null;
  }[];
  traffic_summary: {
    window_hours: number;
    total_events: number;
    allowed_events: number;
    blocked_events: number;
    bytes_in: number;
    bytes_out: number;
    last_observed_at: string | null;
    top_peers: {
      ip_address: string;
      label: string | null;
      events_count: number;
      bytes_in: number;
      bytes_out: number;
      tracked_subject_id: number | null;
    }[];
    recent_events: {
      id: number;
      event_type: string;
      severity: string;
      protocol: string | null;
      src_ip: string | null;
      dst_ip: string | null;
      peer_ip: string | null;
      peer_label: string | null;
      bytes_in: number;
      bytes_out: number;
      observed_at: string;
      tracked_peer_ip_subject_id: number | null;
      tracked_peer_label_subject_id: number | null;
      tracked_url_subject_id: number | null;
    }[];
  } | null;
};

export type NetworkDeviceUpdateInput = {
  display_name?: string | null;
  lifecycle_state?: "active" | "retired" | null;
  asset_label?: string | null;
  model_name?: string | null;
  device_type?: string | null;
  operating_system?: string | null;
  location_hint?: string | null;
  notes?: string | null;
  assigned_user_id?: number | null;
  is_known_device?: boolean;
  is_monitored?: boolean;
};

export type NetworkDeviceBulkUpdateInput = {
  device_ids: number[];
  is_known_device?: boolean | null;
  location_hint?: string | null;
  notes_append?: string | null;
};

export type NetworkDeviceBulkUpdateResponse = {
  updated_count: number;
  items: NetworkDevice[];
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

export type NetworkFirewall = {
  id: number;
  vendor: string;
  name: string;
  model_name: string | null;
  serial_number: string | null;
  management_ip: string | null;
  status: string;
  metadata_sources: Record<string, string> | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type NetworkFirewallEvent = {
  id: number;
  firewall_id: number;
  device_id: number | null;
  source: string;
  event_type: string;
  severity: string;
  log_id: string | null;
  message: string | null;
  src_ip: string | null;
  src_device_label: string | null;
  dst_ip: string | null;
  dst_device_label: string | null;
  protocol: string | null;
  raw_payload: Record<string, unknown> | null;
  observed_at: string;
  tracked_src_ip_subject_id: number | null;
  tracked_dst_ip_subject_id: number | null;
  tracked_domain_subject_id: number | null;
  tracked_url_subject_id: number | null;
};

export type NetworkTrackedSubjectCreateInput = {
  entity_type: "device" | "ip" | "domain" | "url";
  value?: string | null;
  device_id?: number | null;
  label?: string | null;
  notes?: string | null;
};

export type NetworkTrackedSubjectUpdateInput = {
  label?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

export type NetworkFirewallMetric = {
  id: number;
  firewall_id: number;
  metric_key: string;
  metric_value: number | null;
  metric_text: string | null;
  unit: string | null;
  severity: string;
  raw_payload: Record<string, unknown> | null;
  observed_at: string;
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

export type NetworkScanTriggerInput = {
  scan_type?: "incremental" | "arp";
  network_range?: string;
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
  resolved_label: string | null;
  label_source: string | null;
  assigned_user_label: string | null;
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
  continue_on_error?: boolean;
  throttle_ms?: number;
};

export type CapacitasInCassRuoloHarvestInput = {
  credential_id?: number | null;
  anno?: number | null;
  chunk_size?: number;
  limit_subjects?: number | null;
  exclude_synced_subjects?: boolean;
  include_details?: boolean;
  include_partitario?: boolean;
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
};

export type CapacitasInCassSyncItemResult = {
  subject_id: string;
  identifier: string | null;
  display_name: string | null;
  status: string;
  notices_found: number;
  notices_synced: number;
  error: string | null;
};

export type CapacitasInCassSyncJobResult = {
  items: CapacitasInCassSyncItemResult[];
  processed_subjects: number;
  failed_subjects: number;
  notices_found: number;
  notices_synced: number;
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
  captcha_manual_solution?: string | null;
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
  total_error_subjects: number;
  error_subjects: ElaborazioneAnprErrorSubjectItem[];
  recent_runs: ElaborazioneAnprRunItem[];
};
