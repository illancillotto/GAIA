"""Fast outbound command lane: INAZ import, then scoped GATE snapshots and ack."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.presenze.gate_router import (
    _can_view_all_data,
    _period_membership_collaborator_ids,
    _visible_team_ids_for_period,
)
from app.modules.presenze.models import (
    PresenzeAutoSyncConfig,
    PresenzeCollaborator,
    PresenzeCredential,
    PresenzeDailyRecord,
    PresenzeSyncJob,
)
from app.modules.presenze.services.gate_mobile_team_actions import canonical_gaia_user_id
from app.modules.presenze.services.sync_runtime import build_period

ACTION_TYPE = "sync_collaborator"


def _refresh_target(db: Session, action: dict) -> tuple[ApplicationUser, PresenzeCollaborator, str]:
    payload = action["payload_json"]
    actor = db.get(ApplicationUser, canonical_gaia_user_id(payload["gaia_user_id"], label="autore"))
    collaborator = db.get(PresenzeCollaborator, uuid.UUID(action["target_id"]))
    if actor is None or not actor.is_active or collaborator is None:
        raise ValueError("Utente o collaboratore non disponibile")
    if str(collaborator.id) != payload["collaborator_id"]:
        raise ValueError("Identità collaboratore incoerente")
    _assert_unique_inaz_identity(db, collaborator, payload["collaborator_gaia_user_id"])
    month = payload["month"]
    if len(month) != 7 or month[4] != "-":
        raise ValueError("Mese non valido")
    start, end = build_period(int(month[:4]), int(month[5:]))
    if not _can_refresh_collaborator(db, actor, collaborator, start, end):
        raise ValueError("Collaboratore fuori dal perimetro autorizzato")
    return actor, collaborator, month


def _can_refresh_collaborator(db, actor, collaborator, start, end) -> bool:
    if _can_view_all_data(actor) or collaborator.application_user_id == actor.id:
        return True
    teams = _visible_team_ids_for_period(db, actor, period_start=start, period_end=end)
    return collaborator.id in _period_membership_collaborator_ids(
        db, period_start=start, period_end=end, team_ids=teams
    )


def _assert_unique_inaz_identity(
    db: Session, collaborator: PresenzeCollaborator, gaia_user_id: str
) -> None:
    if collaborator.application_user_id is None or str(collaborator.application_user_id) != str(
        canonical_gaia_user_id(gaia_user_id, label="collaboratore")
    ):
        raise ValueError("Mapping canonico del collaboratore assente o incoerente")
    mappings = db.scalars(
        select(PresenzeCollaborator.id).where(
            PresenzeCollaborator.application_user_id == collaborator.application_user_id
        )
    ).all()
    if len(mappings) != 1:
        raise ValueError("Collaboratore fuori dal perimetro autorizzato")
    codes = db.scalars(
        select(PresenzeCollaborator.id).where(
            PresenzeCollaborator.employee_code == collaborator.employee_code
        )
    ).all()
    if len(codes) != 1:
        raise ValueError("Matricola INAZ ambigua: sincronizzazione singola non disponibile")


def _refresh_job(
    db: Session,
    action: dict,
    actor: ApplicationUser,
    collaborator: PresenzeCollaborator,
    month: str,
) -> PresenzeSyncJob:
    # Stable key also covers a lost HTTP response or concurrent pollers.
    job_id = uuid.uuid5(uuid.NAMESPACE_URL, "gate-collaborator-sync:" + action["id"])
    job = db.get(PresenzeSyncJob, job_id)
    if job is not None:
        return job
    config = db.get(PresenzeAutoSyncConfig, 1)
    credential = (
        db.get(PresenzeCredential, config.credential_id)
        if config and config.credential_id
        else None
    )
    if credential is None or not credential.active:
        raise ValueError(
            "Configurare una credenziale INAZ attiva nella sincronizzazione automatica GAIA"
        )
    start, end = build_period(int(month[:4]), int(month[5:]))
    job = PresenzeSyncJob(
        id=job_id,
        status="pending",
        requested_by_user_id=actor.id,
        credential_id=credential.id,
        period_start=start,
        period_end=end,
        priority=0,
        max_attempts=settings.presenze_sync_max_attempts,
        params_json={
            "auth_mode": "credential",
            "year": start.year,
            "month": start.month,
            "trigger": "gate_collaborator_refresh",
            "employee_codes": [collaborator.employee_code],
            "target_scope": "single_collaborator",
            "target_months": [month],
            "gate_action_id": action["id"],
        },
    )
    db.add(job)
    db.commit()
    return job


def _require_complete_import(job: PresenzeSyncJob, employee_code: str) -> None:
    params = job.params_json or {}
    failed = int((params.get("progress") or {}).get("failed_collaborators") or 0)
    completed = (params.get("checkpoint") or {}).get("completed_employee_codes") or []
    incomplete = (
        job.status != "completed",
        bool(job.records_errors),
        not job.records_imported,
        bool(failed),
        employee_code not in completed,
    )
    if any(incomplete):
        raise ValueError(
            "Importazione INAZ incompleta per la matricola richiesta: consultare il job GAIA"
        )


def _scoped_snapshots(
    db: Session, collaborator: PresenzeCollaborator, month: str
) -> tuple[dict, dict]:
    from app.modules.presenze.services.gate_mobile_record_items import build_presenze_record_items
    from app.services.gate_mobile_sync import (
        EXPORT_RULES_VERSION,
        RULES_VERSION,
    )

    start, end = build_period(int(month[:4]), int(month[5:]))
    snapshot_started_at = datetime.now(UTC)
    records = db.scalars(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id == collaborator.id,
            PresenzeDailyRecord.work_date >= start,
            PresenzeDailyRecord.work_date <= end,
        )
        .order_by(PresenzeDailyRecord.work_date)
    ).all()
    items, analyses = build_presenze_record_items(db, month=month, records=records)
    metadata = {
        "schema_version": 1,
        "source": "gaia",
        "month": month,
        "collaborator_id": str(collaborator.id),
        "rules_version": RULES_VERSION,
        "synced_from_gaia_at": snapshot_started_at.isoformat(),
    }
    anomalies = [
        {
            **item,
            "reasons": analyses[item["record_id"]].reasons,
            "operator_message": analyses[item["record_id"]].operator_message,
        }
        for item in items
        if analyses[item["record_id"]].severity != "none"
    ]
    return (
        {**metadata, "export_rules_version": EXPORT_RULES_VERSION, "giornaliere": items},
        {**metadata, "anomalie": anomalies},
    )


async def process_collaborator_refreshes(
    db: Session, client: httpx.AsyncClient, headers: dict
) -> None:
    response = await client.get(
        "/api/mobile/connector/presenze/pending-actions",
        params={"action_type": ACTION_TYPE},
        headers=headers,
    )
    response.raise_for_status()
    for action in response.json()["actions"]:
        if action.get("action_type") != ACTION_TYPE:
            continue
        await _process_refresh(db, client, headers, action)


async def _process_refresh(
    db: Session, client: httpx.AsyncClient, headers: dict, action: dict
) -> None:
    path = f"/api/mobile/connector/presenze/pending-actions/{action['id']}"
    try:
        actor, collaborator, month = _refresh_target(db, action)
        job = _refresh_job(db, action, actor, collaborator, month)
        if job.status in {"pending", "running"}:
            return
        _require_complete_import(job, collaborator.employee_code)
        daily, anomalies = _scoped_snapshots(db, collaborator, month)
        if not daily["giornaliere"]:
            raise ValueError("Nessuna giornaliera disponibile dopo l'importazione INAZ")
    except (ValueError, KeyError, TypeError, HTTPException) as exc:
        db.rollback()
        response = await client.post(
            path + "/fail",
            headers=headers,
            json={
                "error_code": "INAZ_COLLABORATOR_SYNC_FAILED",
                "message": str(exc)[:2000],
                "retryable": False,
            },
        )
        response.raise_for_status()
        return
    # Network/persistence failures keep the command pending for the next poll.
    for kind, snapshot in (("giornaliere", daily), ("anomalie", anomalies)):
        response = await client.post(
            f"/api/mobile/connector/presenze/{kind}/snapshot", headers=headers, json=snapshot
        )
        response.raise_for_status()
    response = await client.post(
        path + "/ack",
        headers=headers,
        json={
            "gaia_entity_type": "presenze_sync_job",
            "gaia_entity_id": str(job.id),
            "message": "Sincronizzazione INAZ e aggiornamento GATE completati",
            "details": {
                "month": month,
                "collaborator_id": str(collaborator.id),
                "records": len(daily["giornaliere"]),
            },
        },
    )
    response.raise_for_status()
