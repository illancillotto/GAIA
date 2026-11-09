# Avvisi per CF/P.IVA, anno e account Poste — 6 novembre 2026

## Stato e scopo

Implementata nel monolite modulare Ruolo una vista operativa degli avvisi,
separata dalla consultazione storica dei lotti di generazione. Nessuna nuova
migrazione, tabella, dipendenza esterna o credenziale. Rilasciata in produzione
sul CED il 6 novembre 2026 alle 10:13 CET, dopo autorizzazione esplicita.
I test non accedono al portale Poste.

GAIA genera o recupera il PDF, verifica gli indirizzi e prepara le bozze tramite
il worker esistente. La verifica finale e il pulsante **INVIA** restano
all'operatore sul portale Poste. Non è introdotto un comando di spedizione.

## Procedura operatore

1. Aprire **Ruolo → Tributi → Invio solleciti → Solleciti generati**.
2. Inserire CF/P.IVA e anno e premere **Genera o recupera PDF**. Il backend
   normalizza il codice e applica gli stessi candidati/regole Tributi già in uso.
   Riusa il PDF definitivo registrato per lo stesso insieme di avvisi;
   la generazione produce soltanto quelli mancanti. Eventuali errori sono esposti.
3. Consultare i gruppi **anno → account Poste**, con conteggi per stato. Gli
   avvisi ancora senza lavorazione sono **Da assegnare**. Il numero avviso
   identifica la riga canonica, anche quando esistono copie in più lotti.
4. Cercare nome, CF/P.IVA o numero avviso; filtrare anno e stato. La selezione
   di un gruppo filtra l'account. Filtri e pagina sono trasmessi al server.
5. Aprire una riga: il pannello mostra PDF autenticato e storico Poste, con ID,
   date e tracking già persistiti. **Spedito** non significa consegna legale.
6. Selezionare fino a 50 avvisi disponibili, scegliere esplicitamente l'account
   e premere **Prepara avvisi su Poste**. Il controllo indirizzi viene accodato;
   soltanto alla sua conclusione positiva si accodano le bozze valide. La catena
   è persistita: non dipende dal mantenere aperto il browser.
7. Aprire **Posta Online** per seguire la lavorazione. I destinatari dubbi,
   account disabilitati o risultati incerti richiedono verifica; gli altri
   controlli anti duplicato e sui documenti restano quelli del servizio esistente.
8. Dopo l'invio manuale su Poste, scegliere **Controlla stato su Poste** sul
   dettaglio o **Aggiorna spedizioni di questo account** sul gruppo account.
   Si accodano job di riconciliazione che leggono gli esiti; il semplice refresh
   della pagina consulta solo il database GAIA. Le letture visibili si aggiornano
   ogni 30 secondi. I lotti già occupati vengono contati senza duplicare il job.

**Storico lotti di generazione** mantiene anteprime, conferma, rigenerazione,
export e precedente selezione per Posta Online. **Torna agli avvisi** riapre la
vista operativa. Il percorso `/ruolo/tributi/solleciti/poste` resta invariato.
Gli utenti con sola lettura consultano documenti e storico, senza comandi.

## Architettura e API

- `services/solleciti_workspace.py`: la window SQL sceglie l'ultimo item per
  numero avviso; gli item senza numero restano distinti. Lo storico comprende
  tutte le copie. I tentativi annullati non assegnano account. Più tentativi
  non annullati diventano **Conflitto**, senza scegliere automaticamente.
- `services/solleciti_generation.py`: riusa il generatore di dominio;
  advisory lock transazionale PostgreSQL per anno e CF/P.IVA protegge due
  richieste concorrenti del nuovo endpoint. Non altera formule o pagamenti.
- `services/poste_preparation.py`: riusa `create_lot`, riservazioni uniche,
  copie documentali e code Poste. Il flag persistito nel job indirizzi viene
  consumato una volta sola; errori di continuazione restano nel risultato job.
  La riconciliazione per account seleziona solo lotti con bozze pendenti, non
  i tentativi già terminali, e mantiene i controlli account e lock esistenti.
- `posta_online_dispatch_runner._finish`: delega il completamento al servizio
  Ruolo nella stessa transazione prima del commit.
- `PosteWorkspace`, `usePosteWorkspace`, `WorkspaceGeneration`, `WorkspaceGroups`
  usano componenti account, preview e storico esistenti. Nessun secondo design
  system o servizio parallelo; la pagina di dominio resta quella esistente.

Prefisso API: `/ruolo/tributi/solleciti/workspace`.

| Metodo | Percorso | Contratto |
| --- | --- | --- |
| GET | prefisso | `q`, `year`, `account`, `stage`, `page`, `page_size` (1–100); restituisce `groups`, `items`, `total`, `page`, `page_size` |
| POST | `/generate` | `year` (2021–anno corrente), `tax_code` (11 cifre o 16 alfanumerici); risultato `created`, `reused`, `problems` |
| POST | `/prepare` | `item_ids` (1–50 UUID), `credential_id` positivo; restituisce il dettaglio lotto esistente |
| POST | `/reconcile` | `credential_id`, `year` opzionale; risultato `queued_jobs`, `busy_lots` |

Tutte le API richiedono modulo Ruolo e `ruolo.tributi.view`; i POST richiedono
anche `ruolo.tributi.manage_status`. Errori: 401/403 accesso, 422 input,
404 risorsa assente, 409 conflitto/account non utilizzabile. Nessun GET produce
azioni sul provider. Gli allegati continuano a passare dalle API autenticate.

