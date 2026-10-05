# Hotspot backlog

Questo elenco non e una coda automatica di refactoring. Il quality ratchet opera
prima sul codice realmente toccato dagli sviluppi; un hotspot di questa lista si
apre solo quando ostacola feature, test o manutenzione e dopo una decisione
esplicita. Una iterazione neutra non autorizza il candidato successivo.

Questo elenco e un seed derivato da una ricognizione del repository. Non e la
baseline autorevole. Hermes deve sostituire dimensioni e priorita con i risultati
del motore AST e con la frequenza di modifica Git.

Snapshot di preparazione: `main` a
`79794c89e42e381a01d5dbbab36fa3a7abbde98d`, 2026-08-17.

## Candidati iniziali

Campagna non-MCP, SISTER matching particella canonica, 2026-10-05:
`_resolve_particella` `IMPROVED`, cog/cyc/LOC/nesting29/26/18/1 ->8/8/18/1.
Normalizzazione payload/filtro candidati condivisi, codice prioritario anche
ambiguo, fallback nome solo senza codice matched; helper sotto soglia.
File cognitive78 ->63, cyclomatic67 ->57, branching60 ->48, LOC134 ->144;
due error resolver eliminati, due error persistenza residui, nessun trasferimento.
41 test/full-file100%, 2352 input/trace accessi lazy equivalenti; ratchet/Ruff
mirato PASS, lint globale UP038 InCass concorrente. Baseline/config/scope
invariati, campagna non-MCP attiva; prossimo candidato persistenza SISTER.

Campagna non-MCP, SISTER mapping persistenza visura, 2026-10-05:
`persist_sister_visura` `IMPROVED`, cog/cyc/LOC/nesting73/40/71/2 ->30/19/34/2.
Mapper completi/date comune sotto soglia; coordinatore conserva SQL/ordine,
cache e catch con scritture parziali, nessun cambiamento transazionale.
File cognitive109 ->78, cyclomatic72 ->67, branching69 ->60, LOC112 ->134;
cinque violation ->quattro error residui su target/resolver, warning LOC
eliminato, nessuna violation trasferita. 33 test/full-file100%, 320 trace
equivalenti; ratchet/Ruff mirato PASS, lint globale UP038 InCass concorrente.
Baseline/config/scope invariati, campagna non-MCP resta attiva.

Campagna non-MCP, frontend presentazione NavItem, 2026-10-05:
`NavItem` `IMPROVED`, cog/cyc/LOC/nesting18/13/75/2 ->8/7/39/1;
presentazione stateless5/6/38/1 sotto soglia, factoring path/hash elimina
predicato duplicato. Sola estrazione neutra non conteggiata; file cognitive38
->33, cyclomatic41 invariato, branching29 ->28, LOC128 ->134, nessun debito
trasferito. Tre warning ->zero violation nel file. 44 test/full-file100%,
10080 rendering DOM e 2048 click equivalenti; ratchet/ESLint/typecheck PASS,
baseline/config/scope invariati. Campagna globale non-MCP attiva, prossimo
candidato da inventory, senza restringere successo al componente sotto soglia.

Campagna non-MCP, frontend click hash navigazione, 2026-10-05:
`handleClick` `IMPROVED`, cog/cyc/LOC/nesting21/11/27/3 ->5/4/6/1;
filtro click e reset hash completi sotto soglia, senza violation trasferite.
NavItem34/20/96/3 ->18/13/75/2; tre error eliminati, tre warning residui sul
componente. File cognitive61 ->38, cyclomatic45 ->41, branching35 ->29,
LOC127 ->128. 43 test/full-file100%, 2048 click e 10080 rendering equivalenti;
ratchet/ESLint/typecheck PASS, baseline/config/scope invariati. Campagna non-MCP
attiva, prossimo candidato tre warning NavItem, non zero debito di repository.

Campagna non-MCP, frontend matching navigazione, 2026-10-05:
`NavItem` `IMPROVED` limitato al matching, cog/cyc/LOC42/28/106 ->34/20/96,
nesting3 invariato. Normalizzazione href e matching exact/prefix condivisi;
helper sotto soglia, nessuna violation trasferita. File cognitive65 ->61,
cyclomatic47 ->45, branching39 ->35, LOC123 ->127; restano cinque violation
(tre error/due warning), incluso handleClick21/11/27/3 invariato. 41 test,
full-file100% su quattro metriche, 10080 rendering equivalenti; ratchet/
ESLint/typecheck PASS, baseline/config/scope invariati. Prossimo candidato:
NavItem ancora in debito; campagna globale non-MCP resta attiva.

