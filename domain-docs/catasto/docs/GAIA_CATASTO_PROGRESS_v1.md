# GAIA — Modulo Catasto
## Progress Tracker v1

### 2026-10-06 — guardia hyperlink XLSX export

- Guardia unica di presenza None nella coppia indici colonna link/apri;
  indici positivi o None, nessun cambio workbook/formula/append/save/close.
- Renderer cognitive/cyclomatic23/11 ->18/9, LOC21/nesting4 invariati; file
  cognitive300 ->295, cyclomatic237 ->235, branching212 ->210. Violation
  20 ->19, warning ciclomatico eliminato senza helper o debt transfer.
- Cinque workbook persistenti verificano formule/link vuoti/colonne mancanti
  o invertite;281 test coverage/caratterizzazione/API/facade PASS, full-file
  exports100% statement223/branch68.393 workbook differenziali controbb907b16
  equivalenti per sheet/coordinate/valori/tipi formula, non byte ZIP timestamp.
  Ratchet/Ruff PASS; lint globale UP038 InCass concorrente, Graphify codice/docs
  aggiornati. Baseline/config/scope invariati, renderer e mapper ancora aperti.

### 2026-10-06 — coordinate particella export bulk

- Proiezione foglio/particella condivisa, fallback input esplicito soltanto
  nella modalita comune. Match presente esporta valori senza fallback None;
  ordine colonne/accessi, zero-stringa e spazi invariati, nessun cambio schema/API.
- Mapper cog/cyc/LOC99/46/62 ->79/38/60, helper5/6/10/0/2 sotto soglia;
  file cognitive315 ->300, cyclomatic239 ->237/callable24 ->25,
  branching215 ->212, LOC485 ->493.20 violation residue, nessun debt transfer.
- Sedici casi persistenti,276 test coverage/caratterizzazione/API/facade PASS;
  full-file exports100% statement223/branch68, zero esclusioni.4000 confronti
  controe6f9ec09 equivalenti per output/ordine/accessi. Ratchet/Ruff mirato PASS,
  lint globale UP038 InCass concorrente; Graphify codice/docs aggiornati.
  Baseline/config/scope invariati, mapper79/38 e campagna ancora aperti.

### 2026-10-06 — colonne utenza e stato export bulk

- Proiezione CCO/link/certificato/stati ruolo separata dalla composizione riga;
  helper8/9/15/0/2 sotto soglia. Guardie CCO, None/zero-stringa, URL calcolato
  prima dei campi, ordine colonne/accessi e doppie letture stati invariati.
- Mapper cog/cyc/LOC115/56/66 ->99/46/62; file cognitive323 ->315,
  cyclomatic240 ->239/callable23 ->24, branching217 ->215, LOC474 ->485.
  20 violation residue, nessun nuovo debito o trasferimento di violation.
- Sedici casi persistenti,260 test coverage/caratterizzazione/API/facade PASS,
  full-file exports100% statement221/branch68, zero esclusioni.4000 confronti
  contro69254dc8 equivalenti per output/ordine/accessi; ratchet/Ruff mirato PASS.
  Lint globale UP038 InCass concorrente, Graphify codice/docs aggiornati.
  Baseline/config/scope/API invariati, mapper99/46 e campagna ancora aperti.

### 2026-10-06 — colonne distretto export bulk

- Proiezione distretto/riordino/superficie separata dalla composizione riga;
  helper4/5/10/0/1 sotto soglia. None esportato vuoto, zero preservato,
  ordine colonne e doppia lettura guardia/valore invariati, nessun cambio API.
- Mapper cog/cyc/LOC122/60/74 ->115/56/66; file cognitive326 ->323,
  cyclomatic239 ->240/callable22 ->23, branching217 invariato, LOC472 ->474.
  20 violation residue, nessun nuovo debito o trasferimento di violation.
- 244 test coverage/caratterizzazione/API/facade PASS; full-file exports100%
  statement219/branch68, zero esclusioni.42 casi persistenti sui campi opzionali
  e4000 differenziali controb68bb1b0 equivalenti per output/ordine/accessi.
  Ratchet/Ruff mirato PASS, lint globale UP038 InCass concorrente; Graphify
  codice/docs aggiornati, baseline/config/scope invariati. Mapper ancora aperto.

### 2026-10-06 — identita owner export bulk

- Proiezione identita/rank distinta dai dettagli contatto; helper8/9/19/0/3
  sotto soglia. Precedenza denominazione/ragione sociale/nomi, data/None,
  zero-stringa, ordine colonne/accessi e rank invariati, nessun cambio API/schema.
- Mapper cog/cyc/LOC145/68/83 ->122/60/74; file cognitive341 ->326,
  cyclomatic238 ->239/callable21 ->22, branching217 invariato, LOC462 ->472.
  20 violation (8 error/12 warning), errore LOC diventa warning senza transfer.
- Dieci caratterizzazioni persistenti,244 test coverage/caratterizzazione/API/
  facade PASS, full-file exports100% statement217/branch68, zero esclusioni.
  4000 differenziali contro93764bf2 equivalenti per valori/ordine/accessi;
  SISTER invariato/sotto soglia. Ratchet/Ruff mirato PASS, lint globale UP038
  InCass concorrente; Graphify codice/docs aggiornati. Baseline/config/scope
  invariati, mapper122/60 e campagna ancora da completare.

### 2026-10-06 — dettagli contatto owner export bulk

- Proiezione contatti/stato owner e note contestuali separata da identita/rank;
  helper6/7/14/0/2 sotto soglia, ordine colonne/accessi e normalizzazione truthy
  invariati, campi identity/date non modificati. Nessun cambio API/schema.
- Mapper cog/cyc/LOC163/74/91 ->145/68/83; file cognitive353 ->341,
  cyclomatic237 ->238/callable20 ->21, branching217 invariato, LOC456 ->462.
  20 violation residue, nessuna nuova violation o trasferimento del debito.
- Nove caratterizzazioni persistenti;234 test coverage/caratterizzazione/API/
  facade PASS, full-file exports100% statement215/branch68, zero esclusioni.
  4000 differenziali contro0ecb6a15 equivalenti per output/ordine/accessi;
  servizio SISTER invariato/sotto soglia. Ratchet/Ruff mirato PASS, lint globale
  UP038 InCass concorrente; Graphify codice/docs aggiornati prima del commit.
  Baseline/config/scope invariati; mapper ancora da ridurre, campagna aperta.

### 2026-10-06 — servizio arricchimento export SISTER

- Query completed/ordinamento e lookup owner/history separati dalle route in
  services/bulk_export_sister.py; tre callable re-esportati con identita invariata.
  JSON dei due payload con ciclo comune e scritture sequenziali: stesso ordine,
  ensure_ascii/sort_keys e mutazioni parziali prima di un errore propagato.
- _attach_sister_data18/12/48/2 ->9/7/43/2, nuovo servizio zero violation.
  Cognitive aggregate381 ->378; branching238 invariato (cyclomatic261 ->263,
  callable23 ->25). LOC507 ->533, distribuite route456/servizio77; violation
  23 ->20, due warning SISTER e file LOC eliminati senza debt transfer.
- 225 test coverage/caratterizzazione/API/facade PASS; full-file100% exports
  statement213/branch68 e servizio statement38/branch12, zero esclusioni.
  Errori JSON al primo/secondo payload e re-export caratterizzati;1200 confronti
  controa0eba126 equivalenti per output/ordine/SQL/accessi. Ratchet/Ruff PASS,
  format nuovo servizio/test PASS; lint globale UP038 InCass concorrente.
  Graphify codice con pruning e docs aggiornati; baseline/config/scope/API
  invariati. Mapper bulk163/74 e altri hotspot rimangono, campagna non completa.

### 2026-10-06 — selezione owner latest export SISTER

- Guardia unica di scarto per estrazione diversa dall'ID selezionato non-None;
  ID accettato memorizzato, duplicati mantenuti. None conserva il comportamento
  storico; query, ordine owner/latest, lookup, JSON e payload invariati.
