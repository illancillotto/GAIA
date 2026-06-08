import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.types import TypeDecorator, UserDefinedType

from app.core.database import Base


class _TSVectorType(TypeDecorator):
    """
    TSVECTOR su PostgreSQL, TEXT su SQLite (per i test in-memory).
    Non usare direttamente: usare il simbolo `TSVector` sotto.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class WikiChunk(Base):
    """
    Frammento di documento indicizzato.
    Retrieval: search_vector (PostgreSQL FTS con GIN index).
    In test SQLite: search_vector è TEXT nullable, la query FTS è mockata.
    """

    __tablename__ = "wiki_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file = Column(String(512), nullable=False, index=True)
    section_title = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    search_vector = Column(_TSVectorType, nullable=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiRequest(Base):
    """Richiesta utente: feature non implementata o domanda senza risposta."""

    __tablename__ = "wiki_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_question = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, default="feature_request")
    request_type = Column(String(32), nullable=False, default="feature_request", index=True)
    status = Column(String(32), nullable=False, default="pending")
    priority = Column(String(16), nullable=False, default="medium", index=True)
    severity = Column(String(16), nullable=False, default="medium", index=True)
    created_by = Column(String(256), nullable=True)
    assigned_to = Column(String(256), nullable=True, index=True)
    module_key = Column(String(64), nullable=True, index=True)
    page_path = Column(String(512), nullable=True)
    source_channel = Column(String(32), nullable=False, default="widget", index=True)
    impact_scope = Column(String(32), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    context_article = Column(String(512), nullable=True)
    context_entity_key = Column(String(512), nullable=True, index=True)
    dedupe_key = Column(String(128), nullable=True, index=True)
    canonical_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wiki_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    desired_outcome = Column(Text, nullable=True)
    observed_behavior = Column(Text, nullable=True)
    expected_behavior = Column(Text, nullable=True)
    resolution_message = Column(Text, nullable=True)
    last_admin_update_at = Column(DateTime, nullable=True, index=True)
    user_last_viewed_at = Column(DateTime, nullable=True, index=True)
    user_feedback_rating = Column(String(16), nullable=True, index=True)
    user_feedback_notes = Column(Text, nullable=True)
    user_feedback_submitted_at = Column(DateTime, nullable=True, index=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiRequestEvent(Base):
    """Timeline append-only delle richieste Wiki per triage e audit operativo."""

    __tablename__ = "wiki_request_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wiki_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(32), nullable=False, index=True)
    actor_username = Column(String(256), nullable=True, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class WikiConversation(Base):
    """Conversazione persistita del Wiki Agent."""

    __tablename__ = "wiki_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    created_by = Column(String(256), nullable=False, index=True)
    context_article = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    priority = Column(String(16), nullable=False, default="medium", index=True)
    assigned_to = Column(String(256), nullable=True, index=True)
    review_reason = Column(String(64), nullable=True, index=True)
    last_reviewed_at = Column(DateTime, nullable=True, index=True)
    resolved_by = Column(String(256), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), index=True)


class WikiConversationGovernanceConfig(Base):
    """Configurazione persistita per review rules e copertura metriche conversazioni."""

    __tablename__ = "wiki_conversation_governance_config"

    id = Column(Integer, primary_key=True, default=1)
    fallback_heavy_threshold = Column(Integer, nullable=False, default=2)
    no_match_repeated_threshold = Column(Integer, nullable=False, default=2)
    high_latency_ms_threshold = Column(Integer, nullable=False, default=1000)
    data_complete_from = Column(Date, nullable=True)
    last_backfill_at = Column(DateTime, nullable=True)
    updated_by = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiConversationMetricsBackfillJob(Base):
    """Job persistito per backfill asincrono delle metriche conversazioni Wiki."""

    __tablename__ = "wiki_conversation_metrics_backfill_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wiki_conversation_metrics_backfill_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retry_count = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="pending", index=True)
    requested_by = Column(String(256), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    data_complete_from = Column(Date, nullable=True)
    progress_total_days = Column(Integer, nullable=False, default=0)
    progress_completed_days = Column(Integer, nullable=False, default=0)
    progress_message = Column(String(300), nullable=True)
    error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class WikiConversationMessage(Base):
    """Messaggio persistito di una conversazione Wiki."""

    __tablename__ = "wiki_conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wiki_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    found = Column(Integer, nullable=True)
    mode = Column(String(32), nullable=True)
    sources_json = Column(Text, nullable=True)
    evidences_json = Column(Text, nullable=True)
    tool_calls_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class WikiConversationEvent(Base):
    """Storico transizioni e cambiamenti di governance per i thread Wiki."""

    __tablename__ = "wiki_conversation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wiki_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(32), nullable=False, index=True)
    actor_username = Column(String(256), nullable=True, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class WikiToolAuditLog(Base):
    """Audit append-only delle tool call del Wiki Agent."""

    __tablename__ = "wiki_tool_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(256), nullable=False, index=True)
    role = Column(String(64), nullable=False)
    intent = Column(String(32), nullable=False, index=True)
    mode = Column(String(32), nullable=False, index=True)
    tool_name = Column(String(128), nullable=False, index=True)
    module_key = Column(String(64), nullable=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    question_hash = Column(String(64), nullable=False, index=True)
    question_preview = Column(String(200), nullable=False)
    context_article = Column(String(512), nullable=True)
    entity_key = Column(String(512), nullable=True, index=True)
    entity_label = Column(String(256), nullable=True)
    response_excerpt = Column(String(300), nullable=True)
    fallback_reason = Column(String(64), nullable=True, index=True)
    success = Column(Integer, nullable=False, default=1)
    found = Column(Integer, nullable=False, default=1)
    latency_ms = Column(Integer, nullable=False, default=0)
    docs_source_count = Column(Integer, nullable=False, default=0)
    evidence_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class WikiTelemetryDailyMetric(Base):
    """Snapshot giornaliero persistente per osservabilita e trend del Wiki Agent."""

    __tablename__ = "wiki_telemetry_daily_metrics"
    __table_args__ = (
        UniqueConstraint("metric_date", "dimension_type", "dimension_key", name="uq_wiki_telemetry_daily_dimension"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date = Column(Date, nullable=False, index=True)
    dimension_type = Column(String(32), nullable=False, index=True)
    dimension_key = Column(String(256), nullable=True, index=True)
    total = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    denied_count = Column(Integer, nullable=False, default=0)
    no_match_count = Column(Integer, nullable=False, default=0)
    docs_only_count = Column(Integer, nullable=False, default=0)
    live_count = Column(Integer, nullable=False, default=0)
    logic_count = Column(Integer, nullable=False, default=0)
    hybrid_count = Column(Integer, nullable=False, default=0)
    avg_latency_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiTelemetryPeriodMetric(Base):
    """Aggregato persistente settimanale/mensile costruito sui daily snapshot."""

    __tablename__ = "wiki_telemetry_period_metrics"
    __table_args__ = (
        UniqueConstraint(
            "period_type",
            "period_start",
            "dimension_type",
            "dimension_key",
            name="uq_wiki_telemetry_period_dimension",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_type = Column(String(16), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    dimension_type = Column(String(32), nullable=False, index=True)
    dimension_key = Column(String(256), nullable=True, index=True)
    total = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    denied_count = Column(Integer, nullable=False, default=0)
    no_match_count = Column(Integer, nullable=False, default=0)
    docs_only_count = Column(Integer, nullable=False, default=0)
    live_count = Column(Integer, nullable=False, default=0)
    logic_count = Column(Integer, nullable=False, default=0)
    hybrid_count = Column(Integer, nullable=False, default=0)
    avg_latency_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiConversationDailyMetric(Base):
    """Snapshot giornaliero persistente del backlog conversazioni Wiki."""

    __tablename__ = "wiki_conversation_daily_metrics"
    __table_args__ = (
        UniqueConstraint(
            "metric_date",
            "dimension_type",
            "dimension_key",
            name="uq_wiki_conversation_daily_dimension",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date = Column(Date, nullable=False, index=True)
    dimension_type = Column(String(32), nullable=False, index=True)
    dimension_key = Column(String(256), nullable=True, index=True)
    created_count = Column(Integer, nullable=False, default=0)
    closed_count = Column(Integer, nullable=False, default=0)
    open_count = Column(Integer, nullable=False, default=0)
    in_review_count = Column(Integer, nullable=False, default=0)
    waiting_user_count = Column(Integer, nullable=False, default=0)
    resolved_count = Column(Integer, nullable=False, default=0)
    high_priority_count = Column(Integer, nullable=False, default=0)
    needs_review_count = Column(Integer, nullable=False, default=0)
    denied_threads_count = Column(Integer, nullable=False, default=0)
    fallback_threads_count = Column(Integer, nullable=False, default=0)
    no_match_threads_count = Column(Integer, nullable=False, default=0)
    review_entered_count = Column(Integer, nullable=False, default=0)
    reassigned_count = Column(Integer, nullable=False, default=0)
    reopened_count = Column(Integer, nullable=False, default=0)
    avg_time_to_review_hours = Column(Integer, nullable=False, default=0)
    avg_time_to_resolve_hours = Column(Integer, nullable=False, default=0)
    avg_open_to_review_hours = Column(Integer, nullable=False, default=0)
    avg_review_to_resolve_hours = Column(Integer, nullable=False, default=0)
    avg_waiting_user_hours = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
