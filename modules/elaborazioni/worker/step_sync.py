"""Execute STEP sync jobs.

Modes:

- ``credential_test``: login only;
- ``list_only``: read every Contribuenti page and refresh the list rows;
- ``sync``: list scan, then open the scheda (documents, tributi, PDFs,
  payments) of every contribuente that is new or whose list row changed
  since its last scheda (``force_details`` re-reads all of them);
- ``archive_import``: load a verified scraper archive from the import folder;
- ``relink``: re-resolve every link to ``ruolo_avvisi``.

After ``sync``, ``archive_import`` and ``relink`` the STEP assignments are
projected onto the notice register (see ``register_projection``). The audit
actor is the user who queued the job or ``STEP_REGISTER_ACTOR_USER_ID`` for
the nightly autosync; without an actor the projection is skipped and reported.

Only login rejections count towards the credential auto-disable; network or
portal errors fail the job without penalizing the account.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.modules.elaborazioni.step import storage
from app.modules.elaborazioni.step.archive import import_archive
from app.modules.elaborazioni.step.credentials import (
    mark_credential_error,
    mark_credential_used,
    pick_credential,
)
from app.modules.elaborazioni.step.jobs import finish_job, update_progress
from app.modules.elaborazioni.step.models import StepContribuente, StepSyncJob
from app.modules.elaborazioni.step.persistence import (
    StoredPdf,
    needs_detail,
    persist_scheda,
    upsert_summary,
)
from app.modules.elaborazioni.step.register_projection import publish_recoveries
from app.modules.elaborazioni.step.ruolo_link import link_documents, relink_all
from step_client import StepBrowserClient, StepClientConfig, StepLoginError
from step_rules import ListReference, StepIntegrityError, record_key

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_SCHEDA_FAILURES = 3
_MAX_REPORTED_ERRORS = 50


@dataclass
class JobContext:
    job_id: int
    mode: str
    payload: dict
    session_factory: sessionmaker
    headless: bool
    client_class: type = StepBrowserClient
    requested_by_user_id: int | None = None


@dataclass(frozen=True)
class _Credential:
    id: int
    username: str
    password: str
    portal_url: str
    min_delay_ms: int


async def run_step_job_by_id(
    *,
    job_id: int,
    session_factory: sessionmaker,
    headless: bool,
    client_class: type = StepBrowserClient,
) -> None:
    with session_factory() as db:
        job = db.get(StepSyncJob, job_id)
        if job is None:
            logger.warning("Job STEP %s non trovato", job_id)
            return
        ctx = JobContext(
            job_id,
            job.mode,
            dict(job.payload_json or {}),
            session_factory,
            headless,
            client_class,
            job.requested_by_user_id,
        )
    handler = _HANDLERS.get(ctx.mode)
    try:
        if handler is None:
            raise ValueError(f"Modalita job STEP non supportata: {ctx.mode}")
        status, result = await handler(ctx)
        if ctx.mode in _REGISTER_MODES:
            result["register"] = await asyncio.to_thread(_publish_register, ctx)
    except Exception as exc:
        logger.exception("Job STEP %s fallito", job_id)
        with session_factory() as db:
            finish_job(db, job_id, status="failed", result=None, error=str(exc))
        return
    with session_factory() as db:
        finish_job(db, job_id, status=status, result=result)


_REGISTER_MODES = frozenset({"sync", "archive_import", "relink"})


def _register_actor(ctx: JobContext) -> int | None:
    if ctx.requested_by_user_id is not None:
        return ctx.requested_by_user_id
    configured = os.getenv("STEP_REGISTER_ACTOR_USER_ID", "").strip()
    return int(configured) if configured.isdigit() else None


def _publish_register(ctx: JobContext) -> dict:
    actor_id = _register_actor(ctx)
    if actor_id is None:
        logger.warning(
            "Job STEP %s: registro avvisi non aggiornato, manca l'utente autore", ctx.job_id
        )
        return {"skipped": "STEP_REGISTER_ACTOR_USER_ID non configurato"}
    with ctx.session_factory() as db:
        return publish_recoveries(db, actor_id=actor_id, job_id=ctx.job_id, now=datetime.now(UTC))


async def _run_archive_import(ctx: JobContext) -> tuple[str, dict]:
    archive = storage.resolve_import_archive(str(ctx.payload.get("archive_name") or ""))

    def progress(values: dict) -> None:
        with ctx.session_factory() as progress_db:
            update_progress(progress_db, ctx.job_id, values)

    def run() -> dict:
        with ctx.session_factory() as db:
            return import_archive(db, archive, job_id=ctx.job_id, progress=progress)

    # Blocking DB/file work runs in a thread so the worker heartbeat keeps beating.
    return "succeeded", await asyncio.to_thread(run)


async def _run_relink(ctx: JobContext) -> tuple[str, dict]:
    def run() -> dict:
        with ctx.session_factory() as db:
            links = relink_all(db, now=datetime.now(UTC))
            db.commit()
            return links

    return "succeeded", {"links": await asyncio.to_thread(run)}


def _load_credential(ctx: JobContext) -> _Credential:
    with ctx.session_factory() as db:
        credential, password = pick_credential(db, ctx.payload.get("credential_id"))
        return _Credential(
            credential.id,
            credential.username,
            password,
            credential.portal_url,
            credential.min_delay_ms,
        )


def _client(ctx: JobContext, credential: _Credential):
    return ctx.client_class(
        StepClientConfig(
            portal_url=credential.portal_url,
            headless=ctx.headless,
            min_delay_ms=credential.min_delay_ms,
        )
    )


async def _login(ctx: JobContext, client, credential: _Credential) -> None:
    try:
        await client.login(credential.username, credential.password)
    except StepLoginError as exc:
        with ctx.session_factory() as db:
            mark_credential_error(db, credential.id, str(exc))
        raise
    with ctx.session_factory() as db:
        mark_credential_used(db, credential.id)


async def _run_credential_test(ctx: JobContext) -> tuple[str, dict]:
    credential = _load_credential(ctx)
    async with _client(ctx, credential) as client:
        await _login(ctx, client, credential)
    return "succeeded", {"ok": True, "checked_at": datetime.now(UTC).isoformat()}


@dataclass
class _LiveSync:
    ctx: JobContext
    credential: _Credential
    pending: list[tuple[int, dict]] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    counts: dict = field(
        default_factory=lambda: {
            "list_rows": 0,
            "new": 0,
            "summary_changed": 0,
            "details": 0,
            "details_changed": 0,
        }
    )
    links: dict = field(default_factory=dict)
    reference: ListReference | None = None
    client: object = None

    async def open(self) -> dict:
        self.client = _client(self.ctx, self.credential)
        await self.client.__aenter__()
        await _login(self.ctx, self.client, self.credential)
        return await self.client.open_contribuenti()

    async def close(self) -> None:
        if self.client is not None:
            await self.client.__aexit__(None, None, None)
            self.client = None

    def _progress(self, phase: str) -> None:
        with self.ctx.session_factory() as db:
            update_progress(
                db, self.ctx.job_id, {"phase": phase, **self.counts, "errors": len(self.errors)}
            )

    async def scan_list(self, state: dict) -> dict:
        self.reference = ListReference.from_first_page(state)
        seen: set[str] = set()
        for page_number in range(1, self.reference.pages + 1):
            if page_number > 1:
                state = await self.client.go_to_page(page_number, state)
            if state["page"] != page_number:
                raise StepIntegrityError(
                    f"Pagina STEP attuale {state['page']}, attesa {page_number}"
                )
            self.reference.validate(state)
            self._store_page(state, page_number, seen)
            if page_number % 10 == 0:
                self._progress("elenco")
        if len(seen) != self.reference.total:
            raise StepIntegrityError(
                "Il numero di contribuenti STEP letti non coincide con il totale"
            )
        return state

    def _store_page(self, state: dict, page_number: int, seen: set[str]) -> None:
        now = datetime.now(UTC)
        force = bool(self.ctx.payload.get("force_details"))
        with self.ctx.session_factory() as db:
            for offset, row in enumerate(state["rows"]):
                key = record_key(row)
                if key in seen:
                    raise StepIntegrityError(f"Contribuente STEP duplicato a pagina {page_number}")
                seen.add(key)
                result = upsert_summary(db, row, job_id=self.ctx.job_id, now=now)
                self.counts["list_rows"] += 1
                self.counts["new"] += int(result.created)
                self.counts["summary_changed"] += int(result.summary_changed and not result.created)
                if force or needs_detail(result.contribuente):
                    self.pending.append(
                        ((page_number - 1) * self.reference.page_size + offset, row)
                    )
            db.commit()

    async def fetch_details(self, state: dict) -> None:
        limit = self.ctx.payload.get("max_details")
        queue = self.pending[:limit] if limit else list(self.pending)
        failures = 0
        for position, (index, summary) in enumerate(queue, 1):
            try:
                state = await self._fetch_one(state, index, summary)
                failures = 0
            except Exception as exc:
                failures += 1
                self._record_error(summary, exc)
                if failures >= MAX_CONSECUTIVE_SCHEDA_FAILURES:
                    self.errors.append(
                        {
                            "error": "Tre errori consecutivi: lettura schede interrotta",
                            "remaining": len(queue) - position,
                        }
                    )
                    return
                await self.close()
                state = await self.open()
            if position % 25 == 0:
                self._progress("schede")

    async def _fetch_one(self, state: dict, index: int, summary: dict) -> dict:
        target = self.reference.page_of(index)
        if state["page"] != target:
            state = await self.client.go_to_page(target, state)
        live = (
            state["rows"][index % self.reference.page_size]
            if index % self.reference.page_size < len(state["rows"])
            else None
        )
        if (
            live is None
            or record_key(live) != record_key(summary)
            or live.get("NUMERODOC") != summary.get("NUMERODOC")
        ):
            raise StepIntegrityError(
                "Posizione o numero documenti del contribuente STEP cambiati durante la lettura"
            )
        scheda = await self.client.extract_scheda(summary)
        self._persist(scheda)
        return state

    def _persist(self, scheda: dict) -> None:
        contents = _detach_pdf_contents(scheda)

        def pdf_store(contribuente: StepContribuente, entry: dict) -> StoredPdf:
            pdf = entry.get("pdf") or {}
            content = contents.get(id(entry))
            if content is None:
                return StoredPdf(status="unavailable", unavailable_reason=pdf.get("reason"))
            return storage.store_pdf(
                content, cod_ent=contribuente.cod_ent, original_filename=pdf.get("originalFilename")
            )

        with self.ctx.session_factory() as db:
            result = persist_scheda(
                db, scheda, job_id=self.ctx.job_id, now=datetime.now(UTC), pdf_store=pdf_store
            )
            for status, count in link_documents(
                db, list(result.document_ids), now=datetime.now(UTC)
            ).items():
                self.links[status] = self.links.get(status, 0) + count
            db.commit()
        self.counts["details"] += 1
        self.counts["details_changed"] += int(result.changed)

    def _record_error(self, summary: dict, exc: Exception) -> None:
        logger.warning(
            "Job STEP %s: scheda %s non acquisita: %s",
            self.ctx.job_id,
            summary.get("COD_FIS_NEW"),
            exc,
        )
        if len(self.errors) < _MAX_REPORTED_ERRORS:
            self.errors.append(
                {"codice_fiscale": summary.get("COD_FIS_NEW"), "error": str(exc)[:500]}
            )

    def result(self) -> dict:
        with self.ctx.session_factory() as db:
            not_seen = db.scalar(
                select(func.count())
                .select_from(StepContribuente)
                .where(StepContribuente.last_seen_job_id.is_distinct_from(self.ctx.job_id))
            )
        return {
            **self.counts,
            "list_total": self.reference.total if self.reference else None,
            "details_pending": len(self.pending),
            "not_seen_in_list": int(not_seen or 0),
            "links": self.links,
            "errors": self.errors,
        }


def _detach_pdf_contents(scheda: dict) -> dict[int, bytes]:
    """Move PDF bytes out of the scheda (kept out of the stored observation) and record their hash."""

    contents: dict[int, bytes] = {}
    for entry in scheda.get("documents") or []:
        pdf = entry.get("pdf") or {}
        content = pdf.pop("content", None)
        if content is not None:
            pdf["sha256"] = storage.validate_pdf(content)
            pdf["bytes"] = len(content)
            contents[id(entry)] = content
    return contents


async def _run_live(ctx: JobContext) -> tuple[str, dict]:
    credential = _load_credential(ctx)
    run = _LiveSync(ctx, credential)
    try:
        state = await run.scan_list(await run.open())
        if ctx.mode == "sync":
            await run.fetch_details(state)
    finally:
        await run.close()
    return ("completed_with_errors" if run.errors else "succeeded"), run.result()


_HANDLERS = {
    "archive_import": _run_archive_import,
    "relink": _run_relink,
    "credential_test": _run_credential_test,
    "list_only": _run_live,
    "sync": _run_live,
}
