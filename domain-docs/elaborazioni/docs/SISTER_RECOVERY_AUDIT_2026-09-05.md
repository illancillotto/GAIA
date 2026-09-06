# Audit recupero visure SISTER - 2026-09-05

## Ambiente ed evidenze

Target verificato tramite SSH `serverCed`: `192.168.1.110`.
Il computer di sviluppo e `192.168.1.83`: il precedente audit Docker/SQL
locale non descriveva il CED e le sue conclusioni operative sono ritirate.
Le query seguenti sono fotografie di un sistema attivo, non contatori stabili.

- Worker visure CED attivo e healthy; nessun fermo globale dimostrato.
- 282 documenti creati nelle ultime 24 ore alla rilevazione; ultimo download
  osservato alle 15:40 UTC (17:40 Europe/Rome).
- 481 richieste `failed/retry_exhausted`: 363 con stato remoto `pending`,
  118 senza stato remoto; tutte con `artifact_dir` valorizzato.
- 478 item AutoSync con quel messaggio nella successiva rilevazione, tutti
  con `linked_request_id`. Richieste e item non sono contatori equivalenti.
- Errori telemetrici 24h: 307 polling, 23 apertura form, 9 login.
  I 338 eventi HTTP error includono risposte che il worker puo classificare
  non bloccanti: non equivalgono a 338 visure fallite.
- Caso `6362f116-22d7-43ae-8fc2-7626a42c4868`: screenshot e HTML
  `final-queued_sister` presenti e risolti dal backend per la preview.
- Caso `7d0825a3-eb45-4d84-a376-4175bd308dd1`: directory artifact vuota,
  stato remoto assente, retry esauriti.

Nessun login SISTER aggiuntivo, invio, cancellazione, retry, modifica DB,
riavvio o deploy eseguito durante questo audit.

## Flusso e difetti

1. Lo scheduler collega item, batch e richiesta. Il worker seleziona la
   credenziale, rispetta calendario/lease e acquisisce la richiesta con token.
2. Il claim incrementa `attempts`, anche per riprendere un documento remoto.
   Per `perpetual_sync` il limite e tre. Il controllo precede l'esecuzione.
3. Login, compilazione e CAPTCHA possono produrre un PDF immediato oppure
   una richiesta asincrona. ID, URL, stato e credenziale remoti sono persistiti.
4. Il polling iniziale ridotto restituisce `queued_sister`. La persistenza
   rimette subito in pending senza `retry_not_before`; il successivo claim
   consuma un altro tentativo. La ripresa usa dieci poll e il relativo timeout
   passa alla gestione errori/sessione recuperabili.
5. Il polling legge ConsultazioneRichieste e tenta di cambiare categoria.
   Il portale osservato usa radio `radioCount` e submit `metodo=Aggiorna`.
   Il vecchio codice clicca una cella testuale: non applica il filtro.
   L'HTML campione mostra espletate=0, non evadibili=246, da trattare=0,
   prelevate=436. Questi numeri non dimostrano in quale categoria sia il
   singolo ID, ma dimostrano che attendere sulla sola categoria vuota non basta.
6. Gli errori recuperabili sono rinviati senza lo snapshot effettuato invece
   sui terminali. `reset_for_retry` registra un codice generico;
   `_mark_retry_exhausted` sostituisce messaggio e codice con il limite.
   Si perde la causa utile all'operatore, anche quando la directory esiste.
7. `_queue_request` rimette in coda senza azzerare `attempts`: un rilancio di
   una richiesta gia esaurita puo essere subito respinto dal claim.
8. La correlazione con ID remoto persistito rifiuta righe di altri ID.
   Senza ID e senza baseline, una sola riga visibile viene invece accettata;
   con piu righe, il matching testuale ignora alcuni token brevi. Questo e un
   rischio da caratterizzare separatamente prima di recuperi massivi.

## Correzione locale verificata

`sister_requests_navigation.select_requests_category` applica la categoria
tramite il valore esatto del radio, seleziona Intero periodo quando presente
e invia Aggiorna prima di rileggere le righe. Conserva il fallback per i
layout legacy e propaga un submit fallito. La correlazione resta nel browser
session; il nuovo adapter non sceglie documenti e non cambia ID o credenziale.