## Analisi preliminare fornita

Letto `verifica_finale.json` nella cartella
`/home/cbo/Desktop/Verifica_duplicati_Poste_20261105_2228`:
943 avvisi attesi, 904 osservati e altrettanti ID spedizione distinti,
24 non osservati non esclusi, 15 esclusi non osservati, zero duplicati,
zero righe recenti non identificate e zero job attivi. Il report dichiara
lettura completa di tutti gli account e database invariato, ma **non** verifica
il contenuto dei PDF sul portale. Queste sono evidenze di quella fotografia,
non una nuova verifica live e non una prova di consegna.

Non sono importati automaticamente quei numeri come esiti dei singoli avvisi.
Le differenze vanno controllate tramite le lavorazioni e la riconciliazione
per account, senza ricreare bozze per il solo fatto che un report non le vede.

## Matrice comportamento → test

| Comportamento | Test |
| --- | --- |
| Identità canonica, copie in lotti diversi, ricerca globale, filtri/pagina e input errato | `test_solleciti_workspace.py::test_workspace_collapses_batch_copies_and_filters_globally` |
| Spedito con storico, account originario, conflitti tra account e annullati | `test_history_ownership_sent_review_and_cross_account_conflict` |
| Stati intermedi e account storico non associato | `test_non_final_states_and_legacy_account_remain_visible` |
| Indirizzi → bozze durevoli, continuazione una volta sola | `test_preparation_survives_browser_close_and_queues_drafts_once` |
| Arresto sicuro per indirizzi dubbi, errori, destinatario incompleto, account disabilitato | `test_preparation_stops_safely_for_review_failures_and_disabled_accounts` |
| Autenticazione, permessi e comandi vietati al viewer | `test_workspace_permissions_and_invalid_commands` |
| Refresh per account/anno, lotti occupati, nessuna mutazione locale dello stato Poste | `test_account_refresh_queues_each_matching_lot_once_and_preserves_external_state` |
| Nessuna bozza, account assente/disabilitato o input errato | `test_refresh_empty_disabled_or_invalid_account_never_creates_a_job` |
| CF/P.IVA esatto, riuso PDF, fallimento renderer e input errato | `test_solleciti_generation.py` |
| Due richieste concorrenti persistono un solo insieme PDF e query JSON/window reale | `test_solleciti_generation_postgres.py` su schema PostgreSQL isolato |
| Nuovi filtri/comandi client, auth e payload POST | `solleciti-workspace-api.test.ts` |
| Selezione solo disponibile, PDF, storico, sola lettura, errori, retry, refresh e risposte obsolete | `solleciti-workspace.test.tsx` |
| Vecchio workflow lotti, documenti, conferma/export | `notice-solleciti-page.test.tsx`, `ruolo-tributi-placeholder-pages.test.tsx` |
| Worker e failure path già esistenti | `test_posta_online_dispatch_runner.py` |
| Browser desktop/mobile, raggruppamenti, generazione, PDF e preparazione simulata | `solleciti-workspace.spec.ts` |
| Browser storico, documento, conferma/export e conflitti | `ruolo-invio-solleciti.spec.ts`, `ruolo-solleciti.spec.ts` |

## Verifiche finali

Verifiche concluse sul perimetro di questa modifica, con evidenze locali in
`/tmp/gaia-workbench-20261106/`. Non è una nuova attestazione del gate dell'intera
piattaforma Communications o del provider reale.

| Controllo | Risultato eseguito |
| --- | --- |
| Backend nuovi endpoint, dominio e concorrenza PostgreSQL | 16 PASS; 5 runtime, 208 statement e 26 branch, tutti coperti |
| Regressione backend mirata completa | 248 PASS, zero skip/failure; PostgreSQL isolato incluso |
| Worker dispatch runner | 23 PASS; intero runtime, 169 statement e 38 branch, tutti coperti |
| Frontend mirato e storico | 79 PASS; 6 runtime, 230 statement, 137 branch, 89 funzioni e 173 linee, tutti coperti |
| Frontend completo | 354 file e 5.512 test PASS, zero failure |
| `cd frontend && npm test` | 18 smoke PASS |
| `npm run typecheck` | PASS |
| ESLint sui runtime e test interessati | PASS senza warning |
| `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` | PASS, 127 file cambiati; nuovi file anche `ruff format --check` |
| `npm run build:clean` | PASS su copia privata, senza toccare la `.next` condivisa |
| Playwright, tre spec pertinenti a 1440/390 px | 6 PASS; storico, PDF nativo caricato, filtri account, generazione, riconciliazione e preparazione simulata |
| `make complexity-ratchet BASE_REF=origin/main` | PASS, zero finding contro baseline del merge-base |
| Baseline privata: `baseline` e `baseline-verify --baseline /tmp/gaia-workbench-20261106/complexity-baseline-private.json` | PASS; riproducibile senza deroghe, baseline condivisa invariata |
| Graphify Ruolo, frontend e worker (target codice dedicati) | PASS; JSON e report aggiornati |
| Graphify documentazione Ruolo | Estrazione semantica completata, `chunk 1/1 done`, nessun chunk fallito |
| Working tree e `git diff --check` | PASS; sorgenti frontend della build identici ai 6 runtime finali, inventario/hash privato |

