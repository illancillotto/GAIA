# Prompt operativo — GAIA Catasto MVP

> Copia e incolla questo come primo messaggio in Claude Code.
> Prima di usarlo, assicurati di aver copiato nella repo:
>   - modules/catasto/docs/PRD_catasto.md
>   - modules/catasto/docs/PROMPT_CODEX_catasto.md

---

Stai lavorando sul repository `GAIA` (github.com/illancillotto/GAIA).

Devi sviluppare **GAIA Catasto**, il quarto modulo della piattaforma. È un sistema che automatizza il download di visure catastali dal portale SISTER dell'Agenzia delle Entrate, con archivio PDF, gestione CAPTCHA e interfaccia web integrata nella piattaforma esistente.

## Documenti di riferimento

Leggi attentamente questi file prima di iniziare:

1. `modules/catasto/docs/PRD_catasto.md` — PRD completo con requisiti, modello dati, API, flusso SISTER
2. `modules/catasto/docs/PROMPT_CODEX_catasto.md` — convenzioni architetturali, stack, vincoli tecnici

Studia anche la struttura dei moduli già esistenti come riferimento per naming e pattern:
3. `modules/accessi/backend/` — backend FastAPI esistente (router, models, schemas, services)
4. `frontend/` — frontend Next.js esistente
5. `docker-compose.yml` — configurazione Docker esistente
6. `modules/accessi/docs/CODEX_PROMPT.md` — convenzioni generali del progetto

## Principi fondamentali

- Il modulo si **aggiunge** al backend e frontend esistenti — NON creare progetti separati
- Backend: aggiungi `app/routers/catasto.py`, `app/models/catasto.py`, `app/schemas/catasto.py`, `app/services/catasto/` al FastAPI esistente
- Frontend: aggiungi `frontend/src/app/catasto/` al Next.js esistente
- Auth JWT: riutilizza il middleware esistente senza modifiche
- Alembic: crea nuove migration in `alembic/versions/` senza toccare quelle esistenti
- Il **browser worker** è l'unico componente che vive in un container Docker separato: `modules/catasto/worker/`
- Le credenziali SISTER sono crittografate con Fernet — la master key è SOLO in env var `CREDENTIAL_MASTER_KEY`

## Piano di sviluppo — Esecuzione ordinata

Procedi in quest'ordine. Per ogni step, implementa, testa, e poi passa al successivo. Non saltare step.

### Step 1 — Setup struttura e modello dati

Crea la struttura cartelle del modulo:

```
modules/catasto/
  worker/
    Dockerfile
    requirements.txt
    worker.py
    browser_session.py
    visura_flow.py
    captcha_solver.py
    credential_vault.py
  backend/
    routers/catasto.py
    models/catasto.py
    schemas/catasto.py
    services/
      batch_service.py
      credential_service.py
      document_service.py
      captcha_service.py
      websocket_service.py
  frontend/
    (verrà sviluppato negli step successivi)
  docs/
    PRD_catasto.md
    PROMPT_CODEX_catasto.md
```

Crea i modelli SQLAlchemy per le tabelle MVP (schema completo nel PRD sezione 3):
- `catasto_credentials` — credenziali SISTER crittografate
- `catasto_batches` — batch di richieste
- `catasto_visure_requests` — singole richieste di visura
- `catasto_documents` — PDF scaricati con metadati
- `catasto_captcha_log` — log immagini CAPTCHA
- `catasto_comuni` — dizionario comuni con codici SISTER

Crea la migration Alembic. Poi crea un seed script per popolare `catasto_comuni` con i comuni del Consorzio (lista completa nel PRD sezione 7).

### Step 2 — Credential Vault

Implementa il servizio di crittografia credenziali:
- `credential_service.py`: encrypt/decrypt con `cryptography.fernet.Fernet`
- La master key viene da `os.environ["CREDENTIAL_MASTER_KEY"]`
- La password decriptata non deve MAI finire in log, response, o messaggi di errore

API endpoints (nel router `/catasto`):
- `POST /catasto/credentials` — salva/aggiorna credenziali
- `GET /catasto/credentials` — verifica se esistono (NON restituire la password)
- `DELETE /catasto/credentials` — elimina
- `POST /catasto/credentials/test` — test connessione (futuro, per ora stub)

Pydantic schemas:
- `CredentialCreate(sister_username, sister_password, convenzione?, codice_richiesta?, ufficio_provinciale?)`
- `CredentialResponse(id, sister_username, convenzione, ufficio_provinciale, verified_at)` — SENZA password
- `CredentialTestResponse(success, message)`

### Step 3 — Batch service e upload CSV

Implementa la logica di upload e validazione CSV/XLSX:
- `batch_service.py`: parsing file, validazione, creazione batch + requests nel DB

