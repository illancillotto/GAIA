from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.capacitas import CapacitasCredential, CapacitasInCassSyncJob
from app.modules.elaborazioni.capacitas import (
    recovery_identity as identity,
)
from app.modules.elaborazioni.capacitas import (
    recovery_ruolo as ruolo,
)
from app.modules.elaborazioni.capacitas import (
    recovery_service as service,
)
from app.modules.elaborazioni.capacitas import (
    recovery_sources as sources,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasAnagraficaDetail,
    CapacitasAnagraficaHistoryImportItemResult,
    CapacitasCertificatoTerreno,
    CapacitasInCassMailingSubjectRow,
    CapacitasInCassNoticeRow,
    CapacitasInCassSearchResult,
    CapacitasIntestatario,
    CapacitasSearchResult,
    CapacitasStoricoAnagraficaRow,
    CapacitasTerrenoCertificato,
    CapacitasTerrenoDetail,
)
from app.modules.elaborazioni.capacitas.recovery_manifest import RecoveryManifest
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.services.incass_read_model import materialize_incass_notice_header
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.scripts import capacitas_full_recovery as cli
from app.services.elaborazioni_capacitas_incass import (
    load_incass_ruolo_subject_ids,
    prepare_incass_sync_jobs_for_recovery,
)

CF = "CDNNTN55T24F698D"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    tables = [
        ApplicationUser.__table__,
        CapacitasCredential.__table__,
        AnagraficaSubject.__table__,
        AnagraficaPerson.__table__,
        AnagraficaCompany.__table__,
        AnagraficaPaymentNotice.__table__,
        CapacitasInCassSyncJob.__table__,
        RuoloImportJob.__table__,
        RuoloAvviso.__table__,
        RuoloPartita.__table__,
        RuoloParticella.__table__,
    ]
    AnagraficaSubject.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


def person(db, identifier=CF, **fields):
    subject = AnagraficaSubject(subject_type="person", source_name_raw="CADONI ANTONIO", **fields)
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id, codice_fiscale=identifier, cognome="CADONI", nome="ANTONIO"
        )
    )
    db.flush()
    return subject


def company(db, vat="01234567890", tax="09876543210"):
    subject = AnagraficaSubject(subject_type="company", source_name_raw="AZIENDA")
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaCompany(
            subject_id=subject.id, ragione_sociale="AZIENDA", partita_iva=vat, codice_fiscale=tax
        )
    )
    db.flush()
    return subject


def notice(db, subject, **fields):
    result = AnagraficaPaymentNotice(
        subject_id=subject.id,
        source_system="incass",
        source_notice_id="020240000890170",
        anno="2024",
        codice_fiscale=CF,
        **fields,
    )
    db.add(result)
    db.flush()
    return result


def test_registry_scan_includes_cadoni_without_any_role(db):
    subject = person(db)
    assert load_incass_ruolo_subject_ids(
        db, anno=None, limit_subjects=None, exclude_synced_subjects=False
    ) == [subject.id]
    assert identity.resolve_recovery_subjects(db, [subject.id], 1)[0][1:] == (CF, "CADONI ANTONIO")
    assert identity.resolve_recovery_subjects(db, [uuid.uuid4()]) == []


def test_document_or_death_review_flag_does_not_hide_verified_identity(db):
    subject = person(db, requires_review=True)
    eligible, blocked = identity.audit_recovery_subjects(db)
    assert blocked == []
    assert eligible[0].requires_review is True
    assert load_incass_ruolo_subject_ids(
        db, anno=None, limit_subjects=None, exclude_synced_subjects=False
    ) == [subject.id]
    assert subject.requires_review is True