Test reali Chrome su HTML sintetico rappresentativo riproducono il mancato
submit del vecchio click e verificano categoria, periodo e submit del nuovo.
Non sostituiscono una verifica del comportamento su SISTER dopo il deploy.

## Artifact e UI

Il bundle frontend CED contiene il componente artifact. I sorgenti non sono
copiati nel container standalone: la loro assenza non prova un deploy vecchio.
La lista AutoSync espone Dettagli; Scarica artifact e Preview screenshot sono
nel dialogo, condizionati da `artifact_dir`. Il caso campione e risolvibile
dal backend. Non e stata verificata una sessione browser autenticata dell'utente:
restano da osservare apertura del dialogo, risposta HTTP e eventuale cache UI.

La directory vuota restituisce uno ZIP vuoto e nessuna preview; una directory
assente produce invece lo ZIP diagnostico missing. La UI dovrebbe distinguere
artifact presenti, directory vuota e artifact scaduti con capacita esplicite
dell'API, anziche inferire la disponibilita dal solo percorso.

## Recupero proposto

Prima di riaprire le 481 richieste:

1. Pubblicare e verificare il filtro con un caso remoto identificato, mantenendo
   l'affinita della credenziale. Non cancellare o risottomettere richieste solo
   perche non compaiono nella categoria corrente.
2. Separare budget invii, riprese/polling e deadline remota persistita. Un timeout
   di produzione documento non deve essere classificato come sessione bloccata
   ne provocare automaticamente un nuovo invio. La deadline e una decisione
   operativa approvata dall'utente: 24 ore dal primo invio remoto, poi
   revisione manuale; evitare polling illimitato. Il timestamp deve essere
   persistito e non ripartire a ogni claim, riavvio, cambio giorno o retry.
3. Conservare ultimo errore, codice, timestamp e artifact per ogni tentativo,
   prima di rilasciare il token; mostrare il limite come motivo terminale
   aggiuntivo, senza sovrascrivere la causa.
4. Preparare un manifest read-only con richiesta, batch, stato, ID remoto,
   credenziale, eventuale documento locale e ultimo errore. Ricontrollare
   stato/token al momento dell'applicazione per evitare gare col worker attivo.
5. Per gli ID remoti gia inviati recuperare prima il risultato originale.
   Per i casi senza ID servono evidenze di mancato invio; l'assenza dell'ID
   locale da sola non autorizza un nuovo submit.
6. Rendere la ripresa esplicita e testata: nuovo ciclo con budget chiaro,
   storico preservato, nessuna cancellazione dei documenti validi.

L'aggiornamento del runtime Python e un intervento separato: il CED usa 3.10,
mentre diversi servizi backend locali usano `datetime.UTC` (3.11+). Non e la
causa del polling osservato sul CED, ma impone una prova bootstrap prima di
pubblicare nuovi moduli backend nel worker.

## Validazione della correzione

- 105 test passati: suite browser session, coverage correlazione/form/lifecycle,
  nuovi test unitari e due scenari HTML su Chrome reale.
- Coverage file runtime toccati: 915/915 statement, 274/274 branch (100%).
- Ruff check e format dei file nuovi: pass.
- `_find_correlated_row_in_tab`: cyc 4 -> 2, cog 4 -> 1, LOC 8 -> 4.
  Nuovo adapter: cyc 6, cog 9, LOC 17, sotto soglia; 22 violation totali
  sul perimetro prima/dopo, nessuna nuova violation.
- Ratchet contro `origin/main` (merge-base `6d6278cb`) non verde: cinque
  regressioni gia presenti prima della patch (form, prepare download, firma
  polling e LOC file). Baseline non aggiornata per assorbirle.
- Graphify: aggiunti target dedicati worker e documentazione Elaborazioni,
  con relative query; `make graphify-elaborazioni-worker-code` completato:
  1498 nodi, 3545 archi, 76 community. Nessuna estrazione dalla root GAIA.
  Il target docs usa gpt-5.4-mini, concorrenza 1 e timeout limitati.

La correzione locale non costituisce un recupero completato dei dati sul CED.

