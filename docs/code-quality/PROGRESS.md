# Progress - GAIA Code Complexity Program

Questo file e la fonte di verita persistente. Hermes deve aggiornarlo dopo ogni
blocco verificato e prima di chiudere un goal.

### Wiki supporto - mapping pathname/modulo (2026-10-02)

- Hotspot unico: `inferModuleKeyFromPath` in `request-support-payload.ts`,
  checkout `main@6bddef61`; file inizialmente pulito. Lavori concorrenti,
  Organigramma e giornaliere preservati. Graphify frontend consultato.
- Prima: callable cognitiva/ciclomatica/LOC `12/13/15`, nesting `1`;
  cinque callable e due warning nel file, zero error. Invarianti: ordine
  dei prefissi, startsWith case-sensitive e permissivo, alias rete/inventario,
  null sui path sconosciuti; payload e link supporto invariati.
- Caratterizzazione: 19 nuovi casi sui dodici prefissi, suffix, casing,
  slash iniziale, path sconosciuti e alias non validi; suite prima della
  slice 43 test verdi e full-file 100%. Slice: tabella readonly ordinata,
  ricerca del primo prefisso corrispondente senza normalizzazioni nuove.
- Dopo: mapper cognitiva `12 -> 1`, ciclomatica `13 -> 2`, LOC `15 -> 3`,
  nesting `1 -> 0`; callback find `0/1/1/0`, nessuna violation.
  File: cognitiva `27 -> 16`, ciclomatica `32 -> 22`, callable `5 -> 6`,
  LOC `104 -> 106` per la tabella dichiarativa. Warning `2 -> 1`, zero error;
  resta solo il warning distinto di `buildSupportHrefFromPayload`.
  Esito `IMPROVED`, decisioni e debito ridotti senza trasferire violation.
- 43 test helper passati prima/dopo, full-file 100% statement (`36/36`),
  branch (`32/32`), funzioni (`6/6`) e linee (`26/26`) dopo.
  Ratchet mirato autorevole contro `origin/main`, merge-base `6b61fd27`,
  PASS prima e dopo, `findings: []`. Baseline, scope ed eccezioni invariati.
