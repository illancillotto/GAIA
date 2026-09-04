from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.capacitas import CapacitasParticelleSyncJob
from app.modules.elaborazioni.capacitas.apps.involture import parsers
from app.modules.elaborazioni.capacitas.models import CapacitasParticelleSyncJobCreateRequest
from app.services import elaborazioni_capacitas_particelle_sync as service


def _db_with_get(value):
    db = MagicMock()
    db.get.return_value = value
    return db


def _item(*, comune: str | None = "Uras") -> service.ParticellaSyncItem:
    return service.ParticellaSyncItem(
        index=1,
        particella_id=uuid4(),
        label="Uras 1/2",
        comune_label=comune,
        sezione="",
        foglio="1",
        particella="2",
        sub="",
    )


def _job(status: str = "pending", **overrides):
    values = {
        "id": 1,
        "status": status,
        "mode": "progressive_catalog",
        "credential_id": 7,
        "requested_by_user_id": None,
        "payload_json": {},
        "result_json": {},
        "error_detail": None,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_job_crud_cancel_and_datetime_helpers() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = ["listed"]
    db.get.return_value = "loaded"
    payload = CapacitasParticelleSyncJobCreateRequest()

    created = service.create_particelle_sync_job(
        db, requested_by_user_id=3, credential_id=7, payload=payload
    )
    assert isinstance(created, CapacitasParticelleSyncJob)
    assert created.payload_json["auto_resume"] is True
    assert service.list_particelle_sync_jobs(db) == ["listed"]
    assert service.get_particelle_sync_job(db, 1) == "loaded"
    service.delete_particelle_sync_job(db, created)

    pending = _job(result_json=None)
    processing = _job("processing", result_json=None)
    terminal = _job("succeeded")
    assert service.cancel_particelle_sync_job(db, pending).status == "cancelled"
    assert service.cancel_particelle_sync_job(db, processing).status == "cancelling"
    assert service.cancel_particelle_sync_job(db, terminal).status == "succeeded"

    naive = datetime(2026, 1, 1)
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    assert service._normalize_job_datetime(None) is None
    assert service._normalize_job_datetime(naive).tzinfo is UTC
    assert service._normalize_job_datetime(aware) == aware


def test_stale_and_recovery_empty_paths() -> None:
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    service.expire_stale_particelle_sync_jobs(db)
    assert service.prepare_particelle_sync_jobs_for_recovery(db) == []

    fresh = _job("processing", started_at=datetime.now(UTC), updated_at=None)
    stale = _job(
        "processing",
        started_at=datetime.now(UTC) - timedelta(hours=2),
        updated_at=None,
        result_json={"current_label": "x"},
        error_detail="old",
    )
    db.scalars.return_value.all.return_value = [fresh, stale]
    service.expire_stale_particelle_sync_jobs(db)
    assert stale.status == "failed"
    assert "old" in stale.error_detail
    assert stale.result_json["current_label"] is None


def test_result_and_comune_helpers_cover_edges() -> None:
    result: dict[str, object] = {"recent_items": "invalid"}
    for index in range(service.RECENT_ITEM_LIMIT + 2):
        service._append_recent_item(result, {"index": index})
    assert len(result["recent_items"]) == service.RECENT_ITEM_LIMIT
    assert service._compute_progress_percent(1, 0) == 100
    assert service._compute_progress_percent(50, 10) == 100

    db = MagicMock()
    assert (
        service._resolve_comune_label(db, SimpleNamespace(nome_comune="Uras", comune_id=None))
        == "Uras"
    )
    comune_id = uuid4()
    db.get.return_value = SimpleNamespace(nome_comune="Cabras")
    assert (
        service._resolve_comune_label(db, SimpleNamespace(nome_comune=None, comune_id=comune_id))
        == "Cabras"
    )
    db.get.return_value = None
    assert (
        service._resolve_comune_label(db, SimpleNamespace(nome_comune=None, comune_id=comune_id))
        is None
    )
    assert (
        service._resolve_comune_label(db, SimpleNamespace(nome_comune=None, comune_id=None)) is None
    )


@pytest.mark.anyio
async def test_sync_item_missing_comune_and_all_result_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = CapacitasParticelleSyncJobCreateRequest()
    client = SimpleNamespace(relogin=AsyncMock())

    missing_db = _db_with_get(None)
    assert (
        await service._sync_particella_item(
            missing_db, client, job_id=1, credential_id=7, payload=payload, item=_item()
        )
    )["status"] == "failed"

    parcel = SimpleNamespace()
    skipped_db = _db_with_get(parcel)
    assert (
        await service._sync_particella_item(
            skipped_db, client, job_id=1, credential_id=7, payload=payload, item=_item(comune=None)
        )
    )["status"] == "skipped"

    results = [
        SimpleNamespace(items=[]),
        SimpleNamespace(items=[SimpleNamespace(ok=False, error=None)]),
        SimpleNamespace(items=[SimpleNamespace(ok=True, total_rows=0)]),
        SimpleNamespace(
            items=[
                SimpleNamespace(ok=True, total_rows=2, imported_certificati=1, imported_details=2)
            ]
        ),
    ]
    for expected, sync_result in zip(
        ("failed", "failed", "skipped", "synced"), results, strict=True
    ):
        monkeypatch.setattr(service, "sync_terreni_batch", AsyncMock(return_value=sync_result))
        db = _db_with_get(SimpleNamespace())
        response = await service._sync_particella_item(
            db, client, job_id=1, credential_id=7, payload=payload, item=_item()
        )
        assert response["status"] == expected


@pytest.mark.anyio
async def test_sync_item_exception_after_deleted_parcel(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    db.get.side_effect = [SimpleNamespace(), None]
    monkeypatch.setattr(
        service, "sync_terreni_batch", AsyncMock(side_effect=RuntimeError("network"))
    )

    result = await service._sync_particella_item(
        db,
        SimpleNamespace(),
        job_id=1,
        credential_id=7,
        payload=CapacitasParticelleSyncJobCreateRequest(),
        item=_item(),
    )

    assert result["status"] == "failed"
    db.rollback.assert_called_once()


@pytest.mark.anyio
async def test_sync_single_rejects_missing_or_unsyncable_parcel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="Particella non trovata"):
        await service.sync_single_particella(
            _db_with_get(None),
            SimpleNamespace(),
            particella_id=uuid4(),
            requested_by_user_id=1,
            credential_id=7,
        )

    monkeypatch.setattr(service, "_build_sync_items", lambda _db, _rows: [])
    with pytest.raises(RuntimeError, match="non sincronizzabile"):
        await service.sync_single_particella(
            _db_with_get(SimpleNamespace()),
            SimpleNamespace(),
            particella_id=uuid4(),
            requested_by_user_id=1,
            credential_id=7,
        )


@pytest.mark.anyio
async def test_sync_single_marks_job_failed_on_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parcel = SimpleNamespace(id=uuid4())
    stored = []
    db = MagicMock()
    db.add.side_effect = stored.append
    db.get.side_effect = lambda model, _id: parcel if model is service.CatParticella else stored[0]
    monkeypatch.setattr(service, "_build_sync_items", lambda _db, _rows: [_item()])
    monkeypatch.setattr(
        service, "_sync_particella_item", AsyncMock(side_effect=RuntimeError("boom"))
    )

    with pytest.raises(RuntimeError, match="boom"):
        await service.sync_single_particella(
            db,
            SimpleNamespace(),
            particella_id=parcel.id,
            requested_by_user_id=1,
            credential_id=7,
        )

    assert stored[0].status == "failed"
    assert stored[0].error_detail == "boom"


def test_apply_progress_for_each_status() -> None:
    job = _job(result_json=None)
    db = _db_with_get(job)
    fallback = service._build_initial_result(3, service.compute_sync_policy())
    for status in ("synced", "skipped", "anomalia"):
        service._apply_item_progress(
            db,
            job_id=1,
            total_items=3,
            item_result={"status": status, "label": status},
            fallback_result=fallback,
        )
    assert job.result_json["processed_items"] == 3
    assert job.result_json["success_items"] == 1
    assert job.result_json["skipped_items"] == 1
    assert job.result_json["failed_items"] == 1


@pytest.mark.anyio
async def test_parallel_runner_processes_queue_and_honors_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(
        "processing", result_json=service._build_initial_result(2, service.compute_sync_policy())
    )
    db = _db_with_get(job)
    worker_db = MagicMock()
    sync_mock = AsyncMock(return_value={"status": "synced", "label": "x"})
    monkeypatch.setattr(service, "_sync_particella_item", sync_mock)
    monkeypatch.setattr(service.asyncio, "sleep", AsyncMock())

    returned = await service._run_particelle_sync_parallel(
        db,
        session_factory=lambda: worker_db,
        clients=[SimpleNamespace(), SimpleNamespace()],
        job=job,
        payload=CapacitasParticelleSyncJobCreateRequest(),
        policy=service.compute_sync_policy(parallel_workers=2),
        items=[_item(), _item()],
        result_json=job.result_json,
    )
    assert returned is job
    assert sync_mock.await_count == 2
    assert worker_db.close.call_count == 2

    cancelling = _job("cancelling")
    db.get.return_value = cancelling
    await service._run_particelle_sync_parallel(
        db,
        session_factory=lambda: worker_db,
        clients=[SimpleNamespace()],
        job=cancelling,
        payload=CapacitasParticelleSyncJobCreateRequest(),
        policy=service.compute_sync_policy(),
        items=[_item()],
        result_json={},
    )
    assert sync_mock.await_count == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "failed_items", "expected"),
    (
        ("processing", 0, "succeeded"),
        ("processing", 1, "completed_with_errors"),
        ("cancelling", 0, "cancelled"),
    ),
)
async def test_run_job_parallel_final_states(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    failed_items: int,
    expected: str,
) -> None:
    job = _job(payload_json={"parallel_workers": 2}, result_json={})
    db = _db_with_get(job)
    monkeypatch.setattr(
        service,
        "_select_particelle_for_job",
        lambda *_args, **_kwargs: [SimpleNamespace(), SimpleNamespace()],
    )
    monkeypatch.setattr(service, "_build_sync_items", lambda *_args: [_item(), _item()])

    async def run_parallel(*_args, **_kwargs):
        job.status = status
        job.result_json = {"failed_items": failed_items}
        return job

    monkeypatch.setattr(service, "_run_particelle_sync_parallel", run_parallel)
    result = await service.run_particelle_sync_job(
        db,
        SimpleNamespace(),
        job,
        session_factory=lambda: MagicMock(),
        clients=[SimpleNamespace(), SimpleNamespace()],
    )
    assert result.status == expected


