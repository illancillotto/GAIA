from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from test_worker_orchestration_coverage import FakeBrowser, FakeDb, bare_worker, run
import worker as worker_module


class Selection:
    def __init__(self, request_id=None, *, wait_reason=None, wait_seconds=None) -> None:
        self.request_id = request_id
        self.execution_token = uuid4() if request_id is not None else None
        self.wait_reason = wait_reason
        self.wait_seconds = wait_seconds

    def resolved_wait_seconds(self, default):
        return self.wait_seconds if self.wait_seconds is not None else default


class BatchRepository:
    def __init__(self, selections=(), *, add_deferred=False) -> None:
        self.selections = list(selections)
        self.add_deferred = add_deferred
        self.failed_unavailable: list[tuple] = []
        self.failed_requests: list[tuple] = []
        self.failed_batches: list[tuple] = []
        self.releases: list[object] = []
        self.resets: list[tuple[tuple, dict]] = []

    def fail_unavailable_pinned_requests(self, *args):
        self.failed_unavailable.append(args)

    def reset_for_retry(self, *args, **kwargs):
        self.resets.append((args, kwargs))

    def fail_request(self, *args):
        self.failed_requests.append(args)

    def fail_batch(self, *args):
        self.failed_batches.append(args)


class ClaimCoordinator:
    def __init__(self, *_args) -> None:
        pass

    async def claim_next(self, repository, _batch_id, _credential_id):
        return repository.selections.pop(0) if repository.selections else Selection()

    async def release(self, request_id):
        return None


class RetryCoordinator:
    instances: list["RetryCoordinator"] = []

    def __init__(self, _lock, deferred, _reset, _delay) -> None:
        self.deferred = deferred
        self.calls: list[tuple[str, tuple]] = []
        type(self).instances.append(self)

    async def defer(self, *args):
        self.calls.append(("defer", args))

    async def defer_recoverable(self, *args):
        self.calls.append(("recoverable", args))


class BatchSessionFactory:
    def __init__(self, outer: FakeDb, repeated_value, scripted_values=()) -> None:
        self.outer = outer
        self.repeated_value = repeated_value
        self.scripted_values = list(scripted_values)
        self.first = True

    def __call__(self):
        if self.first:
            self.first = False
            return self.outer
        value = self.scripted_values.pop(0) if self.scripted_values else self.repeated_value
        return FakeDb(get_values=[value])


def credential(user_id=1, *, username="user"):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        active=True,
        sister_username=username,
        sister_password_encrypted="secret",
    )


def batch(*, pinned=True, kind="manual"):
    return SimpleNamespace(
        id=uuid4(),
        user_id=1,
        status=worker_module.CatastoBatchStatus.PROCESSING.value,
        credential_id=uuid4() if pinned else None,
        batch_kind=kind,
        current_operation=None,
        failed_items=0,
    )


def install_batch_runtime(
    worker,
    repository: BatchRepository,
    monkeypatch: pytest.MonkeyPatch,
    *,
    process=None,
    browser_factory=None,
) -> list[str]:
    operations: list[str] = []
    FakeBrowser.start_error = None
    RetryCoordinator.instances.clear()
    monkeypatch.setattr(worker_module, "SisterRequestClaimCoordinator", ClaimCoordinator)
    monkeypatch.setattr(worker_module, "SisterRequestRetryCoordinator", RetryCoordinator)
    worker._request_repository = lambda: repository
    worker._set_batch_operation = lambda _batch_id, operation: operations.append(operation)
    worker._finalize_batch = lambda _batch_id: operations.append("finalized")
    worker._batch_has_open_requests = lambda _batch_id: False
    worker._build_browser_session = browser_factory or FakeBrowser
    if process is None:
        worker._process_request = lambda *_args: async_none()
    else:
        worker._process_request = process
    return operations


async def async_none():
    return None


def test_batch_outer_guards_and_credential_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    repository = BatchRepository()
    install_batch_runtime(worker, repository, monkeypatch)

    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[None]), None))
    run(worker._process_batch(uuid4()))

    item = batch()
    item.status = worker_module.CatastoBatchStatus.CANCELLED.value
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[item]), item))
    run(worker._process_batch(item.id))

    item = batch()
    wrong_credential = credential(user_id=99)
    outer = FakeDb(get_values=[item, wrong_credential])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))
    run(worker._process_batch(item.id))
    assert item.status == worker_module.CatastoBatchStatus.FAILED.value

    item = batch(pinned=False)
    active = credential()
    inactive = credential()
    inactive.active = False
    outer = FakeDb(get_values=[item], scalars_values=[[inactive, active]])
    repository = BatchRepository([Selection()])
    operations = install_batch_runtime(worker, repository, monkeypatch)
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))
    run(worker._process_batch(item.id))
    assert "finalized" in operations
    assert repository.failed_unavailable[0][1] == {active.id}


