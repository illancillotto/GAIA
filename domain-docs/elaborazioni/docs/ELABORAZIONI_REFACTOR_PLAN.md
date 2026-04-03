# Catasto → Elaborazioni Refactor Plan

> Stato documento
> Proposta operativa per separare il dominio `catasto` dal motore esecutivo `elaborazioni`.
> Obiettivo: evitare che il modulo Catasto coincida con i soli workflow batch/browser.

## Obiettivo

Riposizionare `catasto` come modulo di aggregazione, consultazione e normalizzazione dei dati catastali.

Estrarre l'attuale runtime operativo in un nuovo modulo `elaborazioni`, responsabile di:

- orchestrazione batch e richieste singole
- code di esecuzione e stato avanzamento
- workflow CAPTCHA
- integrazione con worker browser-based
- retry, cancel, audit tecnico e monitoraggio delle esecuzioni

## Razionale

L'attuale modulo `catasto` mescola due responsabilita diverse:

- dominio dati catastali
- execution engine delle lavorazioni

Questo rende difficile:

- aggiungere nuove fonti dati catastali senza farle dipendere dai workflow batch
- esporre un frontend orientato alla consultazione del dato
- separare API di lettura dominio da API tecniche di processo
- evolvere i provider esterni (`SISTER`, `Capacitas`, futuri adapter) come sorgenti indipendenti

## Confine funzionale target

### Catasto

Responsabilita target:

- aggregazione dati catastali
- ricerca e consultazione
- documenti catastali come asset dominio
- anagrafiche, immobili, particelle, estremi catastali, fonti e metadati
- adapter/provider verso sistemi esterni
- normalizzazione dei payload provenienti dai provider

API target indicative:

- `GET /catasto/search`
- `GET /catasto/documents`
- `GET /catasto/documents/{id}`
- `GET /catasto/sources`
- `POST /elaborazioni/capacitas/involture/search`
- future API di consultazione beni, intestatari, immobili, visure aggregate

### Elaborazioni

Responsabilita target:

- creazione batch
- upload file e validazione input operativi
- esecuzione richieste
- gestione stato `pending/processing/completed/failed`
- CAPTCHA manuale e automatico
- WebSocket di avanzamento
- retry, cancel, requeue
- relazione fra richiesta operativa e documento prodotto

API target indicative:

- `POST /elaborazioni/batches`
- `GET /elaborazioni/batches`
- `GET /elaborazioni/batches/{id}`
- `POST /elaborazioni/batches/{id}/start`
- `POST /elaborazioni/batches/{id}/retry-failed`
- `POST /elaborazioni/batches/{id}/cancel`
- `POST /elaborazioni/requests`
- `GET /elaborazioni/requests/{id}`
- `GET /elaborazioni/captcha/pending`
- `POST /elaborazioni/captcha/{request_id}/solve`
- `WS /elaborazioni/ws/{batch_id}`

## Mappa runtime proposta

### Backend

```text
backend/app/modules/
  catasto/
    router.py
    routes.py
    schemas.py
    models.py
    providers/
      sister/
      capacitas/
        apps/
          involture/
          incass/
          inbollettini/
    services.py

  elaborazioni/
    router.py
    routes.py
    schemas.py
    models.py
    services.py
```

### Service layer

Servizi che dovrebbero migrare da `catasto_*` a `elaborazioni_*`:

- `backend/app/services/catasto_batches.py`
- `backend/app/services/catasto_captcha.py`
- parte operativa di `backend/app/services/catasto_credentials.py` relativa al test workflow

Servizi che possono restare in area `catasto`:

- `backend/app/services/catasto_documents.py`
- `backend/app/services/catasto_comuni.py`
- `backend/app/services/elaborazioni_capacitas.py` come candidate a successivo rename in `elaborazioni_provider_capacitas.py`

Nota:

- `catasto_documents.py` resta in `catasto` se il documento e considerato entita dominio
- se invece il documento viene trattato come output tecnico di lavorazione, va spostato in `elaborazioni`
- consiglio: mantenerlo in `catasto`, esponendo da `elaborazioni` solo il legame verso il documento prodotto

### Frontend

```text
frontend/src/app/
  catasto/
    page.tsx
    documents/
    capacitas/
    search/

  elaborazioni/
    page.tsx
    batches/
    new-batch/
    new-single/
    captcha/
```

## Mappa del codice attuale

Da migrare in `elaborazioni`:

- `backend/app/modules/catasto/routes.py` per le sezioni:
  - credentials
  - credentials test
  - batches
  - visure singole operative
  - captcha
  - websocket batch
  - websocket credentials test
- `frontend/src/app/catasto/batches/`
- `frontend/src/app/catasto/new-batch/`
- `frontend/src/app/catasto/new-single/`
- parti operative della dashboard `/catasto` attuale

Da mantenere in `catasto`:

- `backend/app/modules/elaborazioni/capacitas/`
- `backend/app/modules/elaborazioni/capacitas_routes.py`
- `backend/app/services/catasto_documents.py`
- `frontend/src/app/catasto/documents/`
- `frontend/src/app/elaborazioni/capacitas/`
- dashboard `catasto` rifocalizzata come aggregatore dati/fonti

Da decidere esplicitamente:

- credenziali SISTER: se servono solo al motore operativo, vanno in `elaborazioni`
- credenziali Capacitas: ora fanno parte del runtime `elaborazioni`