## Decisione: 24 ore e ricerca nell'arretrato

L'utente ha approvato 24 ore e richiesto esplicitamente di considerare
l'accumulo nell'elenco SISTER. La policy e ora implementata localmente nel
claim/retry (vedi aggiornamento sotto), non ancora distribuita. Il solo filtro Intero periodo non garantisce
una ricerca completa.

L'HTML reale contiene l'avviso: per vedere le altre richieste bisogna
aprire, salvare o eliminare quelle attualmente visualizzate e aggiornare.
Le ultime 400 snapshot di polling ispezionate non contengono un elenco
espletate con link CheckRichiesta: non sono una prova della disponibilita
di paginazione o ricerca per ID. Non inventare endpoint o selettori Avanti.

Contratto richiesto per il recupero:

- Cercare l'ID remoto esatto usando la credenziale e la convenzione originali.
- Esplorare le categorie pertinenti (espletate, non evadibili, da trattare;
  considerare anche prelevate per interruzioni tra download e persistenza).
- Usare i giorni dell'intervallo di recupero, in Europe/Rome, per restringere
  gli elenchi; mantenere la deadline in UTC. Intero periodo resta un fallback,
  non la prova che tutte le righe siano state visitate.
- Seguire soltanto controlli reali di pagina/filtro. Rilevare pagine ripetute,
  nessun avanzamento e limiti di visualizzazione. Un elenco incompleto deve
  essere segnalato come tale, non come documento assente o ancora in produzione.
- Se il portale richiede di consumare le righe visibili, recuperare soltanto
  richieste GAIA con corrispondenza canonica certa. Non aprire, scaricare o
  eliminare pratiche estranee per liberare l'elenco.
- Pianificare il polling equamente tra richieste e credenziali, con attese
  persistite, affinche l'arretrato non monopolizzi il worker.
- Alla scadenza conservare ID remoto, credenziale, cronologia di ricerca,
  ultimo errore e screenshot; richiedere revisione senza nuovo invio automatico.

Test necessari oltre alla correzione radio gia verificata: ID fuori dalla
prima pagina, cambio giorno, molte richieste nello stesso giorno, ID nelle
prelevate, elenco troncato senza paginazione, nessun avanzamento, riavvio del
worker e deadline non prorogata, isolamento di richieste di altri utenti.

## Aggiornamento implementazione locale

- Migration additiva `20260905_1100`: `sister_first_submitted_at` nullable,
  senza backfill inventato. Primo riscontro remoto persistito, mai rinnovato
  da polling, restart o callback successivi. Le righe storiche gia remote con
  data sconosciuta richiedono revisione; non distribuire senza classificare
  preventivamente l'arretrato attivo.
- Claim remoto separato dal contatore dei tentativi di esecuzione iniziale:
  il recupero non incrementa `attempts`, verifica le 24 ore anche in
  `prepare_execution`, conserva ID e credenziale alla scadenza e termina con
  `sister_recovery_review_required`. URL assente impedisce un nuovo invio.
- Resume con un solo poll; `queued_sister` riprogrammato dopo cinque minuti
  nel database. Rimosso il reinvio immediato automatico alla risposta
  DocumentoNotYetProduced. Gli errori di correlazione/PDF non cancellano piu
  identita remota e baseline.
- Ricerca Non evadibili, Espletate e Prelevate anche quando il contatore del giorno corrente
  e zero. Dopo Intero periodo si percorrono i giorni effettivamente esposti
  dal form, senza ripetere le date duplicate. Nessun endpoint di paginazione
  inventato. Se non trova la richiesta, warning esplicito di elenco
  potenzialmente limitato; nessuna cancellazione di richieste estranee.
- Errori di server e recuperabili catturati prima del defer/restart:
  query con token/stato e lock di riga, causa originale persistita, error.txt
  e snapshot best effort con timeout di dieci secondi. Un token scaduto non
  scrive diagnostica. Esaurimento budget conserva la precedente causa.
- Migrazione upgrade/downgrade provata su SQLite con una riga preesistente:
  il timestamp resta NULL. Migrazione PostgreSQL e rollout non eseguiti.
