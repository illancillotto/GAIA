from __future__ import annotations

import pytest

from app.modules.me import router


def test_router_facade_forwards_and_restores_legacy_attributes() -> None:
    original = router._resolve_device_label
    replacement = object()

    router._resolve_device_label = replacement
    assert router._resolve_device_label is replacement

    del router._resolve_device_label
    assert router._resolve_device_label is original


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
