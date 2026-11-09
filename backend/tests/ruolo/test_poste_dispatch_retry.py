import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.modules.ruolo.poste_dispatch_models import PosteDispatchEvent
from app.modules.ruolo.services import poste_dispatch_retry as policy

from .test_poste_dispatch_accounts import complete_jobs, new_lot
from .test_poste_dispatch_service import db as db


def failure(identity=10, *, error="Timeout 60000ms exceeded.", completed=True):
    return SimpleNamespace(
        id=identity,
        status="failed",
        error_detail=error,
        completed_at=datetime.now(UTC) if completed else None,
        payload_json={"lot_id": "00000000-0000-0000-0000-000000000001"},
    )


@pytest.mark.parametrize(
    "error",
    [
        "Timeout 60000ms exceeded",
        "timed out",
        "net::ERR_SOCKET_NOT_CONNECTED",
        "Oops",
        "connection closed",
        "socket failure",
        "HTTP 429",
        "HTTP 503",
        "Archivio Poste Online non raggiunto dopo login: form_login_visibile",
        "Login Poste Online non completato",
        "Due bozze consecutive non create",
        "Poste Online detail:77 HTTP 403",
    ],
)
def test_transient_portal_failures_retry(error):
    assert policy.temporary_error(error)


@pytest.mark.parametrize(
    "error",
    [
        None,
        "unknown failure",
        "HTTP 403",
        "Poste Online detail:77 HTTP 4030",
        "Poste Online detail:abc HTTP 403",
        "Poste Online detail:77 HTTP 403 extra",
        "HTTP 5000",
        "password errata",
        "Login Poste Online richiede autenticazione interattiva o OTP non gestibile dal worker",
        "autorizzazione nell'app PosteBusiness",
        "credenziali non valide",
        "account bloccato",
        "Timeout con CAPTCHA",
        "troppi tentativi",
        "accesso non riuscito",
    ],
)
def test_explicit_attention_conditions_do_not_retry(error):
    assert not policy.temporary_error(error)


def test_progressive_delay_has_no_attempt_limit_and_survives_restart():
    config = {"state": "running"}
    for attempt in range(1, 105):
        job = failure(attempt)
        now = job.completed_at
        assert policy.retry_gate(config, job, now, jitter=lambda low, high: high) == "wait"
        expected = (18, 36, 72)[min(attempt, 3) - 1]
        assert config["retry"]["delay_seconds"] == expected
        original = dict(config["retry"])
        config = json.loads(json.dumps(config))
        # Repeated controller ticks/restarts keep exactly the stored deadline.
        assert (
            policy.retry_gate(config, job, now, jitter=lambda *_: pytest.fail("rescheduled"))
            == "wait"
        )
        assert config["retry"] == original
        due = datetime.fromisoformat(original["next_at_utc"])
        assert policy.retry_gate(config, job, due) == "retry"
        assert config["retry"]["attempt"] == attempt


def test_delay_uses_completion_time_not_controller_start_and_supports_naive_dates():
    job = failure()
    job.completed_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
    config = {"state": "paused", "reason": job.error_detail}
    assert policy.retry_gate(config, job, datetime.now(UTC), jitter=lambda *_: 0) == "retry"
    assert policy._aware(job.completed_at).tzinfo is UTC
    assert policy._aware(datetime.now(UTC)).tzinfo is UTC


def test_missing_completion_uses_now_and_default_jitter_is_bounded(monkeypatch):
    monkeypatch.setattr(policy.random, "randint", lambda low, high: low)
    config = {"state": "running"}
    now = datetime.now(UTC)
    assert policy.retry_gate(config, failure(completed=False), now) == "wait"
    assert datetime.fromisoformat(config["retry"]["next_at_utc"]) == now + timedelta(seconds=15)


