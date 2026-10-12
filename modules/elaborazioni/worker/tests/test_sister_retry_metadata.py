from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.catasto import CatastoVisuraRequest
from sister_exceptions import SisterInvalidDocumentError, SisterRequestCorrelationError
from sister_retry_metadata import clear_remote_request_metadata, recoverable_retry_metadata


@pytest.mark.parametrize("clear_baseline", [None, False, True], ids=["default", "retain", "clear"])
@pytest.mark.parametrize("baseline", [None, ["existing-remote-key"]], ids=["empty", "populated"])
def test_clear_request_metadata_preserves_other_request_state(
    clear_baseline: bool | None, baseline: list[str] | None
) -> None:
    request_id = uuid4()
    credential_id = uuid4()
    request = CatastoVisuraRequest(
        id=request_id,
        status="queued_sister",
        current_operation="Await remote document",
        last_error_code="session_recovery",
        error_message="Synthetic recovery detail",
        attempts=3,
        sister_credential_id=credential_id,
        sister_remote_request_id="synthetic-remote-id",
        sister_remote_request_url="https://synthetic.invalid/request",
        sister_remote_state="queued",
        sister_remote_baseline_keys=baseline,
    )
    for _attempt in range(2):
        if clear_baseline is None:
            result = clear_remote_request_metadata(request)
        else:
            result = clear_remote_request_metadata(request, clear_baseline=clear_baseline)

        assert result is None
        assert request.sister_credential_id is None
        assert request.sister_remote_request_id is None
        assert request.sister_remote_request_url is None
        assert request.sister_remote_state is None
        assert request.sister_remote_baseline_keys is (None if clear_baseline else baseline)
        assert request.id == request_id
        assert request.status == "queued_sister"
        assert request.current_operation == "Await remote document"
        assert request.last_error_code == "session_recovery"
        assert request.error_message == "Synthetic recovery detail"
        assert request.attempts == 3


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            SisterRequestCorrelationError("Synthetic ambiguous correlation"),
            ("Correlazione SISTER non sicura, retry differito", "sister_correlation_error"),
        ),
        (
            SisterInvalidDocumentError("Synthetic invalid PDF"),
            ("PDF SISTER difforme o non valido, retry differito", "sister_invalid_document"),
        ),
        (
            TimeoutError("Synthetic session timeout"),
            ("Sessione/timeout su synthetic-user, retry differito", "session_recovery"),
        ),
    ],
    ids=["unsafe-correlation", "invalid-document", "session-timeout"],
)
def test_retry_metadata_keeps_reason_and_error_code(
    error: Exception, expected: tuple[str, str]
) -> None:
    assert recoverable_retry_metadata(error, "synthetic-user") == expected
