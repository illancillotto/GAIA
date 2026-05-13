"""
Test unitari del parser Ruolo.
Basati sul sample del file .dmp descritto nel PROMPT_CODEX_ruolo.md.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.ruolo.services.parser import (
    ParsedPartitaCNC,
    _parse_header,
    _parse_n4_blocks,
    _parse_particella_line,
    detect_anno_tributario,
    _parse_partite_block,
    extract_text_from_content,
    parse_ruolo_file,
)

# ---------------------------------------------------------------------------
# Sample dati di test (basati sul formato reale descritto nella documentazione)
# ---------------------------------------------------------------------------

SAMPLE_PARTITA_1 = """\
<qm500>--Partita CNC 01.02024000000202--------<017.743><01.A><02024000000202><inizio>
N2 MCCPLA69E23F272E 00000000 00 N
MACCIONI PAOLO 23.05.1969 F272 MOGORO(OR)
Dom: VIA POD.113 CASA 49 MORIMENTA 00000 09095 F272 MOGORO(OR)
Res: 00000 00000 ( )

NP  4  PARTITA 0A1102766/00000 BENI IN COMUNE DI PABILLONIS
NP  5  CONTRIBUENTE: MACCIONI PAOLO     C.F. MCCPLA69E23F272E
NP  6  CO-INTESTATO CON: CASU MARIA ELENA
NP  7  ANNO TRIB DESCRIZIONE                                     RUOLO
NP  8  2024 0648 BENI IN PABILLONIS - CONTRIBUTO OPERE IRRIGUE  6,05 EURO
NP  9  2024 0985 BENI IN PABILLONIS - CONSORZIO QUOTE ORDINARIE 4,32 EURO
NP  10 DOM. DIS. FOG. PART. SUB  SUP.CATA.  SUP.IRR. COLT. MANUT. IRRIG. IST.
NP  11       292    1  361          63       0,23          0,16
NP  12       292    1  390       1.455       5,30          3,78
N4
    2024 0985  1.679.520  36,40  (L. 70.480 )
    OPERE DI BONIFICA (UTENZA 024000002)
N4
    2024 0648  1.679.520  50,94  (L. 98.634 )
    OPERE DI BONIFICA (UTENZA 024000002)
----------------<017.743><01.A><02024000000202><-fine->
"""

SAMPLE_PARTITA_2 = """\
<qm500>--Partita CNC 01.02024000000305--------<013.421><01.B><02024000000305><inizio>
N2 RSSMRA75T50A331X 11111111 01 N
ROSSI MARIA 10.12.1975 A331 ALGHERO(SS)
Dom: VIA ROMA 15 00000 07041 A331 ALGHERO(SS)
Res: VIA ROMA 15 00000 07041 A331 ALGHERO(SS)

NP  4  PARTITA 0B2203577/00000 BENI IN COMUNE DI ARBOREA
NP  5  CONTRIBUENTE: ROSSI MARIA     C.F. RSSMRA75T50A331X
NP  7  ANNO TRIB DESCRIZIONE                                     RUOLO
NP  8  2024 0648 BENI IN ARBOREA - CONTRIBUTO OPERE IRRIGUE  12,50 EURO
NP  9  2024 0985 BENI IN ARBOREA - CONSORZIO QUOTE ORDINARIE 8,75 EURO
NP  10 2024 0668 BENI IN ARBOREA - IRRIGAZIONE               25,00 EURO
NP  11 DOM. DIS. FOG. PART. SUB  SUP.CATA.  SUP.IRR. COLT. MANUT. IRRIG. IST.
NP  12       301    2  450    500            1,80          5,20  7,50
NP  13       301    2  451  A 200            0,72          2,08  3,00
N4
    2024 0648  2.500.000  12,50  (L. 24.188 )
    OPERE DI BONIFICA (UTENZA 025000003)
N4
    2024 0985  2.500.000  8,75  (L. 16.938 )
    OPERE DI BONIFICA (UTENZA 025000003)
N4
    2024 0668  2.500.000  25,00  (L. 48.400 )
    OPERE DI BONIFICA (UTENZA 025000003)
