# GAIA — Multi-Agent Complexity Campaign

**Global goal ACTIVE / INCOMPLETE.** Round2 runtime is integrated and its
focused gates are GREEN; the full backend suite remains in progress. Round3
is active only in isolated worktrees. The original sections after this update
certify the historical R1 checkpoint, not completion of the global mission.
Requirements and
completion audit: `docs/code-quality/CAMPAIGN_GLOBAL_GOAL_2026-10-08.md`.
Next-tail coverage limitations: `ROUND2_EXTREME_READINESS_2026-10-08.md`.

Data: 2026-10-08. Campagna autorizzata di refactoring locale e caratterizzazione,
senza sviluppo funzionale. Questo documento distingue risultati integrati,
prerequisiti test-only e obiettivi strategici ancora aperti.

## Stato cumulativo Round2

Independent integration checkpoint `65097ce2`; runtime commits `87efd9bb`
(Presenze), `3f9863fb` (Settings), `bf4c9a26` (analytics prerequisite).
Eight cumulative runtime slices are accepted, not the entire extreme tail.
All three Round2 slices are IMPROVED, with real aggregate reductions and no
new helper findings; the prerequisite does not claim substantive fuel
decomposition. Source commits `5f1ba840`, `9a01d35a`, `6909abd7`.

| Metrica | Initial clean55a | Round2 integrato | Delta |
| --- | ---: | ---: | ---: |
| Error | 1956 | 1943 | -13 (-0,665%) |
| Warning | 2758 | 2749 | -9 (-0,326%) |
| Finding | 4714 | 4692 | -22 (-0,467%) |
| Cognitive aggregata | 81931 | 81566 | -365 |
| Cyclomatic aggregata | 83666 | 83437 | -229 |
| File LOC aggregata | 332181 | 332206 | +25, non miglioramento LOC |
| Cognitive>300 | 8 | 8 | 0 |
| Cognitive>200 | 18 | 17 | -1 |
| Cognitive>100 | 55 | 55 | 0 |

Scansione completa `/tmp/gaia-r2-integrated-complexity.json`:1665file,
20266callable. Presenze principale550→506, Settings402→335,
fuel366→332, anomalies365→361. Gli otto estremi>300 restano aperti;
i target globali978error/2068warning e zero>200 **NON** sono raggiunti.
Non usare il totale finding come numero di problemi indipendenti.

Round2 characterization indipendente573PASS, cinque runtime modificati
full-file statement/branch100%; ratchetmain PASS0 dopo ciascuna integrazione.
Frontend4074PASS/282file, smoke18PASS/typecheck/cleanbuildPASS; browser52PASS
7skip storici, nessun flaky. Browser certifica frontend `3f9863fb` ma precede
l'integrazione backend P3: non estendere quel PASS a P3. Backend completo sul
runtime congelato `bf4c9a26` in corso, non ancora PASS. Worker/tooling R1
invariati, nessun nuovo full-suite PASS dedotto senza nuova esecuzione.

Global check al checkpoint UI FAIL30: finding objects identici a R1,
nessuna nuova divergenza né assorbimento baseline/soglie/esclusioni/tooling.
Report: `ROUND2_CHECKPOINT_2026-10-08.md`,
`INTEGRATION_ROUND2_2026-10-08.md`, `INTEGRATION_R2_P3_2026-10-08.md`,
`ROUND2_BROWSER_VERIFICATION_2026-10-08.md` e tre report slice R2.

Round3 esclusiva da `65097ce2`: modello mensile Presenze, mutation commands
provider Settings, computazione veicoli fuel. Nessun nuovo backend integrato
durante la suite congelata. Nessun completamento del goal implicito in questi
checkpoint; correttezza e reviewability restano prioritarie.

## Snapshot iniziale

- Branch di origine: `main`.
- HEAD e merge-base verificati: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Audit autorevole: `COMPLEXITY_AUDIT_2026-10-08.md` e
  `complexity-audit-2026-10-08-summary.json`, nel checkout principale.
- AST iniziale dell'audit: `/tmp/gaia-complexity-complete-2026-10-08.json`.
- Baseline operativa della change: baseline versionata al merge-base sopra.
  Nessun numero del report del 7 ottobre usato per il gate.
