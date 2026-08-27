# GAIA Worker Architecture Plan

## Obiettivo

Separare il traffico HTTP, lo scheduling e l'esecuzione dei job per evitare che
ogni processo Uvicorn replichi gli scheduler e per impedire che batch CPU/RAM o
browser-intensive degradino le API di GAIA.

Il piano riguarda l'architettura versionata nel repository. Deploy, restart e
modifiche sul server di produzione restano attivita separate e richiedono una
decisione esplicita.

## Baseline osservata

- Il backend usa quattro processi Uvicorn.
- Il lifespan FastAPI registra undici scheduler in ogni processo web.
- In produzione il job Ruolo e stato osservato in quattro copie concorrenti,
  con durata di circa 17-27 secondi e picchi backend di circa quattro core CPU.
- L'autosync Ruolo legge circa 933.000 righe sorgente e materializza circa
  176.000 record ORM a ogni ciclo.
- Lo status Ruolo viene richiesto dal frontend ogni 15 secondi e oggi include
  una riconciliazione costosa invece di essere una lettura aggregata.
- Il worker Visure puo aprire nove sessioni browser; i PID Docker includono
  processi e thread e non hanno evidenziato zombie nel controllo eseguito.
- Presenze ha gia un worker dedicato con concorrenza tre, ma il recovery non
  offre ancora lease e fencing adatti a repliche multiple.
- Gate Mobile viene eseguito da cron host tramite `docker compose exec`.
- I servizi non hanno ancora budget espliciti per CPU, RAM e numero di processi.

## Invarianti

- I quattro processi Uvicorn continuano a servire le API senza eseguire job
  schedulati o batch monitorabili.
- Un trigger schedulato viene emesso una sola volta per scadenza logica.
- Retry e recovery non possono produrre due owner validi dello stesso job.
- Un worker non puo completare o aggiornare un job dopo aver perso la lease.
- I contratti REST, i payload e gli stati esposti al frontend restano
  compatibili, salvo una decisione funzionale esplicita.
- I job gia persistiti restano leggibili e recuperabili durante il rollout.
- I limiti dei browser vengono applicati sul numero di sessioni prima di
  introdurre un `pids_limit` restrittivo.
- Ogni file runtime nuovo o modificato mantiene coverage al 100%.

## Architettura obiettivo

### API

Il servizio `backend` esegue quattro worker Uvicorn esclusivamente HTTP. Il
lifespan mantiene soltanto bootstrap idempotenti necessari all'applicazione e
non crea istanze APScheduler.

### Scheduler

Un servizio singleton `platform-scheduler`, costruito dalla stessa immagine del
backend, registra tutti i trigger applicativi. Il processo gestisce SIGINT e
SIGTERM, espone un healthcheck di processo e termina APScheduler in modo
ordinato. I singoli job mantengono inoltre advisory lock PostgreSQL dove una
seconda esecuzione sarebbe pericolosa: il singleton riduce le duplicazioni, il
lock protegge da overlap e rollout transitori.

### Code e ownership

PostgreSQL resta il broker persistente. Le code convergono sul seguente
protocollo:

- claim atomico con `FOR UPDATE SKIP LOCKED`;
- `worker_id`, `lease_token`, `lease_expires_at` e `heartbeat_at` persistiti;
- rinnovo periodico della lease durante il lavoro;
- fencing token verificato su progress e completamento;
- recovery dei job scaduti con retry limitato e backoff;
- ordinamento che combina priorita, tentativi e anzianita per evitare starvation.

Le migrazioni vengono introdotte per famiglia di coda, mantenendo compatibilita
con i record esistenti e rollback applicativo documentato.

### Famiglie runtime

- `presenze-worker`: sincronizzazioni Presenze, senza altre code.
- `elaborazioni-worker-visure`: soli flussi SISTER/AdE e browser associati.
- `elaborazioni-worker-runtime`: soli job Capacitas e import REGISTRY.
- `elaborazioni-worker-poste`: soli job Poste Online e relativo browser.
- `elaborazioni-worker-autodoc`: sola sincronizzazione AUTODOC.
- `gate-mobile-sync`: processo dedicato con schedule interno o loop controllato,
  al posto del cron host che entra nel container backend.

