from pathlib import Path
import sys

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from sister_exceptions import SisterRequestCorrelationError
from sister_request_rows import (
    SisterRemoteRequestRow,
    SisterRequestCorrelation,
    build_correlation,
    correlate_remote_row,
    expected_request_tokens,
    extract_remote_id,
    normalize_portal_text,
    parse_remote_rows,
)


def _row(key: str, *, remote_id: str | None = None, text: str = "", state: str = "pending") -> SisterRemoteRequestRow:
    return SisterRemoteRequestRow(0, key, remote_id, state, text, (), None, None)


def test_normalize_and_expected_tokens_ignore_empty_values() -> None:
    request = type(
        "Request",
        (),
        {"subject_id": None, "comune": "Marrubìu", "foglio": "24", "particella": "7", "subalterno": ""},
    )()

    assert normalize_portal_text("  Marrubìu / Terreni ") == "MARRUBIU TERRENI"
    assert expected_request_tokens(request) == ("MARRUBIU", "24")


def test_parse_remote_rows_extracts_ids_states_and_actions() -> None:
    rows = parse_remote_rows(
        [
            {},
            {
                "text": "Richiesta espletata e pronta",
                "hrefs": ["/Visure/CheckRichiesta.do?idRichiesta=ABC-1"],
                "values": [],
            },
            {
                "text": "Richiesta NON EVADIBILE",
                "hrefs": ["/Visure/Elimina.do?protocollo=XYZ"],
                "values": [],
            },
            {"text": "In lavorazione", "hrefs": [], "values": ["idRichiesta=INPUT-9"]},
            {"text": "Risposta non classificata", "hrefs": [], "values": []},
        ]
    )

    assert [row.state for row in rows] == ["ready", "non_evadibile", "pending", "unknown"]
    assert rows[0].remote_id == "ABC-1"
    assert rows[0].download_href is not None
    assert rows[1].remote_id == "XYZ"
    assert rows[1].delete_href is not None
    assert rows[2].remote_id == "INPUT-9"


def test_extract_remote_id_supports_query_regex_and_missing_values() -> None:
    assert extract_remote_id(("/x?requestId=77",)) == "77"
    assert extract_remote_id(("onclick idRich='88'",)) == "88"
    assert extract_remote_id(("/x?unrelated=1",)) is None


def test_build_and_restore_correlation() -> None:
    request = type(
        "Request",
        (),
        {"id": "local-1", "subject_id": "ABC", "comune": None, "foglio": None, "particella": None, "subalterno": None},
    )()
    correlation = build_correlation(request, [_row("old")])

    assert correlation.local_request_id == "local-1"
    assert correlation.baseline_keys == frozenset({"old"})
    assert correlation.with_remote_id("remote").remote_id == "remote"
    assert correlation.with_remote_id(None).remote_id is None


def test_correlate_prefers_remote_id_and_rejects_duplicates() -> None:
    correlation = SisterRequestCorrelation("local", frozenset(), (), "remote-1")
    match = _row("remote-1", remote_id="remote-1")

    assert correlate_remote_row([match], correlation) is match
    with pytest.raises(SisterRequestCorrelationError, match="duplicato"):
        correlate_remote_row([match, match], correlation)

    fallback = _row("new")
    missing_remote = SisterRequestCorrelation("local", frozenset({"old"}), (), "missing")
    assert correlate_remote_row([_row("old"), fallback], missing_remote) is fallback


def test_correlate_uses_only_new_unique_row() -> None:
    correlation = SisterRequestCorrelation("local", frozenset({"old"}), ())
    new = _row("new")

    assert correlate_remote_row([_row("old")], correlation) is None
    assert correlate_remote_row([_row("old"), new], correlation) is new


def test_correlate_uses_expected_tokens_or_fails_closed() -> None:
    correlation = SisterRequestCorrelation("local", frozenset(), ("MARRUBIU", "24"))
    match = _row("one", text="Marrubiu foglio 24")
    unrelated = _row("two", text="Oristano foglio 5")

    assert correlate_remote_row([match, unrelated], correlation) is match
    with pytest.raises(SisterRequestCorrelationError, match="ambigua"):
        correlate_remote_row([unrelated, _row("three", text="Terralba")], correlation)

    without_tokens = SisterRequestCorrelation("local", frozenset(), ())
    with pytest.raises(SisterRequestCorrelationError, match="ambigua"):
        correlate_remote_row([match, unrelated], without_tokens)
