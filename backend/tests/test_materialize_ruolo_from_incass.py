from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/materialize_ruolo_from_incass.py"
_SPEC = importlib.util.spec_from_file_location("materialize_ruolo_from_incass_under_test", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_to_decimal_preserves_parser_decimal_points_and_parses_italian_amounts() -> None:
    assert _MODULE._to_decimal(None) is None
    assert _MODULE._to_decimal("") is None
    assert _MODULE._to_decimal("bad") is None
    assert _MODULE._to_decimal("18.4994") == Decimal("18.4994")
    assert _MODULE._to_decimal("0.9208") == Decimal("0.9208")
    assert _MODULE._to_decimal("184994") == Decimal("184994")
    assert _MODULE._to_decimal("675,28") == Decimal("675.28")
    assert _MODULE._to_decimal("1.808,94") == Decimal("1808.94")
