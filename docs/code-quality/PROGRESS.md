# Progress - GAIA Code Complexity Program

Questo file e la fonte di verita persistente. Hermes deve aggiornarlo dopo ogni
blocco verificato e prima di chiudere un goal.

### SISTER — stati del record estrazione (2026-10-05)

- Chiusura `IMPROVED`: mapper metadati e registrazione stato failed separati;
  creazione fallback nel catch resta nel coordinatore, non anticipata.
  Target cog/cyc/LOC/nesting18/13/26/2 ->12/9/16/2, mapper4/5/14/0,
  registrazione failed0/1/10/0. Helper sotto soglia, zero violation nel file;
  due warning eliminati senza trasferimento o nuovi wrapper artificiali.
- File cognitive sum/max59/18 ->57/12, cyclomatic58/13 ->60/9,
  branching48 invariato, callable10 ->12, LOC150 ->164 sotto soglia file;
  densita0.78 ->0.713415/import8 invariati. Aumento ciclomatico pari ai due
  nuovi callable, nessun branching aggiunto. Baseline/config/scope invariati.
- Nuova caratterizzazione prima del refactoring: observed_at invalida conserva
  parser_version/SHA gia aggiornati, vecchia data e identita existing; catch
  svuota payload e registra failed senza flush. 44 test persistenza/backfill
  PASS prima/dopo; full-file100% dopo statement91/branch18, zero missing,
  partial o esclusioni. Ordine SQL/add/flush, cache e SHA fuori try invariati.
- 320 casi differenziali contro `3673e60b`: SQL/parametri, ordine effetti,
  record/stato failed e input identici. Sessione recording con modelli reali,
  non test PostgreSQL. Ratchet merge-base, Ruff mirato, format-check test e
  whitespace PASS; lint globale compileall PASS, solo UP038 InCass concorrente.
- Aggiornamento Graphify codice backend e docs Catasto/piattaforma richiesto
  prima del commit separato; nessun push, change concorrenti preservate.
  Campagna globale non-MCP resta attiva, prossimo hotspot fuori da questo file.
- Preflight `3673e60b`: singolo hotspot persist_sister_visura18/13/26/2,
  due warning; file cognitive59/cyclomatic58/branching48/LOC150/dieci callable.
- Separare mapping metadati successful e registrazione failed dal coordinatore;
  costruzione e aggiornamenti restano nei rispettivi confini try/catch.
  Preservare identita existing, ordine assegnazioni e stato parziale se data
  osservazione invalida, cache e SHA fuori try, add/flush e transazioni.
- Coverage full-file100% e caratterizzazioni prima/dopo, trace differenziali,
  aggregati/ratchet contro HEAD pre-slice, baseline/config/scope invariati;
  commit separato autorizzato, change concorrenti preservate.

### SISTER — sostituzione record collegati (2026-10-05)

- Chiusura `IMPROVED`: responsabilita sostituzione figli isolata senza
  cambiare ordine delete/flush/owner/history o confini try/catch/transazioni.
  Target cog/cyc/LOC/nesting30/19/34/2 ->18/13/26/2; helper8/7/14/1
  sotto soglia. Due error diventano due warning nel coordinatore, non zero debito.
- File cognitive sum/max63/30 ->59/18, cyclomatic57/19 ->58/13,
  branching48 invariato, callable9 ->10, LOC144 ->150, densita0.833333 ->0.78.
  Un punto ciclomatico strutturale per nuovo callable, nessun branching o debito
  trasferito; import8 invariati. Baseline/config/scope/API invariati.
- Due caratterizzazioni nuove prima del refactoring: molteplicita e ordine
  figli, failure durante secondo evento con scritture parziali conservate.
  43 test persistenza/backfill PASS prima/dopo; full-file100% dopo
  statement86/branch18, zero missing/partial/esclusioni.
- 320 casi differenziali contro `db400891`: SQL/parametri, ordine effetti,
  campi record, stato failed e input invariati. Sessione recording con modelli
  reali; nessuna prova PostgreSQL dichiarata. Ratchet merge-base, Ruff mirato,
  format-check test e whitespace PASS; lint globale compileall PASS,
  UP038 InCass concorrente fuori slice resta, nessuna nuova failure locale.
- Graphify backend codice e docs Catasto/piattaforma da aggiornare prima del
  commit separato autorizzato; nessun push, change concorrenti preservate.
  Campagna non-MCP attiva: prossima slice distinta sui due warning residui.
- Preflight su `db400891`: singolo hotspot persist_sister_visura
  cog/cyc/LOC/nesting30/19/34/2, due error; file cognitive63/cyclomatic57,
  branching48/LOC144/nove callable. Baseline/config/scope invariati.
- Isolare responsabilita sostituzione figli: delete parcel/history, costruzione
  e flush parcel, owner poi eventi. Chiamata dopo flush extraction dentro try;
  SHA fuori try, cache, ordine SQL, catch e scritture parziali invariati.
- Caratterizzazione prima/dopo, coverage full-file100%, differenziale trace,
  aggregati e ratchet contro HEAD pre-slice; preservare change concorrenti.

### SISTER — avvio matching particella canonica (2026-10-05)

- Chiusura `IMPROVED`: normalizzazione strip payload condivisa, filtro comune
  unico per codice/nome, guardia riferimento vuoto fuori dall'iterazione.
  Codice prioritario anche con due match; fallback nome solo senza match codice,
  unico candidato richiesto. Campo canonico conserva casefold senza strip.
- Target cog/cyc/LOC/nesting29/26/18/1 ->8/8/18/1; filtro4/5/8/1,
  normalizzazione2/3/2/0, helper sotto soglia. Due error resolver eliminati;
  restano due error in persist_sister_visura30/19/34/2 invariato.
- File cognitive sum/max78/30 ->63/30, cyclomatic67/26 ->57/19,
  branching60 ->48, callable7 ->9, LOC134 ->144 sotto soglia file;
  import8 invariati, densita1.08209 ->0.833333. Riduzione aggregata reale,
  nessuna violation trasferita o nuova esclusione/baseline/config/API.
- Otto caratterizzazioni nuove sul runtime originale, 38 test prima/dopo;
  41 persistenza/backfill PASS. Full-file100% dopo statement84/branch18,
  zero esclusioni/missing/partial, nessuna nuova failure nel perimetro.
- 2352 input differenziali con codice/nome normalizzati, numerici/blank,
  missing foglio/particella e liste candidati ambigue: risultato, SQL/parametri
  e ordine accessi lazy alle proprieta canoniche identici al pre-slice `cccc8290`.
  Input invariati, sessione recording; nessuna prova PostgreSQL inventata.
- Ratchet merge-base `cccc8290`, Ruff mirato, format-check test e whitespace
  PASS. Lint globale .venv compileall PASS, UP038 InCass concorrente fuori
  slice resta. Graphify backend codice e docs Catasto/piattaforma aggiornati;
  commit separato, nessun push, change concorrenti preservate. Campagna
  globale non-MCP attiva; prossimo candidato persistenza ancora con due error.
- Mapping persistenza `cccc8290` committato; campagna non-MCP attiva.
- Singolo hotspot `_resolve_particella` cog/cyc/LOC/nesting29/26/18/1;
  file cognitive78/cyclomatic67/LOC134, sette callable/quattro error.
- Condividere normalizzazione riferimenti payload e filtro candidati comune
  per codice/nome. Codice ha priorita anche quando ambiguo; nome solo se
  codice non produce candidati. Assenza/ambiguita restituisce None.
- Query is_current/foglio/particella, strip/casefold distinti tra payload e
  campi canonici, lazy attribute access e ordine candidati devono restare identici.
- Test originali piu caratterizzazioni precedenza/ambiguita/whitespace/numerici;
  full-file100%, differenziali SQL/risultati, aggregati/ratchet/Ruff.
  Nessun intervento persistenza/transazioni/API/baseline/config/change concorrente.

### SISTER — avvio mapping persistenza visura (2026-10-05)

- Chiusura `IMPROVED`: mapper completi parcel/owner/history e conversione date
  condivisa; normalizzazione parcel non duplicata. Coordinatore conserva cache,
  add/flush/delete e loop/catch, senza commit/rollback o cambi di transazione.
- Target cog/cyc/LOC/nesting73/40/71/2 ->30/19/34/2; mapper parcel3/4/17/0,
  owner6/7/20/0, history2/3/16/0 e data1/2/2/0 sotto soglia. Nessuna violation
  trasferita. Warning LOC eliminato, restano quattro error nel file:
  due target e due resolver canonico29/26/18/1 invariato, non zero debito.
- File cognitive sum/max109/73 ->78/30, cyclomatic72/40 ->67/26,
  branching69 ->60, callable3 ->7, LOC112 ->134 sotto soglia file;
  import8 invariati, densita1.616071 ->1.08209. Riduzione aggregata reale,
  baseline/config/scope invariati. Import e isinstance(date) allineati a Ruff
  nel file modificato, senza cambio funzionale o nuove esclusioni.
- 30 caratterizzazioni nuove prima/dopo, 33 test persistenza/backfill PASS;
  full-file100% statement78/branch16, zero esclusioni/missing/partial.
  Cache SHA/version, stato failed, query/deduplica, CF/date e matching canonico,
  SHA fuori try e scritture parziali prima del catch dimostrati dai trace.
- 320 input differenziali con owner/date/canonici/existing e failure inject:
  SQL e ordine/payload side-effect, campi record e stato errore identici al
  pre-slice `078c3ec5`, input invariati. Test usano sessione recording e modelli
  reali; non dichiarare un test PostgreSQL non eseguito.
- Ratchet merge-base `078c3ec5`, Ruff mirato, format-check nuovo test e
  whitespace PASS. Lint globale .venv compileall PASS; UP038 InCass concorrente
  fuori slice resta, nessuna nuova failure nel perimetro. Graphify backend
  codice e docs Catasto/piattaforma aggiornati; commit separato, nessun push.
  Campagna globale non-MCP attiva, change concorrenti preservate.
- NavItem `078c3ec5` sotto soglia e committato; campagna non-MCP attiva.
- Singolo hotspot `persist_sister_visura` cog/cyc/LOC/nesting73/40/71/2;
  `_resolve_particella`29/26/18/1 resta fuori refactoring, file LOC112,
  tre callable/cinque violation (quattro error/un warning).
- Separare costruzione record parcel/owner/history e conversione date comune;
  mantenere nel coordinatore cache, add/flush/delete, loop e try/catch.
- Preservare SHA fuori try, cache parser-version, query/ordine SQL, matching
  canonico, normalization CF, stato/payload ed errori, anche scritture parziali
  prima del catch. Nessun commit/rollback aggiunto, transazioni/API/schema intatti.
- Test di caratterizzazione full-file prima/dopo e trace SQL/side-effect,
  metriche/aggregati e ratchet merge-base, Ruff. Nessuna nuova esclusione,
  baseline/config o intervento su change concorrenti; commit separato.

### Frontend layout — avvio presentazione NavItem (2026-10-05)

- Chiusura `IMPROVED`: componente privato stateless responsabile di classi,
  icona/label/badge, accessibilita e Link/span disabled, senza nodo DOM extra.
  Stato/listener/click restano nel pubblico; defaults e handler inoltrati.
  Predicato pathMatches duplicato nei rami hash fattorizzato in path && hash.
- La sola separazione aveva cognitive aggregata38 invariata: non dichiarata
  riduzione. Il factoring path/hash porta riduzione aggregata reale38 ->33;
  nessun debito trasferito. Target18/13/75/2 ->8/7/39/1, presentazione5/6/38/1,
  tutti sotto soglia: eliminati tre warning, zero violation nel file.
- File cognitive sum/max38/18 ->33/8, cyclomatic41/13 ->41/7,
  branching29 ->28, callable12 ->13, LOC128 ->134 sotto soglia;
  cinque import/uno state/uno effect invariati. Nessun cambiamento API/UI,
  esclusione, baseline/config o comportamento click/ordine degli effetti.
- Una nuova caratterizzazione sul runtime originale per transizioni
  disabled/enabled/active; 29 test prima/dopo, 44 NavItem/AppShell PASS.
  Full-file100% dopo statement45/branch42/function13/line40, contatori
  positivi, zero esclusioni. Nessuna failure nuova.
- 10080 rendering differenziali (espansione componente privato fino ai nodi
  DOM) e 2048 click: albero/attributi, ordine/payload effetti, URL e prevented
  identici al pre-slice `75062829`. Listener/cleanup/transizioni anche in suite.
- Ratchet merge-base `75062829`, ESLint, typecheck no-emit e whitespace PASS;
  Graphify frontend codice e docs piattaforma aggiornati. Commit separato,
  nessun push, change concorrenti preservate. Campagna globale non-MCP attiva:
  NavItem sotto soglia, prossimo candidato da inventory oltre questo componente.
- Click hash `75062829` committato; campagna non-MCP attiva. Singolo hotspot
  NavItem cog/cyc/LOC/nesting18/13/75/2; file cognitive38/cyclomatic41/LOC128,
  tre warning. Separare presentazione stateless da stato/listener/click.
- Componente privato responsabile di classi/accessibilita/icona/label/badge e
  Link o span disabled; nessun hook o nuovo nodo DOM. Defaults restano nel
  componente pubblico, eventi inoltrati, stessa precedenza disabled/active.
- Preservare DOM/attributi/ordine, badge0 e varianti, href/hash/alias e click,
  transizioni enabled/disabled/active, listener/cleanup. Full-file100% e
  caratterizzazione prima/dopo, differenziali DOM/click, aggregati e ratchet.
- Un hotspot revisionabile, nessuna API/config/baseline/esclusione o change
  concorrente modificata; commit separato. Nessuna nuova violation nel componente.

### Frontend layout — avvio click hash navigazione (2026-10-05)

- Chiusura `IMPROVED`: filtro click ordinario condiviso, reset hash completa
  responsabilita side-effect con guard clause. Handler conserva short-circuit
  e fallback timeout unico; URL creato solo per click ammessi. Stesso ordine
  prevent/history/state/scroll/popstate, stesso catch scroll e payload.
- `handleClick` cog/cyc/LOC/nesting21/11/27/3 ->5/4/6/1; helper filtro5/6/3/0,
  reset4/4/19/1, nessuna violation trasferita. `NavItem`34/20/96/3 ->18/13/75/2:
  tre error eliminati, restano tre warning sul componente, non zero debito.
- File cognitive sum/max61/34 ->38/18, cyclomatic45/20 ->41/13,
  branching35 ->29, callable10 ->12, LOC127 ->128 sotto soglia file;
  cinque import/uno state/uno effect invariati. Riduzione aggregata reale,
  nessuna nuova esclusione/baseline/config/API o alterazione UI.
- Due nuove caratterizzazioni sul runtime originale per query/ordine effetti;
  28 test prima/dopo, 43 test NavItem/AppShell PASS. Full-file100% dopo
  statement47/branch44/function12/line42, contatori positivi/zero esclusioni.
- 2048 click differenziali, sedici combinazioni modifiers/button/prevented,
  href/location/query/hash e scroll con/senza eccezione: ordine e payload
  effetti, URL e stato prevented identici al pre-slice `44332843`.
  10080 rendering differenziali completi identici; hook/eventi anche nella suite.
- Ratchet merge-base `44332843`, ESLint, typecheck no-emit e whitespace PASS;
  Graphify frontend codice e docs piattaforma aggiornati. Commit separato,
  nessun push, change concorrenti preservate. Campagna non-MCP attiva;
  NavItem ancora con tre warning, da trattare nella prossima unita revisionabile.
- Matching `44332843` committato, campagna globale non-MCP attiva. Singolo
  hotspot `handleClick` cog/cyc/LOC/nesting21/11/27/3, contenuto in NavItem
 34/20/96/3; file cognitive61/cyclomatic45/LOC127, cinque violation.
- Separare filtro click ordinario dal reset hash stessa URL: short-circuit
  identico, URL costruito solo per click ammessi, path+search e ordine effetti
  preventDefault/history/state/scroll/popstate invariati, catch scroll invariato.
- Handler resta chiusura state con fallback timeout unico, helper completi
  senza duplicazioni/wrapper; nessun cambio API/UI o hook/listener/cleanup.
- Test su runtime originale per query coincidente/ordine effetti e mancato
  timer in reset; full-file100%, ratchet merge-base, metriche/aggregati,
  ESLint/typecheck. Nessuna esclusione/baseline/config/change concorrente.

### Frontend layout — avvio matching navigazione (2026-10-05)

- Chiusura `IMPROVED` limitata al matching: href/alias normalizzati dallo
  stesso helper, predicato exact/prefix condiviso per tutti i target senza
  duplicazione. Hash precedence/inactive, query e click handler restano invariati;
  hook, listener/cleanup e rendering non spostati o alterati.
- Target cog/cyc/LOC/nesting42/28/106/3 ->34/20/96/3; helper split2/3/7/0 e
  matching2/3/7/0, callback2/3/1/0, tutti sotto soglia, nessuna violation
  trasferita. Restano cinque violation (tre error/due warning) nel file:
  target ancora sopra soglia e handleClick21/11/27/3 invariato.
- File cognitive sum/max65/42 ->61/34, cyclomatic47/28 ->45/20,
  branching39 ->35, callable8 ->10, LOC123 ->127 sotto soglia file,
  cinque import/uno state/uno effect invariati. Riduzione aggregata reale,
  nessuna esclusione/baseline/config/API modificata, non zero debito.
- 26 caratterizzazioni prima/dopo con Link mock che inoltra i click; hash,
  alias/slash, query, modifiers/prevented, timeout/scroll eccezione, badge0 e
  disabled verificati. 41 test NavItem/AppShell PASS; full-file100% dopo
  statement44/branch42/function10/line40, contatori positivi/zero esclusioni.
- 10080 rendering differenziali pre-slice `e20d355e`, combinazioni href/alias/
  hash/match/badge/disabled: albero completo/props identici. Hook stub nel
  differenziale, comportamento hook/eventi/click dimostrato dalla suite dedicata.
- Ratchet merge-base `e20d355e`, ESLint, typecheck no-emit e whitespace PASS.
  Graphify frontend codice force/pruning e docs piattaforma aggiornati;
  commit separato, nessun push, change concorrenti preservate. Campagna globale
  non-MCP attiva; prossimo candidato nello stesso componente ancora in debito.
- Bonifica `e20d355e` committato; campagna non-MCP attiva. Singolo hotspot
  `NavItem`, cog/cyc/LOC/nesting42/28/106/3, file LOC123/otto callable,
  cinque violation (tre error/due warning); handleClick21/11/27/3 resta separato.
- Condividere normalizzazione href/alias e matching path per target principale
  e alias, eliminando predicati duplicati. Preservare exact/prefix con confine
  slash, hash richiesto/inactive, query, ordine hook/listener/cleanup e DOM.
- Caratterizzare click reali col mock Link che inoltra onClick: hash clearing,
  modifiers/defaultPrevented, timer/scroll eccezione, badge/disabled e alias.
  Coverage full-file100% prima/dopo, metriche aggregate e ratchet merge-base.
- Un solo hotspot revisionabile, nessuna modifica API/UI/config/baseline o
  esclusione, change concorrenti preservate; commit separato richiesto.

### Elaborazioni — avvio parser form Bonifica (2026-10-05)

- Chiusura `IMPROVED`: select e checkbox letti da helper con responsabilita
  completa, raccolta input preserva checkbox/radio/default con guard clause;
  scansione conserva textarea/skip e ordine. Nessun wrapper artificiale,
  valore/ordine chiavi/sovrascritture e liste fresche invariati.
- Target cog/cyc/LOC/nesting51/21/36/4 ->12/7/14/3; helper select6/6/6/1,
  checkbox3/4/7/1 e raccolta input7/7/12/2, tutti sotto soglia. Tre violation
  (due error/un warning) ->zero; nessuna violation trasferita.
- File cognitive sum/max61/51 ->38/12, cyclomatic32/21 ->35/7:
  tre basi callable aggiunte, branching28 invariato; callable4 ->7, LOC65 ->68
  sotto soglia, import2 invariati. Riduzione cognitiva aggregata reale;
  nesting del primo helper input ancora4 corretto con guard clause, non
  assorbito in baseline. Nessuna nuova esclusione/baseline/config/API.
- 34 nuove caratterizzazioni sul runtime originale, 34 test prima/dopo;
  full-file100% dopo statement67/branch38, zero esclusioni/missing/partial.
  5000 documenti differenziali con nomi duplicati/tipi misti/ordine casuale:
  valori completi e ordine chiavi identici al pre-slice `45741085`.
- Ratchet merge-base `45741085`, Ruff mirato, format-check nuovo test e
  whitespace PASS. Lint globale .venv compileall PASS, UP038 InCass concorrente
  fuori slice. Test integrazione Python sistema non collezionabile per
  geoalchemy2 mancante; rieseguito nel virtualenv completo, cinque test pertinenti
  PASS (36 deselezionati), nessuna nuova failure applicativa.
