# GAIA Ruolo — Execution Plan v1.0

> Consorzio di Bonifica dell'Oristanese — Aprile 2026

---

## Milestone

| Milestone | Etichetta | Descrizione |
|-----------|-----------|-------------|
| M0 | Analisi e design | PRD, Execution Plan, Prompt Codex, docs |
| M1 | Fondazione backend | Migration, modelli ORM, parser core, import job |
| M2 | API e query layer | Repository, schemas, tutti gli endpoint |
| M3 | Bootstrap e integrazione | Section keys, flag modulo, integrazione anagrafica |
| M4 | Frontend | Dashboard, avvisi, import, stats, integrazione scheda soggetto |
| M5 | Hardening | Test, permessi, export CSV, idempotenza verificata su dati reali |

---

## Fase 1 — Fondazione backend (M1)

### 1.1 Migration Alembic

Creare `backend/alembic/versions/<timestamp>_add_ruolo_module.py`.

Tabelle nell'ordine:
1. `ruolo_import_jobs`
2. `ruolo_avvisi`
3. `ruolo_partite`
4. `ruolo_particelle`
5. `catasto_parcels`

Verificare dipendenza: `catasto_comuni` deve già esistere (usata per lookup comune_codice).

**Done when**: `alembic upgrade head` applicato, tutte le tabelle presenti, `alembic downgrade` funzionante.

---

### 1.2 Modelli ORM

Creare `backend/app/modules/ruolo/models.py` con le quattro classi SQLAlchemy:
`RuoloImportJob`, `RuoloAvviso`, `RuoloPartita`, `RuoloParticella`.

Creare (o aggiornare) `backend/app/modules/catasto/models.py` aggiungendo `CatastoParcel`.

Registrare i nuovi modelli nel bootstrap metadata del backend.

**Vincoli FK**:
- `triggered_by` → `ForeignKey("application_users.id")`, tipo `Mapped[int]`
- `subject_id` → `ForeignKey("ana_subjects.id")`, tipo `Mapped[uuid.UUID | None]`
- Nessun import cross-modulo diretto: usare solo FK stringa

**Done when**: `from app.modules.ruolo.models import *` funzionante, nessun errore ORM.

---

### 1.3 Enumerazioni

Creare `backend/app/modules/ruolo/enums.py`:

```python
class RuoloImportStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class CodiceTributo(str, Enum):
    manutenzione = "0648"
    istituzionale = "0985"
    irrigazione = "0668"

class CatastoParcelSource(str, Enum):
    ruolo_import = "ruolo_import"
    sister = "sister"
    capacitas = "capacitas"
```

---

### 1.4 Parser — `ruolo/services/parser.py`

Il parser è il componente più critico. Implementare per step:

**Step A — split partite**
```
Dividere il testo grezzo sul marcatore <inizio>.
Ogni blocco termina su <-fine->.
Estrarre codice_cnc dal marcatore precedente.
Regex: r'Partita CNC ([\d.]+)'
```

**Step B — riga N2 e nominativo**
```
N2 <CF/PIVA> <extra_fields>
<Nominativo> <data_nascita> <cod_comune> <comune>(prov)
Dom: <domicilio>
Res: <residenza>
```

**Step C — partite catastali (blocchi NP)**
```
NP X PARTITA <codice_partita>/00000 BENI IN COMUNE DI <comune>
NP X CONTRIBUENTE: ... C.F. ...
NP X CO-INTESTATO CON: ... (opzionale)
NP X ANNO TRIB DESCRIZIONE RUOLO
NP X 2024 0648 ... importo EURO
NP X 2024 0985 ... importo EURO
NP X DOM. DIS. FOG. PART. SUB SUP.CATA. SUP.IRR. COLT. MANUT. IRRIG. IST.
NP X ... riga particella ...
```

**Step D — righe particelle**
```
Colonne fisse (whitespace-split dopo l'header DOM./DIS./...):
[dom, dis, foglio, particella, sub?, sup_cata, sup_irr, colt?, manut, irrig, ist]
Gestire colonne opzionali (sub, colt).
Virgola → punto per separatori decimali.
Punto come separatore migliaia: distinguere dal contesto.
```

