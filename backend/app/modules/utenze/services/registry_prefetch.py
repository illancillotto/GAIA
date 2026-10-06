from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import local

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.utenze.models import AnagraficaImportJob, AnagraficaSubject
from app.modules.utenze.services import import_service as service


class RegistryPrefetch:
    def __init__(self, db, job, workers: int) -> None:
        log = job.log_json if isinstance(job.log_json, dict) else {}
        skipped = (
            service.registry_job_completed_subject_ids(db, job.id)
            if log.get("mode") == "registry_import_resume"
            else set()
        )
        subject_ids = db.scalars(
            select(AnagraficaSubject.id).order_by(
                AnagraficaSubject.nas_folder_letter.asc(), AnagraficaSubject.created_at.asc()
            )
        ).all()
        self._ids = iter(subject_id for subject_id in subject_ids if subject_id not in skipped)
        self._workers = workers
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._pending = {}
        self._thread = local()
        self._services = []
        self._preview = None
        self.connector = self

    def _fill(self) -> None:
        while len(self._pending) < self._workers:
            try:
                subject_id = next(self._ids)
            except StopIteration:
                return
            self._pending[subject_id] = self._executor.submit(self._fetch, subject_id)

    def _fetch(self, subject_id):
        preview_service = getattr(self._thread, "service", None)
        if preview_service is None:
            preview_service = service.AnagraficaImportPreviewService(service.get_nas_client())
            self._thread.service = preview_service
            self._services.append(preview_service)
        with SessionLocal() as db:
            subject = db.get(AnagraficaSubject, subject_id)
            matched = preview_service.match_existing_subject_folder(db, subject)
            preview = preview_service.preview_subject_folder(matched, strict=True)
            return matched, preview

    def match_existing_subject_folder(self, db, subject):
        self._fill()
        future = self._pending.pop(subject.id, None)
        if future is None:
            future = self._executor.submit(self._fetch, subject.id)
        self._fill()
        matched, self._preview = future.result()
        return matched

    def preview_subject_folder(self, matched, *, strict):
        return self._preview

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
        for preview_service in self._services:
            service._close_connector(preview_service.connector)
        self._services.clear()


def run_parallel_registry_job(job_id, workers: int) -> None:
    with SessionLocal() as db:
        job = db.get(AnagraficaImportJob, job_id)
        if job is None or job.letter != "REGISTRY":
            return
        prefetch = RegistryPrefetch(db, job, workers)
        try:
            service.process_registry_bulk_import_job(db, job_id, service=prefetch)
        finally:
            prefetch.close()
