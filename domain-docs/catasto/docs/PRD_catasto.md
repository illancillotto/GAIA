# PRD — GAIA Catasto

> Stato documento
> Documento di dominio allineato alla struttura reale del repository al 20 aprile 2026.
> Il codice resta la fonte primaria in caso di divergenza:
> `backend/app/modules/catasto/`, `backend/app/services/catasto_*`, `frontend/src/app/catasto/`, `frontend/src/components/catasto/`.

## Scopo

`catasto` e il dominio GAIA dedicato a dati e documenti catastali.

Nel repository attuale il modulo non coincide piu con il runtime operativo delle lavorazioni massive: batch, credenziali, CAPTCHA, richieste singole e monitoraggio esecutivo sono stati spostati in `elaborazioni`.

Questo PRD descrive quindi il perimetro reale di `catasto` oggi:

- dizionario comuni catastali
- archivio documenti catastali
- consultazione e dettaglio dei documenti
- superfici frontend dedicate alla navigazione del patrimonio documentale

## Obiettivi di prodotto

Obiettivi correnti del dominio:

- offrire un archivio consultabile dei documenti catastali prodotti dalle lavorazioni
- rendere i documenti ricercabili per metadati catastali e intervallo temporale
- permettere download singolo e download multiplo in ZIP
- esporre un dizionario comuni riusabile dai flussi applicativi che producono o interrogano dati catastali
- mantenere `catasto` come dominio dati separato dal runtime esecutivo

Obiettivi non piu interni al dominio `catasto`:

- orchestrazione batch
- gestione credenziali SISTER
- gestione CAPTCHA
- monitoraggio realtime delle esecuzioni
- richieste singole o massive come workflow operativo

Queste responsabilita vivono nel dominio `elaborazioni`.

## Perimetro funzionale attuale

### 1. Dizionario comuni

Il dominio espone una base comuni catastali usata per:

- lookup applicativo
- validazione input nei workflow a monte
- gestione amministrativa dei comuni censiti

### 2. Archivio documenti catastali

Il dominio espone un archivio documentale con:

- lista documenti
- ricerca per testo libero
- filtri per comune, foglio, particella e date
- dettaglio documento
- download PDF
- download ZIP di selezioni multiple

### 3. Frontend di consultazione

Il frontend `catasto` oggi non e una dashboard operativa completa.

Le superfici attive sono:

- pagina dominio placeholder
- archivio documenti
- dettaglio documento

Le route `catasto` che puntavano ai flussi operativi sono mantenute come redirect o compatibilita verso `elaborazioni`.

## Architettura canonica

GAIA usa backend unico, frontend unico e database unico.

Superfici canoniche del dominio `catasto`:

- router backend: `backend/app/modules/catasto/router.py`
- route backend: `backend/app/modules/catasto/routes.py`
- modelli re-export: `backend/app/modules/catasto/models.py`
- schemi re-export: `backend/app/modules/catasto/schemas.py`
- servizi dominio: `backend/app/services/catasto_comuni.py`, `backend/app/services/catasto_documents.py`
- frontend dominio: `frontend/src/app/catasto/`
- componenti frontend dominio: `frontend/src/components/catasto/`

Vincoli architetturali:

- `catasto` non e il runtime operativo delle visure
- il worker `modules/elaborazioni/worker/` resta un componente tecnico condiviso ma non definisce il perimetro di questo PRD
- il runtime operativo vive nel modulo `elaborazioni`
- i dati del dominio `catasto` convivono nel database condiviso con gli altri moduli

## Modello dati di riferimento

Entita di dominio oggi rilevanti per `catasto`:

- `catasto_comuni`
- `catasto_documents`

Entita correlate ma governate dal runtime `elaborazioni`:

- `catasto_credentials`
- `catasto_connection_tests`
- `catasto_batches`
- `catasto_visure_requests`
- `catasto_captcha_log`

Regola pratica:

- se l'entita serve a consultazione, archivio o metadatazione del patrimonio catastale, resta nel perimetro di questo PRD
- se l'entita serve a orchestration, execution o monitoraggio runtime, va documentata in `elaborazioni`

## API di dominio correnti

### Comuni

- `GET /catasto/comuni`
- `POST /catasto/comuni`
- `PUT /catasto/comuni/{comune_id}`

Note:

- `POST` e `PUT` sono endpoint amministrativi

### Documenti

- `GET /catasto/documents`
- `GET /catasto/documents/search`
- `POST /catasto/documents/download`
- `GET /catasto/documents/{document_id}`
- `GET /catasto/documents/{document_id}/download`

## Frontend corrente

Route `catasto` realmente utili al dominio:

- `/catasto`
- `/catasto/archive`
- `/catasto/documents`
- `/catasto/documents/[id]`

Comportamento attuale:

- `/catasto` e una pagina placeholder di dominio
- `/catasto/archive?view=documents` e la superficie principale per l'archivio
- `/catasto/documents` reindirizza all'archivio documenti
- `/catasto/documents/[id]` mostra il dettaglio documento

Route `catasto` mantenute per compatibilita ma non piu canoniche:

- `/catasto/new`
- `/catasto/new-batch`
- `/catasto/new-single`
- `/catasto/batches`
- `/catasto/batches/[id]`
- `/catasto/settings`
- `/catasto/capacitas`

Queste route reindirizzano o riusano componenti del runtime `elaborazioni`.

## Integrazione con Elaborazioni

`catasto` dipende dal fatto che il runtime `elaborazioni` produca documenti e metadata compatibili con l'archivio.

Interazioni principali:

- `elaborazioni` usa `catasto_comuni` per lookup e validazione
- i documenti generati dalle lavorazioni vengono esposti dal dominio `catasto`
- il frontend operativo e in `frontend/src/app/elaborazioni/`, ma l'output documentale resta consultabile da `catasto`

Documentazione correlata:

- `domain-docs/elaborazioni/docs/ELABORAZIONI_REFACTOR_PLAN.md`
- `domain-docs/elaborazioni/docs/SISTER_debug_runbook.md`

## Stato attuale del modulo

Il modulo `catasto` oggi non e vuoto, ma e ridotto a un perimetro di dominio piu stretto rispetto allo storico:

- backend attivo per comuni e documenti
- frontend attivo per archivio e dettaglio documenti
- dashboard principale ancora volutamente minimale
- workflow operativi demandati a `elaborazioni`

## Regole di manutenzione documentale

- usare questo PRD per cambi a comuni, documenti, archivio e superfici di consultazione `catasto`
- non usare questo PRD per descrivere batch, credenziali, CAPTCHA o richieste runtime
- per cambi ai workflow operativi aggiornare la documentazione in `domain-docs/elaborazioni/docs/`
- se una route `catasto` esiste solo come compatibilita o redirect, dichiararlo esplicitamente nei documenti