**Step E — righe N4 (totali avviso)**
```
Regex: r'^N4\s*$' seguito da due righe:
Riga 1: anno tributo superficie importo (L. lire)
Riga 2: OPERE DI BONIFICA (UTENZA XXXXXXXXX)
Estrarre codice_utenza: r'UTENZA\s+(\d+)'
```

**Fault tolerance**: ogni partita in try/except, log warning + increment errors, continua.

**Test unitari obbligatori** (file: `backend/tests/ruolo/test_parser.py`):
- parse delle due partite di esempio dal file allegato
- parse nominativo PF con domicilio valorizzato e residenza vuota
- parse partita con co-intestato
- parse particella con subalterno letterale (es. `A`, `C`)
- parse N4 con estrazione codice utenza
- gestione riga malformata senza interruzione

**Done when**: tutti i test parser passanti sul sample reale.

---

### 1.5 Import service — `ruolo/services/import_service.py`

Orchestrazione job asincrono. Seguire il pattern `elaborazioni_bonifica_sync.py`.

```python
async def run_import_job(job_id, raw_content, anno):
    # apri sessione DB separata dalla request
    # status = running
    # extract_text_from_content (PDF → testo, o testo grezzo)
    # parse_ruolo_file → lista partite
    # job.total_partite = len(partite); commit
    # for partita in partite:
    #   try: upsert_avviso(db, partita, anno)
    #       → resolve_subject (CF/PIVA → ana_subjects)
    #       → upsert ruolo_avvisi
    #       → upsert ruolo_partite
    #       → upsert ruolo_particelle
    #       → upsert_catasto_parcel (temporale)
    #   except SubjectNotFound: skipped++
    #   except Exception: errors++; log
    # status = completed / failed
    # finished_at, contatori, error_detail
```

**Funzione `upsert_catasto_parcel`**:
```
1. Resolve comune_codice da catasto_comuni (fallback: None + warning)
2. Cerca record esistente con valid_to IS NULL e stessa chiave
3. Superficie uguale → solo ritorna l'UUID (no-op)
4. Superficie diversa → valid_to = anno - 1, crea nuovo record
5. Nessun record → crea con valid_from = anno
```

**Done when**: import completo del sample 2 pagine, contatori corretti, nessun duplicato su re-run.

---

## Fase 2 — API e query layer (M2)

### 2.1 Schemas — `ruolo/schemas.py`

Input:
- `RuoloImportUploadRequest`: `anno_tributario: int`
- `RuoloAvvisiFilterParams`: `anno`, `subject_id`, `codice_fiscale`, `comune`, `codice_utenza`, `unlinked`, `page`, `page_size`

Output:
- `RuoloImportJobResponse`: tutti i campi + `duration_seconds` calcolato
- `RuoloImportJobListResponse`: `items`, `total`, `page`, `page_size`
- `RuoloAvvisoListItemResponse`: dati riassuntivi + display_name soggetto se collegato
- `RuoloAvvisoListResponse`: `items`, `total`, `page`, `page_size`
- `RuoloParticellaResponse`: tutti i campi + `comune_nome` denormalizzato
- `RuoloPartitaResponse`: metadati + lista `particelle`
- `RuoloAvvisoDetailResponse`: dati completi + lista `partite` con `particelle`
- `RuoloStatsResponse`: aggregati per anno

---

### 2.2 Repository — `ruolo/repositories.py`

- `get_job(db, job_id)`
- `list_jobs(db, anno, page, page_size)`
- `get_avviso(db, avviso_id)` — eager load partite + particelle
- `list_avvisi(db, filters)` — con join a `ana_persons` / `ana_companies` per display_name
- `list_avvisi_by_subject(db, subject_id)`
- `search_particelle(db, anno, foglio, particella, comune)`
- `get_stats(db, anno)`

---

### 2.3 Routes

**`ruolo/routes/import_routes.py`**:
- `POST /ruolo/import/upload` — upload multipart, crea job, avvia background task
- `GET /ruolo/import/jobs` — lista job
- `GET /ruolo/import/jobs/{job_id}` — dettaglio job

