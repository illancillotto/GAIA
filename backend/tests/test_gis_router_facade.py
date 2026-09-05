from __future__ import annotations

import pytest

from app.modules.gis import router


def test_router_facade_forwards_and_restores_legacy_attributes() -> None:
    original = router.interrogazione_service
    replacement = object()

    router.interrogazione_service = replacement
    assert router.interrogazione_service is replacement

    del router.interrogazione_service
    assert router.interrogazione_service is original


def test_router_facade_handles_local_and_reserved_attributes() -> None:
    assembled_router = router.router
    router.router = assembled_router
    assert router.router is assembled_router

    router.facade_test_value = "local"
    assert router.facade_test_value == "local"
    del router.facade_test_value
    router.__delattr__("absent_facade_value")

    with pytest.raises(AttributeError):
        _ = router.unknown_legacy_attribute