- Main contiene modifiche concorrenti Presenze, Ruolo ed Elaborazioni:
  nessun reset, stash, copia automatica, commit o integrazione di quel lavoro.

L'audit del checkout principale comprende tre file e quattro callable concorrenti
assenti nello snapshot Git pulito. Per attribuire il delta alla campagna è stata
misurata anche la sorgente pulita: `/tmp/gaia-campaign-clean-before.json`.
I tre file mancanti non sono una riduzione del debito prodotta dalla campagna.
Sono `gate_inaz_details.py`, `inaz_assigned_calendar.py` in Presenze/services e
`posta_online_recipient_columns.py` in Ruolo/services; quattro callable totali.

## Agents

Capacità massima: quattro agenti inclusa root. I ruoli sono stati riassegnati
sequenzialmente mantenendo ownership esclusiva e worktree distinte.

| Role | Agent operativo | Responsabilità |
| --- | --- | --- |
| Coordinator | root | Preflight, registry, sequenza, P6, readiness B3/B6, suite e rapporto |
| Baseline/Provenance | baseline | 30 divergenze storiche, nessuna modifica baseline |
| P1, poi B4 | presenze_ui | Card anomalie Presenze, poi normalizzazione bytes Network |
| P2, P4, poi B5 | capacitas_ui | Capacitas/Catasto characterization, poi eventi metriche Wiki |
| P3, P5 | analytics | Characterization analytics e dettaglio Utenze |
| Integration | baseline, dopo Wave 0 | Review indipendente e cherry-pick sequenziali |
| Integration C2 | capacitas_ui, dopo B5 | Review GIS e gate della slice, ownership sequenziale |
| Final Verification | analytics, dopo P5 | Scansione finale, gate, analisi suite e report indipendente |
| Wave 3 readiness | baseline / presenze_ui | ADE WFS e GIS, sola misura dopo checkpoint verde |

Il registro preventivo completo è
`docs/code-quality/MULTI_AGENT_OWNERSHIP_2026-10-08.md`.
Tutti i 30 percorsi della priority list sono stati considerati nel planning.
Nessun file runtime ha avuto due owner scriventi contemporanei.

## Waves

| Wave | Esito / perimetro realmente eseguito |
| --- | --- |
| 0 | Provenance completata e integrata; 30/30 divergenze classificate |
| 1 | P1/P6 runtime integrati; P2/P3/P4/P5 characterization integrata, runtime bloccato |
| Integration 1 | GREEN: 479 test, full-file 100%, ratchet 0; poi test-only review/gate |
| 2 | B4/B5 runtime integrati dopo review e gate; B1 concurrent, B3/B6 coverage gap |
| Integration 2 | GREEN: Network/Wiki characterization, full-file 100%, ratchet 0 |
| 3 | C2 GIS Excel integrata, full-file100%; ADE WFS runtime bloccato per PostGIS/coverage |
| 4 | Readiness worker completata, altri domini NOT_MEASURED; nessuna implementazione runtime |

Non si dichiara eseguito l'intero backlog di tutte le wave. Il freeze dopo le
cinque slice accettate garantisce che le suite finali certifichino una sorgente
stabile. Le grandi orchestrazioni non coperte non vengono modificate per inseguire
una percentuale arbitraria di finding eliminati. Dopo readiness100% e
checkpoint precedente GREEN è stata autorizzata anche C2 GIS, frontend-only.
Il backend rimane identico durante la sua suite finale; frontend/scanner/build
e browser sono ripetuti dopo C2, non ereditano i PASS di un bundle precedente.

## Branch / worktree

Risultati integrati in:

- Branch `refactor/complexity-campaign-20261008`.
- Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.
- Backend congelato al checkpoint `897dddeadbd93aa3dc849c14cefa491c68e4315a`;
  frontend finale C2 in `1cf26e0359fa57fea4381ca3fac140683b6b9821`, checkpoint
  finale `96e802e5ce2400ed3e37254ca9d2dea0a03917d8`.
- Ogni worktree di dominio nasce dal medesimo snapshot55a; non incorpora main dirty.
- Nessun push, PR, merge nella main o cambio del suo HEAD.

