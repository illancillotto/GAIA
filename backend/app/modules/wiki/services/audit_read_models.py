from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import Session

from app.modules.wiki.models import WikiToolAuditLog


@dataclass(slots=True)
class WikiAuditFilters:
    tool_name: str | None = None
    module_key: str | None = None
    username: str | None = None
    intent: str | None = None
    mode: str | None = None
    success: bool | None = None
    conversation_id: UUID | None = None


@dataclass(slots=True)
class WikiAuditCountReadModel:
    key: str
    count: int


@dataclass(slots=True)
class WikiAuditSummaryReadModel:
    total: int
    success_count: int
    denied_count: int
    no_match_count: int
    docs_only_count: int
    live_count: int
    logic_count: int
    hybrid_count: int
    avg_latency_ms: int
    top_tools: list[WikiAuditCountReadModel]
    top_modules: list[WikiAuditCountReadModel]
    top_intents: list[WikiAuditCountReadModel]
    top_denied_tools: list[WikiAuditCountReadModel]
    latency_by_mode: list[tuple[str, int]]
    daily_counts: list[tuple[str, int, int]]


def _apply_filters(query, filters: WikiAuditFilters):
    if filters.tool_name:
        query = query.where(WikiToolAuditLog.tool_name == filters.tool_name)
    if filters.module_key:
        query = query.where(WikiToolAuditLog.module_key == filters.module_key)
    if filters.username:
        query = query.where(WikiToolAuditLog.username == filters.username)
    if filters.intent:
        query = query.where(WikiToolAuditLog.intent == filters.intent)
    if filters.mode:
        query = query.where(WikiToolAuditLog.mode == filters.mode)
    if filters.success is not None:
        query = query.where(WikiToolAuditLog.success == (1 if filters.success else 0))
    if filters.conversation_id is not None:
        query = query.where(WikiToolAuditLog.conversation_id == filters.conversation_id)
    return query