Campagna non-MCP, Elaborazioni parser form Bonifica, 2026-10-05:
`parse_form_fields` `IMPROVED`, cog/cyc/LOC/nesting51/21/36/4 ->12/7/14/3.
Lettura select/checkbox e raccolta input separate, helper tutti sotto soglia;
valori, ordine e sovrascritture invariati. File cognitive61 ->38, cyclomatic32
->35 per tre basi callable, branching28 invariato, LOC65 ->68; tre violation
->zero, nessuna violation trasferita. 34 test/full-file100%, 5000 documenti
equivalenti; ratchet/Ruff mirato/format test PASS. Lint globale UP038 InCass
concorrente; cinque test integrati PASS nel virtualenv, geoalchemy2 sistema
mancante. Baseline/config/scope invariati, campagna non-MCP resta attiva.

Campagna non-MCP, Ruolo layout parsing particelle, 2026-10-05:
`parse_particella_line` `IMPROVED`, cog/cyc/LOC/nesting66/25/90/8 ->12/10/24/1.
Layout dichiarativi per lunghezza/variante testuale, selettore5/5/7/1 sotto
soglia e conversione comune. File cognitive75 ->25, cyclomatic37 ->25,
branching31 ->19, LOC144 ->140, callable6 invariati; quattro error ->un warning
ciclomatico, nessun debito trasferito. 23 test/full-file100%, 20000 input
equivalenti inclusi campi/eccezioni; ratchet/Ruff mirato PASS. Lint globale
UP038 InCass concorrente fuori slice, baseline/config/scope invariati.

Campagna non-MCP, Network detector watchlist, 2026-10-05:
`event_detection_tags` `IMPROVED`, cog/cyc/LOC/nesting107/39/62/6 ->6/7/25/0.
Matching lazy in registro, normalizzazione condivisa, guard clause watchlist
e separazione normalizzazione/tagging porte; ramo encrypted_dns morto rimosso.
File cognitive111 ->39, cyclomatic44 ->39, branching42 ->31, LOC136 ->161;
cinque violation ->un warning legacy params, nessuna violation trasferita.
64 test/full-file100%, 2940 input equivalenti, 43 test chiamanti PASS;
ratchet/Ruff mirato PASS. Lint globale UP038 su InCass concorrente fuori slice,
baseline/config/scope invariati. Campagna non-MCP resta attiva.

Campagna non-MCP, Catasto registro spiegazioni, 2026-10-05:
`explainCatastoAnomalia` `IMPROVED`, cog/cyc/LOC/nesting20/12/42/1
->2/3/6/1. Definizioni tipizzate con testi/calcoli, lookup Map e assemblaggio
comune; sei strategie nuove sotto soglia (massimo cog/cyc1/2), imponibile
6/6/26/1 invariato. File cognitive58 ->41, cyclomatic71 ->69, branching44
->36, LOC374 invariato: zero error/zero warning nel file, non nel repository.
89 test, full-file100% su quattro metriche, 22275 input equivalenti;
ratchet/typecheck/ESLint PASS, baseline/config/scope invariati. Campagna
globale non-MCP attiva: prossimo candidato da inventory, senza restringere scope.

Campagna non-MCP, Catasto registro descrizioni, 2026-10-05:
`describeCatastoAnomalia` `IMPROVED`, cog/cyc/LOC/nesting22/13/41/1
->4/5/6/1. Registro Map di testo costante/formatter completi, cinque nuovi
formatter sotto soglia (massimo cog/cyc1/2), nessun wrapper o trasferimento.
File cognitive75 ->58, cyclomatic73 ->71, branching51 ->44, LOC365 ->374
sotto soglia. Due warning eliminati; zero error/due warning residui sulle
spiegazioni. 82 test, full-file100% su quattro metriche, 22275 input
equivalenti; ratchet/typecheck/ESLint PASS, baseline/config/scope invariati.

Campagna non-MCP, Catasto catalogo testi guida, 2026-10-05:
`explainCatastoAnomalia` `IMPROVED`, cog/cyc/LOC/nesting24/14/152/1
->20/12/42/1. Catalogo privato tipizzato, copie liste e ordine preservati;
assemblaggio0/1/14/0 e fallback2/3/17/0 senza violation. File cognitive77
->75, cyclomatic71 ->73 per due basi callable, branching51 invariato;
LOC353 ->365 sotto soglia. Zero error/quattro warning residui, nessun
debito trasferito. 72 test, full-file100% su quattro metriche, 22275 input
equivalenti; ratchet/typecheck/ESLint PASS, baseline/config/scope invariati.

Campagna non-MCP, Catasto spiegazioni/calcoli, 2026-10-05:
`explainCatastoAnomalia` `IMPROVED`, cog/cyc/LOC/nesting47/25/191/2
->24/14/152/1. Helper dominio VAL-06 6/6/42/1 sotto soglia, inserimento
calcoli sorgente/percentuale condiviso. File cognitive94 ->77, cyclomatic76
->71, branching57 ->51, LOC350 ->353. Due error diventano warning; restano
un error LOC/quattro warning, nessun debito trasferito. 69 test, full-file100%
su quattro metriche, 5400 input equivalenti; ratchet/typecheck/ESLint PASS.

