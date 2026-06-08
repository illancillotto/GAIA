export interface WikiChunkSource {
  source_file: string;
  section_title: string | null;
  excerpt: string;
}

export interface WikiEvidence {
  type: "docs" | "live_data" | "logic" | "inference";
  label: string;
  source_key: string;
  excerpt?: string | null;
  payload_kind?: string | null;
  payload?: Record<string, unknown> | null;
}

export interface WikiToolCallSummary {
  tool_name: string;
  success: boolean;
  redacted: boolean;
}

export interface WikiChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: WikiChunkSource[];
  evidences?: WikiEvidence[];
  tool_calls?: WikiToolCallSummary[];
  mode?: "docs_only" | "live_data" | "logic" | "hybrid";
  found?: boolean;
  conversationId?: string | null;
  timestamp: Date;
}

export interface WikiChatRequest {
  question: string;
  context_article?: string;
  conversation_id?: string;
}

export interface WikiChatResponse {
  answer: string;
  sources: WikiChunkSource[];
  found: boolean;
  evidences?: WikiEvidence[];
  tool_calls?: WikiToolCallSummary[];
  mode?: "docs_only" | "live_data" | "logic" | "hybrid";
  conversation_id?: string | null;
}

export interface WikiConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: WikiChunkSource[];
  evidences: WikiEvidence[];
  tool_calls: WikiToolCallSummary[];
  mode?: "docs_only" | "live_data" | "logic" | "hybrid" | null;
  found?: boolean | null;
  created_at: string;
}

export interface WikiConversationEvent {
  id: string;
  event_type: string;
  actor_username?: string | null;
  from_status?: "open" | "in_review" | "waiting_user" | "resolved" | null;
  to_status?: "open" | "in_review" | "waiting_user" | "resolved" | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
}

export interface WikiConversationContextLink {
  href?: string | null;
  resolved: boolean;
  resolution_kind: string;
}

export interface WikiConversation {
  id: string;
  title: string;
  created_by: string;
  context_article?: string | null;
  status: "open" | "in_review" | "waiting_user" | "resolved";
  priority: "low" | "medium" | "high";
  assigned_to?: string | null;
  review_reason?: "denied_present" | "fallback_heavy" | "no_match_repeated" | "high_latency" | "manual_flag" | null;
  last_reviewed_at?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  last_mode?: "docs_only" | "live_data" | "logic" | "hybrid" | null;
  top_tool_name?: string | null;
  top_module?: string | null;
  top_intent?: string | null;
  latest_entity_key?: string | null;
  latest_context_article?: string | null;
  denied_count: number;
  fallback_count: number;
  no_match_count: number;
  needs_review: boolean;
  review_score: number;
  last_event_type?: string | null;
  last_owner_change_at?: string | null;
  reopen_count: number;
  created_at: string;
  updated_at: string;
  messages: WikiConversationMessage[];
  events: WikiConversationEvent[];
}

export interface WikiConversationSummary {
  id: string;
  title: string;
  created_by: string;
  context_article?: string | null;
  status: "open" | "in_review" | "waiting_user" | "resolved";
  priority: "low" | "medium" | "high";
  assigned_to?: string | null;
  review_reason?: "denied_present" | "fallback_heavy" | "no_match_repeated" | "high_latency" | "manual_flag" | null;
  last_reviewed_at?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  last_mode?: "docs_only" | "live_data" | "logic" | "hybrid" | null;
  top_tool_name?: string | null;
  top_module?: string | null;
  top_intent?: string | null;
  latest_entity_key?: string | null;
  latest_context_article?: string | null;
  denied_count: number;
  fallback_count: number;
  no_match_count: number;
  needs_review: boolean;
  review_score: number;
  last_event_type?: string | null;
  last_owner_change_at?: string | null;
  reopen_count: number;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface WikiMetricCount {
  key: string;
  count: number;
}

export interface WikiConversationSummaryMetrics {
  total: number;
  open_count: number;
  in_review_count: number;
  waiting_user_count: number;
  resolved_count: number;
  needs_review_count: number;
  high_priority_count: number;
  unassigned_review_count: number;
  open_denied_count: number;
  open_fallback_count: number;
  avg_time_to_review_hours: number;
  avg_time_to_resolve_hours: number;
  review_entered_count?: number;
  reassigned_count?: number;
  reopened_count?: number;
  avg_open_to_review_hours?: number;
  avg_review_to_resolve_hours?: number;
  avg_waiting_user_hours?: number;
  top_mode?: string | null;
  top_tool?: string | null;
  top_review_reasons: WikiMetricCount[];
  backlog_by_status: WikiMetricCount[];
  backlog_by_priority: WikiMetricCount[];
  backlog_by_owner: WikiMetricCount[];
  aging_buckets: WikiMetricCount[];
  items_needing_review: WikiConversationSummary[];
}

export interface WikiArticleSummary {
  source_file: string;
  section_title: string | null;
  excerpt: string;
  chunk_index: number;
}

export interface WikiArticleGroup {
  source_file: string;
  chunks: WikiArticleSummary[];
}

export interface WikiRequestCreate {
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
}

export interface WikiRequest {
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
  last_admin_update_at: string | null;
  user_last_viewed_at: string | null;
  has_unread_update: boolean;
  user_feedback_rating: "helpful" | "not_helpful" | string | null;
  user_feedback_notes: string | null;
  user_feedback_submitted_at: string | null;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}