- Suite browser/flow: 158 test passati, statement e branch 100% su
  browser_session, visura_flow, sister_requests_navigation; include Chrome
  reale con richiesta reperibile solo filtrando il giorno precedente.

Limiti ancora aperti prima del rilascio:

1. Lo storico senza timestamp richiede un manifest verificato contro log e
   dati remoti; non azzerare in massa i tentativi e non rimettere tutte le
   righe in pending. Nessuna modifica al DB CED eseguita.
2. L'elenco troncato all'interno dello stesso giorno non e dimostrabilmente
   percorribile senza altre evidenze dal portale. Il warning non equivale a
   una ricerca completa. Richiesta all'utente una schermata completa degli
   elenchi con molte richieste nello stesso giorno e relativi controlli.
3. Il retry manuale backend e stato completato localmente (aggiornamento
   2026-09-06 sotto). Il matching nell'elenco senza
   ID remoto e stato bloccato nel successivo controllo descritto sotto:
   la patch non autorizza recuperi automatici ambigui.
4. I pulsanti frontend restano nel dialog Dettagli. La patch crea gli
   artifact mancanti per i prossimi errori, non ricrea screenshot storici.

Checkpoint operativo: modifiche soltanto locali; ultimo controllo read-only
del worker CED alle 16:22 UTC del 2026-09-05 conferma ancora resume 1/10 e
intervallo 30 secondi del codice precedente. Non dichiarare recuperate le
richieste sulla base dei soli test locali.

### Verifiche finali della sessione

- 203 test worker/repository/recovery/diagnostica passati; copertura statement
  e branch 100% per `worker.py`, `sister_worker_reliability.py`,
  `sister_recovery_policy.py`, `sister_request_diagnostics.py` e modello
  `backend/app/models/catasto.py`. Il report includeva anche modelli non
  modificati non coperti, da non confondere con il perimetro della change.
- 158 test browser/flow e 1 test migration passati: totale 362.
- Ruff check su tutti i runtime toccati e migration: pass; format dei runtime
  nuovi: pass; `git diff --check` sul perimetro: pass.
- Ratchet autorevole `complexity.py ratchet --base-ref origin/main ...`:
  otto finding contro merge-base `6d6278cb`, cinque browser e tre flow gia
  presenti nella cattura prima (`/tmp/sister-recovery-before.json`). Non
  dichiarare il gate verde; baseline non aggiornata.
- Metriche LOC prima/dopo: browser 1241 -> 1236, flow 475 -> 443,
  reliability 796 -> 795, worker 1464 -> 1474. L'incremento worker comprende
  il riordino import Ruff; resta da chiudere il ratchet locale del debito
  prima del rilascio. Non classificare questa change come hotspot IMPROVED.
- Graphify backend aggiornato (8654 nodi / 21944 archi; HTML omesso per
  dimensione); worker aggiornato e pruning forzato dopo rimozione reinvio;
  docs 93 nodi / 99 archi, 3654 token input / 1292 output, costo stimato
  $0.0035. Output grafi non versionati.
- Evidenze temporanee: `/tmp/sister-recovery-tests.log`,
  `/tmp/sister-browser-tests.log`, `/tmp/sister-recovery-ratchet.log`,
  `/tmp/sister-recovery-before.json`, `/tmp/sister-recovery-after.json`.

Prossima unita: chiudere matching fail-closed senza ID e manifest storico,
verificare navigazione same-day su HTML reale, completare retry manuale e
ratchet; quindi rollout selettivo con migration prima di backend/worker,
smoke test Python 3.10 e recupero canary con verifica del PDF. Non copiare
l'intero working tree sul CED: contiene modifiche estranee a questo incidente.

## Controllo elenchi dopo le schermate utente

Evidenza: `richieste_sister_1.jpg` e `richieste_sister_2.jpg`, fornite
localmente dall'utente (non versionate: contengono dati del portale).
Intero periodo mostra cinque espletate del 31 agosto / 1 settembre; il
5 settembre non mostra righe ma mantiene il contatore cinque. Le categorie
Prelevate e Non evadibili riportano rispettivamente 669 e 293. Nessun
controllo di paginazione dimostrato da queste due schermate.

Implementazione del controllo:

- I contatori non limitano le categorie visitate: Non evadibili, Espletate,
  Prelevate; Intero periodo e poi tutti i giorni realmente esposti, deduplicati.
- Dopo Aggiorna si verifica che SISTER abbia mantenuto il radio della
  categoria richiesta e il giorno selezionato. Se non corrispondono,
  `SisterRequestCorrelationError`, senza consumare le righe di un filtro
  diverso. Nessuna navigazione o paginazione basata su endpoint inventati.
- Il recupero da elenco richiede un ID remoto certo PRIMA di estrarre le
  righe. Nessun fallback sulla sola riga visibile o su descrizioni simili;
  l'assenza di ID non dimostra che l'invio precedente non sia avvenuto.
- Log delle coppie categoria/giorno visitate. Categoria non accessibile e
  ricerca senza risultato producono avvisi espliciti di ricerca incompleta
  o elenco potenzialmente limitato. Un contatore globale positivo non
  contraddice un giorno vuoto e non autorizza un nuovo invio.
- Nessuna apertura/download/eliminazione di righe estranee per sbloccare
  l'elenco. Un arretrato troncato nello stesso giorno resta un limite noto,
  non una ricerca completata con certezza.

Verifiche: 163 test browser/flow passati; statement e branch al 100% su
browser_session, sister_requests_navigation e visura_flow. Fixture Chrome
con quaranta righe estranee, contatori invariati, giorno corrente vuoto e
target reperibile solo nelle prelevate del giorno precedente; variante con
target nascosto verifica nessun download e nessuna navigazione estranea.
Test aggiuntivi: filtri non applicati e correlazione senza ID rifiutati.
Ruff e diff check passati. Report in `/tmp/sister-list-control-tests.log`.

Metriche controllo elenchi prima/dopo: browser LOC 1236 -> 1236;
adapter LOC 53 -> 65; violation complessive 22 -> 22 (errori 2 -> 2).
Ratchet contro merge-base `6d6278cb`: restano i cinque finding browser gia
documentati, nessuno aggiunto dal controllo elenchi. Baseline non modificata.
Evidenze `/tmp/sister-list-control-{before,after}.json` e
`/tmp/sister-list-control-ratchet.json`.

Stato: implementazione e verifica locali. Nessun deploy, migrazione o
recupero massivo sul CED eseguiti in questa sessione.

## Retry manuale e preflight CED (2026-09-06)

Completato localmente il retry manuale con preflight atomico: si bloccano
prima il batch e poi le richieste, mantenendo il controllo di ownership
preesistente. Si validano tutte le righe fallite prima di modificarne una.
Un caso non sicuro restituisce il consueto HTTP 409, indicando la riga e il
motivo; le altre richieste restano invariate, anche se il chiamante commette
successivamente la transazione.

- Recupero remoto ammesso solo con stato attivo, primo invio noto e non
  futuro, meno di 24 ore trascorse, ID remoto, URL e credenziale presenti.
  Non si modificano tentativi, identita remota, data iniziale o artifact.
- Errore e codice originali restano visibili durante il retry manuale.
  Il successo successivo segue il normale percorso di persistenza.
- Token ancora presente o documento gia associato bloccano il retry.
- Una riga senza stato remoto ma con tentativi o altri indizi di invio non
  viene reinviata: l'assenza dell'ID non e prova di mancato inoltro.
  Solo le righe mai tentate e senza indizi remoti possono iniziare da zero.
- Non si azzera il contatore per aggirare `retry_exhausted`, non si rinnova
  la finestra e non si usa `created_at` al posto del primo invio.
- La logica di coda/preflight e nel dominio Elaborazioni, separata dai
  servizi di upload. Contratto delle 24 ore condiviso tra API e worker in
  `sister_recovery_contract.py`, importabile anche da Python 3.10.

Verifiche:

- 132 test backend/API/integration passati; 100% statement e branch su
  `elaborazioni_batches.py`, `sister_manual_retry.py` e
  `sister_recovery_contract.py`. Include date naive/aware, limite esatto,
  data futura, assenza di ID/credenziale, documento/token presenti, budget
  esaurito, mancata modifica parziale e conservazione dell'errore.
