from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_role
from app.core.config import settings
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.schemas.users import ApplicationUserResponse
from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeBankHoursAdjustment,
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeCredential,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeEventSummary,
    PresenzeHoliday,
    PresenzeImportJob,
    PresenzeOperaiRuleConfig,
    PresenzeRecoveryAdjustment,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
    PresenzeSupervisorAssignment,
    PresenzeSyncJob,
)
from app.modules.presenze.schemas import (
    PresenzeAnomalyListItemResponse,
    PresenzeAnomalyListResponse,
    PresenzeAnomalyMonthSummaryItemResponse,
    PresenzeAnomalyMonthSummaryResponse,
    PresenzeAccessContextResponse,
    PresenzeAutoSyncConfigResponse,
    PresenzeAutoSyncConfigUpdate,
    PresenzeBankHoursAdjustmentCreate,
    PresenzeBankHoursAdjustmentResponse,
    PresenzeBankHoursAdjustmentReview,
    PresenzeBankHoursAdjustmentUpdate,
    PresenzeBankHoursBalanceItemResponse,
    PresenzeBankHoursCompensationSummaryResponse,
    PresenzeBankHoursCollaboratorDetailResponse,
    PresenzeBankHoursDashboardResponse,
    PresenzeBankHoursGuidanceConfigResponse,
    PresenzeBankHoursGuidanceConfigRevisionResponse,
    PresenzeBankHoursGuidanceConfigUpdate,
    PresenzeBankHoursLiquidationGuidanceResponse,
    PresenzeBankHoursSnapshotResponse,
    PresenzeScheduleBootstrapApplyRequest,
    PresenzeScheduleBootstrapApplyResponse,
    PresenzeScheduleBootstrapCollaboratorSuggestion,
    PresenzeScheduleBootstrapPresetPreview,
    PresenzeScheduleBootstrapPreviewResponse,
    PresenzeScheduleProfilePreview,
    PresenzeScheduleBootstrapRulePreview,
    PresenzeCollaboratorApplicationUserUpdate,
    PresenzeCollaboratorContractProfileUpdate,
    PresenzeCollaboratorScheduleAssignmentCreate,
    PresenzeCollaboratorScheduleAssignmentResponse,
    PresenzeCollaboratorCalendarResponse,
    PresenzeCollaboratorListResponse,
    PresenzeCollaboratorResponse,
    PresenzeCredentialCreate,
    PresenzeCredentialResponse,
    PresenzeCredentialTestResult,
    PresenzeCredentialUpdate,
    PresenzeCollaboratorSummaryResponse,
    PresenzeDailyRecordListResponse,
    PresenzeDailyRecordManualUpdate,
    PresenzeDailyRecordResponse,
    PresenzeDashboardSummaryResponse,
    PresenzeEventSummaryResponse,
    PresenzeHolidayBootstrapResponse,
    PresenzeHolidayCreate,
    PresenzeHolidayResponse,
    PresenzeHolidayUpdate,
    PresenzeImportJobListResponse,
    PresenzeImportJobResponse,
    PresenzeImportJsonResponse,
    PresenzeImportPreviewResponse,
    PresenzeModuleStatusResponse,
    PresenzeOperaiRuleConfigResponse,
    PresenzeOperaiRuleConfigUpdate,
    PresenzeRecoveryAdjustmentCreate,
    PresenzeRecoveryAdjustmentResponse,
    PresenzeRecoveryAdjustmentReview,
    PresenzeRecoveryAdjustmentUpdate,
    PresenzeRecoveryBalanceItemResponse,
    PresenzeRecoveryDashboardResponse,
    PresenzeScheduleRuleCreate,
    PresenzeScheduleRuleResponse,
    PresenzeScheduleRuleUpdate,
    PresenzeScheduleTemplateCreate,
    PresenzeScheduleTemplateResponse,
    PresenzeScheduleTemplateUpdate,
    PresenzeSupervisorAssignmentResponse,
    PresenzeSupervisorAssignmentUpdate,
    PresenzeStraordinariExportJobCreateRequest,
    PresenzeStraordinariPreviewItemResponse,
    PresenzeStraordinariPreviewResponse,
    PresenzeXlsmExportJobCreateRequest,
    PresenzeSyncJobCreateRequest,
    PresenzeSyncJobListResponse,
    PresenzeSyncJobRetrySelectedRequest,
    PresenzeSyncJobResponse,
)
from app.modules.presenze.services.contract_profile import (
    PresenzeContractProfile,
    normalize_contract_kind,
    normalize_operai_group,
    resolve_contract_profile,
)
from app.modules.presenze.services.credentials import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    test_credential,
    update_credential,
)
from app.modules.presenze.services.import_jobs import build_preview, run_import_job
from app.modules.presenze.services.parser import (
    detail_indicates_special_day,
    detail_indicates_recovery_usage,
    extract_punch_terminal_labels,
    extract_detail_payload,
    load_json_payload,
    parse_import_payload,
    resolve_absence_cause,
    resolve_request_authorized_by,
    resolve_request_description,
    resolve_request_status,
    resolve_request_type,
)
from app.modules.presenze.services.operational_quality import build_daily_operational_quality, build_operai_operational_quality, complete_punch_minutes
from app.modules.presenze.services.operai_rules import ensure_operai_rule_configs, load_operai_rule_configs
from app.modules.presenze.services.schedule_engine import build_schedule_context, classify_daily_record, seed_holidays_for_year
from app.modules.presenze.services.auto_sync import get_auto_sync_config, serialize_auto_sync_config, update_auto_sync_config
from app.modules.presenze.services.bank_hours_guidance_config import (
    get_bank_hours_guidance_config,
    list_bank_hours_guidance_config_revisions,
    serialize_bank_hours_guidance_config_with_user,
    serialize_bank_hours_guidance_revision,
    update_bank_hours_guidance_config,
)
from app.modules.presenze.services.sync_runtime import (
    apply_sync_job_retention,
    build_period,
    delete_sync_artifact_dir,
    get_sync_artifact_dir,
    has_running_sync_job,
    launch_straordinari_export_worker,
    launch_xlsm_export_worker,
    prepare_sync_job_artifacts,
    reconcile_stale_sync_jobs,
    resolve_sync_artifact_path,
    stop_sync_worker,
)
from app.modules.presenze.services.straordinari_export_job import (
    build_period_end as build_straordinari_period_end,
    build_straordinari_export_items,
    build_straordinari_filename,
    format_duration_label,
    list_straordinari_preview_items,
    previous_month_period_start,
)
from app.modules.presenze.services.xlsm_export import DEFAULT_TEMPLATE_PATH
from app.modules.presenze.services.xlsm_export_job import (
    build_period_end,
    generate_xlsm_export,
    resolve_export_template_path as _resolve_export_template_path,
)
from app.modules.accessi.org_structure import OrgStructureAssignment

router = APIRouter(prefix="/presenze", tags=["presenze"])
RequirePresenzeModule = Depends(require_module("presenze"))
RequirePresenzeAdmin = Depends(require_role("super_admin", "admin"))


