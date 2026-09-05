export type WikiRequest = {
  id: string;
  user_question: string;
  agent_response: string | null;
  category: "feature_request" | "bug_report" | "question" | "support_request" | string;
  request_type: "help_request" | "bug_report" | "feature_request" | "access_issue" | "data_issue" | "other_request" | string;
  status: "new" | "triaged" | "investigating" | "waiting_user" | "planned" | "resolved" | "duplicate" | "rejected";
  priority: "low" | "medium" | "high" | "urgent" | string;
  severity: "low" | "medium" | "high" | "critical" | string;
  created_by: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  module_key: string | null;
  page_path: string | null;
  source_channel: "widget" | "wiki_page" | "support_page" | "admin_manual" | string;
  impact_scope: "single_user" | "team" | "office" | "global" | string | null;
  conversation_id: string | null;
  context_article: string | null;
  context_entity_key: string | null;
  dedupe_key: string | null;
  canonical_request_id: string | null;
  canonical_request_question: string | null;
  canonical_request_status: string | null;
  desired_outcome: string | null;
  observed_behavior: string | null;
  expected_behavior: string | null;
  resolution_message: string | null;
  external_ticket_key: string | null;
  external_ticket_url: string | null;
  delivery_status: string | null;
  delivery_notes: string | null;
  last_admin_update_at: string | null;
  user_last_viewed_at: string | null;
  has_unread_update: boolean;
  user_feedback_rating: "helpful" | "not_helpful" | string | null;
  user_feedback_notes: string | null;
  user_feedback_submitted_at: string | null;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type WikiRequestEvent = {
  id: string;
  request_id: string;
  event_type: string;
  actor_username: string | null;
  from_status: string | null;
  to_status: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type WikiRequestArtifact = {
  id: string;
  request_id: string;
  artifact_type: "screenshot" | "ui_snapshot" | "screenshot_meta" | string;
  filename: string | null;
  mime_type: string | null;
  payload: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
};

export type WikiRequestDuplicateCandidate = {
  id: string;
  user_question: string;
  request_type: string;
  status: string;
  module_key: string | null;
  page_path: string | null;
  created_by: string | null;
  assigned_to_name: string | null;
  created_at: string;
  similarity_score: number;
  match_reason: string;
};

export type WikiRequestFamily = {
  canonical_request: WikiRequest;
  linked_duplicates: WikiRequestDuplicateCandidate[];
  family_size: number;
  affected_users: number;
  latest_created_at: string | null;
};

export type WikiRequestAssignee = {
  username: string;
  full_name: string | null;
  role: string;
};

export type WikiRequestCreateInput = {
  user_question: string;
  agent_response?: string | null;
  category: "feature_request" | "bug_report" | "question" | "support_request";
  request_type?: "help_request" | "bug_report" | "feature_request" | "access_issue" | "data_issue" | "other_request";
  module_key?: string | null;
  page_path?: string | null;
  source_channel?: "widget" | "wiki_page" | "support_page" | "admin_manual";
  severity?: "low" | "medium" | "high" | "critical";
  impact_scope?: "single_user" | "team" | "office" | "global" | null;
  conversation_id?: string | null;
  context_article?: string | null;
  context_entity_key?: string | null;
  desired_outcome?: string | null;
  observed_behavior?: string | null;
  expected_behavior?: string | null;
};

export type WikiRequestArtifactCreateInput = {
  screenshotFile?: File | null;
  screenshotMeta?: Record<string, unknown> | null;
  uiSnapshot?: Record<string, unknown> | null;
};

export type WikiRequestUpdateInput = {
  status?: "new" | "triaged" | "investigating" | "waiting_user" | "planned" | "resolved" | "duplicate" | "rejected";
  priority?: "low" | "medium" | "high" | "urgent";
  severity?: "low" | "medium" | "high" | "critical";
  assigned_to?: string | null;
  resolution_message?: string | null;
  admin_notes?: string | null;
  external_ticket_key?: string | null;
  external_ticket_url?: string | null;
  delivery_status?: "discovery" | "planned" | "in_progress" | "released" | "wont_do" | null;
  delivery_notes?: string | null;
};

export type WikiRequestMarkDuplicateInput = {
  canonical_request_id: string;
  admin_notes?: string | null;
};

export type WikiRequestMakeCanonicalInput = {
  admin_notes?: string | null;
};

export type WikiRequestFeedbackInput = {
  rating: "helpful" | "not_helpful";
  notes?: string | null;
};

export type WikiRequestReopenInput = {
  reason?: string | null;
};

export type WikiMyRequestsSummary = {
  total_requests: number;
  open_requests: number;
  unread_updates: number;
  waiting_user_requests: number;
  resolved_feedback_pending: number;
};

export type WikiSupportAnalyticsCount = {
  key: string;
  count: number;
};

export type WikiSupportAnalyticsSummary = {
  total_requests: number;
  open_requests: number;
  assigned_requests: number;
  resolved_requests: number;
  urgent_requests: number;
  high_severity_requests: number;
  feature_requests: number;
  bug_reports: number;
  access_issues: number;
  data_issues: number;
  help_requests: number;
  duplicate_requests: number;
  canonical_cases: number;
  reopened_requests: number;
  no_match_origin_requests: number;
  guardrail_origin_requests: number;
  docs_only_origin_requests: number;
  linked_ticket_requests: number;
  delivery_started_requests: number;
  released_requests: number;
  wont_do_requests: number;
  top_request_types: WikiSupportAnalyticsCount[];
  top_modules: WikiSupportAnalyticsCount[];
  top_statuses: WikiSupportAnalyticsCount[];
  top_priorities: WikiSupportAnalyticsCount[];
  top_severities: WikiSupportAnalyticsCount[];
  top_delivery_statuses: WikiSupportAnalyticsCount[];
  top_pages: WikiSupportAnalyticsCount[];
  top_assignees: WikiSupportAnalyticsCount[];
  top_creators: WikiSupportAnalyticsCount[];
  top_impact_scopes: WikiSupportAnalyticsCount[];
  top_source_channels: WikiSupportAnalyticsCount[];
};

export type WikiSupportCluster = {
  cluster_key: string;
  title: string;
  request_type: string;
  module_key: string | null;
  page_path: string | null;
  total_requests: number;
  open_requests: number;
  duplicate_requests: number;
  affected_users: number;
  canonical_case_count: number;
  latest_created_at: string;
  sample_questions: string[];
};

export type WikiSupportClustersResponse = {
  days: number;
  items: WikiSupportCluster[];
};

export type WikiSupportInsight = {
  insight_type: string;
  severity: "info" | "warning" | "critical";
  title: string;
  description: string;
  metric_value: number | string | null;
  action_hint: string | null;
  related_key: string | null;
};

export type WikiSupportInsightsResponse = {
  days: number;
  items: WikiSupportInsight[];
};

export type WikiSupportAnalyticsSeriesPoint = {
  metric_date: string;
  period_label: string;
  created_count: number;
  resolved_count: number;
  open_count: number;
  feature_request_count: number;
  bug_report_count: number;
  help_request_count: number;
  access_issue_count: number;
  data_issue_count: number;
  urgent_count: number;
  high_severity_count: number;
};

export type WikiSupportAnalyticsSeriesResponse = {
  days: number;
  items: WikiSupportAnalyticsSeriesPoint[];
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