- _attach_sister_data cog/cyc/LOC/nesting21/13/49/3 ->18/12/48/2; file
  cognitive384 ->381, cyclomatic262 ->261, LOC508 ->507, nessun helper nuovo.
  23 violation residue, nessun debt transfer o cambio API/schema/baseline.
- Cinque scenari persistenti UUID/None;222 test coverage/caratterizzazione/API/
  facade PASS, full-file exports100% statement241/branch78, zero esclusioni.
  1200 casi differenziali controca64a522 equivalenti per output/ordine/SQL/accessi.
  Ratchet/Ruff mirato PASS, lint globale UP038 InCass concorrente; Graphify
  codice/docs aggiornati. SISTER18/12 e mapper bulk163/74 restano sopra soglia.

### 2026-10-06 — chiave riga export SISTER

- Mapping dichiarativo della chiave row con fallback truthy e str, casefold
  soltanto comune; distinto dal mapping particella ORM. Ordine lookup/get/
  mutazioni, selezione latest, query e JSON invariati, nessun cambio API/schema.
- _attach_sister_data cog/cyc/LOC33/21/54 ->21/13/49, helper5/6/5 sotto soglia.
  File cognitive391 ->384, cyclomatic264 ->262, LOC508 invariata;23 violation
  residue, due error diventano warning e warning LOC eliminato, nessun transfer.
- 1296 combinazioni persistenti piu missing/numerici;217 test coverage/
  caratterizzazione/API/facade PASS, full-file exports100% statement242/branch80,
  zero missing/esclusioni.1200 casi differenziali contro47bf097b equivalenti per
  output/ordine/SQL/accessi particella e get row. Ratchet/Ruff mirato PASS;
  lint globale UP038 InCass concorrente, Graphify codice/docs aggiornati.
  Baseline/config/scope invariati; SISTER e mapper bulk ancora sopra soglia.

### 2026-10-06 — chiave particella export SISTER

- Chiave particella condivisa per owner/history SISTER: casefold del comune,
  strip delle coordinate, None/vuoti e ordine accessi invariati. Query,
  selezione latest, serializzazione JSON e chiave row con str non modificati.
- _attach_sister_data cog/cyc/LOC57/37/64 ->33/21/54; helper5/6/5 sotto soglia.
  File cognitive410 ->391, cyclomatic274 ->264, LOC513 ->508, nessun nuovo
  debito;24 violation residue, mapper bulk163/74 invariato e ancora da ridurre.
- 625 combinazioni persistenti con ORM reale;216 test coverage/caratterizzazione/
  API/facade PASS, full-file exports100% statement240/branch80, zero esclusioni.
  1200 casi differenziali contro21b9dded equivalenti per output/ordine/SQL/accessi.
  Ratchet/Ruff mirato PASS; lint globale UP038 InCass concorrente. Graphify
  codice/docs aggiornati, nessun cambio API/schema/baseline/config/scope.

### 2026-10-06 — mapping intestatario export bulk

- Proiezione inline dei campi owner identita/contatti, normalizzazione truthy
  condivisa; default vuoti ordinati con dict.fromkeys e count numerico distinto.
  Nessun helper aggiunto, ordine colonne/accessi/rank/note invariati.
- Mapper cognitive/cyclomatic/LOC190/86/100 ->163/74/91; file cognitive
  437 ->410, cyclomatic286 ->274, LOC522 ->513.24 violation residue;
  candidato helper scartato per nuova violation e crescita LOC, non committato.
- 58 nuovi casi persistenti,215 test coverage/caratterizzazione/API/facade
  PASS, full-file exports100% statement238/branch80, zero missing/esclusioni.
  4000 casi differenziali controd87347cd equivalenti per valori/ordine/accessi.
  Ratchet/Ruff mirato PASS; lint globale UP038 InCass concorrente. Graphify
  codice/docs aggiornati, nessun cambio API/schema/baseline/config/scope.

### 2026-10-06 — campi opzionali export bulk

- Mapping dichiarativo dei sette campi distretto/riordino/superficie, None
  esportato come stringa vuota e zero preservato. Ordine colonne/accessi e
  contratti CSV/XLSX invariati, nessun helper o cambio API/schema/baseline.
- Mapper cognitive/cyclomatic218/103 ->190/86; file465/303 ->437/286,
  LOC522/callable21 invariati.24 violation residue: hotspot non completo.
- 42 nuovi casi persistenti;157 test coverage/caratterizzazione/API/facade
  PASS, full-file exports100% statement238/branch80, zero missing/esclusioni.
  4000 casi differenziali contro6f68f891 equivalenti per valori e ordine
  colonne/accessi. Ratchet/Ruff mirato PASS, lint globale UP038 InCass
  concorrente; Graphify codice e docs aggiornati prima del commit separato.

### 2026-10-06 — colonne comuni export bulk

- 115 test coverage/caratterizzazione/API/facade PASS; full-file exports100%
  statement238/238 e branch80/80, zero missing/partial/esclusioni.
- Deduplicato il suffisso comune delle colonne export; prefissi CF/PIVA e
  comune/sezione distinti, ordine CSV/XLSX e accessi attributo invariati.
  Nessun cambio API/schema/fallback input, semantica None/zero, URL o owners.
- Mapper cog/cyc/LOC/nesting281/135/114/3 ->218/103/100/3; cognitive file
  528 ->465, cyclomatic335 ->303, LOC533 ->522, nessun helper aggiunto.
  24 violation residue, hotspot ancora da ridurre; baseline/config invariati.
- 4000 casi differenziali contro37440327 equivalenti per valori, ordine
  colonne e accessi; due casi persistenti di regressione. Ratchet/Ruff mirato
  PASS, lint globale UP038 InCass concorrente; Graphify codice/docs aggiornati.

### 2026-10-06 — filtro righe vuote SISTER

- Filtro idiomatico delle righe normalizzate con filter(None, lines): ordine,
  contenuto della lista e alias raw_lines invariati, nessun helper aggiunto.
- Pubblico cognitive/cyclomatic10/10 ->9/9; file93/93 ->92/92, branching70 ->69,
  LOC270 invariata. Ultimo warning eliminato: parser interamente sotto soglia,
  nessun cambio funzionale/API/versione/config/baseline/scope o debt transfer.
- 83 test parser/persistenza/backfill PASS, full-file100% statement203/branch78;
  66717 casi differenziali equivalenti. Ratchet/Ruff mirato PASS; lint globale
  UP038 InCass concorrente. Graphify backend codice e docs Catasto/piattaforma
  aggiornati prima del commit; campagna non-MCP prosegue sugli altri hotspot.

### 2026-10-05 — scansione proprietari e sezioni SISTER

- Scan legacy owner/indici sezioni isolato, header intestato/intestati
  classificato una volta; INTESTAT uppercase distinto da header catastali.
  Ultimo marker raggiunto prima break, ordine/start e alias raw_lines invariati;
  structured owners sostituisce solo non-empty, history mantiene due scansioni.
- Parser testo cog/cyc/LOC/nesting33/22/40/2 ->10/10/18/2, helper sotto soglia;
  cognitive file102 ->93, branching73 ->70. Due error eliminati, resta warning
  ciclomatico10 pubblico; nessun debt transfer o cambio API/schema/parser-version/
  baseline/config/scope/precedenza sezioni/status.
- Sei caratterizzazioni prima/dopo, 83 test parser/persistenza/backfill PASS,
  full-file100% statement203/branch78; 12288 layout marker/terminatori con trace
  ordine/start equivalenti, 3600 legacy/3600 metadati/2000 testi/45229 sequenze
  identici. Ratchet/Ruff mirato PASS; lint globale UP038 InCass concorrente.
  Graphify backend codice e docs Catasto/piattaforma aggiornati prima del commit;
  campagna non-MCP resta attiva.

### 2026-10-05 — mapping proprietari legacy SISTER

- Mapper proprietario e continuazioni separati, diritto/quota condivisi;
  guardia pending duplicata eliminata. CF remainder search e continuazione
  full-line match/short-circuit, diritto search/match distinti preservati.
  Ordine aggiornamenti/append, chiavi opzionali e precedenza structured owners invariati.