- Evidenze `/tmp/gaia-wiki-module-{before,after}.json`, log characterization/
  after/final/ratchet/lint/types/quality/Graphify con lo stesso prefisso.
  Regressione supporto 46 test passati, stesso full-file 100%; ESLint,
  typecheck senza incremental, diff whitespace e 90 test tooling verdi.
  Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done` senza warning di chunk falliti.
  Un solo hotspot, commit isolato dopo i gate mirati secondo
  l'autorizzazione vigente. Nessun push.

### Wiki - resolver dei link contestuali (2026-10-02)

- Hotspot unico successivo al commit `655c6e78`: `buildWikiContextHref` in
  `features/wiki/context-links.ts`, file inizialmente pulito. Organigramma,
  giornaliere e altri lavori concorrenti esclusi; nessun push.
- Prima: cognitiva `36`, ciclomatica `21`, LOC `62`, nesting `2`, un callable,
  due error e un warning. Invarianti: prefissi e precedenza entity/module,
  suffix non codificato nei path, encoding delle query, lookup speciale,
  fallback e null per moduli sconosciuti preservati.
- Slice: normalizzazione nullish della chiave a stringa vuota, eliminando
  la guardia esterna e il relativo annidamento, senza helper nuovi.
- Caratterizzazione: 27 casi aggiunti di fallback, precedenza, encoding,
  suffix vuoto/ripetuto e lookup; 29 test passati prima e dopo.
- Dopo: cognitiva `36 -> 23`, ciclomatica `21 -> 21`, LOC `62 -> 61`,
  nesting `2 -> 1`; un callable invariato. Error `2 -> 1`, warning `1 -> 2`:
  eliminata la violation cognitive error; resta ciclomatica error legacy.
  Esito `IMPROVED`, nessuna estrazione o trasferimento di debito.
- Core del resolver al 100% statement (`43/43`), branch (`40/40`), funzioni
  (`1/1`) e linee (`43/43`). Ratchet autorevole mirato contro `origin/main`,
  merge-base `6b61fd27`: PASS prima e dopo, `findings: []`.
  Baseline, scope ed eccezioni invariati; nessuna conformita globale dichiarata.
- Graphify frontend aggiornato tramite target dedicato; refresh platform
  docs completato con `chunk 1/1 done`, senza warning di chunk falliti.
  ESLint runtime/test, typecheck senza incremental,
  diff whitespace e 90 test quality tooling passati. Evidenze con prefisso
  `/tmp/gaia-wiki-links-` (metriche before/after, coverage, test e ratchet).
- Slice delimitata al resolver: nessun secondo hotspot. Commit isolato
  autorizzato solo dopo i gate mirati, senza includere altri lavori o push.

### Wiki audit - aggregazione delle modalita (2026-10-02)

- Hotspot unico: `buildWikiAuditStats` in `features/wiki/audit-utils.ts`,
  checkout `main@af768d77`; file inizialmente pulito. Organigramma,
  giornaliere e modifiche concorrenti preservati.
- Primo tentativo di commit Network/API bloccato da `.git/index.lock:
  File system in sola lettura`. Retry esplicitamente autorizzato dopo il
  ripristino dei permessi; scope esteso alla presente slice Wiki verificata.
- Prima: callable cognitiva/ciclomatica/LOC `15/15/59`; callback reducer
  `13/13/28`. Suite iniziale due test verdi, coverage incompleta;
  caratterizzazione portata a 13 test e full-file 100% prima della slice.
- Invarianti: quattro modalita esatte, sconosciute ignorate (anche nomi
  del prototipo), contatori/ranking/latency, fallback module nullish,
  limite top tre e assenza di mutazioni invariati. Slice: mapping esplicito
  delle modalita ai contatori con Map, senza helper o modifica dei contratti.
- Dopo: aggregatore `12/12/51`, reducer `10/10/20`; cognitiva aggregata
  `31 -> 25`, ciclomatica `37 -> 31`, LOC file `84 -> 82`, otto callable
  invariati. Error `1 -> 0`, warning `3 -> 3`; `IMPROVED` senza nuovi
  callable o trasferimento di violation. Le metriche aggregate includono
  la callback sia nel padre sia come callable, secondo lo scanner vigente.
- Validazione: 13 test helper passati prima/dopo; coverage full-file finale
  100% statement (`29/29`), branch (`24/24`), funzioni (`8/8`), linee
  (`29/29`). ESLint runtime/test, typecheck senza incremental e diff
  whitespace passati. Tooling quality: 90 test passati, inclusi aggiornamenti
  concorrenti non modificati da questa slice.
  Regressione con pagina audit: 14 test passati, stesso full-file 100%.
- Ratchet autorevole mirato contro `origin/main`, merge-base `6b61fd27`:
  PASS, `findings: []`. Baseline, esclusioni e scope invariati; nessuna
  sincronizzazione globale sul checkout concorrente.
- Graphify frontend aggiornato tramite target dedicato; refresh platform
  docs tramite `make graphify-platform-docs` tentato: chunk semantico fallito
  per `Connection error` con warning partial results, pur con exit 0.
  Arricchimento docs non verificato nell'ambiente a rete limitata.
- Evidenze in `/tmp/gaia-wiki-stats-{before,after}.json`, log
  `/tmp/gaia-wiki-stats-{characterization,after,final}.log`, directory
  `/tmp/gaia-wiki-stats-final-coverage` e log lint/types/ratchet/quality/
  Graphify con lo stesso prefisso. Restano tre warning, nessun error.
- Iterazione chiusa su un hotspot; nessun secondo refactoring.
  Retry commit: validazione combinata 18 suite, 905 test passati, coverage
  per-file 100% sui tre runtime (190 statement, 179 branch, 33 funzioni,
  189 linee); ESLint e ratchet autorevole mirato verdi. Index isolato:
  tre runtime, tre test e sole sezioni Network/API/Wiki dei due registri.
  Baseline e lavori degli altri team esclusi, nessun push autorizzato.

### API core - precedenza risposte vuote (2026-10-02)

- Slice unica successiva autorizzata: controlli dei risultati vuoti in
  `request`, checkout `main@af768d77`; preservate le slice precedenti e
  le modifiche concorrenti, Organigramma e giornaliere esclusi.
- Prima: request cognitiva `24`, ciclomatica `20`, LOC `60`, nesting `2`;
  aggregati core cognitiva `143`, ciclomatica `98`, LOC `207`, 16 callable.
  Ratchet mirato contro `origin/main`, merge-base `6b61fd27`, PASS.
- Invarianti: errori HTTP prima del controllo body; status 204/205 senza
  leggere header o body; solo lunghezza esattamente `"0"` evita il parsing.
  Parsing JSON, risultati falsy e rejection SyntaxError invariati.
- Caratterizzazione: 19 nuovi casi di precedenza/status/header/body; tutti
  passano prima della modifica. Slice minima: unificare i due return
  undefined con valutazione short-circuit, senza helper o nuova policy.
- Tentativo di unificazione respinto: cognitiva request `24 -> 25`,
  aggregato `143 -> 144`, nuova violation cognitive error rispetto all'inizio
  della slice. Ciclomatica `20` e LOC `60` invariate: nessuna riduzione
  dimostrata. Ripristinati esclusivamente i controlli di questa slice;
  refactoring precedenti preservati, nessuna modifica runtime netta.
- Esito `NO_SAFE_CHANGE`: la guardia condivisa non soddisfa il quality
  ratchet locale, anche se il confronto con la baseline storica resta verde.
  Conservata la caratterizzazione, senza dichiarare riduzione di complessita.
  Metriche finali identiche all'inizio: `24/20/60/2`, aggregati `143/98/207`,
  16 callable; baseline, scope ed eccezioni invariati.
- Validazione finale: 861 test API passati su 15 suite, core al 100%
  statement (`118/118`), branch (`101/101`), funzioni (`16/16`) e linee
  (`117/117`). Metriche/fingerprint/file finali identici al report iniziale;
  ratchet autorevole mirato PASS, `findings: []`. ESLint runtime/test e
  typecheck senza incremental e diff whitespace passati; baseline non
  modificata. Nessuna failure nei test.
- Graphify frontend consultato; nessun refresh codice necessario per una
  slice senza modifiche runtime nette. `make graphify-platform-docs`
  tentato: `chunk 1/1 failed: Connection error`, warning di risultati
  parziali pur con exit 0; arricchimento documentale non verificato.
- Evidenze in `/tmp/gaia-api-empty-{before,after,final}.json`,
  `/tmp/gaia-api-empty-{characterization,tests-final}.log`, directory
  `/tmp/gaia-api-empty-final-coverage` e log ratchet/lint/types/Graphify con
  lo stesso prefisso. Nessun secondo hotspot, commit o push.
- Prossima azione separata: scegliere un candidato diverso con riduzione
  reale, evitando ulteriori estrazioni neutre di request.

### API core - lifecycle timeout e abort (2026-10-02)

- Hotspot unico autorizzato: lifecycle timeout/abort in `request`, checkout
  `main@af768d77`; preservata la precedente estrazione `readResponseError`
  e tutte le modifiche concorrenti, Organigramma e giornaliere esclusi.
- Prima: request cognitiva `28`, ciclomatica `22`, LOC `62`, nesting `2`;
  aggregati core cognitiva `147`, ciclomatica `100`, LOC `209`, 16 callable.
  Suite API iniziale: 833 test verdi, coverage full-file 100%.
  Ratchet mirato contro `origin/main`, merge-base `6b61fd27`, PASS.
- Invarianti: timeout attivo solo per valori truthy; identita del segnale
  senza timeout, propagazione della reason esterna, errore ApiError al
  timeout, identita delle altre rejection e deadline limitata a fetch,
  non alla decodifica del body. Nessun cambio di listener, policy o API.
- Nove test di lifecycle aggiunti: timeout assente/zero/NaN, abort prima e
  durante fetch, confine della deadline, errore rete e body ritardato sulle
  risposte 200/403. Passano prima della slice, coverage core 100%.
- Slice: cleanup del timer una sola volta in finally; guardia controller
  sufficiente per schedulare il timeout gia truthy. Nessun helper nuovo.
- Dopo: request cognitiva `28 -> 24`, ciclomatica `22 -> 20`, LOC `62 -> 60`,
  nesting `2` invariato; file cognitiva `147 -> 143`, ciclomatica `100 -> 98`,
  LOC `209 -> 207`, 16 callable invariati. Error `4 -> 3`, warning `10 -> 11`:
  request scende sotto la soglia error cognitiva; resta error ciclomatica.
  Nessun debito trasferito: `IMPROVED`.
- Prima/dopo della slice: 842 test API verdi su 15 suite; core full-file
  100% statement (`118/118`), branch (`101/101`), funzioni (`16/16`) e linee
  (`117/117`) dopo. Nessun test rimosso o esclusione aggiunta.
- Ratchet mirato contro lo stesso merge-base: PASS, `findings: []`;
  `make quality-test QUALITY_PYTHON=backend/.venv/bin/python`: 83 passati.
  ESLint runtime/test, typecheck senza incremental e diff whitespace passati.
  Baseline, scope, eccezioni e modifiche non correlate preservati; diff della
  baseline nullo. `make complexity-baseline-verify` restituisce ancora
  `false` sul checkout modificato; nessuna conformita globale dichiarata.
- Graphify frontend aggiornato tramite target dedicato: 7.244 nodi e
  17.450 archi. Refresh platform docs tramite `make graphify-platform-docs`;
  chunk semantico fallito per `Connection error` con warning di risultati
  parziali, pur con exit 0. Arricchimento docs non verificato nell'ambiente
  a rete limitata; il grafo codice e aggiornato, nessun refresh docs completo
  dichiarato.
- Evidenze `/tmp/gaia-api-timeout-{before,after}.json`,
  `/tmp/gaia-api-timeout-characterization.log`,
  `/tmp/gaia-api-timeout-tests-after.log`, directory
  `/tmp/gaia-api-timeout-after-coverage` e log ratchet/lint/types/quality/
  Graphify con lo stesso prefisso. Nessuna failure applicativa o tooling.
- Iterazione chiusa su una sola slice. Debito residuo: request mantiene
  ciclomatica error `20`, cognitiva warning `24` e LOC warning `60`;
  eventuale semplificazione dei risultati vuoti richiede una nuova slice.
  Nessun commit, push o secondo hotspot.

### API core - decodifica errori HTTP (2026-10-02)

- Hotspot unico autorizzato: `request` in `frontend/src/lib/api/core.ts`,
  checkout `main@af768d77`; Organigramma e giornaliere riservati agli altri
  team. File runtime inizialmente pulito, modifiche concorrenti preservate.
- Prima: request cognitiva `54`, ciclomatica `30`, LOC `82`, nesting `4`;
  file 15 callable, cognitiva aggregata `155`, ciclomatica `99`, LOC `206`,
  cinque error e nove warning. Ratchet mirato contro `origin/main`,
  merge-base `6b61fd27`: PASS, nessun finding.
- Invarianti: stessi messaggi, status e detailData di ApiError; priorita
  stringa/message/JSON/default e fallback statusText solo su eccezione;
  fetch, header, token, timeout, abort, cleanup e risposte valide invariati.
  Slice: decodifica della risposta HTTP non-2xx in un helper privato;
  nessun riuso nei decoder Blob/XHR, che hanno contratti distinti.
- Caratterizzazione iniziale: quattro suite API, 420 test verdi, coverage
  full-file 100% (119 statement, 105 branch, 15 funzioni, 118 linee).
  Aggiunti 18 casi su dettagli falsy/strutturati, messaggi vuoti, JSON
  invalido/null, fallback e conservazione del detailData su stringify fallito.
- Dopo: request cognitiva `28`, ciclomatica `22`, LOC `62`, nesting `2`;
  helper privato `readResponseError` a `18/9/23/3`, sotto le soglie error.
  Aggregati file: cognitiva `155 -> 147`, ciclomatica `99 -> 100`,
  callable `15 -> 16`, LOC `206 -> 209`; error `5 -> 4`, warning `9 -> 10`.
  L'aumento ciclomatico e il punto base del nuovo callable: decisioni
  normalizzate invariate `84 -> 84`. Riduzione cognitiva reale senza
  trasferimento di violation error-level: `IMPROVED`.
- Prima della slice: 438 test verdi con la caratterizzazione aggiunta.
  Dopo: stessi 438 test verdi; regressione estesa dei client API `833 passed`
  su 15 suite. Core full-file al 100% statement (`120/120`), branch
  (`105/105`), funzioni (`16/16`) e linee (`119/119`). Nessuna esclusione
  coverage o test indebolito; i decoder Blob/XHR restano invariati.
- Ratchet mirato dopo contro lo stesso merge-base: PASS, `findings: []`.
  ESLint runtime/test, typecheck senza incremental, diff whitespace e
  `make quality-test QUALITY_PYTHON=backend/.venv/bin/python` (83 test)
  passati. Baseline, scope ed eccezioni invariati; nessuna sincronizzazione
  globale sul checkout concorrente o dichiarazione di conformita globale.
  `make complexity-baseline-verify` restituisce `false`, come nel controllo
  precedente del checkout modificato; diff della baseline nullo.
- Graphify frontend aggiornato (7.236 nodi, 17.418 archi); patch locale
  `OPENAI_BASE_URL` verificata gia presente senza modificare l'installazione.
  Refresh documentale tramite target dedicato `make graphify-platform-docs`
  tentato: `chunk 1/1 failed: Connection error` e warning di risultati
  parziali, pur con exit 0. Arricchimento semantico docs non verificato
  nell'ambiente a rete limitata; non conteggiato come refresh riuscito.
- Evidenze: `/tmp/gaia-api-request-{before,after}.json`,
  `/tmp/gaia-api-request-characterization.log`,
  `/tmp/gaia-api-request-regression.log`, directory
  `/tmp/gaia-api-request-regression-coverage`,
  `/tmp/gaia-api-request-ratchet-after.log` e log lint/types/quality/Graphify
  con lo stesso prefisso. Nessuna failure applicativa o nel tooling.
- Debito residuo: request conserva error cognitive/cyclomatic e warning LOC;
  il nuovo decoder ha solo un warning cognitive. Iterazione chiusa su una
  responsabilita; eventuale semplificazione successiva di timeout/abort
  richiede una nuova slice. Nessun commit, push o secondo hotspot.

### Network - URL amministrazione dispositivi (2026-10-01)

- Hotspot unico: `getNetworkDeviceAdminUrl` in
  `frontend/src/lib/network-device-utils.ts`, checkout `main@af768d77`.
  Organigramma e giornaliere affidati agli altri team; modifiche concorrenti
  preservate. Orientamento e impatto verificati con Graphify frontend.
- Invarianti: target assoluto HTTP/HTTPS prioritario; path relativo usa HTTPS
  solo con prefisso metadata `https:`; poi sorgente HTTP valida, porta 443,
  porta 80, infine null. Casing, porte, path, assenza di mutazioni e helper
  distinti invariati. Target assente normalizzato a stringa vuota e rami
  appiattiti; nessun nuovo callable o contratto.
- Prima/dopo: cognitiva `22 -> 18`, ciclomatica `12 -> 12`, LOC callable
  `28 -> 24`, nesting `3 -> 2`. File: cognitiva aggregata `48 -> 44`,
  ciclomatica `39 -> 39`, LOC `84 -> 80`, nove callable invariati.
  Esito `IMPROVED` sulla cognitiva, senza trasferimento del debito.
  Restano due warning sul resolver, zero error.
- Caratterizzazione prima della modifica: 30 test passati, compresi 20 casi
  aggiunti su precedenza, casing, metadata assenti/malformati, porte esatte e
  immutabilita. Dopo: stessi 30 test verdi; coverage full-file 100% statement
  (`43/43`), branch (`54/54`), funzioni (`9/9`) e linee (`43/43`).
- Ratchet mirato autorevole contro `origin/main`, merge-base `6b61fd27`:
  PASS prima e dopo, `findings: []`. ESLint runtime/test e typecheck senza
  incremental passati. Baseline, scope ed eccezioni non modificati;
  nessuna sincronizzazione globale sul checkout concorrente.
- Quality tooling: `make quality-test QUALITY_PYTHON=backend/.venv/bin/python`
  passa con 83 test; diff whitespace mirato pulito. `baseline-verify`
  globale restituisce `false` sul runtime modificato, senza aggiornamenti
  della baseline per assorbire il checkout concorrente. Nessuna failure
  nei test o nel ratchet mirati; conformita globale non dichiarata.
- Graphify frontend aggiornato tramite `make graphify-frontend` (7.233 nodi,
  17.414 archi); patch `OPENAI_BASE_URL` verificata gia applicata. Refresh
  documentale con il target dedicato `make graphify-platform-docs` e modello
  `gpt-reserve`: `chunk 1/1 done`, nessun warning di chunk semantico fallito;
  artefatti dei grafi non versionati.
- Evidenze: `/tmp/gaia-network-url-{before,after}.json`,
  `/tmp/gaia-network-url-characterization.log`,
  `/tmp/gaia-network-url-tests-after.log`,
  `/tmp/gaia-network-url-after-coverage/coverage-final.json` e
  `/tmp/gaia-network-url-ratchet-after.log`.
- Iterazione delimitata al resolver; prossima azione separata: selezionare
  una responsabilita con caratterizzazione disponibile fuori dai perimetri
  Organigramma e giornaliere. Nessun commit o secondo hotspot.

### Poste Online - aggregazione contatori import worker (2026-09-28)

- Hotspot unico: `_persist_scrape_payload` in `posta_online_sync.py`, nella
  change Poste non ancora committata. Invarianti: identici sei contatori nel
  `result_json`, valori `None` trattati come zero, stesso ordine di import,
  stato, checkpoint e commit. Caratterizzati due batch con contatori misti.
- Prima: callable ciclomatica `59`, cognitiva `61`, LOC `66`; file LOC `503`,
  somme ciclomatica `194`, cognitiva `226`, 18 callable. Dopo: callable
  `45/47/65`; file `502/180/212`, 18 callable. Nessuna violation spostata o
  introdotta: `IMPROVED` sulla metrica obiettivo e sugli aggregati.
- 39 test worker mirati passati; coverage di `posta_online_sync.py` 100%
  statement e branch (`311/311`, `70/70`); Ruff dei due file toccati passato.
  Ratchet mirato contro `HEAD` ancora rosso con 12 finding nel file, ma i
  valori di questo callable sono diminuiti. Baseline ed eccezioni invariate,
  diff baseline nullo. Prossima azione separata: una slice sul workflow di
  ripresa o persistenza restante, non una baseline che assorba il debito.

### Catasto - caratterizzazione AnagraficaBulkPanel (2026-09-28)

- Audit separato del ratchet residuo: la baseline letta al merge-base
  `c42bea84` dichiara `source_commit=b1d4a988` (2026-08-20), precedente ai
  commit Catasto `4cccd69a` e `97a32f18`. Il codice `HEAD` non modificato
  ha gia il primo `useEffect` a `8/9/33` e il file a LOC `1118`; il working
  tree misura rispettivamente `8/9/33` e `1103`. Anche il callback storico
  e le righe export segnalate sono presenti in `HEAD`: i 15 finding confrontano
  funzionalita gia integrate con una baseline non sincronizzata, non una
  regressione di questa slice. Nessun codice o baseline cambiati in questo
  audit. Esito `NO_SAFE_CHANGE`: una riduzione artificiale fino alla baseline
  di agosto violerebbe l'invariante UI; serve una decisione separata sulla
  riconciliazione della baseline storica secondo la policy del ratchet.
- Iterazione hotspot successiva: caratterizzati tutti i rami eseguibili con 40
  test mirati e coverage `100%` statement/branch/funzioni/linee
  (`387/374/90/334`). Rimossi controlli UI irraggiungibili e la fase `saving`
  mai assegnata; unificato il rendering degli export distretti/comuni senza
  toccare creazione, polling o download dei job.
- Metriche prima della slice export: componente principale ciclomatica `191`,
  cognitiva `217`; file LOC `1104`, somme ciclomatica `497`, cognitiva `503`.
  Dopo: componente `155/181`; file LOC `1103`, somme `479/484`. La sezione
  condivisa e a `14/13/74` (warning, nessun errore) e lo spinner a `1/0/8`:
  riduzione aggregata senza trasferimento di errori, esito `IMPROVED`.
- Typecheck e 40 test mirati verdi; ESLint senza errori, con un warning hook
  preesistente. Ratchet contro `origin/main` (`c42bea84`) ancora rosso con
  15 finding nel pannello, dovuti a callback/LOC delle feature gia presenti
  prima della slice; baseline ed eccezioni non aggiornate. Prossima azione:
  trattare separatamente quelle regressioni, senza allargare questa iterazione.
- Hotspot selezionato: `AnagraficaBulkPanel` dopo il commit export multi-scope
  `97a32f18`; base di confronto `5915305d`. Nessun file runtime modificato:
  la copertura iniziale impediva un refactoring conforme alla policy GAIA.
- Prima e dopo (invariati): callable principale ciclomatica `201`, cognitiva
  `232`, LOC `955`; file LOC `1118`, ciclomatica aggregata `518`, cognitiva
  aggregata `537`. Il ratchet conserva 13 finding nel file rispetto alla base.
- Aggiunta una suite di caratterizzazione per upload CSV/XLSX, validazione
  intestazioni, esecuzione e polling job, export veloce, storico, template,
  errori e renderer delle colonne. Con la suite export esistente: 24 test
  mirati passati. Coverage del pannello `39.13/42.11/42.69/40.47%` a
  `93.09/86.93/97.75/96.42%` (statement/branch/funzioni/linee).
- Typecheck frontend ed ESLint del nuovo test passano. La suite frontend
  completa eseguita per orientamento ha 2640 test passati e 10 failure in
  Presenze/Ruolo, non attribuite a questo file. Nessuna baseline o eccezione
  modificata; diff baseline nullo.
- Esito `REORGANIZED_AND_CHARACTERIZED` solo per la copertura e la
  verificabilita, non `IMPROVED`: restano 12 righe e 58 esiti di branch
  scoperti, compresi percorsi di parser, polling, storico e UI. La prossima
  slice deve caratterizzare i rami eseguibili residui e valutare separatamente
  quelli irraggiungibili; non abbassare la policy coverage o spostare il debito
  in un componente adiacente. Nessun refactoring runtime avviato.

### Accessi - lookup utente amministrativo (2026-09-28)

- Hotspot unico: controllo utente esistente/404 ripetuto nei route handler di
  `admin_users.py`; confronto con la baseline del merge-base `5915305d`.
- Invarianti: stessi endpoint, autorizzazioni, `404 User not found`, ordine delle
  verifiche, revoca QGIS e transazioni. Estratto `_get_existing_user` e riusato
  dagli otto handler che duplicavano il lookup.
- Prima: file LOC `272`, ciclomatica aggregata `43`, cognitiva aggregata `30`;
  `delete_user` LOC `12`, `patch_user_modules` ciclomatica `3`, cognitiva `2`,
  LOC `34`. Dopo: file LOC `261`, ciclomatica `37`, cognitiva `23`;
  `delete_user` LOC `10`, `patch_user_modules` ciclomatica `2`, cognitiva `1`,
  LOC `32`. Il nuovo helper e sotto soglia (`2/1/5`), senza debt transfer:
  `IMPROVED`.
- Test `test_user_management`, `test_gis_platform_api` e
  `test_gis_qgis_desktop_access` passano prima e dopo; coverage del file
  modificato `100%` statement e branch (dopo: 107/107 e 18/18).
  Ruff `check` passa; il format-check completo rileva solo layout legacy
  estraneo alla slice. Ratchet mirato al file contro `5915305d`: zero finding.
  Baseline ed eccezioni invariate; diff baseline nullo.
- Debito residuo: la violation legacy sui 13 parametri di
  `patch_user_modules` resta invariata. Il ratchet globale non e attribuibile
  a questa slice per le modifiche Catasto, GIS, Poste/Ruolo e worker concorrenti.
  Nessun secondo hotspot avviato.

### Poste Online - validazione tabella destinatario (2026-09-24)

- Hotspot unico: `_has_registered_mail_detail_table` nel client worker Poste;
  merge-base autorevole `5e4f57187f24ad2097ed36a627cec4d0732bea96`.
- Prima: ciclomatica `9`, cognitiva `12`, LOC `9`, nesting `2`; file con 39
  callable, somma ciclomatica `205`, cognitiva `267`, LOC `577`.
- Invarianti: la prima tabella `id=destinatario` valida il dettaglio solo se
  contiene una riga con almeno quattro celle, seconda cella diversa da
  `servizio` e nome/indirizzo non vuoti; HTML entity e tag interni mantenuti.
  Test `test_posta_online_client.py` caratterizzano il parser e il fetch.
- Slice: scansione lazy delle righe tramite `any`, senza nuovo helper o
  modifica del contratto di `fetch_detail_html`; caratterizzata anche la
  riga intestazione seguita da un destinatario valido.
- Dopo: ciclomatica `8`, cognitiva `7`, LOC `9`, nesting `1`; file con 39
  callable, somma ciclomatica `204` (-1), cognitiva `262` (-5), LOC `577`
  (invariata). Nessuna violation trasferita: `IMPROVED`.
- Verifiche: 20 test client passati; coverage del runtime 100% statement
  (425/425) e branch (130/130); Ruff lint del runtime e `git diff --check`
  passati. Il file di test conserva rilievi Ruff preesistenti. Ratchet del
  client contro il merge-base ancora rosso con 12 finding; questo callable
  resta sopra la baseline `1/0/2/0` con `8/7/9/1`. Baseline ed eccezioni
  invariate, diff baseline nullo. Nessun commit, deploy o avvio del job 9.
- Prossima azione separata: un ulteriore singolo hotspot Poste dal ratchet;
  non trattato in questa iterazione.

### Poste Online - upsert raccomandata, hotspot dedicato (2026-09-24)

- Perimetro unico: `_upsert_posta_online_registered_mail` in
  `backend/app/modules/ruolo/tributi_repositories.py`; base autorevole
  `5e4f57187f24ad2097ed36a627cec4d0732bea96` (`origin/main`).
- Prima: callable ciclomatica `23`, cognitiva `34`, LOC `73`, nesting `4`,
  parametri `5`; file con 177 callable, ciclomatica totale `1206`, cognitiva
  totale `1424`, LOC `3695`. La violation file-level LOC e gia legacy.
- Invarianti: nessun cambio di import, commit/flush, match automatico o
  `preserve_associations`; gli `avviso_ids` della sola associazione manuale
  sono accettati solo se lista, UUID invalidi ignorati, nessun fallback
  aggiunto dall'`avviso_id` principale. Test di caratterizzazione Ruolo/Poste
  gia presenti, incluso ID manuale invalido.
- Slice: appiattito in-place il parsing degli UUID manuali con lo stesso
  trattamento di `TypeError` e `ValueError`, senza nuovi helper.
- Dopo: callable ciclomatica `20`, cognitiva `25`, LOC `72`, nesting `2`,
  parametri `5`; file con 177 callable, ciclomatica totale `1203` (-3),
  cognitiva totale `1415` (-9), LOC `3694` (-1). Nessuna violation trasferita:
  `IMPROVED`, pur restando due violation error-level sul callable.
- Verifiche: suite Poste e Ruolo passata; repository al 100% statement
  (1862/1862) e branch (724/724). Ruff check del runtime passato;
  `git diff --check` passato. Ratchet del file contro il merge-base ancora
  rosso con 19 finding; questo callable e a `20/25/72/2/5` contro
  `10/9/53/1/4` alla base. Baseline ed eccezioni invariate; diff baseline
  nullo. Nessuna failure nuova, commit, deploy o avvio del job 9.
- Prossima azione separata: scegliere un altro singolo hotspot dal ratchet
  Poste; non estendere questa slice all'intero repository Ruolo.

### Poste Online - validazione ID invii, hotspot dedicato (2026-09-24)

- Perimetro unico: `PostaOnlineRegisteredMailSyncJobCreateRequest.validate_payload`
  in `backend/app/modules/elaborazioni/posta_online/schemas.py`; base
  `5e4f57187f24ad2097ed36a627cec4d0732bea96` (`origin/main`).
- Prima: callable ciclomatica `16`, cognitiva `24`, LOC `13`, nesting `2`;
  file con 4 callable, ciclomatica totale `28`, cognitiva totale `35`, LOC `95`.
- Invarianti: annualita normalizzate prima del controllo delay e degli ID;
  `shipment_ids=None` distinto da lista vuota; strip degli ID, almeno quattro
  cifre secondo `str.isdigit`, univocita e identico messaggio d'errore.
  Test in `test_elaborazioni_posta_online.py`, integrati con casi vuoto/corto.
- Slice: estratta solo la normalizzazione pura degli ID, chiamata nello stesso
  punto del model validator; caratterizzati anche input vuoto e ID corto.
- Dopo: `validate_payload` ciclomatica `8`, cognitiva `8`, LOC `10`, nesting
  `1`; `_normalize_shipment_ids` `9/11/9/1`, sotto soglia error-level. File
  con 5 callable, ciclomatica totale `29` (+1), cognitiva totale `30` (-5),
  LOC `101` (+6). La violation error-level del callable principale e rimossa;
  la cognitiva aggregata cala senza trasferire violation: `IMPROVED`, con
  lieve aumento ciclomatico aggregato esplicitamente visibile.
- Verifiche: test di caratterizzazione passato prima della modifica; suite
  Poste passata dopo, coverage dello schema 100% statement (97/97) e branch
  (14/14). Ruff check di schema e relativo test passato; `git diff --check`
  passato. Ratchet dello schema contro il merge-base ancora rosso con tre
  finding (`8/8/10` contro `7/7/8`). Il format check dell'intero schema
  resta rosso per righe legacy non riformattate; il nuovo helper e formattato.
  Baseline ed eccezioni invariate, diff baseline nullo.
- Debito residuo: tre finding dello schema e gli altri hotspot della feature
  Poste; nessun commit, deploy o avvio del job 9. Prossima azione separata:
  selezionare un solo ulteriore hotspot dal ratchet complessivo.

### Poste Online - retry HTTP, hotspot dedicato (2026-09-24)

- Perimetro unico: `PostaOnlineBrowserClient._request_with_backoff` in
  `modules/elaborazioni/worker/posta_online_client.py`; base autorevole
  `5e4f57187f24ad2097ed36a627cec4d0732bea96` (`origin/main`).
- Prima: callable ciclomatica `11`, cognitiva `20`, LOC `22`, nesting `4`;
  file con 39 callable, ciclomatica totale `208`, cognitiva totale `271`,
  LOC `582`.
- Invarianti: `max_retries + 1` tentativi, retry soltanto per timeout/429/5xx
  previsti, `Retry-After` invariato, stesso tipo e testo degli errori,
  chaining dell'ultimo timeout, nessuna richiesta aggiuntiva. Test esistenti
  in `test_posta_online_client.py` e `test_posta_online_client_branch_closure.py`.
- Slice: appiattiti i rami con uscita immediata per errori terminali; nessun
  nuovo helper o cambio di politica di retry.
- Dopo: callable ciclomatica `8`, cognitiva `16`, LOC `17`, nesting `4`;
  file con 39 callable, ciclomatica totale `205` (-3), cognitiva totale
  `267` (-4), LOC `577` (-5). Nessuna violation trasferita: `IMPROVED`.
- Verifiche: 20 test client passati, coverage del file 100% statement
  (429/429) e branch (134/134); Ruff check del file passato. Ratchet del
  solo client contro il merge-base ancora rosso con 12 finding, di cui
  questo callable resta a `8/16/17/4` contro `7/9/13/2` alla base.
  Baseline ed eccezioni invariate; diff baseline nullo. I 64 finding della
  feature complessiva e il gate di stile restano da risolvere in iterazioni
  separate. Nessun commit, deploy o avvio del job 9.
- Prossima azione separata: selezionare un ulteriore singolo hotspot Poste
  dal ratchet, poi ripetere coverage e confronto autorevole.

### Poste Online - gate di rilascio (2026-09-24)

- `make test-worker` passato: 100% statement/branch su client Poste, sync e
  `worker.py`; totale worker 99% per due file SISTER estranei.
- Suite backend Poste e Ruolo passate: 100% statement/branch sui tre runtime
  backend modificati, dopo due casi di test aggiunti per il job senza
  credenziale esplicita e la raccomandata associata a un avviso diverso.
  Per il run combinato si precarica il `pypdf` reale: gli stub delle suite
  collidono se Pytest le colleziona senza preload.
- Workspace Poste frontend: 12 test passati, 100% statement/branch/funzioni/
  righe; typecheck passato. `git diff --check` passato.
- Stop: ratchet mirato dei sette runtime Poste contro `origin/main` con 64
  finding; `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python` con 52
  rilievi Ruff sui file cambiati. Non sono stati aggiornati baseline o
  eccezioni. Il checkout include inoltre una modifica Catasto estranea:
  nessun commit o deploy finche i gate non sono conformi e il rilascio non
  isola la change Poste. Il job CED 9 resta inattivo.

### Poste Online - persistenza scrape, hotspot dedicato (2026-09-24)

- Perimetro unico: `_persist_scrape_payload` in `modules/elaborazioni/worker/posta_online_sync.py`.
  Base autorevole `5e4f57187f24ad2097ed36a627cec4d0732bea96` (`origin/main`);
  worktree Poste gia modificato e modifica Catasto estranea preservati.
- Prima: callable ciclomatica `75`, cognitiva `86`, LOC `101`, parametri `7`;
  file con 15 callable, somma ciclomatica `191`, somma cognitiva `229`, LOC `496`.
- Invarianti: import dei dettagli in batch da 25 con commit per batch; contatti
  importati solo quando mancano dettagli e `include_details` e falso; errori
  di import fail-hard; conteggi, checkpoint, round, cooldown, status e formato
  del risultato invariati; nessuna modifica ad associazioni, API o schema.
- Test di caratterizzazione esistenti: `test_posta_online_sync_branch_closure.py`
  e `test_worker.py`; slice prevista: separare import transazionale
  e calcolo degli ID ancora da recuperare dalla finalizzazione del job.
- Dopo: `_persist_scrape_payload` ciclomatica `59`, cognitiva `61`, LOC `66`;
  i tre helper di import dettagli, import contatti e ID residui sono sotto
  soglia error-level. File: 18 callable, ciclomatica totale `194` (+3),
  cognitiva totale `226` (-3), LOC `503` (+7). Riduzione reale della metrica
  cognitiva senza trasferire violation error-level: `IMPROVED`, pur con il
  piccolo aumento ciclomatico aggregato esplicitamente visibile.
- Verifiche: 37 test worker mirati passati; coverage `posta_online_sync.py`
  100% statement (310/310) e branch (70/70); `make quality-test`: 76 passed;
  Ruff lint sul file passato. Il format check del file non passa per molte
  righe preesistenti non formattate; non e stato eseguito un format di massa.
  `git diff --check` passato. Ratchet del file contro `origin/main` ancora
  rosso per regressioni della feature Poste rispetto al merge-base, incluso
  questo callable (`14/13/46` alla base), e non attribuibile alla sola slice.
  Nessuna baseline o eccezione aggiornata; diff baseline nullo.
- Graphify worker code aggiornato; Graphify platform docs completato con
  `chunk 1/1 done` e senza warning semantici.
- Debito residuo: funzione principale ancora sopra soglia ciclomatica e
  cognitiva, piu altri finding Poste e modifica Catasto estranea nel worktree.
  Prossima azione separata: affrontare un solo ulteriore hotspot Poste dopo
  review di questa slice e ripetere il ratchet complessivo.

### Verifica integrata QGIS Desktop e gestione utenti (2026-09-23)

- Backend: quattro suite GIS/Accessi passano; gli otto file runtime misurati
  (`admin_users`, `qgis_desktop_access`, `qgis_governance`, `qgis_project`,
  `qgis_server_bootstrap`, `services`, `application_user`, `schemas/users`)
  hanno 100% statement e branch: 1758 statement e 470 branch coperti.
- Frontend: il run mirato passa con 59 test, ma non copre da solo tutto il
  client condiviso `platform.ts`. Il run esteso, escludendo quattro suite
  estranee a QGIS fallite nel run completo, passa con 2562 test e raggiunge
  100% statement, branch, funzioni e linee sui tre runtime in scope:
  `gaia/users/page.tsx`, `user-qgis-desktop-access-panel.tsx`, `platform.ts`.
  `types/api/platform.ts` e escluso dal gate runtime come file di tipi.
- Il run frontend completo non e verde: 14 failure in quattro suite
  (`elaborazioni-settings-sister`, `presenze-giornaliere-page`,
  `registered-mails-console`, `ruolo-tributi-placeholder-pages`). Non sono
  state modificate o disabilitate nei file di test. Nessun deployment o commit
  eseguito in questa verifica.

### QGIS project XML - separazione dei maplayer (2026-09-23)

- Hotspot unico: `build_xml` in `qgis_project.py`. Slice: estratta in
  `_append_map_layer` la costruzione completa di ciascun `<maplayer>`, senza
  cambiare ordine degli elementi, chiamate al datasource o opzioni PostGIS/WMS.
- Prima: `build_xml` ciclomatica `14`, cognitiva `21`, LOC `93` (violation LOC
  error-level). Dopo: ciclomatica `5`, cognitiva `6`, LOC `65`; il nuovo helper
  ha ciclomatica `10`, cognitiva `9`, LOC `35` e nessuna violation error-level.
  Aggregati del file: cognitiva `69 -> 63`, ciclomatica `74 -> 75`, LOC
  `275 -> 280`; il leggero aumento ciclomatico aggregato resta visibile.
  Obiettivo cognitivo e LOC migliorati senza trasferire violation: `IMPROVED`.
- Verifiche: test GIS piattaforma e bootstrap QGIS Server passano; coverage di
  `qgis_project.py` 100% statement e branch (104 statement, 18 branch). Ruff
  lint e format passano; `make quality-test`: 76 passed. Graphify backend
  aggiornato e Graphify platform docs: `chunk 1/1 done`, senza warning
  semantici. Ratchet mirato contro il merge-base di `origin/main`
  senza finding; ratchet globale ancora rosso per regressioni in altri file
  Accessi, Catasto, GIS services e frontend. Nessuna baseline aggiornata.
- Prossima azione separata: risolvere i finding globali per singolo hotspot,
  senza estendere questa slice.

### QGIS PostGIS datasource - separazione connessione e tabella (2026-09-23)

- Singolo callable selezionato dal ratchet nel generatore di progetto QGIS:
  `_postgis_datasource`. Invarianti: precedenza tra view `gis_qgis` e tabella
  sorgente, fallback di schema/tabella/geometria/chiave/SRID e identica sintassi
  della connessione host/porta/database o `service`.
- Prima: ciclomatica `16` (nuova violation error-level). Separati il riferimento
  alla tabella governata/sorgente (`_postgis_table_reference`) e il descrittore
  di connessione (`_postgres_connection`) dal formatter del datasource.
- Dopo: `_postgis_datasource` ciclomatica `9`, cognitiva `8`, LOC `17`;
  helper rispettivamente ciclomatica `6`/LOC `7` e `2`/LOC `7`, senza violation.
  L'aggregato ciclomatico dei tre callable e `17`, contro `16` prima: esito
  `REORGANIZED_AND_CHARACTERIZED`, non `IMPROVED`. La violation error-level di
  `qgis_project.py` ora e solo `build_xml` (LOC `93`), non trattata in questa
  slice.
- Verifiche: suite GIS piattaforma e bootstrap QGIS Server passano; il runtime
  `qgis_project.py` raggiunge 100% statement/branch/linee/funzioni. Ruff passa.
  Ratchet mirato al file non ha rilievi su `_postgis_datasource`, ma resta rosso
  per `build_xml`; nessuna baseline o eccezione aggiornata. Graphify backend da
  aggiornare dopo la slice verificata.
- Prossima azione separata: hotspot `_build_qgis_project_xml` / `build_xml`;
  mantenere fuori scope le modifiche concorrenti Catasto/worker.

### QGIS Desktop access panel - separazione stato e presentazione (2026-09-23)

- Hotspot unico selezionato dal ratchet: `UserQgisDesktopAccessPanel` nel
  pannello di abilitazione QGIS. Baseline del confronto `origin/main`, merge-
  base `1b13ed03a4151426e2de640c0bc8e54ede833fd8`; modifiche concorrenti
  Catasto e worker preservate.
- Prima: callable a ciclomatica `20` e `140` LOC, entrambe oltre soglia
  error-level. Slice: separati hook di stato/API, badge, azioni e presentazione
  delle credenziali monouso; invariati autorizzazioni UI, conferma revoca,
  rotazione, errori, cancellazione degli effetti obsoleti e password mostrata
  una sola volta.
- Dopo: callable principale a ciclomatica `9`, cognitiva `8`; nessuna
  violation error-level nel file. `useQgisDesktopAccess` resta a `74` LOC,
  warning sotto la soglia error-level di `80`; il file ha 16 callable,
  ciclomatica massima `9`, cognitiva massima `8` e 46 punti ciclomatici
  aggregati. Non essendo dimostrata una riduzione dell'aggregato, esito
  `REORGANIZED_AND_CHARACTERIZED`, non `IMPROVED`.
- Verifiche: test pannello `10 passed`, coverage file 100% (60 statement,
  36 branch, 16 funzioni, 56 righe); typecheck frontend passato. Graphify
  frontend aggiornato. Nessuna baseline o eccezione modificata.
- Il ratchet globale resta non verde per callable nuovi sopra soglia in
  `backend/app/modules/gis/qgis_project.py`, regressioni in handler/repository
  e pagina utenti, oltre a rilievi Catasto concorrenti. Il ratchet mirato al
  path segnala `ambiguous_fingerprint` su `Program<anonymous>` e non viene
  usato come prova. Nessun ulteriore hotspot avviato in questa iterazione.
- Prossima azione separata: selezionare un singolo hotspot di generazione
  progetto QGIS (`_postgis_datasource` / `build_xml`), poi ripetere il ratchet
  completo distinguendo i rilievi concorrenti.

## Stato generale

### Verifica finale e commit delle slice frontend (2026-09-22)

- Commit esplicitamente richiesto dopo le cinque iterazioni descritte sotto;
  nessun nuovo hotspot. Base verificata `cb09f4f4`.
- Scope del commit: quattro runtime (`activity-center.tsx`, `guided-workflow.ts`,
  `document-preview.ts`, `request-support-payload.ts`), quattro file di test e
  i due registri code-quality. Modifiche concorrenti Utenze/worker/config/docs
  escluse; nessun aggiornamento baseline, soglie, esclusioni o configurazione test.
- Esecuzione combinata: otto suite e `97 passed`, con
  `VITEST_COVERAGE_INCLUDE` limitato ai quattro runtime e
  `--coverage.thresholds.perFile`. Ogni file raggiunge 100% statement, branch,
  funzioni e righe, verificato anche dal JSON Istanbul (non solo dalla media).
  Totale: 209/209 statement, 215/215 branch, 45/45 funzioni, 171/171 righe.
  Log `/tmp/gaia-quality-final-tests.log`, report
  `/tmp/gaia-quality-final-coverage/coverage-final.json`.
- Typecheck frontend senza incremental, lint sugli otto file runtime/test,
  diff whitespace e tutti i 76 test del quality tooling: passano.
- Ratchet autorevole sui quattro runtime contro `origin/main`, merge-base
  `cb09f4f4`: `findings: []`. Report finale: 45 callable, zero error e otto
  warning legacy residui. Metriche prima/dopo e classificazioni delle singole
  slice restano quelle documentate sotto, incluso `NO_SAFE_CHANGE`.
- Il ratchet dell'intero working tree rileva cinque regressioni nelle sole
  modifiche concorrenti `modules/elaborazioni/worker/worker.py`; nessuna nel
  perimetro del commit. Baseline verify `false`: sincronizzazione non tentata,
  non viene dichiarata conformita globale del repository.
- Smoke frontend (`npm test`): 13 passati, cinque falliti. Riprodotti gli
  stessi cinque fallimenti su un archivio Git isolato di `cb09f4f4` in
  `/tmp/gaia-quality-base-aYyptA`, senza modifiche o dipendenze del working tree.
  Evidenze `/tmp/gaia-quality-{final,base}-smoke.log`; nessun test indebolito.
- Altri log `/tmp/gaia-quality-final-{types,lint,tooling,ratchet,global-ratchet,baseline-verify}.log`;
  metriche `/tmp/gaia-quality-final-metrics.json`.
- Graphify frontend aggiornato con target dedicato (topologia invariata).
  Refresh platform docs tramite `make graphify-platform-docs`, log
  `/tmp/gaia-quality-final-graphify-docs.log`; grafi e report temporanei non
  inclusi nel commit. Build production ed E2E browser non eseguiti.
- Pubblicazione remota non richiesta: solo commit locale, nessun push.

### Wiki request payload - campi comuni (2026-09-22)

- Unico hotspot autorizzato: `buildWikiRequestPayload`, base `cb09f4f4`;
  modifiche precedenti e concorrenti preservate. Slice: costruire una sola
  volta i campi comuni ai tre intent, senza nuovi helper o cambio di contratto.
- Invarianti: ultima domanda utente trimata senza mutare messages, mapping
  pathname, source channel, fallback nullish (stringa vuota preservata),
  campi specifici e assenza di campi estranei per ogni intent, link supporto.
- Prima: cognitive `13`, cyclomatic `10`, LOC `61`. La suite esistente ha
  tre test verdi ma coverage file incompleta (statement 68,96%, branch 51,61%).
  Aggiunta suite payload/URL/mapping; corretto un errore nella forma delle
  fixture test.each (array espansi anziche passati come singolo argomento),
  nessuna failure runtime nuova. Prima del refactoring: 27 test passati e
  coverage full-file 100% (58 statement, 62 branch, 5 funzioni, 37 righe).
- Dopo: cognitive `13 -> 5`, cyclomatic `10 -> 6`, LOC `61 -> 49`;
  nessuna violation sul callable. Aggregati file: cognitive `35 -> 27`,
  cyclomatic `36 -> 32`, LOC `116 -> 104`, cinque callable invariati.
  Warning file `4 -> 2`, sui distinti mapping pathname e URL supporto.
  Esito `IMPROVED`, senza estrazioni o trasferimento del debito.
- Verifiche finali: 27 test passati, coverage 100% (58 statement, 54 branch,
  5 funzioni, 37 righe), lint runtime/test e typecheck senza incremental verdi;
  quality tooling 76 test passati. Diff whitespace pulito.
- Ratchet mirato autorevole sul runtime, `--base-ref origin/main`: verde.
  Globale: stessi cinque rilievi concorrenti in `worker.py`, nessuno wiki;
  baseline verify `false`. Baseline, scope, soglie ed eccezioni invariate.
- Evidenze `/tmp/gaia-wiki-payload-{before,after}.json`,
  `/tmp/gaia-wiki-payload-after-coverage`,
  `/tmp/gaia-wiki-payload-{ratchet,global-ratchet,baseline-verify,quality-tests}.log`.
- Graphify frontend aggiornato tramite target dedicato; refresh platform docs
  con log `/tmp/gaia-wiki-payload-graphify-docs.log`. Grafi non versionati.
  Build production ed E2E non eseguiti. Nessun commit o secondo hotspot.
- Prossima azione separata: valutare un altro hotspot; i due warning residui
  del file non sono autorizzazione ad ampliare automaticamente questa slice.

### Document preview - normalizzazione estensione (2026-09-22)

- Successivo hotspot autorizzato dopo `guidedChangeValidation`, il cui esito
  `NO_SAFE_CHANGE` rimane tracciato qui e nel backlog; non viene riaperto.
- Base `main@cb09f4f4`; modifiche GIS precedenti e concorrenti Utenze/worker
  preservate. Scope: `frontend/src/lib/document-preview.ts`, relativo test.
- Target `getDocumentPreviewKind`: prima cognitive `15`, cyclomatic `12`,
  LOC `23`, due warning. Tre controlli null ripetuti prima dei Set.
- Slice: normalizzare l'assenza di estensione a stringa vuota, gia classificata
  come download, eliminando i tre guard ridondanti. Nessun nuovo helper.
  Invarianti: flag PDF prioritario, estensione esplicita anche vuota prioritaria
  rispetto al filename, fallback solo nullish, casing e formati invariati.
- Caratterizzazione: tre test iniziali, coverage full-file 100% (18 statement,
  24 branch, 3 funzioni, 18 righe); aggiunti dieci casi di precedenza/nullish.
  Tutti i 13 test passano anche prima della modifica runtime.
- Dopo: cognitive `15 -> 9`, cyclomatic `12 -> 9`, LOC `23 -> 23`;
  warning `2 -> 0`, nessuna violation residua nel file. Aggregati file:
  cognitive `16 -> 10`, cyclomatic `15 -> 12`, LOC `34` e tre callable
  invariati. Esito `IMPROVED`, senza debito trasferito.
- Verifiche: 13 test passati; coverage full-file 100% su 18 statement,
  18 branch, tre funzioni e 18 righe. Typecheck senza incremental e lint
  runtime/test verdi. Ratchet mirato contro merge-base `origin/main` verde.
- Report `/tmp/gaia-preview-{before,after}.json`, coverage
  `/tmp/gaia-preview-after-coverage`, ratchet `/tmp/gaia-preview-ratchet.log`.
  Baseline, scope e soglie invariati. Build production ed E2E non eseguiti.
  Nessun commit o secondo hotspot in questa iterazione.
- Quality tooling: 76 test passati. Ratchet globale contro `cb09f4f4`: cinque
  rilievi nelle modifiche concorrenti `worker.py`, su `_solve_llm_captcha`
  (LOC) e `_solve_external_captcha` (cyc/cog/LOC/nesting); nessuno riguarda
  document-preview. Nessun intervento sul worker. Baseline verify `false`,
  nessuna sincronizzazione tentata. Evidenze
  `/tmp/gaia-preview-{global-ratchet,baseline-verify,quality-tests}.log`.
- Graphify frontend rieseguito: topologia invariata. Refresh platform docs
  tramite target dedicato, log `/tmp/gaia-preview-graphify-docs.log`;
  grafi non versionati. Diff whitespace pulito.
- Prossima azione: selezionare un nuovo hotspot indipendente; non riaprire
  automaticamente la validazione GIS gia caratterizzata senza riduzione.

### GIS guided validation - caratterizzazione e stop (2026-09-22)

- Follow-up esplicito su `guidedChangeValidation`, base `main@cb09f4f4`.
  Preservati i diff GIS delle due slice precedenti; nessun runtime modificato
  da questa iterazione.
- Verificati i guard esistenti: elemento, motivazione, attributi/dati
  descrittivi, coordinate. I controlli specifici hanno condizioni distinte;
  non e stata individuata una semplificazione locale convincente senza
  spostare logica in helper o complicare il flusso. Nessun tentativo di
  normalizzare diversamente i campi per abbassare le metriche.
- Dieci casi aggiunti: precedenza degli errori sui quattro tipi, entrambi i
  campi obbligatori, whitespace, descrizione prima delle coordinate, geometria
  ignorata per attributi/eliminazione e priorita della geometria selezionata.
- Esito `NO_SAFE_CHANGE` per il refactoring proposto; caratterizzazione utile,
  ma nessuna riduzione di complessita rivendicata. Callable invariato a
  cognitive `17`, cyclomatic `12`, LOC `29`; aggregati file cognitive `87`,
  cyclomatic `78`, LOC `231`, 18 callable e quattro warning invariati.
- Verifiche: 33 test helper/composer passati, coverage full-file 100%
  (92 statement, 110 branch, 18 funzioni, 80 righe), lint runtime/test e
  ratchet mirato contro la baseline merge-base di `origin/main` verdi.
  Report `/tmp/gaia-validation-{before,after}.json`, coverage
  `/tmp/gaia-validation-coverage`, ratchet `/tmp/gaia-validation-ratchet.log`.
- Baseline non modificata. Typecheck, build, E2E e gate globali non rieseguiti
  in questa iterazione solo-test. Graphify codice consultato e non rigenerato:
  nessun cambiamento strutturale runtime. Refresh platform docs tramite target
  dedicato, log `/tmp/gaia-validation-graphify-docs.log`.
- Stop: nessun altro hotspot avviato. Prossima decisione: scegliere un
  candidato diverso con duplicazione o annidamento realmente eliminabili.

### GIS coordinate reader - hotspot dedicato (2026-09-22)

- Richiesta: successivo singolo hotspot dopo activity center; base `7ee80d94`.
  Modifiche precedenti e concorrenti preservate.
- Target: `coordinatesFromGeometry` in `frontend/src/app/gis/catalogo/guided-workflow.ts`.
  Prima: cognitive `13`, cyclomatic `11`, LOC `19`; un warning cyclomatic.
- Slice: consolidare i rami identici Polygon/MultiLineString, che leggono
  entrambi il primo gruppo. Nessun helper nuovo, modifica di geometrie,
  validazione, payload, autorizzazioni o UI. Case-insensitivity, primo gruppo,
  fallback nullish e assenza di mutazioni sono invarianti espliciti.
- Caratterizzazione: casi parametrizzati per entrambi i tipi e casing,
  gruppi multipli, primo gruppo vuoto/null, array vuoto e immutabilita.
  I 13 test helper estesi passano prima della modifica runtime; prima della
  caratterizzazione i 19 test helper/composer coprivano il file al 100%.
- Dopo: cognitive `13 -> 10`, cyclomatic `11 -> 9`, LOC `19 -> 17`;
  warning del callable eliminato. Aggregati file: cognitive `90 -> 87`,
  cyclomatic `80 -> 78`, LOC `233 -> 231`, callable invariati `18`.
  Warning file complessivi `5 -> 4`, error `0 -> 0`; nessun debito trasferito.
  Esito `IMPROVED`; gli altri helper restano fuori da questa singola slice.
- Verifiche: 23 test helper/composer, coverage full-file 100% su 92 statement,
  110 branch, 18 funzioni e 80 righe. Typecheck senza incremental, lint sui due
  file frontend e diff whitespace passano. Nessun test indebolito o esclusione.
- Ratchet mirato autorevole: `backend/.venv/bin/python tools/code_quality/complexity.py
  ratchet --base-ref origin/main frontend/src/app/gis/catalogo/guided-workflow.ts`
  passa, `findings: []`, merge-base `3ee0e5ee`. Baseline non modificata.
- Evidenze `/tmp/gaia-coordinate-{before,after}.json`,
  `/tmp/gaia-coordinate-after-coverage`, `/tmp/gaia-coordinate-ratchet.log`.
  Build production ed E2E browser non eseguiti; nessun commit o altro hotspot.
- Quality tooling: `76 passed`. Ratchet globale: stessi due rilievi estranei
  in `xlsm_export.py` della slice precedente, nessuno GIS. Baseline verify
  ancora `false`; nessuna sincronizzazione tentata. Log in
  `/tmp/gaia-coordinate-{global-ratchet,baseline-verify,quality-tests}.log`.
- Graphify frontend aggiornato (7043 nodi, 16958 archi). Refresh documentale
  tramite target platform docs, log `/tmp/gaia-coordinate-graphify-docs.log`;
  gli artefatti dei grafi non sono versionati.
- Prossima azione separata: valutare la validazione del draft guidato,
  preservando precedenza degli errori e controlli specifici del tipo richiesta.

### GIS activity center - hotspot dedicato (2026-09-22)

- Base `main@7ee80d94`; modifiche concorrenti Ruolo/Utenze preservate.
- Unica slice: separare lifecycle di caricamento e vista di
  `frontend/src/app/gis/strumenti/activity-center.tsx` con un hook locale.
- Invarianti: richieste parallele e limite 25, audit opzionale, dipendenze
  reload/token/showAudit, cancellazione risposte obsolete, storico mantenuto
  durante reload/errori, testi, DOM, callback e contratto pubblico invariati.
- Prima: `GisActivityCenter` cognitive `14`, cyclomatic `15`, LOC `95`;
  18 callable, due violation error-level. Cinque test esistenti passano con
  coverage full-file 100% (39 statement, 33 branch, 18 funzioni, 34 righe).
- Aggiunta caratterizzazione del cambio token con risposta obsoleta tardiva.
  Metriche e coverage iniziali in `/tmp/gaia-activity-before*`.
- Dopo: componente cognitive `9`, cyclomatic `10`, LOC `62`; hook locale
  cognitive `5`, cyclomatic `6`, LOC `37`, nessuna violation propria.
  Error-level `2 -> 0`; restano due warning sul componente (cyc e LOC).
- Aggregati file: cognitive sum `29 -> 29`, cyclomatic sum `47 -> 48`,
  callable `18 -> 19`, decision point normalizzati `29 -> 29`, LOC `141 -> 145`.
  Esito `REORGANIZED_AND_CHARACTERIZED`: responsabilita separate e massimi
  ridotti, ma nessuna riduzione complessiva delle decisioni viene rivendicata.
- Il nuovo test passa anche prima dell'estrazione. Dopo: 6 test diretti,
  24 test con workspace strumenti/amministrazione; coverage full-file 100%
  (41 statement, 33 branch, 19 funzioni, 36 righe). Typecheck senza incremental
  e lint dei due file frontend passano; quality tooling `76 passed`.
- Ratchet mirato: `backend/.venv/bin/python tools/code_quality/complexity.py
  ratchet --base-ref origin/main frontend/src/app/gis/strumenti/activity-center.tsx`
  passa con `findings: []`, baseline autorevole merge-base `3ee0e5ee`.
- Evidenze finali `/tmp/gaia-activity-after.json`,
  `/tmp/gaia-activity-after-coverage`, `/tmp/gaia-activity-quality-tests.log`.
  Baseline, soglie ed esclusioni invariate; nessun commit o secondo hotspot.
- Graphify frontend aggiornato: 7043 nodi e 16958 archi; artefatti non versionati.
- Graphify platform docs: refresh semantico completato (`chunk 1/1 done`,
  nessun warning di chunk fallito); log `/tmp/gaia-activity-graphify-docs.log`.
- Ratchet globale non verde: due rilievi estranei in `xlsm_export.py`
  (parametri `count_operai_paid_rest_days` `1 -> 2`, LOC file `570 -> 575`),
  file invariato rispetto a HEAD e gia modificato nei commit anteriori alla
  slice. Nessun rilievo GIS. `complexity-baseline-verify` restituisce `false`;
  nessuna sincronizzazione globale tentata. Log `/tmp/gaia-activity-global-ratchet.log`
  e `/tmp/gaia-activity-baseline-verify.log`. Diff whitespace pulito.
- Build production ed E2E browser non eseguiti per questa slice locale.
- Prossima azione separata: scegliere un hotspot con decisioni ridondanti
  eliminabili, senza estendere automaticamente questa estrazione.

### Ruolo - finalizzazione candidati solleciti (2026-09-21)

- Semplificazione locale di `_collect_reminder_candidates` autorizzata dopo
  il blocco LOC del registro avvisi; nessun secondo hotspot.
- Prima: LOC `141`, cyclomatic `39`, cognitive `59`, nesting `2`, parametri
  `8`; baseline autorevole al merge-base `ec5b1375`: LOC `139`.
  Report acquisito in `/tmp/gaia-collect-before.json`.
- Invarianti: query e filtri, gate storico 2022/2023, raggruppamento per CF,
  importi Decimal, promozione soggetto, risoluzione NAS, payload e ordinamento.
- Slice: rimuovere i default NAS sempre sovrascritti e finalizzare direttamente
  la lista dei gruppi, senza lista incrementale duplicata. Nessuna estrazione,
  compressione di layout o modifica di baseline/soglie/esclusioni.
- Caratterizzazione: suite Tributi con fixture storiche verificate mediante
  i comandi auditati del registro, non con bypass del gate di ammissibilita.
  Prima del refactoring: `94 passed`, statement `1848/1848`, branch `696/720`.
- Dopo: LOC callable `138`, file `3659 -> 3656`; cyclomatic `39` e cognitive
  `59` invariati. Aggregati file: `177` callable, sum cyclomatic `1195`, sum
  cognitive `1398`, invariati. Nessun helper aggiunto o debito trasferito.
  Esito `IMPROVED` limitatamente alle LOC; restano le quattro violation legacy
  callable e quella LOC file-level, senza peggioramenti.
- `test_tributi_api.py` e `test_tributi_register_regressions.py`: `108 passed`,
  statement `1847/1847`, branch `720/720`, full-file `100%`, nessuna nuova
  esclusione. I 14 casi aggiunti coprono confini legacy, rollback condiviso
  generazione/registro e cambio verifica STEP dopo selezione dei candidati.
  Due fixture nuove inizialmente prive di campi anagrafici obbligatori sono
  state completate; nessuna failure runtime residua.
- Servizi eligibility/generation: `28 passed` su SQLite e PostgreSQL isolato,
  statement `106/106`, branch `46/46`, entrambi al `100%`.
- `make complexity-ratchet BASE_REF=ec5b1375
  QUALITY_PYTHON=backend/.venv/bin/python`: `PASS`, `findings: []`.
  `make lint-backend` e diff check verdi; quality tooling `76 passed`.
  Baseline invariata; nessuna sincronizzazione eseguita per assorbire il debito.
- Evidenze `/tmp/gaia-collect-{before,after}.json`,
  `/tmp/gaia-collect-final-{tests.log,coverage.json}` e
  `/tmp/gaia-collect-ratchet.log`. Nessun secondo hotspot, commit o deploy.

### Matching duplicati rimossi - registro Ruolo (2026-09-18)

- Follow-up esplicitamente autorizzato dopo lo stop `ambiguous_identity` su
  `frontend/src/components/layout/navigation.ts`, baseline autorevole
  `ec5b1375`. La riga di import del registro sposta le callback di una riga;
  baseline: 11 `isVisible` con fingerprint `a0e8a20228335a32`, correnti: 10.
  La rimozione era gia presente prima della feature; le metriche delle callback
  sono tutte identiche, ma lo spostamento produce distanze a pari merito.
- Correzione delimitata a `resolve_baseline_callable`: confronto multinsieme
  delle tuple primarie per gruppi stesso path/nome/fingerprint, anche quando
  diminuisce il numero di duplicati invariati. Nessuna scelta arbitraria di
  ownership e nessuna assegnazione multipla della stessa occorrenza baseline.
  Fallback fra path e controlli di regressione restano invariati.
- Sette casi aggiunti: rimozioni, gruppo invariato, tuple eterogenee,
  molteplicita eccedente, regressione e riuso indebito di una tupla baseline.
  `make quality-test QUALITY_PYTHON=backend/.venv/bin/python`: 76 passed.
  Ruff check e format-check dei due file tooling/test: passano.
- Ratchet prima: exit 2 per ambiguita; dopo: exit 0, `findings: []` con
  `make complexity-ratchet BASE_REF=ec5b1375
  QUALITY_PYTHON=backend/.venv/bin/python`. Baseline, motori, scope, soglie ed
  eccezioni non modificati. Nessuna riduzione di complessita runtime rivendicata.
- Registro frontend: 45 test mirati, coverage 100% su 258 statement, 234 branch,
  99 funzioni, 215 righe; regressione 138 test e tre E2E desktop/mobile/viewer
  passati. Dettagli, metriche prima/dopo e limiti operativi nella documentazione
  `domain-docs/ruolo/docs/REGISTRO_AVVISI_IMPLEMENTAZIONE.md`.

### Baseline globale - audit e prima slice (2026-09-15)

- Richiesta: affrontare il debito che impedisce la sincronizzazione globale.
- Base `main@3596c36d`; preservata la change dashboard Elaborazioni gia
  rilasciata e ancora non committata.
- Audit read-only: il CLI limita i finding stampati ai primi 100; inventario
  integrale acquisito tramite le stesse funzioni `scan`/`compare` del tool.
- Prima slice: `geometryFromCoordinates` in
  `frontend/src/app/gis/catalogo/guided-workflow.ts`, cyc/cog `15/23`, LOC `31`.
  Una violation nuova cyclomatic raggiunge la soglia error `15`.
- Invarianti: parsing coordinate, tipi GeoJSON, chiusura degli anelli,
  rifiuto input invalidi e precedenza geometria selezionata/layer invariati.
  Il ramo polygon entra soltanto con almeno tre coppie numeriche valide.
- Prima: 7 test helper, coverage full-file 100% su statement `90/90`,
  branch `124/124`, funzioni `18/18`, righe `78/78`.
- Nessuna modifica a soglie, esclusioni, matching o baseline autorizzativa.
- Inventario completo: 200 rilievi su 38 file, baseline sorgente `b1d4a988`.
  Analisi e tranche in `BASELINE_RECOVERY.md`. I primi 100 del CLI nascondevano
  parte dei client API, dei worker e delle regressioni file-level.
- Esito slice `IMPROVED`: conversione Multi unificata nel medesimo callable;
  cyc/cog `15/23 -> 10/20`, LOC `31 -> 28`; file LOC `236 -> 233`, sum cyc
  `85 -> 80`, sum cog `93 -> 90`. Nessun trasferimento del debito.
- 19 test helper/componenti passati, full-file 100%: statement `94/94`,
  branch `114/114`, funzioni `18/18`, righe `82/82`. Aggiunta caratterizzazione
  Polygon/MultiPolygon con ultimo punto che differisce soltanto nella Y.
- TypeScript, ESLint mirato e `git diff --check` passano. Ratchet autorevole
  contro `3596c36d` verde (`findings: []`); baseline globale invariata.
- Graphify frontend aggiornato. Nessun deploy della slice GIS; la dashboard
  Elaborazioni gia pubblicata non viene modificata da questo refactoring.
- Repeat integrale: 199 rilievi su 37 file, rispetto a 200 su 38 prima;
  nessun altro rilievo eliminato o assorbito. Graphify platform docs completato
  con `chunk 1/1 done`, senza failure semantiche.

### Catasto GIS - repeat dei gate (2026-09-07)

- Working tree su `8ae046a3`; nessuna modifica runtime in questo repeat.
- Suite mirata strumentata: `55 passed`; otto runtime GIS al `100%` per
  statement `860/860`, branch `809/809`, funzioni `256/256`, righe `734/734`.
  Report `/tmp/gaia-gis-recheck-coverage`; soglie ed esclusioni invariate.
- `make quality-test`: `69 passed`. TypeScript ed ESLint mirato passano.
- E2E Chromium ripetuti: `2 passed` in 30 secondi, API/tile simulate e
  MapLibre reale; console desktop/mobile e misure con riavvio verificati.
  Log `/tmp/gaia-gis-recheck-e2e.log`; server locale con watcher polling.
- Graphify frontend aggiornato con pruning tramite target dedicato;
  aggiornamento platform docs tramite `make graphify-platform-docs`.
- Allineato `HOTSPOTS.md` al risultato finale della slice archivio: la coverage
  full-file non e piu bloccata; il debito legacy e globale resta esplicito.

### Catasto GIS - archivio rivisto e coverage completa (2026-09-07)

- Follow-up autorizzato dopo la stop condition: stessa responsabilita archivio,
  nessun secondo hotspot. `GisArchivePersistence` gestisce le operazioni API
  con snapshot del render; l'hook possiede catalogo, autoload e preferenze di
  visualizzazione. Contratti, payload e feedback preservati.
- Eliminate le tre nuove violation dell'estrazione preliminare: persistenza max
  cyc/cog `13/15`, hook `5/5`, nessuna nuova violation error-level. Restano
  warning nei comandi di salvataggio e caricamento, senza eccezioni aggiunte.
- Pagina prima/dopo estensione: cyc max `357 -> 302`, cog `404 -> 338`,
  LOC `2416 -> 2187`. Aggregato pagina + archivio (tipi inclusi): sum cyc
  `892 -> 845`, cog `786 -> 725`, LOC `2416 -> 2458`. Il lieve aumento delle
  LOC totali esplicita i confini; le complessita aggregate diminuiscono.
  Classificazione `IMPROVED`; restano le violation legacy della pagina.
- Coverage finale degli otto runtime GIS nuovi/modificati: `55 passed`,
  statement `860/860`, branch `809/809`, funzioni `256/256`, righe `734/734`,
  tutto `100%`. Test di integrazione reali e contratti correnti dei pannelli,
  senza accesso allo stato React interno, callback obsolete o coverage ignore.
- TypeScript, ESLint mirato e diff check passano. Ratchet sul corpus GIS contro
  baseline autorevole merge-base `8ae046a3`: `code: 0`, `findings: []`.
  HEAD e avanzato per attivita concorrenti, preservate. Baseline invariata:
  il limite globale di sincronizzazione gia documentato non e risolto qui.
- E2E Chromium: `2 passed`, console e controlli desktop/mobile, misure e
  riavvio misura con MapLibre reale e API/tile simulate. Il primo tentativo
  si fermava prima del login per `EMFILE` del server dev; il repeat con
  `WATCHPACK_POLLING=true` passa senza modifiche applicative.
- Report coverage `/tmp/gaia-gis100-final-coverage`, metriche
  `/tmp/gaia-gis100-metrics3.json`, ratchet
  `/tmp/gaia-gis100-ratchet-final.log`. Graphify frontend rigenerato con pruning:
  `6686` nodi, `16025` archi. Nessun commit, push o deploy eseguito.

### Catasto GIS - estensione archivio e coverage (2026-09-07)

- Richiesta esplicita: ampliare moderatamente il refactoring e raggiungere il
  `100%` di coverage. Estratti stato e comandi archivio in `use-gis-archive.ts`,
  con test del contratto tramite renderHook e integrazione pagina preservata.
- Verifica attuale: `38 passed`; sul perimetro pagina + archivio statement
  `732/735` (`99,59%`), branch `720/739` (`97,42%`), funzioni `214/214` e
  righe `643/643` (`100%`). Archivio singolarmente al `100%` su tutte le metriche;
  la pagina resta sotto soglia. TypeScript passa. Soglie e ignore invariati.
- Metriche pagina prima/dopo questa estensione: max cyc `357 -> 302`, cog
  `404 -> 338`, LOC file `2416 -> 2186`. Il nuovo `useGisArchive` introduce
  pero tre violation error-level: cyc `48` (soglia `15`), cog `58` (soglia
  `25`), LOC `190` (soglia `80`). La diminuzione della pagina non autorizza
  il trasferimento del debito. Nessun aggiornamento baseline.
- Esito `BLOCKED`: stop condition del programma sulla nuova failure di
  complessita. L'estrazione resta una bozza nel working tree, non conforme.
  Serve decidere se rivedere i confini del solo archivio (persistenza e stato
  di visualizzazione) oppure ritirare questa estrazione mantenendo i test.
- Evidenze: `/tmp/gaia-gis100-tests.log`,
  `/tmp/gaia-gis100-coverage/coverage-final.json`,
  `/tmp/gaia-gis100-metrics.json`, `/tmp/gaia-gis100-types.log`.
  E2E non rieseguiti dopo questa estensione; quelli della slice precedente
  non costituiscono verifica della nuova estrazione.

### Catasto GIS - controlli condivisi e matching (2026-09-07)

- Autorizzazione: follow-up utente sui gate GIS e valutazione del refactoring.
- Base: `main@598b1762`; working tree con modifiche UI GIS del turno precedente
  e modifiche estranee preservate. Durante il lavoro il worker e stato modificato
  da un'altra attivita; i suoi finding non appartengono al perimetro GIS.
- Slice: consolidare i controlli layer duplicati nelle due console e
  caratterizzare i flussi della stessa pagina. Nessun secondo hotspot.
- Invarianti: API, payload, autorizzazioni, calcoli geodetici, import/archivio,
  selezione e comportamento delle due viste. Gli slider hanno ora label
  accessibili e i toggle espongono `aria-pressed`.
- Prima del refactoring: pagina max cyc `386`, cog `433`, LOC file `2619`,
  sum cyc `959`, cog `829`. Dopo: max cyc `357`, cog `404`, LOC `2416`,
  sum cyc `892`, cog `786`. Il nuovo `GisLayerControls` ha max cyc `3`,
  cog `2`, LOC `49`, sum cyc `8`, cog `2`, nessuna violation.
- Aggregato pagina + nuovo componente: cyc sum `959 -> 900`, cog sum
  `829 -> 788`, LOC `2619 -> 2465`. Riduzione reale, senza trasferire debito;
  restano le violation legacy della pagina (LOC, hook e callable principale).
- Rimossi i rami tema scuro dei due render helper: tutti i call site passavano
  `false`. Nessun cambiamento al tema effettivamente visualizzato.
- Matching corretto: il fallback per nome di un modulo rimosso associava gli
  effetti GIS a `WikiWelcomePopup.useEffect[0]<callback>`. Ora esclude nomi
  sintetici e richiede unicita del nome anche nel report corrente. Tre test
  nuovi verificano il caso reale e il mantenimento del blocco nuove violation.
- `make quality-test`: `69 passed`; Ruff sui due file Python modificati verde.
  I due file sono stati allineati al lint obbligatorio; nessun albero legacy
  esterno e stato riformattato.
- Test frontend mirati: `46 passed`; due E2E Chromium passano con API/tile
  simulate, viewport desktop `1920x900`, `1280x720`, mobile `390x844`.
  TypeScript, lint frontend mirato e `git diff --check` verdi.
- Coverage: cinque componenti supporto al `100%`; pagina statement `98,10%`,
  branch `94,18%`, funzioni `99,53%`, righe `99,84%`, ancora sotto il
  `100%` full-file. Nessuna esclusione, ignore o modifica delle soglie.
  Report `/tmp/gaia-gis-refactor-coverage`, log `/tmp/gaia-gis-refactor-tests.log`.
- Ratchet contro baseline merge-base: verde dopo fix matching. Il repeat
  globale include finding del worker concorrente; per il GIS si confronta lo
  stesso report completo e la stessa baseline limitando i finding ai sei file
  runtime della change, senza sostituire il gate globale.
- `make complexity-baseline`: respinto per debito globale preesistente fuori
  perimetro (tra gli altri `capacitas_routes.py` e `activity-center.tsx`).
  Baseline invariata; `complexity-baseline-verify` non riproducibile.
- Graphify frontend aggiornato tramite target dedicato con pruning.
- Esito tecnico del refactoring: `IMPROVED`; esito complessivo change:
  `BLOCKED` dalla coverage full-file e dalla baseline globale non sincronizzabile.
  Non dichiarare la change conforme e non pubblicarla come verificata al 100%.
- Prossimo perimetro: caratterizzazione del controller archivio/sessione e
  rimozione dimostrata delle difese ridondanti della pagina, con metriche proprie.
  Evitare test che manipolano stato React interno o invocano callback obsolete
  soltanto per ottenere la percentuale. Il risanamento del debito globale
  della baseline resta una change separata.

### Stato del programma

- Program status: `RATCHET_ACTIVE_ON_LOCAL_MAIN`
- Current phase: `3 - ordinary ratchet applied to feature recovery`
- Last verified commit: `31f875d4`
- Reference branch: `main`
- Working branch: `main`
- Last update: `2026-08-27`
- Current owner: `GAIA maintainers`
- Active goal: `GIS-H8 GisToolsWorkspace hotspot`
- Blocking CI enabled: `local_main_not_pushed`

> Il branch applicativo `gaia/code-complexity-refactor` e congelato come
> esperimento. Questa fondazione parte da `main` e non contiene i refactoring
> Catasto o Presenze del branch archiviato.

## Checkpoint

| Checkpoint | Stato | Evidenza | Approvazione |
| --- | --- | --- | --- |
| 0 - audit reale | pass | review branch/report 2026-08-20 | completed |
| 1 - tooling e baseline | pass | `df4ad919` integrato su `main` locale | completed |
| 2 - gate differenziale CI | pass on local main | `31f875d4`, workflow e gate locale verdi | push/review required |
| 3 - ratchet ordinario | technical pass | recupero Presenze verificato sul branch dedicato | review required |
| 4 - hotspot dedicato | on demand | solo per impedimento concreto | explicit decision |

## Decision log

| Data | Decisione | Motivo | Impatto |
| --- | --- | --- | --- |
| 2026-09-02 | Adottare un code style ratchet distinto dalla complessita | Ruff era una dipendenza inutilizzata e `make lint-backend` faceva solo `compileall` | Policy in `docs/CODE_STYLE.md`, config in `ruff.toml`, gate sui file Python toccati; niente format di massa del legacy |
| 2026-08-17 | Local-first in Fase 1 | Evitare dipendenza operativa dalla CI | Nessun gate bloccante prima del Checkpoint 1 |
| 2026-08-17 | Un hotspot per goal | Ridurre rischio e facilitare review/revert | Niente batch refactor |
| 2026-08-17 | `/goal` per modifiche, `/loop` per monitoraggio | Goal e verificabile; loop e temporizzato | Refactoring non eseguiti a timer |
| 2026-08-20 | Congelare `gaia/code-complexity-refactor` a `52798f96` | Catasto ha prodotto riduzione reale; Presenze H2-I1 ha spostato debito senza ridurre il callable obiettivo | Nessun altro hotspot sul branch; recupero selettivo del tooling |
| 2026-08-20 | Quality ratchet come modalita predefinita | Integrare la non-regressione nelle feature senza campagne massive | Hotspot dedicati solo quando bloccano sviluppo, test o manutenzione |
| 2026-08-20 | Baseline autorevole dal merge-base | La baseline della stessa change puo mascherare una regressione coordinata | Nuovo comando `complexity-ratchet`; CI in una change successiva alla fondazione |
| 2026-08-20 | Coverage invariata | Non abbassare implicitamente la policy esistente durante il redesign della complessita | Resta `100%` sui file runtime nuovi o modificati |
| 2026-08-20 | Workflow code-quality dedicato | Evitare duplicazione e divergenza tra CI backend/frontend | Un solo job autorevole per test tooling e ratchet |
| 2026-08-25 | Usare il diff come ultima evidenza per callable aggiunti | I nomi JS anonimi ripetuti possono collassare su una pseudo-identita; una nuova callback non deve ereditare arbitrariamente debito legacy | Il fallback si applica solo a span interamente aggiunti e non nasconde nuove violation error-level |

## Esperimento archiviato

- Snapshot: `gaia/code-complexity-refactor` a `52798f964301a382bba37a794e4d5892ff06807d`.
- Catasto GIS: `IMPROVED`; riduzione cumulativa del callable principale circa
  cognitive `-23%`, cyclomatic `-26%`, con stop per rendimento marginale.
- Presenze H2-I1: `REORGANIZED_AND_CHARACTERIZED`; callable principale
  cognitive `577 -> 577`, cyclomatic `482 -> 482`, LOC `2314 -> 2314`, violation
  globali invariate e `6` violation trasferite al nuovo helper.
- Decisione: non integrare il branch in blocco e non iniziare H2-I2. Estrarre
  soltanto rules, skill, scanner e test dopo hardening.

## Audit corrente

- Branch/commit: `gaia/complexity-quality-ratchet` da `main@9562c9e6`.
- Working tree preesistente: pulito nel worktree dedicato; il working tree
  originale con modifiche Catasto/SISTER non e stato toccato.
- Tool estratti: scanner AST Python/JS, baseline, eccezioni, report e gate.
- Test tooling: suite completa `tests/code_quality`, non solo il file storico
  `test_complexity_tool.py`.
- Workflow CI: invariati in questa fase; attivazione rinviata finche la baseline
  non esiste nel branch di destinazione.
- Perimetro runtime: `backend/app`, `frontend/src`,
  `modules/elaborazioni/worker`.
- Coverage: policy corrente invariata.
- Rischio principale corretto: baseline della stessa change non autorevole.

## Fase 1

- [x] Audit completato
- [x] Architettura del motore disponibile nel diff per review
- [x] Adapter Python implementato
- [x] Adapter JS/TS implementato
- [x] Schema comune `2` implementato
- [x] Baseline generata da `main@9562c9e6`
- [x] Eccezioni validate
- [x] Ratchet contro baseline del merge-base implementato
- [x] Test dello strumento verdi
- [x] Target Make verificati
- [x] Documentazione completata
- [x] Report Checkpoint 1 prodotto
- [x] Nessun refactoring applicativo incluso

## Checkpoint 1 - fondazione quality ratchet (2026-08-20)

- Base: `main@9562c9e6711bb8384f889a8b9667a7a5a86eef55`.
- Branch/worktree: `gaia/complexity-quality-ratchet` in
  `/home/cbo/CursorProjects/GAIA-complexity-ratchet`.
- Perimetro: solo rules, skill, documentazione, scanner, test, baseline, report e
  script gate; nessun file runtime applicativo modificato.
- Baseline schema `2`: `1003` file, `15432` callable, `4328` violation (`2123`
  error, `2205` warning). I conteggi includono le soglie file-level, prima
  definite ma non applicate, e non sono confrontabili direttamente con i
  `4122` del prototipo.
- `make quality-test QUALITY_PYTHON=...` -> `33 passed`; la suite include tutti i
  file sotto `tests/code_quality`.
- `make complexity-check QUALITY_PYTHON=...` -> pass, findings vuoti.
- `make complexity-baseline-verify QUALITY_PYTHON=...` -> pass, baseline
  riproducibile ignorando timestamp, commit e metadati runtime.
- `complexity.py validate-exceptions` -> pass, nessuna eccezione.
- Test nuovi: soglia file su codice nuovo, peggioramento file legacy, regressione
  coordinata con baseline, scope change senza engine migration e merge-base
  mancante.
- `make complexity-ratchet BASE_REF=main` -> exit `2` atteso: la baseline non e
  ancora presente nel merge-base. Questo impedisce di attivare prematuramente
  la CI e prova la sequenza di rollout a due change.
- `make graphify-platform-docs` -> pass: `321` nodi, `376` archi, `41`
  community nel corpus `docs`; nessun grafo applicativo richiesto.
- Workflow CI: non modificati; Checkpoint 2 resta separato.

## Checkpoint 2 - attivazione CI (2026-08-20)

- Prerequisito: fondazione `df4ad919` integrata con fast-forward su `main`
  locale; la baseline esiste quindi al merge-base.
- Branch: `gaia/complexity-ratchet-ci`.
- Workflow: `.github/workflows/code-quality.yml`, separato dai workflow
  applicativi backend/frontend.
- Trigger PR: runtime backend/frontend/worker e infrastruttura code-quality.
- Trigger push: solo `main`, usando `github.event.before` come base autorevole.
- Checkout: `fetch-depth: 0`; Python `3.11`, Node `20`, `pytest` e dependency
  graph frontend installati esplicitamente.
- `make quality-test QUALITY_PYTHON=...` -> `33 passed`.
- Workflow YAML caricato con PyYAML -> pass.
- `make complexity-ci-gate BASE_REF=main QUALITY_PYTHON=...` -> pass:
  merge-base/baseline `df4ad919`, findings vuoti, baseline riproducibile ed
  eccezioni valide.
- `make graphify-platform-docs` -> pass: `346` nodi, `432` archi, `40`
  community; `104` file da cache e `3` riestratti.
- File runtime applicativi modificati: nessuno.

## Iterazione attiva

- ID: `Catasto-H3`.
- Hotspot: `frontend/src/app/catasto/gis/page.tsx` / controller e composer di
  `CatastoGisPage`.
- Modulo: Catasto GIS frontend.
- Motivazione: dopo l'estrazione presentazionale H2, la pagina resta non
  importata dai test unitari e concentra ancora stato, effetti, handler e JSX;
  il gate full-file misura `0/762` statement, `0/819` branch, `0/238` funzioni
  e `0/658` righe.
- Invarianti: route e autorizzazione `module_gis`, ordine incondizionato degli
  hook, API e payload, ricerca unificata Territorio, `TerritorioMapExperience`,
  contenuti e ordine dei pannelli, classi responsive, callback, busy/error,
  preview AdE, overlay archivio e comportamento mappa invariati.
- Test di caratterizzazione: i `25` test H2 sui cinque pannelli, smoke Catasto
  esistente e smoke Territorio Playwright flag-on; test mirati da aggiungere
  per helper, controller e composer prima della verifica finale.
- Metriche prima H3: `CatastoGisPage` cyc `388`, cog `435`, LOC `2341`; file
  LOC `2657`, `238` callable, cyc sum `962`, cog sum `831`, `29 useState`,
  `10 useEffect`, tre violation file-level error.
- Slice pianificata: separare helper puri, controller per responsabilita e
  composer/popup presentazionali; la pagina route deve diventare un adapter
  sottile. Vietato trasferire il callable monolitico in un singolo hook.
- File previsti/toccati: `page.tsx`, moduli Catasto GIS dedicati per helper,
  controller e vista, relativi test unitari, `PROGRESS.md` e `HOTSPOTS.md`.
- Stato: `stop_condition_reached`.
- Stop condition: nessun cambio funzionale, nessuna regressione del ratchet,
  nessuna failure nuova e nessun hotspot adiacente.
- Evidenza H3: la route e stata caratterizzata direttamente attraverso i
  callback del confine mappa e mock delle API, senza introdurre un hook
  monolitico. Cinque scenari coprono flusso principale, import/archivio,
  sessione assente, degradazione/errori e polling AdE.
- Coverage H3 corrente su `page.tsx`: statement `642/762` (`84,25%`), branch
  `566/819` (`69,10%`), funzioni `173/238` (`72,68%`), linee `578/658`
  (`87,84%`). La baseline iniziale della route era `0%` perche nessun test la
  importava.
- Decisione richiesta: i circa `253` branch residui appartengono soprattutto
  ai popup e ai controlli layer duplicati tra sidebar e vista estesa. Chiuderli
  richiede una nuova unita revisionabile (`Catasto-H4`) per estrarre popup e
  console layer/import; proseguire dentro H3 violerebbe la stop condition.
- Esito provvisorio: `REORGANIZED_AND_CHARACTERIZED`; il gate full-file non e
  ancora verde e non viene dichiarato completato.

## Iterazioni concluse

| ID | Data | Hotspot | Prima | Dopo | Test/coverage | Commit/PR |
| --- | --- | --- | --- | --- | --- | --- |
| GIS-H1 | 2026-08-25 | `GisAdministrationWorkspace` | cyc `40`, cog `46`, LOC `352` | cyc `3`, cog `3`, LOC `39` | `107` test GIS; coverage mirata `100%` | nessuno |
| GIS-H2 | 2026-08-25 | `GisPermissionsPanel` | cyc `28`, cog `28`, LOC `217` | cyc `4`, cog `3`, LOC `47` | `107` test GIS; coverage mirata `100%` | nessuno |
| GIS-H3 | 2026-08-25 | `GisLayerDetailWorkspace` | cyc `18`, cog `20`, LOC `114` | cyc `6`, cog `5`, LOC `16` | `107` test GIS; coverage mirata `100%` | nessuno |
| GIS-H4 | 2026-08-26 | `ConfirmationDialog` | cyc `6`, cog `5`, LOC `86` | cyc `2`, cog `1`, LOC `20` | `107` test GIS; coverage mirata `100%` | nessuno |
| GIS-H5 | 2026-08-26 | `FeatureSelector` | cyc `19`, cog `19`, LOC `170` | cyc `1`, cog `0`, LOC `33` | `108` test GIS; coverage mirata `100%` | nessuno |
| GIS-H6 | 2026-08-26 | `GuidedChangeRequestComposer` | cyc `35`, cog `36`, LOC `361` | cyc `5`, cog `4`, LOC `54` | `108` test GIS; coverage mirata `100%` | nessuno |
| GIS-H7 | 2026-08-26 | `GuidedAnnotationComposer` | cyc `22`, cog `23`, LOC `195` | cyc `4`, cog `3`, LOC `48` | `108` test GIS; coverage mirata `100%` | nessuno |
| GIS-H8 | 2026-08-27 | `GisToolsWorkspace` | cyc `60`, cog `72`, LOC `226` | cyc `2`, cog `1`, LOC `17` | `111` test GIS; coverage mirata `100%` | nessuno |
| Catasto-H1 | 2026-08-31 | `CatastoParticellaDetailPage` | cyc `131`, cog `145`, LOC `656` | cyc `3`, cog `2`, LOC `42` | `234` test Catasto; coverage perimetro `100%` | nessuno |

### 2026-08-31 - Catasto-H1 dettaglio particella

- Hotspot: `CatastoParticellaDetailPage`; `ParticellaDetailDialog` escluso e
  invariato. Preservati route, API e payload Catasto/Capacitas, fallback
  dell'anno campagna, autenticazione, navigazione embedded, ordine
  incondizionato degli hook, testi, rendering e azioni utente.
- Slice: caricamento e azioni isolati nel controller; formatter e risoluzione
  occupancy in helper puri; colonne e pannelli presentazionali separati per
  responsabilita. Nessun monolite trasferito in un file adiacente.
- Metrica obiettivo: componente principale cyclomatic `131 -> 3`, cognitive
  `145 -> 2`, LOC `656 -> 42`; le violation error-level passano da `7` a `0`.
- Anti-trasferimento sul perimetro dei sei runtime: LOC `778 -> 739`, somma
  cyclomatic `385 -> 317`, somma cognitive `368 -> 260`; violation totali
  `17 -> 4`, tutte warning presentazionali. I file restano sotto la soglia LOC
  file-level e nessuna nuova callable supera una soglia error-level.
- Verifiche: `20` test mirati; regressione Catasto `34` file e `234` test;
  smoke `18` test; typecheck e lint mirato puliti; coverage `272/272`
  statement, `309/309` branch, `99/99` funzioni e `237/237` righe (`100%`).
  `make quality-test` `46 passed`; ratchet mirato contro merge-base
  `840c0100` (`BASE_REF=origin/main`) `PASS`, `findings: []`.
- Baseline ed eccezioni non aggiornate. `baseline-verify` sul working tree
  funzionale restituisce correttamente `false`; la sincronizzazione globale
  non viene eseguita per non assorbire modifiche concorrenti fuori scope. Una
  baseline temporanea limitata ai sei runtime risulta invece riproducibile
  (`baseline_reproducible_ignoring_timestamp_commit: true`).
- Esito: `IMPROVED`. Debito residuo: quattro warning cyclomatic presentazionali
  sotto soglia error; `ParticellaDetailDialog` resta un hotspot separato e non
  viene avviato in questa iterazione.

## Modifiche funzionali verificate fuori dal programma hotspot

### 2026-08-31 - Worker SISTER AutoSync runtime batch

- Hotspot: `CatastoWorker._process_batch` e runner credenziale annidato; la
  crescita necessaria per profili AutoSync e stop graceful superava il ratchet
  legacy.
- Invarianti preservati: claim e fencing richiesta, concorrenza per credenziale,
  lease/heartbeat, finestre operative, cooldown SISTER, retry, CAPTCHA, artifact
  di errore, logout, rilascio lease, finalizzazione batch e stop AutoSync tra due
  visure.
- Slice: orchestration estratta in `_SisterBatchRuntime`, con stato condiviso
  esplicito e metodi separati per lifecycle sessione, attese, claim ed esiti. Il
  test SQLite del pool cross-user usa fixture locali di seeding sotto soglia.
- Metriche principali: `_process_batch` cyclomatic `53 -> 3`, cognitive
  `140 -> 2`, LOC `287 -> 23`; runner credenziale cyclomatic `38 -> 7`,
  cognitive `124 -> 15`, LOC `174 -> 16`. Rispetto alla baseline del merge-base,
  il file passa da somme cyclomatic/cognitive `431/678` a `298/324` e da `20` a
  `4` violation error-level; nessun nuovo callable ha violation error-level.
- Verifiche finali rieseguite sui `30` file di test worker: `make test-worker`
  esegue `503` test verdi e porta tutti i `29` runtime worker a `5241/5241`
  statement e `1358/1358` branch (`100%`). I
  cinque runtime modificati rispetto a `main` totalizzano `1822/1822` statement
  e `482/482` branch (`100%`); `make quality-test` produce `46 passed`, la
  compilazione e `git diff --check` sono verdi e `complexity.py changed` mirato
  produce `findings: []`. Il ratchet globale resta bloccato da nove regressioni
  LOC GIS concorrenti estranee: otto callable in
  `backend/app/modules/gis/router.py` (`+2` ciascuna) e il file
  `frontend/src/types/gis.ts` (`705 -> 836`).
- Baseline ed eccezioni non aggiornate. Esito: `IMPROVED`.

### 2026-08-27 - GIS-H8 workspace strumenti GIS

- Hotspot: `GisToolsWorkspace`; invarianti preservati per sessione senza token, caricamento catalogo e primo layer PostGIS editabile, selezione ZIP e inferenza nome tecnico, area/titolo/SRID/encoding, mapping `domainModule` (`rete -> network` sul valore non trimato), upload, preview, publish/reject con conferma, paginazione change request fino a `has_more=false` o `returned_count=0`, conteggio proposte, `historyVersion`, `GisActivityCenter`, `GisQgisTools`, testi/ARIA/busy e cleanup effetti.
- Slice: validazione e payload in helper puri; catalogo, upload, preview, conferma e ciclo paginato isolati in handler di modulo; pannelli presentazionali per hero, upload, preview/azioni e proposte. Il contratto pubblico resta `GisToolsWorkspace({ token })` da `tools-workspace.tsx`. Nessun `useMemo`/`useCallback`.
- Metrica obiettivo: componente principale cyclomatic `60 -> 2`, cognitive `72 -> 1`, LOC `226 -> 17`; le tre violation error-level sono eliminate. Il massimo residuo della responsabilita e LOC `68` sull'hook (`warning`), senza violation error-level. `buildShapefileUpload` resta a cyclomatic `8` e cognitive `11`, sotto soglia warning.
- Anti-trasferimento sul perimetro dei quattro file: callable `39 -> 60`, somma cognitive `134 -> 80`, somma cyclomatic grezza `147 -> 127` e decision point normalizzati `108 -> 67`; violation error-level `3 -> 0` e warning callable `4 -> 1`. Il file pubblico scende da LOC `269` a `29`; i tre nuovi moduli hanno LOC `104`, `133` e `281`, tutti sotto la soglia file warning di `500`.
- Verifiche: `12` test mirati e `15` file con `111` test GIS passati; typecheck frontend e lint mirato puliti; `39` test del quality tooling passati; coverage mirata dei quattro runtime `100%` con `170/170` statement, `102/102` branch, `60/60` funzioni e `154/154` linee.
- Ratchet autorevole contro il merge-base `ae889f0405dba8cc3fe246f28d0c201384f02d3d` (`BASE_REF=main`): `findings: []`, exit `0`. Il working tree include modifiche concorrenti non GIS (SISTER, scheduler, compose, docs worker) che non appartengono a questa slice; il gate sulle file cambiate non ha introdotto finding sul perimetro H8. Baseline ed eccezioni non modificate. `complexity-check` globale sui quattro file segnala solo `ambiguous_fingerprint` su callback JSX anonime gia note, senza nuove violation error-level.
- Graphify frontend aggiornato: `5.359` nodi, `13.271` archi e `187` community, senza ulteriori variazioni topologiche al re-run. Refresh platform docs `PASS`: `1.198` nodi, `2.669` archi e `92` community (`102` file da cache, `8` riestratti, chunk semantico completato con `gpt-5.4-mini`). Esito GIS-H8: `IMPROVED`.
- Documentazione piattaforma: `docs/GIS_PLATFORM_PROGRESS.md` registra la slice H8, le verifiche 2026-08-27 e il prossimo hotspot `GisLayerViewer` senza avviarlo.

### 2026-08-26 - GIS-H7 wizard annotazioni

- Hotspot: `GuidedAnnotationComposer`; invarianti preservati per scelta elemento
  o intera mappa, caricamento iniziale, modifica con selezione disabilitata,
  validazione titolo/descrizione, riepilogo, submit/retry/reset, annullamento,
  focus dei tre passi e stati busy.
- Slice: stato del wizard, pannelli target/dettaglio/riepilogo e costruzione del
  payload sono separati nel modulo `guided-annotation-composer.tsx`. Il file
  pubblico resta un barrel compatibile; DOM, testi, callback, payload API e
  ordine delle transizioni restano invariati.
- Metrica obiettivo: componente principale cyclomatic `22 -> 4`, cognitive
  `23 -> 3`, LOC `195 -> 48`; tutte le tre violation sono eliminate. Il massimo
  finale della responsabilita e cyclomatic `9`, cognitive `10`, LOC `48`, senza
  warning o error.
- Anti-trasferimento sul perimetro: callable `10 -> 22`, somma cognitive
  `30 -> 29`, somma cyclomatic grezza `36 -> 46` e decision point normalizzati
  `26 -> 24`; violation callable `3 -> 0`. Il file originario scende da LOC
  `210` a `3`; il nuovo modulo ha LOC `386` senza violation file-level.
- Verifiche: `10` test mirati e `15` file con `108` test GIS passati; typecheck
  e lint mirato frontend puliti; `39` test del quality tooling passati; coverage
  mirata dei due runtime `100%` con `51/51` statement, `37/37` branch, `22/22`
  funzioni e `48/48` linee.
- Ratchet autorevole contro il merge-base `61b5928952741466353e2587399cc288ebe37c41`:
  il gate globale mostra i primi `100` finding concorrenti (`92` regressioni
  legacy e `8` nuove violation), senza finding sui file H7. Baseline ed
  eccezioni non modificate.
- Graphify frontend aggiornato senza variazioni topologiche; refresh platform
  docs `PASS`. Esito GIS-H7: `IMPROVED`.

### 2026-08-26 - GIS-H6 wizard richieste di modifica

- Hotspot: `GuidedChangeRequestComposer`; invarianti preservati per selezione
  elemento e tipo, correzioni attributo/geometria, creazione/eliminazione,
  valori prima/dopo, coordinate, motivazione, validazioni, submit/retry/reset,
  modifica esistente, focus dei tre passi e stati busy.
- Slice: shell del wizard condiviso, orchestrazione stato e pannelli dei passi
  sono separati per responsabilita. L'export pubblico resta disponibile da
  `guided-workflow-components.tsx`; DOM, testi, callback, payload API e ordine
  degli effetti restano invariati.
- Metrica obiettivo: componente principale cyclomatic `35 -> 5`, cognitive
  `36 -> 4`, LOC `361 -> 54`; le tre violation error-level sono eliminate. Il
  massimo specifico della nuova responsabilita e cyclomatic `6`, cognitive `7`,
  LOC `67`, con due soli warning LOC e nessuna violation error-level.
- Anti-trasferimento sul perimetro: callable `43 -> 64`, somma cognitive
  `91 -> 77`, somma cyclomatic grezza `126 -> 132` e decision point
  normalizzati `83 -> 68`; violation callable `6 -> 5`. Il file originario
  scende da LOC `624` a `210`; i tre nuovi file hanno LOC `223`, `498` e `36`,
  senza violation file-level. Il distinto `GuidedAnnotationComposer` resta
  invariato a cyclomatic `22`, cognitive `23`, LOC `195`.
- Verifiche: `10` test mirati e `15` file con `108` test GIS passati; typecheck
  frontend e `39` test del quality tooling passati; coverage mirata dei quattro
  runtime `100%` con `135/135` statement, `105/105` branch, `63/63` funzioni e
  `123/123` linee.
- Ratchet autorevole contro il merge-base `61b5928952741466353e2587399cc288ebe37c41`:
  il gate globale mostra i primi `100` finding concorrenti (`90` regressioni
  legacy e `10` nuove violation). Nessun finding riguarda i tre nuovi moduli;
  i due del file pubblico appartengono al distinto composer delle annotazioni.
  Baseline ed eccezioni non modificate.
- Lint mirato pulito; Graphify aggiornato: frontend `5.303` nodi, `13.131`
  archi e `201` community, refresh platform docs `PASS`. Esito GIS-H6:
  `IMPROVED`.

### 2026-08-26 - GIS-H5 selezione guidata elementi

- Hotspot: `FeatureSelector`; invarianti preservati per caricamento iniziale,
  ricerca testuale, paginazione, selezione e nota sull'intera mappa, stati
  busy/disabled, messaggi di errore e annullamento delle risposte dopo unmount.
- Slice: la responsabilita completa e stata spostata nel modulo dedicato
  `feature-selector.tsx`; stato e caricamento sono isolati in un hook, mentre
  ricerca, select, feedback e paginazione hanno confini presentazionali. DOM,
  testi, classi CSS, chiamate API, callback e ordine degli effetti invariati.
- Metrica obiettivo: componente principale cyclomatic `19 -> 1`, cognitive
  `19 -> 0`, LOC `170 -> 33`; le tre violation del callable sono rimosse. Il
  nuovo massimo della responsabilita e cyclomatic `7`, cognitive `6`, LOC `77`,
  con il solo warning LOC dell'hook di caricamento.
- Anti-trasferimento sul perimetro dei due file: callable `58 -> 65`, somma
  cognitive `124 -> 117`, somma cyclomatic grezza `172 -> 174` e decision point
  normalizzati `114 -> 109`; violation callable `9 -> 7`. Il file wizard scende
  da LOC `794` a `624` e il nuovo modulo ha LOC `268` senza violation file-level.
- Verifiche: `10` test mirati e `15` file con `108` test GIS passati; typecheck
  frontend pulito; `39` test del quality tooling passati; coverage mirata dei
  due file runtime `100%` con `160/160` statement, `142/142` branch, `64/64`
  funzioni e `149/149` linee.
- Ratchet autorevole contro il merge-base `61b5928952741466353e2587399cc288ebe37c41`:
  il gate globale mostra ancora i primi `100` finding concorrenti (`88`
  regressioni legacy e `12` nuove violation). Nessun finding riguarda il nuovo
  `feature-selector.tsx`; i cinque del file wizard appartengono ai due composer
  distinti e sono invariati rispetto alle metriche iniziali della slice.
  Baseline ed eccezioni non modificate.
- Graphify aggiornato: frontend `5.266` nodi, `13.055` archi e `190` community;
  refresh platform docs `PASS`. Esito GIS-H5: `IMPROVED`.

### 2026-08-26 - GIS-H4 dialog di conferma

- Hotspot: `ConfirmationDialog`; invarianti preservati per testi e ordine DOM,
  tono primario/distruttivo, conseguenze, feedback `alert`/`status`, azioni di
  conferma e annullamento, blocco della chiusura durante le operazioni e
  integrazione con focus trap, `Escape`, scroll lock e ripristino del focus.
- Slice: props rese esplicite e intestazione, conseguenze/feedback e azioni
  separate per responsabilita presentazionale. Contratto pubblico, callback,
  classi CSS, condizioni di rendering e comportamento percepito invariati.
- Metrica obiettivo: componente principale cyclomatic `6 -> 2`, cognitive
  `5 -> 1`, LOC `86 -> 20`; la violation LOC error-level e stata rimossa e
  nessun nuovo helper supera una soglia warning o error.
- Anti-trasferimento sul file: callable `8 -> 11`, somma cognitive `47 -> 47`,
  somma cyclomatic grezza `52 -> 55` e decision point normalizzati
  `44 -> 44`; LOC file `175 -> 198`. I quattro warning preesistenti del distinto
  `CatalogDialog` restano invariati e fuori dalla slice.
- Verifiche: `6` test mirati e `15` file con `107` test GIS passati; typecheck
  frontend pulito; `39` test del quality tooling passati; coverage mirata
  `100%` con `59/59` statement, `34/34` branch, `11/11` funzioni e `54/54`
  linee.
- Ratchet autorevole contro il merge-base `61b5928952741466353e2587399cc288ebe37c41`:
  il gate globale resta rosso per il debito applicativo concorrente e mostra i
  primi `100` finding (`88` regressioni legacy e `12` nuove violation), ma
  nessun finding riguarda `catalog-dialog.tsx`. Baseline ed eccezioni non
  modificate.
- Graphify frontend aggiornato: `5.257` nodi, `13.039` archi e `192` community.
  Esito GIS-H4: `IMPROVED`.

### 2026-08-25 - GIS-H3 dettaglio layer

- Hotspot: `GisLayerDetailWorkspace`; invarianti preservati per caricamento e
  cancellazione richieste, errore/not-found, viewer geometrico, redirect al
  dominio, stato/descrizione/accesso e informazioni tecniche.
- Slice: caricamento isolato in hook; stati pagina, intestazione, scelta
  viewer/registro e dettagli tecnici separati per responsabilita. API, route,
  testi, destinazioni e markup accessibile invariati.
- Metrica obiettivo: componente principale cyclomatic `18 -> 6`, cognitive
  `20 -> 5`, LOC `114 -> 16`; massimi file cyclomatic `18 -> 6` e cognitive
  `20 -> 5`, senza violation o warning.
- Anti-trasferimento: callable `8 -> 15`, somma cognitive `31 -> 29`; somma
  cyclomatic grezza `36 -> 43`, con decision point normalizzati invariati
  `28 -> 28`. LOC file `142 -> 145` e massimo callable finale `31`.
- Verifiche: `15` file e `107` test unitari GIS passati; typecheck frontend
  pulito; coverage mirata del file `100%` per statement, branch, funzioni e
  linee; check senza baseline con finding e warning vuoti.
- Baseline ed eccezioni non modificate. Esito GIS-H3: `IMPROVED`.

### 2026-08-25 - GIS-H2 permessi GIS

- Hotspot: `GisPermissionsPanel`; invarianti preservati per selezione automatica
  dei layer amministrabili, filtro utenti attivi/GIS, assegnazione a ruolo o
  persona, ricarica permessi, fallback etichette e revoca con conferma.
- Slice: contesto layer/utenti e caricamento permessi isolati; editor e lista
  possiedono rispettivamente assegnazione e revoca. Contratti API, payload,
  testi, feedback ed effetti di cancellazione invariati.
- Metrica obiettivo: componente principale cyclomatic `28 -> 4`, cognitive
  `28 -> 3`, LOC `217 -> 47`; massimi file cyclomatic `28 -> 8` e cognitive
  `28 -> 7`, senza violation o warning.
- Anti-trasferimento: callable `40 -> 45`; somma cognitive `61 -> 56`; somma
  cyclomatic grezza `98 -> 99`, mentre i decision point normalizzati per la base
  di ogni callable scendono `58 -> 54`. LOC file `267 -> 347` per tipi e confini
  espliciti, con massimo callable finale `47`.
- Verifiche: `15` file e `107` test unitari GIS passati; typecheck frontend
  pulito; coverage mirata del file `100%` per statement, branch, funzioni e
  linee; check senza baseline con finding e warning vuoti.
- Baseline ed eccezioni non modificate. Esito GIS-H2: `IMPROVED`.

### 2026-08-25 - GIS-H1 amministrazione GIS

- Hotspot: `GisAdministrationWorkspace`; invarianti preservati per caricamento,
  selezione layer, creazione, metadati, lifecycle con conferma, export, feedback,
  governance QGIS e sezioni amministrative collegate.
- Slice: caricamento/selezione isolati in un hook di catalogo; registrazione,
  metadati, lifecycle ed export separati per responsabilita. Nessuna API, tipo,
  testo operativo o semantica di errore modificati.
- Metrica obiettivo: componente principale cyclomatic `40 -> 3`, cognitive
  `46 -> 3`, LOC `352 -> 39`.
- Anti-trasferimento sul file: callable `71 -> 54`, somma cyclomatic
  `143 -> 120`, somma cognitive `86 -> 77`, LOC file `466 -> 441`; massimi
  finali cyclomatic `9`, cognitive `13`, LOC callable `47`, senza violation.
- Verifiche: `15` file e `107` test unitari GIS passati; typecheck frontend
  pulito; coverage mirata del file `100%` per statement, branch, funzioni e
  linee; check senza baseline del nuovo file con finding vuoti.
- Ratchet globale: resta rosso per gli hotspot applicativi residui gia rilevati;
  baseline ed eccezioni non modificate. Esito GIS-H1: `IMPROVED`.

### 2026-08-25 - Hardening identita callable JS nel quality ratchet

- Scope: solo `tools/code_quality/complexity.py`, test del tooling e presente
  registro; nessuna baseline, eccezione o sorgente applicativa modificata dalla
  slice.
- Problema riprodotto: `61` callback JSX di
  `frontend/src/app/gis/catalogo/page.tsx` con pseudo-identita
  `Program<anonymous>` causavano `ambiguous_identity`; tre effetti omonimi in
  `operational-search-box.tsx` esponevano un secondo caso ambiguo.
- Correzione: il matcher riserva prima i sibling associabili uno-a-uno tramite
  fingerprint; solo come ultimo fallback riconosce come nuovo un callable il
  cui intero span appartiene alle righe aggiunte dal diff autorevole.
- Anti-laundering: i callable parzialmente aggiunti e quelli realmente
  indistinguibili continuano a uscire con codice `2`; un callable aggiunto con
  violation error-level continua a uscire con codice `1`.
- Verifiche: `make quality-test` -> `39 passed`; test identita JS -> `9 passed`;
  `make complexity-ratchet BASE_REF=main` non produce piu ambiguita ed esce
  correttamente con codice `1` sui debiti applicativi reali, senza aggiornare la
  baseline.
- Debito rilevato: il confronto completo mostra `192` finding (`159`
  regressioni callable legacy, `29` nuove violation e `4` regressioni
  file-level). La baseline al merge-base `87e747d7` dichiara ancora come
  sorgente `b1d4a988`; le modifiche successive della ricerca non erano state
  sincronizzate. `complexity-baseline-verify` resta correttamente rosso e la
  baseline non e stata rigenerata.
- Esito della slice tooling: `IMPROVED`; il falso blocco di configurazione e
  rimosso e le regressioni applicative restano visibili e bloccanti.

### 2026-08-19 - Export completo riepiloghi eventi INAZ

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`, base `2ded321cd99aeb59c02865e5e7f2bc158804e4b9`.
- Scope runtime: `backend/app/modules/presenze/services/parser.py` e nuovo `event_summary_export.py`.
- Invarianti: nessuna modifica a route, schema DB, autenticazione, autorizzazione, transazioni o sync; i campi legacy `*_minutes` persistiti restano compatibili.
- Correzione: segno delle durate negative `-HH:MM`; nuovo export unit-aware che conserva i valori grezzi e non filtra le descrizioni.
- Coverage: `pytest tests/test_presenze_event_summary_export.py tests/test_presenze_parser.py --cov=... --cov-fail-under=100` -> `17 passed`, `100%` sui due file runtime e sull'entrypoint CLI.
- Verifiche aggiuntive: compileall completato; suite mirate import/summary `16 passed`; suite backend completa senza failure; export read-only su produzione `6563` righe; Graphify code/docs aggiornato.
- Metriche complessita: tooling/target `complexity-*` non presente sul commit `main` di base; nessuna baseline modificata o rigenerata. Il nuovo servizio usa funzioni piccole e isolate, senza nuove esclusioni o eccezioni.
- Baseline diff: nessuno.
- Commit previsto: `fix(presenze): export complete INAZ event summaries`; PR: nessuna.

