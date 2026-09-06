# Debug arresto download SISTER - 6 settembre 2026

## Perimetro ed evidenze

Indagine read-only sul CED `192.168.1.110`, dopo il rilascio UI/scheduler
`ui-f5ef8428`. Nessun riavvio, deploy, invio SISTER, login aggiuntivo,
cancellazione o modifica DB eseguito durante questa indagine. Snapshot e
log contengono dati personali: conservati solo in directory temporanee locali,
non allegati al repository.

Fotografia alle 10:20:09 UTC (12:20:09 Europe/Rome):

- Ultimo PDF: 09:39:49 UTC, quindi lo stallo precede il deploy UI delle10:00:46.
- Worker attivo e healthy, stesso container avviato alle09:30:35 UTC.
- AutoSync esegue cicli; osservati completamenti alle10:15:53 e10:16:53.
  Il ciclo delle10:17:49 impiega106 secondi; il tick successivo risulta perso
  per46 secondi. Il ritardo esiste, ma non e un arresto dello scheduler.
- Batch `600d450c-322e-4a6f-adc3-360e1b8e9eb2`, perpetual_sync, avviato
  alle09:37:46: 20 richieste, 6 completed, 8 failed/retry_exhausted,
  1 failed per submit non avanzato, 5 con ID remoto in recupero
  (4 pending e1 processing al momento della query).
- Le cinque richieste remote sono state inviate fra09:38:41 e09:41:18;
  restano entro la deadline di24 ore. Non devono essere risottomesse.
- Backlog ruolo_particella: 83090 pending e8 queued; gli altri scope hanno
  ulteriori item pending. Non tutti questi item sono necessariamente eseguibili
  immediatamente: configurazioni, scadenze e credenziali restano vincolanti.

## Difetti dimostrati

### Navigazione dopo il polling

`browser_session.py:135` chiama `_goto_visura_menu_with_retry` quando la pagina
non e riconosciuta come area visure. `browser_session.py:974` presume pero di
essere nella home del portale e clicca `Consultazioni e Certificazioni`.
Il polling ha navigato la stessa pagina su ConsultazioneRichieste, una vista
priva di quel link e del normale menu applicativo.

Per la richiesta `2bac6b20-e26f-4458-a9df-266cc080d247`, `error.txt` e
`final-failed.html/png` alle09:58:47 concordano: pagina Richieste, categoria
Prelevate, giorno31/08/2026, timeout60 secondi cercando il link della home.
Non e un errore password ne una prova di sessione scaduta.

La richiesta successiva consuma tentativi per un errore di navigazione locale;
il database conserva ora correttamente la causa dietro `retry_exhausted`.
Otto richieste del batch sono finite in questo stato senza ID remoto.

Riproduzione su Chrome reale con HTML salvato, JavaScript disabilitato e ogni
richiesta di rete abortita: area non pronta, link assente, stesso TimeoutError
con timeout ridotto a100 ms. Il parser estrae inoltre oltre100 ID dalle righe
della pagina salvata: non e una prova che trovi le cinque richieste cercate.

### ID remoto non applicato alla correlazione in memoria

`sister_browser_reliability.py:50`, `mark_submitted`, ritorna subito se manca
il callback di submission, prima di aggiornare `state.correlation`.
Il callback viene armato nel percorso CAPTCHA; il percorso che rileva un
documento non ancora prodotto durante la preparazione puo non averlo armato.
Anche una prima notifica senza ID consuma il callback, impedendo di arricchire
la correlazione con un ID arrivato successivamente.

La richiesta `6441ee4e-31fb-4c83-807f-760bdfeb97a4` mostra alle09:40:04:
`DocumentNotYetProducedError` seguito da
`SisterRequestCorrelationError: Correlazione SISTER non inizializzata con ID remoto certo`.
Il DB contiene l'ID remoto perche il callback del flow lo persiste separatamente.
La ripresa successiva lo ricostruisce dal DB, ma il primo ciclo e sprecato.

Due riproduzioni deterministiche confermano che l'ID resta None sia senza
callback sia dopo una prima notifica con ID None. Questo difetto da solo non
spiega la mancata disponibilita durante tutte le riprese successive.

### Attesa remota blocca l'avvio dei batch successivi