@pytest.mark.parametrize(
    "reason", ["duplicate", "both", "missing", "type", "blank", "invalid", "collision"]
)
def test_registry_audit_blocks_noncanonical_identities(db, reason):
    subject = person(db)
    if reason == "duplicate":
        subject.status = "duplicate"
    elif reason == "both":
        db.add(
            AnagraficaCompany(
                subject_id=subject.id, ragione_sociale="CONFLICT", partita_iva="01234567890"
            )
        )
    elif reason == "missing":
        db.delete(db.get(AnagraficaPerson, subject.id))
    elif reason == "type":
        subject.subject_type = "company"
    elif reason == "blank":
        db.get(AnagraficaPerson, subject.id).codice_fiscale = " "
    elif reason == "invalid":
        db.get(AnagraficaPerson, subject.id).codice_fiscale = "INVALID"
    else:
        company(db, tax=CF)
    db.flush()
    eligible, blocked = identity.audit_recovery_subjects(db, [subject.id])
    assert eligible == []
    assert blocked[0]["subject_id"] == str(subject.id)


def test_company_searches_both_identifiers_and_inactive_person_is_historical(db):
    company_subject = company(db)
    person(db, status="inactive")
    records, blocked = identity.audit_recovery_subjects(db)
    assert blocked == []
    assert next(
        record for record in records if record.subject_id == company_subject.id
    ).identifiers == ("01234567890", "09876543210")


def test_recent_zero_result_is_not_scanned_again_but_failed_item_is(db):
    checked = person(db)
    failed = company(db)
    now = datetime.now(UTC)
    db.add(
        CapacitasInCassSyncJob(
            status="completed_with_errors",
            completed_at=now,
            result_json={
                "items": [
                    {"subject_id": str(checked.id), "status": "succeeded", "notices_found": 0},
                    {"subject_id": str(failed.id), "status": "failed"},
                    "bad-item",
                ]
            },
        )
    )
    db.add(CapacitasInCassSyncJob(status="succeeded", completed_at=now, result_json=[]))
    db.flush()
    assert identity.load_registry_incass_subject_ids(
        db, limit=None, exclude_synced=False, refreshed_after=now - timedelta(hours=6)
    ) == [failed.id]
    notice(db, failed)
    assert identity.load_registry_incass_subject_ids(
        db, limit=1, exclude_synced=True, refreshed_after=None
    ) == [checked.id]
    assert identity.load_registry_incass_subject_ids(
        db, limit=None, exclude_synced=False, refreshed_after=None
    )


def test_notice_owner_cannot_be_reassigned(db):
    subject = person(db)
    row = notice(db, subject)
    identity.assert_notice_owner(None, subject.id)
    identity.assert_notice_owner(row, subject.id)
    with pytest.raises(ValueError):
        identity.assert_notice_owner(row, uuid.uuid4())


def test_backend_restart_does_not_take_over_external_recovery_job(db):
    job = CapacitasInCassSyncJob(
        status="processing", payload_json={"recovery_task_key": "campaign-task"}
    )
    db.add(job)
    db.flush()
    assert prepare_incass_sync_jobs_for_recovery(db) == []
    assert job.status == "processing"


def test_explicit_year_harvest_preserves_filters_and_limits(db):
    subject = person(db)
    other = company(db)
    job = RuoloImportJob(anno_tributario=2024)
    db.add(job)
    db.flush()
    db.add_all(
        [
            RuoloAvviso(
                import_job_id=job.id, codice_cnc="ONE", anno_tributario=2024, subject_id=subject.id
            ),
            RuoloAvviso(
                import_job_id=job.id, codice_cnc="TWO", anno_tributario=2024, subject_id=other.id
            ),
        ]
    )
    notice(db, subject, synced_at=datetime.now(UTC))
    db.flush()
    kwargs = {"anno": 2024, "limit_subjects": None, "exclude_synced_subjects": False}
    assert set(load_incass_ruolo_subject_ids(db, **kwargs)) == {subject.id, other.id}
    assert load_incass_ruolo_subject_ids(
        db, **(kwargs | {"exclude_synced_subjects": True, "limit_subjects": 1})
    ) == [other.id]
    assert load_incass_ruolo_subject_ids(
        db, **(kwargs | {"stale_synced_before": datetime.now(UTC) - timedelta(hours=1)})
    ) == [other.id]


