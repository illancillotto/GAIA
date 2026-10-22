from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
from zipfile import ZipFile

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=")
os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest-worker.db")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import step_sync
from app.core.database import Base
from app.modules.elaborazioni.step.credentials import create_credential
from app.modules.elaborazioni.step.models import (
    StepContribuente,
    StepCredential,
    StepDocumento,
    StepRuoloLink,
    StepSyncJob,
)
from app.modules.elaborazioni.step.schemas import StepCredentialCreate
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.services.catasto_credentials import get_credential_fernet
from step_client import StepLoginError
from step_rules import StepIntegrityError

PDF = b"%PDF-1.4\nlive\n%%EOF"
_TABLES = (
    "step_credentials",
    "step_sync_jobs",
    "step_contribuenti",
    "step_documenti",
    "step_tributi",
    "step_pagamenti",
    "step_observations",
    "step_ruolo_links",
    "ruolo_import_jobs",
    "ruolo_avvisi",
    "ruolo_notice_documents",
    "ruolo_notice_positions",
    "ruolo_notice_recoveries",
    "ruolo_notice_audit",
)


@pytest.fixture
def factory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> sessionmaker:
    monkeypatch.setenv("STEP_DOCUMENT_STORAGE_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("STEP_IMPORT_ROOT", str(tmp_path / "import"))
    get_credential_fernet.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in _TABLES])
    return sessionmaker(bind=engine, expire_on_commit=False)


def _summary(cf: str, **overrides) -> dict:
    return {
        "COD_ENT": "14215",
        "COD_FIS_NEW": cf,
        "DENOMINAZIONE": cf,
        "NUMERODOC": "1",
        "PAGATO": "0,00",
        "RESIDUO": "1,00",
        **overrides,
    }


def _scheda(summary: dict, *, with_pdf: bool = True) -> dict:
    document = {
        "COD_ENT": "14215",
        "NUM_DOC": f"D-{summary['COD_FIS_NEW']}",
        "PRG_COO": 1,
        "NUM_TRIB": "1",
    }
    tributo = {
        "NUM_DOC": document["NUM_DOC"],
        "ANNO_RIF": "2019",
        "IMP_CAR": "5,00",
        "DES_TRI1": "Avv. N. 020190006018040 Not.",
    }
    pdf = (
        {"status": "downloaded", "content": PDF, "originalFilename": "Doc.pdf"}
        if with_pdf
        else {"status": "unavailable", "reason": "assente"}
    )
    return {
        "summary": summary,
        "anagrafica": {"Codice fiscale": summary["COD_FIS_NEW"]},
        "situazioneContabile": {},
        "sections": [
            {
                "section": "Documenti Emessi",
                "fields": [{"name": "NUM_DOC"}, {"name": "NUM_TRIB"}],
                "rows": [document],
            }
        ],
        "documentReconciliation": {"listed": 1, "observed": 1, "status": "matched"},
        "documents": [{"document": document, "tributi": {"rows": [tributo]}, "pdf": pdf}],
    }