@pytest.mark.anyio
async def test_run_job_cancelled_before_sequential_item(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _job(result_json={})
    db = _db_with_get(job)
    monkeypatch.setattr(
        service, "_select_particelle_for_job", lambda *_args, **_kwargs: [SimpleNamespace()]
    )

    def build_items(*_args):
        job.status = "cancelling"
        return [_item()]

    monkeypatch.setattr(service, "_build_sync_items", build_items)
    result = await service.run_particelle_sync_job(db, SimpleNamespace(), job)
    assert result.status == "cancelled"


@pytest.mark.anyio
async def test_run_job_marks_failed_on_sequential_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _job(result_json={})
    db = _db_with_get(job)
    monkeypatch.setattr(
        service, "_select_particelle_for_job", lambda *_args, **_kwargs: [SimpleNamespace()]
    )
    monkeypatch.setattr(service, "_build_sync_items", lambda *_args: [_item()])
    monkeypatch.setattr(
        service, "_sync_particella_item", AsyncMock(side_effect=RuntimeError("boom"))
    )

    with pytest.raises(RuntimeError, match="boom"):
        await service.run_particelle_sync_job(db, SimpleNamespace(), job)
    assert job.status == "failed"


def test_parser_edge_cases() -> None:
    assert (
        parsers.parse_lookup_options("[{ID:'1',Display:'Comune+Uno'}]")[0].display == "Comune Uno"
    )
    assert parsers.parse_storico_anagrafica_rows([]) == []
    assert len(parsers.parse_storico_anagrafica_rows({"ID": "1", "IDXANA": "1"})) == 1
    assert parsers.parse_lookup_option_rows([None, {"ID": "", "Display": "x"}]) == []
    assert parsers.parse_terreni_search_result({"ID": "1"}).total == 1
    assert parsers._parse_birth_line(["invalid", "nato il 99/99/2020 in Roma"])[0] is None
    assert parsers._parse_birth_line([]) == (None, None)
    assert parsers._parse_residenza_line(["x", "RES: indirizzo"])[1] is None
    assert parsers._parse_residenza_line([]) == (None, None, None)
    assert parsers._parse_titoli_line(["x"]) is None
    assert parsers._derive_row_visual_state(None) == "current_black"
    assert parsers._derive_row_visual_state("#red") == "historic_red"
    assert parsers._derive_row_visual_state("*old") == "historic_marker"
    assert parsers._parse_jsish_payload("") == []
    with pytest.raises(ValueError, match="payload inatteso"):
        parsers._parse_jsish_payload("not-json")
    assert parsers._parse_jsish_payload("{a: 1}") == [{"a": 1}]
    assert parsers._extract_load_data_grid_rows("none") == []
    assert parsers._extract_checkbox_checked(
        parsers.BeautifulSoup("", "html.parser"), "missing", default=True
    )
    assert parsers._parse_date_value(None) is None
    assert parsers._parse_date_value("invalid") is None

    detail_html = """
    <script>loadDataGridV2('x', '[{"Parametro":"", "VStr":"x"}]', false)</script>
    """
    assert parsers.parse_terreno_detail_html(detail_html).parameters == {}
    soup = parsers.BeautifulSoup(
        '<div class="rpt-riga-ana"></div><div class="rpt-riga-vuota"></div>', "html.parser"
    )
    assert parsers._collect_intestatario_detail_lines(soup.select_one(".rpt-riga-ana")) == []