**`ruolo/routes/query_routes.py`**:
- `GET /ruolo/avvisi`
- `GET /ruolo/avvisi/{avviso_id}`
- `GET /ruolo/soggetti/{subject_id}/avvisi`
- `GET /ruolo/particelle`
- `GET /ruolo/stats`
- `GET /ruolo/stats/comuni`

**`ruolo/router.py`**: aggregare i due router, prefisso `/ruolo`.

**Done when**: tutti gli endpoint rispondono con dati corretti su import completato.

---

## Fase 3 — Bootstrap e integrazione (M3)

### 3.1 Bootstrap modulo

In `backend/app/modules/ruolo/bootstrap.py`:
```python
RUOLO_SECTIONS = [
    {"key": "ruolo.dashboard",  "label": "Ruolo — Dashboard",   "module": "ruolo"},
    {"key": "ruolo.avvisi",     "label": "Ruolo — Avvisi",       "module": "ruolo"},
    {"key": "ruolo.import",     "label": "Ruolo — Import",       "module": "ruolo"},
    {"key": "ruolo.stats",      "label": "Ruolo — Statistiche",  "module": "ruolo"},
]
```

Aggiungere `module_ruolo: bool = False` in `ApplicationUser`.
Aggiornare `enabled_modules` e gli schemi auth/users.
Aggiornare `backend/app/scripts/bootstrap_sections.py`.
Registrare il router in `backend/app/api/router.py`.

### 3.2 Integrazione scheda soggetto (anagrafica)

Nel backend: verificare che `GET /ruolo/soggetti/{subject_id}/avvisi` sia accessibile
con auth standard.

Nel frontend: aggiungere sezione "Ruolo Consortile" in
`frontend/src/components/utenze/` (o analogo component di dettaglio soggetto).
Pattern: seguire `catasto_documents` già presente in `AnagraficaSubjectDetailResponse`.

**Done when**: scheda soggetto mostra avvisi per anno, link a dettaglio funzionante.

---

## Fase 4 — Frontend (M4)

### 4.1 API client

Creare `frontend/src/lib/api/ruolo.ts` con funzioni tipizzate per tutti gli endpoint.
Types TypeScript in `frontend/src/types/ruolo.ts`.

### 4.2 Pagine (ordine implementazione)

**1. Import workspace** — `/ruolo/import`
- Drag-and-drop upload, campo anno tributario, pulsante avvia
- Lista job con stato badge, contatori, link al log
- Polling ogni 3 secondi mentre `status = running`

**2. Log job** — `/ruolo/import/[job_id]`
- Header: anno, file, durata, stato
- Card contatori: importati / skipped / errori / totale partite
- Tabella preview errori (max 20 righe)
- Avviso se avvisi già presenti per l'anno

**3. Lista avvisi** — `/ruolo/avvisi`
- Filtri: anno (select), ricerca CF/nominativo, comune, solo non collegati
- Tabella: CF/PIVA, nominativo, anno, comuni, importo totale, stato collegamento
- Paginazione server-side

**4. Dettaglio avviso** — `/ruolo/avvisi/[avviso_id]`
- Card soggetto (con link a scheda anagrafica se collegato; badge "non censito" se NULL)
- Sezione riepilogo importi (card per tributo + totale)
- Per ogni partita: header comune + tabella particelle
  (colonne: foglio / particella / sub / sup. cata. / sup. irr. / manut. / irrig. / ist.)
- Codice utenza consortile

**5. Dashboard** — `/ruolo`
- Card anno corrente: n. avvisi, totale 0648, totale 0985, totale 0668
- Badge avvisi non collegati ad anagrafica
- Link rapidi: import, lista avvisi, statistiche

**6. Statistiche** — `/ruolo/stats`
- Select anno
- Totali per tributo, n. soggetti, superficie totale
- Tabella ripartizione per comune

**Done when**: flusso completo navigabile, lint e type check verdi.

---

## Fase 5 — Hardening (M5)

### 5.1 Test backend

File: `backend/tests/ruolo/`