def test_historical_notice_with_prefix_one_is_materialized(db):
    subject = person(db)
    row = notice(db, subject)
    row.source_notice_id = "120170001949090"
    row.anno = "2017"
    assert materialize_incass_notice_header(db, row).codice_cnc == "01.12017000194909"


def test_manifest_is_durable_and_retry_does_not_repeat_success(tmp_path):
    path = tmp_path / "manifest.sqlite"
    manifest = RecoveryManifest(path)
    manifest.add("subject", "incass", "all", {"identifiers": [CF]})
    manifest.add("subject", "incass", "all", {"replacement": True})
    task = manifest.next_task("subject")
    assert task["payload"] == {"identifiers": [CF]}
    manifest.finish(task, error="network")
    manifest.retry_failed()
    manifest.finish(manifest.next_task(), result={"zero_results": True})
    manifest.close()
    resumed = RecoveryManifest(path)
    assert resumed.next_task() is None
    resumed.retry_failed()
    assert resumed.summary() == [{"stage": "incass", "status": "succeeded", "count": 1}]
    resumed.close()


@pytest.mark.parametrize("values", [(None,), ("WRONG",), (CF, "WRONG")])
def test_source_identity_is_fail_closed(values):
    with pytest.raises(ValueError):
        sources.assert_source_identity(values, (CF,))
    sources.assert_source_identity((CF.lower(), " "), (CF,))


@pytest.mark.anyio
async def test_dual_identifier_search_deduplicates_notices_and_mailing(monkeypatch):
    identifiers = ("01234567890", "09876543210")
    search = AsyncMock(
        return_value=CapacitasInCassSearchResult(
            total=1,
            rows=[
                CapacitasInCassNoticeRow(avviso="020240000890170", codice_fiscale=identifiers[0])
            ],
        )
    )
    mailing = AsyncMock(
        return_value=[
            CapacitasInCassMailingSubjectRow(external_id="rubrica", codice_fiscale=identifiers[1])
        ]
    )
    monkeypatch.setattr(sources.InCassClient, "search_notices", search)
    monkeypatch.setattr(sources.InCassClient, "search_mailing_subjects", mailing)
    client = sources.CanonicalInCassClient(None, identifiers)
    assert (await client.search_notices(identifiers[0])).total == 1
    assert len(await client.search_mailing_subjects(identifiers[0])) == 1
    assert search.await_count == mailing.await_count == 2


@pytest.mark.anyio
@pytest.mark.parametrize("problem", ["truncated", "missing_reference", "missing_mailing_id"])
async def test_source_search_rejects_incomplete_results(monkeypatch, problem):
    client = sources.CanonicalInCassClient(None, (CF,))
    if problem == "missing_mailing_id":
        monkeypatch.setattr(
            sources.InCassClient,
            "search_mailing_subjects",
            AsyncMock(return_value=[CapacitasInCassMailingSubjectRow(codice_fiscale=CF)]),
        )
        with pytest.raises(ValueError):
            await client.search_mailing_subjects(CF)
    else:
        result = CapacitasInCassSearchResult(
            total=1,
            rows=[] if problem == "truncated" else [CapacitasInCassNoticeRow(codice_fiscale=CF)],
        )
        monkeypatch.setattr(sources.InCassClient, "search_notices", AsyncMock(return_value=result))
        with pytest.raises(ValueError):
            await client.search_notices(CF)


@pytest.mark.anyio
async def test_discovery_checks_complete_source_and_keeps_all_contexts():
    row = CapacitasAnagrafica(
        id_ana="idxana", codice_fiscale=CF, cco="55", com="165", pvc="097", fraz="31"
    )
    client = SimpleNamespace(
        search_by_cf=AsyncMock(return_value=CapacitasSearchResult(total=1, rows=[row]))
    )
    subject = identity.RecoverySubject(uuid.uuid4(), (CF,), "CADONI", "person")
    rows = await sources.discover_involture(client, subject)
    assert sources.certificate_context(rows[0])["ccs"] == "00000"
    assert rows[0].source_search_codici_fiscali == [CF]
    with pytest.raises(ValueError):
        sources.certificate_context(CapacitasAnagrafica())
    client.search_by_cf.return_value = CapacitasSearchResult(total=2, rows=[row])
    with pytest.raises(ValueError):
        await sources.discover_involture(client, subject)


