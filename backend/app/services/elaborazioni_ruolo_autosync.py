from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCredential,
    CatastoRuoloAutoSyncConfig,
    CatastoRuoloAutoSyncItem,
    CatastoRuoloAutoSyncItemStatus,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.models.elaborazioni import ElaborazioneBatch
from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.schemas.catasto import (
    CatastoBatchResponse,
    CatastoRuoloAutoSyncConfigResponse,
    CatastoRuoloAutoSyncConfigUpdateRequest,
    CatastoRuoloAutoSyncItemResponse,
    CatastoRuoloAutoSyncStatusCountsResponse,
    CatastoRuoloAutoSyncStatusResponse,
)
from app.services.catasto_comuni import get_catasto_comuni_lookup
from app.services.elaborazioni_batches import (
    BatchConflictError,
    ValidatedVisuraRow,
    create_batch_from_validated_rows,
    ensure_no_processing_batch,
    normalize_lookup_value,
    start_batch,
)
from app.services.elaborazioni_credentials import get_credential_for_user, get_runnable_credential_for_user

UTC = timezone.utc
AUTO_SYNC_RETRY_DELAY = timedelta(minutes=5)
AUTO_SYNC_BATCH_SIZE = 20
AUTO_SYNC_PENDING_BATCH_GRACE = timedelta(minutes=2)


def classify_ruolo_autosync_failure(error_message: str | None) -> str:
    message = (error_message or "").strip().lower()
    if (
        "submit visura non avanzato" in message
        or "manual captcha response missing" in message
        or "automatic captcha exhausted" in message
    ):
        return CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value
    return CatastoRuoloAutoSyncItemStatus.PENDING.value


