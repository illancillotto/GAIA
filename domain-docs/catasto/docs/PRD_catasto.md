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
- anagrafica territoriale `cat_*` per distretti, particelle, utenze irrigue e anomalie
- import Capacitas Fase 1 e basi geospaziali PostGIS
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
- `cat_import_batches`
- `cat_schemi_contributo`
- `cat_aliquote`
- `cat_distretti`
- `cat_distretto_coefficienti`
- `cat_particelle`
- `cat_particelle_history`
- `cat_utenze_irrigue`
- `cat_intestatari`
- `cat_anomalie`

Nota di integrazione territoriale:

- il campo applicativo `cod_comune_capacitas` usato oggi nei flussi Catasto/Capacitas contiene il codice numerico sorgente scambiato da Capacitas
- il mapping da `codice catastale comune` dello shapefile a questo codice Capacitas non deve essere hardcoded nel service, ma derivato dal dataset di riferimento del dominio
- il dataset di riferimento locale mantiene anche il `codice catastale` e il `codice comune ufficiale` per evitare derive semantiche tra naming storico e anagrafica amministrativa reale
- il valore `0` non va trattato come codice comune valido: indica un mapping mancante e va considerato anomalia tecnica o dato incompleto
- prima di aggiungere nuovi comuni o nuove sorgenti shapefile, aggiornare il dataset di riferimento e i test di integrazione, non il SQL inline
- la tabella `cat_comuni` e la sorgente canonica per l'anagrafica comuni; `cat_particelle`, `cat_particelle_history` e `cat_utenze_irrigue` referenziano il comune tramite `comune_id`

Entita correlate ma governate dal runtime `elaborazioni`:

- `catasto_credentials`
- `catasto_connection_tests`
- `catasto_batches`
- `catasto_visure_requests`
- `catasto_captcha_log`

Regola pratica:

- se l'entita serve a consultazione, archivio o metadatazione del patrimonio catastale, resta nel perimetro di questo PRD
- se l'entita serve a orchestration, execution o monitoraggio runtime, va documentata in `elaborazioni`

### Dataset comuni di riferimento

Il dominio Catasto usa un dataset applicativo locale:

- `backend/app/modules/catasto/data/comuni_istat.csv`

Questo dataset contiene per ogni comune:

- `cod_istat`
  codice numerico sorgente usato oggi da Capacitas nei join applicativi del dominio
- `codice_catastale`
  codice catastale alfabetico del comune, usato tipicamente negli shapefile
- `codice_comune_formato_numerico`
  codice comune ufficiale numerico
- `codice_comune_numerico_2017_2025`
  variante numerica ufficiale ISTAT/Province usata negli estratti amministrativi recenti

Vincoli:

- non usare `codice_comune_formato_numerico` al posto di `cod_istat` senza un refactor esplicito di schema e join
- non duplicare il mapping in costanti Python o `CASE` SQL
- tutte le validazioni e i mapping shapefile devono dipendere dallo stesso dataset
- nelle response API e nel frontend preferire `cod_comune_capacitas` per evitare l'equivoco con il codice ISTAT ufficiale

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

### Fase 1 territoriale

- `POST /catasto/import/capacitas`
- `GET /catasto/import/history`
- `GET /catasto/import/{batch_id}/status`
- `GET /catasto/import/{batch_id}/report`
- `GET /catasto/distretti/`
- `GET /catasto/distretti/{distretto_id}`
- `GET /catasto/distretti/{distretto_id}/kpi`
- `GET /catasto/distretti/{distretto_id}/geojson`
- `GET /catasto/particelle/`
- `GET /catasto/particelle/{particella_id}`
- `GET /catasto/particelle/{particella_id}/history`
- `GET /catasto/anomalie/`

Vincoli infrastrutturali:

- la Fase 1 richiede PostgreSQL con estensione PostGIS disponibile
- nello stack locale Docker il servizio `postgres` usa un'immagine `postgis/postgis`
- le migration `cat_*` non sono compatibili con SQLite e vanno validate su PostgreSQL reale

## Frontend corrente

Route `catasto` realmente utili al dominio:

- `/catasto`
- `/catasto/archive`
- `/catasto/documents`
- `/catasto/documents/[id]`
- `/catasto/import`
- `/catasto/distretti`
- `/catasto/distretti/[id]`
- `/catasto/particelle`
- `/catasto/particelle/[id]`
- `/catasto/anomalie`

Comportamento attuale:

- le pagine Fase 1 usano un wrapper frontend condiviso con navigazione di dominio uniforme
- `/catasto` e la dashboard Fase 1 del dominio
- `/catasto/archive?view=documents` e la superficie principale per l'archivio
- `/catasto/documents` reindirizza all'archivio documenti
- `/catasto/documents/[id]` mostra il dettaglio documento
- `/catasto/import` espone il wizard upload -> polling -> report anomalie
- il wizard import gestisce sia il completamento positivo sia il fallimento del batch con esposizione dell'errore applicativo
- il report import espone anche una sintesi batch da `report_json` con anno campagna, righe, distretti e comuni rilevati
- la pagina import espone anche uno storico dei batch recenti con filtro per stato, limite risultati, contatori e riapertura del report
- la pagina import espone inoltre un audit summary dei batch Capacitas con conteggi per stato e timestamp dell'ultimo completato
- `/catasto/import/[id]` espone il dettaglio dedicato di un batch con metadati, preview, contatori e lista anomalie
- il segmento frontend `/catasto` monta la navigation shell di dominio nel layout dedicato, non nel singolo wrapper pagina
- `/catasto/distretti` e `/catasto/distretti/[id]` coprono KPI e drill-down per distretto
- `/catasto/particelle` e `/catasto/particelle/[id]` coprono lookup e dettaglio con utenze/anomalie
- `/catasto/anomalie` espone la lista operativa con aggiornamento stato
- il workflow mutativo sulle anomalie (`PATCH`) è riservato ad admin/super_admin, mentre la consultazione resta disponibile agli utenti Catasto attivi

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
