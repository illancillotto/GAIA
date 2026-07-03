from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.elaborazioni import ElaborazioneAutoJobConfig
from app.modules.utenze.anpr.models import AnprSyncConfig
from app.schemas.catasto import CatastoRuoloAutoSyncConfigUpdateRequest
from app.schemas.elaborazioni import ElaborazioneAutoJobControlResponse
from app.services.elaborazioni_ruolo_autosync import get_ruolo_autosync_config, update_ruolo_autosync_config

VISURE_NAS_ROUTER_JOB_KEY = "visure_nas_router"
WHITECOMPANY_DAILY_SYNC_JOB_KEY = "whitecompany_daily_sync"
WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY = "whitecompany_operazioni_live_sync"
ANPR_JOB_KEY = "anpr_daily_sync"
RUOLO_VISURE_AUTOSYNC_JOB_KEY = "ruolo_visure_autosync"
ELABORAZIONI_DB_BACKUP_JOB_KEY = "elaborazioni_db_backup"


@dataclass(frozen=True)
class AutoJobToggleState:
    enabled: bool
    updated_at: object | None
    updated_by_user_id: int | None


def _get_auto_job_row(db: Session, job_key: str) -> ElaborazioneAutoJobConfig | None:
    return db.scalar(
        select(ElaborazioneAutoJobConfig).where(ElaborazioneAutoJobConfig.job_key == job_key).limit(1)
    )


def get_auto_job_toggle_state(db: Session, job_key: str, *, default_enabled: bool) -> AutoJobToggleState:
    row = _get_auto_job_row(db, job_key)
    if row is None:
        return AutoJobToggleState(enabled=default_enabled, updated_at=None, updated_by_user_id=None)
    return AutoJobToggleState(enabled=row.enabled, updated_at=row.updated_at, updated_by_user_id=row.updated_by_user_id)


def set_auto_job_toggle_state(
    db: Session,
    job_key: str,
    *,
    enabled: bool,
    updated_by_user_id: int,
) -> AutoJobToggleState:
    row = _get_auto_job_row(db, job_key)
    if row is None:
        row = ElaborazioneAutoJobConfig(job_key=job_key, enabled=enabled, updated_by_user_id=updated_by_user_id)
        db.add(row)
    else:
        row.enabled = enabled
        row.updated_by_user_id = updated_by_user_id
        db.add(row)
    db.commit()
    db.refresh(row)
    return AutoJobToggleState(enabled=row.enabled, updated_at=row.updated_at, updated_by_user_id=row.updated_by_user_id)


def is_visure_nas_router_enabled(db: Session) -> bool:
    return get_auto_job_toggle_state(
        db,
        VISURE_NAS_ROUTER_JOB_KEY,
        default_enabled=settings.visure_nas_router_enabled,
    ).enabled


def is_whitecompany_daily_sync_enabled(db: Session) -> bool:
    return get_auto_job_toggle_state(
        db,
        WHITECOMPANY_DAILY_SYNC_JOB_KEY,
        default_enabled=settings.wc_sync_daily_enabled,
    ).enabled


def is_whitecompany_operazioni_live_sync_enabled(db: Session) -> bool:
    return get_auto_job_toggle_state(
        db,
        WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY,
        default_enabled=settings.wc_sync_operazioni_live_enabled,
    ).enabled


def is_elaborazioni_db_backup_enabled(db: Session) -> bool:
    return get_auto_job_toggle_state(
        db,
        ELABORAZIONI_DB_BACKUP_JOB_KEY,
        default_enabled=settings.elaborazioni_db_backup_enabled,
    ).enabled