- Graphify backend codice e docs Elaborazioni/piattaforma aggiornati tramite
  target dedicati; commit separato, nessun push. Campagna globale non-MCP
  attiva, modifiche concorrenti preservate; zero debito nel file, non nel repo.
- Ruolo `45741085` verificato e committato; campagna tutti hotspot non-MCP
  attiva. Singolo hotspot `parse_form_fields` cog/cyc/LOC/nesting51/21/36/4;
  file LOC65, quattro callable, tre violation (due error/un warning).
- Separare lettura select e raccolta input checkbox/radio dalla scansione
  del documento, responsabilita complete senza wrapper artificiali.
- Preservare normalizzazione markup, ordine chiavi/sovrascritture duplicate,
  nomi[]/multiple, checkbox append/copia e defaulton, radio checked/primo vuoto,
  disabled e campi hidden, trim textarea e campi token/method ignorati.
- Caratterizzazioni sul runtime originale, full-file100%, metriche/aggregati
  e ratchet merge-base, Ruff; nessuna nuova esclusione/baseline/API/config o
  modifica concorrente. Commit separato per una sola unita revisionabile.

### Ruolo — avvio layout parsing particelle (2026-10-05)

- Chiusura `IMPROVED`: otto layout di colonne e quattro varianti testuali
  dichiarativi sostituiscono la catena annidata. `_particella_columns` seleziona
  solo sulla colonna ambigua originale, poi mappa campi; conversione comune
  riusa il parser Decimal gia esistente, senza helper pass-through.
- Target cog/cyc/LOC/nesting66/25/90/8 ->12/10/24/1; nuovo selettore5/5/7/1
  sotto soglia. File cognitive sum/max75/66 ->25/12, cyclomatic37/25 ->25/10,
  branching31 ->19, LOC144 ->140, sei callable/quattro import invariati.
  Quattro error ->un warning ciclomatico sul target, nessun debito trasferito.
- Sei nuove caratterizzazioni sul runtime originale, 23 test prima/dopo;
  full-file100% dopo statement65/branch12, zero esclusioni/missing/partial.
  20000 input differenziali su lunghezze0/18, varianti/colonne extra/numerici,
  NaN/Infinity e equals: campi completi/eccezioni identici e input invariati.
- Ratchet merge-base `d88b4370`, Ruff mirato e whitespace PASS;
  baseline/config/scope invariati. Lint globale con .venv compileall PASS,
  resta UP038 nel file InCass concorrente fuori slice, non modificato.
  Nessuna nuova failure nel parser o nei test pertinenti.
- Graphify Ruolo codice force/pruning per rimuovere safe_decimal e docs
  Ruolo/piattaforma aggiornati; commit separato, nessun push. Campagna globale
  non-MCP attiva, modifiche concorrenti preservate; warning target resta visibile.
- Network `d88b4370` committato; campagna tutti hotspot non-MCP attiva.
- Singolo hotspot `parse_particella_line`: cog/cyc/LOC/nesting66/25/90/8,
  quattro error; file LOC144, sei callable, cognitive75/cyclomatic37.
- Sostituire la catena per lunghezza con layout dichiarativi di colonne,
  variante testuale scelta solo sulla colonna originale ambigua. Preservare
  righe4/5/6/7/8/9/10/11+, subalterno/coltura e colonne ignorate, guardie
  equals/foglio/particella, Decimal e zero catastale ->ettari None.
- Conversione/assemblaggio comune senza helper pass-through; niente nuova
  esclusione o modifica API/schema. Test originali piu casi limite prima
  runtime, full-file100%, ratchet merge-base e aggregati; commit separato.

### Network — avvio detector watchlist (2026-10-05)

- Chiusura `IMPROVED`: strategie matching lazy per keyword/domain/url/IP,
  normalizzazione campi condivisa, watchlist con guard clause, normalizzazione
  porta separata dall'applicazione dei tag. Ordine/deduplica e allow finale
  preservati. Eliminato solo append encrypted_dns provatamente irraggiungibile.
- Target cog/cyc/LOC/nesting107/39/62/6 ->6/7/25/0, cinque parametri invariati.
  File cognitive sum/max111/107 ->39/12, cyclomatic44/39 ->39/7,
  branching42 ->31, callable2 ->8, LOC136 ->161 sotto soglia, import3 invariati.
  Tre lambda di matching senza branching nel registro; nessun debito imperativo
  nascosto, nuovi helper sotto soglia, zero violation trasferite.
- Cinque violation (tre error/due warning) ->un warning legacy sui cinque
  parametri pubblici. Zero error, API non alterata per eliminare questo warning.
  La prima estrazione aveva nuovo helper ciclomatico15: respinta dal ratchet,
  sostituita da registro lazy/normalizzazione condivisa, non assorbita in baseline.
- 64 test di caratterizzazione prima/dopo. Prima98% per singolo ramo morto;
  dopo full-file100% statement65/branch26, zero esclusioni/missing/partial.
  2940 input differenziali: tag e ordine identici, default watchlist identici
  e input invariati. 43 test dei chiamanti services/router helpers PASS.
- Ratchet merge-base `0d6346de`, Ruff mirato e format-check nuovo test PASS;
  whitespace PASS, baseline/config/scope invariati. `make lint-backend` con
  python sistema manca Ruff; con QUALITY_PYTHON=.venv/bin/python compileall PASS,
  lint globale fallisce solo UP038 nel file concorrente
  `backend/app/services/elaborazioni_capacitas_incass.py:1041`, fuori slice.
  Nessuna nuova failure nel detector/test; non modificare la change concorrente.
- Graphify Network codice e docs/piattaforma aggiornati con target dedicati;
  commit separato, nessun push. Campagna non-MCP attiva, altri file preservati.
- Passaggio Catasto `0d6346de` committato, file sotto soglia; campagna tutti
  gli hotspot non-MCP resta attiva. Inventory working tree aggiornata: 4319
  violation in 708 file, filtro operativo wiki/MCP senza cambiare scope dei gate.
- Singolo hotspot `event_detection_tags`, cog/cyc/LOC/nesting107/39/62/6,
  cinque parametri; file LOC136, due callable, cinque violation (tre error).
- Separare normalizzazione/matching watchlist e tagging porte, mantenendo
  ordine/deduplica e allow applicato per ultimo. Preservare precedence fallback
  porte, input non-stringa, categorie ignote, mode non-allow e matching lazy.
- Il secondo append encrypted_dns e irraggiungibile: sotto la stessa guardia
  port_tag e gia stato inserito in tags; se e encrypted_dns, not-in e falso.
  Documentare la prova e rimuovere solo questo ramo senza effetti osservabili.
- Test di caratterizzazione prima del runtime e full-file100% dopo; metriche,
  aggregati, ratchet merge-base e Ruff. Nessuna nuova esclusione/baseline/config
  o modifica concorrente; commit separato per una sola unita revisionabile.

### Catasto frontend — avvio registro spiegazioni (2026-10-05)

- Chiusura `IMPROVED`: definizioni tipizzate con testi guida e strategia di
  calcolo nello stesso catalogo; lookup Map elimina i sette case di dispatch.
  Assemblaggio comune conserva ordine chiavi e copie delle liste; strategia
  imponibile produce direttamente calcoli, senza wrapper/violation trasferite.
  La strategia VAL-03 alloca una lista vuota nuova per ciascuna spiegazione.
- Target cog/cyc/LOC/nesting20/12/42/1 ->2/3/6/1; sei nuove strategie sotto
  soglia (massimo cog/cyc1/2), imponibile6/6/26/1 invariato nelle metriche.
  Eliminati entrambi i warning: zero error/zero warning nel file, non nel repo.
- File cognitive sum/max58/20 ->41/6, cyclomatic71/12 ->69/6,
  branching44 ->36, callable27 ->33, LOC374 invariato, tre import invariati;
  densita0.34492 ->0.294118. Riduzione reale del dispatch e aggregati,
  nessun debito trasferito o nuova esclusione/baseline/config.
- Sette caratterizzazioni sul runtime originale per calcoli codice comune
  null/falsy/array/oggetto; 89 test prima/dopo. Full-file100% dopo:
  statement113/branch76/function33/line101, contatori tutti positivi e zero
  esclusioni. 22275 input differenziali, due export/output completo/ordine
  e input invariati rispetto al pre-slice `4bd2805b`.
- Ratchet merge-base `4bd2805b`, ESLint, typecheck no-emit e whitespace PASS.
  Graphify frontend codice aggiornato con patch pruning e force per rimuovere
  simbolo privato rinominato; docs dedicate Catasto/piattaforma aggiornate.
  Commit separato, nessun push; campagna tutti gli hotspot non-MCP attiva,
  modifiche concorrenti preservate. Il prossimo hotspot va scelto dall'inventory
  globale, senza restringere la campagna a questo file ora sotto soglia.
- Passaggio `4bd2805b` verificato e committato; campagna non-MCP attiva,
  singolo hotspot `explainCatastoAnomalia`, commit separato richiesto.
- Prima cog/cyc/LOC/nesting20/12/42/1; file cognitive58/max20,
  cyclomatic71/max12, LOC374, ventisette callable/tre import; due warning.
- Unire testi guida e strategie di calcolo nello stesso catalogo tipizzato,
  lookup Map privato senza chiavi prototype; assemblaggio comune e liste
  sempre fresche. Calcoli imponibile riusati direttamente, niente wrapper.
- Preservare ordine, testo, locale/precisione, truthiness/null, array-oggetto,
  flag strict-true, fallback e indipendenza/mutabilita dei risultati e input.
  Test sul runtime originale, full-file100%, ratchet merge-base e aggregati;
  nessuna esclusione, modifica baseline/config o intervento su change parallele.

### Catasto frontend — avvio registro descrizioni (2026-10-05)

- Chiusura `IMPROVED`: selezione condizionale sostituita da registro Map
  privato di testi/formatter completi per tipo; imponibile riusato direttamente.
  Nessun wrapper triviale per il testo costante, nessuna ereditarieta prototype
  nel lookup. Ordine/testo/conversioni e fallback vuoto/null restano invariati.
- Target cog/cyc/LOC/nesting22/13/41/1 ->4/5/6/1, entrambi i warning eliminati.
  Cinque formatter nuovi sotto soglia, massimo cog/cyc1/2; nessuna violation
  trasferita. Restano due warning su `explainCatastoAnomalia`, zero error.
- File cognitive sum/max75/22 ->58/20, cyclomatic73/13 ->71/12;
  branching51 ->44, callable22 ->27, LOC365 ->374 sotto soglia file,
  densita0.405479 ->0.34492. Riduzione del dispatch e degli aggregati reale;
  nessun nuovo import/esclusione, baseline/config/scope invariati.
- Dieci caratterizzazioni sul runtime originale per fallback prototype e
  codice comune null/falsy/array/oggetto; 82 test prima/dopo. Full-file100%
  dopo: statement111/branch82/function27/line100, contatori tutti positivi,
  zero esclusioni. 22275 input differenziali per entrambi gli export:
  output completo/ordine e input invariati rispetto al pre-slice `828f8cc6`.
- Ratchet merge-base `828f8cc6`, ESLint, typecheck no-emit e whitespace PASS;
  Graphify frontend codice e docs dedicate Catasto/piattaforma aggiornati.
  Commit separato per passaggio, nessun push; campagna non-MCP attiva,
  modifiche concorrenti preservate. Prossimo candidato: spiegazioni Catasto.
- Passaggio precedente `828f8cc6` verificato e committato; campagna non-MCP
  attiva, un hotspot revisionabile e commit separato per passaggio.
- Target `describeCatastoAnomalia` cog/cyc/LOC/nesting22/13/41/1;
  file cognitive75/max22, cyclomatic73/max13, LOC365, ventidue callable,
  quattro warning e zero error. Il dispatch ripete la selezione per tipo.
- Registro privato Map di descrizioni statiche o formatter di dominio;
  responsabilita testuale completa per voce, helper imponibile riusato senza
  wrapper. Preservare testi, spazi/ordine, conversioni, null/truthiness e
  fallback anche per chiavi prototype. Nessun cambiamento API/UI/calcoli.
- Acquisire caratterizzazioni sul runtime originale, full-file100%, metriche
  aggregati/violation e ratchet merge-base; nessuna nuova esclusione/baseline
  o modifica concorrente. Valutare solo riduzione reale del dispatch.

### Catasto frontend — avvio catalogo testi guida (2026-10-05)

- Chiusura `IMPROVED`: catalogo privato tipizzato dei testi VAL-01/07 nello
  stesso file; assemblaggio comune conserva ordine chiavi e copie delle liste.
  Fallback ignoti separato, senza lookup di nomi prototype; testi/calcoli,
  input, mutabilita e indipendenza dei risultati invariati.
- Target cog/cyc/LOC/nesting24/14/152/1 ->20/12/42/1; assemblaggio0/1/14/0,
  fallback2/3/17/0, imponibile6/6/26/1: nessuna violation nei nuovi helper.
  Eliminato error LOC e relativo warning; zero error e quattro warning residui
  nei due export, non zero debito. Nessuna nuova esclusione o import.
- File cognitive sum/max77/24 ->75/22, cyclomatic71/14 ->73/13:
  aumento di due basi callable, branching51 invariato; venti ->ventidue callable.
  LOC353 ->365 per catalogo dichiarativo/assemblaggio, sotto soglia file;
  riduzione LOC del target e cognitive aggregata, nessun debito trasferito.
- Tre caratterizzazioni prima del runtime, 72 test prima/dopo; full-file100%
  statement110/branch87/function22/line100, tutti contatori coperti e nessuna
  esclusione. 22275 input differenziali per entrambi gli export, inclusi tipi
  prototype/null/zero/invalidi/flag strict-true: output completo/ordine identici.
- Ratchet merge-base `f73ff8f8`, typecheck no-emit, ESLint e whitespace PASS;
  baseline/config/scope invariati. Graphify frontend codice aggiornato; docs
  Catasto/piattaforma aggiornate con target dedicati. Commit separato, nessun
  push; campagna non-MCP attiva, modifiche concorrenti preservate.
- Campagna tutti gli hotspot non-MCP attiva; precedente passaggio `f73ff8f8`
  progresso verificato, commit separato ad ogni passaggio.
- Singolo hotspot `explainCatastoAnomalia`: prima cog/cyc/LOC/nesting24/14/152/1,
  file cognitive77/24, cyclomatic71/14, LOC353, venti callable/tre import;
  un error LOC e quattro warning. Separare testi guida dichiarativi dai calcoli.
- Catalogo privato tipizzato solo per tipi noti, assemblaggio con copie delle
  liste e chiavi nell'ordine originale; fallback ignoti/prototype invariato.
  Preservare testi, calcoli, locale/precisione, input e mutabilita/indipendenza.
  Nessuna nuova esclusione, import o wrapper artificiale; nessun debito
  imperativo trasferito nel catalogo. Test prima/dopo e full-file100% richiesti.

### Catasto frontend — avvio spiegazione imponibile VAL-06 (2026-10-05)

- Chiusura `IMPROVED`: helper di dominio `explainImponibile` contiene calcoli,
  formule e istruzioni VAL-06; `pushCalculationText` riusato per percentuale
  e cinque riferimenti sorgente, con truthiness/String identici per dati JSON.
  Nessun helper vuoto o nuovo predicato duplicato; campo comune resta non-null.
- Target cog/cyc/LOC/nesting47/25/191/2 ->24/14/152/1; helper6/6/42/1,
  un parametro e zero violation. Due error (cognitive/cyclomatic) diventano
  warning; file ancora un error LOC e quattro warning, non zero debito.
- File cognitive sum/max94/47 ->77/24, cyclomatic76/25 ->71/14,
  branching57 ->51, LOC350 ->353, venti callable/tre import;
  densita scanner0.485714 ->0.419263. Riduzione aggregata reale, non trasferita.
- Otto nuove caratterizzazioni sul runtime originale: mutabilita/indipendenza
  risultati e liste per tutti gli otto tipi, input invariato. 69 test prima/dopo;
  full-file100% dopo: statement106/branch87/function20/line96 contatori coperti,
  zero esclusioni. 5400 input differenziali, due export completi/otto tipi,
  testo/ordine identici al runtime pre-slice `6acc9feb`.
- Ratchet merge-base `6acc9feb`, typecheck no-emit, ESLint e whitespace PASS;
  baseline/config/scope invariati. Graphify frontend codice e docs dedicati
  Catasto/piattaforma aggiornati; commit separato, nessun push. Campagna attiva
  tutti gli hotspot non-MCP; change concorrenti preservate.
- Campagna tutti gli hotspot non-MCP attiva, commit ad ogni passaggio;
  precedente passaggio `6acc9feb` progresso verificato.
- Singolo hotspot `explainCatastoAnomalia`: prima cog/cyc/LOC/nesting47/25/191/2,
  file cognitive94/47, cyclomatic76/25, LOC350, diciannove callable/tre import.
- Separare spiegazione completa imponibile (calcoli/formule/nota e istruzioni)
  dal dispatch. Preservare ordine, etichette/testo/locale/precisione, guardie,
  flag strict-true, null/invalidi, oggetti/array freschi e input immutati.
  Helper di dominio non vuoto, senza spostare violation, altri casi invariati.
- Test sul runtime originale, full-file100%, ratchet merge-base e aggregati;
  nessuna modifica baseline/config/scope o change parallela/MCP.

### Catasto frontend — avvio descrizioni misure e imponibile (2026-10-05)

- Chiusura `IMPROVED`: riferimenti formattati riusano il predicato condiviso
  con suffisso per unita; `describeImponibile` gestisce il paragrafo completo
  VAL-06 senza duplicazioni. Target cog/cyc/LOC/nesting34/19/49/1 ->22/13/41/1;
  helper imponibile2/3/11/0, nessuna violation. Helper riferimenti sotto soglia,
  tre parametri per suffisso default. Due error target diventano warning,
  file ora tre error e due warning (cinque violation totali), non zero debito.
- File cognitive sum/max104/47 ->94/47, cyclomatic79/25 ->76/25,
  branching61 ->57, LOC347 ->350; diciannove callable/tre import.
  Densita scanner0.527378 ->0.485714, nessun trasferimento del debito.
- Dieci caratterizzazioni aggiunte sul runtime originale, 61 test prima/dopo;
  full-file100% dopo: statement100/branch99/function19/line89 contatori tutti
  coperti, zero esclusioni. 5400 input differenziali per due export/otto tipi,
  inclusi flag strict-true e valori null/zero/invalidi, identici al pre-slice.
- Ratchet merge-base `1b0d72bd`, typecheck no-emit, ESLint e whitespace PASS.
  Baseline/config/scope invariati, altre change preservate, MCP non toccato.
  Graphify frontend codice e docs Catasto/piattaforma aggiornati; commit
  separato ad ogni passaggio come richiesto, nessun push. Goal campagna attivo.
- Campagna tutti gli hotspot non-MCP attiva, commit ad ogni passaggio;
  precedente passaggio `1b0d72bd`, classificato progresso verificato.
- Singolo hotspot `describeCatastoAnomalia`: prima cog/cyc/LOC/nesting34/19/49/1,
  file cognitive104/47, cyclomatic79/25, LOC347, diciotto callable/tre import.
- Riutilizzare descrizione riferimenti per valori formattati/unità e isolare
  il paragrafo imponibile come responsabilita di dominio. Preservare valuta,
  precisione/locale, zero/null/invalidi, flag catastale strict-true, testo/ordine
  e altri export. Valori `dati_json` conformi al contratto JSON, nessuna nuova
  astrazione generale, wrapper vuoto o duplicazione dei predicati.
- Caratterizzare prima del runtime, full-file100%, metriche/aggregati e ratchet
  merge-base; nessuna modifica baseline/config/scope o change parallela.

### Campagna tutti gli hotspot non-MCP — avvio (2026-10-05)

- Passaggio riferimenti sorgente `IMPROVED`: `describeSourceReference` contiene
  il predicato truthy e la conversione/testo condivisi da cinque campi.
  Target cog/cyc/LOC/nesting44/24/49/1 ->34/19/49/1; helper1/2/3/0,
  due parametri e zero violation. File cognitive113 ->104, cyclomatic82 ->79,
  branching65 ->61, LOC344 ->347, diciotto callable/tre import.
  Restano cinque error nel file, nessun trasferimento del debito.
- Nove caratterizzazioni sul runtime originale, 51 test prima/dopo;
  full-file100% statement99/branch106/function18/line88 dopo, zero esclusioni.
  3600 input differenziali con due export/otto tipi/ordine chiavi invertito,
  output identici alla copia pre-slice. Ratchet merge-base `ad1fd588`, ESLint,
  typecheck no-emit e whitespace PASS. Baseline/config/scope invariati.
