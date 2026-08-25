from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.organigramma import repositories
from app.modules.organigramma.models import OrgAssignment, OrgUnit
from app.modules.organigramma.routes.io import _raise_if_duplicates, _validate_snapshot
from app.modules.organigramma.schemas import OrganigrammaSnapshot
from app.modules.organigramma.services import (
    drafts_service,
    organigramma_service,
    whitecompany_sync,
)
from app.modules.organigramma.services.visibility_service import (
    VIA_HIERARCHY,
    _descendants,
)


def _unit_snapshot(unit_id, *, parent_id=None):
    return {
        "id": unit_id,
        "nome": "Unita test",
        "tipo": "settore",
        "parent_id": parent_id,
        "source": "manuale",
    }


def test_repository_assignment_presence_and_delete(session, make_user):
    user = make_user("repo-coverage")
    unit = OrgUnit(nome="Repository", tipo="settore")
    removable = OrgUnit(nome="Removable", tipo="settore")
    session.add_all([unit, removable])
    session.flush()
    session.add(OrgAssignment(user_id=user.id, org_unit_id=unit.id))
    session.commit()

    assert repositories.unit_has_assignments(session, unit.id) is True
    repositories.delete_unit(session, removable)
    assert session.get(OrgUnit, removable.id) is None


def test_snapshot_validation_rejects_parent_duplicates_users_and_units(session, make_user):
    known = make_user("snapshot-known")
    unit_id = uuid4()
    unknown_unit_id = uuid4()

    with pytest.raises(HTTPException, match="unknown parent"):
        _validate_snapshot(
            OrganigrammaSnapshot(units=[_unit_snapshot(unit_id, parent_id=uuid4())]),
            session,
        )

    with pytest.raises(HTTPException, match="duplicate unit"):
        _raise_if_duplicates("unit", [unit_id, unit_id])

    missing_users = OrganigrammaSnapshot.model_validate(
        {
            "units": [_unit_snapshot(unit_id)],
            "assignments": [
                {
                    "id": uuid4(),
                    "user_id": known.id,
                    "manager_user_id": 900001,
                    "org_unit_id": unit_id,
                }
            ],
            "overrides": [
                {
                    "id": uuid4(),
                    "viewer_user_id": known.id,
                    "target_type": "user",
                    "target_user_id": 900002,
                    "scope": "read",
                }
            ],
        }
    )
    with pytest.raises(HTTPException, match="unknown users"):
        _validate_snapshot(missing_users, session)

    unknown_unit = OrganigrammaSnapshot.model_validate(
        {
            "units": [_unit_snapshot(unit_id)],
            "assignments": [
                {
                    "id": uuid4(),
                    "user_id": known.id,
                    "org_unit_id": unknown_unit_id,
                }
            ],
        }
    )
    with pytest.raises(HTTPException, match="unknown org units"):
        _validate_snapshot(unknown_unit, session)


