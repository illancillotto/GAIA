from __future__ import annotations

from uuid import UUID
from typing import Annotated
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, get_current_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import (
    WikiAuditCountRead,
    WikiAuditDailyCountRead,
    WikiAuditLatencyByModeRead,
    WikiToolAuditLogDetailResponse,
    WikiToolAuditLogListResponse,
    WikiToolAuditLogRelatedResponse,
    WikiToolAuditLogRead,
    WikiToolAuditSummaryResponse,
)
from app.modules.wiki.services.audit_read_models import (
    WikiAuditFilters,
    get_wiki_tool_audit_log,
    list_related_wiki_tool_audit_logs,
    list_wiki_tool_audit_logs,
    summarize_wiki_tool_audit_logs,
)

router = APIRouter(prefix="/audit", tags=["Wiki Audit"])


def _serialize_audit_log(item) -> WikiToolAuditLogRead:
    return WikiToolAuditLogRead(
        id=item.id,
        username=item.username,
        role=item.role,
        intent=item.intent,
        mode=item.mode,
        tool_name=item.tool_name,
        module_key=item.module_key,
        conversation_id=item.conversation_id,
        question_hash=item.question_hash,
        question_preview=item.question_preview,
        context_article=item.context_article,
        entity_key=item.entity_key,
        entity_label=item.entity_label,
        response_excerpt=item.response_excerpt,
        fallback_reason=item.fallback_reason,
        success=bool(item.success),
        found=bool(item.found),
        latency_ms=item.latency_ms,
        docs_source_count=item.docs_source_count,
        evidence_count=item.evidence_count,
        created_at=item.created_at,
    )


@router.get("/tool-calls", response_model=WikiToolAuditLogListResponse, dependencies=[RequireAdmin])
def list_tool_calls(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    tool_name: str | None = None,
    module_key: str | None = None,
    username: str | None = None,
    intent: str | None = None,
    mode: str | None = None,
    success: bool | None = None,
    conversation_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> WikiToolAuditLogListResponse:
    items, total = list_wiki_tool_audit_logs(
        db,
        filters=WikiAuditFilters(
            tool_name=tool_name,
            module_key=module_key,
            username=username,
            intent=intent,
            mode=mode,
            success=success,
            conversation_id=conversation_id,
        ),
        page=page,
        page_size=page_size,
    )
    return WikiToolAuditLogListResponse(
        items=[_serialize_audit_log(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tool-calls/export", dependencies=[RequireAdmin])
def export_tool_calls(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    tool_name: str | None = None,
    module_key: str | None = None,
    username: str | None = None,
    intent: str | None = None,
    mode: str | None = None,
    success: bool | None = None,
    conversation_id: UUID | None = None,
) -> Response:
    items, _ = list_wiki_tool_audit_logs(
        db,
        filters=WikiAuditFilters(
            tool_name=tool_name,
            module_key=module_key,
            username=username,
            intent=intent,
            mode=mode,
            success=success,
            conversation_id=conversation_id,
        ),
        page=1,
        page_size=1000,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "created_at",
            "username",
            "role",
            "intent",
            "mode",
            "tool_name",
            "module_key",
            "question_hash",
            "question_preview",
            "entity_key",
            "entity_label",
            "fallback_reason",
            "success",
            "found",
            "latency_ms",
            "docs_source_count",
            "evidence_count",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.created_at.isoformat() if item.created_at else "",
                item.username,
                item.role,
                item.intent,
                item.mode,
                item.tool_name,
                item.module_key or "",
                item.question_hash,
                item.question_preview,
                item.entity_key or "",
                item.entity_label or "",
                item.fallback_reason or "",
                int(item.success or 0),
                int(item.found or 0),
                item.latency_ms,
                item.docs_source_count,
                item.evidence_count,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="wiki-audit-tool-calls.csv"'},
    )


@router.get("/tool-calls/summary", response_model=WikiToolAuditSummaryResponse, dependencies=[RequireAdmin])
def summarize_tool_calls(
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    tool_name: str | None = None,
    module_key: str | None = None,
    username: str | None = None,
    intent: str | None = None,
    mode: str | None = None,
    success: bool | None = None,
    conversation_id: UUID | None = None,
) -> WikiToolAuditSummaryResponse:
    summary = summarize_wiki_tool_audit_logs(
        db,
        filters=WikiAuditFilters(
            tool_name=tool_name,
            module_key=module_key,
            username=username,
            intent=intent,
            mode=mode,
            success=success,
            conversation_id=conversation_id,
        ),
    )
    return WikiToolAuditSummaryResponse(
        total=summary.total,
        success_count=summary.success_count,
        denied_count=summary.denied_count,
        no_match_count=summary.no_match_count,
        docs_only_count=summary.docs_only_count,
        live_count=summary.live_count,
        logic_count=summary.logic_count,
        hybrid_count=summary.hybrid_count,
        avg_latency_ms=summary.avg_latency_ms,
        top_tools=[WikiAuditCountRead(key=item.key, count=item.count) for item in summary.top_tools],
        top_modules=[WikiAuditCountRead(key=item.key, count=item.count) for item in summary.top_modules],
        top_intents=[WikiAuditCountRead(key=item.key, count=item.count) for item in summary.top_intents],
        top_denied_tools=[WikiAuditCountRead(key=item.key, count=item.count) for item in summary.top_denied_tools],
        latency_by_mode=[
            WikiAuditLatencyByModeRead(mode=mode_key, avg_latency_ms=avg_latency_ms)
            for mode_key, avg_latency_ms in summary.latency_by_mode
        ],
        daily_counts=[
            WikiAuditDailyCountRead(day=day, total=total, denied=denied)
            for day, total, denied in summary.daily_counts
        ],
    )


@router.get("/tool-calls/{audit_id}", response_model=WikiToolAuditLogDetailResponse, dependencies=[RequireAdmin])
def get_tool_call_detail(
    audit_id: str,
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WikiToolAuditLogDetailResponse:
    try:
        parsed_audit_id = UUID(audit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audit tool call non trovato") from exc

    item = get_wiki_tool_audit_log(db, audit_id=parsed_audit_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Audit tool call non trovato")
    return WikiToolAuditLogDetailResponse(item=_serialize_audit_log(item))


@router.get("/tool-calls/{audit_id}/related", response_model=WikiToolAuditLogRelatedResponse, dependencies=[RequireAdmin])
def get_related_tool_calls(
    audit_id: str,
    _: Annotated[ApplicationUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(10, ge=1, le=25),
) -> WikiToolAuditLogRelatedResponse:
    try:
        parsed_audit_id = UUID(audit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audit tool call non trovato") from exc

    item = get_wiki_tool_audit_log(db, audit_id=parsed_audit_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Audit tool call non trovato")

    related = list_related_wiki_tool_audit_logs(db, audit_id=parsed_audit_id, limit=limit)
    return WikiToolAuditLogRelatedResponse(items=[_serialize_audit_log(row) for row in related])
