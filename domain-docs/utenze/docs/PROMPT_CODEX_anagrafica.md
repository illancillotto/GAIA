# Prompt Codex — GAIA Anagrafica

> **Regola strutturale vincolante**
> GAIA usa un backend monolitico modulare. Il codice backend del dominio Anagrafica va creato in `backend/app/modules/anagrafica/`. Il frontend del modulo vive in `frontend/src/app/anagrafica/`. Non va creato alcun servizio backend separato.

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata al modulo Anagrafica.

---

## Contesto del progetto

Stai sviluppando **GAIA Anagrafica**, il modulo di gestione delle anagrafiche dei soggetti del Consorzio all'interno della piattaforma **GAIA** per il Consorzio di Bonifica dell'Oristanese.

Attenzione al confine di dominio:
- gli utenti applicativi che accedono a GAIA restano nel dominio `ApplicationUser`
- Anagrafica gestisce invece i soggetti del Consorzio: persone fisiche, persone giuridiche, contribuenti, intestatari, pratiche e documenti collegati

GAIA è una piattaforma IT governance multi-modulo con backend e frontend condivisi:

- **GAIA Accessi** — NAS Audit (completato)
- **GAIA Rete** — Network Monitor (in sviluppo)
- **GAIA Inventario** — IT Inventory (in sviluppo)
- **GAIA Catasto** — Servizi AdE (MVP in integrazione)
- **GAIA Anagrafica** — Gestione anagrafiche soggetti (questo modulo)

Il repository si trova su `github.com/illancillotto/GAIA`.

---

## Stack obbligatorio

**Backend**
- FastAPI, SQLAlchemy, Alembic, PostgreSQL
- `smbprotocol` o `pysmb` per lettura struttura cartelle SMB dal NAS
  (in alternativa `paramiko` SSH, già presente nel progetto per GAIA Accessi)
- `re` stdlib per parsing nomi cartelle e classificazione documenti
- `openpyxl` per export XLSX (già usato in altri moduli)
- `csv` stdlib per export CSV

**Frontend**
- Next.js, React, TypeScript, TailwindCSS
- TanStack Table (già usato negli altri moduli — mantieni coerenza)
- `react-hook-form` per i form anagrafici
- Componenti condivisi esistenti: mantieni coerenza con layout, auth flow, UI patterns

