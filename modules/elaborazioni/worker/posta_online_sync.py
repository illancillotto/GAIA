from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.elaborazioni.posta_online.schemas import (
    PostaOnlineRegisteredMailSyncJobCreateRequest,
)
from app.services.elaborazioni_posta_online import (
    decrypt_posta_online_password,
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from posta_online_client import (
    PostaOnlineBrowserClient,
    PostaOnlineCircuitOpen,
    PostaOnlineScrapeConfig,
)

logger = logging.getLogger(__name__)

POSTA_ONLINE_RESUME_STORAGE_PATH = Path(
    os.getenv(
        "POSTA_ONLINE_RESUME_STORAGE_PATH",
        str(Path(os.getenv("ELABORAZIONI_DEBUG_ARTIFACTS_PATH", "/data/catasto/debug")) / "posta-online-resume"),
    )
)
_RESUME_STATE_KEY = "resume_state"
_RESUMABLE_SCRAPE_STAGES = {"scraping", "scraped"}
_POSTE_RECOVERY_COOLDOWN = timedelta(minutes=20)
_POSTE_MAX_AUTOMATIC_ROUNDS = 3
_POSTE_IMPORT_BATCH_SIZE = 25


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
            completed_at = datetime.now(UTC)
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

    started_at = datetime.now(UTC)
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

        completed_at = datetime.now(UTC)
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
        completed_at = datetime.now(UTC)
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
        if getattr(payload, "shipment_ids", None) is None and resume_payload and resume_payload.get("archive_ids"):
            payload.shipment_ids = list(resume_payload["archive_ids"])
            job.payload_json = payload.model_dump(mode="json")
            db.commit()
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

    started_at = datetime.now(UTC)
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
    except PostaOnlineCircuitOpen as exc:
        _, partial_payload = _load_resume_checkpoint(session_factory=session_factory, job_id=job_id)
        if not partial_payload or not partial_payload.get("details"):
            _pause_registered_mail_job(session_factory=session_factory, job_id=job_id, reason=str(exc))
            return
        scrape_payload = partial_payload
        resumed_from_checkpoint = True
    except Exception as exc:
        logger.exception("Job Poste Online %s fallito durante login/scrape", job_id)
        with session_factory() as db:
            job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = datetime.now(UTC)
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
                job.completed_at = datetime.now(UTC)
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
        shipment_ids=getattr(payload, "shipment_ids", None) or (resume_payload or {}).get("archive_ids") or None,
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
        details = scrape_payload.get("details") or []
        contacts = scrape_payload.get("contacts") or []
        import_jobs = _import_scraped_details(db, job_id, job.requested_by_user_id, requested_payload, details)
        if not details and contacts and not requested_payload.get("include_details", True):
            import_jobs.append(_import_scraped_contacts(db, job_id, job.requested_by_user_id, requested_payload, contacts))
        if not details and not contacts and not scrape_payload.get("errors"):
            raise RuntimeError("Job Poste senza dettagli validi e senza errori espliciti")
        remaining_ids = _remaining_detail_ids(requested_payload, scrape_payload, details)
        rounds = int(_result_json(job.result_json).get("recovery_rounds") or 0)
        incomplete = bool(remaining_ids)
        rounds += int(incomplete)
        paused = incomplete and rounds >= _POSTE_MAX_AUTOMATIC_ROUNDS
        completed_at = datetime.now(UTC)
        status = ("paused" if paused else "queued_resume") if incomplete else (
            "completed_with_errors" if scrape_payload.get("errors") or any(item.records_errors for item in import_jobs) else "succeeded"
        )
        job.status = status
        job.error_detail = None if status == "succeeded" else "Dettagli Poste mancanti o anomalie di import"
        job.completed_at = completed_at if not incomplete else None
        resume_state = _result_resume_state(job.result_json)
        record_counts = {
            f"records_{kind}": sum(getattr(item, f"records_{kind}") or 0 for item in import_jobs)
            for kind in ("total", "imported", "matched", "ambiguous", "unmatched", "errors")
        }
        job.result_json = {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "tributi_import_job_id": str(import_jobs[-1].id) if import_jobs else None,
            "tributi_import_job_ids": [str(item.id) for item in import_jobs],
            "archive_ids": scrape_payload.get("archive_ids", []),
            "details_scraped": len(scrape_payload.get("details") or []),
            "contacts_scraped": len(scrape_payload.get("contacts") or []),
            "scrape_errors": scrape_payload.get("errors", []),
            "resumed_from_checkpoint": resumed_from_checkpoint,
            **record_counts,
            "remaining_ids_count": len(remaining_ids),
            "recovery_rounds": rounds,
            "retry_not_before": (completed_at + _POSTE_RECOVERY_COOLDOWN).isoformat() if incomplete and not paused else None,
        }
        if incomplete:
            resume_state = resume_state or {
                "stage": "scraped", "path": str(_resume_checkpoint_path(job_id))
            }
            resume_state["stage"] = "scraping"
            job.result_json = {**job.result_json, _RESUME_STATE_KEY: resume_state}
        else:
            mark_credential_used(db, credential_id)
        db.commit()
        if not incomplete:
            _delete_resume_checkpoint(job_id)
        return dict(job.result_json or {})


def _import_scraped_details(db, job_id, triggered_by, requested_payload, details):
    import_jobs = []
    for batch_index in range(0, len(details), _POSTE_IMPORT_BATCH_SIZE):
        batch = details[batch_index : batch_index + _POSTE_IMPORT_BATCH_SIZE]
        import_job = _import_tributi_registered_mails(
            db,
            filename=(
                f"posta-online-worker-job-{job_id}.json" if len(details) <= _POSTE_IMPORT_BATCH_SIZE
                else f"posta-online-worker-job-{job_id}-batch-{batch_index // _POSTE_IMPORT_BATCH_SIZE}.json"
            ),
            content=json.dumps({"details": batch}).encode("utf-8"),
            annualita=requested_payload.get("annualita"),
            triggered_by=triggered_by,
            preserve_associations=requested_payload.get("preserve_associations", True),
        )
        if getattr(import_job, "status", "completed") == "failed":
            raise RuntimeError(f"Import Poste batch {batch_index // _POSTE_IMPORT_BATCH_SIZE} fallito")
        if (import_job.records_errors or 0) > 0:
            raise RuntimeError(f"Import Poste batch {batch_index // _POSTE_IMPORT_BATCH_SIZE} incompleto")
        import_jobs.append(import_job)
        db.commit()
    return import_jobs


def _import_scraped_contacts(db, job_id, triggered_by, requested_payload, contacts):
    import_job = _import_tributi_registered_mails(
        db,
        filename=f"posta-online-worker-job-{job_id}-contacts.json",
        content=json.dumps({"contacts": contacts}).encode("utf-8"),
        annualita=requested_payload.get("annualita"),
        triggered_by=triggered_by,
        preserve_associations=requested_payload.get("preserve_associations", True),
    )
    if getattr(import_job, "status", "completed") == "failed":
        raise RuntimeError("Import contatti Poste fallito")
    if (import_job.records_errors or 0) > 0:
        raise RuntimeError("Import contatti Poste incompleto")
    db.commit()
    return import_job


def _remaining_detail_ids(requested_payload, scrape_payload, details):
    archive_ids = scrape_payload.get("archive_ids") or []
    completed_ids = {str(item.get("idInvio")) for item in details if isinstance(item, dict)}
    detail_ids = archive_ids[: requested_payload.get("max_details")] if requested_payload.get("max_details") else archive_ids
    return [str(item) for item in detail_ids if str(item) not in completed_ids] if requested_payload.get("include_details", True) else []


def _pause_registered_mail_job(*, session_factory: sessionmaker, job_id: int, reason: str) -> None:
    with session_factory() as db:
        job = db.get(PostaOnlineRegisteredMailSyncJob, job_id)
        if job is None:
            return
        rounds = int(_result_json(job.result_json).get("recovery_rounds") or 0) + 1
        result = _result_json(job.result_json)
        result["recovery_rounds"] = rounds
        result["retry_not_before"] = (datetime.now(UTC) + _POSTE_RECOVERY_COOLDOWN).isoformat()
        job.result_json = result
        job.status = "paused" if rounds >= _POSTE_MAX_AUTOMATIC_ROUNDS else "queued_resume"
        job.error_detail = reason
        job.started_at = None
        db.commit()


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
    now = datetime.now(UTC)
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
        payload = _result_json(getattr(job, "payload_json", None))
        if archive_ids and payload.get("shipment_ids") is None:
            payload["shipment_ids"] = list(archive_ids)
            job.payload_json = payload
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
