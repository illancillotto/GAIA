# GAIA Worker Architecture Progress

Fonte di verita per l'implementazione del piano
`docs/WORKER_ARCHITECTURE_PLAN.md`.

## Stato generale

- Program status: `IMPLEMENTED_LOCAL`
- Current milestone: `M5 - validazione locale completata`
- Last update: `2026-08-27`
- Local branch: `main`
- Local HEAD at baseline: `ae889f04`
- Merge-base `origin/main`: `112dee6aa43a`
- Production deployment: `NOT_STARTED`

## Working tree concorrente

Le seguenti modifiche concorrenti non appartengono a questo programma o sono
arrivate durante la sua revalidazione:

- `modules/elaborazioni/worker/sister_request_rows.py`
- `modules/elaborazioni/worker/tests/test_sister_request_rows.py`
- runtime e frontend GIS, inclusi i relativi test e
  `docs/GIS_PLATFORM_PROGRESS.md`;
- Ruolo tributi e relativi repository/service;
- allowlist credenziali batch SISTER, inclusi migration `20260827_1100`,
  modello/schema Catasto, route, batch service, runtime worker e relativi test;
- `docs/code-quality/HOTSPOTS.md` e `docs/code-quality/PROGRESS.md`.

Devono essere preservate e non incluse nelle conclusioni o nei rollback di
questo lavoro.

## Baseline operativa

| Area | Evidenza | Rischio |
| --- | --- | --- |
| API | quattro processi Uvicorn | corretto per traffico HTTP, errato se ciascuno avvia scheduler |
| Scheduler | undici registrazioni nel lifespan | trigger duplicati per processo |
| Ruolo | quattro copie concorrenti osservate, 17-27 s | saturazione CPU/RAM e DB |
| Ruolo data path | circa 933.000 sorgenti e 176.000 ORM per ciclo | scansione e materializzazione ripetute |
| Ruolo status | polling frontend ogni 15 s con riconciliazione | latenza API autoindotta |
| Visure | nove browser, circa 54 Chromium e circa 755 task | pressione memoria/PID; nessuno zombie osservato |
| Presenze | worker singleton, concorrenza tre | recovery non sicuro con repliche |
| Gate Mobile | cron host ogni cinque minuti | ownership esterna allo stack |
| Compose | nessun budget CPU/RAM/PID | una famiglia puo degradare l'intero host |

Ambiente produzione osservato: 16 CPU, 30 GiB RAM, swap circa 3,8/4 GiB. Il
checkout remoto era piu vecchio e sporco; nessuna modifica e stata eseguita.

## Decision log

| Data | Decisione | Motivazione |
| --- | --- | --- |
| 2026-08-27 | mantenere quattro worker Uvicorn solo HTTP | parallelismo web utile senza moltiplicare i job |
| 2026-08-27 | usare un runner scheduler singleton | ownership esplicita e lifecycle indipendente dalle API |
| 2026-08-27 | mantenere PostgreSQL come coda | evita una nuova dipendenza Redis/Celery |
| 2026-08-27 | advisory lock anche con scheduler singleton | protegge overlap, rollout transitori e trigger manuali |
| 2026-08-27 | lease con fencing prima di scalare le code | un heartbeat senza fencing non impedisce write tardive |
| 2026-08-27 | limitare prima le sessioni browser, poi i PID | i PID Docker includono thread e un cap cieco puo terminare carichi validi |
| 2026-08-27 | nessun intervento diretto in produzione | implementazione, review e deploy restano fasi distinte |
| 2026-08-27 | Presenze usa generation SQLAlchemy come fencing | impedisce commit tardivi dopo recovery o cancellazione |
| 2026-08-27 | Gate Mobile passa dal timer host a Compose | elimina `docker compose exec backend` e rende ownership/health espliciti |
| 2026-08-27 | Poste viene separato da runtime | un browser Poste non blocca Capacitas o REGISTRY |
| 2026-08-27 | cap Visure a quattro sessioni prima del PID limit | limita browser reali mantenendo un budget PID non restrittivo |
| 2026-08-27 | refresh manuale Ruolo usa lo stesso advisory lock | impedisce overlap con scheduler senza cambiare il contratto REST |
| 2026-08-27 | metadata e migrazione indicizzano `RuoloParticella.created_at` | evita drift Alembic e accelera il watermark sulla sorgente effettiva |

## Milestone tracker

