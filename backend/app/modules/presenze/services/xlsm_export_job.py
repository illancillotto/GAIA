from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.services.contract_profile import resolve_contract_profile
from app.modules.presenze.services.schedule_engine import build_schedule_context
from app.modules.presenze.services.xlsm_export import DEFAULT_TEMPLATE_PATH, ExportTimesheetRow, compile_workbook


def resolve_export_template_path(template_path: str | None) -> Path:
    if template_path:
        requested = Path(template_path)
        if requested.exists():
            return requested
        normalized = Path(
            str(requested)
            .replace("/Giornalere/", "/Giornaliere/")
            .replace("Giornalere_", "Giornaliere_")
        )
        if normalized.exists():
            return normalized
        raise FileNotFoundError(f"Template XLSM not found: {requested}")

    template = DEFAULT_TEMPLATE_PATH
    if template.exists():
        return template
    raise FileNotFoundError(f"Template XLSM not found: {template}")


def resolve_export_employee_kind(employee_kind: str | None, resolved_contract_kinds: set[str]) -> str:
    if employee_kind and employee_kind.strip():
        return employee_kind.strip().upper()
    if len(resolved_contract_kinds) != 1:
        return "PERSONALE"
    resolved_contract_kind = next(iter(resolved_contract_kinds))
    labels = {
        "operaio": "OPERAI",
        "impiegato": "IMPIEGATI",
        "quadro": "QUADRI",
        "altro": "ALTRO",
    }
    return labels.get(resolved_contract_kind, "PERSONALE")


def build_period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date(period_start.year + 1, 1, 1)
    return date(period_start.year, period_start.month + 1, 1)


def generate_xlsm_export(
    db: Session,
    *,
    period_start: date,
    collaborator_ids: list[uuid.UUID] | None,
    employee_kind: str | None,
    template_path: str | None,
    output_path: Path,
) -> str:
    template = resolve_export_template_path(template_path)

    collaborators_stmt = select(PresenzeCollaborator)
    if collaborator_ids:
        collaborators_stmt = collaborators_stmt.where(PresenzeCollaborator.id.in_(collaborator_ids))
    collaborators = db.execute(
        collaborators_stmt.order_by(PresenzeCollaborator.employee_code.asc())
    ).scalars().all()
    if not collaborators:
        raise ValueError("No collaborators found for the selected export scope")

    selected_collaborator_ids = [item.id for item in collaborators]
    period_end = build_period_end(period_start)
    daily_rows = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id.in_(selected_collaborator_ids),
            PresenzeDailyRecord.work_date >= period_start,
            PresenzeDailyRecord.work_date < period_end,
        )
        .order_by(PresenzeDailyRecord.collaborator_id.asc(), PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    daily_rows_by_collaborator_id: dict[uuid.UUID, list[PresenzeDailyRecord]] = defaultdict(list)
    for daily_row in daily_rows:
        daily_rows_by_collaborator_id[daily_row.collaborator_id].append(daily_row)

    active_collaborator_ids = list(daily_rows_by_collaborator_id.keys())
    if not active_collaborator_ids:
        raise ValueError("No daily rows found for the selected period")

    template_codes_by_collaborator = _load_latest_template_codes_by_collaborator(
        db,
        active_collaborator_ids,
        reference_date=period_start,
    )
    schedule_context = build_schedule_context(
        db,
        collaborator_ids=active_collaborator_ids,
        date_from=period_start,
        date_to=period_end,
    )

    punches_by_record_id: dict[str, list[PresenzeDailyPunch]] = defaultdict(list)
    punches = db.execute(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_([item.id for item in daily_rows]))
        .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
    ).scalars().all()
    for punch in punches:
        punches_by_record_id[str(punch.daily_record_id)].append(punch)

    export_rows: list[ExportTimesheetRow] = []
    resolved_contract_kinds: set[str] = set()
    for collaborator in collaborators:
        collaborator_daily_rows = daily_rows_by_collaborator_id.get(collaborator.id, [])
        if not collaborator_daily_rows:
            continue
        profile = resolve_contract_profile(
            collaborator.contract_kind,
            collaborator.standard_daily_minutes,
            template_code=template_codes_by_collaborator.get(collaborator.id),
        )
        collaborator.contract_kind = profile.contract_kind
        collaborator.standard_daily_minutes = profile.standard_daily_minutes
        if profile.contract_kind:
            resolved_contract_kinds.add(profile.contract_kind)
        export_rows.append(
            ExportTimesheetRow(
                collaborator=collaborator,
                daily_rows=collaborator_daily_rows,
                punches_by_record_id=punches_by_record_id,
            )
        )

    if not export_rows:
        raise ValueError("No daily rows found for the selected period")

    resolved_employee_kind = resolve_export_employee_kind(employee_kind, resolved_contract_kinds)
    compile_workbook(
        template=template,
        output=output_path,
        rows=export_rows,
        period_start=period_start,
        employee_kind=resolved_employee_kind,
        schedule_context=schedule_context,
    )
    return resolved_employee_kind


def _load_latest_template_codes_by_collaborator(
    db: Session,
    collaborator_ids: list[uuid.UUID],
    *,
    reference_date: date | None = None,
) -> dict[uuid.UUID, str | None]:
    if not collaborator_ids:
        return {}
    effective_reference_date = reference_date or date.today()
    assignments = db.execute(
        select(PresenzeCollaboratorScheduleAssignment)
        .where(PresenzeCollaboratorScheduleAssignment.collaborator_id.in_(collaborator_ids))
        .order_by(
            PresenzeCollaboratorScheduleAssignment.collaborator_id.asc(),
            PresenzeCollaboratorScheduleAssignment.valid_from.desc(),
            PresenzeCollaboratorScheduleAssignment.id.desc(),
        )
    ).scalars().all()
    template_ids = sorted({assignment.template_id for assignment in assignments})
    templates_by_id = {
        template.id: template
        for template in db.execute(
            select(PresenzeScheduleTemplate).where(PresenzeScheduleTemplate.id.in_(template_ids))
        ).scalars().all()
    }
    assignments_by_collaborator: dict[uuid.UUID, list[PresenzeCollaboratorScheduleAssignment]] = {}
    for assignment in assignments:
        assignments_by_collaborator.setdefault(assignment.collaborator_id, []).append(assignment)

    selected_codes: dict[uuid.UUID, str | None] = {}
    for collaborator_id in collaborator_ids:
        current_assignment = next(
            (
                assignment
                for assignment in assignments_by_collaborator.get(collaborator_id, [])
                if (assignment.valid_from is None or assignment.valid_from <= effective_reference_date)
                and (assignment.valid_to is None or assignment.valid_to >= effective_reference_date)
            ),
            None,
        )
        selected_assignment = current_assignment
        if selected_assignment is None and assignments_by_collaborator.get(collaborator_id):
            selected_assignment = assignments_by_collaborator[collaborator_id][0]
        template = templates_by_id.get(selected_assignment.template_id) if selected_assignment is not None else None
        selected_codes[collaborator_id] = template.code if template is not None else None
    return selected_codes
