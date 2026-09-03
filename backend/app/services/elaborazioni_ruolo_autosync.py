from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC as UTC_TZ
from datetime import datetime, timedelta
from functools import wraps
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCredential,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoRuoloAutoSyncItem,
    CatastoRuoloAutoSyncItemStatus,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.models.elaborazioni import ElaborazioneBatch
from app.modules.ruolo.models import RuoloParticella, RuoloPartita
from app.schemas.catasto import (
    CatastoAutoSyncCredentialProfile,
    CatastoBatchResponse,
    CatastoPerpetualSyncItemResponse,
    CatastoRuoloAutoSyncConfigResponse,
    CatastoRuoloAutoSyncConfigUpdateRequest,
    CatastoRuoloAutoSyncItemResponse,
    CatastoRuoloAutoSyncStatusCountsResponse,
    CatastoRuoloAutoSyncStatusResponse,
)
from app.services.catasto_comuni import get_catasto_comuni_lookup
from app.services.elaborazioni_autosync_dashboard import build_autosync_dashboard
from app.services.elaborazioni_batches import (
    RELEASE_REQUESTED_OPERATION,
    BatchConflictError,
    ValidatedVisuraRow,
    create_batch_from_validated_rows,
    get_batch_requests,
    mark_request_released,
    normalize_lookup_value,
    recalculate_batch_counters,
    start_batch,
)
from app.services.elaborazioni_credentials import (
    get_credential_for_user,
    get_runnable_credential_for_user,
)
from app.services.elaborazioni_perpetual_sync import (
    available_perpetual_credentials,
    maintain_perpetual_sync,
    perpetual_sync_counts,
    refresh_perpetual_sync_sources,
)

UTC = UTC_TZ
AUTO_SYNC_RETRY_DELAY = timedelta(minutes=5)
AUTO_SYNC_BATCH_SIZE = 20
AUTO_SYNC_PENDING_BATCH_GRACE = timedelta(minutes=2)
RUOLO_AUTOSYNC_LOCK_NAMESPACE = 1_196_572_802
RuoloAutosyncResult = TypeVar("RuoloAutosyncResult")
RuoloAutosyncOperation = Callable[[Session, int], CatastoBatch | None]
CONTINUOUS_CONFIG_FIELDS = (
    "primary_enabled",
    "secondary_enabled",
    "role_parcel_refresh_hours",
    "role_subject_refresh_hours",
    "consortium_parcel_refresh_hours",
    "registry_subject_refresh_hours",
    "batch_size",
)


