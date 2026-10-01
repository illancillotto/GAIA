"""Schema compatibility for daily edits, absence exports and related validators."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.presenze import schemas


@pytest.mark.parametrize("kind,override", [("ordinary", False), ("working_override", True)])
def test_holiday_compatibility(kind, override):
    assert schemas.resolve_presenze_holiday_kind(kind, override) == kind
    assert schemas.resolve_presenze_holiday_kind(None, override) == kind
    assert schemas.resolve_presenze_holiday_kind(None, None, current_kind=kind) == kind
    with pytest.raises(ValueError):
        schemas.resolve_presenze_holiday_kind(kind, not override)


@pytest.mark.parametrize(
    "schema,identity",
    [
        (schemas.OrganizationTeamMembershipCreate, {"collaborator_id": uuid4()}),
        (schemas.OrganizationTeamSupervisorCreate, {"application_user_id": 12}),
    ],
)
def test_team_period_validation(schema, identity):
    with pytest.raises(ValidationError):
        schema(**identity, valid_from=date(2026, 10, 2), valid_to=date(2026, 10, 1))


@pytest.mark.parametrize(
    "schema", [schemas.GatePresenzeDailyRecordPatchRequest, schemas.PresenzeDailyRecordManualUpdate]
)
def test_daily_reperibilita_edit_validation(schema):
    assert schema(reperibilita_quantity=0).reperibilita_quantity is None
    assert schema(reperibilita_unit="none").reperibilita_quantity is None
    assert schema(reperibilita_unit="days", reperibilita_quantity=1).reperibilita_quantity == 1
    for payload in [
        {"reperibilita_quantity": 1},
        {"reperibilita_unit": "days"},
        {"reperibilita_unit": "hours", "reperibilita_quantity": 0},
    ]:
        with pytest.raises(ValidationError):
            schema(**payload)


def test_manual_voucher_does_not_reset_omitted_fields():
    assert schemas.PresenzeDailyRecordManualUpdate(meal_voucher_manual=True).model_dump(
        exclude_unset=True
    ) == {"meal_voucher_manual": True}
    assert "meal_voucher_manual" not in schemas.PresenzeDailyRecordManualUpdate(
        km_value=1
    ).model_dump(exclude_unset=True)
    with pytest.raises(ValidationError):
        schemas.PresenzeDailyRecordManualUpdate(meal_voucher_manual=None)


def test_bank_hours_update_requires_valid_sign():
    assert (
        schemas.PresenzeBankHoursAdjustmentUpdate(kind="credit", delta_minutes=1).delta_minutes == 1
    )
    for kind in ["credit", "debit", "liquidation", "correction"]:
        with pytest.raises(ValidationError):
            schemas.PresenzeBankHoursAdjustmentUpdate(kind=kind, delta_minutes=0)
    schemas._validate_bank_hours_delta("correction", 1)


def test_legacy_schema_aliases_remain_available():
    assert schemas.__getattr__("resolve_inaz_holiday_kind") is schemas.resolve_presenze_holiday_kind
    assert (
        schemas.__getattr__("InazDailyRecordManualUpdate")
        is schemas.PresenzeDailyRecordManualUpdate
    )
    for name in ["InazNonexistent", "OtherNonexistent"]:
        with pytest.raises(AttributeError):
            schemas.__getattr__(name)
