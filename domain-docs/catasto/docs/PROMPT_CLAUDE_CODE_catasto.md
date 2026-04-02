# Prompt operativo — GAIA Catasto

> Stato documento
> Documento ripulito e riallineato alla struttura reale del repository al 2 aprile 2026.

> Regola strutturale vincolante
> Il backend applicativo Catasto vive nel monolite sotto `backend/app/modules/catasto/`.
> Il worker resta un servizio tecnico separato sotto `modules/catasto/worker/`.
> Il frontend del modulo vive nel frontend condiviso sotto `frontend/src/app/catasto/`.

## Contesto

Stai lavorando sul repository `GAIA`.

GAIA Catasto automatizza:

- salvataggio e verifica credenziali SISTER
- creazione batch visure da CSV/XLSX
- visure singole
- esecuzione worker Playwright
- risoluzione CAPTCHA
- archivio PDF e download ZIP
- aggiornamenti realtime per test credenziali e stato batch

## File da leggere prima di intervenire

Leggi in quest'ordine:

1. `README.md`
2. `domain-docs/catasto/docs/PRD_catasto.md`
3. `domain-docs/catasto/docs/PROMPT_CODEX_catasto.md`
4. `domain-docs/catasto/docs/SISTER_debug_runbook.md`
5. `backend/app/modules/catasto/routes.py`
6. `modules/catasto/worker/`
7. `frontend/src/app/catasto/`

## Struttura reale del modulo

Backend:

- `backend/app/modules/catasto/router.py`
- `backend/app/modules/catasto/routes.py`
- `backend/app/modules/catasto/models.py`
- `backend/app/modules/catasto/schemas.py`

Servizi backend:

- `backend/app/services/catasto_batches.py`
- `backend/app/services/catasto_captcha.py`
- `backend/app/services/catasto_comuni.py`
- `backend/app/services/catasto_credentials.py`
- `backend/app/services/catasto_documents.py`

Worker:

- `modules/catasto/worker/worker.py`
- `modules/catasto/worker/browser_session.py`
- `modules/catasto/worker/visura_flow.py`
- `modules/catasto/worker/captcha_solver.py`
- `modules/catasto/worker/credential_vault.py`
- `modules/catasto/worker/sister_selectors.py`
- `modules/catasto/worker/sister_selectors.json`

Frontend:

- `frontend/src/app/catasto/page.tsx`
- `frontend/src/app/catasto/settings/page.tsx`
- `frontend/src/app/catasto/new-batch/page.tsx`
- `frontend/src/app/catasto/new-single/page.tsx`
- `frontend/src/app/catasto/batches/page.tsx`
- `frontend/src/app/catasto/batches/[id]/page.tsx`
- `frontend/src/app/catasto/documents/page.tsx`
- `frontend/src/app/catasto/documents/[id]/page.tsx`

## Principi di implementazione

- non creare backend separati
- non creare frontend separati
- non introdurre nuovi path di dominio fuori da `backend/app/modules/catasto/` senza motivo forte
- usa `backend/app/api/router.py` come punto di integrazione router
- mantieni il worker come componente tecnico separato
- tratta `routes.py` come sorgente canonica degli endpoint
- tratta `sister_selectors.json` come sorgente canonica dei selettori runtime

## API attualmente presenti

Credenziali:

- `POST /catasto/credentials`
- `GET /catasto/credentials`
- `DELETE /catasto/credentials`
- `POST /catasto/credentials/test`
- `GET /catasto/credentials/test/{test_id}`
- `WS /catasto/ws/credentials-test/{test_id}`

Comuni:

- `GET /catasto/comuni`
- `POST /catasto/comuni`
- `PUT /catasto/comuni/{comune_id}`

Batch:

- `POST /catasto/batches`
- `GET /catasto/batches`
- `GET /catasto/batches/{batch_id}`
- `GET /catasto/batches/{batch_id}/download`
- `POST /catasto/batches/{batch_id}/start`
- `POST /catasto/batches/{batch_id}/cancel`
- `POST /catasto/batches/{batch_id}/retry-failed`
- `WS /catasto/ws/{batch_id}`

Visure:

- `POST /catasto/visure`
- `GET /catasto/visure/{request_id}`

Documenti:

- `GET /catasto/documents`
- `GET /catasto/documents/search`
- `POST /catasto/documents/download`
- `GET /catasto/documents/{document_id}`
- `GET /catasto/documents/{document_id}/download`

CAPTCHA:

- `GET /catasto/captcha/pending`
- `GET /catasto/captcha/{request_id}/image`
- `POST /catasto/captcha/{request_id}/solve`
- `POST /catasto/captcha/{request_id}/skip`

## Flussi principali da preservare

### Credenziali

- salvataggio cifrato
- test asincrono via worker
- aggiornamento realtime dello stato test

### Batch

- upload file
- validazione
- creazione richieste
- avvio worker
- monitoraggio realtime
- retry delle richieste fallite

### CAPTCHA

- OCR locale
- fallback servizio esterno opzionale
- richiesta solve manuale

### Documenti

- persistenza PDF su storage condiviso
- ricerca e download dal frontend
- ZIP per batch o selezione multipla

## SISTER

Il portale e instabile e puo cambiare markup.

Regole:

- non hardcodare selettori fuori dal sistema di configurazione esistente
- verifica sempre `modules/catasto/worker/sister_selectors.json`
- usa `domain-docs/catasto/docs/SISTER_debug_runbook.md` per casi osservati, recovery e limiti noti

## Cosa fare quando modifichi il modulo

1. verifica prima il comportamento reale nei file runtime
2. implementa seguendo i pattern gia presenti
3. aggiorna test se il comportamento cambia
4. riallinea `PRD_catasto.md` se hai toccato endpoint, flussi o struttura
5. riallinea il runbook se hai cambiato il comportamento del worker verso SISTER

## Cosa non fare

- non usare piu riferimenti legacy come `app/routers/catasto.py` o `app/models/catasto.py` come destinazione primaria
- non descrivere `modules/catasto/backend/` come struttura runtime del progetto
- non trattare il worker come backend pubblico
- non affidarti a sezioni numerate inesistenti del vecchio PRD
