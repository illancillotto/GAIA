# SISTER: supervisione dei blocchi del worker

## Incidente e causa osservata

Il 2026-10-06 alle 08:28:59 Europe/Rome PostgreSQL ha registrato un
segmentation fault del processo che eseguiva una query PostGIS con
ST_AsGeoJSON / ST_CollectionExtract / ST_SimplifyPreserveTopology / ST_Collect
su cat_particelle. Il server ha terminato le altre connessioni ed e entrato
in recovery, tornando disponibile alle 08:29:26.

Il worker visure ha ricevuto OperationalError durante il controllo delle
richieste aperte del credential pool. L'ultimo heartbeat e delle 08:28:49;
il log termina alle 08:29:00 durante logout/chiusura della sessione SISTER.
Alle 16:38 il processo era ancora vivo ma unhealthy, senza nuove elaborazioni.
La sequenza e documentata nei log CED; il punto esatto di sospensione non e
dimostrato da uno stack live del processo. Non attribuire il crash ai sync
senza ulteriori evidenze. La query corrisponde alla superficie preview
geometrie distretti del modulo Catasto: il crash PostGIS richiede un audit
separato, non e corretto da questa slice.

## Fix committata, rilascio annullato

Commit 63291539. Il tentativo di rilascio del 2026-10-06 ha evidenziato
un'incompatibilita con i sync AdE sincroni nel loop del worker: vedere la
sezione operativa finale. La fix NON e attiva sul CED e non va ridistribuita
prima di risolvere questa incompatibilita.

worker_runner.py avvia il worker mediante run_supervised, nello stesso processo.
sister_worker_watchdog.py osserva da un thread indipendente il file heartbeat
gia esistente: non pubblica un heartbeat proprio e non nasconde i blocchi.
Timeout 120 secondi senza avanzamento, controllo ogni 5 secondi; il limite
Docker healthcheck di 90 secondi resta invariato.

Il marker deve essere finito, numerico e appartenere al PID corrente. File
assenti, illeggibili, JSON invalido o heartbeat di un altro PID non resettano
la scadenza. Il tempo trascorso e misurato con monotonic, non con l'orologio
civile. Un cambiamento del marker valido resetta il timer.

Se il loop rimane bloccato, oppure asyncio.run resta sospeso nella cancellazione
dei task dopo un errore mentre il heartbeat non avanza, il thread termina
il processo con exit 1. La policy Docker esistente unless-stopped consente
il riavvio; nessun nuovo cron, container o dipendenza runtime introdotto.
Il watchdog resta attivo fino al ritorno effettivo di asyncio.run, poi viene
fermato e joined su completamento normale o eccezione propagata.

Non modifica account, calendari, DB, ID remoti, retry o transazioni. L'avvio
successivo usa il recovery/fencing esistente. Un arresto forzato non garantisce
logout remoto o completamento delle transazioni: non autorizza reinvii o
recuperi massivi. Nessun deploy, riavvio produttivo o commit in questa slice.

## Matrice di verifica

| Comportamento | Test |
| --- | --- |
| Timing invalidi rifiutati | test_invalid_timing_fails_closed |
| Heartbeat assente, corrotto, invalido o di altro processo non nasconde il blocco | test_invalid_or_foreign_heartbeat_does_not_hide_stall; test_missing_or_malformed_heartbeat_does_not_hide_stall |
| Marker valido e avanzamento monotonic | test_current_process_heartbeat_accepts_finite_timestamp; test_progress_and_unchanged_marker_use_monotonic_time |
| Scadenza termina con exit 1 e log diagnostico senza dati account | test_stalled_heartbeat_exits_nonzero |
| Thread chiuso su ritorno/errore ordinari | test_supervisor_stops_thread_on_clean_return_or_error |
| Processo reale bloccato nel loop o nella cancellazione viene terminato; loop sano sopravvive oltre il timeout | test_real_process_supervision |
| Integrazione nel runner e heartbeat esistente | test_worker_runner.py, incluso entrypoint __main__ |

Test mirati: 23 superati, coverage dei due runtime 100% statement e branch
(63 statement, 14 branch). Riproduzioni reali in subprocess, senza portale
o database produttivo; coverage JSON /tmp/sister-watchdog-coverage.json.
Ruff e formato nuovi file superati. Ratchet read-only contro merge-base
origin/main: findings vuoto, baseline invariata.
Metriche: runner run_worker/main restano cog/cyc 0/1; watchdog read_marker
17/10, monitor 9/6, costruttore 5/5, supervisione 1/2. Lo scanner segnala due
warning, nessuna violazione error-level: il parser difensivo merita attenzione,
non sono introdotti split artificiali per abbassare la metrica.

