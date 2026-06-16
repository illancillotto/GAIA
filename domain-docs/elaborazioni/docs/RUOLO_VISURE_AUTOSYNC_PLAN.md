# Piano Implementazione: AutoSync Visure Particelle a Ruolo

## Obiettivo

Introdurre in `Elaborazioni` un flusso aggiuntivo che, sfruttando il runtime visure esistente, mantenga allineato nel tempo il download delle visure per tutte le particelle presenti a ruolo.

Vincoli richiesti:

- il punto di ingresso UX vive in `Scelta del flusso` del workspace visure
- il flusso deve essere attivabile/disattivabile (`on/off`)
- il sistema deve continuare a pescare le particelle mancanti fino a copertura completa
- se una visura fallisce o non parte, deve entrare in elenco e venire riprovata in seguito
- in questa fase si usa una sola utenza SISTER per volta
- niente elaborazioni multiple concorrenti per questo autosync

## Stato attuale del codice

### Frontend visure

- il workspace visure vive in `frontend/src/components/elaborazioni/request-workspace.tsx`
- la sezione `Scelta del flusso` espone oggi tre modalità:
  - `Visura singola`
  - `Import batch`
  - `Batch recenti`
- il workspace `visure` è usato sia nella pagina `frontend/src/app/elaborazioni/visure/page.tsx` sia nelle modali rapide

### Backend batch visure

- la creazione batch e richieste vive in `backend/app/services/elaborazioni_batches.py`
- il runtime HTTP di `elaborazioni` vive in `backend/app/modules/elaborazioni/runtime_routes.py`
- il modello runtime è aliasato tramite `backend/app/models/elaborazioni.py`, ma i dati reali sono nel dominio `catasto`

### Worker visure

- il polling runtime è in `modules/elaborazioni/worker/worker.py`
- oggi il worker visure usa tutte le credenziali attive dell’utente in parallelo
- questo comportamento è esplicitamente documentato anche in `domain-docs/elaborazioni/README.md`

### Fonte dati ruolo

- le particelle ruolo vivono in `backend/app/modules/ruolo/models.py` (`RuoloParticella`)
- la ricerca e i filtri esistenti vivono in:
  - `backend/app/modules/ruolo/routes/query_routes.py`
  - `backend/app/modules/ruolo/repositories.py`
- il collegamento alla particella catasto corrente è `RuoloParticella.cat_particella_id`

## Decisione architetturale proposta

Non conviene forzare l’autosync dentro i batch manuali esistenti.

La strada più pulita è:

1. riusare la logica di esecuzione delle richieste visura già esistente
2. introdurre un sottodominio dedicato `ruolo visure autosync`
3. materializzare una coda persistita di particelle da lavorare e rilavorare
4. far generare al coordinatore piccoli batch tecnici, marcati come `autosync_ruolo`
5. far processare questi batch dal worker in modalità sequenziale, con una sola credenziale

Questo evita di piegare il flusso manuale `single/batch` a esigenze di lunga durata, retry infinito e stato continuo.

## Ambito funzionale v1

La v1 deve fare solo questo:

- leggere le particelle a ruolo collegate a `cat_particella_id`
- deduplicarle per `cat_particella_id`
- creare/riallineare una coda autosync
- generare richieste visura per i soli elementi ancora da fare o da ritentare
- processarle con una sola credenziale per volta
- persistire esito, ultimo tentativo e prossima riprova
- mostrare in UI:
  - stato `on/off`
  - credenziale usata
  - numero totale / completate / in coda / retry / bloccate
  - elenco errori/blocchi

Fuori scope v1:

- multi-credential
- multi-batch paralleli
- priorità avanzate
- visure per soggetto
- regole di scheduling complesse per anno/comune

## Fonte canonica degli elementi da sincronizzare

### Regola proposta

La sorgente della coda autosync deve essere:

- `RuoloParticella`
- solo righe con `cat_particella_id IS NOT NULL`
- deduplica su `cat_particella_id`

### Perché

- l’autosync deve scaricare visure reali su particelle catasto correnti
- `ruolo_particelle` può contenere più righe logiche riferite alla stessa particella
- deduplicare direttamente su `cat_particella_id` evita di riscaricare la stessa visura più volte solo perché la particella compare in più partite/anni

### Caso particelle non collegate

Le righe `RuoloParticella` senza `cat_particella_id` non devono entrare nel batch tecnico v1.

Devono invece finire in un elenco `bloccate a monte`, con motivazione tipo:

- `missing_cat_particella_link`
- `particella_non_corrente`
- `dati_ruolo_non_risolti`

Questo tiene separati:

- errori di sourcing dati
- errori di esecuzione visura

## Nuovi oggetti dati

### 1. Configurazione autosync

Nuova tabella proposta: `cat_ruolo_visure_autosync_config`

Campi minimi:

- `id`
- `user_id`
- `enabled`
- `selected_credential_id`
- `scope_anno_tributario` nullable
- `batch_size`
- `retry_delay_minutes`
- `last_materialized_at`
- `last_dispatch_at`
- `created_at`
- `updated_at`