@pytest.mark.anyio
async def test_certificate_is_validated_before_persisting_and_fetched_once(monkeypatch):
    certificate = CapacitasTerrenoCertificato(
        intestatari=[CapacitasIntestatario(codice_fiscale=CF.lower())]
    )
    fetch = AsyncMock(return_value=certificate)
    monkeypatch.setattr(sources.InVoltureClient, "fetch_certificato", fetch)
    archive = MagicMock()
    client = sources.ValidatedInVoltureClient(None, (CF,), archive)
    assert await client.fetch_certificato(cco="55") == certificate
    assert fetch.await_count == 1
    assert archive.call_count == 2
    certificate.intestatari = []
    with pytest.raises(ValueError):
        await client.fetch_certificato(cco="55")


@pytest.mark.anyio
@pytest.mark.parametrize("problem", [None, "missing_id", "missing_foglio", "missing_particella"])
async def test_certificate_uses_authoritative_parcel_details(monkeypatch, problem):
    parcel = CapacitasCertificatoTerreno(
        external_row_id=None if problem == "missing_id" else "parcel-id",
        foglio="66",
        particella="16",
        sub="2.062",
    )
    certificate = CapacitasTerrenoCertificato(
        intestatari=[CapacitasIntestatario(codice_fiscale=CF)], terreni=[parcel]
    )
    monkeypatch.setattr(
        sources.InVoltureClient, "fetch_certificato", AsyncMock(return_value=certificate)
    )
    detail = CapacitasTerrenoDetail(
        foglio=None if problem == "missing_foglio" else "66",
        particella=None if problem == "missing_particella" else "16",
    )
    fetch_detail = AsyncMock(return_value=detail)
    monkeypatch.setattr(sources.InVoltureClient, "fetch_terreno_detail", fetch_detail)
    archive = MagicMock()
    client = sources.ValidatedInVoltureClient(None, (CF,), archive)
    if problem:
        with pytest.raises(ValueError):
            await client.fetch_certificato(cco="55")
        assert archive.call_count == 1
    else:
        result = await client.fetch_certificato(cco="55")
        assert result.terreni[0].sub is None
        assert archive.call_args.args[0]["terreni"][0]["sub"] is None
        fetch_detail.assert_awaited_once_with(external_row_id="parcel-id")
        detail.sub = "7"
        assert (await client.fetch_certificato(cco="55")).terreni[0].sub == "7"


@pytest.fixture
def runner(db, tmp_path):
    manifest = RecoveryManifest(tmp_path / "manifest.sqlite")
    result = service.RecoveryRunner(db, None, manifest, tmp_path, 1)
    yield result
    manifest.close()


def make_task(subject, stage, **payload):
    return {
        "subject_id": str(subject.subject_id),
        "stage": stage,
        "task_key": f"{subject.subject_id}:{stage}:all",
        "payload": {"identifiers": list(subject.identifiers), **payload},
    }


@pytest.mark.anyio
async def test_runner_revalidates_identity_and_commits_only_verified_task(db, runner):
    subject = person(db)
    record = identity.audit_recovery_subjects(db)[0][0]
    task = make_task(record, "07_ruolo")
    runner.handlers["07_ruolo"] = AsyncMock(return_value={"ok": True})
    assert await runner.execute(task) == {"ok": True}
    task["payload"]["identifiers"] = ["WRONG"]
    with pytest.raises(ValueError, match="cambiata"):
        await runner.execute(task)
    db.get(AnagraficaSubject, subject.id).status = "duplicate"
    db.flush()
    with pytest.raises(ValueError, match="non utilizzabile"):
        await runner.execute(task)
    missing = make_task(
        identity.RecoverySubject(uuid.uuid4(), (CF,), "missing", "person"), "07_ruolo"
    )
    with pytest.raises(ValueError):
        await runner.execute(missing)


