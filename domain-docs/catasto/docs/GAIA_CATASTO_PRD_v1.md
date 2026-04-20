# GAIA — Modulo Catasto
## Product Requirements Document v1

> Collocazione repository: `backend/app/modules/catasto/` (estensione del modulo esistente)
> Documentazione: `domain-docs/catasto/docs/`

---

## 1. Contesto e obiettivi

### 1.1 Contesto operativo

Il Consorzio di Bonifica dell'Oristanese gestisce un territorio irriguo suddiviso in **distretti irrigui** istituiti tramite decreto regionale. Per ogni distretto, ogni anno, viene prodotto un **ruolo tributi** che elenca le particelle catastali servite dai sistemi irrigui e i relativi proprietari (consorziati), con il calcolo del contributo dovuto.

Il flusso attuale:
1. Capacitas (sistema gestionale esterno) produce il file Excel del ruolo (~90k righe, formato R2025-090-IRR)
2. Il file viene verificato manualmente e confrontato con i dati catastali aggiornati
3. Le anomalie (superfici errate, CF invalidi, proprietari cambiati) vengono corrette a mano
4. Il processo non ha storia digitale strutturata né supporto per il rilevamento dei "non paganti"

### 1.2 Obiettivi del modulo

**Obiettivo primario**: Disporre di una anagrafica catastale aggiornata sulle utenze servite dai sistemi irrigui, con identificazione automatica dei presunti non paganti.

**Obiettivi specifici**:
- Importazione e validazione del ruolo Capacitas con pipeline di controllo strutturata
- Anagrafica storica delle particelle catastali con tracciamento variazioni (proprietario, superficie, stato)
- Mappa GIS interattiva dei distretti irrigui con report per distretto
- Rilevamento automatico di irrigazione non autorizzata tramite Sentinel-2
- Integrazione con SISTER per aggiornamento dati proprietari particelle anomale
- Workflow operativo per segnalazione e gestione dei casi rilevati

### 1.3 Vincoli di dominio

| Vincolo | Descrizione |
|---|---|
| Distretti istituiti da decreto | Un distretto esiste solo se c'è un decreto regionale. Le modifiche ai confini richiedono nuovo decreto |
| Particelle FD | Fuori Distretto = servite dai sistemi irrigui ma non ancora nel distretto. Tributo non dovuto formalmente ma irrigazione monitorabile |
| Peso distretto | `Ind. Spese Fisse` è il coefficiente moltiplicatore del distretto. Valore attuale: 1.2 (standard) o 0.6 (ridotto). Può variare per anno |
| Schema 0648 — contributo irriguo | Contributo per opere irrigue. Calcolato su `SUP.IRRIGABILE × Ind.SpeseFisse × ALIQUOTA`. Aliquota fissa per anno, uguale per tutte le particelle del distretto |
| Schema 0985 — quote ordinarie | Quote Ordinarie del Consorzio. Costo **variabile** basato sulla lettura dei contatori idrici. L'aliquota nel file Capacitas incorpora già il coefficiente di consumo effettivo: **non ricalcolabile** dalla sola superficie. Importo da trattare come dato autoritativo proveniente da Capacitas |
| Multi-anno | Il sistema deve gestire campagne di ruolo per anni diversi e mantenere lo storico |
| Storico particelle | Le particelle possono cambiare proprietario, essere soppresse, essere accorpate. Il sistema deve tracciare queste variazioni |
| Fonte di verità catastale | Lo shapefile QGIS (~500MB) è la fonte primaria. L'Excel 288k è un estratto di questo |

---

## 2. Utenti e ruoli

| Ruolo | Azioni consentite |
|---|---|
| `admin` | Import, gestione distretti, configurazione schemi contributo, accesso completo |
| `reviewer` | Revisione anomalie, note su particelle, attivazione segnalazioni |
| `viewer` | Consultazione sola lettura, export |

---

## 3. Requisiti funzionali

### RF-01 — Import ruolo Capacitas

**Input**: File Excel formato `R{ANNO}-{N}-IRR_Particelle_*.xlsx`
**Sheet atteso**: `Ruoli {ANNO}`

Colonne obbligatorie da mappare:

