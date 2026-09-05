from __future__ import annotations

import pytest

from app.modules.catasto.routes import anagrafica
from app.modules.catasto.routes.anagrafica import resolvers


def test_facade_forwards_and_restores_legacy_monkeypatches(monkeypatch: pytest.MonkeyPatch) -> None:
    original = resolvers.pick_credential
    replacement = object()

    monkeypatch.setattr(anagrafica, "pick_credential", replacement)

    assert resolvers.pick_credential is replacement
    monkeypatch.undo()
    assert resolvers.pick_credential is original


def test_facade_rejects_unknown_legacy_attributes() -> None:
    name = "not_a_legacy_attribute"
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(anagrafica, name)