`backend/app/services/elaborazioni_perpetual_sync.py:476` considera attivo
qualsiasi batch perpetual_sync pending o processing.
`ensure_perpetual_sync_batch`, riga524, ritorna senza pianificare se ne esiste
uno. Non distingue lavoro subito eseguibile da richieste gia inviate e in
attesa remota con `retry_not_before`.

Le cinque richieste tengono aperto il batch anche quando tutte sono rinviate.
La deadline di24 ore evita gli esaurimenti dei vecchi poll, ma con questa
serializzazione puo anche fermare i nuovi batch fino alla chiusura del recupero.
Non basta aumentare tentativi o riavviare AutoSync.

## Limite del recupero gia inviato

Log delle10:14-10:15: ricerca effettiva in Non evadibili, Espletate e Prelevate,
Intero periodo e giorni esposti dal06/09 al31/08. I log terminano con
`richiesta non trovata` e nessun download. Lo snapshot finale del caso6441ee4e
mostra Prelevate al31/08 senza risultati; il precedente snapshot Espletate
al06/09 mostra contatore1 ma nessuna riga per il filtro selezionato.

I contatori globali non dimostrano la disponibilita di uno specifico ID.
Mancano snapshot intermedi per categoria/giorno e un riepilogo degli ID estratti.
Non e dimostrato se i cinque documenti siano ancora non prodotti, nascosti
dal limite del portale o esclusi da un ulteriore problema di lettura/correlazione.
Non autorizzare download estranei o cancellazioni per rendere visibili altri ID.

Nel campione40 minuti: 21 errori apertura form e29 eventi polling classificati
error. Questi ultimi includono l'eccezione attesa di documento non pronto:
non equivalgono a29 errori HTTP. Le30 risposte501 su initPortale sono seguite
da login riusciti; non sono una spiegazione sufficiente dello stallo.

## Correzione raccomandata

1. Ripristinare una pagina di ingresso autenticata verificata dopo il polling,
   prima del form successivo, mantenendo credenziale e convenzione originali.
   Non inventare URL e non aprire sessioni parallele sulla stessa credenziale.
2. Aggiornare la correlazione con l'ID remoto indipendentemente dal callback
   one-shot; gestire la notifica iniziale priva di ID senza perdere quella
   successiva. Conservare la persistenza idempotente e il token del claim.
3. Separare la pianificazione di nuovo lavoro dalla coda di recupero remoto,
   con capacita limitata, fairness e lease originali. Non rimuovere semplicemente
   il guard del batch: serve preservare concorrenza, ownership e assenza duplicati.
4. Registrare nel recupero categoria/giorno applicati, numero righe, esito
   matching esatto, ragione di rinvio e snapshot intermedi selettivi. Verificare
   uno dei cinque ID con la sua credenziale, senza nuovo submit.
5. Solo dopo correzione e canary PDF, valutare il rilancio delle otto richieste
   senza ID sulla base dell'evidenza pre-submit; niente reset massivo dell'arretrato.

## Verifiche e limiti

- SHA256 dei quattro moduli browser/correlazione/navigation identici tra
  sorgenti locali e worker attivo: riproduzione riferita al codice distribuito.
- Tre test diagnostici passati in3.92 secondi. Sono riproduzioni del difetto
  corrente, non test che attestano una correzione.
- Script: `/tmp/test_sister_debug_reproduction.py`; comando:
  `backend/.venv/bin/python -m pytest /tmp/test_sister_debug_reproduction.py -q --override-ini addopts=''`.
- Query aggregate e casi: `/tmp/sister-debug-{20260906,batch}.py`;
  log `/tmp/sister-debug-20260906.log`; artifact `/tmp/sister-debug-artifacts`.
- Nessun file runtime modificato, nessuna baseline alterata e nessuna nuova
  attestazione di coverage runtime. Le modifiche estranee del worktree restano
  preservate. Nessun commit/push o nuovo deploy nell'indagine.

## Implementazione successiva autorizzata

Stato: correzioni locali e documentazione aggiornate; nessun nuovo deploy o
recupero massivo effettuato. Le evidenze sopra descrivono il codice precedente.