| Colonna Excel | Campo interno | Tipo | Note |
|---|---|---|---|
| `ANNO` | `anno_campagna` | Integer | Anno del ruolo |
| `PVC` | `cod_provincia` | Integer | 97 = Oristano |
| `COM` | `cod_comune_istat` | Integer | Codice ISTAT comune |
| `CCO` | `cco` | String | Codice consorziato Capacitas |
| `FRA` | `cod_frazione` | Integer | |
| `DISTRETTO` | `num_distretto` | Integer | |
| `Unnamed: 7` | `nome_distretto_loc` | String | Localita distretto |
| `COMUNE` | `nome_comune` | String | |
| `SEZIONE` | `sezione_catastale` | String nullable | |
| `FOGLIO` | `foglio` | String | |
| `PARTIC` | `particella` | String | alfanumerico (es. STRADA058) |
| `SUB` | `subalterno` | String nullable | |
| `SUP.CATA.` | `sup_catastale_mq` | Numeric | m² |
| `SUP.IRRIGABILE` | `sup_irrigabile_mq` | Numeric | m² |
| `Ind. Spese Fisse` | `ind_spese_fisse` | Numeric | Peso distretto |
| `Imponibile s.f.` | `imponibile_sf` | Numeric | Calcolato: sup_irr × ind_sf |
| `ESENTE 0648` | `esente_0648` | Boolean | |
| `ALIQUOTA 0648` | `aliquota_0648` | Numeric | |
| `IMPORTO 0648` | `importo_0648` | Numeric | |
| `ALIQUOTA 0985` | `aliquota_0985` | Numeric | |
| `IMPORTO 0985` | `importo_0985` | Numeric | |
| `DENOMINAZ` | `denominazione` | String | |
| `CODFISC` | `codice_fiscale` | String | Normalizzare a MAIUSCOLO |

