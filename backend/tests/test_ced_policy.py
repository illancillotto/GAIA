import pytest
from fastapi import HTTPException

from app.models.application_user import ApplicationUser
from app.modules.accessi.user_management_policy import (
    CED_MODULES,
    check_user_payload,
    require_not_ced,
    require_user_manager,
)


def user(role: str, user_id: int = 1, accessi: bool = False) -> ApplicationUser:
    return ApplicationUser(id=user_id, role=role, module_accessi=accessi)


@pytest.mark.parametrize("role,accessi", [("ced", False), ("admin", True), ("super_admin", False)])
def test_user_management_authorized(role: str, accessi: bool) -> None:
    actor = user(role, accessi=accessi)
    assert require_user_manager(actor) is actor


@pytest.mark.parametrize("role", ["viewer", "reviewer", "hr_manager", "operator", "admin"])
def test_user_management_denied(role: str) -> None:
    with pytest.raises(HTTPException) as error:
        require_user_manager(user(role))
    assert error.value.status_code == 403


def test_ced_has_no_network_or_nas_even_with_stale_flags() -> None:
    actor = user("ced", accessi=True)
    actor.module_rete = True
    actor.module_gis = True
    assert actor.enabled_modules == ["gis"]
    with pytest.raises(HTTPException):
        require_not_ced(actor)
    admin = user("admin")
    assert require_not_ced(admin) is admin


@pytest.mark.parametrize("role", ["viewer", "reviewer", "hr_manager", "operator"])
def test_ced_can_manage_standard_users(role: str) -> None:
    check_user_payload(user("ced"), {"role": role, "module_gis": True}, user(role, 2))


@pytest.mark.parametrize("module", sorted(CED_MODULES))
def test_ced_can_delegate_each_explicit_standard_module(module: str) -> None:
    check_user_payload(user("ced"), {f"module_{module}": True}, user("viewer", 2))


@pytest.mark.parametrize("role", ["admin", "super_admin", "ced", "future_role"])
def test_ced_cannot_manage_privileged_or_unknown_accounts(role: str) -> None:
    with pytest.raises(HTTPException):
        check_user_payload(user("ced"), {}, user(role, 2))


@pytest.mark.parametrize("role", ["ced", "admin", "super_admin", "invalid", None])
def test_ced_cannot_assign_privileged_roles(role: str | None) -> None:
    with pytest.raises(HTTPException):
        check_user_payload(user("ced"), {"role": role})


@pytest.mark.parametrize("field", ["module_accessi", "module_rete", "module_future"])
@pytest.mark.parametrize("existing", [False, True])
def test_ced_cannot_change_reserved_modules(field: str, existing: bool) -> None:
    target = user("viewer", 2)
    setattr(target, field, existing)
    check_user_payload(user("ced"), {field: existing}, target)
    with pytest.raises(HTTPException):
        check_user_payload(user("ced"), {field: not existing}, target)
    check_user_payload(user("ced"), {field: False})
    with pytest.raises(HTTPException):
        check_user_payload(user("ced"), {field: True})


def test_self_and_admin_hierarchy() -> None:
    with pytest.raises(HTTPException):
        check_user_payload(user("ced"), {}, user("viewer"))
    with pytest.raises(HTTPException):
        check_user_payload(user("admin"), {}, user("super_admin", 2))
    with pytest.raises(HTTPException):
        check_user_payload(user("admin"), {"role": "super_admin"}, user("viewer", 2))
    check_user_payload(user("super_admin"), {"role": "super_admin"}, user("super_admin", 2))
    check_user_payload(user("admin"), {"role": "ced"})