| Slice | Commit originale | Commit integrato |
| --- | --- | --- |
| Provenance | `49a2b3a1` | `606caa05` |
| P1 Presenze | `c14eb8bd` | `b37d7ec5` |
| P2 Capacitas test-only | `60d44529` | `55082ef2` |
| P6 Settings | `d92d39aa` | `0861f811` |
| P3 Analytics test-only | `48de12ef` | `5efac219` |
| P4 Catasto test-only | `764d3158` | `a205a508` |
| P5 Utenze test-only | `3cb1b6e3` | `71b817b9` |
| B4 Network | `664df72f` | `69c15454` |
| B5 Wiki | `4df202e7` | `6ee6fdf8` |
| C2 GIS Excel | `bf28b1d4` | `1cf26e03` |

Registry e checkpoint contengono i path/branch delle worktree individuali.
Le branch storiche preesistenti non sono state integrate.

## Baseline provenance

Report dedicato: `BASELINE_PROVENANCE_2026-10-08.md`.

- 15 `REAL_REGRESSION` runtime **storiche**, non introdotte dalla campagna.
- 15 `TEST_ONLY_DIVERGENCE`, tutte nei test worker.
- Zero `BASELINE_STALE`, `UNKNOWN` o divergenze assorbite modificando JSON.
- Per ogni finding documentati file, callable, metrica, valore baseline/current,
  commit introduttivo e relazione con il working tree/campagna.
- Distribuzione: Backend MCP13, Frontend MCP1, Frontend Ruolo1, Worker tests15.

Le metriche baseline corrispondono alla sorgente storica dimostrata. Queste
divergenze non sono liquidate come rumore né attribuite automaticamente al refactor.
Resta una attività separata per decidere come rimediare alle regressioni storiche;
la campagna non aggiorna la baseline per nasconderle.

## Initial metrics

| Perimetro | File | Callable | LOC effettive | Error | Warning | Finding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Audit ufficiale8/10 | 1665 | 20261 | n/d | 1956 | 2758 | 4714 |
| Audit applicativo senza worker tests | 1611 | 18940 | 318856 | 1948 | 2703 | 4651 |
| Snapshot Git pulito, ufficiale | 1662 | 20257 | 332181 | 1956 | 2758 | 4714 |
| Snapshot Git pulito, applicativo | 1608 | 18936 | 318776 | 1948 | 2703 | 4651 |

Il totale finding non è il numero di problemi indipendenti: uno stesso callable
può superare più soglie. Le somme cognitive includono il modello di traversal
dei callable annidati dello scanner, non decisioni uniche del programma.

## Final metrics

Scansione `/tmp/gaia-complexity-final.json` e `.md`, sul runtime congelato.

| Perimetro | File | Callable | LOC effettive | Error | Warning | Finding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Snapshot finale ufficiale | 1663 | 20262 | 332159 | 1944 | 2751 | 4695 |
| Snapshot finale applicativo | 1609 | 18941 | 318754 | 1936 | 2696 | 4632 |

La change pulita aggiunge un file e cinque callable netti, inclusi i piccoli
helper/presenter. Non sono stati rimossi file; le differenze con l'audit dirty
iniziale non sono riduzioni attribuite al refactoring.

## Delta

Confronto causale: snapshot Git pulito55a → snapshot finale congelato.

| Metrica | Before | After | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Error | 1956 | 1944 | -12 | -0,61% |
| Warning | 2758 | 2751 | -7 | -0,25% |
| Finding | 4714 | 4695 | -19 | -0,40% |
| Cognitive sum | 81931 | 81667 | -264 | -0,32% |
| Cyclomatic sum | 83666 | 83492 | -174 | -0,21% |
| Callable LOC sum | 328259 | 327961 | -298 | -0,09% |
| File LOC sum | 332181 | 332159 | -22 | -0,01% |
| Callable | 20257 | 20262 | +5 | +0,02% |
| Callable cognitive >300 | 8 | 8 | 0 | 0% |
| Callable cognitive >200 | 18 | 17 | -1 | -5,56% |

