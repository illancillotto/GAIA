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

### Rilascio e canary ancora necessari

Distribuire worker e backend/scheduler con overlay selettivo coerente, senza
pull indiscriminato sul checkout CED sporco. Conservare env, mount, comandi,
immagini e configurazioni di rollback. Nessun reset delle richieste gia inviate.
Verificare prima la navigazione della richiesta nuova, poi il refill del batch
e il recupero di un ID originale. Solo il PDF validato e persistito conferma
il successo end-to-end. Se un ID continua a non comparire, leggere i nuovi
artifact per categoria/giorno: il fix non garantisce che SISTER produca il
documento o renda accessibile un elemento nascosto dal proprio limite.
