# Verifica completezza parsing inCASS partitario - 2026-07-01

## Codice letto prima della verifica

File letti integralmente:
- `backend/app/modules/elaborazioni/capacitas/apps/incass/parsers.py`
- `backend/app/modules/ruolo/services/parsing_common.py`
- `backend/app/modules/elaborazioni/capacitas/models.py`

Modelli `CapacitasInCassPartitario*` presenti in `models.py`:
- `CapacitasInCassPartitarioParcel`
- `CapacitasInCassPartitarioPartita`
- `CapacitasInCassPartitarioDetail`

## Funzioni reali coinvolte nel flusso

Funzioni presenti in `incass/parsers.py` coinvolte nel flusso `parse_incass_partitario_dialog -> _parse_particella_line`:
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

Funzioni presenti in `parsing_common.py` coinvolte direttamente o tramite fallback:
- `looks_like_number`
- `normalize_partita_comune_nome`
- `parse_particella_line`
- `parse_italian_decimal`

## Discrepanze spec/codice

Nessuna sulle funzioni citate nel brief: `_parse_incass_summary_particella_line`, `_parse_incass_domanda_particella_line`, `_merge_wrapped_particella_lines` e `_looks_like_consumption_*` esistono tutte nel codice attuale.

## Fixture usate

Alias creati senza alterare il contenuto:
- `backend/tests/fixtures/incass/partitario_laore.html` -> `03122560927.txt`
- `backend/tests/fixtures/incass/partitario_serra.html` -> `SRRCLD68P09G113D.txt`
- `backend/tests/fixtures/incass/partitario_lml.html` -> `00587060955.txt`

## Copertura fixture

- `laore`: `13` partite, particelle per partita `169, 2, 10, 16, 76, 4, 2, 10, 14, 8, 21, 75, 12`
- `serra`: `1` partita, `2` particelle
- `lml`: `1` partita, `235` particelle

## Tabella casi

| Caso | Riga esempio normalizzata | Atteso | Ottenuto | Esito |
| --- | --- | --- | --- | --- |
| 1. Irrig vuota | `26 2 19 838.570 3.061,00 2.186,06` | `sup_cata=838570`, `manut=3.061,00`, `ist=2.186,06`, `irrig=None` | `{'distretto': '26', 'foglio': '2', 'particella': '19', 'subalterno': None, 'sup_catastale_are': '838570', 'sup_irrigata_ha': None, 'importo_manut_euro': '3061.00', 'importo_irrig_euro': None, 'importo_ist_euro': '2186.06'}` | `CORRETTO` |
| 2. Sub alfabetico | `28 20 12 c 15 0,05 0,04` | `foglio=20`, `particella=12`, `sub='c'`, `sup_cata=15`, `manut=0,05`, `ist=0,04` | `{'distretto': '28', 'foglio': '20', 'particella': '12', 'subalterno': 'c', 'sup_catastale_are': '15', 'sup_irrigata_ha': None, 'importo_manut_euro': '0.05', 'importo_ist_euro': '0.04'}` | `CORRETTO` |
| 3. Domanda con coltura e un solo importo | `3431 15 9 467 5.303 1.330 FRUTTETO 5,42` | `domanda=3431`, `sup_cata=5303`, `sup_irr=0.133 ha`, `coltura=FRUTTETO`, `manut=5,42`, `irrig=None`, `ist=None` | `{'domanda_irrigua': '3431', 'distretto': '15', 'foglio': '9', 'particella': '467', 'sup_catastale_are': '5303', 'sup_irrigata_ha': '0.133', 'coltura': 'FRUTTETO', 'importo_manut_euro': '5.42', 'importo_irrig_euro': None, 'importo_ist_euro': None}` | `CORRETTO` |
| 4. Blocco consumi 0668 | `Consumi da contatore: ...`, `Anno Domanda Distretto Sup.Domanda ...`, `2025 4381 28 671390 8.458,000` | nessuna particella fantasma | output `serra`: sole particelle `1458`, `1462`; nessun `foglio=2025`, nessuna `particella in {671390,678490,680360,680460}` | `CORRETTO` |
| 5. Riga spezzata su due `<br>` | nessun esempio presente nei tre dump | copertura reale della merge logic oppure dichiarazione assenza | ricerca sui tre dump: nessun candidato al pattern di merge attuale | `NON GESTITO DAI TEST` |