Note:

- `selected_credential_id` deve essere obbligatorio per v1
- se nullo o inattivo, l’autosync va in stato `blocked_configuration`
- `batch_size` iniziale consigliata: `10` o `20`, non centinaia

### 2. Coda persistita

Nuova tabella proposta: `cat_ruolo_visure_autosync_item`

Campi minimi:

- `id`
- `config_id`
- `cat_particella_id`
- `last_ruolo_particella_id`
- `anno_tributario_max`
- `comune`
- `foglio`
- `particella`
- `subalterno`
- `catasto`
- `status`
- `attempt_count`
- `last_batch_id`
- `last_request_id`
- `last_document_id`
- `last_error_kind`
- `last_error_message`
- `last_attempt_at`
- `next_retry_at`
- `completed_at`
- `source_payload_json`
- `created_at`
- `updated_at`

Vincolo unico:

- `UNIQUE (config_id, cat_particella_id)`

### 3. Tipo batch tecnico

Estendere `CatastoBatch` con un discriminante:

- `batch_kind`

Valori iniziali:

- `manual_single`
- `manual_batch`
- `ruolo_autosync`

Questo serve per:

- distinguere i batch tecnici da quelli lanciati manualmente
- cambiare comportamento del worker solo sui batch autosync
- filtrare la UI senza introdurre euristiche fragili sul nome batch

## Stato degli item autosync

Stati proposti per `cat_ruolo_visure_autosync_item.status`:

- `pending`
- `queued`
- `processing`
- `completed`
- `retry_wait`
- `blocked_source`
- `blocked_manual`

Semantica:

- `pending`: elemento noto ma non ancora trasformato in richiesta runtime
- `queued`: già agganciato a un batch tecnico non ancora finito
- `processing`: richiesta effettivamente in carico al worker
- `completed`: visura ottenuta
- `retry_wait`: errore recuperabile, da ritentare
- `blocked_source`: non enqueueabile per problema dati ruolo/catasto
- `blocked_manual`: errore non sensato da ritentare in loop cieco

## Classificazione errori proposta

### Retry automatico

Da rimandare in `retry_wait`:

- timeout sessione
- `SISTER_SESSION_LOCKED`
- `HTTP 500`
- CAPTCHA non risolto in tempo
- trasporto/browser error

### Blocco manuale

Da mandare in `blocked_manual`:

- particella non trovata in modo ripetuto
- risposta strutturalmente incoerente
- input catastale non valido
- mismatch persistente tra dato ruolo e dato catasto derivato

### Regola v1

Per evitare loop infiniti, una richiesta che fallisce con la stessa classe `business/non retryable` oltre una soglia minima va in `blocked_manual`, non in retry perpetuo.

## Modalità di esecuzione worker

### Vincolo richiesto

Per questo autosync va usata una sola utenza per volta.

### Impatto sul worker

Oggi `_process_batch()` in `modules/elaborazioni/worker/worker.py` crea un pool concorrente su tutte le credenziali attive.

Per i batch `batch_kind = ruolo_autosync` bisogna invece:

- usare solo `selected_credential_id`
- validare che sia attiva
- lanciare un solo runner
- non eseguire `asyncio.gather` su più credenziali

### Regola di lock

Per v1:

- un solo batch `ruolo_autosync` attivo alla volta per config utente
- opzionalmente, per essere più conservativi, un solo batch `ruolo_autosync` globale

La scelta consigliata è:

- lock per `config_id`
- più semplice da evolvere
- non blocca futuri autosync di altri utenti, ma mantiene il vincolo “una sola utenza per volta” dentro ciascun flusso

## Coordinatore autosync

Serve un nuovo service backend, per esempio:

- `backend/app/services/elaborazioni_ruolo_autosync.py`

Responsabilità:

1. leggere/creare la config
2. materializzare la coda da `ruolo_particelle`
3. scegliere gli item pronti
4. generare batch tecnici `ruolo_autosync`
5. sincronizzare esiti runtime -> stato item
6. evitare batch multipli contemporanei

### Materializzazione iniziale

Ad ogni `refresh` o tick:

- query su `RuoloParticella`
- join a `CatParticella`
- dedup su `cat_particella_id`
- upsert su `cat_ruolo_visure_autosync_item`

### Dispatch batch

Se:

- config `enabled = true`
- nessun batch autosync aperto
- credenziale selezionata attiva

allora:

- prendere i primi `N` item con stato `pending` o `retry_wait` e `next_retry_at <= now`
- creare un batch tecnico `batch_kind = ruolo_autosync`
- creare le relative `ElaborazioneRichiesta`
- portare gli item a `queued`
- avviare il batch

## UI proposta

### Punto di ingresso

Nel blocco `Scelta del flusso` di `frontend/src/components/elaborazioni/request-workspace.tsx` aggiungere una quarta card:

- `AutoSync a ruolo`

Descrizione:

- scarico continuo delle visure per le particelle presenti a ruolo
- una sola credenziale
- retry automatico sugli errori recuperabili

### Workspace dedicato

