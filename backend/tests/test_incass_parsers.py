from __future__ import annotations

from app.modules.elaborazioni.capacitas.apps.incass.parsers import parse_incass_partitario_dialog


PARTITARIO_SAMPLE_HTML = """\
<html>
  <body>
    <div class="kdlg-content">
      ================================================================================
      <br />ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO
      <br />================================================================================
      <br />Partita 000000402/00000 beni in comune di ARBOREA
      <br />Contribuente: Laore Sardegna                               C.F. 03122560927
      <br />Anno Trib Descrizione                                              Ruolo
      <br />2025 0648 Beni in ARBOREA - Contributo Opere Irrigue              17.288,12 euro
      <br />2025 0985 Beni in ARBOREA - Consorzio Quote Ordinarie             12.346,56 euro
      <br />Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.
      <br />33    1    80          2.536                       9,26              6,61
      <br />26    2    10         10.880                      39,71             28,36
      <br />================================================================================
    </div>
  </body>
</html>
"""

PARTITARIO_WRAPPED_ROW_HTML = """\
<div id="divPart" style="font-family: Monospace;">
================================================================================<br />
ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO<br />
================================================================================<br />
Partita 0A0287663/00000 beni in comune di ZEDDIANI<br />
Contribuente: Porcu Giovanni                               C.F. PRCGNN65M02D947W<br />
Co-intestato con: Porcu Pier Antonio<br />
Anno Trib Descrizione                                              Ruolo<br />
2025 0648 Beni in ZEDDIANI - Contributo Opere Irrigue              771,18 euro<br />
2025 0668 Beni in ZEDDIANI - Contributo utenza                      70,00 euro<br />
2025 0985 Beni in ZEDDIANI - Consorzio Quote Ordinarie             550,75 euro<br />
Dom. Dis. Fog. Part.  Sub Sup.Cata.  Sup.Irr. Colt.     Manut.   Irrig.     Ist.<br />
7    6  1323          2.491                       9,09              6,49<br />
7    6  1325          2.334                       8,52              6,08<br />
7    6  1326            187                       0,68              0,49<br />
7    6  1327             51                       0,19              0,13<br />
7    6  1342          9.170                      33,47             23,91<br />
7    6  1346         10.947                      39,96             28,54<br />
7    6  1349        186.086                     679,26            485,11<br />
1598  7    6  1349        186.086     1.000 FRUTTETO             4,07<br />
Legenda:========================================================================<br />
</div>
"""


def test_parse_incass_partitario_dialog_extracts_partite_and_particelle() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_SAMPLE_HTML, avviso="020250007976220")

    assert result is not None
    assert result.avviso == "020250007976220"
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert partita.codice_partita == "000000402/00000"
    assert partita.comune_nome == "ARBOREA"
    assert partita.contribuente == "Laore Sardegna"
    assert partita.contribuente_cf == "03122560927"
    assert partita.importo_0648_euro == "17.288,12"
    assert partita.importo_0985_euro == "12.346,56"
    assert len(partita.particelle) == 2
    assert partita.particelle[0].foglio == "1"
    assert partita.particelle[0].particella == "80"
    assert partita.particelle[0].distretto == "33"
    assert partita.particelle[0].sup_catastale_are == "2536"


def test_parse_incass_partitario_dialog_merges_wrapped_parcel_row() -> None:
    result = parse_incass_partitario_dialog(PARTITARIO_WRAPPED_ROW_HTML, avviso="020250028766300000")

    assert result is not None
    assert len(result.partite) == 1

    partita = result.partite[0]
    assert partita.codice_partita == "0A0287663/00000"
    assert len(partita.particelle) == 7

    last_row = partita.particelle[-1]
    assert last_row.domanda_irrigua == "1598"
    assert last_row.distretto == "7"
    assert last_row.foglio == "6"
    assert last_row.particella == "1349"
    assert last_row.sup_catastale_are == "186086"
    assert last_row.sup_irrigata_ha == "1000"
    assert last_row.coltura == "FRUTTETO"
    assert last_row.importo_manut_euro == "679.26"
    assert last_row.importo_irrig_euro == "4.07"
    assert last_row.importo_ist_euro == "485.11"
