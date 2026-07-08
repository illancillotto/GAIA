from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.utenze import router as utenze_router
from app.modules.utenze.anpr.client import C004Result, C030Result
from app.modules.utenze.anpr.models import AnprCheckLog, AnprJobRun, AnprSyncConfig
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.utenze.anpr.schemas import AnprSyncConfigUpdate
from app.modules.utenze.anpr.service import (
    AnprJobSummary,
    AnprCapacitasCandidate,
    AnprQueueItem,
    _count_calls_for_local_day,
    _build_result_message,
    _infer_death_date_by_exclusion,
    _is_capacitas_deceduto_value,
    _local_day_bounds_utc,
    _map_person_status,
    _normalize_cf,
    _persist_unexpected_subject_error,
    _record_job_run,
    _resolve_ruolo_year,
    build_capacitas_candidates,
    build_capacitas_candidate_query,
    build_check_queue,
    lookup_anpr_by_codice_fiscale,
    refresh_capacitas_deceased_flags,
    run_daily_job,
    sync_single_subject,
    update_config,
    verify_single_subject_alive,
    verify_single_subject_death_date,
)
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject


UTC = timezone.utc


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _create_person_subject(
    db_session: Session,
    codice_fiscale: str,
    *,
    cognome: str = "Rossi",
    nome: str = "Mario",
    data_nascita: date | None = None,
    anpr_id: str | None = None,
    stato_anpr: str | None = None,
    last_anpr_check_at: datetime | None = None,
    capacitas_deceduto: bool | None = None,
) -> AnagraficaSubject:
    subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw=f"{cognome}_{nome}_{codice_fiscale}",
        nas_folder_path=f"/tmp/{uuid.uuid4()}",
        requires_review=False,
    )
    db_session.add(subject)
    db_session.flush()
    db_session.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome=cognome,
            nome=nome,
            codice_fiscale=codice_fiscale,
            data_nascita=data_nascita,
            anpr_id=anpr_id,
            stato_anpr=stato_anpr,
            last_anpr_check_at=last_anpr_check_at,
            capacitas_deceduto=capacitas_deceduto,
        )
    )
    db_session.commit()
    return subject


def _create_ruolo_job(db_session: Session, *, anno_tributario: int) -> RuoloImportJob:
    batch = RuoloImportJob(
        anno_tributario=anno_tributario,
        filename=f"ruolo-{anno_tributario}.txt",
        status="completed",
        total_partite=1,
        records_imported=1,
    )
    db_session.add(batch)
    db_session.commit()
    return batch


def _add_ruolo_row(db_session: Session, *, batch_id, anno_tributario: int, subject_id) -> None:
    db_session.add(
        RuoloAvviso(
            import_job_id=batch_id,
            codice_cnc=f"CNC-{uuid.uuid4().hex[:8]}",
            anno_tributario=anno_tributario,
            subject_id=subject_id,
        )
    )
    db_session.commit()


@pytest.mark.anyio
async def test_build_check_queue_only_role_subjects_oldest_first(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)

    oldest = _create_person_subject(db_session, "OLDROLE000000001", data_nascita=date(1940, 1, 1))
    middle = _create_person_subject(db_session, "MIDROLE000000001", data_nascita=date(1960, 1, 1))
    youngest_non_role = _create_person_subject(db_session, "NOROLE000000001", data_nascita=date(1930, 1, 1))

    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    ruolo_2024 = _create_ruolo_job(db_session, anno_tributario=2024)

    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=oldest.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=middle.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2024.id, anno_tributario=2024, subject_id=youngest_non_role.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(oldest.id), str(middle.id)]
    assert all(item.estimated_calls == 2 for item in queue)


@pytest.mark.anyio
async def test_build_check_queue_excludes_subjects_already_deceased(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)
    deceased = _create_person_subject(
        db_session,
        "DECROLE000000001",
        data_nascita=date(1940, 1, 1),
        stato_anpr="deceased",
    )
    alive = _create_person_subject(db_session, "ALVROLE000000001", data_nascita=date(1950, 1, 1))
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=deceased.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=alive.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(alive.id)]


@pytest.mark.anyio
async def test_build_check_queue_uses_latest_ruolo_year_when_env_not_set(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", None)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)
    old_role_subject = _create_person_subject(db_session, "ROLE20240000001", data_nascita=date(1940, 1, 1))
    latest_role_subject = _create_person_subject(db_session, "ROLE20250000001", data_nascita=date(1950, 1, 1))
    ruolo_2024 = _create_ruolo_job(db_session, anno_tributario=2024)
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2024.id, anno_tributario=2024, subject_id=old_role_subject.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=latest_role_subject.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(latest_role_subject.id)]


@pytest.mark.anyio
async def test_build_check_queue_excludes_subjects_marked_deceased_by_capacitas(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)
    excluded = _create_person_subject(
        db_session,
        "CAPDEC000000001",
        data_nascita=date(1935, 1, 1),
        capacitas_deceduto=True,
    )
    included = _create_person_subject(db_session, "CAPALV000000001", data_nascita=date(1940, 1, 1))
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=excluded.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=included.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(included.id)]


@pytest.mark.anyio
async def test_build_check_queue_skips_recent_not_found_subjects(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=180)
    skipped = _create_person_subject(
        db_session,
        "NFRECENT00000001",
        data_nascita=date(1940, 1, 1),
        stato_anpr="not_found_anpr",
        last_anpr_check_at=frozen_now - timedelta(days=30),
    )
    included = _create_person_subject(db_session, "ROLELIVE2025001", data_nascita=date(1950, 1, 1))
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=skipped.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=included.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(included.id)]


@pytest.mark.anyio
async def test_build_check_queue_retries_not_found_after_retry_threshold(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=180)
    retried = _create_person_subject(
        db_session,
        "NFRETRY000000001",
        data_nascita=date(1940, 1, 1),
        stato_anpr="not_found_anpr",
        last_anpr_check_at=frozen_now - timedelta(days=181),
    )
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=retried.id)

    queue = await build_check_queue(db_session, config)

    assert [item.subject_id for item in queue] == [str(retried.id)]


@pytest.mark.anyio
async def test_sync_single_no_anpr_id(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501U")
    client = AsyncMock()
    client.c030_get_anpr_id = AsyncMock(
        return_value=C030Result(
            success=True,
            anpr_id="ANPR-123",
            id_operazione_anpr="op-c030",
            esito="anpr_id_found",
            error_detail=None,
            id_operazione_client="client-c030",
        )
    )
    client.c004_check_death = AsyncMock(
        return_value=C004Result(
            success=True,
            esito="alive",
            data_decesso=None,
            id_operazione_anpr="op-c004",
            error_detail=None,
            id_operazione_client="client-c004",
            raw_response={},
        )
    )

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)
    logs = db_session.scalars(select(AnprCheckLog).where(AnprCheckLog.subject_id == subject.id).order_by(AnprCheckLog.call_type)).all()

    assert result.success is True
    assert result.esito == "alive"
    assert result.anpr_id == "ANPR-123"
    assert result.calls_made == 2
    assert person is not None
    assert person.anpr_id == "ANPR-123"
    assert person.stato_anpr == "alive"
    assert person.last_c030_check_at is not None
    assert person.last_anpr_check_at is not None
    assert [item.call_type for item in logs] == ["C004", "C030"]
    client.c030_get_anpr_id.assert_awaited_once()
    client.c004_check_death.assert_awaited_once()


