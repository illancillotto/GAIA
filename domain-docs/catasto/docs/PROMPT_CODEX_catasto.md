# Prompt Codex — GAIA Catasto

> Stato documento
> Prompt operativo allineato alla separazione reale tra dominio `catasto` e runtime `elaborazioni` al 20 aprile 2026.

> Regola strutturale vincolante
> GAIA usa backend monolitico modulare, frontend condiviso e worker tecnico separato.
> Il codice backend del dominio Catasto vive in `backend/app/modules/catasto/`.
> Il runtime operativo di batch, richieste, credenziali e CAPTCHA vive in `backend/app/modules/elaborazioni/`.
> Il frontend del dominio vive in `frontend/src/app/catasto/`.
> Il frontend operativo vive in `frontend/src/app/elaborazioni/`.
> Il worker browser-based vive in `modules/catasto/worker/`.

## Contesto del progetto

Stai sviluppando o modificando **GAIA Catasto**, il modulo di integrazione con i servizi dell'Agenzia delle Entrate della piattaforma **GAIA**.

Il dominio e il runtime oggi coprono:

- dominio `catasto`: comuni, documenti, consultazione e archivio PDF
- runtime `elaborazioni`: credenziali SISTER, test connessione, upload batch CSV/XLSX, visure singole, gestione CAPTCHA e aggiornamenti realtime

## Sorgenti da trattare come canoniche

Ordine di priorita:

1. codice runtime
2. `README.md`
3. `domain-docs/catasto/docs/PRD_catasto.md`
4. `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`
5. `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`
6. questo prompt

Superfici primarie:

- `backend/app/modules/catasto/router.py`
- `backend/app/modules/catasto/routes.py`
- `backend/app/modules/catasto/models.py`
- `backend/app/modules/catasto/schemas.py`
- `backend/app/modules/elaborazioni/router.py`
- `backend/app/modules/elaborazioni/runtime_routes.py`
- `backend/app/services/catasto_comuni.py`
- `backend/app/services/catasto_documents.py`
- `backend/app/services/elaborazioni_batches.py`
- `backend/app/services/elaborazioni_captcha.py`
- `backend/app/services/elaborazioni_credentials.py`
- `modules/catasto/worker/`
- `frontend/src/app/catasto/`
- `frontend/src/app/elaborazioni/`

## Principi architetturali

- il backend resta un monolite modulare
- `backend/app/modules/catasto/router.py` e l'entrypoint del dominio
- `backend/app/modules/catasto/routes.py` contiene le route dominio `catasto`
- `backend/app/modules/elaborazioni/runtime_routes.py` contiene le route runtime `elaborazioni`
- `backend/app/modules/catasto/models.py` e `schemas.py` sono superfici canoniche del modulo, anche se oggi re-esportano definizioni condivise
- la business logic backend del dominio Catasto oggi resta nei file `catasto_*` dedicati a comuni e documenti
- la business logic backend del runtime vive nei file `backend/app/services/elaborazioni_*`
- il worker resta un processo tecnico separato e non un backend applicativo parallelo
- il frontend del modulo resta nel frontend condiviso
- Alembic resta unico sotto `backend/alembic/versions/`

## API attuali

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

## Frontend attuale

Route `catasto` attive:

- `/catasto`
- `/catasto/new-batch`
- `/catasto/new-single`
- `/catasto/batches`
- `/catasto/batches/[id]`
- `/catasto/documents`
- `/catasto/documents/[id]`
- `/catasto/settings`

Route `elaborazioni` canoniche:

- `/elaborazioni`
- `/elaborazioni/new-batch`
- `/elaborazioni/new-single`
- `/elaborazioni/batches`
- `/elaborazioni/batches/[id]`
- `/elaborazioni/settings`
- `/elaborazioni/captcha`

Stato UI corrente:

- `/catasto` e un placeholder di dominio in ridefinizione
- le route operative `catasto/new-*`, `catasto/batches*` e `catasto/settings` sono superfici compatibili o redirect verso `elaborazioni`
- la UI operativa reale per batch, credenziali e CAPTCHA sta in `frontend/src/app/elaborazioni/`
- la ricerca documentale rapida resta nel dominio `catasto`

## Worker e SISTER

File primari:

- `modules/catasto/worker/worker.py`
- `modules/catasto/worker/browser_session.py`
- `modules/catasto/worker/visura_flow.py`
- `modules/catasto/worker/sister_selectors.py`
- `modules/catasto/worker/sister_selectors.json`

Regole:

- tratta `sister_selectors.json` come configurazione runtime dei selettori
- usa il runbook SISTER come memoria tecnica dei casi osservati
- non dare per immutabile il DOM del portale
- se cambi il flusso browser, aggiorna anche il runbook

## Istruzioni operative per Codex

Quando implementi o modifichi il modulo Catasto:

- verifica prima i pattern reali del codice esistente
- usa `backend/app/modules/catasto/` per dominio e `backend/app/modules/elaborazioni/` per runtime operativo
- integra il modulo passando da `backend/app/api/router.py`
- mantieni separati route HTTP, schemi, modelli, servizi backend e logica worker
- non spostare logica Playwright nel backend HTTP
- usa `PRD_catasto.md` come documento di prodotto e struttura, non come sorgente superiore al codice
- se trovi indicazioni legacy o divergenti nei documenti, fai prevalere l'architettura reale del repository

## Antipattern da evitare

- creare path runtime primari tipo `app/routers/catasto.py`
- documentare `modules/catasto/backend/` come se fosse backend reale
- descrivere un solo `services.py` quando i servizi sono separati in `app/services/catasto_*`
- affidarsi a sezioni numerate inesistenti del vecchio PRD