- Parser testo cog/cyc/LOC/nesting48/28/61/3 ->33/22/40/2, helper sotto soglia;
  cognitive file114 ->102, branching76 ->73. Warning LOC eliminato, due error
  complessita residui; nessun debt transfer o cambio API/schema/versione parser/
  baseline/config/scope/scansione sezioni/status.
- Quattro caratterizzazioni prima/dopo, 77 test parser/persistenza/backfill PASS,
  full-file100% statement190/branch76; 3600 legacy, 3600 metadati, 2000 testi
  e 45229 sequenze/start differenziali identici. Ratchet/Ruff mirato PASS;
  lint globale UP038 InCass concorrente. Graphify backend codice e docs Catasto/
  piattaforma aggiornati prima del commit; campagna non-MCP ancora attiva.

### 2026-10-05 — metadati e riferimenti payload testo SISTER

- Payload iniziale isolato, gruppo regex opzionale/strip condiviso per data,
  comune e parcel. Priorita storica/attuale, primo match, casing codice/comune,
  campi None, raw_lines e contenitori fresh invariati; parser-version invariata.
- Parser testo cog/cyc/LOC/nesting58/38/87/3 ->48/28/61/3; payload2/3/28/0
  e gruppo2/3/5/1 sotto soglia. Cognitive file120 ->114, branching82 ->76;
  errore LOC diventa warning, due error residui. Nessun debt transfer o cambio
  API/schema/baseline/config/scope/scansione owner/sezioni/status.
- Quattro caratterizzazioni prima/dopo, 73 test parser/persistenza/backfill PASS,
  full-file100% statement186/branch78; 3600 metadati, 2000 testi e 45229
  sequenze/start differenziali identici. Ratchet/Ruff mirato PASS; lint globale
  UP038 InCass concorrente. Graphify backend codice e docs Catasto/piattaforma
  aggiornati prima del commit; campagna non-MCP ancora attiva.

### 2026-10-05 — transizioni owner ed evento storico SISTER

- Transizioni avvio evento/assegnazione owner isolate: owner pending consumato
  dopo creazione evento e prima append, owner corrente mutato solo con data
  valida; data invalida lascia nuovo owner pending, CF aggiorna ancora corrente.
  Alias, dict vuoti distinti, ordine risultati e parser-version invariati.
- Storico cog/cyc/LOC/nesting22/11/27/3 ->10/6/22/3, helper2/3/9/0 e4/4/9/1
  sotto soglia; cognitive file126 ->120, branching82 invariato. Due warning
  eliminati, tre error parser testo residui; nessun debt transfer o cambio
  API/schema/baseline/config/scope.
- Due caratterizzazioni identita owner prima/dopo, 69 test parser/persistenza/
  backfill PASS, full-file100% statement179/branch76 dopo; 45229 sequenze/start
  e 2000 payload testi differenziali identici. Ratchet/Ruff mirato PASS;
  lint globale UP038 InCass concorrente. Graphify backend codice e docs Catasto/
  piattaforma aggiornati prima del commit; campagna non-MCP ancora attiva.

### 2026-10-05 — raccolta riferimenti catastali correlati SISTER

- Aggiornamento stato related e append parcel isolati nella stessa scansione;
  reset precede il marker variati/soppressi, anche sulla stessa riga. Ordine
  riferimenti, duplicati, filtro / e *, parser-version e output invariati.
  Continuazioni owner current/pending appiattite senza cambiare effetti.
- Storico cog/cyc/LOC/nesting40/19/35/3 ->22/11/27/3, helper10/9/15/1 sotto
  soglia; cognitive file134 ->126, branching82 invariato. Due error diventano
  due warning, tre error parser testo residui; nessun debt transfer o cambio
  API/schema/baseline/config/scope.
- Quattro caratterizzazioni prima/dopo, 67 test parser/persistenza/backfill PASS,
  full-file100% statement173/branch76 dopo; 45229 sequenze/start e 2000 testi
  differenziali identici. Ratchet/Ruff mirato PASS; lint globale UP038 InCass
  concorrente. Graphify backend codice e docs Catasto/piattaforma aggiornati
  prima del commit; campagna non-MCP resta attiva.

### 2026-10-05 — aggiornamento dettagli eventi storici SISTER

- CF/diritto condivisi fra current owners e storico, dettagli atto isolati e
  rami pending owner identici fattorizzati. Ordine mutazioni, CF uppercase,
  prima act_date anche None, ultimo act, related duplicati/reset invariati.
- Storico cog/cyc/LOC/nesting59/27/49/4 ->40/19/35/3; current owners15/9/21/2
  ->11/7/15/2; cognitive file147 ->134, branching84 ->82. Due warning eliminati,
  cinque error residui nel parser, nessun debt transfer. Versione parser,
  API/schema, baseline/config/scope e parser testo58/38/87/3 invariati.
- Caratterizzazione full-file100% prima/dopo, 63 test parser/persistenza/backfill
  PASS; statement170/branch76 dopo, 45229 sequenze/start e 2000 payload testi
  differenziali identici. Ratchet/Ruff mirato PASS; lint globale UP038 InCass
  concorrente. Graphify codice backend e docs Catasto/piattaforma aggiornati
  prima del commit; campagna non-MCP ancora attiva.

### 2026-10-05 — stati del record estrazione SISTER

- Mapper metadati successful e registrazione failed separati dal coordinatore.
  Fallback costruito nel catch; identita existing, aggiornamenti parziali prima
  di observed_at invalida, cache, SHA fuori try e ordine add/flush invariati.
- Coordinatore cog/cyc/LOC/nesting18/13/26/2 ->12/9/16/2; mapper4/5/14/0
  e registrazione failed0/1/10/0 sotto soglia. Cognitive file59 ->57,
  branching48 invariato; zero violation nel file, nessun cambio API/schema/
  transazioni/baseline/config/scope o debito trasferito.
- 44 test prima/dopo, full-file100% statement91/branch18, 320 trace SQL/record/
  failure equivalenti. Ratchet/Ruff mirato PASS; lint globale UP038 InCass
  concorrente fuori slice. Graphify codice backend e docs Catasto/piattaforma
  aggiornati prima del commit; campagna globale non-MCP ancora attiva.

### 2026-10-05 — sostituzione record collegati SISTER

- Sostituzione figli isolata: delete parcel/history, add/flush parcel, owner
  poi eventi. Invocazione dopo flush extraction dentro try; cache, SHA fuori
  try, ordine SQL e catch con scritture parziali invariati, nessun commit/rollback.
- Coordinatore cog/cyc/LOC/nesting30/19/34/2 ->18/13/26/2, helper8/7/14/1;
  cognitive file63 ->59, branching48 invariato. Due error diventano due warning;
  nessun cambio API/schema o debito trasferito, baseline/config/scope invariati.
- 43 test prima/dopo, full-file100% statement86/branch18, 320 trace SQL/record/
  failure equivalenti. Ratchet/Ruff mirato PASS; lint globale UP038 InCass
  concorrente fuori slice. Graphify codice backend e docs Catasto/piattaforma
  aggiornati prima del commit; campagna non-MCP resta attiva.

### 2026-10-05 — matching particella canonica SISTER

- Normalizzazione riferimenti payload e filtro comune codice/nome condivisi.
  Codice conserva priorita anche quando ambiguo; nome solo in assenza di match
  codice. Unico candidato richiesto, campi canonici casefold senza strip;
  query is_current/foglio/particella e ordine accessi lazy invariati.
- `_resolve_particella` cog/cyc/LOC/nesting29/26/18/1 ->8/8/18/1;
  cognitive file78 ->63, cyclomatic67 ->57. Due error eliminati senza trasferire
  debito, due error residui nella persistenza; nessun cambio API/schema/transazioni.
- Otto caratterizzazioni nuove, 41 test persistenza/backfill PASS,
  full-file100% statement84/branch18; 2352 input differenziali con risultato,
  SQL/parametri e accessi lazy identici. Ratchet/Ruff mirato PASS; lint globale
  UP038 InCass concorrente fuori slice. Baseline/config/scope invariati,
  Graphify backend codice e docs Catasto/piattaforma aggiornati.

### 2026-10-05 — mapping persistenza visure SISTER

