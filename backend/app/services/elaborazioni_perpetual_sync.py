from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, tuple_, update
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoBatch,
    CatastoBatchKind,
    CatastoBatchStatus,
    CatastoCredential,
    CatastoCredentialLease,
    CatastoPerpetualSyncItem,
    CatastoPerpetualSyncScope,
    CatastoRuoloAutoSyncConfig,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)
from app.services.elaborazioni_batches import (
    BatchConflictError,
    ValidatedVisuraRow,
    create_batch_from_validated_rows,
    is_release_marker_request,
    start_batch,
)
from app.services.elaborazioni_credential_schedule import credential_is_available
from app.services.elaborazioni_perpetual_sources import PerpetualSourceTarget, iter_enabled_targets

UTC = timezone.utc
RETRY_DELAY = timedelta(minutes=15)
BLOCKED_RETRY_DELAY = timedelta(hours=6)
MAX_AUTOSYNC_ATTEMPTS = 3
ROLE_CAMPAIGN_SCOPES = (
    CatastoPerpetualSyncScope.RUOLO_PARTICELLA.value,
    CatastoPerpetualSyncScope.RUOLO_SOGGETTO.value,
)
PLANNER_SCOPE_ORDER = (
    *ROLE_CAMPAIGN_SCOPES,
    CatastoPerpetualSyncScope.CONSORZIO_PARTICELLA.value,
    CatastoPerpetualSyncScope.ANAGRAFE_SOGGETTO.value,
)
SOURCE_REFRESH_INTERVAL = timedelta(minutes=15)
SOURCE_REFRESH_CHUNK_SIZE = 1_000


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _target_values(target: PerpetualSourceTarget) -> dict[str, object | None]:
    return {
        "priority": target.priority,
        "ruolo_particella_id": target.ruolo_particella_id,
        "cat_particella_id": target.cat_particella_id,
        "subject_id": target.subject_id,
        "search_mode": target.search_mode,
        "comune": target.comune,
        "comune_codice": target.comune_codice,
        "catasto": target.catasto,
        "sezione": target.sezione,
        "foglio": target.foglio,
        "particella": target.particella,
        "subalterno": target.subalterno,
        "subject_kind": target.subject_kind,
        "subject_identifier": target.subject_identifier,
        "intestazione": target.intestazione,
        "tipo_visura": target.tipo_visura,
        "request_type": target.request_type,
        "source_updated_at": target.source_updated_at,
    }


def _refresh_existing_item(
    item: CatastoPerpetualSyncItem, target: PerpetualSourceTarget, now: datetime
) -> None:
    previous_source_at = item.source_updated_at
    for field, value in _target_values(target).items():
        setattr(item, field, value)
    source_changed = target.source_updated_at is not None and (
        previous_source_at is None
        or _as_utc(target.source_updated_at) > _as_utc(previous_source_at)
    )
    if item.status == "disabled":
        item.status = "pending"
        item.next_due_at = now
        item.retry_after = None
    elif source_changed and item.status == "completed":
        item.status = "pending"
        item.next_due_at = now


def _target_chunks(
    targets: Iterable[PerpetualSourceTarget],
) -> Iterable[list[PerpetualSourceTarget]]:
    chunk: list[PerpetualSourceTarget] = []
    for target in targets:
        chunk.append(target)
        if len(chunk) == SOURCE_REFRESH_CHUNK_SIZE:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _refresh_target_chunk(
    db: Session,
    config: CatastoRuoloAutoSyncConfig,
    targets: list[PerpetualSourceTarget],
    now: datetime,
) -> int:
    target_keys = [(target.scope, target.target_key) for target in targets]
    existing = {
        (item.scope, item.target_key): item
        for item in db.scalars(
            select(CatastoPerpetualSyncItem).where(
                CatastoPerpetualSyncItem.user_id == config.user_id,
                tuple_(
                    CatastoPerpetualSyncItem.scope,
                    CatastoPerpetualSyncItem.target_key,
                ).in_(target_keys),
            )
        ).all()
    }
    created = 0
    for target in targets:
        item = existing.get((target.scope, target.target_key))
        if item is None:
            db.add(
                CatastoPerpetualSyncItem(
                    user_id=config.user_id,
                    scope=target.scope,
                    target_key=target.target_key,
                    next_due_at=now,
                    **_target_values(target),
                )
            )
            created += 1
        else:
            _refresh_existing_item(item, target, now)
    db.flush()
    return created