### 2026-08-20 - Versionamento hotfix live GATE Presenze

- Branch/worktree: `main` nel worktree dedicato `/home/cbo/CursorProjects/gaia-inaz-ferie-main`; nessuna integrazione dal branch `gaia/code-complexity-refactor`.
- Scope runtime: `backend/app/services/gate_mobile_sync.py`; diff live acquisito dal CED pari a `23` righe aggiunte e `2` rimosse.
- Invarianti: route, schema DB, autenticazione, autorizzazione e transazioni invariati; `_get_gate_record_or_404` continua a essere il gate autorizzativo finale.
- Comportamento: propagazione KM/reperibilita negli snapshot GATE e fallback del record giornaliero rigenerato tramite `collaborator_id/work_date`.
- Provenienza: il file modificato coincide byte per byte con il runtime CED, SHA256 `bb1aad87b1c05884d08afd5a33495a0887e1d081bde7ee2da9747127753ed30e`.
- Coverage: `pytest tests/test_gate_mobile_sync.py --cov=app.services.gate_mobile_sync --cov-fail-under=100` -> `28 passed`, `100%` (`655/655` statement).
- Metriche complessita: i target `complexity-*` non sono presenti sulla base `main`; nessuna baseline, eccezione o esclusione e stata importata dal branch di refactoring.
- Baseline diff: nessuno.