@pytest.mark.anyio
async def test_sync_single_already_has_anpr_id(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501V", anpr_id="ANPR-EXISTING")
    client = AsyncMock()
    client.c030_get_anpr_id = AsyncMock()
    client.c004_check_death = AsyncMock(
        return_value=C004Result(
            success=True,
            esito="alive",
            data_decesso=None,
            id_operazione_anpr="op-c004",
            error_detail=None,
            id_operazione_client="client-c004",
            raw_response={},
        )
    )

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    logs = db_session.scalars(select(AnprCheckLog).where(AnprCheckLog.subject_id == subject.id)).all()

    assert result.success is True
    assert result.calls_made == 1
    assert result.anpr_id == "ANPR-EXISTING"
    assert len(logs) == 1
    assert logs[0].call_type == "C004"
    client.c030_get_anpr_id.assert_not_awaited()
    client.c004_check_death.assert_awaited_once()


@pytest.mark.anyio
async def test_sync_single_deceased(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501Z", anpr_id="ANPR-DEAD")
    client = AsyncMock()
    client.c004_check_death = AsyncMock(
        return_value=C004Result(
            success=True,
            esito="deceased",
            data_decesso=date(2025, 1, 3),
            id_operazione_anpr="op-c004-dead",
            error_detail=None,
            id_operazione_client="client-c004-dead",
            raw_response={},
        )
    )

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)

    assert result.success is True
    assert result.esito == "deceased"
    assert result.data_decesso == date(2025, 1, 3)
    assert person is not None
    assert person.stato_anpr == "deceased"
    assert person.data_decesso == date(2025, 1, 3)


@pytest.mark.anyio
async def test_sync_single_deceased_infers_date_from_historical_c004_checks(db_session: Session) -> None:
    subject = _create_person_subject(
        db_session,
        "MSTGNN58A24F208V",
        anpr_id="BH28554MH",
        data_nascita=date(1958, 1, 24),
    )

    class FakeClient:
        def __init__(self) -> None:
            self.reference_dates: list[date | None] = []

        async def c004_check_death(
            self,
            anpr_id: str,
            key: str,
            *,
            reference_date: date | None = None,
            death_event_date: date | None = None,
        ) -> C004Result:
            assert anpr_id == "BH28554MH"
            assert key
            self.reference_dates.append(reference_date)
            effective_reference_date = reference_date or date.today()
            esito = "deceased" if effective_reference_date >= date(2025, 8, 20) else "alive"
            return C004Result(
                success=True,
                esito=esito,
                data_decesso=None,
                id_operazione_anpr=f"op-{effective_reference_date.isoformat()}",
                error_detail=None,
                id_operazione_client=f"client-{effective_reference_date.isoformat()}",
                raw_response={},
            )

    client = FakeClient()

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)
    logs = db_session.scalars(select(AnprCheckLog).where(AnprCheckLog.subject_id == subject.id)).all()

    assert result.success is True
    assert result.esito == "deceased"
    assert result.data_decesso == date(2025, 8, 20)
    assert result.calls_made > 1
    assert person is not None
    assert person.data_decesso == date(2025, 8, 20)
    assert len(logs) == result.calls_made
    assert client.reference_dates[1] == date.today() - timedelta(days=366)
    assert date(2025, 8, 20) in [value for value in client.reference_dates if value is not None]


@pytest.mark.anyio
async def test_verify_single_subject_alive_skips_death_date_inference(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501Z", anpr_id="ANPR-DEAD")
    client = AsyncMock()
    client.c004_check_death = AsyncMock(
        return_value=C004Result(
            success=True,
            esito="deceased",
            data_decesso=None,
            id_operazione_anpr="op-c004-dead",
            error_detail=None,
            id_operazione_client="client-c004-dead",
            raw_response={},
        )
    )

    result = await verify_single_subject_alive(str(subject.id), db_session, "test", object(), client)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)

    assert result.success is True
    assert result.esito == "deceased"
    assert result.data_decesso is None
    assert result.calls_made == 1
    assert person is not None
    assert person.stato_anpr == "deceased"
    assert person.data_decesso is None


