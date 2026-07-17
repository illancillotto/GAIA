"""Services for riordino operational blocks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatAdeParticella, CatCapacitasGridRow, CatParticella
from app.schemas.elaborazioni import ElaborazioneRichiestaCreateRequest
from app.services.elaborazioni_batches import (
    BatchConflictError,
    BatchValidationError,
    create_single_visura_batch,
    get_batch_requests,
)
from app.services.elaborazioni_credentials import ElaborazioneCredentialConfigurationError
from app.modules.riordino.enums import EventType
from app.modules.riordino.models import (
    RiordinoBlock,
    RiordinoBlockAssignment,
    RiordinoBlockParcelSnapshot,
    RiordinoEvent,
)
from app.modules.riordino.services.common import require_admin_like, utcnow


ASSIGNMENT_COORDINATOR = "coordinator"
ASSIGNMENT_OPERATOR = "operator"
BLOCK_STATUSES = {"draft", "open", "in_progress", "completed", "archived"}
OPERATOR_REVIEW_STATUSES = {"pending", "aligned", "mismatch", "resolved"}
SISTER_VISURA_STATUSES = {"not_requested", "requested", "downloaded", "failed"}


def _same_cadastral_code_filter(code: str | None, administrative_unit: str | None):
    filters = []
    if code:
        filters.append(CatAdeParticella.codice_catastale == code)
    if administrative_unit:
        filters.append(CatAdeParticella.administrative_unit == administrative_unit)
    if not filters:
        return None
    return or_(*filters)


def _selection_json(data: dict) -> dict:
    return {
        "codice_catastale": data.get("codice_catastale"),
        "administrative_unit": data.get("administrative_unit"),
        "foglio": data.get("foglio"),
        "grid_code": data.get("grid_code"),
        "lot_code": data.get("lot_code"),
        "ade_particella_ids": [str(item) for item in data.get("ade_particella_ids", [])],
        "parcel_refs": data.get("parcel_refs", []),
    }


def _code_values(*values: str | None) -> list[str]:
    return sorted({value for value in values if value})


def _next_block_code(db: Session, year: int) -> str:
    prefix = f"RIOB-{year}-"
    max_code = db.scalar(select(func.max(RiordinoBlock.code)).where(RiordinoBlock.code.like(f"{prefix}%")))
    next_no = 1
    if max_code:
        next_no = int(max_code.rsplit("-", 1)[1]) + 1
    return f"{prefix}{next_no:04d}"


def _ade_query_for_selection(db: Session, data: dict) -> Select[tuple[CatAdeParticella]]:
    stmt: Select[tuple[CatAdeParticella]] = select(CatAdeParticella)
    selection_type = data["selection_type"]
    code_filter = _same_cadastral_code_filter(data.get("codice_catastale"), data.get("administrative_unit"))

    if selection_type == "municipality":
        if code_filter is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing municipality filter")
        return stmt.where(code_filter)
    if selection_type == "lot":
        if code_filter is None or not data.get("foglio"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing lot filter")
        return stmt.where(code_filter, CatAdeParticella.foglio == data["foglio"])
    if selection_type in {"parcel_list", "gis_selection"} and data.get("ade_particella_ids"):
        return stmt.where(CatAdeParticella.id.in_(data["ade_particella_ids"]))
    if selection_type == "parcel_list" and data.get("parcel_refs"):
        predicates = []
        for ref in data["parcel_refs"]:
            ref_code_filter = _same_cadastral_code_filter(
                ref.get("codice_catastale"),
                ref.get("administrative_unit"),
            )
            if ref_code_filter is None:
                continue
            predicates.append(
                (ref_code_filter)
                & (CatAdeParticella.foglio == ref["foglio"])
                & (CatAdeParticella.particella == ref["particella"])
            )
        if predicates:
            return stmt.where(or_(*predicates))
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid block parcel selection")


def _match_cat_particella(db: Session, ade: CatAdeParticella) -> tuple[UUID | None, str, str]:
    if not ade.foglio or not ade.particella:
        return None, "unmatched", "AdE parcel without foglio/particella"
    stmt = select(CatParticella).where(
        CatParticella.is_current.is_(True),
        CatParticella.suppressed.is_(False),
        CatParticella.foglio == ade.foglio,
        CatParticella.particella == ade.particella,
    )
    code_values = _code_values(ade.codice_catastale, ade.administrative_unit)
    if code_values:
        stmt = stmt.where(CatParticella.codice_catastale.in_(code_values))
    matches = list(db.scalars(stmt.limit(2)))
    if len(matches) == 1:
        return matches[0].id, "matched", "Matched on codice_catastale, foglio and particella"
    if len(matches) > 1:
        return None, "ambiguous", "Multiple Catasto consortile particles match AdE key"
    return None, "unmatched", "No current Catasto consortile particle matches AdE key"


def _capacitas_payload(db: Session, ade: CatAdeParticella) -> dict:
    if not ade.foglio or not ade.particella:
        return {"match_status": "unmatched", "rows_count": 0, "reason": "AdE parcel without foglio/particella"}
    stmt = select(CatCapacitasGridRow).where(
        CatCapacitasGridRow.foglio == ade.foglio,
        CatCapacitasGridRow.particella == ade.particella,
    )
    code_values = _code_values(ade.codice_catastale, ade.administrative_unit)
    if code_values:
        stmt = stmt.where(CatCapacitasGridRow.source_codice_catastale.in_(code_values))
    rows = list(db.scalars(stmt.limit(3)))
    if not rows:
        return {"match_status": "unmatched", "rows_count": 0, "reason": "No Capacitas row matches AdE key"}
    return {
        "match_status": "matched" if len(rows) == 1 else "ambiguous",
        "rows_count": len(rows),
        "sample": [
            {
                "id": str(row.id),
                "snapshot_id": str(row.snapshot_id),
                "source_comune_label": row.source_comune_label,
                "foglio": row.foglio,
                "particella": row.particella,
                "intestatario": row.intestatario,
                "codice_fiscale": row.codice_fiscale,
                "classification": row.classification,
            }
            for row in rows
        ],
    }


def _snapshot_from_ade(db: Session, block_id: UUID, ade: CatAdeParticella) -> RiordinoBlockParcelSnapshot:
    cat_particella_id, match_status, match_reason = _match_cat_particella(db, ade)
    return RiordinoBlockParcelSnapshot(
        block_id=block_id,
        ade_particella_id=ade.id,
        national_cadastral_reference=ade.national_cadastral_reference,
        administrative_unit=ade.administrative_unit,
        codice_catastale=ade.codice_catastale,
        sezione_catastale=ade.sezione_catastale,
        foglio=ade.foglio,
        particella=ade.particella,
        label=ade.label,
        ade_payload_json=ade.raw_payload_json,
        cat_particella_id=cat_particella_id,
        cat_particella_match_status=match_status,
        cat_particella_match_reason=match_reason,
        capacitas_payload_json=_capacitas_payload(db, ade),
        operator_review_status="pending",
        sister_visura_status="not_requested",
    )


def _replace_assignments(db: Session, block: RiordinoBlock, operator_user_ids: list[int], actor_user_id: int) -> None:
    block.assignments.clear()
    db.flush()
    block.assignments.append(
        RiordinoBlockAssignment(
            block_id=block.id,
            user_id=block.coordinator_user_id,
            assignment_role=ASSIGNMENT_COORDINATOR,
            assigned_by=actor_user_id,
        )
    )
    for user_id in sorted(set(operator_user_ids)):
        if user_id == block.coordinator_user_id:
            continue
        block.assignments.append(
            RiordinoBlockAssignment(
                block_id=block.id,
                user_id=user_id,
                assignment_role=ASSIGNMENT_OPERATOR,
                assigned_by=actor_user_id,
            )
        )
    db.flush()


def _create_block_event(
    db: Session,
    *,
    block_id: UUID,
    created_by: int,
    event_type: str | EventType,
    payload_json: dict | None = None,
) -> RiordinoEvent:
    event = RiordinoEvent(
        block_id=block_id,
        created_by=created_by,
        event_type=event_type.value if isinstance(event_type, EventType) else event_type,
        payload_json=payload_json,
    )
    db.add(event)
    db.flush()
    return event


def create_block(db: Session, data: dict, current_user: ApplicationUser) -> RiordinoBlock:
    require_admin_like(current_user)
    ade_rows = list(db.scalars(_ade_query_for_selection(db, data).order_by(CatAdeParticella.foglio, CatAdeParticella.particella)))
    if not ade_rows:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No AdE particles match selection")

    block = RiordinoBlock(
        code=_next_block_code(db, datetime.now().year),
        title=data["title"],
        description=data.get("description"),
        municipality=data.get("municipality"),
        selection_type=data["selection_type"],
        selection_json=_selection_json(data),
        status="draft",
        coordinator_user_id=data["coordinator_user_id"],
        created_by=current_user.id,
    )
    db.add(block)
    db.flush()

    snapshots = [_snapshot_from_ade(db, block.id, ade) for ade in ade_rows]
    block.parcel_snapshots.extend(snapshots)
    block.parcel_count = len(snapshots)
    block.mismatch_count = sum(1 for item in snapshots if item.cat_particella_match_status != "matched")
    _replace_assignments(db, block, data.get("operator_user_ids", []), current_user.id)
    _create_block_event(
        db,
        block_id=block.id,
        created_by=current_user.id,
        event_type="block_created",
        payload_json={"code": block.code, "parcel_count": block.parcel_count},
    )
    db.flush()
    return block


def _block_detail_options():
    return (
        selectinload(RiordinoBlock.assignments),
        selectinload(RiordinoBlock.parcel_snapshots),
        selectinload(RiordinoBlock.events),
    )


def get_block(db: Session, block_id: UUID, current_user: ApplicationUser) -> RiordinoBlock:
    stmt = (
        select(RiordinoBlock)
        .options(*_block_detail_options())
        .where(RiordinoBlock.id == block_id, RiordinoBlock.deleted_at.is_(None))
    )
    block = db.scalar(stmt)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    if not _can_read_block(block, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Block not assigned to user")
    return block


def _can_read_block(block: RiordinoBlock, user: ApplicationUser) -> bool:
    if user.role in {"admin", "super_admin"}:
        return True
    return any(assignment.is_active and assignment.user_id == user.id for assignment in block.assignments)


def _get_snapshot_for_block(block: RiordinoBlock, snapshot_id: UUID) -> RiordinoBlockParcelSnapshot:
    snapshot = next((item for item in block.parcel_snapshots if item.id == snapshot_id), None)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block parcel snapshot not found")
    return snapshot


def _capacitas_match_status(snapshot: RiordinoBlockParcelSnapshot) -> str:
    payload = snapshot.capacitas_payload_json or {}
    value = payload.get("match_status")
    return value if isinstance(value, str) else "not_checked"


def _wizard_task_status_for_review(snapshot: RiordinoBlockParcelSnapshot) -> str:
    if snapshot.operator_review_status in {"aligned", "resolved"}:
        return "done"
    if snapshot.operator_review_status == "mismatch":
        return "blocked"
    return "todo"


def _wizard_task_status_for_visura(snapshot: RiordinoBlockParcelSnapshot) -> str:
    if snapshot.sister_visura_status == "downloaded":
        return "done"
    if snapshot.sister_visura_status == "requested":
        return "in_progress"
    if snapshot.sister_visura_status == "failed":
        return "blocked"
    return "todo"


def get_block_wizard(db: Session, block_id: UUID, current_user: ApplicationUser) -> dict:
    block = get_block(db, block_id, current_user)
    return _build_block_wizard(block)


def _build_block_wizard(block: RiordinoBlock) -> dict:
    tasks: list[dict] = []
    for snapshot in sorted(block.parcel_snapshots, key=lambda item: (item.foglio or "", item.particella or "")):
        label = f"Fg.{snapshot.foglio or '-'} Part.{snapshot.particella or '-'}"
        cat_status = snapshot.cat_particella_match_status
        capacitas_status = _capacitas_match_status(snapshot)
        tasks.append(
            {
                "code": f"compare:{snapshot.id}",
                "title": f"Confronta AdE, Catasto consortile e Capacitas - {label}",
                "status": _wizard_task_status_for_review(snapshot),
                "snapshot_id": snapshot.id,
                "phase": "phase_1",
                "assignee_hint": "operator",
                "blocking_reason": (
                    f"Catasto={cat_status}, Capacitas={capacitas_status}"
                    if snapshot.operator_review_status == "mismatch"
                    else None
                ),
            }
        )
        tasks.append(
            {
                "code": f"sister:{snapshot.id}",
                "title": f"Richiedi e associa visura Sister - {label}",
                "status": _wizard_task_status_for_visura(snapshot),
                "snapshot_id": snapshot.id,
                "phase": "phase_1",
                "assignee_hint": "operator",
                "blocking_reason": snapshot.sister_visura_error if snapshot.sister_visura_status == "failed" else None,
            }
        )
        if snapshot.cat_particella_match_status != "matched" or capacitas_status != "matched":
            tasks.append(
                {
                    "code": f"resolve-mismatch:{snapshot.id}",
                    "title": f"Risolvi disallineamento catastale - {label}",
                    "status": "done" if snapshot.operator_review_status == "resolved" else "todo",
                    "snapshot_id": snapshot.id,
                    "phase": "phase_1",
                    "assignee_hint": "coordinator",
                    "blocking_reason": f"Catasto={cat_status}, Capacitas={capacitas_status}",
                }
            )
    return {"block_id": block.id, "block_code": block.code, "tasks": tasks}


def _count_values(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def get_block_coordinator_summary(db: Session, block_id: UUID, current_user: ApplicationUser) -> dict:
    block = get_block(db, block_id, current_user)
    if current_user.role not in {"admin", "super_admin"} and current_user.id != block.coordinator_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coordinator summary requires coordinator role")

    wizard = _build_block_wizard(block)
    review_status_counts = _count_values([snapshot.operator_review_status for snapshot in block.parcel_snapshots])
    sister_status_counts = _count_values([snapshot.sister_visura_status for snapshot in block.parcel_snapshots])
    task_status_counts = _count_values([task["status"] for task in wizard["tasks"]])

    operator_rows: list[dict] = []
    for assignment in block.assignments:
        reviewed = [snapshot for snapshot in block.parcel_snapshots if snapshot.reviewed_by == assignment.user_id]
        requested = [snapshot for snapshot in block.parcel_snapshots if snapshot.sister_visura_requested_by == assignment.user_id]
        completed = [snapshot for snapshot in block.parcel_snapshots if snapshot.sister_visura_completed_by == assignment.user_id]
        activity_candidates = [
            *(snapshot.reviewed_at for snapshot in reviewed),
            *(snapshot.sister_visura_requested_at for snapshot in requested),
            *(snapshot.sister_visura_completed_at for snapshot in completed),
        ]
        last_activity_at = max((item for item in activity_candidates if item is not None), default=None)
        operator_rows.append(
            {
                "user_id": assignment.user_id,
                "assignment_role": assignment.assignment_role,
                "is_active": assignment.is_active,
                "reviewed_count": len(reviewed),
                "sister_requested_count": len(requested),
                "sister_completed_count": len(completed),
                "last_activity_at": last_activity_at,
            }
        )

    return {
        "block_id": block.id,
        "block_code": block.code,
        "coordinator_user_id": block.coordinator_user_id,
        "parcel_count": block.parcel_count,
        "mismatch_count": block.mismatch_count,
        "review_status_counts": review_status_counts,
        "sister_status_counts": sister_status_counts,
        "task_status_counts": task_status_counts,
        "operators": sorted(operator_rows, key=lambda item: (item["assignment_role"] != ASSIGNMENT_COORDINATOR, item["user_id"])),
        "recent_events": block.events[:20],
    }


def list_blocks(
    db: Session,
    *,
    current_user: ApplicationUser,
    status_filter: str | None,
    coordinator: int | None,
    page: int,
    per_page: int,
) -> tuple[list[RiordinoBlock], int]:
    stmt: Select[tuple[RiordinoBlock]] = (
        select(RiordinoBlock)
        .options(selectinload(RiordinoBlock.assignments))
        .where(RiordinoBlock.deleted_at.is_(None))
    )
    if current_user.role not in {"admin", "super_admin"}:
        stmt = stmt.join(RiordinoBlockAssignment).where(
            RiordinoBlockAssignment.user_id == current_user.id,
            RiordinoBlockAssignment.is_active.is_(True),
        )
    if status_filter:
        stmt = stmt.where(RiordinoBlock.status == status_filter)
    if coordinator:
        stmt = stmt.where(RiordinoBlock.coordinator_user_id == coordinator)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(RiordinoBlock.created_at.desc()).offset((page - 1) * per_page).limit(per_page)))
    return items, total


def update_block(db: Session, block_id: UUID, data: dict, current_user: ApplicationUser) -> RiordinoBlock:
    require_admin_like(current_user)
    block = get_block(db, block_id, current_user)
    if "status" in data and data["status"] is not None and data["status"] not in BLOCK_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid block status")
    for field in ("title", "description", "status", "coordinator_user_id"):
        if field in data and data[field] is not None:
            setattr(block, field, data[field])
    if data.get("operator_user_ids") is not None:
        _replace_assignments(db, block, data["operator_user_ids"], current_user.id)
    _create_block_event(
        db,
        block_id=block.id,
        created_by=current_user.id,
        event_type="block_updated",
        payload_json={key: value for key, value in data.items() if key != "operator_user_ids"},
    )
    db.flush()
    return block


def review_block_parcel(
    db: Session,
    block_id: UUID,
    snapshot_id: UUID,
    data: dict,
    current_user: ApplicationUser,
) -> RiordinoBlockParcelSnapshot:
    block = get_block(db, block_id, current_user)
    snapshot = _get_snapshot_for_block(block, snapshot_id)
    review_status = data["status"]
    if review_status not in OPERATOR_REVIEW_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid review status")
    snapshot.operator_review_status = review_status
    snapshot.operator_review_notes = data.get("notes")
    snapshot.reviewed_by = current_user.id
    snapshot.reviewed_at = utcnow()
    _create_block_event(
        db,
        block_id=block.id,
        created_by=current_user.id,
        event_type="block_parcel_reviewed",
        payload_json={
            "snapshot_id": str(snapshot.id),
            "status": review_status,
            "notes": snapshot.operator_review_notes,
        },
    )
    db.flush()
    return snapshot


def request_sister_visura(
    db: Session,
    block_id: UUID,
    snapshot_id: UUID,
    data: dict,
    current_user: ApplicationUser,
) -> RiordinoBlockParcelSnapshot:
    block = get_block(db, block_id, current_user)
    snapshot = _get_snapshot_for_block(block, snapshot_id)
    if not snapshot.foglio or not snapshot.particella:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Snapshot missing foglio/particella")
    runtime_batch_id: str | None = None
    runtime_request_id: str | None = None
    if data.get("enqueue", True):
        comune = snapshot.codice_catastale or snapshot.administrative_unit
        if not comune:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Snapshot missing codice catastale")
        try:
            batch = create_single_visura_batch(
                db,
                current_user.id,
                ElaborazioneRichiestaCreateRequest(
                    search_mode="immobile",
                    comune=comune,
                    catasto="Terreni",
                    sezione=snapshot.sezione_catastale,
                    foglio=snapshot.foglio,
                    particella=snapshot.particella,
                    tipo_visura="Sintetica",
                    request_type="STORICA",
                ),
            )
        except BatchValidationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc
        except (BatchConflictError, ElaborazioneCredentialConfigurationError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        requests = get_batch_requests(db, batch.id)
        runtime_batch_id = str(batch.id)
        runtime_request_id = str(requests[0].id) if requests else None
    runtime_ref = f"{runtime_batch_id}:{runtime_request_id}" if runtime_batch_id and runtime_request_id else runtime_batch_id
    snapshot.sister_visura_status = "requested"
    snapshot.sister_visura_request_id = runtime_ref or data.get("request_id")
    snapshot.sister_visura_error = None
    snapshot.sister_visura_requested_by = current_user.id
    snapshot.sister_visura_requested_at = utcnow()
    _create_block_event(
        db,
        block_id=block.id,
        created_by=current_user.id,
        event_type="block_sister_visura_requested",
        payload_json={
            "snapshot_id": str(snapshot.id),
            "request_id": snapshot.sister_visura_request_id,
            "runtime_batch_id": runtime_batch_id,
            "runtime_request_id": runtime_request_id,
            "notes": data.get("notes"),
        },
    )
    db.flush()
    return snapshot


def complete_sister_visura(
    db: Session,
    block_id: UUID,
    snapshot_id: UUID,
    data: dict,
    current_user: ApplicationUser,
) -> RiordinoBlockParcelSnapshot:
    block = get_block(db, block_id, current_user)
    snapshot = _get_snapshot_for_block(block, snapshot_id)
    visura_status = data["status"]
    if visura_status not in {"downloaded", "failed"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid visura status")
    if visura_status == "downloaded" and not data.get("document_ref"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="document_ref is required")
    if visura_status == "failed" and not data.get("error_message"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="error_message is required")
    snapshot.sister_visura_status = visura_status
    snapshot.sister_visura_document_ref = data.get("document_ref")
    snapshot.sister_visura_error = data.get("error_message")
    snapshot.sister_visura_completed_by = current_user.id
    snapshot.sister_visura_completed_at = utcnow()
    _create_block_event(
        db,
        block_id=block.id,
        created_by=current_user.id,
        event_type="block_sister_visura_completed",
        payload_json={
            "snapshot_id": str(snapshot.id),
            "status": visura_status,
            "document_ref": snapshot.sister_visura_document_ref,
            "error_message": snapshot.sister_visura_error,
        },
    )
    db.flush()
    return snapshot


def delete_block(db: Session, block_id: UUID, current_user: ApplicationUser) -> RiordinoBlock:
    require_admin_like(current_user)
    block = get_block(db, block_id, current_user)
    block.deleted_at = utcnow()
    _create_block_event(db, block_id=block.id, created_by=current_user.id, event_type="block_deleted")
    db.flush()
    return block