- Graphify frontend codice e docs Catasto/piattaforma aggiornati tramite
  target dedicati; commit di questo passaggio separato, nessun push.
  La campagna resta attiva: le violation residue non sono dichiarate risolte.
- Goal esplicito: proseguire tutti gli hotspot, commit ad ogni passaggio,
  MCP escluso da questa fase. Esclusione operativa, non modifica di scope/
  baseline/gate; preservare anche le change parallele non correlate.
- Snapshot read-only su `85b179b0`: 4714 violation non-MCP in 778 file,
  filtrando soltanto `/wiki/mcps/`; inventory completa in report AST locale.
  Warning/error e candidati del backlog restano nel perimetro, non solo Catasto.
  Il goal resta attivo finche il perimetro non e verificato completo.
- Consolidate tre slice gia validate con commit separati: `f1887649`
  (caratterizzazione VAL-06, runtime invariato), `9838c415` (spiegazioni VAL-07)
  e `ad1fd588` (parametro formula). Test backend18/frontend42, full-file100%.
- Prossimo singolo hotspot: descrizioni riferimenti sorgente in
  `describeCatastoAnomalia`, base `ad1fd588`, cog/cyc/LOC/nesting44/24/49/1.
  Preservare truthiness (zero/false omessi), String(), testo/punteggiatura,
  ordine fiscale/particella e campo comune non-null. Helper condiviso non
  duplicato, test prima/dopo, full-file100%, ratchet e aggregati obbligatori.

### Catasto frontend — avvio parametro formula inutilizzato (2026-10-05)

- Chiusura `IMPROVED` limitata ai parametri: rimosso `multiplierDigits`
  inutilizzato. Params5 ->4, warning params eliminato e nessun warning ESLint
  residuo; cinque violation error-level rimangono nei due export principali.
  Cognitiva/ciclomatica/LOC/nesting helper5/4/7/1 e aggregati file invariati:
  cognitive113/47, cyclomatic82/25, LOC344, diciassette callable/tre import.
- 42 test prima/dopo, full-file100% sulle quattro metriche: statement98/98,
  function17/17, line87/87, branch114/114 (prima115/115, default morto rimosso),
  configurazione/scope invariati e nessuna esclusione. 686 input VAL-06
  differenziali sul runtime pre-slice con entrambi gli export identici.
- Ratchet mirato contro baseline merge-base `85b179b0`, ESLint runtime/test,
  typecheck frontend no-emit e whitespace PASS. Nessuna baseline aggiornata
  o modifica estranea. Slice VAL-07 e test/docs VAL-06 preservati.
- Audit full corpus read-only sul merge-base aggiornato `85b179b0`: otto
  finding Wiki MCP (auth1, cli2, data-cli1, http4), nessuno nel frontend.
  I precedenti dieci finding non sono piu il conteggio corrente; riduzione
  Wiki non attribuita a questa slice. Intervento Wiki resta separato.
- Graphify frontend codice aggiornato (JSON/report, HTML sopra limite nodi),
  docs dominio/backlog e grafi docs dedicati aggiornati. Nuova slice non
  committata; nessun push. Stop al singolo hotspot; prossimo candidato
  `describeCatastoAnomalia`, cinque error residui non dichiarati risolti.
- Utente conferma percorso Catasto prima, audit Wiki separato. Singolo hotspot:
  `formatFormula`, parametro `multiplierDigits` inutilizzato (warning params5).
- Helper privato, due chiamate interne entrambe con tre argomenti; indice
  sempre formattato da `formatIndexEuroPerMq` a quattro cifre. Rimuovere solo
  il parametro morto, mantenendo default `resultDigits=2`, formato/errori/null.
- Prima target cog/cyc/LOC/nesting/params5/4/7/1/5; file cognitive113/47,
  cyclomatic82/25, LOC344, diciassette callable, sei violation.
  Preservare slice VAL-07 e test/docs VAL-06 gia presenti e non committati.
  Nessun commit/push richiesto; validare full-file100% e ratchet merge-base.

### Catasto frontend — avvio spiegazioni importi VAL-07 (2026-10-05)

- Chiusura `IMPROVED`: helper dominio `pushImportAmountCalculations`
  valida il valore-oggetto e aggiunge atteso/scostamento formattati per voce.
  Target cog/cyc/LOC/nesting59/31/197/2 ->47/25/191/2; helper3/3/10/1,
  tre parametri e nessuna violation. Cognitive file sum/max122/59 ->113/47,
  cyclomatic85/31 ->82/25; branching `sum(cyc-1)`69 ->65.
- File LOC340 ->344, diciassette callable (prima sedici), tre import invariati;
  densita scanner0.608824 ->0.566860. Sei violation residue invariati (cinque
  error/un warning), nessun debito trasferito; wrapper vuoti o duplicazioni
  assenti. Prima proposta ciclo respinta per nesting2 ->3, sostituita.
- Sette caratterizzazioni aggiunte prima del runtime, 42 test verdi prima/dopo.
  Full-file100% statement/branch/function/line: dopo98/115/17/87 contatori
  coperti, prima97/123/16/87; scope e configurazione invariati, nessuna esclusione.
  3600 input differenziali (due export, otto tipi anomalia, ordine sorgente
  invertito, voci null/zero/invalidi/array): output e ordine identici a `9b5357b8`.
- Ratchet mirato merge-base, typecheck frontend no-emit e whitespace PASS.
  ESLint runtime/test exit0 con solo warning legacy `multiplierDigits` inutilizzato,
  non modificato; nessun nuovo warning. Ratchet full corpus read-only contro
  `9b5357b8`: dieci finding Wiki MCP esterni, zero nel runtime frontend toccato.
  Baseline/config/scope invariati. HEAD concorrente `85b179b0` preservato,
  ratchet mirato ripetuto; nessun commit di questa slice o push.
- Graphify frontend codice aggiornato, HTML omesso per limite5000nodi
  (6487nodi): JSON/report presenti. Docs Catasto/backlog e grafi docs dedicati
  aggiornati; test/docs VAL-06 precedenti preservati. Stop al singolo hotspot.
- Dopo `NO_SAFE_CHANGE` VAL-06, autorizzato un hotspot diverso:
  ciclo ordinato per spiegare importi 0648/0985 in `explainCatastoAnomalia`.
  Preservare i test/docs VAL-06 non committati, nessun commit richiesto qui.
- Base `9b5357b8`; prima target cog/cyc/LOC/nesting59/31/197/2,
  sei violation file (cinque error/un warning). Preservare testo, formattazione,
  ordine voci/atteso/delta, valori zero/null/invalidi e array-oggetto;
  nessuna modifica a descrizioni sintetiche, altri casi o rendering consumer.
- Acquisire aggregati, caratterizzazioni/full-file100%, lint/typecheck e ratchet
  contro merge-base. Nessun helper artificiale; eventuali nuovi callable
  devono rispettare soglie e aggregati, senza trasferimento del debito.

### Catasto — avvio attesi e delta VAL-06 (2026-10-05)

- Chiusura `NO_SAFE_CHANGE` per la proposta runtime: ciclo comune attesi/delta
  riduceva cog/cyc 29/22 -> 28/20 ma aumentava LOC target 31 -> 33
  (file 104 -> 106). Ratchet merge-base respinto; proposta rimossa integralmente,
  runtime byte-identico a `9b5357b8`. Nessuna compressione artificiale o
  aggiornamento baseline per aggirare la regressione; non dichiarare riduzione.
- Restano sei nuove caratterizzazioni dei valori mancanti/zero/negativi,
  flag catastale preesistente e ordine chiavi. 18 test verdi prima/finale,
  coverage full-file100% (92/92 statement, 46/46 branch), zero esclusioni.
- Metriche finali identiche a prima: target29/22/31/2, file cognitive64/29,
  cyclomatic54/22, LOC104, sette callable/quattro import, quattro violation
  (due error e due warning). Ratchet mirato finale, Ruff test e whitespace
  PASS; lint-backend bloccato solo dal formatter del nuovo file concorrente
  `backend/app/modules/elaborazioni/domande_irrigue_parallel.py`, non corretto
  qui. Baseline/config/scope invariati; nessun fix estraneo.
- Documentazione e grafi Catasto/piattaforma aggiornati; codice invariato,
  nessun aggiornamento strutturale codice necessario. Test/docs non committati,
  nessun push. Stop: attendere decisione su un hotspot diverso, non aprirlo qui.
- Slice precedente committata `9b5357b8`; singolo hotspot autorizzato:
  calcoli atteso/delta irrigabile e catastale di `build_anomalia_payload`.
- Prima cog/cyc/LOC/nesting 29/22/31/2; file cognitive sum/max 64/29,
  cyclomatic 54/22, LOC 104, sette callable, due error e due warning.
- Unificare i due calcoli con descrittori ordinati e guardie per valori
  mancanti; preservare letture/conversioni, rounding, zero, chiavi preesistenti,
  ordine inserimento, errori e flag catastale (solo quando calcolabile).
  Rami DIR/generici e dati originali invariati; nessun helper o nuovo callable.
- Caratterizzazioni sul runtime originale, full-file100%, metriche prima/dopo
  e aggregati; nessun aggiornamento baseline per assorbire regressioni.

### Catasto — avvio causa superficie senza righe (2026-10-05)

- Chiusura `IMPROVED` **limitata ad annidamento e LOC**: classificazione
  riga singola diretta, poi scelta della causa multi-riga solo con row_ids.
  Nessun helper, nuovo callable o trasferimento del debito. Target
  cog/cyc/LOC/nesting 16/13/26/3 -> 16/13/25/2; cognitive/cyclomatic invariati.
- File cognitive sum/max 64/29 e cyclomatic 54/22 invariati, LOC 105 -> 104,
  sette callable/quattro import. Quattro violation residue (due error,
  due warning), nessuna eliminazione dichiarata; densita scanner
  1.123810 -> 1.134615 per il minor denominatore LOC, non debito aggiunto.
- Prima proposta con early-return respinta dal ratchet per LOC 26 -> 27;
  sostituita prima della chiusura da classificazione piatta sotto le metriche
  iniziali. Nessuna baseline aggiornata per assorbire il tentativo respinto.
- Quattro nuove caratterizzazioni verdi prima del runtime, 12 test verdi
  prima/dopo; full-file100% dopo 92/92 statement e 46/46 branch, zero esclusioni
  (prima 94/94 e 48/48). 2880 payload differenziali identici al runtime
  `753ef6dc`, incluso ordine chiavi e causa preesistente senza righe.
- Ratchet mirato finale merge-base, Ruff runtime/test, whitespace e
  `BASE_REF=753ef6dc make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`
  PASS; baseline/config/scope e VAL-06 invariati. Nessun fix estraneo.
- Ratchet finale full corpus read-only contro `753ef6dc`: dieci finding
  esterni nei file Wiki MCP, nessuno nel payload Catasto; non corretti o
  assorbiti nella baseline di questa slice.
- Graphify Catasto codice aggiornato; docs dominio/backlog e grafi docs
  Catasto/piattaforma aggiornati tramite target dedicati. Nuova slice non
  committata; stop al singolo hotspot, nessun push o secondo hotspot.
- Slice Utenze committata `753ef6dc`; parser ora senza violation.
  Prossimo singolo hotspot: `_enrich_domande_irrigue_surface_payload`.
- Prima cog/cyc/LOC/nesting 16/13/26/3; file cognitive sum/max 64/29,
  cyclomatic 54/22, LOC 105, sette callable, due error e due warning.
- Guardia di uscita dopo tutti gli arricchimenti quando mancano row_ids:
  appiattire solo la classificazione causa senza cambiare deduplica, rounding,
  fallback domanda_ids, ordine chiavi, copie/null o causa preesistente.
  VAL-06 e consumer/transazioni invariati. Test prima/dopo full-file100%,
  metriche/aggregati e ratchet autorevole prima della classificazione.

### Utenze — avvio azienda con PIVA parziale (2026-10-05)

- Chiusura `IMPROVED`: `_parse_partial_company` gestisce la classificazione
  della ragione sociale e review per PIVA a dieci cifre. Target
  cog/cyc/LOC/nesting 15/12/37/1 -> 8/8/28/1; helper 4/5/13/0,
  tre parametri e nessuna violation. Cognitive file sum/max 18/15 -> 15/8.
- **Zero violation nel file**, eliminati entrambi i warning residui senza
  trasferirli nell'helper. Cyclomatic file sum/max 21/12 -> 22/8,
  otto callable (prima sette): incremento della base del nuovo callable,
  branching `sum(cyc-1)` invariato a 14. LOC file 111 -> 113, nessuna
  violation file; densita scanner 0.351351 -> 0.327434, quattro import invariati.
  Signature dei due helper azienda allineate al formatter, nessun altro
  cambiamento nei rami esistenti; riduzione cognitiva non dipende dal wrapping.
- Tre nuove caratterizzazioni verdi sul runtime originale: Unicode,
  identificatore senza nome, nome numerico, warning indipendenti/mutabili.
  37 test verdi prima/dopo; full-file 100% dopo (59/59 statement, 14/14 branch),
  zero esclusioni. 8865 input stringa identici al runtime `9bc764e2`.
- Ratchet mirato merge-base, Ruff, formatter runtime/test, whitespace e
  `BASE_REF=9bc764e2 make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`
  PASS. Ratchet full corpus read-only: dieci finding Wiki MCP esterni,
  zero nel parser; nessun fix estraneo o aggiornamento baseline/config/scope.
- Graphify Utenze codice aggiornato; docs dominio/backlog e grafi Utenze/docs
  piattaforma aggiornati con target dedicati. Nuova slice non committata,
  nessun push; stop a questo singolo hotspot, non avviato un secondo.
- Slice precedente committata `9bc764e2`; singolo hotspot autorizzato:
  separare classificazione/review PIVA a dieci cifre dal dispatch cartella.
- Prima target cog/cyc/LOC/nesting 15/12/37/1; file cognitive 18/15,
  cyclomatic 21/12, LOC 111, sette callable, due warning e zero error.
- Preservare normalizzazione, raw input, ordine CF/PIVA completa/parziale,
  ragione sociale null vs presente, tipo soggetto/confidence e warning
  mutabili indipendenti. Nessuna modifica ai rami persona/azienda completa.
- Helper privato di dominio, nessuna nuova astrazione o duplicazione;
  caratterizzazione prima del runtime, full-file 100%, confronto degli
  aggregati e baseline merge-base prima di dichiarare miglioramento.

### Utenze — avvio azienda con PIVA completa (2026-10-05)

- Chiusura `IMPROVED`: `_parse_complete_company` concentra la validazione
  ragione sociale per PIVA a 11 cifre, senza wrapper vuoti o duplicazioni.
  Target cog/cyc/LOC/nesting 17/13/54/2 -> 15/12/37/1; helper 1/2/21/1,
  tre parametri e nessuna violation. Cognitive file sum/max 19/17 -> 18/15.
- Un warning LOC eliminato, restano due warning (cognitive/cyclomatic),
  zero error. Sette callable (prima sei), cyclomatic file sum/max
  20/13 -> 21/12: incremento della base del nuovo callable, branching
  `sum(cyc-1)` invariato a 14. LOC file 107 -> 111, sotto soglia;
  densita aggregata dello scanner 0.364486 -> 0.351351, quattro import invariati.
- Nove nuove caratterizzazioni verdi sul runtime originale (Unicode, soli
  identificatori/separatori, confine PIVA parziale, warning freschi/mutabili).
  34 test verdi prima/dopo; full-file 100% dopo, 57/57 statement e 14/14 branch,
  zero esclusioni. 8865 casi stringa identici al runtime `40851bbf`.
- Ratchet mirato merge-base PASS; Ruff runtime/test, formatter del test,
  whitespace e `BASE_REF=40851bbf make lint-backend
  QUALITY_PYTHON=backend/.venv/bin/python` PASS. Ratchet full corpus read-only:
  dieci finding Wiki MCP esterni, zero nel parser; nessun fix estraneo.
  Baseline, scope, esclusioni e policy coverage invariati, nessun update.
- Graphify codice Utenze aggiornato; documentazione dominio/backlog e
  grafi docs Utenze/piattaforma aggiornati tramite target dedicati.
  Nuova slice non committata; stop al singolo hotspot, nessun push.
- Slice precedente committata `40851bbf`; prossimo singolo hotspot:
  validazione ragione sociale completa/mancante nel ramo PIVA a 11 cifre.
- Estrarre responsabilita di dominio in helper privato; preservare raw input,
  token/normalizzazione, ordine CF/PIVA/PIVA parziale, tutti i campi,
  warning e liste fresche. Nessuna modifica al ramo PIVA parziale.
- Prima target cog/cyc/LOC/nesting 17/13/54/2; file cognitive sum/max
  19/17, cyclomatic 20/13, LOC 107, sei callable e tre warning, zero error.
  Caratterizzare azienda completa/mancante e confine parziale prima del runtime;
  misurare aggregati, branching e nuove violation prima di dichiarare riduzione.

### Utenze — avvio validazione persona separata dal dispatch (2026-10-05)

- Chiusura `IMPROVED` per complessita cognitiva: il dominio persona CF
  completo/incompleto e nel solo helper `_parse_person`, senza duplicazioni.
  Target cog/cyc/LOC/nesting 19/14/74/2 -> 17/13/54/2; helper 1/2/22/1,
  tre parametri e nessuna violation. Cognitive file sum/max 20/19 -> 19/17.
- Sei callable (prima cinque); cyclomatic file sum/max 19/14 -> 20/13:
  l'unita aggiunta e la base del nuovo callable, branching `sum(cyc-1)`
  invariato a 14. LOC file 105 -> 107, nessuna violation file; densita
  cognitive/LOC 20/105 -> 19/107. Zero error e tre warning invariati,
  nessuna eliminazione di violation o trasferimento del debito dichiarato.
- 25 test prima/dopo; full-file dopo 55/55 statement e 14/14 branch,
  100%, zero esclusioni. 8865 input stringa identici al runtime `a2a66269`.
  Ratchet mirato contro baseline del merge-base, Ruff runtime/test e
  whitespace PASS; baseline, configurazione coverage e scope invariati.
- `BASE_REF=a2a66269 make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`
  bloccato soltanto dal formatter del test concorrente
  `backend/tests/test_capacitas_full_recovery.py`, fuori slice; non corretto.
  Il parser legacy non e format-clean, ma non e un nuovo file e passa Ruff.
- Ratchet full corpus read-only contro `a2a66269`: dieci finding esterni
  nei file Wiki MCP auth/cli/data-cli/experiment_runner/http; zero finding
  nel parser Utenze. Non classificati come regressioni di questa slice,
  non corretti e non assorbiti con aggiornamenti della baseline.
- Graphify Utenze codice aggiornato tramite target dedicato; estrazioni
  documentali Utenze/piattaforma verificate separatamente prima della chiusura.
- Commit precedente `a2a66269`; questa nuova slice resta non committata.
  Stop al singolo hotspot; nessun push o secondo hotspot avviato.
- Prossimo singolo hotspot autorizzato dopo commit `a2a66269`: separare
  il parsing persona CF (nome incompleto/completo) dal dispatch della cartella.
- Helper privato con responsabilita di dominio e tre input espliciti;
  nessuna nuova astrazione generale, wrapper vuoto o duplicazione. Preservare
  ordine classificazione CF/PIVA, raw input, token, payload/errori e liste.
- Prima target cog/cyc/LOC/nesting 19/14/74/2; file cognitive 20/19,
  cyclomatic 19/14, LOC 105 e cinque callable. Coverage full-file 100%,
  25 test di caratterizzazione esistenti. Valutare sum/max origine/helper,
  nuovi warning e branching aggregato: se non migliora, non dichiarare
  riduzione o aprire automaticamente un altro hotspot.

### Utenze — avvio stato di revisione persona (2026-10-05)

- Chiusura `IMPROVED` **limitata a LOC e stato derivato**, non alla
  complessita cognitiva/ciclomatica. Eliminati due alias di costanti e
  `bool` della lista vuota; campi review/confidence/warnings espliciti.
- Target LOC 76 -> 74, file 107 -> 105; cognitive target/file sum/max
  19/20/19 e cyclomatic 14/19/14 invariati. Cinque callable, zero error
  e tre warning invariati; nessun helper o trasferimento del debito.
- Nuova caratterizzazione dell'indipendenza/mutabilita delle liste warning
  e snapshot review passa sul runtime originale; 25 test verdi prima/dopo.
  Coverage dopo full-file 100%, 53/53 statement e 14/14 branch, zero
  esclusioni; due statement realmente eliminati, configurazione invariata.
- 8865 input stringa differenziali identici a `6997dbab`, stesso risultato
  dataclass. Ratchet mirato merge-base, Ruff runtime/test e whitespace PASS;
  baseline/scope/policy invariati. Documentazione e grafi aggiornati.
