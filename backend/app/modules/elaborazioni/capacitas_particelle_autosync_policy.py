from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import and_, case, func, or_, select

from app.core.config import settings
from app.models.catasto_phase1 import CatParticella
from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest


class CapacitasParticelleAutoSyncJobRequest(CapacitasParticelleSyncJobCreateRequest):
    trigger: Literal["autosync"] = "autosync"
    refresh_days: int
    transient_retry_hours: int
    failed_retry_hours: int


def parse_particelle_job_payload(payload_json: dict | list | None):
    model = (
        CapacitasParticelleAutoSyncJobRequest
        if isinstance(payload_json, dict) and payload_json.get("trigger") == "autosync"
        else CapacitasParticelleSyncJobCreateRequest
    )
    return model.model_validate(payload_json or {})


def build_autosync_due_predicate(
    *,
    now: datetime,
    refresh_days: int,
    transient_retry_hours: int,
    failed_retry_hours: int,
):
    refresh_cutoff = now - timedelta(days=refresh_days)
    transient_cutoff = now - timedelta(hours=transient_retry_hours)
    failed_cutoff = now - timedelta(hours=failed_retry_hours)
    error = func.lower(func.coalesce(CatParticella.capacitas_last_sync_error, ""))
    transient_error = or_(
        error.contains("nosessione"),
        error.contains("sessione scaduta"),
        error.contains("timeout"),
        error.contains("temporan"),
        error.contains("connection"),
        error.contains("connession"),
        error.contains("network"),
        error.contains("errore di rete"),
        error.contains("timed out"),
        error.contains("remote disconnected"),
        error.contains("bad gateway"),
        error.contains("service unavailable"),
        error.contains("http 429"),
        error.contains("http 500"),
        error.contains("http 502"),
        error.contains("http 503"),
        error.contains("http 504"),
    )
    slow_failure = or_(
        error.contains("particella ") & error.contains(" non trovata"),
        error.contains("nessuna frazione capacitas trovata"),
    )
    eligible_failure = or_(
        CatParticella.capacitas_last_sync_at.is_(None),
        and_(transient_error, CatParticella.capacitas_last_sync_at < transient_cutoff),
        and_(slow_failure, CatParticella.capacitas_last_sync_at < refresh_cutoff),
        and_(~transient_error, ~slow_failure, CatParticella.capacitas_last_sync_at < failed_cutoff),
    )
    has_comune = or_(
        CatParticella.comune_id.is_not(None),
        func.length(func.trim(func.coalesce(CatParticella.nome_comune, ""))) > 0,
    )
    has_foglio = func.length(func.trim(func.coalesce(CatParticella.foglio, ""))) > 0
    due_status = or_(
        CatParticella.capacitas_last_sync_status.is_(None),
        and_(
            CatParticella.capacitas_last_sync_status.in_(("synced", "skipped")),
            or_(
                CatParticella.capacitas_last_sync_at.is_(None),
                CatParticella.capacitas_last_sync_at < refresh_cutoff,
            ),
        ),
        and_(CatParticella.capacitas_last_sync_status == "failed", eligible_failure),
    )
    return and_(
        CatParticella.is_current.is_(True),
        CatParticella.suppressed.is_(False),
        CatParticella.capacitas_anomaly_type.is_(None),
        has_comune,
        has_foglio,
        due_status,
    )


def build_particelle_due_predicate(
    *,
    trigger: str,
    now: datetime,
    due_before: datetime,
    refresh_days: int,
    transient_retry_hours: int,
    failed_retry_hours: int,
):
    if trigger != "autosync":
        return or_(
            CatParticella.capacitas_last_sync_at.is_(None),
            CatParticella.capacitas_last_sync_at < due_before,
        )
    return build_autosync_due_predicate(
        now=now,
        refresh_days=refresh_days,
        transient_retry_hours=transient_retry_hours,
        failed_retry_hours=failed_retry_hours,
    )


def particelle_sync_order():
    return (
        case((CatParticella.capacitas_last_sync_status.is_(None), 0), else_=1),
        CatParticella.capacitas_last_sync_at.asc().nullsfirst(),
        CatParticella.updated_at.asc(),
    )


def build_particelle_selection_query(
    *,
    payload: CapacitasParticelleSyncJobCreateRequest,
    now: datetime,
    due_before: datetime,
):
    query = (
        select(CatParticella)
        .where(CatParticella.is_current.is_(True), CatParticella.suppressed.is_(False))
        .order_by(*particelle_sync_order())
    )
    if payload.only_due:
        query = query.where(
            build_particelle_due_predicate(
                trigger=getattr(payload, "trigger", "manual"),
                now=now,
                due_before=due_before,
                refresh_days=getattr(
                    payload, "refresh_days", settings.capacitas_particelle_autosync_refresh_days
                ),
                transient_retry_hours=getattr(
                    payload,
                    "transient_retry_hours",
                    settings.capacitas_particelle_autosync_transient_retry_hours,
                ),
                failed_retry_hours=getattr(
                    payload,
                    "failed_retry_hours",
                    settings.capacitas_particelle_autosync_failed_retry_hours,
                ),
            )
        )
    return query.limit(payload.limit) if payload.limit is not None else query
