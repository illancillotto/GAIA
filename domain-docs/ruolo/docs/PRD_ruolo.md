# GAIA Ruolo — Product Requirements Document v1.0

> **Regola repository**
> GAIA Ruolo non introduce un backend separato. Usa il backend monolite modulare condiviso.

> Consorzio di Bonifica dell'Oristanese — Aprile 2026
> Documento interno — uso riservato

---

## 1. Overview del modulo

GAIA Ruolo è il modulo di gestione del **ruolo consortile** all'interno della piattaforma GAIA.
Il ruolo è il documento amministrativo-contabile con cui il Consorzio formalizza annualmente
la posizione tributaria di ogni contribuente: chi deve pagare, quanto, per quale anno,
e su quali immobili o terreni si basa il contributo.

> **Posizione nel sistema**
> GAIA Ruolo è il sesto modulo della piattaforma. Condivide autenticazione JWT, database
> PostgreSQL e infrastruttura Docker con gli altri moduli GAIA.
> Si integra con **GAIA Anagrafica (Utenze)** per il collegamento soggetto–avviso e con
> **GAIA Catasto** per il popolamento e la consultazione delle particelle catastali.

---

### 1.1 Cosa è il Ruolo consortile

Il Ruolo viene emesso annualmente dal sistema gestionale tributi del Consorzio (Capacitas).
Per ogni contribuente viene prodotta una **Partita CNC** (avviso di pagamento) che contiene:

- i dati anagrafici del contribuente
- l'elenco delle **partite catastali** su cui insiste il contributo (per comune)
- per ogni partita: le **particelle**, con superficie catastale e superficie irrigata
- gli **importi** per ciascuno dei tre tributi consortili
- i **totali avviso** con riferimento al codice utenza consortile

Il file sorgente è un PDF testuale generato da Capacitas (formato `.dmp` interno),
con ~9.810 partite per il ruolo 2024.

---

### 1.2 Tributi consortili

| Codice | Nome | Tipo | Base di calcolo |
|--------|------|------|-----------------|
| `0648` | MANUTENZIONE | Fisso | Superficie × tipo impianti e terreno |
| `0985` | ISTITUZIONALE | Fisso | Superficie × coltura |
| `0668` | IRRIGAZIONE | Variabile | Consumo acqua effettivo |

---

### 1.3 Obiettivi del modulo

- Importare in modo strutturato e storicizzato il file Ruolo annuale
- Collegare ogni avviso al soggetto corrispondente in GAIA Anagrafica via CF/PIVA
- Popolare le tabelle catastali di base (`catasto_parcels`) come prima fonte di dati
  sulle particelle (precedendo o integrando SISTER e Capacitas)
- Rendere consultabili posizioni tributarie, avvisi e particelle da frontend
- Supportare la storicità delle particelle (frazionamenti, accorpamenti nel tempo)
- Esporre la posizione tributaria nella scheda soggetto di GAIA Anagrafica

---

### 1.4 Non obiettivi MVP

- Calcolo autonomo degli importi (il calcolo avviene in Capacitas, GAIA importa)
- Emissione o stampa di avvisi di pagamento
- Integrazione con sistemi di riscossione coattiva
- Gestione pagamenti e quietanze
- Notifiche ai contribuenti
- Confronto diff tra anni tributari diversi

---

## 2. Requisiti funzionali

### 2.1 Import del file Ruolo