def list_elaborazione_auto_job_controls(db: Session, *, user_id: int) -> list[ElaborazioneAutoJobControlResponse]:
    anpr_config = db.get(AnprSyncConfig, 1)
    ruolo_config = get_ruolo_autosync_config(db, user_id)
    visure_state = get_auto_job_toggle_state(
        db,
        VISURE_NAS_ROUTER_JOB_KEY,
        default_enabled=settings.visure_nas_router_enabled,
    )
    whitecompany_state = get_auto_job_toggle_state(
        db,
        WHITECOMPANY_DAILY_SYNC_JOB_KEY,
        default_enabled=settings.wc_sync_daily_enabled,
    )
    whitecompany_operazioni_live_state = get_auto_job_toggle_state(
        db,
        WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY,
        default_enabled=settings.wc_sync_operazioni_live_enabled,
    )
    db_backup_state = get_auto_job_toggle_state(
        db,
        ELABORAZIONI_DB_BACKUP_JOB_KEY,
        default_enabled=settings.elaborazioni_db_backup_enabled,
    )

    return [
        ElaborazioneAutoJobControlResponse(
            key=VISURE_NAS_ROUTER_JOB_KEY,
            label="Visure NAS",
            description="Smista automaticamente le visure pubbliche dal NAS verso l’archivio e le anomalie utenze.",
            enabled=visure_state.enabled,
            detail=f"Cron {settings.visure_nas_router_cron} · inbox {settings.visure_nas_inbox_path or 'non configurata'}",
            management_href="/utenze/visure-routing-anomalies",
            updated_at=visure_state.updated_at,
            updated_by_user_id=visure_state.updated_by_user_id,
        ),
        ElaborazioneAutoJobControlResponse(
            key=ANPR_JOB_KEY,
            label="ANPR batch",
            description="Esegue in automatico le verifiche ANPR sui soggetti a ruolo nella finestra consentita.",
            enabled=anpr_config.job_enabled if anpr_config is not None else True,
            detail=(
                f"Cron {(anpr_config.job_cron if anpr_config is not None else '0 8-17 * * *')} · cap "
                f"{anpr_config.max_calls_per_day if anpr_config is not None else settings.anpr_daily_call_hard_limit}/giorno"
            ),
            management_href="/anagrafica/anpr-config",
            updated_at=anpr_config.updated_at if anpr_config is not None else None,
            updated_by_user_id=anpr_config.updated_by_user_id if anpr_config is not None else None,
        ),
        ElaborazioneAutoJobControlResponse(
            key=RUOLO_VISURE_AUTOSYNC_JOB_KEY,
            label="AutoSync visure a ruolo",
            description="Mantiene la coda delle particelle a ruolo e avvia i batch visure quando trova nuove lavorazioni.",
            enabled=ruolo_config.enabled,
            detail=(
                "Scheduler ogni minuto"
                if ruolo_config.credential_id
                else "Scheduler ogni minuto · credenziale mancante"
            ),
            management_href="/elaborazioni/visure",
            updated_at=ruolo_config.updated_at,
            updated_by_user_id=ruolo_config.updated_by_user_id,
        ),
        ElaborazioneAutoJobControlResponse(
            key=WHITECOMPANY_DAILY_SYNC_JOB_KEY,
            label="WhiteCompany daily",
            description="Avvia la sync giornaliera WhiteCompany per le entity operative del modulo Elaborazioni/Operazioni.",
            enabled=whitecompany_state.enabled,
            detail=f"Cron {settings.wc_sync_daily_cron} · lookback {max(settings.wc_sync_daily_lookback_days, 1)} giorni",
            management_href="/elaborazioni/bonifica",
            updated_at=whitecompany_state.updated_at,
            updated_by_user_id=whitecompany_state.updated_by_user_id,
        ),
        ElaborazioneAutoJobControlResponse(
            key=WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY,
            label="WhiteCompany Operazioni live",
            description="Mantiene aggiornate ogni 10 minuti segnalazioni, prese in carico automezzi, registro rifornimenti e richieste magazzino.",
            enabled=whitecompany_operazioni_live_state.enabled,
            detail=(
                f"Ogni {max(settings.wc_sync_operazioni_live_interval_seconds, 60) // 60} minuti · "
                f"lookback {max(settings.wc_sync_operazioni_live_lookback_days, 1)} giorni"
            ),
            management_href="/elaborazioni/bonifica",
            updated_at=whitecompany_operazioni_live_state.updated_at,
            updated_by_user_id=whitecompany_operazioni_live_state.updated_by_user_id,
        ),
        ElaborazioneAutoJobControlResponse(
            key=ELABORAZIONI_DB_BACKUP_JOB_KEY,
            label="DB backup notturno",
            description="Esegue uno snapshot del database GAIA sul NAS nella finestra notturna, mantenendo gli ultimi 5 backup.",
            enabled=db_backup_state.enabled,
            detail=(
                f"Cron {settings.elaborazioni_db_backup_cron} · timezone {settings.elaborazioni_db_backup_timezone} · "
                f"retention {max(settings.elaborazioni_db_backup_retention_count, 1)} snapshot"
            ),
            management_href="/elaborazioni/settings",
            updated_at=db_backup_state.updated_at,
            updated_by_user_id=db_backup_state.updated_by_user_id,
        ),
    ]


def update_elaborazione_auto_job_control(
    db: Session,
    *,
    user_id: int,
    control_key: str,
    enabled: bool,
) -> ElaborazioneAutoJobControlResponse:
    if control_key == ANPR_JOB_KEY:
        config = db.get(AnprSyncConfig, 1)
        if config is None:
            config = AnprSyncConfig(id=1)
            db.add(config)
        config.job_enabled = enabled
        config.updated_by_user_id = user_id
        db.commit()
        db.refresh(config)
    elif control_key == RUOLO_VISURE_AUTOSYNC_JOB_KEY:
        current_config = get_ruolo_autosync_config(db, user_id)
        update_ruolo_autosync_config(
            db,
            user_id,
            CatastoRuoloAutoSyncConfigUpdateRequest(
                enabled=enabled,
                credential_id=current_config.credential_id,
            ),
        )
    elif control_key == VISURE_NAS_ROUTER_JOB_KEY:
        set_auto_job_toggle_state(db, control_key, enabled=enabled, updated_by_user_id=user_id)
    elif control_key == WHITECOMPANY_DAILY_SYNC_JOB_KEY:
        set_auto_job_toggle_state(db, control_key, enabled=enabled, updated_by_user_id=user_id)
    elif control_key == WHITECOMPANY_OPERAZIONI_LIVE_SYNC_JOB_KEY:
        set_auto_job_toggle_state(db, control_key, enabled=enabled, updated_by_user_id=user_id)
    elif control_key == ELABORAZIONI_DB_BACKUP_JOB_KEY:
        set_auto_job_toggle_state(db, control_key, enabled=enabled, updated_by_user_id=user_id)
    else:
        raise ValueError(f"Unknown auto job control: {control_key}")

    refreshed = list_elaborazione_auto_job_controls(db, user_id=user_id)
    for item in refreshed:
        if item.key == control_key:
            return item
    raise ValueError(f"Unknown auto job control: {control_key}")
