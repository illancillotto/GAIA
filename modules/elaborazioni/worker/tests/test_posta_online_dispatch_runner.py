from __future__ import annotations

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

import posta_online_dispatch_runner as runner
import posta_online_sync
from app.modules.ruolo.services import poste_dispatch_work as real_work
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict
from posta_online_dispatch import DraftNotSubmitted, DraftSubmitUncertain

ORISTANO = {
    "street": "VIA CAGLIARI",
    "number": "170",
    "city": "ORISTANO",
    "province": "OR",
    "zipcode": "09170",
}
RECIPIENT = {
    "name": "ROSSI MARIO",
    "name_extra": "",
    "address": "VIA CAGLIARI 170",
    "cap": "09170",
    "city": "ORISTANO",
    "province": "OR",
}


def run(coro):
    return asyncio.run(coro)


def _item(name="GAIA 1", status="address_ok"):
    return real_work.WorkItem(
        uuid4(), name, status, dict(RECIPIENT), {"mode": "directory", "label": "x"}, None
    )


def _row(name="GAIA 1", draft_id="10"):
    return real_work.DraftRow(
        draft_id=draft_id, name=name, status="PREZZATO", price=Decimal("5.43")
    )


class Work:
    """Stand-in for the backend state module: items by status and a log of writes."""

    DRAFT_READY_STATUSES = real_work.DRAFT_READY_STATUSES
    WorkItem, DraftRow = real_work.WorkItem, real_work.DraftRow

    def __init__(self, items=(), missing=(), creating=True, tampered=False):
        self.items, self.missing, self.creating, self.log = list(items), list(missing), creating, []
        self.tampered = tampered

    def lot_items(self, _db, _lot_id, statuses):
        return [item for item in self.items if item.status in statuses]

    def artifact_for_upload(self, _db, _item_id):
        if self.tampered:
            raise DispatchConflict("PDF del lotto mancante o alterato")
        return b"%PDF"

    def mark_draft_creating(self, _db, item_id, *, job_id):
        self.log.append(("creating", item_id))
        return self.creating

    def apply_drafts_snapshot(self, _db, _lot_id, *, job_id, rows):
        self.log.append(("snapshot", tuple(row.name for row in rows)))
        return list(self.missing)

    def __getattr__(self, name):
        def record(_db, item_id, *, job_id, **kwargs):
            self.log.append((name, item_id, kwargs))

        return record


class Db:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def commit(self):
        return None


class Portal:
    def __init__(self, drafts=(), archive=None, complete=True, create_error=None, suggestions=()):
        self.drafts = [list(rows) for rows in drafts]
        self.archive, self.complete = archive or {}, complete
        self.create_error, self.suggestion_list = create_error, list(suggestions)
        self.phase, self.created, self.deleted, self.blocked = "login", [], [], []
        self.client = SimpleNamespace(fetch_detail_html=self._detail)

    async def install_guard(self):
        return None

    async def open_send_form(self):
        self.opened = True

    async def suggestions(self, term):
        return self.suggestion_list

    async def list_drafts(self):
        return self.drafts.pop(0) if len(self.drafts) > 1 else self.drafts[0]

    async def archive_index(self):
        return self.archive, self.complete

    async def _detail(self, shipment_id):
        return f"<html>{shipment_id}</html>"

    async def create_draft(self, item, artifact, before_submit):
        await before_submit()
        self.created.append(item.shipment_name)
        if self.create_error:
            raise self.create_error

    async def delete_draft(self, draft_id):
        self.deleted.append(draft_id)


@pytest.fixture
def work(monkeypatch):
    def install(*args, **kwargs):
        fake = Work(*args, **kwargs)
        monkeypatch.setattr(runner, "work", fake)
        monkeypatch.setattr(
            runner,
            "record_sent",
            lambda _db, item_id, **kwargs: fake.log.append(("sent", item_id, kwargs)),
        )
        monkeypatch.setattr(runner, "PRICE_SETTLE_SECONDS", 0)
        return fake

    return install