| Req | Priorità | Descrizione |
|-----|----------|-------------|
| RF-IMP-01 | MUST | Upload file PDF Ruolo da frontend con anno tributario associato |
| RF-IMP-02 | MUST | Import asincrono con job tracking: stato, contatori, preview errori |
| RF-IMP-03 | MUST | Parser del formato `.dmp`: estrazione partite CNC, partite catastali, particelle, tributi, N4 |
| RF-IMP-04 | MUST | Collegamento avviso → soggetto GAIA tramite CF/PIVA (match su `ana_persons.codice_fiscale` o `ana_companies.partita_iva`) |
| RF-IMP-05 | MUST | Avvisi con soggetto non trovato in anagrafica: importare comunque con `subject_id = NULL`, contare come `skipped` |
| RF-IMP-06 | MUST | Idempotenza: re-import dello stesso anno non crea duplicati; upsert su `(codice_cnc, anno_tributario)` |
| RF-IMP-07 | MUST | Avvertimento operatore se l'anno tributario ha già avvisi importati (senza blocco automatico) |
| RF-IMP-08 | SHOULD | Accettare sia PDF che file `.dmp` grezzo (testo) come formato di upload |
| RF-IMP-09 | SHOULD | Preview job: contatori in tempo reale durante l'elaborazione |
| RF-IMP-10 | COULD | Re-import selettivo per singola partita CNC |

---

### 2.2 Consultazione avvisi

| Req | Priorità | Descrizione |
|-----|----------|-------------|
| RF-AV-01 | MUST | Lista avvisi con filtri: anno, soggetto, CF/PIVA, comune, codice utenza |
| RF-AV-02 | MUST | Dettaglio avviso: dati contribuente, elenco partite per comune, tabella particelle, totali per tributo |
| RF-AV-03 | MUST | Storico avvisi per soggetto: tutti gli anni disponibili |
| RF-AV-04 | SHOULD | Ricerca full-text per nominativo o CF/PIVA nell'elenco avvisi |
| RF-AV-05 | SHOULD | Export CSV/XLSX della lista avvisi filtrata |
| RF-AV-06 | COULD | Confronto importi anno corrente vs anno precedente per stesso soggetto |

---

### 2.3 Consultazione particelle

| Req | Priorità | Descrizione |
|-----|----------|-------------|
| RF-PAR-01 | MUST | Ricerca particelle per comune, foglio, numero, anno tributario |
| RF-PAR-02 | MUST | Storico temporale della particella: variazioni superficie negli anni |
| RF-PAR-03 | SHOULD | Da particella: navigare verso gli avvisi che la contengono |
| RF-PAR-04 | SHOULD | Da avviso: navigare verso le particelle catastali |
| RF-PAR-05 | COULD | Visualizzazione aggregata superficie per comune per anno |

---

### 2.4 Integrazione GAIA Anagrafica

| Req | Priorità | Descrizione |
|-----|----------|-------------|
| RF-INT-01 | MUST | Nella scheda soggetto: sezione "Ruolo Consortile" con avvisi per anno e importi totali |
| RF-INT-02 | SHOULD | Da scheda soggetto: accesso diretto al dettaglio avviso |
| RF-INT-03 | COULD | Badge soggetti con avvisi non collegati (CF non trovato) per revisione anagrafica |

---

### 2.5 Statistiche e dashboard

| Req | Priorità | Descrizione |
|-----|----------|-------------|
| RF-STAT-01 | MUST | Per anno: totale avvisi, totale importi per tributo, numero soggetti non collegati |
| RF-STAT-02 | SHOULD | Ripartizione importi per comune |
| RF-STAT-03 | COULD | Trend importi multi-anno per soggetto o per comune |

---

## 3. Modello dati

### 3.1 Tabelle nuove

#### `ruolo_import_jobs`
Traccia ogni operazione di import del file Ruolo.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `anno_tributario` | Integer NOT NULL | |
| `filename` | VARCHAR(300) | nome file originale |
| `status` | VARCHAR(20) | `pending` / `running` / `completed` / `failed` |
| `started_at` | TIMESTAMPTZ | |
| `finished_at` | TIMESTAMPTZ NULL | |
| `total_partite` | Integer NULL | |
| `records_imported` | Integer NULL | avvisi importati |
| `records_skipped` | Integer NULL | soggetto non trovato |
| `records_errors` | Integer NULL | errori di parsing |
| `error_detail` | Text NULL | max 20 righe preview |
| `triggered_by` | Integer FK → application_users | |
| `params_json` | JSONB NULL | metadati runtime |
| `created_at` | TIMESTAMPTZ | |

---

