import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.modules.elaborazioni.capacitas.export_workbook import ExportPayload
from app.modules.elaborazioni.capacitas.incremental import cycle as c
from app.modules.elaborazioni.capacitas.incremental.journal import begin_cycle, promote
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import SnapshotInvalid
from app.modules.elaborazioni.capacitas.incremental.storage import save_original
from app.modules.utenze.models import AnagraficaPaymentNotice
from app.services.capacitas_ruoli_export_retry import RetryPolicy

from .conftest import NOTICE, NOW, raw_row, workbook


class Exports:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [raw_row()]
        self.calls = []
        self.years = ["2025"]

    async def refresh_session(self):
        pass

    async def list_ricerca_years(self):
        self.calls.append("catalog")
        return self.years

    async def export_ricerca_avvisi(self, year):
        self.calls.append(year)
        return ExportPayload(workbook(self.rows, footer=True), len(self.rows))


class Drive:
    def __init__(self):
        self.files = {}
        self.uploads = 0
        self.fail = False

    async def ensure_folder(self, name, parent):
        if self.fail:
            raise TimeoutError("drive unavailable")
        return "folder"

    async def find_child(self, name, folder):
        return self.files.get(name)

    async def upload_file(self, name, folder, content, mime):
        self.uploads += 1
        self.files[name] = "file-" + str(self.uploads)
        return self.files[name]

    async def replace_or_upload(self, *args):
        return "manifest"


def deps(rows=None):
    return SimpleNamespace(
        exports=Exports(rows), drive=Drive(), parent="root", policy=RetryPolicy(1, 0)
    )


def execute(db, config, dependencies, now=NOW, revision=0):
    cycle = begin_cycle(db, config, now, revision)
    asyncio.run(c.execute_cycle(db, cycle, dependencies, config, now))
    return cycle


def test_shadow_baseline_change_and_repeat(db, config):
    dependencies = deps()
    first = execute(db, config, dependencies)
    assert first.status == "validated" and first.report["baseline"]
    assert db.scalars(select(IncrementalChange)).all() == []
    # Same day retry does no external work.
    execute(db, config, dependencies)
    assert dependencies.exports.calls == ["catalog", "2025"]
    assert dependencies.drive.uploads == 1
    # Re-archiving an already receipted artifact also avoids a duplicate upload.
    asyncio.run(c.archive(db, first, dependencies.drive, "root", config, dependencies.policy))
    assert dependencies.drive.uploads == 1
    second = execute(
        db, config, deps([raw_row(Riscosso="10,00", Differenza="990,00")]), NOW + timedelta(days=1)
    )
    changes = db.scalars(select(IncrementalChange)).all()
    assert len(changes) == 1 and changes[0].status == "shadow"
    assert changes[0].action == "summary" and changes[0].fields["Riscosso"] == ["0.00", "10.00"]
    assert db.get(IncrementalHead, 1).cycle_id == second.id
    assert db.scalars(select(AnagraficaPaymentNotice)).all() == []
    assert first.artifacts["2025"]["sha256"] != second.artifacts["2025"]["sha256"]
    with pytest.raises(SnapshotInvalid, match="cycle_mode"):
        begin_cycle(db, config.model_copy(update={"mode": "active"}), NOW)
    first.status = "partial"
    with pytest.raises(SnapshotInvalid, match="obsolete"):
        promote(db, first, config, NOW)
    db.rollback()


def test_drive_unavailable_retry_reuses_frozen_original(db, config):
    dependencies = deps()
    dependencies.drive.fail = True
    cycle = begin_cycle(db, config, NOW)
    with pytest.raises(TimeoutError):
        asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
    assert cycle.status == "partial" and not db.get(IncrementalHead, 1).cycle_id
    assert cycle.artifacts["2025"]["rows"]
    dependencies.drive.fail = False
    dependencies.exports.rows = [raw_row(Riscosso="10,00")]
    asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
    assert cycle.rows[NOTICE]["Riscosso"] == "0.00"
    assert dependencies.exports.calls == ["catalog", "2025"]