| Milestone | Stato | Gate |
| --- | --- | --- |
| M0 - audit e piano | `DONE` | documenti, baseline e invarianti versionati |
| M1 - scheduler fuori dall'API | `DONE` | runner singleton, Compose, test e coverage |
| M2 - Ruolo single-flight/performance | `DONE` | lock, query incrementali/status aggregate, benchmark |
| M3 - lease/fencing/fairness | `DONE` | migrazione, crash/recovery, PostgreSQL e coverage 100% |
| M4 - isolamento/limiti | `DONE_LOCAL` | servizi, cap browser, healthcheck, budget e runbook; deploy escluso |
| M5 - validazione finale | `DONE_LOCAL` | test aggregati, ratchet del perimetro e Graphify; blocco globale concorrente documentato |

## Registro verifiche

| Data | Milestone | Comando o verifica | Esito |
| --- | --- | --- | --- |
| 2026-08-27 | M0 | branch, SHA, merge-base e working tree | `PASS`; due file preesistenti identificati |
| 2026-08-27 | M0 | audit processi e risorse produzione in sola lettura | `PASS`; nessun deploy o restart |
| 2026-08-27 | M1 | `docker compose config --quiet` | `PASS`; un solo servizio scheduler nello stack dichiarato |
| 2026-08-27 | M1 | suite scheduler e bootstrap mirata | `PASS`; 15 test |
| 2026-08-27 | M1 | coverage `app.main` e `app.platform_scheduler_runner` | `PASS`; 100% statement e branch, 109 statement |
| 2026-08-27 | M1 | Ruff e `make quality-test` | `PASS`; lint pulito e 39 test quality |
| 2026-08-27 | M1 | complexity ratchet contro `origin/main` | `FAIL` globale su diff concorrenti GIS/Ruolo; nessun finding M1, baseline invariata |
| 2026-08-27 | M2 | suite Ruolo mirata dopo fix watermark | `PASS`; 18 test |
| 2026-08-27 | M2 | coverage runtime autosync Ruolo | `PASS`; 949 statement e 88 branch al 100% su modelli Catasto/Ruolo e servizio, incluso il modello Ruolo concorrente |
| 2026-08-27 | M2 | migrazione su schema PostgreSQL isolato | `PASS`; 2 test, deduplica, vincolo, indici, parita metadata e round-trip |
| 2026-08-27 | M2 | benchmark read-only PostgreSQL locale | `PASS`; 1.124.188 sorgenti, 87.205 particelle distinte e 176.735 item; read model a 6 query fisse, 25 campioni: p95 64,773 ms prima e 18,367 ms dopo gli indici; transazione annullata |
| 2026-08-27 | M3 | suite runtime, queue, worker e PostgreSQL | `PASS`; 62 test |
| 2026-08-27 | M3 | coverage cinque runtime Presenze | `PASS`; 1056 statement e 142 branch al 100% |
| 2026-08-27 | M3 | migrazione/fencing PostgreSQL isolato | `PASS`; round-trip, `SKIP LOCKED` e stale owner fenced |
| 2026-08-27 | M4 | runner Gate Mobile | `PASS`; 4 test e 100% statement/branch |
| 2026-08-27 | M4 | cap browser credenziali SISTER | `PASS`; 40 test mirati, 265 statement e 54 branch al 100% su `sister_credential_pool.py`, inclusa l'allowlist concorrente |
| 2026-08-27 | M4 | `docker compose config --quiet` | `PASS`; servizi separati, healthcheck e budget validi |
| 2026-08-27 | M5 | regressione Presenze aggregata | `PASS`; 429 test, inclusi i test PostgreSQL configurati |
| 2026-08-27 | M5 | `make quality-test`, compile e diff check | `PASS`; 46 test quality, runtime compilato e whitespace valido |
| 2026-08-27 | M5 | Compose e Alembic | `PASS`; configurazione valida, servizi separati e singola head `20260827_1100` |
| 2026-08-27 | M5 | migrazione allowlist batch `20260827_1100` su schema PostgreSQL disposable | `PASS`; 2 test, metadata, preservazione righe, JSON allowlist e round-trip downgrade/upgrade |
| 2026-08-27 | M5 | regressione worker isolata per file | `PASS`; 406 test, inclusi browser, pool credenziali, selezione visure, retry, validazione PDF e orchestrazione |
| 2026-08-27 | M5 | coverage runtime worker modificati | `PASS`; 2774/2774 statement e 786/786 branch, 100% sugli otto moduli SISTER misurati |
| 2026-08-27 | M5 | regressione batch e allowlist credenziali | `PASS`; 62 test backend, 76 test frontend mirati e typecheck pulito |
| 2026-08-27 | M5 | coverage nuovi confini allowlist | `PASS`; backend 32 statement/12 branch e frontend 25 statement/19 branch/10 funzioni/22 linee, tutto al 100% |
| 2026-08-27 | M5 | statistiche per batch | `PASS`; durata live/finale, throughput, ETA, tentativi e credenziali usate esposti dal dettaglio e renderizzati nelle superfici batch |
| 2026-08-27 | M5 | coverage statistiche batch | `PASS`; backend 71 statement/22 branch e frontend 24 statement/22 branch/9 funzioni/19 linee, tutto al 100% |
| 2026-08-27 | M5 | build immagini `backend`, `elaborazioni-worker-runtime` e `frontend` | `PASS`; build Next, typecheck e generazione di 154 pagine completati; soli warning lint legacy |
| 2026-08-27 | M5 | smoke import immagini senza rete | `PASS`; backend e worker importabili con environment dummy, worker con Pillow `12.3.0` |
| 2026-08-27 | M5 | recovery lease PostgreSQL isolato | `PASS`; 3 test su round-trip, `SKIP LOCKED` e fencing dello stale owner |
| 2026-08-27 | M5 | gate CI coverage worker | `PASS`; target isolato per file, artifact JSON/XML, gate changed-file 100% e checker coperto al 100% |
| 2026-08-27 | M5 | complexity ratchet mirato contro `origin/main` | `PASS`; `findings: []` su scheduler, Ruolo autosync, Presenze, Gate Mobile e pool browser |
| 2026-08-27 | M5 | complexity ratchet globale contro `origin/main` | `BLOCKED_EXTERNAL`; 100 finding concorrenti, 96 regressioni legacy e 4 nuove violation, nessuno nel perimetro worker, baseline invariata |
| 2026-08-27 | M5 | Graphify code | `PASS`; Presenze, Ruolo e Operazioni senza drift topologico; backend ricostruito con 7.510 nodi, 18.425 archi e 441 community |
| 2026-08-27 | M5 | Graphify docs con `gpt-5.4-mini` | `PASS`; Presenze 419/854, Ruolo 707/1.761, Operazioni 298/665 e dominio aggregato 1.337/2.187 nodi/archi; piattaforma riallineata con refresh incrementale finale |

