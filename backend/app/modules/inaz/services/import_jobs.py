from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inaz.models import InazCollaborator, InazDailyPunch, InazDailyRecord, InazEventSummary, InazImportJob
from app.modules.inaz.schemas import InazImportJobResponse, InazImportJsonResponse, InazImportPreviewCollaborator, InazImportPreviewResponse
from app.modules.inaz.services.parser import (
    duration_to_minutes,
    parse_clock,
    parse_portal_date,
    resolve_absence_minutes,
    resolve_evidenze,
    resolve_justified_minutes,
    resolve_maggiorazione_minutes,
    resolve_mpe_minutes,
    resolve_ordinary_minutes,
    resolve_schedule_code,
    resolve_stato,
    resolve_straordinario_minutes,
    resolve_teo_minutes,
)


def build_preview(parsed: Any) -> InazImportPreviewResponse:
    return InazImportPreviewResponse(
        total_collaborators=len(parsed.collaborators),
        total_daily_rows=sum(len(item.daily_rows) for item in parsed.collaborators),
        total_summary_rows=sum(len(item.summary_rows) for item in parsed.collaborators),
        collaborators=[
            InazImportPreviewCollaborator(
                employee_code=item.collaborator["employee_code"],
                company_code=item.collaborator.get("company_code"),
                name=item.collaborator.get("name") or item.collaborator["employee_code"],
                application_user_id=None,
                total_daily_rows=len(item.daily_rows),
                total_summary_rows=len(item.summary_rows),
                period_start=item.period_start,
                period_end=item.period_end,
            )
            for item in parsed.collaborators
        ],
        errors=parsed.errors,
    )


def run_import_job(
    db: Session,
    *,
    parsed: Any,
    requested_by_user_id: int,
    filename: str | None,
    params_json: dict[str, Any] | None = None,
) -> InazImportJsonResponse:
    preview = build_preview(parsed)
    job = InazImportJob(
        status="running",
        filename=filename,
        requested_by_user_id=requested_by_user_id,
        date_from=parsed.period_start,
        date_to=parsed.period_end,
        total_records=preview.total_daily_rows + preview.total_summary_rows,
        records_errors=len(preview.errors),
        params_json=params_json or {"format": "collaboratori-json"},
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()

    try:
        imported_count = 0
        skipped_count = 0
        for payload in parsed.collaborators:
            collaborator = upsert_collaborator(db, payload)
            collaborator.last_seen_at = datetime.now(UTC)
            db.add(collaborator)
            db.flush()

            for daily_row in payload.daily_rows:
                work_date = parse_portal_date(daily_row.get("work_date"))
                if work_date is None:
                    job.records_errors += 1
                    continue
                record = db.execute(
                    select(InazDailyRecord).where(
                        InazDailyRecord.collaborator_id == collaborator.id,
                        InazDailyRecord.work_date == work_date,
                    )
                ).scalar_one_or_none()
                if record is None:
                    record = InazDailyRecord(
                        collaborator_id=collaborator.id,
                        application_user_id=collaborator.application_user_id,
                        work_date=work_date,
                        source_job_id=job.id,
                    )
                    db.add(record)
                    db.flush()
                    imported_count += 1
                else:
                    skipped_count += 1

                record.application_user_id = collaborator.application_user_id
                record.schedule_code = resolve_schedule_code(daily_row)
                record.teo_minutes = resolve_teo_minutes(daily_row)
                record.ordinary_minutes = resolve_ordinary_minutes(daily_row)
                record.absence_minutes = resolve_absence_minutes(daily_row)
                record.justified_minutes = resolve_justified_minutes(daily_row)
                record.maggiorazione_minutes = resolve_maggiorazione_minutes(daily_row)
                record.mpe_minutes = resolve_mpe_minutes(daily_row)
                record.straordinario_minutes = resolve_straordinario_minutes(daily_row)
                record.stato = resolve_stato(daily_row)
                record.evidenze = resolve_evidenze(daily_row)
                record.raw_weekday = clean(payload=daily_row.get("raw_weekday"))
                record.raw_payload_json = daily_row
                db.query(InazDailyPunch).filter(InazDailyPunch.daily_record_id == record.id).delete()
                for index, punch in enumerate(daily_row.get("punches", []), start=1):
                    db.add(
                        InazDailyPunch(
                            daily_record_id=record.id,
                            sequence=index,
                            entry_time=parse_clock(punch.get("entry")),
                            exit_time=parse_clock(punch.get("exit")),
                        )
                    )

            db.query(InazEventSummary).filter(
                InazEventSummary.collaborator_id == collaborator.id,
                InazEventSummary.period_start == payload.period_start,
                InazEventSummary.period_end == payload.period_end,
            ).delete()
            for summary_row in payload.summary_rows:
                values = summary_row.get("values", {}) if isinstance(summary_row.get("values"), dict) else {}
                db.add(
                    InazEventSummary(
                        collaborator_id=collaborator.id,
                        application_user_id=collaborator.application_user_id,
                        period_start=payload.period_start,
                        period_end=payload.period_end,
                        event_code=clean(payload=summary_row.get("code")),
                        description=str(summary_row.get("description") or "").strip(),
                        valid_from=parse_portal_date(summary_row.get("start_date")),
                        valid_to=parse_portal_date(summary_row.get("end_date")),
                        spettante_minutes=duration_to_minutes(values.get("spettante")),
                        fruito_minutes=duration_to_minutes(values.get("fruito")),
                        residuo_prec_minutes=duration_to_minutes(values.get("residuoprec")),
                        saldo_minutes=duration_to_minutes(values.get("saldo")),
                        autorizzato_minutes=duration_to_minutes(values.get("autorizzato")),
                        pianificato_minutes=duration_to_minutes(values.get("proposto")),
                        richiesto_minutes=duration_to_minutes(values.get("richiesto")),
                        saldo_totale_minutes=duration_to_minutes(values.get("totale")),
                        unitamisura=clean(payload=values.get("unitamisura")),
                        raw_payload_json=summary_row,
                        source_job_id=job.id,
                    )
                )

        job.records_imported = imported_count
        job.records_skipped = skipped_count
        job.status = "completed"
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        db.refresh(job)
        return InazImportJsonResponse(job=InazImportJobResponse.model_validate(job), preview=preview)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise


def upsert_collaborator(db: Session, payload: Any) -> InazCollaborator:
    employee_code = str(payload.collaborator["employee_code"]).strip()
    company_code = clean(payload=payload.collaborator.get("company_code"))
    collaborator = db.execute(
        select(InazCollaborator).where(
            InazCollaborator.employee_code == employee_code,
            InazCollaborator.company_code == company_code,
        )
    ).scalar_one_or_none()
    if collaborator is None:
        collaborator = InazCollaborator(employee_code=employee_code, company_code=company_code, name=employee_code)

    collaborator.kint = clean(payload=payload.collaborator.get("kint"))
    collaborator.kkint = clean(payload=payload.collaborator.get("kkint"))
    collaborator.name = str(payload.collaborator.get("name") or employee_code).strip()
    collaborator.birth_date = parse_portal_date(payload.collaborator.get("birth_date"))
    collaborator.company_label = clean(payload=payload.company_label)
    collaborator.is_active = True
    return collaborator


def clean(*, payload: object | None) -> str | None:
    if payload is None:
        return None
    text = str(payload).strip()
    return text or None
