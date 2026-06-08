"""Test puri del motore di visibilità (nessun DB)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.organigramma.services.visibility_service import (
    VIA_HIERARCHY,
    VIA_OVERRIDE,
    _build_children_map,
    _descendants,
    _within_window,
    compute_visibility,
)

NOW = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)

# Albero:  A -> B -> D ; A -> C
A, B, C, D = uuid4(), uuid4(), uuid4(), uuid4()


def unit(uid, parent=None):
    return SimpleNamespace(id=uid, parent_id=parent)


def assignment(user_id, org_unit_id, manager_user_id=None, active=True):
    return SimpleNamespace(
        user_id=user_id, org_unit_id=org_unit_id, manager_user_id=manager_user_id, active=active
    )


def override(
    viewer_user_id,
    *,
    target_type,
    target_user_id=None,
    target_org_unit_id=None,
    scope="read",
    is_active=True,
    valid_from=None,
    valid_to=None,
):
    return SimpleNamespace(
        viewer_user_id=viewer_user_id,
        target_type=target_type,
        target_user_id=target_user_id,
        target_org_unit_id=target_org_unit_id,
        scope=scope,
        is_active=is_active,
        valid_from=valid_from,
        valid_to=valid_to,
    )


UNITS = [unit(A), unit(B, A), unit(C, A), unit(D, B)]


# --------------------------------------------------------------------------- #
# Helpers puri
# --------------------------------------------------------------------------- #
def test_within_window_bounds():
    assert _within_window(NOW, None, None) is True
    assert _within_window(NOW, NOW - timedelta(days=1), NOW + timedelta(days=1)) is True
    assert _within_window(NOW, NOW + timedelta(days=1), None) is False  # programmato
    assert _within_window(NOW, None, NOW - timedelta(days=1)) is False  # scaduto


def test_build_children_map_and_descendants():
    children = _build_children_map(UNITS)
    assert set(children[A]) == {B, C}
    assert children[B] == [D]
    assert _descendants(A, children) == {A, B, C, D}
    assert _descendants(B, children) == {B, D}
    assert _descendants(C, children) == {C}


# --------------------------------------------------------------------------- #
# super_admin
# --------------------------------------------------------------------------- #
def test_super_admin_sees_everything():
    assignments = [assignment(10, D)]
    result = compute_visibility(
        viewer_id=1, is_super_admin=True, units=UNITS, assignments=assignments, overrides=[], now=NOW
    )
    assert result.full is True
    assert result.unit_ids == {A, B, C, D}
    assert all(via == VIA_HIERARCHY for via in result.unit_via.values())
    assert result.person_ids == {10}


# --------------------------------------------------------------------------- #
# Gerarchia a cascata
# --------------------------------------------------------------------------- #
def test_manager_sees_unit_and_descendants():
    # V (id=2) è manager dei membri della unità B -> vede B + D, non A né C
    assignments = [
        assignment(20, B, manager_user_id=2),
        assignment(30, D, manager_user_id=20),
        assignment(40, C, manager_user_id=99),
    ]
    result = compute_visibility(
        viewer_id=2, is_super_admin=False, units=UNITS, assignments=assignments, overrides=[], now=NOW
    )
    assert result.full is False
    assert result.unit_via == {B: VIA_HIERARCHY, D: VIA_HIERARCHY}
    # persone nelle unità visibili
    assert result.person_via == {20: VIA_HIERARCHY, 30: VIA_HIERARCHY}
    assert 40 not in result.person_ids


def test_inactive_assignment_does_not_grant_hierarchy():
    assignments = [assignment(20, B, manager_user_id=2, active=False)]
    result = compute_visibility(
        viewer_id=2, is_super_admin=False, units=UNITS, assignments=assignments, overrides=[], now=NOW
    )
    assert result.unit_via == {}
    assert result.person_via == {}


# --------------------------------------------------------------------------- #
# Override org_unit
# --------------------------------------------------------------------------- #
def test_override_org_unit_adds_subtree_with_scope():
    overrides = [override(5, target_type="org_unit", target_org_unit_id=B, scope="approve")]
    assignments = [assignment(20, D)]
    result = compute_visibility(
        viewer_id=5, is_super_admin=False, units=UNITS, assignments=assignments, overrides=overrides, now=NOW
    )
    assert result.unit_via == {B: VIA_OVERRIDE, D: VIA_OVERRIDE}
    assert result.unit_scope[B] == "approve"
    assert result.person_via == {20: VIA_OVERRIDE}


def test_hierarchy_takes_precedence_over_override():
    # V manager in B (gerarchia) e anche override su A (che contiene B): B resta gerarchia
    assignments = [assignment(20, B, manager_user_id=7)]
    overrides = [override(7, target_type="org_unit", target_org_unit_id=A, scope="full")]
    result = compute_visibility(
        viewer_id=7, is_super_admin=False, units=UNITS, assignments=assignments, overrides=overrides, now=NOW
    )
    assert result.unit_via[B] == VIA_HIERARCHY
    assert result.unit_via[D] == VIA_HIERARCHY  # discendente via gerarchia
    assert result.unit_via[A] == VIA_OVERRIDE
    assert result.unit_via[C] == VIA_OVERRIDE
    # la persona in B resta gerarchia
    assert result.person_via[20] == VIA_HIERARCHY


# --------------------------------------------------------------------------- #
# Override user
# --------------------------------------------------------------------------- #
def test_override_user_adds_target_person_and_unit():
    overrides = [override(9, target_type="user", target_user_id=50, scope="read")]
    assignments = [assignment(50, C)]
    result = compute_visibility(
        viewer_id=9, is_super_admin=False, units=UNITS, assignments=assignments, overrides=overrides, now=NOW
    )
    assert result.person_via == {50: VIA_OVERRIDE}
    assert result.unit_via == {C: VIA_OVERRIDE}


# --------------------------------------------------------------------------- #
# Finestra temporale e stato
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "kwargs",
    [
        {"is_active": False},
        {"valid_from": NOW + timedelta(days=1)},  # programmato
        {"valid_to": NOW - timedelta(days=1)},  # scaduto
    ],
)
def test_inactive_or_out_of_window_override_ignored(kwargs):
    overrides = [override(3, target_type="org_unit", target_org_unit_id=B, **kwargs)]
    result = compute_visibility(
        viewer_id=3, is_super_admin=False, units=UNITS, assignments=[], overrides=overrides, now=NOW
    )
    assert result.unit_via == {}


def test_override_for_other_viewer_ignored():
    overrides = [override(999, target_type="org_unit", target_org_unit_id=B)]
    result = compute_visibility(
        viewer_id=3, is_super_admin=False, units=UNITS, assignments=[], overrides=overrides, now=NOW
    )
    assert result.unit_via == {}


def test_override_targeting_unknown_unit_is_noop():
    overrides = [override(3, target_type="org_unit", target_org_unit_id=uuid4())]
    result = compute_visibility(
        viewer_id=3, is_super_admin=False, units=UNITS, assignments=[], overrides=overrides, now=NOW
    )
    assert result.unit_via == {}


def test_default_now_branch_executes():
    # now=None deve usare datetime.now(): nessuna eccezione e nessuna visibilità.
    result = compute_visibility(
        viewer_id=1, is_super_admin=False, units=UNITS, assignments=[], overrides=[]
    )
    assert result.unit_via == {}