- Ripristino della home autenticata osservata `/Servizi/` sulla stessa pagina
  quando manca il link del menu; nessuna sessione parallela. Il percorso di
  selezione convenzione resta invariato. Riproduzione Chrome completa:
  Richieste senza menu -> home -> Consultazioni -> area visure -> form pronto.
- `mark_submitted` aggiorna l'ID nella correlazione anche senza callback
  CAPTCHA. Una notifica iniziale priva di ID conserva il callback per quella
  successiva; l'ID noto non puo essere sostituito. Il listener delle risposte
  aggiorna la submission solo se il callback e attivo.
- Diagnostica categoria/giorno per richiesta, con JSON senza testo delle righe
  e snapshot HTML/PNG selettivi. File sovrascritti per filtro; errori diagnostici
  fail-open. Gli artifact conservano i controlli di accesso e la retention.
- Scelta conservativa per il blocco coda: refill dello stesso batch processing,
  non una seconda coda di batch concorrenti. Nuovo modulo
  `backend/app/modules/elaborazioni/sister_autosync_refill.py` per capacita,
  inserimento, mapping riga e link item/richiesta. I due helper esistenti di
  mapping/link restano importabili dal servizio per compatibilita.
- Cap richieste aperte: `min(max(batch_size, 1), 100)`. Si aggiungono solo
  slot liberi e solo se tutte le richieste aperte sono recuperi rinviati,
  non claimed, entro24 ore e con evidenze remote complete. A cap pieno il
  backpressure resta intenzionale. Le righe concluse non occupano slot.
- Lock batch e richieste con SKIP LOCKED; confronto fra conteggio aperte e
  righe effettivamente bloccate per non scambiare una riga claimed per slot
  libero. Lock sugli item e preflight anti-duplicazione gia esistenti;
  nuovi indici dopo il massimo row_index, stesso batch e stessa ownership.
  Non sono alterati ID remoti, credenziali, deadline, documenti o tentativi.
- Nessuna migration o modifica API/frontend richiesta. Il totale del batch
  cresce con il refill: e un limite di lavoro aperto, non un batch immutabile.

### Validazione locale

- Browser/reliability/navigation:145 test,100% statement e branch sui tre
  runtime. Suite aggiuntiva flow/repository/
  recovery:104 test passati.
- Backend:100% statement e branch su servizio perpetual_sync e nuovo modulo
  refill (356 statement e118 branch); verificati anche i vecchi retry sicuri,
  release senza evidenze remote, schedule e lease.
- PostgreSQL effimero locale:3 scenari passati, con lock concorrente sul batch,
  sulla richiesta remota e sull'item. Nessun inserimento finche il lock resta
  acquisito; dopo rilascio una sola aggiunta e nessun batch duplicato.
- Ruff mirato, format-check dei file nuovi e `BASE_REF=HEAD make lint-backend`
  sui10 file Python della change passano. Il lint globale contro
  origin/main resta affetto da debito precedente su file non modificati qui;
  non e stato corretto tramite esclusioni o riformattazioni massive.
- Metriche runtime: servizio principale LOC546 ->541; BrowserSession
  LOC1236 ->1231. I nuovi helper vivono sotto soglia file. Perimetro prima:
  4 file,125 callable,38 finding (3 error); dopo:5 file,134 callable,
  39 finding (3 error). I warning aggiuntivi sono sotto le soglie bloccanti;
  non viene dichiarata una riduzione della complessita aggregata.
- Il ratchet autorevole usa la baseline del merge-base di origin/main.
  Restano finding storici su form/polling/LOC BrowserSession, helper initPortale
  e test browser gia presenti prima della change, oltre a moduli estranei.
  Baseline, scope ed esclusioni non sono stati aggiornati per assorbirli.
- Log: `/tmp/sister-stall-{worker-final-tests,backend-verified-tests,postgres-tests,regression-tests}.log`;
  metriche `/tmp/sister-stall-{before,final}.json`. Graphify backend e worker
  aggiornati tramite target dedicati; docs riallineate dopo la modifica.

### Criteri di rilascio e canary

