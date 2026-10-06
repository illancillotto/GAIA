from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from app.modules.ruolo.models import (
    RuoloTributiPayment,
    RuoloTributiPaymentImportJob,
    RuoloTributiRegisteredMail,
)

from . import test_notice_import as fixture_source
from . import test_registered_mail_campaign_preview as records

api_fixture = fixture_source.api


@pytest.fixture(scope="module")
def api_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = fixture_source._metadata()
    metadata.remove(metadata.tables["ruolo_tributi_payments"])
    RuoloTributiPaymentImportJob.__table__.to_metadata(metadata)
    RuoloTributiPayment.__table__.to_metadata(metadata)
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize(
    ("selection", "legacy"),
    [([], False), ([0], False), ([0, 1], False), ([1, 0], False), ([1], True)],
    ids=["unlink", "single", "cumulative", "reversed-primary", "legacy-single"],
)
def test_association_persists_authoritative_selection(api_fixture, selection, legacy):
    with api_fixture.session() as session:
        subject_id = uuid4()
        subjects = fixture_source._metadata().tables["ana_subjects"]
        session.execute(subjects.insert().values(id=subject_id))
        notices = records.pair(session, subject_id)
        record = records.mail(
            session,
            avviso_id=notices[0].id,
            subject_id=subject_id,
            match_status="matched",
        )
        record_id = record.id
        selected_ids = [str(notices[index].id) for index in selection]
        session.commit()

    payload = {"avviso_ids": selected_ids}
    if legacy:
        payload = {"avviso_id": selected_ids[0]}
    response = api_fixture.client.patch(
        f"/ruolo/tributi/raccomandate/{record_id}/association", json=payload
    )
    assert response.status_code == 200, response.text
    expected_primary = selected_ids[0] if selected_ids else None
    expected_subject = str(subject_id) if selected_ids else None
    expected_status = "matched" if selected_ids else "unmatched"
    result = response.json()
    assert result["avviso_ids"] == selected_ids
    assert result["avviso_id"] == expected_primary
    assert result["subject_id"] == expected_subject
    assert result["match_status"] == expected_status

    with api_fixture.session() as session:
        stored = session.get(RuoloTributiRegisteredMail, record_id)
        assert stored.avviso_id == (UUID(expected_primary) if expected_primary else None)
        assert stored.subject_id == (subject_id if selected_ids else None)
        assert stored.match_status == expected_status
        association = stored.raw_payload_json["manual_association"]
        assert association["active"] is True
        assert association["avviso_id"] == expected_primary
        assert association["avviso_ids"] == selected_ids
        assert association["updated_by"] == 1
