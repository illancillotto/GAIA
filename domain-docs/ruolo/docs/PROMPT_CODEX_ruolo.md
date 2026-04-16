# Prompt Codex — GAIA Ruolo

> **Regola strutturale vincolante**
> GAIA usa un backend monolitico modulare. Il codice backend del dominio Ruolo va creato in
> `backend/app/modules/ruolo/`. Il frontend vive in `frontend/src/app/ruolo/`.
> Non va creato alcun servizio backend separato.

> Da usare come system prompt o primo messaggio in una sessione Claude Code dedicata.

---

## Contesto del progetto

Stai sviluppando **GAIA Ruolo**, il modulo di gestione del ruolo consortile (tributi)
all'interno della piattaforma **GAIA** per il Consorzio di Bonifica dell'Oristanese.

Il **Ruolo** è il documento amministrativo-contabile con cui il Consorzio formalizza
annualmente per ogni contribuente:
- chi deve pagare (soggetto obbligato)
- quanto deve pagare (avviso di pagamento per tributo)
- per quale annualità
- su quali immobili o terreni si basa il contributo (partite catastali e particelle)

GAIA è una piattaforma IT governance multi-modulo con backend e frontend condivisi:

- **GAIA Accessi** — NAS Audit
- **GAIA Rete** — Network Monitor
- **GAIA Inventario** — IT Inventory
- **GAIA Catasto** — Servizi AdE / visure SISTER
- **GAIA Anagrafica (Utenze)** — Registro soggetti con dati anagrafici
- **GAIA Ruolo** — Tributi consortili (questo modulo)

Il repository si trova su `github.com/illancillotto/GAIA`.

---

## Documenti di riferimento obbligatori

Prima di scrivere qualsiasi codice, leggi questi file per capire i pattern reali:

```
backend/app/modules/utenze/models.py          # modello AnagraficaSubject, FK UUID
backend/app/modules/utenze/schemas.py         # pattern schema Pydantic
backend/app/modules/catasto/models.py         # modello catasto_comuni (foglio/particella)
backend/app/modules/elaborazioni/router.py    # pattern router modulo
backend/app/services/elaborazioni_bonifica_sync.py  # pattern job asincrono tracking
backend/alembic/versions/20260410_0038_add_wc_sync_job_and_operazioni_wc_fields.py  # pattern migration
backend/app/core/config.py                    # settings globali
backend/app/main.py                           # registrazione router
```

---

## Vincoli architetturali

- Backend monolite modulare FastAPI in `backend/app/modules/ruolo/`
- Frontend unico Next.js in `frontend/src/app/ruolo/`
- Database PostgreSQL condiviso, tabelle `ruolo_*` e aggiornamenti `catasto_*`
- Auth: tabella `application_users`, PK **Integer** (non UUID!)
- Soggetti: tabella `ana_subjects`, PK **UUID**
  - Join via `ana_persons.codice_fiscale` o `ana_companies.partita_iva`
  - Il modulo Ruolo NON crea soggetti, legge solo da `ana_subjects`
- Migrazioni solo in `backend/alembic/versions/` senza modificare revisioni esistenti
- Nessun import cross-modulo diretto: usare solo FK stringa nei modelli SQLAlchemy

---

## Il file sorgente: formato `.dmp` / PDF del Ruolo

Il Consorzio riceve annualmente un file dal sistema **Capacitas** (software tributi consortili)
che viene esportato come PDF. Il file Ruolo 2024 ha circa 9.810 "partite" (pagine).

### Struttura del file

Il file è testo strutturato con marcatori espliciti di inizio e fine partita:

```
<qm500>--Partita CNC 01.02024000000202--------<017.743><01.A><02024000000202><inizio>
...corpo della partita...
----------------<017.743><01.A><02024000000202><-fine->
```

### Anatomy di una partita CNC