### 2026-08-20 - Recupero selettivo export canonico GATE Presenze

- Provenienza: cherry-pick del solo commit funzionale `f98b6495` dal branch
  archiviato; refactoring Catasto e Presenze H2-I1 esclusi. Il fix successivo
  `66feb26c` non e stato duplicato perche gia presente semanticamente su `main`.
- Invarianti: API, schema DB, auth, autorizzazioni, transazioni e fallback delle
  pending action invariati; il contratto aggiunge versione e valori canonici
  XLSM e collega i supervisori ai collaboratori quando disponibili.
- Primo ratchet: blocco atteso su `gate_mobile_sync.py`, con LOC file
  `1182 -> 1239` e `_gate_record_feature_values` LOC `6 -> 23`, params `1 -> 3`.
  La baseline non e stata aggiornata per assorbire la regressione.
- Slice locale: serializzazione snapshot estratta nel boundary di dominio
  `gate_mobile_payloads.py`; il sync resta orchestratore. Metriche mirate:
  `99 -> 100` callable e `53 -> 53` violation; LOC sync `1239 -> 1146`, nuovo
  servizio `118` LOC senza violation file-level.
- Coverage: `test_gate_mobile_sync.py` -> `28 passed`, `100%` su sync
  (`640/640`) e payload (`36/36`); test GATE di `test_presenze_api.py` ->
  `13 passed`, `100%` sul router (`343/343`); Vitest Presenze -> `60 passed`.