@pytest.mark.anyio
async def test_verify_single_subject_death_date_requires_prior_deceased_status(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501A", anpr_id="ANPR-ALIVE", stato_anpr="alive")
    client = AsyncMock()

    result = await verify_single_subject_death_date(str(subject.id), db_session, "test", object(), client)

    assert result.success is False
    assert result.calls_made == 0
    assert "Prima esegui 'Verifica se vivo'" in result.message


@pytest.mark.anyio
async def test_verify_single_subject_death_date_returns_existing_date_without_calls(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501B", anpr_id="ANPR-DEAD", stato_anpr="deceased")
    person = db_session.get(AnagraficaPerson, subject.id)
    assert person is not None
    person.data_decesso = date(2025, 1, 3)
    db_session.commit()

    client = AsyncMock()
    result = await verify_single_subject_death_date(str(subject.id), db_session, "test", object(), client)

    assert result.success is True
    assert result.calls_made == 0
    assert result.data_decesso == date(2025, 1, 3)


@pytest.mark.anyio
async def test_sync_single_c030_not_found_stops_before_c004_and_persists_status(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501Q")
    client = AsyncMock()
    client.c030_get_anpr_id = AsyncMock(
        return_value=C030Result(
            success=False,
            anpr_id=None,
            id_operazione_anpr="op-c030-miss",
            esito="not_found",
            error_detail="EN122 | E | Soggetto non registrato in ANPR",
            id_operazione_client="client-c030-miss",
        )
    )
    client.c004_check_death = AsyncMock()

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)
    logs = db_session.scalars(select(AnprCheckLog).where(AnprCheckLog.subject_id == subject.id)).all()

    assert result.success is False
    assert result.esito == "not_found"
    assert result.calls_made == 1
    assert "EN122" in result.message
    assert person is not None
    assert person.stato_anpr == "not_found_anpr"
    assert person.anpr_id is None
    assert person.last_c030_check_at is not None
    assert person.last_anpr_check_at is None
    assert len(logs) == 1
    assert logs[0].call_type == "C030"
    assert logs[0].esito == "not_found"
    client.c030_get_anpr_id.assert_awaited_once()
    client.c004_check_death.assert_not_awaited()


@pytest.mark.anyio
async def test_config_singleton(db_session: Session) -> None:
    first = await AnprSyncConfig.get_or_create_default(db_session)
    db_session.commit()
    second = await AnprSyncConfig.get_or_create_default(db_session)

    total = db_session.execute(select(func.count()).select_from(AnprSyncConfig)).scalar_one()

    assert first.id == 1
    assert second.id == 1
    assert total == 1


@pytest.mark.anyio
async def test_update_config_applies_non_none_fields_and_audit_metadata() -> None:
    class FakeAsyncSession:
        def __init__(self, config) -> None:
            self.config = config
            self.committed = False
            self.refreshed = False

        async def commit(self) -> None:
            self.committed = True

        async def refresh(self, config) -> None:
            self.refreshed = True

    config = AnprSyncConfig(
        id=1,
        max_calls_per_day=100,
        job_enabled=True,
        job_cron="0 2 * * *",
        lookback_years=1,
        retry_not_found_days=90,
    )
    session = FakeAsyncSession(config)

    async def fake_get_or_create_default(db):
        return config

    import app.modules.utenze.anpr.service as service_module

    original = service_module.get_config
    service_module.get_config = fake_get_or_create_default
    try:
        updated = await update_config(
            session,
            AnprSyncConfigUpdate(max_calls_per_day=150, job_enabled=False, job_cron="15 3 * * *"),
            user_id=7,
        )
    finally:
        service_module.get_config = original

    assert updated.max_calls_per_day == 150
    assert updated.job_enabled is False
    assert updated.job_cron == "15 3 * * *"
    assert updated.updated_by_user_id == 7
    assert isinstance(updated.updated_at, datetime)
    assert session.committed is True
    assert session.refreshed is True


def test_status_mapping_and_messages_cover_expected_values() -> None:
    assert _map_person_status("alive") == "alive"
    assert _map_person_status("not_found") == "not_found_anpr"
    assert _map_person_status("cancelled") == "cancelled_anpr"
    assert _map_person_status("anpr_id_found") == "unknown"
    assert _build_result_message("deceased", None) == "Soggetto risultato deceduto in ANPR"
    assert "Errore" in _build_result_message("error", "timeout")


def test_capacitas_deceduto_value_parser_is_conservative() -> None:
    assert _is_capacitas_deceduto_value("V") is True
    assert _is_capacitas_deceduto_value("deceduto") is True
    assert _is_capacitas_deceduto_value("true") is True
    assert _is_capacitas_deceduto_value("X") is False
    assert _is_capacitas_deceduto_value("") is False
    assert _is_capacitas_deceduto_value(None) is False


def test_normalize_cf_handles_empty_spacing_and_case() -> None:
    assert _normalize_cf(None) is None
    assert _normalize_cf("") is None
    assert _normalize_cf(" rs s mra80a01 h501u ") == "RSSMRA80A01H501U"


@pytest.mark.anyio
async def test_update_config_rejects_invalid_cron(db_session: Session) -> None:
    class FakeDb:
        async def commit(self):
            raise AssertionError("commit should not be called")

        async def refresh(self, config):
            raise AssertionError("refresh should not be called")

    class FakeUpdate:
        job_cron = "0 2 * *"

        def model_dump(self, *, exclude_none: bool = True):
            return {"job_cron": self.job_cron}

    import app.modules.utenze.anpr.service as service_module

    original = service_module.get_config
    service_module.get_config = AsyncMock(
        return_value=AnprSyncConfig(
            id=1,
            max_calls_per_day=100,
            job_enabled=True,
            job_cron="0 2 * * *",
            lookback_years=1,
            retry_not_found_days=90,
        )
    )
    try:
        with pytest.raises(ValueError, match="job_cron must contain exactly 5 cron fields"):
            await update_config(FakeDb(), FakeUpdate(), user_id=1)
    finally:
        service_module.get_config = original


@pytest.mark.anyio
async def test_build_capacitas_candidates_and_query_cover_force_toggle(db_session: Session) -> None:
    stmt_without_force = build_capacitas_candidate_query(min_age_years=100, limit=10, force=False)
    sql_without_force = str(stmt_without_force.compile(compile_kwargs={"literal_binds": True}))
    stmt_with_force = build_capacitas_candidate_query(min_age_years=100, limit=10, force=True)
    sql_with_force = str(stmt_with_force.compile(compile_kwargs={"literal_binds": True}))
    assert "capacitas_last_check_at IS NULL" in sql_without_force
    assert "capacitas_last_check_at IS NULL" not in sql_with_force

    class FakeResult:
        def __init__(self, rows) -> None:
            self._rows = rows

        def all(self):
            return self._rows

    class FakeDb:
        def __init__(self) -> None:
            self.rows = [
                (uuid.uuid4(), "CAPTEST80A01H501U", 115, "alive"),
                (uuid.uuid4(), "CAPTEST80A01H501V", None, None),
            ]

        def execute(self, stmt):
            return FakeResult(self.rows)

    candidates = await build_capacitas_candidates(FakeDb(), min_age_years=100, limit=10, force=False)
    assert candidates[0].codice_fiscale == "CAPTEST80A01H501U"
    assert candidates[1].age_years is None


@pytest.mark.anyio
async def test_refresh_capacitas_deceased_flags_returns_empty_when_no_candidates(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.utenze.anpr.service.build_capacitas_candidates", AsyncMock(return_value=[]))

    result = await refresh_capacitas_deceased_flags(db_session)

    assert result.processed == 0
    assert result.items == []


@pytest.mark.anyio
async def test_refresh_capacitas_deceased_flags_raises_value_error_when_credentials_missing(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.modules.utenze.anpr.service.build_capacitas_candidates",
        AsyncMock(return_value=[AnprCapacitasCandidate("s1", "CF1", 101, "alive")]),
    )
    monkeypatch.setattr("app.modules.utenze.anpr.service.pick_credential", lambda db, credential_id: (_ for _ in ()).throw(RuntimeError("missing cred")))

    with pytest.raises(ValueError, match="missing cred"):
        await refresh_capacitas_deceased_flags(db_session)


@pytest.mark.anyio
async def test_refresh_capacitas_deceased_flags_covers_checked_missing_and_failed_items(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = _create_person_subject(db_session, "CAPOK80A01H501U", data_nascita=date(1910, 1, 1), stato_anpr="alive")
    missing_subject_id = str(uuid.uuid4())
    candidates = [
        AnprCapacitasCandidate(str(subject.id), "CAPOK80A01H501U", 115, "alive"),
        AnprCapacitasCandidate(missing_subject_id, "MISSING80A01H501U", 116, "alive"),
        AnprCapacitasCandidate(str(subject.id), "CAPERR80A01H501U", 117, "alive"),
    ]
    monkeypatch.setattr("app.modules.utenze.anpr.service.build_capacitas_candidates", AsyncMock(return_value=candidates))

    credential = SimpleNamespace(id=11, username="user")
    monkeypatch.setattr("app.modules.utenze.anpr.service.pick_credential", lambda db, credential_id: (credential, "pwd"))

    used_ids: list[int] = []
    monkeypatch.setattr("app.modules.utenze.anpr.service.mark_credential_used", lambda db, cid: used_ids.append(cid))

    class FakeManager:
        def __init__(self, username: str, password: str) -> None:
            self.closed = False

        async def login(self) -> None:
            return None

        async def activate_app(self, app_name: str) -> None:
            assert app_name == "involture"

        async def close(self) -> None:
            self.closed = True

    class Row:
        def __init__(self, codice_fiscale: str, deceduto: str | None) -> None:
            self.codice_fiscale = codice_fiscale
            self.deceduto = deceduto

    class FakeClient:
        def __init__(self, manager) -> None:
            self.calls = 0

        async def search_by_cf(self, codice_fiscale: str):
            self.calls += 1
            if codice_fiscale == "CAPERR80A01H501U":
                raise RuntimeError("boom capacitas")
            return SimpleNamespace(rows=[Row("capok80a01h501u", "deceduto"), Row("other", None)])

    monkeypatch.setattr("app.modules.utenze.anpr.service.CapacitasSessionManager", FakeManager)
    monkeypatch.setattr("app.modules.utenze.anpr.service.InVoltureClient", FakeClient)
    original_get = db_session.get
    monkeypatch.setattr(db_session, "get", lambda model, key: original_get(model, uuid.UUID(str(key))))

    result = await refresh_capacitas_deceased_flags(db_session)

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)
    assert result.processed == 3
    assert result.marked_deceased == 1
    assert result.failed == 2
    assert {item.status for item in result.items} == {"checked", "missing_subject", "failed"}
    assert person is not None
    assert person.capacitas_deceduto is True
    assert used_ids == [11]


@pytest.mark.anyio
async def test_refresh_capacitas_deceased_flags_counts_unchanged_subjects(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    subject = _create_person_subject(db_session, "CAPUNCH80A01H501U", data_nascita=date(1910, 1, 1), stato_anpr="alive")
    monkeypatch.setattr(
        "app.modules.utenze.anpr.service.build_capacitas_candidates",
        AsyncMock(return_value=[AnprCapacitasCandidate(str(subject.id), "CAPUNCH80A01H501U", 115, "alive")]),
    )
    monkeypatch.setattr("app.modules.utenze.anpr.service.pick_credential", lambda db, credential_id: (SimpleNamespace(id=13, username="user"), "pwd"))
    monkeypatch.setattr("app.modules.utenze.anpr.service.mark_credential_used", lambda db, cid: None)

    class FakeManager:
        def __init__(self, username: str, password: str) -> None:
            return None

        async def login(self) -> None:
            return None

        async def activate_app(self, app_name: str) -> None:
            return None

        async def close(self) -> None:
            return None

    class FakeClient:
        def __init__(self, manager) -> None:
            return None

        async def search_by_cf(self, codice_fiscale: str):
            return SimpleNamespace(rows=[SimpleNamespace(codice_fiscale=codice_fiscale, deceduto="N")])

    monkeypatch.setattr("app.modules.utenze.anpr.service.CapacitasSessionManager", FakeManager)
    monkeypatch.setattr("app.modules.utenze.anpr.service.InVoltureClient", FakeClient)
    original_get = db_session.get
    monkeypatch.setattr(db_session, "get", lambda model, key: original_get(model, uuid.UUID(str(key))))

    result = await refresh_capacitas_deceased_flags(db_session)
    assert result.unchanged == 1


@pytest.mark.anyio
async def test_refresh_capacitas_deceased_flags_rolls_back_and_marks_credential_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = _create_person_subject(db_session, "CAPROLL80A01H501U", data_nascita=date(1910, 1, 1), stato_anpr="alive")
    monkeypatch.setattr(
        "app.modules.utenze.anpr.service.build_capacitas_candidates",
        AsyncMock(return_value=[AnprCapacitasCandidate(str(subject.id), "CAPROLL80A01H501U", 115, "alive")]),
    )
    credential = SimpleNamespace(id=12, username="user")
    monkeypatch.setattr("app.modules.utenze.anpr.service.pick_credential", lambda db, credential_id: (credential, "pwd"))

    errors: list[tuple[int, str]] = []
    monkeypatch.setattr("app.modules.utenze.anpr.service.mark_credential_error", lambda db, cid, msg: errors.append((cid, msg)))

    class FakeManager:
        def __init__(self, username: str, password: str) -> None:
            self.closed = False

        async def login(self) -> None:
            raise RuntimeError("login failed")

        async def activate_app(self, app_name: str) -> None:
            return None

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("app.modules.utenze.anpr.service.CapacitasSessionManager", FakeManager)
    original_get = db_session.get
    monkeypatch.setattr(db_session, "get", lambda model, key: original_get(model, uuid.UUID(str(key))))

    with pytest.raises(RuntimeError, match="login failed"):
        await refresh_capacitas_deceased_flags(db_session)

    assert errors == [(12, "login failed")]


@pytest.mark.anyio
async def test_infer_death_date_by_exclusion_handles_abort_and_budget_edge_cases(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.modules.utenze.anpr.service as service_module

    now = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return date(2026, 7, 8)

    monkeypatch.setattr(service_module, "date", FrozenDate)

    async def fake_run_c004(*args, **kwargs):
        return fake_run_c004.results.pop(0)

    original = service_module._run_c004_check_and_log
    service_module._run_c004_check_and_log = fake_run_c004
    try:
        fake_run_c004.results = [SimpleNamespace(esito="error", calls_used=1)]
        inferred, calls = await _infer_death_date_by_exclusion(
            db_session,
            client=AsyncMock(),
            subject_uuid=uuid.uuid4(),
            anpr_id="ANPR",
            subject_id_short="subj",
            triggered_by="test",
            created_at=now,
            birth_date=None,
        )
        assert inferred is None
        assert calls == 1

        fake_run_c004.results = [SimpleNamespace(esito="deceased", calls_used=10)]
        inferred, calls = await _infer_death_date_by_exclusion(
            db_session,
            client=AsyncMock(),
            subject_uuid=uuid.uuid4(),
            anpr_id="ANPR",
            subject_id_short="subj",
            triggered_by="test",
            created_at=now,
            birth_date=None,
        )
        assert inferred is None
        assert calls == 10

        birth_limit = date(2025, 7, 8)
        fake_run_c004.results = [SimpleNamespace(esito="deceased", calls_used=1)]
        inferred, calls = await _infer_death_date_by_exclusion(
            db_session,
            client=AsyncMock(),
            subject_uuid=uuid.uuid4(),
            anpr_id="ANPR",
            subject_id_short="subj",
            triggered_by="test",
            created_at=now,
            birth_date=birth_limit,
        )
        assert inferred is None
        assert calls == 1

        monkeypatch.setattr(service_module, "ANPR_DEATH_INFERENCE_MAX_CALLS", 2)
        fake_run_c004.results = [
            SimpleNamespace(esito="alive", calls_used=1),
            SimpleNamespace(esito="alive", calls_used=1),
        ]
        inferred, calls = await _infer_death_date_by_exclusion(
            db_session,
            client=AsyncMock(),
            subject_uuid=uuid.uuid4(),
            anpr_id="ANPR",
            subject_id_short="subj",
            triggered_by="test",
            created_at=now,
            birth_date=None,
        )
        assert inferred is None
        assert calls == 2

        monkeypatch.setattr(service_module, "ANPR_DEATH_INFERENCE_MAX_CALLS", 4)
        fake_run_c004.results = [
            SimpleNamespace(esito="alive", calls_used=1),
            SimpleNamespace(esito="error", calls_used=1),
        ]
        inferred, calls = await _infer_death_date_by_exclusion(
            db_session,
            client=AsyncMock(),
            subject_uuid=uuid.uuid4(),
            anpr_id="ANPR",
            subject_id_short="subj",
            triggered_by="test",
            created_at=now,
            birth_date=None,
        )
        assert inferred is None
        assert calls == 2
    finally:
        service_module._run_c004_check_and_log = original


@pytest.mark.anyio
async def test_persist_unexpected_subject_error_updates_person_and_also_handles_missing_person(db_session: Session) -> None:
    subject = _create_person_subject(db_session, "ERRPERS80A01H501U")
    created_at = datetime.now(UTC)

    await _persist_unexpected_subject_error(
        db_session,
        subject_id=str(subject.id),
        triggered_by="job",
        error_detail="errore inatteso",
        created_at=created_at,
    )
    await _persist_unexpected_subject_error(
        db_session,
        subject_id=str(uuid.uuid4()),
        triggered_by="job",
        error_detail="errore orfano",
        created_at=created_at,
    )

    db_session.expire_all()
    person = db_session.get(AnagraficaPerson, subject.id)
    logs = db_session.scalars(select(AnprCheckLog).order_by(AnprCheckLog.created_at.asc())).all()
    assert person is not None
    assert person.stato_anpr == "error"
    assert len(logs) == 2


@pytest.mark.anyio
async def test_sync_single_subject_returns_errors_for_missing_subject_and_missing_cf(db_session: Session) -> None:
    missing = await sync_single_subject(str(uuid.uuid4()), db_session, "test", object(), AsyncMock())
    assert missing.calls_made == 0
    assert missing.message == "Soggetto non trovato o non persona fisica"

    subject_id = str(uuid.uuid4())

    class FakeResult:
        def one_or_none(self):
            return (SimpleNamespace(id=uuid.UUID(subject_id)), SimpleNamespace(codice_fiscale=None))

    class FakeDb:
        def execute(self, stmt):
            return FakeResult()

    missing_cf = await sync_single_subject(subject_id, FakeDb(), "test", object(), AsyncMock())
    assert missing_cf.calls_made == 0
    assert missing_cf.message == "Codice fiscale mancante"


@pytest.mark.anyio
async def test_sync_single_subject_keeps_deceased_without_inferred_date_when_sondes_fail(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    subject = _create_person_subject(db_session, "RSSMRA80A01H501R", anpr_id="ANPR-DEAD")
    client = AsyncMock()
    client.c004_check_death = AsyncMock(
        return_value=C004Result(
            success=True,
            esito="deceased",
            data_decesso=None,
            id_operazione_anpr="op-c004",
            error_detail=None,
            id_operazione_client="client-c004",
            raw_response={},
        )
    )
    monkeypatch.setattr("app.modules.utenze.anpr.service._infer_death_date_by_exclusion", AsyncMock(return_value=(None, 3)))

    result = await sync_single_subject(str(subject.id), db_session, "test", object(), client)

    assert result.esito == "deceased"
    assert result.data_decesso is None
    assert result.calls_made == 4


@pytest.mark.anyio
async def test_verify_single_subject_death_date_covers_missing_subject_missing_cf_c030_and_inference_paths(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = await verify_single_subject_death_date(str(uuid.uuid4()), db_session, "test", object(), AsyncMock())
    assert missing.message == "Soggetto non trovato o non persona fisica"

    subject_id = str(uuid.uuid4())

    class FakeResult:
        def one_or_none(self):
            return (SimpleNamespace(id=uuid.UUID(subject_id)), SimpleNamespace(codice_fiscale=None))

    class FakeDb:
        def execute(self, stmt):
            return FakeResult()

    missing_cf = await verify_single_subject_death_date(subject_id, FakeDb(), "test", object(), AsyncMock())
    assert missing_cf.message == "Codice fiscale mancante"

    c030_not_found_subject = _create_person_subject(db_session, "RSSMRA80A01H501D")
    client_not_found = AsyncMock()
    client_not_found.c030_get_anpr_id = AsyncMock(
        return_value=C030Result(
            success=False,
            anpr_id=None,
            id_operazione_anpr="op-c030",
            esito="not_found",
            error_detail="not found",
            id_operazione_client="client-c030",
        )
    )
    result_not_found = await verify_single_subject_death_date(str(c030_not_found_subject.id), db_session, "test", object(), client_not_found)
    assert result_not_found.esito == "not_found"
    assert result_not_found.calls_made == 1

    c030_ok_subject = _create_person_subject(db_session, "RSSMRA80A01H501E", stato_anpr="deceased")
    client_ok = AsyncMock()
    client_ok.c030_get_anpr_id = AsyncMock(
        return_value=C030Result(
            success=True,
            anpr_id="ANPR-NEW",
            id_operazione_anpr="op-c030-ok",
            esito="anpr_id_found",
            error_detail=None,
            id_operazione_client="client-c030-ok",
        )
    )
    monkeypatch.setattr("app.modules.utenze.anpr.service._infer_death_date_by_exclusion", AsyncMock(side_effect=[(date(2025, 8, 20), 4), (None, 4)]))

    success = await verify_single_subject_death_date(str(c030_ok_subject.id), db_session, "test", object(), client_ok)
    assert success.success is True
    assert success.data_decesso == date(2025, 8, 20)
    assert success.calls_made == 5

    second_subject = _create_person_subject(db_session, "RSSMRA80A01H501F", anpr_id="ANPR-OLD", stato_anpr="deceased")
    failure = await verify_single_subject_death_date(str(second_subject.id), db_session, "test", object(), AsyncMock())
    assert failure.success is False
    assert "Impossibile determinare" in failure.message


@pytest.mark.anyio
async def test_lookup_preview_covers_all_short_circuit_paths() -> None:
    assert (await lookup_anpr_by_codice_fiscale("   ", client=AsyncMock())).message == "Codice fiscale mancante"

    client = AsyncMock()
    client.c030_get_anpr_id = AsyncMock(
        side_effect=[
            C030Result(False, None, "op1", "error", "bad c030", "c1"),
            C030Result(False, None, "op2", "cancelled", "cancelled", "c2"),
            C030Result(True, "   ", "op3", "anpr_id_found", None, "c3"),
            C030Result(True, "ANPR-1", "op4", "anpr_id_found", None, "c4"),
            C030Result(True, "ANPR-2", "op5", "anpr_id_found", None, "c5"),
        ]
    )
    client.c004_check_death = AsyncMock(
        side_effect=[
            C004Result(False, "error", None, "op-c004-1", "bad c004", "x", {}),
            C004Result(True, "alive", None, "op-c004-2", None, "y", {}, calls_used=2),
        ]
    )

    error_c030 = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=client)
    cancelled = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=client)
    empty_uid = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=client)
    error_c004 = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=client)
    alive = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=client)

    assert error_c030.success is False
    assert cancelled.stato_anpr == "cancelled_anpr"
    assert empty_uid.success is False
    assert error_c004.success is False and error_c004.anpr_id == "ANPR-1"
    assert alive.success is True and alive.stato_anpr == "alive" and alive.calls_made == 3


@pytest.mark.anyio
async def test_run_daily_job_covers_lock_limit_and_exception_paths(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 9, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)
    db_session.add(config)
    db_session.commit()
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    ruolo_2025_id = ruolo_2025.id
    ruolo_subject = _create_person_subject(db_session, "RSSMRA80A01H501I", anpr_id="ANPR-RUOLO")
    _add_ruolo_row(db_session, batch_id=ruolo_2025_id, anno_tributario=2025, subject_id=ruolo_subject.id)

    class FakeCursor:
        def execute(self, sql, params):
            return None

        def fetchone(self):
            return (False,)

        def close(self):
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr(service_module.engine.dialect, "name", "postgresql")
    monkeypatch.setattr(service_module.engine, "raw_connection", lambda: FakeConn())

    async def db_factory():
        return db_session

    lock_summary = await run_daily_job(db_factory)
    assert lock_summary.message == "job already running on another worker"

    monkeypatch.setattr(service_module.engine.dialect, "name", "sqlite")
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=10))
    limit_summary = await run_daily_job(db_factory)
    assert limit_summary.message == "daily call limit reached"

    queue_subject = _create_person_subject(db_session, "RSSMRA80A01H501G", anpr_id="ANPR-1")
    _add_ruolo_row(db_session, batch_id=ruolo_2025_id, anno_tributario=2025, subject_id=queue_subject.id)
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=0))
    monkeypatch.setattr(service_module, "build_check_queue", AsyncMock(return_value=[AnprQueueItem(str(queue_subject.id), 2), AnprQueueItem(str(uuid.uuid4()), 20)]))
    monkeypatch.setattr(service_module.anyio, "sleep", AsyncMock())

    async def fake_sync(subject_id: str, db, triggered_by: str, auth, client):
        if subject_id == str(queue_subject.id):
            raise RuntimeError("boom job")
        return SimpleNamespace(success=True, esito="alive", calls_made=1)

    monkeypatch.setattr(service_module, "sync_single_subject", fake_sync)
    summary = await run_daily_job(db_factory)
    assert summary.errors == 1
    assert summary.calls_used == 2