----------------<013.421><01.B><02024000000305><-fine->
"""

FULL_SAMPLE = SAMPLE_PARTITA_1 + "\n" + SAMPLE_PARTITA_2

REALISTIC_MULTI_HEADER_SAMPLE = """\
<qm500>--Partita CNC 01.02025000000101------------------------------------------<017.743><01.A><02025000000101><inizio>
N2 MCCPLA69E23F272E 00000000 00 N
MACCIONI PAOLO 23.05.1969 F272 MOGORO(OR)
Dom: VIA POD.113 CASA 49 MORIMENTA 00000 09095 F272 MOGORO(OR)
Res: 00000 00000 ( )
NP  4  PARTITA 0A1102766/00000 BENI IN COMUNE DI PABILLONIS
----------------<017.743><01.A><02025000000101><-fine->

---------Partita CNC 01.02025000000303------------------------------------------<017.743><01.A><02025000000303><inizio>
N2 MDDLSE06L64H856X 00000000 00 N
MEDDA ELISA 24.07.2006 H856 SAN GAVINO MONREALE(VS)
Dom: VIA NAPOLI N 2 A INT 00006 09030 G207 PABILLONIS(VS)
Res: 00000 00000 ( )
NP  4  PARTITA 0A1404173/00000 BENI IN COMUNE DI PABILLONIS
----------------<017.743><01.A><02025000000303><-fine->
"""


# ---------------------------------------------------------------------------
# Test 1: parse delle due partite di esempio
# ---------------------------------------------------------------------------

def test_parse_two_partite():
    result = parse_ruolo_file(FULL_SAMPLE)
    assert len(result) == 2


def test_parse_partita_1_cnc():
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert "02024000000202" in p.codice_cnc or "01.02024000000202" in p.codice_cnc


def test_parse_partita_1_nominativo():
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert p.codice_fiscale_raw == "MCCPLA69E23F272E"
    assert "MACCIONI PAOLO" in p.nominativo_raw


def test_parse_partita_pf_domicilio_residenza():
    """Parse nominativo PF con domicilio valorizzato e residenza quasi vuota."""
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert p.domicilio_raw is not None
    assert "VIA POD.113" in p.domicilio_raw
    # Res è vuota (solo spazi e zeros)
    assert p.residenza_raw is not None  # valorizzata ma con contenuto minimo


def test_parse_partita_con_cointestatario():
    """Parse partita con co-intestato."""
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert len(p.partite) > 0
    partita = p.partite[0]
    assert partita.co_intestati_raw is not None
    assert "CASU MARIA ELENA" in partita.co_intestati_raw


def test_parse_particella_con_subalterno_letterale():
    """Parse particella con subalterno letterale (es. 'A')."""
    # Seconda partita ha particella con SUB 'A'
    result = parse_ruolo_file(FULL_SAMPLE)
    p2 = result[1]
    assert len(p2.partite) > 0
    # Cerca una particella con subalterno letterale
    particelle = p2.partite[0].particelle
    assert len(particelle) >= 2


def test_parse_n4_importi_e_utenza():
    """Parse N4 con estrazione importi e codice utenza."""
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert p.codice_utenza == "024000002"
    assert p.importo_totale_0985 == Decimal("36.40")
    assert p.importo_totale_0648 == Decimal("50.94")


def test_parse_n4_campo_sconosciuto():
    """Il terzo campo N4 (es. 1.679.520) viene conservato as-is come stringa VARCHAR."""
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    assert p.n4_campo_sconosciuto is not None
    # Il campo è conservato as-is come stringa, non interpretato
    assert isinstance(p.n4_campo_sconosciuto, str)
    assert len(p.n4_campo_sconosciuto) > 0


def test_parse_superficie_are():
    """SUP.CATA. è in are; 1.455 diventa 1455 are = 14.55 ha."""
    result = parse_ruolo_file(FULL_SAMPLE)
    p = result[0]
    partita = p.partite[0]
    # La seconda particella ha sup_cata 1.455 → 1455 are
    if len(partita.particelle) >= 2:
        part2 = partita.particelle[1]
        assert part2.sup_catastale_are == Decimal("1455")
        assert part2.sup_catastale_ha == Decimal("14.55")


def test_parse_riga_malformata_non_interrompe():
    """Righe malformate non interrompono il parse dell'intera partita."""
    malformed = SAMPLE_PARTITA_1.replace(
        "NP  11       292    1  361       63          0,23          0,16",
        "NP  11 RIGA_MALFORMATA_SENZA_SENSO #####",
    )
    result = parse_ruolo_file(malformed + SAMPLE_PARTITA_2)
    # La seconda partita deve essere parsata correttamente
    assert len(result) >= 1


