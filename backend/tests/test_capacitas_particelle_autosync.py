from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatComune, CatParticella
from app.modules.elaborazioni import capacitas_particelle_autosync_scheduler as scheduler_module
from app.modules.elaborazioni.capacitas.apps.involture.parsers import parse_certificato_html
from app.modules.elaborazioni.capacitas.models import (
    CapacitasDomandeIrrigueSyncJobCreateRequest,
    CapacitasParticelleSyncJobCreateRequest,
)
from app.modules.elaborazioni.capacitas_particelle_autosync_policy import (
    CapacitasParticelleAutoSyncJobRequest,
    parse_particelle_job_payload,
)
from app.services.elaborazioni_capacitas_particelle_sync import (
    ParticelleSyncPolicy,
    _select_particelle_for_job,
)


def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "capacitas_particelle_autosync_enabled": True,
        "capacitas_particelle_autosync_interval_minutes": 5,
        "capacitas_particelle_autosync_credential_id": 7,
        "capacitas_particelle_autosync_batch_size": 100,
        "capacitas_particelle_autosync_refresh_days": 30,
        "capacitas_particelle_autosync_transient_retry_hours": 1,
        "capacitas_particelle_autosync_failed_retry_hours": 24,
    }
    for name, value in values.items():
        monkeypatch.setattr(scheduler_module.settings, name, value)


def test_run_particelle_autosync_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler_module.settings, "capacitas_particelle_autosync_enabled", False)
    db = MagicMock()

    assert scheduler_module.run_particelle_autosync(db) == 0
    db.scalar.assert_not_called()


def test_run_particelle_autosync_requires_fixed_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(
        scheduler_module.settings, "capacitas_particelle_autosync_credential_id", None
    )

    assert scheduler_module.run_particelle_autosync(MagicMock()) == 0


def test_run_particelle_autosync_skips_unavailable_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: False)

    assert scheduler_module.run_particelle_autosync(MagicMock()) == 0


def test_run_particelle_autosync_skips_active_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)
    db = MagicMock()
    db.scalar.return_value = 42

    assert scheduler_module.run_particelle_autosync(db) == 0


def test_run_particelle_autosync_skips_without_due_parcel(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)
    db = MagicMock()
    db.scalar.side_effect = [None, None]

    assert scheduler_module.run_particelle_autosync(db) == 0


def test_run_particelle_autosync_queues_bounded_full_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setattr(scheduler_module, "has_available_credential", lambda _db, _id: True)
    db = MagicMock()
    db.scalar.side_effect = [None, "parcel-id"]
    captured: list[tuple[object, object, object]] = []

    def create_job(current_db, *, requested_by_user_id, credential_id, payload):
        captured.append((current_db, requested_by_user_id, payload))
        assert credential_id == 7
        return SimpleNamespace(id=91)

    monkeypatch.setattr(scheduler_module, "create_particelle_sync_job", create_job)

    assert scheduler_module.run_particelle_autosync(db) == 91
    _, requested_by_user_id, payload = captured[0]
    assert requested_by_user_id is None
    assert payload.trigger == "autosync"
    assert payload.limit == 100
    assert payload.fetch_certificati is True
    assert payload.fetch_details is True
    assert payload.parallel_workers == 1
    assert payload.refresh_days == 30


@pytest.mark.anyio
async def test_register_particelle_autosync_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    scheduler = AsyncIOScheduler(timezone="UTC")

    await scheduler_module.register_particelle_autosync_scheduler(scheduler, lambda: None)

    job = scheduler.get_job("capacitas_particelle_autosync")
    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True


@pytest.mark.anyio
async def test_register_particelle_autosync_scheduler_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scheduler_module.settings, "capacitas_particelle_autosync_enabled", False)
    scheduler = AsyncIOScheduler(timezone="UTC")

    await scheduler_module.register_particelle_autosync_scheduler(scheduler, lambda: None)

    assert scheduler.get_job("capacitas_particelle_autosync") is None