def test_batch_happy_path_role_label_and_release_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch(kind=worker_module.CatastoBatchKind.RUOLO_AUTOSYNC.value)
    active = credential()
    request_id = uuid4()
    repository = BatchRepository([Selection(request_id), Selection()])
    calls: list[object] = []

    async def process(*args):
        calls.append(args[-1])

    operations = install_batch_runtime(worker, repository, monkeypatch, process=process)
    outer = FakeDb(get_values=[item, active])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))
    run(worker._process_batch(item.id))
    assert calls == [request_id]
    assert operations[0].startswith("Avvio autosync ruolo") and operations[-1] == "finalized"

    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository()
    install_batch_runtime(worker, repository, monkeypatch)
    cancelled = SimpleNamespace(status=worker_module.CatastoBatchStatus.CANCELLED.value)
    outer = FakeDb(get_values=[item, active])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, cancelled))
    run(worker._process_batch(item.id))

    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository([Selection(uuid4())])
    install_batch_runtime(worker, repository, monkeypatch)
    outer = FakeDb(get_values=[item, active])
    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        BatchSessionFactory(outer, item, [item, SimpleNamespace(status=worker_module.CatastoBatchStatus.CANCELLED.value)]),
    )
    run(worker._process_batch(item.id))


@pytest.mark.parametrize("wait_reason", ["WAIT", "RETRY_LATER", None])
def test_batch_wait_reasons(wait_reason: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository([Selection(wait_reason=wait_reason)])
    operations = install_batch_runtime(worker, repository, monkeypatch)
    worker._batch_has_open_requests = lambda _batch_id: True
    outer = FakeDb(get_values=[item, active])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))

    async def stop(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop)
    run(worker._process_batch(item.id))
    if wait_reason == "WAIT":
        assert "In attesa di input CAPTCHA manuale" in operations
    elif wait_reason == "RETRY_LATER":
        assert any("Richieste differite" in value for value in operations)


def test_batch_retry_wait_uses_deferred_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    class DeferredRetryCoordinator(RetryCoordinator):
        def __init__(self, lock, deferred, reset, delay) -> None:
            super().__init__(lock, deferred, reset, delay)
            deferred[uuid4()] = datetime.now(timezone.utc) + timedelta(seconds=20)

    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository([Selection(wait_reason="RETRY_LATER")])
    operations = install_batch_runtime(worker, repository, monkeypatch)
    monkeypatch.setattr(worker_module, "SisterRequestRetryCoordinator", DeferredRetryCoordinator)
    worker._batch_has_open_requests = lambda _batch_id: True
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[item, active]), item))

    async def stop(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop)
    run(worker._process_batch(item.id))
    assert any("Richieste differite" in value for value in operations)


@pytest.mark.parametrize("resume_at", [datetime.now(timezone.utc) + timedelta(minutes=5), None])
def test_batch_operation_window_pauses(resume_at, monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository()
    operations = install_batch_runtime(worker, repository, monkeypatch)
    worker._is_within_operating_window = lambda _now: False
    worker._next_operating_resume_at = lambda _now: resume_at
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[item, active]), item))

    async def stop(_seconds):
        worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", stop)
    run(worker._process_batch(item.id))
    assert any("fuori finestra operativa" in value for value in operations)


def _run_error_batch(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    *,
    credentials=1,
    fatal_request=None,
    stop_after_sleep=1,
):
    worker = bare_worker()
    item = batch(pinned=credentials == 1)
    active = [credential(username=f"user-{index}") for index in range(credentials)]
    request_id = uuid4()
    selections = [Selection(request_id)] + [Selection() for _ in range(credentials - 1)]
    repository = BatchRepository(selections)

    async def process(*_args):
        raise error

    operations = install_batch_runtime(worker, repository, monkeypatch, process=process)
    worker._batch_has_open_requests = lambda _batch_id: False
    if credentials == 1:
        outer = FakeDb(get_values=[item, active[0]])
    else:
        outer = FakeDb(get_values=[item], scalars_values=[active])
    scripted = [item]
    if fatal_request is not None:
        scripted.append(fatal_request)
    factory = BatchSessionFactory(outer, item, scripted)
    monkeypatch.setattr(worker_module, "SessionLocal", factory)
    sleeps: list[float] = []

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) >= stop_after_sleep:
            worker.state.stop_requested = True

    monkeypatch.setattr(worker_module.asyncio, "sleep", sleep)
    run(worker._process_batch(item.id))
    return worker, repository, operations, sleeps