Nessuna riduzione di parametri o concentrazione degli hook è rivendicata.
Nesting refresh Wiki7→6 e ranking3→2; gli altri target conservano nesting.

## Delta %

Nel perimetro dei cinque file runtime originali accettati e del nuovo helper:

- Cognitive sum3503→3239: **-264 / -7,54%**.
- Cyclomatic sum3253→3079: **-174 / -5,35%**.
- Callable principali selezionati1683→1567: **-116 / -6,89%**.

La coda >300 resta sostanzialmente intatta. Il target P1 -50%/<250 non è
raggiunto e la riduzione strategica dell'intera coda estrema resta aperta.
Non sono successi equivalenti una riduzione locale misurata e il completamento
dell'obiettivo globale della campagna.

## Domain results

| Domain | Error before | Error after | Warning before | Warning after |
| --- | ---: | ---: | ---: | ---: |
| Backend runtime | 1035 | 1033 | 1688 | 1690 |
| Frontend runtime | 878 | 868 | 881 | 872 |
| Worker runtime | 35 | 35 | 134 | 134 |
| Worker tests, fuori campagna runtime | 8 | 8 | 55 | 55 |
| Totale | 1956 | 1944 | 2758 | 2751 |

I due error Wiki e un error LOC GIS diventano warning perché le metriche scendono, non perché
cambia la soglia. B4 riduce la complessità senza eliminare finding sopra soglia.

## Extreme hotspot

| Callable | Before cognitive | After cognitive | Delta |
| --- | ---: | ---: | ---: |
| PresenzeGiornalierePage | 550 | 525 | -25 |
| ElaborazioniSettingsWorkspace | 402 | 366 | -36 |
| _build_network_statistics_summary | 209 | 181 | -28 |
| refresh_wiki_conversation_daily_metrics | 188 | 178 | -10 |
| _latest_dimension_counts | 50 | 23 | -27 |
| CatastoGisPage | 334 | 317 | -17 |
| handleImportXlsx | 43 | 26 | -17 |
| ElaborazioniCapacitasWorkspace | 472 | 472 | 0 |
| DetailContent Utenze | 391 | 391 | 0 |
| CatastoAnomaliePageContent | 390 | 390 | 0 |
| fuel_analytics | 366 | 366 | 0 |
| anomalies_analytics | 365 | 365 | 0 |
| _run_bonifica_sync_background | 269 | 269 | 0 |

Gli aggregati includono presenter/helper nuovi: non è una contabilizzazione
basata soltanto sulla scomparsa di LOC dal callable principale.

## Tests

| Gate | Risultato osservato | Evidenza |
| --- | --- | --- |
| P1/P6 integration characterization | 479 PASS, 0 skip | INTEGRATION_CHECKPOINT |
| Network helper/API | 95 PASS | SLICE_B4, integration rerun |
| Wiki chat/campaign | 107 PASS | SLICE_B5, integration full-file rerun |
| GIS Excel characterization | 37 PASS | SLICE_C2, integration full-file rerun |
| Frontend completa post-C2 | 4059 PASS, 281 file | gaia-campaign-frontend-final2-tests.log |
| Frontend smoke | 18 PASS | gaia-campaign-frontend-final-smoke.log |
| Production build:clean post-C2 | PASS, warning hook legacy | gaia-campaign-frontend-final2-build.log |
| Typecheck / lint-backend changed | PASS | final-typecheck / backend-final-lint logs |
| Tooling completo | 169 PASS | gaia-campaign-quality-final-tests.log |
| Worker completo | 778 PASS, 1 skip, 52 file | gaia-campaign-worker-final-tests3.log |
| Browser finale seriale post-C2 | 52 PASS, 7 skip, 0 fail | gaia-campaign-e2e-final2-serial.json |
| Backend completo finale | 6560 PASS, 449 skip, 0 fail | backend-final-corrected2-tests.log |

I risultati definitivi e i comandi esatti sono certificati dal report indipendente
`FINAL_VERIFICATION_2026-10-08.md`. La suite backend finale dura1379,80s,
quella frontend206,47s; test skipped non sono aggiunti al numero PASS.

### Tentativi falliti e cause