def list_wiki_tool_audit_logs(
    db: Session,
    *,
    filters: WikiAuditFilters,
    page: int,
    page_size: int,
) -> tuple[list[WikiToolAuditLog], int]:
    query = _apply_filters(select(WikiToolAuditLog), filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(desc(WikiToolAuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


def get_wiki_tool_audit_log(db: Session, *, audit_id) -> WikiToolAuditLog | None:
    return db.get(WikiToolAuditLog, audit_id)


def list_related_wiki_tool_audit_logs(
    db: Session,
    *,
    audit_id,
    limit: int = 10,
) -> list[WikiToolAuditLog]:
    item = db.get(WikiToolAuditLog, audit_id)
    if item is None:
        return []

    conditions = [WikiToolAuditLog.username == item.username]
    related_scopes = []
    if item.question_hash:
        related_scopes.append(WikiToolAuditLog.question_hash == item.question_hash)
    if item.entity_key:
        related_scopes.append(WikiToolAuditLog.entity_key == item.entity_key)
    if item.module_key:
        related_scopes.append(WikiToolAuditLog.module_key == item.module_key)
    if related_scopes:
        conditions.append(or_(*related_scopes))

    query = (
        select(WikiToolAuditLog)
        .where(
            WikiToolAuditLog.id != item.id,
            *conditions,
        )
        .order_by(desc(WikiToolAuditLog.created_at))
        .limit(limit)
    )
    return db.scalars(query).all()


def _top_counts(db: Session, *, filters: WikiAuditFilters, column, fallback: str = "n/d") -> list[WikiAuditCountReadModel]:
    key_expr = func.coalesce(column, fallback)
    count_expr = func.count()
    query = _apply_filters(
        select(
            key_expr.label("key"),
            count_expr.label("count"),
        ).group_by(key_expr),
        filters,
    )
    rows = db.execute(query.order_by(desc(count_expr), key_expr).limit(5)).all()
    return [WikiAuditCountReadModel(key=row.key, count=row.count) for row in rows]


def summarize_wiki_tool_audit_logs(db: Session, *, filters: WikiAuditFilters) -> WikiAuditSummaryReadModel:
    filtered = _apply_filters(
        select(
            WikiToolAuditLog.success,
            WikiToolAuditLog.found,
            WikiToolAuditLog.mode,
            WikiToolAuditLog.intent,
            WikiToolAuditLog.tool_name,
            WikiToolAuditLog.module_key,
            WikiToolAuditLog.latency_ms,
        ),
        filters,
    ).subquery()

    row = db.execute(
        select(
            func.count().label("total"),
            func.coalesce(func.sum(case((filtered.c.success == 1, 1), else_=0)), 0).label("success_count"),
            func.coalesce(func.sum(case((filtered.c.success == 0, 1), else_=0)), 0).label("denied_count"),
            func.coalesce(func.sum(case((filtered.c.found == 0, 1), else_=0)), 0).label("no_match_count"),
            func.coalesce(func.sum(case((filtered.c.mode == "docs_only", 1), else_=0)), 0).label("docs_only_count"),
            func.coalesce(func.sum(case((filtered.c.mode == "live_data", 1), else_=0)), 0).label("live_count"),
            func.coalesce(func.sum(case((filtered.c.mode == "logic", 1), else_=0)), 0).label("logic_count"),
            func.coalesce(func.sum(case((filtered.c.mode == "hybrid", 1), else_=0)), 0).label("hybrid_count"),
            func.coalesce(func.avg(filtered.c.latency_ms), 0).label("avg_latency_ms"),
        )
    ).one()

    denied_tools = _apply_filters(
        select(WikiToolAuditLog.tool_name, func.count().label("count"))
        .where(WikiToolAuditLog.success == 0)
        .group_by(WikiToolAuditLog.tool_name),
        filters,
    )
    denied_rows = db.execute(denied_tools.order_by(desc("count"), WikiToolAuditLog.tool_name).limit(5)).all()

    latency_rows = db.execute(
        _apply_filters(
            select(
                WikiToolAuditLog.mode,
                func.coalesce(func.avg(WikiToolAuditLog.latency_ms), 0).label("avg_latency_ms"),
            ).group_by(WikiToolAuditLog.mode),
            filters,
        ).order_by(WikiToolAuditLog.mode)
    ).all()

    day_expr = func.date(WikiToolAuditLog.created_at)
    daily_rows = db.execute(
        _apply_filters(
            select(
                day_expr.label("day"),
                func.count().label("total"),
                func.coalesce(func.sum(case((WikiToolAuditLog.success == 0, 1), else_=0)), 0).label("denied"),
            ).group_by(day_expr),
            filters,
        ).order_by(desc("day")).limit(7)
    ).all()

    return WikiAuditSummaryReadModel(
        total=int(row.total or 0),
        success_count=int(row.success_count or 0),
        denied_count=int(row.denied_count or 0),
        no_match_count=int(row.no_match_count or 0),
        docs_only_count=int(row.docs_only_count or 0),
        live_count=int(row.live_count or 0),
        logic_count=int(row.logic_count or 0),
        hybrid_count=int(row.hybrid_count or 0),
        avg_latency_ms=int(round(float(row.avg_latency_ms or 0))),
        top_tools=_top_counts(db, filters=filters, column=WikiToolAuditLog.tool_name),
        top_modules=_top_counts(db, filters=filters, column=WikiToolAuditLog.module_key),
        top_intents=_top_counts(db, filters=filters, column=WikiToolAuditLog.intent),
        top_denied_tools=[WikiAuditCountReadModel(key=item.tool_name, count=item.count) for item in denied_rows],
        latency_by_mode=[(item.mode, int(round(float(item.avg_latency_ms or 0)))) for item in latency_rows],
        daily_counts=[(item.day, int(item.total), int(item.denied)) for item in daily_rows],
    )