```
<inizio>
N2 MCCPLA69E23F272E 00000000 00 N           ← CF/PIVA + campi sconosciuti (conservare as-is)
MACCIONI PAOLO 23.05.1969 F272 MOGORO(OR)   ← Nome Cognome DataNascita CodComune Comune(Prov)
Dom: VIA POD.113 CASA 49 MORIMENTA 00000 09095 F272 MOGORO(OR)  ← domicilio
Res: 00000 00000 ( )                        ← residenza (può essere vuota)

NP  4  PARTITA 0A1102766/00000 BENI IN COMUNE DI PABILLONIS   ← inizio partita catastale
NP  5  CONTRIBUENTE: MACCIONI PAOLO     C.F. MCCPLA69E23F272E
NP  6  CO-INTESTATO CON: CASU MARIA ELENA    ← opzionale, può non esserci
NP  7  ANNO TRIB DESCRIZIONE                                     RUOLO
NP  8  2024 0648 BENI IN PABILLONIS - CONTRIBUTO OPERE IRRIGUE  6,05 EURO
NP  9  2024 0985 BENI IN PABILLONIS - CONSORZIO QUOTE ORDINARIE 4,32 EURO
NP  10 DOM. DIS. FOG. PART. SUB  SUP.CATA.  SUP.IRR. COLT. MANUT. IRRIG. IST.
NP  11       292    1  361       63          0,23          0,16
NP  12       292    1  390    1.455          5,30          3,78
...
N4
    2024 0985  1.679.520  36,40  (L. 70.480 )
    OPERE DI BONIFICA (UTENZA 024000002)
N4
    2024 0648  1.679.520  50,94  (L. 98.634 )
    OPERE DI BONIFICA (UTENZA 024000002)
<-fine->
```

### Codici tributo

| Codice | Etichetta | Tipo | Colonna dettaglio particella |
|--------|-----------|------|------------------------------|
| `0648` | MANUTENZIONE | Fisso (ettari × coltura × impianti) | `MANUT.` |
| `0985` | ISTITUZIONALE | Fisso (ettari × coltura) | `IST.` |
| `0668` | IRRIGAZIONE | Variabile (consumo acqua) | `IRRIG.` |

### Valori N4 (totali avviso)

Le righe N4 contengono i totali per tributo a livello di avviso:
```
2024 0985  1.679.520  36,40  (L. 70.480 )
OPERE DI BONIFICA (UTENZA 024000002)
```
- `1.679.520` = campo sconosciuto — significato non determinato, conservare as-is in `n4_campo_sconosciuto`
- `36,40` = importo totale tributo 0985 sull'intero avviso (Euro)
- `(L. 70.480 )` = controvalore in Lire (conservare come dato storico)
- `UTENZA 024000002` = codice utenza consortile → salvare sull'avviso

---

## Modello dati da implementare

### Decisione critica: storicità particelle catastali

Le particelle cambiano nel tempo: frazionamenti, accorpamenti, variazioni di superficie.
Il Ruolo fotografa lo stato al momento dell'emissione (anno tributario).
**Il modello catastale deve supportare la temporalità**: la stessa particella
(comune/foglio/numero) può avere superfici diverse in anni diversi.

### Tabelle nuove: `ruolo_*`

#### `ruolo_import_jobs`
Job di import asincrono del file Ruolo.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `anno_tributario` | Integer NOT NULL | es. 2024 |
| `filename` | VARCHAR(300) | nome file originale |
| `status` | VARCHAR(20) | `pending` / `running` / `completed` / `failed` |
| `started_at` | TIMESTAMPTZ | |
| `finished_at` | TIMESTAMPTZ NULL | |
| `total_partite` | Integer NULL | partite trovate nel file |
| `records_imported` | Integer NULL | |
| `records_skipped` | Integer NULL | soggetto non trovato in anagrafica |
| `records_errors` | Integer NULL | |
| `error_detail` | Text NULL | preview errori (max 20 righe) |
| `triggered_by` | Integer FK → application_users | |
| `params_json` | JSONB NULL | metadati runtime (range, durata, etc.) |
| `created_at` | TIMESTAMPTZ | |

Indici: `(anno_tributario)`, `(status)`

---

