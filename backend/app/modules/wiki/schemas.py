from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class WikiChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    context_article: str | None = Field(None, description="Source file da pre-caricare come contesto")
    conversation_id: uuid.UUID | None = None


class WikiChunkSource(BaseModel):
    source_file: str
    section_title: str | None
    excerpt: str  # primi 200 caratteri del chunk


class WikiEvidence(BaseModel):
    type: Literal["docs", "live_data", "logic", "inference"]
    label: str
    source_key: str
    excerpt: str | None = None
    payload_kind: str | None = None
    payload: dict[str, object] | None = None


class WikiToolCallSummary(BaseModel):
    tool_name: str
    success: bool
    redacted: bool = False


class WikiChatResponse(BaseModel):
    answer: str
    sources: list[WikiChunkSource]
    found: bool  # False se nessun chunk rilevante trovato
    evidences: list[WikiEvidence] = Field(default_factory=list)
    tool_calls: list[WikiToolCallSummary] = Field(default_factory=list)
    mode: Literal["docs_only", "live_data", "logic", "hybrid"] = "docs_only"
    conversation_id: uuid.UUID | None = None


class WikiChatStreamChunk(BaseModel):
    event: Literal["meta", "delta", "done", "error"]
    data: dict[str, object]


# ── Articles ──────────────────────────────────────────────────────────────────

class WikiArticleSummary(BaseModel):
    source_file: str
    section_title: str | None
    excerpt: str
    chunk_index: int

    model_config = {"from_attributes": True}


class WikiArticleGroup(BaseModel):
    source_file: str
    chunks: list[WikiArticleSummary]


# ── Requests ──────────────────────────────────────────────────────────────────

class WikiRequestCreate(BaseModel):
    user_question: str = Field(..., min_length=1, max_length=2000)
    agent_response: str | None = None
    category: Literal["feature_request", "bug_report", "question", "support_request"] = "feature_request"
    request_type: Literal["help_request", "bug_report", "feature_request", "access_issue", "data_issue", "other_request"] | None = None
    module_key: str | None = Field(None, max_length=64)
    page_path: str | None = Field(None, max_length=512)
    source_channel: Literal["widget", "wiki_page", "support_page", "admin_manual"] = "widget"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    impact_scope: Literal["single_user", "team", "office", "global"] | None = None
    conversation_id: uuid.UUID | None = None
    context_article: str | None = Field(None, max_length=512)
    context_entity_key: str | None = Field(None, max_length=512)
    desired_outcome: str | None = None
    observed_behavior: str | None = None
    expected_behavior: str | None = None


class WikiRequestRead(BaseModel):
    id: uuid.UUID
    user_question: str
    agent_response: str | None
    category: str
    request_type: str
    status: str
    priority: str
    severity: str
    created_by: str | None
    assigned_to: str | None
    assigned_to_name: str | None = None
    module_key: str | None = None
    page_path: str | None = None
    source_channel: str
    impact_scope: str | None = None
    conversation_id: uuid.UUID | None = None
    context_article: str | None = None
    context_entity_key: str | None = None
    dedupe_key: str | None = None
    canonical_request_id: uuid.UUID | None = None
    canonical_request_question: str | None = None
    canonical_request_status: str | None = None
    desired_outcome: str | None = None
    observed_behavior: str | None = None
    expected_behavior: str | None = None
    resolution_message: str | None = None
    last_admin_update_at: datetime | None = None
    user_last_viewed_at: datetime | None = None
    has_unread_update: bool = False
    user_feedback_rating: str | None = None
    user_feedback_notes: str | None = None
    user_feedback_submitted_at: datetime | None = None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WikiRequestStatusUpdate(BaseModel):
    status: Literal["new", "triaged", "investigating", "waiting_user", "planned", "resolved", "duplicate", "rejected"] | None = None
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    assigned_to: str | None = Field(None, max_length=256)
    resolution_message: str | None = None
    admin_notes: str | None = None


class WikiRequestDuplicateCandidateRead(BaseModel):
    id: uuid.UUID
    user_question: str
    request_type: str
    status: str
    module_key: str | None = None
    page_path: str | None = None
    created_by: str | None = None
    assigned_to_name: str | None = None
    created_at: datetime
    similarity_score: float
    match_reason: str


class WikiRequestDuplicateMarkInput(BaseModel):
    canonical_request_id: uuid.UUID
    admin_notes: str | None = None


