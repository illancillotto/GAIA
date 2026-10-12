import pytest

from app.modules.ruolo.services.posta_online_recipient_columns import recipient_address_columns


@pytest.mark.parametrize(
    ("cells", "expected"),
    [
        (["", "AR", "Mario", "Via Roma 1"], ("Via Roma 1", "", None)),
        (
            ["", "AR", "Mario", "Via Roma 1", "Raccomandata N.123"],
            ("Via Roma 1", "Raccomandata N.123", None),
        ),
        (
            ["", "AR", "Atzori", "TZRNTN43R09L122Q", "Via Baccelli 231 - 09098 Terralba"],
            ("Via Baccelli 231 - 09098 Terralba", "", "TZRNTN43R09L122Q"),
        ),
        (
            [
                "",
                "AR",
                "Atzori",
                " tzrntn43r09l122q ",
                "Via Baccelli 231 - 09098 Terralba",
                "Raccomandata N.123",
                "Restituita",
            ],
            (
                "Via Baccelli 231 - 09098 Terralba",
                "Raccomandata N.123 Restituita",
                "TZRNTN43R09L122Q",
            ),
        ),
        (
            ["", "AR", "Società", "12345678901", "Via Roma 1 - 09170 Oristano", "Info"],
            ("Via Roma 1 - 09170 Oristano", "Info", "12345678901"),
        ),
    ],
)
def test_supported_recipient_layouts(cells, expected):
    assert recipient_address_columns(cells) == expected


@pytest.mark.parametrize(
    "cells",
    [
        ["", "AR", "Atzori", "TZRNTN43R09L122Q"],
        ["", "AR", "Atzori", "TZRNTN43R09L122Q", "Raccomandata N.123"],
    ],
)
def test_fiscal_identifier_without_valid_address_is_rejected(cells):
    with pytest.raises(ValueError, match="layout incompleto"):
        recipient_address_columns(cells)


def test_html_parser_preserves_fiscal_identifier_and_reads_shifted_tracking():
    from app.modules.ruolo.tributi_repositories import _parse_posta_online_detail_html

    rows = _parse_posta_online_detail_html(
        "<table id='destinatario'><tr><th></th><th>Servizio</th><th>Destinatario</th>"
        "<th>Codice fiscale</th><th>Indirizzo</th><th>Info</th></tr>"
        "<tr><td></td><td>AR</td><td>Atzori Antonio</td><td>TZRNTN43R09L122Q</td>"
        "<td>Via Guido Baccelli 231 - 09098 Terralba (OR)</td>"
        "<td>Raccomandata N.619123456789</td></tr></table>",
        fallback_id="10802280",
        source_index=1,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["recipient_address"] == "Via Guido Baccelli 231 - 09098 Terralba (OR)"
    assert row["recipient_zipcode"] == "09098"
    assert row["tracking_number"] == "619123456789"
    assert row["raw"]["recipient_cf"] == "TZRNTN43R09L122Q"
    assert row["raw"]["cells"][3] == "TZRNTN43R09L122Q"