def test_draft_service_fallbacks(monkeypatch):
    assert drafts_service._person_ref(None) is None

    response = SimpleNamespace(person=None, manager=None)
    assignment = SimpleNamespace(
        logical_org_assignment_id=uuid4(),
        user_id=10,
        manager_user_id=20,
        org_unit_id=uuid4(),
        title=None,
        position_code=None,
        is_primary=True,
        active=True,
        valid_from=None,
        valid_to=None,
        source="manuale",
        wc_operator_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(drafts_service.OrgAssignmentResponse, "model_validate", lambda value: response)
    monkeypatch.setattr(drafts_service, "_person_ref", lambda value: value)
    assert drafts_service._revision_assignment_response(assignment, {10: "person", 20: "manager"}).manager == "manager"

    draft = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(drafts_service.repo, "get_active_draft_for_user", lambda db, user_id: draft)
    monkeypatch.setattr(drafts_service, "build_draft_detail", lambda db, value: "detail")
    assert drafts_service.get_active_draft_response(object(), user_id=1) == "detail"

    with pytest.raises(ValueError, match="bozza attiva"):
        drafts_service.create_draft_from_current(object(), SimpleNamespace(name="x"), user_id=1)

    monkeypatch.setattr(drafts_service.repo, "get_revision", lambda db, revision_id: None)
    with pytest.raises(ValueError, match="Revisione di lavoro"):
        drafts_service.publish_draft(object(), SimpleNamespace(working_revision_id=uuid4()), user_id=1)


def test_revision_assignment_collects_manager(monkeypatch):
    assignment = SimpleNamespace(user_id=10, manager_user_id=20)
    monkeypatch.setattr(drafts_service.repo, "list_revision_assignments", lambda db, revision_id: [assignment])
    monkeypatch.setattr(drafts_service.repo, "get_people_map", lambda db, ids: {value: value for value in ids})
    monkeypatch.setattr(drafts_service, "_revision_assignment_response", lambda value, people: sorted(people))
    assert drafts_service.list_assignment_responses_for_revision(object(), uuid4()) == [[10, 20]]


def test_organigramma_service_fallbacks(monkeypatch, make_user):
    assert organigramma_service._person_ref(None) is None
    manager = make_user("manager-fallback")
    managed = [SimpleNamespace(active=True, title=None, manager_user_id=manager.id)]
    assert organigramma_service.resolve_unit_responsabile(managed, {manager.id: manager}) == (manager, None)
    assert organigramma_service.resolve_unit_responsabile([], {}) == (None, None)

    monkeypatch.setattr(organigramma_service.repo, "get_unit", lambda *args, **kwargs: None)
    assert organigramma_service.get_unit_detail(object(), uuid4()) is None

    future = SimpleNamespace(
        is_active=True,
        valid_from=datetime.now(timezone.utc) + timedelta(days=1),
        valid_to=None,
    )
    assert organigramma_service.override_status(future) == "programmato"


def test_override_response_and_list_collect_target_user(monkeypatch, make_user):
    viewer = make_user("override-viewer")
    target = make_user("override-target", full_name="Target User")
    override = SimpleNamespace(
        viewer_user_id=viewer.id,
        target_type="user",
        target_user_id=target.id,
        target_org_unit_id=None,
    )
    response = SimpleNamespace(status=None, viewer=None, target_label=None)
    monkeypatch.setattr(organigramma_service.OrgVisibilityOverrideResponse, "model_validate", lambda value: response)
    monkeypatch.setattr(organigramma_service, "override_status", lambda value: "attivo")
    monkeypatch.setattr(organigramma_service, "_person_ref", lambda value: value)
    assert organigramma_service.override_response(
        object(), override, people={viewer.id: viewer, target.id: target}, units_by_id={}
    ).target_label == "Target User"

    response.target_label = "reset"
    assert organigramma_service.override_response(
        object(), override, people={viewer.id: viewer}, units_by_id={}
    ).target_label is None

    monkeypatch.setattr(organigramma_service.repo, "list_overrides", lambda db, structure_kind: [override])
    monkeypatch.setattr(organigramma_service.repo, "get_people_map", lambda db, ids: {})
    monkeypatch.setattr(organigramma_service.repo, "list_units", lambda db, structure_kind: [])
    monkeypatch.setattr(organigramma_service, "override_response", lambda *args, **kwargs: "override")
    assert organigramma_service.list_override_responses(object()) == ["override"]


def test_visibility_result_skips_ineligible_assignments(monkeypatch, make_user):
    viewer = make_user("visibility-result")
    visible_unit = uuid4()
    other_unit = uuid4()
    visibility = SimpleNamespace(
        full=False,
        unit_via={visible_unit: VIA_HIERARCHY},
        unit_scope={visible_unit: "approve"},
        person_ids={10},
        person_via={10: VIA_HIERARCHY},
        person_scope={10: "approve"},
    )
    unit = SimpleNamespace(id=visible_unit, nome="Visible", tipo="settore", parent_id=None)
    assignments = [
        SimpleNamespace(active=False, user_id=10, org_unit_id=visible_unit, is_primary=False, title=None),
        SimpleNamespace(active=True, user_id=11, org_unit_id=visible_unit, is_primary=False, title=None),
        SimpleNamespace(active=True, user_id=10, org_unit_id=other_unit, is_primary=False, title=None),
        SimpleNamespace(active=True, user_id=10, org_unit_id=visible_unit, is_primary=True, title="Capo"),
    ]
    monkeypatch.setattr(organigramma_service, "effective_visibility", lambda *args, **kwargs: visibility)
    monkeypatch.setattr(organigramma_service.repo, "list_units", lambda *args, **kwargs: [unit])
    monkeypatch.setattr(organigramma_service.repo, "list_assignments", lambda *args, **kwargs: assignments)
    monkeypatch.setattr(organigramma_service.repo, "get_people_map", lambda *args, **kwargs: {})

    result = organigramma_service.build_visibility_result(object(), viewer)
    assert result.people[0].title == "Capo"


def test_descendants_handles_cycle():
    first, second = uuid4(), uuid4()
    assert _descendants(first, {first: [second], second: [first]}) == {first, second}


def test_whitecompany_mapping_helpers():
    assert whitecompany_sync._parse_source_field(None) == {}
    monkey_db = SimpleNamespace()
    monkey_db.get = lambda *args: None
    original = whitecompany_sync._find_unit_link
    try:
        whitecompany_sync._find_unit_link = lambda db, wc_id: None
        assert whitecompany_sync._resolve_root_unit(monkey_db, 1) is None
    finally:
        whitecompany_sync._find_unit_link = original

    assert whitecompany_sync._target_depth_for_role(None) is None
    assert whitecompany_sync._target_depth_for_role("Capo reparto") == 3
    assert whitecompany_sync._target_bucket_for_role(None) is None
    assert whitecompany_sync._target_bucket_for_role("Capo reparto") == "reparto"

    for name, expected in [
        ("Area tecnica", "area"),
        ("Reparto nord", "reparto"),
        ("Distretto sud", "distretto"),
        ("Altro", None),
    ]:
        assert whitecompany_sync._unit_bucket(SimpleNamespace(nome=name)) == expected

    parent = SimpleNamespace(id=uuid4())
    shallow = SimpleNamespace(id=uuid4())
    deep = SimpleNamespace(id=uuid4())
    children = {parent.id: [shallow, deep]}
    cursors = defaultdict(int)
    depths = {shallow.id: 1, deep.id: 2}
    assert whitecompany_sync._pick_child_unit(
        parent_unit=parent,
        child_units_by_parent_id=children,
        next_child_cursor_by_parent_key=cursors,
        target_depth=2,
        unit_depth_by_id=depths,
    ) is deep
    assert whitecompany_sync._pick_child_unit(
        parent_unit=parent,
        child_units_by_parent_id=children,
        next_child_cursor_by_parent_key=cursors,
        target_depth=None,
        unit_depth_by_id=depths,
    ) is shallow


class _QueuedResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class _WhiteCompanyDb:
    def __init__(self, results, units):
        self.results = list(results)
        self.units = units

    def execute(self, statement):
        return _QueuedResult(self.results.pop(0))

    def get(self, model, entity_id):
        return self.units.get(entity_id)

    def add(self, value):
        return None

    def flush(self):
        return None

    def commit(self):
        return None


def test_whitecompany_sync_edge_branches(monkeypatch):
    now = datetime.now(timezone.utc)
    chart_area = SimpleNamespace(wc_id=1, chart_type="area")
    chart_user = SimpleNamespace(wc_id=1, chart_type="user")
    chart_orphan = SimpleNamespace(wc_id=999, chart_type="user")

    root = SimpleNamespace(id=uuid4(), nome="Area tecnica", sort_order=0)
    child = SimpleNamespace(id=uuid4(), nome="Settore uno", sort_order=1)
    grandchild = SimpleNamespace(id=uuid4(), nome="Reparto uno", sort_order=2)
    role_unit = SimpleNamespace(
        id=uuid4(), nome="Old", tipo="settore", sort_order=3, parent_id=None,
        source=None, updated_by_user_id=None,
    )
    locked_unit = SimpleNamespace(id=uuid4(), nome="Locked", sort_order=4)

    def area_entry(wc_id, *, source, role=None, label=None, order=0):
        return SimpleNamespace(
            wc_id=wc_id,
            wc_operator_id=None,
            source_field=source,
            role=role,
            label=label,
            sort_order=order,
            created_at=now,
        )

    area_rows = [
        (area_entry(1, source="depth=0", role="squadra", label="Area root"), chart_area),
        (area_entry(2, source="depth=1|parent=1", order=1), chart_area),
        (area_entry(3, source="depth=2|parent=2", order=2), chart_area),
        (area_entry(10, source="depth=1|parent=1"), chart_area),
        (area_entry(11, source="depth=1|parent=1"), chart_area),
    ]

    operator_specs = [
        (100, 1000),
        (101, 1001),
        (102, 1002),
        (103, 1003),
        (104, 1000),
    ]
    operators = [SimpleNamespace(id=uuid4(), wc_id=wc_id, gaia_user_id=user_id) for wc_id, user_id in operator_specs]
    operator_by_wc_id = {operator.wc_id: operator for operator in operators}

    def user_entry(wc_id, *, parent=None, role=None, operator=True, chart=chart_user):
        source = "depth=0" if parent is None else f"depth=1|parent={parent}"
        return (
            SimpleNamespace(
                wc_id=wc_id,
                wc_operator_id=operator_by_wc_id[wc_id].id if operator and wc_id in operator_by_wc_id else None,
                source_field=source,
                role=role,
                label=str(wc_id),
                sort_order=wc_id,
                created_at=now,
            ),
            chart,
        )

    user_rows = [
        user_entry(900, operator=False, chart=chart_orphan),
        user_entry(901, operator=False),
        (
            SimpleNamespace(
                wc_id=902,
                wc_operator_id=uuid4(),
                source_field="depth=0",
                role=None,
                label="unmapped",
                sort_order=0,
                created_at=now,
            ),
            chart_user,
        ),
        user_entry(100),
        user_entry(101, parent=100, role="Staff"),
        user_entry(102, parent=101, role="Staff"),
        user_entry(103, parent=100, role="Dirigente"),
        user_entry(104, parent=100, role="Staff"),
    ]

    links = {
        1: SimpleNamespace(org_unit_id=root.id, is_manual_locked=False, last_synced_at=None),
        2: SimpleNamespace(org_unit_id=child.id, is_manual_locked=False, last_synced_at=None),
        3: SimpleNamespace(org_unit_id=grandchild.id, is_manual_locked=False, last_synced_at=None),
        10: SimpleNamespace(org_unit_id=locked_unit.id, is_manual_locked=True, last_synced_at=None),
        11: SimpleNamespace(org_unit_id=uuid4(), is_manual_locked=False, last_synced_at=None),
    }
    db = _WhiteCompanyDb(
        [[], area_rows, operators, user_rows],
        {root.id: root, child.id: child, grandchild.id: grandchild, role_unit.id: role_unit, locked_unit.id: locked_unit},
    )
    assignment_link = SimpleNamespace(is_manual_locked=True, last_synced_at=None)
    monkeypatch.setattr(whitecompany_sync, "_find_unit_link", lambda db, wc_id: links.get(wc_id))
    monkeypatch.setattr(whitecompany_sync, "_find_assignment_link", lambda db, wc_id: assignment_link)

    result = whitecompany_sync.sync_from_whitecompany(db, user_id=1)

    assert role_unit.tipo == "settore"
    assert root.tipo == "squadra"
    assert result.assignments_skipped_locked == 4