- 203 test worker passati; 100% sui runtime worker/reliability/policy e
  diagnostics misurati. La suite browser/flow resta quella dei 163 test
  del precedente controllo elenchi, non rieseguita in questa unita.
- Ruff e format nuovi runtime: pass. Metriche servizio batch LOC
  850 -> 833, cyc aggregata 257 -> 253, cog 318 -> 314; non e un hotspot
  dedicato e l'estrazione e organizzativa, non una dichiarazione IMPROVED.
- Ratchet contro `origin/main`: sette finding preesistenti relativi a
  validazione/upload/creazione batch. Nessun finding su retry manuale o
  sui nuovi moduli. Baseline non aggiornata per assorbire debito.
- Import smoke Python 3.10.12 nel container CED: tutti gli undici moduli
  runtime della patch, inclusi worker e reliability, importati con successo
  tramite overlay esclusivamente in memoria. Nessuna estrazione di file,
  avvio del loop, migration, restart o deploy.

Inventario CED read-only: 549 righe `retry_exhausted`, 421 con stato remoto
pending e 128 senza stato. 418 hanno contemporaneamente ID, URL e
credenziale. CSV locale `/tmp/sister-recovery-review-2026-09-06.csv`, 549
record, nessun dato personale incluso intenzionalmente oltre agli ID
tecnici e percorsi artifact. Tutte classificate
`FIRST_SUBMISSION_NOT_VERIFIED`; e un inventario per revisione, non un
manifest che autorizza UPDATE o nuovi invii. Numeri soggetti all'attivita
del worker di produzione.

La telemetria `submit/captcha_submit/success` non basta per il backfill:
il wrapper registra successo quando il metodo ritorna senza eccezione,
anche se il CAPTCHA e rifiutato. Non ricavare da questi eventi una data
certificata di accettazione SISTER.

Checkpoint: codice locale del retry manuale completato; prima del rollout
restano applicazione della migration sul CED, verifica del trattamento delle
righe storiche con data sconosciuta e canary sul CED. Non affermare che le 549
richieste siano state recuperate. Evidenze in
`/tmp/sister-manual-retry-tests.log`, `/tmp/sister-manual-backend.coverage`,
`/tmp/sister-recovery-worker-check.log`, `/tmp/sister-python310-smoke.log`,
`/tmp/sister-manual-retry-{before,after}.json` e
`/tmp/sister-manual-retry-ratchet.json`.

Ulteriore verifica PostgreSQL: container locale usa-e-getta PostgreSQL 16,
porta loopback assegnata da Docker, nessun volume persistente. Due test
migration (SQLite e PostgreSQL) passati: upgrade mantiene NULL per una riga
storica, tipo PostgreSQL timezone-aware, downgrade conserva la riga.
Un test aggiuntivo in schema isolato PostgreSQL verifica il lock del batch:
il secondo chiamante attende il proprietario, riceve lock timeout senza
modificare richieste, e dopo il rilascio ricontrolla lo stato PROCESSING e
restituisce conflitto. Schema eliminato nel finally e container locale
fermato/rimosso al termine. Nessuna DDL eseguita sul CED.

Comandi riproducibili con `GAIA_TEST_POSTGRES_URL` su un database di test:

```sh
backend/.venv/bin/python -m pytest modules/elaborazioni/worker/tests/test_sister_recovery_migration.py -q
backend/.venv/bin/python -m pytest backend/tests/test_sister_manual_retry_postgres.py -q
```

Graphify aggiornato per backend e worker con pruning forzato; documentazione
Elaborazioni aggiornata con il target dedicato. Grafi non versionati.

## 2026-09-06: bypass AutoSync del contratto di recupero

Riproduzione locale confermata: una richiesta FAILED con stato remoto pending,
un tentativo, primo invio 25 ore prima e codice
`sister_recovery_review_required` veniva riclassificata pending dal planner,
con retry dopo 6 ore. La creazione del batch successivo sostituiva il link con
una nuova richiesta. Il retry manuale di campagna azzerava inoltre tentativi e
collegamenti. Nessun dato di produzione modificato durante la riproduzione.

Correzione nel dominio `sister_autosync_guard.py` e nei due planner:

- Una richiesta fallita con tentativi, indizi remoti, documento, token di
  esecuzione o codice review non puo essere sostituita da AutoSync. Il limite
  di 24 ore rimane sulla richiesta originale; non viene rinnovato dal planner.
- Il controllo viene ripetuto al confine di creazione del batch, anche per
  elementi gia pending lasciati da versioni precedenti. Richieste mancanti ma
  ancora referenziate e richieste attive vengono bloccate, non duplicate.
- Il retry manuale di campagna esegue il preflight completo sotto lock degli
  elementi e delle richieste, rileggendo lo stato dal database. Un conflitto
  restituisce HTTP 409 senza rimettere in coda alcun elemento. Nessun reset
  dei tentativi o scollegamento della richiesta originale.
- Il recupero manuale sicuro entro 24 ore resta disponibile sul batch
  originale tramite il contratto `sister_manual_retry`, non tramite la
  ricreazione indiscriminata degli elementi della campagna.
- Il planner legacy non classifica piu come transitorio un errore con indizi
  di invio; la bonifica dei batch mai partiti esclude richieste gia tentate,
  remote o in esecuzione. Le richieste saltate dall'operatore restano skipped;
  un rilascio non autorizza invece a perdere indizi remoti e reinviare.
- I casi bloccati non impediscono al planner di lavorare sugli altri target.
  Nessun backfill inventato delle date storiche.

Verifiche della slice:

- Suite completa ripetuta da zero: 120 test passati, coverage statement e
  branch 100% sui quattro file runtime della correzione AutoSync (796
  statement, 252 branch). Evidenze in `/tmp/sister-autosync-clean.coverage`
  e `/tmp/sister-autosync-clean-tests.log`; regressioni mirate anche in
  `/tmp/sister-autosync-regression-tests.log`.
- Cinque test passati su PostgreSQL 16 usa-e-getta e SQLite: lock del batch,
  lock dell'elemento di campagna, lock della richiesta, rilettura dopo attesa,
  upgrade/downgrade della migration. Schemi eliminati e container fermato e
  rimosso; nessuna DDL sul CED. Log `/tmp/sister-autosync-postgres-tests.log`.
- Ruff e `git diff --check` passati. Ratchet autorevole contro il merge-base
  di origin/main passato sui quattro file della slice, findings vuoti in
  `/tmp/sister-autosync-ratchet.json`. Baseline non modificata.
- Metriche prima/dopo in `/tmp/sister-autosync-{before,after}.json`:
  `_retry_item` ciclomatica 6 -> 7, cognitiva 6 -> 7, sotto soglia;
  bonifica legacy ciclomatica 10 -> 10, cognitiva 19 -> 19, LOC 69 -> 63;
  riconciliazione legacy 15/27 -> 15/27. Nessuna riduzione di complessita
  rivendicata per l'estrazione della query di bonifica.
- Graphify backend aggiornato: 8695 nodi, 22028 archi. Output non versionato.

Comando di verifica completa della slice (log finale separato):

```sh
PYTHONPATH=backend COVERAGE_FILE=/tmp/sister-autosync-clean.coverage \
  backend/.venv/bin/python -m pytest \
  backend/tests/test_elaborazioni_api.py \
  backend/tests/test_sister_autosync_guard.py \
  backend/tests/test_elaborazioni_ruolo_autosync_lock.py \
  -q --disable-warnings \
  --cov=app.services.elaborazioni_perpetual_sync \
  --cov=app.services.elaborazioni_ruolo_autosync \
  --cov=app.modules.elaborazioni.autosync_campaign_routes \
  --cov=app.modules.elaborazioni.sister_autosync_guard \
  --cov-branch --cov-report=term-missing --cov-fail-under=100
```

Stato rollout: correzione locale, non ancora committata o deployata. Il CED ha
modifiche estranee e una versione delle route precedente alla modularizzazione
locale: il rilascio selettivo deve includere il mapping della route HTTP 409,
senza sovrascrivere codice estraneo. La verifica del download di nuovi PDF
dopo il deploy e ancora da eseguire; le evidenze precedenti di produzione non
dimostrano il funzionamento della versione corretta.