@pytest.mark.anyio
async def test_run_daily_job_counts_deceased_errors_and_finalizer_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 9, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 1)
    monkeypatch.setattr(service_module.engine.dialect, "name", "sqlite")
    monkeypatch.setattr(service_module.anyio, "sleep", AsyncMock())

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)

    class FakeGenerator:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

    class FakeDb:
        def __init__(self) -> None:
            self._anpr_generator = iter(FakeGenerator())
            self.recorded = []

        def close(self):
            return None

        def add(self, value):
            self.recorded.append(value)

        async def commit(self):
            return None

    db = FakeDb()

    async def db_factory():
        return db

    monkeypatch.setattr(service_module, "get_config", AsyncMock(return_value=config))
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=0))
    monkeypatch.setattr(service_module, "build_check_queue", AsyncMock(return_value=[AnprQueueItem("s1", 1), AnprQueueItem("s2", 20)]))
    monkeypatch.setattr(service_module, "_resolve_ruolo_year", AsyncMock(return_value=2025))

    results = [
        SimpleNamespace(success=True, esito="deceased", calls_made=1),
        SimpleNamespace(success=False, esito="alive", calls_made=1),
    ]

    async def fake_sync(subject_id: str, db, triggered_by: str, auth, client):
        return results.pop(0)

    monkeypatch.setattr(service_module, "sync_single_subject", fake_sync)

    summary = await run_daily_job(db_factory)
    assert summary.deceased_found == 1
    assert summary.errors == 0