- Mapper parcel/owner/history e conversione date condivisa isolano costruzione
  dei record; coordinatore conserva cache SHA/version, query e ordine add/
  flush/delete, loop e catch. Canonici/CF, payload/stati e scritture parziali
  prima del catch invariati; nessun commit/rollback o cambio API/schema.
- `persist_sister_visura` cog/cyc/LOC/nesting73/40/71/2 ->30/19/34/2;
  cognitive file109 ->78, cyclomatic72 ->67, branching69 ->60. Mapper sotto
  soglia, warning LOC eliminato; restano quattro error target/resolver canonico.
  Nessun debito trasferito o nuova esclusione/baseline/config.
- 30 caratterizzazioni prima/dopo, 33 test persistenza/backfill PASS;
  full-file100% statement78/branch16, 320 trace SQL/side-effect/record/stati
  differenziali identici. Sessione recording con modelli reali, non un test
  PostgreSQL. Ratchet/Ruff mirato PASS; lint globale UP038 InCass concorrente
  fuori slice. Graphify backend codice e docs Catasto/piattaforma aggiornati.

### 2026-10-05 — registro spiegazioni anomalie

- Definizioni tipizzate riuniscono testi guida e strategie di calcolo; lookup
  Map senza chiavi prototype sostituisce il dispatch. Assemblaggio comune
  conserva ordine chiavi, liste nuove mutabili e input immutati; strategia
  imponibile riusata direttamente, senza wrapper o debito trasferito.
- `explainCatastoAnomalia` cog/cyc/LOC/nesting20/12/42/1 ->2/3/6/1;
  `IMPROVED`, cognitive file58 ->41, cyclomatic71 ->69, branching44 ->36,
  LOC374 invariato. Strategie tutte sotto soglia: zero warning/error nel file
  frontend anomalie, senza dichiarare concluso il programma di repository.
- Sette caratterizzazioni prima del runtime, 89 test prima/dopo;
  full-file100% statement/branch/function/line, 22275 input equivalenti per
  entrambi gli export e ordine invariato. Ratchet merge-base, typecheck ed
  ESLint PASS, baseline/config/scope invariati; Graphify codice force/pruning.

### 2026-10-05 — registro descrizioni anomalie

- Registro Map privato di descrizioni statiche/formatter completi per tipo
  sostituisce il dispatch condizionale; helper imponibile riusato senza wrapper.
  Testi, ordine, spazi, conversioni e fallback null/vuoto/prototype invariati.
- `describeCatastoAnomalia` cog/cyc/LOC/nesting22/13/41/1 ->4/5/6/1;
  `IMPROVED`, cognitive file75 ->58, cyclomatic73 ->71, branching51 ->44.
  Cinque formatter sotto soglia, nessun debito trasferito; LOC365 ->374 sotto
  soglia file. Eliminati due warning: restano solo due warning sulle spiegazioni.
- Dieci caratterizzazioni prima del runtime, 82 test prima/dopo, full-file100%
  statement/branch/function/line; 22275 input equivalenti per entrambi gli
  export, input e output completo/ordine invariati. Ratchet merge-base,
  typecheck ed ESLint PASS, baseline/config/scope invariati.

### 2026-10-05 — catalogo testi guida anomalie

- Testi VAL-01/07 separati dai calcoli in catalogo privato tipizzato nello
  stesso file. Assemblaggio conserva ordine chiavi e copie delle liste;
  fallback ignoti/prototype separato. Testi, calcoli, input e mutabilita
  dei risultati restano invariati, nessuna nuova esclusione.
- `explainCatastoAnomalia` cog/cyc/LOC/nesting24/14/152/1 ->20/12/42/1;
  `IMPROVED`, cognitive file77 ->75. Cyclomatic71 ->73 per due basi callable,
  branching51 invariato; LOC353 ->365 sotto soglia file. Eliminato error LOC:
  zero error e quattro warning residui, non zero debito o debito trasferito.
- Tre caratterizzazioni prima del runtime, 72 test prima/dopo; full-file100%
  statement/branch/function/line, 22275 input equivalenti per i due export
  inclusi nomi prototype. Ratchet merge-base/typecheck/ESLint PASS;
  baseline/config/scope invariati, modifiche concorrenti preservate.

### 2026-10-05 — spiegazione imponibile e calcoli sorgente condivisi

- Helper di dominio per spiegazione completa VAL-06; inserimento calcoli
  percentuale e riferimenti sorgente riusa truthiness/String. Ordine, testo,
  guardie, precisione/locale e flag catastale preservati; risultati/liste
  freschi e mutabili, input invariato, campo comune conserva non-null.
- `explainCatastoAnomalia` cog/cyc/LOC/nesting47/25/191/2 ->24/14/152/1;
  helper6/6/42/1 sotto soglia. `IMPROVED`, cognitive file94 ->77,
  cyclomatic76 ->71, nessun trasferimento. File ancora un error LOC e quattro
  warning: due error cognitivi/ciclomatici ridotti a warning, non eliminati.
- Otto caratterizzazioni prima del runtime, 69 test prima/dopo; full-file100%
  su quattro metriche, 5400 input equivalenti per i due export. Ratchet
  merge-base/typecheck/ESLint PASS, baseline/config invariati.

### 2026-10-05 — descrizioni misure e imponibile condivise

- Riferimenti formattati riusano il predicato e supportano il suffisso unita;
  paragrafo imponibile isolato per responsabilita di dominio. Valuta, locale,
  precisione, zero/null/invalidi, flag strict-true, testo e ordine preservati.
- `describeCatastoAnomalia` cog/cyc/LOC34/19/49 ->22/13/41, nesting1;
  helper imponibile2/3/11/0 sotto soglia. `IMPROVED`, cognitive file104 ->94,
  cyclomatic79 ->76, nessun trasferimento; due error target diventano warning.
  File ancora con tre error/due warning, non dichiarati eliminati.
- Dieci nuove caratterizzazioni prima del runtime, 61 test prima/dopo,
  full-file100% su quattro metriche e 5400 input identici per entrambi gli
  export. Ratchet merge-base/typecheck/ESLint PASS, baseline invariata.

### 2026-10-05 — descrizioni riferimenti sorgente condivise

- Predicate truthy/String/testo condivisi per codice fiscale, errore,
  foglio/particella/subalterno. Zero/false omessi, array/oggetti convertiti
  come prima, ordine e punteggiatura invariati; comune conserva non-null.
- `describeCatastoAnomalia` cog/cyc44/24 ->34/19, LOC49/nesting1 invariati;
  helper1/2/3/0 sotto soglia. `IMPROVED`, cognitive file113 ->104,
  cyclomatic82 ->79 senza trasferire debito; cinque error residui nel file.
- Nove caratterizzazioni prima del runtime, 51 test prima/dopo,
  full-file100% su quattro metriche, 3600 input equivalenti per entrambi
  gli export. Ratchet merge-base/typecheck/ESLint PASS, baseline invariata.

### 2026-10-05 — parametro formula inutilizzato rimosso

- Rimosso `multiplierDigits` dal helper privato frontend: non influiva sulla
  formula, indice sempre a quattro cifre e risultato a due. Entrambi i
  caller passano tre argomenti; testo, null/errori e formato restano invariati.
- Parametri5 ->4, warning params e warning ESLint eliminati; `IMPROVED`
  limitato ai parametri, cognitiva/ciclomatica invariate. Restano cinque
  violation error-level nei due export del file, nessun debito trasferito.
- 42 test prima/dopo, full-file100% statement/branch/function/line, 686 input
  differenziali identici; ratchet mirato, typecheck ed ESLint pulito PASS.
  Baseline/config invariati; test/docs precedenti preservati.

### 2026-10-05 — spiegazioni importi VAL-07 condivise

- Helper frontend di dominio per validazione voci e inserimento calcoli atteso/
  scostamento. Voci0648/0985, testo, formato, ordine, null/zero/invalidi e
  valori array-oggetto preservati; altri casi/esportazioni/UI invariati.
- `explainCatastoAnomalia` cog/cyc/LOC59/31/197 ->47/25/191, nesting2
  invariato; helper3/3/10/1 sotto soglia. `IMPROVED`, cognitive file122 ->113,
  cyclomatic85 ->82, nessun debito trasferito; sei violation residue invariati.
