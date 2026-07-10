from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.router import _serialize_daily_record
from app.modules.presenze.schemas import (
    GatePresenzeAnomaliesResponse,
    GatePresenzeAnomalyItemResponse,
    GatePresenzeAvailableMonthsResponse,
    GatePresenzeDailyRecordAnalysisResponse,
    GatePresenzeDailyRecordDetailResponse,
    GatePresenzeDailyRecordItemResponse,
    GatePresenzeDailyRecordPatchRequest,
    GatePresenzeDailyRecordValidateRequest,
    GatePresenzeDailyRecordsResponse,
    GatePresenzeExportPreviewResponse,
    GatePresenzeExportGenerateRequest,
    GatePresenzeExportGenerateResponse,
    GatePresenzeMonthItemResponse,
    GatePresenzeResolveAnomalyRequest,
    GatePresenzeRuleItemResponse,
    GatePresenzeRulesResponse,
    GatePresenzeRuleSectionResponse,
    OrganizationTeamCreate,
    OrganizationTeamMembershipCreate,
    OrganizationTeamMembershipResponse,
    OrganizationTeamResponse,
    OrganizationTeamSupervisorCreate,
    OrganizationTeamSupervisorResponse,
    OrganizationTeamUpdate,
)


router = APIRouter(prefix="/gate/presenze", tags=["gate-presenze"])
RequirePresenzeModule = Depends(require_module("presenze"))
RULES_VERSION = "presenze-2026-07-extra-3h"
EXPORT_RULES_VERSION = "presenze-xlsm-2026-07"