@pytest.mark.parametrize(
    "error",
    [
        "Poste Oops: elenco temporaneamente non disponibile",
        "timed out",
        "Due bozze consecutive non create: lavorazione interrotta",
        "Poste Online detail:77 HTTP 403",
        "Page.goto: net::ERR_SOCKET_NOT_CONNECTED",
        "connection closed",
        "socket failure",
    ],
)
def test_fresh_session_recovery_retries_remain_within_one_minute_plus_jitter(error):
    config = {"state": "running"}
    for attempt, seconds in enumerate((18, 36, 72, 72), start=1):
        job = failure(attempt, error=error)
        now = job.completed_at
        assert policy.retry_gate(config, job, now, jitter=lambda low, high: high) == "wait"
        due = datetime.fromisoformat(config["retry"]["next_at_utc"])
        assert due == now + timedelta(seconds=seconds)
        assert policy.retry_gate(config, job, due - timedelta(microseconds=1)) == "wait"
        assert policy.retry_gate(config, job, due) == "retry"


@pytest.mark.parametrize(
    "error",
    ["HTTP 429", "Timeout: HTTP 429", "HTTP 503", "Login Poste Online non completato"],
)
def test_rate_limits_and_other_failures_keep_conservative_backoff(error):
    config = {"state": "running", "retry": {"attempt": 4}}
    job = failure(error=error)
    now = job.completed_at
    assert policy.retry_gate(config, job, now, jitter=lambda low, high: high) == "wait"
    assert datetime.fromisoformat(config["retry"]["next_at_utc"]) == now + timedelta(minutes=36)
    assert policy.retry_gate(config, job, now + timedelta(minutes=3)) == "wait"


def test_archive_login_redirect_retries_without_long_idle_or_restart_postponement():
    config = {"state": "running"}
    for attempt in range(1, 105):
        job = failure(
            attempt,
            error="Archivio Poste Online non raggiunto dopo login: form_login_visibile",
        )
        now = job.completed_at
        assert policy.retry_gate(config, job, now, jitter=lambda low, high: high) == "wait"
        delay = (72, 144, 360)[min(attempt, 3) - 1]
        deadline = now + timedelta(seconds=delay)
        assert config["retry"]["delay_seconds"] == delay
        config = json.loads(json.dumps(config))
        assert policy.retry_gate(config, job, deadline - timedelta(microseconds=1)) == "wait"
        assert policy.retry_gate(config, job, deadline) == "retry"
        assert config["retry"]["attempt"] == attempt


@pytest.mark.parametrize("attention", ["OTP", "CAPTCHA", "password errata", "account bloccato"])
def test_archive_login_redirect_preserves_explicit_attention_conditions(attention):
    error = f"Archivio Poste Online non raggiunto dopo login: {attention}"
    job = failure(error=error)
    config = {"state": "paused", "reason": error}
    assert not policy.temporary_error(error)
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "hold"


def test_archive_login_redirect_with_rate_limit_keeps_conservative_backoff():
    error = "Archivio Poste Online non raggiunto dopo login: HTTP 429 Timeout"
    assert policy._retry_delays(error) == policy.DELAYS_SECONDS


@pytest.mark.parametrize("state,expected", [("running", "normal"), ("paused", "hold")])
def test_no_job_or_busy_jobs_do_not_change_the_schedule(state, expected):
    for job in [None, *[SimpleNamespace(status=s) for s in policy.ACTIVE_STATUSES]]:
        config = {"state": state}
        assert policy.retry_gate(config, job, datetime.now(UTC)) == expected
        assert config == {"state": state}


def test_manual_pause_is_never_overridden_and_success_resets_progression():
    job = failure()
    config = {"state": "paused", "reason": "Operator is checking drafts"}
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "hold"


