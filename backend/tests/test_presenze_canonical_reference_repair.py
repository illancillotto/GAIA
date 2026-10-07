from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_presenze_api import (  # noqa: F401 - shared isolated database fixture
    TestingSessionLocal,
    _create_user,
    setup_database,
)
from test_presenze_meal_vouchers import _record

from app.models.application_user import ApplicationUser
from app.modules.presenze.mapping_audit import PresenzeCollaboratorMappingAudit
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeEventSummary,
)
from app.modules.presenze.services.canonical_reference_repair import repair_canonical_references


def fixture_data():
    actor = _create_user("repair-admin")
    target = _create_user("repair-target", role="viewer", module_presenze=False)
    rid, cid = _record(actor.id)
    with TestingSessionLocal() as db:
        db.get(PresenzeCollaborator, cid).application_user_id = target.id
        db.add(
            PresenzeEventSummary(
                collaborator_id=cid,
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 31),
                description="Ferie",
                event_code="F",
                saldo_minutes=90,
            )
        )
        db.commit()
    return actor.id, target.id, cid, rid


def test_dry_run_apply_idempotence_and_preserved_values():
    actor_id, uid, cid, rid = fixture_data()
    with TestingSessionLocal() as db:
        actor = db.get(ApplicationUser, actor_id)
        kwargs = dict(actor=actor, reason="User authorized existing canonical references")
        report = repair_canonical_references(db, [(uid, cid)], **kwargs)
        assert report == dict(
            dry_run=True,
            identities=1,
            daily_references=1,
            event_references=1,
            canonical_mapping_changes=0,
        )
        assert db.get(PresenzeDailyRecord, rid).application_user_id is None
        report = repair_canonical_references(db, [(uid, cid)], dry_run=False, **kwargs)
        db.commit()
        day = db.get(PresenzeDailyRecord, rid)
        assert (day.application_user_id, day.ordinary_minutes, day.schedule_code) == (
            uid,
            420,
            "OPE0613",
        )
        event = db.scalar(select(PresenzeEventSummary))
        assert (event.application_user_id, event.saldo_minutes) == (uid, 90)
        assert db.get(PresenzeCollaborator, cid).application_user_id == uid
        assert db.get(ApplicationUser, uid).module_presenze is False
        audit = db.scalar(select(PresenzeCollaboratorMappingAudit))
        assert (audit.previous_application_user_id, audit.new_application_user_id) == (uid, uid)
        assert audit.source == "canonical_references"
        for dry in (True, False):
            again = repair_canonical_references(db, [(uid, cid)], dry_run=dry, **kwargs)
            assert again["daily_references"] == again["event_references"] == 0
        db.commit()
        assert len(db.scalars(select(PresenzeCollaboratorMappingAudit)).all()) == 1


@pytest.mark.parametrize(
    "case",
    [
        "no_actor",
        "role",
        "reason",
        "empty",
        "duplicate",
        "missing_collaborator",
        "different_mapping",
        "missing_user",
        "daily_conflict",
        "event_conflict",
    ],
)
def test_invalid_batches_never_change_rows(case):
    actor_id, uid, cid, rid = fixture_data()
    with TestingSessionLocal() as db:
        actor = db.get(ApplicationUser, actor_id)
        reason = "Authorized repair"
        identities = [(uid, cid)]
        if case == "no_actor":
            actor = None
        if case == "role":
            actor = db.get(ApplicationUser, uid)
        if case == "reason":
            reason = "  "
        if case == "empty":
            identities = []
        if case == "duplicate":
            identities.append((uid, cid))
        if case == "missing_collaborator":
            identities = [(uid, uuid4())]
        if case == "different_mapping":
            identities = [(actor_id, cid)]
        if case == "missing_user":
            db.get(PresenzeCollaborator, cid).application_user_id = 999999
            identities = [(999999, cid)]
            db.flush()
        if case == "daily_conflict":
            db.get(PresenzeDailyRecord, rid).application_user_id = actor_id
            db.flush()
        if case == "event_conflict":
            db.scalar(select(PresenzeEventSummary)).application_user_id = actor_id
            db.flush()
        with pytest.raises(ValueError):
            repair_canonical_references(db, identities, actor=actor, reason=reason, dry_run=False)
        assert db.get(PresenzeDailyRecord, rid).application_user_id in (None, actor_id)
        assert db.scalar(select(PresenzeCollaboratorMappingAudit)) is None
