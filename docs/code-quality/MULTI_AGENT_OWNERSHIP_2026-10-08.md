# GAIA — Campaign ownership 2026-10-08

Coordinator: Codex root. Snapshot/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Audit: `reports/code-quality/COMPLEXITY_AUDIT_2026-10-08.md`.
Il checkout main contiene lavoro concorrente Presenze/Ruolo/Elaborazioni:
nessun reset, copia automatica o commit di quel lavoro nello swarm.
Integrazione su branch dedicata; main non viene spostato durante la campagna.
Baseline, soglie, esclusioni e tooling complexity sono read-only.

## Ownership attiva e sequenza

### Capacitas characterization continuation — runtime held

Previous goal turn produced integrated R3 evidence and plans, not completion.
R3 backend6608PASS449skip, frontend4099PASS, worker778PASS1skip; browser
confirmation52PASS7skip after initial GISFAIL. UNKNOWN residual-risk decision
still pending. This continuation authorizes only test-only characterization,
not another runtime wave, baseline absorption or implicit GIS risk acceptance.
New worktrees from39dbcc40; all runtime read-only, owners exclusive new specs.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| C0 (capacitas_ui) | Capacitas UI tests | frontend/tests/unit/campaign-capacitas-credentials.test.tsx; reports/code-quality/SLICE_CAPACITAS_C0_2026-10-08.md | Source14615c27;17new/36combinedPASS, ratchet0; coverage100FAIL, runtime unchanged | GAIA-campaign-20261008-c0-tests | refactor/complexity-capacitas-credentials-tests | READY_FOR_REVIEW |
| C6 (analytics) | Capacitas UI tests | frontend/tests/unit/campaign-capacitas-certificati.test.tsx; reports/code-quality/SLICE_CAPACITAS_C6_2026-10-08.md | Commit7bc9ec17;11new/30combinedPASS, ratchet0; coverage100 remainsFAIL, runtime unchanged | GAIA-campaign-20261008-c6-tests | refactor/complexity-capacitas-certificati-tests | READY_FOR_REVIEW |
| C7 (integration_r3) | Capacitas UI tests | frontend/tests/unit/campaign-capacitas-anomalie.test.tsx; reports/code-quality/SLICE_CAPACITAS_C7_2026-10-08.md | Sourcebc312caf;20new/39combinedPASS, ratchet0; coverage100FAIL, runtime unchanged | GAIA-campaign-20261008-c7-tests | refactor/complexity-capacitas-anomalie-tests | READY_FOR_REVIEW |
| Characterization Integration (characterization_integration) | Integration | reports/code-quality/INTEGRATION_CAPACITAS_CHARACTERIZATION_2026-10-08.md; approved test-only cherry-picks only | Independently review C6 first, then C0/C7 exact READY commits; preserve frozen runtime and remeasure cumulative coverage honestly | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |

No owner writes the common capacitas runtime or existing batch tests, fixtures,
smoke/config/tooling/shared files. Isolated API mocks in new specs are test
boundaries, not runtime duplication. A slice stops after its behavioral matrix,
test PASS and honest full-file coverage evidence (expected FAIL100 until all
sections are characterized). No full-suite/build/E2E re-run per micro-slice.
Source commits authorized for coherent test-only slices; integration only
after independent review/ratchet, one cherry-pick at a time. Runtime complexity
must stay identical; classification NO_CHANGE, not IMPROVED. Never fake branch
coverage with private closures, malformed impossible mocks or ignore additions.

Coordinator also owns `reports/code-quality/GIS_BROWSER_CAUSALITY_2026-10-08.md`
for read-only diagnosis of the unresolved browser gate. Disposable offline
MapLibre reproduction artifacts are allowed in `/tmp` only, no production or
committed runtime/test modifications; results must distinguish demonstrated
library behavior from unobserved state in the original failing application.

### Continuazione del goal globale (Round 2)