- Slice precedente committata `6997dbab`. Stop a questo singolo goal;
  nuova slice non committata, nessun push o secondo hotspot avviato.
- Singolo goal successivo autorizzato dopo commit `6997dbab`: eliminare
  le variabili locali derivate `warnings`/`confidence` nel ramo persona
  completa, valorizzando direttamente il risultato con False/0.98/lista vuota.
- Sono costanti dal precedente recupero della guardia irraggiungibile;
  mantenere lista warning fresca per ogni chiamata, snapshot di review,
  mutabilita, campi e ordine del risultato. Nessun altro ramo modificato.
- Prima target cog/cyc/LOC/nesting 19/14/76/2; file cognitive 20/19,
  cyclomatic 19/14, LOC 107 e cinque callable. Obiettivo LOC/stato derivato,
  non promettere riduzione cognitiva o eliminazione di warning.

### Utenze — avvio guardia input vuoto (2026-10-05)

- Chiusura `IMPROVED`: guardia iniziale `if not tokens`, rimosso soltanto
  il controllo di stringa vuota gia implicato dal tokenizer. Nessun helper,
  modifica ai test, spostamento o trasferimento del debito.
- Target cog/cyc/LOC/nesting 22/16/76/2 -> 19/14/76/2; file cognitive
  sum/max 23/22 -> 20/19, cyclomatic 21/16 -> 19/14, LOC 107, cinque
  callable e quattro import invariati. Error-level 1 -> 0; restano tre
  warning (cognitive, cyclomatic, LOC), non dichiarati eliminati.
- 24 test verdi prima/dopo; coverage full-file 100%, 55/55 statement,
  14/14 branch, zero esclusioni, denominatori invariati. 8865 input stringa
  differenziali identici a `6241b4ca`, compresi vuoti/soli separatori/Unicode.
- Ratchet mirato merge-base e Ruff runtime PASS; scope/baseline/config
  invariati. Lint globale bloccato dalle change Capacitas concorrenti
  `recovery_service.py` e `capacitas_full_recovery.py`, non corrette qui.
- Commit precedente `6241b4ca` fatto con indice alternativo: staging dei
  18 file MCP concorrenti preservato byte-identico, poi committato dall'owner
  in `16476689`. HEAD cambiato esternamente, perimetro parser ricontrollato
  e ratchet mirato ripetuto senza finding; nessuna patch estranea incorporata.
- Docs dominio/backlog e grafi aggiornati. Stop al singolo goal;
  nuova slice non committata, nessun push o aggiornamento baseline.
- Prossimo singolo goal autorizzato dopo commit `6241b4ca`: rimuovere
  `not normalized_name` duplicato nella guardia iniziale del parser.
- Invariante: nome normalizzato vuoto implica lista token vuota; viceversa
  la lista vuota comprende anche nomi di soli separatori. `not tokens`
  conserva quindi esattamente il ramo `empty_folder_name`, senza leggere
  `tokens[-1]` sugli input vuoti. Tokenizer e tutti i payload invariati.
- Prima target cog/cyc/LOC/nesting 22/16/76/2; file cognitive 23/22,
  cyclomatic 21/16, LOC 107, cinque callable. Test W1 e casi Unicode
  gia caratterizzano i due stati. Nessun nuovo hotspot o commit implicito.

### Utenze — avvio normalizzazione nomi persona (2026-10-05)

- Chiusura `IMPROVED`: rimossi solo replace/strip duplicati sui token persona
  e fallback `or None` impossibili. Stesso tokenizer, output e cinque callable;
  nessun helper, wrapper o trasferimento del debito.
- Target cognitive 28 -> 22, cyclomatic 20 -> 16, LOC 76 e nesting 2
  invariati; file cognitive sum/max 29/28 -> 23/22, cyclomatic
  25/20 -> 21/16, LOC 107, quattro import invariati. Error-level 2 -> 1:
  cognitive ora warning, restano tre violation (un error, due warning).
- Due casi nuovi (separatori ripetuti e whitespace Unicode) passano sul
  runtime originale; 24 test verdi prima/dopo. Coverage full-file 100%
  55/55 statement e 14/14 branch, zero esclusioni e denominatori invariati.
- 8865 casi differenziali stringa conformi: payload dataclass identici a
  `554c04af`; include input vuoti, Unicode, CF/PIVA e nomi multipli.
  Ratchet mirato merge-base PASS, Ruff runtime/test e whitespace PASS;
  baseline, soglie, scope, configurazioni coverage/CI invariati.
- `make lint-backend` globale FAIL per import/format delle change Capacitas
  concorrenti (`elaborazioni_capacitas_incass.py` e `recovery_ruolo.py`), non in questi due
  file. Ratchet completo 12 finding esterni, nessuno nel parser; nessun gate
  globale verde dichiarato e nessuna correzione opportunistica Capacitas.
- Documentazione dominio/backlog e grafi Utenze/piattaforma aggiornati.
  Stop al singolo hotspot. Nuova slice non committata; Catasto precedente
  committato isolatamente in `554c04af`, nessun push.
- Singolo hotspot successivo autorizzato dopo commit Catasto `554c04af`:
  semplificare solo cognome/nome del percorso persona completa nel parser.
- Token gia privi di underscore, trimmed e non vuoti; almeno tre token
  garantiscono cognome e nome non vuoti. Rimozione di replace/strip duplicati
  e fallback `or None` impossibili; nessun cambio al tokenizer o ai rami
  persona incompleta, azienda e sconosciuto. Input/API/dati preservati.
- Prima target cog/cyc/LOC/nesting 28/20/76/2; file cognitive 29/28,
  cyclomatic 25/20, LOC 107 e cinque callable. Test/coverage prima e dopo,
  ratchet merge-base e aggregati obbligatori; nessun commit del nuovo goal.

### Catasto — avvio mapping campi VAL-06 (2026-10-05)

- Chiusura `IMPROVED`: quattro guardie di serializzazione opzionale
  sostituite da mapping ordinato e predicato unico `value is not None`.
  Nessun helper, nuovo callable o trasferimento del debito.
- Dopo target cog/cyc/LOC/nesting 29/22/31/2 (prima 30/24/31/2);
  file cognitive sum/max 64/29 (65/30), cyclomatic 54/22 (56/24),
  LOC 105, sette callable e quattro import invariati. Quattro violation
  residue (due error, due warning), nessuna eliminazione dichiarata.
- Sei test iniziali con full-file 100%; due nuove caratterizzazioni
  (zero, overwrite/ordine, null che conserva campi originali) verdi prima
  della modifica runtime; otto test verdi dopo. Coverage full-file dopo
  94/94 statement e 48/48 branch, zero esclusioni, gate 100% superato.
- 2500 casi differenziali (null, zero, decimali positivi/negativi, valori
  invalidi, payload iniziali diversi): output, ordine chiavi e errori
  identici al runtime `c75fe0a2`. Ratchet mirato merge-base PASS;
  lint-backend/style, Ruff e whitespace PASS, baseline/config invariati.
- Documentazione dominio e backlog aggiornati, Graphify con target Catasto
  codice/docs e piattaforma. Stop al singolo hotspot, nessun secondo goal.
- Prossimo singolo hotspot autorizzato dopo commit Utenze `c75fe0a2`:
  `build_anomalia_payload`, runtime/test puliti; nessun altro hotspot ammesso.
- Prima target cog/cyc/LOC/nesting 30/24/31/2, file cognitive 65/30,
  cyclomatic 56/24, LOC 105 e sette callable. Coverage W1 full-file 100%.
- Slice: serializzazione esplicita dei quattro valori numerici opzionali,
  senza cambiare accessi/rounding, presenza di zero, ordine chiavi, payload
  originale, attesi/delta, errori, flussi DIR o transazioni dei consumer.
- Nessun helper artificiale o nuova esclusione; acquisire metriche/test
  prima/dopo, rispettare non-regressione LOC e aggregati. Commit di questa
  nuova slice non implicito nella richiesta di commit della precedente.

### Utenze — avvio guardia irraggiungibile (2026-10-05)

- Chiusura `IMPROVED`: rimossi solo la guardia morta e i suoi due statement;
  ordinati gli import per correggere I001 del runtime ora toccato. Nessun
  helper, spostamento, nuovo callable o modifica ai test/contratti.
- Dopo target cog/cyc/LOC/nesting 28/20/76/2 (prima 30/21/79/2);
  file cognitive sum/max 29/28 (31/30), cyclomatic 25/20 (26/21),
  LOC 107 (110), cinque callable e quattro import invariati. Tre violation
  legacy residue (due error, un warning); nessuna eliminazione dichiarata.
- Prima/dopo 22 test verdi; full-file dopo 55/55 statement e 14/14 branch,
  100%, zero esclusioni. Prima 56/58 e 15/16; denominatore ridotto dal
  codice realmente irraggiungibile rimosso, non da configurazioni coverage.
- 5655 input `str` (vuoti, separatori, whitespace, Unicode, CF/PIVA e token
  multipli) confrontati con il runtime HEAD: payload dataclass identici.
  Ratchet mirato autorevole contro `8f59ad9a` PASS, `findings=[]`;
  lint-backend/style e Ruff runtime PASS. Baseline/scope/soglie invariati.
- Graphify Utenze codice aggiornato tramite target dedicato; docs dominio
  e piattaforma aggiornate. Stop al singolo hotspot; nessun commit/push.
- Goal runtime separato autorizzato dopo W1: sola rimozione di `if not nome`
  in `parse_folder_name`, base `8f59ad9a`; runtime/test candidati puliti.
- Invariante: token non vuoti dopo strip e almeno tre token nel percorso
  persona completa garantiscono un nome non vuoto. Input senza nome resta
  nel ramo `person_name_incomplete`. Nessun monkeypatch o esclusione coverage.
- Prima target cog/cyc/LOC/nesting 30/21/79/2; file cognitive 31/30,
  cyclomatic 26/21, LOC 110, cinque callable. Caratterizzazione W1 22 test,
  statement 56/58 e branch 15/16; nuove misure in `/tmp/gaia-utenze-guard-*`.
- Nessun ulteriore hotspot, baseline update, commit o push autorizzato;
  preservare le change concorrenti Wiki/Presenze/worker/infrastruttura.

### W1 — checkpoint finale dei tre goal (2026-10-05)

- Patch integrate serialmente dopo review/hash/ownership, tutte a base
  `bfc8e68f`. Nessun commit, branch nuovo o baseline update.
- Catasto test-only: sei test, coverage full-file 99/99 statement e 52/52
  branch, 100%; runtime e metriche invariati. Prerequisito chiuso.
- Utenze test-only: 22 test, 56/58 statement e 15/16 branch; residuo unico
  `missing_nome` dimostrato irraggiungibile. Runtime invariato, nessuna
  esclusione. Rimozione autorizzata solo per il prossimo goal separato.
- Organigramma `IMPROVED`: target cognitive 23 -> 16 e nesting 2 -> 1;
  file cog sum/max 59/23 -> 52/16, cyc 50/12, LOC 95 e 13 callable invariati.
  Nessun helper o trasferimento, quattro warning residue. 38 test verdi,
  coverage 62/62 statement, 58/58 branch, 13/13 funzioni, 50/50 linee;
  ESLint scoped e typecheck integrato PASS.
- Ratchet completo isolato Organigramma PASS. Confronto corpus completo
  integrato con baseline del merge-base sul perimetro W1 PASS. Scan parziale
  del precedente split dava falsi matching move; risolto con corpus completo,
  nessun fix tooling/baseline o firma runtime alterata per abbassare metriche.
- Globali ancora rossi: 11 finding working tree (otto Wiki e tre test worker
  concorrenti), 29 confronto integrale baseline. Nessuno sulle patch W1.
  Tooling 169 passed, lint-backend PASS, whitespace PASS.
- Report `PARALLEL_W1_RESULTS_2026-10-05.md`, backlog aggiornato;
  Graphify frontend aggiornato. Tre goal chiusi, W2 non avviata.

### W1 — avvio dei tre goal autorizzati (2026-10-05)

- Ripresa autorizzata: confermata ownership e adattamento temporaneo Git
  `core.excludesFile=/tmp/gaia-w1-local-git-excludes` nei subprocess degli
  isolati, limitato al symlink `/frontend/node_modules`. Nessuna modifica
  dello scope scanner, baseline o configurazione versionata.
- Catasto test-only integrato dopo review: scenario VAL-06 imponibile nullo,
  sei test, statement 99/99 e branch 52/52, zero esclusioni. Runtime invariato.
- Utenze caratterizzazione integrata dopo review: 22 test, statement 56/58
  e branch 15/16; residuo solo guardia `missing_nome` dimostrata irraggiungibile
  per input `str` conformi. Runtime invariato. Rimozione approvata dall'utente
  esclusivamente come prossimo goal separato, non eseguita in W1.
- Organigramma preflight incontra sei finding parametri nel report parziale:
  firme invariate, nessun path controller nella baseline; l'omissione di
  sorgenti ancora esistenti nel corpus attiva erroneamente matching move.
  Il confronto sul corpus completo prima restituisce zero finding controller.
  Verifica full-corpus dopo obbligatoria prima dell'integrazione runtime.
- Approvati Catasto test-only, audit/caratterizzazione Utenze e singolo
  hotspot selezione Organigramma; nessun ulteriore hotspot ammesso.
- Isolamento in tre worktree detached `/tmp/gaia-w1-{catasto,utenze,organigramma}`
  al medesimo `bfc8e68fd6d4acf373b23b7cc15693c80bd75f18`. Nessun branch
  o commit creato, nessuna change dirty Wiki/Presenze/SISTER trasferita.
- Allowlist: A solo `test_catasto_anomalie_payloads.py`; B solo
  `test_anagrafica_parser.py`; C controller selezione e relativo test unit.
  Runtime backend read-only; dipendenze/config/baseline/docs single writer.
  Hash dei sei file puliti acquisiti in `/tmp/gaia-w1-source-hashes.txt`.
- Riproduzione gate negli isolati prima della change; patch da revisionare
  e integrare serialmente soltanto con preflight hash e ownership stabili.
  Richiesta conferma assenza di owner concorrenti prima dell'integrazione.
- Stop pre-integrazione: il link locale `frontend/node_modules` degli
  isolati viene enumerato come untracked e `added_lines_since` tenta di
  leggerlo come file (`IsADirectoryError`). Causa identificata, nessun fix
  tooling/scope/baseline. Richiesta decisione sull'esclusione Git temporanea
  del solo link ambiente, oltre alla conferma ownership.
- Prima dello stop: Catasto riproduce cinque test e branch 50/52, nessun
  edit; Utenze caratterizzazione solo isolata 22 test, statement 56/58 e
  branch 15/16, residuo `missing_nome`; Organigramma caratterizzazione
  solo isolata 38 test con coverage full-file 100%, runtime invariato.
  Nessuna patch integrata e nessun refactoring runtime applicato.

### W0 — readiness parallela verificata (2026-10-05)

- Audit autorizzato, tre agenti in parallelo solo per misure. Nessun runtime,
  test, baseline o configurazione modificati; nessun branch/worktree/commit.
- Snapshot `main@bfc8e68f`: 1604 file, 19714 callable, 4742 violation
  (2041 error/2701 warning). Checkout concorrente: non attribuire il delta
  rispetto al piano a W0. Finding globale 26, ratchet working tree otto Wiki;
  ratchet scoped tre candidati PASS, nessun finding.
- Tooling 169 passed; lint-backend/style ratchet PASS su 26 file cambiati.
  Organigramma: 35 test, statement 62/62, branch 57/57, funzioni 13/13,
  linee 50/50; ESLint scoped e typecheck PASS.
- Catasto: cinque test verdi, statement 99/99 ma branch 50/52; runtime
  bloccato fino alla caratterizzazione di imponibile nullo con superfici.
  Utenze: cinque test verdi, statement 52/58, branch 12/16; serve audit
  della guardia apparentemente irraggiungibile `missing_nome`, niente fake
  impossibili o esclusioni per ottenere 100%.
- Registro, classificazione completa dei 26 finding e isolamento proposto in
  `PARALLEL_W0_READINESS_2026-10-05.md`. W0 conclusa come audit, non via libera
  a tre refactoring; W1 non iniziata. Proposta: Catasto test-only, Utenze
  audit/caratterizzazione, Organigramma hotspot dopo ownership/isolation gate.
- Graphify platform docs aggiornato con target dedicato: chunk 1/1 completo,
  nessun warning semantico; evidenza `/tmp/gaia-w0-graph-docs.log`.

### Pianificazione riduzione estesa multi-agente (2026-10-05)

- Richiesto un piano completo, con agenti paralleli. Tre agenti hanno
  analizzato backend, frontend/worker e governance in sola lettura;
  nessuna implementazione runtime, branch/worktree o commit avviato.
- Snapshot fresco `main@bfc8e68f`: 1603 file, 19713 callable, 4741 violation
  (2041 error/2700 warning); backend/frontend/worker 2745/1775/221.
  Confronto integrale baseline: 26 finding, ratchet working tree: otto
  Wiki ereditati. Scope worker test invariato, nessuna baseline update.
- Proposta in `PARALLEL_REDUCTION_PLAN_2026-10-05.md`: coordinatore e tre
  implementatori, un hotspot per goal, ownership runtime/test/fixture
  esclusiva, isolamento futuro da autorizzare, gate slice/ondata/globale,
  characterization full-file prima dei monoliti e single writer baseline/grafi.
- W0 stabilizza base/ownership/coverage e classifica i finding; W1 propone
  Catasto anomalie, parser Utenze e selezione Organigramma indipendenti.
  W2/W3 introducono IO/worker e confini condivisi solo dopo checkpoint.
  W4 richiede test-only per i grandi monoliti; nessun refactoring massivo
  in una singola change o nuova deroga alle policy.
- Artefatti snapshot `/tmp/gaia-mass-plan-*`; obiettivi pilota sul paniere
  selezionato, non promesse di riduzione del totale repository o rilascio.
  Prima decisione proposta: W0 e predisposizione isolata. README aggiornato;
  Graphify platform docs tramite target dedicato con controllo chunk.

### Baseline - riduzione reale Wiki/MCP, prima slice (2026-10-03)

- Richiesta esplicita: ridurre il codice prima di aggiornare la baseline, non
  riallineare il JSON assorbendo peggioramenti. Unico hotspot di questa slice:
  `DataService.call`, checkout `main@fccd06b0`; runtime/test target inizialmente
  puliti, altre modifiche preservate. Nessun commit o push autorizzato qui.
- Audit completo del solo codice committato in worktree detached: 1580 file,
  19591 callable, 4731 violation (2043 error, 2688 warning). Non sono 4731
  funzioni distinte. Il rispetto delle soglie dell'intero progetto non si
  ottiene aggiornando una baseline, ne con un refactoring massivo.
- Prima: target cog/cyc/LOC/nesting `13/10/60/2`; file cog/cyc sum `58/48`,
  9 callable, 172 LOC, 5 warning e zero error. Baseline del target
  `12/9/58`; due ulteriori finding ereditati nel costruttore per il parametro
  audit gia committato. Non rimuovere la funzionalita audit per ripristinare
  quei numeri. Graphify Wiki consultato per ownership e impatto.
- Invarianti: schema risposta e provenance, paginazione, scope e validazione,
  classi/errori minimizzati, stima token, correlazione e principal redatto,
  log prima della scrittura audit; errore audit resta propagato.
- Sei nuovi casi di caratterizzazione superati prima e dopo. Prima: 90 test,
  106/106 statement e 22/22 branch. Dopo: 129 test con HTTP/integrazione,
  109/109 statement e 22/22 branch; full-file 100%, nessuna esclusione.
- Dopo: target cog/cyc/LOC/nesting `2/3/25/1`, nuovo `_call_response`
  `10/7/38/2`; entrambi sotto ogni soglia warning. File cognitiva `58 -> 57`,
  ciclomatica `48` invariata, LOC `172 -> 175`, callable `9 -> 10`, warning
  `5 -> 3`, zero error. `IMPROVED`, senza attribuire alla riduzione globale
  l'intero calo del target dovuto alla separazione delle responsabilita.
- Ruff, lint-backend isolato e whitespace verdi. Scanner completo isolato
  contro baseline del merge-base: due finding ereditati del costruttore,
  nessun finding nuovo; ratchet exit 1, non certificato PASS. Check completo:
  finding baseline `23 -> 20`, violation globali `4731 -> 4729`, nessun error
  eliminato. Baseline non aggiornata dopo un ratchet ancora bloccato.
- Audit e scope del costruttore restano invariati: rimuovere il parametro
  audit per recuperare il vecchio numero richiederebbe cambiare API.
  Non si nasconde in kwargs, non si assorbono i 20 finding residui.
