"""Device patches validate assignees before lifecycle changes and persistence."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.application_user import ApplicationUser
from app.modules.network.models import NetworkDevice
from app.modules.network.router.routes import devices as routes
from app.modules.network.schemas import NetworkDeviceUpdateRequest


@pytest.fixture
def patch_request(monkeypatch):
    def prepare(*, changes=None, user_exists=True, device_exists=True, retired_at=None, fail=None):
        trace = []

        def record(name, *args):
            trace.append((name, *args))
            if name == fail:
                raise RuntimeError(f"failed {name}")

        class Device(SimpleNamespace):
            def __setattr__(self, name, value):
                record("write", name, value)
                super().__setattr__(name, value)

        row = Device(
            assigned_user_id=17,
            lifecycle_state="active",
            retired_at=retired_at,
            is_monitored=True,
            notes="original",
        )
        payload = NetworkDeviceUpdateRequest(**(changes or {}))

        def model_dump(**kwargs):
            record("dump", kwargs)
            return payload.model_dump(**kwargs)

        request = SimpleNamespace(model_dump=model_dump)

        def get(model, key):
            if model is NetworkDevice:
                record("device_get", key)
                return row if device_exists else None
            assert model is ApplicationUser
            record("user_get", key)
            return SimpleNamespace(id=key) if user_exists else None

        db = SimpleNamespace(
            get=get,
            add=lambda device: record("add", device is row),
            commit=lambda: record("commit"),
            refresh=lambda device: record("refresh", device is row),
        )
        response = object()

        def serialize(device, **kwargs):
            record("serialize", device is row, kwargs)
            return response

        monkeypatch.setattr(routes, "_require_network_module", lambda _user: record("auth"))
        monkeypatch.setattr(
            routes,
            "sync_network_device_alert_state",
            lambda session, device: record("sync", session is db, dict(vars(device))),
        )
        monkeypatch.setattr(
            routes, "get_device_positions", lambda _db, key: record("positions", key)
        )
        monkeypatch.setattr(
            routes, "get_device_scan_history", lambda _db, key: record("history", key)
        )
        monkeypatch.setattr(
            routes, "_build_device_traffic_summary", lambda _db, _row: record("traffic")
        )
        monkeypatch.setattr(routes, "_serialize_device", serialize)
        return SimpleNamespace(
            call=lambda: routes.patch_device(3, request, SimpleNamespace(), db),
            row=row,
            request=request,
            trace=trace,
            response=response,
        )

    return prepare


@pytest.mark.parametrize(
    "changes,expected,queries",
    [
        ({}, 17, []),
        ({"assigned_user_id": None}, None, []),
        ({"assigned_user_id": 0}, 0, [0]),
        ({"assigned_user_id": 23}, 23, [23]),
    ],
)
def test_omitted_null_zero_and_existing_assignees(patch_request, changes, expected, queries):
    case = patch_request(changes=changes)
    assert case.call() is case.response
    assert case.row.assigned_user_id == expected
    assert [entry[1] for entry in case.trace if entry[0] == "user_get"] == queries
    assert case.trace[:3] == [("auth",), ("device_get", 3), ("dump", {"exclude_unset": True})]
    if not changes:
        assert not any(entry[0] == "write" for entry in case.trace)


@pytest.mark.parametrize("lifecycle", [None, "active", "retired"])
def test_missing_assignee_raises_before_lifecycle_writes_or_side_effects(patch_request, lifecycle):
    changes = {"assigned_user_id": 404, "notes": "new"}
    if lifecycle is not None:
        changes["lifecycle_state"] = lifecycle
    case = patch_request(changes=changes, user_exists=False)
    before = dict(vars(case.row))
    with pytest.raises(HTTPException) as caught:
        case.call()
    assert (caught.value.status_code, caught.value.detail) == (404, "Assigned user not found")
    assert dict(vars(case.row)) == before
    assert [entry[0] for entry in case.trace] == ["auth", "device_get", "dump", "user_get"]


def test_missing_device_precedes_payload_dump_and_user_lookup(patch_request):
    case = patch_request(changes={"assigned_user_id": 404}, device_exists=False)
    with pytest.raises(HTTPException) as caught:
        case.call()
    assert (caught.value.status_code, caught.value.detail) == (404, "Device not found")
    assert case.trace == [("auth",), ("device_get", 3)]


@pytest.mark.parametrize("existing", [None, datetime(2026, 1, 1, tzinfo=UTC)])
def test_retirement_validates_then_clears_assignee_and_preserves_retirement_time(
    patch_request, existing
):
    case = patch_request(
        changes={"assigned_user_id": 23, "lifecycle_state": "retired"}, retired_at=existing
    )
    start = datetime.now(UTC)
    case.call()
    end = datetime.now(UTC)
    assert case.row.assigned_user_id is None
    assert case.row.is_monitored is False
    assert case.row.lifecycle_state == "retired"
    if existing is None:
        assert start <= case.row.retired_at <= end
    else:
        assert case.row.retired_at is existing
    assert [entry[0] for entry in case.trace[:4]] == ["auth", "device_get", "dump", "user_get"]
    assert [entry[1] for entry in case.trace if entry[0] == "write"] == [
        "lifecycle_state",
        "assigned_user_id",
        "is_monitored",
        "retired_at",
    ]
    synced = next(entry[2] for entry in case.trace if entry[0] == "sync")
    assert synced == vars(case.row)


def test_activation_clears_retirement_time_without_changing_monitoring(patch_request):
    case = patch_request(changes={"lifecycle_state": "active"}, retired_at=datetime.now(UTC))
    case.row.is_monitored = False
    case.trace.clear()
    case.call()
    assert case.row.retired_at is None
    assert case.row.is_monitored is False
    assert case.row.assigned_user_id == 17


def test_validation_precedes_writes_then_one_commit_refresh_and_response_reads(patch_request):
    case = patch_request(changes={"assigned_user_id": 23})
    case.call()
    assert [entry[0] for entry in case.trace] == [
        "auth",
        "device_get",
        "dump",
        "user_get",
        "write",
        "sync",
        "add",
        "commit",
        "refresh",
        "positions",
        "history",
        "traffic",
        "serialize",
    ]
    assert case.trace[-1] == (
        "serialize",
        True,
        {"positions": None, "scan_history": None, "traffic_summary": None},
    )


@pytest.mark.parametrize(
    "fail",
    [
        "auth",
        "device_get",
        "dump",
        "user_get",
        "write",
        "sync",
        "add",
        "commit",
        "refresh",
        "positions",
        "history",
        "traffic",
        "serialize",
    ],
)
def test_failures_stop_without_retry_rollback_or_later_effects(patch_request, fail):
    case = patch_request(changes={"assigned_user_id": 23}, fail=fail)
    with pytest.raises(RuntimeError, match=f"failed {fail}"):
        case.call()
    order = [
        "auth",
        "device_get",
        "dump",
        "user_get",
        "write",
        "sync",
        "add",
        "commit",
        "refresh",
        "positions",
        "history",
        "traffic",
        "serialize",
    ]
    assert [entry[0] for entry in case.trace] == order[: order.index(fail) + 1]


def test_validation_preserves_repeated_mapping_reads(patch_request):
    case = patch_request(changes={"assigned_user_id": 23})
    reads = []

    class Updates(dict):
        def __contains__(self, key):
            reads.append(("contains", key))
            return super().__contains__(key)

        def __getitem__(self, key):
            reads.append(("getitem", key))
            return super().__getitem__(key)

    case.request.model_dump = lambda **_kwargs: Updates(assigned_user_id=23)
    case.call()
    assert reads == [
        ("contains", "assigned_user_id"),
        ("getitem", "assigned_user_id"),
        ("getitem", "assigned_user_id"),
    ]