Il goal dell'allegato e49b8632 resta ACTIVE: il checkpoint iniziale con cinque
slice non completa la missione globale. Runtime di partenza R2:
`5a56f05cbd41e92cae247d8a4b25376a173ed36a`; merge-base main55a invariato.
Misura attuale1944error/2751warning,8callable>300,17>200. Si mantengono tutti
i vincoli, inclusi full-file100%, equivalenza, ratchet e baseline read-only.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R2 Coordinator | Governance | Registry, PROGRESS, rapporto cumulativo e checkpoint globale | Riapertura e mantenimento goal originale | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R2 P1 (r2_presenze) | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; helper nuovi privati nella stessa directory; test giornaliere esclusivi; SLICE_R2_P1_2026-10-08.md | Monthly selection dedup: integrated87efd9bb,375tests/full-file100/ratchet0 | GAIA-campaign-20261008-r2-presenze | refactor/complexity-r2-presenze-model | MERGED |
| R2 P6 (capacitas_ui) | Settings UI | frontend/src/components/elaborazioni/settings-workspace.tsx; helper/component privati elaborazioni; test settings esclusivi; SLICE_R2_P6_2026-10-08.md | Provider summaries dedup: integrated3f9863fb,119tests/full-file100/ratchet0 | GAIA-campaign-20261008-r2-settings | refactor/complexity-r2-settings-provider | MERGED |
| R2 P3 (analytics) | Operazioni analytics | backend/app/modules/operazioni/routes/analytics.py; test_operazioni_analytics_characterization.py e nuovo test r2 esclusivo; SLICE_R2_P3_2026-10-08.md | Invariant guards prerequisite integrated bf4c9a26;79cases/full-file100/lint/ratchet0 | GAIA-campaign-20261008-r2-analytics | refactor/complexity-r2-fuel-analytics | MERGED |
| R2 Integration (baseline) | Integration | reports/code-quality/INTEGRATION_ROUND2_2026-10-08.md; integration runtime only through approved cherry-pick | P1/P6 review and independent gate green; report59fa4e42, P3 not included | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R2 Browser verification (capacitas_ui) | Verification | reports/code-quality/ROUND2_BROWSER_VERIFICATION_2026-10-08.md; temporary isolated Docker/Next/browser artifacts only | 52PASS7skip0flaky; report40171b07, resources cleaned | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R2 P3 Integration (baseline) | Integration | reports/code-quality/INTEGRATION_R2_P3_2026-10-08.md; reviewed analytics cherry-pick only | Independent proof/style review and79tests/full-file100/ratchet0;report65097ce2 | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R3 P1 (r2_presenze) | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; new private monthly model helper; giornaliere tests; SLICE_R3_P1_2026-10-08.md | Monthly model471935ec integratedfbd4172d; independent388PASS/full-file100/ratchet0 | GAIA-campaign-20261008-r3-presenze | refactor/complexity-r3-presenze-monthly-model | MERGED |
| R3 P6 (capacitas_ui) | Settings UI | frontend/src/components/elaborazioni/settings-workspace.tsx; private provider commands helper; settings tests; frontend/tests/smoke.test.mjs; SLICE_R3_P6_2026-10-08.md | Commands82ec7533 integratedb0dd9228; independent131unit/18smokePASS/full-file100/ratchet0; authorized smoke contract checks preserved | GAIA-campaign-20261008-r3-settings | refactor/complexity-r3-settings-commands | MERGED |
| R3 P3 (analytics) | Operazioni fuel | backend/app/modules/operazioni/routes/analytics.py; backend/app/modules/operazioni/routes/_fuel_vehicle_metrics.py; backend/tests/test_operazioni_fuel_vehicle_r3.py; SLICE_R3_P3_2026-10-08.md | Vehicle computation399825ab integrated0b1a0d37 after freeze release; independent98PASS/full-file100/ratchet0 | GAIA-campaign-20261008-r3-analytics | refactor/complexity-r3-fuel-vehicle-model | MERGED |
| R3 Integration (integration_r3) | Integration | reports/code-quality/INTEGRATION_ROUND3_2026-10-08.md; approved slice cherry-picks only | Sequential review and617PASS/full-file100/ratchet0; report8c4e8c40+c7d79229, runtime frozen0b1a0d37 | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |

Ownership R1 conclusa: gli owner delle righe storiche non scrivono i percorsi R2.

### Pianificazione successiva, nessuna autorizzazione runtime prima del checkpoint

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R4 planning (r2_presenze) | Presenze UI | Runtime R3 read-only; reports/code-quality/PLAN_R4_P1_2026-10-08.md esclusivo | Proposta di una responsabilità mensile residua, invarianti e stima anti-laundering; nessun runtime/test edit o integrazione | GAIA-campaign-20261008-r3-presenze | refactor/complexity-r3-presenze-monthly-model | PLANNED |
| R4 planning (capacitas_ui) | Catasto GIS UI | Runtime GIS R1 read-only; reports/code-quality/PLAN_R4_C2_2026-10-08.md esclusivo | Proposta di una responsabilità reale che riduca il principal317 e il debito aggregato; nessun MapContainer censurato, runtime/test edit o integrazione | GAIA-campaign-20261008-gis-readiness | refactor/complexity-gis-readiness | PLANNED |
| R3 Final Verification (analytics, Coordinator final suite sync) | Verification | reports/code-quality/ROUND3_VERIFICATION_2026-10-08.md; runtime and protected files read-only | Report0f7ab9d8+a14e9a78; backend6608PASS449skip, all executed gates recorded, GISUNKNOWN residual-risk decision pending | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R3 Browser Verification (capacitas_ui) | Verification | reports/code-quality/ROUND3_BROWSER_VERIFICATION_2026-10-08.md; own disposable resources only, all repository runtime/tests/config read-only | Reportaee8a737 integrated; initial51PASS7skip1FAIL, confirmation52PASS7skip; resources cleaned, UNKNOWN GIS risk decision pending | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R4 planning (integration_r3) | Operazioni fuel | R3 analytics runtime/tests read-only; reports/code-quality/PLAN_R4_P3_2026-10-08.md exclusively | Propose one remaining fuel computational aggregation responsibility with actual decision deduplication, not neutral relocation; no runtime/test edit or integration | GAIA-campaign-20261008-r3-analytics | refactor/complexity-r3-fuel-vehicle-model | PLANNED |
| Extreme readiness planning (capacitas_ui) | Capacitas UI | Runtime/tests read-only; reports/code-quality/PLAN_CAPACITAS_COVERAGE_2026-10-08.md exclusively | Identify concrete legitimate full-file coverage closure work for472 principal from existing branch/test evidence; no runtime/test edits | GAIA-campaign-20261008-capacitas | refactor/complexity-capacitas-ui | PLANNED |

Round2 runtime integrated and independently GREEN at65097ce2: P1/P6/P3
ratchet PASS0, 573 focused tests PASS, five modified R2 runtime full-file100%.
R2 frontend4074PASS/buildPASS/browser52PASS7skip; complete backend suite is
running on frozen bf4c9a26 runtime. R3 worktrees branch from65097ce2 and may
implement/test privately; no new backend integration until that frozen suite
has finished and its evidence is recorded. Every R3 agent stops after one
reviewable slice; no continuation based merely on a lower main-callable score.