def _disable_missing_items(
    db: Session,
    user_id: int,
    keys: set[tuple[str, str]],
) -> int:
    missing_ids: list[UUID] = []
    disabled = 0
    rows = db.execute(
        select(
            CatastoPerpetualSyncItem.id,
            CatastoPerpetualSyncItem.scope,
            CatastoPerpetualSyncItem.target_key,
        ).where(
            CatastoPerpetualSyncItem.user_id == user_id,
            CatastoPerpetualSyncItem.status.not_in(("queued", "processing")),
        )
    ).yield_per(SOURCE_REFRESH_CHUNK_SIZE)
    for item_id, scope, target_key in rows:
        if (scope, target_key) in keys:
            continue
        missing_ids.append(item_id)
        if len(missing_ids) == SOURCE_REFRESH_CHUNK_SIZE:
            db.execute(
                update(CatastoPerpetualSyncItem)
                .where(CatastoPerpetualSyncItem.id.in_(missing_ids))
                .values(status="disabled")
            )
            disabled += len(missing_ids)
            missing_ids = []
    if missing_ids:
        db.execute(
            update(CatastoPerpetualSyncItem)
            .where(CatastoPerpetualSyncItem.id.in_(missing_ids))
            .values(status="disabled")
        )
        disabled += len(missing_ids)
    return disabled


def refresh_perpetual_sync_sources(
    db: Session, config: CatastoRuoloAutoSyncConfig
) -> dict[str, int]:
    now = datetime.now(UTC)
    targets = iter_enabled_targets(
        db, primary=config.primary_enabled, secondary=config.secondary_enabled
    )
    keys: set[tuple[str, str]] = set()
    created = 0
    total = 0
    for chunk in _target_chunks(targets):
        keys.update((target.scope, target.target_key) for target in chunk)
        created += _refresh_target_chunk(db, config, chunk, now)
        total += len(chunk)

    disabled = _disable_missing_items(db, config.user_id, keys)
    config.last_source_refresh_at = now
    config.last_planner_at = now
    config.source_watermarks = {
        "target_count": total,
        "refreshed_at": now.isoformat(),
    }
    db.commit()
    return {"created": created, "updated": total - created, "disabled": disabled}


def reconcile_perpetual_sync_items(
    db: Session, config: CatastoRuoloAutoSyncConfig
) -> None:
    now = datetime.now(UTC)
    items = db.scalars(
        select(CatastoPerpetualSyncItem).where(
            CatastoPerpetualSyncItem.user_id == config.user_id,
            CatastoPerpetualSyncItem.linked_request_id.is_not(None),
        )
    ).all()
    changed = False
    for item in items:
        request = db.get(CatastoVisuraRequest, item.linked_request_id)
        changed = _reconcile_item(item, request, config, now) or changed
    if changed:
        db.commit()


def _reconcile_item(
    item: CatastoPerpetualSyncItem,
    request: CatastoVisuraRequest | None,
    config: CatastoRuoloAutoSyncConfig,
    now: datetime,
) -> bool:
    if request is None:
        return _reconcile_missing_request(item, now)
    item.attempt_count = max(item.attempt_count, request.attempts or 0)
    request_status = request.status
    if request_status == CatastoVisuraRequestStatus.PENDING.value:
        item.status = "queued"
        return True
    if request_status in {
        CatastoVisuraRequestStatus.PROCESSING.value,
        CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
    }:
        item.status = "processing"
        return True
    if request_status in {
        CatastoVisuraRequestStatus.COMPLETED.value,
        CatastoVisuraRequestStatus.NOT_FOUND.value,
    }:
        _complete_item(item, request, config, now)
        return True
    if request_status == CatastoVisuraRequestStatus.FAILED.value:
        _retry_item(item, request, now)
        return True
    if request_status == CatastoVisuraRequestStatus.SKIPPED.value:
        if is_release_marker_request(request):
            item.status = "pending"
            item.retry_after = None
            item.next_due_at = now
            item.linked_batch_id = None
            item.linked_request_id = None
            return True
        item.status = "skipped"
        item.retry_after = None
        item.next_due_at = now
        item.last_error_message = request.error_message
        return True
    return False


