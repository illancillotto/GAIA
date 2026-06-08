from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.accessi.org_structure import OrgStructureAssignment
from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.operazioni.models.wc_operator import WCOperator
from app.schemas.org_structure import (
    OrgStructureAssignmentResponse,
    OrgStructureAssignmentUpdate,
    OrgStructureBootstrapResponse,
    OrgStructureMetricsResponse,
    OrgStructureSuggestionResponse,
    OrgStructureUserSummary,
    OrgStructureWorkspaceResponse,
)

router = APIRouter(prefix="/admin/org-structure", tags=["admin — org-structure"])
RequireAccessiAdmin = Depends(require_module("accessi"))


@router.get("", response_model=OrgStructureWorkspaceResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def get_org_structure_workspace(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=True),
) -> OrgStructureWorkspaceResponse:
    users = _load_users(db, include_inactive=include_inactive)
    assignments = db.scalars(select(OrgStructureAssignment)).all()
    items = _serialize_workspace_items(db, users, assignments)
    suggestions = _build_suggestions(db, users, assignments)
    metrics = OrgStructureMetricsResponse(
        total_users=len(users),
        published_nodes=len(assignments),
        root_nodes=sum(1 for item in items if item.manager_user_id is None and item.is_active),
        unassigned_users=sum(1 for user in users if user.id not in {item.application_user_id for item in items}),
        linked_whitecompany_users=sum(1 for suggestion in suggestions),
    )
    return OrgStructureWorkspaceResponse(items=items, suggestions=suggestions, metrics=metrics)