P3 prerequisite review: 79 real-database characterization cases PASS and
runtime full-file670/670 statement310/310 branch after invariant guard cleanup.
Coordinator authorizes minimal Ruff closure in this same owned file because
CODE_STYLE requires full-file lint for modified Python: local renames/import
cleanup, UTC alias, redundant parentheses/f-string/cast only when equivalent,
loop-closure binding preserving synchronous sorting, en-dash escaped without
changing response text. No ignore, broad format, new feature or aggregation
refactor. Stop and reject runtime on behavioral ambiguity or ratchet regression.
Integration e Final Verification vengono assegnati dopo slice READY_FOR_REVIEW,
non scrivono nei file runtime degli agenti attivi. Stop per singola unità,
non un falso completamento del goal globale. Nessuna nuova delega shared.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Governance | Questo registro, progress e report finale | Sequencing e gate conclusi; main preservata | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| BASELINE | Provenance | reports/code-quality/BASELINE_PROVENANCE_2026-10-08.md | 30 divergenze; sorgenti read-only | GAIA-campaign-20261008-baseline | refactor/complexity-baseline-provenance | MERGED |
| P1 | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; helper locali nuovi e test Presenze esclusivi | Consolidamento card anomalie; target estremo residuo | GAIA-campaign-20261008-presenze | refactor/complexity-presenze-ui | MERGED |
| P2 | Capacitas UI | frontend/src/components/elaborazioni/capacitas-workspace.tsx; helper locali nuovi e test Capacitas esclusivi | Controller/modello batch coerente | GAIA-campaign-20261008-capacitas | refactor/complexity-capacitas-ui | BLOCKED |
| P3 | Operazioni | backend/app/modules/operazioni/routes/analytics.py; helper analytics locali nuovi; backend/tests/test_operazioni_analytics.py e test nuovi esclusivi | fuel_analytics aggregazione; poi anomalies soltanto dopo gate | GAIA-campaign-20261008-analytics | refactor/complexity-operazioni-analytics | BLOCKED |
| P4 | Catasto UI | frontend/src/app/catasto/anomalie/page.tsx; helper locali nuovi e test anomalie esclusivi | Runtime BLOCKED_COVERAGE; test-only pronto | GAIA-campaign-20261008-catasto-ui | refactor/complexity-catasto-anomalie-ui | BLOCKED |
| P5 | Utenze UI | frontend/src/app/utenze/[id]/page.tsx; helper locali nuovi e test detail esclusivi | Runtime BLOCKED_COVERAGE; test-only pronto | GAIA-campaign-20261008-utenze-ui | refactor/complexity-utenze-detail-ui | BLOCKED |
| P6 | Elaborazioni UI | frontend/src/components/elaborazioni/settings-workspace.tsx; helper locali nuovi e test settings esclusivi | Consolidamento credenziali HTTP/WebSocket | GAIA-campaign-20261008-settings-ui | refactor/complexity-elaborazioni-settings-ui | MERGED |
| INTEGRATION (baseline, poi capacitas_ui per C2) | Integration | Branch integration, report integration esclusivo; runtime read-only per review | Cinque slice runtime e test-only integrati, overlap zero | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| FINAL | Verification | reports/code-quality/FINAL_VERIFICATION_2026-10-08.md; runtime read-only | Suite finali PASS con skip dichiarati; ratchet0/globalcheck30storici | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| B4 | Network | backend/app/modules/network/router/helpers/traffic.py; backend/tests/test_network_traffic_campaign.py | Statistiche: normalizzazione bytes; integrazione verificata nel checkpoint | GAIA-campaign-20261008-network | refactor/complexity-network-statistics | MERGED |
| B5 | Wiki | backend/app/modules/wiki/services/conversation_metrics.py; backend/tests/test_wiki_metrics_campaign.py | Refresh eventi/ranking: integrazione verificata, full-file 100%, cognitive -37 | GAIA-campaign-20261008-wiki | refactor/complexity-wiki-metrics | MERGED |
| B3 readiness | Capacitas Terreni | backend/app/services/elaborazioni_capacitas_terreni.py read-only | 130 test; coverage 76,98% statement / 62,95% branch, runtime non autorizzato | GAIA-campaign-20261008-terreni | refactor/complexity-capacitas-terreni | BLOCKED |
| B6 readiness | Bonifica | backend/app/services/elaborazioni_bonifica_sync.py read-only | 14 test; coverage 34,34% statement / 28,13% branch, runtime non autorizzato | GAIA-campaign-20261008-bonifica | refactor/complexity-bonifica-orchestration | BLOCKED |
| C1 readiness | Catasto backend | backend/app/modules/catasto/services/ade_wfs.py read-only; reports/code-quality/WAVE3_READINESS_2026-10-08.md | ADE WFS BLOCKED_COVERAGE: 8 skip PostGIS | GAIA-campaign-20261008-catasto-backend | refactor/complexity-catasto-ade-readiness | BLOCKED |
| C2 | GIS frontend | frontend/src/app/catasto/gis/page.tsx; excel-references.ts locale; test GIS esclusivi; reports/code-quality/SLICE_C2_2026-10-08.md | Normalizzazione Excel: page334→317, aggregata621→574, full-file100% | GAIA-campaign-20261008-gis-readiness | refactor/complexity-gis-readiness | MERGED |
| W4 readiness | Worker/altri domini | reports/code-quality/WAVE4_READINESS_2026-10-08.md; runtime read-only | Report-only integrato; cinque candidati worker100%, altri NOT_MEASURED | GAIA-campaign-20261008-catasto-backend | refactor/complexity-catasto-ade-readiness | MERGED |

