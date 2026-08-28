# GAIA Worker Architecture Progress

Fonte di verita per l'implementazione del piano
`docs/WORKER_ARCHITECTURE_PLAN.md`.

## Stato generale

- Program status: `IMPLEMENTED_LOCAL`
- Current milestone: `M6 - pre-deploy e osservabilita completati localmente`
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
| 2026-08-27 | heartbeat su progresso loop invece del solo PID 1 | rileva event loop o supervisori bloccati senza confondere la liveness del processo con la salute operativa |
| 2026-08-27 | soglia Gate Mobile 900 s, altri loop 90 s | Gate include il ciclo outbound sincrono; i ticker/supervisori interni devono avanzare con frequenza molto maggiore |

## Milestone tracker

| Milestone | Stato | Gate |
| --- | --- | --- |
| M0 - audit e piano | `DONE` | documenti, baseline e invarianti versionati |
| M1 - scheduler fuori dall'API | `DONE` | runner singleton, Compose, test e coverage |
| M2 - Ruolo single-flight/performance | `DONE` | lock, query incrementali/status aggregate, benchmark |
| M3 - lease/fencing/fairness | `DONE` | migrazione, crash/recovery, PostgreSQL e coverage 100% |
| M4 - isolamento/limiti | `DONE_LOCAL` | servizi, cap browser, healthcheck, budget e runbook; deploy escluso |
| M5 - validazione finale | `DONE_LOCAL` | test aggregati, ratchet del perimetro e Graphify; blocco globale concorrente documentato |
| M6 - pre-deploy/health semantica | `DONE_LOCAL` | restore produzione, round-trip migration, audit timer CED e heartbeat stale-aware |

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
| 2026-08-28 | M6 | revalidazione SISTER dopo le modifiche concorrenti | `PASS`; `make test-worker` finale 430 test e tutti i 27 runtime al 100%; suite backend batch/allowlist/integration e migration PostgreSQL verdi |
| 2026-08-27 | M6 | restore backup CED `gaia-20260820-172136-pre-sister-20260820-172136.dump` | `PASS`; SHA-256 locale/remoto `fab968aa...7818`, restore PostgreSQL/PostGIS isolato exit 0; il dump locale del 6 agosto e stato scartato per EOF durante i dati |
| 2026-08-27 | M6 | round-trip `20260826_1200 -> 0900 -> 1000 -> 1100` sul clone | `PASS`; nuovo unique e 3 indici Ruolo, zero duplicati, 7 colonne/3 indici Presenze e allowlist JSON; downgrade pulito e secondo upgrade ripetibile |
| 2026-08-27 | M6 | audit Gate Mobile CED in sola lettura | `PASS`; timer/service systemd non installati, nessuna unita alias attiva e servizio Compose non ancora presente; nessuna disabilitazione necessaria |
| 2026-08-27 | M6 | heartbeat semantici e Compose | `PASS`; file atomici stale-aware per 7 servizi, `docker compose config --quiet`, 43 test backend e coverage finale 374 statement/74 branch al 100% |
| 2026-08-27 | M6 | canary singola replica su DB/schema clone isolato | `PASS_IDLE`; 7 loop, 120 s, zero restart/OOM/duplicati, 16 PID ciascuno, RSS 89-166 MiB; heartbeat tutti freschi e Gate disabilitato senza chiamate esterne |
| 2026-08-27 | M6 | fault injection heartbeat | `PASS`; worker AUTODOC in pausa con PID vivo, check stale exit 1, recovery verde dopo `unpause` senza restart |
| 2026-08-27 | M6 | compatibilita immagine worker Python 3.10 | `PASS`; sostituiti due usi runtime di `datetime.UTC`; startup delle 4 famiglie e coverage backend finale 374 statement/74 branch al 100% |
| 2026-08-28 | M6 | coverage globale worker | `PASS`; 430 test isolati per file, 27 runtime, 5077/5077 statement e 1314/1314 branch al 100% |
| 2026-08-28 | M6 | complexity ratchet finale contro `origin/main` | `PASS_SELECTED`; nessun finding nel perimetro worker, healthcheck e supervisori. Il checkout globale resta bloccato soltanto dalle modifiche concorrenti GIS M21/sidebar escluse dalla slice; baseline invariata |
| 2026-08-27 | M6 | Graphify backend e platform docs | `PASS`; backend 7.535 nodi/18.564 archi/446 community; docs 1.398 nodi/3.051 archi/101 community, 112 file da cache e 3 riestratti |

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
- M6 health: nuovo `app.worker_health` con JSON atomico e CLI stale-aware;
  ticker asincrono per scheduler/Elaborazioni, progress per giro supervisore
  Presenze e stato ciclo Gate Mobile. Il perimetro backend finale totalizza
  374 statement e 74 branch al 100%. Nessuna soglia o pragma coverage e stata
  modificata.
- Chiusura worker: 430 test eseguiti con un processo pytest per file per evitare
  la contaminazione degli stub globali installati da `test_worker.py`. Tutti i
  27 runtime worker totalizzano 5077 statement e 1314 branch, tutti coperti;
  non sono stati usati pragma o abbassamenti della soglia.