def test_committed_retry_recovers_a_stale_control_file_without_resetting_attempts():
    job = failure()
    job.payload_json["campaign_retry"] = {"attempt": 8, "error": "previous Timeout"}
    config = {"state": "paused", "reason": "previous Timeout"}
    assert policy.retry_gate(config, job, datetime.now(UTC), jitter=lambda *_: 0) == "wait"
    assert config["retry"]["attempt"] == 9
    job.status = "succeeded"
    config = {"state": "paused", "reason": "previous Timeout"}
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "normal"
    assert config["state"] == "running"
    config = {"state": "running", "retry": {"attempt": 100}}
    job.status = "succeeded"
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "normal"
    assert "retry" not in config
    job.status = "cancelled"
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "normal"
    job.status, job.error_detail = "failed", "OTP required"
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "normal"
    config = {"state": "paused", "reason": job.error_detail}
    assert policy.retry_gate(config, job, datetime.now(UTC)) == "hold"


def test_automatic_counter_hold_can_be_scheduled_but_manual_credential_disable_cannot():
    job = failure()
    config = {
        "state": "paused",
        "reason": "Credential absent or disabled; other campaign accounts may continue",
    }
    assert policy.retry_gate(config, job, datetime.now(UTC), jitter=lambda *_: 0) == "wait"
    assert not policy.retry_credential(None, None, job, None, actor_id=1)
    c = SimpleNamespace(active=False, consecutive_failures=5, last_error="manual disable")
    assert not policy.retry_credential(None, c, job, None, actor_id=1)


def test_due_retry_reconciles_same_account_preserves_uncertainty_and_audits(db, tmp_path):
    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    item.status = "draft_uncertain"
    job = db.scalars(select(PostaOnlineRegisteredMailSyncJob)).first()
    job.status, job.error_detail = "failed", "Timeout 60000ms exceeded."
    job.completed_at = datetime.now(UTC) - timedelta(minutes=10)
    c = db.get(PostaOnlineCredential, 1)
    c.active, c.consecutive_failures, c.last_error = False, 9, job.error_detail
    config = {"state": "running"}
    assert policy.retry_gate(config, job, datetime.now(UTC), jitter=lambda *_: 0) == "retry"
    queued = policy.queue_retry(db, config, job, c, actor_id=1)
    db.commit()
    assert queued.mode == "poste_dispatch_reconcile" and queued.credential_id == 1
    assert queued.payload_json["lot_id"] == str(lot.id)
    assert item.status == "draft_uncertain" and item.poste_draft_id is None
    assert job.status == "failed" and job.error_detail == "Timeout 60000ms exceeded."
    assert c.active and c.consecutive_failures == 9 and c.last_error == job.error_detail
    assert config["resume_after_job_id"] == queued.id
    assert config["retry"]["queued_job_id"] == queued.id
    events = list(
        db.scalars(
            select(PosteDispatchEvent).where(
                PosteDispatchEvent.kind.in_(
                    [
                        "credential_transient_retry_enabled",
                        "transient_retry_queued",
                    ]
                )
            )
        )
    )
    assert len(events) == 2 and all(event.actor_id == 1 for event in events)
    assert events[0].detail["success_claimed"] is False
    assert events[1].detail["send_action"] is False
    assert policy.retry_credential(db, c, job, lot, actor_id=1)


def test_due_retry_does_not_enable_an_operator_disabled_credential(db, tmp_path):
    lot, _ = new_lot(db, tmp_path)
    complete_jobs(db)
    job = db.scalars(select(PostaOnlineRegisteredMailSyncJob)).first()
    job.status, job.error_detail = "failed", "Timeout"
    c = db.get(PostaOnlineCredential, 1)
    c.active, c.consecutive_failures = False, 0
    config = {"state": "retry_wait", "retry": {"lot_id": str(lot.id)}}
    assert policy.queue_retry(db, config, job, c, actor_id=1) is None
    assert config["state"] == "paused" and not c.active


def archive_failure(db, tmp_path, *, status="draft_priced"):
    from app.modules.ruolo.services import poste_dispatch

    lot, item = new_lot(db, tmp_path)
    complete_jobs(db)
    item.status, item.poste_draft_id, item.poste_status = status, "77", "PREZZATO"
    job = poste_dispatch.request_job(db, lot.id, "reconcile", actor_id=1)
    job.status, job.error_detail = "failed", "Poste Online detail:77 HTTP 403"
    job.completed_at = datetime.now(UTC) - timedelta(minutes=10)
    cfg = {"state": "paused", "reason": job.error_detail}
    assert policy.retry_gate(cfg, job, datetime.now(UTC), jitter=lambda *_: 0) == "retry"
    return lot, item, job, cfg