- Typecheck globale: non verde per failure preesistenti nei test TypeScript non
  toccati; `presenze-pages.test.tsx` non compare tra le failure.
- Quality gate: `complexity-ratchet BASE_REF=main` -> pass, findings vuoti;
  baseline `1003 -> 1004` file, `15432 -> 15435` callable e `4328 -> 4328`
  violation, scope/esclusioni invariati; `baseline-verify` -> pass.

## Failure preesistenti

| Data | Comando | Failure | Riproducibile | Relazione con il lavoro |
| --- | --- | --- | --- | --- |
| - | - | - | - | - |

## Blocker e domande aperte

- Revisionare e pubblicare i commit locali del workflow CI e del recupero
  Presenze; nessun push e stato eseguito.
- Dopo l'integrazione, osservare le prime PR per falsi positivi operativi.
- Calibrare soglie ed eccezioni solo su falsi positivi osservati, non prima.
- Il controllo semantico contro split/wrapper artificiali e lo spostamento
  neutro del debito resta una review obbligatoria degli aggregati; non viene
  sostituito da un euristico CI inaffidabile.
- La policy coverage resta invariata; un eventuale ratchet per righe legacy e
  una decisione separata.

## Prossima azione

Hotspot GIS successivo consigliato, senza avviarlo: `GisLayerViewer` in
`frontend/src/app/gis/catalogo/layer-viewer.tsx`. Non aprire in questa iterazione
`list_layer_features`, `GisActivityCenter`, `geometryFromCoordinates`,
`catalogo/page.tsx` o `services.py`. Le modifiche concorrenti nel working tree
restano escluse.

