from __future__ import annotations

import html
from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from app.modules.elaborazioni.capacitas.apps.incass.parsers import parse_incass_partitario_dialog


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "incass"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


def _normalized_lines(raw_html: str) -> list[str]:
    text = html.unescape(BeautifulSoup(raw_html, "html.parser").get_text("\n", strip=False)).replace("\xa0", " ")
    return [
        line
        for raw_line in text.splitlines()
        if (line := " ".join(raw_line.split()).strip())
    ]


def _decimal(value: str | None) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def test_incass_partitario_real_fixtures_current_behavior() -> None:
    laore_raw = _load_fixture("partitario_laore.html")
    serra_raw = _load_fixture("partitario_serra.html")
    lml_raw = _load_fixture("partitario_lml.html")

    laore = parse_incass_partitario_dialog(laore_raw, avviso="03122560927")
    serra = parse_incass_partitario_dialog(serra_raw, avviso="SRRCLD68P09G113D")
    lml = parse_incass_partitario_dialog(lml_raw, avviso="00587060955")

    assert laore is not None
    assert serra is not None
    assert lml is not None

    # Hardcoded from manual inspection of the three fixture dumps:
    # - laore contains 13 "Partita ..." blocks
    # - serra contains 1 "Partita ..." block
    # - lml contains 1 "Partita ..." block
    assert len(laore.partite) == 13
    assert len(serra.partite) == 1
    assert len(lml.partite) == 1

    # Hardcoded from manual inspection of normalized rows within each partita block.
    assert [len(partita.particelle) for partita in laore.partite] == [169, 2, 10, 16, 76, 4, 2, 10, 14, 8, 21, 75, 12]
    assert [len(partita.particelle) for partita in serra.partite] == [2]
    assert [len(partita.particelle) for partita in lml.partite] == [235]

    # Case 1: summary row with empty Irrig column.
    arborea = laore.partite[0]
    row_case_1 = next(parcel for parcel in arborea.particelle if parcel.foglio == "2" and parcel.particella == "19")
    assert row_case_1.distretto == "26"
    assert row_case_1.subalterno is None
    assert row_case_1.sup_catastale_are == "838570"
    assert row_case_1.sup_irrigata_ha is None
    assert row_case_1.importo_manut_euro == "3061.00"
    assert row_case_1.importo_irrig_euro is None
    assert row_case_1.importo_ist_euro == "2186.06"

    # Case 2: alphabetical subalterno in lml.
    # Manual inspection of partitario_lml.html shows 17 normalized rows with a non-numeric sub token.
    lml_lines = _normalized_lines(lml_raw)
    raw_non_numeric_sub_rows = [
        line
        for line in lml_lines
        if (tokens := line.split())
        and len(tokens) == 7
        and all(token.isdigit() for token in tokens[:3])
        and not tokens[3].replace(".", "").replace(",", ".").isdigit()
    ]
    assert len(raw_non_numeric_sub_rows) == 17
    parsed_non_numeric_sub_rows = [
        parcel
        for parcel in lml.partite[0].particelle
        if parcel.subalterno is not None and not parcel.subalterno.isdigit()
    ]
    assert len(parsed_non_numeric_sub_rows) == 17
    row_case_2 = next(parcel for parcel in parsed_non_numeric_sub_rows if parcel.foglio == "20" and parcel.particella == "12")
    assert row_case_2.distretto == "28"
    assert row_case_2.subalterno == "c"
    assert row_case_2.sup_catastale_are == "15"
    assert row_case_2.importo_manut_euro == "0.05"
    assert row_case_2.importo_ist_euro == "0.04"
    assert row_case_2.sup_irrigata_ha is None

    # Case 3: domanda irrigua row with coltura and a single trailing import.
    # In the fixed-width layout the single amount of a domanda row sits under
    # the Irrig. (0668) column, never under Manut.
    siamaggiore = next(partita for partita in laore.partite if partita.comune_nome == "SIAMAGGIORE")
    row_case_3 = next(parcel for parcel in siamaggiore.particelle if parcel.particella == "467")
    assert row_case_3.domanda_irrigua == "3431"
    assert row_case_3.distretto == "15"
    assert row_case_3.foglio == "9"
    assert row_case_3.sup_catastale_are == "5303"
    assert row_case_3.sup_irrigata_ha == "0.133"
    assert row_case_3.coltura == "FRUTTETO"
    assert row_case_3.importo_manut_euro is None
    assert row_case_3.importo_irrig_euro == "5.42"
    assert row_case_3.importo_ist_euro is None

    # Case 4: 0668 consumption block must not generate ghost parcels.
    assert [parcel.particella for parcel in serra.partite[0].particelle] == ["1458", "1462"]
    assert all(parcel.foglio != "2025" for parcel in serra.partite[0].particelle)
    assert all(parcel.particella not in {"671390", "678490", "680360", "680460"} for parcel in serra.partite[0].particelle)

    # Case 5: none of the three real fixtures contains a wrapped parcel row matching the current merge heuristic.
    for raw_html in (laore_raw, serra_raw, lml_raw):
        lines = _normalized_lines(raw_html)
        wrapped_candidates = []
        for idx in range(len(lines) - 1):
            current = lines[idx].split()
            following = lines[idx + 1].split()
            if len(current) == 6 and len(following) == 8 and following[1:5] == current[:4]:
                wrapped_candidates.append((lines[idx], lines[idx + 1]))
        assert wrapped_candidates == []