@pytest.mark.anyio
async def test_run_daily_job_handles_zero_budget_break_and_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 9, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 1)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.engine.dialect, "name", "sqlite")
    monkeypatch.setattr(service_module.anyio, "sleep", AsyncMock())
    monkeypatch.setattr(service_module, "_resolve_ruolo_year", AsyncMock(return_value=2025))

    config = AnprSyncConfig(id=1, max_calls_per_day=1, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)

    class Gen:
        yielded = False

        def __iter__(self):
            return self

        def __next__(self):
            if self.yielded:
                raise StopIteration
            self.yielded = True
            raise StopIteration

    class FakeDb:
        def __init__(self) -> None:
            self._anpr_generator = iter(Gen())
            self.closed = False

        async def close(self):
            self.closed = True

        def add(self, value):
            return None

        async def commit(self):
            return None

    db = FakeDb()

    async def db_factory():
        return db

    monkeypatch.setattr(service_module, "get_config", AsyncMock(return_value=config))
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=1))
    monkeypatch.setattr(service_module, "build_check_queue", AsyncMock(return_value=[AnprQueueItem("s1", 1)]))

    summary = await run_daily_job(db_factory)
    assert summary.message == "daily call limit reached"
    assert db.closed is True


@pytest.mark.anyio
async def test_run_daily_job_counts_unsuccessful_results_and_skips_rollback_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 9, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.engine.dialect, "name", "sqlite")
    monkeypatch.setattr(service_module.anyio, "sleep", AsyncMock())
    monkeypatch.setattr(service_module, "_resolve_ruolo_year", AsyncMock(return_value=2025))
    monkeypatch.setattr(service_module, "_persist_unexpected_subject_error", AsyncMock())

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)

    class FakeDb:
        def add(self, value):
            return None

        async def commit(self):
            return None

    db = FakeDb()

    async def db_factory():
        return db

    monkeypatch.setattr(service_module, "get_config", AsyncMock(return_value=config))
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=0))
    monkeypatch.setattr(service_module, "build_check_queue", AsyncMock(return_value=[AnprQueueItem("s1", 1), AnprQueueItem("s2", 1)]))

    results = [
        SimpleNamespace(success=False, esito="alive", calls_made=1),
    ]

    async def fake_sync(subject_id: str, db, triggered_by: str, auth, client):
        if subject_id == "s1":
            return results.pop(0)
        raise RuntimeError("boom no rollback")

    monkeypatch.setattr(service_module, "sync_single_subject", fake_sync)

    summary = await run_daily_job(db_factory)
    assert summary.errors == 2