## Functional maintenance - SISTER visure reliability and Profilo A (2026-08-20)

- Scope: worker visure, stato persistito `CatastoVisuraRequest`, documenti, migration e contratti API; nessun nuovo hotspot del programma Fase 3.
- Profilo richiesto: `idConv=1050380`, label completa `CONSORZIO DI BONIFICA DELL'ORISTANESE (CONSULTAZIONI - PROFILO A)`, verificati anche sull'HTML multi-convenzione fornito.
- Decisione doppio ruolo: nessun flag sulle credenziali; selezione dinamica ID+label nella sessione SISTER, probe fino all'area visure e comportamento fail-closed.
- Affidabilita: baseline remota obbligatoria, correlazione deterministica, polling/download/delete limitati alla riga correlata, stato remoto persistito, affinità credenziale dopo restart, errore esplicito se la credenziale proprietaria non e disponibile.
- Concorrenza/retry: `execution_token` come fencing, `retry_not_before` e `last_error_code` persistiti, backoff e massimo tentativi, reset coerente su cancel/release/retry.
- Documenti: path univoco per utente/batch/request/execution, download `.part`, firma `%PDF-`, rename atomico, SHA-256 e upsert idempotente del documento.
- Stati: `completed`, `not_found`, `failed` e `non_evadibile` distinti; i non evadibili correlati vengono eliminati prima del retry.

### Complexity evidence

- Slice comparabile prima: `6` file, `276` callable, `112` violation (`43` error, `69` warning).
- Slice comparabile dopo: `6` file, `307` callable, `92` violation (`29` error, `63` warning).
- `worker.py`: LOC `1534 -> 1194`, cognitive sum `678 -> 470`, cyclomatic sum `431 -> 308`, max cognitive `120 -> 119`, max cyclomatic `52 -> 51`.
- `browser_session.py`: max cognitive `44 -> 25`, max cyclomatic `19 -> 14`, density `0.737548 -> 0.663941`; LOC aumenta `1044 -> 1223` per le nuove garanzie browser/correlazione.
- `visura_flow.py`: max cognitive `121 -> 63`, max cyclomatic `50 -> 26`, cognitive sum `130 -> 107`, density `0.732558 -> 0.513736`.
- Nuovi moduli affidabilita: nessuna violation error-level; `sister_worker_reliability.py` resta a `790` LOC, sotto la soglia error file di `800`.
- Baseline delta: `NONE`; nessuna eccezione o esclusione aggiunta.

### Tests and gates

- Worker browser/flow: `92 passed`; repository/orchestrazione worker: `67 passed`; client worker aggiuntivi: `30 passed`; CAPTCHA Pillow isolato: `4 passed`.
- Coverage nucleo SISTER: `1092/1092` statement e `274/274` branch, `100%` sui sette moduli misurati.
- Backend elaborazioni API/integration: `47 passed`; tutte le righe introdotte in `elaborazioni_batches.py` sono esercitate, mentre il file completo conserva debito coverage legacy.
- `make lint-backend`: `PASS`; `npm run typecheck:from-root`: `PASS`; `make quality-test`: `22 passed`; `make complexity-check`: `PASS`; `git diff --check`: `PASS`.
- Alembic: singolo head `20260820_0900`; SQL offline del range upgrade/downgrade della nuova revisione: `PASS`.
- Limite test: i test worker restano eseguiti in processi separati perche `test_worker.py` installa stub globali in `sys.modules`; `test_captcha_solver.py` usa il Python di sistema con Pillow, mentre i test Playwright usano `backend/.venv`.
- Failure nuove: `NONE`; commit/push/PR: `NO`.

### Final review addendum

- Corretto un race residuo nell'attesa CAPTCHA manuale: ingresso e letture sono ora transazionali e verificano batch, stato richiesta ed `execution_token`; cancel/release prima o durante l'attesa restituiscono subito `skip` senza riattivare il claim.
- Nuovo componente delimitato: `sister_captcha_wait.py`, coperto al `100%` statement/branch; suite repository/worker aggiornata a `70 passed`.
- `make complexity-check`: `PASS`, findings vuoti dopo la riduzione della firma `_wait_for_manual_captcha`; nessuna eccezione o esclusione aggiunta.
- Baseline aggiornata con il comando ufficiale della CLI usando Python `3.11.15`, cioe lo stesso motore registrato nella baseline. Il tentativo con il Python `3.12.3` del target `make` e stato correttamente rifiutato come engine migration non autorizzata; `/home/cbo/.local/bin/python3.11 tools/code_quality/complexity.py baseline-verify` restituisce `true`.
- Delta baseline limitato a `backend/app/services/elaborazioni_batches.py`, runtime/test SISTER e nuovi helper SISTER; nessun file applicativo di altri domini e nessuna engine migration.
- Graphify finale: `make graphify-backend` `7186` nodi, `make graphify-frontend` `4904` nodi; dopo l'ultima modifica docs, `make graphify-docs` `1129` nodi, `1691` archi, `99` community.
- Limite coverage policy: i moduli estratti di affidabilita sono al `100%`, ma i file legacy runtime modificati non raggiungono ancora il `100%` full-file (`browser_session.py` `41%` e `worker.py` `35%` nelle suite mirate; `elaborazioni_batches.py` conserva debito legacy). La change non va dichiarata pienamente conforme alla policy coverage integrale finche questo debito non viene colmato o il perimetro non viene ridisegnato in una iterazione separata.

### Full-file coverage closure

- Il limite coverage precedente e superato: tutti i file runtime SISTER modificati sono ora al `100%` statement e branch, senza pragma, esclusioni, abbassamenti gate o refactoring runtime finalizzati alla metrica.
- Worker SISTER: `2857/2857` statement e `784/784` branch su `browser_session.py`, `worker.py`, `visura_flow.py`, `sister_exceptions.py`, `sister_selectors.py`, `sister_browser_reliability.py`, `sister_captcha_wait.py`, `sister_request_rows.py`, `sister_worker_files.py` e `sister_worker_reliability.py`.
- Backend SISTER: `1081/1081` statement e `216/216` branch su `app/models/catasto.py`, `app/schemas/catasto.py` e `app/services/elaborazioni_batches.py`.
- Suite worker isolate: browser/flow/helper `158 passed`; repository/orchestrazione `116 passed`. L'isolamento resta obbligatorio perche `test_worker.py` installa stub globali in `sys.modules`.
- Suite backend isolate: API `38 passed`, integrazione visure `9 passed`, nuovi test full-file `18 passed`; totale `65 passed`. Le coverage dei processi sono combinate soltanto dopo il completamento delle suite.
- Nuovi test di caratterizzazione: lifecycle/form/correlazione browser, dispatch/recovery/claim/fencing/retry/cooldown worker, validator Pydantic, fallback `StrEnum` Python 3.10, parsing upload, transizioni batch e metriche runtime.
- Complexity: firma del locator browser finto ridotta da `8` a `6` parametri; `/home/cbo/.local/bin/python3.11 tools/code_quality/complexity.py check` restituisce `findings: []`.
- Baseline aggiornata esclusivamente con il comando ufficiale Python `3.11`; `baseline-verify` restituisce `true`. Nessuna esclusione, eccezione o engine migration aggiunta.
- Snapshot complessita dopo i test: `1021` file, `15916` callable, `4134` violation (`2001` error, `2133` warning); nessuna nuova finding rispetto alla baseline aggiornata.
- Gate eseguiti: `make lint-backend` `PASS`; `make quality-test`: `22 passed`; `npm run typecheck:from-root`: `PASS`; `git diff --check`: `PASS`.
- Graphify: `make graphify-backend` `PASS`, nessuna variazione topologica; `make graphify-platform-docs` `PASS`, refresh incrementale del corpus completato.

## Functional maintenance - SISTER settings credential pool UI (2026-08-20)

- Scope: `/elaborazioni/settings`, presentazione del pool credenziali SISTER e orchestrazione frontend dei test; nessuna modifica API, DB, autenticazione, autorizzazione o selezione Profilo A.
- UI: la precedente tabella orizzontale e sostituita da card responsive con stato attivo/default, convenzione, codice richiesta, ufficio, ultima verifica e azioni contestuali.
- Bulk test: `Testa tutte` include credenziali attive e disattivate, ma esegue sempre una sola verifica per volta; ogni POST viene seguito dal polling fino allo stato terminale prima di passare all'account successivo.
- Resilienza: un errore o timeout resta associato al singolo account e non ferma gli altri; sono disponibili avanzamento, riepilogo, cancellazione e refresh finale del pool. Il worker continua a usare soltanto credenziali attive.
- Correzione: l'errore di un test singolo non viene piu cancellato da un refresh nel `finally`; il refresh immediato viene eseguito solo per credenziali persistite e risultati terminali.

### Complexity evidence

- Before, baseline `settings-workspace.tsx`: LOC `2106`, callable `132`, cyclomatic sum/max `783/386`, cognitive sum/max `835/467`, density `0.768281`.
- After, `settings-workspace.tsx`: LOC `1977`, callable `128`, cyclomatic sum/max `717/352`, cognitive sum/max `755/425`, density `0.744562`.
- Delta workspace: LOC `-129`, callable `-4`, cyclomatic sum/max `-66/-34`, cognitive sum/max `-80/-42`, density `-0.023719`.
- Nuovi runtime estratti: controller LOC `125`, view LOC `147`, facade LOC `45`, orchestratore puro LOC `146`, diagnostica LOC `32`; nessuna violation error-level e `8` warning non bloccanti complessivi.
- La prima bozza monolitica del pool aveva `5` violation error-level ed e stata scartata; la separazione finale mantiene controller, view e orchestrazione sotto le soglie error-level.
- `make complexity-check`: `PASS`, findings vuoti; snapshot globale `1026` file, `15962` callable, `4137` violation (`2000` error, `2137` warning).
- Baseline delta di questa slice: `NONE`; nessuna eccezione o esclusione aggiunta. `make complexity-baseline-verify` non e stato dichiarato verde: restituisce `false` sul checkout funzionale non assorbito nella baseline, che non e stata ampliata per registrare nuovo debito warning-level.

### Tests and gates

- Coverage mirata sui sei runtime frontend: `660/660` statement, `910/910` branch, `175/175` funzioni e `591/591` righe, tutte al `100%`; `69 passed`.
- `npm run typecheck:from-root`: `PASS`.
- `npm run lint`: `PASS` con soli warning preesistenti fuori dal perimetro Elaborazioni modificato.
- `make quality-test`: `22 passed`.
- `git diff --check`: `PASS`.
- Verifica HTTP: `GET http://gaia.lan/elaborazioni/settings` risponde `200`; validazione visuale browser non eseguita per assenza di una sessione Chrome DevTools disponibile.
- Graphify: `make graphify-frontend` `PASS` (`4904` nodi, `12233` archi); `make graphify-docs` `PASS` (`1134` nodi, `1708` archi); `make graphify-platform-docs` `PASS` (`821` nodi, `1529` archi).

## Functional maintenance - SISTER portal telemetry and DEMANIO R9 batch (2026-08-20)