Regression gate make test-worker: exit 0, 737 test superati in 51 file,
log /tmp/sister-watchdog-full.log. I due runtime modificati restano al 100%
anche nel report combinato /tmp/sister-watchdog-full-coverage.json.
Coverage globale worker 99,8562%: cinque statement legacy non coperti in
sister_credential_pool.py e sister_retry_metadata.py, non modificati qui.
La variante PostgreSQL della migrazione storica e saltata senza
GAIA_TEST_POSTGRES_URL; nessuno schema o codice DB cambia in questa fix.

make lint-backend contro HEAD superato, log /tmp/sister-watchdog-lint.log;
git diff --check e ruff format --check sui due file nuovi superati.
Build Dockerfile ufficiale locale superata, /tmp/sister-watchdog-build.log;
20 test watchdog nell'immagine, import runner e pip check superati senza rete,
/tmp/sister-watchdog-smoke.log. Nessun type-check statico worker configurato;
frontend/API non coinvolti. Nessun test di crash o riavvio sul CED effettuato.
Graphify codice aggiornato dal target modulo e docs dal target dominio:
/tmp/sister-watchdog-graph-code.log e /tmp/sister-watchdog-graph-docs.log;
estrazione semantica chunk 1/1 completata senza risultati parziali.

## Residui e limiti

- La slice protegge heartbeat fermo e shutdown sospeso, non il crash PostGIS.
- Un singolo task sospeso con event loop e heartbeat ancora regolari non viene
  rilevato: servirebbero deadline operative e cleanup specifici, separatamente.
- Un blocco nativo che trattiene il GIL puo impedire anche il thread: serve
  supervisione esterna per quel failure path; non dichiarato risolto.
- La policy Docker deve restare unless-stopped; il riavvio puo ripetersi se la
  dipendenza resta indisponibile. Non introdotte retry transazionali arbitrarie.
- Il worker resta nella struttura runtime esistente modules/elaborazioni/worker;
  nessuna modifica frontend, API, schema o architettura parallela.
- Il deploy autorizzato e stato annullato: occorre una decisione sul trattamento
  dei sync AdE prima di proseguire.

## Tentativo di rilascio e rollback del 2026-10-06

Immagine candidata gaia-elaborazioni-worker-visure:sister-63291539 costruita
dall'immagine CED attiva sostituendo soltanto runner e watchdog. I 20 test
watchdog nell'immagine candidata e pip check sono superati; nessuna richiesta
visura risultava processing/queued_sister/waiting_captcha al preflight.
Il vecchio worker bloccato ha richiesto arresto forzato dopo 60 secondi (137).
Il nuovo container e partito alle 17:03:52 Europe/Rome, inizialmente healthy;
ambiente, volumi e altri container verificati invariati.

Durante la verifica live il worker ha prelevato il sync AdE
7fe00f00-5d13-449c-959b-0bf64282d5b4 e ha continuato chiamate WFS con HTTP 200,
ma il heartbeat non avanzava. _process_ade_sync_run in worker.py esegue
execute_ade_sync_run direttamente nel loop async con SessionLocal sincrona.
Un sync lungo blocca quindi il loop pur continuando lavoro utile: il watchdog
lo avrebbe interrotto erroneamente dopo 120 secondi. Questo scenario non era
coperto dalla prima matrice; i test di loop sano non simulavano un sync reale.

Rollback applicato alle 17:05:07 prima della scadenza watchdog, dopo arresto
con finestra di 10 secondi. Ripristinati runner e immagine precedente
sha256:828866450855c3402a244d212246ebbd7b4faf26efc1759687e41f63bf8e7dbf;
watchdog rimosso dalla copia delle sorgenti CED. Il worker precedente e tornato
healthy e ha ripreso il sync, ma il problema originario resta irrisolto.
Non si dichiara il rollout riuscito o la produzione protetta dalla fix.

Evidenze remote riservate in /opt/gaia/releases/sister-20261006-63291539/:
build.log, predeploy-tests.log, deploy.log, rollback-applied.txt e manifest.
Il rollback puo interrompere una transazione del sync: nessun dato corretto
o run rischedulato manualmente; lo stato finale del sync va verificato.

Prima di un nuovo rilascio occorre eseguire il sync fuori dal loop async con
sessione creata/chiusa nello stesso thread, oppure separarne la famiglia dal
worker visure usando il layout runtime esistente. Preservare transazioni,
claim e shutdown: non passare sessioni ORM tra thread, non aumentare il
timeout per mascherare il blocco. Servono test di heartbeat durante sync lento
e failure/cancellazione reali. Questa estensione richiede una decisione prima
di modificare il percorso di esecuzione AdE.