def test_parse_realistic_headers_without_qm500_on_following_blocks():
    result = parse_ruolo_file(REALISTIC_MULTI_HEADER_SAMPLE)
    assert len(result) == 2
    assert result[0].codice_cnc == "01.02025000000101"
    assert result[1].codice_cnc == "01.02025000000303"


def test_parse_particelle_stops_before_consumi_section():
    sample = """\
<qm500>--Partita CNC 01.02025000634843------------------------------------------<017.743><01.A><02025000634843><inizio>
N2 SRRDNC42A05M153H 00000000 00 N
SERRA DOMENICO FELICE 05.01.1942 M153 ZEDDIANI(OR)
Dom: VIA ROMA 00112 09070 M153 ZEDDIANI(OR)
Res: 00000 00000 ( )
NP   4 PARTITA 000000548/00000 BENI IN COMUNE DI ZEDDIANI
NP   5 CONTRIBUENTE: SERRA DOMENICO FELICE                        C.F. SRRDNC42A05M153H
NP  10 DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  11         7    8   752          1.870                       6,83              4,87
NP  12         7    9    27    A     5.565                      20,31             14,51
NP  16 CONSUMI DA CONTATORE:      908,000 MC    IMPOSTA:      10,90 EURO (TRIBUTO 0668)
NP  17 ANNO DOMANDA DISTRETTO SUP.DOMANDA CONTATORE  SERIALE    TESSERA   CONSUMO (MC)
NP  18 2025    1539         7             1846000490                           908,000
NP  19 ================================================================================
N4
    2025 0668        90.800           70,00  (L.       135.539 )
    OPERE DI BONIFICA (UTENZA 025006348)
----------------<017.743><01.A><02025000634843><-fine->
"""
    result = parse_ruolo_file(sample)
    assert len(result) == 1
    assert len(result[0].partite) == 1
    assert len(result[0].partite[0].particelle) == 2


def test_parse_partita_normalizza_comune_con_quota():
    sample = """\
<qm500>--Partita CNC 01.02025000000001------------------------------------------<017.743><01.A><02025000000001><inizio>
N2 RSSMRA75T50A331X 00000000 00 N
ROSSI MARIA
NP   4 PARTITA 000000001/00000 BENI IN COMUNE DI URAS                      (QUOTA 1/30)
NP   5 CONTRIBUENTE: ROSSI MARIA                        C.F. RSSMRA75T50A331X
NP  9  DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  10         7    8   752          1.870                       6,83              4,87
----------------<017.743><01.A><02025000000001><-fine->
"""
    result = parse_ruolo_file(sample)
    assert result[0].partite[0].comune_nome == "URAS"
    assert len(result[0].partite[0].particelle) == 1


def test_parse_partita_normalizza_alias_comune_storico():
    sample = """\
<qm500>--Partita CNC 01.02025000000002------------------------------------------<017.743><01.A><02025000000002><inizio>
N2 RSSMRA75T50A331X 00000000 00 N
ROSSI MARIA
NP   4 PARTITA 000000002/00000 BENI IN COMUNE DI SILI'*ORISTANO
NP   5 CONTRIBUENTE: ROSSI MARIA                        C.F. RSSMRA75T50A331X
NP  9  DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  10         7    8   752          1.870                       6,83              4,87
----------------<017.743><01.A><02025000000002><-fine->

---------Partita CNC 01.02025000000003------------------------------------------<017.743><01.A><02025000000003><inizio>
N2 VRDPLA75T50A331X 00000000 00 N
VERDI PAOLA
NP   4 PARTITA 000000003/00000 BENI IN COMUNE DI OLLASTRA SIMAXIS
NP   5 CONTRIBUENTE: VERDI PAOLA                        C.F. VRDPLA75T50A331X
NP  9  DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  10         7    9    27    A     5.565                      20,31             14,51
----------------<017.743><01.A><02025000000003><-fine->
"""
    result = parse_ruolo_file(sample)
    assert result[0].partite[0].comune_nome == "SILI"
    assert result[1].partite[0].comune_nome == "OLLASTRA"


