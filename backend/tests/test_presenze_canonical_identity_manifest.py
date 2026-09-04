from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.presenze.mapping_audit import PresenzeCollaboratorMappingAudit
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeEventSummary,
    PresenzeImportJob,
)
from app.modules.presenze.services.canonical_identity_manifest import (
    CanonicalIdentityEntry,
    CanonicalIdentityManifestError,
    apply_canonical_identity_manifest,
    parse_canonical_identity_manifest,
)
from scripts import backfill_presenze_canonical_identities as backfill_script

COLLABORATOR_ID = uuid.UUID("13126cf8-32b6-4206-9910-58374f125681")


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ApplicationUser.__table__,
            WCOperator.__table__,
            PresenzeImportJob.__table__,
            PresenzeCollaborator.__table__,
            PresenzeDailyRecord.__table__,
            PresenzeEventSummary.__table__,
            PresenzeCollaboratorMappingAudit.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _user(user_id: int, username: str) -> ApplicationUser:
    return ApplicationUser(
        id=user_id,
        username=username,
        email=f"{username}@example.test",
        password_hash="hash",
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
    )


def _operator(user_id: int, *, wc_id: int, area: str | None = None) -> WCOperator:
    return WCOperator(
        wc_id=wc_id,
        gaia_user_id=user_id,
        enabled=True,
        personnel_area=area,
    )


def _manifest(*people: object, **person: object) -> dict[str, object]:
    rows = list(people)
    if person:
        rows.append(person)
    return {"version": 1, "people": rows}


def test_manifest_backfill_is_atomic_audited_and_idempotent() -> None:
    db = _session()
    try:
        actor = _user(1, "manifest.actor")
        person = _user(238, "manifest.person")
        operator = _operator(person.id, wc_id=2380)
        collaborator = PresenzeCollaborator(
            id=COLLABORATOR_ID,
            employee_code="1423",
            name="Canonical Person",
        )
        daily = PresenzeDailyRecord(
            collaborator_id=collaborator.id,
            work_date=date(2026, 8, 1),
        )
        summary = PresenzeEventSummary(
            collaborator_id=collaborator.id,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            description="Test",
        )
        db.add_all([actor, person, operator, collaborator, daily, summary])
        db.commit()
        entries = parse_canonical_identity_manifest(
            _manifest(
                gaia_user_id=238,
                personnel_area="IMPIANTI",
                presenze_collaborator_id=str(COLLABORATOR_ID),
            )
        )

        dry_run = apply_canonical_identity_manifest(
            db,
            entries,
            changed_by=actor,
            reason="Reparto Nord canonical mapping",
            dry_run=True,
        )
        assert dry_run.as_dict() == {
            "entries": 1,
            "operator_area_changes": 1,
            "collaborator_mapping_changes": 1,
            "unchanged": 0,
            "dry_run": True,
        }
        assert operator.personnel_area is None
        assert collaborator.application_user_id is None

        applied = apply_canonical_identity_manifest(
            db,
            entries,
            changed_by=actor,
            reason=" Reparto Nord canonical mapping ",
            dry_run=False,
        )
        assert applied.operator_area_changes == 1
        assert applied.collaborator_mapping_changes == 1
        assert operator.personnel_area == "IMPIANTI"
        assert collaborator.application_user_id == person.id
        assert daily.application_user_id == person.id
        assert summary.application_user_id == person.id
        audit = db.query(PresenzeCollaboratorMappingAudit).one()
        assert audit.source == "canonical_manifest"
        assert audit.reason == "Reparto Nord canonical mapping"

        repeated = apply_canonical_identity_manifest(
            db,
            entries,
            changed_by=actor,
            reason="Reparto Nord canonical mapping",
            dry_run=False,
        )
        assert repeated.unchanged == 1
        assert repeated.operator_area_changes == 0
        assert repeated.collaborator_mapping_changes == 0
        assert db.query(PresenzeCollaboratorMappingAudit).count() == 1
    finally:
        db.close()


@pytest.mark.parametrize(
    "raw,message",
    [
        ({}, "version=1"),
        ({"version": 1, "people": []}, "non contiene persone"),
        (_manifest("invalid"), "campi non validi"),
        (
            _manifest(gaia_user_id=1, personnel_area="AGRARIO", username="forbidden"),
            "campi non validi",
        ),
        (_manifest(gaia_user_id=True, personnel_area="AGRARIO"), "intero positivo"),
        (_manifest(gaia_user_id=0, personnel_area="AGRARIO"), "intero positivo"),
        (_manifest(gaia_user_id=1, personnel_area="TETI"), "personnel_area non valida"),
        (
            _manifest(
                {"gaia_user_id": 1, "personnel_area": "AGRARIO"},
                {"gaia_user_id": 1, "personnel_area": "IMPIANTI"},
            ),
            "gaia_user_id duplicato",
        ),
        (
            _manifest(gaia_user_id=1, personnel_area="AGRARIO", presenze_collaborator_id=123),
            "deve essere un UUID",
        ),
        (
            _manifest(gaia_user_id=1, personnel_area="AGRARIO", presenze_collaborator_id="bad"),
            "deve essere un UUID",
        ),
        (
            _manifest(
                {
                    "gaia_user_id": 1,
                    "personnel_area": "AGRARIO",
                    "presenze_collaborator_id": str(COLLABORATOR_ID),
                },
                {
                    "gaia_user_id": 2,
                    "personnel_area": "IMPIANTI",
                    "presenze_collaborator_id": str(COLLABORATOR_ID),
                },
            ),
            "presenze_collaborator_id duplicato",
        ),
    ],
)
def test_manifest_parser_rejects_noncanonical_or_ambiguous_rows(raw: object, message: str) -> None:
    with pytest.raises(CanonicalIdentityManifestError, match=message):
        parse_canonical_identity_manifest(raw)