Validazioni da implementare:
- Colonne obbligatorie: citta, catasto, foglio, particella, tipo_visura
- `citta` deve esistere in `catasto_comuni`
- `catasto` deve essere "Terreni" o "Terreni e Fabbricati"
- `tipo_visura` deve essere "Sintetica" o "Completa"
- `foglio` e `particella` devono essere numerici
- Righe con errori vengono segnalate ma non bloccano il batch

API endpoints:
- `POST /catasto/batches` — upload CSV, ritorna preview con errori
- `GET /catasto/batches` — lista batch utente
- `GET /catasto/batches/{id}` — dettaglio con lista requests
- `POST /catasto/batches/{id}/start` — avvia elaborazione
- `POST /catasto/batches/{id}/cancel` — annulla

### Step 4 — Worker Docker container (browser automation)

Questo è il cuore del sistema. Crea il container worker:

**Dockerfile** basato su `mcr.microsoft.com/playwright/python:v1.40.0-jammy`:
- Installa pytesseract + tesseract-ocr + tesseract-ocr-ita
- Copia il codice del worker
- Entry point: `python worker.py`

**worker.py** — main loop:
- Polling su PostgreSQL ogni 3 secondi per batch con `status = 'processing'`
- Per ogni batch trovato, processa le requests con `status = 'pending'`
- Gestisci graceful shutdown (completa la visura corrente, poi fermati)

**browser_session.py** — gestione sessione Playwright:
- Login su SISTER (flusso completo nel PRD sezione 9)
- Conferma informativa
- Navigazione fino alla sezione visure catastali
- Selezione ufficio provinciale
- Re-login proattivo ogni 28 minuti

**visura_flow.py** — flusso singola visura:
- Click "Immobile" nel menu laterale
- Compilazione form (catasto, comune, sezione, foglio, particella, subalterno, motivo)
- Click "Visura"
- Selezione tipo visura (Sintetica/Completa)
- Gestione CAPTCHA (delega a captcha_solver.py)
- Click "Inoltra"
- Attesa documento pronto
- Download PDF tramite Playwright download event
- Rinomina: `{CODICE_FISCALE}_{FOGLIO}_{PARTICELLA}[_{SUBALTERNO}].pdf`
- Salvataggio in volume Docker + creazione record in `catasto_documents`
- Ritorno al form per la prossima visura