class WikiRequestFeedbackUpdate(BaseModel):
    rating: Literal["helpful", "not_helpful"]
    notes: str | None = None


class WikiRequestAssigneeRead(BaseModel):
    username: str
    full_name: str | None = None
    role: str


class WikiRequestEventRead(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    event_type: str
    actor_username: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    payload: dict[str, object] | None = None
    created_at: datetime


class WikiSupportAnalyticsCountRead(BaseModel):
    key: str
    count: int


class WikiSupportAnalyticsSummaryRead(BaseModel):
    total_requests: int
    open_requests: int
    assigned_requests: int
    resolved_requests: int
    urgent_requests: int
    high_severity_requests: int
    feature_requests: int
    bug_reports: int
    access_issues: int
    data_issues: int
    help_requests: int
    top_request_types: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_modules: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_statuses: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_priorities: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_severities: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_pages: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_assignees: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_creators: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)
    top_impact_scopes: list[WikiSupportAnalyticsCountRead] = Field(default_factory=list)


class WikiSupportAnalyticsSeriesPointRead(BaseModel):
    metric_date: date
    period_label: str
    created_count: int
    resolved_count: int
    open_count: int
    feature_request_count: int
    bug_report_count: int
    help_request_count: int
    access_issue_count: int
    data_issue_count: int
    urgent_count: int
    high_severity_count: int


class WikiSupportAnalyticsSeriesResponse(BaseModel):
    days: int
    items: list[WikiSupportAnalyticsSeriesPointRead] = Field(default_factory=list)


