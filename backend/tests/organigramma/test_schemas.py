from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.organigramma.schemas import (
    OrgUnitCreate,
    OrgVisibilityOverrideCreate,
)


def test_unit_create_rejects_invalid_tipo():
    with pytest.raises(ValidationError):
        OrgUnitCreate(nome="X", tipo="reparto")  # type: ignore[arg-type]


def test_unit_create_rejects_invalid_source():
    with pytest.raises(ValidationError):
        OrgUnitCreate(nome="X", tipo="settore", source="sap")  # type: ignore[arg-type]


def test_override_user_target_requires_user_id_only():
    ok = OrgVisibilityOverrideCreate(
        viewer_user_id=1, target_type="user", target_user_id=2, scope="read"
    )
    assert ok.target_user_id == 2

    with pytest.raises(ValidationError):
        OrgVisibilityOverrideCreate(
            viewer_user_id=1, target_type="user", target_org_unit_id=uuid4(), scope="read"
        )


def test_override_org_unit_target_requires_unit_id_only():
    unit_id = uuid4()
    ok = OrgVisibilityOverrideCreate(
        viewer_user_id=1, target_type="org_unit", target_org_unit_id=unit_id, scope="full"
    )
    assert ok.target_org_unit_id == unit_id

    with pytest.raises(ValidationError):
        OrgVisibilityOverrideCreate(
            viewer_user_id=1, target_type="org_unit", target_user_id=5, scope="full"
        )


def test_override_rejects_invalid_scope():
    with pytest.raises(ValidationError):
        OrgVisibilityOverrideCreate(
            viewer_user_id=1, target_type="org_unit", target_org_unit_id=uuid4(), scope="write"  # type: ignore[arg-type]
        )