- Graphify Wiki aggiornato con force e patch: 115 file AST, 985 nodi,
  2361 archi; grafi ignorati. Report e limiti in
  `BASELINE_REDUCTION_2026-10-03.md`. Stop al singolo hotspot; nessuna seconda
  slice o commit eseguiti. `_execute` e solo una proposta per il seguito.

### Tooling - sblocco gate condivisi e pruning Graphify (2026-10-03)

- Tranche autorizzata sui tre blocchi globali, non un nuovo hotspot GIS.
  Checkout iniziale `main@2bc93d66`, merge-base finale `main@b8929feb`.
  Modifiche concorrenti preservate; nessun runtime applicativo modificato.
- Ruff I001 risolto nei soli import di
  `backend/tests/test_presenze_operations_postgres.py`; collection dei tre
  test riuscita, corpi test invariati. PostgreSQL live non eseguito.
  `lint-backend` usa ora una cache bytecode temporanea con cleanup anche
  in caso di failure, evitando cache runtime non scrivibili create dai
  container. Due contratti Make verificano successo, fallimento, cleanup
  e mancato avvio del ratchet quando compileall fallisce.
- Matcher: una nuova callback interamente aggiunta non rende ambigui i
  duplicati invariati solo quando tutte le occorrenze non aggiunte
  riproducono esattamente il multinsieme completo baseline. Le aggiunte
  restano nuove e non ereditano debito, anche a coordinate coincidenti
  con una voce baseline. Nove nuovi casi verificano
  crescita legittima, survivor mancante, regressione legacy, aggiunta
  parziale, violation nuova bloccante e riscritture legacy senza prova
  di aggiunta. Matching ambiguo non dimostrabile
  continua a fallire, nessuna soglia o esclusione cambiata.
- Ratchet autorevole su `navigation.ts`: PASS, `findings: []`, senza
  cambiare il frontend o rigenerare baseline. Il ratchet globale ora
  completa il confronto (prima exit 2 per `isVisible`) ed esce 1 con
  32 finding: 31 regressioni callable e una LOC file-level, nei lavori
  concorrenti Wiki/accessi/Ruolo/frontend. Verificati gli stessi 32 finding
  con il matcher originale sui medesimi path, escludendo solo navigation.
  Non sono assorbiti dalla baseline
  e non sono trattati come debito legacy approvato. Il loro recupero richiede
  una change separata con ownership e test; nessun altro hotspot aperto.
- Patch locale riproducibile `scripts/patch_graphify_force_pruning.py`:
  `--force` rende autorevoli le sorgenti riestratte anche per i nodi
  preesistenti assenti dalla nuova AST. Restano i nodi di altre sorgenti;
  non e pruning generale di file cancellati. Target Make dedicato e
  dipendenza automatica di `graphify-backend`; layout upstream sconosciuti/
  ambigui, package/file assenti e installazioni non scrivibili fail-closed.
  Quattordici contratti coprono pruning force/incrementale, preservazione,
  idempotenza, discovery CLI e failure di installazione.
- Suite quality tooling finale: `169 passed` (anche `make quality-test`). Full-file `complexity.py`
  `709/709` statement e `276/276` branch; patch Graphify `27/27` e `6/6`,
  100% per file, nessuna esclusione o test saltato. Config temporanea include
  subprocess CLI e i due runtime: non cambia gate/scope CI repository.
  Prima il matcher era `702/702`, `270/270`; nuovo script interamente
  caratterizzato. Nessuna riduzione della complessita applicativa dichiarata.
- Ruff mirato e formatter nuovi file verdi. `make lint-backend` senza
  workaround esterni PASS su 145 file cambiati. Whitespace verde;
  baseline, eccezioni e scope invariati, sincronizzazione non eseguita
  per le 32 regressioni residue. Evidenze `/tmp/gaia-blockers-final-run-dir`,
  final-ratchet, navigation-ratchet, lint-final, preexisting-proof e
  graph-code log con prefisso `/tmp/gaia-blockers-`.
- Graphify backend aggiornato tramite target con force e patch: 865 file
  AST, 9670 nodi, 24634 archi e 530 community. Verificata assenza del vecchio
  `gis_services_jsonable_record` e presenza del nuovo simbolo canonico;
  HTML omesso dal limite previsto di 5000 nodi, JSON/report aggiornati.
  Questo risolve il limite della tranche GIS precedente. Documentazione
  piattaforma aggiornata tramite target dedicato: `chunk 1/1 done`, nessun
  warning semantico; refresh finale dei registri dopo i 169 test. Grafi non
  versionati. Commit isolato della sola manutenzione tooling successivamente
  richiesto dall'utente; le 32 regressioni del working tree e le altre slice
  non sono incluse. Nessun push.

### Catasto GIS - lookup dei componenti DMS direzionali (2026-10-03)

- Hotspot unico `parseDirectionalDms`, checkout `main@2bc93d66`;
  runtime/test puliti, Graphify consultato, altri lavori preservati.
- Prima: cognitiva/ciclomatica/LOC/nesting `13/11/16/2`.
- Slice: dichiarare direction obbligatoria nel risultato del validatore
  (sempre restituita dal runtime) e rimuovere le due guardie truthy nei
  lookup NS/EW. Le regex gia rifiutano una stringa vuota; nessun cambio
  funzionale, parsing, validazione numerica, segni e ordinamento invariati.
- Diciassette nuovi casi su emisferi, ordine invertito, casing, gradi
  negativi e limiti, direzioni duplicate, componenti mancanti/extra e valori
  invalidi. Suite prima/dopo 48 test verdi, full-file 100% su tutte le metriche.
- Dopo: cognitiva `13 -> 11`, ciclomatica `11 -> 9`, LOC/nesting `16/2`
  invariati. Le due callback find passano da cog/cyc `1/2` a `0/1`, nessun
  nuovo callable; aggregati file cognitiva `50 -> 46`, ciclomatica `59 -> 55`,
  diciannove callable e LOC `196` invariati. Esito `IMPROVED`, debito non
  trasferito; warning `1 -> 0`, zero error, nessuna violation nel file.
- Coverage dopo: statement `89/89`, branch `64/64`, funzioni `19/19`,
  linee `71/71`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo, `findings: []`, merge-base `6b61fd27`; baseline/scope invariati.
  ESLint, typecheck senza incremental, 144 test tooling e whitespace verdi.
  Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
- Evidenze `/tmp/gaia-directional-dms-{before,after}.{json,md}`, log
  characterization/after/ratchet-before/after/lint/types/quality e Graphify
  con lo stesso prefisso. Un solo hotspot, commit isolato dopo i gate
  secondo autorizzazione vigente; altri lavori preservati, nessun push.

### GIS - validatore ZIP sotto soglia (2026-10-03)

- Unico hotspot `_validate_shapefile_zip`; ripresa su `main@bfc158cc`,
  HEAD concorrente `2bc93d66` durante i gate. Conservate le due slice
  precedenti e tutti i lavori estranei. Nessuna modifica a GATE.
- Responsabilita di dominio in `shapefile_validation.py`: selezione dello
  stem completo, lettura/normalizzazione pyshp e serializzazione JSON
  condivisa. Alias `_jsonable_record` e costante disponibili in `services`;
  orchestrazione ZIP/SRID/encoding/report/checksum nel servizio.
  Ordine errori, guardie input/auth, API, schema, transazioni, audit,
  staging, concorrenza e dati invariati. Una feature NULL resta un record.
- Prima cog/cyc/LOC del validatore `21/19/62`; dopo `7/8/33`.
  Componenti `4/5/15`, lettura `10/8/35`, serializzatore `4/4/4`.
  Zero violation sul validatore e sui tre callable del modulo estratto;
  nessuna violation trasferita. Perimetro aggregato: cog `490 -> 490`,
  cyc `503 -> 505`, callable `109 -> 111`, LOC `2202 -> 2235`.
  LOC servizio `2202 -> 2175`; violation `39 -> 36` (error `15 -> 14`,
  warning `24 -> 22`). Classificazione `REORGANIZED_AND_CHARACTERIZED`,
  non riduzione delle decisioni di dominio o azzeramento globale.
- Undici casi pertinenti su archivi reali: cardinalita/stem, componenti
  mancanti ordinati, precedenza errori, DBF Latin-1/date/numeri/null,
  geometrie miste/tutte NULL, header corrotto, codec/decodifica e zero
  feature. Passano anche eseguendo la funzione originale di `bfc158cc`.
  L'aspettativa iniziale bbox NULL assente era errata anche prima del
  refactoring: caratterizzata la bbox reale pyshp `[0,0,0,0]`, senza
  modifica runtime. Nessun mock artificiale o controllo esterno rimosso.
- Corpus GIS/Catasto GIS: `300 passed`, `102` warning PyJWT preesistenti,
  nessun test saltato. Fresh coverage full-file: servizio `1050/1050`
  statement e `314/314` branch; modulo `34/34` e `10/10` (100% ciascuno),
  nessuna linea/branch mancante o esclusa. Dati isolati nella directory
  indicata da `/tmp/gaia-gis-zero-final-run-dir`.
- Ruff su runtime e test GIS toccati, formatter dei file nuovi, whitespace,
  ratchet mirato autorevole contro `main@2bc93d66` (`findings: []`) e
  `make quality-test` (`144 passed`) verdi. AST delle altre 110 unita
  top-level invariato; solo serializzatore spostato e validatore cambiato.
  Evidenze `/tmp/gaia-gis-zero-{before,after}.json`, AST invariants,
  characterization, final-ratchet, lint e quality log con lo stesso prefisso.
- Gate globali NON verdi: `make lint-backend` incontra cache bytecode
  non scrivibili fuori GIS; ripetuto con `PYTHONPYCACHEPREFIX` temporaneo,
  compila ma segnala I001 in `test_presenze_operations_postgres.py`.
  Ratchet globale si ferma con `ambiguous_identity` per `isVisible` in
  `frontend/src/components/layout/navigation.ts`. Problemi esterni non
  corretti ne assorbiti; baseline/scope/soglie/esclusioni invariati.
  Sincronizzazione baseline globale non eseguita per questa ambiguita.
- Graphify backend aggiornato: 865 file AST, 9958 nodi, 25304 archi,
  529 community; HTML omesso dal limite previsto di 5000 nodi, JSON/report
  aggiornati. Il vecchio nodo `gis_services_jsonable_record` resta stale
  dopo `make graphify-backend GRAPHIFY_CODE_FLAGS=--force`: questa versione
  conserva i nodi preesistenti non presenti nella nuova AST anche con force.
  Non alterati manualmente i grafi o il tooling per nascondere il limite.
  Docs piattaforma: `chunk 1/1 done`, nessun chunk fallito; refresh finale
  dopo la registrazione di questo limite. Grafi non versionati.
  PostGIS/QGIS live ed E2E non
  eseguiti; restano 36 violation legacy nel perimetro, fuori dal validatore.
  Nessun commit/push: i controlli globali bloccanti non sono tutti superati.

### Catasto GIS - componenti DMS senza direzione (2026-10-03)

- Hotspot unico `parseSignedDms`, checkout `main@bfc158cc`;
  runtime/test puliti, Graphify consultato, altri lavori esclusi.
- Prima: cognitiva/ciclomatica/LOC/nesting `19/9/12/2`.
- Slice finale: riuso di parseDmsValues gia condiviso, con direzione vuota
  equivalente a nessuna direzione nel calcolo del segno; elimina parsing e
  validazione duplicati nel solo parser signed, senza nuovi helper.
  Invarianti: regex, segno e ordine lat/lon, limiti minuti/secondi
  `[0,60)`, limiti geografici, esattamente due componenti, parser con
  direzioni, overlay e URL invariati.
- Diciassette nuovi casi DMS su omissioni, zero, segni, decimali e limiti,
  conteggio componenti e rifiuti. Il gate iniziale aveva due helper mai
  eseguiti (overlay/response): due test di caratterizzazione ne verificano
  shape, fallback, identita GeoJSON e immutabilita; runtime non modificati.
  Suite prima/finale 31 test verdi e full-file 100% su tutte le metriche.
- Dopo: cognitiva `19 -> 4`, ciclomatica `9 -> 4`, LOC `12 -> 10`, nesting
  `2` invariato. Aggregati file cognitiva `65 -> 50`, ciclomatica `64 -> 59`,
  LOC `198 -> 196`, diciannove callable invariati; helper condiviso invariato
  a `11/7/13/1`. Esito `IMPROVED`, nessuna violation trasferita, warning
  `2 -> 1`, zero error; resta la ciclomatica del parser direzionale.
- Coverage finale: statement `89/89`, branch `68/68`, funzioni `19/19`,
  linee `71/71`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e finale, `findings: []`, merge-base `6b61fd27`; baseline/scope invariati.
  ESLint finale, typecheck senza incremental, 144 test tooling e whitespace
  verdi. Graphify frontend aggiornato; refresh platform docs completato
  con `chunk 1/1 done`, senza warning di chunk semantici falliti.
- Evidenze `/tmp/gaia-signed-dms-{before,final}.{json,md}`, log
  characterization/final/ratchet-before/final/lint-final/types-final/quality
  e Graphify con lo stesso prefisso. Un solo hotspot, commit isolato dopo
  i gate secondo autorizzazione vigente; altri lavori preservati, nessun push.

### Elaborazioni - dispatch dei workspace statici (2026-10-03)

- Hotspot unico `NativeWorkspaceRenderer`, checkout `main@b824e2f1`;
  runtime/test puliti, Graphify consultato, lavori degli altri team esclusi.
- Prima: cognitiva/ciclomatica/LOC/nesting `14/15/67/1`.
- Slice: tabella locale delle dieci route esatte e relativi elementi JSX,
  senza factory/helper nuovi. Elementi ricreati a ogni render, solo quello
  selezionato montato. Request mode e Capacitas prioritari, route dinamiche,
  ID, props embedded/view/isolatedView, callback e iframe invariati.
- Dodici nuovi casi verificano matching esatto delle dieci route statiche,
  fallback iframe e callback load, props view/isolatedView e unico archivio
  montato; le dodici route native gia testate verificano ora embedded.
  Suite prima/dopo 62 test verdi e full-file 100% su tutte le metriche.
- Dopo: cognitiva `14 -> 5`, ciclomatica `15 -> 6`, LOC `67 -> 53`, nesting
  `1` invariato. Aggregati file cognitiva `33 -> 24`, ciclomatica `41 -> 32`,
  LOC `190 -> 176`, dodici callable invariati. Esito `IMPROVED`, nessun
  trasferimento di debito. Error `1 -> 0`, due warning LOC residui.
- Coverage finale: statement `57/57`, branch `30/30`, funzioni `12/12`,
  linee `55/55`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo, `findings: []`, merge-base `6b61fd27`; baseline/scope invariati.
  La prima tabella JSX in tuple attivava jsx-key: convertita a proprieta
  oggetto/Map senza aggiungere key che cambino la riconciliazione React.
  ESLint finale, typecheck senza incremental, 144 test tooling e whitespace
  verdi. Graphify frontend aggiornato; refresh platform docs completato
  con `chunk 1/1 done`, senza warning di chunk semantici falliti.
- Evidenze `/tmp/gaia-native-workspace-{before,final}.{json,md}`, log
  characterization/final/ratchet-before/final/lint-final/types/quality e
  Graphify con lo stesso prefisso. Un solo hotspot, commit isolato dopo
  i gate secondo autorizzazione vigente; altri lavori preservati, nessun push.

### GIS - ZIP, confronto encoding del warning (2026-10-03)

- Seconda slice ZIP autorizzata dopo la costruzione ordinata dei warning;
  checkout `main@b824e2f1`, preservata la prima slice non committata e tutti
  i lavori concorrenti. Unica responsabilita toccata: predicato
  `encoding_overridden` nel validatore, nessun altro hotspot aperto.
- Invariante: il CPG vuoto non genera override; un CPG non vuoto
  equivalente all'encoding selezionato senza distinguere maiuscole/minuscole
  non genera override; ogni altro CPG non vuoto lo genera. Il confronto
  usa stringhe gia normalizzate, senza effetti collaterali. Condizioni
  di input, precedenza encoding, errori HTTP, auth, dati, audit/staging,
  transazioni e concorrenza restano invariati.
- Due nuovi casi con ZIP reali: CPG vuoto ed encoding ISO-8859-1 esplicito,
  CPG a casing misto equivalente all'encoding UTF-8 esplicito. La matrice
  ora contiene nove casi: tutti passano prima e dopo la modifica.
  Nessun mock di input impossibili o test destinato alla sola percentuale.
- Slice: confronto del CPG normalizzato con i due valori ammessi senza
  warning (vuoto o encoding selezionato), anziche guardia piu confronto
  separati. Nessun helper, wrapper, duplicazione o guardia esterna rimossa.
- Metriche prima/dopo: target cog `23 -> 21`, cyc `21 -> 19`, LOC `62`
  invariata; somme runtime cog `492 -> 490`, cyc `505 -> 503`;
  file LOC `2202`, 109 callable e numero violation invariati.
  `IMPROVED`: riduzione aggregata senza spostare debito. Rimane debito
  legacy: ciclomatica `19` ancora error-level, cognitiva `21` e LOC `62`
  warning-level. Nessuna dichiarazione di chiusura di tutto il servizio.
- Ruff runtime/test, whitespace e ratchet autorevole mirato contro
  merge-base `main` passati senza findings. Baseline, eccezioni, scope e
  soglie invariati. AST di 108 funzioni top-level invariato; anche tutto
  il validatore fuori dal singolo predicato e identico alla prima slice.
  Evidenze `/tmp/gaia-gis-zip2-{before,after}.json`,
  `/tmp/gaia-gis-zip2-ast-invariants.json` e log characterization/
  target-after/ratchet con lo stesso prefisso. `make quality-test`: 144
  test passati.
- Gate corpus completo GIS/Catasto GIS: 289 test passati, fresh full-file
  100% statement `1072/1072` e branch `324/324`, nessuna linea/branch
  mancante o esclusa, nessun test saltato. Exit code e asserzioni passati,
  non usati i soli nove casi ZIP come prova del gate. Directory indicata
  da `/tmp/gaia-gis-zip2-final-run-dir`. Restano 102 warning PyJWT sulla
  chiave HMAC del fixture preesistente; nessuna regressione osservata.
- Graphify backend aggiornato tramite target dedicato: 861 file AST,
  nessun cambio di topologia rilevato, output lasciati coerentemente
  invariati. Docs piattaforma riallineati dopo il gate tramite target
  dedicato; verificare chunk completati, non soltanto l'exit code.
  PostGIS/QGIS live ed E2E non eseguiti; nessun commit o push autorizzato
  in questa slice.

### GIS - validazione ZIP, costruzione warning (2026-10-03)

- Ripresa della sola slice `_validate_shapefile_zip` autorizzata dopo
  la caratterizzazione full-file; checkout `main@b824e2f1`. Preservati
  tutti i lavori concorrenti e i test GIS della tranche precedente.
- Invarianti: encoding esplicito/CPG/default, confronto case-insensitive,
  assenza versus CPG vuoto, ordine warning, errori HTTP, SRID, checksum,
  geometrie e attributi invariati. Nessuna guardia auth o input eliminata;
  schema, endpoint, staging, transazioni e concorrenza non modificati.
- Slice minima: costruire la lista warning da due condizioni ordinate,
  senza helper o wrapper. Valori stringa vuoti mantengono lo stesso
  short-circuit e truthiness; non e una nuova policy di validazione.
  Sette test ZIP reali gia caratterizzati passano dopo il cambiamento.
- Metriche prima/dopo: target cog `25 -> 23`, cyc `22 -> 21`, LOC
  `63 -> 62`; somme runtime cog `494 -> 492`, cyc `506 -> 505`,
  file LOC `2203 -> 2202`, 109 callable invariati. Error-level
  `16 -> 15`, warning `23 -> 24` per il downgrade della sola cognitiva.
  Classificazione `IMPROVED`: riduzione aggregata senza trasferire debito.
  Rimangono la ciclomatica error-level `21`, LOC warning `62` e gli altri
  debiti legacy del servizio, non dichiarati eliminati.
- Ratchet autorevole mirato contro merge-base `main` passato senza
  findings, Ruff runtime/test e whitespace verdi. Baseline, scope,
  eccezioni e soglie invariati. AST di 108 funzioni top-level identico;
  anche tutto il validatore fuori dal blocco warning e identico.
  Evidenze `/tmp/gaia-gis-zip-{before,after}.json`,
  `/tmp/gaia-gis-zip-ast-invariants.json` e ratchet/target-tests log
  con lo stesso prefisso. `make quality-test`: 144 test passati.
- Gate conclusivo corpus GIS/Catasto GIS: 287 test passati, coverage
  fresh full-file 100% statement `1072/1072` e branch `324/324`,
  nessuna linea/branch esclusa o mancante, nessun test saltato.
  Report/log nella directory indicata da
  `/tmp/gaia-gis-zip-final-run-dir`; i denominatori cambiano rispetto
  alla caratterizzazione per la sola costruzione warning rifattorizzata.
  Nessuna regressione osservata; restano 102 warning PyJWT preesistenti
  sulla chiave HMAC del fixture. I sette test mirati non sostituiscono
  questa verifica full-file; asserzioni ed exit code del corpus passati.