def test_exhausted_cycle_is_failed_without_advancing_head(db, config):
    dependencies = deps()
    dependencies.drive.fail = True
    config.max_attempts = 1
    cycle = begin_cycle(db, config, NOW)
    with pytest.raises(TimeoutError):
        asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
    assert cycle.status == "failed" and db.get(IncrementalHead, 1).cycle_id is None


def test_special_role_catalog_is_not_coerced_to_ordinary_year(db, config):
    dependencies = deps([raw_row(Anno="9926", CodFisc=None)])
    dependencies.exports.years = ["9926"]
    cycle = execute(db, config, dependencies)
    assert cycle.status == "validated" and cycle.rows[NOTICE]["Anno"] == "9926"
    assert cycle.rows[NOTICE]["CodFisc"] is None
    assert not db.scalars(select(IncrementalChange)).all()


def test_crash_after_upload_before_receipt_is_idempotent(db, config, monkeypatch):
    dependencies = deps()
    cycle = begin_cycle(db, config, NOW)
    asyncio.run(c.collect(db, cycle, dependencies.exports, config, dependencies.policy))
    real_commit = db.commit
    fail = True

    def crash():
        nonlocal fail
        if fail:
            fail = False
            raise RuntimeError("simulated crash")
        real_commit()

    monkeypatch.setattr(db, "commit", crash)
    with pytest.raises(RuntimeError):
        asyncio.run(c.archive(db, cycle, dependencies.drive, "root", config, dependencies.policy))
    db.rollback()
    monkeypatch.setattr(db, "commit", real_commit)
    asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
    assert cycle.status == "validated" and dependencies.drive.uploads == 1


def test_crash_diff_transaction_does_not_promote(db, config, monkeypatch):
    execute(db, config, deps())
    cycle = begin_cycle(db, config, NOW + timedelta(days=1))
    dependencies = deps([raw_row(StatoPag="1")])
    asyncio.run(c.collect(db, cycle, dependencies.exports, config, dependencies.policy))
    asyncio.run(c.archive(db, cycle, dependencies.drive, "root", config, dependencies.policy))
    previous = db.get(IncrementalHead, 1).cycle_id
    real_commit = db.commit
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("crash")))
    with pytest.raises(RuntimeError):
        promote(db, cycle, config, NOW + timedelta(days=1))
    db.rollback()
    assert db.get(IncrementalHead, 1).cycle_id == previous
    assert db.scalars(select(IncrementalChange)).all() == []
    monkeypatch.setattr(db, "commit", real_commit)
    promote(db, cycle, config, NOW + timedelta(days=1))
    promote(db, cycle, config, NOW + timedelta(days=1))
    assert len(db.scalars(select(IncrementalChange)).all()) == 1


@pytest.mark.parametrize(
    "problem",
    [
        "empty",
        "bad_year",
        "invalid_catalog",
        "schema",
        "integrity",
        "decode_resume",
        "archive_integrity",
    ],
)
def test_invalid_cycles_never_promote(db, config, problem, monkeypatch):
    dependencies = deps([] if problem == "empty" else None)
    cycle = begin_cycle(db, config, NOW)
    if problem == "bad_year":
        dependencies.exports.rows = [raw_row(Anno="9926")]
    if problem == "invalid_catalog":
        dependencies.exports.years = ["2025", "2025"]
    if problem == "schema":
        monkeypatch.setattr(
            c,
            "decode_workbook",
            lambda *a: (_ for _ in ()).throw(SnapshotInvalid("missing_columns")),
        )
    if problem in {"integrity", "decode_resume", "archive_integrity"}:
        asyncio.run(c.collect(db, cycle, dependencies.exports, config, dependencies.policy))
        artifact = cycle.artifacts["2025"]
        if problem == "decode_resume":
            artifact.pop("rows")
            cycle.artifacts = {"2025": dict(artifact)}
            db.commit()
        else:
            from pathlib import Path

            Path(artifact["path"]).write_bytes(b"corrupt")
            if problem == "integrity":
                with pytest.raises(SnapshotInvalid):
                    c.decode_artifact(db, cycle, "2025", config)
    if problem == "decode_resume":
        asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
        assert cycle.status == "validated"
        return
    with pytest.raises(SnapshotInvalid):
        asyncio.run(c.execute_cycle(db, cycle, dependencies, config, NOW))
    assert cycle.status == "invalid" and not db.get(IncrementalHead, 1).cycle_id


