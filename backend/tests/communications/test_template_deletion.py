"""Confirmed version deletion preserves historical messages and template identity."""

from uuid import UUID, uuid4

import pytest
from ruolo.test_notice_register_api import _headers
from sqlalchemy import select

from app.modules.communications import models, policy, registry

from .conftest import create


def template(api, channel="pec", approve=False):
    response = api.client.post(
        "/communications/templates",
        json={
            "code": f"delete-test-{channel}",
            "name": "Sollecito sintetico",
            "channel": channel,
            "subject": "Avviso {{numero_avviso}}",
            "body": "Gentile {{contribuente_nome}}",
        },
    )
    assert response.status_code == 201, response.text
    value = response.json()
    if approve:
        response = api.client.post(f"/communications/templates/{value['id']}/approve")
        assert response.status_code == 200
        value = response.json()
    return next(
        row
        for row in api.client.get("/communications/admin/templates").json()
        if row["id"] == value["id"]
    )


@pytest.mark.parametrize("channel", ["pec", "email"])
@pytest.mark.parametrize("approve", [False, True])
def test_delete_hides_only_selected_version_and_is_idempotent(api, channel, approve):
    first = template(api, channel, approve)
    second = template(api, channel, approve)
    other_channel = template(api, "email" if channel == "pec" else "pec", True)
    path = f"/communications/templates/{second['id']}"
    for _ in range(2):
        response = api.client.request("DELETE", path, json={"confirmed": True})
        assert response.status_code == 200, response.text
        assert response.json() == second | {"status": "deleted"}
    admin_ids = {row["id"] for row in api.client.get("/communications/admin/templates").json()}
    operator_ids = {row["id"] for row in api.client.get("/communications/templates").json()}
    assert admin_ids == {first["id"], other_channel["id"]}
    assert second["id"] not in operator_ids
    assert (first["id"] in operator_ids) == approve
    assert other_channel["id"] in operator_ids
    with api.session() as db:
        persisted = db.get(models.CommunicationTemplate, UUID(second["id"]))
        assert persisted.status == "deleted"
        assert persisted.body == second["body"]
        assert persisted.version == 2
        events = list(
            db.scalars(
                select(models.CommunicationEvent).where(
                    models.CommunicationEvent.aggregate_id == persisted.id,
                    models.CommunicationEvent.kind == "template_deleted",
                )
            )
        )
        assert len(events) == 1
        assert events[0].actor_id == 1
        assert events[0].detail == {"version": 2, "previous_status": second["status"]}
        with pytest.raises(policy.Conflict, match="non approvato"):
            registry.approved_template(db, persisted.id, channel)
    assert api.client.post(f"{path}/approve").status_code == 409
    assert template(api, channel)["version"] == 3


@pytest.mark.parametrize("state", ["draft", "submitted"])
def test_delete_preserves_existing_message_and_exact_snapshot(api, state):
    value = template(api, approve=True)
    message = create(api, template_id=value["id"], subject=None, body=None)
    with api.session() as db:
        persisted = db.get(models.CommunicationMessage, UUID(message["id"]))
        persisted.state = state
        part = db.scalar(
            select(models.CommunicationAttachment).where(
                models.CommunicationAttachment.message_id == persisted.id
            )
        )
        original_pdf = part.content
        db.commit()
    message_path = f"/communications/messages/{message['id']}"
    before = api.client.get(message_path).json()
    response = api.client.request(
        "DELETE", f"/communications/templates/{value['id']}", json={"confirmed": True}
    )
    assert response.status_code == 200
    assert api.client.get(message_path).json() == before
    preview = api.client.get(f"{message_path}/attachments/{part.id}/preview")
    assert preview.status_code == 200
    assert preview.content == original_pdf
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": "pec",
            "recipient": "synthetic@example.org",
            "template_id": value["id"],
        },
    )
    assert response.status_code == 409
    with api.session() as db:
        messages = list(db.scalars(select(models.CommunicationMessage)))
        assert [str(row.id) for row in messages] == [message["id"]]
        assert messages[0].template_id == UUID(value["id"])


@pytest.mark.parametrize(
    "payload",
    [{}, {"confirmed": False}, {"confirmed": "true"}, {"confirmed": True, "status": "deleted"}],
)
def test_delete_requires_explicit_confirmation_without_extra_fields(api, payload):
    value = template(api)
    path = f"/communications/templates/{value['id']}"
    assert api.client.request("DELETE", path).status_code == 422
    assert api.client.request("DELETE", path, json=payload).status_code == 422
    assert api.client.get("/communications/admin/templates").json() == [value]


@pytest.mark.parametrize("user,status", [(2, 403), (4, 401)])
def test_delete_requires_admin_and_never_changes_state_for_other_users(api, user, status):
    value = template(api)
    response = api.client.request(
        "DELETE",
        f"/communications/templates/{value['id']}",
        json={"confirmed": True},
        headers=_headers(user),
    )
    assert response.status_code == status
    assert api.client.get("/communications/admin/templates").json() == [value]


@pytest.mark.parametrize("user", [1, 3, 5])
def test_delete_preserves_existing_admin_access_independent_of_ruolo_sections(api, user):
    value = template(api)
    response = api.client.request(
        "DELETE",
        f"/communications/templates/{value['id']}",
        json={"confirmed": True},
        headers=_headers(user),
    )
    assert response.status_code == 200
    assert api.client.get("/communications/admin/templates").json() == []


def test_delete_missing_identity_invalid_uuid_and_unauthenticated(api):
    assert (
        api.client.request(
            "DELETE", f"/communications/templates/{uuid4()}", json={"confirmed": True}
        ).status_code
        == 404
    )
    assert (
        api.client.request(
            "DELETE", "/communications/templates/invalid", json={"confirmed": True}
        ).status_code
        == 422
    )
    api.client.headers.pop("Authorization")
    assert (
        api.client.request(
            "DELETE", f"/communications/templates/{uuid4()}", json={"confirmed": True}
        ).status_code
        == 401
    )


def test_delete_rolls_back_status_if_audit_cannot_be_saved(api, monkeypatch):
    value = template(api, approve=True)

    def fail_audit(*args, **kwargs):
        raise policy.Conflict("Audit indisponibile")

    monkeypatch.setattr(registry, "event", fail_audit)
    response = api.client.request(
        "DELETE", f"/communications/templates/{value['id']}", json={"confirmed": True}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Audit indisponibile"
    assert api.client.get("/communications/admin/templates").json() == [value]
    assert api.client.get("/communications/templates").json() == [value]