#### `ruolo_avvisi`
Un avviso di pagamento (Partita CNC) per soggetto per anno.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `import_job_id` | UUID FK → ruolo_import_jobs | |
| `codice_cnc` | VARCHAR(50) NOT NULL | es. `01.02024000000202` |
| `anno_tributario` | Integer NOT NULL | |
| `subject_id` | UUID FK → ana_subjects NULL | NULL se non trovato |
| `codice_fiscale_raw` | VARCHAR(20) | sempre valorizzato |
| `nominativo_raw` | VARCHAR(300) | riga nominativo dal file |
| `domicilio_raw` | TEXT NULL | |
| `residenza_raw` | TEXT NULL | |
| `n2_extra_raw` | VARCHAR(100) NULL | campi sconosciuti riga N2 |
| `codice_utenza` | VARCHAR(30) NULL | es. `024000002` |
| `importo_totale_0648` | Numeric(12,2) NULL | totale MANUTENZIONE |
| `importo_totale_0985` | Numeric(12,2) NULL | totale ISTITUZIONALE |
| `importo_totale_0668` | Numeric(12,2) NULL | totale IRRIGAZIONE |
| `importo_totale_euro` | Numeric(12,2) NULL | somma dei tre tributi |
| `importo_totale_lire` | Numeric(14,2) NULL | controvalore storico in Lire |
| `n4_campo_sconosciuto` | VARCHAR(30) NULL | terzo campo riga N4 (es. `1.679.520`) — significato non determinato, conservare as-is |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Indici: `(codice_cnc, anno_tributario)` UNIQUE, `(subject_id)`, `(codice_fiscale_raw)`, `(anno_tributario)`

---

#### `ruolo_partite`
Partita catastale all'interno di un avviso (raggruppamento per comune).

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `avviso_id` | UUID FK → ruolo_avvisi | |
| `codice_partita` | VARCHAR(30) NOT NULL | es. `0A1102766/00000` |
| `comune_nome` | VARCHAR(100) NOT NULL | |
| `comune_codice` | VARCHAR(10) NULL | codice Belfiore |
| `contribuente_cf` | VARCHAR(20) NULL | |
| `co_intestati_raw` | TEXT NULL | |
| `importo_0648` | Numeric(10,2) NULL | |
| `importo_0985` | Numeric(10,2) NULL | |
| `importo_0668` | Numeric(10,2) NULL | |
| `created_at` | TIMESTAMPTZ | |

Indici: `(avviso_id)`, `(codice_partita)`

---

#### `ruolo_particelle`
Singola particella catastale all'interno di una partita. Fotografia al momento dell'emissione.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `partita_id` | UUID FK → ruolo_partite | |
| `anno_tributario` | Integer NOT NULL | denormalizzato per query temporali |
| `domanda_irrigua` | VARCHAR(10) NULL | colonna DOM. |
| `distretto` | VARCHAR(10) NULL | colonna DIS. |
| `foglio` | VARCHAR(10) NOT NULL | |
| `particella` | VARCHAR(20) NOT NULL | |
| `subalterno` | VARCHAR(10) NULL | |
| `sup_catastale_are` | Numeric(10,4) NULL | SUP.CATA. in are (1 ara = 100 mq) |
| `sup_catastale_ha` | Numeric(10,4) NULL | ettari calcolati (sup_catastale_are / 100) |
| `sup_irrigata_ha` | Numeric(10,4) NULL | |
| `coltura` | VARCHAR(50) NULL | |
| `importo_manut` | Numeric(10,2) NULL | tributo 0648 |
| `importo_irrig` | Numeric(10,2) NULL | tributo 0668 |
| `importo_ist` | Numeric(10,2) NULL | tributo 0985 |
| `catasto_parcel_id` | UUID FK → catasto_parcels NULL | link catastale |
| `created_at` | TIMESTAMPTZ | |

Indici: `(partita_id)`, `(anno_tributario, foglio, particella)`, `(catasto_parcel_id)`

---

### 3.2 Tabella nuova in `catasto`

