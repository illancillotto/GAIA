from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
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

POSTA_ONLINE_RESUME_STORAGE_PATH = Path(
    os.getenv(
        "POSTA_ONLINE_RESUME_STORAGE_PATH",
        str(Path(os.getenv("ELABORAZIONI_DEBUG_ARTIFACTS_PATH", "/data/catasto/debug")) / "posta-online-resume"),
    )
)
_RESUME_STATE_KEY = "resume_state"
_RESUMABLE_SCRAPE_STAGES = {"scraping", "scraped"}


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
    resume_state, resume_payload = _load_resume_checkpoint(session_factory=session_factory, job_id=job_id)
    resume_stage = str(resume_state.get("stage") or "") if resume_state else ""
    has_complete_scrape_checkpoint = resume_stage == "scraped" and resume_payload is not None

    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            logger.warning("Job Poste Online %s non trovato", job_id)
            return
        payload = PostaOnlineRegisteredMailSyncJobCreateRequest.model_validate(job.payload_json or {})
        if has_complete_scrape_checkpoint:
            credential_id = _resolved_credential_id(job, payload)
            username = ""
            password = ""
            min_delay_ms = payload.min_delay_ms or 3500
            max_delay_ms = payload.max_delay_ms or 9000
        else:
            credential, password = pick_credential(db, payload.credential_id)
            credential_id = credential.id
            min_delay_ms = payload.min_delay_ms or credential.min_delay_ms
            max_delay_ms = payload.max_delay_ms or credential.max_delay_ms
            username = credential.username

    started_at = datetime.now(timezone.utc)
    try:
        if has_complete_scrape_checkpoint:
            logger.info("Job Poste Online %s: riuso checkpoint scrape completo", job_id)
            scrape_payload = resume_payload or {}
            resumed_from_checkpoint = True
        else:
            if resume_payload is not None:
                logger.info("Job Poste Online %s: riprendo scrape da checkpoint parziale", job_id)

            async def progress_callback(partial_payload: dict[str, Any]) -> None:
                _write_resume_checkpoint(
                    session_factory=session_factory,
                    job_id=job_id,
                    scrape_payload=partial_payload,
                    stage="scraping",
                    started_at=started_at,
                )

            scrape_payload = await _scrape_posta_online_payload(
                username=username,
                password=password,
                payload=payload,
                headless=headless,
                min_delay_ms=min_delay_ms,
                max_delay_ms=max_delay_ms,
                client_class=_client_class,
                resume_payload=resume_payload,
                progress_callback=progress_callback,
            )
            _write_resume_checkpoint(
                session_factory=session_factory,
                job_id=job_id,
                scrape_payload=scrape_payload,
                stage="scraped",
                started_at=started_at,
            )
            resumed_from_checkpoint = resume_payload is not None
    except Exception as exc:
        logger.exception("Job Poste Online %s fallito durante login/scrape", job_id)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                result_json = {
                    "error": str(exc),
                    "started_at": started_at.isoformat(),
                    "completed_at": job.completed_at.isoformat(),
                }
                resume_state = _result_resume_state(job.result_json)
                if resume_state is not None:
                    result_json[_RESUME_STATE_KEY] = resume_state
                job.result_json = result_json
            mark_credential_error(db, credential_id if "credential_id" in locals() else None, str(exc))
            db.commit()
        return

    try:
        import_result = _persist_scrape_payload(
            session_factory=session_factory,
            job_id=job_id,
            credential_id=credential_id,
            requested_payload=payload.model_dump(mode="json"),
            scrape_payload=scrape_payload,
            started_at=started_at,
            resumed_from_checkpoint=resumed_from_checkpoint,
        )
        logger.info("Job Poste Online %s completato: %s", job_id, import_result)
    except Exception as exc:
        logger.exception("Job Poste Online %s fallito durante persistenza", job_id)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                result_json = {
                    "error": str(exc),
                    "started_at": started_at.isoformat(),
                    "completed_at": job.completed_at.isoformat(),
                }
                resume_state = _result_resume_state(job.result_json)
                if resume_state is not None:
                    result_json[_RESUME_STATE_KEY] = resume_state
                job.result_json = result_json
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
    resume_payload: dict[str, Any] | None = None,
    progress_callback=None,
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
        return await client.scrape_registered_mails(resume_payload=resume_payload, progress_callback=progress_callback)


