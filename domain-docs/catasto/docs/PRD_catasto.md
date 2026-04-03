# PRD — GAIA Catasto

> Stato documento
> Documento allineato alla struttura reale del repository al 2 aprile 2026.
> Il codice runtime resta la fonte primaria in caso di divergenza:
> `backend/app/modules/catasto/`, `app/services/catasto_*`, `frontend/src/app/catasto/`, `modules/catasto/worker/`.

## Scopo

GAIA Catasto e il modulo della piattaforma GAIA che automatizza le visure catastali tramite il portale SISTER dell'Agenzia delle Entrate.

Nota evolutiva:

- `catasto` e in fase di riposizionamento come modulo di aggregazione dati catastali
- i workflow operativi batch, CAPTCHA e orchestrazione esecutiva sono candidati a migrare nel nuovo modulo `elaborazioni`
- il piano operativo del runtime e tracciato in `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`

Obiettivi operativi del modulo:

- salvare e verificare in modo sicuro le credenziali SISTER
- caricare batch CSV/XLSX di richieste visura
- gestire visure singole con lo stesso backend applicativo
- processare le richieste tramite worker Playwright separato
- risolvere i CAPTCHA con OCR, fallback esterno opzionale e intervento manuale
- archiviare i PDF scaricati e renderli ricercabili dal frontend
- pubblicare aggiornamenti realtime su test credenziali e avanzamento batch

## Architettura canonica

GAIA usa backend unico, frontend unico e database unico.

Superfici principali del modulo:

- backend HTTP e WebSocket: `backend/app/modules/catasto/`
- entrypoint router di modulo: `backend/app/modules/catasto/router.py`
- implementazione route: `backend/app/modules/catasto/routes.py`
- integrazioni provider dominio in definizione; il runtime `Capacitas` e ora ospitato in `backend/app/modules/elaborazioni/capacitas/`
- modelli e schemi canonici re-export: `backend/app/modules/catasto/models.py`, `backend/app/modules/catasto/schemas.py`
- servizi applicativi runtime: `backend/app/services/elaborazioni_batches.py`, `elaborazioni_captcha.py`, `elaborazioni_credentials.py`, oltre ai servizi dominio `catasto_comuni.py` e `catasto_documents.py`
- frontend condiviso dominio dati: `frontend/src/app/catasto/`
- frontend runtime operativo: `frontend/src/app/elaborazioni/`
- worker tecnico separato: `modules/catasto/worker/`

Target architetturale in corso di definizione:

- `catasto` come superficie di aggregazione dati, documenti e provider
- `elaborazioni` come superficie operativa per batch, richieste singole, CAPTCHA e avanzamento esecuzioni
- a livello backend il confine router e gia stato introdotto: `catasto` mantiene consultazione e provider, `elaborazioni` concentra i workflow runtime
- anche il service layer operativo e in transizione verso namespace canonici `elaborazioni_*`
- lato frontend il namespace canonico per i flussi operativi e `frontend/src/app/elaborazioni/`
- la pagina `frontend/src/app/catasto/page.tsx` e attualmente un placeholder minimale, mantenuto essenziale mentre il dominio e in corso di sviluppo e ridefinizione
- la pagina `frontend/src/app/elaborazioni/page.tsx` funge da dashboard operativa per batch, richieste, CAPTCHA e credenziali
- anche il naming applicativo del runtime sta convergendo su alias `Elaborazione*` per model, schema e tipi frontend
- i componenti UI condivisi del runtime stanno convergendo su `frontend/src/components/elaborazioni/`, con batch detail, request workspace, archive workspace e settings gia resi concreti nel nuovo namespace

Vincoli architetturali:

- non esiste un backend Catasto separato
- il worker Catasto non espone API applicative pubbliche
- le migration restano nel backend unico sotto `backend/alembic/versions/`
- i dati applicativi Catasto convivono nel database condiviso con gli altri moduli

## Funzionalita correnti

### 1. Vault credenziali SISTER

