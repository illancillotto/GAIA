from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

from app.models.capacitas import CapacitasInCassSyncJob
from app.modules.catasto.services.domande_irrigue import persist_capacitas_domande_irrigue_batch
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.apps.involture.domande_irrigue import DomandeIrrigueScraper
from app.modules.elaborazioni.capacitas.models import (
    CapacitasAnagrafica,
    CapacitasAnagraficaHistoryImportItem,
    CapacitasInCassSyncJobCreateRequest,
    CapacitasTerreniBatchItem,
    CapacitasTerreniBatchRequest,
)
from app.modules.elaborazioni.capacitas.recovery_identity import (
    assert_incass_downloads_complete,
    audit_recovery_subjects,
)
from app.modules.elaborazioni.capacitas.recovery_ruolo import reconcile_subject_ruolo
from app.modules.elaborazioni.capacitas.recovery_sources import (
    CanonicalInCassClient,
    ValidatedInVoltureClient,
    assert_source_identity,
    certificate_context,
    discover_involture,
)
from app.services.elaborazioni_capacitas_anagrafica_history import (
    _import_single_item,
    _sort_history_rows,
)
from app.services.elaborazioni_capacitas_incass import run_incass_sync_job
from app.services.elaborazioni_capacitas_terreni import (
    sync_certificato_snapshot,
    sync_terreni_batch,
)