#### `catasto_parcels`
Registro storico delle particelle catastali. Prima fonte: import Ruolo.
Supporta variazioni nel tempo (frazionamenti, accorpamenti).

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `comune_codice` | VARCHAR(10) NOT NULL | FK → catasto_comuni (stringa) |
| `comune_nome` | VARCHAR(100) NOT NULL | |
| `foglio` | VARCHAR(10) NOT NULL | |
| `particella` | VARCHAR(20) NOT NULL | |
| `subalterno` | VARCHAR(10) NULL | |
| `sup_catastale_ha` | Numeric(10,4) NULL | |
| `valid_from` | Integer NOT NULL | anno tributario di validità inizio |
| `valid_to` | Integer NULL | anno tributario fine (NULL = attivo) |
| `source` | VARCHAR(30) | `ruolo_import` / `sister` / `capacitas` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Indici: `(comune_codice, foglio, particella, subalterno, valid_from)` UNIQUE,
`(comune_codice, foglio, particella)`, `(valid_to)`

**Logica upsert**: stessa superficie → no-op; superficie diversa → chiude record (`valid_to = anno - 1`) + nuovo record; non esiste → crea.

---

### 3.3 Relazione con moduli esistenti

| Modulo | Tabella | Tipo relazione |
|--------|---------|----------------|
| Utenze / Anagrafica | `ana_subjects` → `ana_persons` / `ana_companies` | FK nullable `subject_id`; join via CF/PIVA |
| Catasto | `catasto_comuni` | Lookup per risoluzione comune_codice |
| Catasto | `catasto_parcels` (nuova) | Popolamento da import Ruolo |
| Core | `application_users` | FK `triggered_by` su import_jobs |

---

### 3.4 Enumerazioni

```
RuoloImportStatus: pending | running | completed | failed
CodiceTributo: 0648 | 0985 | 0668
CatastoParcelSource: ruolo_import | sister | capacitas
```

---

## 4. API Endpoints

Tutti sotto prefisso `/ruolo`.

### Import

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `POST` | `/ruolo/import/upload` | Upload file + anno, avvia job asincrono. Ritorna `job_id`. |
| `GET` | `/ruolo/import/jobs` | Lista job (filtro anno, paginazione) |
| `GET` | `/ruolo/import/jobs/{job_id}` | Dettaglio job con contatori e preview errori |

### Avvisi

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/ruolo/avvisi` | Lista avvisi; filtri: `anno`, `subject_id`, `codice_fiscale`, `comune`, `codice_utenza`, `unlinked` |
| `GET` | `/ruolo/avvisi/{avviso_id}` | Dettaglio avviso con partite e particelle |
| `GET` | `/ruolo/soggetti/{subject_id}/avvisi` | Tutti gli avvisi di un soggetto (tutti gli anni) |

### Particelle

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/ruolo/particelle` | Ricerca: `anno`, `foglio`, `particella`, `comune` |
| `GET` | `/catasto/parcels` | (modulo catasto) Lista particelle con storico `valid_from`/`valid_to` |
| `GET` | `/catasto/parcels/{id}/history` | Storico variazioni di una particella |