#### `ruolo_avvisi`
Un avviso di pagamento per soggetto per anno.
Corrisponde a una "Partita CNC" nel file sorgente.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `import_job_id` | UUID FK → ruolo_import_jobs | |
| `codice_cnc` | VARCHAR(50) NOT NULL | es. `01.02024000000202` |
| `anno_tributario` | Integer NOT NULL | es. 2024 |
| `subject_id` | UUID FK → ana_subjects NULL | NULL se soggetto non trovato |
| `codice_fiscale_raw` | VARCHAR(20) | CF/PIVA estratto dal file (sempre salvare) |
| `nominativo_raw` | VARCHAR(300) | riga nominativo estratta dal file |
| `domicilio_raw` | TEXT NULL | |
| `residenza_raw` | TEXT NULL | |
| `n2_extra_raw` | VARCHAR(100) NULL | i campi `00000000 00 N` della riga N2 (conservare as-is) |
| `codice_utenza` | VARCHAR(30) NULL | es. `024000002` da riga "OPERE DI BONIFICA (UTENZA …)" |
| `importo_totale_0648` | Numeric(12,2) NULL | totale MANUTENZIONE sull'avviso |
| `importo_totale_0985` | Numeric(12,2) NULL | totale ISTITUZIONALE sull'avviso |
| `importo_totale_0668` | Numeric(12,2) NULL | totale IRRIGAZIONE sull'avviso |
| `importo_totale_euro` | Numeric(12,2) NULL | somma dei tre tributi |
| `n4_campo_sconosciuto` | VARCHAR(30) NULL | terzo campo riga N4 (es. `1.679.520`) — significato non determinato, conservare as-is |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Indici: `(codice_cnc)` UNIQUE, `(anno_tributario, subject_id)`, `(codice_fiscale_raw)`, `(subject_id)`

---

#### `ruolo_partite`
Ogni avviso può contenere più partite catastali (più comuni).

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `avviso_id` | UUID FK → ruolo_avvisi | |
| `codice_partita` | VARCHAR(30) NOT NULL | es. `0A1102766/00000` |
| `comune_nome` | VARCHAR(100) NOT NULL | es. `PABILLONIS` |
| `comune_codice` | VARCHAR(10) NULL | codice Belfiore se noto (join con `catasto_comuni`) |
| `contribuente_cf` | VARCHAR(20) NULL | CF del contribuente indicato nella partita |
| `co_intestati_raw` | TEXT NULL | riga "CO-INTESTATO CON: …" completa |
| `importo_0648` | Numeric(10,2) NULL | |
| `importo_0985` | Numeric(10,2) NULL | |
| `importo_0668` | Numeric(10,2) NULL | |
| `created_at` | TIMESTAMPTZ | |

Indici: `(avviso_id)`, `(codice_partita)`

---

#### `ruolo_particelle`
Singola particella catastale all'interno di una partita.
**Punto chiave**: questa tabella è la fotografia storica al momento dell'emissione del ruolo.
Non sovrascrive né sostituisce i dati catastali aggiornati.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `partita_id` | UUID FK → ruolo_partite | |
| `anno_tributario` | Integer NOT NULL | denormalizzato per query temporali |
| `domanda_irrigua` | VARCHAR(10) NULL | colonna DOM. |
| `distretto` | VARCHAR(10) NULL | colonna DIS. |
| `foglio` | VARCHAR(10) NOT NULL | |
| `particella` | VARCHAR(20) NOT NULL | es. `361` o `41` |
| `subalterno` | VARCHAR(10) NULL | es. `A`, `C`, numerico |
| `sup_catastale_are` | Numeric(10,4) NULL | SUP.CATA. in are (1 ara = 100 mq = 0,01 ha) — confermato |
| `sup_catastale_ha` | Numeric(10,4) NULL | ettari derivati (are / 100), calcolati all'import |
| `sup_irrigata_ha` | Numeric(10,4) NULL | SUP.IRR. |
| `coltura` | VARCHAR(50) NULL | COLT. se presente |
| `importo_manut` | Numeric(10,2) NULL | MANUT. (0648) |
| `importo_irrig` | Numeric(10,2) NULL | IRRIG. (0668) |
| `importo_ist` | Numeric(10,2) NULL | IST. (0985) |
| `catasto_parcel_id` | UUID FK → catasto_parcels NULL | collegamento alla tabella catastale (vedi sotto) |
| `created_at` | TIMESTAMPTZ | |