Capacità disponibile: quattro agenti inclusa root. BASELINE parte prima;
gli agenti successivi sono avviati in batch, massimo tre child simultanei.
INTEGRATION e FINAL usano la stessa branch in momenti diversi, mai due owner
scriventi sugli stessi percorsi. Ogni agent ha report esclusivo in
`reports/code-quality/SLICE_<AGENT>_2026-10-08.md`.
Modifiche a lib/hooks/UI/layout condivisi richiedono ownership esplicita del
Coordinator. Nessun agente modifica PROGRESS o baseline condivise.
Copertura full-file statement/branch 100% obbligatoria per runtime toccati:
un candidato privo di questo gate resta BLOCKED/REJECTED, non viene integrato.

## Planning wave successive

Wave 2: Ruolo tributi/repositories, Capacitas Terreni, Network scan/statistiche,
Wiki orchestrator/metriche, Bonifica orchestration. Una responsabilità per
slice, agenti aggiunti al registro prima dello spawn. Tributi è inizialmente
BLOCKED_BY_CONCURRENT_WORK nel checkout principale.
Wave 3: Catasto backend (ADE WFS, matching, GIS, anomalie/import), frontend GIS,
GIS condiviso; ownership distinte. Wave 4: altri domini soltanto dopo checkpoint
di integrazione verde e sulla base del ranking aggiornato.

## File priority list considerata

| Path | Planning |
| --- | --- |
| backend/app/modules/ruolo/tributi_repositories.py | W2 B1; concurrent, non assegnato runtime |
| backend/app/services/elaborazioni_capacitas_terreni.py | W2 B3 |
| frontend/src/app/presenze/giornaliere/page.tsx | W1 P1 |
| backend/app/modules/ruolo/repositories.py | W2 B2 |
| frontend/src/features/organigramma/organigramma-workspace.tsx | W4 |
| frontend/src/components/elaborazioni/capacitas-workspace.tsx | W1 P2 |
| backend/app/modules/operazioni/routes/mobile_sync.py | W4; contract skill obbligatoria |
| frontend/src/app/operazioni/analisi/page.tsx | W4 |
| backend/app/services/elaborazioni_capacitas_incass.py | W2 follow-up separato |
| backend/app/modules/gis/services.py | W3 GIS backend |
| backend/app/modules/operazioni/routes/analytics.py | W1 P3 |
| frontend/src/app/ruolo/tributi/page.tsx | W4 |
| backend/app/modules/network/services.py | W2 B4 |
| frontend/src/components/catasto/gis/MapContainer.tsx | W3 GIS frontend |
| backend/app/modules/utenze/services/import_service.py | W4 |
| backend/app/modules/catasto/services/ade_wfs.py | W3 |
| backend/app/modules/riordino/services/block_service.py | W4 |
| backend/app/modules/utenze/anpr/service.py | W4 |
| backend/app/modules/catasto/routes/anagrafica/matching.py | W3 |
| backend/app/modules/catasto/services/gis_service.py | W3 |
| frontend/src/app/catasto/anomalie/page.tsx | W1 P4 |
| backend/app/modules/catasto/routes/anomalie.py | W3 |
| backend/app/modules/catasto/routes/import_routes.py | W3 |
| frontend/src/components/elaborazioni/settings-workspace.tsx | W1 P6 |
| frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx | W4 |
| frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx | W3 |
| backend/app/modules/operazioni/services/import_fleet_transactions.py | W4 |
| backend/app/modules/wiki/services/orchestrator.py | W2 B5 |
| backend/app/services/gate_mobile_sync.py | W4; concurrent domain e contract |
| modules/elaborazioni/worker/browser_session.py | W4 worker |

