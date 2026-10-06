# Preflight rilascio dopo le slice di complessita

## Stato verificato

Commit applicativo: `9a11320d344a230dc7c86c45065836e63dff3b83`, push
confermato su `origin/main` anche tramite `git ls-remote`. Il push pubblica
la storia committata da `6b61fd27` fino a questo commit, non soltanto banca ore.
Le modifiche documentali concorrenti nel working tree locale sono preservate
e non incluse. MPC/MCP resta escluso dalle slice di refactoring.

La slice banca ore ha 227 test router/API verdi e coverage full-file 100%
(221 statement, 72 branch), lint/format e ratchet mirato verdi. Review:
`domain-docs/presenze/docs/BANK_HOURS_COMPLEXITY_VALIDATION_2026-10-06.md`.
Graphify Presenze codice/docs e platform docs aggiornati; estrazioni docs
con `chunk 1/1 done`, senza warning di chunk semantici falliti.

## Gate globale

Snapshot iniziale sul commit `9a11320d`: il confronto dell'intero repository contro il merge-base del push
`6b61fd27` NON e verde: 24 finding, 17 `legacy_metric_regression` e
7 `new_callable_violation`. Non sono attribuiti alla sola slice banca ore.
Nessuna baseline, esclusione o soglia e stata aggiornata per assorbirli.

```bash
python tools/code_quality/complexity.py ratchet --base-ref 6b61fd27
```

Evidenza: `/tmp/gaia-release-audit-20261006/full-ratchet.json`.
Il controllo GitHub per lo SHA applicativo mostra soltanto check Dependabot
e dependency graph riusciti; non prova backend-ci, frontend-ci o code-quality-ci
verdi. Non equiparare l'assenza di quei check a un esito positivo.

Il push segnala inoltre 32 advisory Dependabot (1 critical, 15 high,
13 moderate, 3 low): non e stato svolto un audit vulnerabilita in questa slice.

## Riconciliazione CED

L'utente richiede esplicitamente di riconciliare gli hotfix con main prima
del deploy. Finora tutte le verifiche remote sono read-only.

- Checkout `/opt/gaia` sul CED: `6b61fd27`, sette file tracciati modificati,
  file runtime e overlay non tracciati. Nessun reset, stash o restore eseguito.
- I tre sorgenti SISTER `sister_exceptions.py`, `sister_request_rows.py` e
  `sister_requests_navigation.py` hanno AST identico a main.
- La cancellazione squadre e il controllo console-admin sono gia in main;
  il dispatcher differisce per il refactoring a tabella.
- La materializzazione inCass e la preservazione dei dettagli pesanti sono
  presenti in main. Il controllo proprietario dell'avviso e aggiunto in main;
  il read model accetta anche identificativi ordinari con prefisso `1`.
- L'ack di cancellazione squadra usa `team_id` anche in main. Altre funzioni
  Gate, recupero inCass e risoluzione soggetti differiscono e richiedono la
  verifica dei contratti/test, non una semplice equivalenza testuale.

Il checkout non descrive da solo i container in esecuzione:

| Servizio | Immagine rilevata |
| --- | --- |
| backend | `gaia-backend:turnisti-open-ended-44b0c4ac` |
| frontend | `gaia-frontend` |
| elaborazioni-worker-runtime | `gaia-elaborazioni-worker-runtime:irrigue-four-20261005` |

Gli overlay attivi comprendono inCass, recupero Capacitas/irrigue, quattro
worker paralleli e il compose override frontend. Gate sync e presenze worker
montano il backend della release `turnisti-open-ended-44b0c4ac` su `/app`.
Non e ancora dimostrata la riconciliazione completa delle immagini/overlay
attivi con il nuovo checkout. Tutti i servizi dotati di healthcheck risultano
healthy; il manifest release storico non prova lo SHA delle immagini attive.

## Decisione operativa

Deploy NON eseguito: nessun restart, migration, modifica dati o env remoto.
Il deploy standard `scripts/deploy-ced-gaia.sh` richiede checkout pulito,
builda lo stack base e copia l'env locale sul server; non usarlo per eliminare
implicitamente hotfix e configurazioni di produzione non riconciliati.

Prima del rilascio occorrono:

1. Chiudere o decidere esplicitamente i finding globali in slice revisionabili
   (24 nello snapshot iniziale, 23 dopo la slice retry sotto).
2. Verificare le regressioni degli hotfix e le immagini realmente attive,
   conservando backup e possibilita di rollback prima di qualsiasi mutazione.
3. Confrontare overlay ed env senza pubblicare segreti, preservando volumi,
   segreti e configurazione canonica di produzione.
4. Dimostrare i gate della release, poi deploy canonico e smoke test finali.

Artefatti audit locali: `/tmp/gaia-release-audit-20261006/`;
checkpoint `/tmp/gaia-release-context-checkpoint-20261006.md`.
Il programma di complessita resta incompleto e non viene dichiarato concluso.