@router.post("/bootstrap", response_model=OrgStructureBootstrapResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def bootstrap_org_structure_from_whitecompany(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> OrgStructureBootstrapResponse:
    linked_operators = db.scalars(select(WCOperator).where(WCOperator.gaia_user_id.is_not(None))).all()
    existing = {
        item.application_user_id: item
        for item in db.scalars(select(OrgStructureAssignment)).all()
    }
    chart_map = _whitecompany_chart_summary_by_gaia_user(db)
    created = 0
    updated = 0
    skipped = 0

    for operator in linked_operators:
        if operator.gaia_user_id is None:
            skipped += 1
            continue
        assignment = existing.get(operator.gaia_user_id)
        chart_summary = chart_map.get(operator.gaia_user_id)
        if assignment is None:
            assignment = OrgStructureAssignment(
                application_user_id=operator.gaia_user_id,
                manager_user_id=None,
                source_mode="whitecompany",
                title=operator.role,
                area_label=None,
                is_active=True,
                source_wc_operator_id=operator.id,
                source_wc_role=operator.role,
                source_chart_summary=chart_summary,
                last_synced_from_source_at=datetime.now(timezone.utc),
            )
            db.add(assignment)
            created += 1
            continue

        touched = False
        if assignment.source_wc_operator_id is None:
            assignment.source_wc_operator_id = operator.id
            touched = True
        if operator.role and not assignment.source_wc_role:
            assignment.source_wc_role = operator.role
            touched = True
        if operator.role and not assignment.title:
            assignment.title = operator.role
            touched = True
        if chart_summary and chart_summary != assignment.source_chart_summary:
            assignment.source_chart_summary = chart_summary
            touched = True
        assignment.last_synced_from_source_at = datetime.now(timezone.utc)
        if touched:
            updated += 1
        else:
            skipped += 1
        db.add(assignment)

    db.commit()
    return OrgStructureBootstrapResponse(created=created, updated=updated, skipped=skipped)


@router.put("/users/{user_id}", response_model=OrgStructureAssignmentResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def upsert_org_structure_assignment(
    user_id: int,
    payload: OrgStructureAssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> OrgStructureAssignmentResponse:
    user = db.get(ApplicationUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.manager_user_id == user_id:
        raise HTTPException(status_code=400, detail="A user cannot manage themselves")
    if payload.manager_user_id is not None and db.get(ApplicationUser, payload.manager_user_id) is None:
        raise HTTPException(status_code=404, detail="Manager user not found")

    assignment = db.scalar(select(OrgStructureAssignment).where(OrgStructureAssignment.application_user_id == user_id))
    if assignment is None:
        assignment = OrgStructureAssignment(application_user_id=user_id, source_mode="manual")

    if payload.manager_user_id is not None and _would_create_cycle(db, user_id=user_id, manager_user_id=payload.manager_user_id):
        raise HTTPException(status_code=400, detail="This assignment would create a reporting cycle")

    assignment.manager_user_id = payload.manager_user_id
    assignment.title = _clean_optional(payload.title)
    assignment.area_label = _clean_optional(payload.area_label)
    assignment.notes = _clean_optional(payload.notes)
    assignment.is_active = payload.is_active
    assignment.source_mode = "manual" if assignment.source_mode != "whitecompany" else "hybrid"
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _serialize_assignment(db, assignment, db.scalars(select(OrgStructureAssignment)).all())


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[RequireAdmin, RequireAccessiAdmin])
def delete_org_structure_assignment(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    assignment = db.scalar(select(OrgStructureAssignment).where(OrgStructureAssignment.application_user_id == user_id))
    if assignment is None:
        raise HTTPException(status_code=404, detail="Org structure assignment not found")

    children = db.scalars(select(OrgStructureAssignment).where(OrgStructureAssignment.manager_user_id == user_id)).all()
    for child in children:
        child.manager_user_id = None
        db.add(child)
    db.delete(assignment)
    db.commit()


def _load_users(db: Session, *, include_inactive: bool) -> list[ApplicationUser]:
    stmt: Select[tuple[ApplicationUser]] = select(ApplicationUser).order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())
    if not include_inactive:
        stmt = stmt.where(ApplicationUser.is_active.is_(True))
    return db.scalars(stmt).all()


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _whitecompany_chart_summary_by_gaia_user(db: Session) -> dict[int, str]:
    operators = db.scalars(select(WCOperator).where(WCOperator.gaia_user_id.is_not(None))).all()
    by_wc_operator = {operator.id: operator.gaia_user_id for operator in operators if operator.gaia_user_id is not None}
    chart_names_by_user: dict[int, set[str]] = defaultdict(set)
    entries = db.execute(
        select(WCOrgChartEntry, WCOrgChart).join(WCOrgChart, WCOrgChart.id == WCOrgChartEntry.org_chart_id)
    ).all()
    for entry, chart in entries:
        if entry.wc_operator_id is None:
            continue
        gaia_user_id = by_wc_operator.get(entry.wc_operator_id)
        if gaia_user_id is None:
            continue
        label = chart.name.strip() if chart.name else None
        if label:
            chart_names_by_user[gaia_user_id].add(label)
    return {
        user_id: " · ".join(sorted(names))
        for user_id, names in chart_names_by_user.items()
    }


def _build_suggestions(
    db: Session,
    users: list[ApplicationUser],
    assignments: list[OrgStructureAssignment],
) -> list[OrgStructureSuggestionResponse]:
    users_by_id = {user.id: user for user in users}
    published = {assignment.application_user_id for assignment in assignments}
    chart_map = _whitecompany_chart_summary_by_gaia_user(db)
    operators = db.scalars(select(WCOperator).where(WCOperator.gaia_user_id.is_not(None)).order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc())).all()
    suggestions: list[OrgStructureSuggestionResponse] = []
    for operator in operators:
        if operator.gaia_user_id is None:
            continue
        user = users_by_id.get(operator.gaia_user_id)
        if user is None:
            continue
        suggestions.append(
            OrgStructureSuggestionResponse(
                application_user_id=user.id,
                wc_operator_id=str(operator.id),
                username=user.username,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                wc_role=operator.role,
                chart_summary=chart_map.get(user.id),
                already_published=user.id in published,
            )
        )
    return suggestions


def _serialize_workspace_items(
    db: Session,
    users: list[ApplicationUser],
    assignments: list[OrgStructureAssignment],
) -> list[OrgStructureAssignmentResponse]:
    users_by_id = {user.id: user for user in users}
    manager_children: dict[int, list[int]] = defaultdict(list)
    assignments_by_user = {item.application_user_id: item for item in assignments}
    for assignment in assignments:
        if assignment.manager_user_id is not None:
            manager_children[assignment.manager_user_id].append(assignment.application_user_id)

    memo_depth: dict[int, int] = {}
    memo_descendants: dict[int, int] = {}

    def depth_for(user_id: int) -> int:
        if user_id in memo_depth:
            return memo_depth[user_id]
        assignment = assignments_by_user.get(user_id)
        if assignment is None or assignment.manager_user_id is None:
            memo_depth[user_id] = 0
            return 0
        memo_depth[user_id] = depth_for(assignment.manager_user_id) + 1
        return memo_depth[user_id]

    def descendants_for(user_id: int) -> int:
        if user_id in memo_descendants:
            return memo_descendants[user_id]
        total = 0
        for child_id in manager_children.get(user_id, []):
            total += 1 + descendants_for(child_id)
        memo_descendants[user_id] = total
        return total

    items = [
        OrgStructureAssignmentResponse(
            **assignment.__dict__,
            user=_serialize_user_summary(users_by_id[assignment.application_user_id]),
            manager=_serialize_user_summary(users_by_id[assignment.manager_user_id]) if assignment.manager_user_id in users_by_id else None,
            direct_reports_count=len(manager_children.get(assignment.application_user_id, [])),
            descendants_count=descendants_for(assignment.application_user_id),
            depth=depth_for(assignment.application_user_id),
        )
        for assignment in assignments
        if assignment.application_user_id in users_by_id
    ]
    return sorted(items, key=lambda item: (item.depth, (item.user.full_name or item.user.username).lower()))


def _serialize_user_summary(user: ApplicationUser) -> OrgStructureUserSummary:
    return OrgStructureUserSummary(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


def _serialize_assignment(
    db: Session,
    assignment: OrgStructureAssignment,
    all_assignments: list[OrgStructureAssignment] | None = None,
) -> OrgStructureAssignmentResponse:
    if all_assignments is None:
        all_assignments = db.scalars(select(OrgStructureAssignment)).all()
    users = _load_users(db, include_inactive=True)
    items = _serialize_workspace_items(db, users, all_assignments)
    response = next((item for item in items if item.application_user_id == assignment.application_user_id), None)
    if response is None:
        raise HTTPException(status_code=500, detail="Unable to serialize org structure assignment")
    return response


def _would_create_cycle(db: Session, *, user_id: int, manager_user_id: int) -> bool:
    assignments = db.scalars(select(OrgStructureAssignment)).all()
    manager_by_user = {item.application_user_id: item.manager_user_id for item in assignments}
    manager_by_user[user_id] = manager_user_id
    cursor = manager_user_id
    seen: set[int] = set()
    while cursor is not None:
        if cursor == user_id:
            return True
        if cursor in seen:
            return True
        seen.add(cursor)
        cursor = manager_by_user.get(cursor)
    return False
