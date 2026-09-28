import pytest

from sister_worker_reliability import _ClaimScan


@pytest.mark.parametrize("delays", [(), (30,), (30, 10, 20), (0,), (30, 0)])
@pytest.mark.parametrize("captcha", [False, True])
def test_claim_scan_preserves_wait_priority_and_earliest_retry(delays, captcha):
    scan = _ClaimScan(has_waiting_captcha=captcha)
    for seconds in delays:
        scan.record_deferred(seconds)

    selection = scan.selection()

    assert selection.request_id is None
    assert selection.wait_reason == ("WAIT" if captcha else "RETRY_LATER" if delays else None)
    assert selection.wait_seconds == (min(delays) if delays and not captcha else None)