- Graphify backend aggiornato (9933 nodi, 25242 archi); HTML non generato
  per limite dimensionale, JSON/report aggiornati. Docs piattaforma
  riallineati dopo il gate finale tramite target dedicato. Nessun secondo hotspot aperto,
  nessun commit o push autorizzato in questa tranche. PostGIS/QGIS live
  ed E2E non eseguiti; i test usano i contratti e il DB SQLite esistenti.

### GIS - caratterizzazione full-file del servizio (2026-10-03)

- Tranche di soli test autorizzata dopo il blocco del run API isolato;
  checkout `main@9836f719`, runtime GIS pulito e mantenuto byte-identico
  a HEAD. Nessuna modifica a API, schema, autenticazione, autorizzazione,
  transazioni, concorrenza o comportamento. GATE, Capacitas e altri team
  esclusi; nessuna nuova esclusione coverage o sincronizzazione baseline.
- Il corpus GIS/Catasto GIS esistente, misurato insieme, copre gia il
  servizio full-file: non serviva inventare casi per colmare il report
  della sola suite API. Aggiunti comunque 34 contratti pertinenti in
  `backend/tests/test_gis_services_contracts.py`, oltre ai sette ZIP/encoding
  conservati dalla tranche precedente: patch annotate no-op e reali,
  input null/invalidi, isolamento layer, stati terminali, metadata,
  review/reset, listing senza leakage, apply con target assente e audit.
- I test usano il fixture DB API esistente e sessioni SQLite reali:
  verificano valori dopo commit/rollback, campi cambiati nell'audit,
  nessun audit di successo dopo failure, actor e timestamp review.
  La tabella sorgente di test viene rimossa dal teardown; nessun mock
  sostituisce persistenza o dominio. Gli errori iniziali di setup (tabella
  custom non rimossa) e payload attachment (stringa invece di oggetto)
  erano difetti del nuovo test, corretti prima del gate finale.
- Run finale isolato, senza riuso di dati coverage: `287 passed`, nessun
  test saltato; `services.py` statement `1076/1076`, branch `328/328`,
  100% full-file, zero linee/branch mancanti o esclusi. Verificate tutte
  le asserzioni e l'exit code, non solo la percentuale. Il primo run
  combinato includeva ancora il payload test errato ed era rosso pur
  mostrando 100% coverage: non e usato come prova del gate superato.
  Suite nuova separata: 34 passati. Restano 102 warning PyJWT sulla
  chiave HMAC breve del fixture preesistente.
- Comando riproducibile in `docs/GIS_SHAPEFILE_IMPORT_RUNBOOK.md`;
  ultimo report/log nella directory indicata da
  `/tmp/gaia-gis-characterized-run-dir`, misura fresh con `mktemp` e
  `--cov-fail-under=100`. JSON controllato per statement/branch completi.
  Il run limitato del 2026-10-02 resta evidenza storica parziale, non lo
  stato finale del corpus. Gate coverage full-file ora VERDE.
- Ruff sui due file test, formatter del nuovo file, diff whitespace e
  `make quality-test` (144 test) passati. Ratchet mirato contro merge-base
  `main` passato senza findings; metriche runtime invariate: validatore
  cog/cyc/LOC `25/22/63`, file LOC `2203`, 109 callable, somme `494/506`.
  Verificata anche la coerenza delle linee tra AST sorgente e bytecode
  caricato; nessun risultato basato su una sorgente runtime diversa.
- Non e un refactoring `IMPROVED` o una nuova estrazione: e una tranche
  di caratterizzazione. Backlog passa da blocked a ready. Nessuna
  semplificazione runtime applicata e nessun commit autorizzato in questa
  tranche; riprendere il validatore richiede la successiva slice.
- Graphify backend aggiornato (9916 nodi, 25219 archi), HTML non generato
  per limite dimensionale; JSON/report aggiornati. Docs piattaforma
  riallineati tramite target dedicato dopo le evidenze finali, con
  `chunk 1/1 done`, nessun warning di chunk falliti; log
  `/tmp/gaia-gis-characterized-graph-docs.log`. Target rieseguito dopo
  l'ultima precisazione sui reset nullable, senza dichiarare riusciti
  refresh semantici sulla sola base dell'exit code.
  PostGIS/QGIS live, network e E2E non eseguiti: i test SQL di adattatore
  non sostituiscono una verifica live. Nessuna regressione osservata
  nel corpus eseguito, nessuna dichiarazione di coverage globale repository.

### Elaborazioni - sezione Capacitas dal link (2026-10-03)

- Hotspot unico `getCapacitasSectionFromHref`, checkout `main@9836f719`;
  runtime/test puliti, Graphify consultato, altri lavori preservati.
- Prima: cognitiva/ciclomatica/LOC/nesting `22/10/14/2`.
- Slice: lookup tipizzato delle sei sezioni, mantenendo URL parsing,
  query prioritaria all'hash anche se vuota/sconosciuta, primo parametro
  duplicato, matching esatto, fallback particelle, catch e SSR senza window.
  UI, routing degli altri workspace e lifecycle modale invariati.
- Ventitre nuovi casi verificano tutte le sezioni via hash/SSR, priorita
  query, parametri duplicati, encoding, casing/whitespace e chiavi prototype.
  Suite prima/dopo: 50 test verdi, full-file 100% su tutte le metriche.
  Una prima asserzione SSR confrontava testo contiguo con HTML contenente
  marker React: normalizzati i soli commenti nel test prima della slice.
- Dopo: cognitiva `22 -> 7`, ciclomatica `10 -> 5`, LOC `14 -> 13`,
  nesting `2` invariato. Callback find `0/1/1/0`, nessuna violation nuova.
  Aggregati file cognitiva `48 -> 33`, ciclomatica `45 -> 41`, LOC `191 -> 190`,
  callable `11 -> 12`. Esito `IMPROVED`, nessun debito trasferito; warning
  `4 -> 2`, error `1` invariato. Target senza violation; restano debito
  del renderer e LOC del componente modale, non toccati dalla slice.
- Coverage dopo: statement `73/73`, branch `48/48`, funzioni `12/12`,
  linee `71/71`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo con `findings: []`, merge-base `6b61fd27`; baseline/scope invariati.
  ESLint, typecheck senza incremental, 144 test tooling e whitespace verdi.
  Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
- Evidenze `/tmp/gaia-capacitas-section-{before,after}.{json,md}`, log
  characterization/after/ratchet-before/after/lint/types/quality e Graphify
  con lo stesso prefisso. Un solo hotspot, commit isolato dopo i gate
  secondo autorizzazione vigente; altri lavori preservati, nessun push.

### Utenze - conteggi nel riepilogo avvisi (2026-10-02)

- Hotspot unico `buildPaymentNoticeSummary`, checkout `main@8d89faf6`;
  runtime/test puliti, Graphify consultato, lavori concorrenti preservati.
- Prima: cognitiva/ciclomatica/LOC/nesting `10/11/25/0`.
- Slice: somma dei conteggi paid/partial non negativi al posto della
  disgiunzione dei due confronti. Invarianti: conteggi da lunghezze array,
  soglia residuo stretta `0.005`, precedenza paid senza debito, lista vuota,
  importi, label/descrizioni e immutabilita.
- Dieci nuovi test caratterizzano conteggi vuoti/paid/partial/unpaid/misti
  e residui sotto/sulla/sopra soglia. Suite prima/dopo: 28 test verdi;
  full-file 100% statement `47/47`, branch `59/59`, funzioni `9/9`,
  linee `38/38` dopo la slice.
- Dopo: cognitiva `10 -> 9`, ciclomatica `11 -> 10`, LOC/nesting `25/0`
  invariati. Aggregati file cognitiva `51 -> 50`, ciclomatica `44 -> 43`,
  nove callable e LOC `76` invariati. Esito `IMPROVED`, nessun nuovo helper
  o debito trasferito; tre warning legacy e zero error invariati, warning
  ciclomatico del riepilogo ancora presente alla soglia `10`.
- Ratchet mirato autorevole contro `origin/main` PASS prima/dopo con
  `findings: []`, merge-base `6b61fd27`; baseline/scope invariati.
  ESLint, typecheck senza incremental, 144 test tooling e whitespace verdi.
  Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
  Evidenze `/tmp/gaia-payment-summary-` per metriche
  before/after, characterization/after, ratchet-before/after e gate.
  Un solo hotspot; commit isolato autorizzato dopo i gate, nessun push.

### GIS - audit validazione ZIP e caratterizzazione encoding (2026-10-02)

- Slice autorizzata sul solo `_validate_shapefile_zip` in
  `backend/app/modules/gis/services.py`, checkout `main@8d89faf6`;
  nessuna modifica concorrente nel perimetro GIS. Auth, permessi, errori
  HTTP, checksum, staging e transazioni sono invarianti non modificabili.
- Prima: cognitiva `25`, ciclomatica `22`, LOC `63`; file `2203` LOC,
  109 callable, somme cog/cyc `494/506`. Test esistenti API verificano
  import valido, 403 viewer, archivi incompleti/corrotti/insicuri, SRID,
  report, persistenza nello staging e lifecycle. Sette nuovi casi reali
  coprono priorita encoding esplicito/CPG/default, spazi, case-insensitive,
  CPG vuoto/presente/assente, warning e contenuto geometrico/DBF invariato.
  Tutti passano sul codice originale; nessun mock di shapefile impossibili.
- Valutata una sola semplificazione dichiarativa dei warning, senza helper:
  cog/cyc/LOC del target `25/22/63 -> 23/21/62`, somme `492/505`,
  109 callable invariati. Ratchet contro merge-base `HEAD@8d89faf6`
  passato senza findings; baseline, soglie ed esclusioni invariati.
- Il run completo `test_gis_platform_api.py` passa, ma il runtime full-file
  non soddisfa la policy: statement `952/1072` (88,81%), branch `152/324`
  (46,91%), combinato 79,08%; 120 linee e 172 branch non coperti,
  tutti fuori dal validatore, che e gia coperto interamente. Warning
  dipendenza PyJWT su chiave HMAC breve nell'ambiente di test.
  Evidenze `/tmp/gaia-gis-before-coverage.json` e `/tmp/gaia-gis-before.log`.
- Stop condition: caratterizzare il resto delle responsabilita di questo
  servizio supererebbe la singola slice autorizzata. Runtime ripristinato
  integralmente; conservati solo i sette test pertinenti. Metriche finali
  identiche a prima, nessun nuovo runtime scoperto, nessuna regressione
  osservata nei test eseguiti. Classificazione `BLOCKED` per requisito
  full-file, non `IMPROVED`; proposta non applicata ne committata.
- Ruff su servizi/test e whitespace passati. Log dei nuovi test prima/dopo
  e finali `/tmp/gaia-gis-{characterization,after-target,final-target}.log`;
  metriche della proposta `/tmp/gaia-gis-{before,after}.json`.
  Runbook chiarisce i warning implementati, Graphify backend/piattaforma
  aggiornati tramite target dedicati. API/DB reali PostGIS ed E2E non
  verificati: i test API impiegano il database SQLite di caratterizzazione.
- Regressione finale mirata: nove test passati, sette nuovi encoding e due
  API su import/persistenza/403 e invalidi; 63 deselected, quattro warning
  PyJWT preesistenti. Log `/tmp/gaia-gis-final-regression.log`. Graphify
  backend aggiornato (9885 nodi, 25175 archi); docs completato con
  `chunk 1/1 done`, senza chunk falliti, poi riallineato ai registri finali.
- Decisione richiesta alla chiusura del 2026-10-02: autorizzare una tranche dedicata di caratterizzazione
  full-file GIS prima del refactoring, oppure scegliere un hotspot gia
  coperto al 100%. Tranche autorizzata e completata il 2026-10-03 come
  riportato sopra: il blocco coverage e risolto, runtime ancora invariato.
  GATE e lavori concorrenti restano esclusi, nessun commit.

### Utenze - riconoscimento degli stati espliciti degli avvisi (2026-10-02)

- Hotspot unico: `getPaymentNoticeStatus`, checkout `main@1e6e2677`;
  runtime/test puliti, Graphify frontend consultato, altri team esclusi.
- Prima: cognitiva `22`, ciclomatica `14`, LOC `15`, nesting `1`;
  otto callable e tre warning nel file, zero error. Suite iniziale sette
  test verdi e full-file 100% su tutte le metriche.
- Slice: lookup tipizzato dei tre stati espliciti ammessi, senza alterare
  parsing degli importi, classificazione derivata, riepiloghi o soglie.
  Invarianti: stato esplicito prioritario, matching esatto case-sensitive,
  stato sconosciuto/nullish usa gli stessi fallback finanziari e label;
  nessuna mutazione.
- Caratterizzazione: 11 nuovi casi, tutti gli stati espliciti contro tre
  classificazioni derivate contraddittorie, valori nullish/sconosciuti,
  casing/whitespace e chiavi prototype; immutabilita verificata.
  Suite prima/dopo 18 test verdi e full-file 100% su tutte le metriche.
- Dopo: cognitiva `22 -> 18`, ciclomatica `14 -> 12`, LOC `15 -> 14`,
  nesting `1` invariato. Callback find `0/1/1/0`, nessuna violation;
  aggregati file cognitiva `55 -> 51`, ciclomatica `45 -> 44`, LOC `77 -> 76`,
  callable `8 -> 9`. Esito `IMPROVED`, debito non trasferito; tre warning
  legacy e zero error invariati (stato avvisi e riepilogo ancora sopra soglia).
- Coverage dopo: statement `47/47`, branch `61/61`, funzioni `9/9`,
  linee `38/38`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo, merge-base `6b61fd27`, `findings: []`; baseline/scope invariati.
  ESLint, typecheck senza incremental, 144 test tooling e diff whitespace verdi.
- Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
  Evidenze `/tmp/gaia-payment-status-{before,after}.{json,md}`, log initial/
  characterization/after/ratchet-before/ratchet-after/lint/types/quality e
  Graphify con lo stesso prefisso. Nessuna conformita globale dichiarata.
  Un solo hotspot, commit isolato dopo i gate secondo l'autorizzazione
  vigente; nessun push, modifiche degli altri team preservate.

### Network - parsing della sorgente HTTP amministrativa (2026-10-02)

- Hotspot unico: `getNetworkDeviceAdminUrl`, checkout `main@3e4d6801`;
  runtime e test puliti. Graphify frontend consultato; altri team esclusi.
- Prima: cognitiva `18`, ciclomatica `12`, LOC `24`, nesting `2`;
  nove callable e due warning nel file, nessun error.
- Slice: parsing comune della sorgente HTTP assente/vuota e controllo
  dichiarativo dei due schemi ammessi, eliminando il livello esterno.
  Invarianti: precedenza target assoluto/relativo, sorgente HTTP, porte;
  casing, porta non vuota ma non validata, suffix dopo il secondo segmento
  ignorato, fallback 443 prima di 80, null e immutabilita preservati.
- Caratterizzazione: 12 nuovi casi su sorgente assente/vuota, schema e porta
  mancanti, casing/whitespace, porta zero/testuale e segmenti extra.
  Suite prima/dopo: 42 test verdi e full-file 100%; nessun comportamento nuovo.
- Dopo: cognitiva `18 -> 13`, ciclomatica `12 -> 11`, LOC `24 -> 21`,
  nesting `2 -> 1`. Nessun nuovo callable; aggregati file cognitiva `44 -> 39`,
  ciclomatica `39 -> 38`, LOC `80 -> 77`, nove callable invariati.
  Esito `IMPROVED`; warning `2 -> 1`, zero error: cognitiva sotto soglia,
  resta soltanto il warning cyclomatic del resolver.
- Coverage dopo: statement `41/41`, branch `53/53`, funzioni `9/9`,
  linee `41/41`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo, merge-base `6b61fd27`, `findings: []`; baseline/scope invariati.
  ESLint, typecheck senza incremental, 144 test tooling e diff whitespace verdi.
- Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
  Evidenze `/tmp/gaia-network-source-{before,after}.{json,md}`, log
  characterization/after/ratchet-before/ratchet-after/lint/types/quality e
  Graphify con lo stesso prefisso. Nessuna conformita globale dichiarata.
  Un solo hotspot, commit isolato dopo i gate secondo l'autorizzazione
  vigente; nessun push, modifiche degli altri team preservate.

### Catasto - descrizione degli importi anomali (2026-10-02)

- Hotspot unico: `describeCatastoAnomalia`, checkout `main@368731e9`;
  runtime e test inizialmente puliti, altri lavori preservati.
- Prima: cognitiva `60`, ciclomatica `32`, LOC `54`, nesting `1`.
  Graphify frontend consultato per consumatori e impatto.
- Slice: consolidare la descrizione delle voci 0648/0985 di VAL-07,
  senza modificare explainCatastoAnomalia o gli altri tipi di anomalia.
  Invarianti: testo esatto, ordine voce/atteso/delta, precisione quattro
  decimali, omissione solo nullish dei campi, accettazione degli oggetti,
  fallback e comportamento legacy sui numeri non validi.
- Caratterizzazione: 15 nuovi casi per entrambe le voci, testo completo,
  ordine e immutabilita; zero, stringhe numeriche, valori invalidi/non finiti,
  nullish e oggetti vuoti preservati (anche il testo legacy `null`).
  Suite prima/dopo: 35 test verdi, coverage full-file 100% su tutte le metriche.
- Dopo: descrittore cognitiva `60 -> 44`, ciclomatica `32 -> 24`,
  LOC `54 -> 49`, nesting `1` invariato. Helper privato condiviso delle
  due voci cognitiva/ciclomatica/LOC/nesting `5/5/8/1`, nessuna violation.
  Aggregati file: cognitiva `133 -> 122`, ciclomatica `88 -> 85`, callable
  `15 -> 16`, LOC `337 -> 340`. Esito `IMPROVED`, debito non trasferito.
  Violation `7 -> 6` (error `5` invariati, warning `2 -> 1`): warning LOC
  del descrittore eliminato; resta il debito legacy dei due descrittori.
- Coverage dopo: statement `97/97`, branch `123/123`, funzioni `16/16`,
  linee `87/87`. Ratchet mirato autorevole contro `origin/main` PASS prima
  e dopo, merge-base `6b61fd27`, `findings: []`; baseline/scope invariati.
  ESLint senza errori: unico warning multiplierDigits preesistente,
  riprodotto sul runtime HEAD. Typecheck senza incremental, 90 test tooling
  e diff whitespace verdi. Nessuna conformita globale dichiarata.
- Graphify frontend aggiornato; refresh platform docs completato con
  `chunk 1/1 done`, senza warning di chunk semantici falliti.
  Evidenze before `/tmp/gaia-next-catasto-metrics.{json,md}`, after e log
  characterization/after/ratchet-before/ratchet-after/lint/lint-before/types/
  quality/Graphify con prefisso `/tmp/gaia-catasto-description-`.
  Un solo hotspot, commit isolato dopo i gate secondo l'autorizzazione
  vigente; nessun push, nessuna modifica agli altri team.

### Wiki supporto - query opzionale del link (2026-10-02)

- Hotspot unico: `buildSupportHrefFromPayload`, checkout `main@c4fa269c`,
  file inizialmente pulito; mapper precedente e lavori concorrenti preservati.
- Prima: cognitiva `10`, ciclomatica `11`, LOC `23`, nesting `1`;
  file cognitiva `16`, ciclomatica `22`, sei callable, unico warning cyclomatic.
- Invarianti: ordine e nomi query, default nullish dei campi obbligatori,
  omissione dei valori falsy opzionali, whitespace e stringa zero conservati,
  encoding URLSearchParams, draft ultimo, nessuna mutazione payload.
- Slice: tabella readonly delle sette chiavi opzionali e serializzazione
  comune con forEach; draft separato e ultimo. Quattordici nuovi test di
  caratterizzazione verificano omissione, encoding, ordine e immutabilita.
- Dopo: builder cognitiva `10 -> 4`, ciclomatica `11 -> 5`, LOC `23 -> 22`,
  nesting `1` invariato; callback `1/2/6/1`, nessuna violation nuova.
  File: cognitiva `16 -> 11`, ciclomatica `22 -> 18`, callable `6 -> 7`,
  LOC `106 -> 114` per la tabella dichiarativa; warning `1 -> 0`, zero error.
  Esito `IMPROVED`, riduzione reale anche includendo la callback.
- Sessanta test di regressione supporto passati prima e dopo; full-file
  100% statement (`27/27`), branch (`20/20`), funzioni (`7/7`), linee (`24/24`).
  ESLint runtime/test, typecheck senza incremental e 90 test tooling verdi.
  Ratchet mirato autorevole contro `origin/main`, merge-base `6b61fd27`,
  PASS con `findings: []`; baseline, scope ed eccezioni invariati.
