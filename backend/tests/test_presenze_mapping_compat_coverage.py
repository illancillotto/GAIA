from __future__ import annotations

from datetime import date
import uuid

import pytest
from pydantic import ValidationError

from app.modules.presenze import models as presenze_models
from app.modules.presenze import schemas as presenze_schemas
from app.modules.presenze.schemas import (
    GatePresenzeDailyRecordPatchRequest,
    OrganizationTeamMembershipCreate,
    OrganizationTeamSupervisorCreate,
    PresenzeCollaboratorApplicationUserUpdate,
    PresenzeDailyRecordManualUpdate,
    resolve_presenze_holiday_kind,
)


def test_presenze_models_legacy_aliases_and_unknown_attribute() -> None:
    assert presenze_models.InazCollaborator is presenze_models.PresenzeCollaborator
    assert (
        presenze_models.INAZ_CONTRACT_KIND_OPERAIO
        is presenze_models.PRESENZE_CONTRACT_KIND_OPERAIO
    )
    with pytest.raises(AttributeError):
        getattr(presenze_models, "MissingAlias")


def test_presenze_schemas_legacy_aliases_and_unknown_attribute() -> None:
    assert (
        presenze_schemas.resolve_inaz_holiday_kind
        is resolve_presenze_holiday_kind
    )
    assert (
        presenze_schemas.InazModuleStatusResponse
        is presenze_schemas.PresenzeModuleStatusResponse
    )
    with pytest.raises(AttributeError):
        getattr(presenze_schemas, "MissingAlias")


def test_resolve_presenze_holiday_kind_validation_and_fallback() -> None:
    with pytest.raises(ValueError, match="incoerenti"):
        resolve_presenze_holiday_kind("ordinary", True)
    assert resolve_presenze_holiday_kind(None, None, current_kind="suppressed") == "suppressed"
    assert resolve_presenze_holiday_kind(None, True) == "working_override"
    assert resolve_presenze_holiday_kind(None, False) == "ordinary"
    assert resolve_presenze_holiday_kind("suppressed", True) == "suppressed"


def test_presenze_collaborator_application_user_update_reason_normalization() -> None:
    payload = PresenzeCollaboratorApplicationUserUpdate(
        application_user_id=1,
        reason="  mapped for hierarchy  ",
    )
    assert payload.reason == "mapped for hierarchy"
    with pytest.raises(ValidationError):
        PresenzeCollaboratorApplicationUserUpdate(application_user_id=1, reason="   ")


def test_organization_team_period_validators_reject_inverted_ranges() -> None:
    with pytest.raises(ValidationError):
        OrganizationTeamMembershipCreate(
            collaborator_id=uuid.uuid4(),
            valid_from=date(2026, 8, 10),
            valid_to=date(2026, 8, 1),
        )
    with pytest.raises(ValidationError):
        OrganizationTeamSupervisorCreate(
            application_user_id=7,
            valid_from=date(2026, 8, 10),
            valid_to=date(2026, 8, 1),
        )


def test_reperibilita_validators_for_gate_and_manual_updates() -> None:
    with pytest.raises(ValidationError):
        GatePresenzeDailyRecordPatchRequest(reperibilita_unit="none", reperibilita_quantity=1)
    cleared = GatePresenzeDailyRecordPatchRequest(reperibilita_unit="none", reperibilita_quantity=0)
    assert cleared.reperibilita_quantity is None
    with pytest.raises(ValidationError):
        GatePresenzeDailyRecordPatchRequest(reperibilita_unit="shifts", reperibilita_quantity=0)
    gate_ok = GatePresenzeDailyRecordPatchRequest(reperibilita_unit="shifts", reperibilita_quantity=2)
    assert gate_ok.reperibilita_quantity == 2

    with pytest.raises(ValidationError):
        PresenzeDailyRecordManualUpdate(reperibilita_unit="none", reperibilita_quantity=2)
    manual_cleared = PresenzeDailyRecordManualUpdate(reperibilita_unit="none", reperibilita_quantity=0)
    assert manual_cleared.reperibilita_quantity is None
    with pytest.raises(ValidationError):
        PresenzeDailyRecordManualUpdate(reperibilita_unit="shifts", reperibilita_quantity=None)
    manual_ok = PresenzeDailyRecordManualUpdate(reperibilita_unit="shifts", reperibilita_quantity=3)
    assert manual_ok.reperibilita_quantity == 3


def test_validate_bank_hours_delta_rules() -> None:
    with pytest.raises(ValueError, match="positive for credit"):
        presenze_schemas._validate_bank_hours_delta("credit", 0)
    with pytest.raises(ValueError, match="negative for debit"):
        presenze_schemas._validate_bank_hours_delta("debit", 1)
    with pytest.raises(ValueError, match="non-zero for correction"):
        presenze_schemas._validate_bank_hours_delta("correction", 0)
    presenze_schemas._validate_bank_hours_delta("credit", 30)
    presenze_schemas._validate_bank_hours_delta("liquidation", -15)
    presenze_schemas._validate_bank_hours_delta("correction", -5)