@pytest.mark.anyio
async def test_run_daily_job_finalizer_handles_missing_close_with_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 9, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 10)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.engine.dialect, "name", "sqlite")
    monkeypatch.setattr(service_module.anyio, "sleep", AsyncMock())
    monkeypatch.setattr(service_module, "_resolve_ruolo_year", AsyncMock(return_value=2025))

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)

    class Gen:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

    class FakeDb:
        def __init__(self) -> None:
            self._anpr_generator = iter(Gen())

        def add(self, value):
            return None

        async def commit(self):
            return None

    db = FakeDb()

    async def db_factory():
        return db

    monkeypatch.setattr(service_module, "get_config", AsyncMock(return_value=config))
    monkeypatch.setattr(service_module, "_count_calls_for_local_day", AsyncMock(return_value=0))
    monkeypatch.setattr(service_module, "build_check_queue", AsyncMock(return_value=[]))

    summary = await run_daily_job(db_factory)
    assert summary.message == "job completed"


@pytest.mark.anyio
async def test_service_helpers_cover_time_count_ruolo_and_record_run(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 5)
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", None)

    reference = datetime(2026, 7, 8, 10, 0, tzinfo=UTC)
    start_utc, end_utc = _local_day_bounds_utc(reference)
    assert start_utc < end_utc
    assert await _count_calls_for_local_day(db_session, reference) == 0

    with pytest.raises(ValueError, match="Nessuna annualita ruolo"):
        await _resolve_ruolo_year(db_session)

    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    subject = _create_person_subject(db_session, "RSSMRA80A01H501H", data_nascita=date(1940, 1, 1))
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject.id)

    await _record_job_run(
        db_session,
        started_at=reference,
        status="completed",
        configured_daily_limit=10,
        hard_daily_limit=20,
        daily_calls_before=2,
        calls_used=3,
        subjects_selected=1,
        subjects_processed=1,
        deceased_found=0,
        errors=0,
        notes="ok",
    )
    run = db_session.execute(select(AnprJobRun).order_by(AnprJobRun.id.desc())).scalar_one()
    assert run.daily_calls_after == 5