Campagna non-MCP, Catasto misure/imponibile, 2026-10-05:
`describeCatastoAnomalia` `IMPROVED`, cog/cyc/LOC34/19/49 ->22/13/41.
Helper imponibile2/3/11/0 sotto soglia, predicato valori formattati condiviso;
file cognitive104 ->94, cyclomatic79 ->76, branching61 ->57, LOC347 ->350.
Due error target diventano warning; tre error/due warning file residui,
nessun debito trasferito. 61 test, full-file100% su quattro metriche,
5400 input equivalenti; ratchet/typecheck/ESLint PASS, baseline invariata.

Campagna non-MCP, Catasto riferimenti sorgente, 2026-10-05:
`describeCatastoAnomalia` `IMPROVED`, cog/cyc44/24 ->34/19; helper
condiviso1/2/3/0, zero violation. Cognitive file113 ->104, cyclomatic82 ->79,
LOC344 ->347, nessun debito trasferito; cinque error residui nel file.
51 test, full-file100% su quattro metriche, 3600 input equivalenti;
ratchet mirato/typecheck/ESLint PASS. Campagna tutti gli hotspot attiva,
MCP escluso operativamente senza alterare baseline/config/scope dei gate.

Catasto frontend formula, 2026-10-05: `formatFormula` `IMPROVED` limitato
ai parametri5 ->4; rimosso parametro inutilizzato, warning params eliminato
ed ESLint ora pulito. Cognitive/cyclomatic/LOC invariati, cinque error
residui nei due export principali. 42 test, full-file100% su quattro
metriche, 686 input equivalenti; ratchet mirato/typecheck/ESLint PASS.
Baseline invariata, nessun altro hotspot runtime aperto in questa slice.

Catasto frontend spiegazioni VAL-07, 2026-10-05: `explainCatastoAnomalia`
`IMPROVED`, cog/cyc/LOC59/31/197 ->47/25/191, nesting2 invariato.
Helper di dominio3/3/10/1, nessuna violation; cognitive file122 ->113,
cyclomatic85 ->82, branching69 ->65, diciassette callable, LOC340 ->344.
Sei violation residue invariati, nessun debito trasferito. 42 test,
full-file100% su quattro metriche, 3600 input equivalenti; ratchet mirato,
typecheck/ESLint PASS (solo warning ESLint legacy). Baseline invariata;
dieci finding globali Wiki MCP esterni, test/docs VAL-06 preservati.

Catasto attesi/delta VAL-06, 2026-10-05: `NO_SAFE_CHANGE` per unificazione
del calcolo. Il ciclo proposto riduceva cog/cyc29/22 ->28/20 ma aumentava
LOC31 ->33; respinto dal ratchet e rimosso. Runtime invariato, baseline
invariata: nessuna riduzione dichiarata. Sei nuove caratterizzazioni,
18 test, full-file100%; ratchet finale/Ruff PASS. Lint globale bloccato
dal formatter del file concorrente `domande_irrigue_parallel.py`. Prossima scelta
di hotspot richiede decisione separata, non avviata automaticamente.

Catasto causa superficie, 2026-10-05: `_enrich_domande_irrigue_surface_payload`
`IMPROVED` limitato a nesting 3 -> 2 e LOC 26 -> 25; cognitive16 e
cyclomatic13 invariati. Nessun helper/callable nuovo o trasferimento debito;
file LOC105 ->104, cognitive64/cyclomatic54 invariati, quattro violation
residue. 12 test prima/dopo, full-file100%, 2880 payload equivalenti con
ordine chiavi preservato; ratchet mirato/Ruff/lint PASS, baseline invariata.

Utenze PIVA parziale, 2026-10-05: `parse_folder_name` `IMPROVED`,
cog/cyc/LOC/nesting 15/12/37/1 -> 8/8/28/1; helper dominio 4/5/13/0,
nessuna violation. **Zero violation nell'intero parser**, entrambi i warning
residui eliminati; cognitive file 18 -> 15, branching aggregato invariato.
Cyclomatic 21 -> 22 per base dell'ottavo callable, LOC file 111 -> 113.
37 test prima/dopo, full-file 100%, 8865 input equivalenti; ratchet mirato,
Ruff/formatter/lint PASS. Dieci finding globali Wiki MCP esterni,
baseline invariata; nessun altro hotspot avviato.