def test_manifest_database_validation_fails_before_writes() -> None:
    db = _session()
    try:
        actor = _user(1, "validation.actor")
        person = _user(2, "validation.person")
        other = _user(3, "validation.other")
        operator = _operator(person.id, wc_id=20)
        collaborator = PresenzeCollaborator(id=COLLABORATOR_ID, employee_code="E2", name="Person")
        other_collaborator = PresenzeCollaborator(
            id=uuid.uuid4(),
            employee_code="E3",
            name="Other",
        )
        db.add_all([actor, person, other, operator, collaborator, other_collaborator])
        db.commit()

        cases = [
            (CanonicalIdentityEntry(999, "AGRARIO"), "gaia_user_id 999 non trovato"),
            (CanonicalIdentityEntry(other.id, "AGRARIO"), "WCOperator non univoca"),
            (
                CanonicalIdentityEntry(person.id, "AGRARIO", uuid.uuid4()),
                "presenze_collaborator_id .* non trovato",
            ),
        ]
        for entry, message in cases:
            with pytest.raises(CanonicalIdentityManifestError, match=message):
                apply_canonical_identity_manifest(
                    db,
                    [entry],
                    changed_by=actor,
                    reason="validation",
                    dry_run=False,
                )
            assert operator.personnel_area is None

        db.add(_operator(person.id, wc_id=21))
        db.commit()
        with pytest.raises(CanonicalIdentityManifestError, match="WCOperator non univoca"):
            apply_canonical_identity_manifest(
                db,
                [CanonicalIdentityEntry(person.id, "AGRARIO")],
                changed_by=actor,
                reason="validation",
                dry_run=False,
            )
        db.query(WCOperator).filter(WCOperator.wc_id == 21).delete()
        collaborator.application_user_id = other.id
        db.commit()
        with pytest.raises(CanonicalIdentityManifestError, match="collegato a un altro"):
            apply_canonical_identity_manifest(
                db,
                [CanonicalIdentityEntry(person.id, "AGRARIO", collaborator.id)],
                changed_by=actor,
                reason="validation",
                dry_run=False,
            )
        collaborator.application_user_id = None
        other_collaborator.application_user_id = person.id
        db.commit()
        with pytest.raises(CanonicalIdentityManifestError, match="gia collegato"):
            apply_canonical_identity_manifest(
                db,
                [CanonicalIdentityEntry(person.id, "AGRARIO", collaborator.id)],
                changed_by=actor,
                reason="validation",
                dry_run=False,
            )
        with pytest.raises(CanonicalIdentityManifestError, match="motivo"):
            apply_canonical_identity_manifest(
                db,
                [CanonicalIdentityEntry(person.id, "AGRARIO")],
                changed_by=actor,
                reason=" ",
                dry_run=True,
            )
    finally:
        db.close()


def test_backfill_script_dry_run_and_missing_actor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = _session()
    actor = _user(1, "script.actor")
    person = _user(2, "script.person")
    db.add_all([actor, person, _operator(person.id, wc_id=20)])
    db.commit()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(_manifest(gaia_user_id=2, personnel_area="AGRARIO")),
        encoding="utf-8",
    )
    monkeypatch.setattr(backfill_script, "SessionLocal", lambda: db)

    assert (
        backfill_script.main(
            [str(manifest_path), "--changed-by-gaia-user-id", "1", "--reason", "test"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["dry_run"] is True

    assert (
        backfill_script.main(
            [
                str(manifest_path),
                "--changed-by-gaia-user-id",
                "1",
                "--reason",
                "audit",
                "--require-unchanged",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert json.loads(output.out)["operator_area_changes"] == 1
    assert "IDENTITY_MANIFEST_DRIFT" in output.err

    assert (
        backfill_script.main(
            [str(manifest_path), "--changed-by-gaia-user-id", "1", "--reason", "test", "--apply"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["operator_area_changes"] == 1

    assert (
        backfill_script.main(
            [
                str(manifest_path),
                "--changed-by-gaia-user-id",
                "1",
                "--reason",
                "audit",
                "--require-unchanged",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["unchanged"] == 1

    with pytest.raises(CanonicalIdentityManifestError, match="read-only"):
        backfill_script.main(
            [
                str(manifest_path),
                "--changed-by-gaia-user-id",
                "1",
                "--reason",
                "invalid",
                "--apply",
                "--require-unchanged",
            ]
        )

    with pytest.raises(CanonicalIdentityManifestError, match="autore"):
        backfill_script.main(
            [str(manifest_path), "--changed-by-gaia-user-id", "999", "--reason", "test"]
        )
