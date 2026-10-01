from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeDailyRecord


def build_presenze_record_items(
    db: Session, *, month: str, records: list[PresenzeDailyRecord]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from app.services import gate_mobile_sync as sync

    period_start, period_end = sync._month_period(month)
    if not records:
        return [], {}

    collaborators = sync._collaborator_map(db, [record.collaborator_id for record in records])
    team_ids_by_collaborator = sync._team_ids_by_collaborator(
        db,
        [record.collaborator_id for record in records],
        period_start=period_start,
        period_end=period_end,
    )
    punches_by_record_id = sync._presenze_punches_by_record_id(db, records)
    classification_by_record_id = sync._build_classification_map(
        db, records, punches_by_record_id=punches_by_record_id
    )
    operai_rule_configs = sync.load_operai_rule_configs(db)
    operational_quality_by_record_id = sync._build_operational_quality_map(
        db,
        records,
        punches_by_record_id=punches_by_record_id,
        classifications=classification_by_record_id,
        operai_rule_configs=operai_rule_configs,
    )

    record_items: list[dict[str, Any]] = []
    analyses_by_record_id: dict[str, Any] = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        serialized = sync._serialize_daily_record_matrix(
            record,
            classification=classification_by_record_id.get(record.id),
            operational_quality=operational_quality_by_record_id.get(record.id),
            operai_rule_configs=operai_rule_configs,
        )
        analysis = sync._gate_record_analysis_from_serialized(record, serialized)
        record_id = str(record.id)
        analyses_by_record_id[record_id] = analysis
        record_items.append(
            {
                **sync.build_presenze_mobile_record_payload(
                    record,
                    collaborator=collaborator,
                    team_ids=team_ids_by_collaborator.get(record.collaborator_id, []),
                    serialized=serialized,
                    severity=analysis.severity,
                    classification=classification_by_record_id[record.id],
                ),
                "has_complete_punches": sync._has_complete_punches(
                    punches_by_record_id.get(record.id, [])
                ),
                "detail_punch_rows": sync._detail_punch_rows(
                    punches_by_record_id.get(record.id, [])
                ),
            }
        )
    return record_items, analyses_by_record_id