Utenze PIVA completa, 2026-10-05: `parse_folder_name` `IMPROVED`,
cog/cyc/LOC/nesting 17/13/54/2 -> 15/12/37/1; helper azienda 1/2/21/1,
nessuna violation. Cognitive file 19 -> 18; branching aggregato invariato,
cyclomatic 20 -> 21 per base del settimo callable, LOC file 107 -> 111.
Eliminato warning LOC; restano due warning, zero error. 34 test prima/dopo,
full-file 100%, 8865 input equivalenti; ratchet mirato/Ruff/lint PASS.
Ratchet globale con dieci finding Wiki MCP esterni; baseline invariata.

Utenze dispatch persona, 2026-10-05: `parse_folder_name` `IMPROVED` cognitivo,
19 -> 17; helper persona 1/2/22/1 (cog/cyc/LOC/nesting), nessuna violation.
Cognitive file 20 -> 19; cyclomatic 19 -> 20 per base del sesto callable,
branching aggregato invariato a 14. LOC file 105 -> 107, tre warning
invariati, zero error. 25 test, full-file 100%, 8865 input equivalenti;
ratchet mirato PASS, baseline invariata. Lint globale bloccato da formatter
del test concorrente Capacitas, non incluso nella slice.

Utenze review persona, 2026-10-05: `parse_folder_name` `IMPROVED` solo per
LOC/stato derivato, eliminati alias warnings/confidence e bool della lista
vuota. LOC target 76 -> 74, file 107 -> 105; cognitive 19 e cyclomatic 14
invariati, zero error/tre warning. 25 test, full-file 100%, 8865 input
equivalenti, nessun helper/debito trasferito o baseline update.

Utenze guardia vuoto, 2026-10-05: `parse_folder_name` `IMPROVED`, controllo
di input vuoto basato soltanto sui token. Target cog/cyc/LOC 22/16/76 ->
19/14/76; file cognitive 23 -> 20, cyclomatic 21 -> 19, cinque callable
invariati. **Zero error-level**, tre warning residui; 24 test, full-file 100%
e 8865 input equivalenti. Nessun helper/debito trasferito o baseline update.

Utenze nomi persona, 2026-10-05: `parse_folder_name` `IMPROVED`, rimossi
normalizzazioni duplicate e fallback null impossibili sui token persona.
Target cog/cyc/LOC 28/20/76 -> 22/16/76, file cognitive 29 -> 23,
cyclomatic 25 -> 21, cinque callable invariati; error-level 2 -> 1
(cognitive ora warning). 24 test, coverage full-file 100%, 8865 casi
differenziali identici. Nessun helper/debito trasferito, baseline invariata.

Follow-up Catasto, 2026-10-05: `build_anomalia_payload` `IMPROVED`,
serializzazione dei quattro campi numerici VAL-06 con mapping ordinato
e predicato unico non-null. Target cog/cyc/LOC 30/24/31 -> 29/22/31;
file cognitive 65 -> 64, cyclomatic 56 -> 54, sette callable invariati.
Otto test, coverage full-file 100% e 2500 casi differenziali identici;
quattro violation residue, nessun helper/debito trasferito, baseline invariata.

Follow-up Utenze, 2026-10-05: `parse_folder_name` `IMPROVED` dopo il goal
separato di rimozione della guardia `missing_nome` irraggiungibile.
Target cog/cyc/LOC 30/21/79 -> 28/20/76, file cognitive 31 -> 29,
cinque callable invariati; coverage full-file 100%, 22 test e 5655 casi
differenziali identici. Tre violation legacy residue, baseline invariata.
Il blocco coverage registrato nel checkpoint W1 sotto e ora superato.

Checkpoint W1 parallelo, 2026-10-05:

- Organigramma `handleSchemaCardSelect`: `IMPROVED`, cognitive 23 -> 16,
  nesting 2 -> 1, cognitive file 59 -> 52; nessun helper o debito trasferito.
  Restano quattro warning callable nel file. Singolo hotspot chiuso.
- Catasto `build_anomalia_payload`: caratterizzazione completata full-file
  100% (99 statement, 52 branch), runtime invariato 30/24/31/2.
  Il refactoring runtime resta un goal futuro, non avviato da W1.
- Utenze `parse_folder_name`: caratterizzazione 22 test; resta la guardia
  irraggiungibile `missing_nome`, statement 56/58 e branch 15/16.
  Rimozione approvata solo come prossimo goal separato; runtime invariato.

Evidenze nel checkpoint W1 in `PROGRESS.md`; nessuna baseline aggiornata.

Audit baseline globale e ordine delle tranche:
[BASELINE_RECOVERY.md](BASELINE_RECOVERY.md), 2026-09-15.