**Pipeline di validazione obbligatoria** (ogni riga passa tutti i check, le anomalie non bloccano l'import):

| Check | ID | Severità | Logica |
|---|---|---|---|
| Superficie irrigabile ≤ catastale | `VAL-01` | `error` | `sup_irrigabile > sup_catastale * 1.01` (1% tolleranza) |
| Codice fiscale valido | `VAL-02` | `error` | Normalizza MAIUSC → verifica algoritmo CF (PF: 16 car + checksum; PG: 11 cifre + checksum) |
| CF mancante | `VAL-03` | `warning` | `CODFISC` NULL o stringa vuota |
| Comune valido | `VAL-04` | `warning` | `COM` deve essere in tabella comuni italiani (ISTAT) |
| Particella presente in anagrafica | `VAL-05` | `info` | Join con `cat_particelle` su `(cod_comune_istat, foglio, particella, subalterno)`. Se non trovata: info (shapefile potrebbe non essere ancora caricato) |
| Imponibile coerente | `VAL-06` | `warning` | `abs(imponibile - sup_irr * ind_sf) > 0.01` |
| Importi coerenti | `VAL-07` | `warning` | `abs(importo_N - imponibile * aliquota_N) > 0.01` per ogni schema |
| CCO formato | `VAL-08` | `info` | Formato atteso: `000000NNN` o `0ANNNNNNN` |

**Check VAL-07 — nota su schema 0985**: L'importo 0985 dipende dalla lettura dei contatori e non è ricalcolabile da superficie × aliquota. Il check VAL-07 per 0985 verifica solo la coerenza interna del file (`IMPORTO 0985 ≈ Imponibile × ALIQUOTA 0985`) ma **non tenta di validare** il valore assoluto dell'aliquota, che viene accettata come dato autoritativo di Capacitas.

**Collegamento utenza ↔ consorziato**: Il campo `CCO` (codice consorziato Capacitas) è un identificativo interno Capacitas, non corrisponde al codice White Company. Il collegamento tra la riga del ruolo e l'anagrafica consorziati GAIA avviene tramite `CODFISC` (persone fisiche, 16 caratteri) o `CODFISC` a 11 cifre (persone giuridiche / P.IVA). Il `CCO` viene salvato come riferimento opaco per eventuale riconciliazione futura.


```json
{
  "righe_totali": 90000,
  "righe_importate": 89750,
  "righe_con_anomalie": 1200,
  "anomalie_per_tipo": {
    "VAL-01": 45,
    "VAL-02": 320,
    "VAL-03": 180,
    ...
  },
  "preview_anomalie": [...]
}
```

**Idempotenza**: Un import dello stesso `(ANNO, PVC, hash_file)` viene rifiutato con errore se già presente. Un re-import esplicito (`force=true`) cancella il batch precedente dello stesso anno e reimporta.

---

### RF-02 — Import anagrafica catastale (Shapefile)

**Input**: Shapefile QGIS (~500MB) contenente:
- Layer particelle con geometry `MultiPolygon` EPSG:4326 (o EPSG:25832, da verificare)
- Attributi catastali (NATIONALCA, CODI_FISC, FOGLIO, PARTIC, SUBA_PART, SUPE_PART, CFM, NUM_DIST, Nome_Dist)

**Modalità di import**: Script amministrativo `scripts/import_shapefile_catasto.sh` che esegue:
```bash
ogr2ogr -f PostgreSQL "PG:..." input.shp \
  -nln cat_particelle_staging \
  -t_srs EPSG:4326 \
  -progress
```
Seguito da stored procedure PL/pgSQL di upsert verso `cat_particelle` con tracking variazioni.

**Layer distretti**: Estratto dal campo `NUM_DIST` + `Nome_Dist` via query di aggregazione spaziale:
```sql
INSERT INTO cat_distretti (num_distretto, nome_distretto, geometry)
SELECT NUM_DIST, Nome_Dist, ST_Union(geometry)
FROM cat_particelle
WHERE NUM_DIST != 'FD'
GROUP BY NUM_DIST, Nome_Dist;
```

**Storico**: Ogni import shapefile crea un record in `cat_import_batches`. Le particelle modificate vengono archiviate in `cat_particelle_history`.

---

### RF-03 — Anagrafica distretti

- CRUD distretti con coefficiente `ind_spese_fisse` per anno
- Visualizzazione geometria distretto su mappa
- KPI per distretto: n. particelle, sup. totale, sup. irrigabile, importo totale 0648, importo totale 0985, n. consorziati, n. presunti non paganti
- Particelle FD associate al distretto di prossimità (per monitoraggio, non per tributo)

---

### RF-04 — Mappa GIS interattiva

- Mappa base: OpenStreetMap o satellite
- Layer distretti: poligoni colorati per status (tutti paganti / anomalie / non paganti rilevati)
- Click su distretto: pannello laterale con KPI e lista particelle
- Layer particelle: visualizzazione on-demand per distretto selezionato, colorazione per status
- Click su particella: scheda con dati catastali, proprietario, tributo, anomalie, note, storico
- Layer FD: visibile separatamente con colore distinto
- Filtri mappa: anno campagna, distretto, status anomalia, presenza irrigazione Sentinel

---

### RF-05 — Gestione anomalie

- Lista anomalie filtrabile per tipo, severità, distretto, anno, status
- Assegnazione anomalia a operatore
- Note libere per ogni anomalia
- Status workflow: `aperta → in_revisione → chiusa | segnalazione_inviata`
- Export anomalie selezionate in XLSX

---

### RF-06 — Wizard analisi anomalie

Flusso multi-step per la revisione delle anomalie rilevate:

1. **Step 1 — Selezione batch**: Scegli anno campagna e distretto
2. **Step 2 — Panoramica**: Riepilogo anomalie per tipo con grafici
3. **Step 3 — Revisione CF**: Lista particelle con CF invalido → azione: correggi / ignora / lancia visura Sister
4. **Step 4 — Revisione superfici**: Lista eccedenze superficie → azione: segnala / ignora
5. **Step 5 — Presunti non paganti**: Lista particelle con irrigazione rilevata da Sentinel e non in ruolo → azione: lancia recupero dati Sister / invia segnalazione operatori
6. **Step 6 — Report**: Riepilogo azioni intraprese, export

---

### RF-07 — Integrazione Sister per proprietari

- Da scheda particella o da wizard: lancio visura per soggetto (PF o PG) tramite modulo `elaborazioni`
- Aggiornamento `cat_intestatari` con dati restituiti da Sister
- Storico richieste Sister per particella

---

### RF-08 — Analisi Sentinel-2 (Fase 4)

- Acquisizione immagini Sentinel-2 L2A per area distretto, periodo Maggio-Settembre
- Calcolo NDVI e NDWI per ogni particella (spatial join geometria)
- Classificazione: `irrigata_probabile` | `non_irrigata` | `incerta`
- Confronto con ruolo: particelle irrigate non presenti nel ruolo → anomalia `presunto_non_pagante`
- Particelle FD con NDVI alto → anomalia `fd_irrigante_da_verificare` (severità ridotta)
- Storico analisi per particella (multi-periodo)

---

### RF-09 — Segnalazioni operatori

- Da anomalia o da scheda particella: apertura segnalazione verso modulo `operazioni`
- La segnalazione eredita i dati catastali della particella (distretto, proprietario, note)
- Tracciamento stato segnalazione nella scheda particella

---

## 4. Requisiti non funzionali

| Requisito | Target |
|---|---|
| Import 90k righe | < 60 secondi |
| Import shapefile 500MB | < 10 minuti (script batch, non API sincrona) |
| Query lista particelle con filtri | < 500ms |
| Query GeoJSON distretto singolo | < 1s |
| Tiles MVT per mappa | < 200ms per tile |
| Multi-anno | Campagne dal 2020 in avanti supportate |

---

## 5. Domande aperte (decisioni da prendere)

| ID | Domanda | Impatto |
|---|---|---|
| OQ-01 | ~~Il campo `CCO` corrisponde al `wc_id` White Company?~~ | ✅ **RISOLTO**: CCO ≠ wc_id. Il collegamento tra utenza tributaria e consorziato avviene tramite `codice_fiscale` / P.IVA |
| OQ-02 | ~~Codici schema fissi?~~ | ✅ **RISOLTO**: 0648 = contributo irriguo (aliquota fissa), 0985 = Quote Ordinarie (aliquota variabile da contatori). Fissi per ora |
| OQ-03 | ~~EPSG shapefile?~~ | ✅ **RISOLTO**: EPSG:3003 Monte Mario / Italy zone 1. `ogr2ogr` deve convertire a EPSG:4326 con `-s_srs EPSG:3003 -t_srs EPSG:4326` |
| OQ-04 | ~~PARTIC alfanumerico?~~ | ✅ **RISOLTO**: sì, confermato. Schema già corretto con `VARCHAR(20)` |
| OQ-05 | ~~Anni precedenti disponibili?~~ | ✅ **RISOLTO**: solo 2025. Import storico non necessario in Fase 1 |
