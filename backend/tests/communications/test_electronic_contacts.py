"""Real API/SQL resolution for companies and individuals; synthetic contacts only."""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from ruolo.test_notice_register_api import _headers

from app.modules.communications import ruolo_source
from app.modules.utenze.contact_models import AnagraficaElectronicContact as Contact
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.modules.utenze.services import electronic_contacts as service
from app.modules.utenze.services.contact_assessment import assess

from .conftest import approved, metadata


def subject(api, kind="person", legacy=None):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        value = AnagraficaSubject(subject_type=kind, source_name_raw="Synthetic individual")
        db.add(value)
        db.flush()
        item.subject_id = value.id
        if kind == "person":
            db.add(
                AnagraficaPerson(
                    subject_id=value.id,
                    codice_fiscale="SYNTHETIC1234567",
                    nome="Test",
                    cognome="Test",
                    email=legacy,
                )
            )
        else:
            db.add(
                AnagraficaCompany(
                    subject_id=value.id,
                    partita_iva="12345678901",
                    ragione_sociale="Synthetic company",
                    email_pec=legacy,
                )
            )
        db.commit()
        return value.id


def classify(api, identity, **changes):
    return api.client.put(
        f"/communications/admin/subjects/{identity}/contacts",
        json={
            "address": "reviewed@example.org",
            "channel": "pec",
            "state": "active",
            "source": "synthetic",
            "evidence_reference": "synthetic reviewed contact #1",
            "expected_version": 0,
            **changes,
        },
    )


def candidates(api, channel, **params):
    return api.client.get(
        "/communications/ruolo/candidates", params={"channel": channel, **params}
    ).json()


@pytest.mark.parametrize("kind", ["person", "company"])
@pytest.mark.parametrize("channel", ["pec", "email"])
def test_both_channels_for_both_subject_types_and_filters(api, kind, channel):
    sid = subject(api, kind)
    response = classify(api, sid, channel=channel, address=" Reviewed@EXAMPLE.org ")
    assert response.status_code == 200, response.text
    assert response.json()["address"] == "reviewed@example.org"
    assert response.json()["version"] == 1
    other = "email" if channel == "pec" else "pec"
    result = candidates(api, channel, **{f"has_{channel}": "true"})
    assert result["total"] == 1
    assert result["items"][0][channel] == "reviewed@example.org"
    assert result["items"][0][other] is None
    assert candidates(api, channel, **{f"has_{channel}": "false"})["total"] == 0
    assert candidates(api, channel, has_contact="true")["total"] == 1
    assert candidates(api, other, has_contact="true")["total"] == 0
    with api.session() as db:
        assert ruolo_source.contacts(db, ruolo_source.source_item(db, api.source_id)) == {
            channel: "reviewed@example.org",
            other: None,
        }
        assert db.scalar(sa.select(AnagraficaAuditLog)).diff_json["before"] is None
    listing = api.client.get(f"/communications/admin/subjects/{sid}/contacts").json()
    assert listing["resolved"][channel] == "reviewed@example.org"
    assert len(listing["items"]) == 1


@pytest.mark.parametrize("kind,channel", [("person", "email"), ("company", "pec")])
def test_legacy_fields_preserved_until_classified(api, kind, channel):
    sid = subject(api, kind, "legacy@example.org")
    assert candidates(api, channel, has_contact="true")["total"] == 1
    with api.session() as db:
        assert service.contact_values(db, sid)[channel] == "legacy@example.org"
    other = "pec" if channel == "email" else "email"
    assert classify(api, sid, address="legacy@example.org", channel=other).status_code == 200
    assert candidates(api, channel, has_contact="true")["total"] == 0
    assert candidates(api, other, has_contact="true")["total"] == 1
    assert candidates(api, other)["items"][0][other] == "legacy@example.org"


