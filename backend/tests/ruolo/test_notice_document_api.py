from uuid import uuid4

import pytest

from app.modules.ruolo.routes import notice_document_routes as routes

from .test_notice_register_api import _headers
from .test_notice_register_api import api as api
from .test_notice_register_api import api_engine as api_engine


def endpoint(kind):
    prefix = f"/ruolo/tributi/solleciti/batches/{uuid4()}"
    return prefix + (f"/items/{uuid4()}/preview" if kind == "preview" else "/export")


@pytest.mark.parametrize(
    "kind,user",
    [
        ("preview", 3),
        ("preview", 4),
        ("preview", 5),
        ("export", 2),
        ("export", 3),
        ("export", 4),
        ("export", 5),
    ],
)
def test_permissions_enforced_before_document_access(api, monkeypatch, kind, user):
    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized artifact access")

    monkeypatch.setattr(routes, "preview_item", forbidden)
    monkeypatch.setattr(routes, "export_batch", forbidden)
    response = api.client.request(
        "GET" if kind == "preview" else "POST", endpoint(kind), headers=_headers(user)
    )
    assert response.status_code == (401 if user == 4 else 403)


@pytest.mark.parametrize("kind,user", [("preview", 1), ("preview", 2), ("export", 1)])
def test_download_is_authenticated_private_and_correctly_typed(api, monkeypatch, kind, user):
    def document(engine, batch_id, item_or_actor):
        if kind == "export":
            assert item_or_actor == 1
        return b"marked-pdf" if kind == "preview" else b"final-zip"

    monkeypatch.setattr(routes, "preview_item" if kind == "preview" else "export_batch", document)
    response = api.client.request(
        "GET" if kind == "preview" else "POST", endpoint(kind), headers=_headers(user)
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["content-type"] == (
        "application/pdf" if kind == "preview" else "application/zip"
    )
    assert response.content == (b"marked-pdf" if kind == "preview" else b"final-zip")


@pytest.mark.parametrize(
    "kind,exception,status",
    [
        ("preview", LookupError, 404),
        ("preview", routes.DraftReviewBlocked, 409),
        ("preview", routes.PreviewUnavailable, 503),
        ("export", routes.DraftReviewBlocked, 409),
        ("export", routes.GenerationRevisionChanged, 409),
        ("export", routes.RevisionProtocolUnavailable, 503),
    ],
)
def test_document_errors_have_no_download_body(api, monkeypatch, kind, exception, status):
    def blocked(*args):
        raise exception("Documento non disponibile")

    monkeypatch.setattr(routes, "preview_item" if kind == "preview" else "export_batch", blocked)
    response = api.client.request("GET" if kind == "preview" else "POST", endpoint(kind))
    assert response.status_code == status
    assert "content-disposition" not in response.headers


def test_export_get_cannot_create_a_claim(api):
    assert api.client.get(endpoint("export")).status_code == 405