## Checkpoint iniziale

HEAD e merge-base main coincidono con lo snapshot richiesto. I runtime W1 non
risultano modificati nei working tree locali al preflight. Branch storiche
esistenti non vengono riutilizzate né integrate. Commit e merge sono autorizzati
dal brief corrente, esclusivamente nelle worktree/branch dello swarm.

## Decisioni slice iniziali

Chiusura: cinque slice runtime IMPROVED, sei file runtime full-file100%,
ratchet finale PASS0. Error1956→1944/warning2758→2751; cognitive-264,
cyclomatic-174. Backend6560PASS449skip, frontend4059PASS, worker778PASS1skip,
E2E52PASS7skip. Nessuna ulteriore ownership runtime attiva. Gli stati BLOCKED
si riferiscono al refactoring runtime, anche quando characterization/report
sono già integrati. Il target strategico della coda estrema resta aperto.

- P1: characterization esistente full-file 100% PASS. Prima slice approvata:
  consolidamento duplicazione card anomalie nelle due viste, presenter sotto
  soglia e riduzione aggregata reale. Non dichiarare raggiunto il target -50%
  con una singola slice più piccola; ulteriori slice solo dopo gate verde.
- P3: worktree preparata; prima suite analytics/coverage avviata dal Coordinator.
  Ownership temporanea Coordinator fino al passaggio esplicito all'agent P3.
- P6: readiness coverage delle tre suite settings/modal in corso dal Coordinator;
  nessuna modifica runtime prima del gate di caratterizzazione.
- P6: readiness PASS, full-file statement472/branch682/function126/line418 al100%.
- P3: readiness analytics 30 PASS, coverage full-file66,08% combinata,
  statement494/688 e branch180/332; servono test aggiuntivi prima dell'integrazione.
- P2: NO_CHANGE/BLOCKED_COVERAGE; runtime invariato. Commit60d44529 conserva
  19test nuovi significativi; coverage workspace35,58%statement/28,31%branch.
- P4: suite utility esistente non importa la pagina: coverage pagina0%.
  Agent P2 riassegnato a P4 per UI characterization; runtime solo con full-file100%.
- P3: commit48de12ef test-only; 50PASS e full-file600/688statement253/332branch.
  Gate100%FAILesplicito; runtime invariato, non integrabile come refactor.
- Provenance preliminare: 30 valori baseline corrispondono alla sorgente storica;
  regressioni metriche runtime e divergenze test introdotte in commit successivi,
  non dal lavoro corrente. Il report BASELINE conserva commit e dettagli.
- Symlink dipendenze dei worktree esclusi tramite git common info/exclude locale,
  non una exclusion dello scanner o una modifica versionata. Evita che il diff
  tenti di leggere directory come file nei gate.
- Checkpoint P1/P6 GREEN: 479 test e coverage full-file 100%; cognitive aggregata
  -155, cyclomatic -111. Target estremo P1 non raggiunto, nessun claim -50%.
- P4 e P5 test-only pronti alla review; coverage pagina rispettivamente
  59,09%/40,46% e 36,28%/37,54% statement/branch. Runtime invariati.
- B4 assegnato dopo checkpoint GREEN. La suite traffico raggiunge 283/283
  statement e 92/92 branch con 19 test; autorizzata una slice di normalizzazione
  locale, non il refactor monolitico di run_network_scan.
- Follow-up integration test-only: P3 `5efac219`, P4 `a205a508`, P5 `71b817b9`
  cherry-picked dopo review; ratchet PASS0 dopo ciascuno. Test pertinenti
  50/116/21 PASS; runtime dei tre domini invariati e ancora BLOCKED_COVERAGE.
  Nessuna riduzione metrica attribuita alle caratterizzazioni.