@pytest.mark.anyio
async def test_discovery_archives_and_seeds_distinct_work(db, runner, monkeypatch):
    person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    row = CapacitasAnagrafica(
        id_ana="idx", codice_fiscale=CF, cco="55", com="165", pvc="097", fraz="31"
    )
    monkeypatch.setattr(
        service,
        "discover_involture",
        AsyncMock(return_value=[row, row.model_copy(update={"id_ana": None})]),
    )
    result = await runner.discovery(make_task(subject, "02_discovery"), subject)
    assert result == {"source_rows": 2}
    assert len(runner.manifest.summary()) == 3
    assert list((runner.output / str(subject.subject_id)).glob("*.json"))


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["person", "company", "empty"])
async def test_history_archives_all_records_and_reuses_canonical_history_import(
    db, runner, monkeypatch, kind
):
    company(db) if kind == "company" else person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    history = (
        []
        if kind == "empty"
        else [
            CapacitasStoricoAnagraficaRow(
                history_id="historic", codice_fiscale=subject.identifiers[0]
            )
        ]
    )
    runner.involture = SimpleNamespace(
        fetch_anagrafica_history=AsyncMock(return_value=history),
        fetch_anagrafica_detail=AsyncMock(
            return_value=CapacitasAnagraficaDetail(codice_fiscale=subject.identifiers[0])
        ),
    )
    imported = AsyncMock(return_value=CapacitasAnagraficaHistoryImportItemResult(status="imported"))
    monkeypatch.setattr(service, "_import_single_item", imported)
    result = await runner.history(make_task(subject, "03_history", idxana="idx"), subject)
    assert (
        result.get("status") == "imported" if kind != "company" else result["archived_records"] == 1
    )


@pytest.mark.anyio
async def test_certificate_seeds_all_parcels_and_rejects_invalid_keys(db, runner, monkeypatch):
    person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    certificate = CapacitasTerrenoCertificato(
        comune_label="ARBOREA", terreni=[CapacitasCertificatoTerreno(foglio="3", particella="10")]
    )
    monkeypatch.setattr(
        service,
        "sync_certificato_snapshot",
        AsyncMock(return_value=(certificate, SimpleNamespace(id=uuid.uuid4()))),
    )
    task = make_task(subject, "04_certificates", context={"fra": "31"}, row={"comune": "ARBOREA"})
    assert (await runner.certificates(task, subject))["terreni"] == 1
    assert runner.manifest.next_task()["stage"] == "05_terreni"
    certificate.comune_label = None
    certificate.terreni[0].sub = "1"
    await runner.certificates(task, subject)
    certificate.terreni[0].foglio = None
    with pytest.raises(ValueError):
        await runner.certificates(task, subject)


@pytest.mark.anyio
async def test_terreni_and_domande_propagate_incomplete_results(db, runner, monkeypatch):
    person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    result = MagicMock(failed_items=0)
    result.model_dump.return_value = {"imported_rows": 1}
    monkeypatch.setattr(service, "sync_terreni_batch", AsyncMock(return_value=result))
    task = make_task(
        subject, "05_terreni", item={"frazione_id": "31", "foglio": "3", "particella": "10"}
    )
    assert (await runner.terreni(task, subject))["imported_rows"] == 1
    assert not service.sync_terreni_batch.await_args.args[2].fetch_certificati
    result.failed_items = 1
    with pytest.raises(RuntimeError, match="imported_rows"):
        await runner.terreni(task, subject)
    scraper = MagicMock()
    scraper.fetch_for_anagrafica_rows = AsyncMock(
        return_value=SimpleNamespace(model_dump=lambda **kwargs: {})
    )
    monkeypatch.setattr(service, "DomandeIrrigueScraper", MagicMock(return_value=scraper))
    from app.modules.catasto.services.domande_irrigue import DomandeIrriguePersistSummary

    summary = DomandeIrriguePersistSummary(1, 1, 1, 0, 0, 0, 0, 0)
    monkeypatch.setattr(
        service, "persist_capacitas_domande_irrigue_batch", MagicMock(return_value=summary)
    )
    task = make_task(subject, "06_domande", row={"codice_fiscale": CF})
    assert (await runner.domande(task, subject))["domande_inserted"] == 1
    monkeypatch.setattr(
        service,
        "persist_capacitas_domande_irrigue_batch",
        MagicMock(return_value=SimpleNamespace(invalid_year_rows=[{}])),
    )
    with pytest.raises(ValueError):
        await runner.domande(task, subject)


