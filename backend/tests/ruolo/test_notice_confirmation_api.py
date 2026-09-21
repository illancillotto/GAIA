from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.ruolo.routes import notice_confirmation_routes as routes

from .test_notice_register_api import _headers
from .test_notice_register_api import api as api
from .test_notice_register_api import api_engine as api_engine


def endpoint():
    return f"/ruolo/tributi/solleciti/batches/{uuid4()}/confirm"


@pytest.mark.parametrize("user", [2, 3, 4, 5])
def test_confirmation_permission_denied(api, user, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized request reached confirmation")

    monkeypatch.setattr(routes, "confirm_generation", forbidden)
    expected = 401 if user == 4 else 403
    assert (
        api.client.post(endpoint(), headers=_headers(user), json={"batch": True}).status_code
        == expected
    )


def test_single_confirmation_request_rejected(api):
    assert api.client.post(endpoint(), json={"batch": False}).status_code == 422


@pytest.mark.parametrize(
    "exception,expected",
    [
        (routes.DraftReviewBlocked, 409),
        (routes.GenerationRevisionChanged, 409),
        (routes.RevisionProtocolUnavailable, 503),
    ],
)
def test_confirmation_error_contract(api, monkeypatch, exception, expected):
    def blocked(*args, **kwargs):
        raise exception("Conferma bloccata")

    monkeypatch.setattr(routes, "confirm_generation", blocked)
    assert api.client.post(endpoint(), json={"batch": True}).status_code == expected


def test_confirmation_response_and_actor(api, monkeypatch):
    from sqlalchemy.orm import Session

    result = SimpleNamespace(
        id=uuid4(),
        generation_id=uuid4(),
        generation_kind="batch",
        review_digest="a" * 64,
        input_basis={},
        identity_keys=["b" * 64],
        notice_numbers=["12026222300001"],
        confirmed_by=1,
        confirmed_at=datetime.now(UTC),
    )

    def confirm(db, identifier, *, batch, actor_id):
        assert actor_id == 1 and batch
        return result

    monkeypatch.setattr(routes, "confirm_generation", confirm)
    monkeypatch.setattr(Session, "refresh", lambda *args: None)
    response = api.client.post(endpoint(), json={"batch": True})
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(result.id)
