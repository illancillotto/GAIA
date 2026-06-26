from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeImportJob
from app.modules.presenze.services import import_jobs
from app.modules.presenze.services.parser import ParsedCollaboratorPayload, ParsedImportPayload


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username: str) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_accessi=True,
            module_presenze=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _parsed_collaborator(*, employee_code: str = "1854", work_date: str = "01/05/2026") -> ParsedCollaboratorPayload:
    return ParsedCollaboratorPayload(
        collaborator={
            "employee_code": employee_code,
            "company_code": "53",
            "name": "AMADU SALVATORE",
            "birth_date": "26/02/1967",
        },
        company_label="53 - Consorzio",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        daily_rows=[
            {
                "work_date": work_date,
                "raw_weekday": "L",
                "punches": [{"entry": "07:00", "exit": "13:30"}],
                "detail_punch_rows": [{"Ora": "07:00", "EU": "E", "Term": "Badge 1"}],
            }
        ],
        summary_rows=[
            {
                "code": "10011",
                "description": "Permesso",
                "start_date": "01/01/2026",
                "end_date": "31/12/2026",
                "values": {"saldo": "01:00"},
            }
        ],
    )


def test_import_collaborator_payload_counts_invalid_work_dates_as_errors() -> None:
    user = _create_user("import_job_invalid_day")
    db = TestingSessionLocal()
    try:
        parsed = ParsedImportPayload(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            collaborators=[],
            errors=[],
        )
        job = import_jobs.create_import_job(db, parsed=parsed, requested_by_user_id=user.id, filename="invalid.json")

        imported, skipped, errors = import_jobs.import_collaborator_payload(
            db,
            payload=_parsed_collaborator(work_date=" "),
            job=job,
        )

        assert (imported, skipped, errors) == (0, 0, 1)
        assert job.records_errors == 1
    finally:
        db.close()


def test_import_collaborator_payload_imports_then_skips_existing_rows() -> None:
    user = _create_user("import_job_success")
    db = TestingSessionLocal()
    try:
        parsed = ParsedImportPayload(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            collaborators=[],
            errors=[],
        )
        job = import_jobs.create_import_job(db, parsed=parsed, requested_by_user_id=user.id, filename="ok.json")
        payload = _parsed_collaborator()

        imported, skipped, errors = import_jobs.import_collaborator_payload(db, payload=payload, job=job)
        assert (imported, skipped, errors) == (1, 0, 0)
        assert job.records_imported == 1

        imported, skipped, errors = import_jobs.import_collaborator_payload(db, payload=payload, job=job)
        assert (imported, skipped, errors) == (0, 1, 0)
        assert job.records_skipped == 1
    finally:
        db.close()


def test_run_import_job_marks_job_failed_when_collaborator_import_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user("import_job_failure")
    db = TestingSessionLocal()
    try:
        parsed = ParsedImportPayload(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            collaborators=[_parsed_collaborator()],
            errors=[],
        )

        def _explode(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(import_jobs, "import_collaborator_payload", _explode)

        with pytest.raises(RuntimeError, match="boom"):
            import_jobs.run_import_job(
                db,
                parsed=parsed,
                requested_by_user_id=user.id,
                filename="broken.json",
            )

        job = db.execute(select(PresenzeImportJob).order_by(PresenzeImportJob.created_at.desc())).scalar_one()
        assert job.status == "failed"
        assert job.error_detail == "boom"
        assert job.finished_at is not None
    finally:
        db.close()


def test_parsed_collaborator_from_jsonable_validates_collaborator_and_defaults_periods() -> None:
    default_period_start = date(2026, 5, 1)
    default_period_end = date(2026, 5, 31)

    parsed = import_jobs.parsed_collaborator_from_jsonable(
        {
            "collaborator": {"employee_code": "1854", "name": "AMADU"},
            "company_label": " Consorzio ",
            "daily_rows": [{"work_date": "02/05/2026"}, "skip"],
            "summary_rows": [{"code": "10011"}, 1],
        },
        default_period_start=default_period_start,
        default_period_end=default_period_end,
    )

    assert parsed.company_label == "Consorzio"
    assert parsed.period_start == default_period_start
    assert parsed.period_end == default_period_end
    assert parsed.daily_rows == [{"work_date": "02/05/2026"}]
    assert parsed.summary_rows == [{"code": "10011"}]

    with pytest.raises(ValueError, match="Invalid collaborator payload"):
        import_jobs.parsed_collaborator_from_jsonable(
            {"collaborator": {"name": "Missing code"}},
            default_period_start=default_period_start,
            default_period_end=default_period_end,
        )


def test_run_import_job_returns_completed_response() -> None:
    user = _create_user("import_job_completed")
    db = TestingSessionLocal()
    try:
        payload = _parsed_collaborator()
        parsed = ParsedImportPayload(
            period_start=payload.period_start,
            period_end=payload.period_end,
            collaborators=[payload],
            errors=["preview warning"],
        )

        response = import_jobs.run_import_job(
            db,
            parsed=parsed,
            requested_by_user_id=user.id,
            filename="completed.json",
            params_json={"format": "collaboratori-json", "origin": "test"},
        )

        assert response.job.status == "completed"
        assert response.job.records_imported == 1
        assert response.preview.errors == ["preview warning"]
        assert response.preview.total_collaborators == 1
    finally:
        db.close()