**captcha_solver.py** — risoluzione CAPTCHA:
- Screenshot dell'immagine CAPTCHA
- Preprocessing: grayscale → resize 2x → binarizzazione → median filter
- OCR con pytesseract (`--psm 7 --oem 3`, whitelist alfanumerica)
- Se OCR fallisce dopo 3 tentativi: aggiorna request status a `awaiting_captcha`, salva immagine nel volume
- Il worker si mette in pausa per quella request e passa alla prossima (o attende l'input manuale)

**credential_vault.py** — decrypt credenziali nel worker:
- Legge le credenziali dal DB per l'utente del batch
- Decripta la password con Fernet
- La password vive SOLO in memoria, per la durata della sessione

Selettori SISTER chiave (da PRD sezione 9):
- Tab Sister login: `a.nav-link[href="#tab-5"]`
- Username: `#username-sister` / Password: `#password-sister`
- Conferma informativa: `//input[@value='Conferma']`
- Territorio: `select[name='listacom']` → value `ORISTANO Territorio-OR`
- Catasto: `select[name='tipoCatasto']`
- Comune: `select[name='denomComune']`
- Foglio: `input[name='foglio']` / Particella: `input[name='particella1']` / Subalterno: `input[name='subalterno1']`
- Motivo: `select[name='motivoLista']` → value `"Altri fini istituzionali "`
- Visura button: `input[name='scelta'][value='Visura']`
- Tipo visura: `input[name='tipoVisura']` → `3` (Sintetica) o `2` (Completa)
- CAPTCHA field: `input[name='codSicurezza']`
- Inoltra: `input[name='inoltra'][value='Inoltra']`
- Salva: `input[name='metodo'][value='Salva']`

⚠️ **NOTA IMPORTANTE**: questi selettori sono stati rilevati a marzo 2026 dagli screenshot del portale. Potrebbero essere diversi a runtime. Usa `page.pause()` in debug mode per ispezionare il DOM reale prima di hardcodare i selettori. Prevedi un file di configurazione separato per i selettori così possono essere aggiornati senza toccare il codice.

### Step 5 — WebSocket per progress e CAPTCHA

Implementa l'endpoint WebSocket:
- `ws://.../catasto/ws/{batch_id}`
- Il backend fa polling sullo stato del batch e invia aggiornamenti al frontend

Messaggi:
```json
{"type": "progress", "completed": 15, "total": 50, "current": "MARRUBIU Fg.12 Part.603"}
{"type": "captcha_needed", "request_id": "uuid", "image_url": "/catasto/captcha/uuid/image"}
{"type": "visura_completed", "request_id": "uuid", "filename": "SLRNMR80M47A948Z_12_603.pdf"}
{"type": "batch_completed", "ok": 45, "failed": 3, "skipped": 2}
```

API CAPTCHA:
- `GET /catasto/captcha/pending` — lista requests in attesa
- `GET /catasto/captcha/{request_id}/image` — immagine CAPTCHA
- `POST /catasto/captcha/{request_id}/solve` — invia soluzione
- `POST /catasto/captcha/{request_id}/skip` — salta

### Step 6 — Archivio documenti

API:
- `GET /catasto/documents` — lista con filtri (comune, foglio, particella, data, utente)
- `GET /catasto/documents/{id}` — metadati
- `GET /catasto/documents/{id}/download` — download PDF
- `GET /catasto/documents/search` — ricerca
- `GET /catasto/batches/{id}/download` — ZIP di tutti i PDF del batch

Storage: volume Docker `catasto-data`, path strutturato `/{anno}/{comune}/{file}.pdf`

### Step 7 — Frontend: settings credenziali

Pagina `/catasto/settings`:
- Form con username e password SISTER
- Campi opzionali: convenzione, codice richiesta, ufficio provinciale
- Pulsante "Salva"
- Pulsante "Testa connessione" con feedback live
- Pulsante "Elimina credenziali" con conferma

Stile coerente con GAIA Accessi: professionale, pulito, TailwindCSS.

### Step 8 — Frontend: upload batch e avvio

Pagina `/catasto/new-batch`:
- Upload file CSV/XLSX (drag & drop o click)
- Preview tabella con validazione: righe valide in verde, errori in rosso con messaggio
- Nome descrittivo del batch (opzionale)
- Pulsante "Avvia download" (disabilitato se non ci sono credenziali salvate)
- Link a template CSV scaricabile

### Step 9 — Frontend: dettaglio batch con progress

Pagina `/catasto/batches/{id}`:
- Progress bar con percentuale e contatore (es. "15/50")
- Label dell'operazione corrente
- Tabella righe con badge stato per ciascuna: pending (grigio), processing (blu), completed (verde), failed (rosso), awaiting_captcha (arancione)
- **CAPTCHA dialog**: quando arriva il messaggio WebSocket `captcha_needed`, mostra un modal con l'immagine CAPTCHA grande, campo di testo, pulsanti "Invia" e "Salta"
- Pulsante "Annulla batch"
- A batch completato: riepilogo con contatori + pulsante "Scarica tutti i PDF (ZIP)"

### Step 10 — Frontend: archivio documenti

Pagina `/catasto/documents`:
- TanStack Table con colonne: comune, foglio, particella, tipo visura, data, utente, azioni
- Filtri: comune (dropdown), foglio, particella, range date
- Pulsante download per ogni riga
- Selezione multipla + download ZIP

Pagina `/catasto/documents/{id}`:
- Metadati documento
- Preview PDF inline (embed)
- Pulsante download

### Step 11 — Frontend: dashboard e visura singola

Pagina `/catasto` (dashboard):
- Batch recenti con stato
- Documenti scaricati oggi
- CAPTCHA in attesa (con link diretto)
- Quick actions: "Nuova visura singola", "Nuovo batch", "Archivio"

Pagina `/catasto/new-single`:
- Form con dropdown comuni, catasto, sezione, foglio, particella, subalterno, tipo visura
- Pulsante "Scarica visura"
- Feedback in tempo reale (stesso WebSocket del batch, batch con 1 riga)

### Step 12 — Docker Compose e integrazione

Aggiungi al `docker-compose.yml`:

```yaml
catasto-worker:
  build: ./modules/catasto/worker
  depends_on:
    - postgres
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - CREDENTIAL_MASTER_KEY=${CREDENTIAL_MASTER_KEY}
    - CAPTCHA_MAX_OCR_ATTEMPTS=3
    - BETWEEN_VISURE_DELAY_SEC=5
    - DOCUMENT_STORAGE_PATH=/data/catasto/documents
    - CAPTCHA_STORAGE_PATH=/data/catasto/captcha
  volumes:
    - catasto-data:/data/catasto
  restart: unless-stopped

volumes:
  catasto-data:
```

Aggiungi al `.env.example`:
```
CREDENTIAL_MASTER_KEY=  # Genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Aggiorna il `README.md` della repo con la documentazione del quarto modulo.

## Checklist finale

Prima di considerare il MVP completato, verifica:
- [ ] Migration Alembic eseguibile senza errori
- [ ] Seed comuni caricato
- [ ] Credenziali SISTER salvabili e recuperabili (password mai in chiaro)
- [ ] Upload CSV con validazione funzionante
- [ ] Worker si avvia, fa login su SISTER, naviga fino al form
- [ ] Worker compila form e gestisce CAPTCHA (OCR + fallback)
- [ ] PDF scaricato, rinominato e archiviato
- [ ] WebSocket invia progress al frontend
- [ ] CAPTCHA dialog funzionante nel browser
- [ ] Archivio documenti consultabile con filtri
- [ ] Dashboard con overview
- [ ] Docker Compose avvia tutto con `make up`