class Portal:
    def __init__(self, rows: list[dict], *, page_size: int = 2) -> None:
        self.rows = rows
        self.page_size = page_size
        self.failures: dict[str, Exception] = {}
        self.reject_login = False
        self.logins = 0
        self.closed = 0
        self.extracted: list[str] = []
        self.page_override: dict[int, dict] = {}

    def state(self, page: int) -> dict:
        if page in self.page_override:
            return self.page_override[page]
        start = (page - 1) * self.page_size
        pages = -(-len(self.rows) // self.page_size)
        return {
            "total": len(self.rows),
            "page": page,
            "pages": pages,
            "fields": [],
            "rows": self.rows[start : start + self.page_size],
        }

    def client_class(self, config):
        return FakeClient(self, config)


class FakeClient:
    def __init__(self, portal: Portal, config) -> None:
        self.portal = portal
        self.config = config

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        self.portal.closed += 1

    async def login(self, username, password):
        self.portal.logins += 1
        if self.portal.reject_login:
            raise StepLoginError("credenziali rifiutate")

    async def open_contribuenti(self):
        return self.portal.state(1)

    async def go_to_page(self, target, previous):
        return self.portal.state(target)

    async def extract_scheda(self, summary):
        cf = summary["COD_FIS_NEW"]
        self.portal.extracted.append(cf)
        if cf in self.portal.failures:
            raise self.portal.failures[cf]
        return _scheda(summary, with_pdf=cf != "C3")


def _job(factory, mode: str, requested_by: int | None = None, **payload) -> int:
    with factory() as db:
        if db.scalar(select(StepCredential)) is None:
            create_credential(
                db,
                StepCredentialCreate(
                    label="STEP", username="user", password="pw", portal_url="https://step.example"
                ),
            )
        job = StepSyncJob(
            status="processing", mode=mode, payload_json=payload, requested_by_user_id=requested_by
        )
        db.add(job)
        db.commit()
        return job.id


def _run(factory, job_id: int, portal: Portal | None = None) -> StepSyncJob:
    portal = portal or Portal([])
    asyncio.run(
        step_sync.run_step_job_by_id(
            job_id=job_id, session_factory=factory, headless=True, client_class=portal.client_class
        )
    )
    with factory() as db:
        return db.get(StepSyncJob, job_id)


def test_missing_and_unsupported_jobs(factory) -> None:
    asyncio.run(step_sync.run_step_job_by_id(job_id=999, session_factory=factory, headless=True))
    job = _run(factory, _job(factory, "bogus"))
    assert job.status == "failed" and "non supportata" in job.error_detail


def test_credential_test_marks_credential(factory) -> None:
    portal = Portal([])
    assert _run(factory, _job(factory, "credential_test"), portal).status == "succeeded"
    portal.reject_login = True
    failed = _run(factory, _job(factory, "credential_test"), portal)
    assert failed.status == "failed" and "rifiutate" in failed.error_detail
    with factory() as db:
        credential = db.scalar(select(StepCredential))
        assert credential.consecutive_failures == 1 and credential.last_error


def test_sync_fetches_new_schede_and_skips_unchanged(factory) -> None:
    with factory() as db:
        job = RuoloImportJob(id=uuid.uuid4(), anno_tributario=2019, status="completed")
        db.add_all(
            [
                job,
                RuoloAvviso(
                    id=uuid.uuid4(),
                    import_job_id=job.id,
                    codice_cnc="01.02019000601804",
                    anno_tributario=2019,
                ),
            ]
        )
        db.commit()
    portal = Portal([_summary("C1"), _summary("C2"), _summary("C3")])

    first = _run(factory, _job(factory, "sync"), portal)
    assert first.status == "succeeded", first.result_json
    assert first.result_json["list_rows"] == 3 and first.result_json["new"] == 3
    assert first.result_json["details"] == 3 and first.result_json["links"]["linked"] == 3
    assert portal.extracted == ["C1", "C2", "C3"] and portal.closed == 1
    with factory() as db:
        assert {doc.pdf_status for doc in db.scalars(select(StepDocumento))} == {
            "downloaded",
            "unavailable",
        }

    portal.extracted.clear()
    portal.rows[1] = _summary("C2", RESIDUO="1,01")
    portal.rows[2] = _summary("C3", PAGATO="1,00")
    second = _run(factory, _job(factory, "sync"), portal)
    assert portal.extracted == ["C3"]
    assert (
        second.result_json["summary_changed"] == 2 and second.result_json["not_seen_in_list"] == 0
    )

    portal.extracted.clear()
    listed = _run(factory, _job(factory, "list_only", force_details=True), portal)
    assert (
        listed.status == "succeeded"
        and listed.result_json["details_pending"] == 3
        and portal.extracted == []
    )

    _run(factory, _job(factory, "sync", force_details=True, max_details=1), portal)
    assert portal.extracted == ["C1"]


def test_sync_records_errors_reconnects_and_stops_after_three(factory) -> None:
    rows = [_summary(f"E{index}") for index in range(6)]
    portal = Portal(rows)
    portal.failures = {
        "E0": RuntimeError("timeout"),
        "E2": RuntimeError("a"),
        "E3": RuntimeError("b"),
        "E4": RuntimeError("c"),
    }
    job = _run(factory, _job(factory, "sync"), portal)

    assert job.status == "completed_with_errors"
    errors = job.result_json["errors"]
    assert [item.get("codice_fiscale") for item in errors] == ["E0", "E2", "E3", "E4", None]
    assert errors[-1]["remaining"] == 1
    assert portal.extracted == ["E0", "E1", "E2", "E3", "E4"]
    assert portal.logins == 4
    with factory() as db:
        assert [
            row.codice_fiscale
            for row in db.scalars(
                select(StepContribuente).where(StepContribuente.detail_fingerprint.is_not(None))
            )
        ] == ["E1"]


def test_sync_detects_moved_rows(factory) -> None:
    portal = Portal([_summary("M1"), _summary("M2"), _summary("M3")])
    original = portal.state
    navigations: list[int] = []

    def moved(page):
        # After the list scan the first page shows a different, shorter list.
        if page == 1 and navigations:
            return {**original(1), "rows": [_summary("X")]}
        return original(page)

    async def go_to_page(self, target, previous):
        navigations.append(target)
        return self.portal.state(target)

    portal.state = moved
    FakeClient.go_to_page, previous = go_to_page, FakeClient.go_to_page
    try:
        job = _run(factory, _job(factory, "sync"), portal)
    finally:
        FakeClient.go_to_page = previous
    assert job.status == "completed_with_errors"
    assert [item["codice_fiscale"] for item in job.result_json["errors"]] == ["M1", "M2"]
    assert all("cambiati" in item["error"] for item in job.result_json["errors"])
    assert portal.extracted == ["M3"]


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({2: {"total": 3, "page": 1, "pages": 2, "fields": [], "rows": [{}]}}, "attesa 2"),
        (
            {2: {"total": 3, "page": 2, "pages": 2, "fields": [], "rows": [_summary("D1")]}},
            "duplicato",
        ),
    ],
)
def test_list_scan_integrity_errors(factory, override, message) -> None:
    portal = Portal([_summary("D1"), _summary("D2"), _summary("D3")])
    portal.page_override = override
    job = _run(factory, _job(factory, "list_only"), portal)
    assert job.status == "failed" and message in job.error_detail