def test_batch_server_error_global_pause_and_credential_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    worker, repository, operations, sleeps = _run_error_batch(
        worker_module.SisterServerError("500"),
        monkeypatch,
        stop_after_sleep=3,
    )
    assert RetryCoordinator.instances[-1].calls[0][0] == "defer"
    assert any("pausa globale" in value for value in operations)
    assert len(sleeps) >= 3

    worker, repository, operations, sleeps = _run_error_batch(
        worker_module.SisterServerError("500"),
        monkeypatch,
        credentials=2,
        stop_after_sleep=3,
    )
    assert any("in cooldown" in value for value in operations)


def test_batch_recoverable_and_fatal_errors_are_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _worker, _repository, _operations, _sleeps = _run_error_batch(
        RuntimeError("SISTER_SESSION_LOCKED"),
        monkeypatch,
    )
    assert RetryCoordinator.instances[-1].calls[0][0] == "recoverable"

    request = SimpleNamespace(artifact_dir=str(tmp_path))
    worker, repository, _operations, _sleeps = _run_error_batch(
        ValueError("fatal"),
        monkeypatch,
        fatal_request=request,
    )
    assert repository.failed_requests
    assert (tmp_path / "error.txt").exists()

    worker, repository, _operations, _sleeps = _run_error_batch(
        ValueError("fatal-no-artifact"),
        monkeypatch,
        fatal_request=SimpleNamespace(artifact_dir=None),
    )
    assert repository.failed_requests


def test_batch_rejected_credential_reassigns_request_to_remaining_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch(pinned=False)
    rejected = credential(username="rejected")
    available = credential(username="available")
    request_id = uuid4()
    repository = BatchRepository([Selection(request_id), Selection(request_id), Selection()])
    processed_by: list[str] = []

    async def process(_browser, selected, _batch_id, _request_id):
        processed_by.append(selected.sister_username)
        if selected is rejected:
            raise RuntimeError("Credenziali SISTER rifiutate: Autenticazione fallita.")

    operations = install_batch_runtime(worker, repository, monkeypatch, process=process)
    worker._batch_has_open_requests = lambda _batch_id: False
    outer = FakeDb(get_values=[item], scalars_values=[[rejected, available]])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(worker_module.asyncio, "sleep", no_sleep)

    run(worker._process_batch(item.id))

    assert processed_by == ["rejected", "available"]
    assert repository.resets[0][1]["error_code"] == "sister_credential_rejected"
    assert repository.failed_unavailable[-1][1] == {available.id}
    assert not repository.failed_requests
    assert operations[-1] == "finalized"


def test_batch_all_rejected_credentials_stops_in_resumable_state(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch(pinned=False)
    rejected = credential(username="rejected")
    repository = BatchRepository([Selection(uuid4())])

    async def process(*_args):
        raise RuntimeError("Credenziali errate. Autenticazione fallita.")

    operations = install_batch_runtime(worker, repository, monkeypatch, process=process)
    worker._batch_has_open_requests = lambda _batch_id: True
    outer = FakeDb(get_values=[item], scalars_values=[[rejected]])
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(outer, item))

    run(worker._process_batch(item.id))

    assert item.status == worker_module.CatastoBatchStatus.FAILED.value
    assert "aggiornare il pool e riprendere il batch" in item.current_operation
    assert repository.resets
    assert "finalized" not in operations


def test_batch_stop_checkpoint_and_pool_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository([Selection(uuid4())])

    async def stop_process(*_args):
        worker.state.stop_requested = True

    install_batch_runtime(worker, repository, monkeypatch, process=stop_process)
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[item, active]), item))
    run(worker._process_batch(item.id))

    worker = bare_worker()
    item = batch()
    active = credential()
    repository = BatchRepository()

    class BrokenBrowser(FakeBrowser):
        async def start(self):
            raise RuntimeError("start")

    install_batch_runtime(worker, repository, monkeypatch, browser_factory=BrokenBrowser)
    monkeypatch.setattr(worker_module, "SessionLocal", BatchSessionFactory(FakeDb(get_values=[item, active]), item))
    run(worker._process_batch(item.id))
    assert repository.failed_batches