@router.get("/rules", response_model=GatePresenzeRulesResponse)
def get_gate_presenze_rules(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeRulesResponse:
    return _build_rules_response()


@router.get("/months/available", response_model=GatePresenzeAvailableMonthsResponse)
def list_gate_presenze_available_months(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeAvailableMonthsResponse:
    stmt = _apply_gate_record_visibility(
        db,
        current_user,
        stmt=select(PresenzeDailyRecord.work_date),
        period_start=None,
        period_end=None,
        team_id=None,
    )
    counts: dict[str, int] = {}
    for (work_date,) in db.execute(stmt).all():
        month = work_date.strftime("%Y-%m")
        counts[month] = counts.get(month, 0) + 1
    return GatePresenzeAvailableMonthsResponse(
        rules_version=RULES_VERSION,
        months=[
            GatePresenzeMonthItemResponse(month=month, records_total=counts[month])
            for month in sorted(counts)
        ],
    )


@router.get("/giornaliere", response_model=GatePresenzeDailyRecordsResponse)
def list_gate_presenze_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    team_id: uuid.UUID | None = Query(default=None),
) -> GatePresenzeDailyRecordsResponse:
    period_start, period_end = _month_period(month)
    records = _load_gate_records(db, current_user, period_start=period_start, period_end=period_end, team_id=team_id)
    collaborators = _collaborator_map(db, [record.collaborator_id for record in records])
    team_ids_by_collaborator = _team_ids_by_collaborator(
        db,
        [record.collaborator_id for record in records],
        period_start=period_start,
        period_end=period_end,
    )
    return GatePresenzeDailyRecordsResponse(
        month=month,
        rules_version=RULES_VERSION,
        generated_at=datetime.now(UTC),
        records=[
            _serialize_gate_record_item(
                db,
                record,
                collaborator=collaborators.get(record.collaborator_id),
                team_ids=team_ids_by_collaborator.get(record.collaborator_id, []),
            )
            for record in records
        ],
    )


@router.get("/giornaliere/{record_id}", response_model=GatePresenzeDailyRecordDetailResponse)
def get_gate_presenze_giornaliera(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeDailyRecordDetailResponse:
    record = _get_gate_record_or_404(db, current_user, record_id)
    return _serialize_gate_record_detail(db, record)


@router.post("/giornaliere/{record_id}/validate", response_model=GatePresenzeDailyRecordDetailResponse)
def validate_gate_presenze_giornaliera(
    record_id: uuid.UUID,
    payload: GatePresenzeDailyRecordValidateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeDailyRecordDetailResponse:
    record = _get_gate_record_or_404(db, current_user, record_id)
    before = _gate_record_snapshot(record)
    record.validation_status = payload.validation_status
    record.validation_note = payload.operator_note
    if payload.validation_status == "validated":
        record.validated_by_user_id = current_user.id
        record.validated_at = datetime.now(UTC)
    else:
        record.validated_by_user_id = None
        record.validated_at = None
    _append_gate_audit(
        record,
        action="validate",
        current_user=current_user,
        operator_note=payload.operator_note,
        client_request_id=payload.client_request_id,
        before=before,
        after=_gate_record_snapshot(record),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_gate_record_detail(db, record)


@router.post("/giornaliere/{record_id}/patch", response_model=GatePresenzeDailyRecordDetailResponse)
def patch_gate_presenze_giornaliera(
    record_id: uuid.UUID,
    payload: GatePresenzeDailyRecordPatchRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeDailyRecordDetailResponse:
    record = _get_gate_record_or_404(db, current_user, record_id)
    patch_data = payload.model_dump(exclude_unset=True, exclude={"operator_note", "client_request_id"})
    before = _gate_record_snapshot(record)
    for field, value in patch_data.items():
        setattr(record, field, value)
    _append_gate_audit(
        record,
        action="patch",
        current_user=current_user,
        operator_note=payload.operator_note,
        client_request_id=payload.client_request_id,
        before=before,
        after=_gate_record_snapshot(record),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_gate_record_detail(db, record)


@router.get("/anomalie", response_model=GatePresenzeAnomaliesResponse)
def list_gate_presenze_anomalie(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    team_id: uuid.UUID | None = Query(default=None),
) -> GatePresenzeAnomaliesResponse:
    period_start, period_end = _month_period(month)
    records = _load_gate_records(db, current_user, period_start=period_start, period_end=period_end, team_id=team_id)
    collaborators = _collaborator_map(db, [record.collaborator_id for record in records])
    team_ids_by_collaborator = _team_ids_by_collaborator(
        db,
        [record.collaborator_id for record in records],
        period_start=period_start,
        period_end=period_end,
    )
    anomalies: list[GatePresenzeAnomalyItemResponse] = []
    for record in records:
        item = _serialize_gate_record_item(
            db,
            record,
            collaborator=collaborators.get(record.collaborator_id),
            team_ids=team_ids_by_collaborator.get(record.collaborator_id, []),
        )
        analysis = _gate_record_analysis(db, record)
        if analysis.severity == "none":
            continue
        anomalies.append(
            GatePresenzeAnomalyItemResponse(
                **item.model_dump(),
                reasons=analysis.reasons,
                operator_message=analysis.operator_message,
            )
        )
    return GatePresenzeAnomaliesResponse(
        month=month,
        rules_version=RULES_VERSION,
        generated_at=datetime.now(UTC),
        anomalies=anomalies,
    )


@router.post("/anomalie/{record_id}/resolve", response_model=GatePresenzeDailyRecordDetailResponse)
def resolve_gate_presenze_anomalia(
    record_id: uuid.UUID,
    payload: GatePresenzeResolveAnomalyRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeDailyRecordDetailResponse:
    record = _get_gate_record_or_404(db, current_user, record_id)
    before = _gate_record_snapshot(record)
    record.validation_status = "validated"
    record.validation_note = payload.operator_note
    record.validated_by_user_id = current_user.id
    record.validated_at = datetime.now(UTC)
    _append_gate_audit(
        record,
        action="resolve_anomaly",
        current_user=current_user,
        operator_note=payload.operator_note,
        client_request_id=payload.client_request_id,
        before=before,
        after=_gate_record_snapshot(record),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_gate_record_detail(db, record)


@router.get("/export/preview", response_model=GatePresenzeExportPreviewResponse)
def preview_gate_presenze_export(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    team_id: uuid.UUID | None = Query(default=None),
) -> GatePresenzeExportPreviewResponse:
    period_start, period_end = _month_period(month)
    records = _load_gate_records(db, current_user, period_start=period_start, period_end=period_end, team_id=team_id)
    blocking_total = sum(1 for record in records if _gate_record_analysis(db, record).severity == "blocking")
    return GatePresenzeExportPreviewResponse(
        month=month,
        rules_version=RULES_VERSION,
        export_rules_version=EXPORT_RULES_VERSION,
        records_total=len(records),
        collaborators_total=len({record.collaborator_id for record in records}),
        blocking_anomalies_total=blocking_total,
        can_generate=blocking_total == 0,
    )


@router.post("/export/generate", response_model=GatePresenzeExportGenerateResponse)
def generate_gate_presenze_export(
    payload: GatePresenzeExportGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> GatePresenzeExportGenerateResponse:
    period_start, period_end = _month_period(payload.month)
    records = _load_gate_records(
        db,
        current_user,
        period_start=period_start,
        period_end=period_end,
        team_id=payload.team_id,
    )
    blocking_total = sum(1 for record in records if _gate_record_analysis(db, record).severity == "blocking")
    if blocking_total > 0:
        return GatePresenzeExportGenerateResponse(
            month=payload.month,
            rules_version=RULES_VERSION,
            export_rules_version=EXPORT_RULES_VERSION,
            status="blocked",
            records_total=len(records),
            blocking_anomalies_total=blocking_total,
            message="Export bloccato: chiudere le anomalie bloccanti prima della generazione.",
        )
    return GatePresenzeExportGenerateResponse(
        month=payload.month,
        rules_version=RULES_VERSION,
        export_rules_version=EXPORT_RULES_VERSION,
        status="ready",
        records_total=len(records),
        blocking_anomalies_total=0,
        message="Dataset validato: GATE puo generare l'export con la versione regole dichiarata.",
    )


@router.get("/teams", response_model=list[OrganizationTeamResponse])
def list_gate_presenze_teams(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    scope: str | None = Query(default=None),
    active: bool | None = Query(default=None),
) -> list[OrganizationTeamResponse]:
    stmt = select(OrganizationTeam)
    if scope is not None:
        stmt = stmt.where(OrganizationTeam.scope == scope)
    if active is not None:
        stmt = stmt.where(OrganizationTeam.active.is_(active))
    if not _can_view_all_data(current_user):
        visible_team_ids = _visible_team_ids(db, current_user)
        if not visible_team_ids:
            return []
        stmt = stmt.where(OrganizationTeam.id.in_(visible_team_ids))
    teams = db.execute(stmt.order_by(OrganizationTeam.name.asc())).scalars().all()
    return [_serialize_team(db, team) for team in teams]


@router.post("/teams", response_model=OrganizationTeamResponse)
def create_gate_presenze_team(
    payload: OrganizationTeamCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> OrganizationTeamResponse:
    _require_team_management(current_user)
    team = OrganizationTeam(
        name=payload.name.strip(),
        code=payload.code.strip() if payload.code else None,
        scope=payload.scope,
        active=payload.active,
        created_from_channel="gaia_web",
        created_by_user_id=current_user.id,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return _serialize_team(db, team)


@router.put("/teams/{team_id}", response_model=OrganizationTeamResponse)
def update_gate_presenze_team(
    team_id: uuid.UUID,
    payload: OrganizationTeamUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> OrganizationTeamResponse:
    _require_team_management(current_user)
    team = _get_team_or_404(db, team_id)
    update_payload = payload.model_dump(exclude_unset=True)
    if "name" in update_payload and update_payload["name"] is not None:
        team.name = update_payload["name"].strip()
    if "code" in update_payload:
        team.code = update_payload["code"].strip() if update_payload["code"] else None
    if "scope" in update_payload and update_payload["scope"] is not None:
        team.scope = update_payload["scope"]
    if "active" in update_payload and update_payload["active"] is not None:
        team.active = update_payload["active"]
    db.add(team)
    db.commit()
    db.refresh(team)
    return _serialize_team(db, team)


@router.post("/teams/{team_id}/memberships", response_model=OrganizationTeamMembershipResponse)
def create_gate_presenze_team_membership(
    team_id: uuid.UUID,
    payload: OrganizationTeamMembershipCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> OrganizationTeamMembershipResponse:
    _require_team_management(current_user)
    _get_team_or_404(db, team_id)
    _get_collaborator_or_404(db, payload.collaborator_id)
    _ensure_no_overlapping_membership(
        db,
        collaborator_id=payload.collaborator_id,
        team_id=team_id,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
    )
    membership = OrganizationTeamMembership(
        team_id=team_id,
        collaborator_id=payload.collaborator_id,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        role=payload.role,
        source_channel="gaia_web",
        created_by_user_id=current_user.id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _serialize_membership(db, membership)


@router.post("/teams/{team_id}/supervisors", response_model=OrganizationTeamSupervisorResponse)
def create_gate_presenze_team_supervisor(
    team_id: uuid.UUID,
    payload: OrganizationTeamSupervisorCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> OrganizationTeamSupervisorResponse:
    _require_team_management(current_user)
    _get_team_or_404(db, team_id)
    user = db.get(ApplicationUser, payload.application_user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="Application user not found")
    if not user.module_presenze and not user.is_super_admin:
        raise HTTPException(status_code=409, detail="The selected user is not enabled for the Presenze module")
    assignment = OrganizationTeamSupervisorAssignment(
        team_id=team_id,
        application_user_id=payload.application_user_id,
        permission_scope=payload.permission_scope,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        source_channel="gaia_web",
        assigned_by_user_id=current_user.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _serialize_supervisor(db, assignment)


def _can_view_all_data(current_user: ApplicationUser) -> bool:
    return current_user.role in {"admin", "super_admin", "hr_manager"}


def _require_team_management(current_user: ApplicationUser) -> None:
    if not _can_view_all_data(current_user):
        raise HTTPException(status_code=403, detail="GATE Presenze team management requires admin or HR privileges")


def _periods_overlap(
    left_from: date | None,
    left_to: date | None,
    right_from: date | None,
    right_to: date | None,
) -> bool:
    min_date = date(1, 1, 1)
    max_date = date(9999, 12, 31)
    return (left_from or min_date) <= (right_to or max_date) and (right_from or min_date) <= (left_to or max_date)


def _get_team_or_404(db: Session, team_id: uuid.UUID) -> OrganizationTeam:
    team = db.get(OrganizationTeam, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Organization team not found")
    return team


def _get_collaborator_or_404(db: Session, collaborator_id: uuid.UUID) -> PresenzeCollaborator:
    collaborator = db.get(PresenzeCollaborator, collaborator_id)
    if collaborator is None:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return collaborator


def _ensure_no_overlapping_membership(
    db: Session,
    *,
    collaborator_id: uuid.UUID,
    team_id: uuid.UUID,
    valid_from: date | None,
    valid_to: date | None,
) -> None:
    memberships = db.execute(
        select(OrganizationTeamMembership).where(
            OrganizationTeamMembership.collaborator_id == collaborator_id,
        )
    ).scalars().all()
    for membership in memberships:
        if not _periods_overlap(valid_from, valid_to, membership.valid_from, membership.valid_to):
            continue
        if membership.team_id == team_id:
            raise HTTPException(status_code=409, detail="Collaborator already belongs to this team in the selected period")
        raise HTTPException(status_code=409, detail="Collaborator already belongs to another team in the selected period")


def _visible_team_ids(db: Session, current_user: ApplicationUser) -> list[uuid.UUID]:
    today = date.today()
    rows = db.execute(
        select(OrganizationTeamSupervisorAssignment.team_id).where(
            OrganizationTeamSupervisorAssignment.application_user_id == current_user.id,
            or_(OrganizationTeamSupervisorAssignment.valid_from.is_(None), OrganizationTeamSupervisorAssignment.valid_from <= today),
            or_(OrganizationTeamSupervisorAssignment.valid_to.is_(None), OrganizationTeamSupervisorAssignment.valid_to >= today),
        )
    ).scalars().all()
    return list(dict.fromkeys(rows))


def _serialize_membership(
    db: Session,
    membership: OrganizationTeamMembership,
) -> OrganizationTeamMembershipResponse:
    collaborator = db.get(PresenzeCollaborator, membership.collaborator_id)
    return OrganizationTeamMembershipResponse.model_validate(
        {
            **membership.__dict__,
            "collaborator_name": collaborator.name if collaborator is not None else None,
            "employee_code": collaborator.employee_code if collaborator is not None else None,
        }
    )


def _serialize_supervisor(
    db: Session,
    assignment: OrganizationTeamSupervisorAssignment,
) -> OrganizationTeamSupervisorResponse:
    user = db.get(ApplicationUser, assignment.application_user_id)
    return OrganizationTeamSupervisorResponse.model_validate(
        {
            **assignment.__dict__,
            "user_label": (user.full_name or user.username) if user is not None else None,
            "username": user.username if user is not None else None,
        }
    )


def _serialize_team(db: Session, team: OrganizationTeam) -> OrganizationTeamResponse:
    memberships = db.execute(
        select(OrganizationTeamMembership)
        .where(OrganizationTeamMembership.team_id == team.id)
        .order_by(OrganizationTeamMembership.valid_from.asc(), OrganizationTeamMembership.created_at.asc())
    ).scalars().all()
    supervisors = db.execute(
        select(OrganizationTeamSupervisorAssignment)
        .where(OrganizationTeamSupervisorAssignment.team_id == team.id)
        .order_by(
            OrganizationTeamSupervisorAssignment.permission_scope.asc(),
            OrganizationTeamSupervisorAssignment.created_at.asc(),
        )
    ).scalars().all()
    return OrganizationTeamResponse.model_validate(
        {
            **team.__dict__,
            "memberships": [_serialize_membership(db, membership) for membership in memberships],
            "supervisors": [_serialize_supervisor(db, supervisor) for supervisor in supervisors],
        }
    )


def _build_rules_response() -> GatePresenzeRulesResponse:
    return GatePresenzeRulesResponse(
        rules_version=RULES_VERSION,
        export_rules_version=EXPORT_RULES_VERSION,
        updated_at=datetime(2026, 7, 8, tzinfo=UTC),
        summary=(
            "GAIA calcola giornaliere e anomalie come source of truth. GATE usa le stesse regole "
            "per mostrare agli operatori cosa correggere, cosa verificare e quando l'export puo essere generato."
        ),
        sections=[
            GatePresenzeRuleSectionResponse(
                code="anomalie",
                title="Anomalie operative",
                description="Regole che determinano se una giornata entra nella coda di verifica.",
                rules=[
                    GatePresenzeRuleItemResponse(
                        code="extra_over_3h",
                        title="Straordinario oltre 3 ore",
                        description=(
                            "Una giornata con timbrature complete e solo extra/straordinario non e bloccante fino a 180 minuti. "
                            "Oltre 180 minuti entra nella coda Da verificare."
                        ),
                        severity="warning",
                        applies_to=["operai", "impiegati", "giornaliere", "anomalie"],
                        operator_action="Verificare autorizzazione e validare se lo straordinario e corretto.",
                    ),
                    GatePresenzeRuleItemResponse(
                        code="missing_or_blocking_time",
                        title="Minuti mancanti o giornata bloccante",
                        description="Se mancano timbrature essenziali, teorico, causale o copertura coerente, la giornata e bloccante.",
                        severity="blocking",
                        applies_to=["giornaliere", "anomalie", "export"],
                        operator_action="Correggere dati operativi o causale prima dell'export.",
                    ),
                    GatePresenzeRuleItemResponse(
                        code="inaz_detail_anomaly",
                        title="Anomalia tecnica Inaz",
                        description=(
                            "Le anomalie tecniche Inaz vengono mostrate come Da verificare, ma non prevalgono se GAIA ricostruisce "
                            "una giornata coerente con timbrature, teorico e causali."
                        ),
                        severity="warning",
                        applies_to=["inaz", "giornaliere", "anomalie"],
                        operator_action="Controllare il dettaglio e confermare se la giornata e coerente.",
                    ),
                ],
            ),
            GatePresenzeRuleSectionResponse(
                code="validazione",
                title="Validazione e audit",
                description="Regole di scrittura usate da GAIA e GATE quando un operatore lavora una giornata.",
                rules=[
                    GatePresenzeRuleItemResponse(
                        code="gate_writes_gaia",
                        title="GATE scrive direttamente su GAIA",
                        description="Ogni validazione, patch o chiusura anomalia fatta da GATE viene salvata su GAIA e poi riletta da GAIA.",
                        severity="info",
                        applies_to=["gate", "gaia", "audit"],
                        operator_action="Dopo il salvataggio verificare lo stato aggiornato mostrato dal sistema.",
                    ),
                    GatePresenzeRuleItemResponse(
                        code="gate_audit",
                        title="Audit canale GATE",
                        description="Le azioni GATE registrano canale, utente, nota operatore, client_request_id, versione regole e prima/dopo.",
                        severity="info",
                        applies_to=["gate", "audit"],
                        operator_action="Inserire una nota quando la decisione non e immediatamente evidente.",
                    ),
                ],
            ),
            GatePresenzeRuleSectionResponse(
                code="export",
                title="Export",
                description="Regole che determinano se il dataset e pronto per generare il file mensile.",
                rules=[
                    GatePresenzeRuleItemResponse(
                        code="export_blocking_anomalies",
                        title="Export bloccato da anomalie bloccanti",
                        description="L'export non e pronto se esistono giornate con severita Bloccante non chiuse.",
                        severity="blocking",
                        applies_to=["export", "anomalie"],
                        operator_action="Chiudere o correggere tutte le anomalie bloccanti prima di generare il file.",
                    ),
                    GatePresenzeRuleItemResponse(
                        code="export_rules_version",
                        title="Versione regole export",
                        description="Ogni preview/export espone export_rules_version per allineare GAIA e GATE.",
                        severity="info",
                        applies_to=["export", "gate"],
                        operator_action="Segnalare mismatch se la versione usata da GATE differisce da quella esposta da GAIA.",
                    ),
                ],
            ),
        ],
    )


def _month_period(month: str) -> tuple[date, date]:
    try:
        period_start = date.fromisoformat(f"{month}-01")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be in YYYY-MM format") from exc
    period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return period_start, period_end


def _period_membership_collaborator_ids(
    db: Session,
    *,
    period_start: date | None,
    period_end: date | None,
    team_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    stmt = select(OrganizationTeamMembership.collaborator_id)
    if team_ids is not None:
        if not team_ids:
            return []
        stmt = stmt.where(OrganizationTeamMembership.team_id.in_(team_ids))
    if period_start is not None and period_end is not None:
        stmt = stmt.where(
            or_(OrganizationTeamMembership.valid_from.is_(None), OrganizationTeamMembership.valid_from <= period_end),
            or_(OrganizationTeamMembership.valid_to.is_(None), OrganizationTeamMembership.valid_to >= period_start),
        )
    rows = db.execute(stmt).scalars().all()
    return list(dict.fromkeys(rows))


def _visible_team_ids_for_period(
    db: Session,
    current_user: ApplicationUser,
    *,
    period_start: date | None,
    period_end: date | None,
) -> list[uuid.UUID]:
    stmt = select(OrganizationTeamSupervisorAssignment.team_id).where(
        OrganizationTeamSupervisorAssignment.application_user_id == current_user.id,
    )
    if period_start is not None and period_end is not None:
        stmt = stmt.where(
            or_(OrganizationTeamSupervisorAssignment.valid_from.is_(None), OrganizationTeamSupervisorAssignment.valid_from <= period_end),
            or_(OrganizationTeamSupervisorAssignment.valid_to.is_(None), OrganizationTeamSupervisorAssignment.valid_to >= period_start),
        )
    rows = db.execute(stmt).scalars().all()
    return list(dict.fromkeys(rows))


def _apply_gate_record_visibility(
    db: Session,
    current_user: ApplicationUser,
    *,
    stmt,
    period_start: date | None,
    period_end: date | None,
    team_id: uuid.UUID | None,
):
    if period_start is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date >= period_start)
    if period_end is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date <= period_end)

    selected_team_ids: list[uuid.UUID] | None = [team_id] if team_id is not None else None
    if not _can_view_all_data(current_user):
        visible_team_ids = _visible_team_ids_for_period(
            db,
            current_user,
            period_start=period_start,
            period_end=period_end,
        )
        if selected_team_ids is not None:
            selected_team_ids = [value for value in selected_team_ids if value in set(visible_team_ids)]
        else:
            selected_team_ids = visible_team_ids
        if not selected_team_ids:
            return stmt.where(PresenzeDailyRecord.id.is_(None))

    collaborator_ids = _period_membership_collaborator_ids(
        db,
        period_start=period_start,
        period_end=period_end,
        team_ids=selected_team_ids,
    )
    if selected_team_ids is not None and not collaborator_ids:
        return stmt.where(PresenzeDailyRecord.id.is_(None))
    if collaborator_ids:
        stmt = stmt.where(PresenzeDailyRecord.collaborator_id.in_(collaborator_ids))
    return stmt


def _load_gate_records(
    db: Session,
    current_user: ApplicationUser,
    *,
    period_start: date,
    period_end: date,
    team_id: uuid.UUID | None,
) -> list[PresenzeDailyRecord]:
    stmt = _apply_gate_record_visibility(
        db,
        current_user,
        stmt=select(PresenzeDailyRecord),
        period_start=period_start,
        period_end=period_end,
        team_id=team_id,
    )
    return db.execute(
        stmt.order_by(PresenzeDailyRecord.work_date.asc(), PresenzeDailyRecord.collaborator_id.asc())
    ).scalars().all()


def _collaborator_map(
    db: Session,
    collaborator_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PresenzeCollaborator]:
    if not collaborator_ids:
        return {}
    rows = db.execute(
        select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(list(dict.fromkeys(collaborator_ids))))
    ).scalars().all()
    return {row.id: row for row in rows}


def _team_ids_by_collaborator(
    db: Session,
    collaborator_ids: list[uuid.UUID],
    *,
    period_start: date,
    period_end: date,
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not collaborator_ids:
        return {}
    rows = db.execute(
        select(OrganizationTeamMembership).where(
            OrganizationTeamMembership.collaborator_id.in_(list(dict.fromkeys(collaborator_ids))),
            or_(OrganizationTeamMembership.valid_from.is_(None), OrganizationTeamMembership.valid_from <= period_end),
            or_(OrganizationTeamMembership.valid_to.is_(None), OrganizationTeamMembership.valid_to >= period_start),
        )
    ).scalars().all()
    result: dict[uuid.UUID, list[uuid.UUID]] = {}
    for row in rows:
        result.setdefault(row.collaborator_id, []).append(row.team_id)
    return result


def _get_gate_record_or_404(
    db: Session,
    current_user: ApplicationUser,
    record_id: uuid.UUID,
) -> PresenzeDailyRecord:
    record = db.get(PresenzeDailyRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Daily record not found")
    if _can_view_all_data(current_user):
        return record
    team_ids = _visible_team_ids_for_period(
        db,
        current_user,
        period_start=record.work_date,
        period_end=record.work_date,
    )
    collaborator_ids = _period_membership_collaborator_ids(
        db,
        period_start=record.work_date,
        period_end=record.work_date,
        team_ids=team_ids,
    )
    if record.collaborator_id not in set(collaborator_ids):
        raise HTTPException(status_code=404, detail="Daily record not found")
    return record


def _weekday_label(value: date) -> str:
    labels = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
    return labels[value.weekday()]


def _record_has_complete_punches(db: Session, record_id: uuid.UUID) -> bool:
    punches = db.execute(
        select(PresenzeDailyPunch).where(PresenzeDailyPunch.daily_record_id == record_id)
    ).scalars().all()
    return bool(punches) and all(punch.entry_time is not None and punch.exit_time is not None for punch in punches)


def _serialize_gate_record_item(
    db: Session,
    record: PresenzeDailyRecord,
    *,
    collaborator: PresenzeCollaborator | None,
    team_ids: list[uuid.UUID],
) -> GatePresenzeDailyRecordItemResponse:
    serialized = _serialize_daily_record(db, record, include_raw_payload=False)
    analysis = _gate_record_analysis_from_serialized(record, serialized)
    return GatePresenzeDailyRecordItemResponse(
        record_id=record.id,
        collaborator_id=record.collaborator_id,
        collaborator_name=collaborator.name if collaborator is not None else str(record.collaborator_id),
        employee_code=collaborator.employee_code if collaborator is not None else "",
        team_ids=team_ids,
        work_date=record.work_date,
        weekday=_weekday_label(record.work_date),
        status=serialized.operational_status,
        review_status=record.validation_status,
        severity=analysis.severity,
        contract_kind=collaborator.contract_kind if collaborator is not None else None,
        schedule_code=record.schedule_code,
        ordinary_minutes=record.ordinary_minutes,
        extra_minutes=serialized.effective_extra_minutes or 0,
        missing_minutes=serialized.operational_missing_minutes,
        absence_cause=serialized.resolved_absence_cause,
        has_request=bool(serialized.detail_requests or record.request_type or record.request_description),
        has_complete_punches=_record_has_complete_punches(db, record.id),
        validated_at=record.validated_at,
        validated_by_user_id=record.validated_by_user_id,
    )


def _gate_record_analysis(db: Session, record: PresenzeDailyRecord) -> GatePresenzeDailyRecordAnalysisResponse:
    serialized = _serialize_daily_record(db, record, include_raw_payload=False)
    return _gate_record_analysis_from_serialized(record, serialized)


def _gate_record_analysis_from_serialized(
    record: PresenzeDailyRecord,
    serialized,
) -> GatePresenzeDailyRecordAnalysisResponse:
    if record.validation_status == "validated":
        return GatePresenzeDailyRecordAnalysisResponse(
            status="ok",
            severity="none",
            reasons=[],
            operator_message="Giornata gia validata.",
        )
    reasons: list[str] = []
    severity = "none"
    if serialized.operational_status == "blocking" or serialized.operational_missing_minutes > 0:
        severity = "blocking"
        reasons.append("missing_or_blocking_time")
    if (serialized.effective_extra_minutes or 0) > 180:
        if severity != "blocking":
            severity = "warning"
        reasons.append("extra_over_3h")
    if serialized.detail_error or serialized.detail_anomalies:
        if severity != "blocking":
            severity = "warning"
        reasons.append("inaz_detail_anomaly")
    if serialized.operational_status == "in_analysis":
        if severity != "blocking":
            severity = "warning"
        reasons.append("operational_review")
    if severity == "blocking":
        return GatePresenzeDailyRecordAnalysisResponse(
            status="correggere_subito",
            severity="blocking",
            reasons=reasons,
            operator_message="Giornata bloccante: correggere timbrature, causali o minuti mancanti prima dell'export.",
        )
    if severity == "warning":
        return GatePresenzeDailyRecordAnalysisResponse(
            status="da_verificare",
            severity="warning",
            reasons=reasons,
            operator_message="Giornata da verificare: controllare extra, richieste o anomalie tecniche.",
        )
    return GatePresenzeDailyRecordAnalysisResponse(
        status="ok",
        severity="none",
        reasons=[],
        operator_message="Giornata coerente secondo le regole GAIA.",
    )


def _serialize_gate_record_detail(
    db: Session,
    record: PresenzeDailyRecord,
) -> GatePresenzeDailyRecordDetailResponse:
    collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
    serialized = _serialize_daily_record(db, record, include_raw_payload=True)
    return GatePresenzeDailyRecordDetailResponse(
        record_id=record.id,
        rules_version=RULES_VERSION,
        collaborator={
            "id": str(record.collaborator_id),
            "name": collaborator.name if collaborator is not None else str(record.collaborator_id),
            "employee_code": collaborator.employee_code if collaborator is not None else None,
            "contract_kind": collaborator.contract_kind if collaborator is not None else None,
            "operai_group": collaborator.operai_group if collaborator is not None else None,
        },
        work_date=record.work_date,
        analysis=_gate_record_analysis_from_serialized(record, serialized),
        record=serialized,
        audit=_gate_audit_entries(record),
    )


def _gate_audit_entries(record: PresenzeDailyRecord) -> list[dict]:
    if isinstance(record.raw_payload_json, dict):
        value = record.raw_payload_json.get("_gate_audit")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _gate_record_snapshot(record: PresenzeDailyRecord) -> dict[str, object]:
    return {
        "validation_status": record.validation_status,
        "validated_by_user_id": record.validated_by_user_id,
        "validated_at": record.validated_at.isoformat() if record.validated_at is not None else None,
        "km_value": record.km_value,
        "trasferta_minutes": record.trasferta_minutes,
        "trasferta_montano": record.trasferta_montano,
        "reperibilita_unit": record.reperibilita_unit,
        "reperibilita_quantity": record.reperibilita_quantity,
        "override_straordinario_minutes": record.override_straordinario_minutes,
        "override_mpe_minutes": record.override_mpe_minutes,
        "manual_note": record.manual_note,
        "validation_note": record.validation_note,
    }


def _append_gate_audit(
    record: PresenzeDailyRecord,
    *,
    action: str,
    current_user: ApplicationUser,
    operator_note: str | None,
    client_request_id: str | None,
    before: dict[str, object],
    after: dict[str, object],
) -> None:
    raw_payload = dict(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {"_source_payload": record.raw_payload_json}
    audit = raw_payload.get("_gate_audit")
    if not isinstance(audit, list):
        audit = []
    audit.append(
        {
            "action": action,
            "channel": "gate_mobile",
            "user_id": current_user.id,
            "username": current_user.username,
            "operator_note": operator_note,
            "client_request_id": client_request_id,
            "rules_version": RULES_VERSION,
            "at": datetime.now(UTC).isoformat(),
            "before": before,
            "after": after,
        }
    )
    raw_payload["_gate_audit"] = audit
    record.raw_payload_json = raw_payload
    flag_modified(record, "raw_payload_json")
