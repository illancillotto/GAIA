"""R128 characterization of WhiteCompany operator unit placement.

Every scenario drives the public ``sync_from_whitecompany`` service against the
real SQLite test schema and asserts the exact org unit chosen per operator.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.organigramma.models import OrgAssignment, OrgSourceLink, OrgUnit
from app.modules.organigramma.services import whitecompany_sync

# Area tree used by the placement matrix (wc_id, name, parent wc_id, depth).
# DFS order below the root: Settore uno > Sezione alfa > Reparto beta, Settore due > Gruppo misto.
_AREA_TREE = [
    (1, "Area tecnica", None, 0),
    (2, "Settore uno", 1, 1),
    (3, "Sezione alfa", 2, 2),
    (6, "Reparto beta", 3, 3),
    (4, "Settore due", 1, 1),
    (5, "Gruppo misto", 4, 2),
]


def _source(*, chart: str, depth: int | None, parent: int | str | None) -> str:
    parts = ["datasource_node", f"chart={chart}"]
    if depth is not None:
        parts.append(f"depth={depth}")
    if parent is not None:
        parts.append(f"parent={parent}")
    return "|".join(parts)


def _build_area_tree(session, *, chart_wc_id: int = 50, tree=_AREA_TREE) -> WCOrgChart:
    areas = {
        wc_id: WCArea(wc_id=wc_id, name=name, is_district=False) for wc_id, name, _p, _d in tree
    }
    session.add_all(areas.values())
    area_chart = WCOrgChart(wc_id=chart_wc_id, chart_type="area", name="Area chart")
    session.add(area_chart)
    session.flush()
    session.add_all(
        [
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=wc_id,
                label=name,
                wc_area_id=areas[wc_id].id,
                source_field=_source(chart="area", depth=depth, parent=parent),
                sort_order=index,
            )
            for index, (wc_id, name, parent, depth) in enumerate(tree)
        ]
    )
    session.flush()
    return area_chart


def _add_user_chart(session, *, chart_wc_id: int, rows, make_user, operators=None):
    """rows: (wc_id, parent wc_id, role, username). Returns {wc_id: user}."""
    operators = {} if operators is None else operators
    users = {}
    for wc_id, _parent, _role, username in rows:
        if username is None:
            continue
        if username not in operators:
            operators[username] = make_user(username)
        users[wc_id] = operators[username]
    wc_operators = {
        wc_id: WCOperator(wc_id=wc_id, gaia_user_id=user.id) for wc_id, user in users.items()
    }
    session.add_all(wc_operators.values())
    user_chart = WCOrgChart(wc_id=chart_wc_id, chart_type="user", name=f"User chart {chart_wc_id}")
    session.add(user_chart)
    session.flush()
    session.add_all(
        [
            WCOrgChartEntry(
                org_chart_id=user_chart.id,
                wc_id=wc_id,
                label=str(wc_id),
                role=role,
                wc_operator_id=wc_operators[wc_id].id if wc_id in wc_operators else None,
                source_field=_source(chart="user", depth=None, parent=parent),
                sort_order=index,
            )
            for index, (wc_id, parent, role, _username) in enumerate(rows)
        ]
    )
    session.flush()
    return users


def _placement_by_wc_id(session, users):
    session.expire_all()
    names = {unit.id: unit.nome for unit in session.query(OrgUnit).all()}
    assignments = {row.user_id: row for row in session.query(OrgAssignment).all()}
    return {
        wc_id: names[assignments[user.id].org_unit_id]
        for wc_id, user in users.items()
        if user.id in assignments
    }


# (wc_id, parent wc_id, role, username)
_MATRIX_ROWS = [
    (100, None, "Dirigente", "u100"),  # (a) no parent -> root
    (101, 100, "Amministratore", "u101"),  # (b) target depth <= parent depth -> parent unit
    (102, 100, "Capo sezione", "u102"),  # (c) bucket descendant, skipping the settore level
    (103, 100, "Capo sezione", "u103"),  # (c) bucket cursor clamps to the last candidate
    (104, 102, "Capo reparto", "u104"),  # (c) bucket descendant below an operator unit
    (105, 100, "Capo settore", "u105"),  # bucket cursor 0
    (106, 100, "Capo settore", "u106"),  # bucket cursor 1
    (107, 106, "Capo sezione", "u107"),  # (d) bucket miss -> depth-matched child
    (108, 106, "Capo reparto", "u108"),  # (d) bucket miss, no depth match -> any child
    (109, 107, "Capo reparto", "u109"),  # (e) nothing to pick -> parent unit
    (110, 100, None, "u110"),  # (f) no role, has operator children -> child cursor 0
    (111, 110, "Staff", "u111"),  # (g) unrecognised role, leaf -> child of its parent unit
    (112, 100, None, "u112"),  # (g) no role, leaf -> shares the (parent, -1) cursor: index 1
    (113, 100, "Staff", "u113"),  # (g) cursor clamps to the last child
    (114, 9999, "Capo settore", "u114"),  # unknown parent operator -> root, no manager
]


def test_r128_operator_placement_matrix(session, make_user):
    _build_area_tree(session)
    users = _add_user_chart(session, chart_wc_id=1, rows=_MATRIX_ROWS, make_user=make_user)
    session.commit()

    first = whitecompany_sync.sync_from_whitecompany(session, user_id=None)

    assert (first.units_created, first.units_updated, first.units_skipped_locked) == (6, 0, 0)
    assert (
        first.assignments_created,
        first.assignments_updated,
        first.assignments_skipped_locked,
    ) == (
        len(_MATRIX_ROWS),
        0,
        0,
    )
    # First run quirk (autoflush=False): the link of the last area created in the run is not
    # flushed yet, so "Gruppo misto" is missing from the tree and its operators stay on Settore due.
    first_placement = _placement_by_wc_id(session, users)
    assert [first_placement[wc_id] for wc_id in (107, 108, 109)] == ["Settore due"] * 3

    result = whitecompany_sync.sync_from_whitecompany(session, user_id=None)

    assert (result.units_created, result.units_updated, result.units_skipped_locked) == (0, 6, 0)
    assert (
        result.assignments_created,
        result.assignments_updated,
        result.assignments_skipped_locked,
    ) == (
        0,
        len(_MATRIX_ROWS),
        0,
    )
    assert _placement_by_wc_id(session, users) == {
        100: "Area tecnica",
        101: "Area tecnica",
        102: "Sezione alfa",
        103: "Sezione alfa",
        104: "Reparto beta",
        105: "Settore uno",
        106: "Settore due",
        107: "Gruppo misto",
        108: "Gruppo misto",
        109: "Gruppo misto",
        110: "Settore uno",
        111: "Sezione alfa",
        112: "Settore due",
        113: "Settore due",
        114: "Settore due",
    }

    managers = {row.user_id: row.manager_user_id for row in session.query(OrgAssignment).all()}
    assert managers[users[100].id] is None
    assert managers[users[101].id] == users[100].id
    assert managers[users[104].id] == users[102].id
    assert managers[users[111].id] == users[110].id
    assert managers[users[114].id] is None

    links = session.query(OrgSourceLink).filter(OrgSourceLink.entity_type == "org_assignment").all()
    assert sorted(link.external_wc_id for link in links) == [wc_id for wc_id, *_ in _MATRIX_ROWS]

    # Rerun: placement is recomputed with fresh cursors and identical results via the link path.
    rerun = whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    assert (rerun.assignments_created, rerun.assignments_updated) == (0, len(_MATRIX_ROWS))
    assert _placement_by_wc_id(session, users)[112] == "Settore due"


def test_r128_exact_unit_for_capo_sezione_under_capo_settore(session, make_user):
    """Stronger, exact-unit version of the test_api area-tree scenario."""
    tree = [
        (1, "Area agraria", None, 0),
        (2, "Settore Manutenzione", 1, 1),
        (6, "Sezione reti sud", 2, 2),
    ]
    _build_area_tree(session, chart_wc_id=9, tree=tree)
    rows = [
        (455, None, "Dirigente", "dir"),
        (13010, 455, "Capo settore", "sett"),
        (548, 13010, "Capo sezione", "sez"),
    ]
    users = _add_user_chart(session, chart_wc_id=1, rows=rows, make_user=make_user)
    session.commit()

    whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    # First run: the link of the last created area ("Sezione reti sud") is not flushed yet,
    # so the capo sezione stays on the settore unit (test_api accepts either unit).
    assert _placement_by_wc_id(session, users) == {
        455: "Area agraria",
        13010: "Settore Manutenzione",
        548: "Settore Manutenzione",
    }

    whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    assert _placement_by_wc_id(session, users) == {
        455: "Area agraria",
        13010: "Settore Manutenzione",
        548: "Sezione reti sud",
    }


def test_r128_locked_parent_still_anchors_children_and_users_are_deduplicated(session, make_user):
    _build_area_tree(session)
    shared = {}
    users = _add_user_chart(
        session,
        chart_wc_id=1,
        rows=[
            (100, None, "Dirigente", "boss"),
            (101, 100, "Capo settore", "locked"),
            (102, 101, "Capo sezione", "child"),
            (103, 100, "Capo settore", "boss"),  # same GAIA user as 100 -> skipped
            (104, None, None, None),  # entry without operator -> skipped
        ],
        make_user=make_user,
        operators=shared,
    )
    # Second user chart: the same GAIA user again (skipped across charts) and a fresh one.
    second_users = _add_user_chart(
        session,
        chart_wc_id=4,
        rows=[(200, None, "Staff", "child"), (201, None, "Staff", "second")],
        make_user=make_user,
        operators=shared,
    )
    # Third user chart whose root has no unit link: ignored entirely.
    orphan_users = _add_user_chart(
        session, chart_wc_id=777, rows=[(300, None, "Staff", "orphan")], make_user=make_user
    )
    # Operator whose GAIA user equals the parent operator's: no self-manager.
    self_parent = WCOperator(wc_id=400, gaia_user_id=make_user("selfie").id)
    session.add(self_parent)
    session.flush()
    self_users = _add_user_chart(
        session, chart_wc_id=2, rows=[(401, 400, "Staff", None)], make_user=make_user
    )
    self_op = WCOperator(wc_id=401, gaia_user_id=self_parent.gaia_user_id)
    session.add(self_op)
    session.flush()
    session.query(WCOrgChartEntry).filter(
        WCOrgChartEntry.wc_id == 401
    ).one().wc_operator_id = self_op.id
    session.commit()

    first = whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    assert first.assignments_created == 5
    assert self_users == {}

    locked_link = session.query(OrgSourceLink).filter(OrgSourceLink.external_wc_id == 101).one()
    locked_link.is_manual_locked = True
    locked_assignment = session.get(OrgAssignment, locked_link.org_assignment_id)
    locked_assignment.org_unit_id = (
        session.query(OrgUnit).filter(OrgUnit.nome == "Gruppo misto").one().id
    )
    session.commit()

    second = whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    assert (
        second.assignments_created,
        second.assignments_updated,
        second.assignments_skipped_locked,
    ) == (
        0,
        4,
        1,
    )
    placement = _placement_by_wc_id(session, users)
    assert placement[100] == "Area tecnica"
    assert placement[101] == "Gruppo misto"  # locked: untouched
    assert placement[102] == "Sezione alfa"  # still placed below the computed Settore uno
    assert placement[103] == "Area tecnica"  # 103 shares 100's user: only 100 assigned
    # Chart 4 is rooted at the unit of area wc_id 4.
    assert _placement_by_wc_id(session, second_users) == {200: "Sezione alfa", 201: "Settore due"}
    assert _placement_by_wc_id(session, orphan_users) == {}
    selfie = (
        session.query(OrgAssignment).filter(OrgAssignment.user_id == self_parent.gaia_user_id).one()
    )
    assert selfie.manager_user_id is None
    assert session.get(OrgUnit, selfie.org_unit_id).nome == "Settore uno"


def test_r128_bucket_miss_falls_back_to_depth_matched_non_first_child(session, make_user):
    """Bucket miss: the fallback must honour the role depth, not just take the first child."""
    tree = [
        (1, "Area tecnica", None, 0),
        (2, "Settore uno", 1, 1),
        (3, "Ufficio alto", 2, 3),  # first child of Settore uno, wrong depth, no bucket
        (4, "Gruppo misto", 2, 2),  # second child, depth 2, no bucket
        (5, "Settore coda", 1, 1),
    ]
    _build_area_tree(session, tree=tree)
    users = _add_user_chart(
        session,
        chart_wc_id=1,
        rows=[
            (100, None, "Dirigente", "a"),
            (101, 100, "Capo settore", "b"),
            (102, 101, "Capo sezione", "c"),
        ],
        make_user=make_user,
    )
    session.commit()

    whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    whitecompany_sync.sync_from_whitecompany(session, user_id=None)

    assert _placement_by_wc_id(session, users) == {
        100: "Area tecnica",
        101: "Settore uno",
        102: "Gruppo misto",
    }


def test_r128_area_sync_edge_branches(session, make_user):
    unlinked_area = WCArea(wc_id=70, name="Area senza unita", is_district=False)
    root_area = WCArea(wc_id=1, name="Area radice", is_district=False)
    child_area = WCArea(wc_id=2, name="Settore figlio", is_district=False)
    self_area = WCArea(wc_id=3, name="Settore autoreferenziale", is_district=False)
    session.add_all([unlinked_area, root_area, child_area, self_area])
    session.flush()
    session.add(
        OrgSourceLink(entity_type="org_unit", source_system="whitecompany", external_wc_id=70)
    )
    area_chart = WCOrgChart(wc_id=50, chart_type="area", name="Area chart")
    stray_chart = WCOrgChart(wc_id=60, chart_type="area", name="Stray chart")
    session.add_all([area_chart, stray_chart])
    session.flush()
    session.add_all(
        [
            # Root entry without depth and with an unrecognised role, no sort order.
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=1,
                label=None,
                role="ufficio",
                source_field="datasource_node|chart=area",
                sort_order=None,
            ),
            # Child entry without depth.
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=2,
                label="Settore figlio",
                source_field="datasource_node|chart=area|parent=1",
                sort_order=1,
            ),
            # Entry pointing at itself as parent: parent cleared.
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=3,
                label="Settore autoreferenziale",
                source_field="datasource_node|chart=area|depth=1|parent=3",
                sort_order=2,
            ),
            # Chart whose first row already has a parent: no root, never grouped.
            WCOrgChartEntry(
                org_chart_id=stray_chart.id,
                wc_id=2,
                label="Settore figlio",
                source_field="datasource_node|chart=area|depth=1|parent=1",
                sort_order=0,
            ),
        ]
    )
    session.flush()
    users = _add_user_chart(
        session,
        chart_wc_id=1,
        rows=[(100, None, "Dirigente", "r"), (101, 100, "Capo settore", "s")],
        make_user=make_user,
    )
    session.commit()

    result = whitecompany_sync.sync_from_whitecompany(session, user_id=None)

    assert (result.units_created, result.units_updated) == (3, 0)
    session.expire_all()
    units = {unit.nome: unit for unit in session.query(OrgUnit).all()}
    assert units["Area radice"].tipo == "settore"
    assert units["Area radice"].parent_id is None
    assert units["Settore figlio"].parent_id == units["Area radice"].id
    assert units["Settore autoreferenziale"].parent_id is None
    assert units["Settore autoreferenziale"].sort_order == 0  # last created area: link unflushed

    rerun = whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    assert (rerun.units_created, rerun.units_updated) == (0, 3)
    session.expire_all()
    units = {unit.nome: unit for unit in session.query(OrgUnit).all()}
    assert units["Settore autoreferenziale"].sort_order == 2
    assert units["Settore autoreferenziale"].parent_id is None
    unlinked = session.query(OrgSourceLink).filter(OrgSourceLink.external_wc_id == 70).one()
    assert unlinked.org_unit_id is None
    assert unlinked.last_synced_at is not None
    assert _placement_by_wc_id(session, users) == {100: "Area radice", 101: "Settore figlio"}


def _sync_then_detach_assignment_link(session, make_user, *, delete_assignment: bool):
    _build_area_tree(session)
    _add_user_chart(
        session, chart_wc_id=1, rows=[(100, None, "Dirigente", "a")], make_user=make_user
    )
    session.commit()
    whitecompany_sync.sync_from_whitecompany(session, user_id=None)

    link = (
        session.query(OrgSourceLink)
        .filter(OrgSourceLink.entity_type == "org_assignment", OrgSourceLink.external_wc_id == 100)
        .one()
    )
    assignment = session.get(OrgAssignment, link.org_assignment_id)
    link.org_assignment_id = None
    session.flush()
    if delete_assignment:
        session.delete(assignment)
    session.commit()


@pytest.mark.parametrize(
    "delete_assignment", [False, True], ids=["keep-assignment", "delete-assignment"]
)
def test_r128_unlocked_link_without_assignment_hits_known_duplicate_link_bug(
    session, make_user, delete_assignment
):
    """Known pre-existing bug (characterized, not fixed in R128).

    An unlocked org_assignment link whose org_assignment_id is NULL falls through to the
    wc_operator lookup (update path when the assignment survives, create path when it was
    deleted); both write a second link with the same external_wc_id, so the commit violates
    uq_org_source_link_entity_source_external.
    """
    _sync_then_detach_assignment_link(session, make_user, delete_assignment=delete_assignment)

    # SQLite reports the constraint by its columns rather than by name.
    unique_columns = (
        r"UNIQUE constraint failed: org_source_link\.entity_type, "
        r"org_source_link\.source_system, org_source_link\.external_wc_id"
    )
    with pytest.raises(IntegrityError, match=unique_columns):
        whitecompany_sync.sync_from_whitecompany(session, user_id=None)
    session.rollback()