def _run(portal):
    return runner.DispatchRun(lambda: Db(), 3, uuid4(), portal)


def test_addresses_are_matched_against_the_directory(work):
    found, review = _item("GAIA 1", "address_pending"), _item("GAIA 2", "address_pending")
    review.recipient["address"] = "VIA ROMA 1"
    fake = work([found, review])
    dispatch_run = _run(Portal(suggestions=[ORISTANO]))
    run(runner.run_addresses(dispatch_run))
    assert fake.log[0][2]["suggestion"] == ORISTANO and fake.log[1][2]["suggestion"] is None
    assert fake.log[1][2]["labels"] == ["VIA CAGLIARI 170, ORISTANO (OR), 09170"]
    assert (
        dispatch_run.counters == {"found": 1, "review": 1}
        and dispatch_run.portal.phase == "addresses"
    )


def test_drafts_are_created_once_and_existing_ones_are_adopted(work):
    new, existing, twice = _item("GAIA 1"), _item("GAIA 2"), _item("GAIA 3")
    fake = work([new, existing, twice])
    before = [_row("GAIA 2", "20"), _row("GAIA 3", "30"), _row("GAIA 3", "31")]
    portal = Portal(drafts=[before, [*before, _row("GAIA 1", "10")]])
    dispatch_run = _run(portal)
    run(runner.run_drafts(dispatch_run))
    assert portal.created == ["GAIA 1"] and dispatch_run.counters == {"created": 1}
    kinds = [entry[0] for entry in fake.log]
    assert kinds == [
        "snapshot",
        "creating",
        "record_draft_row",
        "record_draft_row",
        "record_anomaly",
        "snapshot",
    ]
    assert fake.log[2][2]["row"].draft_id == "10" and fake.log[3][1] == existing.id


def test_a_draft_failing_before_continua_is_retryable(work):
    fake = work([_item()])
    run(runner.run_drafts(_run(Portal(drafts=[[]], create_error=DraftNotSubmitted("modulo")))))
    assert (
        "record_draft_failure",
        fake.items[0].id,
        {"submitted": False, "error": "modulo"},
    ) in fake.log


def test_an_altered_pdf_is_never_uploaded(work):
    fake = work([_item()], tampered=True)
    portal = Portal(drafts=[[]])
    run(runner.run_drafts(_run(portal)))
    failure = next(entry for entry in fake.log if entry[0] == "record_draft_failure")
    assert portal.created == [] and failure[2] == {
        "submitted": False,
        "error": "PDF del lotto mancante o alterato",
    }


def test_a_changed_item_is_never_submitted(work):
    fake = work([_item()], creating=False)
    portal = Portal(drafts=[[]])
    run(runner.run_drafts(_run(portal)))
    assert portal.created == [] and fake.log[-2][2]["submitted"] is False


@pytest.mark.parametrize(
    "after,error", [([], "non trovata"), ([_row(), _row(draft_id="11")], "Più bozze")]
)
def test_an_uncertain_continua_is_settled_by_the_drafts_list(work, after, error):
    fake = work([_item()])
    portal = Portal(drafts=[[], after, after], create_error=DraftSubmitUncertain("timeout"))
    run(runner.run_drafts(_run(portal)))
    failure = next(entry for entry in fake.log if entry[0] == "record_draft_failure")
    assert failure[2]["submitted"] is True and error in failure[2]["error"]


def test_an_uncertain_continua_with_the_draft_listed_is_a_success(work):
    fake = work([_item()])
    run(
        runner.run_drafts(
            _run(Portal(drafts=[[], [_row()]], create_error=DraftSubmitUncertain("timeout")))
        )
    )
    assert [entry[0] for entry in fake.log].count("record_draft_row") == 1