## Evidenza analitica per caso

### 1. Attribuzione colonne con Irrig vuota

Riga reale normalizzata da `laore`:
- `26 2 19 838.570 3.061,00 2.186,06`

Percorso attivato nel codice:
- `_parse_incass_particella_line`
- `_parse_incass_summary_particella_line`

Giudizio:
- `CORRETTO` sui dati attuali

Nota:
- la mappatura non e guidata dall'header HTML
- e assunta dal pattern `6/7 token summary = distretto, foglio, particella, [sub], sup_cata, manut, ist`
- se in futuro comparisse una riga summary con `0668` per particella, il codice non ha un pattern per distinguerla

### 2. Subalterno alfabetico

Riga reale normalizzata da `lml`:
- `28 20 12 c 15 0,05 0,04`

Conteggio righe raw con `sub` non numerico in `lml`:
- `17`

Conteggio righe parse con `sub` non numerico:
- `17`

Giudizio:
- `CORRETTO` sui dati attuali

### 3. Domanda irrigua con coltura e un solo importo in coda

Riga reale normalizzata da `laore`:
- `3431 15 9 467 5.303 1.330 FRUTTETO 5,42`

Percorso attivato nel codice:
- `_parse_incass_particella_line`
- `_parse_incass_domanda_particella_line`
- `_parse_incass_domanda_surface_ha`

Giudizio:
- `CORRETTO` sui dati attuali

Nota:
- l'importo singolo in coda finisce in `importo_manut_euro` per effetto di `numeric_tail[0]`
- e una convenzione di parsing, non una lettura della colonna da header

### 4. Blocco consumi 0668

Righe reali normalizzate da `serra`:
- `Consumi da contatore: 30.416,000 mc Imposta: 364,99 euro (Tributo 0668)`
- `Anno Domanda Distretto Sup.Domanda Contatore Seriale Tessera Consumo (mc)`
- `2025 4381 28 671390 8.458,000`

Condizioni esatte di scarto:
- summary: `_looks_like_consumption_summary` usa `startswith("CONSUMI DA CONTATORE:")`
- header: `_looks_like_consumption_header` usa `startswith("ANNO DOMANDA DISTRETTO SUP.DOMANDA")`
- row: `_looks_like_consumption_row` richiede:
  - `len(tokens) in (5, 6, 7)`
  - `tokens[0] == "2025"`
  - `tokens[1:4]` tutti numerici
  - `tokens[4]` numerico

Giudizio:
- `CORRETTO` sui dati attuali

Nota:
- lo scarto non dipende solo dal count-gating
- dipende da filtri dedicati
- resta fragile perche i filtri sono string/pattern-based, con prefissi e shape fissi

### 5. Righe particella spezzate su due `<br>`

Esito ricerca nei tre dump:
- nessun candidato al pattern `6 token summary + 8 token domanda` del merge attuale
- nessun candidato al merge `summary + detail` su riga successiva

Giudizio:
- `_merge_wrapped_particella_lines` non e coperto da queste fixture
- va verificato con una fixture dedicata

## BLOCCANTI

- Nessun difetto bloccante emerso sui quattro casi verificati nei tre dump reali.

## NON BLOCCANTI

- La mappatura delle summary rows non e header-driven: il codice assume che i `6/7` token siano sempre `sup_cata, manut, ist`. Regge sui dati attuali ma non garantisce la presenza futura di un eventuale importo `0668` per particella.
- La mappatura delle domanda rows con un solo importo in coda e anch'essa convenzionale: il primo e unico importo viene mappato a `manut`.
- I filtri del blocco consumi `0668` sono dedicati ma fragili a variazioni testuali o di shape del blocco.
- `_merge_wrapped_particella_lines` esiste nel codice ma non e coperto dai tre dump reali.

## Conclusione

La logica attuale e `SUFFICIENTE-CON-RISERVE`.
Sui tre dump reali e sui quattro casi chiave richiesti il comportamento osservato e corretto e non emergono misattribuzioni silenziose. Restano pero assunzioni di shape non guidate dall'header e una merge logic non coperta da queste fixture, quindi non si puo dichiarare sufficienza piena per un parsing "completo" di formati futuri o varianti non presenti nei dump.
