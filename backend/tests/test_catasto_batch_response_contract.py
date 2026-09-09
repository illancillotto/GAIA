from uuid import uuid4

from app.schemas.catasto import (
    CatastoBatchCredentialUsageResponse,
    CatastoCredentialAvailabilitySchedule,
)


def test_batch_credential_response_preserves_zero_completed_visure() -> None:
    response = CatastoBatchCredentialUsageResponse(
        credential_id=uuid4(),
        label="Operatore",
        sister_username=None,
        request_count=5,
        execution_count=12,
        completed_count=0,
    )
    assert response.model_dump()["completed_count"] == 0


def test_credential_schedule_accepts_distinct_monthly_exceptions() -> None:
    schedule = CatastoCredentialAvailabilitySchedule(
        exceptions=[
            {"kind": "nth_weekday_of_month", "weekday": 5, "occurrence": 1, "windows": []},
            {"kind": "nth_weekday_of_month", "weekday": 5, "occurrence": 2, "windows": []},
        ]
    )
    assert [exception.occurrence for exception in schedule.exceptions] == [1, 2]