def test_ordinary_observation_and_private_storage(db, config, owner):
    first = execute(db, config, deps())
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id=NOTICE,
            subject_id=owner.id,
            raw_row_json=raw_row(Riscosso="10,00"),
        )
    )
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass", source_notice_id="not-exported", raw_row_json={}
        )
    )
    db.commit()
    assert c.shadow_observation(db, first)["unexplained_unchanged"] == 1
    notice = db.scalar(
        select(AnagraficaPaymentNotice).where(AnagraficaPaymentNotice.source_notice_id == NOTICE)
    )
    notice.raw_row_json = raw_row(Riscosso="bad")
    db.commit()
    assert c.shadow_observation(db, first)["invalid_registry_rows"] == 1
    notice.raw_row_json = raw_row()
    db.commit()
    assert c.shadow_observation(db, first)["matched"] == 1
    # A change to stored partitario content with an unchanged Excel is surfaced.
    first.report = {"ordinary_sync_comparison": c.shadow_observation(db, first)}
    db.commit()
    notice.raw_detail_json = {"partitario": {"changed": True}}
    db.commit()
    assert c.shadow_observation(db, first)["heavy_changed_without_excel_change"] == 1
    changed_cycle = begin_cycle(db, config, NOW + timedelta(days=1))
    changed_cycle.rows = {NOTICE: {**first.rows[NOTICE], "Carico": "2000.00"}}
    assert c.shadow_observation(db, changed_cycle)["heavy_changed_without_excel_change"] == 0
    sha, path = save_original(config.root, b"one")
    assert path.stat().st_mode & 0o777 == 0o600
    assert save_original(config.root, b"one")[0] == sha
    path.write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="integrity"):
        save_original(config.root, b"one")


def test_fake_http_export_and_quantitative_plan(db, config):
    import httpx

    from app.modules.elaborazioni.capacitas.apps.incass.exports import InCassExportClient

    rows = [raw_row(Avviso=f"02025{index:010d}") for index in range(1000)]
    requests = []

    def server(request):
        requests.append(request)
        if request.url.path.endswith("ricercaAvvisi.aspx"):
            return httpx.Response(
                200,
                text='<select id="ContentMain_ddlAnno"><option value="2025">2025</option></select>',
            )
        if request.method == "POST":
            return httpx.Response(200, text="SI")
        return httpx.Response(
            200,
            content=workbook(rows),
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
        )

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(server)) as http:
            manager = SimpleNamespace(
                get_http_client=lambda: http, get_token=lambda: "synthetic-token"
            )
            exports = InCassExportClient(manager, progress_timeout_seconds=30)
            exports.refresh_session = Exports().refresh_session
            dependencies = deps()
            dependencies.exports = exports
            first = begin_cycle(db, config, NOW)
            await c.execute_cycle(db, first, dependencies, config, NOW)
            assert len(first.rows) == 1000
            rows[0]["Riscosso"] = "10,00"
            rows[0]["Differenza"] = "990,00"
            rows[1]["IDLista"] = "2"
            second = begin_cycle(db, config, NOW + timedelta(days=1))
            await c.execute_cycle(db, second, dependencies, config, NOW + timedelta(days=1))
            assert second.report["counts"] == {"changed": 2, "unchanged": 998}
            assert second.report["planned"] == 2
            assert second.report["unchanged_notices_without_refresh"] == 998
            assert second.report["hypothetical_full_refresh_requests_avoided"] == 1996
            assert all(item.action == "summary" for item in db.scalars(select(IncrementalChange)))

    asyncio.run(exercise())
    assert len(requests) == 6  # Catalog + export POST + XLSX GET, for each day.
