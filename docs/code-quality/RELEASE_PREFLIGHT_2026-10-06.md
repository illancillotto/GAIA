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
   (24 nello snapshot iniziale, 23 dopo retry, 22 dopo la slice SISTER sotto).
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

## Secondo finding chiuso — classificazione 501 SISTER

La regola dei tre messaggi di sessione bloccata usa una sequenza immutabile
e `any`, con gli stessi match e la stessa precedenza. Un messaggio bloccante
resta terminale anche se titolo/corpo contengono le indicazioni di home pronta.
Nessuna modifica a navigazione, timeout, correlazione, callback o retry.

- `_is_non_blocking_init_portale_error`: cognitive/cyclomatic 17/15 -> 15/13,
  LOC 16 invariata; nessun helper introdotto. Errore cyclomatic eliminato,
  warning residui. Cognitive/cyclomatic aggregate diminuiscono entrambe di 2.
- 10 nuove caratterizzazioni verdi prima e dopo; 40 test mirati e full-file
  coverage 149 statement e 40 branch al 100%, zero esclusioni.
- 86 test browser/DOM e 23 worker passano in processi isolati. L'esecuzione
  combinata produce 7 failure HTML per lo stub `async_playwright` di
  `test_worker.py`: riprodotte identiche anche sul runtime `75c008cd`.
  Nessuna modifica a test estranei o suppression; la suite combinata non e verde.
- Ruff/lint, diff-check e ratchet mirato verdi; ratchet globale contro
  `6b61fd27` 23 -> 22 finding, nessuno sul runtime toccato. Graphify worker
  aggiornato con il target dedicato. Baseline e soglie restano invariate.

Evidenze `/tmp/gaia-browser-full-ratchet.json`,
`/tmp/gaia-browser-coverage.json`, `/tmp/gaia-browser-base-integration.log`.
Il deploy resta non eseguito: oltre ai finding globali, la failure preesistente
di isolamento dei test combinati deve essere considerata nella verifica CI.

## Riconciliazione estesa dei sorgenti attivi

Audit successivo sul main applicativo `1c8456fb`, confermato anche con
`git ls-remote origin refs/heads/main`. Il CED resta sul checkout `6b61fd27`,
con gli stessi sette file tracciati modificati e gli overlay non tracciati.
Nessun file remoto e stato modificato e nessun servizio e stato riavviato.

Il confronto ora copre tutti i file Python presenti nei seguenti perimetri,
letti dai container e confrontati tramite AST senza attributi posizionali:

| Container / perimetro | AST identico a main | AST diverso | File solo remoti |
| --- | ---: | ---: | ---: |
| `gaia-backend`, `/app/app` | 843 | 39 | 0 |
| `gaia-elaborazioni-worker-runtime`, `/app/worker` e `/app/backend/app` | 817 | 70 | 0 |
| `gaia-elaborazioni-worker-visure`, `/app/worker` | 75 | 9 | 0 |

Per tutti i 70 file differenti del runtime worker, tutti i 9 del worker
visure e 38 dei 39 del backend, l'AST remoto coincide esattamente con una
versione nella storia di main. La ricerca ha considerato fino a 40 commit
per file. L'unica eccezione, `gate_mobile_payloads.py`, differisce soltanto
nella composizione del dizionario in `_gate_record_feature_values`:
il runtime usa `{**shift_record_values(record), ...}`, main usa
`shift_record_values(record) | {...}`. Il servizio restituisce un dizionario;
restano invariati valori e precedenza delle chiavi a destra. Non e un hotfix
funzionale da recuperare. Questo controllo identifica versioni pregresse,
non dimostra da solo l'equivalenza comportamentale di tutti i cambi successivi.

Gli hotfix SISTER del checkout sono AST-identici a main; quelli realmente
attivi nel worker visure sono gia rappresentati nella storia di main.
Le differenze Gate/inCass del checkout restano quelle analizzate sopra,
senza nuovi simboli remoti da recuperare; il loader inCass resta importato
ed esportato in main. Anche `frontend/package-lock.json` del checkout CED
e identico al file locale. `portal_probe.py` nell'hotfix irrigue e uno script
diagnostico esterno al runtime, non va importato ne eseguito per il rilascio.

La riconciliazione dei sorgenti applicativi verificati non richiede quindi
di copiare hotfix in main. Non copre dipendenze installate, binari, frontend
compilato, altri container o tutti i file delle immagini. Le label compose
confermano inoltre stack sovrapposti: backend, scheduler, Presenze, Gate e
runtime worker non sono stati creati tutti con lo stesso insieme di override.
Non usarle come prova che un singolo comando compose riproduca lo stack attivo.

Il ratchet globale rieseguito contro `6b61fd27` conferma **22 finding**,
exit code 1. Non sono state cambiate baseline, soglie o esclusioni.
I 325 test mirati riportati sopra restano evidenza dell'audit precedente:
non sono stati rieseguiti in questo passaggio read-only/documentale.

### Sequenza di rilascio ancora necessaria

1. Chiudere i finding globali in slice separate e verificare i gate CI,
   inclusa la failure di isolamento della suite SISTER combinata.
2. Prima di modificare il checkout CED, conservare un backup esterno di
   patch, file non tracciati, compose, configurazione e riferimenti immagine;
   verificare che sia leggibile e sufficiente al rollback, senza esporre segreti.
3. Preparare una release pulita dello SHA approvato senza sovrascrivere
   il checkout sporco; riconciliare esplicitamente i compose effettivi,
   mantenendo volumi, segreti, mount e parallelismo quattro del worker.
4. Verificare le immagini costruite e la catena migration rispetto al DB
   attivo prima del cambio runtime. Poi eseguire deploy e smoke test,
   con rollback delle immagini/configurazioni predisposto.

Artefatti aggiuntivi in `/tmp/gaia-release-audit-20261006/reconcile/`:
`checkout-comparison.json`, `backend-full-ast.json`, `worker-full-ast.json`,
`visure-full-ast.json`, `runtime-history-matches.json`,
`gate-mobile-payloads-active.diff` e `full-ratchet.json`.
Gli archivi sono snapshot di sorgenti, non backup completi di produzione.
Il deploy resta **NON eseguito**: l'autorizzazione a riconciliare gli hotfix
non autorizza a ignorare gate rossi o a eliminare overlay non verificati.

## Terzo finding chiuso — decoder del client API frontend

Sul main applicativo `7868b734`, una slice separa la decodifica HTTP da
fetch/timeout in `frontend/src/lib/api/core.ts`. Gli errori restano precedenti
a status 204/205, content-length esattamente zero e parsing del body.
Timeout, signal esterno, FormData, header, URL e messaggi restano invariati.

- `request`: cognitive/cyclomatic/LOC `24/20/60 -> 16/14/42`;
  decoder `6/6/21`, sotto soglia, nessuna violation trasferita.
- 61 test mirati verdi prima e dopo, coverage full-file 100%:
  119 statement, 99 branch e 17 funzioni dopo la modifica.
- Suite frontend completa: 277 file e 3962 test verdi, senza suppression.
- Typecheck, ESLint e diff-check PASS. Ratchet globale contro `6b61fd27`
  `22 -> 21` finding, nessuno sul runtime toccato; baseline invariata.
- Graphify frontend aggiornato; metriche e comandi in `PROGRESS.md`.
  MPC/MCP e le modifiche concorrenti restano fuori dalla slice.

Questo risultato non chiude il gate globale e non costituisce un deploy.
