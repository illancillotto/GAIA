from datetime import date

from app.services.sister_visura_parser import parse_sister_visura_text


def test_parse_current_sister_snapshot_with_multiple_owners() -> None:
    payload = parse_sister_visura_text(
        """
        Visura storica per immobile
        Situazione degli atti informatizzati al 23/09/2026
        Dati della richiesta Comune di TRAMATZA (Codice:L321)
        Catasto Terreni Foglio: 4 Particella: 94
        INTESTATI
        1 TROGU Costantino nato a SOLARUSSA (OR) il 16/05/1950 TRGCTN50E16I791R* (1) Proprieta' 1/3
        2 MANCA Antonino nato a TRAMATZA (OR) il 09/07/1953 MNCNNN53L09L321N* (1) Proprieta' 2/3
        Situazione degli intestati dal 01/05/2015
        1 OLD Owner nato a ORISTANO (OR) il 01/01/1940 OLDOWN40A01G113X* (1) Proprieta' 1/1
        """
    )
    assert payload["status"] == "completed"
    assert payload["comune_codice"] == "L321"
    assert payload["parcel"] == {"foglio": "4", "particella": "94", "subalterno": None}
    assert payload["observed_at"] == date(2026, 9, 23)
    assert len(payload["owners"]) == 2
    assert payload["owners"][0]["codice_fiscale"] == "TRGCTN50E16I791R"
    assert payload["owners"][1]["quota"] == "2/3"


def test_parse_review_required_when_cadastral_reference_is_missing() -> None:
    payload = parse_sister_visura_text(
        """
        Visura per soggetto
        Comune di TRAMATZA (Codice:L321)
        INTESTATO
        1 MANCA Grazia nata a TRAMATZA (OR) il 12/07/1930
        """
    )
    assert payload["status"] == "review_required"
    assert payload["owners"][0]["denominazione"] == "MANCA Grazia"


def test_parse_sister_historical_layout_and_ownership_event() -> None:
    payload = parse_sister_visura_text(
        """
        Visura storica per immobile
        Situazione degli atti informatizzati dall'impianto meccanografico al 23/08/2026
        Dati identificativi: Comune di MARRUBIU (E972) (OR)
        Foglio 6 Particella 832
        Intestati catastali
        1. REGIONE AUTONOMA DELLA SARDEGNA (CF 80002870923)
        Diritto di: Proprieta' per 1/1
        Sono stati inoltre variati/soppressi i seguenti immobili:
        Comune: MARRUBIU (E972)
        Foglio 6 Particella 834
        Storia degli intestati dell'immobile
        Dati identificativi: Immobile attuale - Comune di MARRUBIU (E972) (OR) Foglio 6 Particella 832
        dal 03/11/2025
        1. REGIONE AUTONOMA DELLA SARDEGNA                    1. Atto amministrativo DECRETO
        (CF 80002870923)
        Diritto di: Proprieta' per 1/1
        """
    )
    assert payload["status"] == "completed"
    assert payload["parcel"]["particella"] == "832"
    assert payload["owners"][0]["codice_fiscale"] == "80002870923"
    assert payload["owners"][0]["quota"] == "1/1"
    assert payload["related_parcels"] == [{"foglio": "6", "particella": "834"}]
    assert payload["history_events"][0]["from_date"] == date(2025, 11, 3)
    assert payload["history_events"][0]["owner"]["codice_fiscale"] == "80002870923"