- una credenziale per utente applicativo
- password cifrata a riposo
- verifica asincrona della connessione SISTER tramite worker
- feedback realtime del test credenziali via WebSocket dedicato

### 2. Gestione batch visure

- upload file CSV/XLSX
- validazione righe in ingresso
- creazione batch con richieste singole correlate
- avvio, annullamento e retry delle richieste fallite
- dettaglio batch con stato, contatori ed eventi realtime

### 3. Visura singola

- creazione di una richiesta puntuale senza passare da upload batch
- ritorno immediato del batch di una sola richiesta
- stesso flusso worker del processing batch standard

### 4. Workflow CAPTCHA

- tentativi OCR locali tramite Tesseract
- fallback opzionale ad Anti-Captcha se configurato
- persistenza dell'immagine CAPTCHA per intervento manuale
- endpoint API per lista pendenti, immagine, solve e skip

### 5. Archivio documenti

- lista documenti filtrabile
- ricerca testuale e filtri per comune, foglio, particella e intervallo date
- dettaglio documento
- download PDF singolo
- download ZIP per batch o per selezione multipla

## Modello dati

Entita principali del dominio:

- `catasto_credentials`
- `catasto_connection_tests`
- `catasto_batches`
- `catasto_visure_requests`
- `catasto_documents`
- `catasto_captcha_log`
- `catasto_comuni`

Semantica operativa:

- `catasto_credentials` contiene le credenziali SISTER cifrate a riposo
- `catasto_connection_tests` traccia i test asincroni di connettivita e autenticazione
- `catasto_batches` rappresenta il contenitore di richieste create da upload o da visura singola
- `catasto_visure_requests` traccia ogni visura, il suo stato, l'operazione corrente e gli eventuali dati CAPTCHA
- `catasto_documents` rappresenta i PDF scaricati e i metadati necessari a ricerca e download
- `catasto_captcha_log` conserva le immagini e il metodo di risoluzione quando richiesto dal workflow
- `catasto_comuni` e il dizionario usato per validazione input e selezione SISTER

## Stati operativi

Stati ricorrenti lato batch:

- `pending`
- `processing`
- `completed`
- `failed`
- `cancelled`

Stati ricorrenti lato richiesta visura:

- `pending`
- `processing`
- `awaiting_captcha`
- `completed`
- `failed`
- `skipped`

Il worker puo riportare anche un `current_operation` descrittivo per rendere leggibile il punto del flusso in UI e WebSocket.

## API correnti

Gli endpoint di dominio restano sotto prefisso `/catasto`.
Gli endpoint runtime operativi sono esposti sotto prefisso `/elaborazioni`.

### Credenziali

- `POST /elaborazioni/credentials`
- `GET /elaborazioni/credentials`
- `DELETE /elaborazioni/credentials`
- `POST /elaborazioni/credentials/test`
- `GET /elaborazioni/credentials/test/{test_id}`
- `WS /elaborazioni/ws/credentials-test/{test_id}`

### Dizionario comuni

- `GET /catasto/comuni`
- `POST /catasto/comuni`
- `PUT /catasto/comuni/{comune_id}`

Note:

- `POST` e `PUT` sono endpoint admin

### Batch

- `POST /elaborazioni/batches`
- `GET /elaborazioni/batches`
- `GET /elaborazioni/batches/{batch_id}`
- `GET /elaborazioni/batches/{batch_id}/download`
- `POST /elaborazioni/batches/{batch_id}/start`
- `POST /elaborazioni/batches/{batch_id}/cancel`
- `POST /elaborazioni/batches/{batch_id}/retry-failed`
- `WS /elaborazioni/ws/{batch_id}`

### Visure singole

- `POST /elaborazioni/requests`
- `GET /elaborazioni/requests/{request_id}`

### Documenti

- `GET /catasto/documents`
- `GET /catasto/documents/search`
- `POST /catasto/documents/download`
- `GET /catasto/documents/{document_id}`
- `GET /catasto/documents/{document_id}/download`

### CAPTCHA

