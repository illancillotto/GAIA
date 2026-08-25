from types import SimpleNamespace
from uuid import uuid4

from app.modules.presenze.services.visibility_policy import (
    PresenzeVisibilityPolicy,
    _legacy_hierarchy_user_ids,
    can_approve_daily_record,
    can_read_collaborator,
    can_read_daily_record,
)


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_conditions):
        return self

    def all(self):
        return self.rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_entities):
        return _FakeQuery(self.rows)


def test_legacy_hierarchy_stops_on_cycles() -> None:
    rows = [
        SimpleNamespace(manager_user_id=1, application_user_id=2),
        SimpleNamespace(manager_user_id=2, application_user_id=1),
    ]
    assert _legacy_hierarchy_user_ids(_FakeSession(rows), 1) == {2}


def test_full_policy_can_read_collaborator() -> None:
    policy = PresenzeVisibilityPolicy(viewer_user_id=1, full_access=True)
    collaborator = SimpleNamespace(owner_user_id=None, application_user_id=None, id=uuid4())
    assert can_read_collaborator(policy, collaborator) is True


def test_scoped_policy_checks_user_and_legacy_collaborator_targets() -> None:
    collaborator_id = uuid4()
    policy = PresenzeVisibilityPolicy(
        viewer_user_id=1,
        full_access=False,
        readable_user_ids=frozenset({2}),
        approvable_user_ids=frozenset({3}),
        legacy_collaborator_ids=frozenset({collaborator_id}),
    )
    readable = SimpleNamespace(owner_user_id=None, application_user_id=2, collaborator_id=uuid4())
    approvable = SimpleNamespace(owner_user_id=None, application_user_id=3, collaborator_id=uuid4())
    legacy = SimpleNamespace(owner_user_id=None, application_user_id=None, collaborator_id=collaborator_id)
    denied = SimpleNamespace(owner_user_id=None, application_user_id=4, collaborator_id=uuid4())

    assert can_read_daily_record(policy, readable) is True
    assert can_approve_daily_record(policy, approvable) is True
    assert can_read_daily_record(policy, legacy) is True
    assert can_approve_daily_record(policy, legacy) is True
    assert can_read_daily_record(policy, denied) is False
    assert can_approve_daily_record(policy, denied) is False
