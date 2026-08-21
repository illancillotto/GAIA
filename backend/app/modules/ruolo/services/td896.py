from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TD896_DOCUMENT_CODE = "896"

_CUSTOMER_BASE_LENGTH = 16
_CUSTOMER_CODE_LENGTH = 18
_POSTAL_ACCOUNT_LENGTH = 12
_BARCODE_PAYLOAD_LENGTH = 50
_DATA_CODEWORD_CAPACITY = 49
_ERROR_CODEWORD_COUNT = 28
_ERROR_CORRECTION_FACTORS = (
    211,
    231,
    43,
    97,
    71,
    96,
    103,
    174,
    37,
    151,
    170,
    53,
    75,
    34,
    249,
    121,
    17,
    138,
    110,
    213,
    141,
    136,
    120,
    151,
    233,
    168,
    93,
    255,
)
_DATA_ROWS = 14
_DATA_COLUMNS = 44
_REGION_DATA_COLUMNS = 22
_SYMBOL_ROWS = 16
_SYMBOL_COLUMNS = 48
_QUIET_ZONE = 2
_NON_DIGIT_RE = re.compile(r"\D+")
_AMOUNT_CODE_RE = re.compile(r"\d{8}\+\d{2}")


@dataclass(frozen=True)
class Td896PaymentCode:
    customer_code: str
    amount_code: str
    postal_account_code: str
    barcode_payload: str
    codeline: str


def build_td896_payment_code(
    *,
    notice_number: str,
    amount: str | Decimal,
    postal_account: str,
) -> Td896PaymentCode:
    customer_code = td896_customer_code(notice_number)
    amount_code = td896_amount_code(amount)
    postal_account_code = _normalize_postal_account(postal_account)
    barcode_payload = build_td896_barcode_payload(
        customer_code,
        amount_code,
        postal_account_code,
    )
    return Td896PaymentCode(
        customer_code=customer_code,
        amount_code=amount_code,
        postal_account_code=postal_account_code,
        barcode_payload=barcode_payload,
        codeline=(
            f"<{customer_code}> "
            f"{amount_code}> "
            f"{postal_account_code}< "
            f"{TD896_DOCUMENT_CODE}>"
        ),
    )


def td896_customer_code(notice_number: str) -> str:
    digits = _NON_DIGIT_RE.sub("", notice_number)
    if not digits:
        raise ValueError("Il numero avviso deve contenere almeno una cifra")
    if len(digits) > _CUSTOMER_BASE_LENGTH - 1:
        raise ValueError("Il numero avviso non puo superare 15 cifre per il TD 896")

    base_code = f"{digits}9".zfill(_CUSTOMER_BASE_LENGTH)
    return f"{base_code}{int(base_code) % 93:02d}"


def td896_amount_code(amount: str | Decimal) -> str:
    decimal_amount = _parse_amount(amount)
    if decimal_amount < 0:
        raise ValueError("L'importo TD 896 non puo essere negativo")

    normalized = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cents_total = int(normalized * 100)
    if cents_total > 9_999_999_999:
        raise ValueError("L'importo TD 896 supera le otto cifre intere consentite")

    integer_part, cents = divmod(cents_total, 100)
    return f"{integer_part:08d}+{cents:02d}"


def build_td896_barcode_payload(
    customer_code: str,
    amount_code: str,
    postal_account_code: str,
) -> str:
    _validate_customer_code(customer_code)
    if not _AMOUNT_CODE_RE.fullmatch(amount_code):
        raise ValueError("L'importo TD 896 deve avere il formato 00000000+00")

    normalized_account = _normalize_postal_account(postal_account_code)
    amount_digits = amount_code.replace("+", "")
    payload = (
        f"18{customer_code}"
        f"12{normalized_account}"
        f"10{amount_digits}"
        f"3{TD896_DOCUMENT_CODE}"
    )
    if len(payload) != _BARCODE_PAYLOAD_LENGTH:
        raise ValueError("Il payload ottico TD 896 deve contenere 50 cifre")
    return payload


