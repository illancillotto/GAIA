from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyRecord,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.router.helpers.schedule_definitions import (
    _OPERAI_SUMMER_END_DAY,
    _OPERAI_SUMMER_END_MONTH,
    _OPERAI_SUMMER_START_DAY,
    _OPERAI_SUMMER_START_MONTH,
    BOOTSTRAP_TEMPLATE_PRESETS,
    SCHEDULE_PROFILE_DEFINITIONS,
    SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS,
    _BootstrapRuleDefinition,
    _BootstrapTemplatePreset,
    _ScheduleProfileDefinition,
    _SystemScheduleTemplateDefinition,
)
from app.modules.presenze.schemas import (
    PresenzeCollaboratorScheduleAssignmentResponse,
    PresenzeScheduleBootstrapCollaboratorSuggestion,
    PresenzeScheduleBootstrapPresetPreview,
    PresenzeScheduleBootstrapPreviewResponse,
    PresenzeScheduleBootstrapRulePreview,
    PresenzeScheduleProfilePreview,
    PresenzeScheduleTemplateResponse,
)
from app.modules.presenze.services.contract_profile import (
    normalize_operai_group,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

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

# fmt: on

__all__ = [
    "BOOTSTRAP_TEMPLATE_PRESETS",
    "SCHEDULE_PROFILE_DEFINITIONS",
    "SYSTEM_SCHEDULE_TEMPLATE_DEFINITIONS",
    "_OPERAI_SUMMER_END_DAY",
    "_OPERAI_SUMMER_END_MONTH",
    "_OPERAI_SUMMER_START_DAY",
    "_OPERAI_SUMMER_START_MONTH",
    "_BootstrapRuleDefinition",
    "_BootstrapTemplatePreset",
    "_ScheduleProfileDefinition",
    "_SystemScheduleTemplateDefinition",
    "_build_schedule_bootstrap_preview",
    "_load_latest_template_codes_by_collaborator",
    "_preset_by_key",
    "_preset_by_template_code",
    "_resolve_schedule_configuration_status",
    "_serialize_schedule_assignment",
    "_serialize_schedule_template",
    "_suggest_bootstrap_preset",
    "_suggest_probable_bootstrap_preset",
    "_template_code_is_operai_profile",
    "_upsert_template_rules",
    "ensure_system_schedule_templates",
]
