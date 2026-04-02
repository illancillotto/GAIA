# Prompt Codex — GAIA Catasto

> Stato documento
> Prompt riallineato alla struttura reale del repository al 2 aprile 2026.

> Regola strutturale vincolante
> GAIA usa backend monolitico modulare, frontend condiviso e worker tecnico separato.
> Il codice backend del dominio Catasto vive in `backend/app/modules/catasto/`.
> Il frontend del modulo vive in `frontend/src/app/catasto/`.
> Il worker browser-based vive in `modules/catasto/worker/`.

## Contesto del progetto

Stai sviluppando o modificando **GAIA Catasto**, il modulo di integrazione con i servizi dell'Agenzia delle Entrate della piattaforma **GAIA**.

Il modulo oggi copre:

- credenziali SISTER cifrate
- test connessione asincrono via worker
- upload batch CSV/XLSX
- visure singole
- gestione CAPTCHA automatica e manuale
- archivio PDF
- aggiornamenti realtime tramite WebSocket

## Sorgenti da trattare come canoniche

Ordine di priorita:

1. codice runtime
2. `README.md`
3. `domain-docs/catasto/docs/PRD_catasto.md`
4. `domain-docs/catasto/docs/SISTER_debug_runbook.md`
5. questo prompt

Superfici primarie:

- `backend/app/modules/catasto/router.py`
- `backend/app/modules/catasto/routes.py`
- `backend/app/modules/catasto/models.py`
- `backend/app/modules/catasto/schemas.py`
- `backend/app/services/catasto_batches.py`
- `backend/app/services/catasto_captcha.py`
- `backend/app/services/catasto_comuni.py`
- `backend/app/services/catasto_credentials.py`
- `backend/app/services/catasto_documents.py`
- `modules/catasto/worker/`
- `frontend/src/app/catasto/`

## Principi architetturali

- il backend resta un monolite modulare
- `backend/app/modules/catasto/router.py` e l'entrypoint del modulo
- `backend/app/modules/catasto/routes.py` contiene le route HTTP e WebSocket
- `backend/app/modules/catasto/models.py` e `schemas.py` sono superfici canoniche del modulo, anche se oggi re-esportano definizioni condivise
- la business logic backend del dominio Catasto oggi e distribuita nei file `backend/app/services/catasto_*`
- il worker resta un processo tecnico separato e non un backend applicativo parallelo
- il frontend del modulo resta nel frontend condiviso
- Alembic resta unico sotto `backend/alembic/versions/`

## API attuali del modulo

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

## Frontend attuale

Route attive:

- `/catasto`
- `/catasto/new-batch`
- `/catasto/new-single`
- `/catasto/batches`
- `/catasto/batches/[id]`
- `/catasto/documents`
- `/catasto/documents/[id]`
- `/catasto/settings`

Obiettivo UI:

- interfaccia amministrativa sobria
- leggibilita operativa prima dell'estetica
- feedback chiaro su stati batch, errori e CAPTCHA
- ricerca documentale rapida

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
- usa `backend/app/modules/catasto/` come superficie primaria del backend
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