### Statistiche

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/ruolo/stats` | Aggregati per anno: avvisi totali, importi per tributo, soggetti non collegati |
| `GET` | `/ruolo/stats/comuni` | Ripartizione importi per comune per anno |

---

## 5. Pagine frontend

| Route | Contenuto |
|-------|-----------|
| `/ruolo` | Dashboard: card metriche anno corrente, avvisi non collegati, link rapidi |
| `/ruolo/avvisi` | Lista avvisi con ricerca, filtri, paginazione |
| `/ruolo/avvisi/[avviso_id]` | Dettaglio avviso: dati soggetto, partite per comune, tabella particelle, totali |
| `/ruolo/import` | Upload file + anno, lista job con stato |
| `/ruolo/import/[job_id]` | Log dettagliato job: contatori, preview errori, link agli avvisi importati |
| `/ruolo/stats` | Statistiche e aggregati per anno |

**Integrazione in `/anagrafica/[id]`**: sezione "Ruolo Consortile" con lista avvisi per anno
e importi totali, accesso al dettaglio avviso.

---

## 6. Permessi e ruoli

| Azione | admin | reviewer | viewer |
|--------|-------|----------|--------|
| Upload file Ruolo | ✅ | ❌ | ❌ |
| Visualizza job import | ✅ | ✅ | ❌ |
| Consulta avvisi | ✅ | ✅ | ✅ |
| Consulta particelle | ✅ | ✅ | ✅ |
| Visualizza statistiche | ✅ | ✅ | ✅ |
| Export CSV avvisi | ✅ | ✅ | ❌ |

---

## 7. Regole di business

### 7.1 Matching soggetto
La chiave primaria di collegamento è il **codice fiscale** (persona fisica) o la
**partita IVA** (persona giuridica). Il matching avviene sulla prima riga N2 del blocco
(il CF/PIVA principale). I co-intestati vengono salvati come testo libero
(`co_intestati_raw`), non come FK separate nel MVP.

### 7.2 Idempotenza import
- Chiave univoca: `(codice_cnc, anno_tributario)` su `ruolo_avvisi`
- Re-import dello stesso file: upsert senza duplicati
- Re-import su anno già presente: avvertimento, non blocco automatico
- `catasto_parcels`: logica temporale esplicita, mai sovrascrittura diretta

### 7.3 Storicità particelle
Una particella può cambiare superficie nel tempo per frazionamento o accorpamento.
Il dato in `ruolo_particelle` è una **fotografia storica** dell'anno tributario.
Il dato in `catasto_parcels` è il **registro aggiornato** con tracciamento temporale.
I due livelli coesistono e si collegano via `catasto_parcel_id`.

### 7.4 Avvisi orfani
Un avviso con `subject_id = NULL` non è un errore di sistema: significa che il
contribuente non è ancora censito in GAIA Anagrafica. La lista avvisi deve
supportare filtro `unlinked=true` per permettere all'operatore di fare il censimento.

---

## 8. Considerazioni tecniche

### 8.1 Estrazione testo dal PDF
Il PDF Ruolo è generato da testo pre-formattato, non è una scansione.
L'estrazione con `pypdf` o `pdfminer.six` dovrebbe mantenere la struttura a righe.
Come fallback: accettare il `.dmp` grezzo come `text/plain`.

### 8.2 Parser robusto
Il parser deve essere **fault-tolerant**: errore su una singola partita non deve
interrompere l'intero import. Ogni eccezione per-partita viene loggata e contata
in `records_errors`, l'import continua.

### 8.3 Unità superfici
La colonna `SUP.CATA.` nel file sorgente usa il punto come separatore migliaia e la
virgola come decimale (es. `1.455` = millequattrocentocinquantacinque).
**Unità confermata: are** (1 ara = 100 mq = 0,01 ha).
La colonna DB `sup_catastale_are` contiene il valore in are; `sup_catastale_ha` è il valore
derivato in ettari (are / 100), calcolato al momento dell'import e salvato per comodità.

### 8.4 Performance
~9.800 partite × media 5 particelle = ~49.000 righe `ruolo_particelle` per import.
L'import in background con savepoint per-partita garantisce consistenza senza
bloccare la sessione principale.

---

## 9. Integrazioni future pianificate

- Collegamento co-intestati come FK verso `ana_subjects` (post-MVP)
- Confronto diff tra anni (variazioni importo, nuove/cessate particelle)
- Alimentazione `catasto_parcels` da SISTER e Capacitas come fonti aggiuntive
- Export per riscossione coattiva (passaggio a moduli legali)
- Integrazione con inCASS (Capacitas) per verifica pagamenti

---

## 10. Path canonici

| Livello | Path |
|---------|------|
| Backend | `backend/app/modules/ruolo/` |
| Frontend | `frontend/src/app/ruolo/` |
| Docs | `domain-docs/ruolo/docs/` |
| Migration | `backend/alembic/versions/<timestamp>_add_ruolo_module.py` |