def test_two_consecutive_failures_stop_the_lot(work):
    work([_item("GAIA 1"), _item("GAIA 2"), _item("GAIA 3")])
    portal = Portal(drafts=[[]], create_error=DraftNotSubmitted("portale"))
    with pytest.raises(RuntimeError, match="Due bozze consecutive"):
        run(runner.run_drafts(_run(portal)))
    assert portal.created == ["GAIA 1", "GAIA 2"]


def test_reconcile_records_sent_missing_and_ambiguous_shipments(work):
    sent, gone, twice = (
        _item("GAIA 1", "draft_priced"),
        _item("GAIA 2", "draft_priced"),
        _item("GAIA 3", "draft_priced"),
    )
    fake = work([sent, gone, twice], missing=[sent.id, gone.id, twice.id])
    dispatch_run = _run(Portal(drafts=[[]], archive={"GAIA 1": ["77"], "GAIA 3": ["78", "79"]}))
    run(runner.run_reconcile(dispatch_run))
    assert (
        "sent",
        sent.id,
        {"job_id": 3, "id_invio": "77", "detail_html": "<html>77</html>"},
    ) in fake.log
    assert ("record_missing", gone.id, {}) in fake.log
    assert any(entry[0] == "record_anomaly" and entry[1] == twice.id for entry in fake.log)
    assert dispatch_run.counters == {"sent": 1, "missing": 1}


def test_an_incomplete_archive_never_marks_a_draft_missing(work):
    item = _item("GAIA 1", "draft_priced")
    fake = work([item], missing=[item.id])
    run(runner.run_reconcile(_run(Portal(drafts=[[]], complete=False))))
    assert [entry[0] for entry in fake.log] == ["snapshot", "record_anomaly"]


def test_reconcile_without_missing_items_skips_the_archive(work):
    fake = work([_item("GAIA 1", "draft_priced")])
    run(runner.run_reconcile(_run(Portal(drafts=[[_row()]]))))
    assert [entry[0] for entry in fake.log] == ["snapshot"]


def test_delete_removes_requested_drafts_and_checks_they_are_gone(work):
    gone, stuck, absent = (
        _item("GAIA 1", "cancel_requested"),
        _item("GAIA 2", "cancel_requested"),
        _item("GAIA 3", "cancel_requested"),
    )
    fake = work([gone, stuck, absent], missing=[absent.id])
    portal = Portal(drafts=[[_row("GAIA 1", "10"), _row("GAIA 2", "20")], [_row("GAIA 2", "20")]])
    dispatch_run = _run(portal)
    run(runner.run_delete(dispatch_run))
    assert portal.deleted == ["10", "20"] and dispatch_run.counters == {"deleted": 1, "missing": 1}
    assert ("record_deleted", gone.id, {}) in fake.log
    assert any(entry[0] == "record_anomaly" and entry[1] == stuck.id for entry in fake.log)


class JobPortal(Portal):
    def __init__(self, client):
        super().__init__()
        self.client = client


class JobDb(Db):
    def __init__(self, store):
        self.store = store

    def get(self, _model, _job_id):
        return self.store["job"]


class Client:
    instances: list = []

    def __init__(self, config):
        self.config, self.page = config, None
        Client.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def login(self, username, password):
        if password == "wrong":
            raise RuntimeError("login rifiutato")


def _job_store(mode="poste_dispatch_reconcile"):
    job = SimpleNamespace(
        mode=mode,
        credential_id=None,
        payload_json={"lot_id": str(uuid4())},
        status="processing",
        error_detail=None,
        completed_at=None,
        result_json=None,
    )
    return {"job": job}


def _patch_credentials(monkeypatch, password="secret", calls=None):
    credential = SimpleNamespace(id=9, username="poste", min_delay_ms=1000, max_delay_ms=2000)
    calls = calls if calls is not None else []
    monkeypatch.setattr(runner, "pick_credential", lambda _db, _id: (credential, password))
    monkeypatch.setattr(
        runner, "mark_credential_used", lambda _db, cid: calls.append(("used", cid))
    )
    monkeypatch.setattr(
        runner, "mark_credential_error", lambda _db, cid, error: calls.append(("error", cid, error))
    )
    return calls