- Sette nuove caratterizzazioni sul runtime originale, 42 test prima/dopo;
  full-file100% statement/branch/function/line, 3600 input equivalenti per
  entrambi gli export. Ratchet mirato/typecheck PASS, ESLint exit0 con solo
  warning legacy. Baseline invariata; test/docs VAL-06 precedenti preservati.

### 2026-10-05 — caratterizzazione attesi/delta VAL-06

- Sei caratterizzazioni aggiunte per superfici/indice/importo mancanti,
  valori zero/negativi, ordine chiavi e conservazione del flag catastale
  preesistente quando non calcolabile. 18 test verdi, full-file100%
  (92 statement, 46 branch), nessuna esclusione; Ruff PASS. Lint globale
  bloccato dal formatter del file concorrente `domande_irrigue_parallel.py`,
  fuori perimetro e non modificato qui.
- Runtime invariato a `9b5357b8`: ciclo comune respinto dal ratchet per LOC
  31 ->33, pur riducendo cog/cyc29/22 ->28/20. Esito `NO_SAFE_CHANGE`,
  nessuna riduzione dichiarata o baseline aggiornata. API, calcoli,
  rounding, payload, dati originali e transazioni restano invariati.

### 2026-10-05 — classificazione causa superficie senza annidamento esterno

- Righe singole classificate direttamente; solo le righe multiple scelgono
  fra stessa domanda e piu domande. Senza righe, causa preesistente e tutti
  gli arricchimenti restano invariati. Deduplica/rounding/ordine preservati;
  nessuna modifica a VAL-06, API, query, schema o transazioni.
- `_enrich_domande_irrigue_surface_payload`: nesting3 ->2, LOC26 ->25;
  cognitive16/cyclomatic13 invariati. `IMPROVED` limitato a nesting/LOC,
  nessun helper o nuovo callable; quattro violation residue nel file.
- Quattro nuove caratterizzazioni prima del runtime, 12 test prima/dopo;
  coverage full-file100% (92 statement, 46 branch), zero esclusioni.
  2880 payload differenziali identici con ordine chiavi; ratchet mirato,
  Ruff e lint PASS. Baseline/config invariati, prossimo hotspot separato.

### 2026-10-05 — serializzazione payload anomalie VAL-06

- Unificata la serializzazione dei quattro campi numerici opzionali con
  mapping ordinato e controllo esplicito non-null. Zero, campi preesistenti,
  ordine chiavi, arrotondamenti, attesi/delta e errori preservati.
- `build_anomalia_payload`: cognitive 30 -> 29, cyclomatic 24 -> 22,
  LOC 31 invariate; nessun helper o debito trasferito. Flussi DIR invariati.
- Otto test verdi, coverage full-file 100% (94 statement, 48 branch),
  2500 casi differenziali identici, ratchet mirato/Ruff PASS.
- `IMPROVED`, quattro violation legacy residue; API, query, schema,
  transazioni e baseline non modificati.

---

## Stato generale

| Fase | Descrizione | Status | Note |
|---|---|---|---|
| **1** | Foundation: DB, import, API, frontend tabellare | 🟡 In corso (core pronto) | Backend+frontend Fase 1 implementati; restano ottimizzazioni/performance e alcune rifiniture UX |
| **2** | GIS Map UI: MapLibre + Martin | 🟢 Completato | Estensione GIS implementata su modulo `catasto` esistente |
| **3** | Sister integration per intestatari | 🔴 Non iniziato | Dipende da Fase 1 |
| **4** | Sentinel-2 NDVI + classificazione | 🔴 Non iniziato | Dipende da Fase 2 |
| **5** | Wizard anomalie completo + segnalazioni | 🔴 Non iniziato | Dipende da Fase 1, 4 |

Legend: 🔴 Non iniziato · 🟡 In corso · 🟢 Completato · ⚫ Bloccato

---

## Fase 1 — Foundation

### Infrastruttura e DB

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 1.1 | Alembic migration PostGIS + tutte le tabelle | 🟢 | `backend/alembic/versions/20260420_0051_catasto_phase1_postgis_and_tables.py` | Include estensioni PostGIS + tabelle `cat_*` + indici |
| 1.2 | Seed schemi contributo 0648 e 0985 | 🟢 | nella migration | Seed in `cat_schemi_contributo` |
| 1.3 | Aggiungere `geoalchemy2` a requirements.txt | 🟢 | `backend/requirements.txt` | |
| 1.4 | Aggiungere `codicefiscale` a requirements.txt | 🟢 | `backend/requirements.txt` | |

### Backend — Modelli

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Modello `CatParticella` | 🟢 | `backend/app/models/catasto_phase1.py` | ORM Fase 1 consolidato in `app/models/catasto_phase1.py` |
| 2.2 | Modello `CatDistretto` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.3 | Modello `CatImportBatch` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.4 | Modello `CatUtenzeIrrigua` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.5 | Modello `CatAnomalia` | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.6 | Modelli rimanenti (distretto_coeff, schemi, aliquote, intestatari) | 🟢 | `backend/app/models/catasto_phase1.py` | |
| 2.7 | Selezioni GIS salvate | 🟢 | `backend/app/models/catasto_phase1.py` + `backend/alembic/versions/20260429_0069_add_cat_gis_saved_selections.py` | Persistenza per utente di selezioni importate da Excel con colore e riferimenti particella |

### Backend — Services

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | `validate_codice_fiscale()` | 🟢 | `backend/app/modules/catasto/services/validation.py` | Include checksum CF 16 e PIVA 11; usa `codicefiscale` se installato |
| 3.2 | Comuni ISTAT CSV + `validate_comune()` | 🟢 | `backend/app/modules/catasto/data/comuni_istat.csv` + `backend/app/modules/catasto/services/validation.py` | |
| 3.3 | `validate_superficie()`, `validate_imponibile()`, `validate_importi()` | 🟢 | `backend/app/modules/catasto/services/validation.py` | |
| 3.4 | Unit test validazione | 🟡 | `backend/tests/test_catasto_phase1.py` | Test base presenti; suite specifica validazione dedicata ancora da separare se utile |
| 4.1 | `import_capacitas()` — mapping colonne + normalizzazioni | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.2 | `import_capacitas()` — pipeline validazione VAL-01..08 | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.3 | `import_capacitas()` — bulk insert + report_json | 🟡 | `backend/app/modules/catasto/services/import_capacitas.py` | Implementato ma non ottimizzato per 90k (manca COPY/bulk spinto) |
| 4.4 | `import_capacitas()` — idempotenza + force | 🟢 | `backend/app/modules/catasto/services/import_capacitas.py` | |
| 4.5 | `import_capacitas()` — upsert coefficienti e aliquote | 🟡 | `backend/app/modules/catasto/services/import_capacitas.py` | Da completare/allineare a execution plan (upsert automatici) |
| 5.1 | `finalize_shapefile_import()` — upsert SCD Type 2 | 🟢 | `backend/app/modules/catasto/services/import_shapefile.py` | SCD2 + history; update finale del batch differito a fine transazione per evitare lock tra finalize e progress logger su `cat_import_batches`; fast path DB vuoto ora materializza dedup, inserisce a chunk con step progressivi e alza il parallelismo SQL di sessione in modo aggressivo (`work_mem`, `temp_buffers`, `max_parallel_workers_per_gather`, costi planner, I/O concurrency) |
| 5.2 | `finalize_shapefile_import()` — deriva distretti via ST_Union | 🟢 | `backend/app/modules/catasto/services/import_shapefile.py` | Upsert `cat_distretti` |
| 5.3 | Script bash `import_shapefile_catasto.sh` | 🟢 | `scripts/import_shapefile_catasto.sh` | `ogr2ogr` → staging + finalize API; default CRS sorgente `EPSG:7791` per RDN2008 / UTM zone 32N; backend upload ZIP usa `ogr2ogr` con `PG_USE_COPY=YES` e droppa `cat_particelle_staging` a fine finalize/errore |

