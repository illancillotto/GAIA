from __future__ import annotations

import asyncio
from collections.abc import Generator
from dataclasses import asdict
from datetime import date
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

ENTITY_BOUNDARIES = {
    "report_types": (
        sync_service.BonificaReportTypesClient,
        "fetch_report_types",
        "sync_white_report_types",
    ),
    "reports": (sync_service.BonificaReportsClient, "fetch_reports", "sync_white_reports"),
    "vehicles": (sync_service.BonificaVehiclesClient, "fetch_vehicles", "sync_white_vehicles"),
    "refuels": (
        sync_service.BonificaRefuelsClient,
        "fetch_refuels_for_vehicle_codes",
        "sync_white_refuels",
    ),
    "taken_charge": (
        sync_service.BonificaTakenChargeClient,
        "fetch_taken_charge",
        "sync_white_taken_charge",
    ),
    "users": (sync_service.BonificaUsersClient, "fetch_users", "sync_white_operators"),
    "areas": (sync_service.BonificaAreasClient, "fetch_areas", "sync_white_areas"),
    "warehouse_requests": (
        sync_service.BonificaWarehouseRequestsClient,
        "fetch_warehouse_requests",
        "sync_white_warehouse_requests",
    ),
    "org_charts": (
        sync_service.BonificaOrgChartsClient,
        "fetch_org_charts",
        "sync_white_org_charts_to_canonical",
    ),
    "consorziati": (
        sync_service.BonificaUsersClient,
        "fetch_consorziati",
        "sync_white_consorziati",
    ),
}
PLAIN_RESULTS = {
    "report_types": WhiteReportTypesSyncResult,
    "users": WhiteOperatorsSyncResult,
    "areas": WhiteAreasSyncResult,
    "warehouse_requests": WhiteWarehouseSyncResult,
    "consorziati": WhiteConsorziatiSyncResult,
}


def domain_result(entity: str, synced: int, errors: list[str]):
    if entity == "reports":
        return WhiteReportsSyncResult(synced, 7, errors, 999)
    if entity == "org_charts":
        return WhiteOrgChartsSyncResult(synced, 7, 999, errors)
    if entity in {"vehicles", "refuels", "taken_charge"}:
        pairs = {"vehicles": (91, 92), "refuels": (93, 94), "taken_charge": (95, 96)}
        pairs[entity] = (synced, 7)
        return WhiteVehiclesSyncResult(
            *pairs["vehicles"], *pairs["refuels"], *pairs["taken_charge"], errors
        )
    return PLAIN_RESULTS[entity](synced, 7, errors)


@pytest.fixture
def normalization_db(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
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
                id=1,
                username="result-admin",
                email="result-admin@example.local",
                password_hash="unused",
                role="super_admin",
                is_active=True,
            )
        )
        session.add(
            BonificaOristaneseCredential(
                label="test",
                login_identifier="test@example.local",
                password_encrypted=get_credential_fernet().encrypt(b"test-password").decode(),
            )
        )
        session.commit()
        monkeypatch.setattr(sync_service, "SessionLocal", lambda: session)
        yield session
    get_credential_fernet.cache_clear()
    engine.dispose()