- Telemetria completa distribuita su backend, frontend e worker: eventi strutturati SISTER, dashboard `/elaborazioni/portal-health`, retention eventi/artifact e rotazione log Docker.
- Alembic verificato con singolo head `20260820_1100`; backend e frontend healthy, worker visure stabile su Python `3.10.12`; la route protetta `GET /elaborazioni/portal-health` risponde `401` senza token.
- Compatibilita worker corretta sostituendo `datetime.UTC` con `timezone.utc` nei moduli retention e telemetry; import dei moduli verificato nel container Python 3.10.
- Safeguard login: `Credenziali SISTER rifiutate` e `Autenticazione fallita` sono errori recuperabili, quindi attivano differimento, cooldown e telemetria invece di fallire in sequenza tutte le richieste della batch.
- Retention iniziale completata nel solo perimetro debug/report consentito: `76358` file, `22951` directory e `4691290206` byte rimossi; purge eventi scaduti `0`.

### DEMANIO R9 deployment evidence

- Origine: `/home/cbo/Desktop/DEMANIO_R9.xlsx`, `3503` righe complete; rimossi `144` duplicati esatti.
- Template: `/home/cbo/Desktop/DEMANIO_R9_visure_template.xlsx`, SHA-256 `ab2db1d8eb296b6544e33dcc4047427b357ea3c6913bb349e9ac77a34043ac78`, `3359/3359` righe validate dal parser applicativo.
- Mapping creato: Marrubiu `2168`, Terralba sezione `A` `124`, Uras `1067`; catasto `Terreni`, tipo visura `Sintetica`.
- Batch server: `32f88227-962f-4751-9efe-2d5a6c178689`, nome `DEMANIO R9 - Visure terreni`, utente `admin`, `3359` richieste.
- Il collaudo live ha rilevato `Credenziali errate / Autenticazione fallita` sulla credenziale predefinita. La batch e stata rilasciata e normalizzata in stato resumibile: `cancelled`, `3359` richieste `skipped` con operazione di release, nessun fallimento catastale persistito.
- Condizione di ripresa: aggiornare e testare positivamente la password SISTER in `/elaborazioni/settings`, quindi riavviare la batch esistente; non crearne una nuova.

### Tests and gates

- Retention e telemetry: `215/215` statement e `36/36` branch, `100%`, `6 passed`.
- Worker e reliability: `1333/1333` statement e `364/364` branch, `100%`, `116 passed`.
- Test completi precedenti della slice: worker regressioni `122 passed`, browser/reliability `146 passed`, backend Elaborazioni `67 passed`, frontend telemetria/navigazione `19 passed` con runtime modificato al `100%`; typecheck frontend `PASS`.
- Baseline complexity: nessun aggiornamento eseguito in questa slice; le modifiche preesistenti al file baseline sono state preservate.
- `make complexity-check`: `PASS`, `findings: []`; snapshot `1039` file, `16133` callable, `4141` violation (`1999` error, `2142` warning). `git diff --check` e `docker compose config --quiet`: `PASS`.
- Graphify finale: backend `7219` nodi, `17418` archi e `423` community; frontend `4938` nodi, `12305` archi e `177` community; docs `1147` nodi, `1737` archi e `115` community.
- Verifica live finale: `GET /health` `200`, `GET /elaborazioni/portal-health` senza token `401`; `20` eventi della batch registrati, inclusi login error, logout e chiusura sessione.

### Revalidation 2026-08-21

- Backend telemetria/router/base: `280/280` statement e `30/30` branch, `100%`, `3 passed`.
- Worker osservabilita/retention/telemetry: `511/511` statement e `82/82` branch, `100%`, `23 passed`.
- Worker orchestrazione/reliability: `1333/1333` statement e `364/364` branch, `100%`, `116 passed`.
- Frontend Portal Health/navigazione: `170/170` statement, `179/179` branch, `58/58` funzioni e `141/141` righe, `100%`, `19 passed`.
- Regressioni: backend Elaborazioni `68 passed`; browser/flow worker `158 passed`; client/osservabilita worker `53 passed`; CAPTCHA Pillow isolato `4 passed`.
- Corretto il test backend dipendente dal giorno fisso: la finestra usa ora `datetime.now(UTC)` e verifica il totale dei bucket giornalieri senza assumere che le ultime sette ore cadano nello stesso giorno UTC.
- Gate: typecheck frontend, compile backend, `make quality-test` (`22 passed`), `make complexity-check` (`findings: []`), `git diff --check`, compose e Alembic head/current `20260820_1100`: `PASS`.
- Lint frontend: exit `0`, con soli warning legacy fuori dal perimetro Portal Health; nessun warning nuovo attribuito alla slice.
- Graphify: backend e frontend senza variazioni topologiche; domain docs `1151` nodi, `1756` archi e `109` community; refresh platform docs `PASS`.

## Hotspot Presenze - visibility router characterization (2026-08-25)

- Scope: singolo hotspot `backend/app/modules/presenze/router.py`; nessun secondo hotspot avviato. La policy estratta in `services/visibility_policy.py` conserva il dual-read tra Organigramma canonico e assegnazioni supervisore legacy.
- Invarianti: `admin`, `hr_manager` e `super_admin` vedono tutti i dati Presenze; dirigenti e capi leggono il proprio sottoalbero; approvazione gerarchica distinta dagli override `read`; route, payload, schema DB e transazioni Presenze invariati.
- Coverage router prima: `1603/1988` statement, `80,63%`. Dopo i test di caratterizzazione: `1988/1988`, `100%`, `0` righe mancanti e `0` esclusioni. La nuova policy di visibilita e a sua volta al `100%` (`56/56`, `0` mancanti).
- Coverage runtime completo Organigramma/Presenze: `3350/3350`, `100%`, `0` righe mancanti e `0` esclusioni sui `13` file modificati. Il conteggio include modelli, posizioni, repository, import/export, bozze, servizi di organigramma/visibilita, sync WhiteCompany, router e policy Presenze.
- Metriche prima, router: LOC `4668`, cognitive sum/max `1372/111`, cyclomatic sum/max `1156/64`, `1` violation file-level.
- Metriche dopo, aggregato router + policy: LOC `4670`, cognitive sum/max `1366/111`, cyclomatic sum/max `1157/64`, `1` violation file-level. Il debito non e ridotto in modo univoco e non viene classificato come miglioramento.
- Test: suite strumentata Organigramma/Presenze `PASS`; `pytest -q tests/organigramma tests/test_presenze_*.py` `PASS`; `compileall` e `git diff --check` `PASS`; `make quality-test` `34 passed` dopo l'aggiunta della regressione sul matching cross-file. `test_modified_runtime_coverage.py` caratterizza errori import, fallback bozze/dettagli, cicli di visibilita e rami di mapping WhiteCompany.
- Ratchet autorevole isolato: checkout temporaneo della base `8e2008d24bac2f19c9403416fb06681a34952161` con i soli runtime Presenze modificati; `make complexity-ratchet BASE_REF=8e2008d24bac2f19c9403416fb06681a34952161` `PASS`, `findings: []`.
- Ratchet globale: il falso rename di un file nuovo e stato corretto limitando il matching cross-file ai percorsi baseline realmente assenti. Il gate completo resta in exit `2` per una distinta `ambiguous_identity` nel file concorrente `frontend/src/app/gis/catalogo/page.tsx`, ampiamente riorganizzato; baseline globale non aggiornata.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Debito residuo: router legacy sopra soglia LOC; una futura riduzione richiede una nuova autorizzazione hotspot separata.

## Functional maintenance - GIS coordinates and overtime months (2026-08-21)

- Scope GIS: ricerca globale, parser coordinate e nuova route `/catasto/gis/coordinate`; la pagina `/catasto/gis` e `MapContainer` sono identici a `main`, senza modifiche API, DB o auth.
- Scope Straordinari: nuovo router periodico, selettore mese self-service e query dei mesi con extra effettivi positivi; endpoint legacy, template XLSX e mapping collaboratore invariati.
- Coverage backend: `34 passed`, `342/342` statement e `84/84` branch, `100%` su router API, router periodico e service export.
- Coverage frontend: Straordinari `106/106` statement e `74/74` branch; route/parser GIS `101/101` statement e `78/78` branch; search box `143/143` statement e `129/129` branch. Tutti i file runtime nuovi o modificati sono al `100%` anche per funzioni e righe.
- Regressione frontend: `149` file e `1447` test verdi. Typecheck globale: `149` diagnostiche legacy, stesso insieme di `main` dopo normalizzazione e nessuna nei file modificati.
- Regressione backend: suite globale con due failure preesistenti riprodotte su `main`, entrambe fixture SISTER incomplete in `test_coverage_small_runtime.py`; test della change verdi.
- Quality ratchet: `make quality-test` -> `33 passed`; `make complexity-ratchet BASE_REF=main` -> `PASS`, `findings: []`; baseline, eccezioni ed esclusioni non modificate.
- Build production: il primo `npm run build` ha rilevato l'export helper non ammesso dalla route Next; il builder overlay e stato spostato nel helper GIS senza variazioni funzionali. Build finale `PASS`, con `/catasto/gis/coordinate` e `/me/straordinari` generate.
- Verifica finale del fix GIS: `15 passed`; `101/101` statement, `78/78` branch, `23/23` funzioni e `83/83` righe, `100%`; regressione frontend completa confermata a `149` file e `1447` test verdi.
- Graphify: Presenze code `643` nodi e `1989` archi; Catasto code `871` nodi e `2097` archi; frontend finale `4521` nodi, `11051` archi e `185` community; refresh Catasto docs, Presenze docs e platform docs `PASS`.
- Verifiche residue: backend `compileall` `PASS`; `git diff --check` `PASS`.

## Tooling - worker coverage CI gate (2026-08-27)

- Scope: solo tooling, test e documentazione; nessuna modifica ai runtime,
  contratti, database, concorrenza o baseline complessita.
- `make test-worker` esegue i 22 file pytest worker in processi distinti,
  combina statement e branch coverage ed esclude test/cache dagli artifact.
- `.github/workflows/backend.yml` installa le dipendenze worker, esegue il
  target, pubblica JSON/XML e applica il gate changed-file al 100% tramite
  `scripts/check_changed_worker_coverage.py`.
- Validazione: `404 passed`; otto runtime worker modificati al 100%; report
  completo runtime worker al 93% combinato, mantenuto warn-only per il debito
  legacy. Checker CI: `65/65` statement, `24/24` branch, 100%, `7 passed`.
- `make quality-test`: `46 passed`; compile, workflow YAML, Compose e
  `git diff --check`: `PASS`.
- Baseline complexity, eccezioni ed esclusioni: `NONE`; nessun runtime nel
  perimetro di questa estensione del tooling.

## Hotspot GIS - services baseline drift (2026-08-28)

- Branch: `quality/gis-services-baseline-drift-20260828`, derivato da
  `main@7a27fdaf`. Scope: singolo hotspot
  `backend/app/modules/gis/services.py` e impostazioni dichiarative necessarie
  a rendere verificabile M21; nessun file M21 incluso.
- Provenienza: tutto il drift GIS rispetto alla baseline sorgente
  `b1d4a988` deriva da `268234f9`. Su `services.py` il report passa da `2304`
  a `3145` LOC (`+841`), non `+834`; su `config.py` da `653` a `689` (`+36`).
- Classificazione completa `services.py`: `74` callable con fingerprint AST
  invariato e `+521` LOC di sola riformattazione; `_default_export_path` con
  regressione funzionale reale (`cyclomatic +1`, `cognitive +1`, `LOC +6`);
  nove callable nuove per `301` LOC, con errori nuovi su
  `_feature_selector_columns` e `list_layer_features`; nessun errore di
  matching.
- Correzione: ripristinata la rappresentazione delle callable AST-equivalenti;
  query catalogo/feature, builder di risposta e supporto export estratti in
  moduli sotto soglia; `list_layer_features` scomposta; settings GIS e storage
  ereditate da classi dichiarative dedicate. Route, payload, alias di settings,
  transazioni e comportamento osservabile restano invariati.
- Metriche dopo: `services.py` LOC `2266`, callable `110`, cyclomatic sum/max
  `540/22`, cognitive sum/max `530/27`; `catalog_queries.py` LOC `314`,
  cyclomatic max `9`, cognitive max `11`; `service_support.py` LOC `25` e
  `response_builders.py` LOC `50`, nessuna violation. `config.py` LOC `612`;
  il margine copre i `30` LOC M21 senza aggiornare la baseline.
- `make complexity-ratchet BASE_REF=main` con motore Babel disponibile:
  `PASS`, `findings: []`. `make quality-test`: `46 passed`.
- `make complexity-baseline` e stato eseguito solo dopo il ratchet e ha
  correttamente rifiutato l'update per regressioni non classificate di altri
  domini gia presenti su `main`. Baseline, scope, eccezioni ed esclusioni
  restano invariati; nessun JSON modificato manualmente.
- Esito: `IMPROVED`. Debito residuo: `services.py` resta sopra la soglia file
  legacy, ma senza crescita rispetto alla baseline; il riallineamento globale
  della baseline richiede change separate per i finding non GIS rifiutati.

### Follow-up callable headroom M21

- Il primo riallineamento M21 ha isolato tre aumenti LOC reali nelle callable
  legacy `_validate_change_request_payload` (`+1`), `create_layer` (`+1`) e
  `update_layer_metadata` (`+2`); nessun aggiornamento baseline eseguito.
- Costruzione `GisLayer` e calcolo degli update metadata sono stati estratti in
  `_new_layer` e `_layer_metadata_updates`. I dati, gli alias, il controllo
  admin, l'audit e i confini di commit/flush restano invariati.
- Test GIS/config: `52 passed`, coverage `1384/1384` statement, `100%` su
  `services.py` e `config.py`; `make lint-backend` e `git diff --check` verdi.
- Ratchet della follow-up contro `main@691bec1d`: `PASS`, `findings: []`.
  Baseline, eccezioni ed esclusioni restano invariate.
- Il successivo gate M21 non ha piu rilevato regressioni callable, ma solo il
  file-level `services.py 2304 -> 2323`. Il builder puro `_layer_response` e
  stato quindi spostato in `response_builders.py`, mantenendo in `services.py`
  il wrapper compatibile e la risoluzione dell'access level esistente.
- Verifica dell'estrazione finale: `41 passed`, coverage `1116/1116` statement
  (`100%`), lint e diff check verdi; ratchet contro `main@be143751` `PASS`,
  `findings: []`. Nessun aggiornamento baseline.

## API/router modularization - type facade (2026-09-05)

- Scope completato: `frontend/src/types/api.ts` trasformato in facciata
  compatibile e definizioni ripartite in sette barrel di dominio sotto
  `frontend/src/types/api/`; Presenze ed Elaborazioni sono ulteriormente
  separati in `base` e `operations` per restare sotto soglia file-level.
- Metriche prima: file dichiarativo, LOC scanner `4403`, callable `0`, cognitive
  e cyclomatic `0`; nessuna complessita callable da ridurre.
- Verifiche: typecheck frontend globale `PASS`; 409 test API mirati `PASS` sul
  prototipo runtime e sulla facciata tipi.
- Il prototipo `frontend/src/lib/api.ts` e stato ritirato: coverage mirata dei
  moduli proposti 84.21% statement, 56.77% branch, 98.57% functions e 86.33%
  lines, inferiore alla policy del 100% per nuovi runtime.
- Router backend non modificati; snapshot OpenAPI pre-change: 746 path e 876
  operazioni. Baseline complexity ed eccezioni non aggiornate.
- Classificazione: `REORGANIZED_AND_CHARACTERIZED`. Prossima azione: completare
  la caratterizzazione runtime di `lib/api.ts`, poi aprire separatamente il
  pilot `utenze/router.py`.

## API/router modularization - runtime facade (2026-09-05)

- Scope completato: `frontend/src/lib/api.ts` sostituito dalla facciata
  compatibile `frontend/src/lib/api/index.ts` e da 15 moduli per trasporto,
  dominio e gruppo operativo. Inventario pubblico invariato: `450` export prima
  e dopo, nessun nome mancante o aggiunto.
- Caratterizzazione: generatori coverage aggiornati per la facciata modulare,
  nuovo test generato dei branch e casi manuali aggiunti per trasporto e rami
  non rappresentabili dal generatore. Suite API mirata: `811 passed`.
- Coverage sui 16 file runtime della slice: `1,263/1,263` statement,
  `826/826` branch, `420/420` funzioni e `1,195/1,195` linee, tutti al `100%`.
- Metriche prima: LOC `5,339`, callable `419`, cognitive sum/max `545/54`,
  cyclomatic sum/max `850/30`, una violation file-level error. Dopo: LOC
  `5,080`, callable `420`, cognitive sum/max `545/54`, cyclomatic sum/max
  `851/30`; resta un warning file-level su `frontend/src/lib/api/network.ts`.
  Il callback `credentialIds.forEach`, ora rilevato separatamente, spiega il
  callable e il punto ciclomatico aggiuntivi; non e stato introdotto un ramo di
  comportamento.
- Regressione frontend completa: `206` file e `2.205` test passati. Typecheck
  globale: `PASS`. ESLint del perimetro: exit `0`, nessun errore e `11` warning
  legacy nei test generati; nessun warning sul runtime o sui tipi estratti.
- Generatori di caratterizzazione: output deterministico dopo rigenerazione;
  `ruff check` e `ruff format --check`: `PASS`. `make quality-test`: `63 passed`.
- `make complexity-ratchet BASE_REF=main`: nessun finding attribuito alla
  modularizzazione; exit `2` soltanto per le nuove violation concorrenti
  `get_portal_health` e `HealthHero` nelle modifiche Elaborazioni preesistenti.
  Baseline ed eccezioni non aggiornate.
- Graphify finale: frontend forzato per eliminare i riferimenti al file rimosso,
  `6.647` nodi, `15.943` archi e `237` community; documentazione piattaforma
  `1.855` nodi, `4.189` archi e `127` community.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Debito callable invariato; ownership,
  navigabilita e copertura migliorate. Prossima slice separata: pilot router
  Utenze con snapshot OpenAPI invariato; Network e Presenze restano esclusi.

## API/router modularization - Utenze router pilot (2026-09-05)

- Scope: `backend/app/modules/utenze/router.py` sostituito dal package facade
  compatibile `router/`; le 42 route locali sono assemblate nello stesso ordine
  da moduli per import, Bonifica, soggetti, documenti e reporting. Supporto e
  proiezione dettaglio soggetto sono separati senza modifiche funzionali.
- Contratti legacy preservati: `get_anagrafica_import_service`, `get_stats`,
  `_build_subject_detail` e il monkeypatch `get_nas_client` restano importabili
  da `app.modules.utenze.router`.
- OpenAPI normalizzata byte-identica: `746` path, `876` operazioni, SHA-256
  `e5d00458a818f5c9af7e9d54b2aa6905d647c7b82588fb1382a1e18e5b34fada`.
- Coverage: `89 passed`; `870/870` statement e `220/220` branch, `100%` su
  facade e moduli nuovi. La suite preesistente copriva il monolite al `60%`;
  sono stati caratterizzati error path, resume, XLSX, Bonifica, NAS e documenti.
- Metriche prima: LOC `1.983`, callable `79`, cognitive sum/max `417/39`,
  cyclomatic sum/max `409/28`, una violation file-level error. Dopo: LOC
  `2.050`, callable `80`, cognitive `409/39`, cyclomatic `403/28`; resta un
  warning LOC su `routes/support.py` (`640`), nessuna violation file-level error.
- Ruff check/format, compileall, `make quality-test` (`63 passed`) e diff check:
  `PASS`. Ratchet: zero finding Utenze; i soli finding globali sono
  `get_portal_health` e `HealthHero` nelle modifiche Elaborazioni concorrenti.
  Baseline ed eccezioni non aggiornate.
- Graphify finale: Utenze `575` nodi, `1.579` archi e `24` community; backend
  `8.077` nodi, `20.419` archi e `461` community. Platform docs aggiornato a
  `1.874` nodi, `4.189` archi e `146` community con risultato parziale: uno dei
  sei chunk semantici ha superato il timeout di 60 secondi.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Prossima eventuale slice separata:
  Network; Presenze resta fuori scope.

## API/router modularization - Network router (2026-09-05)

- Scope: `backend/app/modules/network/router.py` sostituito dal package facade
  compatibile `router/`; 39 endpoint assemblati nello stesso ordine da route
  VPN, overview, dispositivi, tracking, firewall, scansioni e planimetrie.
  Helper separati per device/RDAP, label endpoint, tracking, inferenza, traffico,
  scansioni e Sophos; ogni file resta sotto la soglia LOC file-level.
- Compatibilita preservata: `_resolve_device_label` per il router `me` e i
  monkeypatch `run_network_scan`, `poll_sophos_firewall_metrics` e
  `urllib.request.urlopen` restano disponibili dalla facade.
- OpenAPI normalizzata byte-identica: `746` path, `876` operazioni, SHA-256
  `2392ea45da9938cfcd0773e2d7e253023604e8e38697b922404c04c950510a4e`.
- Coverage: `75 passed`; `1.406/1.406` statement e `452/452` branch, `100%` su
  facade e moduli nuovi. La baseline dei 41 test API copriva il monolite al
  `74%`; sono stati caratterizzati error path, RDAP/DNS, riconciliazione e
  inferenza, traffico/statistiche, timeline ARP, Sophos e diff scansioni.
- Metriche prima: LOC `2.630`, callable `87`, cognitive sum/max `1.101/209`,
  cyclomatic sum/max `774/109`, una violation file-level error. Dopo, aggregato
  del package: LOC `2.943`, callable `87`, cognitive `1.101/209`, cyclomatic
  `774/109`; l'aumento LOC e overhead di import/facade, mentre complessita e
  callable sono identici e nessun file resta sopra soglia LOC.
- Ruff runtime check/format, compileall, diff check e `make quality-test`
  (`63 passed`): `PASS`. Ratchet: zero finding Network; i soli finding globali
  sono `get_portal_health` e `HealthHero` nelle modifiche Elaborazioni
  concorrenti. Baseline ed eccezioni non aggiornate.