### Backend — Routes

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 6.1 | Routes distretti (lista, dettaglio, kpi, geojson) | 🟢 | `backend/app/modules/catasto/routes/distretti.py` | GeoJSON senza hard-deps `geoalchemy2` |
| 6.2 | Routes particelle (lista, dettaglio, utenze, anomalie, geojson) | 🟢 | `backend/app/modules/catasto/routes/particelle.py` | `utenze` e `anomalie` per particella incluse |
| 6.3 | Routes import (upload, finalize, status, report, history) | 🟢 | `backend/app/modules/catasto/routes/import_routes.py` | Include finalize shapefile |
| 6.4 | Routes anomalie (lista, patch, summary, wizard CF/comune/particella) | 🟢 | `backend/app/modules/catasto/routes/anomalie.py` | Include `PATCH /catasto/anomalie/{id}`, `GET /catasto/anomalie/summary`, `GET /catasto/anomalie/wizard/cf/items`, `POST /catasto/anomalie/wizard/cf/apply`, `GET /catasto/anomalie/wizard/comune/items`, `POST /catasto/anomalie/wizard/comune/apply`, `GET /catasto/anomalie/wizard/particella/items`, `POST /catasto/anomalie/wizard/particella/apply` |
| 6.5 | Dashboard aggregata | 🟢 | `backend/app/modules/catasto/routes/dashboard.py` | `GET /catasto/dashboard/summary` espone stato import, copertura particelle, utenze, anomalie e KPI distretti in una sola chiamata; dal 2026-07-13 espone anche `importo_totale_0668` e `importo_ruolo_totale` per distinguere il totale Capacitas `0648+0985` dal totale ruolo completo `0648+0668+0985` |
| 6.6 | Registrazione router in main/catasto module | 🟢 | `backend/app/modules/catasto/routes/__init__.py` + `backend/app/modules/catasto/router.py` | Router incluso in API |
| 6.7 | Visure storiche AdE particelle ruolo non collegate | 🟢 | `backend/app/modules/catasto/services/ade_status_scan.py` + `ade_historical_visura_parser.py` + `routes/anomalie.py` + `modules/elaborazioni/worker` | `GET /catasto/anomalie/ade-scan/summary`, `GET /catasto/anomalie/ade-scan/candidates`, `POST /catasto/anomalie/ade-scan/run`; crea batch SISTER con `purpose=ade_status_scan`, scarica visura storica sintetica, salva PDF e payload in `ruolo_particelle.ade_scan_*` |

### Frontend

| # | Task | Status | File | Note |
|---|---|---|---|---|
| F1.1 | Tipi TypeScript `catasto.ts` | 🟢 | `frontend/src/types/catasto.ts` | |
| F1.2 | Client API `catastoApi` | 🟢 | `frontend/src/lib/api/catasto.ts` | Include `PATCH` anomalie + endpoints particella |
| F2.1 | Componente `AnomaliaStatusBadge` | 🟢 | `frontend/src/components/catasto/AnomaliaStatusBadge.tsx` | |
| F2.2 | Componente `CfBadge` | 🟢 | `frontend/src/components/catasto/CfBadge.tsx` | |
| F2.3 | Componente `KpiCard` | 🟢 | `frontend/src/components/catasto/KpiCard.tsx` | |
| F2.4 | Componente `ImportStatusBadge` | 🟢 | `frontend/src/components/catasto/ImportStatusBadge.tsx` | |
| F3 | Dashboard `/catasto` | 🟢 | `frontend/src/app/catasto/page.tsx` | Cruscotto operativo basato su `/catasto/dashboard/summary`: stato import, KPI precisi, copertura dati, qualità/anomalie e priorità distretti senza chiamate N+1; i tributi fissi `0648+0985`, il tributo irriguo `0668` e le superfici irrigabili sono mostrati in card separate |
| F4 | Wizard Import `/catasto/import` (3 step) | 🟢 | `frontend/src/app/catasto/import/page.tsx` | |
| F5 | Lista Distretti `/catasto/distretti` | 🟢 | `frontend/src/app/catasto/distretti/page.tsx` | |
| F6 | Dettaglio Distretto `/catasto/distretti/[id]` | 🟢 | `frontend/src/app/catasto/distretti/[id]/page.tsx` | Tab anomalie distretto collegata |
| F7 | Scheda Particella `/catasto/particelle/[id]` | 🟢 | `frontend/src/app/catasto/particelle/[id]/page.tsx` | Sezioni utenze+anomalie collegate |
| F8 | Console Anomalie `/catasto/anomalie` | 🟢 | `frontend/src/app/catasto/anomalie/page.tsx` | Summary per famiglia, sezione `Code di lavoro`, triage tabellare, wizard attivi per `VAL-02/03`, `VAL-04` e `VAL-05`, e pannello `Scansione AdE particelle non collegate` per avviare/monitorare batch SISTER dedicati |
| F9 | Layout + navigazione catasto | 🟢 | `frontend/src/app/catasto/layout.tsx` + sidebar | |
| F10 | Elaborazioni massive `/catasto/elaborazioni-massive` | 🟢 | `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx` + `modules/elaborazioni/worker/worker.py` | Job persistiti su backend con polling stato/progresso; il worker esegue la massiva, il backend parsea i file caricati e l'export CSV/XLSX viene scaricato da endpoint dedicato, mantenendo il dettaglio completo dei `MULTIPLE_MATCHES` |

---