def test_incass_partitario_marrubiu_current_behavior() -> None:
    marrubiu_raw = _load_fixture("partitario_marrubiu.html")
    marrubiu_lines = _normalized_lines(marrubiu_raw)
    result = parse_incass_partitario_dialog(marrubiu_raw, avviso="80001090952")

    assert result is not None
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert partita.contribuente_cf == "80001090952"
    assert partita.importo_0648_euro == "15.981,87"
    assert partita.importo_0668_euro == "70,00"
    assert partita.importo_0985_euro == "11.413,68"

    # Manual inspection of normalized lines in partitario_marrubiu.html:
    # - candidate parcel rows total = 729
    # - shapes = 722 rows at 6 tokens, 6 rows at 7 tokens, 1 row at 8 tokens
    candidate_rows = []
    for idx, line in enumerate(marrubiu_lines):
        tokens = line.split()
        if idx < 10:
            continue
        if line.startswith("Legenda:"):
            continue
        if line.startswith("Consumi da contatore:") or line.startswith("Anno Domanda Distretto"):
            continue
        if line.startswith("2025 "):
            continue
        if tokens and tokens[0].isdigit() and len(tokens) in {6, 7, 8}:
            candidate_rows.append((idx, line, tokens))
    assert len(candidate_rows) == 729
    assert sum(1 for _, _, tokens in candidate_rows if len(tokens) == 6) == 722
    assert sum(1 for _, _, tokens in candidate_rows if len(tokens) == 7) == 6
    assert sum(1 for _, _, tokens in candidate_rows if len(tokens) == 8) == 1

    # All 729 candidate rows are emitted, including the textual particella "acque".
    assert len(partita.particelle) == 729

    # Case 1, normalized line 11 by manual inspection:
    # "31 2 62 60 0,22 0,16"
    row_case_1 = next(parcel for parcel in partita.particelle if parcel.foglio == "2" and parcel.particella == "62")
    assert row_case_1.distretto == "31"
    assert row_case_1.subalterno is None
    assert row_case_1.sup_catastale_are == "60"
    assert row_case_1.importo_manut_euro == "0.22"
    assert row_case_1.importo_irrig_euro is None
    assert row_case_1.importo_ist_euro == "0.16"

    # Case 2, normalized lines 323 and 561 by manual inspection.
    parsed_non_numeric_sub_rows = [
        parcel
        for parcel in partita.particelle
        if parcel.subalterno is not None and not parcel.subalterno.isdigit()
    ]
    assert len(parsed_non_numeric_sub_rows) == 6

    row_case_2a = next(parcel for parcel in parsed_non_numeric_sub_rows if parcel.foglio == "17" and parcel.particella == "193")
    assert row_case_2a.distretto == "34"
    assert row_case_2a.subalterno == "a"
    assert row_case_2a.sup_catastale_are == "23500"
    assert row_case_2a.importo_manut_euro == "85.78"
    assert row_case_2a.importo_ist_euro == "61.26"

    row_case_2b = next(parcel for parcel in parsed_non_numeric_sub_rows if parcel.foglio == "28" and parcel.particella == "110")
    assert row_case_2b.distretto == "34"
    assert row_case_2b.subalterno == "c"
    assert row_case_2b.sup_catastale_are == "213"
    assert row_case_2b.importo_manut_euro == "0.78"
    assert row_case_2b.importo_ist_euro == "0.56"

    # Case 3, normalized line 80 by manual inspection:
    # "31 6 acque 650 2,37 1,69" — the textual particella is preserved as-is.
    acque_rows = [parcel for parcel in partita.particelle if parcel.particella == "acque"]
    assert len(acque_rows) == 1
    assert acque_rows[0].foglio == "6"
    assert acque_rows[0].sup_catastale_are == "650"
    assert acque_rows[0].importo_manut_euro == "2.37"
    assert acque_rows[0].importo_ist_euro == "1.69"
    assert all(not (parcel.foglio == "6" and parcel.particella == "650") for parcel in partita.particelle)

    # Case 4, normalized line 10 by manual inspection:
    # "7245 31 1 837 16.600 5.000 PRATO-PA 44,82"
    # The single amount of a domanda row belongs to the Irrig. (0668) column.
    row_case_4 = next(parcel for parcel in partita.particelle if parcel.foglio == "1" and parcel.particella == "837")
    assert row_case_4.domanda_irrigua == "7245"
    assert row_case_4.distretto == "31"
    assert row_case_4.sup_catastale_are == "16600"
    assert row_case_4.sup_irrigata_ha == "0.5"
    assert row_case_4.coltura == "PRATO-PA"
    assert row_case_4.importo_manut_euro is None
    assert row_case_4.importo_irrig_euro == "44.82"
    assert row_case_4.importo_ist_euro is None