- Backend dalla root sul runtime iniziale: 6497 PASS, 449 skip, 1 FAIL.
  `test_database_sqlite_engine_options_in_subprocess` non trova `app` nel
  subprocess senza cwd backend/PYTHONPATH. Eseguito correttamente dalla directory
  backend: tutto il file26PASS. Non cambiato il test o il runtime per farlo passare.
- Un primo avvio della suite corretta è stato fermato subito dal Coordinator,
  prima della collection, per aspettare il freeze B5: TERMINATED, non PASS.
- Worker tentativo1: Settings mancanti DATABASE_URL/JWT; tentativo2: root scripts
  fuori PYTHONPATH. Tentativo3 con ambiente sintetico/PYTHONPATH root esegue tutti
  i52file. Nessuna modifica al Makefile o alle dipendenze.
- E2E parallelo tentativo1:51PASS1FAIL7skip, timeout login Distretti; retry isolato
 2PASS. Tentativo2:51PASS1FAIL7skip, editor turnista non trovato dopo reload;
  retry isolato3PASS. Intera suite seriale52PASS7skip senza cambi di test/timeout.
  I due tentativi restano failure documentate; non vengono convertiti in PASS.
- Coverage eager dotted-source Network: collection SQLAlchemy double registration;
  misura corretta directory-source, stessa strategia prima/dopo, nessun waiver.

I sette skip browser: feature ritirata1, drilldown non seedati2, integrazioni
GIS/Territorio opt-in2, provider/MCP live opt-in2. Worker skip PostgreSQL migration:
`GAIA_TEST_POSTGRES_URL` non disponibile. Skip non equivale a PASS.

## Coverage

| Runtime modificato | Statements | Branches | Gate |
| --- | ---: | ---: | --- |
| Presenze giornaliere | 1186/1186 | 1336/1336 | 100% PASS |
| Settings | 477/477 | 658/658 | 100% PASS |
| Network traffic | 276/276 | 92/92 | 100% PASS |
| Wiki conversation_metrics | 265/265 | 102/102 | 100% PASS |
| Catasto GIS page | 587/587 | 613/613 | 100% PASS |
| GIS excel-references | 9/9 | 4/4 | 100% PASS |

Misura full-file, non solo righe cambiate. Nessun test rimosso/indebolito,
nessuna nuova exclusion. Worker runtime invariato ha coverage globale99,8573%
combinata nel gate disponibile: non dichiarato100%. La suite completa non
dimostra100% dell'intero backend/frontend; il claim riguarda soltanto i runtime
modificati, come verificato dai JSON e dall'identità byte delle sorgenti integrate.

## Ratchet

Ogni cherry-pick runtime e test-only è stato seguito da ratchet completo contro
main55a: **PASS, zero finding nuovi**. Controllo read-only, baseline del merge-base.
Nessun cambio BASE_REF opportunistico. Gate conclusivo nel report verifier.

## Global baseline status

`complexity-check` rimane **FAIL per le30 divergenze storiche** già classificate.
Non è il gate differenziale della change. Nessuna `complexity-baseline`,
`baseline-repair` o equivalente è stata eseguita. Baseline, soglie, scope,
eccezioni e tooling sono byte-identici rispetto al merge-base.

## Improved slices

- P1: duplicazione reale card giornaliere/collaboratore consolidata in presenter
  locali di dominio; stato, effetti e comandi invariati.
- P6: una sola implementazione del mapping verifica SISTER, mantenendo fallback
  diversi della lista e dei due alias; nessuna variazione HTTP/WebSocket.
- B4: quattro conversioni byte identiche sostituite da helper puro5LOC;
  conversione/clamp/eccezioni e ordine dei lookup preservati.
- B5: guard eventi elimina un livello di nesting; ramo ranking identico
  consolidato. Arrotondamenti/import conformi Ruff, semantica protetta da test.
- C2: lookup alias Excel tipizzato consolidato; fallback nullish, ordine colonne,
  massimo5000righe e indice+2 invariati. Aggregata page+helper cognitive621→574,
  cyclomatic712→663; nessuna nuova violation nei tre piccoli callable helper.

## Reorganized slices