def configure_boundaries(
    monkeypatch: pytest.MonkeyPatch, session: Session, results: dict, events: list
):
    original_close = session.close

    def close_session():
        events.append("db.close")
        original_close()

    monkeypatch.setattr(session, "close", close_session)

    class PortalSession:
        def __init__(self, **kwargs):
            assert kwargs["password"] == "test-password"

        async def login(self):
            events.append("login")
            return SimpleNamespace(authenticated_url="https://test.example.local/home")

        async def close(self):
            events.append("manager.close")

    monkeypatch.setattr(sync_service, "BonificaOristaneseSessionManager", PortalSession)

    def record_commit(committed_session):
        jobs = [
            item for item in committed_session.identity_map.values() if isinstance(item, WCSyncJob)
        ]
        events.append(
            (
                "commit",
                tuple(
                    (
                        job.entity,
                        job.status,
                        job.params_json.get("source_total"),
                        job.records_synced,
                        job.records_errors,
                    )
                    for job in jobs
                ),
            )
        )

    event.listen(session, "after_commit", record_commit)

    def install(entity, value):
        client_class, method, service_name = ENTITY_BOUNDARIES[entity]

        async def fetch(_client, **kwargs):
            events.append(("fetch", entity))
            if entity in sync_service.DATE_AWARE_SYNC_ENTITIES:
                assert kwargs["date_from"] == date.today()
                assert kwargs["date_to"] == date.today()
            return [], 123

        def synchronize(**kwargs):
            assert kwargs["db"] is session
            assert kwargs["rows"] == []
            events.append(("sync", entity))
            if isinstance(value, Exception):
                raise value
            return value

        monkeypatch.setattr(client_class, method, fetch)
        monkeypatch.setattr(sync_service, service_name, synchronize)

    for entity, value in results.items():
        install(entity, value)


def run_jobs(session: Session, entities: list[str]):
    jobs = [
        WCSyncJob(
            entity=entity,
            status="queued",
            triggered_by=1,
            params_json={
                "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat(),
                "preserved": "yes",
            },
        )
        for entity in entities
    ]
    session.add_all(jobs)
    session.commit()
    asyncio.run(
        sync_service._run_bonifica_sync_background(
            triggered_by_user_id=1,
            request=BonificaSyncRunRequest(entities=entities),
            job_ids_by_entity={job.entity: str(job.id) for job in jobs},
        )
    )
    return jobs


@pytest.mark.parametrize("entity", list(ENTITY_BOUNDARIES))
@pytest.mark.parametrize("error_count,synced", [(0, 0), (1, 0), (1, 3), (20, 3), (21, 3), (25, 3)])
def test_real_domain_results_persist_selected_counts_and_error_preview(
    normalization_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    entity: str,
    error_count: int,
    synced: int,
):
    errors = [f"errore {index} - dettaglio" for index in range(error_count)]
    result = domain_result(entity, synced, errors)
    before = asdict(result)
    events: list = []
    configure_boundaries(monkeypatch, normalization_db, {entity: result}, events)
    run_jobs(normalization_db, [entity])
    with Session(normalization_db.bind) as verification:
        job = verification.scalar(select(WCSyncJob).where(WCSyncJob.entity == entity))
        assert job is not None
        assert (job.records_synced, job.records_skipped, job.records_errors) == (
            synced,
            7,
            error_count,
        )
        assert job.status == ("failed" if error_count and not synced else "completed")
        assert job.error_detail == ("\n".join(errors[:20]) if errors else None)
        assert job.finished_at is not None
        assert job.params_json["preserved"] == "yes"
        assert job.params_json["source_total"] == 123
        summary = job.params_json["report_summary"]
        assert summary["outcome"] == job.status
        assert summary["records_errors"] == error_count
        assert summary["records_synced"] == synced
        assert summary["error_preview"] == (errors[:5] if errors else None)
        credential = verification.scalar(select(BonificaOristaneseCredential))
        assert credential.last_authenticated_url == "https://test.example.local/home"
        assert credential.consecutive_failures == 0
    assert asdict(result) == before
    fetch_at = events.index(("fetch", entity))
    sync_at = events.index(("sync", entity))
    assert events[fetch_at + 1] == ("commit", ((entity, "running", 123, 0, 0),))
    assert sync_at == fetch_at + 2
    assert events[sync_at + 1] == (
        "commit",
        (
            (
                entity,
                "failed" if error_count and not synced else "completed",
                123,
                synced,
                error_count,
            ),
        ),
    )
    assert events[-2:] == ["manager.close", "db.close"]