- Automazione CI: `make test-worker` riproduce l'isolamento, combina branch
  coverage e pubblica JSON/XML. Il gate worker changed-file richiede il 100% e
  il report runtime completo ha ora raggiunto il 100% statement/branch.
- Packaging: le immagini backend, worker runtime e frontend sono state
  ricostruite. Gli smoke import offline confermano le dipendenze runtime del
  worker, inclusi Pillow `12.3.0` e `pytesseract 0.3.13`; il frontend completa
  build, typecheck e generazione di 154 pagine.
- Ratchet finale del perimetro: `PASS`, nessun finding. I callable principali
  rispetto alla baseline del merge-base sono diminuiti: claim Presenze
  cyclomatic/cognitive/LOC `5/4/32 -> 2/1/16`, run worker
  `51/116/262 -> 40/75/242`, refresh Ruolo `16/27/60 -> 1/0/2` e status Ruolo
  `9/8/51 -> 5/4/20`.
- Baseline diff: nessun aggiornamento. Il perimetro worker non produce finding;
  il checkout globale resta bloccato dalle modifiche concorrenti GIS M21/sidebar
  escluse dalla slice e non autorizza una sincronizzazione della baseline.

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
- L'audit CED del 2026-08-27 non ha trovato il timer Gate Mobile installato; va
  comunque ripetuto immediatamente prima del rollout per evitare drift host.
- La suite worker non va eseguita in un unico processo: `test_worker.py`
  installa stub globali in `sys.modules` che contaminano la collection degli
  altri file. `make test-worker` automatizza il percorso validato (`430` test);
  Pillow e pytesseract sono presenti nel venv e nell'immagine worker.
- Il ratchet stabile non rileva regressioni su `_process_batch` o sulla closure
  `_credential_runner`. Healthcheck, supervisori e test aggiunti non producono
  finding; i soli blocchi globali appartengono al GIS M21/sidebar concorrenti e
  restano esclusi. La baseline non e stata aggiornata.
- Il bootstrap Alembic da database completamente vuoto fallisce nella revisione
  storica `20260612_0900` per assenza di `org_unit`. Il dry-run su backup reale
  e valido; il canary ha usato uno schema-only clone a head con tabelle vuote.
  La catena greenfield richiede una correzione migration separata e testata.
- Il canary eseguito e uno soak idle/sicuro, non un ciclo di picco con browser o
  payload reali. Il soak di picco resta un gate di staging/pre-produzione.

## Backlog verifiche e implementazioni

| Priorita | Tipo | Attivita | Gate di chiusura | Stato |
| --- | --- | --- | --- | --- |
| P0 | merge | integrare la slice worker separatamente dal GIS M21/sidebar concorrente | ratchet del perimetro worker senza finding, baseline invariata | `DONE_LOCAL` |
| P0 | pre-deploy | provare `0900 -> 1000 -> 1100` su un restore del backup produzione | upgrade, smoke query, downgrade tecnico e nuovo upgrade documentati sul clone | `DONE_LOCAL` |
| P0 | rollout | verificare e disabilitare il timer Gate Mobile host prima del servizio Compose | nessun timer/service legacy attivo e un solo owner Compose | `VERIFIED_NO_LEGACY_UNIT` |
| P0 | osservabilita | introdurre heartbeat semantici per scheduler e loop worker | healthcheck fallisce su loop fermo anche se PID 1 e ancora vivo | `DONE_LOCAL` |
| P1 | staging | canary a replica singola e soak su un ciclo di picco | zero duplicati/OOM, lease e retry coerenti, KPI prima/dopo registrati | `IDLE_CANARY_PASS_PEAK_OPEN` |
| P1 | migration | riparare bootstrap Alembic greenfield a `20260612_0900` | `alembic upgrade head` da `template0` passa e preserva upgrade backup | `OPEN_PREEXISTING` |
| P1 | coverage | chiudere il report worker completo dal 93% al 100% | tutti i runtime worker al 100% statement e branch | `DONE_LOCAL` |
| P2 | evoluzione | spostare gli scheduler inline pesanti su code persistenti per famiglia | API e scheduler non eseguono carichi massivi inline | `PLANNED` |
| P2 | scalabilita | estendere lease/fencing oltre Presenze solo alle famiglie da replicare | crash/recovery e stale-owner testati per ogni nuova famiglia | `PLANNED` |

Gli healthcheck Compose verificano ora l'avanzamento semantico del loop tramite
heartbeat stale-aware. Il canary deve comunque usare anche last-run, lease, eta
coda ed eventi persistiti: il heartbeat prova responsivita, non successo del job.

## Prossima azione

Sottoporre il change set a review e pianificare separatamente il rollout del
runbook. Prima del deploy devono essere risolti i finding concorrenti del
ratchet globale e va eseguito il dry-run delle migrazioni sul backup di
produzione. Nessun deploy o restart e stato eseguito durante questo programma.