def get_ruolo_autosync_config(db: Session, user_id: int) -> CatastoRuoloAutoSyncConfig:
    config = db.scalar(
        select(CatastoRuoloAutoSyncConfig).where(CatastoRuoloAutoSyncConfig.user_id == user_id)
    )
    if config is not None:
        return config

    credential = get_runnable_credential_for_user(db, user_id)
    config = CatastoRuoloAutoSyncConfig(
        user_id=user_id,
        credential_id=credential.id if credential is not None else None,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_ruolo_autosync_config_for_update(db: Session, user_id: int) -> CatastoRuoloAutoSyncConfig:
    config = db.scalar(
        select(CatastoRuoloAutoSyncConfig)
        .where(CatastoRuoloAutoSyncConfig.user_id == user_id)
        .with_for_update()
    )
    if config is not None:
        return config
    db.rollback()
    return get_ruolo_autosync_config(db, user_id)


def update_ruolo_autosync_config(
    db: Session,
    user_id: int,
    payload: CatastoRuoloAutoSyncConfigUpdateRequest,
) -> CatastoRuoloAutoSyncConfig:
    config = get_ruolo_autosync_config(db, user_id)
    fields = payload.model_fields_set

    if "credential_id" in fields:
        if payload.credential_id is None:
            config.credential_id = None
        else:
            credential = get_credential_for_user(db, user_id, payload.credential_id)
            if credential is None:
                raise ValueError("Credenziale SISTER non trovata")
            if not credential.active:
                raise ValueError("La credenziale selezionata non e attiva")
            config.credential_id = credential.id

    if "enabled" in fields and payload.enabled is not None:
        config.enabled = bool(payload.enabled)

    if config.enabled:
        if config.credential_id is None:
            raise ValueError("Per attivare l'autosync devi selezionare una credenziale SISTER attiva")
        selected_credential = get_credential_for_user(db, user_id, config.credential_id)
        if selected_credential is None or not selected_credential.active:
            raise ValueError("La credenziale autosync non e disponibile o non e attiva")

    config.updated_by_user_id = user_id
    config.last_error_message = None
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def refresh_ruolo_autosync_source(db: Session, user_id: int) -> dict[str, int]:
    config = get_ruolo_autosync_config(db, user_id)
    comune_lookup = get_catasto_comuni_lookup(db)
    rows = db.execute(
        select(
            RuoloParticella.id,
            RuoloParticella.cat_particella_id,
            RuoloParticella.foglio,
            RuoloParticella.particella,
            RuoloParticella.subalterno,
            RuoloPartita.comune_nome,
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .where(RuoloParticella.cat_particella_id.is_not(None))
        .order_by(RuoloParticella.anno_tributario.desc(), RuoloParticella.created_at.desc(), RuoloParticella.id.asc())
    ).all()

    existing = {
        item.ruolo_particella_id: item
        for item in db.scalars(
            select(CatastoRuoloAutoSyncItem).where(CatastoRuoloAutoSyncItem.user_id == user_id)
        ).all()
    }
    seen_source_keys: set[str] = set()
    created = 0
    updated = 0

    for ruolo_particella_id, cat_particella_id, foglio, particella, subalterno, comune_nome in rows:
        source_key = str(cat_particella_id or ruolo_particella_id)
        if source_key in seen_source_keys:
            continue
        seen_source_keys.add(source_key)

        comune = comune_lookup.get(normalize_lookup_value(comune_nome))
        item = existing.get(ruolo_particella_id)
        if item is None:
            item = CatastoRuoloAutoSyncItem(
                user_id=user_id,
                ruolo_particella_id=ruolo_particella_id,
            )
            db.add(item)
            created += 1
        else:
            updated += 1

        item.cat_particella_id = cat_particella_id
        item.comune = comune.nome if comune is not None else (comune_nome or None)
        item.comune_codice = comune.codice_sister if comune is not None else None
        item.catasto = "Terreni"
        item.foglio = str(foglio).strip() if foglio is not None else None
        item.particella = str(particella).strip() if particella is not None else None
        item.subalterno = str(subalterno).strip() if subalterno else None
        item.tipo_visura = "Sintetica"
        if comune is None:
            item.status = CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value
            item.last_error_message = f"Comune ruolo non censito in Catasto comuni: {comune_nome}"
        elif item.status == CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value:
            item.status = CatastoRuoloAutoSyncItemStatus.PENDING.value
            item.last_error_message = None
        config.last_error_message = None

    config.last_source_refresh_at = datetime.now(UTC)
    db.add(config)
    db.commit()
    return {"created": created, "updated": updated, "total_candidates": len(seen_source_keys)}


def recover_stale_pending_ruolo_autosync_batches(db: Session, user_id: int) -> int:
    now = datetime.now(UTC)
    cutoff = now - AUTO_SYNC_PENDING_BATCH_GRACE
    pending_batches = list(
        db.scalars(
            select(CatastoBatch)
            .where(
                CatastoBatch.user_id == user_id,
                CatastoBatch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value,
                CatastoBatch.status == CatastoBatchStatus.PENDING.value,
                CatastoBatch.started_at.is_(None),
                CatastoBatch.completed_at.is_(None),
                CatastoBatch.created_at < cutoff,
            )
            .order_by(CatastoBatch.created_at.asc())
        ).all()
    )
    if not pending_batches:
        return 0

    recovered = 0
    recovery_message = "Batch autosync pendente bonificato automaticamente dopo mancato avvio"
    request_error = "Richiesta rimessa in coda dopo bonifica automatica di un batch autosync mai partito."

    for batch in pending_batches:
        requests = list(
            db.scalars(
                select(CatastoVisuraRequest)
                .where(CatastoVisuraRequest.batch_id == batch.id)
                .order_by(CatastoVisuraRequest.row_index.asc())
            ).all()
        )
        request_ids = [request.id for request in requests]
        item_statement = select(CatastoRuoloAutoSyncItem).where(
            CatastoRuoloAutoSyncItem.user_id == user_id,
            CatastoRuoloAutoSyncItem.linked_batch_id == batch.id,
        )
        items = list(db.scalars(item_statement).all())
        if request_ids:
            extra_items = list(
                db.scalars(
                    select(CatastoRuoloAutoSyncItem).where(
                        CatastoRuoloAutoSyncItem.user_id == user_id,
                        CatastoRuoloAutoSyncItem.linked_request_id.in_(request_ids),
                    )
                ).all()
            )
            existing_ids = {item.id for item in items}
            items.extend(item for item in extra_items if item.id not in existing_ids)

        for item in items:
            item.status = CatastoRuoloAutoSyncItemStatus.PENDING.value
            item.linked_batch_id = None
            item.linked_request_id = None
            item.retry_after = None
            item.last_error_message = request_error

        for request in requests:
            if request.status in {
                CatastoVisuraRequestStatus.PENDING.value,
                CatastoVisuraRequestStatus.PROCESSING.value,
                CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
            }:
                request.status = CatastoVisuraRequestStatus.FAILED.value
                request.current_operation = "Bonificata dopo mancato avvio"
                request.error_message = request_error
                request.processed_at = now

        batch.status = CatastoBatchStatus.FAILED.value
        batch.current_operation = recovery_message
        batch.completed_at = now
        recovered += 1

    db.commit()
    return recovered


def reconcile_ruolo_autosync_items(db: Session, user_id: int) -> None:
    recover_stale_pending_ruolo_autosync_batches(db, user_id)
    now = datetime.now(UTC)
    items = list(
        db.scalars(select(CatastoRuoloAutoSyncItem).where(CatastoRuoloAutoSyncItem.user_id == user_id)).all()
    )
    changed = False

    for item in items:
        if item.linked_request_id is None:
            continue
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        if request is None:
            if item.status in {
                CatastoRuoloAutoSyncItemStatus.QUEUED.value,
                CatastoRuoloAutoSyncItemStatus.PROCESSING.value,
            }:
                item.status = CatastoRuoloAutoSyncItemStatus.PENDING.value
                item.retry_after = None
                changed = True
            continue

        item.attempt_count = max(item.attempt_count, request.attempts or 0)
        if request.status == CatastoVisuraRequestStatus.PENDING.value:
            item.status = CatastoRuoloAutoSyncItemStatus.QUEUED.value
            changed = True
            continue
        if request.status in {
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
        }:
            item.status = CatastoRuoloAutoSyncItemStatus.PROCESSING.value
            changed = True
            continue
        if request.status in {
            CatastoVisuraRequestStatus.COMPLETED.value,
            CatastoVisuraRequestStatus.NOT_FOUND.value,
        }:
            item.status = CatastoRuoloAutoSyncItemStatus.COMPLETED.value
            item.last_error_message = request.error_message
            item.retry_after = None
            item.last_completed_at = request.processed_at or now
            changed = True
            continue
        if request.status in {
            CatastoVisuraRequestStatus.FAILED.value,
            CatastoVisuraRequestStatus.SKIPPED.value,
        }:
            item.last_error_message = request.error_message
            classified_status = classify_ruolo_autosync_failure(request.error_message)
            item.status = classified_status
            item.retry_after = (
                None
                if classified_status == CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value
                else now + AUTO_SYNC_RETRY_DELAY
            )
            changed = True

    if changed:
        db.commit()


def ensure_ruolo_autosync_batch(db: Session, user_id: int) -> CatastoBatch | None:
    config = get_ruolo_autosync_config_for_update(db, user_id)
    reconcile_ruolo_autosync_items(db, user_id)

    if not config.enabled or config.credential_id is None:
        return None

    credential = get_credential_for_user(db, user_id, config.credential_id)
    if credential is None or not credential.active:
        config.last_error_message = "Credenziale autosync non disponibile o non attiva"
        db.add(config)
        db.commit()
        return None

    existing_processing = db.scalar(
        select(ElaborazioneBatch).where(
            ElaborazioneBatch.user_id == user_id,
            ElaborazioneBatch.status == CatastoBatchStatus.PROCESSING.value,
        )
    )
    if existing_processing is not None:
        return None

    existing_pending = db.scalar(
        select(CatastoBatch)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value,
            CatastoBatch.status == CatastoBatchStatus.PENDING.value,
            CatastoBatch.started_at.is_(None),
            CatastoBatch.completed_at.is_(None),
        )
        .order_by(CatastoBatch.created_at.asc())
    )
    if existing_pending is not None:
        try:
            return start_batch(db, user_id, existing_pending.id)
        except BatchConflictError:
            return None

    now = datetime.now(UTC)
    due_items = list(
        db.scalars(
            select(CatastoRuoloAutoSyncItem)
            .where(
                CatastoRuoloAutoSyncItem.user_id == user_id,
                CatastoRuoloAutoSyncItem.status == CatastoRuoloAutoSyncItemStatus.PENDING.value,
            )
            .order_by(
                CatastoRuoloAutoSyncItem.retry_after.asc().nullsfirst(),
                CatastoRuoloAutoSyncItem.updated_at.asc(),
                CatastoRuoloAutoSyncItem.created_at.asc(),
            )
        ).all()
    )
    runnable_items = [
        item
        for item in due_items
        if item.comune and item.comune_codice and item.foglio and item.particella
        and (item.retry_after is None or item.retry_after <= now)
    ][:AUTO_SYNC_BATCH_SIZE]

    if not runnable_items:
        return None

    rows = [
        ValidatedVisuraRow(
            row_index=index,
            search_mode="immobile",
            comune=item.comune,
            comune_codice=item.comune_codice,
            catasto=item.catasto,
            sezione=None,
            foglio=item.foglio,
            particella=item.particella,
            subalterno=item.subalterno,
            tipo_visura=item.tipo_visura,
            purpose="visura_pdf",
            target_ruolo_particella_id=item.ruolo_particella_id,
        )
        for index, item in enumerate(runnable_items, start=1)
    ]
    batch_name = f"AutoSync ruolo visure {now.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%S')}"
    batch, requests = create_batch_from_validated_rows(
        db,
        user_id,
        rows,
        batch_name,
        source_filename="ruolo_autosync",
        batch_kind=CatastoBatchKind.RUOLO_AUTOSYNC.value,
        credential_id=credential.id,
    )

    request_by_ruolo = {
        request.target_ruolo_particella_id: request
        for request in requests
        if request.target_ruolo_particella_id is not None
    }
    for item in runnable_items:
        request = request_by_ruolo.get(item.ruolo_particella_id)
        item.status = CatastoRuoloAutoSyncItemStatus.QUEUED.value
        item.linked_batch_id = batch.id
        item.linked_request_id = request.id if request is not None else None
        item.last_enqueued_at = now
        item.last_error_message = None
        item.retry_after = None

    config.last_batch_started_at = now
    config.last_error_message = None
    db.add(config)
    db.commit()
    try:
        started = start_batch(db, user_id, batch.id)
    except BatchConflictError as exc:
        cleanup_now = datetime.now(UTC)
        request_ids = {request.id for request in requests}
        for item in runnable_items:
            if item.linked_batch_id == batch.id or item.linked_request_id in request_ids:
                item.status = CatastoRuoloAutoSyncItemStatus.PENDING.value
                item.linked_batch_id = None
                item.linked_request_id = None
                item.retry_after = cleanup_now + AUTO_SYNC_RETRY_DELAY
                item.last_error_message = "Batch autosync non avviato per conflitto di concorrenza, item rimesso in coda"
        config.last_error_message = str(exc)
        db.add(config)
        db.execute(delete(CatastoVisuraRequest).where(CatastoVisuraRequest.batch_id == batch.id))
        db.delete(batch)
        db.commit()
        return None
    return started


def maintain_ruolo_autosync(db: Session, user_id: int) -> CatastoBatch | None:
    refresh_ruolo_autosync_source(db, user_id)
    return ensure_ruolo_autosync_batch(db, user_id)


def run_ruolo_autosync_maintenance_for_all_users(db: Session) -> int:
    configs = list(db.scalars(select(CatastoRuoloAutoSyncConfig).where(CatastoRuoloAutoSyncConfig.enabled.is_(True))).all())
    started = 0
    for config in configs:
        try:
            batch = maintain_ruolo_autosync(db, config.user_id)
        except Exception as exc:
            config.last_error_message = str(exc)
            db.add(config)
            db.commit()
            continue
        if batch is not None:
            started += 1
    return started


def build_ruolo_autosync_status(db: Session, user_id: int) -> CatastoRuoloAutoSyncStatusResponse:
    config = get_ruolo_autosync_config(db, user_id)
    reconcile_ruolo_autosync_items(db, user_id)
    items = list(
        db.scalars(
            select(CatastoRuoloAutoSyncItem)
            .where(CatastoRuoloAutoSyncItem.user_id == user_id)
            .order_by(CatastoRuoloAutoSyncItem.updated_at.desc(), CatastoRuoloAutoSyncItem.created_at.desc())
        ).all()
    )
    counter = Counter(item.status for item in items)
    running_batch = db.scalar(
        select(CatastoBatch).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value,
            CatastoBatch.status == CatastoBatchStatus.PROCESSING.value,
        )
    )
    last_batch = db.scalar(
        select(CatastoBatch)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind == CatastoBatchKind.RUOLO_AUTOSYNC.value,
        )
        .order_by(CatastoBatch.created_at.desc())
    )
    error_items = [
        item for item in items
        if item.status in {
            CatastoRuoloAutoSyncItemStatus.PENDING.value,
            CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value,
            CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value,
        }
        and item.last_error_message
    ][:12]

    return CatastoRuoloAutoSyncStatusResponse(
        config=CatastoRuoloAutoSyncConfigResponse.model_validate(config),
        counts=CatastoRuoloAutoSyncStatusCountsResponse(
            total=len(items),
            pending=counter.get(CatastoRuoloAutoSyncItemStatus.PENDING.value, 0),
            queued=counter.get(CatastoRuoloAutoSyncItemStatus.QUEUED.value, 0),
            processing=counter.get(CatastoRuoloAutoSyncItemStatus.PROCESSING.value, 0),
            completed=counter.get(CatastoRuoloAutoSyncItemStatus.COMPLETED.value, 0),
            blocked_source=counter.get(CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value, 0),
            blocked_runtime=counter.get(CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value, 0),
        ),
        running_batch=CatastoBatchResponse.model_validate(running_batch) if running_batch is not None else None,
        last_batch=CatastoBatchResponse.model_validate(last_batch) if last_batch is not None else None,
        error_items=[CatastoRuoloAutoSyncItemResponse.model_validate(item) for item in error_items],
        recent_items=[CatastoRuoloAutoSyncItemResponse.model_validate(item) for item in items[:12]],
    )