class WikiConversationMessageRead(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[WikiChunkSource] = Field(default_factory=list)
    evidences: list[WikiEvidence] = Field(default_factory=list)
    tool_calls: list[WikiToolCallSummary] = Field(default_factory=list)
    mode: Literal["docs_only", "live_data", "logic", "hybrid"] | None = None
    found: bool | None = None
    created_at: datetime


class WikiConversationEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_username: str | None = None
    from_status: WikiConversationStatus | None = None
    to_status: WikiConversationStatus | None = None
    payload: dict[str, object] | None = None
    created_at: datetime


class WikiConversationContextLinkRead(BaseModel):
    href: str | None = None
    resolved: bool = False
    resolution_kind: str = "none"


class WikiConversationGovernanceConfigRead(BaseModel):
    fallback_heavy_threshold: int
    no_match_repeated_threshold: int
    high_latency_ms_threshold: int
    data_complete_from: str | None = None
    last_backfill_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None


class WikiConversationGovernanceConfigUpdate(BaseModel):
    fallback_heavy_threshold: int | None = Field(None, ge=1, le=20)
    no_match_repeated_threshold: int | None = Field(None, ge=1, le=20)
    high_latency_ms_threshold: int | None = Field(None, ge=100, le=60000)


class WikiConversationMetricsBackfillRequest(BaseModel):
    start_date: str
    end_date: str
    data_complete_from: str | None = None


class WikiConversationMetricsBackfillJobRead(BaseModel):
    id: uuid.UUID
    parent_job_id: uuid.UUID | None = None
    retry_count: int = 0
    status: str
    requested_by: str
    start_date: str
    end_date: str
    data_complete_from: str | None = None
    progress_total_days: int
    progress_completed_days: int
    progress_percent: int
    progress_message: str | None = None
    error_detail: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    queue_position: int | None = None
    is_latest_attempt: bool = False


class WikiConversationMetricsBackfillJobListResponse(BaseModel):
    items: list[WikiConversationMetricsBackfillJobRead] = Field(default_factory=list)


class WikiConversationMetricsBackfillJobChainRead(BaseModel):
    root_job_id: uuid.UUID
    chain_status: str
    retry_count_total: int = 0
    has_active_retry: bool = False
    oldest_created_at: datetime
    latest_job: WikiConversationMetricsBackfillJobRead
    items: list[WikiConversationMetricsBackfillJobRead] = Field(default_factory=list)


class WikiConversationMetricsBackfillJobChainListResponse(BaseModel):
    items: list[WikiConversationMetricsBackfillJobChainRead] = Field(default_factory=list)


class WikiConversationMetricsBackfillJobChainSummaryRead(BaseModel):
    total_chains: int = 0
    failed_chains: int = 0
    chains_with_active_retry: int = 0
    completed_chains: int = 0
    avg_retries_per_chain: float = 0
    oldest_active_chain_created_at: datetime | None = None


class WikiConversationMetricsBackfillJobChainDetailRead(BaseModel):
    root_job_id: uuid.UUID
    chain_status: str
    retry_count_total: int = 0
    has_active_retry: bool = False
    oldest_created_at: datetime
    latest_job: WikiConversationMetricsBackfillJobRead
    items: list[WikiConversationMetricsBackfillJobRead] = Field(default_factory=list)


class WikiConversationMetricsBackfillJobPruneResponse(BaseModel):
    deleted_count: int


class WikiConversationRead(BaseModel):
    id: uuid.UUID
    title: str
    created_by: str
    context_article: str | None = None
    status: WikiConversationStatus = "open"
    priority: WikiConversationPriority = "medium"
    assigned_to: str | None = None
    review_reason: WikiConversationReviewReason | None = None
    last_reviewed_at: datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    last_mode: Literal["docs_only", "live_data", "logic", "hybrid"] | None = None
    top_tool_name: str | None = None
    top_module: str | None = None
    top_intent: str | None = None
    latest_entity_key: str | None = None
    latest_context_article: str | None = None
    denied_count: int = 0
    fallback_count: int = 0
    no_match_count: int = 0
    needs_review: bool = False
    review_score: int = 0
    last_event_type: str | None = None
    last_owner_change_at: datetime | None = None
    reopen_count: int = 0
    created_at: datetime
    updated_at: datetime
    messages: list[WikiConversationMessageRead] = Field(default_factory=list)
    events: list[WikiConversationEventRead] = Field(default_factory=list)


class WikiConversationSummaryRead(BaseModel):
    id: uuid.UUID
    title: str
    created_by: str
    context_article: str | None = None
    status: WikiConversationStatus = "open"
    priority: WikiConversationPriority = "medium"
    assigned_to: str | None = None
    review_reason: WikiConversationReviewReason | None = None
    last_reviewed_at: datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    last_mode: Literal["docs_only", "live_data", "logic", "hybrid"] | None = None
    top_tool_name: str | None = None
    top_module: str | None = None
    top_intent: str | None = None
    latest_entity_key: str | None = None
    latest_context_article: str | None = None
    denied_count: int = 0
    fallback_count: int = 0
    no_match_count: int = 0
    needs_review: bool = False
    review_score: int = 0
    last_event_type: str | None = None
    last_owner_change_at: datetime | None = None
    reopen_count: int = 0
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class WikiConversationUpdate(BaseModel):
    status: WikiConversationStatus | None = None
    priority: WikiConversationPriority | None = None
    assigned_to: str | None = None


class WikiConversationFlagUpdate(BaseModel):
    review_reason: WikiConversationReviewReason = "manual_flag"


class WikiMetricCountRead(BaseModel):
    key: str
    count: int


class WikiConversationSummaryMetricsRead(BaseModel):
    total: int
    open_count: int
    in_review_count: int
    waiting_user_count: int
    resolved_count: int
    needs_review_count: int
    high_priority_count: int
    unassigned_review_count: int
    open_denied_count: int
    open_fallback_count: int
    avg_time_to_review_hours: float = 0
    avg_time_to_resolve_hours: float = 0
    top_mode: str | None = None
    top_tool: str | None = None
    top_review_reasons: list[WikiMetricCountRead] = Field(default_factory=list)
    backlog_by_status: list[WikiMetricCountRead] = Field(default_factory=list)
    backlog_by_priority: list[WikiMetricCountRead] = Field(default_factory=list)
    backlog_by_owner: list[WikiMetricCountRead] = Field(default_factory=list)
    aging_buckets: list[WikiMetricCountRead] = Field(default_factory=list)
    items_needing_review: list[WikiConversationSummaryRead] = Field(default_factory=list)


class WikiConversationMetricsSeriesPointRead(BaseModel):
    metric_date: str
    period_label: str
    created_count: int
    closed_count: int
    open_count: int
    in_review_count: int
    waiting_user_count: int
    resolved_count: int
    high_priority_count: int
    needs_review_count: int
    denied_threads_count: int
    fallback_threads_count: int
    no_match_threads_count: int
    review_entered_count: int
    reassigned_count: int
    reopened_count: int
    avg_time_to_review_hours: int
    avg_time_to_resolve_hours: int
    avg_open_to_review_hours: int
    avg_review_to_resolve_hours: int
    avg_waiting_user_hours: int


class WikiConversationMetricsSummaryRead(BaseModel):
    total_threads: int
    created_count: int
    closed_count: int
    open_count: int
    in_review_count: int
    waiting_user_count: int
    resolved_count: int
    high_priority_count: int
    needs_review_count: int
    review_entered_count: int
    reassigned_count: int
    reopened_count: int
    avg_time_to_review_hours: int
    avg_time_to_resolve_hours: int
    avg_open_to_review_hours: int
    avg_review_to_resolve_hours: int
    avg_waiting_user_hours: int
    data_complete_from: str | None = None
    last_backfill_at: datetime | None = None
    top_statuses: list[WikiMetricCountRead] = Field(default_factory=list)
    top_priorities: list[WikiMetricCountRead] = Field(default_factory=list)
    top_owners: list[WikiMetricCountRead] = Field(default_factory=list)
    top_review_reasons: list[WikiMetricCountRead] = Field(default_factory=list)
    top_event_types: list[WikiMetricCountRead] = Field(default_factory=list)


class WikiConversationMetricsSeriesResponse(BaseModel):
    dimension_type: str
    dimension_key: str | None = None
    days: int
    granularity: str
    items: list[WikiConversationMetricsSeriesPointRead]


# ── Index ─────────────────────────────────────────────────────────────────────

class WikiIndexResult(BaseModel):
    indexed_files: list[str]
    total_chunks: int
    message: str


# ── Audit ─────────────────────────────────────────────────────────────────────

class WikiToolAuditLogRead(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    intent: str
    mode: str
    tool_name: str
    module_key: str | None = None
    conversation_id: uuid.UUID | None = None
    question_hash: str
    question_preview: str
    context_article: str | None = None
    entity_key: str | None = None
    entity_label: str | None = None
    response_excerpt: str | None = None
    fallback_reason: str | None = None
    success: bool
    found: bool
    latency_ms: int
    docs_source_count: int
    evidence_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WikiToolAuditLogListResponse(BaseModel):
    items: list[WikiToolAuditLogRead]
    total: int
    page: int
    page_size: int


class WikiToolAuditLogRelatedResponse(BaseModel):
    items: list[WikiToolAuditLogRead]


class WikiAuditCountRead(BaseModel):
    key: str
    count: int


class WikiAuditLatencyByModeRead(BaseModel):
    mode: str
    avg_latency_ms: int


class WikiAuditDailyCountRead(BaseModel):
    day: str
    total: int
    denied: int


class WikiToolAuditSummaryResponse(BaseModel):
    total: int
    success_count: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int
    top_tools: list[WikiAuditCountRead]
    top_modules: list[WikiAuditCountRead]
    top_intents: list[WikiAuditCountRead]
    top_denied_tools: list[WikiAuditCountRead]
    latency_by_mode: list[WikiAuditLatencyByModeRead]
    daily_counts: list[WikiAuditDailyCountRead]


class WikiToolAuditLogDetailResponse(BaseModel):
    item: WikiToolAuditLogRead


class WikiTelemetryCountRead(BaseModel):
    key: str
    count: int


class WikiTelemetrySeriesPointRead(BaseModel):
    metric_date: str
    period_label: str
    total: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int


class WikiTelemetrySummaryResponse(BaseModel):
    total: int
    success_count: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int
    top_tools: list[WikiTelemetryCountRead]
    top_modules: list[WikiTelemetryCountRead]
    top_modes: list[WikiTelemetryCountRead]
    top_fallback_reasons: list[WikiTelemetryCountRead]


class WikiTelemetrySeriesResponse(BaseModel):
    dimension_type: str
    dimension_key: str | None = None
    days: int
    granularity: str
    items: list[WikiTelemetrySeriesPointRead]


class WikiTelemetryRefreshResponse(BaseModel):
    status: str
    days: int


class WikiTelemetryScheduleRead(BaseModel):
    enabled: bool
    cron: str
    timezone: str
    lookback_days: int


class WikiTelemetryRetentionRead(BaseModel):
    audit_retention_days: int
    daily_retention_days: int
    period_retention_days: int


class WikiTelemetryPruneResponse(BaseModel):
    status: str
    deleted_audit_rows: int
    deleted_daily_rows: int
    deleted_period_rows: int
WikiConversationStatus = Literal["open", "in_review", "waiting_user", "resolved"]
WikiConversationPriority = Literal["low", "medium", "high"]
WikiConversationReviewReason = Literal[
    "denied_present",
    "fallback_heavy",
    "no_match_repeated",
    "high_latency",
    "manual_flag",
]