def test_failed_entity_continues_in_canonical_order_and_closes_resources(
    normalization_db: Session, monkeypatch: pytest.MonkeyPatch
):
    events: list = []
    configure_boundaries(
        monkeypatch,
        normalization_db,
        {"report_types": RuntimeError("domain failure"), "users": domain_result("users", 4, [])},
        events,
    )
    run_jobs(normalization_db, ["users", "report_types"])
    assert [
        item for item in events if isinstance(item, tuple) and item[0] in {"fetch", "sync"}
    ] == [
        ("fetch", "report_types"),
        ("sync", "report_types"),
        ("fetch", "users"),
        ("sync", "users"),
    ]
    with Session(normalization_db.bind) as verification:
        jobs = {job.entity: job for job in verification.scalars(select(WCSyncJob))}
        assert jobs["report_types"].status == "failed"
        assert jobs["report_types"].error_detail == "domain failure"
        assert jobs["report_types"].records_errors == 1
        assert jobs["users"].status == "completed"
        assert jobs["users"].records_synced == 4
    assert events[-2:] == ["manager.close", "db.close"]


@pytest.mark.parametrize(
    "errors,detail,preview",
    [
        ([""], "", None),
        ([" \t"], " \t", [" \t"]),
        (
            ["duplicate", "duplicate", "embedded\nnewline", ""],
            "duplicate\nduplicate\nembedded\nnewline\n",
            ["duplicate", "duplicate", "embedded", "newline", ""],
        ),
    ],
)
def test_error_detail_preserves_empty_whitespace_duplicate_and_embedded_newline_messages(
    normalization_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    errors: list[str],
    detail: str,
    preview: list[str] | None,
):
    before = errors.copy()
    events: list = []
    configure_boundaries(
        monkeypatch,
        normalization_db,
        {"report_types": domain_result("report_types", 3, errors)},
        events,
    )
    run_jobs(normalization_db, ["report_types"])
    with Session(normalization_db.bind) as verification:
        job = verification.scalar(select(WCSyncJob))
        assert job.records_errors == len(before)
        assert job.error_detail == detail
        assert job.params_json["report_summary"]["error_preview"] == preview
        assert job.status == "completed"
    assert errors == before


@pytest.mark.parametrize("has_errors", [False, True])
def test_error_list_operation_order_is_count_then_truthiness_then_conditional_slice(
    normalization_db: Session, monkeypatch: pytest.MonkeyPatch, has_errors: bool
):
    operations: list[str] = []

    class ObservedErrors(list[str]):
        def __len__(self):
            operations.append("len")
            return super().__len__()

        def __getitem__(self, index):
            assert index == slice(None, 20)
            operations.append("slice")
            return super().__getitem__(index)

    errors = ObservedErrors(["domain message"] if has_errors else [])
    events: list = []
    configure_boundaries(
        monkeypatch,
        normalization_db,
        {"report_types": domain_result("report_types", 3, errors)},
        events,
    )
    run_jobs(normalization_db, ["report_types"])
    assert operations == (["len", "len", "slice"] if has_errors else ["len", "len"])


def test_invalid_join_item_fails_current_entity_and_still_continues(
    normalization_db: Session, monkeypatch: pytest.MonkeyPatch
):
    events: list = []
    configure_boundaries(
        monkeypatch,
        normalization_db,
        {
            "report_types": WhiteReportTypesSyncResult(3, 7, ["valid", 42]),
            "users": domain_result("users", 4, []),
        },
        events,
    )
    run_jobs(normalization_db, ["report_types", "users"])
    with Session(normalization_db.bind) as verification:
        jobs = {job.entity: job for job in verification.scalars(select(WCSyncJob))}
        assert jobs["report_types"].status == "failed"
        assert jobs["report_types"].records_synced == 0
        assert jobs["report_types"].records_errors == 1
        assert (
            jobs["report_types"].error_detail == "sequence item 1: expected str instance, int found"
        )
        assert jobs["users"].status == "completed"
        assert jobs["users"].records_synced == 4
    assert events[-2:] == ["manager.close", "db.close"]