Distribuire worker e backend/scheduler con overlay selettivo coerente, senza
pull indiscriminato sul checkout CED sporco. Conservare env, mount, comandi,
immagini e configurazioni di rollback. Nessun reset delle richieste gia inviate.
Verificare prima la navigazione della richiesta nuova, poi il refill del batch
e il recupero di un ID originale. Solo il PDF validato e persistito conferma
il successo end-to-end. Se un ID continua a non comparire, leggere i nuovi
artifact per categoria/giorno: il fix non garantisce che SISTER produca il
documento o renda accessibile un elemento nascosto dal proprio limite.

## Rilascio selettivo 258d23fe

Deploy del 6 settembre 2026, avvio container alle 11:49:48 UTC (13:49:48
Europe/Rome), autorizzato dall'utente insieme al commit.

- Commit funzionale: `258d23fe`.
- Backend e platform-scheduler: `gaia-backend:stall-258d23fe`, digest
  `sha256:9f3c5bc0f7c4b4ff5f4e8e028db42de5f764c4e4d956af555c13ebc29d48fd11`.
- Worker visure: `gaia-elaborazioni-worker-visure:stall-258d23fe`, digest
  `sha256:70a61008780158b3e48b035c50341fa1464b44074c820c01ac15ab438f179cbe`.
- Overlay sulle immagini effettivamente attive `ui-f5ef8428` e
  `sister-621cb157`: i quattro file runtime preesistenti sono stati
  confrontati tramite Git blob hash e coincidono con il parent del commit.
  Aggiunto il modulo refill anche nel backend incorporato nel worker.
- Bundle CED `/opt/gaia-releases/stall-258d23fe`, con Dockerfile, sorgenti,
  `compose.pinned.json`, `compose.rollback.pinned.json` e snapshot container.
  Le configurazioni riservate restano sul server con permessi 0600.
- Env (confronto per chiave), mount (per destinazione), entrypoint e command
  verificati prima e dopo; SHA256 dei cinque runtime verificati nei container.
  Frontend, altri servizi, checkout CED e database non modificati.
- Smoke import delle immagini candidate: backend Python 3.11.16 e worker
  Python 3.10.12, entrambi riusciti. Nessun loop worker avviato dallo smoke.
- Scheduler arrestato con exit 0. Il vecchio worker ha eseguito logout e
  rilasciato le richieste, ma non ha terminato entro 120 secondi: Docker lo ha
  terminato con exit 137. Prima della sostituzione: zero execution token,
  cinque identita remote invariate. Il lento shutdown resta da approfondire,
  non e qualificato come arresto completamente graceful.
- Tre container healthy e restart count 0. Health API e pagina
  `/elaborazioni/visure`: HTTP 200.
- Scheduler registrato a intervallo di un minuto; primo ciclo osservato
  alle 11:50:50 UTC. Il worker ha ripreso lo stesso batch alle 11:49:51 UTC.
- Nuovi artifact di ricerca JSON e snapshot HTML/PNG effettivamente presenti
  dopo il primo polling. Le prime ricerche delle vecchie richieste non hanno
  trovato gli ID, anche applicando filtri per singolo giorno. La presenza
  degli artifact non dimostra che il documento sia stato prodotto da SISTER.
- Refill automatico alle 11:52:27 UTC: stesso batch da 20 a 35 righe,
  15 aggiunte e 20 richieste aperte complessive, conforme al cap configurato.
  Le cinque identita originali restano identiche (confronto digest su ID,
  URL remoto, credenziale e data primo invio). Nessuna mutazione manuale DB.
  Prima nuova riga arrivata al form pronto alle 11:52:42 UTC.
- Primo ciclo scheduler terminato con successo alle 11:52:31 UTC, durata
  circa 100 secondi, con conseguente tick mancato. La manutenzione sincrona
  lenta e un limite preesistente ancora osservabile, non risolto da questo
  overlay. `last_error_message` del planner nullo.
- Canary end-to-end persistito alle 11:53:09.385827 UTC (13:53 locali):
  richiesta `3d8ace38-f3bf-4e11-9304-bbc4f6cd616a`, documento
  `e93433ff-4e35-4a43-93c1-424708e557c4`, 16586 byte, SHA256
  `45cbf3ebe66ecf27a25f1619b4a176b4a590cde6a5af380ce11de71267e24032`.
  Verificati contenuto `%PDF-`, size/hash, link documento-richiesta e stato
  completed tramite accesso read-only dal backend. E il primo documento
  successivo allo stallo delle 09:39:49 UTC, non un semplice heartbeat.