Coverage dei **12 runtime** interessati: 100% statement e branch, senza nuove
esclusioni. Nessuna linea o branch mancante. La prima regressione mista conteneva
330 test (246 backend + 84 worker); dopo i nuovi casi reconcile è stata ripetuta
la parte backend (248) e il runner worker (23) con nuove evidenze distinte.
Non sommare questi conteggi come casi unici.

Metriche prima/dopo (ciclomatica/cognitiva/LOC): `SollecitiWorkspace`
4/3/25 → 4/3/25, `useSolleciti` 14/20/50 invariato, `_finish` 1/0/8 → 1/0/5.
Il codice nuovo ha massimi ciclomatica 12, cognitiva 11; nessun errore sopra
soglia. Restano tre warning non bloccanti introdotti (generazione, componente
workspace e LOC dell'hook) e cinque warning preesistenti sullo scope:
nessuna regressione dei callable legacy, nessun refactoring massivo o nuova
esclusione. Baseline condivisa, soglie e configurazioni dei gate invariate,
per non assorbire le numerose modifiche concorrenti. La sincronizzazione
e verifica eseguite su copia privata comprendono anche sorgenti concorrenti
(1.870 → 1.901 file, 58 record file differenti): non sono trasferite al
repository. Include/exclude, motori di analisi e soglie conservati; la copia
registra il runtime Python locale 3.14.4 anziché 3.12.3, con stesso motore AST
versione 1. Nessuna modifica al tooling o alla policy.

Tentativi iniziali non verdi conservati: un test unit obsoleto richiedeva lo
storico come vista iniziale; adattato verificando sia vista nuova che storico.
Gli E2E dello storico avevano fixture account/stato annuale `{}` al posto del
contratto reale; corrette le fixture senza cambiare runtime o asserzioni di
conferma/export. Il nuovo E2E inizializzava localStorage anche nel frame PDF:
limitata l'inizializzazione alla finestra principale, mantenendo il controllo
assenza di errori browser e aggiungendo verifica del viewer nativo caricato.
Le esecuzioni precedenti fallite restano nei log; il run finale congiunto ha
sei scenari passati. Screenshot desktop/mobile verificati visivamente, incluso
PDF visibile su mobile; nessun overflow orizzontale nei due viewport.

Altri errori di invocazione corretti: comando Ruff con interprete di sistema
privo di Ruff; sorgenti coverage passati come file anziché moduli importati;
credenziali del database di test inizialmente errate; fixture diretta lotto
senza reader PDF sintetico; sottocomando complexity `scan` inesistente.
Nessuno di questi tentativi è contato come controllo passato. I comandi finali
usano l'interprete backend, moduli importati e il database Docker dedicato con
schema eliminato a fine test. Le credenziali del test non sono stampate né
versionate.

Warning residui: chiave JWT sintetica corta nei test già esistenti; navigazione
jsdom non implementata; lint della build su componenti legacy fuori scope;
workspace root Next dedotta da lockfile sotto `/tmp`; combinazione NO_COLOR /
FORCE_COLOR nel runner browser. Nessuna esclusione aggiunta per eliminarli.
Il grafo frontend supera il limite HTML di 5.000 nodi: JSON/report aggiornati,
visualizzazione HTML non rigenerata da Graphify. Non è un errore di estrazione.

Documentazione aggiornata: PRD Ruolo, execution plan, PROGRESS, procedura Poste,
questo contratto/rapporto e rimando README. Working tree condiviso ancora dirty
per modifiche preesistenti Communications, Utenze, Presenze e operazioni Poste;
non incluse, ripristinate o committate da questa unità. Nuovi sorgenti/test di
questa modifica restano presenti e non tracciati finché non verrà richiesto un
commit. Il gate locale non ha eseguito push, migrazioni, deploy o invii reali;
il successivo rilascio autorizzato è documentato sotto.

Esito del gate locale della modifica: **PASS**. Rilascio coordinato autorizzato
e completato; il collaudo reale sul provider resta distinto e non è stato eseguito.

## Limiti e rilascio

La vista deduplica in SQL, ma costruisce aggregati e applica ricerca/filtri
sull'insieme canonico in memoria prima della paginazione: nessuna promessa di
scalabilità oltre il corpus attuale. Gli avvisi multiannualità compaiono nei
gruppi dei propri anni: i conteggi tra anni non vanno sommati come avvisi unici.
La UI **Da preparare** indica disponibilità del documento e assenza di
assegnazione; i controlli di preparazione restano vincolanti al comando.

Il riuso PDF segue metadati generati e insieme degli ID di origine, non dimostra
nuovamente la reperibilità fisica dei byte: download e preparazione verificano
il documento tramite il servizio esistente. La protezione PostgreSQL del nuovo
generatore serializza quel percorso; non introduce un lock globale sulle altre
funzioni legacy di generazione. Le loro regole rimangono quelle esistenti.

Per un rilascio autorizzato servono backend, frontend e worker Poste coerenti:
il nuovo completamento job deve essere presente nel worker con il backend
condiviso. Nessuna migrazione; verificare assenza di job in corso prima di
sostituire il worker. Non abilitare trasporti PEC/email come effetto collaterale.
Rollback con immagini precedenti coordinate e previa verifica dei job accodati
con `prepare_drafts_after_addresses`: il vecchio worker non continua quel flag.
Conservare lotti, copie documentali ed eventi; non cancellarli nel rollback.

## Rilascio autorizzato sul CED — 6 novembre, 10:13 CET

Release `solleciti-workspace-20261106`, attivata alle 09:13:40 UTC. Aggiornati
soltanto backend, frontend e worker Poste; tutti healthy e con configurazione
effettiva invariata. Preservati 50 container estranei. Nessuna migrazione:
Alembic resta `20261104_1400`. Le immagini e le evidenze prive di segreti sono
registrate in [SOLLECITI_WORKSPACE_RELEASE_2026-11-06.json](evidence/SOLLECITI_WORKSPACE_RELEASE_2026-11-06.json).

Il pacchetto è derivato dalle immagini live, senza trasferire il working tree
condiviso. Preservati 986 sorgenti backend, 1.597 sorgenti worker e tutte le
196 route frontend. Nel router è stata aggiunta soltanto la superficie workspace
(quattro route): il controllo particelle locale estraneo è escluso. Import e
formattazione del router candidato passano Ruff. Il worker include anche
`notice_pdf_regeneration.py` e `notice_recipient_identity.py`, copiati senza
modifiche dal backend live: erano assenti nell'immagine worker precedente e
necessari alla chiusura degli import di `poste_dispatch`. La continuazione
riusa `enqueue_job`; non genera o rigenera documenti.

Prima dell'attivazione, ripetuti sulle immagini candidate 16 test backend con
PostgreSQL isolato e 23 worker: tutti PASS, coverage statement e branch 100%.
Il router distribuito ha due statement in meno del checkout per l'esclusione
della route estranea: totale backend candidato 206 statement e 26 branch.
Ulteriore controllo ORM reale del worker, con SQLite sintetico e rete disabilitata:
successo, indirizzi da rivedere, errore del job e account disabilitato PASS;
la callback ripetuta non crea un secondo job. Sei E2E desktop/mobile sul canary
e sei sulla release pubblicata PASS, senza skip, failure o casi flaky.
Tutte le azioni browser sui provider sono simulate.

Backup dello schema completo e dei dati delle dieci tabelle interessate,
verificato tramite hash e ripristino su un clone isolato: PASS. Non è un backup
integrale degli 84 GB del database tributario. Dump e configurazioni contenenti
PII o segreti restano esclusivamente nella directory protetta del CED.

Il primo tentativo è stato automaticamente annullato da un probe che confrontava
testualmente date UTC serializzate come `+00:00` e `Z`. Ripristinati e verificati
i tre servizi precedenti prima di proseguire. Una diagnosi di sola lettura su
33 righe di storico ha confermato identità dei valori; differenze soltanto nella
serializzazione di `draft_created_at`, `sent_at` e `updated_at`. Corretto il probe
usando il modello già esistente per normalizzare le date, senza cambiare runtime,
test applicativi o immagini. Seconda attivazione completata con i controlli
autenticati e il confronto dello storico superati. Evidenze del tentativo e del
rollback conservate.

Controlli finali via GAIA: sei pagine HTTP 200; tre API anonime HTTP 401.
Il probe autenticato, con transazione di sola lettura, verifica 1.112 avvisi
canonici complessivi, 1.009 del 2021 e 12 gruppi; confronta tre campioni spediti
con lo storico persistito e verifica che non siano nuovamente preparabili.
Nessun download dinamico di PDF o comando di generazione eseguito nel probe.
Questi conteggi descrivono il database al rilascio, non il numero di invii
verificati sul portale né l'eleggibilità di tutti gli avvisi.

Prima e dopo il rilascio: 1.277 item di lavorazione Poste, 431 nello stato
`sent`, zero job attivi o continuazioni pendenti. Controllati tutti gli stati
attivi del servizio: `pending`, `queued_resume`, `processing`. Communications
resta in pausa, con account, messaggi e job pari a zero; PEC/email non abilitate
da questo rilascio. Non sono state effettuate chiamate ai provider nei test né
modifiche ai dati tributari. INVIA resta manuale sul portale Poste.

Canary, database sintetici e file `.env` temporanei rimossi; immagini precedenti,
backup ed evidenze conservati per il rollback. Nessun commit o push eseguito.
Il working tree mantiene le modifiche concorrenti estranee. I limiti funzionali
e di scalabilità descritti sopra restano validi; non è attestato un nuovo gate
globale dell'intera piattaforma Communications o un collaudo dei provider reali.

## Revisione UX successiva al rilascio — collaudo locale prima della pubblicazione

Dopo l'uso della release l'utente richiede anno e ricerca unica per
nominativo/CF, pulsante **Genera o recupera PDF** disabilitato e una UI ordinaria
senza lotti. Autorizzata esplicitamente anche la realizzazione della schermata
semplificata. Le verifiche seguenti descrivono il checkout prima della nuova
autorizzazione. Il rilascio sul CED è documentato nella sezione finale; la
sezione precedente descrive la prima release del mattino.

### Analisi e comportamento implementato

| Problema osservato | Comportamento implementato |
| --- | --- |
| Anno e identificativo ripetuti nel pannello generazione e nei filtri | Una sola barra con anno e ricerca per nome/cognome, CF/P.IVA o numero avviso. Pulsante PDF disabilitato, con motivazione accessibile, senza form o handler di generazione |
| Riquadri account e annualità non selezionate prima dell'elenco | Eliminato `WorkspaceGroups`; gli aggregati restano nel contratto API soltanto per popolare le opzioni dei filtri |
| Troppi comandi simultanei | Stato/account e controllo del portale per account sotto **Altri filtri**, richiudibile, con indicazione quando i filtri sono attivi |
| L'operatore deve scorrere prima di arrivare ai documenti | Elenco compatto a sinistra e dettaglio/PDF a destra, subito dopo i filtri; layout verticale su mobile |
| Account e informazioni di trasporto occupano spazio su ogni riga | Righe con contribuente, CF, anno, numero, importo e stato; ID Poste, date e tracking consultabili nello storico richiudibile del dettaglio |
| Preparazione visibile anche senza selezioni | Barra persistente sul fondo soltanto quando ci sono avvisi selezionati; account richiesto esplicitamente, comando **Prepara su Poste** |
| Dopo la preparazione si apre automaticamente un lotto | Conferma nella stessa pagina, selezione azzerata, stessi filtri e avviso aperto; nessun cambio automatico di scheda |
| Il polling smonta e ricarica il PDF durante la lettura | Refresh manuale/automatico mantiene il documento montato. Cambio filtri svuota i risultati precedenti; cambio sessione cancella dati, selezione e dettaglio |
| La struttura tecnica dei lotti confonde il percorso ordinario | Storico lotti accessibile soltanto da **Strumenti avanzati**; nessun comando Apri lavorazione nel dettaglio ordinario |

Il selettore conserva l'anno scelto anche mentre la richiesta è in corso.
**Aggiorna elenco** rilegge GAIA; **Controlla stato su Poste** e il controllo per
account accodano letture tramite il worker esistente. Questi comandi non sono
confusi con la creazione di bozze o con una spedizione. Gli avvisi già spediti
restano consultabili ma non selezionabili. PDF mancante, elenco vuoto e fallimenti
di preparazione/lettura restano distinti; la selezione rimane disponibile dopo
un errore di preparazione per consentire la verifica e il retry esplicito.

API, permessi, lotti persistiti, riservazioni anti duplicato, account e worker
sono invariati. La scheda Posta Online e le funzioni storiche sono conservate
per accesso esplicito; non diventano il passaggio obbligato del nuovo percorso.
Il blocco PDF riguarda il pulsante operativo: non disabilita globalmente l'API
di generazione o i vecchi strumenti amministrativi. Verifica finale e INVIA
restano sempre sul portale Poste. Nessuna nuova dipendenza, migrazione o azione
su provider durante lo sviluppo.

### Verifiche della revisione

Evidenze locali in `/tmp/gaia-solleciti-ux-20261106/`. I primi controlli sulla
sola disabilitazione sono stati ampliati dopo l'autorizzazione alla nuova UI.

- 86 test frontend pertinenti PASS su cinque file. Coverage dei cinque runtime
  attuali: 100% statement (197), branch (130), funzioni (72), linee (150).
- `npm test`: 18 smoke PASS. Typecheck ed ESLint dei runtime/test interessati
  PASS, senza warning nel perimetro.
- La suite verifica ricerca/anno, filtri aggiuntivi, PDF e storico, selezione,
  permessi, preparazione senza cambio contesto, errori/retry, paginazione,
  sessione, risposte obsolete e PDF mantenuto durante il refresh.
- Complessità complessiva dei cinque file, includendo il modulo gruppi ritirato
  nel prima e il modulo stati nel dopo: ciclomatica 201 → 178, cognitiva
  136 → 125, LOC 352 → 327. Zero errori; cinque warning, con hotspot legacy del
  padre invariati. Nessun cambiamento a soglie, baseline o esclusioni.
- Ratchet contro il merge-base `origin/main`: nessun finding sullo scope. La
  verifica globale fallisce per 17 finding Presenze estranei su sette file;
  non sono corretti né assorbiti. Non è dichiarato un PASS globale.

Un primo ratchet ristretto attribuiva erroneamente `filter` al callable omonimo
Dotazioni, presente sul disco ma escluso dal report ristretto. Verificata la
provenienza della baseline: quel callable vive in `DotazioniList.tsx`. Il ratchet
con il contesto originale Dotazioni incluso passa con zero finding; quello
completo conferma solo i finding Presenze. Il file Dotazioni è invariato.
Nessuna modifica allo scanner o formattazione artificiale per ridurre LOC.

Tentativi intermedi conservati: fixture che selezionava un account prima del
caricamento delle opzioni; JSDOM che non filtra i figli di `details` chiusi nei
role query; branch storico inizialmente mancante. Corretti attesa dell'account,
controllo dello stato `open` e caso di lettura dello storico, mantenendo le
asserzioni sui comandi. Tentativo di Vitest dalla root fallito per risoluzione
del binario/provider; esecuzioni valide tramite il binario in `frontend/`.
Nessun package o lockfile cambiato da questa revisione. La build iniziale è
stata ripetuta dopo la correzione del refresh per verificare i byte finali.

Verifica conclusiva sul codice finale: `npm run build:clean` PASS su copia
isolata, senza cancellare la `.next` condivisa; typecheck e lint mirato PASS.
La build completa riporta warning legacy esterni al perimetro e la deprecazione
di `next lint`; nessun warning ESLint nei runtime/test interessati.
Sei E2E PASS, zero skip, failure o flaky, su viewport 1440 e 390 px. I test
verificano anche il rendering riuscito del PDF sintetico nel viewer Chromium,
l'assenza di overflow orizzontale e di sovrapposizione ricerca/pulsante.
Il controllo visivo aveva rilevato una sovrapposizione mobile: corretta la
distribuzione dello spazio del campo, poi ripetuti build, coverage ed E2E.
Screenshot desktop/mobile e barra selezioni ispezionati dopo la correzione.
I cinque runtime della build sono byte-per-byte identici al checkout misurato.

### Matrice comportamento → test della revisione

I nomi sotto identificano test effettivi in
`frontend/tests/unit/solleciti-workspace.test.tsx`, salvo indicazione diversa.

| Funzionalità | Comportamento atteso | Test |
| --- | --- | --- |
| Ricerca e anno | Filtri server-side, senza campi duplicati | `filters on the server by reference year, account, status and search`; `disables PDF generation without duplicate identity or year fields and keeps the unified search usable` |
| Filtri secondari | Schermata iniziale essenziale, filtri su richiesta | `keeps the default screen focused on notices and reveals extra filters only on request` |
| Elenco e PDF | Documento reale, assenza documento esplicita, paginazione | `opens canonical notices and only selects available ones for worker preparation`; `paginates and exposes missing documents without a false preview`; E2E `ricerca unica, PDF e preparazione senza lotti` a entrambe le larghezze |
| Storico | ID/date consultabili senza aprire un lotto | `keeps Poste identifiers and dates in the notice detail without exposing a lot command` |
| Preparazione | Account obbligatorio, selezioni limitate, nessuna navigazione automatica | `opens canonical notices and only selects available ones for worker preparation`; `discards stale reads, bounds selection and clears it when filters change`; E2E sopra |
| Errori | Messaggi espliciti, selezione preservata per retry manuale | `reports preparation conflicts, preserves selection and supports retry`; `reports empty/error reads and yearless historical records` |
| Riconciliazione | Solo account scelto o job esistente, errori visibili | `refreshes only an explicitly selected account and reports queueing and provider errors`; `can queue an account refresh across all years and surfaces non-Error failures`; `reconciles via the existing worker job and reports failures instead of changing sent state locally` |
| Permessi | Utente lettore senza comandi di scrittura | `keeps read-only users from generation, selections and reconciliation writes` |
| Refresh e sessione | PDF stabile, risposte obsolete ignorate, dati azzerati al cambio identità | `keeps the open PDF mounted while refreshing states`; `ignores a failed obsolete request after a newer filter has loaded`; `refreshes visible pages and cleans the timer on unmount`; `clears previous identity data, selection and detail when the session token changes` |
| Compatibilità | Storico avanzato e scheda Posta Online conservati | `preserves technical batch history without making it the default view`; E2E `ruolo-invio-solleciti.spec.ts` e `ruolo-solleciti.spec.ts` |

Il grafo frontend è stato ricostruito tramite il target dedicato con pruning:
6540 nodi, 13786 relazioni, zero nodi del componente gruppi ritirato. L'ultimo
aggiornamento incrementale sui byte finali conferma nessun cambio di topologia.
Nessun artefatto Graphify incluso nel versionamento.
Aggiornato anche il corpus documentale con `make graphify-ruolo-docs`:
estrazione semantica completata (`chunk 1/1 done`), senza chunk falliti.

Perimetro finale: cinque runtime, due file di test unitari adattati/estesi,
tre E2E e quattro documenti di dominio. Rimosso il componente gruppi non più
usato. Nessuna modifica backend, DB, dipendenze o configurazioni di produzione
in questa revisione. Working tree concorrente preservato, `git diff --check`
del perimetro PASS; log, coverage e build rimangono sotto `/tmp`.

Il gate globale rimane **FAIL** per i 17 finding Presenze già descritti; non
è stato eseguito un nuovo collaudo completo dell'intero repository o di provider
reali. Il gate locale della schermata passa. Residui: decisione di rilascio
della nuova UX e risoluzione dei finding estranei nel rispettivo ciclo.

Durante il collaudo locale nessun deploy, commit, push o invio reale. Working
tree concorrente preservato; artefatti di verifica esterni al repository.


## Rilascio UX autorizzato e apertura dalla riga — 2026-11-06

Su richiesta esplicita «deploya / porta in produzione la modifica», pubblicata
la release frontend `solleciti-ux-20261106` alle **12:48:43 CET**. Durante la
preparazione l’utente ha richiesto anche di aprire PEC/email cliccando sulla
riga dell’avviso e rimuovere Componi: la revisione è inclusa nello stesso
pacchetto, dopo nuovi test e una nuova build. Immagine finale:
`sha256:196463ab023f3fdf6f1913f3dd47f0bed07cc79c302e8432f565186987711929`.

### Apertura del compositore PEC/email

La riga conserva la semantica di tabella ed è raggiungibile con Tab; clic,
Invio o Spazio eseguono lo stesso `open` che gestiva Componi/Apri comunicazione.
Se esiste un messaggio si apre lo storico, altrimenti vengono caricati campi e
anteprima sorgente. Rimossi il pulsante e la relativa colonna Azioni; Nuova
revisione resta accanto allo stato del messaggio annullato. Checkbox e Nuova
revisione fermano la propagazione del clic, evitando una doppia apertura.
Durante il caricamento i comandi sono bloccati. Nessuna bozza o spedizione
viene creata automaticamente dal clic; snapshot, checklist e autorizzazione
restano obbligatori. Utenti lettori possono aprire soltanto messaggi esistenti.

| Comportamento | Test pertinente |
| --- | --- |
| Clic sulla riga carica i campi, cambio avviso azzera i campi precedenti | `keeps the selected notice and fields in the right panel while the candidate list remains available` |
| Apertura con Invio/Spazio; checkbox indipendente; nessun pulsante Componi | `activates notice rows with Enter or Space and keeps checkbox keys and clicks independent` |
| Lettore bloccato sulle nuove bozze, storico consultabile | `blocks row activation for read-only drafts but opens existing history` |
| Caricamento in corso, errore e nuova revisione senza doppia apertura | `blocks additional row and revision actions while loading history and recovers after failure` |
| PDF intero prima della bozza, approvazione e invio simulato | Quattro E2E `PDF integrale e approvazione individuale`, PEC/email a 1440/390 px |

I test unitari si trovano in `frontend/tests/unit/communications/workspace.test.tsx`;
le quattro prove browser in `frontend/tests/e2e/communications.spec.ts`.

### Isolamento e verifiche del pacchetto

Sorgenti ricostruite dalla release frontend attiva del mattino, senza copiare
l’intero checkout sporco. Confronto hash: **sei runtime cambiati/aggiunti**, un
componente gruppi rimosso, **765 file sorgente/config/pubblici preservati** e
196 route conservate. Nessuna modifica Presenze locale inclusa. Base precedente
`cb2169a8fc62`, tag di rollback conservato sul CED. Configurazione effettiva
ambiente, comando, healthcheck, risorse, mount e reti identica alla precedente.
Soltanto il frontend è stato ricreato; nginx ricaricato per aggiornare l’upstream.
**52 altri container preservati** al momento dell’attivazione.

- 143 test frontend PASS su 13 file, inclusi 15 della workspace PEC/email.
- Coverage full-file dei sei runtime: 100% statement **262/262**, branch
  **160/160**, funzioni **110/110**, linee **185/185**. Nessuna esclusione nuova.
- Typecheck e lint mirato PASS; clean build sull’immagine candidata PASS.
  Warning legacy esterni alla revisione e deprecazione `next lint` conservati.
- Dieci E2E sull’istanza temporanea PASS, zero skip, failure o flaky; API
  interamente simulate, nessuna connessione o spedizione su provider reali.
- Ratchet contestuale dei sei runtime contro `origin/main` PASS, zero finding.
  Aggregati finali: ciclomatica 238, cognitiva 150, LOC 383; zero errori e sei
  warning legacy/sotto soglia. Soglie e baseline invariate. Il precedente gate
  globale resta FAIL per le modifiche Presenze estranee; non è attestato un
  nuovo collaudo completo dell’intero repository.
- Grafo frontend aggiornato: `CandidateRow()` presente e gruppi ritirati
  assenti. PRD/manuale/progress/changelog Communications aggiornati e grafo
  documentazione piattaforma completato (`chunk 1/1 done`, nessun chunk fallito).

Controlli live: login, Solleciti, Posta Online, PEC, Email e health HTTP 200;
workspace senza credenziali HTTP 401. Probe autenticato in sola lettura PASS:
1.125 identità canoniche complessive, **1.022 del 2021**, 12 gruppi account;
tre campioni di storico corrispondenti al DB e avvisi spediti non preparabili.
La prima prova riutilizzava il vecchio raggruppamento per numero avviso ed è
fallita prima dell’attivazione: il backend già pubblicato per gli eredi usa
anche `heir_delivery.reference`. Il solo probe è stato allineato a questa
identità verificata nel servizio live; nessuna modifica runtime per superarlo.

Communications resta in pausa con zero account al controllo pre-rilascio.
Nessuna abilitazione trasporti, migrazione, modifica tributaria o invio reale.
Log di build, tentativi superati e controlli in
`/tmp/gaia-solleciti-ux-deploy-20261106/`; copie protette e configurazioni di
rollback in `/opt/gaia/releases/solleciti-ux-20261106/` sul CED. La prima build
solo Solleciti è stata superata dalla richiesta sulle righe; un tentativo della
build successiva è stato cancellato prima dell’attivazione per correggere un
parametro inutilizzato emerso nel lint. L’immagine finale è stata ricostruita e
ricollaudata. Nessun commit o push; modifiche concorrenti preservate.

Verifica browser dopo l’attivazione su `http://gaia.lan`: **dieci E2E PASS**,
zero skip, errori o flaky, con API simulate. Le prove esercitano il bundle
pubblicato senza scritture al database reale. La consultazione autenticata
separata usa soltanto letture e confronta lo storico persistito.

Istanza temporanea rimossa dopo il collaudo; immagine precedente e configurazione
di rollback conservate. Frontend, backend e worker Poste healthy alla chiusura.
Evidenza pubblicabile senza segreti:
[evidence/SOLLECITI_UX_RELEASE_2026-11-06.json](evidence/SOLLECITI_UX_RELEASE_2026-11-06.json).


## Stati Poste visibili nell’elenco — verifica del 6 novembre

Segnalazione operatore: nelle prime pagine tutti gli avvisi sembrano «Da
preparare». Audit live in sola lettura: **1.022 avvisi 2021**, dei quali **436
spediti, 467 caricati, 68 da preparare, 49 da verificare, 2 in lavorazione**.
Nessun conflitto al momento della verifica. La proiezione API è coerente con
le lavorazioni persistite: `sent` 436; `draft_created` 10 + `draft_priced` 457;
`address_review` 48 + `draft_error` 1; `address_ok` 2. I 346 tentativi annullati
non assegnano un avviso allo stato caricato/spedito.

Causa UX: l’ordinamento corrente è per anno, etichetta account e nominativo;
«Da assegnare» precede gli account. I 68 avvisi senza lavorazione attiva
occupano quindi le prime quattro pagine. Tre numeri leggibili nella schermata
segnalata sono stati cercati nell’API e risultano effettivamente senza
lavorazione attiva GAIA. Non sono stati cambiati stati per far coincidere la
schermata con un’aspettativa: nessun backfill, invio, import o aggiornamento DB.

La UI mostra ora contatori cliccabili per tutti gli stati prima dell’elenco,
calcolati dai gruppi globali restituiti dall’API, indipendenti dalla pagina
corrente. Sono rispettati anno, ricerca e account scelti; il filtro di stato
non nasconde gli altri contatori, consentendo di cambiare vista direttamente.
I badge distinguono per testo e colore spediti, caricati, in lavorazione e
stati da verificare. Le righe caricate/spedite mostrano ID Poste e data salvati;
la raccomandata compare quando presente. Una data assente resta «-», un ID
assente «Non registrato»; nessuna data ricavata arbitrariamente da updated_at.
Il dettaglio conserva lo storico completo dei tentativi.

La scelta dell’evidenza nella riga rispetta lo stato aggregato: solo `sent`
per uno spedito, `draft_created`/`draft_priced` per un caricato. I tentativi
annullati non vengono usati per quel riepilogo. Metadati mancanti sono espliciti.
La checkbox mantiene il `can_prepare` del backend; un badge non sblocca nuove
spedizioni. Gli stati sono quelli salvati in GAIA, non una nuova lettura del
portale: Controlla stato su Poste continua a richiedere esplicitamente il job
esistente, senza caricare o spedire.

| Comportamento | Test in `solleciti-workspace.test.tsx` |
| --- | --- |
| Contatori globali, anno/account e cambio diretto dello stato | `shows global Poste state counts independently of the current page and filters them by year/account` |
| Badge e ID/date di caricato/spedito; tentativo annullato ignorato; checkbox bloccata | `shows persisted sent/upload IDs and dates in the list, ignoring cancelled attempts and keeping selection blocked` |
| Evidenza mancante, ID/data null e gruppi vuoti | `keeps absent Poste metadata explicit without fabricating a shipment date or draft ID` |

21 test della workspace PASS, coverage dei due runtime modificati 100%
statement/branch/funzioni/linee (65/77/34/49). Typecheck, lint e ratchet dello
scope contro `origin/main` PASS. Nessuna modifica a API, backend, modelli,
migrazioni, dipendenze, worker o ordine/paginazione server. Lo stato del
rilascio e il collaudo browser conclusivo sono registrati sotto.


### Pubblicazione della visibilità stati — 13:27 CET

Release `poste-status-20261106` attivata il 6 novembre alle **13:27:12 CET**;
frontend `c74c02c59022` (immagine completa nell’evidenza). Il pacchetto deriva
esattamente dalla release attiva `196463ab023f`: soltanto i due runtime dello
stato cambiano, 769 sorgenti/config/file pubblici preservati e 196 route
invariate. Clean build PASS; dieci E2E sulla candidata PASS senza skip o flaky.
Screenshot desktop e mobile ispezionati. 89 test di regressione frontend PASS
anche sulle sorgenti della candidata, 18 smoke PASS. Nessuna nuova dipendenza.

Configurazione effettiva invariata e 52 altri container preservati. Login,
Solleciti, Posta Online, PEC, Email e health HTTP 200; workspace anonima HTTP
401. Probe autenticato readonly PASS: tre campioni di storico identici al DB,
avvisi già spediti non preparabili, 1.022 identità canoniche 2021. Nessuna
migrazione o modifica di dati/stati, nessuna spedizione o connessione ai provider
nei test. Backend e worker non riavviati. Immagine e configurazione precedenti
conservate per rollback. Log e controlli protetti sul CED in
`/opt/gaia/releases/poste-status-20261106/`; evidenze locali in
`/tmp/gaia-poste-status-20261106/`.

Il gate dello scope passa; resta il precedente gate globale FAIL per 17
finding Presenze estranei, non inclusi nel pacchetto. Baseline, soglie e test
preesistenti non sono stati indeboliti. Nessun commit o push.

Dieci E2E ripetuti sulla release pubblicata su `gaia.lan`: PASS, zero skip,
errori o flaky; API simulate anche in questo collaudo. I contatori e il cambio
filtro dello stato sono verificati insieme a PDF e composizione PEC/email.
Evidenza: [POSTE_STATUS_VISIBILITY_2026-11-06.json](evidence/POSTE_STATUS_VISIBILITY_2026-11-06.json).

Istanza temporanea e tunnel di collaudo rimossi. Immagine precedente e rollback
conservati; frontend, backend e worker Poste healthy alla chiusura.