- Evidenze `/tmp/gaia-wiki-href-{before,final}.json`, log characterization,
  final, ratchet-final, lint-final, types-final, quality e Graphify con lo
  stesso prefisso. Graphify frontend aggiornato tramite target dedicato;
  refresh platform docs completato con `chunk 1/1 done`, senza warning di
  chunk falliti. Diff whitespace verde; nessuna conformita globale dichiarata.
  Un solo hotspot, commit isolato autorizzato dopo i gate; nessun push.

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

### Organigramma - completamento coverage controller al 100% (2026-10-02)

- L'utente autorizza esplicitamente la rimozione dei soli controlli interni
  dimostrati ridondanti. Nessuna guardia auth, permessi, input o API rimossa;
  nessuna esclusione o modifica della baseline. Giornalieri GATE invariati.
- Controller layout con tre operazioni di realignment/layout/compattazione e
  risoluzione del padre settore, 32 test pertinenti con geometria reale;
  controller loading con loadCore/refreshStructure, 18 test su cataloghi,
  selezione, token, auth/ruoli e failure atomiche della lettura. Viewport esteso
  al lifecycle drag/focus: 16 test su listener, cleanup, pointer cancel,
  persistence, sessione/edit e nodi eliminati da refresh concorrente.
- Presentazione caratterizzata tramite i contratti nullable esistenti di
  TreeNode, SchemaNodeCard e AssignmentInboxPanel: 7 test su metadata,
  preview, summary parziali, provenance e leaf behavior. Pagina a 159 test,
  includendo preferenze invalide/presentation, operatori senza full_name,
  filtri/menu stale dopo refresh, scope/status null e ricerca senza risultati.
- Invarianti delle rimozioni: tutti i layout assegnano posizioni a ogni ID
  nella foresta, per entrambe le orientazioni e ogni densita; tre test
  verificano totalita, coordinate finite e immutabilita. La coda e densa e
  lo shift avviene solo se non vuota; ID univoci del dominio assicurano
  discendenti non vuoti nel riallineamento. Metadata e nodo menu sono derivati
  dalla stessa foresta; i bottoni subtree/lead verificano gia la disponibilita
  prima della callback. La conferma import viene mostrata solo dopo il file.
  Restano intatte le difese per parent mancanti, cataloghi parziali e ingressi
  del controller, incluse le snapshot stale durante il drag.
- Ultimo run: `434 passed` su 16 suite. Statement `1626/1626`, branch
  `1339/1339`, funzioni `452/452`, linee `1448/1448`: 100% ciascuna.
  Anche ogni singolo runtime modificato raggiunge il 100%: workspace
  `968/968` statement, `952/952` branch, `348/348` funzioni. Gate completo
  frontend VERDE, senza ignore, soglie ridotte, test saltati o mock di layout impossibili.
- Risolta l'ambiguita di matching dopo l'autorizzazione dell'utente:
  renderer `renderSchemaNodeCard` e azioni `selectSchemaSubtree` /
  `openSchemaLeadDrawer` hanno nomi espliciti, senza wrapper o spostamenti
  di responsabilita. Le coordinate del connector sono destrutturate dalla
  stessa mappa totale invece di duplicare alias intermedi. Ratchet mirato
  contro merge-base `main@c4fa269c` PASS, `findings: []`.
  Baseline, eccezioni e scope invariati; nessuna regressione assorbita.
- L'ultimo caso ordinamento e coperto da un catalogo reale con operatore non
  assegnato prima dei due assegnati, verificando ordine e ricerca per username.
  Rimossa la guardia ridondante del reset: l'unico ingresso e il pulsante di
  SchemaBoard, renderizzato solo nella vista schema. Test nelle due
  orientazioni verificano reset e persistenza delle preferenze canoniche,
  senza scritture della struttura. Eliminata soltanto la dipendenza `view`
  divenuta inutilizzata; le altre dipendenze hook restano invariate.
- ESLint zero errori/due warning hook legacy; typecheck runtime senza
  incremental passato; `make quality-test` 90 test verdi. Evidenze finali:
  `/tmp/gaia-org-100.log` e directory coverage `/tmp/gaia-org-100`,
  `/tmp/gaia-org-100-{ratchet,eslint,types,quality}.log` e
  `/tmp/gaia-org-100-metrics.json`. Nessun commit, push o deploy.
- Metriche pre-controller/attuali: workspace cog `477 -> 167`, cyc
  `363 -> 147`, LOC `1779 -> 1086`; file LOC `4305 -> 3593`.
  Aggregati workspace/sei controller: cog `1508 -> 1173`, cyc
  `1619 -> 1411`, callable `404 -> 435`. Le estrazioni restano
  `REORGANIZED_AND_CHARACTERIZED`: le somme cambiano anche per ownership
  e nested counting, non sono una prova di riduzione del debito aggregato.
  Le sole difese ridondanti eliminate sono descritte negli invarianti sopra.
- Verifica AST finale: 26 corpi funzione dei controller mutazioni/snapshot/
  selezione/caricamento e quattro componenti presentazione identici allo
  snapshot originale, ignorando commenti/indentazione. Le sole semplificazioni
  runtime intenzionali sono documentate negli invarianti di questa tranche.
- Graphify frontend aggiornato con `--force`: 624 file AST, 7358 nodi e
  17726 archi. Target docs dominio/piattaforma tentati; entrambi segnalano
  `chunk 1/1 failed: Connection error` e risultati parziali, non refresh
  semantico completo. Log `/tmp/gaia-org-100-graph-*.log`.

#### Verifica finale e gate commit (2026-10-02)

- Run finale: 434 test / 16 suite; coverage frontend full-file invariata al
  100% su tutte le quattro metriche. Typecheck senza incremental, ESLint
  (zero errori, due warning hook legacy), Ruff sui due file Python toccati,
  formatter del nuovo test e diff whitespace passati. Ratchet mirato contro
  `main@c4fa269c` passato, senza findings o modifiche della baseline.
- Tooling: 90 test passati anche misurando i subprocess CLI con Coverage
  `patch = subprocess` in una configurazione temporanea fuori repository.
  La funzione modificata `added_lines_since` ha tutte le linee e i branch
  coperti. Il file runtime `tools/code_quality/complexity.py`, pero, resta
  a `600/703` statement (85,35%) e `210/272` branch (77,21%), 83,08%
  combinato: 103 linee e 62 branch non coperti fuori dalla funzione modificata.
  Il requisito full-file GAIA non e soddisfatto: il gate commit complessivo
  era BLOCCATO in questo run, nonostante il gate frontend verde; risolto
  dalla slice tooling successiva riportata sotto. Nessun test artificiale,
  esclusione o abbassamento della soglia introdotto per aggirarlo.
- Evidenze riproducibili: `/tmp/gaia-org-release-coverage.log`, report in
  `/tmp/gaia-org-release-coverage`, log ratchet/eslint/types con lo stesso
  prefisso; `/tmp/gaia-org-release-tooling-subprocess.log` e relativo JSON.
  La sola misura in-process non includeva i test CLI ed e stata sostituita
  dalla misura completa. Copertura live API/DB ed E2E non verificata in
  questa tranche frontend: i test API dei controller usano i mock dei
  contratti esistenti, non provano integrazioni con servizi esterni reali.
- Graphify codice finale rigenerato con `make graphify-frontend
  GRAPHIFY_CODE_FLAGS=--force`: 624 file, 7358 nodi, 17726 archi; HTML
  omesso dal limite dimensionale del visualizzatore, JSON/report aggiornati.
  Docs dominio: chunk semantico fallito per `Connection error`, risultati
  parziali non equivalenti a refresh completo. Il target piattaforma
  iniziale ha riutilizzato la cache; il refresh del documento aggiornato
  fallisce anch'esso con `chunk 1/1 failed: Connection error`, risultati
  parziali. Entrambi i grafi docs richiedono un retry con backend raggiungibile.
  I log finali sono `/tmp/gaia-org-release-graph-{code,domain,platform}.log`.
- Nessuna regressione osservata nelle suite eseguite; debito legacy di
  complessita e due warning hook restano dichiarati. Non e stata verificata
  l'intera working tree concorrente e nessun lavoro degli altri team e stato
  incluso. Nessun commit eseguito in questo run: la caratterizzazione del
  tooling e stata autorizzata come slice separata e completata sotto.

#### Slice tooling - contratti e coverage full-file (2026-10-02)

- Slice separata autorizzata dall'utente dopo il blocco full-file. Aggiunti
  54 casi pertinenti in `test_complexity_contracts.py` e
  `test_complexity_matching_contracts.py`: classi Python, parametri, bool e
  comprehension, scope runtime, eccezioni, parser JS e dipendenze mancanti,
  errori Git, baseline corrotta, comparazione limitata ai file cambiati,
  drift di scope/engine, migrazione esplicitamente approvata, verifica
  read-only e rifiuto di baseline locali non autorevoli. Matching coperto
  per duplicati/rename/move, gruppi equivalenti, crescita, span ambigui,
  tie-break univoco e callable interamente aggiunti senza ownership inventata.
- Rimossa soltanto la guardia interna `child is not root` del traversal:
  `ast.parse` produce alberi aciclici, `ast.iter_child_nodes` restituisce
  esclusivamente figli, non antenati. Tre test su AST realmente parsati
  dimostrano l'invariante e le metriche attese per funzioni semplici,
  condizionali e annidate. Nessun AST ciclico sintetico, ignore coverage,
  nuova soglia o baseline modificata; output dello scanner su sorgenti
  valide invariato. Test degli errori esterni continuano a verificare il
  fail-closed e l'assenza di riscritture dei dati.
- Metriche prima/dopo della sola semplificazione: `py_complexities`
  cog/cyc/LOC `8/7/37 -> 6/6/36`; callback `walk`
  `8/7/20 -> 6/6/19`; `added_lines_since` invariata `14/11/26`.
  Evidenze `/tmp/gaia-tooling-{before,after}.json`; nessun trasferimento
  di responsabilita o nuovo callable runtime.
- Suite completa: 144 test passati, coverage full-file
  `702/702` statement e `270/270` branch, 100% senza esclusioni.
  Coverage include i subprocess CLI tramite configurazione temporanea
  `patch = subprocess`; nessuna configurazione CI/versionata modificata.
  Report `/tmp/gaia-tooling-final.json`, log `/tmp/gaia-tooling-final.log`.
  Ruff e format check dei nuovi test verdi, whitespace pulito; ratchet
  Organigramma contro il merge-base corrente `main` verde, senza findings.
  La slice frontend resta `REORGANIZED_AND_CHARACTERIZED`, senza debito
  legacy dichiarato eliminato; i due warning hook legacy rimangono.
- Superato il precedente blocco coverage del tooling; commit autorizzato
  dopo la verifica conclusiva e solo per le modifiche Organigramma/tooling
  e le rispettive sezioni dei documenti condivisi, escludendo altri team.
  Graphify frontend aggiornato; docs dominio/piattaforma rieseguiti dopo
  l'aggiornamento delle evidenze: entrambi falliscono il chunk semantico
  per `Connection error`, con warning partial results. Il codice e
  aggiornato; il refresh semantico docs resta incompleto per la rete.
  Log `/tmp/gaia-tooling-graph-{code,domain,platform}.log`.
- Verifica conclusiva combinata: 434 test frontend e 144 test tooling
  passati, coverage 100% per-file sui runtime toccati. Ruff/formatter,
  ESLint (due warning legacy), typecheck e ratchet mirato passati.
  Nessuna regressione osservata; integrazioni API/DB live ed E2E non
  rieseguite. Nessun commit o push di modifiche estranee autorizzato.
- Commit finale tentato dopo i gate: `git add` dei soli quattro file
  tooling rifiutato con `.git/index.lock: File system in sola lettura`.
  Nessuna modifica all'index; commit non creato e nessun tentativo di
  aggirare il sandbox. Il solo blocco locale al commit e il filesystem;
  patch isolata Organigramma/tooling preparata in
  `/tmp/gaia-organigramma-final.patch`, senza documenti degli altri team
  o grafi generati. Il retry richiede un ambiente con Git scrivibile.
- Retry autorizzato dall'utente con filesystem ora scrivibile: patch
  rigenerata contro HEAD corrente per escludere le modifiche concorrenti
  Utenze, Presenze e Dotazioni. Controlli conclusivi rieseguiti prima del
  commit isolato; nessun push o integrazione live aggiuntiva autorizzata.

### Organigramma - controller snapshot, viewport e selezione (2026-10-02)

- Prosecuzione della slice controller autorizzata, stesso hotspot workspace.
  Nessuna modifica alle giornaliere GATE, al backend, ai contratti REST,
  alle esclusioni coverage o alla baseline. Working tree concorrente preservato;
  nessun commit creato da questa sessione.
- Estratti sette handler snapshot, quattro viewport e sei selezione con
  contesti tipizzati e adapter che ricevono lo stato della render corrente.
  Le dipendenze hook originali restano invariate. Verifica AST sullo snapshot
  originale `af768d77`: 28 corpi funzione, incluse funzioni annidate dei quattro
  controller, identici ignorando commenti/indentazione. Anche il corpo del
  drawer esportato per test standalone resta identico.
- Nuovi test controller: snapshot 32, viewport 23, selezione 35, tutti verdi.
  Copertura full-file: snapshot `82/82` statement, `42/42` branch, `7/7`
  funzioni e `72/72` linee; viewport `117/117`, `36/36`, `16/16`, `104/104`;
  selezione `62/62`, `57/57`, `13/13`, `50/50` (100% ciascuna).
  Il controller mutazioni conserva il 100%; contesti type-only senza runtime.
- Quattordici test geometria coprono coordinate invalide, bounds, foreste
  ramificate, immutabilita, snapshot parziali e collisioni sature nelle due
  orientazioni. Suite pagina a 150 test: deep link, perdita/ripristino sessione,
  auth override, risposte tardive detail/visibilita, nodo orfano, limite shortcut,
  errori layout nelle due orientazioni, drop senza drag, permessi read-only,
  gruppi grandi e drawer con sessione/dati parziali. I test non forzano output
  impossibili dei layout per eseguire guardie interne.
- Nove suite: `336 passed`. Gate completo ROSSO: statement `1614/1633`
  (98,83%), branch `1310/1381` (94,85%), funzioni `444/444` (100%),
  linee `1445/1451` (99,58%). Workspace `1150/1169` statement (98,37%),
  `1024/1095` branch (93,51%), funzioni 100%, linee 99,42%.
  Restano 19 statement e 71 esiti branch: obiettivo 100% non raggiunto e
  change non ancora conforme alla policy runtime modificati.
- Parte del residuo e irraggiungibile per costruzione: mappe posizione appena
  costruite dagli stessi nodi, coda densa non vuota prima di `shift`, fallback
  metadata completo. Chiesta decisione sulla rimozione delle sole difese
  dimostrate ridondanti, invece di introdurre test artificiali o ignore.
  Restano inoltre guardie negli ingressi layout/caricamento e lifecycle.
- Metriche rispetto allo snapshot pre-controller: workspace cog `477 -> 269`,
  cyc `363 -> 225`, LOC `1779 -> 1350`; file LOC `4305 -> 3864`.
  Aggregati dei cinque runtime controller/workspace: cog `1508 -> 1300`,
  cyc `1619 -> 1504`, callable `404 -> 427`. Tutti i corpi estratti invariati:
  calo delle somme dovuto anche al conteggio annidato e ownership, non prova
  di riduzione del debito. Esito `REORGANIZED_AND_CHARACTERIZED`.
  Nessun nuovo error-level nei controller; baseline non aggiornata.
- Ratchet mirato contro merge-base `main@c4fa269c` PASS (`findings: []`);
  HEAD avanzato da altre attivita durante la sessione. Typecheck senza
  incremental PASS; ESLint zero errori e due warning hook legacy invariati.
  `make quality-test`: 90 test verdi; diff whitespace mirato pulito.
  Evidenze: `/tmp/gaia-org-final-review.log` e relativa directory coverage,
  `/tmp/gaia-org-final-metrics.json`, `/tmp/gaia-org-final-ratchet.log`,
  `/tmp/gaia-org-final-{types,eslint}.log`.
- Graphify frontend aggiornato con pruning tramite target dedicato `--force`:
  618 file AST, 7321 nodi, 17609 archi. Target docs dominio/piattaforma tentati:
  entrambi `chunk 1/1 failed: Connection error` e risultati parziali, pur con
  exit 0. Nessun refresh semantico completo dichiarato. Log con prefisso
  `/tmp/gaia-org-final-graph-`.

### Organigramma - slice controller mutazioni (2026-10-02)

- Slice controller autorizzata esplicitamente dopo la caratterizzazione dei
  modal. Un solo hotspot workspace; giornaliere GATE e modifiche concorrenti
  preservate. Nessun commit, nuova esclusione o modifica baseline.
- Estratte sei operazioni in `organigramma-mutations.ts`: spostamento,
  collegamento gerarchico, assegnazione utente, creazione unita, rimozione
  assegnazione e cancellazione unita. Il contesto tipizzato espone soltanto
  dipendenze esistenti; ciascuna operazione riceve il sottoinsieme necessario.
  Gli adapter UI restituiscono la promise del controller direttamente.
- Verifica AST contro `HEAD@af768d77`: tutti i sei corpi handler identici
  ignorando commenti/indentazione. Token, permessi, edit mode, vincoli sui
  discendenti, payload, kind organizzativo/territoriale, conferma e ordine
  API/setter/refresh invariati. Nessun rollback, retry o lock introdotto.
- 54 nuovi test controller: guardie non raggiungibili dalla UI, nodi/utenti
  mancanti, cicli, responsabile occupato, assegnazioni esistenti, coordinate
  assenti/zero, conferma cancellata, selezione funzionale, Error/non-Error,
  fallimenti del refresh e delle operazioni successive, `territoriale`.
  Controller standalone full-file: statement `115/115`, branch `102/102`,
  funzioni `13/13`, linee `98/98` (100% ciascuna).
- Integrazione UI/controller: 215 test verdi su cinque suite. Perimetro
  workspace/controller/helper: statement `1564/1616` (96,78%), branch
  `1250/1381` (90,51%), funzioni `427/427` (100%), linee `1426/1438`
  (99,16%). Workspace 96,31% statement, 89,34% branch, 100% funzioni,
  99,04% linee. Il gate 100% full-file workspace e ancora ROSSO: questa
  estrazione non chiude l'obiettivo coverage e non e una change conforme
  al requisito finale sui runtime modificati.
- Metriche prima/dopo: componente workspace cog `477 -> 393`, cyc
  `363 -> 303`, LOC `1779 -> 1650`; file LOC `4305 -> 4172`.
  Aggregato workspace/controller cog `1508 -> 1424`, cyc `1619 -> 1565`,
  callable `404 -> 410`. Controller cog max `18`, cyc max `14`, LOC `181`:
  nessuna violation error-level nuova. I sei corpi non sono semplificati:
  le somme dello scanner cambiano anche per il conteggio delle funzioni
  annidate e l'ownership. Esito `REORGANIZED_AND_CHARACTERIZED`, non
  `IMPROVED`; nessuna riduzione reale del debito viene dichiarata.
- Ratchet mirato autorevole contro merge-base `main@af768d77`: PASS,
  `findings: []`. ESLint zero errori/due warning hook legacy; typecheck
  senza incremental e diff whitespace verificati. Baseline invariata.
  Graphify frontend aggiornato tramite target dedicato con `--force`.
- Refresh docs dominio e piattaforma tentati con i target dedicati: entrambi
  hanno `chunk 1/1 failed: Connection error` e warning di risultati parziali
  pur con exit 0. Nessun arricchimento semantico completo dichiarato.
- Residui full-file: snapshot/sessione, controller viewport/layout,
  fallback geometria e presentazione. Nessuna guardia eliminata per alzare
  la coverage. La prossima slice deve restare nello stesso hotspot e
  caratterizzare una responsabilita di questi ingressi; il 100% del solo
  controller mutazioni non va presentato come il 100% del workspace.
- Evidenze: `/tmp/gaia-controller-unit-final.log`, directory
  `/tmp/gaia-controller-unit-final`, `/tmp/gaia-controller-final.log`,
  directory `/tmp/gaia-controller-final`, `/tmp/gaia-controller-{before,after}.json`,
  `/tmp/gaia-controller-ratchet.log`, log eslint/types/Graphify con lo stesso
  prefisso. Documentazione dominio e struttura aggiornate.

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

### Organigramma - coverage e correzione tooling (2026-10-02)

- Richiesta esplicita: coverage 100%, estrazioni mirate behavior-preserving e
  follow-up del blocco tooling. Giornalieri GATE e modifiche concorrenti
  preservati; nessun commit, esclusione o aggiornamento baseline.
