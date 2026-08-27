from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.application_user import ApplicationUser
from app.services import elaborazioni_batch_credentials as credential_service
from app.services.elaborazioni_credentials import ElaborazioneCredentialNotFoundError


class FakeDb:
    def __init__(self, *, owner=None, credentials=()) -> None:
        self.owner = owner
        self.credentials = list(credentials)
        self.statement = None

    def get(self, model, _identity):
        return self.owner if model is ApplicationUser else None

    def scalars(self, statement):
        self.statement = statement
        return self.credentials


def batch(*, credential_id=None, credential_ids=None):
    return SimpleNamespace(credential_id=credential_id, credential_ids=credential_ids)


def test_require_batch_credentials_supports_pinned_and_automatic_pools(monkeypatch: pytest.MonkeyPatch) -> None:
    selected_id = uuid4()
    selected = SimpleNamespace(id=selected_id, active=True)
    get_pinned = monkeypatch.setattr
    get_pinned(credential_service, "get_credential_for_user", lambda *_args: selected)
    credential_service.require_batch_credentials(FakeDb(), batch(credential_id=selected_id), 1)

    monkeypatch.setattr(credential_service, "get_credential_for_user", lambda *_args: None)
    with pytest.raises(ElaborazioneCredentialNotFoundError, match="not active"):
        credential_service.require_batch_credentials(FakeDb(), batch(credential_id=selected_id), 1)

    required = []
    monkeypatch.setattr(credential_service, "require_credentials_for_user", lambda *_args: required.append(True))
    credential_service.require_batch_credentials(FakeDb(), batch(), 1)
    assert required == [True]


@pytest.mark.parametrize("values", [["not-a-uuid"], []])
def test_require_batch_credentials_rejects_invalid_allowlists(values: list[str]) -> None:
    with pytest.raises(ElaborazioneCredentialNotFoundError):
        credential_service.require_batch_credentials(FakeDb(), batch(credential_ids=values), 1)


def test_require_batch_credentials_scopes_non_admin_allowlists() -> None:
    selected_id = uuid4()
    selected = SimpleNamespace(id=selected_id)
    db = FakeDb(owner=SimpleNamespace(is_super_admin=False), credentials=[selected])

    credential_service.require_batch_credentials(
        db,
        batch(credential_ids=[str(selected_id)]),
        1,
    )

    assert "catasto_credentials.user_id" in str(db.statement)

    missing = FakeDb(owner=SimpleNamespace(is_super_admin=True), credentials=[])
    with pytest.raises(ElaborazioneCredentialNotFoundError, match="missing or inactive"):
        credential_service.require_batch_credentials(
            missing,
            batch(credential_ids=[str(selected_id)]),
            1,
        )