Nessun runtime accettato viene classificato come semplice riorganizzazione.
P2/P3/P4/P5 sono `NO_CHANGE` sul runtime e characterization significativa,
non una riduzione numerica rivendicata.

## Blocked slices

| Candidate | Evidence / motivo | Azione richiesta |
| --- | --- | --- |
| P2 Capacitas | 35,58% statement / 28,31% branch | Coprire wizard/configurazione/results prima di runtime |
| P3 fuel analytics | 87,21% statement / 76,20% branch full-file | Characterization dei percorsi mancanti e domini correlati |
| P4 Catasto anomalie | 59,09% statement / 40,46% branch | Wizard/ADE/dialog mutation flows |
| P5 Utenze detail | 36,28% statement / 37,54% branch | Documenti/upload/NAS/classificazione/pagamenti |
| B1 Ruolo tributi | Working tree concurrent nel file assegnabile | Concordare ownership dopo chiusura lavoro concorrente |
| B3 Terreni readiness | 130 test PASS; 76,98% statement / 62,95% branch | Characterization residua prima di orchestrazione |
| B6 Bonifica readiness | 14 test PASS; 34,34% statement / 28,13% branch | Side-effect/retry/commit/rollback prima del refactor |
| C1 ADE WFS readiness | 8 test PostGIS SKIPPED; 20,15% statement / 0% branch | Provisioning PostGIS e characterization delle sorgenti reali |
| Wave4 runtime e altri percorsi Wave3 | Non implementati nel freeze verificato | Readiness e nuova singola slice dopo review |

Le worktree readiness B3/B6 non producono cambi applicativi; i loro numeri sono
misure delle suite indicate, non un giudizio su tutta la coverage repository.

## Regressions rejected

Nessuna slice `REGRESSED` è integrata. P1 aveva una regressione callback params
nel primo tentativo: ratchet FAIL; contratto callback corretto e ratchet PASS,
senza ignore/baseline change. B5 primo tentativo compattava assignment in un int
booleano: rifiutato in review Coordinator, mantenuto l'if esplicito.
Tentativi intermedi non sono risultati accettati.

## Remaining top 30 hotspot

Ranking riproducibile dalla scansione finale, cognitive discendente.
L'audit finale non esclude worker test per far sparire divergenze.

