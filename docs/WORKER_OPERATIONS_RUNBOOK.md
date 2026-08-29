# GAIA Worker Operations Runbook

## Scopo

Questo runbook descrive deploy, osservazione e rollback dell'architettura worker
versionata in `docs/WORKER_ARCHITECTURE_PLAN.md`. Non autorizza implicitamente
interventi in produzione.

## Servizi e ownership

| Servizio | Responsabilita | Default iniziale |
| --- | --- | --- |
| `backend` | quattro processi Uvicorn solo HTTP | 4 CPU, 4 GiB, 512 PID |
| `platform-scheduler` | tutti gli undici trigger APScheduler | 2 CPU, 2 GiB, 256 PID |
| `presenze-worker` | claim e child delle sync Presenze | 3 CPU, 4 GiB, 512 PID |
| `elaborazioni-worker-visure` | SISTER, AdE e bulk catastali | 6 CPU, 8 GiB, 1536 PID, 4 browser |
| `elaborazioni-worker-runtime` | Capacitas e import REGISTRY | 2 CPU, 2 GiB, 256 PID |
| `elaborazioni-worker-poste` | Poste Online e relativo browser | 2 CPU, 3 GiB, 768 PID |
| `elaborazioni-worker-autodoc` | AUTODOC e relativo browser | 2 CPU, 3 GiB, 768 PID |
| `gate-mobile-sync` | proiezione outbound verso Gate ogni 5 minuti | 1 CPU, 1 GiB, 128 PID |

I budget sono limiti di sicurezza iniziali, non valori di capacity planning
definitivi. Possono essere modificati dalle variabili documentate in
`.env.example` senza cambiare Compose.

## Single-flight Ruolo

L'autosync Ruolo usa un advisory lock PostgreSQL per utente. Scheduler e
`run-now` usano un tentativo non bloccante: se esiste gia un owner non avviano
una seconda materializzazione. Il refresh manuale usa lo stesso lock in modalita
bloccante, preservando il contratto HTTP e aspettando il ciclo corrente.

Lo status e read-only: esegue sei query fisse, usa `GROUP BY` per i conteggi e
limita a 12 elementi sia recenti sia errori. Il benchmark locale su 176.735 item
ha misurato p95 `64,773 ms` prima e `18,367 ms` dopo gli indici della migrazione
`20260827_0900`, su 25 campioni e senza persistere la migrazione nel DB locale.

## Lease Presenze

- Claim: `FOR UPDATE SKIP LOCKED`, ordinato per priorita, retry e anzianita.
- Lease default: 300 secondi, rinnovata dal supervisore dei child attivi.
- Recovery: lease scaduta riaccodata dopo 30 secondi finche restano tentativi.
- Fencing: `lease_generation` e la colonna di versione SQLAlchemy; un owner
  stale riceve `StaleDataError` e termina con exit code `75`.
- Cancellazione: generation incrementata e lease pulita prima di inviare
  `SIGTERM` al process group.
- Shutdown del supervisore: non marca il job cancellato; la lease scade e il
  recovery lo riaccoda.

Variabili:

```dotenv
PRESENZE_WORKER_LEASE_SECONDS=300
PRESENZE_WORKER_RETRY_BACKOFF_SECONDS=30
```

La lease deve essere almeno tre volte il massimo intervallo di polling atteso.

## Gate Mobile

`gate-mobile-sync` esegue subito un ciclo e poi attende
`GATE_MOBILE_SYNC_INTERVAL_SECONDS`, con default 300. Un errore di ciclo viene
registrato e ritentato al ciclo seguente; SIGINT e SIGTERM chiudono il loop.

Prima del rollout verificare e disabilitare il timer host legacy, se presente:

```bash
sudo systemctl disable --now gaia-gate-mobile-sync.timer
sudo systemctl disable --now gaia-gate-mobile-sync.service
```

Non avviare contemporaneamente timer legacy e servizio Compose.

## Sequenza rollout

1. Salvare un backup, verificare una sola head Alembic e applicare le
   migrazioni additive fino a `head`. Nel checkout validato la head e
   `20260827_1100`; le revisioni del redesign worker sono `20260827_0900` e
   `20260827_1000`, mentre `20260827_1100` aggiunge l'allowlist credenziali
   batch usata dallo stesso runtime SISTER.