def _normalize_employee_codes(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        code = str(value or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return normalized


def _load_sync_job_summary(job_id: str) -> dict[str, object]:
    summary_path = resolve_sync_artifact_path(job_id, "summary")
    if not summary_path.exists():
        raise HTTPException(status_code=409, detail="Summary artifact not available for this sync job")
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=409, detail="Summary artifact is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=409, detail="Summary artifact has an unexpected structure")
    return payload


@dataclass(frozen=True)
class _BootstrapRuleDefinition:
    label: str | None
    weekday: int | None
    recurrence_kind: str
    start_time: time
    end_time: time
    week_of_month: int | None = None
    interval_weeks: int | None = None
    anchor_date: date | None = None
    season_start_month: int | None = None
    season_start_day: int | None = None
    season_end_month: int | None = None
    season_end_day: int | None = None
    applies_on_holiday: bool = False
    ordinary_label: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class _BootstrapTemplatePreset:
    preset_key: str
    template_code: str
    template_label: str
    template_notes: str
    source_schedule_codes: tuple[str, ...]
    rules: tuple[_BootstrapRuleDefinition, ...]


@dataclass(frozen=True)
class _SystemScheduleTemplateDefinition:
    code: str
    label: str
    company_code: str | None
    notes: str
    rules: tuple[_BootstrapRuleDefinition, ...] = ()


@dataclass(frozen=True)
class _ScheduleProfileDefinition:
    profile_code: str
    profile_label: str
    description: str
    default_template_code: str | None
    template_codes: tuple[str, ...]
    assignable_template_codes: tuple[str, ...]
    inherited_template_codes: tuple[str, ...]
    rule_summaries: tuple[str, ...]


_OPERAI_SUMMER_START_MONTH = 6
_OPERAI_SUMMER_START_DAY = 1
_OPERAI_SUMMER_END_MONTH = 9
_OPERAI_SUMMER_END_DAY = 30


BOOTSTRAP_TEMPLATE_PRESETS: tuple[_BootstrapTemplatePreset, ...] = (
    _BootstrapTemplatePreset(
        preset_key="operai_0714_primo_terzo_sabato",
        template_code="OPE0714_1E3SAB",
        template_label="Operai 07:00-14:00 con 1° e 3° sabato",
        template_notes=(
            "Generato da INAZ: OPE0714 / OPE0613 / OP_5.3_12.3 + OPESAB / OSAB5.3_12.3. "
            "Default GAIA: fascia estiva 01/06-30/09 con timbrature anticipate ma ore operaio invariate. "
            "Verificare i sabati 1° e 3° del mese."
        ),
        source_schedule_codes=("OPE0714", "OPE0613", "OP_5.3_12.3", "OPESAB", "OSAB5.3_12.3"),
        rules=(
            _BootstrapRuleDefinition(
                label="Lun 07:00-14:00",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=0,
            ),
            _BootstrapRuleDefinition(
                label="Lun 05:30-12:30",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=5,
            ),
            _BootstrapRuleDefinition(
                label="Mar 07:00-14:00",
                weekday=1,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=10,
            ),
            _BootstrapRuleDefinition(
                label="Mar 05:30-12:30",
                weekday=1,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=15,
            ),
            _BootstrapRuleDefinition(
                label="Mer 07:00-14:00",
                weekday=2,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=20,
            ),
            _BootstrapRuleDefinition(
                label="Mer 05:30-12:30",
                weekday=2,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=25,
            ),
            _BootstrapRuleDefinition(
                label="Gio 07:00-14:00",
                weekday=3,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=30,
            ),
            _BootstrapRuleDefinition(
                label="Gio 05:30-12:30",
                weekday=3,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=35,
            ),
            _BootstrapRuleDefinition(
                label="Ven 07:00-14:00",
                weekday=4,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPE0714",
                sort_order=40,
            ),
            _BootstrapRuleDefinition(
                label="Ven 05:30-12:30",
                weekday=4,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OP_5.3_12.3",
                sort_order=45,
            ),
            _BootstrapRuleDefinition(
                label="1° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="first_weekday_of_month",
                start_time=time(7, 0),
                end_time=time(13, 30),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPESAB",
                sort_order=50,
            ),
            _BootstrapRuleDefinition(
                label="1° sabato 05:30-12:30",
                weekday=5,
                recurrence_kind="first_weekday_of_month",
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OSAB5.3_12.3",
                sort_order=55,
            ),
            _BootstrapRuleDefinition(
                label="3° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="nth_weekday_of_month",
                week_of_month=3,
                start_time=time(7, 0),
                end_time=time(13, 30),
                season_start_month=10,
                season_start_day=1,
                season_end_month=_OPERAI_SUMMER_START_MONTH,
                season_end_day=_OPERAI_SUMMER_START_DAY - 1,
                ordinary_label="OPESAB",
                sort_order=60,
            ),
            _BootstrapRuleDefinition(
                label="3° sabato 05:30-12:30",
                weekday=5,
                recurrence_kind="nth_weekday_of_month",
                week_of_month=3,
                start_time=time(5, 30),
                end_time=time(12, 30),
                season_start_month=_OPERAI_SUMMER_START_MONTH,
                season_start_day=_OPERAI_SUMMER_START_DAY,
                season_end_month=_OPERAI_SUMMER_END_MONTH,
                season_end_day=_OPERAI_SUMMER_END_DAY,
                ordinary_label="OSAB5.3_12.3",
                sort_order=65,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_flessibile",
        template_code="IMP1_STD",
        template_label="Impiegati flessibile 07:35-14:00",
        template_notes="Generato da INAZ: IMP1.",
        source_schedule_codes=("IMP1",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(7, 35),
                end_time=time(14, 0),
                ordinary_label="IMP1",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_rientro",
        template_code="IMP1_RIENTRO",
        template_label="Impiegati con rientro 07:35-14:00 / 14:30-17:45",
        template_notes="Generato da INAZ: IMP1 + RIENTRO IMP.",
        source_schedule_codes=("IMP1", "RIENTRO IMP"),
        rules=(
            *tuple(
                _BootstrapRuleDefinition(
                    label=f"Giorno feriale {weekday}",
                    weekday=weekday,
                    recurrence_kind="weekly",
                    start_time=time(7, 35),
                    end_time=time(14, 0),
                    ordinary_label="IMP1",
                    sort_order=weekday,
                )
                for weekday in range(5)
            ),
            _BootstrapRuleDefinition(
                label="Rientro lunedi pomeriggio",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(14, 30),
                end_time=time(17, 45),
                ordinary_label="RIENTRO IMP",
                sort_order=10,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="operai_0620_1356",
        template_code="OPE0736_STD",
        template_label="Operai 06:20-13:56",
        template_notes="Generato da INAZ: OPE0736.",
        source_schedule_codes=("OPE0736",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(6, 20),
                end_time=time(13, 56),
                ordinary_label="OPE0736",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
)

SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS: tuple[_SystemScheduleTemplateDefinition, ...] = (
    _SystemScheduleTemplateDefinition(
        code="OPE0613",
        label="Operai 06:00-13:00",
        company_code="53",
        notes="Template orario feriale per codice INAZ OPE0613. Per gli operai il teorico resta 7h e viene verificato dal motore legato a operai_group.",
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(6, 0),
                end_time=time(13, 0),
                ordinary_label="OPE0613",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _SystemScheduleTemplateDefinition(
        code="OP_5.3_12.3",
        label="Operai 05:30-12:30",
        company_code="53",
        notes="Template orario feriale per codice INAZ OP_5.3_12.3. Per gli operai i minuti attesi restano comunque verificati dal motore legato a operai_group.",
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(5, 30),
                end_time=time(12, 30),
                ordinary_label="OP_5.3_12.3",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _SystemScheduleTemplateDefinition(
        code="OSAB5.3_12.3",
        label="Operai sabato 05:30-12:30",
        company_code="53",
        notes="Template orario sabato per codice INAZ OSAB5.3_12.3. Non impone da solo i minuti nominali: per gli operai il teorico del sabato resta definito da operai_group (agrario 6h30, catasto/magazzino 6h).",
    ),
)

SCHEDULE_PROFILE_DEFINITIONS: tuple[_ScheduleProfileDefinition, ...] = (
    _ScheduleProfileDefinition(
        profile_code="operai_gaia",
        profile_label="Profilo Operai",
        description=(
            "Controllo rigido delle ore effettive con assegnazione flessibile del turno INAZ: "
            "agrario e catasto/magazzino condividono il profilo, ma hanno regole sabato diverse."
        ),
        default_template_code="OPE0714_1E3SAB",
        template_codes=("OPE0714_1E3SAB", "OPE0736_STD", "OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"),
        assignable_template_codes=("OPE0714_1E3SAB", "OPE0736_STD"),
        inherited_template_codes=("OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"),
        rule_summaries=("Feriale 7h", "Agrario sabato 6h30", "Catasto/magazzino sabato 6h"),
    ),
    _ScheduleProfileDefinition(
        profile_code="impiegati_gaia",
        profile_label="Profilo Impiegati",
        description=(
            "Profilo gestionale per impiegati con orari INAZ flessibili, rientri e controllo banca ore "
            "separato dalle regole rigide degli operai."
        ),
        default_template_code="IMP1_STD",
        template_codes=("IMP1_STD", "IMP1_RIENTRO"),
        assignable_template_codes=("IMP1_STD", "IMP1_RIENTRO"),
        inherited_template_codes=(),
        rule_summaries=("Flessibile IMP1", "Rientro lunedi pomeriggio", "Controllo banca ore / anomalie"),
    ),
)


@router.get("", response_model=PresenzeModuleStatusResponse)
def get_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeModuleStatusResponse:
    return PresenzeModuleStatusResponse(
        module="presenze",
        enabled=True,
        username=current_user.username,
        message="GAIA Presenze collaboratori module is enabled for the current user.",
    )


@router.get("/access-context", response_model=PresenzeAccessContextResponse)
def get_presenze_access_context(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAccessContextResponse:
    assigned_count = int(
        db.scalar(
            select(func.count(PresenzeSupervisorAssignment.id)).where(
                PresenzeSupervisorAssignment.supervisor_user_id == current_user.id
            )
        )
        or 0
    )
    hierarchy_scope_count = len(_hierarchy_scope_user_ids(db, current_user))
    return PresenzeAccessContextResponse(
        can_view_all_data=_can_view_all_inaz_data(current_user),
        can_view_all_credentials=current_user.is_super_admin,
        can_manage_supervisors=_can_manage_supervisors(current_user),
        is_supervisor=assigned_count > 0 or hierarchy_scope_count > 0,
        assigned_collaborators_count=assigned_count + hierarchy_scope_count,
    )


@router.get("/application-users", response_model=list[ApplicationUserResponse])
def list_inaz_application_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[ApplicationUserResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Presenze user management requires admin privileges")
    rows = db.execute(
        select(ApplicationUser)
        .where(ApplicationUser.is_active.is_(True), ApplicationUser.module_presenze.is_(True))
        .order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())
    ).scalars().all()
    return [ApplicationUserResponse.model_validate(row) for row in rows]


@router.get("/supervisor-assignments", response_model=list[PresenzeSupervisorAssignmentResponse])
def list_supervisor_assignments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    supervisor_user_id: int | None = Query(default=None),
) -> list[PresenzeSupervisorAssignmentResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    stmt = select(PresenzeSupervisorAssignment)
    if supervisor_user_id is not None:
        stmt = stmt.where(PresenzeSupervisorAssignment.supervisor_user_id == supervisor_user_id)
    rows = db.execute(
        stmt.order_by(
            PresenzeSupervisorAssignment.supervisor_user_id.asc(),
            PresenzeSupervisorAssignment.collaborator_id.asc(),
        )
    ).scalars().all()
    return [_serialize_supervisor_assignment(db, row) for row in rows]


@router.put("/supervisor-assignments/{collaborator_id}", response_model=PresenzeSupervisorAssignmentResponse | None)
def update_supervisor_assignment(
    collaborator_id: uuid.UUID,
    payload: PresenzeSupervisorAssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSupervisorAssignmentResponse | None:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    _get_collaborator_or_404(db, collaborator_id)
    assignment = db.execute(
        select(PresenzeSupervisorAssignment).where(PresenzeSupervisorAssignment.collaborator_id == collaborator_id)
    ).scalar_one_or_none()

    if payload.supervisor_user_id is None:
        if assignment is not None:
            db.delete(assignment)
            db.commit()
        return None

    supervisor = db.get(ApplicationUser, payload.supervisor_user_id)
    if supervisor is None or not supervisor.is_active:
        raise HTTPException(status_code=404, detail="Supervisor user not found")
    if not supervisor.module_presenze and not supervisor.is_super_admin:
        raise HTTPException(status_code=409, detail="The selected user is not enabled for the Presenze module")
    if supervisor.role == "operator":
        raise HTTPException(status_code=409, detail="Operators cannot be assigned as Presenze supervisors")

    if assignment is None:
        assignment = PresenzeSupervisorAssignment(
            supervisor_user_id=payload.supervisor_user_id,
            collaborator_id=collaborator_id,
            assigned_by_user_id=current_user.id,
        )
    else:
        assignment.supervisor_user_id = payload.supervisor_user_id
        assignment.assigned_by_user_id = current_user.id
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _serialize_supervisor_assignment(db, assignment)


@router.get("/holidays", response_model=list[PresenzeHolidayResponse])
def list_presenze_holidays(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> list[PresenzeHolidayResponse]:
    stmt = select(PresenzeHoliday)
    if year is not None:
        stmt = stmt.where(
            PresenzeHoliday.holiday_date >= date(year, 1, 1),
            PresenzeHoliday.holiday_date <= date(year, 12, 31),
        )
    items = db.execute(
        stmt.order_by(PresenzeHoliday.holiday_date.asc(), PresenzeHoliday.company_code.asc())
    ).scalars().all()
    return [PresenzeHolidayResponse.model_validate(item) for item in items]


@router.post("/holidays/bootstrap", response_model=PresenzeHolidayBootstrapResponse)
def bootstrap_presenze_holidays(
    year: int = Query(..., ge=2000, le=2100),
    db: Annotated[Session, Depends(get_db)] = ...,
    _: Annotated[ApplicationUser, RequirePresenzeAdmin] = ...,
    __: Annotated[ApplicationUser, RequirePresenzeModule] = ...,
) -> PresenzeHolidayBootstrapResponse:
    items = seed_holidays_for_year(db, year)
    db.commit()
    return PresenzeHolidayBootstrapResponse(
        year=year,
        created=len(items),
        items=[PresenzeHolidayResponse.model_validate(item) for item in items],
    )


@router.post("/holidays", response_model=PresenzeHolidayResponse, status_code=201)
def create_presenze_holiday(
    payload: PresenzeHolidayCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeHolidayResponse:
    item = PresenzeHoliday(**payload.to_model_payload())
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeHolidayResponse.model_validate(item)


@router.patch("/holidays/{holiday_id}", response_model=PresenzeHolidayResponse)
def update_presenze_holiday(
    holiday_id: int,
    payload: PresenzeHolidayUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeHolidayResponse:
    item = db.get(PresenzeHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for field, value in payload.to_model_payload(current_kind=item.holiday_kind).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeHolidayResponse.model_validate(item)


@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_inaz_holiday(
    holiday_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(item)
    db.commit()


@router.get("/schedule/templates", response_model=list[PresenzeScheduleTemplateResponse])
def list_schedule_templates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeScheduleTemplateResponse]:
    ensure_system_schedule_templates(db)
    templates = db.execute(
        select(PresenzeScheduleTemplate).order_by(PresenzeScheduleTemplate.code.asc())
    ).scalars().all()
    return [_serialize_schedule_template(db, item) for item in templates]


@router.post("/schedule/templates", response_model=PresenzeScheduleTemplateResponse, status_code=201)
def create_schedule_template(
    payload: PresenzeScheduleTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleTemplateResponse:
    item = PresenzeScheduleTemplate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)


@router.patch("/schedule/templates/{template_id}", response_model=PresenzeScheduleTemplateResponse)
def update_schedule_template(
    template_id: int,
    payload: PresenzeScheduleTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleTemplateResponse:
    item = db.get(PresenzeScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)


@router.delete("/schedule/templates/{template_id}", status_code=204)
def delete_schedule_template(
    template_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    db.delete(item)
    db.commit()


@router.post("/schedule/templates/{template_id}/rules", response_model=PresenzeScheduleRuleResponse, status_code=201)
def create_schedule_rule(
    template_id: int,
    payload: PresenzeScheduleRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleRuleResponse:
    if db.get(PresenzeScheduleTemplate, template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    item = PresenzeScheduleRule(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeScheduleRuleResponse.model_validate(item)


@router.patch("/schedule/rules/{rule_id}", response_model=PresenzeScheduleRuleResponse)
def update_schedule_rule(
    rule_id: int,
    payload: PresenzeScheduleRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleRuleResponse:
    item = db.get(PresenzeScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeScheduleRuleResponse.model_validate(item)


@router.delete("/schedule/rules/{rule_id}", status_code=204)
def delete_schedule_rule(
    rule_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    db.delete(item)
    db.commit()


@router.get(
    "/collaborators/{collaborator_id}/schedule-assignments",
    response_model=list[PresenzeCollaboratorScheduleAssignmentResponse],
)
def list_collaborator_schedule_assignments(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeCollaboratorScheduleAssignmentResponse]:
    _get_collaborator_or_404(db, collaborator_id)
    rows = db.execute(
        select(PresenzeCollaboratorScheduleAssignment)
        .where(PresenzeCollaboratorScheduleAssignment.collaborator_id == collaborator_id)
        .order_by(
            PresenzeCollaboratorScheduleAssignment.valid_from.desc(),
            PresenzeCollaboratorScheduleAssignment.id.desc(),
        )
    ).scalars().all()
    return [_serialize_schedule_assignment(db, row) for row in rows]


@router.post(
    "/collaborators/{collaborator_id}/schedule-assignments",
    response_model=PresenzeCollaboratorScheduleAssignmentResponse,
    status_code=201,
)
def create_collaborator_schedule_assignment(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorScheduleAssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorScheduleAssignmentResponse:
    _get_collaborator_or_404(db, collaborator_id)
    if db.get(PresenzeScheduleTemplate, payload.template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    duplicate_assignment = db.execute(
        select(PresenzeCollaboratorScheduleAssignment).where(
            PresenzeCollaboratorScheduleAssignment.collaborator_id == collaborator_id,
            PresenzeCollaboratorScheduleAssignment.template_id == payload.template_id,
            PresenzeCollaboratorScheduleAssignment.valid_from == payload.valid_from,
            PresenzeCollaboratorScheduleAssignment.valid_to == payload.valid_to,
        )
    ).scalar_one_or_none()
    if duplicate_assignment is not None:
        raise HTTPException(status_code=409, detail="Questo template e gia assegnato al collaboratore con la stessa validita")
    item = PresenzeCollaboratorScheduleAssignment(collaborator_id=collaborator_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_assignment(db, item)


@router.delete("/schedule-assignments/{assignment_id}", status_code=204)
def delete_schedule_assignment(
    assignment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeCollaboratorScheduleAssignment, assignment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule assignment not found")
    db.delete(item)
    db.commit()


@router.get("/configuration/schedule-bootstrap-preview", response_model=PresenzeScheduleBootstrapPreviewResponse)
def get_schedule_bootstrap_preview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleBootstrapPreviewResponse:
    return _build_schedule_bootstrap_preview(db)


@router.post("/configuration/schedule-bootstrap-apply", response_model=PresenzeScheduleBootstrapApplyResponse)
def apply_schedule_bootstrap(
    payload: PresenzeScheduleBootstrapApplyRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleBootstrapApplyResponse:
    preview = _build_schedule_bootstrap_preview(db)
    existing_templates = {
        item.code.strip().upper(): item for item in db.execute(select(PresenzeScheduleTemplate)).scalars().all()
    }
    created_templates = 0
    created_assignments = 0
    skipped_existing_templates = 0
    skipped_existing_assignments = 0
    template_codes: list[str] = []
    assigned_employee_codes: list[str] = []

    if payload.create_missing_templates:
        for preset in preview.presets:
            if preset.already_exists:
                skipped_existing_templates += 1
                continue
            preset_def = _preset_by_template_code(preset.template_code)
            if preset_def is None:
                continue
            template = PresenzeScheduleTemplate(
                code=preset_def.template_code,
                label=preset_def.template_label,
                company_code="53",
                is_active=True,
                notes=preset_def.template_notes,
            )
            db.add(template)
            db.flush()
            _upsert_template_rules(db, template, preset_def.rules)
            existing_templates[template.code.strip().upper()] = template
            created_templates += 1
            template_codes.append(template.code)

    if payload.assign_unassigned_collaborators:
        for suggestion in preview.collaborator_suggestions:
            if suggestion.suggested_template_code is None:
                continue
            if suggestion.suggestion_confidence != "high":
                skipped_existing_assignments += 1
                continue
            if suggestion.already_assigned:
                skipped_existing_assignments += 1
                continue
            template = existing_templates.get(suggestion.suggested_template_code.strip().upper())
            if template is None:
                skipped_existing_assignments += 1
                continue
            db.add(
                PresenzeCollaboratorScheduleAssignment(
                    collaborator_id=suggestion.collaborator_id,
                    template_id=template.id,
                    notes=f"Bootstrap automatico da schedule code INAZ: {', '.join(suggestion.schedule_codes)}",
                )
            )
            created_assignments += 1
            assigned_employee_codes.append(suggestion.employee_code)

    db.commit()
    return PresenzeScheduleBootstrapApplyResponse(
        created_templates=created_templates,
        created_assignments=created_assignments,
        skipped_existing_templates=skipped_existing_templates,
        skipped_existing_assignments=skipped_existing_assignments,
        template_codes=template_codes,
        assigned_employee_codes=assigned_employee_codes,
    )


@router.post("/credentials", response_model=PresenzeCredentialResponse, status_code=201)
def create_presenze_credential(
    payload: PresenzeCredentialCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    return create_credential(db, current_user.id, payload)


@router.get("/credentials", response_model=list[PresenzeCredentialResponse])
def list_presenze_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[PresenzeCredentialResponse]:
    return list_credentials(db, current_user)


@router.get("/credentials/{credential_id}", response_model=PresenzeCredentialResponse)
def get_presenze_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    credential = get_credential(db, credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    return PresenzeCredentialResponse.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=PresenzeCredentialResponse)
def update_presenze_credential(
    credential_id: int,
    payload: PresenzeCredentialUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    credential = update_credential(db, credential_id, current_user, payload)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    return credential


@router.delete("/credentials/{credential_id}", status_code=204)
def delete_inaz_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not delete_credential(db, credential_id, current_user):
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")


@router.post("/credentials/{credential_id}/test", response_model=PresenzeCredentialTestResult)
async def test_presenze_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialTestResult:
    result = await test_credential(db, current_user, credential_id)
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)
    return result


@router.get("/collaborators", response_model=PresenzeCollaboratorListResponse)
def list_collaborators(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    q: str | None = Query(default=None),
    mapped_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> PresenzeCollaboratorListResponse:
    stmt = select(PresenzeCollaborator)
    count_stmt = select(func.count(PresenzeCollaborator.id))
    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(PresenzeSupervisorAssignment.collaborator_id).where(
            PresenzeSupervisorAssignment.supervisor_user_id == current_user.id
        )
        visibility_filter = or_(
            PresenzeCollaborator.owner_user_id == current_user.id,
            PresenzeCollaborator.id.in_(visible_collaborator_ids),
            PresenzeCollaborator.owner_user_id.in_(hierarchy_scope),
            PresenzeCollaborator.application_user_id.in_(hierarchy_scope),
        )
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
    if q:
        term = f"%{q.strip()}%"
        condition = or_(
            PresenzeCollaborator.name.ilike(term),
            PresenzeCollaborator.employee_code.ilike(term),
            PresenzeCollaborator.company_code.ilike(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if mapped_only is True:
        stmt = stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
        count_stmt = count_stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
    if mapped_only is False:
        stmt = stmt.where(PresenzeCollaborator.application_user_id.is_(None))
        count_stmt = count_stmt.where(PresenzeCollaborator.application_user_id.is_(None))

    rows = db.execute(
        stmt.order_by(PresenzeCollaborator.name.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    template_codes = _load_latest_template_codes_by_collaborator(db, [row.id for row in rows])
    return PresenzeCollaboratorListResponse(
        items=[_serialize_collaborator(db, row, template_code=template_codes.get(row.id)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/collaborators/{collaborator_id}/application-user", response_model=PresenzeCollaboratorResponse)
def map_collaborator_to_application_user(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorApplicationUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    if payload.application_user_id is not None and db.get(ApplicationUser, payload.application_user_id) is None:
        raise HTTPException(status_code=404, detail="Application user not found")
    collaborator.application_user_id = payload.application_user_id
    db.add(collaborator)
    db.query(PresenzeDailyRecord).filter(PresenzeDailyRecord.collaborator_id == collaborator.id).update(
        {"application_user_id": payload.application_user_id}
    )
    db.query(PresenzeEventSummary).filter(PresenzeEventSummary.collaborator_id == collaborator.id).update(
        {"application_user_id": payload.application_user_id}
    )
    db.commit()
    db.refresh(collaborator)
    return _serialize_collaborator(db, collaborator)


@router.put("/collaborators/{collaborator_id}/contract-profile", response_model=PresenzeCollaboratorResponse)
def update_collaborator_contract_profile(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorContractProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    collaborator.contract_kind = payload.contract_kind
    collaborator.operai_group = payload.operai_group
    collaborator.standard_daily_minutes = payload.standard_daily_minutes
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return _serialize_collaborator(db, collaborator)


@router.get("/configuration/operai-rules", response_model=list[PresenzeOperaiRuleConfigResponse])
def list_operai_rule_configs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeOperaiRuleConfigResponse]:
    ensure_operai_rule_configs(db)
    db.commit()
    items = db.execute(select(PresenzeOperaiRuleConfig).order_by(PresenzeOperaiRuleConfig.code.asc())).scalars().all()
    return [PresenzeOperaiRuleConfigResponse.model_validate(item) for item in items]


@router.patch("/configuration/operai-rules/{rule_id}", response_model=PresenzeOperaiRuleConfigResponse)
def update_operai_rule_config(
    rule_id: int,
    payload: PresenzeOperaiRuleConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeOperaiRuleConfigResponse:
    ensure_operai_rule_configs(db)
    db.commit()
    item = db.get(PresenzeOperaiRuleConfig, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Operai rule config not found")
    data = payload.model_dump(exclude_unset=True)
    if "operai_group" in data:
        data["operai_group"] = normalize_operai_group(data["operai_group"])
    for key, value in data.items():
        setattr(item, key, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeOperaiRuleConfigResponse.model_validate(item)


@router.get("/giornaliere", response_model=PresenzeDailyRecordListResponse)
def list_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    include_punches: bool = Query(default=False),
    include_raw_payload: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> PresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord)
    count_stmt = select(func.count(PresenzeDailyRecord.id))

    stmt, count_stmt = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=count_stmt,
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )

    rows = db.execute(
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None
    if include_punches and rows:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([row.id for row in rows]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        punches_by_record_id = {}
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    classification_by_record_id = _build_classification_map(db, rows, punches_by_record_id=punches_by_record_id)
    monthly_night_bonus_by_record_id = _build_monthly_night_bonus_map(db, rows, classifications=classification_by_record_id)
    operai_rule_configs = load_operai_rule_configs(db)
    return PresenzeDailyRecordListResponse(
        items=[
            _serialize_daily_record(
                db,
                row,
                punches=punches_by_record_id.get(row.id) if punches_by_record_id is not None else [],
                include_raw_payload=include_raw_payload,
                classification=classification_by_record_id.get(row.id),
                monthly_night_bonus=monthly_night_bonus_by_record_id.get(row.id),
                operai_rule_configs=operai_rule_configs,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/anomalie", response_model=PresenzeAnomalyListResponse)
def list_anomalie_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    only_anomalies: bool = Query(default=True),
    only_requests: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=5000),
) -> PresenzeAnomalyListResponse:
    stmt = select(PresenzeDailyRecord)
    stmt, _ = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=select(func.count(PresenzeDailyRecord.id)),
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    rows = db.execute(stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
    filtered_rows = _filter_anomaly_rows(rows, only_anomalies=only_anomalies, only_requests=only_requests)
    total = len(filtered_rows)
    page_rows = filtered_rows[(page - 1) * page_size : page * page_size]
    collaborator_ids = list({row.collaborator_id for row in page_rows})
    collaborator_map = _build_collaborator_snapshot_map(db, collaborator_ids)
    return PresenzeAnomalyListResponse(
        items=[_serialize_anomaly_list_item(row, collaborator_map=collaborator_map) for row in page_rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/anomalie/month-summary", response_model=PresenzeAnomalyMonthSummaryResponse)
def get_anomalie_month_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    months: int = Query(default=12, ge=1, le=24),
    anchor_month: str | None = Query(default=None),
) -> PresenzeAnomalyMonthSummaryResponse:
    month_values = _resolve_recent_month_values(months=months, anchor_month=anchor_month)
    if not month_values:
        return PresenzeAnomalyMonthSummaryResponse(items=[])
    first_month = month_values[-1]
    last_month = month_values[0]
    date_from = date.fromisoformat(f"{first_month}-01")
    date_to = _month_end(date.fromisoformat(f"{last_month}-01"))
    stmt = select(PresenzeDailyRecord)
    stmt, _ = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=select(func.count(PresenzeDailyRecord.id)),
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=None,
    )
    rows = db.execute(stmt).scalars().all()
    counts = {month: 0 for month in month_values}
    for row in rows:
        if not _daily_record_has_anomaly(row):
            continue
        month_key = row.work_date.strftime("%Y-%m")
        if month_key in counts:
            counts[month_key] += 1
    return PresenzeAnomalyMonthSummaryResponse(
        items=[
            PresenzeAnomalyMonthSummaryItemResponse(month=month, count=counts[month])
            for month in month_values
            if counts[month] > 0
        ]
    )


@router.get("/giornaliere/matrix", response_model=PresenzeDailyRecordListResponse)
def list_giornaliere_matrix(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> PresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord)
    count_stmt = select(func.count(PresenzeDailyRecord.id))

    stmt, count_stmt = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=count_stmt,
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )

    rows = db.execute(
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    if rows:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([row.id for row in rows]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    operai_rule_configs = load_operai_rule_configs(db)
    classification_by_record_id = _build_classification_map(db, rows, punches_by_record_id=punches_by_record_id)
    operational_quality_by_record_id = _build_operational_quality_map(
        db,
        rows,
        punches_by_record_id=punches_by_record_id,
        classifications=classification_by_record_id,
        operai_rule_configs=operai_rule_configs,
    )
    return PresenzeDailyRecordListResponse(
        items=[
            _serialize_daily_record_matrix(
                record,
                classification=classification_by_record_id.get(record.id),
                operational_quality=operational_quality_by_record_id.get(record.id),
                operai_rule_configs=operai_rule_configs,
            ).model_copy(
                update={
                    "monthly_night_shift_count": 0,
                    "ordinary_night_bonus_threshold_met": False,
                    "ordinary_night_bonus_rate": None,
                }
            )
            for record in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def _apply_daily_record_filters(
    db: Session,
    current_user: ApplicationUser,
    *,
    stmt,
    count_stmt,
    collaborator_id: uuid.UUID | None,
    application_user_id: int | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
):

    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(PresenzeSupervisorAssignment.collaborator_id).where(
            PresenzeSupervisorAssignment.supervisor_user_id == current_user.id
        )
        visibility_filter = or_(
            PresenzeDailyRecord.owner_user_id == current_user.id,
            PresenzeDailyRecord.collaborator_id.in_(visible_collaborator_ids),
            PresenzeDailyRecord.owner_user_id.in_(hierarchy_scope),
            PresenzeDailyRecord.application_user_id.in_(hierarchy_scope),
        )
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)

    if collaborator_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if application_user_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.application_user_id == application_user_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.application_user_id == application_user_id)
    if date_from is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date >= date_from)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date <= date_to)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date <= date_to)
    if q:
        term = f"%{q.strip()}%"
        filters = or_(
            PresenzeDailyRecord.evidenze.ilike(term),
            PresenzeDailyRecord.stato.ilike(term),
            PresenzeDailyRecord.request_description.ilike(term),
            PresenzeDailyRecord.request_status.ilike(term),
            PresenzeDailyRecord.request_authorized_by.ilike(term),
            PresenzeDailyRecord.resolved_absence_cause.ilike(term),
        )
        stmt = stmt.where(filters)
        count_stmt = count_stmt.where(filters)

    return stmt, count_stmt


@router.get("/giornaliere/{record_id}", response_model=PresenzeDailyRecordResponse)
def get_giornaliera(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeDailyRecordResponse:
    return _serialize_daily_record(
        db,
        _get_daily_record_or_404(db, record_id, current_user),
        operai_rule_configs=load_operai_rule_configs(db),
    )


@router.patch("/giornaliere/{record_id}", response_model=PresenzeDailyRecordResponse)
def update_giornaliera(
    record_id: uuid.UUID,
    payload: PresenzeDailyRecordManualUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeDailyRecordResponse:
    record = _get_daily_record_or_404(db, record_id, current_user)
    payload_data = payload.model_dump(exclude_unset=True)
    validation_fields = {"validation_status", "validation_note"}
    manual_edit_fields = {
        "km_value",
        "trasferta_minutes",
        "trasferta_montano",
        "reperibilita_unit",
        "reperibilita_quantity",
        "override_straordinario_minutes",
        "override_mpe_minutes",
        "manual_note",
    }
    if any(field in payload_data for field in manual_edit_fields) and not _can_edit_daily_record(current_user, record):
        raise HTTPException(status_code=403, detail="Edit privileges required for this daily record")
    if any(field in payload_data for field in validation_fields) and not _can_validate_daily_record(db, current_user, record):
        raise HTTPException(status_code=403, detail="Validation privileges required for this daily record")
    for field, value in payload_data.items():
        setattr(record, field, value)
    if "validation_status" in payload_data:
        if record.validation_status == "validated":
            record.validated_by_user_id = current_user.id
            record.validated_at = datetime.now(UTC)
        else:
            record.validated_by_user_id = None
            record.validated_at = None
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_daily_record(db, record)


@router.post("/giornaliere/{record_id}/refresh-from-inaz", response_model=PresenzeSyncJobResponse)
def refresh_giornaliera_from_inaz(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    record = _get_daily_record_or_404(db, record_id, current_user)
    collaborator = _get_collaborator_or_404(db, record.collaborator_id, current_user)
    employee_code = (collaborator.employee_code or "").strip()
    if not employee_code:
        raise HTTPException(status_code=409, detail="Il collaboratore non ha una matricola INAZ configurata")

    credential = _resolve_refresh_credential_for_user(db, current_user)
    job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=credential.id,
        year=record.work_date.year,
        month=record.work_date.month,
        collaborator_limit=1,
        employee_codes=[employee_code],
        period_start_override=record.work_date,
        period_end_override=record.work_date,
        params_overrides={
            "target_scope": "single_day_single_employee",
            "target_record_id": str(record.id),
            "target_collaborator_id": str(collaborator.id),
            "target_work_date": record.work_date.isoformat(),
        },
        trigger="manual_record_refresh",
    )
    return PresenzeSyncJobResponse.model_validate(job)


@router.get("/collaborators/{collaborator_id}/calendar", response_model=PresenzeCollaboratorCalendarResponse)
def get_collaborator_calendar(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> PresenzeCollaboratorCalendarResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    rows = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id == collaborator_id,
            PresenzeDailyRecord.work_date >= date_from,
            PresenzeDailyRecord.work_date <= date_to,
        )
        .order_by(PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    classification_by_record_id = _build_classification_map(db, rows)
    monthly_night_bonus_by_record_id = _build_monthly_night_bonus_map(db, rows, classifications=classification_by_record_id)
    return PresenzeCollaboratorCalendarResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        date_from=date_from,
        date_to=date_to,
        items=[
            _serialize_daily_record(
                db,
                row,
                classification=classification_by_record_id.get(row.id),
                monthly_night_bonus=monthly_night_bonus_by_record_id.get(row.id),
            )
            for row in rows
        ],
    )


@router.get("/collaborators/{collaborator_id}/summary", response_model=PresenzeCollaboratorSummaryResponse)
def get_collaborator_summary(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeCollaboratorSummaryResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    items = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.collaborator_id == collaborator_id,
            PresenzeEventSummary.period_start == period_start,
            PresenzeEventSummary.period_end == period_end,
        )
        .order_by(PresenzeEventSummary.description.asc())
    ).scalars().all()
    return PresenzeCollaboratorSummaryResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        period_start=period_start,
        period_end=period_end,
        items=[PresenzeEventSummaryResponse.model_validate(item) for item in items],
    )


@router.get("/recovery/dashboard", response_model=PresenzeRecoveryDashboardResponse)
def get_recovery_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    negative_only: bool = Query(default=False),
    pending_validation_only: bool = Query(default=False),
    pending_adjustments_only: bool = Query(default=False),
    manual_adjustments_only: bool = Query(default=False),
) -> PresenzeRecoveryDashboardResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery dashboard requires HR or admin privileges")
    return _build_recovery_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        q=q,
        negative_only=negative_only,
        pending_validation_only=pending_validation_only,
        pending_adjustments_only=pending_adjustments_only,
        manual_adjustments_only=manual_adjustments_only,
    )


@router.get("/recovery/adjustments", response_model=list[PresenzeRecoveryAdjustmentResponse])
def list_recovery_adjustments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    approval_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
) -> list[PresenzeRecoveryAdjustmentResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery dashboard requires HR or admin privileges")
    stmt = select(PresenzeRecoveryAdjustment)
    if collaborator_id is not None:
        stmt = stmt.where(PresenzeRecoveryAdjustment.collaborator_id == collaborator_id)
    if approval_status is not None:
        stmt = stmt.where(PresenzeRecoveryAdjustment.approval_status == approval_status)
    rows = db.execute(
        stmt.order_by(PresenzeRecoveryAdjustment.adjustment_date.desc(), PresenzeRecoveryAdjustment.created_at.desc())
    ).scalars().all()
    return _serialize_recovery_adjustments(db, rows)


@router.post("/recovery/adjustments", response_model=PresenzeRecoveryAdjustmentResponse, status_code=201)
def create_recovery_adjustment(
    payload: PresenzeRecoveryAdjustmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    _get_collaborator_or_404(db, payload.collaborator_id)
    item = PresenzeRecoveryAdjustment(
        **payload.model_dump(),
        approval_status="pending",
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)


@router.patch("/recovery/adjustments/{adjustment_id}", response_model=PresenzeRecoveryAdjustmentResponse)
def update_recovery_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeRecoveryAdjustmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(item, field, value)
    if changed_fields:
        item.approval_status = "pending"
        item.approval_note = None
        item.reviewed_by_user_id = None
        item.reviewed_at = None
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)


@router.post("/recovery/adjustments/{adjustment_id}/review", response_model=PresenzeRecoveryAdjustmentResponse)
def review_recovery_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeRecoveryAdjustmentReview,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    item.approval_status = payload.approval_status
    item.approval_note = payload.approval_note
    item.reviewed_by_user_id = current_user.id
    item.reviewed_at = datetime.now(UTC)
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)


@router.delete("/recovery/adjustments/{adjustment_id}", status_code=204)
def delete_recovery_adjustment(
    adjustment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    db.delete(item)
    db.commit()


@router.get("/bank-hours/dashboard", response_model=PresenzeBankHoursDashboardResponse)
def get_bank_hours_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    negative_only: bool = Query(default=False),
    pending_adjustments_only: bool = Query(default=False),
    manual_adjustments_only: bool = Query(default=False),
) -> PresenzeBankHoursDashboardResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    return _build_bank_hours_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        q=q,
        negative_only=negative_only,
        pending_adjustments_only=pending_adjustments_only,
        manual_adjustments_only=manual_adjustments_only,
    )


@router.get("/bank-hours/collaborators/{collaborator_id}", response_model=PresenzeBankHoursCollaboratorDetailResponse)
def get_bank_hours_collaborator_detail(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> PresenzeBankHoursCollaboratorDetailResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    return _build_bank_hours_collaborator_detail(
        db,
        collaborator,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/bank-hours/adjustments", response_model=list[PresenzeBankHoursAdjustmentResponse])
def list_bank_hours_adjustments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    approval_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
) -> list[PresenzeBankHoursAdjustmentResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    stmt = select(PresenzeBankHoursAdjustment)
    if collaborator_id is not None:
        stmt = stmt.where(PresenzeBankHoursAdjustment.collaborator_id == collaborator_id)
    if approval_status is not None:
        stmt = stmt.where(PresenzeBankHoursAdjustment.approval_status == approval_status)
    rows = db.execute(
        stmt.order_by(PresenzeBankHoursAdjustment.adjustment_date.desc(), PresenzeBankHoursAdjustment.created_at.desc())
    ).scalars().all()
    return _serialize_bank_hours_adjustments(db, rows)


@router.post("/bank-hours/adjustments", response_model=PresenzeBankHoursAdjustmentResponse, status_code=201)
def create_bank_hours_adjustment(
    payload: PresenzeBankHoursAdjustmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    _get_collaborator_or_404(db, payload.collaborator_id)
    item = PresenzeBankHoursAdjustment(
        **payload.model_dump(),
        approval_status="pending",
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)


@router.patch("/bank-hours/adjustments/{adjustment_id}", response_model=PresenzeBankHoursAdjustmentResponse)
def update_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeBankHoursAdjustmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(item, field, value)
    if changed_fields:
        _validate_bank_hours_adjustment_balance(db, item, current_item_id=item.id)
        item.approval_status = "pending"
        item.approval_note = None
        item.reviewed_by_user_id = None
        item.reviewed_at = None
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)


@router.post("/bank-hours/adjustments/{adjustment_id}/review", response_model=PresenzeBankHoursAdjustmentResponse)
def review_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeBankHoursAdjustmentReview,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    if payload.approval_status == "approved":
        _validate_bank_hours_adjustment_balance(db, item, current_item_id=item.id)
    item.approval_status = payload.approval_status
    item.approval_note = payload.approval_note
    item.reviewed_by_user_id = current_user.id
    item.reviewed_at = datetime.now(UTC)
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)


@router.delete("/bank-hours/adjustments/{adjustment_id}", status_code=204)
def delete_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    db.delete(item)
    db.commit()


@router.post("/import/preview", response_model=PresenzeImportPreviewResponse)
async def preview_import_json(
    file: UploadFile = File(...),
    _: Annotated[ApplicationUser, RequirePresenzeAdmin] = ...,
    __: Annotated[ApplicationUser, RequirePresenzeModule] = ...,
) -> PresenzeImportPreviewResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    return build_preview(parsed)


@router.post("/import/json", response_model=PresenzeImportJsonResponse)
async def import_json(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    file: UploadFile = File(...),
) -> PresenzeImportJsonResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    try:
        return run_import_job(
            db,
            parsed=parsed,
            requested_by_user_id=current_user.id,
            filename=file.filename,
            params_json={"format": "collaboratori-json"},
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/import/jobs", response_model=PresenzeImportJobListResponse)
def list_import_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeImportJobListResponse:
    stmt = select(PresenzeImportJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeImportJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeImportJob.created_at.desc())).scalars().all()
    return PresenzeImportJobListResponse(items=[PresenzeImportJobResponse.model_validate(job) for job in jobs], total=len(jobs))


@router.get("/import/jobs/{job_id}", response_model=PresenzeImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeImportJobResponse:
    job = db.get(PresenzeImportJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Import job not found")
    return PresenzeImportJobResponse.model_validate(job)


def _create_sync_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    credential_id: int,
    year: int,
    month: int,
    collaborator_limit: int | None,
    employee_codes: list[str] | None = None,
    period_start_override: date | None = None,
    period_end_override: date | None = None,
    params_overrides: dict[str, object] | None = None,
    trigger: str = "manual",
) -> PresenzeSyncJob:
    credential = db.get(PresenzeCredential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    if not credential.active:
        raise HTTPException(status_code=409, detail="La credenziale Presenze selezionata non e attiva")

    period_start, period_end = build_period(year, month)
    if period_start_override is not None:
        period_start = period_start_override
    if period_end_override is not None:
        period_end = period_end_override
    normalized_employee_codes = _normalize_employee_codes(employee_codes)
    params_json: dict[str, object] = {
        "auth_mode": "credential",
        "year": year,
        "month": month,
        "trigger": trigger,
        "employee_codes": normalized_employee_codes,
    }
    if params_overrides:
        params_json.update(params_overrides)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=collaborator_limit,
        max_attempts=settings.presenze_sync_max_attempts,
        params_json=params_json,
    )
    db.add(job)
    db.flush()
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    apply_sync_job_retention(db)
    return job


@router.get("/sync/config", response_model=PresenzeAutoSyncConfigResponse)
def get_sync_config(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAutoSyncConfigResponse:
    _ = current_user
    return serialize_auto_sync_config(get_auto_sync_config(db))


@router.put("/sync/config", response_model=PresenzeAutoSyncConfigResponse)
def put_sync_config(
    payload: PresenzeAutoSyncConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAutoSyncConfigResponse:
    config = update_auto_sync_config(db, payload, user_id=current_user.id)
    return serialize_auto_sync_config(config)


@router.get("/bank-hours/guidance-config", response_model=PresenzeBankHoursGuidanceConfigResponse)
def get_bank_hours_guidance_policy(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursGuidanceConfigResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    return serialize_bank_hours_guidance_config_with_user(db, get_bank_hours_guidance_config(db))


@router.put("/bank-hours/guidance-config", response_model=PresenzeBankHoursGuidanceConfigResponse)
def put_bank_hours_guidance_policy(
    payload: PresenzeBankHoursGuidanceConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursGuidanceConfigResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    config = update_bank_hours_guidance_config(db, payload, user_id=current_user.id)
    return serialize_bank_hours_guidance_config_with_user(db, config)


@router.get("/bank-hours/guidance-config/history", response_model=list[PresenzeBankHoursGuidanceConfigRevisionResponse])
def get_bank_hours_guidance_policy_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeBankHoursGuidanceConfigRevisionResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    return [serialize_bank_hours_guidance_revision(db, revision) for revision in list_bank_hours_guidance_config_revisions(db)]


@router.post("/sync/jobs", response_model=PresenzeSyncJobResponse)
def create_sync_job(
    payload: PresenzeSyncJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")
    credential = get_credential(db, payload.credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=credential.id,
        year=payload.year,
        month=payload.month,
        collaborator_limit=payload.collaborator_limit,
        employee_codes=payload.employee_codes,
        trigger="manual",
    )
    return PresenzeSyncJobResponse.model_validate(job)


@router.get("/sync/jobs", response_model=PresenzeSyncJobListResponse)
def list_sync_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    count_stmt = select(func.count(PresenzeSyncJob.id))
    if not _can_view_all_inaz_data(current_user):
        visibility_filter = PresenzeSyncJob.requested_by_user_id == current_user.id
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
    stmt = stmt.order_by(PresenzeSyncJob.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    jobs = db.execute(stmt).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in jobs], total=total)


@router.get("/sync/jobs/{job_id}", response_model=PresenzeSyncJobResponse)
def get_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    return PresenzeSyncJobResponse.model_validate(job)


@router.post("/sync/jobs/{job_id}/retry", response_model=PresenzeSyncJobResponse)
def retry_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "completed"}:
        raise HTTPException(status_code=409, detail="Sync job is not retryable in the current state")
    if job.credential_id is None:
        raise HTTPException(status_code=409, detail="Questo job usa una configurazione legacy. Crea una nuova sync con una credenziale Presenze salvata.")
    checkpoint = dict((job.params_json or {}).get("checkpoint") or {})
    completed_employee_codes = checkpoint.get("completed_employee_codes")
    has_resume_checkpoint = isinstance(completed_employee_codes, list) and len(completed_employee_codes) > 0
    if job.attempt_count >= job.max_attempts and not has_resume_checkpoint:
        raise HTTPException(status_code=409, detail="Sync job reached the configured max attempts")

    job.status = "pending"
    job.error_detail = None
    job.started_at = None
    job.finished_at = None
    job.worker_pid = None
    prepare_sync_job_artifacts(job)
    db.add(job)
    db.commit()
    db.refresh(job)
    return PresenzeSyncJobResponse.model_validate(job)


@router.post("/sync/jobs/{job_id}/retry-selected", response_model=PresenzeSyncJobResponse)
def retry_sync_job_selected(
    job_id: uuid.UUID,
    payload: PresenzeSyncJobRetrySelectedRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    source_job = db.get(PresenzeSyncJob, job_id)
    if source_job is None or (not _can_view_all_inaz_data(current_user) and source_job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if source_job.credential_id is None:
        raise HTTPException(status_code=409, detail="Questo job usa una configurazione legacy. Crea una nuova sync con una credenziale Presenze salvata.")

    requested_codes = _normalize_employee_codes(payload.employee_codes)
    if not requested_codes:
        raise HTTPException(status_code=422, detail="At least one employee code is required")

    summary_payload = _load_sync_job_summary(str(source_job.id))
    error_items = summary_payload.get("error_items")
    failed_codes = {
        str(item.get("employee_code") or "").strip()
        for item in error_items
        if isinstance(item, dict) and str(item.get("employee_code") or "").strip()
    } if isinstance(error_items, list) else set()
    if not failed_codes:
        raise HTTPException(status_code=409, detail="No failed collaborators available in the job summary")

    invalid_codes = [code for code in requested_codes if code not in failed_codes]
    if invalid_codes:
        raise HTTPException(
            status_code=409,
            detail=f"Selected employee codes are not retryable for this job: {', '.join(invalid_codes)}",
        )

    retry_job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=source_job.credential_id,
        year=int((source_job.params_json or {}).get("year") or source_job.period_end.year),
        month=int((source_job.params_json or {}).get("month") or source_job.period_end.month),
        collaborator_limit=None,
        employee_codes=requested_codes,
        period_start_override=source_job.period_start,
        period_end_override=source_job.period_end,
        params_overrides={
            "target_scope": (source_job.params_json or {}).get("target_scope"),
            "target_months": (source_job.params_json or {}).get("target_months"),
        },
        trigger="retry_selected",
    )
    return PresenzeSyncJobResponse.model_validate(retry_job)


@router.get("/sync/jobs/{job_id}/artifacts/{artifact_name}")
def download_sync_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Sync job artifact not found")
    media_type = {
        "json": "application/json",
        "summary": "application/json",
        "progress": "application/json",
        "events": "application/x-ndjson",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    return FileResponse(artifact_path, media_type=media_type, filename=artifact_path.name)


@router.post("/sync/jobs/{job_id}/cancel", response_model=PresenzeSyncJobResponse)
def cancel_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Sync job cannot be cancelled in the current state")
    if job.status == "running" and job.worker_pid is not None:
        try:
            stop_sync_worker(job)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    job.status = "cancelled"
    job.error_detail = "Sync job cancelled by user"
    job.finished_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return PresenzeSyncJobResponse.model_validate(job)


@router.delete("/sync/jobs/{job_id}", status_code=204)
def delete_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal sync jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/export/giornaliere.xlsm")
def export_giornaliere_xlsm(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    collaborator_id: list[uuid.UUID] | None = Query(default=None),
    employee_kind: str | None = Query(default=None),
    template_path: str | None = Query(default=None),
) -> FileResponse:
    with tempfile.NamedTemporaryFile(prefix="inaz_", suffix=".xlsm", delete=False) as tmp:
        output_path = Path(tmp.name)
    try:
        generate_xlsm_export(
            db,
            period_start=period_start,
            collaborator_ids=collaborator_id,
            employee_kind=employee_kind,
            template_path=template_path,
            output_path=output_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(output_path, media_type="application/vnd.ms-excel.sheet.macroEnabled.12", filename=output_path.name)


def resolve_export_template_path(template_path: str | None) -> Path:
    if template_path is not None:
        try:
            return _resolve_export_template_path(template_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if DEFAULT_TEMPLATE_PATH.exists():
        return DEFAULT_TEMPLATE_PATH
    raise HTTPException(status_code=404, detail=f"Template XLSM not found: {DEFAULT_TEMPLATE_PATH}")


def _is_xlsm_export_job(job: PresenzeSyncJob) -> bool:
    return (job.params_json or {}).get("mode") == "export_xlsm"


def _is_straordinari_export_job(job: PresenzeSyncJob) -> bool:
    return (job.params_json or {}).get("mode") == "export_straordinari_xlsx"


def _create_xlsm_export_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    period_start: date,
    collaborator_ids: list[uuid.UUID] | None,
    employee_kind: str | None,
    template_path: str | None,
) -> PresenzeSyncJob:
    period_end = build_period_end(period_start)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=None,
        period_start=period_start,
        period_end=date.fromordinal(period_end.toordinal() - 1),
        collaborator_limit=len(collaborator_ids) if collaborator_ids else None,
        max_attempts=1,
        params_json={
            "mode": "export_xlsm",
            "period_start": period_start.isoformat(),
            "collaborator_ids": [str(item) for item in collaborator_ids] if collaborator_ids else [],
            "employee_kind": employee_kind,
            "template_path": template_path,
            "progress": {
                "state": "pending",
                "last_event": "queued",
                "last_event_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "giornaliere_export.xlsm")

    try:
        job.worker_pid = launch_xlsm_export_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start Presenze XLSM export worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _resolve_straordinari_collaborator(
    db: Session,
    *,
    current_user: ApplicationUser,
    collaborator_id: uuid.UUID | None,
) -> PresenzeCollaborator:
    if collaborator_id is not None:
        collaborator = db.get(PresenzeCollaborator, collaborator_id)
        if collaborator is None or not _can_access_collaborator(db, current_user, collaborator):
            raise HTTPException(status_code=404, detail="Collaboratore non trovato")
        return collaborator

    candidates = db.execute(
        select(PresenzeCollaborator).where(PresenzeCollaborator.application_user_id == current_user.id).order_by(PresenzeCollaborator.name.asc())
    ).scalars().all()
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise HTTPException(status_code=409, detail="Nessun collaboratore GAIA associato all'utente corrente")
    raise HTTPException(status_code=409, detail="Seleziona il collaboratore per l'export straordinari")


def _create_straordinari_export_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    collaborator: PresenzeCollaborator,
    period_start: date,
    template_path: str | None,
    items: list[dict[str, object]],
) -> PresenzeSyncJob:
    period_end = build_straordinari_period_end(period_start)
    job = PresenzeSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=None,
        period_start=period_start,
        period_end=date.fromordinal(period_end.toordinal() - 1),
        collaborator_limit=1,
        max_attempts=1,
        params_json={
            "mode": "export_straordinari_xlsx",
            "period_start": period_start.isoformat(),
            "collaborator_id": str(collaborator.id),
            "collaborator_name": collaborator.name,
            "template_path": template_path,
            "items": items,
            "output_filename": build_straordinari_filename(period_start),
            "progress": {
                "state": "pending",
                "last_event": "queued",
                "last_event_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "straordinari.xlsx")

    try:
        job.worker_pid = launch_straordinari_export_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start Presenze straordinari export worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/export/jobs/xlsm", response_model=PresenzeSyncJobResponse)
def create_xlsm_export_job(
    payload: PresenzeXlsmExportJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    job = _create_xlsm_export_job_record(
        db,
        requested_by_user_id=current_user.id,
        period_start=payload.period_start,
        collaborator_ids=payload.collaborator_ids,
        employee_kind=payload.employee_kind,
        template_path=payload.template_path,
    )
    return PresenzeSyncJobResponse.model_validate(job)


@router.get("/export/jobs/xlsm", response_model=PresenzeSyncJobListResponse)
def list_xlsm_export_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeSyncJob.created_at.desc())).scalars().all()
    filtered_jobs = [job for job in jobs if _is_xlsm_export_job(job)]
    total = len(filtered_jobs)
    if limit is not None:
        filtered_jobs = filtered_jobs[:limit]
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in filtered_jobs], total=total)


@router.get("/export/jobs/xlsm/{job_id}", response_model=PresenzeSyncJobResponse)
def get_xlsm_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    return PresenzeSyncJobResponse.model_validate(job)


@router.delete("/export/jobs/xlsm/{job_id}", status_code=204)
def delete_xlsm_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal XLSM export jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/export/jobs/xlsm/{job_id}/artifacts/{artifact_name}")
def download_xlsm_export_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_xlsm_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="XLSM export job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="XLSM export job artifact not found")
    media_type = {
        "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
        "summary": "application/json",
        "progress": "application/json",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    return FileResponse(artifact_path, media_type=media_type, filename=artifact_path.name)


@router.get("/export/straordinari/preview", response_model=PresenzeStraordinariPreviewResponse)
def preview_straordinari_export(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
) -> PresenzeStraordinariPreviewResponse:
    collaborator = _resolve_straordinari_collaborator(db, current_user=current_user, collaborator_id=collaborator_id)
    period_start = previous_month_period_start()
    period_end = date.fromordinal(build_straordinari_period_end(period_start).toordinal() - 1)
    _, items = list_straordinari_preview_items(db, collaborator_id=collaborator.id, period_start=period_start)
    return PresenzeStraordinariPreviewResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        period_start=period_start,
        period_end=period_end,
        items=[
            PresenzeStraordinariPreviewItemResponse(
                record_id=item.record_id,
                work_date=item.work_date,
                motivation=item.motivation,
                start_time=item.start_time,
                end_time=item.end_time,
                duration_minutes=item.duration_minutes,
                duration_label=format_duration_label(item.duration_minutes),
            )
            for item in items
        ],
    )


@router.post("/export/jobs/straordinari", response_model=PresenzeSyncJobResponse)
def create_straordinari_export_job(
    payload: PresenzeStraordinariExportJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    collaborator = _resolve_straordinari_collaborator(db, current_user=current_user, collaborator_id=payload.collaborator_id)
    if payload.template_path and not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Solo admin e super admin possono indicare un template straordinari personalizzato")
    period_start = previous_month_period_start()
    requested_motivations = {item.record_id: item.motivation for item in payload.items}
    try:
        _, export_items = build_straordinari_export_items(
            db,
            collaborator_id=collaborator.id,
            period_start=period_start,
            requested_motivations=requested_motivations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    job = _create_straordinari_export_job_record(
        db,
        requested_by_user_id=current_user.id,
        collaborator=collaborator,
        period_start=period_start,
        template_path=payload.template_path,
        items=[
            {
                "work_date": item.work_date.isoformat(),
                "motivation": item.motivation,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration_minutes": item.duration_minutes,
            }
            for item in export_items
        ],
    )
    return PresenzeSyncJobResponse.model_validate(job)


@router.get("/export/jobs/straordinari", response_model=PresenzeSyncJobListResponse)
def list_straordinari_export_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PresenzeSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(PresenzeSyncJob)
    if not _can_view_all_inaz_data(current_user):
        stmt = stmt.where(PresenzeSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(PresenzeSyncJob.created_at.desc())).scalars().all()
    filtered_jobs = [job for job in jobs if _is_straordinari_export_job(job)]
    total = len(filtered_jobs)
    if limit is not None:
        filtered_jobs = filtered_jobs[:limit]
    return PresenzeSyncJobListResponse(items=[PresenzeSyncJobResponse.model_validate(job) for job in filtered_jobs], total=total)


@router.get("/export/jobs/straordinari/{job_id}", response_model=PresenzeSyncJobResponse)
def get_straordinari_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    return PresenzeSyncJobResponse.model_validate(job)


@router.delete("/export/jobs/straordinari/{job_id}", status_code=204)
def delete_straordinari_export_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> Response:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal straordinari export jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/export/jobs/straordinari/{job_id}/artifacts/{artifact_name}")
def download_straordinari_export_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    job = db.get(PresenzeSyncJob, job_id)
    if job is None or not _is_straordinari_export_job(job) or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Straordinari export job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Straordinari export job artifact not found")
    media_type = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "summary": "application/json",
        "progress": "application/json",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    filename = (job.params_json or {}).get("output_filename") if artifact_name == "xlsx" else artifact_path.name
    return FileResponse(artifact_path, media_type=media_type, filename=str(filename))


@router.get("/dashboard/summary", response_model=PresenzeDashboardSummaryResponse)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeDashboardSummaryResponse:
    collaborator_stmt = select(PresenzeCollaborator)
    collaborator_count_stmt = select(func.count(PresenzeCollaborator.id))
    record_stmt = select(PresenzeDailyRecord).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )
    record_count_stmt = select(func.count(PresenzeDailyRecord.id)).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )

    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(PresenzeSupervisorAssignment.collaborator_id).where(
            PresenzeSupervisorAssignment.supervisor_user_id == current_user.id
        )
        collaborator_visibility_filter = or_(
            PresenzeCollaborator.owner_user_id == current_user.id,
            PresenzeCollaborator.id.in_(visible_collaborator_ids),
            PresenzeCollaborator.owner_user_id.in_(hierarchy_scope),
            PresenzeCollaborator.application_user_id.in_(hierarchy_scope),
        )
        record_visibility_filter = or_(
            PresenzeDailyRecord.owner_user_id == current_user.id,
            PresenzeDailyRecord.collaborator_id.in_(visible_collaborator_ids),
            PresenzeDailyRecord.owner_user_id.in_(hierarchy_scope),
            PresenzeDailyRecord.application_user_id.in_(hierarchy_scope),
        )
        collaborator_stmt = collaborator_stmt.where(collaborator_visibility_filter)
        collaborator_count_stmt = collaborator_count_stmt.where(collaborator_visibility_filter)
        record_stmt = record_stmt.where(record_visibility_filter)
        record_count_stmt = record_count_stmt.where(record_visibility_filter)

    collaborators_total = db.execute(collaborator_count_stmt).scalar_one()
    mapped_collaborators_total = db.execute(
        collaborator_count_stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
    ).scalar_one()
    daily_records_total = db.execute(record_count_stmt).scalar_one()

    records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()

    ordinary_minutes_total = 0
    absence_minutes_total = 0
    extra_minutes_total = 0
    straordinario_minutes_total = 0
    maggior_presenza_minutes_total = 0
    km_total = 0
    trasferta_minutes_total = 0
    trasferta_days_total = 0
    trasferta_montano_days_total = 0
    anomaly_total = 0
    special_day_total = 0
    recovery_days_matured_total = 0
    recovery_days_used_total = 0
    worked_days_total = 0
    absence_days_total = 0
    justified_days_total = 0
    active_collaborator_ids: set[uuid.UUID] = set()
    cause_stats: dict[str, int] = {}
    schedule_stats: dict[str, int] = {}
    classification_by_record_id = _build_classification_map(db, records)

    for record in records:
        classification = classification_by_record_id.get(record.id)
        active_collaborator_ids.add(record.collaborator_id)
        ordinary_minutes_total += record.ordinary_minutes or 0
        absence_minutes_total += record.absence_minutes or 0
        effective_straordinario = (
            record.override_straordinario_minutes
            if record.override_straordinario_minutes is not None
            else record.straordinario_minutes or 0
        )
        effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes or 0
        straordinario_minutes_total += effective_straordinario
        maggior_presenza_minutes_total += effective_mpe
        extra_minutes_total += effective_straordinario + effective_mpe
        km_total += record.km_value or 0
        trasferta_minutes_total += record.trasferta_minutes or 0
        if (record.trasferta_minutes or 0) > 0 or record.trasferta_montano:
            trasferta_days_total += 1
        if record.trasferta_montano:
            trasferta_montano_days_total += 1
        if (record.ordinary_minutes or 0) > 0:
            worked_days_total += 1
        if (record.absence_minutes or 0) > 0:
            absence_days_total += 1
        if (record.justified_minutes or 0) > 0:
            justified_days_total += 1

        detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
        anomalies = detail.get("anomalies") or []
        detail_status = str(detail.get("status") or "").lower()
        stato = str(record.stato or "").lower()
        if anomalies or "anom" in detail_status or "anom" in stato:
            anomaly_total += 1
        if classification is not None and classification.special_day:
            special_day_total += 1
        if classification is not None and classification.grants_recovery_day:
            recovery_days_matured_total += 1
        if _record_uses_recovery_day(record):
            recovery_days_used_total += 1

        cause = (record.resolved_absence_cause or "").strip().lower()
        if cause:
            cause_stats[cause] = (cause_stats.get(cause) or 0) + 1

        schedule_code = (record.schedule_code or "").strip()
        if not schedule_code and isinstance(detail.get("programmed_schedule"), str):
            schedule_code = str(detail["programmed_schedule"]).split(" - ")[0].strip()
        if schedule_code:
            schedule_stats[schedule_code] = (schedule_stats.get(schedule_code) or 0) + 1

    top_schedule_stats = [
        {"code": code, "count": count}
        for code, count in sorted(schedule_stats.items(), key=lambda item: (-item[1], item[0]))[:4]
    ]

    return PresenzeDashboardSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        collaborators_total=collaborators_total,
        mapped_collaborators_total=mapped_collaborators_total,
        active_collaborators_total=len(active_collaborator_ids),
        daily_records_total=daily_records_total,
        ordinary_minutes_total=ordinary_minutes_total,
        absence_minutes_total=absence_minutes_total,
        extra_minutes_total=extra_minutes_total,
        straordinario_minutes_total=straordinario_minutes_total,
        maggior_presenza_minutes_total=maggior_presenza_minutes_total,
        km_total=km_total,
        trasferta_minutes_total=trasferta_minutes_total,
        trasferta_days_total=trasferta_days_total,
        trasferta_montano_days_total=trasferta_montano_days_total,
        anomaly_total=anomaly_total,
        special_day_total=special_day_total,
        recovery_days_matured_total=recovery_days_matured_total,
        recovery_days_used_total=recovery_days_used_total,
        recovery_days_balance_total=recovery_days_matured_total - recovery_days_used_total,
        worked_days_total=worked_days_total,
        absence_days_total=absence_days_total,
        justified_days_total=justified_days_total,
        cause_stats=cause_stats,
        schedule_stats=top_schedule_stats,
    )


def _build_schedule_bootstrap_preview(db: Session) -> PresenzeScheduleBootstrapPreviewResponse:
    collaborators = db.execute(
        select(PresenzeCollaborator).order_by(PresenzeCollaborator.employee_code.asc())
    ).scalars().all()
    collaborator_ids = [item.id for item in collaborators]
    assigned_template_codes = _load_latest_template_codes_by_collaborator(db, collaborator_ids)

    record_rows = db.execute(
        select(PresenzeDailyRecord.collaborator_id, PresenzeDailyRecord.schedule_code).where(
            PresenzeDailyRecord.collaborator_id.in_(collaborator_ids),
            PresenzeDailyRecord.schedule_code.is_not(None),
        )
    ).all()

    schedule_counts_by_collaborator: dict[uuid.UUID, dict[str, int]] = {}
    total_schedule_counts: dict[str, int] = {}
    collaborators_by_schedule_code: dict[str, set[uuid.UUID]] = {}
    for collaborator_id, schedule_code in record_rows:
        normalized_code = (schedule_code or "").strip().upper()
        if not normalized_code:
            continue
        schedule_counts_by_collaborator.setdefault(collaborator_id, {})
        schedule_counts_by_collaborator[collaborator_id][normalized_code] = (
            schedule_counts_by_collaborator[collaborator_id].get(normalized_code, 0) + 1
        )
        total_schedule_counts[normalized_code] = total_schedule_counts.get(normalized_code, 0) + 1
        collaborators_by_schedule_code.setdefault(normalized_code, set()).add(collaborator_id)

    existing_templates = db.execute(select(PresenzeScheduleTemplate)).scalars().all()
    existing_template_codes = {item.code.strip().upper() for item in existing_templates}

    presets: list[PresenzeScheduleBootstrapPresetPreview] = []
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        detected_records_count = sum(total_schedule_counts.get(code, 0) for code in preset.source_schedule_codes)
        detected_collaborators: set[uuid.UUID] = set()
        for code in preset.source_schedule_codes:
            detected_collaborators.update(collaborators_by_schedule_code.get(code, set()))
        if detected_records_count <= 0 and not detected_collaborators:
            continue
        presets.append(
            PresenzeScheduleBootstrapPresetPreview(
                preset_key=preset.preset_key,
                template_code=preset.template_code,
                template_label=preset.template_label,
                template_notes=preset.template_notes,
                source_schedule_codes=list(preset.source_schedule_codes),
                detected_records_count=detected_records_count,
                detected_collaborators_count=len(detected_collaborators),
                already_exists=preset.template_code.strip().upper() in existing_template_codes,
                rules=[
                    PresenzeScheduleBootstrapRulePreview(
                        label=rule.label,
                        weekday=rule.weekday,
                        recurrence_kind=rule.recurrence_kind,
                        week_of_month=rule.week_of_month,
                        interval_weeks=rule.interval_weeks,
                        anchor_date=rule.anchor_date,
                        start_time=rule.start_time,
                        end_time=rule.end_time,
                        season_start_month=rule.season_start_month,
                        season_start_day=rule.season_start_day,
                        season_end_month=rule.season_end_month,
                        season_end_day=rule.season_end_day,
                        applies_on_holiday=rule.applies_on_holiday,
                        ordinary_label=rule.ordinary_label,
                        sort_order=rule.sort_order,
                    )
                    for rule in preset.rules
                ],
            )
        )

    collaborator_suggestions: list[PresenzeScheduleBootstrapCollaboratorSuggestion] = []
    for collaborator in collaborators:
        code_counts = schedule_counts_by_collaborator.get(collaborator.id, {})
        sorted_codes = [code for code, _ in sorted(code_counts.items(), key=lambda item: (-item[1], item[0]))]
        preset, confidence, reason = _suggest_bootstrap_preset(sorted_codes, code_counts)
        assigned_template_code = assigned_template_codes.get(collaborator.id)
        suggested_template_code = preset.template_code if preset is not None else None
        configuration_status, configuration_notes = _resolve_schedule_configuration_status(
            collaborator,
            assigned_template_code=assigned_template_code,
            suggested_template_code=suggested_template_code,
        )
        collaborator_suggestions.append(
            PresenzeScheduleBootstrapCollaboratorSuggestion(
                collaborator_id=collaborator.id,
                employee_code=collaborator.employee_code,
                collaborator_name=collaborator.name,
                company_code=collaborator.company_code,
                dominant_schedule_code=sorted_codes[0] if sorted_codes else None,
                schedule_codes=sorted_codes,
                assigned_template_code=assigned_template_code,
                suggested_template_code=suggested_template_code,
                suggested_template_label=preset.template_label if preset is not None else None,
                suggestion_confidence=confidence,
                suggestion_reason=reason,
                already_assigned=assigned_template_code is not None,
                configuration_status=configuration_status,
                configuration_notes=configuration_notes,
            )
        )

    collaborator_suggestions.sort(
        key=lambda item: (
            item.already_assigned,
            item.suggestion_confidence == "none",
            item.suggestion_confidence == "low",
            item.employee_code,
        )
    )

    return PresenzeScheduleBootstrapPreviewResponse(
        detected_collaborators_total=len(collaborators),
        collaborators_with_suggestion_total=sum(1 for item in collaborator_suggestions if item.suggested_template_code is not None),
        collaborators_without_assignment_total=sum(1 for item in collaborator_suggestions if not item.already_assigned),
        profiles=[
            PresenzeScheduleProfilePreview(
                profile_code=profile.profile_code,
                profile_label=profile.profile_label,
                description=profile.description,
                default_template_code=profile.default_template_code,
                template_codes=list(profile.template_codes),
                assignable_template_codes=list(profile.assignable_template_codes),
                inherited_template_codes=list(profile.inherited_template_codes),
                rule_summaries=list(profile.rule_summaries),
                active=any(template_code.strip().upper() in existing_template_codes for template_code in profile.template_codes),
            )
            for profile in SCHEDULE_PROFILE_DEFINITIONS
        ],
        presets=presets,
        collaborator_suggestions=collaborator_suggestions,
    )


def _resolve_schedule_configuration_status(
    collaborator: PresenzeCollaborator,
    *,
    assigned_template_code: str | None,
    suggested_template_code: str | None,
) -> tuple[str, list[str]]:
    if assigned_template_code is None:
        return "unassigned", ["Nessun template orario assegnato."]

    notes: list[str] = []
    normalized_assigned = assigned_template_code.strip().upper()
    normalized_suggested = suggested_template_code.strip().upper() if suggested_template_code else None
    if normalized_suggested is None:
        notes.append("Configurazione precedente: non esiste un preset GAIA suggerito dai codici osservati.")
    elif normalized_assigned != normalized_suggested:
        notes.append(f"Template assegnato {normalized_assigned}, ma i dati suggeriscono {normalized_suggested}.")

    if _template_code_is_operai_profile(normalized_suggested or normalized_assigned):
        if (collaborator.contract_kind or "").strip().lower() != "operaio":
            notes.append("Profilo contratto non impostato come operaio.")
        if normalize_operai_group(collaborator.operai_group) is None:
            notes.append("Gruppo operaio mancante: serve distinguere agrario da catasto/magazzino.")
        if collaborator.standard_daily_minutes != 420:
            notes.append("Standard feriale non allineato alla regola GAIA operai da 420 minuti.")

    if notes:
        return "legacy_review", notes
    return "current", ["Configurazione allineata alla logica GAIA corrente."]


def _template_code_is_operai_profile(template_code: str) -> bool:
    normalized = template_code.strip().upper()
    return normalized in {"OPE0714_1E3SAB", "OPE0736_STD", "OPE0613", "OP_5.3_12.3", "OSAB5.3_12.3"}


def _suggest_bootstrap_preset(
    sorted_codes: list[str],
    code_counts: dict[str, int],
) -> tuple[_BootstrapTemplatePreset | None, str, str | None]:
    code_set = set(sorted_codes)
    if {"OPE0714", "OPE0613", "OPE0714_1E3SAB", "OP_5.3_12.3"} & code_set:
        return (
            _preset_by_key("operai_0714_primo_terzo_sabato"),
            "high",
            "Sono stati rilevati codici operai compatibili con il turno 07:00-14:00 e il sabato 07:00-13:30.",
        )
    if "RIENTRO IMP" in code_set:
        return (
            _preset_by_key("impiegati_rientro"),
            "high",
            "E' presente il codice di rientro impiegati, quindi il profilo con rientro e il piu coerente.",
        )
    if "IMP1" in code_set:
        return (
            _preset_by_key("impiegati_flessibile"),
            "high",
            "Il codice IMP1 e stato rilevato in modo coerente sui dati storici.",
        )
    if "OPE0736" in code_set:
        return (
            _preset_by_key("operai_0620_1356"),
            "high",
            "Il codice OPE0736 e stato rilevato in modo coerente sui dati storici.",
        )
    probable_preset = _suggest_probable_bootstrap_preset(sorted_codes, code_counts)
    if probable_preset is not None:
        return probable_preset
    return None, "none", None


def _suggest_probable_bootstrap_preset(
    sorted_codes: list[str],
    code_counts: dict[str, int],
) -> tuple[_BootstrapTemplatePreset | None, str, str | None] | None:
    if not sorted_codes:
        return None
    dominant_code = sorted_codes[0]
    total_count = sum(code_counts.values())
    dominant_count = code_counts.get(dominant_code, 0)
    dominance_ratio = (dominant_count / total_count) if total_count > 0 else 0

    if dominant_code in {"OPESAB", "OSAB5.3_12.3"}:
        return (
            _preset_by_key("operai_0714_primo_terzo_sabato"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto OPESAB: il sistema propone il profilo operai con sabato, ma richiede conferma.",
        )
    if dominant_code in {"OPE0613", "OP_5.3_12.3"}:
        return (
            _preset_by_key("operai_0714_primo_terzo_sabato"),
            "medium" if dominance_ratio >= 0.6 else "low",
            f"E' stato rilevato soprattutto {dominant_code}: il sistema propone il profilo operai, ma richiede conferma.",
        )
    if dominant_code == "IMP1":
        return (
            _preset_by_key("impiegati_flessibile"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto IMP1: il sistema propone il profilo impiegati standard, ma richiede conferma.",
        )
    if dominant_code == "RIENTRO IMP":
        return (
            _preset_by_key("impiegati_rientro"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto RIENTRO IMP: il sistema propone il profilo con rientro, ma richiede conferma.",
        )
    if dominant_code == "OPE0736":
        return (
            _preset_by_key("operai_0620_1356"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto OPE0736: il sistema propone il profilo operai 06:20-13:56, ma richiede conferma.",
        )
    return None


def _preset_by_key(preset_key: str) -> _BootstrapTemplatePreset | None:
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        if preset.preset_key == preset_key:
            return preset
    return None


def _upsert_template_rules(
    db: Session,
    template: PresenzeScheduleTemplate,
    rule_definitions: tuple[_BootstrapRuleDefinition, ...],
) -> bool:
    existing_rules = db.execute(
        select(PresenzeScheduleRule)
        .where(PresenzeScheduleRule.template_id == template.id)
        .order_by(PresenzeScheduleRule.sort_order.asc(), PresenzeScheduleRule.id.asc())
    ).scalars().all()
    desired_signature = [
        (
            rule.label,
            rule.weekday,
            rule.recurrence_kind,
            rule.week_of_month,
            rule.interval_weeks,
            rule.anchor_date,
            rule.start_time,
            rule.end_time,
            rule.season_start_month,
            rule.season_start_day,
            rule.season_end_month,
            rule.season_end_day,
            rule.applies_on_holiday,
            rule.ordinary_label,
            rule.sort_order,
        )
        for rule in rule_definitions
    ]
    existing_signature = [
        (
            rule.label,
            rule.weekday,
            rule.recurrence_kind,
            rule.week_of_month,
            rule.interval_weeks,
            rule.anchor_date,
            rule.start_time,
            rule.end_time,
            rule.season_start_month,
            rule.season_start_day,
            rule.season_end_month,
            rule.season_end_day,
            rule.applies_on_holiday,
            rule.ordinary_label,
            rule.sort_order,
        )
        for rule in existing_rules
    ]
    if existing_signature == desired_signature:
        return False

    if existing_rules:
        db.execute(delete(PresenzeScheduleRule).where(PresenzeScheduleRule.template_id == template.id))

    for rule in rule_definitions:
        db.add(
            PresenzeScheduleRule(
                template_id=template.id,
                label=rule.label,
                weekday=rule.weekday,
                recurrence_kind=rule.recurrence_kind,
                week_of_month=rule.week_of_month,
                interval_weeks=rule.interval_weeks,
                anchor_date=rule.anchor_date,
                start_time=rule.start_time,
                end_time=rule.end_time,
                season_start_month=rule.season_start_month,
                season_start_day=rule.season_start_day,
                season_end_month=rule.season_end_month,
                season_end_day=rule.season_end_day,
                applies_on_holiday=rule.applies_on_holiday,
                ordinary_label=rule.ordinary_label,
                sort_order=rule.sort_order,
            )
        )
    return True


def ensure_system_schedule_templates(db: Session) -> list[PresenzeScheduleTemplate]:
    existing_templates = db.execute(select(PresenzeScheduleTemplate)).scalars().all()
    existing_by_code = {item.code.strip().upper(): item for item in existing_templates}
    created = False

    for definition in SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS:
        normalized_code = definition.code.strip().upper()
        template = existing_by_code.get(normalized_code)
        if template is None:
            template = PresenzeScheduleTemplate(
                code=definition.code,
                label=definition.label,
                company_code=definition.company_code,
                is_active=True,
                notes=definition.notes,
            )
            db.add(template)
            db.flush()
            existing_by_code[normalized_code] = template
            created = True
        elif not template.notes and definition.notes:
            template.notes = definition.notes
            db.add(template)
            created = True

        if not definition.rules:
            continue

        if _upsert_template_rules(db, template, definition.rules):
            created = True

    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        normalized_code = preset.template_code.strip().upper()
        template = existing_by_code.get(normalized_code)
        if template is None:
            continue
        if not template.notes and preset.template_notes:
            template.notes = preset.template_notes
            db.add(template)
            created = True
        if _upsert_template_rules(db, template, preset.rules):
            created = True

    if created:
        db.commit()
        existing_templates = db.execute(select(PresenzeScheduleTemplate)).scalars().all()
    return existing_templates


def _preset_by_template_code(template_code: str) -> _BootstrapTemplatePreset | None:
    normalized = template_code.strip().upper()
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        if preset.template_code.strip().upper() == normalized:
            return preset
    return None


def _serialize_daily_record(
    db: Session,
    record: PresenzeDailyRecord,
    *,
    punches: list[PresenzeDailyPunch] | None = None,
    include_raw_payload: bool = True,
    classification=None,
    monthly_night_bonus=None,
    operai_rule_configs=None,
) -> PresenzeDailyRecordResponse:
    if punches is None:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id == record.id)
            .order_by(PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    terminal_rows = extract_punch_terminal_labels(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else []
    detail_punch_rows = []
    for row in detail.get("punch_rows") or []:
        time_value = row.get("Ora") or row.get("ora") or row.get("col_1")
        direction = row.get("EU") or row.get("eu") or row.get("col_2")
        terminal_label = row.get("Term") or row.get("term") or row.get("col_4")
        detail_punch_rows.append(
            {
                "time": time_value,
                "direction": direction,
                "terminal_label": terminal_label,
                "raw": row,
            }
        )
    serialized_punches = []
    for punch in punches:
        terminal_label = punch.terminal_label
        if terminal_label is None:
            entry = punch.entry_time.strftime("%H:%M") if punch.entry_time else None
            exit_value = punch.exit_time.strftime("%H:%M") if punch.exit_time else None
            terminal_label = next(
                (
                    item["terminal_label"]
                    for item in terminal_rows
                    if (item["direction"] == "E" and item["time"] == entry)
                    or (item["direction"] == "U" and item["time"] == exit_value)
                ),
                None,
            )
        serialized_punches.append(
            {
                "id": punch.id,
                "daily_record_id": punch.daily_record_id,
                "sequence": punch.sequence,
                "entry_time": punch.entry_time,
                "exit_time": punch.exit_time,
                "terminal_label": terminal_label,
            }
        )
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    if classification is None:
        classification = _build_daily_record_classification(
            db,
            record,
            punches=punches,
        )
    uses_recovery_day = _record_uses_recovery_day(record)
    recovery_day_credit = 1 if classification.grants_recovery_day else 0
    recovery_day_debit = 1 if uses_recovery_day else 0
    if monthly_night_bonus is None:
        monthly_night_bonus = _build_monthly_night_bonus_map(db, [record], classifications={record.id: classification}).get(record.id)
    collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
    catasto_saturday_coverage_counts = _build_catasto_saturday_coverage_counts(
        db,
        [record],
        {collaborator.id: collaborator} if collaborator is not None else {},
    )
    operational_quality = build_daily_operational_quality(
        collaborator,
        record,
        punches,
        classification=classification,
        operai_rule_configs=operai_rule_configs,
        catasto_month_saturday_coverage_count=catasto_saturday_coverage_counts.get(
            (record.collaborator_id, record.work_date.year, record.work_date.month)
        ),
    )
    return PresenzeDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": serialized_punches,
            "effective_straordinario_minutes": effective_straordinario,
            "effective_mpe_minutes": effective_mpe,
            "effective_extra_minutes": (effective_straordinario or 0) + (effective_mpe or 0) or None,
            "operational_status": operational_quality.status,
            "operational_formula_code": operational_quality.formula_code,
            "operational_expected_minutes": operational_quality.expected_minutes,
            "operational_worked_minutes": operational_quality.worked_minutes,
            "operational_missing_minutes": operational_quality.missing_minutes,
            "operational_mpe_minutes": operational_quality.mpe_minutes,
            "operational_notes": list(operational_quality.notes),
            "night_minutes": classification.night_minutes,
            "festive_minutes": classification.festive_minutes,
            "festive_night_minutes": classification.festive_night_minutes,
            "ordinary_night_minutes": classification.ordinary_night_minutes,
            "overtime_day_minutes": classification.overtime_day_minutes,
            "overtime_night_minutes": classification.overtime_night_minutes,
            "overtime_festive_minutes": classification.overtime_festive_minutes,
            "overtime_festive_night_minutes": classification.overtime_festive_night_minutes,
            "shift_festive_day_minutes": classification.shift_festive_day_minutes,
            "shift_night_minutes": classification.shift_night_minutes,
            "shift_festive_night_minutes": classification.shift_festive_night_minutes,
            "monthly_night_shift_count": monthly_night_bonus["monthly_night_shift_count"] if monthly_night_bonus is not None else 0,
            "ordinary_night_bonus_threshold_met": monthly_night_bonus["ordinary_night_bonus_threshold_met"] if monthly_night_bonus is not None else False,
            "ordinary_night_bonus_rate": monthly_night_bonus["ordinary_night_bonus_rate"] if monthly_night_bonus is not None else None,
            "request_type": record.request_type
            or (resolve_request_type(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_description": record.request_description
            or (resolve_request_description(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_status": record.request_status
            or (resolve_request_status(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_authorized_by": record.request_authorized_by
            or (resolve_request_authorized_by(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "resolved_absence_cause": _resolved_absence_cause_for_response(record, classification),
            "detail_title": detail.get("title"),
            "detail_status": detail.get("status"),
            "detail_programmed_schedule": detail.get("programmed_schedule"),
            "detail_effective_schedule": detail.get("effective_schedule"),
            "detail_time_slots": detail.get("time_slots"),
            "detail_schedule_type": detail.get("schedule_type"),
            "detail_theoretical_hours": detail.get("theoretical_hours"),
            "detail_absence_hours": detail.get("absence_hours"),
            "detail_day_summary": detail.get("day_summary") or {},
            "detail_day_totals": detail.get("day_totals") or {},
            "detail_requests": detail.get("requests") or [],
            "detail_anomalies": detail.get("anomalies") or [],
            "detail_punch_rows": detail_punch_rows,
            "detail_text": detail.get("text"),
            "detail_error": detail.get("error"),
            "special_day": classification.special_day,
            "holiday_kind": classification.holiday_kind,
            "grants_recovery_day": classification.grants_recovery_day,
            "recovery_day_credit": recovery_day_credit,
            "uses_recovery_day": uses_recovery_day,
            "recovery_day_debit": recovery_day_debit,
            "recovery_day_balance_delta": recovery_day_credit - recovery_day_debit,
            "raw_payload_json": record.raw_payload_json if include_raw_payload else None,
        }
    )


def _build_collaborator_snapshot_map(
    db: Session,
    collaborator_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PresenzeCollaborator]:
    if not collaborator_ids:
        return {}
    rows = db.execute(
        select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))
    ).scalars().all()
    return {row.id: row for row in rows}


def _daily_record_detail(record: PresenzeDailyRecord) -> dict[str, object]:
    return extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}


def _daily_record_has_anomaly(record: PresenzeDailyRecord) -> bool:
    detail = _daily_record_detail(record)
    detail_anomalies = detail.get("anomalies") or []
    detail_error = detail.get("error")
    return bool(detail_anomalies or detail_error)


def _daily_record_has_requests(record: PresenzeDailyRecord) -> bool:
    detail = _daily_record_detail(record)
    if detail.get("requests"):
        return True
    return any(
        (
            record.request_type,
            record.request_description,
            record.request_status,
            record.request_authorized_by,
        )
    )


def _daily_record_is_special_day(record: PresenzeDailyRecord) -> bool:
    if record.work_date.weekday() >= 5:
        return True
    if isinstance(record.raw_payload_json, dict) and detail_indicates_special_day(record.raw_payload_json):
        return True
    return False


def _classification_has_worked_time(classification) -> bool:
    worked_minutes = (
        (classification.ordinary_minutes or 0)
        + classification.overtime_day_minutes
        + classification.overtime_night_minutes
        + classification.overtime_festive_minutes
        + classification.overtime_festive_night_minutes
        + classification.shift_festive_day_minutes
        + classification.shift_night_minutes
        + classification.shift_festive_night_minutes
    )
    return worked_minutes > 0


def _resolved_absence_cause_for_response(record: PresenzeDailyRecord, classification) -> str | None:
    explicit_cause = record.resolved_absence_cause or (
        resolve_absence_cause(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None
    )
    if explicit_cause:
        return explicit_cause
    if classification.holiday_kind == "ordinary" and classification.special_day and not _classification_has_worked_time(classification):
        return "festivita"
    return None


def _summarize_detail_values(detail_summary: dict[str, str]) -> str:
    if not detail_summary:
        return "—"
    return " · ".join(
        f"{label}: {value}"
        for label, value in list(detail_summary.items())[:3]
    )


def _serialize_anomaly_list_item(
    record: PresenzeDailyRecord,
    *,
    collaborator_map: dict[uuid.UUID, PresenzeCollaborator],
) -> PresenzeAnomalyListItemResponse:
    detail = _daily_record_detail(record)
    collaborator = collaborator_map.get(record.collaborator_id)
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    ) or 0
    effective_mpe = (
        record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    ) or 0
    company_parts = [part for part in (collaborator.company_label if collaborator else None, collaborator.company_code if collaborator else None) if part]
    company = company_parts[0] if company_parts else "—"
    return PresenzeAnomalyListItemResponse(
        id=record.id,
        collaborator_id=record.collaborator_id,
        work_date=record.work_date,
        collaborator_name=collaborator.name if collaborator is not None else str(record.collaborator_id),
        collaborator_code=collaborator.employee_code if collaborator is not None else "—",
        company=company,
        schedule_code=record.schedule_code,
        programmed_schedule=detail.get("programmed_schedule"),
        status=(detail.get("status") or record.stato),
        time_slots=detail.get("time_slots"),
        ordinary_minutes=record.ordinary_minutes,
        absence_minutes=record.absence_minutes,
        effective_extra_minutes=effective_straordinario + effective_mpe,
        km_value=record.km_value,
        special_day=_daily_record_is_special_day(record),
        has_anomalies=_daily_record_has_anomaly(record),
        has_requests=_daily_record_has_requests(record),
        evidenze=record.evidenze,
        summary=_summarize_detail_values(detail.get("day_summary") or {}),
    )


def _filter_anomaly_rows(
    rows: list[PresenzeDailyRecord],
    *,
    only_anomalies: bool,
    only_requests: bool,
) -> list[PresenzeDailyRecord]:
    filtered: list[PresenzeDailyRecord] = []
    for row in rows:
        has_anomalies = _daily_record_has_anomaly(row)
        has_requests = _daily_record_has_requests(row)
        if only_anomalies and not has_anomalies:
            continue
        if only_requests and not has_requests:
            continue
        filtered.append(row)
    return filtered


def _resolve_recent_month_values(*, months: int, anchor_month: str | None) -> list[str]:
    if anchor_month is None:
        cursor = date.today().replace(day=1)
    else:
        try:
            cursor = date.fromisoformat(f"{anchor_month}-01")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="anchor_month must be in YYYY-MM format") from exc
    values: list[str] = []
    for _ in range(months):
        values.append(cursor.strftime("%Y-%m"))
        previous_month_end = cursor - timedelta(days=1)
        cursor = previous_month_end.replace(day=1)
    return values


def _month_end(value: date) -> date:
    next_month = (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _serialize_daily_record_matrix(
    record: PresenzeDailyRecord,
    *,
    classification=None,
    operational_quality=None,
    operai_rule_configs=None,
) -> PresenzeDailyRecordResponse:
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    detail_anomalies = detail.get("anomalies") or []
    if classification is None:
        classification = _build_daily_record_classification(None, record, punches=[])
    if operational_quality is None:
        operational_quality = build_daily_operational_quality(
            None,
            record,
            [],
            classification=classification,
            operai_rule_configs=operai_rule_configs,
        )
    uses_recovery_day = _record_uses_recovery_day(record)
    recovery_day_credit = 1 if classification.grants_recovery_day else 0
    recovery_day_debit = 1 if uses_recovery_day else 0
    return PresenzeDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": [],
            "effective_straordinario_minutes": effective_straordinario,
            "effective_mpe_minutes": effective_mpe,
            "effective_extra_minutes": (effective_straordinario or 0) + (effective_mpe or 0) or None,
            "operational_status": operational_quality.status,
            "operational_formula_code": operational_quality.formula_code,
            "operational_expected_minutes": operational_quality.expected_minutes,
            "operational_worked_minutes": operational_quality.worked_minutes,
            "operational_missing_minutes": operational_quality.missing_minutes,
            "operational_mpe_minutes": operational_quality.mpe_minutes,
            "operational_notes": list(operational_quality.notes),
            "night_minutes": classification.night_minutes,
            "festive_minutes": classification.festive_minutes,
            "festive_night_minutes": classification.festive_night_minutes,
            "ordinary_night_minutes": classification.ordinary_night_minutes,
            "overtime_day_minutes": classification.overtime_day_minutes,
            "overtime_night_minutes": classification.overtime_night_minutes,
            "overtime_festive_minutes": classification.overtime_festive_minutes,
            "overtime_festive_night_minutes": classification.overtime_festive_night_minutes,
            "shift_festive_day_minutes": classification.shift_festive_day_minutes,
            "shift_night_minutes": classification.shift_night_minutes,
            "shift_festive_night_minutes": classification.shift_festive_night_minutes,
            "monthly_night_shift_count": 0,
            "ordinary_night_bonus_threshold_met": False,
            "ordinary_night_bonus_rate": None,
            "request_type": record.request_type
            or (resolve_request_type(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_description": record.request_description
            or (resolve_request_description(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_status": record.request_status
            or (resolve_request_status(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_authorized_by": record.request_authorized_by
            or (resolve_request_authorized_by(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "resolved_absence_cause": _resolved_absence_cause_for_response(record, classification),
            "detail_title": None,
            "detail_status": detail.get("status"),
            "detail_programmed_schedule": detail.get("programmed_schedule"),
            "detail_effective_schedule": None,
            "detail_time_slots": None,
            "detail_schedule_type": None,
            "detail_theoretical_hours": None,
            "detail_absence_hours": None,
            "detail_day_summary": {},
            "detail_day_totals": {},
            "detail_requests": [],
            "detail_anomalies": detail_anomalies,
            "detail_punch_rows": [],
            "detail_text": None,
            "detail_error": detail.get("error"),
            "special_day": classification.special_day,
            "holiday_kind": classification.holiday_kind,
            "grants_recovery_day": classification.grants_recovery_day,
            "recovery_day_credit": recovery_day_credit,
            "uses_recovery_day": uses_recovery_day,
            "recovery_day_debit": recovery_day_debit,
            "recovery_day_balance_delta": recovery_day_credit - recovery_day_debit,
            "raw_payload_json": None,
        }
    )


def _get_collaborator_or_404(
    db: Session,
    collaborator_id: uuid.UUID,
    current_user: ApplicationUser | None = None,
) -> PresenzeCollaborator:
    collaborator = db.get(PresenzeCollaborator, collaborator_id)
    if collaborator is None or (current_user is not None and not _can_access_collaborator(db, current_user, collaborator)):
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return collaborator


def _get_daily_record_or_404(
    db: Session,
    record_id: uuid.UUID,
    current_user: ApplicationUser | None = None,
) -> PresenzeDailyRecord:
    record = db.get(PresenzeDailyRecord, record_id)
    if record is None or (current_user is not None and not _can_access_daily_record(db, current_user, record)):
        raise HTTPException(status_code=404, detail="Daily record not found")
    return record


def _resolve_refresh_credential_for_user(
    db: Session,
    current_user: ApplicationUser,
) -> PresenzeCredential:
    auto_sync_config = get_auto_sync_config(db)
    if auto_sync_config.credential_id is not None:
        auto_sync_credential = get_credential(db, auto_sync_config.credential_id, current_user)
        if auto_sync_credential is not None and auto_sync_credential.active:
            return auto_sync_credential

    fallback_credential = db.execute(
        select(PresenzeCredential)
        .where(
            PresenzeCredential.application_user_id == current_user.id,
            PresenzeCredential.active.is_(True),
        )
        .order_by(PresenzeCredential.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if fallback_credential is None:
        raise HTTPException(
            status_code=409,
            detail="Nessuna credenziale Presenze attiva disponibile per recuperare i dati da INAZ",
        )
    return fallback_credential


def _build_daily_record_classification(
    db: Session | None,
    record: PresenzeDailyRecord,
    *,
    punches: list[PresenzeDailyPunch],
):
    schedule_context = None
    if db is not None:
        schedule_context = build_schedule_context(
            db,
            collaborator_ids=[record.collaborator_id],
            date_from=record.work_date,
            date_to=record.work_date,
        )
    collaborator = PresenzeCollaborator(
        id=record.collaborator_id,
        employee_code="",
        company_code=None,
        name="",
    )
    if db is not None:
        collaborator_row = db.get(PresenzeCollaborator, record.collaborator_id)
        if collaborator_row is not None:
            collaborator = collaborator_row
    return classify_daily_record(collaborator, record, punches, schedule_context)


def _record_uses_recovery_day(record: PresenzeDailyRecord) -> bool:
    raw_payload = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else None
    if raw_payload is not None and detail_indicates_recovery_usage(raw_payload):
        return True
    cause = (record.resolved_absence_cause or "").strip().lower()
    if cause == "riposo":
        return True
    combined = " ".join(
        part
        for part in (
            record.request_description,
            record.evidenze,
            record.stato,
        )
        if part
    ).casefold()
    return any(marker in combined for marker in ("riposo compensativo", "riposo goduto", "giornata di recupero", "recupero"))


def _build_user_label_map(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    users = db.execute(select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))).scalars().all()
    return {user.id: (user.full_name or user.username) for user in users}


def _serialize_recovery_adjustments(
    db: Session,
    items: list[PresenzeRecoveryAdjustment],
) -> list[PresenzeRecoveryAdjustmentResponse]:
    user_ids = {
        value
        for item in items
        for value in (item.created_by_user_id, item.updated_by_user_id, item.reviewed_by_user_id)
        if value is not None
    }
    labels = _build_user_label_map(db, user_ids)
    return [
        PresenzeRecoveryAdjustmentResponse(
            id=item.id,
            collaborator_id=item.collaborator_id,
            adjustment_date=item.adjustment_date,
            delta_days=item.delta_days,
            kind=item.kind,
            approval_status=item.approval_status,
            reason=item.reason,
            note=item.note,
            approval_note=item.approval_note,
            created_by_user_id=item.created_by_user_id,
            updated_by_user_id=item.updated_by_user_id,
            reviewed_by_user_id=item.reviewed_by_user_id,
            created_by_label=labels.get(item.created_by_user_id) if item.created_by_user_id is not None else None,
            updated_by_label=labels.get(item.updated_by_user_id) if item.updated_by_user_id is not None else None,
            reviewed_by_label=labels.get(item.reviewed_by_user_id) if item.reviewed_by_user_id is not None else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
            reviewed_at=item.reviewed_at,
        )
        for item in items
    ]


def _serialize_recovery_adjustment(
    db: Session,
    item: PresenzeRecoveryAdjustment,
) -> PresenzeRecoveryAdjustmentResponse:
    return _serialize_recovery_adjustments(db, [item])[0]


def _serialize_bank_hours_adjustments(
    db: Session,
    items: list[PresenzeBankHoursAdjustment],
) -> list[PresenzeBankHoursAdjustmentResponse]:
    user_ids = {
        value
        for item in items
        for value in (item.created_by_user_id, item.updated_by_user_id, item.reviewed_by_user_id)
        if value is not None
    }
    labels = _build_user_label_map(db, user_ids)
    return [
        PresenzeBankHoursAdjustmentResponse(
            id=item.id,
            collaborator_id=item.collaborator_id,
            adjustment_date=item.adjustment_date,
            delta_minutes=item.delta_minutes,
            kind=item.kind,
            approval_status=item.approval_status,
            reason=item.reason,
            note=item.note,
            approval_note=item.approval_note,
            created_by_user_id=item.created_by_user_id,
            updated_by_user_id=item.updated_by_user_id,
            reviewed_by_user_id=item.reviewed_by_user_id,
            created_by_label=labels.get(item.created_by_user_id) if item.created_by_user_id is not None else None,
            updated_by_label=labels.get(item.updated_by_user_id) if item.updated_by_user_id is not None else None,
            reviewed_by_label=labels.get(item.reviewed_by_user_id) if item.reviewed_by_user_id is not None else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
            reviewed_at=item.reviewed_at,
        )
        for item in items
    ]


def _serialize_bank_hours_adjustment(
    db: Session,
    item: PresenzeBankHoursAdjustment,
) -> PresenzeBankHoursAdjustmentResponse:
    return _serialize_bank_hours_adjustments(db, [item])[0]


def _build_classification_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None,
):
    if not records:
        return {}
    collaborator_ids = sorted({record.collaborator_id for record in records})
    date_from = min(record.work_date for record in records)
    date_to = max(record.work_date for record in records)
    schedule_context = build_schedule_context(db, collaborator_ids=collaborator_ids, date_from=date_from, date_to=date_to)
    collaborators = {
        row.id: row
        for row in db.execute(select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))).scalars().all()
    }
    effective_punches_by_record_id = punches_by_record_id
    if effective_punches_by_record_id is None:
        effective_punches_by_record_id = {}
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            effective_punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    classifications = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        if collaborator is None:
            collaborator = PresenzeCollaborator(id=record.collaborator_id, employee_code="", company_code=None, name="")
        punches = effective_punches_by_record_id.get(record.id, [])
        classifications[record.id] = classify_daily_record(collaborator, record, punches, schedule_context)
    return classifications


def _build_operational_quality_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None,
    classifications: dict[uuid.UUID, object] | None = None,
    operai_rule_configs=None,
):
    if not records:
        return {}
    collaborator_ids = sorted({record.collaborator_id for record in records})
    collaborators = {
        row.id: row
        for row in db.execute(select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))).scalars().all()
    }
    catasto_saturday_coverage_counts = _build_catasto_saturday_coverage_counts(db, records, collaborators)
    effective_punches_by_record_id = punches_by_record_id
    if effective_punches_by_record_id is None:
        effective_punches_by_record_id = {}
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            effective_punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    qualities = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        punches = effective_punches_by_record_id.get(record.id, [])
        qualities[record.id] = build_daily_operational_quality(
            collaborator,
            record,
            punches,
            classification=(classifications or {}).get(record.id),
            operai_rule_configs=operai_rule_configs,
            catasto_month_saturday_coverage_count=catasto_saturday_coverage_counts.get(
                (record.collaborator_id, record.work_date.year, record.work_date.month)
            ),
        )
    return qualities


def _build_catasto_saturday_coverage_counts(
    db: Session,
    records: list[PresenzeDailyRecord],
    collaborators: dict[uuid.UUID, PresenzeCollaborator],
) -> dict[tuple[uuid.UUID, int, int], int]:
    month_keys = sorted(
        {
            (record.collaborator_id, record.work_date.year, record.work_date.month)
            for record in records
            if (
                (collaborator := collaborators.get(record.collaborator_id)) is not None
                and collaborator.contract_kind == PRESENZE_CONTRACT_KIND_OPERAIO
                and collaborator.operai_group == PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO
            )
        }
    )
    if not month_keys:
        return {}

    counts: dict[tuple[uuid.UUID, int, int], int] = {key: 0 for key in month_keys}
    for collaborator_id, year, month in month_keys:
        month_start = date(year, month, 1)
        month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        saturday_records = db.execute(
            select(PresenzeDailyRecord)
            .where(
                PresenzeDailyRecord.collaborator_id == collaborator_id,
                PresenzeDailyRecord.work_date >= month_start,
                PresenzeDailyRecord.work_date < month_end,
            )
            .order_by(PresenzeDailyRecord.work_date.asc())
        ).scalars().all()
        saturday_records = [record for record in saturday_records if record.work_date.weekday() == 5]
        if not saturday_records:
            continue
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in saturday_records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
        for record in saturday_records:
            worked_minutes = complete_punch_minutes(punches_by_record_id.get(record.id, [])) or 0
            cause = record.resolved_absence_cause.strip().lower() if isinstance(record.resolved_absence_cause, str) else None
            justified_minutes = max(record.justified_minutes or 0, record.absence_minutes or 0)
            if worked_minutes > 0 or (cause in {"ferie", "permesso"} and justified_minutes > 0):
                counts[(collaborator_id, year, month)] += 1
    return counts


def _build_monthly_night_bonus_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    classifications: dict[uuid.UUID, object] | None = None,
) -> dict[uuid.UUID, dict[str, int | bool | None]]:
    if not records:
        return {}

    month_keys = sorted({(record.collaborator_id, record.work_date.year, record.work_date.month) for record in records})
    month_ranges = {}
    for collaborator_id, year, month in month_keys:
        month_start = date(year, month, 1)
        month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        month_ranges[(collaborator_id, year, month)] = (month_start, month_end)

    collaborator_ids = sorted({collaborator_id for collaborator_id, _, _ in month_keys})
    global_start = min(start for start, _ in month_ranges.values())
    global_end_inclusive = max(end for _, end in month_ranges.values())
    monthly_records = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id.in_(collaborator_ids),
            PresenzeDailyRecord.work_date >= global_start,
            PresenzeDailyRecord.work_date < global_end_inclusive,
        )
        .order_by(PresenzeDailyRecord.collaborator_id.asc(), PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    monthly_record_ids = [row.id for row in monthly_records]
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    if monthly_record_ids:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_(monthly_record_ids))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)

    classification_map = _build_classification_map(db, monthly_records, punches_by_record_id=punches_by_record_id)
    if classifications is not None:
        classification_map.update(classifications)

    counts_by_month_key: dict[tuple[uuid.UUID, int, int], int] = {}
    for monthly_record in monthly_records:
        month_key = (monthly_record.collaborator_id, monthly_record.work_date.year, monthly_record.work_date.month)
        classification = classification_map.get(monthly_record.id)
        if classification is None:
            continue
        ordinary_night_total = (
            classification.ordinary_night_minutes
            + classification.shift_night_minutes
            + classification.shift_festive_night_minutes
        )
        if ordinary_night_total > 0:
            counts_by_month_key[month_key] = counts_by_month_key.get(month_key, 0) + 1

    result: dict[uuid.UUID, dict[str, int | bool | None]] = {}
    for record in records:
        month_key = (record.collaborator_id, record.work_date.year, record.work_date.month)
        count = counts_by_month_key.get(month_key, 0)
        result[record.id] = {
            "monthly_night_shift_count": count,
            "ordinary_night_bonus_threshold_met": count >= 20,
            "ordinary_night_bonus_rate": 15 if count >= 20 else (10 if count > 0 else None),
        }
    return result


def _build_recovery_dashboard(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
    negative_only: bool = False,
    pending_validation_only: bool = False,
    pending_adjustments_only: bool = False,
    manual_adjustments_only: bool = False,
) -> PresenzeRecoveryDashboardResponse:
    collaborator_stmt = select(PresenzeCollaborator)
    if q:
        term = f"%{q.strip()}%"
        collaborator_stmt = collaborator_stmt.where(
            or_(
                PresenzeCollaborator.name.ilike(term),
                PresenzeCollaborator.employee_code.ilike(term),
                PresenzeCollaborator.company_code.ilike(term),
            )
        )
    collaborators = db.execute(collaborator_stmt.order_by(PresenzeCollaborator.name.asc())).scalars().all()
    collaborator_ids = [item.id for item in collaborators]

    records: list[PresenzeDailyRecord] = []
    adjustments: list[PresenzeRecoveryAdjustment] = []
    if collaborator_ids:
        record_stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.collaborator_id.in_(collaborator_ids))
        adjustment_stmt = select(PresenzeRecoveryAdjustment).where(
            PresenzeRecoveryAdjustment.collaborator_id.in_(collaborator_ids)
        )
        if date_from is not None:
            record_stmt = record_stmt.where(PresenzeDailyRecord.work_date >= date_from)
            adjustment_stmt = adjustment_stmt.where(PresenzeRecoveryAdjustment.adjustment_date >= date_from)
        if date_to is not None:
            record_stmt = record_stmt.where(PresenzeDailyRecord.work_date <= date_to)
            adjustment_stmt = adjustment_stmt.where(PresenzeRecoveryAdjustment.adjustment_date <= date_to)
        records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
        adjustments = db.execute(
            adjustment_stmt.order_by(PresenzeRecoveryAdjustment.adjustment_date.desc())
        ).scalars().all()

    classification_by_record_id = _build_classification_map(db, records)
    adjustment_totals_by_collaborator: dict[uuid.UUID, int] = {}
    last_adjustment_date_by_collaborator: dict[uuid.UUID, date] = {}
    last_adjustment_status_by_collaborator: dict[uuid.UUID, str] = {}
    adjustment_count_by_collaborator: dict[uuid.UUID, int] = {}
    pending_adjustment_count_by_collaborator: dict[uuid.UUID, int] = {}
    for item in adjustments:
        adjustment_count_by_collaborator[item.collaborator_id] = adjustment_count_by_collaborator.get(item.collaborator_id, 0) + 1
        if item.approval_status == "approved":
            adjustment_totals_by_collaborator[item.collaborator_id] = adjustment_totals_by_collaborator.get(item.collaborator_id, 0) + item.delta_days
        if item.approval_status == "pending":
            pending_adjustment_count_by_collaborator[item.collaborator_id] = pending_adjustment_count_by_collaborator.get(item.collaborator_id, 0) + 1
        if item.collaborator_id not in last_adjustment_date_by_collaborator:
            last_adjustment_date_by_collaborator[item.collaborator_id] = item.adjustment_date
            last_adjustment_status_by_collaborator[item.collaborator_id] = item.approval_status

    aggregates: dict[uuid.UUID, dict[str, int | date | None]] = {
        item.id: {
            "matured_days": 0,
            "used_days": 0,
            "pending_validation_count": 0,
            "last_matured_date": None,
            "last_used_date": None,
        }
        for item in collaborators
    }
    for record in records:
        bucket = aggregates.setdefault(
            record.collaborator_id,
            {
                "matured_days": 0,
                "used_days": 0,
                "pending_validation_count": 0,
                "last_matured_date": None,
                "last_used_date": None,
            },
        )
        classification = classification_by_record_id.get(record.id)
        uses_recovery = _record_uses_recovery_day(record)
        if classification is not None and classification.grants_recovery_day:
            bucket["matured_days"] = int(bucket["matured_days"]) + 1
            if bucket["last_matured_date"] is None or record.work_date > bucket["last_matured_date"]:
                bucket["last_matured_date"] = record.work_date
        if uses_recovery:
            bucket["used_days"] = int(bucket["used_days"]) + 1
            if bucket["last_used_date"] is None or record.work_date > bucket["last_used_date"]:
                bucket["last_used_date"] = record.work_date
        if record.validation_status != "validated" and ((classification is not None and classification.grants_recovery_day) or uses_recovery):
            bucket["pending_validation_count"] = int(bucket["pending_validation_count"]) + 1

    items: list[PresenzeRecoveryBalanceItemResponse] = []
    matured_total = 0
    used_total = 0
    manual_total = 0
    pending_total = 0
    pending_adjustments_total = 0
    negative_total = 0
    balance_total = 0
    for collaborator in collaborators:
        bucket = aggregates.get(collaborator.id) or {}
        matured_days = int(bucket.get("matured_days") or 0)
        used_days = int(bucket.get("used_days") or 0)
        manual_delta_days = adjustment_totals_by_collaborator.get(collaborator.id, 0)
        pending_validation_count = int(bucket.get("pending_validation_count") or 0)
        manual_adjustment_count = adjustment_count_by_collaborator.get(collaborator.id, 0)
        pending_adjustment_count = pending_adjustment_count_by_collaborator.get(collaborator.id, 0)
        balance_days = matured_days - used_days + manual_delta_days
        item = PresenzeRecoveryBalanceItemResponse(
            collaborator_id=collaborator.id,
            employee_code=collaborator.employee_code,
            collaborator_name=collaborator.name,
            company_code=collaborator.company_code,
            application_user_id=collaborator.application_user_id,
            matured_days=matured_days,
            used_days=used_days,
            manual_delta_days=manual_delta_days,
            balance_days=balance_days,
            pending_validation_count=pending_validation_count,
            manual_adjustment_count=manual_adjustment_count,
            pending_adjustment_count=pending_adjustment_count,
            last_matured_date=bucket.get("last_matured_date"),
            last_used_date=bucket.get("last_used_date"),
            last_adjustment_date=last_adjustment_date_by_collaborator.get(collaborator.id),
            last_adjustment_status=last_adjustment_status_by_collaborator.get(collaborator.id),
        )
        include_item = matured_days or used_days or manual_delta_days or pending_validation_count or manual_adjustment_count or not q
        if negative_only and balance_days >= 0:
            include_item = False
        if pending_validation_only and pending_validation_count <= 0:
            include_item = False
        if pending_adjustments_only and pending_adjustment_count <= 0:
            include_item = False
        if manual_adjustments_only and manual_adjustment_count <= 0:
            include_item = False
        if include_item:
            items.append(item)
            matured_total += matured_days
            used_total += used_days
            manual_total += manual_delta_days
            pending_total += pending_validation_count
            pending_adjustments_total += pending_adjustment_count
            balance_total += balance_days
            if balance_days < 0:
                negative_total += 1

    items.sort(
        key=lambda item: (
            -item.pending_validation_count,
            -item.pending_adjustment_count,
            item.balance_days,
            item.collaborator_name,
        )
    )
    return PresenzeRecoveryDashboardResponse(
        date_from=date_from,
        date_to=date_to,
        collaborators_total=len(items),
        matured_days_total=matured_total,
        used_days_total=used_total,
        manual_delta_days_total=manual_total,
        balance_days_total=balance_total,
        pending_validation_total=pending_total,
        pending_adjustments_total=pending_adjustments_total,
        negative_balance_total=negative_total,
        items=items,
    )


def _build_bank_hours_dashboard(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
    negative_only: bool = False,
    pending_adjustments_only: bool = False,
    manual_adjustments_only: bool = False,
) -> PresenzeBankHoursDashboardResponse:
    collaborator_stmt = select(PresenzeCollaborator)
    if q:
        term = f"%{q.strip()}%"
        collaborator_stmt = collaborator_stmt.where(
            or_(
                PresenzeCollaborator.name.ilike(term),
                PresenzeCollaborator.employee_code.ilike(term),
                PresenzeCollaborator.company_code.ilike(term),
            )
        )
    collaborators = db.execute(collaborator_stmt.order_by(PresenzeCollaborator.name.asc())).scalars().all()
    collaborator_ids = [item.id for item in collaborators]
    template_codes_by_collaborator = _load_latest_template_codes_by_collaborator(db, collaborator_ids)
    snapshots_by_collaborator, adjustments_by_collaborator = _load_bank_hours_context(
        db,
        collaborator_ids,
        date_to=date_to,
    )

    items: list[PresenzeBankHoursBalanceItemResponse] = []
    imported_balance_total_minutes = 0
    approved_adjustment_total_minutes = 0
    effective_balance_total_minutes = 0
    liquidation_total_minutes = 0
    pending_adjustments_total = 0
    negative_balance_total = 0
    for collaborator in collaborators:
        profile, profile_source = _resolve_collaborator_contract_profile(
            db,
            collaborator,
            template_code=template_codes_by_collaborator.get(collaborator.id),
        )
        snapshots = snapshots_by_collaborator.get(collaborator.id, [])
        scoped_snapshots = [item for item in snapshots if (date_from is None or item.period_start >= date_from) and (date_to is None or item.period_end <= date_to)]
        latest_snapshot = snapshots[-1] if snapshots else None
        approved_adjustments = [
            item
            for item in adjustments_by_collaborator.get(collaborator.id, [])
            if item.approval_status == "approved" and (date_to is None or item.adjustment_date <= date_to)
        ]
        scoped_adjustments = [
            item
            for item in adjustments_by_collaborator.get(collaborator.id, [])
            if (date_from is None or item.adjustment_date >= date_from) and (date_to is None or item.adjustment_date <= date_to)
        ]
        approved_adjustment_minutes = sum(item.delta_minutes for item in approved_adjustments)
        pending_adjustment_count = sum(1 for item in scoped_adjustments if item.approval_status == "pending")
        manual_adjustment_count = len(scoped_adjustments)
        liquidation_minutes_total = sum(-item.delta_minutes for item in approved_adjustments if item.kind == "liquidation")
        imported_prev_balance_minutes = (latest_snapshot.residuo_prec_minutes or 0) if latest_snapshot is not None else 0
        imported_accrued_minutes = sum((item.spettante_minutes or 0) for item in scoped_snapshots)
        imported_used_minutes = sum((item.fruito_minutes or 0) for item in scoped_snapshots)
        imported_balance_minutes = (latest_snapshot.saldo_totale_minutes or 0) if latest_snapshot is not None else 0
        effective_balance_minutes = imported_balance_minutes + approved_adjustment_minutes
        available_debit_minutes = max(effective_balance_minutes, 0)
        item = PresenzeBankHoursBalanceItemResponse(
            collaborator_id=collaborator.id,
            employee_code=collaborator.employee_code,
            collaborator_name=collaborator.name,
            company_code=collaborator.company_code,
            application_user_id=collaborator.application_user_id,
            contract_kind=profile.contract_kind,
            standard_daily_minutes=profile.standard_daily_minutes,
            contract_profile_source=profile_source,
            imported_prev_balance_minutes=imported_prev_balance_minutes,
            imported_accrued_minutes=imported_accrued_minutes,
            imported_used_minutes=imported_used_minutes,
            imported_balance_minutes=imported_balance_minutes,
            approved_adjustment_minutes=approved_adjustment_minutes,
            effective_balance_minutes=effective_balance_minutes,
            available_debit_minutes=available_debit_minutes,
            available_debit_days=_minutes_to_standard_days(available_debit_minutes, profile.standard_daily_minutes),
            liquidation_minutes_total=liquidation_minutes_total,
            manual_adjustment_count=manual_adjustment_count,
            pending_adjustment_count=pending_adjustment_count,
            latest_snapshot_period_start=latest_snapshot.period_start if latest_snapshot is not None else None,
            latest_snapshot_period_end=latest_snapshot.period_end if latest_snapshot is not None else None,
            last_adjustment_date=scoped_adjustments[0].adjustment_date if scoped_adjustments else None,
            last_adjustment_status=scoped_adjustments[0].approval_status if scoped_adjustments else None,
        )
        include_item = bool(scoped_snapshots or scoped_adjustments or not q)
        if negative_only and effective_balance_minutes >= 0:
            include_item = False
        if pending_adjustments_only and pending_adjustment_count <= 0:
            include_item = False
        if manual_adjustments_only and manual_adjustment_count <= 0:
            include_item = False
        if include_item:
            items.append(item)
            imported_balance_total_minutes += imported_balance_minutes
            approved_adjustment_total_minutes += approved_adjustment_minutes
            effective_balance_total_minutes += effective_balance_minutes
            liquidation_total_minutes += liquidation_minutes_total
            pending_adjustments_total += pending_adjustment_count
            if effective_balance_minutes < 0:
                negative_balance_total += 1

    items.sort(
        key=lambda item: (
            -item.pending_adjustment_count,
            item.effective_balance_minutes,
            item.collaborator_name,
        )
    )
    return PresenzeBankHoursDashboardResponse(
        date_from=date_from,
        date_to=date_to,
        collaborators_total=len(items),
        imported_balance_total_minutes=imported_balance_total_minutes,
        approved_adjustment_total_minutes=approved_adjustment_total_minutes,
        effective_balance_total_minutes=effective_balance_total_minutes,
        liquidation_total_minutes=liquidation_total_minutes,
        pending_adjustments_total=pending_adjustments_total,
        negative_balance_total=negative_balance_total,
        items=items,
    )


def _build_bank_hours_collaborator_detail(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    date_from: date | None,
    date_to: date | None,
) -> PresenzeBankHoursCollaboratorDetailResponse:
    profile, profile_source = _resolve_collaborator_contract_profile(
        db,
        collaborator,
        template_code=_load_latest_template_codes_by_collaborator(db, [collaborator.id]).get(collaborator.id),
    )
    snapshots_by_collaborator, adjustments_by_collaborator = _load_bank_hours_context(
        db,
        [collaborator.id],
        date_to=date_to,
    )
    snapshots = [
        item
        for item in snapshots_by_collaborator.get(collaborator.id, [])
        if (date_from is None or item.period_start >= date_from) and (date_to is None or item.period_end <= date_to)
    ]
    adjustments = [
        item
        for item in adjustments_by_collaborator.get(collaborator.id, [])
        if (date_from is None or item.adjustment_date >= date_from) and (date_to is None or item.adjustment_date <= date_to)
    ]
    latest_snapshot = snapshots_by_collaborator.get(collaborator.id, [])[-1] if snapshots_by_collaborator.get(collaborator.id) else None
    approved_adjustment_minutes = sum(
        item.delta_minutes
        for item in adjustments_by_collaborator.get(collaborator.id, [])
        if item.approval_status == "approved" and (date_to is None or item.adjustment_date <= date_to)
    )
    imported_balance_minutes = (latest_snapshot.saldo_totale_minutes or 0) if latest_snapshot is not None else 0
    effective_balance_minutes = imported_balance_minutes + approved_adjustment_minutes
    available_debit_minutes = max(effective_balance_minutes, 0)
    guidance_config = get_bank_hours_guidance_config(db)
    compensation_summary = _build_bank_hours_compensation_summary(
        db,
        collaborator_id=collaborator.id,
        date_from=date_from,
        date_to=date_to,
    )
    return PresenzeBankHoursCollaboratorDetailResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        contract_profile_source=profile_source,
        date_from=date_from,
        date_to=date_to,
        imported_balance_minutes=imported_balance_minutes,
        approved_adjustment_minutes=approved_adjustment_minutes,
        effective_balance_minutes=effective_balance_minutes,
        available_debit_minutes=available_debit_minutes,
        available_debit_days=_minutes_to_standard_days(available_debit_minutes, profile.standard_daily_minutes),
        compensation_summary=compensation_summary,
        liquidation_guidance=_build_bank_hours_liquidation_guidance(
            available_debit_minutes=available_debit_minutes,
            standard_daily_minutes=profile.standard_daily_minutes,
            contract_profile_source=profile_source,
            compensation_summary=compensation_summary,
            guidance_config=guidance_config,
        ),
        snapshots=[_serialize_bank_hours_snapshot(item) for item in reversed(snapshots)],
        adjustments=_serialize_bank_hours_adjustments(db, adjustments),
    )


def _load_bank_hours_context(
    db: Session,
    collaborator_ids: list[uuid.UUID],
    *,
    date_to: date | None,
) -> tuple[dict[uuid.UUID, list[PresenzeEventSummary]], dict[uuid.UUID, list[PresenzeBankHoursAdjustment]]]:
    snapshots_by_collaborator: dict[uuid.UUID, list[PresenzeEventSummary]] = {}
    adjustments_by_collaborator: dict[uuid.UUID, list[PresenzeBankHoursAdjustment]] = {}
    if not collaborator_ids:
        return snapshots_by_collaborator, adjustments_by_collaborator

    summary_stmt = select(PresenzeEventSummary).where(PresenzeEventSummary.collaborator_id.in_(collaborator_ids))
    if date_to is not None:
        summary_stmt = summary_stmt.where(PresenzeEventSummary.period_end <= date_to)
    summaries = db.execute(
        summary_stmt.order_by(PresenzeEventSummary.collaborator_id.asc(), PresenzeEventSummary.period_start.asc())
    ).scalars().all()
    for item in summaries:
        if not _is_bank_hours_summary(item):
            continue
        snapshots_by_collaborator.setdefault(item.collaborator_id, []).append(item)

    adjustment_stmt = select(PresenzeBankHoursAdjustment).where(
        PresenzeBankHoursAdjustment.collaborator_id.in_(collaborator_ids)
    )
    if date_to is not None:
        adjustment_stmt = adjustment_stmt.where(PresenzeBankHoursAdjustment.adjustment_date <= date_to)
    adjustments = db.execute(
        adjustment_stmt.order_by(
            PresenzeBankHoursAdjustment.adjustment_date.desc(),
            PresenzeBankHoursAdjustment.created_at.desc(),
        )
    ).scalars().all()
    for item in adjustments:
        adjustments_by_collaborator.setdefault(item.collaborator_id, []).append(item)
    return snapshots_by_collaborator, adjustments_by_collaborator


def _build_bank_hours_compensation_summary(
    db: Session,
    *,
    collaborator_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> PresenzeBankHoursCompensationSummaryResponse:
    record_stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if date_from is not None:
        record_stmt = record_stmt.where(PresenzeDailyRecord.work_date >= date_from)
    if date_to is not None:
        record_stmt = record_stmt.where(PresenzeDailyRecord.work_date <= date_to)
    records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
    if not records:
        return PresenzeBankHoursCompensationSummaryResponse()

    punches = db.execute(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
        .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
    ).scalars().all()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    for punch in punches:
        punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)

    classifications = _build_classification_map(db, records, punches_by_record_id=punches_by_record_id)
    monthly_night_bonus = _build_monthly_night_bonus_map(db, records, classifications=classifications)

    worked_days_total = 0
    night_shift_days_total = 0
    night_minutes_total = 0
    festive_minutes_total = 0
    festive_night_minutes_total = 0
    ordinary_night_minutes_total = 0
    overtime_day_minutes_total = 0
    overtime_night_minutes_total = 0
    overtime_festive_minutes_total = 0
    overtime_festive_night_minutes_total = 0
    shift_festive_day_minutes_total = 0
    shift_night_minutes_total = 0
    shift_festive_night_minutes_total = 0
    max_monthly_night_shift_count = 0
    ordinary_night_bonus_threshold_met = False
    ordinary_night_bonus_rate: int | None = None

    for record in records:
        classification = classifications.get(record.id)
        if classification is None:
            continue
        imported_extra_minutes = (record.straordinario_minutes or 0) + (record.mpe_minutes or 0)
        punch_candidate_minutes = _complete_punch_minutes(punches_by_record_id.get(record.id, [])) if imported_extra_minutes > 0 else 0
        if (record.ordinary_minutes or 0) > 0 or (record.straordinario_minutes or 0) > 0 or (record.mpe_minutes or 0) > 0:
            worked_days_total += 1
        night_minutes_total += classification.night_minutes
        festive_minutes_total += classification.festive_minutes
        festive_night_minutes_total += classification.festive_night_minutes
        ordinary_night_minutes_total += classification.ordinary_night_minutes
        overtime_day_minutes_total += max(classification.overtime_day_minutes, imported_extra_minutes, punch_candidate_minutes)
        overtime_night_minutes_total += classification.overtime_night_minutes
        overtime_festive_minutes_total += classification.overtime_festive_minutes
        overtime_festive_night_minutes_total += classification.overtime_festive_night_minutes
        shift_festive_day_minutes_total += classification.shift_festive_day_minutes
        shift_night_minutes_total += classification.shift_night_minutes
        shift_festive_night_minutes_total += classification.shift_festive_night_minutes
        if classification.ordinary_night_minutes + classification.shift_night_minutes + classification.shift_festive_night_minutes > 0:
            night_shift_days_total += 1
        night_bonus = monthly_night_bonus.get(record.id)
        if night_bonus is None:
            continue
        monthly_count = int(night_bonus["monthly_night_shift_count"] or 0)
        max_monthly_night_shift_count = max(max_monthly_night_shift_count, monthly_count)
        if bool(night_bonus["ordinary_night_bonus_threshold_met"]):
            ordinary_night_bonus_threshold_met = True
        bonus_rate = night_bonus["ordinary_night_bonus_rate"]
        if bonus_rate is not None:
            ordinary_night_bonus_rate = max(ordinary_night_bonus_rate or 0, int(bonus_rate))

    return PresenzeBankHoursCompensationSummaryResponse(
        records_total=len(records),
        worked_days_total=worked_days_total,
        night_minutes_total=night_minutes_total,
        festive_minutes_total=festive_minutes_total,
        festive_night_minutes_total=festive_night_minutes_total,
        ordinary_night_minutes_total=ordinary_night_minutes_total,
        overtime_day_minutes_total=overtime_day_minutes_total,
        overtime_night_minutes_total=overtime_night_minutes_total,
        overtime_festive_minutes_total=overtime_festive_minutes_total,
        overtime_festive_night_minutes_total=overtime_festive_night_minutes_total,
        shift_festive_day_minutes_total=shift_festive_day_minutes_total,
        shift_night_minutes_total=shift_night_minutes_total,
        shift_festive_night_minutes_total=shift_festive_night_minutes_total,
        night_shift_days_total=night_shift_days_total,
        max_monthly_night_shift_count=max_monthly_night_shift_count,
        ordinary_night_bonus_threshold_met=ordinary_night_bonus_threshold_met,
        ordinary_night_bonus_rate=ordinary_night_bonus_rate,
    )


def _complete_punch_minutes(punches: list[PresenzeDailyPunch]) -> int:
    worked_minutes = 0
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        start_minutes = punch.entry_time.hour * 60 + punch.entry_time.minute
        end_minutes = punch.exit_time.hour * 60 + punch.exit_time.minute
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        worked_minutes += end_minutes - start_minutes
    return worked_minutes


def _build_bank_hours_liquidation_guidance(
    *,
    available_debit_minutes: int,
    standard_daily_minutes: int | None,
    contract_profile_source: str,
    compensation_summary: PresenzeBankHoursCompensationSummaryResponse,
    guidance_config,
) -> PresenzeBankHoursLiquidationGuidanceResponse:
    included_overtime_buckets: list[str] = []
    candidate_minutes_from_overtime = 0
    if guidance_config.include_overtime_day:
        candidate_minutes_from_overtime += compensation_summary.overtime_day_minutes_total
        included_overtime_buckets.append("overtime_day")
    if guidance_config.include_overtime_night:
        candidate_minutes_from_overtime += compensation_summary.overtime_night_minutes_total
        included_overtime_buckets.append("overtime_night")
    if guidance_config.include_overtime_festive:
        candidate_minutes_from_overtime += compensation_summary.overtime_festive_minutes_total
        included_overtime_buckets.append("overtime_festive")
    if guidance_config.include_overtime_festive_night:
        candidate_minutes_from_overtime += compensation_summary.overtime_festive_night_minutes_total
        included_overtime_buckets.append("overtime_festive_night")
    requires_profile_review = contract_profile_source == "missing" or (
        contract_profile_source == "derived" and not guidance_config.allow_derived_profile
    )
    notes: list[str] = []
    reason_code: str = "ok"
    liquidable_minutes = 0
    keep_in_bank_minutes = 0
    review_minutes = 0

    if available_debit_minutes <= 0:
        reason_code = "no_available_balance"
        notes.append("Il collaboratore non ha saldo banca ore disponibile da liquidare nel periodo selezionato.")
    elif candidate_minutes_from_overtime <= 0:
        reason_code = "no_overtime_candidate"
        keep_in_bank_minutes = available_debit_minutes
        notes.append("Nel periodo selezionato non risultano minuti di straordinario candidabili a liquidazione automatica.")
    elif requires_profile_review:
        reason_code = "missing_profile"
        review_minutes = min(available_debit_minutes, candidate_minutes_from_overtime)
        keep_in_bank_minutes = max(available_debit_minutes - review_minutes, 0)
        if contract_profile_source == "derived":
            notes.append("Il profilo contrattuale e derivato dal template e la configurazione corrente richiede revisione HR prima di liquidare.")
        else:
            notes.append("Il profilo contrattuale non e completo: prima di liquidare conviene confermare operaio/impiegato e orario standard.")
    else:
        liquidable_minutes = min(available_debit_minutes, candidate_minutes_from_overtime)
        keep_in_bank_minutes = max(available_debit_minutes - liquidable_minutes, 0)
        notes.append("La proposta usa il minore tra saldo banca ore disponibile e straordinario del periodo classificato dal motore CCNL.")

    if 0 < liquidable_minutes < guidance_config.min_suggested_minutes:
        review_minutes += liquidable_minutes
        liquidable_minutes = 0
        reason_code = "partial_review"
        notes.append(
            f"La proposta resta sotto la soglia minima configurata di {guidance_config.min_suggested_minutes} minuti e viene rimessa a revisione HR."
        )

    if (
        not requires_profile_review
        and available_debit_minutes > 0
        and candidate_minutes_from_overtime > 0
        and candidate_minutes_from_overtime < available_debit_minutes
    ):
        notes.append("Una quota del saldo resta in banca ore perche non trova copertura nello straordinario del periodo selezionato.")

    if requires_profile_review and review_minutes > 0 and available_debit_minutes > review_minutes:
        reason_code = "partial_review"
        notes.append("Una parte del saldo resta in banca ore, mentre la quota candidata richiede validazione HR.")

    if compensation_summary.ordinary_night_bonus_rate is not None:
        notes.append(
            f"Nel periodo e presente notturno con soglia Art. 82 valorizzata al {compensation_summary.ordinary_night_bonus_rate}%."
        )

    return PresenzeBankHoursLiquidationGuidanceResponse(
        allow_derived_profile=guidance_config.allow_derived_profile,
        included_overtime_buckets=included_overtime_buckets,
        min_suggested_minutes=guidance_config.min_suggested_minutes,
        available_minutes=available_debit_minutes,
        candidate_minutes_from_overtime=candidate_minutes_from_overtime,
        suggested_minutes=liquidable_minutes,
        suggested_days=_minutes_to_standard_days(liquidable_minutes, standard_daily_minutes),
        liquidable_minutes=liquidable_minutes,
        keep_in_bank_minutes=keep_in_bank_minutes,
        review_minutes=review_minutes,
        requires_profile_review=requires_profile_review,
        reason_code=reason_code,
        notes=notes,
    )


def _validate_bank_hours_adjustment_balance(
    db: Session,
    item: PresenzeBankHoursAdjustment,
    *,
    current_item_id: uuid.UUID | None = None,
) -> None:
    if item.delta_minutes >= 0:
        return
    available_minutes = _resolve_bank_hours_available_minutes(
        db,
        item.collaborator_id,
        up_to_date=item.adjustment_date,
        exclude_adjustment_id=current_item_id if item.approval_status != "approved" else None,
    )
    if available_minutes + item.delta_minutes < 0:
        raise HTTPException(
            status_code=409,
            detail="La rettifica banca ore supera il saldo disponibile alla data selezionata.",
        )


def _resolve_bank_hours_available_minutes(
    db: Session,
    collaborator_id: uuid.UUID,
    *,
    up_to_date: date,
    exclude_adjustment_id: uuid.UUID | None = None,
) -> int:
    summaries = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.collaborator_id == collaborator_id,
            PresenzeEventSummary.period_start <= up_to_date,
        )
        .order_by(PresenzeEventSummary.period_start.asc(), PresenzeEventSummary.period_end.asc())
    ).scalars().all()
    latest_summary = next((item for item in reversed(summaries) if _is_bank_hours_summary(item)), None)
    imported_balance_minutes = latest_summary.saldo_totale_minutes if latest_summary is not None and latest_summary.saldo_totale_minutes is not None else 0
    adjustment_stmt = select(PresenzeBankHoursAdjustment).where(
        PresenzeBankHoursAdjustment.collaborator_id == collaborator_id,
        PresenzeBankHoursAdjustment.approval_status == "approved",
        PresenzeBankHoursAdjustment.adjustment_date <= up_to_date,
    )
    approved_adjustments = db.execute(
        adjustment_stmt.order_by(PresenzeBankHoursAdjustment.adjustment_date.asc())
    ).scalars().all()
    adjustment_total = 0
    for current_item in approved_adjustments:
        if exclude_adjustment_id is not None and current_item.id == exclude_adjustment_id:
            continue
        adjustment_total += current_item.delta_minutes
    return imported_balance_minutes + adjustment_total


def _is_bank_hours_summary(item: PresenzeEventSummary) -> bool:
    return "banca ore" in (item.description or "").strip().casefold()


def _serialize_bank_hours_snapshot(item: PresenzeEventSummary) -> PresenzeBankHoursSnapshotResponse:
    return PresenzeBankHoursSnapshotResponse(
        collaborator_id=item.collaborator_id,
        period_start=item.period_start,
        period_end=item.period_end,
        description=item.description,
        residuo_prec_minutes=item.residuo_prec_minutes or 0,
        spettante_minutes=item.spettante_minutes or 0,
        fruito_minutes=item.fruito_minutes or 0,
        saldo_minutes=item.saldo_minutes or 0,
        saldo_totale_minutes=item.saldo_totale_minutes or 0,
        source_job_id=item.source_job_id,
    )


def _is_admin_user(current_user: ApplicationUser) -> bool:
    return current_user.role in {"admin", "super_admin"}


def _is_hr_manager(current_user: ApplicationUser) -> bool:
    return current_user.role == "hr_manager"


def _can_view_all_inaz_data(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user) or _is_hr_manager(current_user)


def _can_manage_supervisors(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user)


def _has_supervisor_assignment(db: Session, current_user: ApplicationUser, collaborator_id: uuid.UUID) -> bool:
    assignment = db.execute(
        select(PresenzeSupervisorAssignment.id).where(
            PresenzeSupervisorAssignment.supervisor_user_id == current_user.id,
            PresenzeSupervisorAssignment.collaborator_id == collaborator_id,
        )
    ).scalar_one_or_none()
    return assignment is not None


def _hierarchy_scope_user_ids(db: Session, current_user: ApplicationUser) -> set[int]:
    assignments = db.scalars(select(OrgStructureAssignment)).all()
    children_by_manager: dict[int, list[int]] = {}
    for assignment in assignments:
        if assignment.manager_user_id is None:
            continue
        children_by_manager.setdefault(assignment.manager_user_id, []).append(assignment.application_user_id)
    scope: set[int] = set()
    queue = list(children_by_manager.get(current_user.id, []))
    while queue:
        user_id = queue.pop(0)
        if user_id in scope:
            continue
        scope.add(user_id)
        queue.extend(children_by_manager.get(user_id, []))
    return scope


def _can_access_by_hierarchy(current_user: ApplicationUser, *, owner_user_id: int | None, application_user_id: int | None, hierarchy_scope: set[int]) -> bool:
    if owner_user_id == current_user.id:
        return True
    if owner_user_id is not None and owner_user_id in hierarchy_scope:
        return True
    if application_user_id is not None and application_user_id in hierarchy_scope:
        return True
    return False


def _can_access_collaborator(db: Session, current_user: ApplicationUser, collaborator: PresenzeCollaborator) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=collaborator.owner_user_id,
        application_user_id=collaborator.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, collaborator.id)


def _can_access_daily_record(db: Session, current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=record.owner_user_id,
        application_user_id=record.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, record.collaborator_id)


def _can_validate_daily_record(db: Session, current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=record.owner_user_id,
        application_user_id=record.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, record.collaborator_id)


def _can_edit_daily_record(current_user: ApplicationUser, record: PresenzeDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    return record.owner_user_id == current_user.id


def _serialize_schedule_template(
    db: Session,
    template: PresenzeScheduleTemplate,
) -> PresenzeScheduleTemplateResponse:
    rules = db.execute(
        select(PresenzeScheduleRule)
        .where(PresenzeScheduleRule.template_id == template.id)
        .order_by(PresenzeScheduleRule.sort_order.asc(), PresenzeScheduleRule.id.asc())
    ).scalars().all()
    return PresenzeScheduleTemplateResponse.model_validate({**template.__dict__, "rules": rules})


def _serialize_schedule_assignment(
    db: Session,
    assignment: PresenzeCollaboratorScheduleAssignment,
) -> PresenzeCollaboratorScheduleAssignmentResponse:
    template = db.get(PresenzeScheduleTemplate, assignment.template_id)
    serialized_template = _serialize_schedule_template(db, template) if template is not None else None
    return PresenzeCollaboratorScheduleAssignmentResponse.model_validate(
        {**assignment.__dict__, "template": serialized_template}
    )


def _serialize_collaborator(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    template_code: str | None = None,
) -> PresenzeCollaboratorResponse:
    profile, _ = _resolve_collaborator_contract_profile(db, collaborator, template_code=template_code)
    return PresenzeCollaboratorResponse.model_validate(
        {
            **collaborator.__dict__,
            "contract_kind": profile.contract_kind,
            "standard_daily_minutes": profile.standard_daily_minutes,
        }
    )


def _resolve_collaborator_contract_profile(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    template_code: str | None = None,
) -> tuple[PresenzeContractProfile, str]:
    resolved_template_code = template_code
    if resolved_template_code is None:
        resolved_template_code = _load_latest_template_codes_by_collaborator(db, [collaborator.id]).get(collaborator.id)
    has_explicit_profile = normalize_contract_kind(collaborator.contract_kind) is not None or collaborator.standard_daily_minutes is not None
    profile = resolve_contract_profile(
        collaborator.contract_kind,
        collaborator.standard_daily_minutes,
        template_code=resolved_template_code,
    )
    if has_explicit_profile:
        return profile, "explicit"
    if profile.contract_kind is not None or profile.standard_daily_minutes is not None:
        return profile, "derived"
    return profile, "missing"


def _minutes_to_standard_days(minutes: int, standard_daily_minutes: int | None) -> float | None:
    if standard_daily_minutes is None or standard_daily_minutes <= 0:
        return None
    return round(minutes / standard_daily_minutes, 2)


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


def _serialize_supervisor_assignment(
    db: Session,
    assignment: PresenzeSupervisorAssignment,
) -> PresenzeSupervisorAssignmentResponse:
    collaborator = db.get(PresenzeCollaborator, assignment.collaborator_id)
    supervisor = db.get(ApplicationUser, assignment.supervisor_user_id)
    supervisor_payload = None
    if supervisor is not None:
        supervisor_payload = {
            "id": supervisor.id,
            "username": supervisor.username,
            "full_name": supervisor.full_name,
            "email": supervisor.email,
            "role": supervisor.role,
            "is_active": supervisor.is_active,
        }
    return PresenzeSupervisorAssignmentResponse.model_validate(
        {
            **assignment.__dict__,
            "supervisor": supervisor_payload,
            "collaborator": _serialize_collaborator(db, collaborator) if collaborator is not None else None,
        }
    )