## Strategia di migrazione

### Fase 1

- creare il nuovo modulo backend `elaborazioni`
- creare il nuovo namespace frontend `/elaborazioni`
- spostare route e service operativi mantenendo wrapper di compatibilita temporanei
- mantenere inizialmente le route legacy `/catasto/...` come proxy o alias interni

Stato attuale:

- scaffold backend creato in `backend/app/modules/elaborazioni/`
- `api_router` aggiornato per montare il nuovo modulo
- route operative centralizzate in `backend/app/modules/elaborazioni/runtime_routes.py`
- nuovo prefisso `/elaborazioni` attivo per i workflow runtime
- namespace frontend iniziale creato in `frontend/src/app/elaborazioni/`
- le principali chiamate frontend runtime in `frontend/src/lib/api.ts` puntano ora a `/elaborazioni/...`
- le route frontend operative canoniche sono:
  - `/elaborazioni/batches`
  - `/elaborazioni/batches/[id]`
  - `/elaborazioni/new-batch`
  - `/elaborazioni/new-single`
  - `/elaborazioni/settings`
- il namespace UI runtime e stato introdotto in `frontend/src/components/elaborazioni/`
- i building block UI del runtime, i workspace `request/archive/settings` e la pagina `/elaborazioni/batches/[id]` hanno ora implementazioni concrete nel namespace `elaborazioni`, non piu semplici re-export
- il provider runtime `Capacitas` e stato spostato in `backend/app/modules/elaborazioni/capacitas/` con router dedicato `/elaborazioni/capacitas/...`
- le route legacy `catasto/new*`, `catasto/batches` e `catasto/archive?view=batches` reindirizzano verso il nuovo namespace
- service layer operativo canonico creato in:
  - `backend/app/services/elaborazioni_batches.py`
  - `backend/app/services/elaborazioni_captcha.py`
  - `backend/app/services/elaborazioni_credentials.py`
- i moduli `catasto_*` corrispondenti restano come shim di compatibilita sugli import legacy
- introdotti alias canonici di naming:
  - backend model: `backend/app/models/elaborazioni.py`
  - backend schema: `backend/app/schemas/elaborazioni.py`
  - frontend types: `frontend/src/types/elaborazioni.ts`
  - frontend api alias: `frontend/src/lib/api.ts`
- le firme TypeScript del runtime in `frontend/src/lib/api.ts` usano ora tipi `Elaborazione*` pur mantenendo funzioni compatibili legacy

### Fase 2

- ridurre `catasto` alle API di dominio e provider
- spostare la dashboard principale `catasto` su consultazione e aggregazione
- spostare la UX operativa in `/elaborazioni`

Stato attuale:

- `backend/app/modules/catasto/routes.py` ora contiene solo superfici dominio di consultazione
- le route operative batch, richieste, credenziali runtime, CAPTCHA e WebSocket sono state estratte in `elaborazioni`
- il mount backend legacy `/catasto/...` per gli endpoint runtime e stato rimosso; `catasto` espone ora solo superfici di dominio, provider e consultazione
- il layer servizi del runtime non ha piu il punto di verita in `catasto_*`, ma in `elaborazioni_*`
- il frontend non usa piu `/catasto` come percorso canonico per batch, nuove richieste e credenziali operative
- il modulo `elaborazioni` puo usare naming `Elaborazione*` senza cambiare tabelle o payload legacy
- i componenti condivisi del runtime hanno ora un namespace dedicato `components/elaborazioni/*`
- il frontend operativo canonico `elaborazioni` non dipende piu da re-export diretti di pagine o componenti `catasto`
- nel frontend operativo i nomi `Elaborazione*` sono usati per batch, credenziali, captcha e websocket; restano `Catasto*` solo le superfici di dominio come comuni e documenti
- in `frontend/src/lib/api.ts` le funzioni runtime canoniche sono ora solo `Elaborazione*`; gli alias frontend `Catasto*` per il runtime sono stati rimossi
- anche le superfici legacy `frontend/src/app/catasto/*` e `frontend/src/components/catasto/*` che rappresentano runtime operativo usano ora API e tipi `Elaborazione*`, pur mantenendo il naming legacy dei file
- anche il naming backend interno del runtime e stato ripulito: servizi, eccezioni e router `elaborazioni_*` non usano piu simboli `Catasto*` per le sole responsabilita operative
- gli helper HTTP/WebSocket condivisi sono stati spostati da `backend/app/modules/catasto/http_shared.py` a `backend/app/modules/shared/http_shared.py`

### Fase 3

- rimuovere alias legacy `/catasto` per endpoint puramente operativi
- rinominare servizi e modelli residui per coerenza definitiva

Stato attuale:

- gli endpoint runtime backend sono ora esposti solo sotto `/elaborazioni`
- `backend/app/modules/catasto/router.py` non monta piu alias operativi del runtime
- il backend `catasto` conserva solo route di dominio e provider

## Decisioni consigliate

- introdurre `elaborazioni` come modulo reale, non solo cartella service
- mantenere `catasto` come dominio dati e integrazione provider
- non spostare subito `capacitas` in `elaborazioni`: oggi e piu coerente come provider dominio
- eseguire il refactor in piu PR, iniziando da router e frontend routes, non dal modello dati
