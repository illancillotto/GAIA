"""Authenticate under the credential lease before spending a request attempt."""

from datetime import datetime, timedelta, timezone
from time import monotonic
from uuid import uuid4

from sqlalchemy import select, text

from app.models.catasto import CatastoCredential
from app.modules.elaborazioni.telemetry_models import SisterPortalEvent

UTC = timezone.utc  # noqa: UP017 - Deployed worker uses Python 3.10.


def authentication_reason(message: str) -> str:
    text = message.lower()
    markers = (
        ("utente non abilitato", "account_not_enabled"),
        ("password cambiata", "password_changed"),
        ("password modificata", "password_changed"),
        ("password scaduta", "password_expired"),
        ("credenziali sister rifiutate", "credentials_rejected"),
        ("session", "session_unavailable"),
    )
    return next((code for marker, code in markers if marker in text), "authentication_failed")


def suspension_seconds(failures: int) -> int:
    if failures < 3:
        return 180
    return min(900 * 2 ** min(failures - 3, 2), 3600)


def suspended_until(previous):
    if previous is None or previous.outcome != "error":
        return None
    until = previous.occurred_at.replace(tzinfo=UTC) + timedelta(seconds=previous.cooldown_seconds)
    return until if until > datetime.now(UTC) else None


def acquire_probe_lock(db, username):
    if db.get_bind().dialect.name != "postgresql":
        return True
    return db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
        {"key": "sister-auth:" + username},
    )


class SisterAuthenticationGate:
    """Caller holds the username lease, including the single recovery probe.

    Events retain the circuit across restarts. Storage failures propagate so
    an unavailable circuit never permits claiming requests without a check.
    """

    def __init__(self, runtime, session_factory):
        self.runtime = runtime
        self.session_factory = session_factory

    def previous(self, credential):
        with self.session_factory() as db:
            return db.scalar(
                select(SisterPortalEvent)
                .join(CatastoCredential, CatastoCredential.id == SisterPortalEvent.credential_id)
                .where(
                    CatastoCredential.sister_username == credential.sister_username,
                    SisterPortalEvent.event_type == "authentication_gate",
                )
                .order_by(SisterPortalEvent.occurred_at.desc(), SisterPortalEvent.id.desc())
                .limit(1)
            )

    async def ready(self, credential, browser) -> bool:
        if self.runtime.batch.batch_kind not in {"perpetual_sync", "ruolo_autosync"}:
            return True
        with self.session_factory() as lock_db:
            if not acquire_probe_lock(lock_db, credential.sister_username):
                return False
            previous = self.previous(credential)
            if suspended_until(previous) is not None:
                return False
            return await self.probe(credential, browser, previous)

    def suspended(self, credential) -> bool:
        if self.runtime.batch.batch_kind not in {"perpetual_sync", "ruolo_autosync"}:
            return False
        until = suspended_until(self.previous(credential))
        if until is None:
            return False
        self.runtime.worker._set_batch_operation(
            self.runtime.batch_id,
            f"Credenziale {credential.label}: autenticazione sospesa fino a {until.isoformat()}",
        )
        return True

    async def probe(self, credential, browser, previous) -> bool:
        observability = getattr(self.runtime.worker, "_sister_observability", None)
        if observability is not None:
            observability._binding(browser, credential, self.runtime.batch_id)
        started = monotonic()
        failures = 0
        reason = None
        try:
            await browser.ensure_authenticated(
                credential.sister_username,
                self.runtime.worker.vault.decrypt(credential.sister_password_encrypted),
            )
        except Exception as exc:
            failures = (previous.attempt if previous is not None else 0) + 1
            reason = authentication_reason(str(exc))
        self.record(credential, failures, reason, round((monotonic() - started) * 1000))
        return failures == 0

    def record(self, credential, failures, reason, duration_ms):
        with self.session_factory() as db:
            db.add(
                SisterPortalEvent(
                    occurred_at=datetime.now(UTC),
                    user_id=credential.user_id,
                    batch_id=self.runtime.batch_id,
                    credential_id=credential.id,
                    session_id=uuid4(),
                    event_type="authentication_gate",
                    step="preclaim_authentication",
                    outcome="error" if failures else "success",
                    severity="warning" if failures else "info",
                    duration_ms=duration_ms,
                    attempt=failures,
                    cooldown_seconds=suspension_seconds(failures) if failures else 0,
                    context_json={"error_code": reason} if reason else None,
                )
            )
            db.commit()
