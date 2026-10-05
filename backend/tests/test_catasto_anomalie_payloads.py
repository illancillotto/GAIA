from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.catasto_phase1 import CatAnomalia, CatUtenzaIrrigua
from app.modules.catasto.services.anomalie_payloads import build_anomalia_payload


def test_build_anomalia_payload_enriches_dir_surface_multiple_domande() -> None:
    anomalia = CatAnomalia(
        tipo="DIR-01-superficie_coltura_superata",
        dati_json={
            "sup_irrigata_mq": "120.00",
            "superficie_riferimento_mq": "100.00",
            "domanda_particella_ids": ["row-1", "row-2", "row-2"],
            "domanda_ids": ["dom-1", "dom-1", "dom-2"],
            "domande": [
                {"id": "dom-1", "numero": "10", "cco": "000000001"},
                {"id": "dom-1", "numero": "10", "cco": "000000001"},
                {"id": "dom-2", "numero": "11", "cco": "000000002"},
            ],
        },
    )

    payload = build_anomalia_payload(anomalia)

    assert payload == {
        "sup_irrigata_mq": "120.00",
        "superficie_riferimento_mq": "100.00",
        "eccedenza_mq": "20.00",
        "domanda_particella_ids": ["row-1", "row-2"],
        "righe_domanda_count": 2,
        "domanda_ids": ["dom-1", "dom-2"],
        "domande_distinte_count": 2,
        "domande": [
            {"id": "dom-1", "numero": "10", "cco": "000000001"},
            {"id": "dom-2", "numero": "11", "cco": "000000002"},
        ],
        "causa_superficie": "piu_domande",
    }


def test_build_anomalia_payload_enriches_dir_surface_same_domanda_with_sparse_values() -> None:
    anomalia = CatAnomalia(
        tipo="DIR-02-superficie_totale_da_verificare",
        dati_json={
            "sup_irrigata_mq": "non-numerico",
            "superficie_riferimento_mq": "100.00",
            "domanda_particella_ids": ["row-1", "row-2"],
            "domande": [
                {"id": "dom-1", "numero": "10"},
                {"id": "dom-1", "numero": "10"},
                "valore-non-mappato",
            ],
        },
    )

    payload = build_anomalia_payload(anomalia)

    assert payload == {
        "sup_irrigata_mq": "non-numerico",
        "superficie_riferimento_mq": "100.00",
        "domanda_particella_ids": ["row-1", "row-2"],
        "righe_domanda_count": 2,
        "domande": [{"id": "dom-1", "numero": "10"}],
        "domanda_ids": ["dom-1"],
        "domande_distinte_count": 1,
        "causa_superficie": "piu_righe_stessa_domanda",
    }


def test_build_anomalia_payload_enriches_dir_surface_single_row_without_domande() -> None:
    anomalia = CatAnomalia(
        tipo="DIR-01-superficie_coltura_superata",
        dati_json={
            "sup_irrigata_mq": Decimal("37.626"),
            "superficie_riferimento_mq": Decimal("35.936"),
            "domanda_particella_ids": ["row-1"],
            "domande": "non-lista",
        },
    )

    payload = build_anomalia_payload(anomalia)

    assert payload == {
        "sup_irrigata_mq": Decimal("37.626"),
        "superficie_riferimento_mq": Decimal("35.936"),
        "eccedenza_mq": "1.69",
        "domanda_particella_ids": ["row-1"],
        "righe_domanda_count": 1,
        "domande": "non-lista",
        "causa_superficie": "riga_singola",
    }


def test_build_anomalia_payload_preserves_incomplete_dir_surface_payload() -> None:
    anomalia = CatAnomalia(
        tipo="DIR-01-superficie_coltura_superata",
        dati_json={"sup_irrigata_mq": None},
    )

    assert build_anomalia_payload(anomalia) == {"sup_irrigata_mq": None}


def test_build_anomalia_payload_preserves_generic_payloads_and_val06_enrichment() -> None:
    assert build_anomalia_payload(CatAnomalia(tipo="VAL-01-generica", dati_json=None)) is None
    generic_payload = build_anomalia_payload(CatAnomalia(tipo="VAL-01-generica", dati_json={"campo": "valore"}))
    assert generic_payload == {
        "campo": "valore"
    }
    assert build_anomalia_payload(CatAnomalia(tipo="VAL-06-imponibile", dati_json={"base": True})) == {
        "base": True
    }
    assert (
        build_anomalia_payload(CatAnomalia(tipo="VAL-06-imponibile", dati_json={}), CatUtenzaIrrigua()) is None
    )

    utenza = CatUtenzaIrrigua(
        sup_irrigabile_mq=Decimal("10.00"),
        sup_catastale_mq=Decimal("12.00"),
        ind_spese_fisse=Decimal("1.23456"),
        imponibile_sf=Decimal("12.35"),
    )

    payload = build_anomalia_payload(
        CatAnomalia(tipo="VAL-06-imponibile", dati_json={"base": True}),
        utenza,
    )

    assert payload == {
        "base": True,
        "sup_irrigabile_mq": 10.0,
        "sup_catastale_mq": 12.0,
        "ind_spese_fisse": 1.2346,
        "imponibile_registrato": 12.35,
        "atteso": 12.35,
        "atteso_catastale": 14.82,
        "delta_vs_catastale": 2.47,
        "coincide_con_catastale": False,
        "delta": 0.0,
    }