@pytest.mark.anyio
async def test_incass_job_is_resumable_and_seeds_role_only_after_success(db, runner, monkeypatch):
    person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    task = make_task(subject, "01_incass")

    async def succeeded(session, client, job):
        job.status = "succeeded"
        job.result_json = {"items": []}
        session.commit()
        return job

    monkeypatch.setattr(service, "run_incass_sync_job", succeeded)
    first = await runner.incass(task, subject)
    assert (await runner.incass(task, subject))["job_id"] == first["job_id"]
    assert runner.manifest.next_task()["stage"] == "07_ruolo"

    async def failed(session, client, job):
        job.status = "failed"
        job.error_detail = None
        return job

    monkeypatch.setattr(service, "run_incass_sync_job", failed)
    with pytest.raises(RuntimeError):
        await runner.incass(task, subject)
    monkeypatch.setattr(
        service, "reconcile_subject_ruolo", lambda session, subject_id: {"reconciled": 1}
    )
    assert await runner.ruolo(task, subject) == {"reconciled": 1}


def test_partitario_reconciliation_is_scoped_and_idempotent(db, monkeypatch):
    subject = person(db)
    row = notice(db, subject)
    row.raw_detail_json = {
        "partitario": {
            "partite": [
                {
                    "codice_partita": "55",
                    "comune_nome": "ARBOREA",
                    "importo_0648_euro": "10.00",
                    "importo_0985_euro": "2.00",
                    "importo_0668_euro": "0",
                    "particelle": [],
                }
            ]
        }
    }
    monkeypatch.setattr(
        "scripts.materialize_ruolo_from_incass._resolve_comune_codice_for_ruolo",
        lambda session, comune: None,
    )
    assert ruolo.reconcile_subject_ruolo(db, subject.id)["notices_reconciled"] == 1
    assert ruolo.reconcile_subject_ruolo(db, subject.id)["notices_reconciled"] == 1
    assert len(db.scalars(select(RuoloPartita)).all()) == 1
    assert db.scalar(select(RuoloAvviso)).importo_totale_euro == 12
    row.raw_detail_json = None
    assert ruolo.reconcile_subject_ruolo(db, subject.id)["notices_without_partite"] == 1
    row.anno = "2525"
    assert ruolo.reconcile_subject_ruolo(db, subject.id)["non_ordinary_notices"] == 1


def test_reconciliation_preserves_existing_parcel_keys_and_handles_invalid_partita(db, monkeypatch):
    subject = person(db)
    row = notice(db, subject)
    avviso = materialize_incass_notice_header(db, row)
    partita = RuoloPartita(avviso_id=avviso.id, codice_partita="55", comune_nome="ARBOREA")
    db.add(partita)
    db.flush()
    db.add(
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2024,
            foglio="3",
            particella="10",
            subalterno=None,
        )
    )
    db.flush()
    _, keys = ruolo._existing_partitario(db, avviso)
    assert next(iter(keys)).subalterno == ""
    monkeypatch.setattr(
        ruolo,
        "_extract_partite",
        lambda *args, **kwargs: [{"particelle": [{}]}, {"particelle": [{}]}],
    )
    monkeypatch.setattr(ruolo, "_ensure_ruolo_partita", MagicMock(side_effect=[None, partita]))
    parcels = MagicMock()
    monkeypatch.setattr(ruolo, "_ensure_ruolo_particella", parcels)
    ruolo.reconcile_subject_ruolo(db, subject.id)
    assert parcels.call_count == 1


