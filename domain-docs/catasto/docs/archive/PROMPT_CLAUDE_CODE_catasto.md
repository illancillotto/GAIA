# Prompt operativo — GAIA Catasto

> Stato documento
> Documento storico archiviato.
> Prompt del periodo di transizione tra dominio `catasto` e runtime `elaborazioni`, non piu da usare come prompt operativo corrente.

> Regola strutturale vincolante
> Il backend applicativo Catasto vive nel monolite sotto `backend/app/modules/catasto/`.
> Il runtime operativo di credenziali, batch, richieste singole e CAPTCHA vive nel monolite sotto `backend/app/modules/elaborazioni/`.
> Il worker resta un servizio tecnico separato sotto `modules/elaborazioni/worker/`.
> Il frontend dominio Catasto vive in `frontend/src/app/catasto/`.
> Il frontend operativo runtime vive in `frontend/src/app/elaborazioni/`.

## Contesto

Stai lavorando sul repository `GAIA`.

GAIA Catasto oggi va letto come dominio piu runtime collegato.

Superfici di dominio `catasto`:

- dizionario comuni
- archivio documenti
- consultazione e dettaglio documenti

Superfici operative ora ospitate in `elaborazioni`:

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
3. `domain-docs/catasto/docs/archive/PROMPT_CODEX_catasto.md`
4. `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`
5. `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`
6. `backend/app/modules/catasto/routes.py`
7. `backend/app/modules/elaborazioni/runtime_routes.py`
8. `modules/elaborazioni/worker/`
9. `frontend/src/app/catasto/`
10. `frontend/src/app/elaborazioni/`

## Struttura reale del modulo

Backend:

- `backend/app/modules/catasto/router.py`
- `backend/app/modules/catasto/routes.py`
- `backend/app/modules/catasto/models.py`
- `backend/app/modules/catasto/schemas.py`
- `backend/app/modules/elaborazioni/router.py`
- `backend/app/modules/elaborazioni/runtime_routes.py`

Servizi backend:

- `backend/app/services/catasto_comuni.py`
- `backend/app/services/catasto_documents.py`
- `backend/app/services/elaborazioni_batches.py`
- `backend/app/services/elaborazioni_captcha.py`
- `backend/app/services/elaborazioni_credentials.py`

Worker:

- `modules/elaborazioni/worker/worker.py`
- `modules/elaborazioni/worker/browser_session.py`
- `modules/elaborazioni/worker/visura_flow.py`
- `modules/elaborazioni/worker/captcha_solver.py`
- `modules/elaborazioni/worker/credential_vault.py`
- `modules/elaborazioni/worker/sister_selectors.py`
- `modules/elaborazioni/worker/sister_selectors.json`

Frontend:

- `frontend/src/app/catasto/page.tsx`
- `frontend/src/app/catasto/documents/page.tsx`
- `frontend/src/app/catasto/documents/[id]/page.tsx`
- `frontend/src/app/elaborazioni/page.tsx`
- `frontend/src/app/elaborazioni/settings/page.tsx`
- `frontend/src/app/elaborazioni/new-batch/page.tsx`
- `frontend/src/app/elaborazioni/new-single/page.tsx`
- `frontend/src/app/elaborazioni/batches/page.tsx`
- `frontend/src/app/elaborazioni/batches/[id]/page.tsx`

## Principi di implementazione

- non creare backend separati
- non creare frontend separati
- non introdurre nuovi path di dominio fuori da `backend/app/modules/catasto/` senza motivo forte
- non reintrodurre workflow runtime dentro `backend/app/modules/catasto/`
- usa `backend/app/api/router.py` come punto di integrazione router
- mantieni il worker come componente tecnico separato
- tratta `backend/app/modules/catasto/routes.py` come sorgente canonica degli endpoint dominio
- tratta `backend/app/modules/elaborazioni/runtime_routes.py` come sorgente canonica degli endpoint runtime
- tratta `sister_selectors.json` come sorgente canonica dei selettori runtime

## API attualmente presenti

Dominio Catasto:

- `GET /catasto/comuni`
- `POST /catasto/comuni`
- `PUT /catasto/comuni/{comune_id}`
- `GET /catasto/documents`
- `GET /catasto/documents/search`
- `POST /catasto/documents/download`
- `GET /catasto/documents/{document_id}`
- `GET /catasto/documents/{document_id}/download`

Runtime Elaborazioni:

- `POST /elaborazioni/credentials`
- `GET /elaborazioni/credentials`
- `GET /elaborazioni/credentials/{credential_id}`
- `PATCH /elaborazioni/credentials/{credential_id}`
- `DELETE /elaborazioni/credentials`
- `DELETE /elaborazioni/credentials/{credential_id}`
- `POST /elaborazioni/credentials/test`
- `GET /elaborazioni/credentials/test/{test_id}`
- `WS /elaborazioni/ws/credentials-test/{test_id}`
- `POST /elaborazioni/batches`
- `GET /elaborazioni/batches`
- `GET /elaborazioni/batches/{batch_id}`
- `GET /elaborazioni/batches/{batch_id}/download`
- `GET /elaborazioni/batches/{batch_id}/report.json`
- `GET /elaborazioni/batches/{batch_id}/report.md`
- `POST /elaborazioni/batches/{batch_id}/start`
- `POST /elaborazioni/batches/{batch_id}/cancel`
- `POST /elaborazioni/batches/{batch_id}/retry-failed`
- `WS /elaborazioni/ws/{batch_id}`
- `POST /elaborazioni/requests`
- `GET /elaborazioni/requests/{request_id}`
- `GET /elaborazioni/requests/{request_id}/artifacts/download`
- `GET /elaborazioni/captcha/pending`
- `GET /elaborazioni/captcha/summary`
- `GET /elaborazioni/captcha/{request_id}/image`
- `POST /elaborazioni/captcha/{request_id}/solve`
- `POST /elaborazioni/captcha/{request_id}/skip`

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
- verifica sempre `modules/elaborazioni/worker/sister_selectors.json`
- usa `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md` per casi osservati, recovery e limiti noti

## Cosa fare quando modifichi il modulo

1. verifica prima il comportamento reale nei file runtime
2. implementa seguendo i pattern gia presenti
3. aggiorna test se il comportamento cambia
4. riallinea `PRD_catasto.md` se hai toccato endpoint, flussi o struttura
5. riallinea il runbook `elaborazioni` se hai cambiato il comportamento del worker verso SISTER

## Cosa non fare

- non usare piu riferimenti legacy come `app/routers/catasto.py` o `app/models/catasto.py` come destinazione primaria
- non descrivere `modules/catasto/backend/` come struttura runtime del progetto
- non trattare il worker come backend pubblico
- non affidarti a sezioni numerate inesistenti del vecchio PRD