- Graphify finale: Network `429` nodi, `1.093` archi e `18` community; backend
  `8.178` nodi, `20.710` archi e `448` community. Anche il grafo platform docs
  e stato aggiornato con successo e tutti i file semantici modificati sono
  stati estratti.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Prossima eventuale slice separata:
  Presenze; non avviata in questa iterazione.

## API/router modularization - Presenze router (2026-09-05)

- Scope: `backend/app/modules/presenze/router.py` sostituito dal package facade
  compatibile `router/`; 86 route assemblate nello stesso ordine da 11 gruppi
  HTTP. Helper separati per accesso, scheduling, collaboratori, giornaliere,
  recovery, banca ore e job; definizioni dichiarative degli orari isolate.
- Invarianti preservati: OpenAPI, auth, autorizzazioni, transazioni, ordine
  route, import pubblici verso `me`/Gate Mobile e monkeypatch legacy. Il mapping
  canonico resta esclusivamente
  `presenze_collaborators.application_user_id -> application_users.id`, senza
  fallback anagrafici o numerici.
- OpenAPI globale byte-identica subito dopo la slice: `746` path, `876`
  operazioni, SHA-256
  `e5d00458a818f5c9af7e9d54b2aa6905d647c7b82588fb1382a1e18e5b34fada`.
  Dopo l'aggiunta concorrente di `/organigramma/sync/inaz/preview`, il confronto
  finale isolato Presenze resta byte-identico: `64` path, SHA-256
  `19da9c78abf3488310bca1c1ff29ac65969f4125d09d6c026e4225710a36b35c`.
- Coverage: `241` test passati; `2.292/2.292` statement e `696/696` branch,
  `100%` sui 23 runtime nuovi. `make quality-test`: `63 passed`; lint/style e
  format-check dei runtime: `PASS`.
- Metriche prima: LOC `4.616`, callable `160`, cognitive sum/max `1.353/111`,
  cyclomatic sum/max `1.139/64`, una violation file-level error. Dopo: LOC
  aggregato `5.267`, callable `163`, cognitive `1.370/111`, cyclomatic
  `1.154/64`, file max LOC `718`. Escludendo i tre callable tecnici della
  facade, i 160 callable legacy conservano esattamente cognitive `1.353/111` e
  cyclomatic `1.139/64`; la violation file-level e eliminata.
- Ratchet autorevole contro `main@33fbdb9c`: non verde. I finding Presenze sono
  falsi `new_callable_violation` su tre callable spostati ma modificati dopo il
  source commit della baseline (`list_collaborators`,
  `_apply_daily_record_filters`, `get_dashboard_summary`); AST e metriche prima
  e dopo risultano invariati. Restano inoltre i finding concorrenti
  `get_portal_health` e `HealthHero` di Elaborazioni. Baseline, matcher,
  eccezioni ed esclusioni non sono stati modificati.
- Graphify finale: Presenze `1.079` nodi, `3.432` archi e `43` community;
  backend `8.379` nodi, `21.292` archi e `478` community; platform docs `1.935`
  nodi, `4.318` archi e `144` community, con i tre file semantici residui
  riestratti nel refresh finale.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Debito callable invariato; ownership,
  navigabilita, copertura e soglia file-level migliorate. Prossima azione:
  riallineare la baseline storica Presenze in una change tooling dedicata e
  indipendente, senza assorbire i finding concorrenti.

## API/router modularization - Me router (2026-09-05)

- Scope: `backend/app/modules/me/router.py` sostituito dal package facade
  compatibile `router/`; 17 route assemblate nello stesso ordine da gruppi
  stato/Presenze, summary, Operazioni e asset. I 14 helper condivisi vivono in
  `common.py`.
- Invarianti: path, metodi, operation ID, auth, response model, parametri,
  transazioni e ordine route invariati. Gli import privati usati da
  `straordinari_period_router.py` e i monkeypatch legacy su export,
  `shutil`/`subprocess` e `_resolve_device_label` restano validi tramite facade.
- OpenAPI Me byte-identica: `17` path e `17` operazioni, SHA-256
  `cb6eb0146e45c4d6d7b5631f48c4ee84ce7babce22f2a59e42e3eb63ea3d6c61`;
  anche la sequenza metodo/path coincide con lo snapshot precedente.
- Coverage finale: `129` test passati; `369/369` statement e `70/70` branch,
  `100%` sui sette runtime nuovi. `make quality-test`: `63 passed`.
- Metriche prima: LOC file `862`, callable `29`, cognitive sum/max `123/38`,
  cyclomatic sum/max `130/24`, LOC callable aggregata `765`, 18 violation
  callable e una violation file-level error. Dopo: LOC package `990`, callable
  `32`, cognitive `140/38`, cyclomatic `145/24`, file max LOC `336`.
- I 29 fingerprint legacy sono tutti riconosciuti e conservano esattamente
  cognitive `123`, cyclomatic `130`, LOC `765`, nesting, parametri e le 18
  violation. I tre callable aggiunti appartengono solo alla facade e non hanno
  violation. I blocchi `fmt: off` preservano il layout legacy misurato mentre
  l'intero package passa `ruff format --check`.
- Ruff check/format, compileall, diff check: `PASS`. Il ratchet globale contro
  la baseline autorevole `b1d4a988` resta rosso per regressioni storiche gia
  presenti in Elaborazioni, GIS, Presenze, Ruolo e frontend; nessun finding e
  attribuito a Me. `style-ratchet` usa correttamente il virtualenv ma resta
  rosso su 102 file storici non formattati. Baseline e tooling non aggiornati.
- Graphify aggiornato: backend `8.437` nodi, `21.457` archi e `471` community;
  platform docs `1.943` nodi, `4.348` archi e `143` community. Il primo tentativo
  docs ha superato il timeout sul singolo chunk; il retry incrementale ha
  estratto con successo tutti i sei file non in cache.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. La violation file-level e rimossa,
  il debito callable non e stato ridotto ne spostato. Prossima azione: scegliere
  una nuova slice indipendente; valutare GIS separatamente per rischio dominio.

## API/router modularization - GIS Platform router (2026-09-05)

- Scope: `backend/app/modules/gis/router.py` sostituito dal package facade
  compatibile `router/`; sette moduli mantengono i gruppi contigui
  catalogo/runtime, interrogazione/proxy/QGIS, import Shapefile, layer,
  annotazioni, permessi/change request ed export/audit.
- Invarianti: la facade registra prima i child router Scheda territoriale,
  QGIS external e QGIS OGC, quindi i 45 endpoint locali nello stesso ordine.
  Dipendenza `require_module("gis")`, tag, auth, modelli, parametri e transazioni
  sono invariati. Anche `endpoint.__module__ == "app.modules.gis.router"` e il
  forwarding legacy di `interrogazione_service`/`interroga` sono preservati.
- OpenAPI GIS byte-identica: `47` path e `51` operazioni, SHA-256
  `07d3eeae0e764aeff06e90d0b26704e0c976a8e53e8ea45717e39325f7ec2b95`;
  sequenza metodo/path/modulo/nome endpoint identica allo snapshot precedente.
- Coverage finale: `111` test passati; `272/272` statement e `24/24` branch,
  `100%` sui nove runtime nuovi. Suite GIS estesa: `220 passed`.
- Metriche prima: LOC file `587`, callable `46`, cognitive sum/max `6/2`,
  cyclomatic sum/max `52/3`, LOC callable `408`, nove violation callable per
  parametri e un warning file-level. Dopo: LOC package `709`, callable `49`,
  cognitive `23/8`, cyclomatic `67/7`, file max LOC `122`.
- Tutti i 46 fingerprint legacy conservano esattamente cognitive `6`,
  cyclomatic `52`, LOC `408`, nesting, parametri e nove violation. I tre
  callable nuovi appartengono soltanto alla facade e non hanno violation.
- Ruff check/format, compileall, diff check e `make quality-test` (`63 passed`):
  `PASS`. Il ratchet globale contro `b1d4a988` resta rosso con 100 finding
  storici, nessuno sotto `backend/app/modules/gis/router/`; lo style ratchet
  globale resta rosso su 105 file storici, mentre tutti i dieci file nuovi
  della slice passano.
- Graphify aggiornato: backend `8.493` nodi, `21.514` archi e `481` community;
  platform docs `1.946` nodi, `4.360` archi e `147` community. Il primo batch
  semantico e andato in timeout; il retry ha estratto tutti i sei file mancanti.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Il warning file-level e rimosso e il
  debito callable non e stato ridotto ne spostato. Baseline e tooling invariati;
  `gis/services.py` resta una eventuale slice separata ad alto rischio.

## API/router modularization - Catasto anagrafica router (2026-09-05)

- Scope: `backend/app/modules/catasto/routes/anagrafica.py` sostituito dal
  package facade compatibile `anagrafica/`; normalizzazione, export, upload,
  persone, intestatari, matching, resolver live/autoritativi, execution e route
  job/distretto hanno moduli con ownership separata.
- Invarianti: le 13 operazioni conservano ordine, metodo, path, nome e
  `endpoint.__module__ == "app.modules.catasto.routes.anagrafica"`. Auth,
  request/response model, query, transazioni, worker/recovery, accesso live
  Capacitas e punti di monkeypatch legacy restano invariati.
- OpenAPI isolata byte-identica: 11 path, SHA-256
  `c71647faeb8d71d05aa65ca2847e4ede74a2c2e4a4521e5a8a23afa8e9ff4709`;
  anche lo snapshot ordinato delle route coincide byte per byte.
- Coverage finale: `285 passed`; `1.791/1.791` statement e `634/634` branch,
  `100%` sugli 11 moduli runtime. `make quality-test`: `63 passed`.
- Metriche prima: LOC file `3.486`, callable `122`, cognitive sum/max
  `2.087/363`, cyclomatic sum/max `1.354/135`, una violation file-level error.
  Dopo: LOC package `4.335`, callable `125`, cognitive `2.101/363`, cyclomatic
  `1.367/135`, file max LOC `765`; nessun file supera la soglia error `800`.
- Ruff check/format, compileall e diff check: `PASS`. Il ratchet autorevole
  contro `main@33fbdb9c` non passa: 49 finding sono incrementi LOC dei callable
  legacy dopo la formattazione obbligatoria dei file nuovi; 20 record
  `new_callable_violation` riguardano sette callable spostati il cui fingerprint
  AST cambia con i nuovi confini/import. Baseline, matcher, eccezioni ed
  esclusioni non sono stati modificati.
- `make lint-backend` con il virtualenv resta rosso sul working tree condiviso:
  460 errori Ruff in modifiche esterne alla slice e due nuovi test worker non
  formattati. Il check Ruff mirato sui 15 file Catasto/test della slice passa;
  la failure globale non e stata modificata o assorbita.
- Esito: `REORGANIZED_AND_CHARACTERIZED`. Il monolite e rimosso e la soglia
  file-level e risolta, ma gli aggregati callable non dimostrano una riduzione.
  Stop condition: decidere in una change separata se migliorare il matching dei
  move modulari o ridurre realmente i callable segnalati; non iniziare un altro
  hotspot automaticamente.
- Graphify aggiornato: Catasto `1.117` nodi, `2.674` archi e `52` community;
  backend `8.668` nodi, `21.972` archi e `483` community; platform docs `1.953`
  nodi, `4.380` archi e `144` community; sei file semantici sono stati
  riestratti nel primo refresh e due nel riallineamento finale.

### Follow-up matching move modulari Catasto

- Scope: solo matcher e test del quality tooling; runtime Catasto, baseline,
  eccezioni e soglie invariati.
- Il matcher ora associa un callable a un path baseline rimosso quando il nome
  qualificato e unico, anche se alias/import necessari allo split cambiano il
  fingerprint AST. Se esistono piu candidati omonimi non sceglie; il callable
  resta nuovo e continua a essere soggetto alle soglie error-level.
- Test aggiunti: move unico con fingerprint diverso passa; una regressione del
  move riconosciuto fallisce; candidati omonimi multipli non ereditano debito.
  Suite tooling: `66 passed`; `py_compile` e diff check: `PASS`.
- Ratchet Catasto dopo il fix: nessuna ambiguita e nessuna
  `new_callable_violation`; tutti i move sono confrontati con la baseline e
  restano 60 `legacy_metric_regression`, esclusivamente sulla LOC. Cognitive,
  cyclomatic, nesting e parametri restano invariati.
- Una simulazione a 120 colonne con trailing comma non magiche lascia 20
  regressioni; una compressione a 1.000 colonne le nasconderebbe tutte ma e
  stata rifiutata come metric gaming. Prossima azione separata: riduzione reale
  o ripristino fedele del layout legacy dei callable, senza aggiornare la
  baseline per assorbire i delta.

### Follow-up layout legacy Catasto

- Scope: soli 11 moduli del package `catasto/routes/anagrafica`; matcher,
  baseline, soglie, eccezioni e comportamento runtime invariati.
- Per 49 callable con fingerprint AST identico e stato ripristinato byte per
  byte il segmento sorgente pre-change, recuperando le 230 LOC introdotte dal
  formatter. Per i 10 callable esterni con AST adattato allo split, il layout
  legacy e stato ricostruito applicando esclusivamente le differenze correnti;
  ogni candidato e stato confrontato con `ast.dump` prima della sostituzione.
  Il callable annidato `refresh_match` e compreso nel relativo segmento padre.
- Blocchi `fmt: off` iniziano dopo import e costanti, come nei precedenti split
  GIS/Me/Presenze: Ruff continua quindi a validare e ordinare gli import mentre
  preserva il layout misurato dei callable legacy. Nessuna compressione globale
  o configurazione a larghezza artificiale e stata applicata.
- Metriche finali: 12 file, LOC package `3.943`, callable `125`, cognitive
  sum/max `2.101/363`, cyclomatic sum/max `1.367/135`, file max LOC `712` in
  `matching.py`. Prima: LOC `3.486`, callable `122`, cognitive `2.087/363`,
  cyclomatic `1.354/135`, file max `3.486`; i tre callable aggiuntivi sono
  infrastruttura facade sotto soglia.
- Ratchet autorevole contro `main@c15f4e7a`: `PASS`, `findings: []`. Baseline,
  eccezioni ed esclusioni non aggiornate.
- Verifiche: `285 passed`; coverage `1.791/1.791` statement e `634/634` branch
  (`100%`); 13 route e 11 path OpenAPI byte-identici; Ruff check/format,
  compileall e diff check verdi; quality tooling `66 passed`.
- Esito finale invariato: `REORGANIZED_AND_CHARACTERIZED`. La violation
  file-level e rimossa e il ratchet non rileva debito callable spostato o
  peggiorato; nessuna riduzione cognitive/cyclomatic viene dichiarata.

### Chiusura e gate finali modularizzazione API/router (2026-09-06)

- Coverage frontend isolata sui 16 runtime API: `811 passed`, statement
  `1.263/1.263`, branch `826/826`, funzioni `420/420`, linee `1.195/1.195`.
- Coverage backend, con processi e file dati separati: Utenze `89 passed`
  (`870/870`, branch `220/220`), Network `68 passed` (`1.405/1.405`, branch
  `452/452`), Presenze `241 passed` (`2.292/2.292`, branch `696/696`), Me `48`
  test selezionati (`369/369`, branch `70/70`), GIS `73` test selezionati
  (`272/272`, branch `24/24`) e Catasto `285 passed` (`1.791/1.791`, branch
  `634/634`). Tutti i gate raggiungono `100%`.
- Statici: ESLint mirato senza errori e con 11 warning legacy nei test; Ruff
  check/format sui runtime e test nuovi, compileall e diff check passano;
  `make quality-test` passa con `66` test.
- Il typecheck globale e bloccato dalla modifica concorrente
  `frontend/src/app/presenze/festivita/page.tsx` (`HTMLArticleElement`). I
  ratchet globali restano rossi per modifiche concorrenti Elaborazioni/worker e
  debito di stile whole-file. Dopo la riduzione neutra di una lista intermedia,
  Network non introduce piu delta di codice; le sole segnalazioni dentro i
  file API estratti riguardano metriche gia presenti byte-identiche nel
  monolite a `main@c15f4e7a`, anteriori allo split. Baseline, eccezioni e scope
  non sono stati aggiornati.
- Classificazione conclusiva: `REORGANIZED_AND_CHARACTERIZED`. Contratti,
  facade e ordine route restano invariati; nessuna riduzione cognitiva o
  ciclomatica viene dichiarata.

### 2026-09-28 - Hotspot cooldown job Poste Online

- Scope: sola selezione del job in `CatastoWorker._next_posta_online_job_id`;
  filtro lazy dei job pronti e predicato dedicato per `retry_not_before`.
  Ordine FIFO, claim, credenziali, log e semantica dei timestamp invariati.
- Baseline di confronto: `HEAD@2d8a0634` per isolare il worktree e merge-base
  `origin/main` per il ratchet autorevole. Prima: metodo 15 cyclomatic,
  38 cognitive, 40 LOC, nesting 5. Dopo: metodo 7/11/29/3; predicato nuovo
  8/8/13/2. Cognitive aggregata della responsabilita 38 -> 19 e massimo
  cyclomatic 15 -> 8; nessuna nuova violation nel predicato.
- Il ratchet isolato `BASE_REF=HEAD` scende da 67 a 63 finding; quello
  autorevole contro `origin/main` da 76 a 72. Le quattro regressioni del
  metodo Poste sono rimosse. Baseline ed esclusioni non modificate; i finding
  residui degli altri hotspot non sono attribuiti a questa estrazione.
- Verifiche: test mirati del claim/cooldown `4 passed`; `make test-worker`
  `PASS`, `worker.py` 882/882 statement e 240/240 branch (`100%`). Ruff sul
  runtime `worker.py` passa. La suite worker globale e 99% per file SISTER
  non toccati; il ratchet di stile del checkout resta rosso per 50 rilievi
  preesistenti, inclusi test legacy nel perimetro Poste.
- Riverifica sul checkout concorrente del 2026-09-28: `make test-worker` senza
  root nel `PYTHONPATH` si ferma in collection su `test_sister_efficiency.py`
  (modifica SISTER non tracciata). `PYTHONPATH="$PWD" make test-worker` passa;
  `worker.py` 888/888 statement e 244/244 branch (`100%`). Il ratchet mirato
  del file lascia cinque finding SISTER, nessuno nel claim Poste. Graphify
  worker code e platform docs aggiornati. Il cooldown resta isolabile come
  filtro dei job `queued_resume` gia inclusi nella query del worker; il resto
  della feature Poste non e incluso nel commit di questo hotspot.
- Commit isolato: caratterizzazione aggiuntiva in
  `tests/test_posta_online_cooldown.py` (`7 passed`), senza includere nel
  commit il file legacy `test_worker.py` che ha 35 rilievi Ruff preesistenti.
  Lo snapshot staged e verificato separatamente dal worktree concorrente.
- Classificazione: `IMPROVED` per la complessita cognitiva del cooldown.
  Iterazione chiusa su un solo hotspot; restano altri rilievi Poste da
  affrontare separatamente prima del commit della feature completa.

### 2026-09-28 - Hotspot selezione retry AutoSync SISTER

- Slice autorizzata: eliminare lo stato derivato duplicato in `_ClaimScan`,
  senza modificare query, priorita CAPTCHA, deadline, pinning, lock o claim.
- Prima: `sister_worker_reliability.py` 800 LOC metriche e una violation
  file-level error; `_ClaimScan.record_deferred` 5 LOC, cognitive 1,
  cyclomatic 2. Baseline e altre modifiche del checkout restano invariate.
- Caratterizzazione aggiunta prima del refactoring: assenza di retry,
  minimo tra piu rinvii, zero valido e precedenza CAPTCHA in tutti i casi.
- Dopo: file 798 LOC, nessuna violation error-level; `record_deferred`
  4 LOC. Cognitive sum/max 199/16 e cyclomatic sum/max 213/11 invariati;
  49 callable invariati, nessuna estrazione o trasferimento di debito.
  Esito `IMPROVED` limitato a LOC e stato duplicato, non a cognitive/cyclomatic.
- Ratchet mirato contro `origin/main` (merge-base `c42bea845`): PASS,
  `findings: []`. Ratchet dei sei runtime SISTER: 15 -> 14 finding; restano
  gli altri rilievi, incluso il classificatore login (+2 LOC), fuori da questa
  singola slice. Baseline, eccezioni ed esclusioni non modificate.
- Verifiche: nuova caratterizzazione 10 test verdi prima e dopo;
  cinque file pytest isolati (`test_worker_repository`,
  `test_worker_reliability`, `test_sister_auth_gate`, `test_sister_claim_scan`,
  `test_sister_recovery_policy`) 151 test verdi, coverage del runtime
  `sister_worker_reliability.py` 522/522 statement e 140/140 branch (100%).
  Ruff runtime/test e formatter del nuovo test superati. Commit successivamente
  richiesto con validazione isolata del contenuto staged; nessun deploy.

## 2026-10-01 — recupero baseline e operazioni Presenze

Intervento circoscritto autorizzato dall'utente dopo il primo report di blocco.
Baseline GAIA riparata dal runtime committed invariato, in commit separato
`dc669728`, con comando `baseline-repair` fail-closed e 83 test tooling passati.
GATE applica il proprio comando di recupero in `3baaed8` (36 test tooling).

Il ratchet della feature confronta con quei commit, prima della sincronizzazione
delle baseline. Nessuna nuova esclusione o regressione assorbita. Serializzazione
condivisa dei bucket classificati, responsabilita esplicite per toolbar/riga
buoni, riuso del caricamento mensile, contratti giornalieri e editor null-safe:
`REORGANIZED_AND_CHARACTERIZED`, senza dichiarare riduzione di debito trasferito.
Runtime Presenze modificato coperto al 100%; dettagli e metriche nel report
`domain-docs/presenze/docs/IMPLEMENTATION_PRESENZE_COLLABORATORI_GIORNALIERE.md`.