| Stato | Percorso | Segnale iniziale | Nota |
| --- | --- | --- | --- |
| closed | `backend/app/modules/wiki/mcps/experiment_runner.py` / firma `run_comparison` | parametri `6 -> 3`; warning runner `1 -> 0` | `IMPROVED` 2026-10-05 limitato alla firma, API Python interna modificata con autorizzazione esplicita: executor gia configurato al posto dei quattro parametri separati. Chiamante CLI/test aggiornati, nessun wrapper o esclusione; CLI e HTTP pubblici invariati. Due runtime senza warning/error, 19 callable e aggregate cognitive/cyclomatic invariati; 304 MCP verdi, entrambi i file statement/branch 100%, ratchet mirato da scan completo verde. Baseline invariata; gate globali estranei non verdi |
| closed | `backend/app/modules/wiki/mcps/experiment_runner.py` / `ResultJournal.__init__` | cog/cyc/LOC/nesting `18/10/19/2 -> 5/4/13/2`; file cognitive `71 -> 66` | `IMPROVED` 2026-10-05: lettura/validazione separata dal lifecycle lock/cleanup; `_read_rows` `8/7/9/1` sotto soglia. Due warning eliminati, decisioni aggregate 48 invariate. 36 test experiment prima/dopo, 303 MCP verdi, full-file statement/branch 100%, ratchet mirato verde da scan completo. Resta il warning della firma `run_comparison`, fuori da questa slice; baseline invariata |
| reduced | `backend/app/modules/wiki/mcps/experiment_runner.py` / `run_comparison` | target cog/cyc/LOC/nesting `21/9/34/4 -> 4/4/11/2`; file cognitive sum `81 -> 71` | `IMPROVED` 2026-10-05: orchestration separata dalla ripresa/retry del singolo item; `execute_item` `7/6/19/2` sotto soglia. Warning `5 -> 3`, decisioni aggregate `48 -> 48`, nessun debito trasferito. 31 test experiment, full-file statement/branch 100%, ratchet mirato verde con scan completo; restano warning del costruttore journal e dei parametri pubblici. Baseline invariata, gate globali estranei non verdi; stop dopo un hotspot |
| reduced | `backend/app/modules/wiki/mcps/data/service.py` / `DataService.call` | cog/cyc/LOC `13/10/60 -> 2/3/25`, file cog sum `58 -> 57`, cyc `48` invariata | `IMPROVED` 2026-10-03: risposta e telemetria separate, helper `10/7/38` sotto soglia, 129 test e full-file 100%; warning `5 -> 3`, nessun debito trasferito. Baseline invariata: due finding ereditati del costruttore bloccano il ratchet, 20 globali residui; report `BASELINE_REDUCTION_2026-10-03.md` |
| reduced | `frontend/src/lib/catasto-gis-coordinate-search.ts` / DMS direzionale | `parseDirectionalDms` cog/cyc `13/11 -> 11/9`, LOC `16` invariata | `IMPROVED` 2026-10-03: direzione obbligatoria nel tipo privato, guardie lookup ridondanti rimosse; aggregati cog/cyc `50/59 -> 46/55`, 48 test e full-file 100%, ratchet mirato verde; zero violation nel file |
| reduced | `frontend/src/lib/catasto-gis-coordinate-search.ts` / DMS signed | `parseSignedDms` cog/cyc `19/9 -> 4/4`, LOC `12 -> 10` | `IMPROVED` 2026-10-03: validatore DMS esistente riusato, nessun nuovo helper, segni/limiti/fallback invariati; aggregati cog/cyc `65/64 -> 50/59`, 31 test e full-file 100%, ratchet mirato verde; warning signed eliminato, ciclomatica direzionale residua |
| reduced | `frontend/src/components/elaborazioni/workspace-modal.tsx` / route statiche | `NativeWorkspaceRenderer` cog/cyc `14/15 -> 5/6`, LOC `67 -> 53` | `IMPROVED` 2026-10-03: dispatch dichiarativo locale senza factory, props e fallback invariati; aggregati cog/cyc `33/41 -> 24/32`, 62 test e full-file 100%, ratchet mirato verde; error ciclomatica eliminata, due warning LOC residui |
| reduced | `frontend/src/components/elaborazioni/workspace-modal.tsx` / sezione Capacitas | `getCapacitasSectionFromHref` cog/cyc `22/10 -> 7/5`, LOC `14 -> 13` | `IMPROVED` 2026-10-03: lookup tipizzato, query/hash e fallback SSR invariati; aggregati cog/cyc `48/45 -> 33/41`, 50 test e full-file 100%, ratchet mirato verde; due warning target eliminati, debito renderer/modale residuo |
| reduced | `frontend/src/lib/utenze-payment-notices-summary.ts` / riepilogo conteggi | `buildPaymentNoticeSummary` cog/cyc `10/11 -> 9/10`, LOC `25` invariata | `IMPROVED` 2026-10-02: conteggi non negativi sommati, soglia e testi invariati; nessun nuovo helper, aggregati cog/cyc `51/44 -> 50/43`, 28 test e full-file 100%, ratchet mirato verde; warning alla soglia 10 residuo |
| reduced | `frontend/src/lib/utenze-payment-notices-summary.ts` / stato esplicito | `getPaymentNoticeStatus` cog/cyc `22/14 -> 18/12`, LOC `15 -> 14` | `IMPROVED` 2026-10-02: lookup tipizzato dei tre stati ammessi, priorita e fallback finanziari invariati; aggregati cog/cyc `55/45 -> 51/44`, 18 test e full-file 100%, ratchet mirato verde; tre warning legacy residui |
| reduced | `frontend/src/lib/network-device-utils.ts` / sorgente HTTP | `getNetworkDeviceAdminUrl` cog/cyc `18/12 -> 13/11`, LOC `24 -> 21`, nesting `2 -> 1` | `IMPROVED` 2026-10-02: parsing assente/vuoto consolidato, schemi ammessi dichiarativi; nessun nuovo helper, 42 test e full-file 100%, ratchet mirato verde; cognitiva sotto soglia, warning cyclomatic residuo |
| reduced | `frontend/src/lib/catasto-anomalie.ts` / descrizione importi | `describeCatastoAnomalia` cog/cyc `60/32 -> 44/24`, LOC `54 -> 49` | `IMPROVED` 2026-10-02: descrizione condivisa delle voci VAL-07, testo e ordine invariati; aggregati cog/cyc `133/88 -> 122/85`, 35 test e full-file 100%, ratchet mirato verde; warning LOC eliminato, debito legacy residuo |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` / query opzionale | `buildSupportHrefFromPayload` cog/cyc `10/11 -> 4/5`, LOC `23 -> 22` | `IMPROVED` 2026-10-02: chiavi ordinate e serializzazione comune preservano omissione, encoding e ordine; aggregati cog/cyc `16/22 -> 11/18`, zero violation nel file, 60 test e full-file 100%, ratchet mirato verde |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` / mapping pathname | `inferModuleKeyFromPath` cog/cyc `12/13 -> 1/2`, LOC `15 -> 3` | `IMPROVED` 2026-10-02: tabella ordinata conserva startsWith e alias; aggregati cog/cyc `27/32 -> 16/22`, warning mapper rimosso, full-file 100% e ratchet mirato verde |
| reduced | `frontend/src/features/wiki/context-links.ts` | `buildWikiContextHref` cog `36 -> 23`, cyc `21` invariata, LOC `62 -> 61`, nesting `2 -> 1` | `IMPROVED` 2026-10-02: chiave assente normalizzata, guardia esterna eliminata; 29 test e full-file 100%, ratchet mirato verde; error cognitiva rimossa, ciclomatica legacy residua |
| reduced | `frontend/src/features/wiki/audit-utils.ts` | `buildWikiAuditStats` cog/cyc `15/15 -> 12/12`, LOC `59 -> 51` | `IMPROVED` 2026-10-02: Map delle modalita, sconosciute ignorate, nessun nuovo callable; aggregati cog/cyc `31/37 -> 25/31`, error `1 -> 0`, full-file 100%, ratchet mirato verde |
| blocked | `frontend/src/lib/api/core.ts` / risposte vuote | `request` cog/cyc/LOC `24/20/60` invariati | `NO_SAFE_CHANGE` 2026-10-02: guardia condivisa aumentava la cognitiva a 25, ripristinata; conservati 19 test di precedenza/parsing, nessun delta runtime della slice; scegliere un candidato diverso |
| reduced | `frontend/src/lib/api/core.ts` / lifecycle timeout-abort | `request` cog `28 -> 24`, cyc `22 -> 20`, LOC `62 -> 60` | `IMPROVED` 2026-10-02: cleanup in finally e guardia ridondante rimossa, nessun nuovo helper; 842 test API, full-file 100%, ratchet mirato verde; error cognitiva rimossa, ciclomatica legacy residua |
| reduced | `frontend/src/lib/api/core.ts` | `request` cog `54 -> 28`, cyc `30 -> 22`, LOC `82 -> 62` | `IMPROVED` 2026-10-02: decoder HTTP privato sotto soglia error, cognitiva aggregata `155 -> 147`; 833 test API e coverage full-file 100%, ratchet mirato verde; debito timeout/abort e decoder Blob/XHR residuo |
| reduced | `frontend/src/lib/network-device-utils.ts` | `getNetworkDeviceAdminUrl` cog `22 -> 18`, cyc `12` invariata, LOC `28 -> 24`, nesting `3 -> 2` | `IMPROVED` 2026-10-01: risoluzione target appiattita senza helper; 30 test e coverage full-file 100%, ratchet mirato verde, due warning residui |
| reduced | `frontend/src/lib/organigramma.ts` | `computeTreeInclusion` cyc `11 -> 10`, cog `19 -> 17`, LOC `27` invariata | `IMPROVED` 2026-10-01: controllo ricerca vuota ridondante eliminato, aggregati ridotti senza estrazioni; 20 test e coverage full-file 100%, due warning residui |
| reduced | `frontend/src/features/wiki/request-support-payload.ts` | `buildWikiRequestPayload` cyc `10 -> 6`, cog `13 -> 5`, LOC `61 -> 49` | `IMPROVED` 2026-09-22: campi comuni consolidati senza helper, target sotto soglia, due warning distinti residui; 27 test e coverage full-file 100% |
| closed | `frontend/src/lib/document-preview.ts` | `getDocumentPreviewKind` cyc `12 -> 9`, cog `15 -> 9`, LOC `23` invariata | `IMPROVED` 2026-09-22: estensione normalizzata una volta, tre guard null eliminati, zero violation nel file; 13 test e coverage full-file 100% |
| blocked | `frontend/src/app/gis/catalogo/guided-workflow.ts` / `guidedChangeValidation` | cognitive `17`, cyclomatic `12`, LOC `29`, invariati | `NO_SAFE_CHANGE` 2026-09-22: nessuna semplificazione locale convincente individuata; dieci test di precedenza/confine aggiunti, 33 test complessivi e coverage 100%; scegliere un candidato diverso |
| reorganized | `frontend/src/app/gis/strumenti/activity-center.tsx` | Componente cyc `15 -> 10`, cog `14 -> 9`, LOC `95 -> 62` | `REORGANIZED_AND_CHARACTERIZED` 2026-09-22; lifecycle in hook locale sotto soglia, error `2 -> 0`, due warning residui; decisioni aggregate invariate, 24 test e coverage full-file 100% |
| reduced | `frontend/src/app/gis/catalogo/guided-workflow.ts` | `geometryFromCoordinates` cyc `15 -> 10`; slice 2026-09-22 `coordinatesFromGeometry` cyc `11 -> 9`, cog `13 -> 10`, LOC `19 -> 17` | `IMPROVED`; rami Polygon/MultiLineString unificati, aggregati ridotti senza estrazioni, zero error e quattro warning nel file, 23 test e coverage full-file 100%; baseline globale ancora da recuperare |
| reorganized | `backend/app/modules/presenze/router.py` | facade package; cognitive legacy sum/max `1.353/111`, cyclomatic legacy sum/max `1.139/64` | `REORGANIZED_AND_CHARACTERIZED`; 86 route e OpenAPI invariati, coverage 100%, file max LOC `718`; tre mismatch di identita contro baseline storica da risolvere separatamente |
| reorganized | `backend/app/modules/me/router.py` | facade package; cognitive legacy sum/max `123/38`, cyclomatic legacy sum/max `130/24` | `REORGANIZED_AND_CHARACTERIZED`; 17 route e OpenAPI invariati, coverage 100%, tutti i 29 fingerprint legacy e le metriche callable preservati, file max LOC `336` |
| reorganized | `backend/app/modules/gis/router.py` | facade package; cognitive legacy sum/max `6/2`, cyclomatic legacy sum/max `52/3` | `REORGANIZED_AND_CHARACTERIZED`; 51 operazioni e OpenAPI invariati, coverage 100%, tutti i 46 fingerprint legacy preservati, file max LOC `122` |
| reorganized, coverage complete | `frontend/src/features/organigramma/organigramma-workspace.tsx` | `OrganigrammaWorkspace` cyc `363 -> 147`, cog `477 -> 167`, LOC `1779 -> 1086` | 2026-10-02: workspace, sei controller e helper al 100% su tutte le metriche, 434 test verdi; matching risolto con nomi espliciti dei renderer/azioni, ratchet main verde. Contratti preservati; nessuna esclusione, modifica baseline o test di stati impossibili. `REORGANIZED_AND_CHARACTERIZED`; debito legacy di complessita residuo non dichiarato eliminato |
| reduced | `frontend/src/app/catasto/gis/page.tsx` | Controlli e archivio 2026-09-07: cyc `386 -> 302`, cog `433 -> 338`, LOC file `2619 -> 2187` | `IMPROVED`; otto runtime GIS al 100% full-file, archivio caratterizzato e ratchet GIS verde; restano debito legacy della pagina e sincronizzazione baseline globale separata |
| reduced | `frontend/src/app/catasto/particelle/[id]/page.tsx` | Catasto-H1 `CatastoParticellaDetailPage` cyc `131 -> 3` cog `145 -> 2` LOC `656 -> 42` | Hotspot dedicato chiuso; perimetro aggregato senza violation error-level |
| reduced | `frontend/src/app/gis/strumenti/tools-workspace.tsx` | GIS-H8 `GisToolsWorkspace` cyc `60 -> 2` cog `72 -> 1` LOC `226 -> 17` | Hotspot dedicato chiuso; warning LOC residuo sull'hook |
| candidate | `frontend/src/lib/api.ts` | circa 5.833 righe | Valutare quanto e dichiarativo prima di priorizzarlo |
| blocked | `frontend/src/app/presenze/giornaliere/page.tsx` | `PresenzeGiornalierePage` cog `573`, cyc `478`, LOC `2284` | 2026-09-30: 14 test verdi dopo isolamento WhatsApp; coverage reale statement 70,88%, branch 57,02%; esclusione v8 dell'intera pagina non dimostra il gate 100%; caratterizzazione necessaria prima della slice runtime |
| candidate | `backend/app/modules/ruolo/tributi_repositories.py` | circa 4.233 righe | Dominio critico; refactor solo con caratterizzazione forte |
| candidate | `frontend/src/app/ruolo/tributi/page.tsx` | file molto grande | Dominio critico e UI complessa |
| candidate | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | file molto grande | Verificare stato, effetti e confini feature |
| reorganized | `backend/app/modules/catasto/routes/anagrafica.py` | facade package; cognitive sum/max `2.101/363`, cyclomatic sum/max `1.367/135` | `REORGANIZED_AND_CHARACTERIZED`; 13 operazioni e OpenAPI invariati, coverage 100%, file max LOC `712`, ratchet verde senza aggiornare la baseline |
| reorganized | `backend/app/modules/network/router.py` | facade package; cognitive sum/max `1.101/209`, cyclomatic sum/max `774/109` | `REORGANIZED_AND_CHARACTERIZED`; 39 endpoint e OpenAPI invariati, coverage 100%, nessun file estratto sopra soglia LOC |
| below-threshold | `backend/app/modules/gis/services.py` / `_validate_shapefile_zip` | cog/cyc/LOC `25/22/63 -> 21/19/62 -> 7/8/33` | Semplificazioni iniziali `IMPROVED`, poi `REORGANIZED_AND_CHARACTERIZED` 2026-10-03: componenti e lettura pyshp in `shapefile_validation.py`, tutti i callable sotto soglia, nessun contratto cambiato. Aggregati dell'ultima slice cog/cyc `490/503 -> 490/505`, 111 callable; nessuna riduzione delle decisioni dichiarata. 300 test, full-file 100% sui due runtime e ratchet mirato verde. Zero violation target/estratti; restano 36 violation legacy estranee e gate globali bloccati da modifiche concorrenti |
| candidate | `modules/elaborazioni/worker/worker.py` | circa 1.676 righe | Preservare retry, concorrenza e lifecycle |
| reorganized | `frontend/src/types/api.ts` | `0` callable; facciata di 8 righe su 7 barrel dominio, tutti i file sotto soglia | `REORGANIZED_AND_CHARACTERIZED`; nessun runtime o contratto pubblico modificato |
| reorganized | `frontend/src/lib/api.ts` | facciata su 15 moduli; cognitive sum/max `545/54`, cyclomatic sum/max `851/30` | `REORGANIZED_AND_CHARACTERIZED`; 450 export preservati, coverage completa, warning file-level residuo in `network.ts` |
| reorganized | `backend/app/modules/utenze/router.py` | facade package + route modules; cognitive sum/max `409/39`, cyclomatic sum/max `403/28` | `REORGANIZED_AND_CHARACTERIZED`; OpenAPI identica, coverage 100%, warning LOC residuo in `routes/support.py` |

## Dati da aggiungere dopo la Fase 1

| Percorso | Max cognitive | Max cyclomatic | Densita | Violazioni | Churn 90d | Rischio | Priorita |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| - | - | - | - | - | - | - | - |

## Regole di selezione

1. Il candidato deve essere misurato dal motore corrente.
2. LOC da sole non determinano la priorita.
3. Preferire una slice con test esistenti e comportamento osservabile.
4. Evitare come primo intervento un dominio fiscale/catastale critico se manca
   caratterizzazione.
5. Considerare churn e difetti storici.
6. Un file dichiarativo puo diventare eccezione stretta, non un refactoring
   artificiale.
7. Ogni goal sposta una sola riga in `in_progress`.

## Stati

- `candidate`: da misurare;
- `ready`: invarianti e test individuati;
- `in_progress`: un solo goal attivo;
- `reduced`: metriche ridotte, debito residuo presente;
- `closed`: sotto soglia o responsabilita adeguatamente separate;
- `blocked`: serve decisione o test mancante;
- `exception-review`: possibile codice dichiarativo da valutare.
- `reorganized`: ownership migliorata senza dichiarare una riduzione di complessita callable.