@pytest.mark.anyio
async def test_cli_tasks_persist_failure_and_success_and_stop_at_limit(tmp_path, monkeypatch):
    manifest = RecoveryManifest(tmp_path / "manifest.sqlite")
    manifest.add("subject", "01_incass", "all", {})
    manifest.add("subject", "02_discovery", "all", {})
    runner = SimpleNamespace(
        manifest=manifest,
        db=MagicMock(),
        execute=AsyncMock(side_effect=[ValueError("identity conflict"), {"ok": True}]),
    )
    monkeypatch.setattr(cli.asyncio, "sleep", AsyncMock())
    assert (await cli.run_tasks(runner, None, 1))[0]["status"] == "failed"
    await cli.run_tasks(runner, None, None)
    assert manifest.next_task() is None
    manifest.close()


@pytest.mark.anyio
@pytest.mark.parametrize("exhausted", [True, False])
async def test_cli_transport_recovery_is_bounded_and_reactivates_both_apps(monkeypatch, exhausted):
    monkeypatch.setattr(cli.asyncio, "sleep", AsyncMock())
    failure = httpx.ReadTimeout("timeout")
    runner = SimpleNamespace(
        db=MagicMock(),
        manager=SimpleNamespace(close=AsyncMock(), login=AsyncMock(), activate_app=AsyncMock()),
        execute=AsyncMock(side_effect=[failure, failure, failure if exhausted else {"ok": True}]),
    )
    if exhausted:
        with pytest.raises(httpx.ReadTimeout):
            await cli.execute_with_retry(runner, {})
    else:
        assert await cli.execute_with_retry(runner, {}) == {"ok": True}
    assert runner.execute.await_count == 3
    assert runner.manager.activate_app.await_count == 4


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["dry", "status", "apply", "failed", "missing_user"])
async def test_cli_campaign_modes_and_durable_summary(db, tmp_path, monkeypatch, mode):
    person(db)
    db.commit()
    args = cli.parser().parse_args(["--output", str(tmp_path), "--priority-identifier", CF])
    args.apply = mode not in ("dry", "status")
    args.status = mode == "status"
    args.retry_failed = mode == "apply"
    monkeypatch.setattr(cli, "SessionLocal", lambda: db)
    if mode != "missing_user":
        db.add(
            ApplicationUser(
                id=1, username="admin", email="admin@example.test", password_hash="test"
            )
        )
        db.commit()
    monkeypatch.setattr(
        cli, "pick_credential", lambda *args: (SimpleNamespace(username="user"), "secret")
    )
    manager = MagicMock()
    manager.activate_app = AsyncMock()
    manager.__aenter__ = AsyncMock(return_value=manager)
    manager.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(cli, "CapacitasSessionManager", MagicMock(return_value=manager))
    summary = [
        {"stage": "incass", "status": "failed" if mode == "failed" else "succeeded", "count": 1}
    ]
    monkeypatch.setattr(cli, "run_tasks", AsyncMock(return_value=summary))
    if mode in ("failed", "missing_user"):
        with pytest.raises((ValueError, RuntimeError)):
            await cli.run(args)
    else:
        await cli.run(args)
    if mode == "apply":
        recorded = json.loads((tmp_path / "summary.json").read_text())
        assert {row["stage"] for row in recorded} == {"01_incass", "02_discovery"}
        assert all(row["status"] == "pending" for row in recorded)


def test_cli_main_dispatches_arguments(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["recovery", "--output", str(tmp_path)])
    monkeypatch.setattr(cli, "run", lambda args: "coroutine")
    run = MagicMock()
    monkeypatch.setattr(cli.asyncio, "run", run)
    cli.main()
    run.assert_called_once_with("coroutine")


@pytest.mark.anyio
async def test_empty_discovery_and_explicit_certificate_section():
    client = SimpleNamespace(
        search_by_cf=AsyncMock(return_value=CapacitasSearchResult(total=0, rows=[]))
    )
    subject = identity.RecoverySubject(uuid.uuid4(), (CF,), "CADONI", "person")
    assert await sources.discover_involture(client, subject) == []
    assert (
        sources.certificate_context(
            CapacitasAnagrafica(cco="55", com="165", pvc="097", fraz="31", sche="00001")
        )["ccs"]
        == "00001"
    )