## Metriche quality ratchet

- Mode: `ordinary ratchet`
- Runtime scope M1: `backend/app/main.py` e nuovo
  `backend/app/platform_scheduler_runner.py`.
- Metriche prima `main.py`: LOC `122`, dipendenze `26`, cyclomatic max `6`,
  cognitive max `9`, nessuna violation.
- Metriche dopo `main.py`: LOC `96`, dipendenze `14`, cyclomatic max `6`,
  cognitive max `9`, nessuna violation.
- Metriche runner nuovo: LOC `56`, cyclomatic max `2`, cognitive max `1`,
  nessuna violation.
- Coverage M1: `100%` statement e branch sui due runtime modificati.
- Baseline diff: nessun aggiornamento; ratchet globale bloccato da modifiche
  concorrenti estranee al perimetro M1.
- M2: advisory lock PostgreSQL per utente; sorgente deduplicata con window
  query e watermark `created_at`; status con `GROUP BY`, liste `LIMIT 12` e 6
  query fisse; migrazione verso unicita `(user_id, cat_particella_id)` e indici
  mirati. Scheduler e `run-now` saltano un owner occupato; il refresh manuale
  attende sullo stesso lock. Benchmark p95 sullo stesso dataset:
  `64,773 -> 18,367 ms`. Coverage runtime M2: 949 statement e 88 branch al
  100% tra modelli e servizio.
- M3: `FOR UPDATE SKIP LOCKED`, lease 300 secondi, retry 30 secondi,
  generation fencing e heartbeat supervisore. Coverage 100% su 1056 statement
  e 142 branch dei cinque runtime modificati.
- M4: runner Gate Mobile LOC 36, cyclomatic max 3 e cognitive max 4; cap
  browser aggiunge un semaforo locale senza cambiare il claim delle richieste.
  Il pool corrente, inclusa l'allowlist concorrente, e coperto al 100% su 265
  statement e 54 branch con 40 test.
- Chiusura worker: 406 test eseguiti con un processo pytest per file per evitare
  la contaminazione degli stub globali installati da `test_worker.py`. Gli otto
  runtime worker SISTER modificati totalizzano 2774 statement e 786 branch, tutti
  coperti; non sono stati usati pragma o abbassamenti della soglia.
- Automazione CI: `make test-worker` riproduce l'isolamento, combina branch
  coverage e pubblica JSON/XML. Il gate worker changed-file richiede il 100%; il
  report runtime completo misura il debito legacy al 93% e resta warn-only.
- Packaging: le immagini backend, worker runtime e frontend sono state
  ricostruite. Gli smoke import offline confermano le dipendenze runtime del
  worker, inclusi Pillow `12.3.0` e `pytesseract 0.3.13`; il frontend completa
  build, typecheck e generazione di 154 pagine.