| # | Callable | Cognitive | Cyclomatic | LOC | Path |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | PresenzeGiornalierePage | 525 | 432 | 2194 | `frontend/src/app/presenze/giornaliere/page.tsx` |
| 2 | ElaborazioniCapacitasWorkspace | 472 | 416 | 2631 | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` |
| 3 | DetailContent | 391 | 304 | 1908 | `frontend/src/app/utenze/[id]/page.tsx` |
| 4 | CatastoAnomaliePageContent | 390 | 342 | 2109 | `frontend/src/app/catasto/anomalie/page.tsx` |
| 5 | ElaborazioniSettingsWorkspace | 366 | 316 | 1527 | `frontend/src/components/elaborazioni/settings-workspace.tsx` |
| 6 | fuel_analytics | 366 | 208 | 402 | `backend/app/modules/operazioni/routes/analytics.py` |
| 7 | anomalies_analytics | 365 | 160 | 388 | `backend/app/modules/operazioni/routes/analytics.py` |
| 8 | CatastoGisPage | 317 | 281 | 1889 | `frontend/src/app/catasto/gis/page.tsx` |
| 9 | MePageContent | 271 | 256 | 1133 | `frontend/src/app/me/me-page-content.tsx` |
| 10 | _run_bonifica_sync_background | 269 | 47 | 232 | `backend/app/services/elaborazioni_bonifica_sync.py` |
| 11 | ElaborazioniBonificaSyncWorkspace | 259 | 202 | 835 | `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx` |
| 12 | MapContainer | 246 | 169 | 953 | `frontend/src/components/catasto/gis/MapContainer.tsx` |
| 13 | PresenzeCollaboratoreDetailPage | 233 | 212 | 1600 | `frontend/src/app/presenze/collaboratori/[id]/page.tsx` |
| 14 | ElaborazioneBatchDetailWorkspace | 216 | 177 | 751 | `frontend/src/components/elaborazioni/batch-detail-workspace.tsx` |
| 15 | PresenzeExportPage | 209 | 172 | 1097 | `frontend/src/app/presenze/export/page.tsx` |
| 16 | sync_from_whitecompany | 205 | 77 | 290 | `backend/app/modules/organigramma/services/whitecompany_sync.py` |
| 17 | RuoloTributiPageContent | 204 | 173 | 1064 | `frontend/src/app/ruolo/tributi/page.tsx` |
| 18 | run_network_scan | 195 | 101 | 267 | `backend/app/modules/network/services.py` |
| 19 | UtenzeSubjectsSection | 184 | 169 | 991 | `frontend/src/components/utenze/utenze-subjects-section.tsx` |
| 20 | TrackingContent | 183 | 159 | 913 | `frontend/src/app/network/tracking/page.tsx` |
| 21 | AnagraficaBulkPanel | 181 | 155 | 839 | `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx` |
| 22 | _build_network_statistics_summary | 181 | 101 | 214 | `backend/app/modules/network/router/helpers/traffic.py` |
| 23 | refresh_wiki_conversation_daily_metrics | 178 | 49 | 153 | `backend/app/modules/wiki/services/conversation_metrics.py` |
| 24 | CatastoImportPage | 175 | 149 | 1114 | `frontend/src/app/catasto/import/page.tsx` |
| 25 | ImportContent | 173 | 160 | 971 | `frontend/src/app/utenze/import/page.tsx` |
| 26 | RuoloDashboardPage | 168 | 157 | 1147 | `frontend/src/app/ruolo/page.tsx` |
| 27 | OrganigrammaWorkspace | 167 | 147 | 1086 | `frontend/src/features/organigramma/organigramma-workspace.tsx` |
| 28 | WikiRequestsPage | 166 | 132 | 759 | `frontend/src/features/wiki/WikiRequestsPage.tsx` |
| 29 | GaiaUsersPage | 162 | 146 | 1011 | `frontend/src/app/gaia/users/page.tsx` |
| 30 | PresenzeConfigurazionePage | 158 | 148 | 1135 | `frontend/src/app/presenze/configurazione/page.tsx` |

## Architectural changes

Confini locali, non ridisegno globale: due presenter Presenze e mapper Settings
privati nello stesso file; parser byte privato Network; guard e deduplication
nel servizio Wiki; modulo puro GIS `excel-references.ts` di28LOC effettive.
Nessun mega-context, nuovo framework, relocation legacy,
microservizio, API, schema DB, auth, transazione o componente shared modificato.
FastAPI unico, Next.js unico, PostgreSQL unico restano l'architettura.

Graphify code aggiornato tramite target frontend, Network, Wiki e Catasto nei corpus
corretti; grafi non committati e non usati come prova delle metriche.
Refresh documentazione piattaforma verificato separatamente per risultati parziali.
Primo refresh piattaforma PASS: `chunk10/10 done`, nessun semantic-chunk failure,
233 nodi/225 edge/55 community; token989329 input/37011 output, costo stimato
Graphify$0,4549. Modello `gpt-reserve`, API locale caricata senza esporre credenziali.
Refresh piattaforma conclusivo PASS: `chunk2/2 done`, nessun semantic-chunk failure,
131file cached/20riestratti, 262nodi/247edge/63community; token148799input/4863output,
costo stimato$0,0673. Evidenza `/tmp/gaia-campaign-graphify-platform-docs-final.log`.

## Risks

- Otto callable >300 restano: la campagna locale non raggiunge il target strategico.
- P1 principale525, Settings366, Network181 e Wiki178 sono ancora hotspot.
- Test SQLite/mocked boundary non certificano produzione PostgreSQL/PostGIS,
  portali INAZ/SISTER/GATE, browser automation reali o provider esterni.
- E2E paralleli hanno mostrato instabilità: gate seriale passa senza cambiare
  i test, ma restano due failure da triage separato prima di pretendere stabilità.
- Artefatti `/tmp` e dipendenze symlink sono locali/effimeri; i report versionati
  conservano comandi e risultati, non credenziali o un ambiente portabile.
- Integration non include sviluppo concorrente main: una futura integrazione
  con quel lavoro richiede nuova review, test e ratchet, non cherry-pick cieco.

## Recommended next campaign

1. Chiudere i gap full-file dei quattro mega-hotspot con characterization reale,
   una responsabilità e un owner per volta; non indebolire la policy100%.
2. Prima nuova slice: Presenze filter/selection o Capacitas batch controller,
   preservando le transizioni React e misurando aggregati anti-laundering.
3. Fuel analytics: proteggere query/filter/response ordering, poi isolare una
   sola aggregazione. Non attaccare contemporaneamente anomalies_analytics.
4. Bonifica: proteggere ordine external side effect, retry, DB commit/rollback e
   progress/status prima di intervenire sul nesting13.
5. Trattare separatamente le15 regressioni runtime storiche della provenance.
   Nessun riallineamento baseline per renderle invisibili.
6. Valutare ADE/GIS e worker solo sulla readiness misurata; non aprire tutti i
   domini per eliminare warning minori mentre la coda >300 resta.

La consegna è una branch revisionabile con cinque refactor reali e prerequisiti
test-only, non la dichiarazione che l'intera complessità di GAIA sia risolta.

## Chiusura e riproduzione

Gate delle slice e suite disponibili verdi; zero nuove regressioni nel ratchet.
Restano il target P1 e la riduzione strategica della coda estrema: **non raggiunti**.
Nessuna equivalenza di produzione/live dedotta dalla sola coverage o dagli skip.
La main resta allo snapshot55a con tutto il lavoro concorrente preservato.

Comandi di scansione dalla worktree integration:

```bash
make complexity-report REPORT_JSON=/tmp/gaia-complexity-final.json \
  REPORT_MD=/tmp/gaia-complexity-final.md
