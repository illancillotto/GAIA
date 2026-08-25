from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.catasto import (
    CatastoCredentialAvailabilitySchedule,
    CatastoCredentialAvailabilityWindow,
    CatastoCredentialCreateRequest,
    CatastoCredentialTestRequest,
    CatastoSingleVisuraCreateRequest,
)
from app.services.elaborazioni_credential_schedule import (
    credential_is_available,
    next_credential_availability,
)

SCHEDULE = {
    "timezone": "Europe/Rome",
    "weekly": {
        "0": [{"start": "18:00", "end": "08:00"}],
        "1": [{"start": "10:00", "end": "12:00"}],
        "5": [{"start": "00:00", "end": "00:00"}],
    },
}


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def test_disabled_schedule_is_always_available() -> None:
    reference = utc("2026-08-25T07:00:00")
    assert credential_is_available(False, None, reference)
    assert next_credential_availability(False, None, reference) == reference


def test_weekly_schedule_supports_daytime_overnight_and_full_day_windows() -> None:
    assert credential_is_available(True, SCHEDULE, utc("2026-08-24T17:00:00"))
    assert credential_is_available(True, SCHEDULE, utc("2026-08-25T05:59:00"))
    assert not credential_is_available(True, SCHEDULE, utc("2026-08-25T06:00:00"))
    assert credential_is_available(True, SCHEDULE, utc("2026-08-25T09:00:00"))
    assert not credential_is_available(True, SCHEDULE, utc("2026-08-25T10:00:00"))
    assert credential_is_available(True, SCHEDULE, utc("2026-08-29T12:00:00"))


def test_next_availability_finds_the_next_minute_or_returns_none() -> None:
    reference = utc("2026-08-25T07:59:00")
    assert next_credential_availability(True, SCHEDULE, reference) == utc("2026-08-25T08:00:00")
    assert next_credential_availability(True, {"timezone": "Europe/Rome", "weekly": {}}, reference) is None
    assert not credential_is_available(True, None, reference)


def test_schedule_payload_rejects_unsupported_values() -> None:
    valid_schedule = CatastoCredentialAvailabilitySchedule(
        timezone="Europe/Rome",
        weekly={"0": [{"start": "18:00", "end": "08:00"}]},
    )
    assert valid_schedule.timezone == "Europe/Rome"
    assert CatastoCredentialCreateRequest(
        sister_username="user",
        sister_password="secret",
        schedule_enabled=True,
        availability_schedule=valid_schedule,
    ).schedule_enabled
    with pytest.raises(ValidationError, match="HH:MM"):
        CatastoCredentialAvailabilityWindow(start="24:00", end="08:00")
    with pytest.raises(ValidationError, match="Europe/Rome"):
        CatastoCredentialAvailabilitySchedule(timezone="UTC")
    with pytest.raises(ValidationError, match="weekdays"):
        CatastoCredentialAvailabilitySchedule(weekly={"7": []})
    with pytest.raises(ValidationError, match="maximum of four"):
        CatastoCredentialAvailabilitySchedule(
            weekly={"0": [{"start": "08:00", "end": "09:00"}] * 5},
        )
    with pytest.raises(ValidationError, match="schedule is required"):
        CatastoCredentialCreateRequest(
            sister_username="user",
            sister_password="secret",
            schedule_enabled=True,
        )


def test_catasto_credential_and_visura_payload_validation_branches() -> None:
    assert CatastoCredentialTestRequest().credential_id is None
    credential_id = uuid4()
    assert CatastoCredentialTestRequest(credential_id=credential_id).credential_id == credential_id
    assert CatastoCredentialTestRequest(sister_username="user", sister_password="secret").sister_username == "user"
    with pytest.raises(ValidationError, match="either credential_id"):
        CatastoCredentialTestRequest(
            credential_id=credential_id,
            sister_username="user",
            sister_password="secret",
        )
    with pytest.raises(ValidationError, match="Both sister_username"):
        CatastoCredentialTestRequest(credential_id=credential_id, sister_username="user")

    with pytest.raises(ValidationError, match="subject_id is required"):
        CatastoSingleVisuraCreateRequest(search_mode="soggetto")
    piva = CatastoSingleVisuraCreateRequest(search_mode="soggetto", subject_id=" 01234567890 ")
    assert piva.subject_kind == "PNF" and piva.subject_id == "01234567890"
    codice_fiscale = CatastoSingleVisuraCreateRequest(
        search_mode="soggetto",
        subject_id="rssmra80a01h501u",
    )
    assert codice_fiscale.subject_kind == "PF" and codice_fiscale.subject_id == "RSSMRA80A01H501U"
    with pytest.raises(ValidationError, match="Codice fiscale non valido"):
        CatastoSingleVisuraCreateRequest(search_mode="soggetto", subject_kind="PF", subject_id="invalid")
    with pytest.raises(ValidationError, match="Partita IVA non valida"):
        CatastoSingleVisuraCreateRequest(search_mode="soggetto", subject_kind="PNF", subject_id="123")
    with pytest.raises(ValidationError, match="either 'immobile' o 'soggetto'"):
        CatastoSingleVisuraCreateRequest(search_mode="unknown")
    with pytest.raises(ValidationError, match="Missing required fields"):
        CatastoSingleVisuraCreateRequest(search_mode="immobile")
    immobile = CatastoSingleVisuraCreateRequest(
        search_mode="immobile",
        comune="ORISTANO",
        catasto="TERRENI",
        foglio="1",
        particella="2",
    )
    assert immobile.particella == "2"
