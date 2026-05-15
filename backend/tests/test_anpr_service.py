from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catasto_phase1 import CatImportBatch, CatUtenzaIrrigua
from app.modules.utenze.anpr.client import C004Result, C030Result
from app.modules.utenze.anpr.models import AnprCheckLog, AnprSyncConfig
from app.modules.utenze.anpr.schemas import AnprSyncConfigUpdate
from app.modules.utenze.anpr.service import (
    AnprJobSummary,
    _build_result_message,
    _map_person_status,
    build_check_queue,
    lookup_anpr_by_codice_fiscale,
    run_daily_job,
    sync_single_subject,
    update_config,
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
        )
    )
    db_session.commit()
    return subject


def _create_import_batch(db_session: Session, *, anno_campagna: int) -> CatImportBatch:
    batch = CatImportBatch(
        filename=f"utenze-{anno_campagna}.csv",
        tipo="utenze",
        anno_campagna=anno_campagna,
        status="completed",
        righe_totali=1,
        righe_importate=1,
    )
    db_session.add(batch)
    db_session.commit()
    return batch


def _add_utenza_row(db_session: Session, *, batch_id, anno_campagna: int, codice_fiscale: str) -> None:
    db_session.add(
        CatUtenzaIrrigua(
            import_batch_id=batch_id,
            anno_campagna=anno_campagna,
            codice_fiscale=codice_fiscale,
            codice_fiscale_raw=codice_fiscale,
            anomalia_cf_mancante=False,
            anomalia_cf_invalido=False,
            anomalia_superficie=False,
            anomalia_comune_invalido=False,
            anomalia_particella_assente=False,
            anomalia_imponibile=False,
            anomalia_importi=False,
            esente_0648=False,
        )
    )
    db_session.commit()


@pytest.mark.anyio
async def test_build_check_queue_priority_order(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.utenze.anpr.service as service_module

    frozen_now = datetime(2026, 4, 30, 10, 0, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz is None else frozen_now.astimezone(tz)

    monkeypatch.setattr(service_module, "datetime", FrozenDateTime)

    config = AnprSyncConfig(id=1, max_calls_per_day=10, job_enabled=True, job_cron="0 2 * * *", lookback_years=1, retry_not_found_days=90)

    prev_only = _create_person_subject(db_session, "PRVONLY000000001", data_nascita=date(1990, 1, 1))
    current_only = _create_person_subject(db_session, "CURONLY000000001", data_nascita=date(1980, 1, 1))
    both_years = _create_person_subject(db_session, "BOTHYRS00000001", data_nascita=date(1970, 1, 1))

    batch_prev = _create_import_batch(db_session, anno_campagna=2025)
    batch_current = _create_import_batch(db_session, anno_campagna=2026)

    _add_utenza_row(db_session, batch_id=batch_prev.id, anno_campagna=2025, codice_fiscale="PRVONLY000000001")
    _add_utenza_row(db_session, batch_id=batch_current.id, anno_campagna=2026, codice_fiscale="CURONLY000000001")
    _add_utenza_row(db_session, batch_id=batch_prev.id, anno_campagna=2025, codice_fiscale="BOTHYRS00000001")
    _add_utenza_row(db_session, batch_id=batch_current.id, anno_campagna=2026, codice_fiscale="BOTHYRS00000001")

    queue = await build_check_queue(db_session, config)

    assert queue[0] == str(prev_only.id)
    assert set(queue) == {str(prev_only.id), str(current_only.id), str(both_years.id)}


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
            job_cron="0 2 * * *",
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
