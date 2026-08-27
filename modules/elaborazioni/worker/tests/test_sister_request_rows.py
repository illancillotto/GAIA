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


def _row(
    key: str,
    *,
    remote_id: str | None = None,
    text: str = "",
    state: str = "pending",
    download_href: str | None = None,
) -> SisterRemoteRequestRow:
    return SisterRemoteRequestRow(0, key, remote_id, state, text, (), download_href, None)


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
    assert extract_remote_id(("/x?unrelated=1&idRichiesta=77",)) == "77"
    assert extract_remote_id(("onclick idRich='88'",)) == "88"
    assert extract_remote_id(("/x?unrelated=1", "onclick idRich='88'")) == "88"
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

    missing_remote = SisterRequestCorrelation("local", frozenset({"old"}), (), "missing")
    assert correlate_remote_row([_row("old"), _row("new")], missing_remote) is None


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


def test_correlate_selects_first_of_equivalent_ready_duplicates() -> None:
    correlation = SisterRequestCorrelation("local", frozenset(), ("MARRUBIU", "33", "815"))
    newest = _row(
        "newest",
        text="26/08/2026 23:36:54 Visura Fg. 33 Part. 815 di Marrubiu",
        download_href="/download/newest",
    )
    oldest = _row(
        "oldest",
        text="26/08/2026 23:36:39 Visura Fg. 33 Part. 815 di Marrubiu",
        download_href="/download/oldest",
    )

    assert correlate_remote_row([oldest, newest], correlation) is newest


def test_correlate_keeps_first_equivalent_duplicate_without_timestamps() -> None:
    correlation = SisterRequestCorrelation("local", frozenset(), ("MARRUBIU", "33", "815"))
    first = _row("first", text="Visura Fg. 33 Part. 815 di Marrubiu", download_href="/first")
    second = _row("second", text="Visura Fg. 33 Part. 815 di Marrubiu", download_href="/second")

    assert correlate_remote_row([first, second], correlation) is first


@pytest.mark.parametrize(
    "rows",
    [
        [
            _row("one", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/one"),
            _row("two", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/two"),
            _row("three", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/three"),
            _row("four", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/four"),
        ],
        [
            _row("one", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/one"),
            _row("two", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready"),
        ],
        [
            _row("one", text="Visura Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/one"),
            _row("two", text="Visura analitica Fg. 33 Part. 815 di Marrubiu", state="ready", download_href="/two"),
        ],
    ],
)
def test_correlate_rejects_non_equivalent_duplicate_candidates(rows: list[SisterRemoteRequestRow]) -> None:
    correlation = SisterRequestCorrelation("local", frozenset(), ("MARRUBIU", "33", "815"))

    with pytest.raises(SisterRequestCorrelationError, match="ambigua"):
        correlate_remote_row(rows, correlation)


def test_real_sister_completed_rows_preserve_remote_identity() -> None:
    rows = parse_remote_rows(
        [
            {
                "text": "26/08/2026 23:36:54\nVISURA FG. 33 PART. 815 DI MARRUBIU\nPDF",
                "hrefs": [
                    "/Servizi/ConsultazioneRichieste.do?metodo=apri&idRichiesta=2043007920&servizio=TIS",
                    "/Servizi/ConsultazioneRichieste.do?metodo=salva&idRichiesta=2043007920&servizio=TIS",
                ],
                "values": ["idElemento=2043007920"],
            },
            {
                "text": "26/08/2026 23:36:39\nVISURA FG. 33 PART. 815 DI MARRUBIU\nPDF",
                "hrefs": [
                    "/Servizi/ConsultazioneRichieste.do?metodo=apri&idRichiesta=2043007901&servizio=TIS",
                    "/Servizi/ConsultazioneRichieste.do?metodo=salva&idRichiesta=2043007901&servizio=TIS",
                ],
                "values": ["idElemento=2043007901"],
            },
        ]
    )
    correlation = SisterRequestCorrelation("local", frozenset(), ("MARRUBIU", "33", "815"), "2043007920")

    assert [row.remote_id for row in rows] == ["2043007920", "2043007901"]
    assert correlate_remote_row(rows, correlation) is rows[0]
