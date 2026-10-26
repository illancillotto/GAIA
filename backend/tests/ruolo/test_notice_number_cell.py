from app.modules.ruolo.services.notice_number_cell import notice_numbers_html


def test_each_avviso_number_gets_its_own_line() -> None:
    assert notice_numbers_html("020210000743640, 020217801062586") == (
        "020210000743640<br>020217801062586"
    )
    assert notice_numbers_html("CNC-<2025>") == "CNC-&lt;2025&gt;"
    assert notice_numbers_html("-") == "-"