class RuoloAutosyncBusyError(HTTPException):
    """HTTP 409 returned when another autosync operation owns the user lock."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un aggiornamento delle sorgenti è già in corso. Riprova tra poco.",
        )


@contextmanager
def _ruolo_autosync_xact_lock(db: Session, user_id: int) -> Iterator[bool]:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        yield True
        return

    # Keep the advisory transaction open on a dedicated connection. A rollback
    # releases the lock even when the main Session commits or returns to its pool.
    with bind.connect() as connection:
        transaction = connection.begin()
        try:
            acquired = bool(
                connection.scalar(
                    select(func.pg_try_advisory_xact_lock(RUOLO_AUTOSYNC_LOCK_NAMESPACE, user_id))
                )
            )
            yield acquired
        finally:
            transaction.rollback()


def _ruolo_autosync_serialized(
    operation: Callable[[Session, int], RuoloAutosyncResult],
) -> Callable[[Session, int], RuoloAutosyncResult]:
    @wraps(operation)
    def locked_operation(db: Session, user_id: int) -> RuoloAutosyncResult:
        with _ruolo_autosync_xact_lock(db, user_id) as acquired:
            if not acquired:
                raise RuoloAutosyncBusyError()
            return operation(db, user_id)

    return locked_operation


def _ruolo_autosync_single_flight(operation: RuoloAutosyncOperation) -> RuoloAutosyncOperation:
    @wraps(operation)
    def locked_operation(db: Session, user_id: int) -> CatastoBatch | None:
        with _ruolo_autosync_xact_lock(db, user_id) as acquired:
            if not acquired:
                return None
            return operation(db, user_id)

    return locked_operation


def _ruolo_autosync_source_rows(*, refreshed_after: datetime | None):
    rank = func.row_number().over(
        partition_by=RuoloParticella.cat_particella_id,
        order_by=(
            RuoloParticella.anno_tributario.desc(),
            RuoloParticella.created_at.desc(),
            RuoloParticella.id.asc(),
        ),
    ).label("source_rank")
    statement = (
        select(
            RuoloParticella.id.label("ruolo_particella_id"),
            RuoloParticella.cat_particella_id,
            RuoloParticella.foglio,
            RuoloParticella.particella,
            RuoloParticella.subalterno,
            RuoloPartita.comune_nome,
            RuoloParticella.created_at.label("source_created_at"),
            rank,
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .where(RuoloParticella.cat_particella_id.is_not(None))
    )
    if refreshed_after is not None:
        statement = statement.where(RuoloParticella.created_at > refreshed_after)
    return statement.subquery("ruolo_autosync_source")


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
    _update_config_credentials(db, config, user_id, payload, fields)
    if "credential_profiles" in fields:
        _sync_active_autosync_batch_credentials(db, user_id, config.credential_ids or [])
    was_enabled = config.enabled
    if "enabled" in fields and payload.enabled is not None:
        config.enabled = bool(payload.enabled)
    _update_continuous_config_fields(config, payload, fields)
    if config.enabled:
        _validate_enabled_autosync_config(db, config, user_id)

    config.updated_by_user_id = user_id
    config.last_error_message = None
    db.add(config)
    db.commit()
    db.refresh(config)
    if was_enabled and not config.enabled:
        _release_active_autosync_batches(db, user_id)
    return config


def _sync_active_autosync_batch_credentials(
    db: Session,
    user_id: int,
    credential_ids: list[str],
) -> None:
    batches = db.scalars(
        select(CatastoBatch).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_((
                CatastoBatchKind.RUOLO_AUTOSYNC.value,
                CatastoBatchKind.PERPETUAL_SYNC.value,
            )),
            CatastoBatch.status.in_((
                CatastoBatchStatus.PENDING.value,
                CatastoBatchStatus.PROCESSING.value,
            )),
        )
    ).all()
    for batch in batches:
        batch.credential_ids = list(credential_ids)


def _release_active_autosync_batches(db: Session, user_id: int) -> None:
    batches = db.scalars(
        select(CatastoBatch).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_((
                CatastoBatchKind.RUOLO_AUTOSYNC.value,
                CatastoBatchKind.PERPETUAL_SYNC.value,
            )),
            CatastoBatch.status == CatastoBatchStatus.PROCESSING.value,
        )
    ).all()
    now = datetime.now(UTC)
    releasable_statuses = {
        CatastoVisuraRequestStatus.PENDING.value,
        CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
    }
    for batch in batches:
        requests = get_batch_requests(db, batch.id)
        for request in requests:
            if request.status in releasable_statuses:
                mark_request_released(request, now)
        batch.current_operation = RELEASE_REQUESTED_OPERATION
        if not any(request.status == CatastoVisuraRequestStatus.PROCESSING.value for request in requests):
            batch.status = CatastoBatchStatus.CANCELLED.value
            batch.completed_at = now
        recalculate_batch_counters(batch, requests)
    if batches:
        db.commit()


def _update_config_credentials(
    db: Session,
    config: CatastoRuoloAutoSyncConfig,
    user_id: int,
    payload: CatastoRuoloAutoSyncConfigUpdateRequest,
    fields: set[str],
) -> None:

    if "credential_profiles" in fields:
        normalized = _normalize_credential_profiles(
            db,
            user_id,
            payload.credential_profiles or {},
        )
        config.credential_profiles = normalized
        config.credential_ids = [
            credential_id
            for credential_id, profile in normalized.items()
            if bool(profile.get("enabled"))
        ]

    _update_legacy_credential_ids(config, payload, fields)
    _update_legacy_credential(db, config, user_id, payload, fields)


def _normalize_credential_profiles(
    db: Session,
    user_id: int,
    profiles: dict[str, CatastoAutoSyncCredentialProfile],
) -> dict[str, dict[str, object]]:
    normalized: dict[str, dict[str, object]] = {}
    for raw_id, profile in profiles.items():
        credential_id = UUID(str(raw_id))
        credential = _get_autosync_credential(db, user_id, credential_id)
        if credential is None or not credential.active:
            if not profile.enabled:
                continue
            raise ValueError("Una credenziale autosync non e disponibile o non e attiva")
        normalized[str(credential_id)] = profile.model_dump(mode="json")
    return normalized


def _update_legacy_credential_ids(
    config: CatastoRuoloAutoSyncConfig,
    payload: CatastoRuoloAutoSyncConfigUpdateRequest,
    fields: set[str],
) -> None:
    if "credential_ids" in fields and "credential_profiles" not in fields:
        config.credential_ids = list(dict.fromkeys(str(value) for value in payload.credential_ids or ()))


def _update_legacy_credential(
    db: Session,
    config: CatastoRuoloAutoSyncConfig,
    user_id: int,
    payload: CatastoRuoloAutoSyncConfigUpdateRequest,
    fields: set[str],
) -> None:
    if "credential_id" not in fields:
        return
    if payload.credential_id is None:
        config.credential_id = None
        return
    credential = _get_autosync_credential(db, user_id, payload.credential_id)
    if credential is None:
        raise ValueError("Credenziale SISTER non trovata")
    if not credential.active:
        raise ValueError("La credenziale selezionata non e attiva")
    config.credential_id = credential.id



def _update_continuous_config_fields(
    config: CatastoRuoloAutoSyncConfig,
    payload: CatastoRuoloAutoSyncConfigUpdateRequest,
    fields: set[str],
) -> None:
    for field in CONTINUOUS_CONFIG_FIELDS:
        value = getattr(payload, field)
        if field in fields and value is not None:
            setattr(config, field, value)


def _validate_enabled_autosync_config(
    db: Session, config: CatastoRuoloAutoSyncConfig, user_id: int
) -> None:
    selected_ids = config.credential_ids or (
        [str(config.credential_id)] if config.credential_id is not None else []
    )
    for value in selected_ids:
        selected_credential = _get_autosync_credential(db, user_id, UUID(str(value)))
        if selected_credential is None or not selected_credential.active:
            raise ValueError("Una credenziale autosync non e disponibile o non e attiva")
    if not (config.primary_enabled or config.secondary_enabled):
        raise ValueError("Attiva almeno una priorita della sincronizzazione continua")


def _get_autosync_credential(db: Session, user_id: int, credential_id: UUID):
    owner = db.get(ApplicationUser, user_id)
    if owner is not None and owner.is_super_admin:
        return db.get(CatastoCredential, credential_id)
    return get_credential_for_user(db, user_id, credential_id)


def _load_ruolo_autosync_source_candidates(
    db: Session,
    user_id: int,
    *,
    refreshed_after: datetime | None,
):
    source_rows = _ruolo_autosync_source_rows(refreshed_after=refreshed_after)
    candidates = select(
        source_rows.c.ruolo_particella_id,
        source_rows.c.cat_particella_id,
        source_rows.c.foglio,
        source_rows.c.particella,
        source_rows.c.subalterno,
        source_rows.c.comune_nome,
        source_rows.c.source_created_at,
    ).where(source_rows.c.source_rank == 1)
    rows = db.execute(candidates.order_by(source_rows.c.ruolo_particella_id.asc())).all()
    existing = {
        item.cat_particella_id: item
        for item in db.scalars(
            select(CatastoRuoloAutoSyncItem).where(
                CatastoRuoloAutoSyncItem.user_id == user_id,
                CatastoRuoloAutoSyncItem.cat_particella_id.in_(
                    select(source_rows.c.cat_particella_id).where(source_rows.c.source_rank == 1)
                ),
            )
        ).all()
    }
    return rows, existing


def _upsert_ruolo_autosync_item(
    db: Session,
    user_id: int,
    row,
    existing: dict,
    comune_lookup: dict,
) -> bool:
    (
        ruolo_particella_id,
        cat_particella_id,
        foglio,
        particella,
        subalterno,
        comune_nome,
        _source_created_at,
    ) = row
    comune = comune_lookup.get(normalize_lookup_value(comune_nome))
    item = existing.get(cat_particella_id)
    created = item is None
    if created:
        item = CatastoRuoloAutoSyncItem(user_id=user_id, ruolo_particella_id=ruolo_particella_id)
        db.add(item)

    item.ruolo_particella_id = ruolo_particella_id
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
    return created


def _refresh_ruolo_autosync_source(
    db: Session,
    user_id: int,
    *,
    incremental: bool,
) -> dict[str, int]:
    config = get_ruolo_autosync_config(db, user_id)
    refresh_started_at = datetime.now(UTC)
    refreshed_after = config.last_source_refresh_at if incremental else None
    comune_lookup = get_catasto_comuni_lookup(db)
    rows, existing = _load_ruolo_autosync_source_candidates(
        db,
        user_id,
        refreshed_after=refreshed_after,
    )

    source_watermark = max(
        (row.source_created_at for row in rows),
        default=refreshed_after or refresh_started_at,
    )
    created = sum(_upsert_ruolo_autosync_item(db, user_id, row, existing, comune_lookup) for row in rows)
    if rows:
        config.last_error_message = None
    config.last_source_refresh_at = source_watermark
    db.add(config)
    db.commit()
    return {"created": created, "updated": len(rows) - created, "total_candidates": len(rows)}


@_ruolo_autosync_serialized
def refresh_ruolo_autosync_source(db: Session, user_id: int) -> dict[str, int]:
    config = get_ruolo_autosync_config(db, user_id)
    if config.credential_ids is not None:
        summary = refresh_perpetual_sync_sources(db, config)
        return {**summary, "total_candidates": summary["created"] + summary["updated"]}
    return _refresh_ruolo_autosync_source(db, user_id, incremental=False)


def _refresh_ruolo_autosync_source_incremental(db: Session, user_id: int) -> dict[str, int]:
    return _refresh_ruolo_autosync_source(db, user_id, incremental=True)


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
        for item in runnable_items:
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


def _maintain_legacy_ruolo_autosync(db: Session, user_id: int) -> CatastoBatch | None:
    _refresh_ruolo_autosync_source_incremental(db, user_id)
    return ensure_ruolo_autosync_batch(db, user_id)


@_ruolo_autosync_single_flight
def _maintain_autosync(db: Session, user_id: int) -> CatastoBatch | None:
    config = get_ruolo_autosync_config(db, user_id)
    if config.credential_ids is not None:
        return maintain_perpetual_sync(db, config)
    return _maintain_legacy_ruolo_autosync(db, user_id)


maintain_ruolo_autosync = _maintain_autosync


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


def run_perpetual_sync_maintenance_for_all_users(db: Session) -> int:
    configs = list(
        db.scalars(
            select(CatastoRuoloAutoSyncConfig).where(
                CatastoRuoloAutoSyncConfig.enabled.is_(True)
            )
        ).all()
    )
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


def _load_ruolo_autosync_item_status(db: Session, user_id: int):
    counts = dict(
        db.execute(
            select(CatastoRuoloAutoSyncItem.status, func.count(CatastoRuoloAutoSyncItem.id))
            .where(CatastoRuoloAutoSyncItem.user_id == user_id)
            .group_by(CatastoRuoloAutoSyncItem.status)
        ).all()
    )
    recent_items = list(
        db.scalars(
            select(CatastoRuoloAutoSyncItem)
            .where(CatastoRuoloAutoSyncItem.user_id == user_id)
            .order_by(CatastoRuoloAutoSyncItem.updated_at.desc(), CatastoRuoloAutoSyncItem.created_at.desc())
            .limit(12)
        ).all()
    )
    error_items = list(
        db.scalars(
            select(CatastoRuoloAutoSyncItem)
            .where(
                CatastoRuoloAutoSyncItem.user_id == user_id,
                CatastoRuoloAutoSyncItem.status.in_(
                    (
                        CatastoRuoloAutoSyncItemStatus.PENDING.value,
                        CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value,
                        CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value,
                    )
                ),
                CatastoRuoloAutoSyncItem.last_error_message.is_not(None),
            )
            .order_by(CatastoRuoloAutoSyncItem.updated_at.desc(), CatastoRuoloAutoSyncItem.created_at.desc())
            .limit(12)
        ).all()
    )
    return counts, recent_items, error_items


def _load_ruolo_autosync_status_batches(db: Session, user_id: int):
    automatic_kinds = (
        CatastoBatchKind.PERPETUAL_SYNC.value,
        CatastoBatchKind.RUOLO_AUTOSYNC.value,
    )
    running_batch = db.scalar(
        select(CatastoBatch)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(automatic_kinds),
            CatastoBatch.status.in_(
                (CatastoBatchStatus.PENDING.value, CatastoBatchStatus.PROCESSING.value)
            ),
        )
        .order_by(CatastoBatch.created_at.desc())
        .limit(1)
    )
    last_batch = db.scalar(
        select(CatastoBatch)
        .where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind.in_(automatic_kinds),
        )
        .order_by(CatastoBatch.created_at.desc())
        .limit(1)
    )
    return running_batch, last_batch


def build_ruolo_autosync_status(db: Session, user_id: int) -> CatastoRuoloAutoSyncStatusResponse:
    config = get_ruolo_autosync_config(db, user_id)
    counts, recent_items, error_items = _load_ruolo_autosync_item_status(db, user_id)
    running_batch, last_batch = _load_ruolo_autosync_status_batches(db, user_id)
    perpetual_recent = list(
        db.scalars(
            select(CatastoPerpetualSyncItem)
            .where(CatastoPerpetualSyncItem.user_id == user_id)
            .order_by(CatastoPerpetualSyncItem.updated_at.desc())
            .limit(12)
        ).all()
    )
    perpetual_errors = list(
        db.scalars(
            select(CatastoPerpetualSyncItem)
            .where(
                CatastoPerpetualSyncItem.user_id == user_id,
                CatastoPerpetualSyncItem.last_error_message.is_not(None),
            )
            .order_by(CatastoPerpetualSyncItem.updated_at.desc())
            .limit(12)
        ).all()
    )

    return CatastoRuoloAutoSyncStatusResponse(
        config=CatastoRuoloAutoSyncConfigResponse.model_validate(config),
        counts=CatastoRuoloAutoSyncStatusCountsResponse(
            total=sum(counts.values()),
            pending=counts.get(CatastoRuoloAutoSyncItemStatus.PENDING.value, 0),
            queued=counts.get(CatastoRuoloAutoSyncItemStatus.QUEUED.value, 0),
            processing=counts.get(CatastoRuoloAutoSyncItemStatus.PROCESSING.value, 0),
            completed=counts.get(CatastoRuoloAutoSyncItemStatus.COMPLETED.value, 0),
            blocked_source=counts.get(CatastoRuoloAutoSyncItemStatus.BLOCKED_SOURCE.value, 0),
            blocked_runtime=counts.get(CatastoRuoloAutoSyncItemStatus.BLOCKED_RUNTIME.value, 0),
        ),
        running_batch=CatastoBatchResponse.model_validate(running_batch) if running_batch is not None else None,
        last_batch=CatastoBatchResponse.model_validate(last_batch) if last_batch is not None else None,
        error_items=[CatastoRuoloAutoSyncItemResponse.model_validate(item) for item in error_items],
        recent_items=[CatastoRuoloAutoSyncItemResponse.model_validate(item) for item in recent_items],
        scope_counts=perpetual_sync_counts(db, user_id),
        available_credential_ids=[
            credential.id for credential in available_perpetual_credentials(db, config)
        ],
        perpetual_error_items=[
            CatastoPerpetualSyncItemResponse.model_validate(item) for item in perpetual_errors
        ],
        perpetual_recent_items=[
            CatastoPerpetualSyncItemResponse.model_validate(item) for item in perpetual_recent
        ],
        dashboard=build_autosync_dashboard(db, user_id),
    )