## Fase 2 — GIS Map UI

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | Container Martin in docker-compose | 🟢 | `docker-compose.yml` | Servizio interno, non esposto su porta host |
| 2.2 | Config Martin | 🟢 | `config/martin.toml` | Config YAML compatibile con Martin v1.7, montata come `/config.toml` |
| 2.3 | Proxy nginx `/tiles/` | 🟢 | `nginx/nginx.conf` | `/tiles/catalog` e tile distretti verificati via nginx |
| 2.4 | View particelle correnti per Martin | 🟢 | `backend/alembic/versions/20260427_0066_catasto_gis_view.py` | `cat_particelle_current` con `geometry` e `ha_anomalie` |
| 2.5 | Endpoint GIS backend | 🟢 | `backend/app/modules/catasto/routes/gis.py` + `services/gis_service.py` + `services/gis_export_service.py` | Select spaziale, export CSV/XLSX/GeoJSON, popup particella, resolve riferimenti Excel e CRUD selezioni salvate |
| 2.6 | Dipendenze MapLibre/Draw | 🟢 | `frontend/package.json` | `maplibre-gl` già presente; aggiunto `maplibre-gl-draw` |
| 2.7 | Pagina GIS `/catasto/gis` | 🟢 | `frontend/src/app/catasto/gis/page.tsx` | Console GIS a mappa piena con toolbar flottante, sidebar destra persistente, import Excel con riepilogo, colore layer, salvataggio/caricamento selezioni e pannelli analisi/selezione; export `CSV`/`XLSX` con campi reimportabili GIS (`comune`, `sezione`, `foglio`, `particella`, `sub`, codici catastali e geometrie) e microcopy distinta rispetto al `GeoJSON` per uso cartografico diretto |
| 2.8 | Layer distretti e particelle MVT | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` | Distretti zoom 7+, particelle correnti zoom 13+ |
| 2.8.1 | Confini distretti dissolti | 🟢 | `backend/alembic/versions/20260511_0073_catasto_distretti_boundaries_view.py` + `config/martin.toml` | Vista MVT `cat_distretti_boundaries` disponibile; in UI l'outline resta nascosto quando il fill distretti e attivo, cosi il layer principale non mostra il reticolo particellare |
| 2.8.2 | Pannello distretti GIS | 🟢 | `frontend/src/app/catasto/gis/page.tsx` | Accordion sidebar con elenco distretti, palette colore coerente con la mappa, selezione/centratura e toggle particelle del distretto |
| 2.8.3 | Sfondo mappa selezionabile | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` + `frontend/src/app/catasto/gis/page.tsx` | Selettore sidebar per `Mappa` OSM, `Satellite` imagery raster e `Google Earth` via Google Map Tiles API con `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` |
| 2.9 | Scheda particella GIS con ruolo aggregato | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` + `frontend/src/app/catasto/gis/page.tsx` + `backend/app/modules/catasto/services/gis_service.py` | Click mappa -> fetch `/catasto/gis/particella/{id}/popup`, card React con dati base, anomalie, aggregazione ruolo via chiave catastale `catasto_parcels`, fallback anno corrente/precedente, importi per particella e apertura `ParticellaDetailDialog` |
| 2.10 | Overlay import Excel persistente | 🟢 | `frontend/src/components/catasto/gis/MapContainer.tsx` + `frontend/src/lib/api/catasto.ts` | GeoJSON caricato sulla mappa quando la source è pronta; colore configurabile da pannello; **opacità layer** (`opacity` su overlay, slider in `frontend/src/app/catasto/gis/page.tsx`) moltiplica l’opacità interpolata sullo zoom nei paint fill/circle (`__overlayOpacity` nelle proprietà feature) |
| 2.11 | Staging WFS Agenzia Entrate | 🟢 | `backend/app/modules/catasto/services/ade_wfs.py` + `routes/gis.py` + migration `20260513_0076` | `POST /catasto/gis/ade-wfs/sync-bbox` scarica `CP:CadastralParcel` per bbox, crea `cat_ade_sync_runs`, gestisce ordine assi `EPSG:6706`, riproietta a `EPSG:4326` e salva in `cat_ade_particelle` senza toccare `cat_particelle` |
| 2.12 | Alert dashboard allineamento AdE | 🟢 | `backend/app/modules/catasto/routes/dashboard.py` + `frontend/src/app/catasto/page.tsx` | Il summary dashboard espone `ade_alignment`; se lo staging AdE contiene particelle nuove o geometrie variate rispetto a GAIA, la dashboard mostra banner e popup con rimando al GIS |
| 2.13 | Report differenze run AdE | 🟢 | `backend/app/modules/catasto/services/ade_wfs.py` + `routes/gis.py` | `GET /catasto/gis/ade-wfs/alignment-report/{run_id}` classifica differenze per run: nuove AdE, geometrie variate, match ambigui, mancanti AdE nello scope bbox e allineate |
| 2.14 | Wizard GIS allineamento AdE | 🟢 | `frontend/src/app/catasto/gis/page.tsx` + `frontend/src/lib/api/catasto.ts` | Pannello sidebar `Allinea particelle AdE`: bbox manuale, da area disegnata o distretto selezionato; avvia sync WFS, usa `run_id` e mostra il report differenze senza apply automatico |
| 2.15 | Preview geometrica AdE/GAIA | 🟢 | `backend/app/modules/catasto/services/ade_wfs.py` + `frontend/src/components/catasto/gis/MapContainer.tsx` | Il report include GeoJSON preview delle differenze; il wizard lo carica come overlay colorato in mappa per nuove AdE, geometrie variate, geometrie GAIA correnti e mancanti AdE |
| 2.16 | Dry-run apply allineamento AdE | 🟢 | `backend/app/modules/catasto/services/ade_wfs.py` + `routes/gis.py` + `frontend/src/app/catasto/gis/page.tsx` | `POST /catasto/gis/ade-wfs/alignment-apply-preview/{run_id}` stima inserimenti, update geometria, soppressioni e impatti sui riferimenti collegati senza modificare `cat_particelle`; il wizard mostra la preview e i match ambigui sono esclusi |
| 2.17 | Apply backend allineamento AdE | 🟢 | `backend/app/modules/catasto/services/ade_wfs.py` + `routes/gis.py` | `POST /catasto/gis/ade-wfs/alignment-apply/{run_id}` richiede `confirm=true`, inserisce nuove AdE risolvibili su comune, aggiorna geometrie in-place con history e consente soppressione mancanti solo con flag esplicito |
| 2.18 | Apply guidato GIS AdE | 🟢 | `frontend/src/app/catasto/gis/page.tsx` + `frontend/src/lib/api/catasto.ts` | Il wizard consente apply non soppressivo solo dopo dry-run, senza match ambigui e con conferma testuale `APPLICA <run>`; dopo l'apply aggiorna report e overlay |
| 2.19 | Batch/worker per `Allinea comprensorio AdE` | 🟡 | `backend/app/modules/catasto/services/ade_wfs.py` + `routes/gis.py` + `frontend/src/app/elaborazioni/ade-alignment/page.tsx` + `frontend/src/components/elaborazioni/ade-alignment-workspace.tsx` | Prima tranche implementata: run asincrono persistito, polling stato e workspace operativo spostato in `elaborazioni`; `catasto/gis` resta superficie di stato/report. Progress runtime migliorato con fase, messaggio, `tiles_completed` e contatori live. Resta da valutare evoluzione verso worker dedicato con resume più robusto |
| 2.20 | Preview GIS distretto nel workspace | 🟢 | `frontend/src/components/catasto/distretti/distretto-gis-preview.tsx` + `frontend/src/components/catasto/distretti/distretto-preview-content.tsx` + `frontend/src/components/catasto/gis/MapContainer.tsx` + `backend/app/modules/catasto/routes/distretti.py` | Modal distretto con vista GIS read-only: perimetro + particelle da `GET /catasto/distretti/{id}/geojson` (`particelle_preview_geometry` semplificata e `particelle_bounds_geometry` per il fit). La stessa preview ora viene aperta anche dai link ai distretti dentro `CatastoWorkspaceModal` su `/catasto`, senza cambiare il comportamento della pagina dedicata `/catasto/distretti`. Fix 2026-07-14: opacità overlay riscritte come `interpolate` top-level tramite `buildOverlayFillOpacity`/`buildOverlayCentroidOpacity` in `map-filters.ts` (il pattern `["*", opacity, ["interpolate", ..., ["zoom"], ...]]` è rifiutato da MapLibre e `addLayer` falliva in silenzio lasciando le particelle senza riempimento, incluso `dui-2026-fill`); il `min-h-[560px]` di default di `MapContainer` non viene più applicato se il chiamante passa un proprio `min-h-*`, perché il conflitto CSS produceva un canvas 560px clippato nel contenitore 430px tagliando le particelle a sud |

---

## Fase 3 — Sister Integration

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | Endpoint batch visure per anomalie CF | 🔴 | | |
| 3.2 | Aggiornamento `cat_intestatari` da risultati Sister | 🔴 | | |
| 3.3 | UI: pulsante "Verifica Sister" in scheda particella | 🔴 | | |
| 3.4 | Visura storica sintetica AdE per anomalie ruolo | 🟢 | `modules/elaborazioni/worker/visura_flow.py` + `browser_session.py` + parser PDF | Per richieste `purpose=ade_status_scan`, il worker usa `request_type=STORICA`, scarica PDF sintetico, crea `catasto_documents` e parsa soppressioni/origini/variazioni |

---

## Fase 4 — Sentinel-2

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 4.1 | Account Copernicus Data Space | 🔴 | — | Azione manuale |
| 4.2 | `pip install openeo` + env variables | 🔴 | | |
| 4.3 | `sentinel_service.py` — auth + query | 🔴 | | |
| 4.4 | Job NDVI per distretto | 🔴 | | |
| 4.5 | Classificazione `irrigata_probabile` | 🔴 | | |
| 4.6 | Rilevamento presunti non paganti | 🔴 | | |
| 4.7 | Overlay NDVI su mappa | 🔴 | | |

---

## Fase 5 — Wizard + Segnalazioni

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 5.1 | Wizard anomalie 6 step completo | 🔴 | | |
| 5.2 | Integrazione segnalazioni con `operazioni` | 🔴 | | |

---

## Domande aperte

| ID | Domanda | Status | Risposta |
|---|---|---|---|
| OQ-01 | CCO corrisponde al wc_id White Company? | ✅ Risolto | No. Link tramite `codice_fiscale` / P.IVA |
| OQ-02 | Codici schema fissi? | ✅ Risolto | Sì: 0648 = contributo irriguo (aliquota fissa); 0985 = Quote Ordinarie (aliquota variabile da contatori, dato autoritativo Capacitas) |
| OQ-03 | EPSG shapefile? | ✅ Risolto | Default operativo aggiornato a EPSG:7791 RDN2008 / UTM zone 32N. `EPSG:3003` resta selezionabile solo per sorgenti Monte Mario / Gauss-Boaga. |
| OQ-04 | PARTIC alfanumerico? | ✅ Risolto | Sì (STRADA058 ecc.). Schema già corretto con `VARCHAR(20)` |
| OQ-05 | Anni precedenti disponibili? | ✅ Risolto | Solo 2025. Import storico non necessario in Fase 1 |

---

## Note tecniche

- PostGIS da abilitare prima di eseguire la migration Fase 1
- Lo shapefile deve essere copiato in un path accessibile dal server GAIA prima dello script `import_shapefile_catasto.sh`
- Martin si avvia automaticamente con `docker compose up` dopo aggiunta al compose
- Workspace `Elaborazioni > Moduli Capacitas`: la UI e organizzata in sezioni operative (`sync progressiva particelle`, `storico anagrafico`, `Avvisi pagamenti`, `Terreni batch`) e non espone piu la ricerca anagrafica puntuale, perche i dati Capacitas vengono sincronizzati su GAIA.
- `Avvisi pagamenti`: il backend registra un autosync inCASS attivo di default ogni 15 minuti. Accoda soggetti ruolo non sincronizzati o stale, lavora in chunk, non duplica il lavoro se un job inCASS e gia attivo e salta il ciclo se non esiste una credenziale Capacitas attiva. Il monitor espone soggetti, avvisi sincronizzati, pagati/parziali/non pagati, cambi stato e nuovi pagati.
- PDF avvisi inCASS: durante il sync vengono scaricati i PDF indicati nel dettaglio avviso, salvati come `ana_documents`, caricati nel NAS del soggetto in `capacitas/avvisi` e collegati a `ana_payment_notices.pdf_links_json` con `download_url` interno GAIA. I PDF gia archiviati non vengono riscaricati nei cicli successivi.
- Workspace `Elaborazioni > Capacitas > Terreni`: resta solo il flusso massivo da file; la preview del file e collassata di default e mostra un campione limitato, mentre il job usa comunque tutte le righe importate; i job espongono `double_speed`, `parallel_workers` e `throttle_ms`; il backend usa i parametri sia nel job batch sia nel rerun, con parallelo fino a 2 sessioni Capacitas e pausa applicata tra righe/item Terreni
- `Terreni batch`: la risoluzione delle frazioni Capacitas per i file che passano `comune + sezione + foglio + particella` usa ora un mapping esplicito `comune + sezione catastale -> frazione Capacitas` per i casi validati (`Oristano`, `Cabras`, `Simaxis`) e mantiene la precedente euristica per comune/frazione come fallback
- `Terreni batch` e fallback live elaborazioni massive: per i terreni storicamente scambiati `Terralba / sezione B`, la lookup Capacitas usa `Arborea` come comune di ricerca e `31 ARBOREA` come frazione prioritaria, perche in Capacitas molti record risultano ancora censiti sul comune storico
- `Elaborazioni massive > Particelle -> Intestatari`: con `include_capacitas_live` attivo, se una particella esiste in GAIA ma non ha ancora snapshot consortili locali, il backend puo lanciare una sync Terreni live mirata su `comune + sezione + foglio + particella`, persistendo `cat_capacitas_terreni_rows`, `cat_consorzio_units`, `cat_consorzio_occupancies`, certificato e intestatari prima di produrre il risultato/export
- `Elaborazioni massive > Particelle -> Intestatari`: se il match locale ha gia un `CCO` ma mancano ancora le fonti locali per costruire `link_involture` (`cat_capacitas_certificati`, `cat_consorzio_occupancies`, `cat_capacitas_terreni_rows`), il resolver live forza anche il backfill del certificato Capacitas e dei suoi intestatari, cosi il link e gli intestatari possono comparire gia nello stesso export
- Job Capacitas monitorabili da frontend (`Terreni` e `sync progressiva particelle`): avvio runtime con `asyncio.create_task(...)` tracciato lato backend, stato persistito su DB e recovery automatico degli orfani/stale job; la scadenza della sessione GAIA interrompe il polling UI ma non deve essere confusa con l'arresto del job backend
- `sync progressiva particelle`: al bootstrap backend i job compatibili in stato `pending/processing` vengono riconciliati in `queued_resume` e rilanciati automaticamente; il resume e guidato dal dominio (`capacitas_last_sync_at/status`) e non dal vecchio thread runtime interrotto
- `AutoSync particelle consortili`: lo scheduler di piattaforma accoda una sola tranche Particelle alla volta, con batch iniziale di 100, pipeline completa Terreni/certificati/dettagli, credenziale fissa e freschezza a 30 giorni. Le particelle mai sincronizzate hanno priorita; sessione/rete vengono ritentate dopo 1 ora, le failure generiche dopo 24 ore, mentre non trovate/nessuna frazione dopo 30 giorni. Record non correnti, soppressi, senza comune/foglio o in anomalia restano sospesi. Il ciclo sequenziale condivide l'elaborazione per-item col percorso parallelo. Verifica: `262` test e coverage runtime `1074/1074` (`100%`). Il default versionato e disabilitato; l'attivazione locale richiede una credenziale attiva e una verifica preventiva della coda inCASS che usa la stessa risorsa Capacitas.
- `AutoSync domande irrigue`: il `platform-scheduler` singleton accoda chunk
  notturni di CF/PIVA estratti dalle utenze locali e conserva cursore e job in
  attesa in `capacitas_domande_irrigue_autosync_state`. Il worker Capacitas
  preleva questi job dopo quelli manuali; il cursore avanza solo per
  `succeeded` o `completed_with_errors`, mentre una failure ripete il chunk.
  L'anno della domanda e esclusivamente `Anno` Capacitas: valori assenti, non
  numerici o fuori `1900..2100` sono scartati e registrati nel risultato. Il
  default e disabilitato e richiede una credenziale fissa. Verifica locale:
  suite Capacitas `224` test, suite worker `510` test, coverage backend
  `1420/1420` e worker `892/892`, entrambi `100%`; migration head
  `20260905_0900`.
- `Terreni` batch: supporta `auto_resume` esplicito per i job che devono essere ripianificati automaticamente dopo restart backend; i batch manuali senza flag restano recuperabili solo via monitor/rerun esplicito
- `Storico anagrafica Capacitas`: ora usa un modello job persistente dedicato con monitor frontend, progress report incrementale, cleanup stale e auto-resume dopo restart backend
- `Catasto > Particelle`: la sync singola Capacitas è disponibile direttamente nella dialog/lista particelle e nella scheda dettaglio, con label di ultimo aggiornamento (`capacitas_last_sync_at/status/error`) e route dedicata `POST /catasto/particelle/{id}/capacitas-sync`
- `Catasto > Particelle/GIS`: le particelle collegate dal Ruolo con reason `swapped_arborea_terralba` espongono `swapped_capacitas` nel dettaglio particella e nel popup GIS, mostrando comune reale GAIA e comune sorgente Capacitas/Ruolo.
- `Catasto > GIS`: l'import Excel delle particelle usa `POST /catasto/gis/resolve-refs` per generare il layer GeoJSON temporaneo; le selezioni possono essere salvate lato backend con nome/colore, riaperte dalle sessioni successive e rigenerate dalle geometrie correnti delle particelle.
- MapLibre: `["zoom"]` è valido solo come input di un `interpolate`/`step` di primo livello nelle paint property; un'espressione annidata tipo `["*", opacity, ["interpolate", ..., ["zoom"], ...]]` fa fallire `addLayer` in silenzio (l'errore arriva solo come evento `error` della mappa). Per le opacità overlay usare `buildOverlayFillOpacity`/`buildOverlayCentroidOpacity` in `frontend/src/components/catasto/gis/map-filters.ts`, che pre-moltiplicano gli stop; il test `catasto-gis-map-filters.test.ts` valida le espressioni contro `@maplibre/maplibre-gl-style-spec`
- `MapContainer` applica `min-h-[560px]` di default solo se il `className` del chiamante non contiene già un `min-h-*`: due utility `min-h-*` in conflitto vengono risolte dall'ordine arbitrario nel CSS compilato, non dall'ordine nell'attributo class
- `codicefiscale` Python su PyPI: https://pypi.org/project/codicefiscale/
- Copernicus Data Space gratuito per enti EU: https://dataspace.copernicus.eu
