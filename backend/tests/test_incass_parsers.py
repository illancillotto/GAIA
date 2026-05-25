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
