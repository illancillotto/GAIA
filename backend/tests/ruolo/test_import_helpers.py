from decimal import Decimal

from app.modules.ruolo.services.import_service import _merge_particella_rows, _normalize_comune_codice
from app.modules.ruolo.services.parser import ParsedParticella


def test_normalize_comune_codice_handles_composite_sister_value() -> None:
    assert _normalize_comune_codice("F272#MOGORO#0#0") == "F272"


def test_normalize_comune_codice_keeps_short_plain_code() -> None:
    assert _normalize_comune_codice("A357") == "A357"


def test_merge_particella_rows_combines_duplicate_keys() -> None:
    rows = [
        ParsedParticella(
            domanda_irrigua=None,
            distretto="4",
            foglio="9",
            particella="877",
            subalterno="I",
            sup_catastale_are=Decimal("805"),
            sup_catastale_ha=Decimal("8.05"),
            sup_irrigata_ha=None,
            coltura=None,
            importo_manut=Decimal("2.94"),
            importo_irrig=None,
            importo_ist=Decimal("2.10"),
        ),
        ParsedParticella(
            domanda_irrigua="1111",
            distretto="4",
            foglio="9",
            particella="877",
            subalterno="I",
            sup_catastale_are=Decimal("834"),
            sup_catastale_ha=Decimal("8.34"),
            sup_irrigata_ha=Decimal("8.34"),
            coltura="FRUTTETO",
            importo_manut=None,
            importo_irrig=Decimal("3.40"),
            importo_ist=None,
        ),
    ]

    merged = _merge_particella_rows(rows)
    assert len(merged) == 1
    item = merged[0]
    assert item.domanda_irrigua == "1111"
    assert item.coltura == "FRUTTETO"
    assert item.sup_irrigata_ha == Decimal("8.34")
    assert item.importo_manut == Decimal("2.94")
    assert item.importo_irrig == Decimal("3.40")