def test_build_anomalia_payload_calculates_expected_without_registered_amount() -> None:
    anomalia = CatAnomalia(tipo="VAL-06-imponibile", dati_json={"base": True})
    utenza = CatUtenzaIrrigua(
        sup_irrigabile_mq=Decimal("10.00"),
        sup_catastale_mq=Decimal("12.00"),
        ind_spese_fisse=Decimal("1.23456"),
        imponibile_sf=None,
    )

    payload = build_anomalia_payload(anomalia, utenza)

    assert payload == {
        "base": True,
        "sup_irrigabile_mq": 10.0,
        "sup_catastale_mq": 12.0,
        "ind_spese_fisse": 1.2346,
        "atteso": 12.35,
        "atteso_catastale": 14.82,
    }
    assert anomalia.dati_json == {"base": True}
    assert utenza.imponibile_sf is None


def test_build_anomalia_payload_preserves_zero_values_and_field_order() -> None:
    original_payload = {"imponibile_registrato": 99, "base": True}
    anomalia = CatAnomalia(tipo="VAL-06-imponibile", dati_json=original_payload)
    utenza = CatUtenzaIrrigua(
        sup_irrigabile_mq=Decimal("0"),
        sup_catastale_mq=Decimal("0"),
        ind_spese_fisse=Decimal("0"),
        imponibile_sf=Decimal("0"),
    )

    payload = build_anomalia_payload(anomalia, utenza)

    expected = {
        "imponibile_registrato": 0.0,
        "base": True,
        "sup_irrigabile_mq": 0.0,
        "sup_catastale_mq": 0.0,
        "ind_spese_fisse": 0.0,
        "atteso": 0.0,
        "delta": 0.0,
        "atteso_catastale": 0.0,
        "delta_vs_catastale": 0.0,
        "coincide_con_catastale": True,
    }
    assert payload == expected
    assert list(payload) == list(expected)
    assert original_payload == {"imponibile_registrato": 99, "base": True}


def test_build_anomalia_payload_keeps_original_fields_when_values_are_missing() -> None:
    original_payload = {
        "sup_irrigabile_mq": "original-irrigabile",
        "sup_catastale_mq": "original-catastale",
        "ind_spese_fisse": "original-indice",
        "imponibile_registrato": "original-imponibile",
    }
    anomalia = CatAnomalia(tipo="VAL-06-imponibile", dati_json=original_payload)

    payload = build_anomalia_payload(anomalia, CatUtenzaIrrigua())

    assert payload == original_payload
    assert list(payload) == list(original_payload)
    assert payload is not original_payload


@pytest.mark.parametrize("row_ids", [None, [], "non-lista"])
def test_surface_payload_without_rows_keeps_enrichment_and_existing_cause(row_ids) -> None:
    original_payload = {
        "causa_superficie": "causa-originale",
        "domanda_particella_ids": row_ids,
        "sup_irrigata_mq": "120.00",
        "superficie_riferimento_mq": "100.00",
        "domande": [{"id": "dom-1"}, {"id": "dom-1"}, {"id": "dom-2"}],
    }
    anomalia = CatAnomalia(tipo="DIR-01-superficie_coltura_superata", dati_json=original_payload)

    payload = build_anomalia_payload(anomalia)

    expected = {
        **original_payload,
        "domande": [{"id": "dom-1"}, {"id": "dom-2"}],
        "eccedenza_mq": "20.00",
        "domanda_ids": ["dom-1", "dom-2"],
        "domande_distinte_count": 2,
    }
    assert payload == expected
    assert list(payload) == list(expected)
    assert payload is not original_payload
    assert anomalia.dati_json == original_payload
    assert original_payload["domande"] == [{"id": "dom-1"}, {"id": "dom-1"}, {"id": "dom-2"}]


def test_surface_payload_without_rows_and_data_remains_none() -> None:
    assert build_anomalia_payload(
        CatAnomalia(tipo="DIR-02-superficie_totale_da_verificare", dati_json={})
    ) is None
