"""Read-only, credential-free summary for the administrator home notification."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.capacitas import (
    CapacitasAnagraficaHistoryImportJob,
    CapacitasDomandeIrrigueSyncJob,
    CapacitasInCassSyncJob,
    CapacitasParticelleSyncJob,
    CapacitasTerreniSyncJob,
)
from app.models.catasto import CatastoBatch, CatastoRuoloAutoSyncConfig
from app.models.catasto_phase1 import CatAdeSyncRun
from app.models.posta_online import PostaOnlineRegisteredMailSyncJob
from app.models.sync_job import SyncJob
from app.models.wc_sync_job import WCSyncJob
from app.modules.elaborazioni.step.models import StepSyncJob
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.presenze.models import (
    PresenzeAutoSyncConfig,
    PresenzeCredential,
    PresenzeSyncJob,
)
from app.modules.utenze.anpr.models import AnprJobRun

FAILED_STATUSES = {"failed", "error", "cancelled", "partial", "completed_with_errors"}
AUTOSYNC_KINDS = ("ruolo_autosync", "perpetual_sync")


class SyncAlert(BaseModel):
    id: str
    service: str
    message: str


@dataclass(frozen=True)
class SyncSource:
    key: str
    title: str
    model: Any
    clock: str = "created_at"
    conditions: tuple = ()
    partition: Any = None


SYNC_SOURCES = (
    SyncSource("domande-irrigue", "Capacitas domande irrigue", CapacitasDomandeIrrigueSyncJob),
    SyncSource("capacitas-storico", "Capacitas anagrafica", CapacitasAnagraficaHistoryImportJob),
    SyncSource("capacitas-terreni", "Capacitas terreni", CapacitasTerreniSyncJob),
    SyncSource("capacitas", "Capacitas particelle", CapacitasParticelleSyncJob),
    SyncSource("incass", "Capacitas inCass", CapacitasInCassSyncJob),
    SyncSource("posta", "Poste Online", PostaOnlineRegisteredMailSyncJob),
    SyncSource("step", "STEP riscossione", StepSyncJob),
    SyncSource("presenze", "Presenze INAZ", PresenzeSyncJob),
    SyncSource("nas", "NAS e directory", SyncJob),
    SyncSource("mobile", "GAIA Mobile Sync", GateMobileSyncRun, "started_at"),
    SyncSource("ade", "Allineamento AdE", CatAdeSyncRun, "started_at"),
    SyncSource("anpr", "ANPR", AnprJobRun, "started_at"),
    SyncSource(
        "visure",
        "SISTER visure",
        CatastoBatch,
        conditions=(CatastoBatch.batch_kind.not_in(AUTOSYNC_KINDS),),
        partition=CatastoBatch.user_id,
    ),
    SyncSource(
        "autosync",
        "SISTER autosync",
        CatastoBatch,
        conditions=(CatastoBatch.batch_kind.in_(AUTOSYNC_KINDS),),
        partition=CatastoBatch.user_id,
    ),
    SyncSource(
        "whitecompany",
        "WhiteCompany",
        WCSyncJob,
        "started_at",
        conditions=(WCSyncJob.entity != "autodoc_vehicle_details",),
        partition=WCSyncJob.entity,
    ),
    SyncSource(
        "autodoc",
        "AUTODOC mezzi",
        WCSyncJob,
        "started_at",
        conditions=(WCSyncJob.entity == "autodoc_vehicle_details",),
    ),
)


def _job_alerts(db: Session, source: SyncSource) -> list[SyncAlert]:
    model = source.model
    order = (getattr(model, source.clock).desc(), model.id.desc())
    latest = select(model.id, model.status).where(*source.conditions).order_by(*order).limit(1)
    if source.partition is not None:
        ranked = (
            select(
                model.id,
                model.status,
                func.row_number()
                .over(partition_by=source.partition, order_by=order)
                .label("position"),
            )
            .where(*source.conditions)
            .subquery()
        )
        latest = select(ranked.c.id, ranked.c.status).where(ranked.c.position == 1)
    return [
        SyncAlert(
            id=f"{source.key}:job:{row.id}:{row.status}",
            service=source.title,
            message="L'ultima esecuzione si è interrotta o è terminata con errori.",
        )
        for row in db.execute(latest)
        if row.status in FAILED_STATUSES
    ]


def _inaz_configuration_alerts(db: Session) -> list[SyncAlert]:
    blocked = db.execute(
        select(PresenzeAutoSyncConfig.id, PresenzeAutoSyncConfig.credential_id)
        .outerjoin(
            PresenzeCredential, PresenzeCredential.id == PresenzeAutoSyncConfig.credential_id
        )
        .where(
            PresenzeAutoSyncConfig.job_enabled.is_(True),
            or_(PresenzeCredential.id.is_(None), PresenzeCredential.active.is_(False)),
        )
    )
    return [
        SyncAlert(
            id=f"presenze:credential:{row.id}:{row.credential_id}",
            service="Presenze INAZ",
            message="Sincronizzazione automatica bloccata: credenziale assente o disabilitata.",
        )
        for row in blocked
    ]


def collect_sync_alerts(db: Session) -> list[SyncAlert]:
    alerts = [alert for source in SYNC_SOURCES for alert in _job_alerts(db, source)]
    alerts.extend(_inaz_configuration_alerts(db))
    for config in db.execute(
        select(CatastoRuoloAutoSyncConfig.id, CatastoRuoloAutoSyncConfig.updated_at).where(
            CatastoRuoloAutoSyncConfig.last_error_message.is_not(None),
            CatastoRuoloAutoSyncConfig.last_error_message != "",
        )
    ):
        alerts.append(
            SyncAlert(
                id=f"autosync:planner:{config.id}:{config.updated_at.isoformat()}",
                service="SISTER autosync",
                message="Il pianificatore segnala un errore: verificare la sincronizzazione.",
            )
        )
    for job_id in db.scalars(
        select(PresenzeSyncJob.id).where(
            PresenzeSyncJob.status == "running",
            PresenzeSyncJob.lease_expires_at < datetime.now(UTC),
        )
    ):
        alerts.append(
            SyncAlert(
                id=f"presenze:lease:{job_id}",
                service="Presenze INAZ",
                message="Il worker non rinnova più la sincronizzazione in corso.",
            )
        )
    return alerts


router = APIRouter(prefix="/elaborazioni", tags=["elaborazioni"])


@router.get("/sync-alerts", response_model=list[SyncAlert])
def read_sync_alerts(
    _: Annotated[ApplicationUser, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SyncAlert]:
    return collect_sync_alerts(db)
