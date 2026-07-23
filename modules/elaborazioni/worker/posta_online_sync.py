from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.elaborazioni.posta_online.schemas import PostaOnlineRegisteredMailSyncJobCreateRequest
from app.services.elaborazioni_posta_online import (
    decrypt_posta_online_password,
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from posta_online_client import PostaOnlineBrowserClient, PostaOnlineScrapeConfig

logger = logging.getLogger(__name__)


async def run_posta_online_job_by_id(
    *,
    job_id: int,
    session_factory: sessionmaker,
    headless: bool,
    _client_class=PostaOnlineBrowserClient,
) -> None:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            logger.warning("Job Poste Online %s non trovato", job_id)
            return
        mode = job.mode

    if mode == "credential_test":
        await run_posta_online_credential_test_job_by_id(
            job_id=job_id,
            session_factory=session_factory,
            headless=headless,
            _client_class=_client_class,
        )
        return

    await run_posta_online_registered_mail_job_by_id(
        job_id=job_id,
        session_factory=session_factory,
        headless=headless,
        _client_class=_client_class,
    )


async def run_posta_online_credential_test_job_by_id(
    *,
    job_id: int,
    session_factory: sessionmaker,
    headless: bool,
    _client_class=PostaOnlineBrowserClient,
) -> None:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            logger.warning("Job test Poste Online %s non trovato", job_id)
            return
        payload = job.payload_json if isinstance(job.payload_json, dict) else {}
        credential_id = int(payload.get("credential_id") or job.credential_id or 0)
        credential = db.get(PostaOnlineCredential, credential_id)
        if credential is None:
            completed_at = datetime.now(timezone.utc)
            job.status = "failed"
            job.error_detail = "Credenziale Poste Online non trovata"
            job.completed_at = completed_at
            job.result_json = {"ok": False, "error": job.error_detail, "checked_at": completed_at.isoformat()}
            db.commit()
            return
        username = credential.username
        password = decrypt_posta_online_password(credential.password_encrypted)
        min_delay_ms = int(payload.get("min_delay_ms") or credential.min_delay_ms)
        max_delay_ms = int(payload.get("max_delay_ms") or credential.max_delay_ms)

    started_at = datetime.now(timezone.utc)
    try:
        config = PostaOnlineScrapeConfig(
            min_delay_ms=min_delay_ms,
            max_delay_ms=max_delay_ms,
            max_pages=1,
            max_details=1,
            include_contacts=False,
            include_details=False,
            continue_on_error=False,
            headless=headless,
        )
        async with _client_class(config) as client:
            await client.login(username, password)

        completed_at = datetime.now(timezone.utc)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "succeeded"
                job.error_detail = None
                job.completed_at = completed_at
                job.result_json = {
                    "ok": True,
                    "error": None,
                    "checked_at": completed_at.isoformat(),
                    "started_at": started_at.isoformat(),
                }
            mark_credential_used(db, credential_id)
            db.commit()
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        logger.exception("Job test Poste Online %s fallito", job_id)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = completed_at
                job.result_json = {
                    "ok": False,
                    "error": str(exc),
                    "checked_at": completed_at.isoformat(),
                    "started_at": started_at.isoformat(),
                }
            mark_credential_error(db, credential_id, str(exc))
            db.commit()


async def run_posta_online_registered_mail_job_by_id(
    *,
    job_id: int,
    session_factory: sessionmaker,
    headless: bool,
    _client_class=PostaOnlineBrowserClient,
) -> None:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            logger.warning("Job Poste Online %s non trovato", job_id)
            return
        payload = PostaOnlineRegisteredMailSyncJobCreateRequest.model_validate(job.payload_json or {})
        credential, password = pick_credential(db, payload.credential_id)
        credential_id = credential.id
        min_delay_ms = payload.min_delay_ms or credential.min_delay_ms
        max_delay_ms = payload.max_delay_ms or credential.max_delay_ms
        username = credential.username

    started_at = datetime.now(timezone.utc)
    try:
        scrape_payload = await _scrape_posta_online_payload(
            username=username,
            password=password,
            payload=payload,
            headless=headless,
            min_delay_ms=min_delay_ms,
            max_delay_ms=max_delay_ms,
            client_class=_client_class,
        )
        import_result = _persist_scrape_payload(
            session_factory=session_factory,
            job_id=job_id,
            credential_id=credential_id,
            requested_payload=payload.model_dump(mode="json"),
            scrape_payload=scrape_payload,
            started_at=started_at,
        )
        logger.info("Job Poste Online %s completato: %s", job_id, import_result)
    except Exception as exc:
        logger.exception("Job Poste Online %s fallito", job_id)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                job.result_json = {
                    "error": str(exc),
                    "started_at": started_at.isoformat(),
                    "completed_at": job.completed_at.isoformat(),
                }
            mark_credential_error(db, credential_id if "credential_id" in locals() else None, str(exc))
            db.commit()


async def _scrape_posta_online_payload(
    *,
    username: str,
    password: str,
    payload: PostaOnlineRegisteredMailSyncJobCreateRequest,
    headless: bool,
    min_delay_ms: int,
    max_delay_ms: int,
    client_class,
) -> dict[str, Any]:
    config = PostaOnlineScrapeConfig(
        min_delay_ms=min_delay_ms,
        max_delay_ms=max_delay_ms,
        max_pages=payload.max_pages,
        max_details=payload.max_details,
        include_contacts=payload.include_contacts,
        include_details=payload.include_details,
        continue_on_error=payload.continue_on_error,
        headless=headless,
    )
    async with client_class(config) as client:
        await client.login(username, password)
        return await client.scrape_registered_mails()


def _persist_scrape_payload(
    *,
    session_factory: sessionmaker,
    job_id: int,
    credential_id: int,
    requested_payload: dict[str, Any],
    scrape_payload: dict[str, Any],
    started_at: datetime,
) -> dict[str, Any]:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            raise RuntimeError(f"Job Poste Online {job_id} non trovato durante persistenza")
        import_job = _import_tributi_registered_mails(
            db,
            filename=f"posta-online-worker-job-{job_id}.json",
            content=json.dumps(scrape_payload).encode("utf-8"),
            annualita=requested_payload.get("annualita"),
            triggered_by=job.requested_by_user_id,
        )
        completed_at = datetime.now(timezone.utc)
        status = "completed_with_errors" if scrape_payload.get("errors") or (import_job.records_errors or 0) > 0 else "succeeded"
        job.status = status
        job.error_detail = None if status == "succeeded" else "Job completato con errori o anomalie"
        job.completed_at = completed_at
        job.result_json = {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "tributi_import_job_id": str(import_job.id),
            "archive_ids": scrape_payload.get("archive_ids", []),
            "details_scraped": len(scrape_payload.get("details") or []),
            "contacts_scraped": len(scrape_payload.get("contacts") or []),
            "scrape_errors": scrape_payload.get("errors", []),
            "records_total": import_job.records_total,
            "records_imported": import_job.records_imported,
            "records_matched": import_job.records_matched,
            "records_ambiguous": import_job.records_ambiguous,
            "records_unmatched": import_job.records_unmatched,
            "records_errors": import_job.records_errors,
        }
        mark_credential_used(db, credential_id)
        db.commit()
        return dict(job.result_json or {})


def _import_tributi_registered_mails(db, **kwargs):
    from app.modules.ruolo import tributi_repositories

    return tributi_repositories.import_posta_online_registered_mails(db, **kwargs)


def write_debug_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