2. Verificare che il timer Gate Mobile legacy sia disabilitato.
3. Ricreare `backend` con scheduler API disabilitati.
4. Avviare un solo `platform-scheduler` e verificare il suo healthcheck.
5. Avviare `presenze-worker` a replica singola e osservare claim e heartbeat.
6. Avviare separatamente runtime, Poste, Visure e AUTODOC.
7. Avviare `gate-mobile-sync` e verificare l'ultimo run dall'endpoint admin.
8. Aumentare la concorrenza solo dopo un ciclo completo senza duplicati.

Comandi di sola configurazione prima del deploy:

```bash
docker compose config --quiet
docker compose config --services
```

## Validazione pre-rollout

Eseguire i gruppi coverage separatamente, sempre con branch coverage e soglia
100%. Il registro dei conteggi autorevole e
`docs/WORKER_ARCHITECTURE_PROGRESS.md`.

```bash
cd backend
.venv/bin/python -m pytest tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py tests/test_platform_scheduler_runner.py --cov=app.main --cov=app.platform_scheduler_runner --cov-branch --cov-fail-under=100
.venv/bin/python -m pytest tests/test_elaborazioni_api.py -k ruolo_autosync --cov=app --cov-branch --cov-report=
.venv/bin/python -m pytest tests/ruolo/test_tributi_api.py::test_tributi_calculation_policy_crud_validates_active_year_ranges --cov=app --cov-branch --cov-append --cov-report=
.venv/bin/python -m coverage report --include='app/models/catasto.py,app/modules/ruolo/models.py,app/services/elaborazioni_ruolo_autosync.py' --fail-under=100
.venv/bin/python -m pytest tests/test_presenze_queue_worker.py tests/test_presenze_sync_runtime.py tests/test_presenze_sync_worker.py --cov=app --cov-branch --cov-report=
.venv/bin/python -m coverage report --include='app/modules/presenze/models.py,app/modules/presenze/sync_models.py,app/modules/presenze/services/queue_worker.py,app/modules/presenze/services/sync_runtime.py,app/modules/presenze/services/sync_worker.py' --fail-under=100
.venv/bin/python -m pytest tests/test_gate_mobile_sync_runner.py --cov=app.scripts.gate_mobile_sync_runner --cov-branch --cov-fail-under=100
```

Le prove PostgreSQL devono usare uno schema disposable tramite
`GAIA_TEST_POSTGRES_URL`. Nello stack locale:

```bash
docker compose exec -T backend sh -lc 'GAIA_TEST_POSTGRES_URL="$DATABASE_URL" python -m pytest -m postgres tests/test_ruolo_autosync_migration_postgres.py tests/test_presenze_worker_leases_postgres.py tests/test_catasto_batch_credential_allowlist_migration_postgres.py'
docker compose exec -T backend sh -lc 'GAIA_TEST_POSTGRES_URL="$DATABASE_URL" python -m pytest tests/test_presenze_*.py'
```

La regressione worker e la coverage combinata usano il target condiviso da CI:

```bash
make test-worker
python scripts/check_changed_worker_coverage.py \
  --coverage-json backend/coverage-worker.json \
  --base-sha origin/main \
  --head-sha HEAD \
  --min-coverage 100
```

La regressione completa worker deve usare un processo pytest distinto per ogni
file. `test_worker.py` installa stub globali in `sys.modules`, quindi una singola
collection aggregata puo dipendere dall'ordine. Nel checkout validato il totale
e `430 passed`; tutti i 27 runtime worker sono al 100% con `5077/5077`
statement e `1314/1314` branch. Il report completo runtime e pubblicato da CI;
il gate changed-file resta attivo e il totale globale non ha piu gap noti.

Per l'allowlist credenziali dei batch, eseguire anche i gate mirati del servizio
backend e del selettore UI documentati nel runbook SISTER. Nel checkout
validato entrambi sono al 100%; la regressione associata conta 62 test backend,
76 test frontend e typecheck TypeScript pulito.

Prima del rollout ricostruire tutte le superfici modificate e verificare gli
import senza accesso di rete:

```bash
docker compose build backend elaborazioni-worker-runtime frontend
docker run --rm --network none --env-file .env gaia-backend python -c 'import app.main'
docker run --rm --network none --env-file .env gaia-elaborazioni-worker-runtime python -c 'import PIL, worker; print(PIL.__version__)'
```

Usare credenziali e URL dummy per gli smoke import se `.env` non e disponibile;
lo smoke non deve connettersi a PostgreSQL, Redis o servizi esterni. La build
validata completa anche typecheck Next e generazione di 154 pagine.

## Osservabilita

Scheduler e worker pubblicano heartbeat JSON atomici in
`runtime-data/worker-health/`. Gli healthcheck Compose usano
`python -m app.worker_health check` e falliscono quando il timestamp non avanza,
anche se il PID 1 e ancora vivo. Scheduler, Presenze e le quattro famiglie
Elaborazioni hanno una soglia di 90 secondi; Gate Mobile usa 900 secondi per
includere intervallo e durata del ciclo outbound.

```bash
docker compose ps platform-scheduler gate-mobile-sync presenze-worker \
  elaborazioni-worker-visure elaborazioni-worker-runtime \
  elaborazioni-worker-poste elaborazioni-worker-autodoc
jq . runtime-data/worker-health/*.json
docker compose exec platform-scheduler \
  python -m app.worker_health check --service platform-scheduler \
  --max-age-seconds 90
```

Un heartbeat `healthy` prova la responsivita del loop/supervisore, non il
successo funzionale dei job. Durante canary e soak la decisione deve quindi
includere anche last-run, lease, eta coda ed eventi persistiti. Per Gate Mobile
il file passa da `cycle_running` a `waiting` e registra `last_exit_code`; per
Presenze espone `active_jobs`; per Elaborazioni espone le famiglie assegnate.

Nel canary isolato si puo provare esplicitamente la staleness mettendo in pausa
un solo container e verificando da un altro container che il comando esca 1;
eseguire sempre `unpause` e controllare il ritorno a `healthy`. Non usare fault
injection sullo stack di produzione.

Controllare almeno:

- p50/p95/p99 e timeout API;
- CPU, RSS, PID e OOM per servizio;
- connessioni e query lente PostgreSQL;
- job `pending/running`, eta del piu vecchio e throughput;
- lease scadute, retry, generation e job falliti a max attempts;
- numero di processi Chromium e sessioni SISTER;
- ultimo run Gate Mobile e relativo `error_kind`.

Il cap browser e applicato da `ELABORAZIONI_BROWSER_SESSION_LIMIT` prima del
`pids_limit`. Se il servizio Visure raggiunge 1536 PID con non piu di quattro
sessioni, raccogliere `docker stats`, processi Chromium e thread prima di
aumentare il limite.

## Tuning

Modificare un solo budget per volta e osservare almeno un ciclo di picco. Un
OOM richiede prima l'analisi di RSS per browser/job; un throttling CPU continuo
richiede confronto con latenza e throughput. Non rimuovere i limiti in blocco.

Per aumentare Visure da quattro a sei sessioni:

```dotenv
ELABORAZIONI_BROWSER_SESSION_LIMIT=6
```

Ricalibrare memoria e PID soltanto dopo la misura del nuovo picco.

## Rollback

- Scheduler: fermare `platform-scheduler` prima di ripristinare qualsiasi
  registrazione nell'API; non lasciare mai entrambi attivi.
- Presenze: mantenere una sola replica. Le colonne additive possono restare;
  il downgrade DB va eseguito solo dopo rollback del codice.
- Gate Mobile: fermare il servizio Compose prima di riattivare il timer host.
- Poste: riportare temporaneamente `ELABORAZIONI_WORKER_FAMILIES_RUNTIME` a
  `runtime,poste` solo dopo aver fermato `elaborazioni-worker-poste`.
- Limiti: aumentare il singolo budget che interrompe un carico valido; non
  eliminare contemporaneamente CPU, memoria e PID.

## Evidenze rollout

Registrare timestamp, versione, migrazioni, servizi avviati, healthcheck,
metriche prima/dopo, job duplicati, lease scadute, OOM e decisioni di tuning in
`docs/WORKER_ARCHITECTURE_PROGRESS.md`.