**Infrastructure**
- Nessun container Docker aggiuntivo richiesto per questo modulo (l'import NAS è sincrono o quasi)
- Se l'import asincrono sarà necessario in futuro, usare APScheduler già presente nel backend

---

## Principi architetturali

- Il modulo si **aggiunge** al backend e frontend **esistenti** — NON creare progetti separati
- Backend: aggiungi il router sotto `/anagrafica` al FastAPI esistente integrando in `backend/app/api/router.py`
- Frontend: aggiungi `frontend/src/app/anagrafica/` al Next.js esistente
- Auth JWT condivisa: riutilizzare il middleware esistente senza modifiche
- Alembic: crea nuove migration in `alembic/versions/` senza toccare quelle esistenti
- Database: usa il PostgreSQL condiviso, nessun database separato
- Non duplicare meccanismi di auth, sessione DB, configurazione già esistenti
- Integra il modulo anche nel sistema esistente di abilitazione moduli e sezioni: `application_users`, `enabled_modules`, bootstrap sezioni, home e sidebar frontend

---

## Istruzioni operative per Claude Code

Quando implementi il modulo Anagrafica:

1. **Leggi prima** la struttura reale del repository e segui i pattern già usati in `backend/app/modules/accessi/`, `backend/app/modules/catasto/`, `backend/app/modules/network/`
2. Considera `backend/app/modules/anagrafica/` come superficie primaria del backend
3. Aggiungi il router di modulo in `backend/app/api/router.py` esattamente come fatto per gli altri moduli
4. Mantieni separati modelli, schemi, servizi e route, ma adatta la superficie del modulo ai pattern reali del repo (`router.py` o `routes.py`)
5. Evita refactor non richiesti ai moduli esistenti
6. Preserva compatibilità con il monolite condiviso e con il database unico
7. Usa `domain-docs/anagrafica/docs/PRD_anagrafica.md` come riferimento funzionale di base, ma fai prevalere l'architettura canonica del repository quando trovi indicazioni obsolete
8. Registra esplicitamente i modelli del modulo nel bootstrap metadata usato dal backend (`backend/app/db/base.py`) se necessario per Alembic e ORM
9. Aggiorna i DTO utente e la UI globale per rendere il modulo realmente visibile e assegnabile in piattaforma

---

## Modello dati da implementare

```
ana_subjects         — anagrafica soggetti (PF e PG) con link cartella NAS
ana_persons          — dati specifici persona fisica (1:1 con ana_subjects)
ana_companies        — dati specifici persona giuridica (1:1 con ana_subjects)
ana_documents        — documenti: link NAS o upload locale, con classificazione
ana_import_jobs      — log dei job di import NAS per lettera
ana_audit_log        — storico modifiche per soggetto
```

Schema completo in `domain-docs/anagrafica/docs/PRD_anagrafica.md` sezione 3.

---

## API da implementare

Tutti gli endpoint del modulo devono essere esposti dal backend condiviso e pubblicati sotto prefisso `/anagrafica`.

Pattern architetturale:
- route dichiarate in `router.py` o `routes.py`, coerentemente con il pattern del modulo scelto
- business logic in `services.py` e sottodirectory `services/`
- accesso dati in `repositories.py` quando utile; non forzarlo se il modulo segue un pattern più leggero coerente con il repo
- schemi request/response in `schemas.py`
- modelli SQLAlchemy in `models.py`

Riferimento endpoint: `domain-docs/anagrafica/docs/PRD_anagrafica.md`, sezione 4.

---

## Pagine frontend da implementare

```text
/anagrafica
/anagrafica/new
/anagrafica/[id]
/anagrafica/[id]/edit
/anagrafica/import
/anagrafica/import/[jobId]
/anagrafica/search  (opzionale, può essere integrato in /anagrafica con query params)
```

Linee guida frontend:
- usare App Router nella struttura esistente di `frontend/src/app/`
- evitare applicazioni frontend separate o microfrontend
- mantenere coerenza con layout, auth flow, componenti condivisi e convenzioni già presenti nel progetto
- TanStack Table per la lista soggetti con sorting, filtri e paginazione lato server

---

## Piano di sviluppo — Esecuzione ordinata

Procedi in quest'ordine. Per ogni step: implementa, verifica, poi passa al successivo.

### Step 1 — Modello dati e migration

Crea i modelli SQLAlchemy per tutte le tabelle:
- `ana_subjects`, `ana_persons`, `ana_companies`, `ana_documents`, `ana_import_jobs`, `ana_audit_log`

Definisci le enumerazioni:
- `SubjectType`: PERSON | COMPANY | UNKNOWN
- `SubjectStatus`: ACTIVE | INACTIVE | DUPLICATE
- `DocType`: INGIUNZIONE | NOTIFICA | ESTRATTO_DEBITO | PRATICA_INTERNA | VISURA | CORRISPONDENZA | CONTRATTO | ALTRO
- `ClassificationSource`: AUTO | MANUAL
- `StorageType`: NAS_LINK | LOCAL_UPLOAD
- `ImportJobStatus`: PENDING | RUNNING | COMPLETED | FAILED

Aggiungi indici:
- `ana_persons(codice_fiscale)` — unique
- `ana_companies(partita_iva)` — unique
- `ana_subjects(nas_folder_letter)`
- `ana_documents(subject_id, doc_type)`
- `tsvector` su cognome+nome e ragione_sociale per full-text search

Crea la migration Alembic.

Nello stesso step, integra il modulo nel runtime GAIA:
- aggiungi `module_anagrafica` in `application_users`
- aggiorna `enabled_modules`
- aggiorna gli schemi utenti backend/frontend
- predispone l'aggiunta del modulo nelle schermate di amministrazione utenti

### Step 2 — Parser nome cartella NAS

Implementa `backend/app/modules/anagrafica/services/parser_service.py`:

```python
def parse_folder_name(folder_name: str) -> ParseResult:
    """
    Input: nome cartella grezza (es. "Obinu_Santina_BNOSTN34L64I743F")
    Output: ParseResult con subject_type, campi estratti, confidence score
    
    Regole:
    1. Se l'ultimo token (split '_') è lungo 16 char e matcha regex CF → PERSON
       cognome = token[0], nome = token[1], cf = token[-1]
    2. Se l'ultimo token è 11 cifre → COMPANY
       piva = token[-1], ragione_sociale = ' '.join(token[:-1]).replace('_', ' ')
    3. Altrimenti → UNKNOWN, folder_name salvato raw
    """
```

Testa il parser con i casi reali osservati nell'archivio:
- `Obinu_Santina_BNOSTN34L64I743F` → PERSON
- `3M_Societa_Agricola_Semplice_0123806095` → COMPANY (nota: 10 cifre → gestisci edge case)
- `Olati_Srl_14542661005` → COMPANY
- `TELERILEVAMENTO` → UNKNOWN (cartella speciale)
- `00710430950` → UNKNOWN o COMPANY (sola P.IVA, nessuna ragione sociale)

### Step 3 — Classificatore documenti

Implementa `backend/app/modules/anagrafica/services/classify_service.py`:

```python
PATTERNS = {
    "INGIUNZIONE":      [r"(?i)ingiunzione", r"(?i)[_\-]ing[_\-]", r"(?i)^ing_"],
    "NOTIFICA":         [r"(?i)relata", r"(?i)notifica"],
    "ESTRATTO_DEBITO":  [r"(?i)estratto.?debito", r"(?i)estrattoDebito"],
    "PRATICA_INTERNA":  [r"(?i)^PE_", r"(?i)_prot\d"],
    "VISURA":           [r"(?i)visura"],
    "CORRISPONDENZA":   [r"(?i)lettera", r"(?i)comunicaz"],
    "CONTRATTO":        [r"(?i)contratto", r"(?i)convenzione"],
}
# Fallback: ALTRO

def classify_filename(filename: str) -> tuple[DocType, ClassificationSource]:
    """Applica pattern matching sul nome file. Restituisce (DocType, AUTO)."""
```

### Step 4 — Connettore NAS

Implementa `backend/app/modules/anagrafica/services/import_service.py`:

```python
async def list_nas_letter(letter: str) -> list[NASFolderInfo]:
    """
    Connessione al NAS via SMB (smbprotocol) o SSH (paramiko).
    Legge ARCHIVIO/<letter>/ e restituisce lista di cartelle con file.
    Usa le credenziali NAS già configurate nel backend (env vars esistenti).
    """

async def preview_import(letter: str) -> ImportPreview:
    """
    Esegue list_nas_letter + parsing senza commit al DB.
    Restituisce preview con: soggetti parsed, file per soggetto, errori attesi.
    """

async def run_import(letter: str, job_id: UUID) -> ImportJobResult:
    """
    Commit al DB: crea ana_subjects, ana_persons/ana_companies, ana_documents.
    Idempotente: upsert su codice_fiscale / partita_iva / nas_folder_path.
    Aggiorna ImportJob con statistiche e log errori.
    """
```

**Nota su connessione NAS:**
- Verifica prima se il progetto usa già `paramiko` per accedere al NAS (modulo Accessi)
- Se sì, riutilizza la stessa configurazione (host, credenziali) — non duplicarla
- Path NAS base: `smb://nas_cbo.local/settore catasto/ARCHIVIO/` (share: `settore catasto`, path: `ARCHIVIO/`)
- Prima di introdurre nuove env vars, verifica quelle reali già presenti nel backend. Ad oggi la configurazione condivisa espone variabili come `NAS_HOST`, `NAS_PORT`, `NAS_USERNAME`, `NAS_PASSWORD`, `NAS_PRIVATE_KEY_PATH`, `NAS_TIMEOUT`
- Se serve una base path specifica per l'archivio Anagrafica, aggiungi solo env vars strettamente necessarie e documentale in modo coerente con `app/core/config.py`

### Step 5 — Router e API backend

Implementa `backend/app/modules/anagrafica/routes.py`:

Endpoint obbligatori MVP:
- `GET /anagrafica/subjects` — lista con query params: `q` (full-text), `type`, `status`, `letter`, `page`, `page_size`
- `POST /anagrafica/subjects` — crea soggetto manuale
- `GET /anagrafica/subjects/{id}` — dettaglio + documenti + audit log
- `PUT /anagrafica/subjects/{id}` — aggiorna
- `DELETE /anagrafica/subjects/{id}` — disattivazione logica
- `GET /anagrafica/subjects/{id}/documents` — lista documenti
- `PATCH /anagrafica/documents/{id}` — aggiorna tipo/note documento
- `POST /anagrafica/import/preview` — body: `{ "letter": "O" }` → restituisce preview
- `POST /anagrafica/import/run` — body: `{ "letter": "O" }` → avvia import, restituisce job_id
- `GET /anagrafica/import/jobs` — lista job
- `GET /anagrafica/import/jobs/{id}` — dettaglio job con log
- `GET /anagrafica/stats` — statistiche aggregate
- `GET /anagrafica/export` — export CSV/XLSX

Integra il router in `backend/app/api/router.py`.

Aggiungi anche:
- nuove section key `anagrafica.*` in `backend/app/scripts/bootstrap_sections.py`
- gating del modulo con `require_module(\"anagrafica\")` o pattern equivalente coerente con il backend

### Step 6 — Frontend: lista soggetti e ricerca

Implementa `frontend/src/app/anagrafica/page.tsx`:
- TanStack Table con colonne: tipo soggetto (badge PF/PG), nome/ragione sociale, CF/P.IVA, lettera, n. documenti, stato
- Filtri: tipo soggetto, lettera, testo libero (full-text)
- Paginazione lato server
- Link a scheda soggetto per ogni riga

Aggiorna anche la navigazione globale:
- home moduli
- `PlatformSidebar`
- `ModuleSidebar`
- eventuali tipi condivisi `CurrentUser` / `ApplicationUser`

### Step 7 — Frontend: scheda soggetto

Implementa `frontend/src/app/anagrafica/[id]/page.tsx`:
- Dati anagrafici in sezione superiore (edit inline o link a /edit)
- Lista documenti con colonne: tipo (badge), nome file, dimensione, data, link NAS, azioni
- Azione su documento: cambia tipo manualmente (dropdown)
- Sezione audit log (collassabile)
- Link a visure GAIA Catasto se correlazione disponibile

### Step 8 — Frontend: wizard import NAS

Implementa `frontend/src/app/anagrafica/import/page.tsx`:

Wizard a 3 step:
1. **Selezione**: scelta lettera (A–Z) + pulsante "Anteprima"
2. **Preview**: tabella soggetti che verranno importati, evidenziazione errori/warning, pulsante "Conferma import"
3. **Esecuzione**: progress indicator + link al job di log

### Step 9 — Frontend: dashboard

Implementa `frontend/src/app/anagrafica/page.tsx` (variante dashboard pre-lista):
- Card statistiche: totale soggetti, PF vs PG, documenti totali, documenti non classificati
- Tabella ultime importazioni con stato job
- Quick links: "Importa nuova lettera", "Cerca soggetto"

### Step 10 — Full-text search PostgreSQL

Aggiungi colonna `search_vector tsvector` a `ana_persons` e `ana_companies`.
Popola e aggiorna via trigger PostgreSQL o in `services.py` ad ogni upsert.
Usa `to_tsquery` nell'API `GET /anagrafica/subjects?q=...`.

---

## Requisiti UI/UX

- UI amministrativa sobria, coerente con gli altri moduli GAIA
- Badge per tipo soggetto: PF (blu chiaro), PG (verde chiaro), UNKNOWN (grigio)
- Badge per tipo documento con colori semantici fissi
- Badge per stato import job: PENDING (grigio), RUNNING (arancione animato), COMPLETED (verde), FAILED (rosso)
- Form anagrafico organizzato in tab: "Persona Fisica" / "Persona Giuridica"
- Wizard import con step indicator visuale
- Tabelle con sorting, filtri colonna e paginazione lato server
- Responsive desktop-first; mobile secondario

---

## Vincoli tecnici

- Non creare un backend separato per Anagrafica
- Non introdurre nuovi path primari fuori da `backend/app/modules/anagrafica/`
- Non duplicare meccanismi di auth, sessione DB, configurazione già esistenti
- Non scrivere mai sul NAS — il modulo è read-only rispetto all'archivio NAS
- Non hardcodare path SMB o credenziali NAS — usare env vars
- Non usare chiamate API interne tra moduli dello stesso backend se il dato è già nel DB condiviso
- Idempotenza import: `ON CONFLICT DO UPDATE` su CF/P.IVA, mai duplicati per re-import
- Prima di introdurre wrapper legacy, privilegiare sempre la struttura canonica del modulo
- Non assumere che il pattern dei moduli esistenti sia perfettamente uniforme: osserva il repo reale e scegli il livello di formalizzazione minimo coerente

---

## Variabili d'ambiente necessarie

Aggiungi a `.env.example`:

```env
# NAS condiviso GAIA
NAS_HOST=nas_cbo.local
NAS_PORT=22
NAS_USERNAME=...
NAS_PASSWORD=...

# Solo se serve distinguere il path archivio Anagrafica dal resto della config NAS condivisa
ANAGRAFICA_NAS_ARCHIVE_ROOT=/volume1/settore catasto/ARCHIVIO
```

Prima di aggiungere nuove env vars, verifica sempre `backend/app/core/config.py` e riusa i nomi già esistenti.

---

## Edge case noti nell'archivio NAS

Rilevati dall'analisi visiva dell'archivio (marzo 2026):

| Caso | Esempio | Gestione |
|------|---------|----------|
| CF con caratteri lowercase | `bnostn34l64i743f` | Normalizza uppercase prima del match |
| P.IVA a 10 cifre | `0123806095` (9 cifre + lettera?) | Verifica e gestisci come UNKNOWN o COMPANY con warning |
| Cartelle speciali | `TELERILEVAMENTO`, `00710430950` | SubjectType=UNKNOWN, importa con flag `requires_review=true` |
| Sottocartelle annidate | `Obinu Santina/PE_Prot5620/` | Scendi ricorsivamente fino a 2 livelli, cataloga tutti i file trovati |
| File non-PDF | `Ingiunzione step.gif` | Catalogato normalmente, `doc_type` determinato dal nome |
| Spazi nel nome cartella | `Obinu Giovanni Giampaolo_BNOGNN...` | Split su `_` dall'ultimo token verso sinistra |

---

## Riferimento architetturale

Prima di iniziare, leggi:
- `backend/app/modules/catasto/` — pattern più recente e canonico del monolite
- `backend/app/modules/accessi/` — esempio di connessione NAS esistente
- `backend/app/MONOLITH_MODULAR.md` — regole architetturali del backend
- `backend/app/db/base.py` — registry metadata attuale
- `backend/app/models/application_user.py` — flag modulo ed `enabled_modules`
- `backend/app/scripts/bootstrap_sections.py` — sezioni piattaforma da estendere
- `frontend/src/components/layout/platform-sidebar.tsx` e `frontend/src/components/layout/module-sidebar.tsx` — navigazione globale da aggiornare
- `domain-docs/anagrafica/docs/PRD_anagrafica.md` — questo PRD

Non avviare alcuna implementazione prima di aver verificato la struttura reale del repository con `ls` e `cat` sui file chiave.
