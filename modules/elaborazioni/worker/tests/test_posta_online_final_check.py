import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

import posta_online_dispatch_runner as runner
import posta_online_sync
from app.modules.ruolo.services.poste_dispatch_final_check import MODE, record_account_snapshot
from app.modules.ruolo.services.poste_dispatch_work import DraftRow
from posta_online_final_check import run_final_check


class ReadOnlyPortal:
    def __init__(self, *, complete=True, fail_at=None):
        self.complete, self.fail_at = complete, fail_at
        self.reads = []

    async def list_drafts(self):
        self.reads.append("drafts_all_pages")
        if self.fail_at == "drafts":
            raise TimeoutError("draft page timeout")
        return [DraftRow(None, "GAIA 123", "IN ATTESA", None)]

    async def archive_index(self):
        self.reads.append("archive_all_pages")
        if self.fail_at == "archive":
            raise TimeoutError("archive page timeout")
        return {"GAIA 456": ["12"]}, self.complete


def test_final_check_is_dispatched_with_existing_account_lease_workflow():
    assert runner.HANDLERS[MODE] is run_final_check
    assert posta_online_sync._job_runner(MODE) is runner.run_dispatch_job


def test_complete_account_pass_records_drafts_and_archive_without_portal_mutation():
    writes, counters = [], []
    portal = ReadOnlyPortal()
    run = SimpleNamespace(
        portal=portal,
        lot_id=uuid4(),
        write=lambda *a, **kw: writes.append((a, kw)),
        count=counters.append,
    )
    asyncio.run(run_final_check(run))
    assert portal.reads == ["drafts_all_pages", "archive_all_pages"]
    [(args, kwargs)] = writes
    assert args == (record_account_snapshot, run.lot_id)
    assert kwargs["snapshot"]["drafts"][0]["draft_id"] is None
    assert kwargs["snapshot"]["archive"] == {"GAIA 456": ["12"]}
    assert counters == ["accounts_verified"]


@pytest.mark.parametrize("fail_at", ["drafts", "archive", "incomplete_archive"])
def test_timeout_or_incomplete_pagination_never_records_a_successful_snapshot(fail_at):
    writes, counters = [], []
    portal = ReadOnlyPortal(complete=fail_at != "incomplete_archive", fail_at=fail_at)
    run = SimpleNamespace(
        portal=portal,
        lot_id=uuid4(),
        write=lambda *a, **kw: writes.append((a, kw)),
        count=counters.append,
    )
    with pytest.raises((TimeoutError, RuntimeError)):
        asyncio.run(run_final_check(run))
    assert writes == counters == []