- Suite UI estesa da 54 a 133 test: sessione, import/export/sync, preferenze,
  filtri, pan/zoom, assegnazioni, gerarchie e errori. Mock resettati tra test.
  Otto test standalone caratterizzano i modal, inclusi callback rifiutate,
  cataloghi vuoti, nomi assenti, default aggiornati e padre mancante.
- Il primo tentativo di split in tre file produceva `ambiguous_fingerprint`
  e associazioni cross-file a simboli estranei. La correzione tooling include
  i file non tracciati nel calcolo delle righe aggiunte; non cambia ordine o
  semantica del matching. Dopo il fix restavano finding di move non riconosciuti.
  Lo split e stato ritirato: i tre modal restano nel modulo e nella posizione
  originale, con soli export per testarli direttamente. Nessuna validazione
  spostata o modifica alla gestione degli errori.
- `make quality-test`: 90 test verdi, inclusi sette nuovi casi sul calcolo
  delle righe aggiunte: file tracked/untracked/ignorati, nomi con spazi,
  file vuoti/binari, errori Git e input senza base/path. Le regressioni gia
  esistenti verificano che callback nuove sopra soglia falliscano ancora
  (exit 1) e matching parziale ambiguo rimanga fail-closed (exit 2).
  Ruff check runtime/test e format check del nuovo test passano.
- Ultima coverage full-file: 161 test verdi su quattro suite, workspace
  statement `1454/1522` (95,53%), branch `1186/1332` (89,03%), funzioni
  `402/402` (100%), linee `1331/1350` (98,59%). I tre modal sono interamente
  coperti; `src/lib/organigramma.ts` resta al 100% su tutte le metriche.
  Gate 100% workspace ancora ROSSO: non dichiarare obiettivo raggiunto.
- Metriche callable workspace invariate: 404 callable, somma ciclomatica
  1619 e cognitiva 1508; `OrganigrammaWorkspace` 363/477/1779.
  Esito della caratterizzazione: `REORGANIZED_AND_CHARACTERIZED`, non
  riduzione della complessita. Ratchet mirato contro merge-base `main`
  (`af768d77`) verde, `findings: []`; baseline e scope invariati.
- Il confronto con `origin/main` usa invece il commit piu vecchio `6b61fd27`
  e segnala due metriche della callback `assignments.find` (cyc 1->2,
  cog 0->1). Il diff runtime workspace corrente ha soltanto tre export:
  quella callback e invariata rispetto a HEAD. Non assorbire i finding
  sincronizzando la baseline remota nella change.
- ESLint mirato: zero errori, due warning legacy sulle dipendenze hook;
  typecheck senza incremental e diff whitespace passano.
  `make lint-backend` si arresta nel compileall globale per permessi sui
  bytecode Wiki concorrenti; non e una failure Ruff del perimetro modificato.
- Residui: guardie auth/permessi negli handler, eliminazione vietata con
  figli/assegnazioni, fallback geometrici e dati inconsistenti. La UI non
  espone diversi ingressi difensivi. Il prossimo blocco deve isolare una
  responsabilita del controller e i relativi test senza spostare il debito
  o alterare contratti; il lavoro corrente non e conforme al gate full-file.
- Graphify frontend aggiornato con pruning tramite target dedicato `--force`:
  7252 nodi e 17472 archi. Refresh platform docs gia tentato con errore di
  connessione semantico; risultato parziale, nessun refresh docs completo
  dichiarato. Evidenze: `/tmp/gaia-org-retained-final.log`, directory
  `/tmp/gaia-org-retained-final`, `/tmp/gaia-org-main-ratchet.log`,
  `/tmp/gaia-org-quality-final.log`, `/tmp/gaia-org-graph-final.log`.

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

### Organigramma workspace - visibilita, override e drawer (2026-10-02)

- Tranche di caratterizzazione autorizzata, limitata alla suite UI esistente;
  giornaliere riservate al team GATE e modifiche concorrenti preservate.
- Prima: 40 test verdi, coverage full-file statement `1029/1522` (67,60%),
  branch `819/1332` (61,48%), funzioni `270/402` (67,16%), linee `945/1350`
  (70%). Il branch differisce di un esito rispetto al run del 2026-10-01.
- Aggiunti 14 test: scelta viewer, visibilita gerarchica/override, perimetro
  vuoto e recupero API, creazione override unita/persona e payload opzionali,
  date e scope, errori API e annullamento, accesso read-only, rendering status
  e fallback, drawer con assegnazioni/percorso e override pertinenti,
  assegnazioni assenti/errori, risposte tardive dopo chiusura e unita sconosciuta.
- Dopo: 54 test verdi; coverage full-file statement `1111/1522` (72,99%),
  branch `952/1332` (71,47%), funzioni `309/402` (76,86%), linee `1015/1350`
  (75,18%). ESLint della suite, typecheck senza incremental e diff check
  passati. Il comando coverage esce 1 soltanto per il gate 100% ancora rosso.
- Metriche callable identiche al report precedente: 404 callable, aggregati
  ciclomatica `1619`, cognitiva `1508`; `OrganigrammaWorkspace` `363/477/1779`.
  Runtime, baseline, eccezioni e configurazione coverage invariati.
- Esito `REORGANIZED_AND_CHARACTERIZED`; refactoring runtime ancora `BLOCKED`
  dal gate full-file. Restano 411 statement e 380 esiti branch scoperti.
  Evidenze in `/tmp/gaia-org-visibility-{before,after}.log`, rispettive directory
  coverage e `/tmp/gaia-org-visibility-metrics.json`.
- Graphify: orientamento tramite query frontend; refresh platform docs tentato
  con target dedicato, ma il chunk semantico fallisce con `Connection error`
  e restituisce risultati parziali pur uscendo 0. Arricchimento documentale
  non verificato; log `/tmp/gaia-org-visibility-graph-docs.log`.
- Prossima azione separata: caratterizzare errori caricamento, esportazione,
  sincronizzazione e gestione assegnazioni prima della slice runtime.

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

### Organigramma workspace - caratterizzazione import JSON (2026-10-01)

- Slice unica successiva autorizzata: import JSON del workspace; giornaliere
  riservate al team GATE. Working tree concorrente preservato.
- Prerequisiti: 25 test UI verdi; coverage reale full-file statement
  `938/1522` (61,62%), branch `755/1332` (56,68%), funzioni `250/402`
  (62,18%), linee `865/1350` (64,07%). Il gate 100% non consente di
  modificare il runtime del workspace.
- Aggiunti 15 test UI nella suite esistente: merge e contatori server,
  conferma esatta replace, cancellazione, duplicati e troncamento messaggio,
  parent/assegnazioni/override mancanti, warning non bloccanti, riferimenti
  validi, errori di lettura in entrambe le modalita e fallimento API replace.
  La funzione `analyzeOrganigrammaSnapshot` non ha statement o branch scoperti
  nel report risultante; nessun export o seam runtime aggiunto per i test.
- Dopo: 40 test verdi; coverage full-file statement `1029/1522` (67,60%),
  branch `820/1332` (61,56%), funzioni `270/402` (67,16%), linee `945/1350`
  (70%). ESLint della suite, typecheck e diff check passati.
- Metriche prima/dopo invariate: `OrganigrammaWorkspace` ciclomatica `363`,
  cognitiva `477`, LOC `1779`; `analyzeOrganigrammaSnapshot` `17/18/47`;
  aggregati file ciclomatica `1619`, cognitiva `1508`, 404 callable.
  Runtime, baseline, eccezioni e configurazione coverage invariati.
- Esito caratterizzazione `REORGANIZED_AND_CHARACTERIZED`; refactoring
  runtime `BLOCKED` dal gate full-file, con 493 statement e 512 esiti branch
  ancora scoperti. Nessuna riduzione di complessita dichiarata.
- Evidenze: `/tmp/gaia-organigramma-workspace-{before,after}.log`, rispettive
  directory coverage e `/tmp/gaia-organigramma-workspace-metrics-before.json`.
  Prossima decisione: tranche separata sui percorsi di visibilita/override e
  drawer persona, mantenendo il requisito 100% prima del refactoring.

### Organigramma - ricerca e inclusione albero (2026-10-01)

- Hotspot unico: `computeTreeInclusion` in `frontend/src/lib/organigramma.ts`;
  confronto autorevole con baseline a `HEAD@af768d77`. Le giornaliere restano
  affidate al team GATE; modifiche concorrenti preservate.
- Invarianti: normalizzazione della ricerca, filtro tipo, ordine dei match,
  inclusione degli antenati e `includeIds=null` senza filtri. Eliminato il
  controllo ridondante sulla ricerca vuota: `String.includes("")` e vero.
  Nessuna estrazione, modifica dei contratti o nuovo callable.
- Prima/dopo: ciclomatica `11 -> 10`, cognitiva `19 -> 17`, LOC `27` invariata;
  aggregati file ciclomatica `55 -> 54`, cognitiva `58 -> 56`, 19 callable.
  Restano due warning e zero error; esito `IMPROVED`.
- Caratterizzazione prima della modifica: 20 test passati; dopo, stessi 20
  test passati. Coverage full-file 100% statement (`88/88`), branch (`49/49`),
  funzioni (`19/19`) e linee (`82/82`). ESLint mirato e typecheck passati.
- `complexity.py ratchet --base-ref HEAD frontend/src/lib/organigramma.ts`:
  PASS, zero finding. Il controllo globale precedente rilevava nove finding
  nei file concorrenti inCASS/accessi/bootstrap; baseline ed eccezioni non
  aggiornate, diff baseline nullo.
- Evidenze in `/tmp/gaia-organigramma-{before,after}.json` e nei log
  `/tmp/gaia-organigramma-tests-{before,after}.log`. Iterazione chiusa;
  prossima azione separata: scegliere una responsabilita del workspace
  Organigramma e verificarne la caratterizzazione prima di modificarla.

### Presenze giornaliere - verifica prerequisiti hotspot (2026-09-30)

- Hotspot autorizzato: `PresenzeGiornalierePage` in
  `frontend/src/app/presenze/giornaliere/page.tsx`; checkout `main@6b61fd27`.
  Modifiche MCP e documentazione concorrenti preservate.
- Metriche runtime prima/dopo invariate: cognitiva `573`, ciclomatica `478`,
  LOC callable `2284`, nesting `3`. Nessun refactoring runtime applicato;
  baseline, eccezioni e configurazione coverage invariate.
- Suite iniziale: 5 test passati e 9 falliti per `useRouter` del componente
  WhatsApp senza App Router montato. Isolato il confine
  `WhatsAppReminderAlert` nella suite della pagina, senza rimuovere assertion.
  I componenti WhatsApp hanno suite dedicate; verifica pagina: 14 test passati.
- Diagnosi coverage: rimossa temporaneamente e poi ripristinata integralmente
  l'esclusione `v8 ignore` dell'intera pagina. Il run con
  `VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx` misura
  statement `840/1185` (70,88%), branch `808/1417` (57,02%), funzioni
  `233/306` (76,14%), linee `742/979` (75,79%). Il gate 100% fallisce;
  restano 345 statement e 609 esiti branch scoperti. Non usare l'esclusione
  preesistente come prova di coverage del refactoring.
- Evidenze locali: `/tmp/gaia-presenze-giornaliere-tests-before.log`,
  `/tmp/gaia-presenze-giornaliere-coverage.log` e
  `/tmp/gaia-presenze-giornaliere-coverage/coverage-summary.json`.
- Esito `BLOCKED` dalla coverage full-file richiesta. La caratterizzazione
  residua richiede una fase separata prima della slice runtime; nessuna
  riduzione di complessita dichiarata. Prossima decisione: delimitare una
  tranche di caratterizzazione dei filtri e dei riepiloghi mensili, quindi
  proseguire con modali, salvataggi e polling, mantenendo il requisito 100%.

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


## 2026-10-05 — slice autorizzate del ciclo turnisti

Rimosse19regressioni del ciclo tramite slice mirate su maturazione buono,
export CCNL, audit condiviso GATE/GAIA, interpretazione override, registry modello
e controlli operativi UI. Nessuna baseline/scanner/soglia modificata.
Metriche prima/dopo, test e stato finale nel report
`domain-docs/presenze/docs/TURNISTI_COMPLEXITY_SLICES_2026-10-05.md`.
Ratchet mirato ciclo PASS; ratchet globale conserva finding Wiki concorrenti.
Gli interventi Wiki precedenti in questo documento sono preservati.

## 2026-10-05 — hotspot MCP runner sintetico

- Slice richiesta dall'utente: `experiment_runner.py::run_comparison`, il
  massimo cognitivo MCP corrente (21/9/34/4 cognitive/cyclomatic/LOC/nesting).
  Snapshot iniziale HEAD `6997dbab`; working tree concorrente preservato.
- Invarianti: schedule seeded, skip completed, conteggio retry per item,
  stesso contesto per i retry e UUID esperimento deterministico, append/fsync
  prima dell'aggiornamento in memoria, close e rilascio lock su abort.
  Nessuna modifica OAuth/HTTP/HTTPS, API, DB, budget o scoring.
- Baseline pre-change: 28 test experiment verdi, runner 139/139 statement e
  30/30 branch (100%). Slice: separare orchestration dell'esperimento da
  esecuzione resumable del singolo item, senza nuovi file runtime.
- Caratterizzazione: tre casi aggiuntivi verdi prima del refactoring (resume
  parziale e due abort); 31 test experiment verdi dopo. Prima prova coverage
  concorrente non valida: sorgente formattata durante il test e dati di un altro
  processo nel file coverage condiviso. Riverifica isolata con `COVERAGE_FILE`
  dedicato: runner 142/142 statement e 30/30 branch (100%).
- Dopo: `run_comparison` 4/4/11/2; `ComparisonExecutor.execute_item`
  7/6/19/2, quattro parametri incluso self, nessuna violation. Il manifest
  validato resta nel journal e determina l'UUID; non e ripassato come stato
  duplicato. Costruttore journal +1 LOC, cognitive/cyclomatic invariati.
- Aggregati file: cognitive sum/max 81/21 -> 71/18; cyclomatic sum/max
  63/10 -> 64/10, solo la base del nuovo callable (decisioni 48 -> 48);
  file LOC 210 -> 207; warning 5 -> 3, nessun error o warning trasferito.
  `IMPROVED` per cognitive/nesting, non per numero di decisioni.
- Ratchet mirato: PASS, `findings: []`, baseline del merge-base `6b61fd27`;
  scan dell'intero repository, filtro sul solo runtime dopo il matching.
  Evidenze `/tmp/gaia-runner-{before,after}.json`,
  `/tmp/gaia-runner-full-final.json`, `/tmp/gaia-runner-ratchet-scoped.json`.
  Ruff check e format check runtime/test verdi; `git diff --check` verde.
- Gate globali non verdi: ratchet 24 finding estranei al runner; lint-backend
  bloccato dal formatter di `presenze/services/{daily_details,shift_assignments}.py`.
  Nessun tentativo di correggere quei lavori concorrenti. Baseline, report
  versionati, esclusioni e soglie invariati; nessuna sincronizzazione globale
  della baseline e nessun commit/push di questa tranche.
- Documentazione dominio aggiornata su ownership e compatibilita manifest;
  dettagli di test, Graphify e debito residuo in
  `domain-docs/mcps/RUNNER_COMPLEXITY_REVIEW_2026-10-05.md`.

  Stop dopo questo singolo hotspot.

## 2026-10-05 — hotspot MCP validazione journal

- Richiesta successiva: eliminare i warning legacy del runner. Una sola slice:
  `ResultJournal.__init__` cognitive/cyclomatic/LOC/nesting 18/10/19/2.
  Snapshot HEAD `40851bbf`; le modifiche precedenti e concorrenti restano.
- Invarianti: flock non bloccante prima della lettura, verifica di tutte le
  newline prima del parsing JSON, manifest identico, nessuna scrittura su
  contenuto rifiutato, rilascio file/lock su errore, append/flush/fsync invariati.
  Separazione prevista: lifecycle nel costruttore, lettura/validazione in
  un metodo coeso, senza trasferire warning.
- Cinque caratterizzazioni aggiunte: file incompleto, precedenza incomplete
  su JSON invalido, JSON invalido completo, manifest diverso e prima scrittura
  fallita. Verificano byte preservati e lock realmente riacquisibile.
- Il warning dei sei parametri `run_comparison` riguarda una seconda slice;
  richiesta decisione esplicita sull'API Python interna, nessun wrapper
  artificiale o cambiamento CLI/HTTP per aggirare la metrica.
- Prima/dopo: 36 test experiment verdi, full-file 142 -> 145 statement e
  30 branch coperti al 100%. Suite MCP finale: 303 test verdi, 1996 statement
  e 420 branch al 100% sui 42 runtime MCP/router. Coverage file isolati.
- Costruttore 18/10/19/2 -> 5/4/13/2; `_read_rows` 8/7/9/1, sotto soglia.
  File cognitive sum/max 71/18 -> 66/8, cyclomatic sum/max 64/10 -> 65/7,
  decisioni 48 -> 48, LOC 207 -> 210, warning 3 -> 1, zero error. Esito
  `IMPROVED`, nessuna violation trasferita; un solo hotspot trattato.
- Ruff/check-format e diff-check PASS; ratchet target PASS dopo scan completo,
  baseline merge-base `6b61fd27`, `findings: []`. Evidenze
  `/tmp/gaia-journal-{before,after}.json`,
  `/tmp/gaia-journal-ratchet-scoped.json`, `/tmp/gaia-journal-mcp-suite.log`.
- Ratchet globale ancora 24 finding estranei; lint globale ancora due
  formatter Presenze. Baseline, report versionati, soglie ed esclusioni
  invariati, nessuna sincronizzazione globale o commit/push. Documentazione
  dominio e Graphify aggiornati con i target dedicati; dettagli nella review
  `domain-docs/mcps/RUNNER_COMPLEXITY_REVIEW_2026-10-05.md`.

## 2026-10-05 — API interna runner MCP autorizzata

- L'utente autorizza la modifica della firma Python per eliminare l'ultimo
  warning legacy. Una sola slice: `run_comparison`, parametri 6 -> 3 mediante
  l'oggetto `ComparisonExecutor` gia esistente, non un wrapper nuovo.
  Snapshot iniziale HEAD `753ef6dc`; working tree concorrente preservato.
- Invarianti: stessa configurazione per manifest/schedule/esecuzione,
  ownership del modello nel context manager CLI, ciclo di vita journal,
  retry/resume/scoring immutati; nessuna modifica a CLI o HTTP pubblici.
- Perimetro: runner, CLI interna e relativi test. Baseline e soglie invariate.
  Il vecchio contratto Python a sei argomenti viene sostituito esplicitamente,
  senza shim variadic o alias finalizzati ad aggirare le metriche.
- Baseline pre-change: 36 test, entrambi i runtime al 100%; nuovo caso cleanup
  CLI su errore del runner verde prima del cambio. Test di wiring aggiornato
  per verificare identita di corpus/config/modello e fonte nell'executor.
- Dopo: firma `run_comparison(cases, executor, output)`, tre parametri; zero
  warning/error in runner e CLI, nessuna esclusione o wrapper aggiunto.
  Cognitive/cyclomatic aggregate dei due runtime invariati (74/71), 19
  callable invariati. LOC runner 210 -> 211 e CLI 52 -> 59 per firma
  tipizzata/import esplicito. `IMPROVED` limitato a parametri e debito firma.
- 37 test experiment verdi; runner 144/144 statement e 30/30 branch, CLI
  37/37 statement e 4/4 branch (100%). Suite MCP completa: 304 test verdi,
  1996 statement e 420 branch al 100% sui 42 runtime MCP/router.
- Ruff/check-format/diff-check PASS; ratchet mirato sui due file PASS con
  `findings: []`, full scan contro baseline del merge-base `6b61fd27`.
  Evidenze `/tmp/gaia-api-{before,after}.json`,
  `/tmp/gaia-api-ratchet-scoped.json`, `/tmp/gaia-mcp-api-final-coverage.json`,
  `/tmp/gaia-api-mcp-suite.log`. Baseline e report versionati invariati.
- Restano estranei al perimetro 24 finding globali e due formatter Presenze;
  niente correzioni opportunistiche, sincronizzazione baseline o commit/push.
  Documentazione e Graphify aggiornati con target dedicati; AST Wiki forzato
  dopo la patch pruning idempotente per rimuovere le relazioni stale dovute
  allo spostamento della costruzione executor nella CLI. Stop dopo questa slice.
- Commit isolato successivamente richiesto dall'utente: include solo runner,
  CLI, test e documentazione di queste tre slice, non gli altri refactoring
  MCP o i lavori concorrenti. Le sezioni dei documenti condivisi sono staged
  selettivamente. Nessun push; i gate globali estranei restano dichiarati.