class RecoveryRunner:
    def __init__(self, db, manager, manifest, output, user_id):
        self.db = db
        self.manager = manager
        self.manifest = manifest
        self.output = output
        self.user_id = user_id
        self.involture = InVoltureClient(manager)
        self.handlers = {
            "01_incass": self.incass,
            "02_discovery": self.discovery,
            "03_history": self.history,
            "04_certificates": self.certificates,
            "05_terreni": self.terreni,
            "06_domande": self.domande,
            "07_ruolo": self.ruolo,
        }

    def save_source(self, task, value):
        directory = self.output / task["subject_id"]
        directory.mkdir(parents=True, exist_ok=True)
        name = sha256(task["task_key"].encode()).hexdigest()[:20]
        path = directory / f"{task['stage']}-{name}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, default=str), encoding="utf-8")
        temporary.replace(path)

    async def execute(self, task):
        subject_id = UUID(task["subject_id"])
        eligible, blocked = audit_recovery_subjects(self.db, [subject_id])
        if blocked or not eligible:
            raise ValueError(f"Identità anagrafica non utilizzabile: {blocked}")
        subject = eligible[0]
        if list(subject.identifiers) != task["payload"]["identifiers"]:
            raise ValueError("Identità anagrafica cambiata dopo il manifest: rieseguire l'audit")
        result = await self.handlers[task["stage"]](task, subject)
        self.db.commit()
        return result

    def add_task(self, subject, stage, key, payload):
        self.manifest.add(
            subject.subject_id,
            stage,
            key,
            {"identifiers": list(subject.identifiers), **payload},
        )

    async def incass(self, task, subject):
        marker = f"{self.output.name}:{task['task_key']}"
        job = self.db.scalar(
            select(CapacitasInCassSyncJob).where(
                CapacitasInCassSyncJob.payload_json["recovery_task_key"].as_string() == marker
            )
        )
        if job is None:
            payload = CapacitasInCassSyncJobCreateRequest(
                subject_ids=[subject.subject_id],
                include_details=True,
                include_partitario=True,
                include_mailing_list=True,
                download_mailing_receipts=True,
                continue_on_error=False,
                throttle_ms=250,
            ).model_dump(mode="json")
            job = CapacitasInCassSyncJob(
                requested_by_user_id=self.user_id,
                status="processing",
                mode="subjects_sync",
                payload_json={**payload, "recovery_task_key": marker},
                started_at=datetime.now(UTC),
            )
            self.db.add(job)
            self.db.commit()
        client = CanonicalInCassClient(self.manager, subject.identifiers)
        if task.get("attempts", 0) > 0 and job.status == "succeeded":
            job.result_json = None
        job = await run_incass_sync_job(self.db, client, job)
        if job.status != "succeeded":
            raise RuntimeError(job.error_detail or "Recupero avvisi inCASS incompleto")
        assert_incass_downloads_complete(self.db, subject.subject_id)
        self.add_task(subject, "07_ruolo", "all", {})
        return {"job_id": job.id, "result": job.result_json}

    async def discovery(self, task, subject):
        rows = await discover_involture(self.involture, subject)
        self.save_source(task, [row.model_dump(mode="json") for row in rows])
        for row in rows:
            if row.id_ana:
                self.add_task(subject, "03_history", row.id_ana, {"idxana": row.id_ana})
            context = certificate_context(row)
            key = "-".join(context.values())
            payload = {"row": row.model_dump(mode="json"), "context": context}
            self.add_task(subject, "04_certificates", key, payload)
            self.add_task(subject, "06_domande", key, payload)
        return {"source_rows": len(rows)}

    async def history(self, task, subject):
        idxana = task["payload"]["idxana"]
        history = await self.involture.fetch_anagrafica_history(idxana=idxana)
        details = {}
        for row in history:
            details[row.history_id] = await self.involture.fetch_anagrafica_detail(
                history_id=row.history_id
            )
        self.save_source(
            task,
            {
                "history": [row.model_dump(mode="json") for row in history],
                "details": {key: value.model_dump(mode="json") for key, value in details.items()},
            },
        )
        if subject.subject_type == "company":
            return {"archived_records": len(history), "normalized_company_history_supported": False}
        if history:
            latest = _sort_history_rows(history)[-1]
            detail = details[latest.history_id]
            assert_source_identity(
                (detail.codice_fiscale or latest.codice_fiscale,), subject.identifiers
            )
        result = await _import_single_item(
            self.db,
            self.involture,
            CapacitasAnagraficaHistoryImportItem(subject_id=subject.subject_id, idxana=idxana),
            storico_cache={idxana: history},
            detail_cache=details,
        )
        return result.model_dump(mode="json")

    async def certificates(self, task, subject):
        client = ValidatedInVoltureClient(
            self.manager, subject.identifiers, lambda value: self.save_source(task, value)
        )
        certificate, snapshot = await sync_certificato_snapshot(
            self.db, client, **task["payload"]["context"]
        )
        for parcel in certificate.terreni:
            if not parcel.foglio or not parcel.particella:
                raise ValueError("Terreno nel certificato privo di foglio o particella")
            item = CapacitasTerreniBatchItem(
                frazione_id=task["payload"]["context"]["fra"],
                comune=certificate.comune_label or task["payload"]["row"]["comune"],
                foglio=parcel.foglio,
                particella=parcel.particella,
                sub=parcel.sub or "",
            )
            key = f"{item.frazione_id}-{item.foglio}-{item.particella}-{item.sub or '0'}"
            self.add_task(subject, "05_terreni", key, {"item": item.model_dump(mode="json")})
        return {"snapshot_id": str(snapshot.id), "terreni": len(certificate.terreni)}

    async def terreni(self, task, subject):
        client = self.involture
        result = await sync_terreni_batch(
            self.db,
            client,
            CapacitasTerreniBatchRequest(
                items=[CapacitasTerreniBatchItem.model_validate(task["payload"]["item"])],
                fetch_certificati=False,
                fetch_details=True,
                continue_on_error=False,
            ),
        )
        if result.failed_items:
            raise RuntimeError(f"Recupero terreni incompleto: {result.model_dump(mode='json')}")
        return result.model_dump(mode="json")

    async def domande(self, task, subject):
        scraper = DomandeIrrigueScraper(self.manager)
        batch = await scraper.fetch_for_anagrafica_rows(
            [CapacitasAnagrafica.model_validate(task["payload"]["row"])],
            include_details=True,
            continue_on_error=False,
        )
        self.save_source(task, batch.model_dump(mode="json"))
        summary = persist_capacitas_domande_irrigue_batch(self.db, batch, run_anomaly_checks=False)
        if summary.invalid_year_rows:
            raise ValueError("Domande irrigue con annualità invalida: recupero incompleto")
        return asdict(summary)

    async def ruolo(self, task, subject):
        return reconcile_subject_ruolo(self.db, subject.subject_id)
