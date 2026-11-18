"""Tracking creation preserves reactivation, legacy transactions and error order."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.modules.network.router.routes import tracking as routes


@pytest.fixture
def creation_case(monkeypatch):
    def prepare(mode, *, label=None, notes=None, fail=None, refreshed_ip=None):
        trace = []
        counts = {}
        queries = []
        added = []
        user = SimpleNamespace(id=41)
        device = SimpleNamespace(id=7, ip_address="192.0.2.7")
        payload = SimpleNamespace(
            entity_type="device" if mode.startswith("device") else "domain",
            device_id=7,
            value="  Example.TEST  ",
            label=label,
            notes=notes,
        )
        old = SimpleNamespace(
            id=8,
            label="old label",
            notes="old notes",
            is_active=False,
            device_id=None,
            value="old value",
            created_by_user_id=31,
        )
        reconciled = SimpleNamespace(**vars(old), entity_type="device")

        def record(name, *args):
            counts[name] = counts.get(name, 0) + 1
            point = f"{name}{counts[name]}"
            trace.append((point, *args))
            if fail == point:
                raise RuntimeError(point)

        def authorize(current):
            assert current is user
            record("auth")

        def get(model, device_id):
            assert model is routes.NetworkDevice
            record("get", device_id)
            return None if mode == "device_missing" else device

        def scalar(query):
            compiled = query.compile(dialect=postgresql.dialect())
            queries.append((str(compiled), compiled.params))
            record("query")
            if mode == "device_legacy" or (
                mode.endswith("existing") and (len(queries) == 2 or mode == "domain_existing")
            ):
                return old
            return None

        def reconcile(session, subject):
            assert session is db and subject is old
            record("reconcile")
            return reconciled, True

        def add(subject):
            record("add")
            added.append(subject)

        def commit():
            record("commit")

        def refresh(subject):
            record("refresh")
            if refreshed_ip is not None:
                device.ip_address = refreshed_ip

        def normalize(entity_type, value):
            record("normalize", entity_type, value)
            return value.lower()

        def serialize(session, subject, **kwargs):
            assert session is db
            record("serialize", kwargs)
            return subject

        db = SimpleNamespace(get=get, scalar=scalar, add=add, commit=commit, refresh=refresh)
        monkeypatch.setattr(routes, "_require_network_module", authorize)
        monkeypatch.setattr(routes, "_normalize_tracked_value", normalize)
        monkeypatch.setattr(routes, "_reconcile_legacy_ip_tracked_subject", reconcile)
        monkeypatch.setattr(routes, "_serialize_tracked_subject", serialize)
        return SimpleNamespace(
            call=lambda: routes.create_tracked_subject(payload, user, db),
            trace=trace,
            queries=queries,
            added=added,
            old=old,
            reconciled=reconciled,
            device=device,
            payload=payload,
        )

    return prepare


@pytest.mark.parametrize("mode", ["device_legacy", "device_existing", "domain_existing"])
@pytest.mark.parametrize("label,notes", [(None, None), ("", ""), ("new label", "new notes")])
def test_reactivation_preserves_omitted_fields_and_clears_empty_fields(
    creation_case, mode, label, notes
):
    case = creation_case(mode, label=label, notes=notes)
    result = case.call()
    assert result is (case.reconciled if mode == "device_legacy" else case.old)
    assert result.label == ("old label" if label is None else label or None)
    assert result.notes == ("old notes" if notes is None else notes or None)
    assert result.is_active is True
    assert result.created_by_user_id == 31
    assert case.added == [result]
    if mode == "device_existing":
        assert (result.device_id, result.value) == (7, "192.0.2.7")
    elif mode == "domain_existing":
        assert (result.device_id, result.value) == (None, "old value")
    names = [event[0] for event in case.trace]
    expected = (
        ["auth1", "get1", "query1", "reconcile1", "commit1", "refresh1"]
        if mode == "device_legacy"
        else (
            ["auth1", "get1", "query1", "query2"]
            if mode == "device_existing"
            else ["auth1", "normalize1", "query1"]
        )
    )
    expected += (
        ["add1", "commit2", "refresh2", "serialize1"]
        if mode == "device_legacy"
        else ["add1", "commit1", "refresh1", "serialize1"]
    )
    assert names == expected
    assert case.trace[-1] == ("serialize1", {"include_activity_summary": False})
    if mode.startswith("device"):
        sql, params = case.queries[0]
        assert "network_tracked_subjects.device_id IS NULL" in sql
        assert params == {"entity_type_1": "ip", "value_1": "192.0.2.7"}
    if mode != "device_legacy":
        assert case.queries[-1][1] == {
            "entity_type_1": "device" if mode.startswith("device") else "domain",
            "normalized_value_1": "7" if mode.startswith("device") else "example.test",
        }


@pytest.mark.parametrize("mode", ["device_new", "domain_new"])
@pytest.mark.parametrize("label,notes", [(None, None), ("", ""), ("new", "note")])
def test_new_subject_keeps_normalized_identity_and_author(creation_case, mode, label, notes):
    case = creation_case(mode, label=label, notes=notes)
    subject = case.call()
    assert case.added == [subject]
    assert subject.entity_type == case.payload.entity_type
    assert subject.normalized_value == ("7" if mode == "device_new" else "example.test")
    assert subject.value == ("192.0.2.7" if mode == "device_new" else "Example.TEST")
    assert subject.device_id == (7 if mode == "device_new" else None)
    assert subject.created_by_user_id == 41
    assert (subject.label, subject.notes, subject.is_active) == (label or None, notes or None, True)
    assert [e[0] for e in case.trace][-4:] == ["add1", "commit1", "refresh1", "serialize1"]


def test_reconciled_subject_is_not_rebound_to_device_after_refresh(creation_case):
    case = creation_case("device_legacy", refreshed_ip="192.0.2.99")
    subject = case.call()
    assert case.device.ip_address == "192.0.2.99"
    assert (subject.device_id, subject.value) == (None, "old value")
    assert len(case.queries) == 1


@pytest.mark.parametrize("mode", ["device_missing", "domain_new"])
def test_target_errors_precede_queries_and_writes(creation_case, mode):
    case = creation_case(mode)
    if mode == "domain_new":
        case.payload.value = None
    with pytest.raises(HTTPException) as exc:
        case.call()
    assert exc.value.status_code == (404 if mode == "device_missing" else 422)
    assert exc.value.detail == (
        "Device not found" if mode == "device_missing" else "Missing tracking value"
    )
    assert not case.queries and not case.added


@pytest.mark.parametrize(
    "mode,point",
    [
        ("device_legacy", "auth1"),
        ("device_legacy", "get1"),
        ("device_legacy", "query1"),
        ("device_legacy", "reconcile1"),
        ("device_legacy", "commit1"),
        ("device_legacy", "refresh1"),
        ("device_legacy", "add1"),
        ("device_legacy", "commit2"),
        ("device_legacy", "refresh2"),
        ("device_legacy", "serialize1"),
        ("device_existing", "query2"),
        ("domain_existing", "normalize1"),
        ("domain_existing", "commit1"),
        ("device_new", "commit1"),
    ],
)
def test_failure_stops_at_the_original_transaction_boundary(creation_case, mode, point):
    case = creation_case(mode, label="new label", notes="new notes", fail=point)
    with pytest.raises(RuntimeError, match=point):
        case.call()
    assert case.trace[-1][0] == point
    if mode == "device_legacy" and point in {"commit1", "refresh1"}:
        assert case.reconciled.is_active is False
        assert (case.reconciled.label, case.reconciled.notes) == ("old label", "old notes")
    if point == "add1":
        assert case.reconciled.is_active is True
        assert (case.reconciled.label, case.reconciled.notes) == ("new label", "new notes")