@pytest.mark.anyio
async def test_run_daily_job_returns_disabled_summary_without_processing() -> None:
    class FakeDb:
        async def close(self) -> None:
            return None

    db = FakeDb()

    async def db_factory():
        return db

    import app.modules.utenze.anpr.service as service_module

    original_get_config = service_module.get_config

    async def fake_get_config(_db):
        return AnprSyncConfig(
            id=1,
            max_calls_per_day=100,
            job_enabled=False,
            job_cron="0 8-17 * * *",
            lookback_years=1,
            retry_not_found_days=90,
        )

    service_module.get_config = fake_get_config
    try:
        summary = await run_daily_job(db_factory)
    finally:
        service_module.get_config = original_get_config

    assert isinstance(summary, AnprJobSummary)
    assert summary.subjects_processed == 0
    assert summary.calls_used == 0
    assert summary.message == "job disabled"


@pytest.mark.anyio
async def test_run_daily_job_skips_outside_processing_window_and_persists_run(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 5, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 90)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)

    async def db_factory():
        return db_session

    summary = await run_daily_job(db_factory)
    run = db_session.execute(select(AnprJobRun).order_by(AnprJobRun.started_at.desc())).scalar_one()

    assert summary.subjects_processed == 0
    assert summary.message == "outside processing window"
    assert run.status == "outside_window"
    assert run.calls_used == 0


@pytest.mark.anyio
async def test_run_daily_job_respects_daily_cap_and_batch_size(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 3)

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 8-17 * * *", lookback_years=1, retry_not_found_days=90)
    db_session.add(config)
    db_session.commit()

    subject_one = _create_person_subject(db_session, "RSSAAA80A01H501U", data_nascita=date(1940, 1, 1), anpr_id="ANPR-1")
    subject_two = _create_person_subject(db_session, "RSSBBB80A01H501U", data_nascita=date(1950, 1, 1), anpr_id="ANPR-2")
    subject_three = _create_person_subject(db_session, "RSSCCC80A01H501U", data_nascita=date(1960, 1, 1), anpr_id="ANPR-3")
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_one.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_two.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_three.id)

    db_session.add(
        AnprCheckLog(
            subject_id=subject_one.id,
            call_type="C004",
            id_operazione_client="preexisting",
            id_operazione_anpr="preexisting",
            esito="alive",
            error_detail=None,
            data_decesso_anpr=None,
            triggered_by="job",
            created_at=frozen_now,
        )
    )
    db_session.commit()

    async def fake_get_config(_db):
        return config

    class FakeClient:
        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:
            return C004Result(
                success=True,
                esito="alive",
                data_decesso=None,
                id_operazione_anpr=f"op-{anpr_id}",
                error_detail=None,
                id_operazione_client=f"cli-{key}",
                raw_response={},
            )

    class FakeAuth:
        pass

    monkeypatch.setattr(service_module, "get_config", fake_get_config)
    monkeypatch.setattr("app.modules.utenze.anpr.auth.PdndAuthManager", FakeAuth)
    monkeypatch.setattr(service_module, "AnprClient", lambda auth: FakeClient())

    async def db_factory():
        return db_session

    summary = await run_daily_job(db_factory)
    runs = db_session.scalars(select(AnprJobRun).order_by(AnprJobRun.started_at.desc())).all()

    assert summary.subjects_processed == 2
    assert summary.calls_used == 2
    assert len(runs) == 1
    assert runs[0].daily_calls_before == 1
    assert runs[0].daily_calls_after == 3
    assert runs[0].subjects_selected == 2


@pytest.mark.anyio
async def test_run_daily_job_second_run_same_day_stops_at_limit_reached(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 2)

    subject_one = _create_person_subject(db_session, "RUNONE80A01H501U", data_nascita=date(1940, 1, 1), anpr_id="ANPR-1")
    subject_two = _create_person_subject(db_session, "RUNTWO80A01H501U", data_nascita=date(1950, 1, 1), anpr_id="ANPR-2")
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_one.id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_two.id)

    async def fake_get_config(_db):
        return AnprSyncConfig(
            id=1,
            max_calls_per_day=10,
            job_enabled=True,
            job_cron="0 8-17 * * *",
            lookback_years=1,
            retry_not_found_days=90,
        )

    class FakeClient:
        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:
            return C004Result(
                success=True,
                esito="alive",
                data_decesso=None,
                id_operazione_anpr=f"op-{anpr_id}",
                error_detail=None,
                id_operazione_client=f"cli-{key}",
                raw_response={},
            )

    class FakeAuth:
        pass

    monkeypatch.setattr(service_module, "get_config", fake_get_config)
    monkeypatch.setattr("app.modules.utenze.anpr.auth.PdndAuthManager", FakeAuth)
    monkeypatch.setattr(service_module, "AnprClient", lambda auth: FakeClient())

    async def db_factory():
        return db_session

    first_summary = await run_daily_job(db_factory)
    second_summary = await run_daily_job(db_factory)
    runs = db_session.scalars(select(AnprJobRun).order_by(AnprJobRun.started_at.asc())).all()

    assert first_summary.calls_used == 2
    assert second_summary.calls_used == 0
    assert second_summary.message == "daily call limit reached"
    assert len(runs) == 2
    assert runs[0].status == "completed"
    assert runs[0].daily_calls_after == 2
    assert runs[1].status == "limit_reached"
    assert runs[1].daily_calls_before == 2
    assert runs[1].daily_calls_after == 2