make complexity-ratchet BASE_REF=main
make complexity-check
make quality-test
```

Comando backend finale dalla directory `backend/`:

```bash
APP_ENV=test DATABASE_URL=sqlite:////tmp/gaia-campaign-backend-final-corrected2.db \
  .venv/bin/python -m pytest -q -o addopts='' \
  -o cache_dir=/tmp/gaia-campaign-backend-final-corrected2-cache --tb=short
```

Comandi frontend finali dalla directory `frontend/`:

```bash
npm test
npm run test:unit -- --maxWorkers=2
npm run typecheck
npm run lint
npm run build:clean
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 npm run test:e2e \
  -- --config=/tmp/gaia-campaign-playwright.config.ts --workers=1
```

L'ultimo comando richiede lo stack isolato ricreato e credenziali sintetiche
fornite tramite ambiente, non gli account di produzione. Backend montato read-only,
DB/storage tmpfs, rete Docker internal, nessuna .env di produzione o volume DB.
Output verificato della connessione esterna errno101: nessun accesso portali.

Worker completo dalla root integration:

```bash
APP_ENV=test DATABASE_URL=sqlite:////tmp/gaia-campaign-worker-final3.db \
  JWT_SECRET_KEY='<synthetic-test-key>' PYTHONPATH="$PWD" make test-worker \
  WORKER_COVERAGE_JSON=/tmp/gaia-campaign-worker-final-coverage.json \
  WORKER_COVERAGE_XML=/tmp/gaia-campaign-worker-final-coverage.xml
```

Report indipendente: `FINAL_VERIFICATION_2026-10-08.md`, commit `800e597a`.
Report readiness: `WAVE3_READINESS_2026-10-08.md`,
`WAVE3_GIS_READINESS_2026-10-08.md`, `WAVE4_READINESS_2026-10-08.md`.
I report slice forniscono comandi coverage, matrice comportamenti e rischi residui.
I servizi E2E creati dalla campagna vengono fermati/rimossi alla consegna;
le worktree e branch revisionabili vengono conservate. Nessun servizio concorrente
o artefatto preesistente viene rimosso.
Cleanup verificato: entrambi i container `gaia-complexity-e2e-*-20261008`,
la rete internal della campagna e il relativo processo Next sono rimossi/fermati;
porte8080/13000 libere, file ambiente sintetico eliminato. I servizi concorrenti
release e gate-quality rimangono attivi. Working tree integration pulito alla
consegna; root registry sincronizzato senza alterare le modifiche altrui.