def test_unreadable_archive_detail_holds_only_that_notice_and_reconciles_others(db, tmp_path):
    from app.modules.ruolo.services import poste_dispatch_work as work

    lot, item, old_job, cfg = archive_failure(db, tmp_path)
    previous_review = {"reason": "Previous address verification", "source_sha256": "verified"}
    item.address_review = previous_review
    before = (
        item.artifact,
        item.artifact_sha256,
        item.recipient,
        item.poste_address,
        item.poste_draft_id,
        item.poste_status,
        item.active_key,
        item.active_source_key,
    )
    _, other = new_lot(db, tmp_path)
    complete_jobs(db)
    old_job.status = "failed"
    other_before = other.status
    credential = db.get(PostaOnlineCredential, 1)
    queued = policy.queue_retry(db, cfg, old_job, credential, actor_id=1)
    db.commit()
    assert queued.mode == "poste_dispatch_reconcile" and queued.credential_id == 1
    assert queued.payload_json["lot_id"] == str(lot.id)
    assert item.status == "address_review" and other.status == other_before
    assert item.address_review["archive_shipment_id"] == "77"
    assert item.address_review["no_automatic_retry"] is True
    assert item.address_review["previous_review"] == previous_review
    assert before == (
        item.artifact,
        item.artifact_sha256,
        item.recipient,
        item.poste_address,
        item.poste_draft_id,
        item.poste_status,
        item.active_key,
        item.active_source_key,
    )
    assert not work.mark_draft_creating(db, item.id, job_id=queued.id)
    assert item.registered_mail_id is None and item.sent_at is None
    event = db.scalar(
        select(PosteDispatchEvent).where(PosteDispatchEvent.kind == "archive_detail_unavailable")
    )
    assert event.actor_id == 1 and event.job_id == old_job.id
    assert event.from_status == "draft_priced" and event.to_status == "address_review"
    assert event.detail["pdf_and_recipient_preserved"] is True


@pytest.mark.parametrize("status", ["cancel_requested", "sent", "address_review"])
def test_archive_403_does_not_override_protected_or_changed_states(db, tmp_path, status):
    _, item, job, cfg = archive_failure(db, tmp_path, status=status)
    assert policy.queue_retry(db, cfg, job, db.get(PostaOnlineCredential, 1), actor_id=1) is None
    assert cfg["state"] == "paused" and "protetto" in cfg["reason"]
    assert item.status == status and item.poste_draft_id == "77"
    assert not list(
        db.scalars(
            select(PosteDispatchEvent).where(
                PosteDispatchEvent.kind == "archive_detail_unavailable"
            )
        )
    )


def test_archive_403_without_an_identifiable_item_requires_review(db, tmp_path):
    _, item, job, cfg = archive_failure(db, tmp_path)
    item.poste_draft_id = "78"
    assert policy.queue_retry(db, cfg, job, db.get(PostaOnlineCredential, 1), actor_id=1) is None
    assert cfg["state"] == "paused" and item.status == "draft_priced"


@pytest.mark.parametrize("invalid", ["mode", "actor", "account"])
def test_archive_403_validates_the_bound_job_and_operator_before_holding(db, tmp_path, invalid):
    from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

    from .poste_dispatch_fixtures import seed_account

    _, item, job, cfg = archive_failure(db, tmp_path)
    if invalid == "mode":
        job.mode = "poste_dispatch_drafts"
    elif invalid == "actor":
        job.requested_by_user_id = None
    else:
        seed_account(db, 2, "other-poste-account")
        job.credential_id = 2
    with pytest.raises(DispatchConflict):
        policy.queue_retry(db, cfg, job, db.get(PostaOnlineCredential, 1), actor_id=1)
    assert item.status == "draft_priced" and item.address_review is None