@pytest.mark.anyio
async def test_run_daily_job_continues_after_unexpected_subject_exception(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(service_module.settings, "anpr_job_timezone", "Europe/Rome")
    monkeypatch.setattr(service_module.settings, "anpr_job_start_hour", 8)
    monkeypatch.setattr(service_module.settings, "anpr_job_end_hour", 18)
    monkeypatch.setattr(service_module.settings, "anpr_job_ruolo_year", 2025)
    monkeypatch.setattr(service_module.settings, "anpr_job_batch_size", 2)
    monkeypatch.setattr(service_module.settings, "anpr_daily_call_hard_limit", 10)

    subject_one = _create_person_subject(db_session, "ERRCNT80A01H501U", data_nascita=date(1940, 1, 1), anpr_id="ANPR-1")
    subject_two = _create_person_subject(db_session, "ERRCNT80A01H501V", data_nascita=date(1950, 1, 1), anpr_id="ANPR-2")
    subject_one_id = subject_one.id
    subject_two_id = subject_two.id
    ruolo_2025 = _create_ruolo_job(db_session, anno_tributario=2025)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_one_id)
    _add_ruolo_row(db_session, batch_id=ruolo_2025.id, anno_tributario=2025, subject_id=subject_two_id)

    async def fake_get_config(_db):
        return AnprSyncConfig(
            id=1,
            max_calls_per_day=20,
            job_enabled=True,
            job_cron="0 8-17 * * *",
            lookback_years=1,
            retry_not_found_days=90,
        )

    class FakeClient:
        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:
            return C004Result(
                success=True,
                esito="alive",
                data_decesso=None,
                id_operazione_anpr=f"op-{anpr_id}",
                error_detail=None,
                id_operazione_client=f"cli-{key}",
                raw_response={},
            )

    class FakeAuth:
        pass

    original_sync_single_subject = service_module.sync_single_subject

    async def fake_sync_single_subject(subject_id: str, db, triggered_by: str, auth, client):
        if subject_id == str(subject_one_id):
            raise RuntimeError("boom")
        return await original_sync_single_subject(subject_id, db, triggered_by, auth, client)

    monkeypatch.setattr(service_module, "get_config", fake_get_config)
    monkeypatch.setattr("app.modules.utenze.anpr.auth.PdndAuthManager", FakeAuth)
    monkeypatch.setattr(service_module, "AnprClient", lambda auth: FakeClient())
    monkeypatch.setattr(service_module, "sync_single_subject", fake_sync_single_subject)

    async def db_factory():
        return db_session

    summary = await run_daily_job(db_factory)
    db_session.expire_all()
    first_person = db_session.get(AnagraficaPerson, subject_one_id)
    second_person = db_session.get(AnagraficaPerson, subject_two_id)
    joberr_logs = db_session.scalars(
        select(AnprCheckLog).where(AnprCheckLog.subject_id == subject_one_id, AnprCheckLog.call_type == "JOBERR")
    ).all()

    assert summary.subjects_processed == 1
    assert summary.errors == 1
    assert first_person is not None
    assert first_person.stato_anpr == "error"
    assert second_person is not None
    assert second_person.stato_anpr == "alive"
    assert len(joberr_logs) == 1
    assert "boom" in (joberr_logs[0].error_detail or "")


def test_get_stats_reports_deceased_kpis(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utenze_router.settings, "anpr_job_timezone", "Europe/Rome")

    alive_subject = _create_person_subject(db_session, "STATSALV0000001", data_nascita=date(1960, 1, 1))
    recent_subject = _create_person_subject(db_session, "STATSREC0000001", data_nascita=date(1950, 1, 1))
    old_subject = _create_person_subject(db_session, "STATSOLD0000001", data_nascita=date(1940, 1, 1))

    db_session.add_all(
        [
            AnprCheckLog(
                subject_id=recent_subject.id,
                call_type="C004",
                id_operazione_client="kpi-recent",
                id_operazione_anpr="kpi-recent",
                esito="deceased",
                error_detail=None,
                data_decesso_anpr=date(2026, 5, 14),
                triggered_by="job",
                created_at=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
            ),
            AnprCheckLog(
                subject_id=old_subject.id,
                call_type="C004",
                id_operazione_client="kpi-month",
                id_operazione_anpr="kpi-month",
                esito="deceased",
                error_detail=None,
                data_decesso_anpr=date(2026, 5, 1),
                triggered_by="job",
                created_at=datetime(2026, 5, 2, 9, 0, tzinfo=UTC),
            ),
            AnprCheckLog(
                subject_id=alive_subject.id,
                call_type="C004",
                id_operazione_client="kpi-year",
                id_operazione_anpr="kpi-year",
                esito="deceased",
                error_detail=None,
                data_decesso_anpr=date(2026, 2, 1),
                triggered_by="job",
                created_at=datetime(2026, 2, 3, 9, 0, tzinfo=UTC),
            ),
            AnprCheckLog(
                subject_id=alive_subject.id,
                call_type="C004",
                id_operazione_client="kpi-ignore",
                id_operazione_anpr="kpi-ignore",
                esito="alive",
                error_detail=None,
                data_decesso_anpr=None,
                triggered_by="job",
                created_at=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
            return current if tz is None else current.astimezone(tz)

    monkeypatch.setattr(utenze_router, "datetime", FrozenDateTime)

    stats = utenze_router.get_stats(None, None, db_session)

    assert stats.deceased_updates_last_24h == 1
    assert stats.deceased_updates_current_month == 2
    assert stats.deceased_updates_current_year == 3


@pytest.mark.anyio
async def test_lookup_anpr_by_codice_fiscale_runs_c030_then_c004() -> None:
    class FakeClient:
        async def c030_get_anpr_id(self, cf: str, key: str) -> C030Result:
            assert cf == "RSSMRA80A01H501U"
            assert key == "preview"
            return C030Result(
                success=True,
                anpr_id="ANPR-X",
                id_operazione_anpr="op1",
                esito="anpr_id_found",
                error_detail=None,
                id_operazione_client="cli1",
            )

        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:
            assert anpr_id == "ANPR-X"
            return C004Result(
                success=True,
                esito="alive",
                data_decesso=None,
                id_operazione_anpr="op2",
                error_detail=None,
                id_operazione_client="cli2",
                raw_response=None,
            )

    result = await lookup_anpr_by_codice_fiscale("rss mra80a01 h501 u", client=FakeClient())
    assert result.success is True
    assert result.anpr_id == "ANPR-X"
    assert result.stato_anpr == "alive"
    assert result.calls_made == 2


@pytest.mark.anyio
async def test_lookup_anpr_by_codice_fiscale_returns_after_c030_not_found_single_call() -> None:
    class FakeClient:
        async def c030_get_anpr_id(self, cf: str, key: str) -> C030Result:
            del cf, key
            return C030Result(
                success=False,
                anpr_id=None,
                id_operazione_anpr=None,
                esito="not_found",
                error_detail=None,
                id_operazione_client="cli",
            )

        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:  # pragma: no cover - must not run
            raise AssertionError()

    result = await lookup_anpr_by_codice_fiscale("FOO", client=FakeClient())
    assert result.success is True
    assert result.stato_anpr == "not_found_anpr"
    assert result.calls_made == 1


@pytest.mark.anyio
async def test_lookup_anpr_by_codice_fiscale_returns_error_after_c004_failure() -> None:
    class FakeClient:
        async def c030_get_anpr_id(self, cf: str, key: str) -> C030Result:
            assert cf == "RSSMRA80A01H501U"
            assert key == "preview"
            return C030Result(
                success=True,
                anpr_id="ANPR-X",
                id_operazione_anpr="op1",
                esito="anpr_id_found",
                error_detail=None,
                id_operazione_client="cli1",
            )

        async def c004_check_death(self, anpr_id: str, key: str) -> C004Result:
            assert anpr_id == "ANPR-X"
            assert key == "preview"
            return C004Result(
                success=False,
                esito="error",
                data_decesso=None,
                id_operazione_anpr="op2",
                error_detail="EN148 | E | Devi specificare la sezione verifica dati decesso per questo caso d'uso",
                id_operazione_client="cli2",
                raw_response=None,
            )

    result = await lookup_anpr_by_codice_fiscale("RSSMRA80A01H501U", client=FakeClient())

    assert result.success is False
    assert result.anpr_id == "ANPR-X"
    assert result.calls_made == 2
    assert "EN148" in result.message