def _persist_scrape_payload(
    *,
    session_factory: sessionmaker,
    job_id: int,
    credential_id: int,
    requested_payload: dict[str, Any],
    scrape_payload: dict[str, Any],
    started_at: datetime,
    resumed_from_checkpoint: bool = False,
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
            "resumed_from_checkpoint": resumed_from_checkpoint,
            "records_total": import_job.records_total,
            "records_imported": import_job.records_imported,
            "records_matched": import_job.records_matched,
            "records_ambiguous": import_job.records_ambiguous,
            "records_unmatched": import_job.records_unmatched,
            "records_errors": import_job.records_errors,
        }
        mark_credential_used(db, credential_id)
        db.commit()
        _delete_resume_checkpoint(job_id)
        return dict(job.result_json or {})


def _import_tributi_registered_mails(db, **kwargs):
    from app.modules.ruolo import tributi_repositories

    return tributi_repositories.import_posta_online_registered_mails(db, **kwargs)


def _resolved_credential_id(job: PostaOnlineRegisteredMailSyncJob, payload: PostaOnlineRegisteredMailSyncJobCreateRequest) -> int:
    return int(payload.credential_id or job.credential_id or 0)


def _result_json(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _result_resume_state(value: Any) -> dict[str, Any] | None:
    state = _result_json(value).get(_RESUME_STATE_KEY)
    if not isinstance(state, dict):
        return None
    if str(state.get("stage") or "") not in _RESUMABLE_SCRAPE_STAGES:
        return None
    return dict(state)


def _resume_checkpoint_path(job_id: int) -> Path:
    return POSTA_ONLINE_RESUME_STORAGE_PATH / f"job-{job_id}-scrape-payload.json"


def _load_resume_checkpoint(
    *,
    session_factory: sessionmaker,
    job_id: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            return None, None
        state = _result_resume_state(job.result_json)
    if state is None:
        return None, None
    path = Path(str(state.get("path") or _resume_checkpoint_path(job_id)))
    if not path.exists():
        logger.warning("Job Poste Online %s: checkpoint resume dichiarato ma file assente: %s", job_id, path)
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Job Poste Online %s: checkpoint resume non leggibile: %s", job_id, path, exc_info=True)
        return None, None
    if not isinstance(payload, dict):
        logger.warning("Job Poste Online %s: checkpoint resume non valido: %s", job_id, path)
        return None, None
    return state, payload


def _write_resume_checkpoint(
    *,
    session_factory: sessionmaker,
    job_id: int,
    scrape_payload: dict[str, Any],
    stage: str,
    started_at: datetime,
) -> None:
    path = _resume_checkpoint_path(job_id)
    try:
        write_debug_payload(path, scrape_payload)
    except OSError:
        logger.warning("Job Poste Online %s: checkpoint resume non scrivibile: %s", job_id, path, exc_info=True)
        return
    now = datetime.now(timezone.utc)
    details = scrape_payload.get("details") or []
    contacts = scrape_payload.get("contacts") or []
    archive_ids = scrape_payload.get("archive_ids") or []
    errors = scrape_payload.get("errors") or []
    state = {
        "stage": stage,
        "path": str(path),
        "updated_at": now.isoformat(),
        "archive_ids_count": len(archive_ids) if isinstance(archive_ids, list) else 0,
        "details_count": len(details) if isinstance(details, list) else 0,
        "contacts_count": len(contacts) if isinstance(contacts, list) else 0,
        "errors_count": len(errors) if isinstance(errors, list) else 0,
    }
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            return
        result_json = _result_json(job.result_json)
        result_json.setdefault("started_at", started_at.isoformat())
        result_json[_RESUME_STATE_KEY] = state
        job.result_json = result_json
        try:
            db.commit()
        except Exception:
            logger.warning("Job Poste Online %s: metadati checkpoint resume non salvati", job_id, exc_info=True)
            db.rollback()


def _delete_resume_checkpoint(job_id: int) -> None:
    try:
        _resume_checkpoint_path(job_id).unlink()
    except FileNotFoundError:
        return
    except OSError:
        logger.warning("Job Poste Online %s: impossibile eliminare checkpoint resume", job_id, exc_info=True)


def write_debug_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