def _reconcile_missing_request(item: CatastoPerpetualSyncItem, now: datetime) -> bool:
    if item.status not in {"queued", "processing"}:
        return False
    item.status = "pending"
    item.next_due_at = now
    return True


def _complete_item(
    item: CatastoPerpetualSyncItem,
    request: CatastoVisuraRequest,
    config: CatastoRuoloAutoSyncConfig,
    now: datetime,
) -> None:
    item.status = "completed"
    item.last_completed_at = request.processed_at or now
    # A completed campaign item is re-opened only by a newer source version.
    item.next_due_at = item.last_completed_at
    item.retry_after = None
    item.last_error_message = request.error_message


def _retry_item(
    item: CatastoPerpetualSyncItem, request: CatastoVisuraRequest, now: datetime
) -> None:
    item.last_error_message = request.error_message
    if item.status == "pending" and item.retry_after is not None:
        return
    if item.attempt_count >= MAX_AUTOSYNC_ATTEMPTS:
        item.status = "failed"
        item.retry_after = None
        item.next_due_at = now
        return
    item.status = "pending"
    base_delay = BLOCKED_RETRY_DELAY if request.last_error_code else RETRY_DELAY
    delay = base_delay * (2 ** max(item.attempt_count - 1, 0))
    item.retry_after = now + delay
    item.next_due_at = item.retry_after