## Verifica aggiuntiva delle immagini attive

Successivo audit read-only, senza modifiche a runtime, env o dati:

- Nel container backend attivo, gli AST di `gate_mobile_team_actions.py`,
  `gate_mobile_sync.py`, `elaborazioni_capacitas_incass.py` e
  `incass_read_model.py` sono identici a main. Le differenze osservate nel
  checkout root non rappresentano questi quattro sorgenti realmente eseguiti.
- Nell'immagine worker runtime, `runtime_runner.py`, `capacitas_lane_gate.py`,
  `domande_irrigue_parallel.py`, `ordered_prefetch.py` e `registry_prefetch.py`
  hanno AST identico a main. Parallelismo default quattro worker invariato.
- Il worker conserva una versione precedente del read model/inCass: main
  accetta anche il prefisso ordinario `1`, impedisce cambio proprietario
  dell'avviso e separa la ripresa dei job con `recovery_task_key` dal recupero
  legacy. Il resolver soggetti e delegato al servizio recovery; il loader
  resta esportato tramite import, non e una API eliminata.
- Confronto env tramite digest, senza esporre valori: nessuna chiave condivisa
  differisce; `APP_ENV`, database, password Postgres, JWT, master key credenziali,
  volume Postgres e API base coincidono. L'unica chiave presente solo nel file
  locale e `ELABORAZIONI_RUNTIME_PARALLEL_WORKERS`, gia quattro nel default
  del runtime e nell'overlay remoto. Nessuna copia env eseguita.

### Test di regressione sul main pubblicato

| Suite | Test verdi |
| --- | ---: |
| Cancellazione squadre, read model inCass, Gate mobile sync | 90 |
| SISTER navigation/HTML/correlazione e runtime runner | 106 |
| Recupero Capacitas, sorgenti parallele, scheduler irrigue, inCass | 129 |
| Totale aggiuntivo | 325 |

Comandi mirati, nessuna esclusione o modifica ai test:

```bash
.venv/bin/python -m pytest -q backend/tests/test_gate_mobile_team_delete.py \
  backend/tests/ruolo/test_incass_read_model.py backend/tests/test_gate_mobile_sync.py
.venv/bin/python -m pytest -q \
  modules/elaborazioni/worker/tests/test_sister_requests_navigation.py \
  modules/elaborazioni/worker/tests/test_sister_requests_navigation_html.py \
  modules/elaborazioni/worker/tests/test_sister_request_rows.py \
  modules/elaborazioni/worker/tests/test_runtime_runner.py
.venv/bin/python -m pytest -q backend/tests/test_capacitas_full_recovery.py \
  backend/tests/test_runtime_parallel_sources.py \
  backend/tests/test_domande_irrigue_autosync_scheduler.py \
  backend/tests/test_elaborazioni_capacitas.py -k 'incass or recovery or parallel or domande'
```

La terza suite emette un RuntimeWarning nel test `test_cli_module_entrypoint`
per il modulo gia caricato in `sys.modules` prima di `runpy`; non e una failure
di test. Nessun runtime e stato modificato in questo audit, nessuna suppression
introdotta. Questi test non sostituiscono il gate globale ancora rosso e non
dimostrano l'equivalenza dell'intero filesystem delle immagini.

Log e snapshot sanitizzati sotto `/tmp/gaia-release-audit-20261006/`:
`hotfix-backend-tests.log`, `hotfix-worker-tests.log`, `incass-parallel-tests.log`,
`backend-active.tar.gz`, `worker-active.tar.gz`, `env-comparison.json`.
Il deploy resta non eseguito, in attesa della decisione sui prerequisiti globali.

## Primo finding chiuso — retry sync Presenze

Una slice successiva isola parsing legacy e formato del checkpoint in
`_has_sync_job_resume_checkpoint`, nello stesso file della route. Nessuna
variazione a HTTP, auth, stato, limite tentativi, artefatti o transazioni.

- `retry_sync_job`: cognitive/cyclomatic/LOC 19/17/29 -> 13/11/27.
- Helper 5/6/6, un parametro e zero violation; cognitive aggregate 98 -> 97,
  cyclomatic aggregate 88 -> 88. Nessun trasferimento di violation.
- 22 nuove caratterizzazioni verdi prima e dopo; suite router/API 249 test.
- Coverage full-file `router/routes/sync_jobs.py`: 144 statement e 42 branch
  al 100%, zero esclusioni. Ruff, format runtime, lint e ratchet mirato verdi.
- Ratchet globale contro `6b61fd27`: 24 -> 23 finding, nessuno nel file
  modificato. Gate globale ancora non verde; baseline e soglie invariate.

Evidenze `/tmp/gaia-retry-full-ratchet.json` e `/tmp/gaia-retry-coverage.json`;
metriche e comandi in `PROGRESS.md`. Questa verifica non autorizza a saltare
gli altri prerequisiti e non costituisce un deploy. MPC/MCP esclusi dalla slice.