Test obbligatori:
- `test_parser.py`: 6+ test unitari sul parser (già descritti in M1)
- `test_import.py`:
  - import sample 2 partite → contatori corretti
  - re-import idempotente → nessun duplicato
  - partita con CF non in anagrafica → skipped, non errore
  - import su anno già presente → avviso UI senza blocco
- `test_api.py`:
  - `GET /ruolo/avvisi` con filtro anno
  - `GET /ruolo/avvisi/{id}` dettaglio con partite
  - `GET /ruolo/soggetti/{id}/avvisi` richiede subject esistente
  - `GET /ruolo/stats`
- `test_catasto_parcels.py`:
  - upsert particella nuova → creata con valid_to = NULL
  - re-upsert stessa superficie → no-op
  - upsert superficie diversa → valid_to settato + nuovo record

### 5.2 Permessi

Verificare section gating su tutti gli endpoint:
- upload solo `admin`
- lettura: `admin`, `reviewer`, `viewer` (con `module_ruolo` abilitato)

### 5.3 Export CSV avvisi

`GET /ruolo/avvisi/export` (con stessi filtri della lista):
- Colonne: CF/PIVA, nominativo, anno, codice_cnc, codice_utenza, importo_0648, importo_0985, importo_0668, importo_totale, soggetto_collegato

### 5.4 Validazione su dati reali

Eseguire import del file Ruolo 2024 completo (~9.810 partite) su ambiente di test.
Verificare:
- Durata job accettabile (< 5 minuti)
- Contatore `skipped` plausibile rispetto ai soggetti censiti in anagrafica
- Nessun crash su partite edge case (subalterni letterali, superfici a zero, co-intestati multipli)
- `catasto_parcels` popolata con valori sensati

**Done when**: suite test verde, import reale completato senza errori, permessi verificati.

---

## Dipendenze e prerequisiti

| Prerequisito | Stato atteso |
|-------------|-------------|
| `catasto_comuni` popolata | Necessaria per risoluzione codice Belfiore |
| `ana_subjects` + `ana_persons` + `ana_companies` presenti | Necessarie per matching CF/PIVA |
| `application_users` con flag moduli | Pattern esistente da seguire |
| `pypdf` o `pdfminer.six` in requirements | Verificare, aggiungere se assente |

---

## Rischi e mitigazioni

| Rischio | Probabilità | Mitigazione |
|---------|-------------|-------------|
| Unità superficie SUP.CATA. | ~~Alta~~ **Risolto** | Are (confermato). Colonne: `sup_catastale_are` + `sup_catastale_ha` (are / 100). |
| CF/PIVA non corrispondenti ad anagrafica | Alta | Avvisi orfani sono previsti dal design; filtro `unlinked` per bonifica |
| Estrazione testo PDF non strutturata | Media | Accettare `.dmp` grezzo come fallback; test sul PDF reale in M1 |
| Performance import ~9.800 partite | Bassa | Background task + savepoint per-partita; monitorare in M5 |
| Parser fragile su edge case formato | Media | Fault-tolerance by design; log errori per-partita senza interruzione |

---

## Backlog tecnico ordinato

### Backend
1. Migration (5 tabelle)
2. Modelli ORM (`RuoloImportJob`, `RuoloAvviso`, `RuoloPartita`, `RuoloParticella`, `CatastoParcel`)
3. Enumerazioni
4. `parser.py` + test unitari parser
5. `import_service.py` (job asincrono + upsert catasto_parcels)
6. `schemas.py`
7. `repositories.py`
8. `import_routes.py`
9. `query_routes.py`
10. `router.py`
11. `bootstrap.py` + flag `module_ruolo` su `ApplicationUser`
12. Registrazione router in `api/router.py`
13. Test import + API
14. Test catasto_parcels
15. Permessi section gating
16. Export CSV

### Frontend
1. `types/ruolo.ts`
2. `lib/api/ruolo.ts`
3. Layout modulo + navigazione
4. `/ruolo/import` + `/ruolo/import/[job_id]`
5. `/ruolo/avvisi` (lista)
6. `/ruolo/avvisi/[avviso_id]` (dettaglio)
7. `/ruolo` (dashboard)
8. `/ruolo/stats`
9. Integrazione scheda soggetto anagrafica
10. Lint + type check