def test_job_runs_the_handler_with_the_guard_installed(monkeypatch):
    store, calls, seen = _job_store(), _patch_credentials(monkeypatch), []

    async def handler(dispatch_run):
        seen.append((dispatch_run.job_id, dispatch_run.portal.phase))
        dispatch_run.count("sent")

    monkeypatch.setitem(runner.HANDLERS, "poste_dispatch_reconcile", handler)
    run(
        runner.run_dispatch_job(
            job_id=4,
            session_factory=lambda: JobDb(store),
            headless=True,
            _client_class=Client,
            _portal_class=JobPortal,
        )
    )
    job = store["job"]
    assert job.status == "succeeded" and job.result_json["counters"] == {"sent": 1}
    assert (
        seen == [(4, "login")]
        and calls == [("used", 9)]
        and Client.instances[-1].config.headless is True
    )


def test_login_failures_count_against_the_credential(monkeypatch):
    store = _job_store()
    calls = _patch_credentials(monkeypatch, password="wrong")
    run(
        runner.run_dispatch_job(
            job_id=4,
            session_factory=lambda: JobDb(store),
            headless=False,
            _client_class=Client,
            _portal_class=JobPortal,
        )
    )
    assert store["job"].status == "failed" and store["job"].error_detail == "login rifiutato"
    assert calls == [("error", 9, "login rifiutato")]


def test_portal_failures_after_login_do_not_disable_the_credential(monkeypatch):
    store, calls = _job_store(), _patch_credentials(monkeypatch)

    async def broken(_dispatch_run):
        raise RuntimeError("Verifica e invia non raggiungibile")

    monkeypatch.setitem(runner.HANDLERS, "poste_dispatch_reconcile", broken)
    run(
        runner.run_dispatch_job(
            job_id=4,
            session_factory=lambda: JobDb(store),
            headless=True,
            _client_class=Client,
            _portal_class=JobPortal,
        )
    )
    assert store["job"].status == "failed" and calls == []


def test_missing_credentials_fail_the_job_without_a_browser(monkeypatch):
    store = _job_store()

    def unavailable(_db, _id):
        raise RuntimeError("Nessuna credenziale Poste Online disponibile")

    monkeypatch.setattr(runner, "pick_credential", unavailable)
    run(
        runner.run_dispatch_job(
            job_id=4,
            session_factory=lambda: JobDb(store),
            headless=True,
            _client_class=Client,
            _portal_class=JobPortal,
        )
    )
    assert store["job"].status == "failed" and "credenziale" in store["job"].error_detail


def test_the_poste_queue_routes_outbox_jobs_to_the_runner(monkeypatch):
    calls = []

    async def dispatch_job(**kwargs):
        calls.append(kwargs["job_id"])

    store = _job_store("poste_dispatch_drafts")
    monkeypatch.setattr(runner, "run_dispatch_job", dispatch_job)
    run(
        posta_online_sync.run_posta_online_job_by_id(
            job_id=8, session_factory=lambda: JobDb(store), headless=True
        )
    )
    assert calls == [8]


def test_archive_records_are_written_by_the_backend_reconciliation(monkeypatch):
    from app.modules.ruolo.services import poste_dispatch_reconcile

    calls = []
    monkeypatch.setattr(
        poste_dispatch_reconcile,
        "record_sent",
        lambda db, item_id, **kwargs: calls.append((db, item_id, kwargs)),
    )
    runner.record_sent("db", "item", job_id=1, id_invio="77", detail_html="<html/>")
    assert calls == [("db", "item", {"job_id": 1, "id_invio": "77", "detail_html": "<html/>"})]