def _configured_credential_ids(config: CatastoRuoloAutoSyncConfig) -> set[UUID] | None:
    profiles = config.credential_profiles
    if isinstance(profiles, dict):
        values = [credential_id for credential_id, profile in profiles.items() if isinstance(profile, dict) and profile.get("enabled")]
    else:
        values = config.credential_ids
    if values is None:
        return {config.credential_id} if config.credential_id is not None else None
    parsed: set[UUID] = set()
    for value in values:
        try:
            parsed.add(UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return parsed


def _autosync_schedule(
    config: CatastoRuoloAutoSyncConfig,
    credential: CatastoCredential,
) -> tuple[bool, dict | None]:
    profiles = config.credential_profiles
    if not isinstance(profiles, dict):
        return credential.schedule_enabled, credential.availability_schedule
    profile = profiles.get(str(credential.id))
    if not isinstance(profile, dict) or not profile.get("enabled"):
        return True, None
    return bool(profile.get("schedule_enabled")), profile.get("availability_schedule")


def available_perpetual_credentials(
    db: Session, config: CatastoRuoloAutoSyncConfig, *, at: datetime | None = None
) -> list[CatastoCredential]:
    now = at or datetime.now(UTC)
    owner = db.get(ApplicationUser, config.user_id)
    statement = select(CatastoCredential).where(CatastoCredential.active.is_(True))
    if owner is None or not owner.is_super_admin:
        statement = statement.where(CatastoCredential.user_id == config.user_id)
    allowed_ids = _configured_credential_ids(config)
    if allowed_ids is not None:
        statement = statement.where(CatastoCredential.id.in_(allowed_ids))
    credentials = list(
        db.scalars(
            statement.order_by(
                CatastoCredential.is_default.desc(), CatastoCredential.updated_at.desc()
            )
        ).all()
    )
    leases = {
        lease.sister_username
        for lease in db.scalars(
            select(CatastoCredentialLease).where(CatastoCredentialLease.expires_at > now)
        ).all()
    }
    available: list[CatastoCredential] = []
    for credential in credentials:
        schedule_enabled, schedule = _autosync_schedule(config, credential)
        if credential.sister_username not in leases and credential_is_available(
            schedule_enabled, schedule, now
        ):
            available.append(credential)
    return available


def _runnable(item: CatastoPerpetualSyncItem) -> bool:
    if item.search_mode == "soggetto":
        return bool(item.subject_identifier and item.subject_kind)
    return bool(item.comune and item.comune_codice and item.foglio and item.particella)


def _due_items(
    db: Session, config: CatastoRuoloAutoSyncConfig, now: datetime, scope: str
) -> list[CatastoPerpetualSyncItem]:
    statement = (
        select(CatastoPerpetualSyncItem)
        .where(
            CatastoPerpetualSyncItem.user_id == config.user_id,
            CatastoPerpetualSyncItem.scope == scope,
            CatastoPerpetualSyncItem.status == "pending",
            CatastoPerpetualSyncItem.next_due_at <= now,
            or_(
                CatastoPerpetualSyncItem.retry_after.is_(None),
                CatastoPerpetualSyncItem.retry_after <= now,
            ),
        )
        .order_by(
            CatastoPerpetualSyncItem.priority.asc(),
            CatastoPerpetualSyncItem.next_due_at.asc(),
            CatastoPerpetualSyncItem.updated_at.asc(),
        )
        .with_for_update(skip_locked=True)
    )
    return [
        item
        for item in db.scalars(statement).all()
        if _runnable(item)
    ][: max(config.batch_size, 1)]


def _scope_has_open_items(db: Session, user_id: int, scope: str) -> bool:
    statement = select(CatastoPerpetualSyncItem).where(
        CatastoPerpetualSyncItem.user_id == user_id,
        CatastoPerpetualSyncItem.scope == scope,
        CatastoPerpetualSyncItem.status.in_(("pending", "queued", "processing")),
    )
    return any(_runnable(item) for item in db.scalars(statement).all())


def _next_campaign_scope(db: Session, user_id: int) -> str | None:
    for scope in PLANNER_SCOPE_ORDER:
        if _scope_has_open_items(db, user_id, scope):
            return scope
    return None


def _validated_row(index: int, item: CatastoPerpetualSyncItem) -> ValidatedVisuraRow:
    return ValidatedVisuraRow(
        row_index=index,
        search_mode=item.search_mode,
        comune=item.comune,
        comune_codice=item.comune_codice,
        catasto=item.catasto,
        sezione=item.sezione,
        foglio=item.foglio,
        particella=item.particella,
        subalterno=item.subalterno,
        tipo_visura=item.tipo_visura,
        purpose="perpetual_sync",
        target_ruolo_particella_id=item.ruolo_particella_id,
        subject_kind=item.subject_kind,
        subject_id=item.subject_identifier,
        request_type=item.request_type,
        intestazione=item.intestazione,
    )


def _link_items(
    items: Iterable[CatastoPerpetualSyncItem], batch: CatastoBatch,
    requests: list[CatastoVisuraRequest], now: datetime,
) -> None:
    for item, request in zip(items, requests, strict=True):
        item.status = "queued"
        item.linked_batch_id = batch.id
        item.linked_request_id = request.id
        item.last_enqueued_at = now
        item.retry_after = None
        item.last_error_message = None


def _active_perpetual_batch_exists(db: Session, user_id: int) -> bool:
    return db.scalar(
        select(CatastoBatch.id).where(
            CatastoBatch.user_id == user_id,
            CatastoBatch.batch_kind == CatastoBatchKind.PERPETUAL_SYNC.value,
            CatastoBatch.status.in_(
                (CatastoBatchStatus.PENDING.value, CatastoBatchStatus.PROCESSING.value)
            ),
        )
    ) is not None


def _campaign_label(scope: str) -> str:
    return {
        CatastoPerpetualSyncScope.RUOLO_PARTICELLA.value: "Particelle a ruolo",
        CatastoPerpetualSyncScope.RUOLO_SOGGETTO.value: "Anagrafiche a ruolo",
        CatastoPerpetualSyncScope.CONSORZIO_PARTICELLA.value: "Particelle consorzio",
        CatastoPerpetualSyncScope.ANAGRAFE_SOGGETTO.value: "Soggetti anagrafe",
    }[scope]


def _suspend_conflicting_batch(
    db: Session,
    config: CatastoRuoloAutoSyncConfig,
    batch: CatastoBatch,
    items: list[CatastoPerpetualSyncItem],
    now: datetime,
    exc: BatchConflictError,
) -> None:
    for item in items:
        item.status = "pending"
        item.linked_batch_id = None
        item.linked_request_id = None
        item.retry_after = now + RETRY_DELAY
        item.next_due_at = item.retry_after
    batch.status = CatastoBatchStatus.CANCELLED.value
    batch.current_operation = "Planner sospeso: precedenza a un batch concorrente"
    batch.completed_at = now
    config.last_error_message = str(exc)
    db.commit()


def ensure_perpetual_sync_batch(
    db: Session, config: CatastoRuoloAutoSyncConfig
) -> CatastoBatch | None:
    reconcile_perpetual_sync_items(db, config)
    if not config.enabled or not (config.primary_enabled or config.secondary_enabled):
        return None
    if _active_perpetual_batch_exists(db, config.user_id):
        return None
    credentials = available_perpetual_credentials(db, config)
    if not credentials:
        return None
    now = datetime.now(UTC)
    scope = _next_campaign_scope(db, config.user_id)
    if scope is None:
        return None
    items = _due_items(db, config, now, scope)
    if not items:
        return None
    campaign_label = _campaign_label(scope)
    batch, requests = create_batch_from_validated_rows(
        db,
        config.user_id,
        [_validated_row(index, item) for index, item in enumerate(items, start=1)],
        f"{campaign_label} · elaborazione progressiva {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "perpetual_sync",
        batch_kind=CatastoBatchKind.PERPETUAL_SYNC.value,
        credential_ids=[credential.id for credential in credentials],
    )
    _link_items(items, batch, requests, now)
    config.last_batch_started_at = now
    config.last_planner_at = now
    config.last_error_message = None
    db.commit()
    try:
        return start_batch(db, config.user_id, batch.id)
    except BatchConflictError as exc:
        _suspend_conflicting_batch(db, config, batch, items, now, exc)
        return None


def maintain_perpetual_sync(db: Session, config: CatastoRuoloAutoSyncConfig) -> CatastoBatch | None:
    if not config.enabled:
        return None
    now = datetime.now(UTC)
    if (
        config.last_source_refresh_at is None
        or _as_utc(config.last_source_refresh_at) <= now - SOURCE_REFRESH_INTERVAL
    ):
        refresh_perpetual_sync_sources(db, config)
    return ensure_perpetual_sync_batch(db, config)


def perpetual_sync_counts(db: Session, user_id: int) -> dict[str, dict[str, int]]:
    rows = db.execute(
        select(
            CatastoPerpetualSyncItem.scope,
            CatastoPerpetualSyncItem.status,
            func.count(CatastoPerpetualSyncItem.id),
        )
        .where(CatastoPerpetualSyncItem.user_id == user_id)
        .group_by(CatastoPerpetualSyncItem.scope, CatastoPerpetualSyncItem.status)
    ).all()
    result: dict[str, dict[str, int]] = {}
    for scope, status, count in rows:
        result.setdefault(scope, {})[status] = int(count)
    return result


def retry_perpetual_sync_failures(db: Session, user_id: int, scope: str) -> int:
    if scope not in ROLE_CAMPAIGN_SCOPES:
        raise ValueError("Campagna AutoSync non valida")
    items = list(
        db.scalars(
            select(CatastoPerpetualSyncItem).where(
                CatastoPerpetualSyncItem.user_id == user_id,
                CatastoPerpetualSyncItem.scope == scope,
                CatastoPerpetualSyncItem.status == "failed",
            )
        ).all()
    )
    now = datetime.now(UTC)
    for item in items:
        item.status = "pending"
        item.attempt_count = 0
        item.linked_batch_id = None
        item.linked_request_id = None
        item.last_error_message = None
        item.retry_after = None
        item.next_due_at = now
    if items:
        db.commit()
    return len(items)
