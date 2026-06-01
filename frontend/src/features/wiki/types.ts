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
  agent_response?: string;
  category: "feature_request" | "bug_report" | "question";
}

export interface WikiRequest {
  id: string;
  user_question: string;
  agent_response: string | null;
  category: string;
  status: "pending" | "reviewed" | "planned" | "done";
  created_by: string | null;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}
