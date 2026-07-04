# Verifica parsing inCASS partitario su fixture Marrubiu

## Codice letto prima della verifica

File letti integralmente:
- `backend/app/modules/elaborazioni/capacitas/apps/incass/parsers.py`
- `backend/app/modules/ruolo/services/parsing_common.py`
- `backend/app/modules/elaborazioni/capacitas/models.py`

Modelli `CapacitasInCassPartitario*` presenti:
- `CapacitasInCassPartitarioParcel`
- `CapacitasInCassPartitarioPartita`
- `CapacitasInCassPartitarioDetail`

## Funzioni reali del flusso

In `incass/parsers.py`:
- `parse_incass_partitario_dialog`
- `_extract_partitario_lines`
- `_coalesce_partitario_lines`
- `_merge_wrapped_particella_lines`
- `_looks_like_partitario_header`
- `_looks_like_partitario_separator`
- `_looks_like_consumption_summary`
- `_looks_like_consumption_header`
- `_looks_like_consumption_row`
- `_parse_incass_particella_line`
- `_parse_incass_split_particella_line`
- `_parse_incass_summary_particella_line`
- `_parse_incass_domanda_particella_line`
- `_parse_incass_domanda_surface_ha`
- `_decimal_to_string`

In `parsing_common.py`:
- `looks_like_number`
- `normalize_partita_comune_nome`
- `parse_particella_line`
- `parse_italian_decimal`

## Fixture

Usata:
- `backend/tests/fixtures/incass/partitario_marrubiu.html`

Presenza verificata: `ok`

## Ground truth da ispezione manuale del dump

Righe testata normalizzate:
- riga `6`: `2025 0648 Beni in MARRUBIU - Contributo Opere Irrigue 15.981,87 euro`
- riga `7`: `2025 0668 Beni in MARRUBIU - Contributo utenza 70,00 euro`
- riga `8`: `2025 0985 Beni in MARRUBIU - Consorzio Quote Ordinarie 11.413,68 euro`

Struttura righe candidate:
- totale candidate: `729`
- `722` righe a `6` token
- `6` righe a `7` token
- `1` riga a `8` token

## Tabella casi

| Caso | Riga | Atteso | Ottenuto | Esito |
| --- | --- | --- | --- | --- |
| Summary standard (6 token) | `31 2 62 60 0,22 0,16` | `sup_cata=60`, `manut=0,22`, `ist=0,16`, `irrig=None` | `{'distretto': '31', 'foglio': '2', 'particella': '62', 'sup_catastale_are': '60', 'importo_manut_euro': '0.22', 'importo_irrig_euro': None, 'importo_ist_euro': '0.16'}` | `CORRETTO` |
| Sub alfabetico 1 (7 token) | `34 17 193 a 23.500 85,78 61,26` | `sub='a'`, `sup_cata=23500`, `manut=85,78`, `ist=61,26` | `{'distretto': '34', 'foglio': '17', 'particella': '193', 'subalterno': 'a', 'sup_catastale_are': '23500', 'importo_manut_euro': '85.78', 'importo_ist_euro': '61.26'}` | `CORRETTO` |
| Sub alfabetico 2 (7 token) | `34 28 110 c 213 0,78 0,56` | `sub='c'`, `sup_cata=213`, `manut=0,78`, `ist=0,56` | `{'distretto': '34', 'foglio': '28', 'particella': '110', 'subalterno': 'c', 'sup_catastale_are': '213', 'importo_manut_euro': '0.78', 'importo_ist_euro': '0.56'}` | `CORRETTO` |
| Particella testuale | `31 6 acque 650 2,37 1,69` | verificare output reale | nessun parcel con `particella='acque'`; nessun parcel con `foglio='6'` e `particella='650'` | `ERRATO` |
| Domanda con coltura tratteggiata | `7245 31 1 837 16.600 5.000 PRATO-PA 44,82` | verificare in quale campo finisce `44,82` | `{'domanda_irrigua': '7245', 'distretto': '31', 'foglio': '1', 'particella': '837', 'sup_catastale_are': '16600', 'sup_irrigata_ha': '0.5', 'coltura': 'PRATO-PA', 'importo_manut_euro': '44.82', 'importo_irrig_euro': None, 'importo_ist_euro': None}` | `ERRATO` |

## Conteggi sub alfabetico

- righe raw con sub non numerico: `6`
- righe parse con sub non numerico: `6`

Su questo aspetto il parser e corretto sui dati della fixture.

## Riconciliazione testata vs somme colonne parse

| Tributo | Somma colonna parse | Testata | Delta | Esito |
| --- | --- | --- | --- | --- |
| `0648` (`sum(importo_manut_euro)`) | `16024,32` | `15981,87` | `+42,45` | `FALLISCE` |
| `0985` (`sum(importo_ist_euro)`) | `11412,09` | `11413,68` | `-1,59` | `FALLISCE` |
| `0668` (`sum(importo_irrig_euro)`) | `0,00` | `70,00` | `-70,00` | `FALLISCE` |

## Interpretazione numerica

Osservazioni certe dal dump e dall'output del parser:
- il `70,00` di `0668` e esposto solo a livello testata (`CapacitasInCassPartitarioPartita.importo_0668_euro`)
- non compare in nessuna particella
- la riga `7245 31 1 837 16.600 5.000 PRATO-PA 44,82` viene parse con `importo_manut_euro='44.82'`
- la riga `31 6 acque 650 2,37 1,69` viene persa integralmente

Effetto combinato sulla riconciliazione:
- la mis-attribuzione di `44,82` a `0648` gonfia la somma manutenzione
- la perdita della riga `acque` sottrae `2,37` a `0648` e `1,69` a `0985`
- per questo il delta netto su `0648` e `+42,45` invece di `+44,82`

Formula:
- `+44,82` (`PRATO-PA` messo in manut)
- `-2,37` (riga `acque` persa su manut)
- netto `+42,45`

Su `0985`:
- atteso da ispezione indipendente: riconciliazione quasi piena
- osservato: `-1,59`
- il delta e coerente con la perdita della riga `acque` (`ist=1,69`) al netto di un residuo `+0,10` menzionato nel brief

## BLOCCANTI

- La riga `7245 31 1 837 16.600 5.000 PRATO-PA 44,82` viene attribuita a `importo_manut_euro`. La testata `0648=15.981,87` dimostra che questa attribuzione porta a una misattribuzione silenziosa nella colonna `0648`.
- La riga `31 6 acque 650 2,37 1,69` viene persa perche il parser richiede `particella` numerica nel fallback `parse_particella_line`. Questo genera dati mancanti silenziosi e rompe la riconciliazione sia `0648` sia `0985`.
- La riconciliazione particelle vs testata fallisce per tutti e tre i tributi (`0648`, `0985`, `0668`) oltre la tolleranza richiesta.

## NON BLOCCANTI

- Nessun blocco consumi `0668` e presente in questa fixture; il `70,00` resta correttamente solo in testata. Questo e un comportamento coerente col dump, ma rende impossibile riconciliare `0668` dalle particelle.
- Il parsing delle `6` righe con subalterno alfabetico risulta corretto e completo sui dati presenti.

## Verdetto

La riga `PRATO-PA` (`44,82`) e mis-attribuita a `0648`: `si`.
L'evidenza diretta e il parcel parse con `importo_manut_euro='44.82'`; l'evidenza numerica aggregata e la somma `0648` a particelle `16024,32` contro testata `15981,87`, con delta netto `+42,45` mascherato solo in parte dalla perdita della riga `acque`.