Indici: `(partita_id)`, `(anno_tributario, foglio, particella)`, `(catasto_parcel_id)`

---

### Tabelle aggiornate: `catasto_*`

#### `catasto_parcels` ← NUOVA

Questa tabella non esiste ancora. Il modulo Ruolo la introduce come primo popolamento
dei dati catastali di base. In futuro potrà essere alimentata anche da SISTER/Capacitas.

**Design temporale**: ogni record rappresenta una particella in un intervallo temporale.
Quando una particella viene frazionata o accorpata, il record viene chiuso (`valid_to`)
e ne vengono creati di nuovi.

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | UUID PK | |
| `comune_codice` | VARCHAR(10) NOT NULL | codice Belfiore, FK verso `catasto_comuni` |
| `comune_nome` | VARCHAR(100) NOT NULL | |
| `foglio` | VARCHAR(10) NOT NULL | |
| `particella` | VARCHAR(20) NOT NULL | |
| `subalterno` | VARCHAR(10) NULL | |
| `sup_catastale_are` | Numeric(10,4) NULL | in are (unità confermata) |
| `sup_catastale_ha` | Numeric(10,4) NULL | ettari derivati (are / 100) |
| `valid_from` | Integer NOT NULL | anno tributario da cui il record è valido |
| `valid_to` | Integer NULL | anno tributario fino a cui è valido (NULL = ancora attivo) |
| `source` | VARCHAR(30) | `ruolo_import` / `sister` / `capacitas` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Indici: `(comune_codice, foglio, particella, subalterno, valid_from)`,
`(comune_codice, foglio, particella)` — per ricerche senza subalterno

**Logica upsert durante import Ruolo**:
- Se esiste un record con stesso (comune, foglio, particella, subalterno) con `valid_to IS NULL`
  e stessa superficie → non fare nulla, solo linkare via `catasto_parcel_id`
- Se esiste ma superficie diversa → chiudere il record esistente (`valid_to = anno - 1`)
  e creare un nuovo record con `valid_from = anno`
- Se non esiste → creare nuovo record

---

## Parser del file `.dmp`

Il parser è il cuore del modulo. Deve essere implementato in
`backend/app/modules/ruolo/services/parser.py`.

### Algoritmo di parsing

```python
# Pseudocodice — implementare in Python reale

def parse_ruolo_file(raw_text: str) -> list[PartitaCNC]:
    """
    Divide il testo per marcatori <inizio>/<-fine-> ed estrae ogni partita.
    Resistente a righe malformate: loggare warning senza interrompere.
    """

    # 1. Split per marcatore <inizio>
    blocks = re.split(r'<inizio>', raw_text)

    for block in blocks[1:]:  # il primo elemento è l'header del file
        # 2. Estrai codice CNC dal marcatore precedente
        cnc_match = re.search(r'Partita CNC ([\d.]+)', block_header)

        # 3. Riga N2: CF/PIVA + campi extra
        # "N2 MCCPLA69E23F272E 00000000 00 N"
        n2_match = re.match(r'^N2\s+(\S+)\s+(.*)', first_line)
        codice_fiscale_raw = n2_match.group(1)
        n2_extra_raw = n2_match.group(2)

        # 4. Riga nominativo (seconda riga dopo N2)
        # "MACCIONI PAOLO 23.05.1969 F272 MOGORO(OR)"
        nominativo_raw = next_line

        # 5. Dom: e Res:
        domicilio_raw = parse_dom_line(...)
        residenza_raw = parse_res_line(...)

        # 6. Parse partite catastali (NP 4 PARTITA ...)
        for each block starting with "NP X PARTITA":
            codice_partita = ...
            comune_nome = ...

            # 6a. Tributi per partita (NP X 2024 YYYY DESCRIZIONE IMPORTO EURO)
            tributi = parse_tributi_lines(...)

            # 6b. CO-INTESTATO se presente
            co_intestati_raw = ...

            # 6c. Righe particelle (NP XX  292  1  361  63  0,23  0,16)
            particelle = []
            for each detail_line after DOM.DIS.FOG. header:
                particella = parse_particella_line(line)
                particelle.append(particella)

        # 7. Righe N4 (totali avviso + codice utenza)
        n4_blocks = parse_n4_blocks(block)
        importo_totale_0648 = ...
        importo_totale_0985 = ...
        codice_utenza = ...   # da "OPERE DI BONIFICA (UTENZA XXXXXXXXX)"
```