def test_incass_partitario_marrubiu_reconciles_0648_against_header_total() -> None:
    raw = _load_fixture("partitario_marrubiu.html")
    result = parse_incass_partitario_dialog(raw, avviso="80001090952")

    assert result is not None
    partita = result.partite[0]

    # Manual header inspection of partitario_marrubiu.html:
    # normalized line 6 => 0648 = 15.981,87 euro
    total_manut = sum(_decimal(parcel.importo_manut_euro) for parcel in partita.particelle)
    assert abs(total_manut - Decimal("15981.87")) <= Decimal("0.50")


def test_incass_partitario_marrubiu_reconciles_0985_against_header_total() -> None:
    raw = _load_fixture("partitario_marrubiu.html")
    result = parse_incass_partitario_dialog(raw, avviso="80001090952")

    assert result is not None
    partita = result.partite[0]

    # Manual header inspection of partitario_marrubiu.html:
    # normalized line 8 => 0985 = 11.413,68 euro
    total_ist = sum(_decimal(parcel.importo_ist_euro) for parcel in partita.particelle)
    assert abs(total_ist - Decimal("11413.68")) <= Decimal("0.50")


def test_incass_partitario_marrubiu_0668_particelle_sum_stays_below_flat_minimum() -> None:
    raw = _load_fixture("partitario_marrubiu.html")
    result = parse_incass_partitario_dialog(raw, avviso="80001090952")

    assert result is not None
    partita = result.partite[0]

    # The 0668 header (70,00 euro) is the flat "Contributo utenza" minimum, so it
    # does NOT reconcile with the per-parcel Irrig. amounts. The only domanda row
    # in this fixture ("7245 31 1 837 ... PRATO-PA 44,82") carries 44,82 euro.
    assert partita.importo_0668_euro == "70,00"
    total_irrig = sum(_decimal(parcel.importo_irrig_euro) for parcel in partita.particelle)
    assert total_irrig == Decimal("44.82")