@pytest.mark.parametrize("kind,channel", [("person", "email"), ("company", "pec")])
def test_quarantined_invalid_legacy_stays_preserved_and_cannot_be_activated(api, kind, channel):
    from types import SimpleNamespace

    sid = subject(api, kind, "invalid-legacy-address")
    with api.session() as db:
        service.classify(
            db,
            sid,
            SimpleNamespace(
                address="invalid-legacy-address",
                channel="unclassified",
                state="review",
                source="synthetic_legacy_quarantine",
                evidence_reference="Invalid historical value retained solely for review",
                expected_version=0,
            ),
            None,
        )
        db.commit()
        legacy = db.get(AnagraficaPerson if kind == "person" else AnagraficaCompany, sid)
        assert (
            getattr(legacy, "email" if kind == "person" else "email_pec")
            == "invalid-legacy-address"
        )
        assert service.contact_values(db, sid) == {"email": None, "pec": None}
        audit = db.scalar(sa.select(AnagraficaAuditLog))
        assert audit.changed_by_user_id is None
        assert audit.diff_json["after"]["state"] == "review"
    assert candidates(api, channel, has_contact="true")["total"] == 0
    assert candidates(api, channel, has_contact="false")["total"] == 1
    assert (
        classify(
            api, sid, address="invalid-legacy-address", channel=channel, expected_version=1
        ).status_code
        == 422
    )
    result = api.client.get(f"/communications/admin/subjects/{sid}/contacts").json()
    assert result["items"][0]["state"] == "review"
    assert result["resolved"] == {"email": None, "pec": None}


@pytest.mark.parametrize(
    "channel,state", [("pec", "revoked"), ("pec", "review"), ("unclassified", "review")]
)
def test_revoked_unknown_and_pending_do_not_fall_back_to_legacy(api, channel, state):
    sid = subject(api, legacy="legacy@example.org")
    assert (
        classify(api, sid, address="legacy@example.org", channel=channel, state=state).status_code
        == 200
    )
    for chosen in ("pec", "email"):
        assert candidates(api, chosen, has_contact="true")["total"] == 0
        assert candidates(api, chosen, **{f"has_{chosen}": "false"})["total"] == 1


def test_multiple_addresses_require_review_and_can_be_resolved(api):
    sid = subject(api)
    assert classify(api, sid).status_code == 200
    assert classify(api, sid, address="second@example.org").status_code == 200
    assert candidates(api, "pec", has_pec="true")["total"] == 0
    response = classify(api, sid, address="second@example.org", state="revoked", expected_version=1)
    assert response.status_code == 200 and response.json()["version"] == 2
    assert candidates(api, "pec", has_pec="true")["items"][0]["pec"] == "reviewed@example.org"
    with api.session() as db:
        audits = list(db.scalars(sa.select(AnagraficaAuditLog)))
        assert len(audits) == 3
        assert audits[-1].diff_json["before"]["state"] == "active"
        assert audits[-1].diff_json["after"]["state"] == "revoked"


@pytest.mark.parametrize(
    "changes",
    [
        {"address": "invalid"},
        {"address": "a@example.org\r\nBcc:other@example.org"},
        {"channel": "sms"},
        {"state": "deleted"},
        {"channel": "unclassified", "state": "active"},
        {"evidence_reference": " "},
        {"source": " "},
        {"expected_version": -1},
        {"extra": True},
    ],
)
def test_invalid_classification_rejected_without_writes(api, changes):
    sid = subject(api)
    assert classify(api, sid, **changes).status_code == 422
    with api.session() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(Contact)) == 0


@pytest.mark.parametrize("user", [2, 3, 4, 5])
def test_classification_is_admin_only(api, user):
    sid = subject(api)
    path = f"/communications/admin/subjects/{sid}/contacts"
    assert api.client.put(path, json={}, headers=_headers(user)).status_code in (401, 403)
    assert api.client.get(path, headers=_headers(user)).status_code in (401, 403)


def test_missing_inactive_replay_stale_and_database_error(api, monkeypatch):
    assert classify(api, uuid4()).status_code == 404
    sid = subject(api)
    assert classify(api, sid).status_code == 200
    assert classify(api, sid).status_code == 409
    assert classify(api, sid, expected_version=7).status_code == 409
    with api.session() as db:
        db.get(AnagraficaSubject, sid).status = "inactive"
        db.commit()
    assert classify(api, sid, expected_version=1).status_code == 409

    def fail(*args):
        raise sa.exc.IntegrityError("synthetic", {}, Exception("sensitive detail"))

    monkeypatch.setattr(service, "classify", fail)
    response = classify(api, sid, expected_version=1)
    assert response.status_code == 409 and "sensitive" not in response.text
    assert api.client.get(f"/communications/admin/subjects/{uuid4()}/contacts").json() == {
        "resolved": {"email": None, "pec": None},
        "items": [],
    }