def td896_datamatrix_svg(value: str) -> str:
    symbol = td896_datamatrix(value)
    rects = [
        f'<rect x="{column + _QUIET_ZONE}" y="{row + _QUIET_ZONE}" width="1" height="1"/>'
        for row, modules in enumerate(symbol)
        for column, filled in enumerate(modules)
        if filled
    ]
    width = _SYMBOL_COLUMNS + (_QUIET_ZONE * 2)
    height = _SYMBOL_ROWS + (_QUIET_ZONE * 2)
    return (
        '<svg class="bollettino-datamatrix" role="img" '
        'aria-label="Data Matrix TD 896" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        'shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{width}" height="{height}" fill="#fff"/>'
        '<g fill="#111">'
        f'{"".join(rects)}'
        '</g></svg>'
    )


def td896_datamatrix(value: str) -> tuple[tuple[bool, ...], ...]:
    if len(value) != _BARCODE_PAYLOAD_LENGTH or not value.isdigit():
        raise ValueError("Il Data Matrix TD 896 richiede il payload numerico di 50 cifre")

    data_codewords = _encode_numeric_data(value)
    codewords = data_codewords + _reed_solomon_error_codewords(data_codewords)
    placement = _DataMatrixPlacement(codewords)
    return _add_finder_patterns(placement.place())


def _parse_amount(amount: str | Decimal) -> Decimal:
    if isinstance(amount, Decimal):
        decimal_amount = amount
    else:
        normalized = amount.strip().upper().replace("EUR", "").replace("€", "").replace(" ", "")
        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        try:
            decimal_amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError("L'importo TD 896 non e un valore decimale valido") from exc
    if not decimal_amount.is_finite():
        raise ValueError("L'importo TD 896 deve essere finito")
    return decimal_amount


def _normalize_postal_account(postal_account: str) -> str:
    digits = postal_account.replace(" ", "").replace(".", "")
    if not digits.isdigit() or len(digits) > _POSTAL_ACCOUNT_LENGTH:
        raise ValueError("Il conto corrente TD 896 deve contenere al massimo 12 cifre")
    return digits.zfill(_POSTAL_ACCOUNT_LENGTH)


def _validate_customer_code(customer_code: str) -> None:
    if len(customer_code) != _CUSTOMER_CODE_LENGTH or not customer_code.isdigit():
        raise ValueError("Il codice cliente TD 896 deve contenere 18 cifre")
    if int(customer_code[:_CUSTOMER_BASE_LENGTH]) % 93 != int(customer_code[-2:]):
        raise ValueError("Il controcodice modulo 93 del codice cliente TD 896 non e valido")


def _encode_numeric_data(value: str) -> list[int]:
    codewords = [int(value[index : index + 2]) + 130 for index in range(0, len(value), 2)]
    codewords.append(129)
    while len(codewords) < _DATA_CODEWORD_CAPACITY:
        position = len(codewords) + 1
        randomized = 129 + (((149 * position) % 253) + 1)
        codewords.append(randomized if randomized <= 254 else randomized - 254)
    return codewords


def _reed_solomon_error_codewords(data_codewords: list[int]) -> list[int]:
    exponent, logarithm = _galois_tables()
    error_codewords = [0] * _ERROR_CODEWORD_COUNT
    for codeword in data_codewords:
        feedback = error_codewords[-1] ^ codeword
        for index in range(_ERROR_CODEWORD_COUNT - 1, 0, -1):
            product = _galois_multiply(
                feedback,
                _ERROR_CORRECTION_FACTORS[index],
                exponent,
                logarithm,
            )
            error_codewords[index] = error_codewords[index - 1] ^ product
        error_codewords[0] = _galois_multiply(
            feedback,
            _ERROR_CORRECTION_FACTORS[0],
            exponent,
            logarithm,
        )
    return list(reversed(error_codewords))


def _galois_tables() -> tuple[list[int], list[int]]:
    exponent = [0] * 255
    logarithm = [0] * 256
    value = 1
    for power in range(255):
        exponent[power] = value
        logarithm[value] = power
        value <<= 1
        if value & 0x100:
            value ^= 0x12D
    return exponent, logarithm


def _galois_multiply(
    left: int,
    right: int,
    exponent: list[int],
    logarithm: list[int],
) -> int:
    if left == 0 or right == 0:
        return 0
    return exponent[(logarithm[left] + logarithm[right]) % 255]


