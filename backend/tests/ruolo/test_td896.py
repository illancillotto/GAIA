from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest
from app.modules.ruolo.services import td896

PAYLOAD_120_67 = "18025257650095110900120010072148261000000120673896"


def test_build_td896_payment_code_contract() -> None:
    payment_code = td896.build_td896_payment_code(
        notice_number="025257650095110",
        amount="€ 120,67 EUR",
        postal_account="1007 214826",
    )

    assert payment_code.customer_code == "025257650095110900"
    assert int(payment_code.customer_code[:16]) % 93 == int(payment_code.customer_code[-2:])
    assert payment_code.amount_code == "00000120+67"
    assert payment_code.postal_account_code == "001007214826"
    assert payment_code.barcode_payload == PAYLOAD_120_67
    assert payment_code.codeline == "<025257650095110900> 00000120+67> 001007214826< 896>"


def test_td896_customer_code_is_unique_validated_and_notice_derived() -> None:
    assert td896.td896_customer_code("12026242500001") == "012026242500001985"
    assert td896.td896_customer_code("AVV-1") == "000000000000001919"

    with pytest.raises(ValueError, match="almeno una cifra"):
        td896.td896_customer_code("AVV")
    with pytest.raises(ValueError, match="superare 15 cifre"):
        td896.td896_customer_code("1234567890123456")


def test_td896_amount_code_formats_and_limits() -> None:
    assert td896.td896_amount_code(Decimal(1)) == "00000001+00"
    assert td896.td896_amount_code("1.005") == "00000001+01"
    assert td896.td896_amount_code("1.234,56") == "00001234+56"
    assert td896.td896_amount_code("99999999,99") == "99999999+99"

    with pytest.raises(ValueError, match="valore decimale valido"):
        td896.td896_amount_code("non disponibile")
    with pytest.raises(ValueError, match="deve essere finito"):
        td896.td896_amount_code(Decimal("NaN"))
    with pytest.raises(ValueError, match="non puo essere negativo"):
        td896.td896_amount_code("-0,01")
    with pytest.raises(ValueError, match="otto cifre intere"):
        td896.td896_amount_code("100000000,00")


def test_td896_barcode_payload_rejects_invalid_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="18 cifre"):
        td896.build_td896_barcode_payload("123", "00000001+00", "1007214826")
    with pytest.raises(ValueError, match="modulo 93"):
        td896.build_td896_barcode_payload("025257650095110901", "00000001+00", "1007214826")
    with pytest.raises(ValueError, match=r"formato 00000000\+00"):
        td896.build_td896_barcode_payload("025257650095110900", "1,00", "1007214826")
    with pytest.raises(ValueError, match="al massimo 12 cifre"):
        td896.build_td896_barcode_payload("025257650095110900", "00000001+00", "conto")
    with pytest.raises(ValueError, match="al massimo 12 cifre"):
        td896.build_td896_barcode_payload("025257650095110900", "00000001+00", "conto123")
    with pytest.raises(ValueError, match="al massimo 12 cifre"):
        td896.build_td896_barcode_payload("025257650095110900", "00000001+00", "1234567890123")

    monkeypatch.setattr(td896, "_BARCODE_PAYLOAD_LENGTH", 49)
    with pytest.raises(ValueError, match="50 cifre"):
        td896.build_td896_barcode_payload("025257650095110900", "00000001+00", "1007214826")


def test_td896_datamatrix_ecc200_16_by_48_contract() -> None:
    symbol = td896.td896_datamatrix(PAYLOAD_120_67)
    bit_string = "".join("1" if module else "0" for row in symbol for module in row)

    assert len(symbol) == 16
    assert {len(row) for row in symbol} == {48}
    assert hashlib.sha256(bit_string.encode()).hexdigest() == (
        "c43e7a3089aa387905f874c9b0aa33aeaec8bdc415345592530ceb621f931a06"
    )
    assert symbol[0] == tuple(column % 2 == 0 for column in range(48))
    assert all(symbol[-1])
    assert all(symbol[row][0] and symbol[row][24] for row in range(1, 15))
    assert all(symbol[row][23] == (row % 2 == 1) for row in range(1, 15))
    assert all(symbol[row][47] == (row % 2 == 1) for row in range(1, 15))

    svg = td896.td896_datamatrix_svg(PAYLOAD_120_67)
    assert svg.startswith('<svg class="bollettino-datamatrix"')
    assert 'aria-label="Data Matrix TD 896"' in svg
    assert 'viewBox="0 0 52 20"' in svg
    assert 'shape-rendering="crispEdges"' in svg

    with pytest.raises(ValueError, match="50 cifre"):
        td896.td896_datamatrix("123")
    with pytest.raises(ValueError, match="50 cifre"):
        td896.td896_datamatrix("X" * 50)


def test_galois_zero_product() -> None:
    exponent, logarithm = td896._galois_tables()
    assert td896._galois_multiply(0, 42, exponent, logarithm) == 0
    assert td896._galois_multiply(42, 0, exponent, logarithm) == 0