@pytest.mark.anyio
async def test_job_wrapper_closes_generator_database(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()

    def get_db():
        yield db

    monkeypatch.setattr(scheduler_module, "run_particelle_autosync", lambda current_db: 0)

    await scheduler_module._run_job_wrapper(get_db)

    db.close.assert_called_once_with()


@pytest.mark.anyio
async def test_job_wrapper_closes_async_database_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AsyncDb:
        closed = False

        async def close(self) -> None:
            self.closed = True

    db = AsyncDb()

    def fail(_db) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(scheduler_module, "run_particelle_autosync", fail)

    await scheduler_module._run_job_wrapper(lambda: db)

    assert db.closed is True


@pytest.mark.anyio
async def test_job_wrapper_accepts_database_without_close(monkeypatch: pytest.MonkeyPatch) -> None:
    db = SimpleNamespace()
    monkeypatch.setattr(scheduler_module, "run_particelle_autosync", lambda current_db: 0)

    await scheduler_module._run_job_wrapper(lambda: db)


def test_capacitas_domande_payload_still_requires_a_search_source() -> None:
    with pytest.raises(ValueError, match="Indicare almeno una ricerca"):
        CapacitasDomandeIrrigueSyncJobCreateRequest()


def test_particelle_payload_parser_preserves_autosync_policy() -> None:
    autosync = parse_particelle_job_payload(
        {
            "trigger": "autosync",
            "refresh_days": 30,
            "transient_retry_hours": 1,
            "failed_retry_hours": 24,
        }
    )
    manual = parse_particelle_job_payload(None)

    assert isinstance(autosync, CapacitasParticelleAutoSyncJobRequest)
    assert autosync.refresh_days == 30
    assert type(manual) is CapacitasParticelleSyncJobCreateRequest


def test_certificato_parser_stops_utenza_status_before_terreni_without_owner() -> None:
    certificato = parse_certificato_html(
        """
        <pre id="Capacitas_ContentMain_ContentCertificatoPre">
          <div>PARTITA: 014000391/14/00000 - CABRAS - STATO: Iscrivibile a ruolo</div>
          <div>UTENZA: E003369334 - STATO CNC: non iscritta a ruolo</div>
          <div>TERRENI 4 S DIS FOG MAPP SUB SUPERFICIE BAC. IDRAUL QUALITA CL DIV</div>
          <div class="rpt-riga rpt-riga-terreno">6 573 D 113 0 1010 PASCOLO</div>
        </pre>
        """
    )

    assert certificato.utenza_status == "non iscritta a ruolo"


def test_autosync_policy_selects_status_specific_due_dates() -> None:
    engine = create_engine("sqlite://")
    CatComune.__table__.create(engine)
    CatParticella.__table__.create(engine)
    now = datetime.now(UTC)
    cases = (
        (None, None, None, "1", None, True),
        ("synced", now - timedelta(days=31), None, "2", None, True),
        ("synced", now - timedelta(days=29), None, "3", None, False),
        ("skipped", now - timedelta(days=31), None, "4", None, True),
        ("failed", now - timedelta(hours=2), "NOSessione scaduta", "5", None, True),
        ("failed", now - timedelta(days=2), "Particella 1/6 non trovata", "6", None, False),
        ("failed", now - timedelta(hours=25), "Errore inatteso", "7", None, True),
        (None, None, None, "", None, False),
        ("synced", None, None, "8", None, True),
        ("failed", None, "Errore inatteso", "9", None, True),
        ("failed", now - timedelta(hours=2), "Errore di connessione", "10", None, True),
        ("synced", now - timedelta(days=31), None, "11", "frazione_ambigua", False),
    )

    with Session(engine) as db:
        comune = CatComune(nome_comune="Uras", codice_catastale="L496", cod_comune_capacitas=289)
        db.add(comune)
        rows = []
        expected_ids = set()
        for index, (status, synced_at, error, foglio, anomaly_type, _expected) in enumerate(
            cases, start=1
        ):
            row = CatParticella(
                comune=comune,
                cod_comune_capacitas=289,
                nome_comune="Uras",
                foglio=foglio,
                particella=f"autosync-{index}",
                is_current=True,
                suppressed=False,
                capacitas_last_sync_status=status,
                capacitas_last_sync_at=synced_at,
                capacitas_last_sync_error=error,
                capacitas_anomaly_type=anomaly_type,
            )
            db.add(row)
            rows.append(row)
        db.commit()
        for row, case in zip(rows, cases, strict=True):
            if case[-1]:
                expected_ids.add(row.id)

        selected = _select_particelle_for_job(
            db,
            payload=CapacitasParticelleAutoSyncJobRequest(
                only_due=True,
                limit=20,
                refresh_days=30,
                transient_retry_hours=1,
                failed_retry_hours=24,
            ),
            policy=ParticelleSyncPolicy(False, 900, now, 72, 1, 1),
        )

        assert {row.id for row in selected} == expected_ids
        assert selected[0].capacitas_last_sync_status is None

        manual_selected = _select_particelle_for_job(
            db,
            payload=CapacitasParticelleSyncJobCreateRequest(only_due=True),
            policy=ParticelleSyncPolicy(False, 900, now - timedelta(days=30), 72, 1, 1),
        )

        assert rows[0] in manual_selected
        assert rows[1] in manual_selected
        assert rows[2] not in manual_selected

        all_selected = _select_particelle_for_job(
            db,
            payload=CapacitasParticelleSyncJobCreateRequest(only_due=False),
            policy=ParticelleSyncPolicy(False, 900, now, 72, 1, 1),
        )

        assert rows[2] in all_selected
