"""Characterization of the Bonifica background orchestrator (R113).

Pins entity dispatch, client construction, commit sequencing, partial-failure
continuation, bootstrap failure semantics, invalid-uuid re-raise and nested
resource cleanup of ``_run_bonifica_sync_background``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.bonifica_oristanese import BonificaOristaneseCredential
from app.models.wc_sync_job import WCSyncJob
from app.modules.accessi.sync_org_charts import WhiteOrgChartsSyncResult
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaSyncRunRequest
from app.modules.inventory.services import WhiteWarehouseSyncResult
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.operazioni.services.sync_areas import WhiteAreasSyncResult
from app.modules.operazioni.services.sync_operators import WhiteOperatorsSyncResult
from app.modules.operazioni.services.sync_report_types import WhiteReportTypesSyncResult
from app.modules.operazioni.services.sync_vehicles import WhiteVehiclesSyncResult
from app.modules.operazioni.services.sync_white import WhiteReportsSyncResult
from app.modules.utenze.services.sync_consorziati import WhiteConsorziatiSyncResult
from app.services import elaborazioni_bonifica_sync as sync_service
from app.services.catasto_credentials import get_credential_fernet

CLIENT_CLASS_NAMES = (
    "BonificaAreasClient",
    "BonificaReportTypesClient",
    "BonificaReportsClient",
    "BonificaVehiclesClient",
    "BonificaRefuelsClient",
    "BonificaTakenChargeClient",
    "BonificaUsersClient",
    "BonificaWarehouseRequestsClient",
    "BonificaOrgChartsClient",
)
USER_ID = 7
DAY = date(2026, 3, 10)
WINDOW = {"date_from": DAY, "date_to": DAY + timedelta(days=2)}
# entity -> (client class, fetch method, fetch kwargs, sync service, sync kwargs, counters)
DISPATCH = {
    "report_types": (
        "BonificaReportTypesClient",
        "fetch_report_types",
        {},
        "sync_white_report_types",
        ("db", "rows"),
        (11, 12),
    ),
    "reports": (
        "BonificaReportsClient",
        "fetch_reports",
        WINDOW,
        "sync_white_reports",
        ("current_user", "db", "rows"),
        (21, 22),
    ),
    "vehicles": (
        "BonificaVehiclesClient",
        "fetch_vehicles",
        {},
        "sync_white_vehicles",
        ("current_user", "db", "rows"),
        (31, 32),
    ),
    "refuels": (
        "BonificaRefuelsClient",
        "fetch_refuels_for_vehicle_codes",
        {**WINDOW, "vehicle_codes": ["AB123", "CD456"]},
        "sync_white_refuels",
        ("current_user", "db", "rows"),
        (41, 42),
    ),
    "taken_charge": (
        "BonificaTakenChargeClient",
        "fetch_taken_charge",
        WINDOW,
        "sync_white_taken_charge",
        ("current_user", "db", "rows"),
        (51, 52),
    ),
    "users": (
        "BonificaUsersClient",
        "fetch_users",
        {},
        "sync_white_operators",
        ("db", "rows"),
        (61, 62),
    ),
    "areas": (
        "BonificaAreasClient",
        "fetch_areas",
        {},
        "sync_white_areas",
        ("db", "rows"),
        (71, 72),
    ),
    "warehouse_requests": (
        "BonificaWarehouseRequestsClient",
        "fetch_warehouse_requests",
        WINDOW,
        "sync_white_warehouse_requests",
        ("db", "rows"),
        (81, 82),
    ),
    "org_charts": (
        "BonificaOrgChartsClient",
        "fetch_org_charts",
        {},
        "sync_white_org_charts_to_canonical",
        ("db", "rows", "user_id"),
        (91, 92),
    ),
    "consorziati": (
        "BonificaUsersClient",
        "fetch_consorziati",
        {},
        "sync_white_consorziati",
        ("db", "rows"),
        (101, 102),
    ),
}


def make_result(entity: str, synced: int, skipped: int):
    errors = ["warn"]
    if entity == "reports":
        return WhiteReportsSyncResult(synced, skipped, errors, 0)
    if entity == "org_charts":
        return WhiteOrgChartsSyncResult(synced, skipped, 0, errors)
    if entity in {"vehicles", "refuels", "taken_charge"}:
        values = {"vehicles": [0, 0], "refuels": [0, 0], "taken_charge": [0, 0]}
        values[entity] = [synced, skipped]
        return WhiteVehiclesSyncResult(
            *values["vehicles"], *values["refuels"], *values["taken_charge"], errors
        )
    plain = {
        "report_types": WhiteReportTypesSyncResult,
        "users": WhiteOperatorsSyncResult,
        "areas": WhiteAreasSyncResult,
        "warehouse_requests": WhiteWarehouseSyncResult,
        "consorziati": WhiteConsorziatiSyncResult,
    }
    return plain[entity](synced, skipped, errors)


@pytest.fixture
def dispatch_db(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            ApplicationUser.__table__,
            BonificaOristaneseCredential.__table__,
            WCSyncJob.__table__,
            Vehicle.__table__,
        ],
    )
    monkeypatch.setattr(
        sync_service.settings,
        "credential_master_key",
        "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=",
    )
    get_credential_fernet.cache_clear()
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            ApplicationUser(
                id=USER_ID,
                username="dispatch-admin",
                email="dispatch-admin@example.local",
                password_hash="unused",
                role="super_admin",
                is_active=True,
            )
        )
        session.add(
            BonificaOristaneseCredential(
                label="test",
                login_identifier="dispatch@example.local",
                password_encrypted=get_credential_fernet().encrypt(b"pw").decode(),
            )
        )
        session.commit()
        monkeypatch.setattr(sync_service, "SessionLocal", lambda: session)
        yield session
    get_credential_fernet.cache_clear()
    engine.dispose()


class Harness:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, session: Session):
        self.monkeypatch = monkeypatch
        self.session = session
        self.events: list = []
        self.managers: list = []
        self.fetch_failures: dict[str, Exception] = {}
        self.sync_failures: dict[str, Exception] = {}
        self.ctor_failure: str | None = None
        self.login_failure: Exception | None = None
        self.close_failure: Exception | None = None
        self._install()

    def _install(self) -> None:
        harness = self
        events = self.events
        original_close = self.session.close

        def close_session():
            events.append("db.close")
            original_close()

        self.monkeypatch.setattr(self.session, "close", close_session)

        class PortalSession:
            def __init__(self, **kwargs):
                assert kwargs == {
                    "login_identifier": "dispatch@example.local",
                    "password": "pw",
                    "remember_me": False,
                }
                harness.managers.append(self)

            async def login(self):
                events.append("login")
                if harness.login_failure is not None:
                    raise harness.login_failure
                return SimpleNamespace(authenticated_url="https://portal.example.local/home")

            async def close(self):
                events.append("manager.close")
                if harness.close_failure is not None:
                    raise harness.close_failure

        self.monkeypatch.setattr(sync_service, "BonificaOristaneseSessionManager", PortalSession)

        def make_client(class_name: str):
            class FakeClient:
                def __init__(self, manager):
                    assert manager is harness.managers[-1]
                    events.append(("construct", class_name))
                    if harness.ctor_failure == class_name:
                        raise RuntimeError(f"ctor {class_name}")

                def __getattr__(self, method):
                    async def fetch(**kwargs):
                        events.append(("fetch", class_name, method, kwargs))
                        entity = next(
                            name
                            for name, spec in DISPATCH.items()
                            if spec[0] == class_name and spec[1] == method
                        )
                        if entity in harness.fetch_failures:
                            raise harness.fetch_failures[entity]
                        return [f"row-{entity}"], 7

                    return fetch

            return FakeClient

        for class_name in CLIENT_CLASS_NAMES:
            self.monkeypatch.setattr(sync_service, class_name, make_client(class_name))

        for entity, (_, _, _, service_name, _, counters) in DISPATCH.items():

            def synchronize(_entity=entity, _service=service_name, _counters=counters, **kwargs):
                events.append(("sync", _service, kwargs))
                if _entity in harness.sync_failures:
                    raise harness.sync_failures[_entity]
                return make_result(_entity, *_counters)

            self.monkeypatch.setattr(sync_service, service_name, synchronize)

        original_window = sync_service._resolve_date_window_from_job

        def resolve_window(job, entity):
            events.append(("window", entity))
            return original_window(job, entity)

        self.monkeypatch.setattr(sync_service, "_resolve_date_window_from_job", resolve_window)

        def vehicle_codes(db):
            assert db is self.session
            events.append("vehicle_codes")
            return ["AB123", "CD456"]

        self.monkeypatch.setattr(sync_service, "_list_vehicle_refuel_search_codes", vehicle_codes)

        def record_commit(committed_session):
            jobs = sorted(
                (
                    (job.entity, job.status, (job.params_json or {}).get("source_total"))
                    for job in committed_session.identity_map.values()
                    if isinstance(job, WCSyncJob)
                ),
            )
            events.append(("commit", tuple(jobs)))

        event.listen(self.session, "after_commit", record_commit)

    def add_jobs(self, entities: list[str], params: dict | None = None) -> dict[str, WCSyncJob]:
        jobs = {
            entity: WCSyncJob(
                entity=entity,
                status="queued",
                triggered_by=USER_ID,
                params_json=dict(
                    params
                    if params is not None
                    else {
                        "date_from": WINDOW["date_from"].isoformat(),
                        "date_to": WINDOW["date_to"].isoformat(),
                        "keep": "yes",
                    }
                ),
            )
            for entity in entities
        }
        self.session.add_all(jobs.values())
        self.session.commit()
        self.events.clear()
        return jobs

    def run(self, entities, job_ids_by_entity: dict[str, str], user_id: int = USER_ID) -> None:
        asyncio.run(
            sync_service._run_bonifica_sync_background(
                triggered_by_user_id=user_id,
                request=BonificaSyncRunRequest(entities=entities),
                job_ids_by_entity=job_ids_by_entity,
            )
        )

    def stored_jobs(self) -> dict[str, WCSyncJob]:
        with Session(self.session.bind) as verification:
            return {job.entity: job for job in verification.scalars(select(WCSyncJob))}

    def stored_credential(self) -> BonificaOristaneseCredential:
        with Session(self.session.bind) as verification:
            return verification.scalar(select(BonificaOristaneseCredential))

    def calls(self, kind: str) -> list:
        return [item for item in self.events if isinstance(item, tuple) and item[0] == kind]


def ids(jobs: dict[str, WCSyncJob]) -> dict[str, str]:
    return {entity: str(job.id) for entity, job in jobs.items()}


@pytest.mark.parametrize("entity", list(DISPATCH))
def test_each_entity_dispatches_fetch_snapshot_sync_and_finalize_in_order(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch, entity: str
):
    client_name, method, fetch_kwargs, service_name, sync_keys, counters = DISPATCH[entity]
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs([entity])
    harness.run([entity], ids(jobs))

    construct = [("construct", name) for name in CLIENT_CLASS_NAMES]
    prefix = [
        "login",
        ("commit", ((entity, "queued", None),)),
        *construct,
        ("commit", ((entity, "running", None),)),
    ]
    assert harness.events[: len(prefix)] == prefix
    body = harness.events[len(prefix) :]
    expected_pre_fetch: list = []
    if entity in sync_service.DATE_AWARE_SYNC_ENTITIES:
        expected_pre_fetch.append(("window", entity))
    if entity == "refuels":
        expected_pre_fetch.append("vehicle_codes")
    assert body[: len(expected_pre_fetch)] == expected_pre_fetch
    body = body[len(expected_pre_fetch) :]
    assert body[0] == ("fetch", client_name, method, fetch_kwargs)
    assert body[1] == ("commit", ((entity, "running", 7),))
    sync_event = body[2]
    assert sync_event[:2] == ("sync", service_name)
    assert tuple(sorted(sync_event[2])) == sync_keys
    assert sync_event[2]["db"] is dispatch_db
    assert sync_event[2]["rows"] == [f"row-{entity}"]
    if "current_user" in sync_keys:
        assert sync_event[2]["current_user"].id == USER_ID
    if "user_id" in sync_keys:
        assert sync_event[2]["user_id"] == USER_ID
    assert body[3:] == [("commit", ((entity, "completed", 7),)), "manager.close", "db.close"]

    stored = harness.stored_jobs()[entity]
    assert (stored.records_synced, stored.records_skipped, stored.records_errors) == (
        *counters,
        1,
    )
    assert stored.error_detail == "warn"
    assert stored.params_json["keep"] == "yes"
    assert stored.params_json["source_total"] == 7
    assert stored.params_json["report_summary"]["outcome"] == "completed"
    assert stored.finished_at is not None
    assert harness.stored_credential().last_authenticated_url == "https://portal.example.local/home"


def test_all_entities_run_in_canonical_order_with_clients_built_once(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs(list(reversed(list(DISPATCH))))
    harness.run("all", ids(jobs))
    assert harness.calls("construct") == [("construct", name) for name in CLIENT_CLASS_NAMES]
    assert [item[1] for item in harness.calls("sync")] == [spec[3] for spec in DISPATCH.values()]
    assert {job.status for job in harness.stored_jobs().values()} == {"completed"}
    assert len(harness.managers) == 1
    assert harness.events[-2:] == ["manager.close", "db.close"]


def test_fetch_and_sync_failures_mark_only_that_job_and_continue(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    harness.fetch_failures["report_types"] = RuntimeError("fetch boom")
    harness.sync_failures["vehicles"] = ValueError("sync boom")
    jobs = harness.add_jobs(["report_types", "vehicles", "users"])
    harness.run(["users", "vehicles", "report_types"], ids(jobs))

    assert [item[1] for item in harness.calls("sync")] == [
        "sync_white_vehicles",
        "sync_white_operators",
    ]
    rt, us, ve = "report_types", "users", "vehicles"
    assert harness.calls("commit") == [
        ("commit", ((rt, "queued", None), (us, "queued", None), (ve, "queued", None))),
        ("commit", ((rt, "running", None), (us, "queued", None), (ve, "queued", None))),
        ("commit", ((rt, "failed", None), (us, "queued", None), (ve, "queued", None))),
        ("commit", ((rt, "failed", None), (us, "queued", None), (ve, "running", None))),
        ("commit", ((rt, "failed", None), (us, "queued", None), (ve, "running", 7))),
        ("commit", ((rt, "failed", None), (us, "queued", None), (ve, "failed", 7))),
        ("commit", ((rt, "failed", None), (us, "running", None), (ve, "failed", 7))),
        ("commit", ((rt, "failed", None), (us, "running", 7), (ve, "failed", 7))),
        ("commit", ((rt, "failed", None), (us, "completed", 7), (ve, "failed", 7))),
    ]
    stored = harness.stored_jobs()
    fetch_failed = stored["report_types"]
    assert (fetch_failed.status, fetch_failed.error_detail) == ("failed", "fetch boom")
    assert (
        fetch_failed.records_synced,
        fetch_failed.records_skipped,
        fetch_failed.records_errors,
    ) == (0, 0, 1)
    assert "source_total" not in fetch_failed.params_json
    assert fetch_failed.params_json["keep"] == "yes"
    assert fetch_failed.params_json["report_summary"]["outcome"] == "failed"
    assert fetch_failed.params_json["report_summary"]["error_preview"] == ["fetch boom"]
    assert fetch_failed.finished_at is not None
    sync_failed = stored["vehicles"]
    assert (sync_failed.status, sync_failed.error_detail) == ("failed", "sync boom")
    assert sync_failed.params_json["source_total"] == 7
    assert stored["users"].status == "completed"
    assert harness.stored_credential().consecutive_failures == 0
    assert harness.events[-2:] == ["manager.close", "db.close"]


def test_reversed_job_window_fails_entity_before_fetch(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs(
        ["refuels", "areas"],
        params={"date_from": "2026-03-12", "date_to": "2026-03-10"},
    )
    harness.run(["refuels", "areas"], ids(jobs))
    assert [item[1] for item in harness.calls("fetch")] == ["BonificaAreasClient"]
    assert "vehicle_codes" not in harness.events
    refuels = harness.stored_jobs()["refuels"]
    assert refuels.status == "failed"
    assert refuels.error_detail == "`date_from` non può essere successiva a `date_to`"
    assert harness.stored_jobs()["areas"].status == "completed"


def test_missing_job_id_and_unknown_job_are_skipped(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs(["areas"])
    job_ids = {
        "report_types": "",
        "users": "00000000-0000-0000-0000-000000000001",
        "areas": str(jobs["areas"].id),
    }
    harness.run(["report_types", "users", "areas", "vehicles"], job_ids)
    assert [item[1] for item in harness.calls("fetch")] == ["BonificaAreasClient"]
    assert harness.stored_jobs()["areas"].status == "completed"
    assert harness.events[-2:] == ["manager.close", "db.close"]


def test_missing_user_fails_all_jobs_without_credential_or_manager(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs(["report_types", "users"])
    job_ids = {**ids(jobs), "areas": "", "vehicles": "00000000-0000-0000-0000-000000000002"}
    harness.run(["report_types", "users", "areas", "vehicles"], job_ids, user_id=999)
    assert harness.events == [
        ("commit", (("report_types", "failed", None), ("users", "failed", None))),
        "db.close",
    ]
    for job in harness.stored_jobs().values():
        assert job.status == "failed"
        assert job.error_detail == "Utente non trovato per esecuzione sync Bonifica"
        assert (job.records_synced, job.records_skipped, job.records_errors) == (0, 0, 1)
        assert job.params_json["keep"] == "yes"
        assert job.params_json["report_summary"]["outcome"] == "failed"
        assert job.finished_at is not None
    credential = harness.stored_credential()
    assert credential.consecutive_failures == 0
    assert credential.last_error is None


def test_login_failure_marks_credential_and_all_jobs_then_closes_manager(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    harness.login_failure = RuntimeError("login refused")
    jobs = harness.add_jobs(["report_types", "users"])
    harness.run(["report_types", "users"], ids(jobs))
    assert harness.calls("construct") == []
    assert harness.events[-3:] == [
        ("commit", (("report_types", "failed", None), ("users", "failed", None))),
        "manager.close",
        "db.close",
    ]
    credential = harness.stored_credential()
    assert credential.consecutive_failures == 1
    assert credential.last_error == "login refused"
    assert {job.error_detail for job in harness.stored_jobs().values()} == {"login refused"}


def test_client_construction_failure_is_a_bootstrap_failure(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    harness.ctor_failure = "BonificaTakenChargeClient"
    jobs = harness.add_jobs(["report_types", "users"])
    harness.run(["report_types", "users"], ids(jobs))
    assert harness.calls("construct") == [("construct", name) for name in CLIENT_CLASS_NAMES[:6]]
    assert harness.calls("fetch") == []
    stored = harness.stored_jobs()
    assert {job.status for job in stored.values()} == {"failed"}
    assert {job.error_detail for job in stored.values()} == {"ctor BonificaTakenChargeClient"}
    assert harness.stored_credential().consecutive_failures == 1
    assert harness.events[-2:] == ["manager.close", "db.close"]


def test_invalid_job_uuid_reraises_after_partial_progress(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    jobs = harness.add_jobs(["report_types", "areas"])
    job_ids = {**ids(jobs), "users": "not-a-uuid"}
    with pytest.raises(ValueError):
        harness.run(["report_types", "users", "areas"], job_ids)
    assert [item[1] for item in harness.calls("fetch")] == ["BonificaReportTypesClient"]
    stored = harness.stored_jobs()
    assert stored["report_types"].status == "completed"
    assert stored["areas"].status == "queued"
    credential = harness.stored_credential()
    assert credential.consecutive_failures == 1
    assert credential.last_error == "badly formed hexadecimal UUID string"
    assert harness.events[-2:] == ["manager.close", "db.close"]


def test_manager_close_failure_still_closes_db_and_propagates(
    dispatch_db: Session, monkeypatch: pytest.MonkeyPatch
):
    harness = Harness(monkeypatch, dispatch_db)
    harness.close_failure = RuntimeError("close boom")
    jobs = harness.add_jobs(["areas"])
    with pytest.raises(RuntimeError, match="close boom"):
        harness.run(["areas"], ids(jobs))
    assert harness.events[-2:] == ["manager.close", "db.close"]
    assert harness.stored_jobs()["areas"].status == "completed"


def test_fetch_helper_rejects_unsupported_entity_without_client_calls():
    with pytest.raises(RuntimeError, match=r"^Entity `unknown` non supportata$"):
        asyncio.run(
            sync_service._fetch_entity_rows(
                SimpleNamespace(), SimpleNamespace(params_json={}), "unknown", SimpleNamespace()
            )
        )


def test_sync_helper_rejects_unsupported_entity_instead_of_consorziati(
    monkeypatch: pytest.MonkeyPatch,
):
    called: list = []
    monkeypatch.setattr(sync_service, "sync_white_consorziati", lambda **kw: called.append(kw))
    with pytest.raises(RuntimeError, match=r"^Entity `unknown` non supportata$"):
        sync_service._sync_entity_rows(
            SimpleNamespace(), "unknown", SimpleNamespace(id=USER_ID), []
        )
    assert called == []