def test_prepare_manifest_includes_nonpriority_subjects(db, tmp_path):
    person(db)
    company(db)
    args = cli.parser().parse_args(["--output", str(tmp_path)])
    manifest = RecoveryManifest(tmp_path / "manifest.sqlite")
    assert cli.prepare_manifest(db, args, manifest) is None
    assert sum(row["count"] for row in manifest.summary()) == 4
    manifest.close()


def test_cli_module_entrypoint(monkeypatch, tmp_path):
    import runpy

    monkeypatch.setattr("sys.argv", ["recovery", "--output", str(tmp_path)])
    monkeypatch.setattr(cli.asyncio, "run", lambda coroutine: coroutine.close())
    runpy.run_module("app.scripts.capacitas_full_recovery", run_name="__main__")


def test_full_registry_owner_query_stays_below_postgres_parameter_limit():
    from sqlalchemy.dialects import postgresql

    records = [
        identity.RecoverySubject(uuid.uuid4(), (f"{index:011d}",), "person", "person")
        for index in range(33000)
    ]
    db = MagicMock()
    db.execute.return_value = []
    assert identity._identifier_owners(db, records) == {}
    query = db.execute.call_args.args[0]
    compiled = query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"render_postcompile": True}
    )
    assert len(compiled.params) < 65535


def test_cli_fatal_errors_are_bounded_and_do_not_print_sql_parameters(
    monkeypatch, tmp_path, capsys
):
    from sqlalchemy.exc import OperationalError

    monkeypatch.setattr("sys.argv", ["recovery", "--output", str(tmp_path)])

    def failed(coroutine):
        coroutine.close()
        raise OperationalError(
            "SELECT huge query", {"private": "PRIVATE_VALUE"}, RuntimeError("parameter limit")
        )

    monkeypatch.setattr(cli.asyncio, "run", failed)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    message = capsys.readouterr().err
    assert "parameter limit" in message
    assert "PRIVATE_VALUE" not in message


@pytest.mark.anyio
async def test_source_session_refresh_preserves_both_applications(monkeypatch):
    manager = SimpleNamespace(activate_app=AsyncMock())
    monkeypatch.setattr(sources.InCassClient, "refresh_session", AsyncMock())
    monkeypatch.setattr(sources.InVoltureClient, "relogin", AsyncMock())
    await sources.CanonicalInCassClient(manager, (CF,)).refresh_session()
    await sources.ValidatedInVoltureClient(manager, (CF,), MagicMock()).relogin()
    assert [call.args[0] for call in manager.activate_app.await_args_list] == [
        "involture",
        "incass",
    ]


def test_missing_pdf_is_reported_as_incomplete_recovery(db):
    subject = person(db)
    row = notice(db, subject)
    identity.assert_incass_downloads_complete(db, subject.id)
    row.pdf_links_json = [{"document_id": "stored"}, {"download_error": "timeout"}]
    db.flush()
    with pytest.raises(ValueError, match="PDF"):
        identity.assert_incass_downloads_complete(db, subject.id)
    row.pdf_links_json = [{"url": "https://example.test/notice.pdf"}]
    db.flush()
    with pytest.raises(ValueError):
        identity.assert_incass_downloads_complete(db, subject.id)


@pytest.mark.anyio
@pytest.mark.parametrize("prior_status", ["succeeded", "failed"])
async def test_retry_of_incomplete_pdf_reexecutes_subject(db, runner, monkeypatch, prior_status):
    person(db)
    subject = identity.audit_recovery_subjects(db)[0][0]
    task = make_task(subject, "01_incass")

    async def succeeded(session, client, job):
        assert job.result_json is None
        job.status = "succeeded"
        job.result_json = {"items": []}
        session.commit()
        return job

    monkeypatch.setattr(service, "run_incass_sync_job", succeeded)
    result = await runner.incass(task, subject)
    job = db.get(CapacitasInCassSyncJob, result["job_id"])
    job.status = prior_status
    job.result_json = None
    task["attempts"] = 1
    await runner.incass(task, subject)
