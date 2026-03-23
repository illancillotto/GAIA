from app.schemas.permissions import PermissionCalculationRequest, PermissionEntryInput, PermissionUserInput
from app.services.permissions import calculate_effective_permissions


def test_calculate_effective_permissions_applies_write_implies_read() -> None:
    payload = PermissionCalculationRequest(
        users=[PermissionUserInput(username="mrossi", groups=["amministrazione"])],
        permission_entries=[
            PermissionEntryInput(
                share_name="contabilita",
                subject_type="group",
                subject_name="amministrazione",
                permission_level="write",
                is_deny=False,
            )
        ],
    )

    results = calculate_effective_permissions(payload)

    assert results[0].can_read is True
    assert results[0].can_write is True
    assert results[0].is_denied is False


def test_calculate_effective_permissions_prioritizes_deny() -> None:
    payload = PermissionCalculationRequest(
        users=[PermissionUserInput(username="mrossi", groups=["amministrazione"])],
        permission_entries=[
            PermissionEntryInput(
                share_name="contabilita",
                subject_type="group",
                subject_name="amministrazione",
                permission_level="write",
                is_deny=False,
            ),
            PermissionEntryInput(
                share_name="contabilita",
                subject_type="user",
                subject_name="mrossi",
                permission_level="read",
                is_deny=True,
            ),
        ],
    )

    results = calculate_effective_permissions(payload)

    assert results[0].can_read is False
    assert results[0].can_write is False
    assert results[0].is_denied is True