### Note critiche sul parsing

**Separatore decimale**: il file usa la virgola come separatore decimale italiano
(`6,05` → `6.05`). Convertire sempre prima del cast a float/Decimal.

**Separatore migliaia**: il punto viene usato come separatore migliaia nei numeri grandi
(`1.455` → 1455). Rimuovere i punti migliaia prima del cast a Decimal.

**Superfici**: `SUP.CATA.` è in **are** (unità confermata). `1.455` = 1455 are = 14,55 ha.
Convertire rimuovendo il punto migliaia, poi dividere per 100 per ottenere ettari.
Salvare entrambe le colonne: `sup_catastale_are` (valore letto) e `sup_catastale_ha` (are / 100).

**Riga N4**: le righe N4 sono la sezione di totali. Appaiono FUORI dai blocchi NP,
dopo la LEGENDA. Pattern:
```
N4
    2024 0985  1.679.520  36,40  (L. 70.480 )
    OPERE DI BONIFICA (UTENZA 024000002)
```

**Codice utenza**: estrarre il numero dopo `UTENZA ` con regex `r'UTENZA\s+(\d+)'`.
Può comparire più volte per tributo; usare il primo trovato (sono uguali).

**Soggetto non trovato**: se il CF/PIVA non corrisponde a nessun `ana_subjects`,
l'avviso viene comunque creato con `subject_id = NULL` e `codice_fiscale_raw` valorizzato.
Contare come `records_skipped` nel job.

---

## Struttura modulo backend

```
backend/app/modules/ruolo/
├── __init__.py
├── bootstrap.py          # section keys + flag modulo
├── enums.py              # RuoloImportStatus
├── models.py             # 4 tabelle SQLAlchemy
├── schemas.py            # Pydantic I/O
├── repositories.py       # query layer
├── services/
│   ├── parser.py         # parser file .dmp/PDF
│   ├── import_service.py # orchestrazione job asincrono
│   └── query_service.py  # query UI (avvisi, particelle)
└── routes/
    ├── __init__.py
    ├── import_routes.py  # upload + job tracking
    └── query_routes.py   # consultazione avvisi e particelle
```

---

## API Endpoints

Tutti sotto prefisso `/ruolo`.

### Import

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `POST` | `/ruolo/import/upload` | Upload file PDF/DMP, avvia job asincrono. Accetta `multipart/form-data` con `file` + `anno_tributario`. Ritorna job_id. |
| `GET` | `/ruolo/import/jobs` | Lista job (paginata, filtro anno) |
| `GET` | `/ruolo/import/jobs/{job_id}` | Dettaglio job con contatori e preview errori |