- Ratchet finale del perimetro: `PASS`, nessun finding. I callable principali
  rispetto alla baseline del merge-base sono diminuiti: claim Presenze
  cyclomatic/cognitive/LOC `5/4/32 -> 2/1/16`, run worker
  `51/116/262 -> 40/75/242`, refresh Ruolo `16/27/60 -> 1/0/2` e status Ruolo
  `9/8/51 -> 5/4/20`.
- Baseline diff: nessun aggiornamento. Il ratchet globale resta bloccato da
  modifiche concorrenti GIS e Ruolo tributi, quindi non puo autorizzare una
  sincronizzazione della baseline in questa change.

## Rischi aperti

- Il modulo runner GIS legacy resta importabile per compatibilita, ma lo stack
  standard non lo avvia; un deploy misto non deve lasciare attivi entrambi i
  runner sullo stesso job.
- Alcuni scheduler eseguono lavoro inline invece di accodarlo; l'estrazione
  isola l'API ma non sostituisce ancora tutte le esecuzioni con code persistenti.
- Le altre code non adottano ancora lo schema Presenze; vanno migrate per
  famiglia solo quando serve scalare repliche multiple.
- I budget Compose sono default iniziali validati staticamente e con test di
  concorrenza, ma richiedono tuning su un carico produzione rappresentativo.
- Il timer Gate Mobile eventualmente gia installato sul server va disabilitato
  prima di avviare il servizio Compose.
- La suite worker non va eseguita in un unico processo: `test_worker.py`
  installa stub globali in `sys.modules` che contaminano la collection degli
  altri file. `make test-worker` automatizza il percorso validato (`406` test);
  Pillow e pytesseract sono presenti nel venv e nell'immagine worker.
- Il ratchet esteso a tutta `modules/elaborazioni/worker` rileva 14 finding nel
  flusso SISTER concorrente escluso da questo redesign. Il ratchet del perimetro
  architetturale resta verde; la baseline non e stata aggiornata.
- Il report completo worker resta al 93%. I gap principali sono
  `autodoc_sync.py`, `reporting.py`, `runtime_policy.py` e
  `credential_vault.py` a 0%; seguono `anti_captcha_client.py` al 72% e i
  client/reliability browser tra 97% e 99%. La chiusura richiede una slice test
  separata e non blocca il gate 100% dei file modificati.
- Il ratchet globale del checkout deve tornare verde dopo la risoluzione delle
  modifiche concorrenti GIS/Ruolo tributi; nessuna baseline e stata assorbita.

## Backlog verifiche e implementazioni

| Priorita | Tipo | Attivita | Gate di chiusura | Stato |
| --- | --- | --- | --- | --- |
| P0 | merge | risolvere i 100 finding del ratchet globale e i 14 finding SISTER concorrenti | ratchet globale `findings: []`, baseline non ampliata per assorbire regressioni | `OPEN_CONCURRENT` |
| P0 | pre-deploy | provare `0900 -> 1000 -> 1100` su un restore del backup produzione | upgrade, smoke query, downgrade tecnico e nuovo upgrade documentati sul clone | `OPEN_EXTERNAL` |
| P0 | rollout | verificare e disabilitare il timer Gate Mobile host prima del servizio Compose | nessun timer/service legacy attivo e un solo owner Compose | `OPEN_EXTERNAL` |
| P0 | osservabilita | introdurre heartbeat semantici per scheduler e loop worker | healthcheck fallisce su loop fermo anche se PID 1 e ancora vivo | `OPEN_IMPLEMENTATION` |
| P1 | staging | canary a replica singola e soak su un ciclo di picco | zero duplicati/OOM, lease e retry coerenti, KPI prima/dopo registrati | `OPEN_EXTERNAL` |
| P1 | coverage | chiudere il report worker completo dal 93% al 100% | tutti i runtime worker al 100% statement e branch | `OPEN_IMPLEMENTATION` |
| P2 | evoluzione | spostare gli scheduler inline pesanti su code persistenti per famiglia | API e scheduler non eseguono carichi massivi inline | `PLANNED` |
| P2 | scalabilita | estendere lease/fencing oltre Presenze solo alle famiglie da replicare | crash/recovery e stale-owner testati per ogni nuova famiglia | `PLANNED` |

Gli healthcheck Compose correnti sono liveness check sul comando del PID 1. Sono
utili contro processi terminati o entrypoint errati, ma non dimostrano avanzamento
del loop; il canary deve quindi usare anche last-run, lease, eta coda ed eventi
persistiti finche gli heartbeat semantici non saranno implementati.

## Prossima azione

Sottoporre il change set a review e pianificare separatamente il rollout del
runbook. Prima del deploy devono essere risolti i finding concorrenti del
ratchet globale e va eseguito il dry-run delle migrazioni sul backup di
produzione. Nessun deploy o restart e stato eseguito durante questo programma.