class _DataMatrixPlacement:
    def __init__(self, codewords: list[int]) -> None:
        self._codewords = codewords
        self._modules = [-1] * (_DATA_ROWS * _DATA_COLUMNS)

    def place(self) -> tuple[tuple[bool, ...], ...]:
        row = 4
        column = 0
        codeword_index = 0
        while row < _DATA_ROWS or column < _DATA_COLUMNS:
            if row == _DATA_ROWS - 2 and column == 0:
                self._corner_three(codeword_index)
                codeword_index += 1
            row, column, codeword_index = self._sweep_upward(row, column, codeword_index)
            row, column, codeword_index = self._sweep_downward(row, column, codeword_index)

        return tuple(
            tuple(self._modules[(row * _DATA_COLUMNS) + column] == 1 for column in range(_DATA_COLUMNS))
            for row in range(_DATA_ROWS)
        )

    def _sweep_upward(self, row: int, column: int, codeword_index: int) -> tuple[int, int, int]:
        while row >= 0 and column < _DATA_COLUMNS:
            if row < _DATA_ROWS and column >= 0 and not self._has_module(row, column):
                self._utah(row, column, codeword_index)
                codeword_index += 1
            row -= 2
            column += 2
        return row + 1, column + 3, codeword_index

    def _sweep_downward(self, row: int, column: int, codeword_index: int) -> tuple[int, int, int]:
        while row < _DATA_ROWS and column >= 0:
            if row >= 0 and column < _DATA_COLUMNS and not self._has_module(row, column):
                self._utah(row, column, codeword_index)
                codeword_index += 1
            row += 2
            column -= 2
        return row + 3, column + 1, codeword_index

    def _utah(self, row: int, column: int, codeword_index: int) -> None:
        self._place_bit(row - 2, column - 2, codeword_index, 1)
        self._place_bit(row - 2, column - 1, codeword_index, 2)
        self._place_bit(row - 1, column - 2, codeword_index, 3)
        self._place_bit(row - 1, column - 1, codeword_index, 4)
        self._place_bit(row - 1, column, codeword_index, 5)
        self._place_bit(row, column - 2, codeword_index, 6)
        self._place_bit(row, column - 1, codeword_index, 7)
        self._place_bit(row, column, codeword_index, 8)

    def _corner_three(self, codeword_index: int) -> None:
        self._place_bit(_DATA_ROWS - 3, 0, codeword_index, 1)
        self._place_bit(_DATA_ROWS - 2, 0, codeword_index, 2)
        self._place_bit(_DATA_ROWS - 1, 0, codeword_index, 3)
        self._place_bit(0, _DATA_COLUMNS - 2, codeword_index, 4)
        self._place_bit(0, _DATA_COLUMNS - 1, codeword_index, 5)
        self._place_bit(1, _DATA_COLUMNS - 1, codeword_index, 6)
        self._place_bit(2, _DATA_COLUMNS - 1, codeword_index, 7)
        self._place_bit(3, _DATA_COLUMNS - 1, codeword_index, 8)

    def _place_bit(self, row: int, column: int, codeword_index: int, bit: int) -> None:
        if row < 0:
            row += _DATA_ROWS
            column += 4 - ((_DATA_ROWS + 4) % 8)
        if column < 0:
            column += _DATA_COLUMNS
            row += 4 - ((_DATA_COLUMNS + 4) % 8)
        value = self._codewords[codeword_index] & (1 << (8 - bit))
        self._set_module(row, column, bool(value))

    def _has_module(self, row: int, column: int) -> bool:
        return self._modules[(row * _DATA_COLUMNS) + column] >= 0

    def _set_module(self, row: int, column: int, value: bool) -> None:
        self._modules[(row * _DATA_COLUMNS) + column] = int(value)


def _add_finder_patterns(
    data_modules: tuple[tuple[bool, ...], ...],
) -> tuple[tuple[bool, ...], ...]:
    symbol = [[False] * _SYMBOL_COLUMNS for _ in range(_SYMBOL_ROWS)]
    for column in range(_SYMBOL_COLUMNS):
        symbol[0][column] = column % 2 == 0
        symbol[-1][column] = True

    for data_row, modules in enumerate(data_modules):
        symbol_row = data_row + 1
        for region in range(2):
            region_start = region * (_REGION_DATA_COLUMNS + 2)
            symbol[symbol_row][region_start] = True
            symbol[symbol_row][region_start + _REGION_DATA_COLUMNS + 1] = data_row % 2 == 0
            for region_column in range(_REGION_DATA_COLUMNS):
                data_column = (region * _REGION_DATA_COLUMNS) + region_column
                symbol[symbol_row][region_start + region_column + 1] = modules[data_column]
    return tuple(tuple(row) for row in symbol)