def test_contact_change_invalidates_prior_authorization(api):
    sid = subject(api)
    assert classify(api, sid).status_code == 200
    value = approved(api)
    assert classify(api, sid, state="revoked", expected_version=1).status_code == 200
    response = api.client.post(
        f"/communications/messages/{value['id']}/dispatch", json={"expected_version": 1}
    )
    assert response.status_code == 409 and "cambiati" in response.text
    assert api.client.get("/communications/jobs").json() == []


@pytest.mark.parametrize(
    "evidence,channel,state,reason",
    [
        ([], "unclassified", "review", "missing_or_conflicting_type"),
        ([{"type": "PEC", "active_code": 1}], "pec", "active", "explicit_source_type"),
        ([{"type": "EMAIL", "active_code": 1}], "email", "active", "explicit_source_type"),
        ([{"type": "PEC", "active_code": -2}], "pec", "revoked", "source_revocation"),
        (
            [{"type": "PEC", "active_code": 1, "revocation_at": "2021-01-01"}],
            "pec",
            "revoked",
            "source_revocation",
        ),
        ([{"type": "PEC", "active_code": 0}], "pec", "review", "source_not_active"),
        (
            [{"type": "PEC", "active_code": 1}, {"type": "EMAIL", "active_code": 1}],
            "unclassified",
            "review",
            "missing_or_conflicting_type",
        ),
        (
            [{"type": "OTHER", "active_code": 1}],
            "unclassified",
            "review",
            "missing_or_conflicting_type",
        ),
    ],
)
def test_assessment_uses_explicit_type_and_activity(evidence, channel, state, reason):
    evidence = [dict(row, email="TEST@example.org") for row in evidence]
    assert assess(" test@example.org ", evidence) == {
        "address": "test@example.org",
        "channel": channel,
        "state": state,
        "reason": reason,
        "source_count": len(evidence),
    }


def test_assessment_never_guesses_from_domain_or_uses_unrelated_contacts():
    assert (
        assess("test@pec.it", [{"email": "other@pec.it", "type": "PEC", "active_code": 1}])[
            "channel"
        ]
        == "unclassified"
    )
    assert assess("bad address", [])["reason"] == "invalid_syntax"
    assert assess("test@example.org", [{"email": None, "type": "PEC"}])["source_count"] == 0


def test_migration_roundtrip_no_automatic_classification():
    source = metadata()
    source.remove(source.tables["ana_electronic_contacts"])
    engine = sa.create_engine("sqlite://")
    current = load_python_file(
        str(Path(__file__).resolve().parents[2] / "alembic" / "versions"),
        "20261104_1400_electronic_contacts.py",
    )
    with engine.begin() as connection:
        source.create_all(connection)
        with Operations.context(MigrationContext.configure(connection)):
            current.upgrade()
            assert connection.scalar(sa.text("SELECT count(*) FROM ana_electronic_contacts")) == 0
            current.downgrade()
            assert "ana_electronic_contacts" not in sa.inspect(connection).get_table_names()
            current.upgrade()
    engine.dispose()


def test_schema_registration_and_database_constraints(api):
    from app.db import base

    assert "ana_electronic_contacts" in base.Base.metadata.tables
    sid = subject(api)
    assert classify(api, sid).status_code == 200
    with api.session() as db:
        for values in (
            {"address": "reviewed@example.org"},
            {"channel": "sms"},
            {"state": "invalid"},
            {"version": 0},
            {"channel": "unclassified", "state": "active"},
            {"subject_id": uuid4()},
        ):
            with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
                db.add(
                    Contact(
                        **(
                            {
                                "subject_id": sid,
                                "address": "new@example.org",
                                "channel": "email",
                                "state": "active",
                                "source": "synthetic",
                                "evidence_reference": "Synthetic",
                                "version": 1,
                            }
                            | values
                        )
                    )
                )
                db.flush()