- `GET /elaborazioni/captcha/pending`
- `GET /elaborazioni/captcha/{request_id}/image`
- `POST /elaborazioni/captcha/{request_id}/solve`
- `POST /elaborazioni/captcha/{request_id}/skip`

## Contratti realtime

### WebSocket batch

Path:

- `/elaborazioni/ws/{batch_id}`

Eventi pubblicati:

- `progress`
- `captcha_needed`
- `visura_completed`
- `batch_completed`

Payload principali:

- `progress`: stato batch, contatori, totale e operazione corrente
- `captcha_needed`: `request_id` e `image_url`
- `visura_completed`: `request_id` e `document_id`
- `batch_completed`: stato finale e contatori aggregati

### WebSocket test credenziali

Path:

- `/elaborazioni/ws/credentials-test/{test_id}`

Evento pubblicato:

- `credentials_test`

## Frontend corrente

Route attive:

- `/catasto`
- `/catasto/new-batch`
- `/catasto/new-single`
- `/catasto/batches`
- `/catasto/batches/[id]`
- `/catasto/documents`
- `/catasto/documents/[id]`
- `/catasto/settings`

Comportamenti attesi:

- dashboard con metriche, batch recenti e CAPTCHA pendenti
- pagina credenziali con salvataggio, eliminazione, test asincrono e feedback realtime
- creazione batch con upload CSV/XLSX
- creazione visura singola
- dettaglio batch con progress e gestione CAPTCHA
- archivio documenti con ricerca, selezione multipla e download

## Worker Catasto

Runtime principale:

- `modules/catasto/worker/worker.py`
- `modules/catasto/worker/browser_session.py`
- `modules/catasto/worker/visura_flow.py`
- `modules/catasto/worker/captcha_solver.py`
- `modules/catasto/worker/credential_vault.py`
- `modules/catasto/worker/sister_selectors.py`
- `modules/catasto/worker/sister_selectors.json`

Capacita correnti del worker:

- recupero richieste e test connessione pendenti dal database
- recovery di richieste o test rimasti in `processing` dopo restart
- login SISTER con gestione informativa privacy
- recovery limitato della sessione bloccata
- navigazione al form visura
- compilazione campi e scelta tipo visura
- OCR CAPTCHA locale
- fallback Anti-Captcha opzionale
- download PDF e persistenza metadati
- artifact di debug HTML/PNG sul filesystem

## SISTER e selettori

Fonte canonica per i selettori runtime:

- `modules/catasto/worker/sister_selectors.json`

Il file Python `sister_selectors.py` contiene default e caricamento configurabile via:

- `CATASTO_SISTER_SELECTORS_PATH`

I selettori SISTER vanno trattati come configurazione operativa instabile. Il runbook tecnico resta in:

- `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`

## Configurazione operativa

Variabili principali del worker:

- `DATABASE_URL`
- `CREDENTIAL_MASTER_KEY`
- `CATASTO_POLL_INTERVAL_SEC`
- `CAPTCHA_MAX_OCR_ATTEMPTS`
- `CAPTCHA_MANUAL_TIMEOUT_SEC`
- `ANTI_CAPTCHA_API_KEY`
- `ANTI_CAPTCHA_POLL_INTERVAL_SEC`
- `ANTI_CAPTCHA_TIMEOUT_SEC`
- `BETWEEN_VISURE_DELAY_SEC`
- `SESSION_TIMEOUT_SEC`
- `CATASTO_DOCUMENT_STORAGE_PATH`
- `CATASTO_CAPTCHA_STORAGE_PATH`
- `CATASTO_DEBUG_ARTIFACTS_PATH`
- `CATASTO_HEADLESS`
- `CATASTO_DEBUG_BROWSER`
- `CATASTO_SISTER_SELECTORS_PATH`

## Regole di manutenzione documentale

- se cambia la struttura del modulo, aggiornare prima questo file e poi i prompt operativi
- se cambiano gli endpoint, verificare sempre `backend/app/modules/catasto/routes.py`
- se cambia il flusso SISTER, aggiornare `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md` e i selettori runtime
- se una nota e solo storica, marcarla esplicitamente come storica