### Canary prolungato: esito parziale, non chiusura incidente

Alle 11:56:25 UTC il nuovo PDF resta uno; i cinque recuperi originari non
sono ancora conclusi e le loro identita sono invariate. I cicli scheduler
successivi delle 11:52:50 e 11:53:50 terminano in circa 3 secondi senza errori.

La richiesta successiva `6109ac51-a1d2-4515-a5ec-e6edc2cc3802`, aperta dopo
il polling di una richiesta originale nella sessione riutilizzata, evidenzia
due stati non coperti dal primo canary:

1. Alle 11:54:46 UTC il menu Consultazioni e aperto, ma nel DOM dello snapshot
   manca il link `Visure catastali`; timeout locator dopo 60 secondi.
   Non basta quindi recuperare il link Consultazioni dalla home. La causa
   della diversa risposta del menu resta da riprodurre prima di cambiare
   ulteriormente la navigazione.
2. Alle 11:54:49 UTC il retry raggiunge `Informativa.do`, ma il documento
   visualizzato e gia `Scelta province`, senza alcun controllo Conferma.
   `_confirm_visura_informativa_if_present` deduce la presenza dell'informativa
   dal solo URL e cerca un pulsante inesistente. Lo snapshot dimostra che
   URL e stato del form non sono equivalenti su una sessione riutilizzata.

Il terzo retry torna al primo stato e la richiesta viene differita per errore
recuperabile alle 11:55:53 UTC, senza documento e senza invio remoto nuovo.
Snapshot riservati nel volume CED sotto
`/data/catasto/debug/connection-tests/20260906T115446Z/` e
`/data/catasto/debug/connection-tests/20260906T115450Z/`; non versionati.

Il deploy risolve refill e primo download, ma **non dimostra ancora download
continuativi stabili**. Non sono effettuati reset o retry manuali delle vecchie
richieste. Prossima change da approvare: riprodurre questi due stati con test
browser, rendere la navigazione idempotente rispetto al DOM realmente presente
e riconoscere l'informativa dai suoi controlli, non dal solo URL. Richiesta una
decisione prima di ampliare l'overlay in presenza della nuova failure, secondo
la stop condition di progetto. Non qualificare il rilascio come tutto verde.

### Follow-up autorizzato dopo il canary

L'utente ha autorizzato di proseguire dopo la segnalazione della failure.
Patch locale stretta, senza modificare submission, ownership o deadline:

- Se il menu contiene gia `Visure catastali`, aprire direttamente quel link,
  senza cliccare nuovamente Consultazioni. La fixture copre menu inizialmente
  aperto e chiuso; non dimostra da sola che ogni risposta anomala del portale
  derivi dal toggle del menu, quindi resta necessario il canary reale.
- Se `Informativa.do` contiene gia il selettore delle province e non il testo
  Conferma Lettura, non cercare il pulsante inesistente. Una pagina sconosciuta
  senza selettore e senza conferma conserva il comportamento fail-closed.
- Due regressioni Chrome falliscono prima del fix e passano dopo. Suite
  browser completa: 147 test passati, 1112 statement e 332 branch coperti al
  100%. Ruff/style sui tre file della slice e format del nuovo test passano.
- Scope runtime locale: 2 file, 86 callable, 23 finding (2 error) prima/dopo;
  BrowserSession LOC 1231 ->1233, comunque inferiore alle 1236 della base
  pre-incidente. Nessun aggiornamento baseline/esclusioni. Il gate globale
  resta distinto dai test e dallo style mirati.
- Graphify worker aggiornato dal target dedicato: 1588 nodi, 3698 archi.

Rollback selettivo, dopo rilascio delle richieste attive:

```sh
docker compose -p gaia \
  -f /opt/gaia-releases/stall-258d23fe/compose.rollback.pinned.json \
  up -d --no-deps --no-build backend platform-scheduler elaborazioni-worker-visure
```

Le modifiche locali estranee a coverage plan, report complessita e skill
Graphify non sono incluse nel commit. Il checkout CED sporco e stato preservato.