Ogni servizio usa `init: true`, healthcheck e stop grace period. I budget
operativi vengono impostati dopo misure di picco e includono almeno memoria,
CPU e PID; un limite che interrompe carichi validi non viene applicato alla
cieca.

## Milestone

### M1 - Scheduler fuori dall'API

Deliverable:

- runner unico per tutti gli scheduler;
- lifespan FastAPI senza APScheduler;
- servizio Compose singleton con healthcheck;
- rimozione del runner GIS separato per evitare due owner dello stesso trigger;
- test unitari su registrazione, segnali, shutdown e lifespan HTTP.

Exit criteria:

- avviando quattro worker API non vengono registrati job;
- il runner registra una volta tutti gli undici scheduler;
- test mirati, coverage e quality ratchet verdi.

Rollback: ripristino del servizio GIS precedente e del lifespan solo tramite
revert del change set; nessun deploy misto deve lasciare entrambi i runner
abilitati.

### M2 - Ruolo single-flight e letture economiche

Deliverable:

- advisory lock dedicato all'autosync Ruolo;
- stesso lock applicato a scheduler, `run-now` e refresh manuale;
- materializzazione incrementale/set-based, evitando il caricamento ORM completo;
- endpoint status read-only basato su aggregazioni SQL e liste limitate;
- polling frontend adattivo o sospeso quando la pagina non e visibile.

Exit criteria:

- due invocazioni concorrenti producono una sola materializzazione;
- lo status non esegue riconciliazioni o scansioni ORM complete;
- p95 e query count sono misurabili prima/dopo con lo stesso dataset.

Rollback: disabilitazione autosync tramite toggle esistente e ripristino della
query precedente senza perdita dei dati sorgente.

### M3 - Lease, fencing e fairness

Deliverable:

- primitive condivise per identita worker e lease;
- migrazione e adozione iniziale sulla coda Presenze;
- heartbeat, recovery per lease scaduta, retry/backoff e fencing;
- metriche/log strutturati per claim, rinnovo, scadenza e tentativi.

Exit criteria:

- due worker non possono possedere contemporaneamente lo stesso token valido;
- un owner scaduto non puo completare il job;
- crash e restart recuperano il lavoro entro la finestra configurata;
- i job anziani non restano indefinitamente dietro ai job nuovi.

Rollback: esecuzione a replica singola e feature flag del protocollo lease; le
nuove colonne restano additive fino alla stabilizzazione.

### M4 - Isolamento e limiti operativi

Deliverable:

- Gate Mobile come servizio dedicato;
- code browser e non-browser non condivise quando possono bloccarsi a vicenda;
- limite configurabile alle sessioni browser attive;
- `init`, healthcheck, stop grace period e budget iniziali nei servizi Compose;
- runbook per capacity planning e tuning.

Exit criteria:

- nessun cron host usa `docker compose exec backend` per eseguire job;
- il numero di sessioni Chromium non supera il limite configurato;
- saturare una famiglia worker non degrada il polling delle altre;
- i limiti sono validati con carico rappresentativo e rollback documentato.

## Rollout produzione

Il rollout non fa parte dell'implementazione locale. La sequenza prevista e:

1. backup e verifica migrazioni additive;
2. deploy del codice con scheduler API disabilitati;
3. avvio di un solo `platform-scheduler` e controllo del registro job;
4. canary delle lease con una replica per famiglia;
5. aumento controllato delle repliche e verifica di claim/heartbeat;
6. applicazione graduale dei limiti dopo almeno un ciclo di osservazione;
7. rimozione del cron Gate Mobile solo dopo healthcheck del nuovo servizio.

I KPI minimi sono p50/p95/p99 API, CPU e RSS per servizio, query PostgreSQL,
lag/eta delle code, job duplicati, lease scadute, retry e sessioni browser.

## Verifiche obbligatorie

- suite mirate per scheduler, Ruolo, Presenze, Gate Mobile e worker;
- coverage 100% di tutti i file runtime modificati;
- `make quality-test`;
- `make complexity-ratchet BASE_REF=origin/main`;
- verifica manuale di transazioni, retry, segnali e concorrenza;
- Graphify backend, moduli di dominio e documentazione piattaforma impattati.

Il runbook operativo, inclusi budget iniziali, rollout e rollback, e in
`docs/WORKER_OPERATIONS_RUNBOOK.md`.