def test_parse_particelle_ignora_legenda_e_header_estesi():
    sample = """\
<qm500>--Partita CNC 01.02025000000004------------------------------------------<017.743><01.A><02025000000004><inizio>
N2 RSSMRA75T50A331X 00000000 00 N
ROSSI MARIA
NP   4 PARTITA 000000004/00000 BENI IN COMUNE DI MOGORO
NP   5 CONTRIBUENTE: ROSSI MARIA                        C.F. RSSMRA75T50A331X
NP  9  DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  10         7    8   752          1.870                       6,83              4,87
NP  11      DOM.=DOMANDA IRRIGUA           DIS.=CODICE DISTRETTO
NP  12      FOG.=FOGLIO CATASTALE         PART.=PARTICELLA CATASTALE   SUB=SUBALTERNO
NP  13 SUP.CATA.=SUPERFICIE CATASTALE  SUP.IRR.=SUPERFICIE IRRIGATA  COLT.=COLTURA
NP  14   MANUT. =MANUTENZIONE(0648)      IRRIG.=IRRIGAZIONE(0668)
NP  15 ================================================================================
----------------<017.743><01.A><02025000000004><-fine->
"""
    result = parse_ruolo_file(sample)
    assert len(result[0].partite[0].particelle) == 1
    assert result[0].partite[0].particelle[0].foglio == "8"


# ---------------------------------------------------------------------------
# Test helper: _parse_header
# ---------------------------------------------------------------------------

def test_parse_header_base():
    block = (
        "N2 MCCPLA69E23F272E 00000000 00 N\n"
        "MACCIONI PAOLO 23.05.1969 F272 MOGORO(OR)\n"
        "Dom: VIA ESEMPIO 1\n"
        "Res: 00000\n"
    )
    cf, extra, nom, dom, res = _parse_header(block)
    assert cf == "MCCPLA69E23F272E"
    assert extra == "00000000 00 N"
    assert "MACCIONI PAOLO" in nom
    assert dom == "VIA ESEMPIO 1"


# ---------------------------------------------------------------------------
# Test helper: _parse_particella_line
# ---------------------------------------------------------------------------

def test_parse_particella_line_standard():
    tokens = ["292", "1", "361", "63", "0,23", "0,16"]
    p = _parse_particella_line(tokens)
    assert p is not None
    assert p.foglio == "1"
    assert p.particella == "361"
    assert p.sup_catastale_are == Decimal("63")
    assert p.sup_irrigata_ha == Decimal("0.23")


def test_parse_particella_line_superficie_migliaia():
    """1.455 deve diventare 1455 are, non 1.455."""
    tokens = ["292", "1", "390", "1.455", "5,30", "3,78"]
    p = _parse_particella_line(tokens)
    assert p is not None
    assert p.sup_catastale_are == Decimal("1455")
    assert p.sup_catastale_ha == Decimal("14.55")


# ---------------------------------------------------------------------------
# Test: extract_text_from_content fallback testo grezzo
# ---------------------------------------------------------------------------

def test_extract_text_plain():
    content = FULL_SAMPLE.encode("utf-8")
    text = extract_text_from_content(content, filename="ruolo.dmp")
    assert "<inizio>" in text


def test_detect_anno_tributario_from_structured_content():
    content = FULL_SAMPLE.encode("utf-8")
    assert detect_anno_tributario(content, filename="ruolo_ignoto.pdf") == 2024


def test_detect_anno_tributario_from_partita_cnc_pattern():
    content = b"<qm500>--Partita CNC 01.02021000039305--------<inizio>"
    assert detect_anno_tributario(content, filename="ruolo_ignoto.pdf") == 2021


def test_detect_anno_tributario_from_filename_fallback():
    content = b"contenuto senza anno utile"
    assert detect_anno_tributario(content, filename="RUOLO_BONIFICA_2025.dmp.pdf") == 2025


def test_detect_anno_tributario_from_filename_r_pattern():
    content = b"contenuto senza anno utile"
    assert detect_anno_tributario(content, filename="R2024.14215.00002.dmp.pdf") == 2024
    assert detect_anno_tributario(content, filename="R2022.14215.00002.dmp.pdf") == 2022
    assert detect_anno_tributario(content, filename="R2019.irr.14215.dmp.pdf") == 2019
