"""Legacy tracking preserves canonical metadata and persistence boundaries."""

from itertools import product
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking


class RecordingSession:
    def __init__(self, canonical, *, fail=None):
        self.canonical = canonical
        self.fail = fail
        self.events = []
        self.query = None

    def scalar(self, query):
        self.query = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.events.append(("scalar",))
        if self.fail == "scalar":
            raise RuntimeError("scalar unavailable")
        return self.canonical

    def add(self, value):
        self.events.append(("add", value))
        if self.fail == "add":
            raise RuntimeError("add unavailable")

    def delete(self, value):
        self.events.append(("delete", value))
        if self.fail == "delete":
            raise RuntimeError("delete unavailable")


def setup_reconciliation(monkeypatch, canonical, *, fail=None):
    subject = SimpleNamespace(
        id=3,
        entity_type="ip",
        device_id=None,
        normalized_value="10.0.0.7",
        value="10.0.0.7",
        label="Legacy",
        notes="Legacy notes",
        is_active=True,
    )
    device = SimpleNamespace(id=7, ip_address="10.0.0.8")
    db = RecordingSession(canonical, fail=fail)
    lookups = []

    def find_device(session, candidate):
        assert session is db
        assert candidate is subject
        lookups.append(candidate)
        return device

    monkeypatch.setattr(tracking, "_find_matching_device_for_legacy_ip_subject", find_device)
    return subject, device, db, lookups


@pytest.mark.parametrize(
    "has_label,has_notes,legacy_present,canonical_active,legacy_active",
    list(product((False, True), repeat=5)),
)
def test_canonical_metadata_wins_and_legacy_is_deleted_after_add(
    monkeypatch, has_label, has_notes, legacy_present, canonical_active, legacy_active
):
    canonical = SimpleNamespace(
        id=9,
        entity_type="device",
        normalized_value="7",
        label="Canonical" if has_label else "",
        notes="Canonical notes" if has_notes else None,
        is_active=canonical_active,
        device_id=99,
        value="old",
    )
    subject, device, db, lookups = setup_reconciliation(monkeypatch, canonical)
    subject.label = "Legacy" if legacy_present else None
    subject.notes = "Legacy notes" if legacy_present else ""
    subject.is_active = legacy_active
    original_subject = vars(subject).copy()

    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, subject)

    assert result is canonical
    assert changed is True
    assert vars(canonical) == {
        "id": 9,
        "entity_type": "device",
        "normalized_value": "7",
        "label": "Canonical" if has_label else "Legacy" if legacy_present else "",
        "notes": "Canonical notes" if has_notes else "Legacy notes" if legacy_present else None,
        "is_active": canonical_active or legacy_active,
        "device_id": device.id,
        "value": device.ip_address,
    }
    assert vars(subject) == original_subject
    assert lookups == [subject]
    assert db.events == [("scalar",), ("add", canonical), ("delete", subject)]
    assert "network_tracked_subjects.entity_type = 'device'" in db.query
    assert "network_tracked_subjects.normalized_value = '7'" in db.query
    assert "network_tracked_subjects.id != 3" in db.query


def test_missing_canonical_converts_same_subject_without_delete(monkeypatch):
    subject, device, db, _ = setup_reconciliation(monkeypatch, None)
    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, subject)
    assert result is subject
    assert changed is True
    assert (subject.entity_type, subject.device_id, subject.normalized_value, subject.value) == (
        "device",
        device.id,
        str(device.id),
        device.ip_address,
    )
    assert (subject.label, subject.notes, subject.is_active) == ("Legacy", "Legacy notes", True)
    assert db.events == [("scalar",), ("add", subject)]


def test_missing_device_does_not_query_or_mutate_subject(monkeypatch):
    subject, _, db, _ = setup_reconciliation(monkeypatch, None)
    original = vars(subject).copy()
    monkeypatch.setattr(tracking, "_find_matching_device_for_legacy_ip_subject", lambda *_: None)
    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, subject)
    assert result is subject
    assert changed is False
    assert vars(subject) == original
    assert db.events == []


@pytest.mark.parametrize(
    "fail,operations",
    [("scalar", ["scalar"]), ("add", ["scalar", "add"]), ("delete", ["scalar", "add", "delete"])],
)
def test_persistence_errors_propagate_without_later_operations(monkeypatch, fail, operations):
    canonical = SimpleNamespace(label="", notes="", is_active=False)
    subject, _, db, _ = setup_reconciliation(monkeypatch, canonical, fail=fail)
    with pytest.raises(RuntimeError, match=f"{fail} unavailable"):
        tracking._reconcile_legacy_ip_tracked_subject(db, subject)
    assert [event[0] for event in db.events] == operations


def test_legacy_values_are_read_again_for_assignment_and_active_is_lazy(monkeypatch):
    class Legacy:
        id = 3
        label_reads = 0
        notes_reads = 0

        @property
        def label(self):
            self.label_reads += 1
            return "first label" if self.label_reads == 1 else "second label"

        @property
        def notes(self):
            self.notes_reads += 1
            return "first notes" if self.notes_reads == 1 else "second notes"

        @property
        def is_active(self):
            raise AssertionError("canonical active must short circuit")

    subject = Legacy()
    canonical = SimpleNamespace(label=None, notes=None, is_active="active")
    db = RecordingSession(canonical)
    monkeypatch.setattr(
        tracking,
        "_find_matching_device_for_legacy_ip_subject",
        lambda *_: SimpleNamespace(id=7, ip_address="10.0.0.7"),
    )
    result, changed = tracking._reconcile_legacy_ip_tracked_subject(db, subject)
    assert result is canonical and changed is True
    assert (canonical.label, canonical.notes, canonical.is_active) == (
        "second label",
        "second notes",
        "active",
    )
    assert (subject.label_reads, subject.notes_reads) == (2, 2)
    assert db.events == [("scalar",), ("add", canonical), ("delete", subject)]