La card non deve aprire il form singolo o batch.

Deve aprire un pannello dedicato, per esempio:

- stesso file con modalità nuova `mode = "ruolo-autosync"`
- oppure componente separato `ruolo-autosync-workspace.tsx`

Scelta consigliata:

- componente separato
- meno complessità condizionale nel file già grande del request workspace

### Contenuto minimo del pannello

- toggle `Abilitato / Disabilitato`
- select credenziale SISTER dedicata
- eventuale filtro `anno ruolo` per v1
- KPI:
  - totale item
  - completati
  - in coda
  - retry
  - bloccati
- azioni:
  - `Aggiorna sorgente ruolo`
  - `Avvia ciclo ora`
  - `Metti in pausa`
  - `Riprova errori`
- tabella errori/blocchi
- link al batch tecnico aperto se presente

## API backend da introdurre

Base consigliata:

- `/elaborazioni/ruolo-autosync/*`

Endpoint v1:

- `GET /elaborazioni/ruolo-autosync/config`
- `PUT /elaborazioni/ruolo-autosync/config`
- `POST /elaborazioni/ruolo-autosync/refresh-source`
- `POST /elaborazioni/ruolo-autosync/run-once`
- `GET /elaborazioni/ruolo-autosync/status`
- `GET /elaborazioni/ruolo-autosync/items`
- `POST /elaborazioni/ruolo-autosync/items/retry-blocked`
- `POST /elaborazioni/ruolo-autosync/items/{id}/retry`

`status` deve restituire almeno:

- config
- batch tecnico attivo
- conteggi per stato
- ultimo errore
- ultima dispatch

## Integrazione con il worker

### Scelta consigliata

Non creare un nuovo worker separato in v1.

Usare lo stesso `modules/elaborazioni/worker/worker.py`, aggiungendo:

- riconoscimento `batch_kind = ruolo_autosync`
- esecuzione single-credential
- hook finale di sync stato item

### Hook necessari

Punti da introdurre:

- prima di iniziare il batch: marcare item `processing`
- a fine richiesta:
  - `completed` se documento creato
  - `retry_wait` se errore retryable
  - `blocked_manual` se errore definitivo
- a fine batch:
  - se restano item `pending/retry_wait`, il coordinatore li rilancerà al tick successivo

## Scheduling

### v1 semplice

Il coordinatore può essere invocato:

- da `run-once` manuale
- dal polling worker principale ad ogni ciclo, prima della ricerca del prossimo batch visure

Regola:

- se enabled
- e non c’è batch autosync aperto
- allora dispatcha il prossimo lotto tecnico

Questo evita di introdurre già ora scheduler aggiuntivi o timer separati.

## Test da prevedere

### Backend

- materializzazione coda da `RuoloParticella` con dedup su `cat_particella_id`
- esclusione righe senza `cat_particella_id`
- creazione batch tecnico `ruolo_autosync`
- blocco doppio dispatch se esiste già un batch aperto
- sync esito richiesta -> stato item
- selezione singola credenziale nel worker

### Frontend

- render card `AutoSync a ruolo` in `Scelta del flusso`
- toggle enable/disable
- stato KPI e lista errori
- azione `Avvia ciclo ora`

## Ordine di sviluppo consigliato

### Fase 1 - Dati e service

- migration config autosync
- migration queue item
- `batch_kind` su batch
- service `elaborazioni_ruolo_autosync.py`

### Fase 2 - API

- config CRUD
- status
- materializzazione sorgente
- run-once
- lista item

### Fase 3 - Worker

- single credential mode su `ruolo_autosync`
- sync esiti item
- lock anti-concorrenza

### Fase 4 - UI

- card in `Scelta del flusso`
- workspace dedicato
- tabella errori e KPI

### Fase 5 - Hardening

- retry policy
- classificazione errori
- test end-to-end

## Assunzioni operative da validare prima del coding

1. La deduplica va fatta su `cat_particella_id`, non su coppia `foglio/particella`.
2. Le righe `ruolo_particelle` non collegate a catasto non entrano in run automatico v1.
3. La credenziale da usare è esplicita in config, non “prima attiva disponibile”.
4. Il flusso autosync deve vivere in un workspace dedicato, non nel form batch manuale.
5. I retry automatici sono ammessi solo per errori tecnici/recuperabili; gli errori business vanno in elenco bloccato.

## Rischi principali

- accumulo di item duplicati se non si chiude bene la deduplica
- loop infiniti su particelle strutturalmente non risolvibili
- collisione con i batch manuali se non si separa `batch_kind`
- regressione sul worker visure se la logica single-credential viene messa come branch fragile dentro `_process_batch()`

## Raccomandazione finale

Per questa feature non conviene “nasconderla” dentro il batch manuale esistente.

La soluzione più solida è:

- nuova coda persistita
- batch tecnico dedicato
- branch worker dedicato per `ruolo_autosync`
- UI dedicata nel workspace visure

In questo modo si soddisfano sia il requisito funzionale di copertura continua, sia il vincolo operativo di una sola utenza e zero parallelismo in questa fase.