### Consultazione

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/ruolo/avvisi` | Lista avvisi con filtri: `anno`, `subject_id`, `codice_fiscale`, `codice_utenza`, `comune`, paginazione |
| `GET` | `/ruolo/avvisi/{avviso_id}` | Dettaglio avviso con partite, particelle e link soggetto |
| `GET` | `/ruolo/soggetti/{subject_id}/avvisi` | Tutti gli avvisi di un soggetto per anno |
| `GET` | `/ruolo/particelle` | Ricerca particelle: `anno`, `foglio`, `particella`, `comune` |
| `GET` | `/ruolo/stats` | Aggregati per anno: totale avvisi, totale importi per tributo |

---

## Job asincrono — Pattern

Seguire il pattern di `elaborazioni_bonifica_sync.py` / `wc_sync_job`:

```python
# import_routes.py
@router.post("/import/upload")
async def upload_ruolo(
    file: UploadFile,
    anno_tributario: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # 1. Creare record job con status=pending
    job = create_import_job(db, anno=anno_tributario, filename=file.filename, user=current_user)
    # 2. Leggere contenuto file (PDF → estrai testo con pdfminer o pypdf2, oppure
    #    accettare anche il .dmp grezzo come text/plain)
    raw_content = await file.read()
    # 3. Avviare background task
    background_tasks.add_task(run_import_job, job.id, raw_content, anno_tributario)
    return {"job_id": str(job.id), "status": "pending"}


async def run_import_job(job_id: UUID, raw_content: bytes, anno: int):
    # Apre nuova sessione DB (non riusare quella della request)
    with get_db_session() as db:
        job = db.get(RuoloImportJob, job_id)
        job.status = "running"
        db.commit()
        try:
            text = extract_text_from_content(raw_content)
            partite = parse_ruolo_file(text)
            job.total_partite = len(partite)
            db.commit()

            imported = skipped = errors = 0
            error_lines = []

            for partita in partite:
                try:
                    upsert_avviso(db, partita, anno)
                    imported += 1
                except SubjectNotFound:
                    skipped += 1
                except Exception as e:
                    errors += 1
                    error_lines.append(str(e))

            job.status = "completed"
            job.records_imported = imported
            job.records_skipped = skipped
            job.records_errors = errors
            job.error_detail = "\n".join(error_lines[:20]) if error_lines else None
        except Exception as e:
            job.status = "failed"
            job.error_detail = str(e)
        finally:
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
```

### Estrazione testo dal PDF

Il file sorgente è un PDF generato da testo pre-formattato (non scansione).
Usare `pypdf` (già in requirements) o `pdfminer.six` per l'estrazione.
Verificare che il testo estratto mantenga la struttura a righe del formato `.dmp`.
Se il PDF ha un layout a colonne che rompe l'estrazione, accettare anche il `.dmp`
grezzo come upload alternativo (`Content-Type: text/plain`).

---

## Integrazione con `catasto_parcels`

Durante l'import, per ogni `ruolo_particella`:

1. Risolvere il `comune_codice` da `comune_nome` usando la tabella `catasto_comuni`
   (già popolata). Se non trovato: loggare warning, lasciare `catasto_parcel_id = NULL`.

2. Applicare la logica upsert temporale descritta sopra.

3. Popolare `ruolo_particelle.catasto_parcel_id` con l'UUID del record
   `catasto_parcels` trovato o creato.

---

## Migration Alembic

Creare `backend/alembic/versions/<timestamp>_add_ruolo_module.py`.

Tabelle da creare nell'ordine:
1. `ruolo_import_jobs`
2. `ruolo_avvisi`
3. `ruolo_partite`
4. `ruolo_particelle`
5. `catasto_parcels`

---

## Bootstrap modulo

In `backend/app/modules/ruolo/bootstrap.py`, aggiungere:

```python
RUOLO_SECTIONS = [
    {"key": "ruolo.dashboard",  "label": "Ruolo — Dashboard",   "module": "ruolo"},
    {"key": "ruolo.avvisi",     "label": "Ruolo — Avvisi",       "module": "ruolo"},
    {"key": "ruolo.import",     "label": "Ruolo — Import",       "module": "ruolo"},
    {"key": "ruolo.stats",      "label": "Ruolo — Statistiche",  "module": "ruolo"},
]
```

In `backend/app/modules/core/models.py` (o dove risiede `ApplicationUser`),
aggiungere il flag `module_ruolo: bool = False`.

Registrare il router in `backend/app/api/router.py`.

---

## Frontend

### Route

```
frontend/src/app/ruolo/
├── page.tsx                     # Dashboard / landing
├── avvisi/
│   ├── page.tsx                 # Lista avvisi con filtri
│   └── [avviso_id]/page.tsx     # Dettaglio avviso
├── import/
│   ├── page.tsx                 # Upload + lista job
│   └── [job_id]/page.tsx        # Log dettagliato job
└── stats/page.tsx               # Statistiche per anno
```

### Componenti chiave

**`AvvisoDetail`**: mostra dati soggetto (con link alla scheda anagrafica), elenco partite
per comune, tabella particelle con colonne foglio / particella / subalterno / sup. catastale /
sup. irrigata / importi 0648 / 0985 / 0668, totali avviso.

**`RuoloImportWorkspace`**: upload drag-and-drop, campo anno tributario, pulsante avvia,
polling stato job ogni 3 secondi mentre `status = running`, progress bar con contatori.

**`RuoloStats`**: card per anno con totale avvisi, totale importi per tributo (0648/0985/0668),
numero soggetti non trovati in anagrafica.

### API client

Creare `frontend/src/lib/api/ruolo.ts` con funzioni tipizzate per tutti gli endpoint.
Pattern: seguire `frontend/src/lib/api/anagrafica.ts` o analogo esistente.

---

## Integrazione con modulo Utenze / Anagrafica

- Nella scheda soggetto (`/anagrafica/[id]`), aggiungere una sezione "Ruolo Consortile"
  che mostra gli avvisi per anno (chiamata a `GET /ruolo/soggetti/{subject_id}/avvisi`).
- Il componente va aggiunto come tab o sezione collassabile in
  `frontend/src/components/utenze/` seguendo il pattern delle `catasto_documents`
  già presenti in `AnagraficaSubjectDetailResponse`.

---

## Sequenza di lavoro consigliata

1. **Migration** — creare le 5 tabelle con tutti gli indici
2. **Modelli ORM** — `ruolo/models.py` + aggiornamento `catasto_parcels`
3. **Parser** — `ruolo/services/parser.py` con test unitari su sample del file allegato
4. **Import service** — job asincrono + upsert `catasto_parcels`
5. **Repository + Schemas** — layer query e DTO
6. **Routes backend** — import + query
7. **Bootstrap** — section keys + flag modulo
8. **Test backend** — almeno: parse sample, import idempotente, avviso non duplicato su re-import
9. **Frontend** — API client → pagine in ordine: import → avvisi lista → avviso dettaglio → stats
10. **Integrazione anagrafica** — sezione "Ruolo Consortile" nella scheda soggetto

---

## Regole di idempotenza

- Re-import dello stesso `anno_tributario` con lo stesso file NON crea duplicati.
  Usare `(codice_cnc, anno_tributario)` come chiave di upsert su `ruolo_avvisi`.
- Prima di un nuovo import su anno già presente, il job deve verificare se esistono
  avvisi per quell'anno e avvertire l'operatore (senza bloccare automaticamente).
- `catasto_parcels`: applicare la logica temporale — mai modificare `valid_from`/`valid_to`
  di record precedenti senza ragione esplicita.

---

## Note finali

- Il campo `n2_extra_raw` (`00000000 00 N`) è sconosciuto nel dominio attuale.
  Conservarlo sempre come stringa per analisi futura.
- I numeri in Lire nelle righe N4 `(L. 70.480 )` sono dati storici.
  Conservarli come colonna `importo_lire` su `ruolo_avvisi` (opzionale, nullable).
- La colonna `COLT.` (coltura) nelle righe particelle compare raramente nel sample.
  Gestirla come nullable senza lanciare errore se assente.
- Priorità FK tipo discipline: `application_users.id` è **Integer**, `ana_subjects.id` è **UUID**.
  Verificare sempre prima di definire colonne FK.
- Il campo `n4_campo_sconosciuto` (terzo valore numerico nella riga N4, es. `1.679.520`)
  ha significato non determinato nel dominio attuale. Conservarlo as-is come VARCHAR(30).
  Non tentare di interpretarlo come superficie, rendita o importo.