def test_list_scan_requires_every_contribuente(factory, monkeypatch: pytest.MonkeyPatch) -> None:
    portal = Portal([_summary("T1"), _summary("T2")])
    original = step_sync._LiveSync._store_page

    def skip_second_page(self, state, page_number, seen):
        original(self, state, page_number, seen)
        seen.discard("14215:T1")

    monkeypatch.setattr(step_sync._LiveSync, "_store_page", skip_second_page)
    job = _run(factory, _job(factory, "list_only"), portal)
    assert job.status == "failed" and "non coincide" in job.error_detail
    assert isinstance(StepIntegrityError("x"), RuntimeError)


def test_progress_is_published_every_ten_pages_and_25_schede(factory) -> None:
    portal = Portal([_summary(f"P{index:02d}") for index in range(26)], page_size=1)
    job = _run(factory, _job(factory, "sync"), portal)
    assert job.status == "succeeded"
    assert job.result_json["progress"]["phase"] == "schede" and job.result_json["details"] == 26


def _archive(path, summary: dict) -> None:
    scheda = _scheda(summary)
    entry = scheda["documents"][0]
    content = entry["pdf"].pop("content")
    entry["pdf"].update({"sha256": hashlib.sha256(content).hexdigest(), "file": "doc.pdf"})
    with ZipFile(path, "w") as archive:
        archive.writestr("contributors/a/scheda.json", json.dumps(scheda))
        archive.writestr("contributors/a/doc.pdf", content)
        archive.writestr(
            "verification.json",
            json.dumps(
                {
                    "contributors": 1,
                    "documents": 1,
                    "tributi": 1,
                    "pdfs": 1,
                    "unavailablePdfs": 0,
                    "sha256": "s",
                }
            ),
        )


def test_archive_import_and_relink_jobs(factory, tmp_path) -> None:
    (tmp_path / "import").mkdir()
    _archive(tmp_path / "import" / "raccolta.zip", _summary("A1"))
    imported = _run(factory, _job(factory, "archive_import", archive_name="raccolta.zip"))
    assert imported.status == "succeeded" and imported.result_json["imported"] == 1
    assert imported.result_json["progress"]["total"] == 1

    missing = _run(factory, _job(factory, "archive_import", archive_name="missing.zip"))
    assert missing.status == "failed"

    with factory() as db:
        job = RuoloImportJob(id=uuid.uuid4(), anno_tributario=2019, status="completed")
        db.add_all(
            [
                job,
                RuoloAvviso(
                    id=uuid.uuid4(),
                    import_job_id=job.id,
                    codice_cnc="01.02019000601804",
                    anno_tributario=2019,
                ),
            ]
        )
        db.commit()
    relinked = _run(factory, _job(factory, "relink"))
    assert relinked.result_json["links"]["linked"] == 1
    with factory() as db:
        assert db.scalar(select(StepRuoloLink)).status == "linked"


def test_error_report_is_capped_and_failed_reconnect_is_closed(
    factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(step_sync, "_MAX_REPORTED_ERRORS", 1)
    portal = Portal([_summary("R1"), _summary("R2"), _summary("R3")])
    portal.failures = {"R1": RuntimeError("one")}
    created: list[FakeClient] = []

    def client_class(config):
        if created:
            raise RuntimeError("browser non avviabile")
        created.append(FakeClient(portal, config))
        return created[-1]

    job_id = _job(factory, "sync")
    asyncio.run(
        step_sync.run_step_job_by_id(
            job_id=job_id, session_factory=factory, headless=True, client_class=client_class
        )
    )
    with factory() as db:
        job = db.get(StepSyncJob, job_id)
    assert job.status == "failed" and "non avviabile" in job.error_detail
    assert portal.closed == 1

    monkeypatch.setattr(step_sync, "MAX_CONSECUTIVE_SCHEDA_FAILURES", 5)
    portal = Portal([_summary("S1"), _summary("S2")])
    portal.failures = {"S1": RuntimeError("one"), "S2": RuntimeError("two")}
    capped = _run(factory, _job(factory, "sync"), portal)
    assert [item["codice_fiscale"] for item in capped.result_json["errors"]] == ["S1"]


def test_register_projection_runs_after_linking_jobs(
    factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STEP_REGISTER_ACTOR_USER_ID", raising=False)
    skipped = _run(factory, _job(factory, "relink"))
    assert skipped.result_json["register"] == {
        "skipped": "STEP_REGISTER_ACTOR_USER_ID non configurato"
    }

    by_user = _run(factory, _job(factory, "relink", requested_by=5))
    assert by_user.result_json["register"]["updated"] == 0

    monkeypatch.setenv("STEP_REGISTER_ACTOR_USER_ID", "9")
    from_env = _run(factory, _job(factory, "relink"))
    assert "skipped" not in from_env.result_json["register"]

    listed = _run(factory, _job(factory, "list_only"), Portal([_summary("L1")]))
    assert "register" not in listed.result_json
