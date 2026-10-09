# R12 Capacitas — integrated complexity checkpoint

## Status and scope

**IMPROVED / CERTIFIED / INTEGRATED.** Global campaign **ACTIVE / INCOMPLETE**.
This is one bounded eight-command lifecycle responsibility, not a feature,
complete module rewrite or global final verification. GIS synchronization failure
was separately fixed and certified; its existing tests run unchanged here.
Optional GIS/provider/PostGIS skips remain unverified, never relabeled PASS.

Author, independent reviewer/integrator and distinct final verifier use separate
branches/worktrees and exclusive writes. Coordinator controls publication/git
custody, sequential integration, closure docs and Graphify. Registry:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R12_CAPACITAS_COMMANDS_2026-10-09.md`.
No overlap, shared-runtime edit, threshold change, ignore or baseline inflation.

## Snapshot and exact sequential integration

Immutable main/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Campaign integration branch: `refactor/complexity-campaign-20261008`.
Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.

| Phase | Published source commit | Integration commit | Actual main55a ratchet |
| --- | --- | --- | --- |
| Original characterization | c11503ea | cf2a95b8 | PASS0 |
| Independent original replay | Frozen review1a9 | ecb4fe51 | PASS0 |
| Runtime + SLICE | 3b511b6d | 673026e7 | PASS0 |
| Independent runtime REVIEW only | 8da06a90 | 29f29497 | PASS0 |
| Distinct final certificate only | bfe0b2d7 | b7e3ff2c | PASS0 |

Each source/review/certificate pick completed only after its predecessor's gate
returned0/findings[]. No incomplete branch import or main merge/push/deployment.
Governance435b4d31 precedes source integration; closure documents are separately
owned Coordinator work. Actual root full AST and all30historical finding objects
match independent certificate, not merely aggregate counts.

| Frozen integrated artifact | SHA256 |
| --- | --- |
| Workspace | b69cbc44b3c219503c940304ce9c1b335faeb7f3703d7569267ba5104bac555d |
| SLICE | 732922515265c90099749dba0aa3e69b93befafb7978f107f81409d33ca962c4 |
| REVIEW | 1308bb1040c49e011135e683cbdb06bafd043d885c56b6212cf85ce085d089f9 |
| VERIFICATION | 8e898848ff9034750359f1f4d05cc3b4f904e54fb9ce86f36c29d90dbf5d146b |
| Baseline | 38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95 |

## Behavioral invariants and architecture

Private typed action/family ports deduplicate actual token/busy/API/success/error/
finally phases. Existing eight names bind original endpoints/setters; rerun awaits
original reload, delete functionally filters current rows. API remains unbound;
no extra async success wrapper/await, component, hook, context, reducer or export.
Missing token, exact IDs/messages, command-versus-refresh auth handling and token
capture remain original. Earlier finally may clear newer busy; late list may
resurrect deleted rows. No race, business rule, polling or authorization fix.

All20tests/config/policy and3507other author tracked paths remain frozen.
36other named functions/component outside8handlers source-exact. New helper
9cognitive/8cyclomatic/24LOC/nesting1/3params is below all warning thresholds.
This is deduplication, not relocation of an above-threshold mega callable.

## Local before / after / delta

| Metric, complete workspace + unchanged fraction policy | R11 before | R12 after | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 391 | 359 | -32 (-8.18%) |
| Principal cyclomatic | 360 | 336 | -24 |
| Principal callable LOC | 2527 | 2487 | -40 |
| Combined cognitive | 926 | 871 | -55 (-5.94%) |
| Combined decisions | 803 | 762 | -41 (-5.11%) |
| Combined raw cyclomatic | 1062 | 1016 | -46 |
| Combined callable LOC | 4677 | 4615 | -62 |
| Combined effective file LOC | 3131 | 3131 | 0 |
| Combined callables | 259 | 254 | -5 |
| Error / warning findings | 17 / 16 | 17 / 16 | 0 / 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |

All nested ancestry and callbacks counted. Workspace3096effectiveLOC unchanged.
Against official initial Capacitas472:359 is -113/-23.94%, not a50% reduction.
Principal still extreme; unchanged finding counts do not negate real structural
deduplication. No eliminated independent-defect count is inferred from findings.

## Global snapshot against official 8 October

| Metric | Official initial | Current integrated | Delta | Delta percent |
| --- | ---: | ---: | ---: | ---: |
| Files | 1665 | 1672 | +7 | +0.42% |
| Callables | 20261 | 20315 | +54 | +0.27% |
| Error | 1956 | 1926 | -30 | -1.53% |
| Warning | 2758 | 2741 | -17 | -0.62% |
| Findings | 4714 | 4667 | -47 | -1.00% |

Application without worker tests:1618files/18994callables/318975effectiveLOC/
4604findings. Official application LOC318856: +119/+0.04%. Snapshot clean-Git/
scope differences remain documented in prior campaign entries; the7October
numbers are not substituted. Findings overlap and are not independent issues.
R12 itself changes no error/warning count; its delta is structural metrics above.

| Domain | Error before | Error after | Warning before | Warning after |
| --- | ---: | ---: | ---: | ---: |
| Backend | 1035 | 1033 | 1688 | 1689 |
| Frontend | 878 | 850 | 881 | 863 |
| Worker runtime | 35 | 35 | 134 | 134 |
| Worker tests | 8 | 8 | 55 | 55 |

## Tests, coverage, attempts and remaining limits

Distinct verifier:80focused/1file,476complete/20specs,4655wholefrontend/306files
PASS, zero unit skip. Do not sum these overlapping execution counts as distinct
tests. Entire modified workspace715statements/798branches/248functions/622lines
and entire policy9/6/6/8 are100%, no missing/skipped counters. Denominator decrease
comes from actual deduplication, not a coverage/config change.

Project and explicit new-spec TypeScript, owned lint0, smoke18 and clean build
PASS. Full lint retains35exact historical warnings. Native browser56cases+real
login, four families14cases each,32overlap timelines,68command requests PASS.
Actual public controls/API/auth/rows checked; disclosed browser virtual clock
drives unchanged real polling, not precise wall-clock certification.

Existing pertinent E2E4PASS; full available E2E54PASS/7historicalSKIP,
61cases/0failure/retry/flaky. Exact skipped identities/reasons in VERIFICATION_R12.
All fresh final gates passed first attempt; startup502readiness probes retained
until200 before browser. Historical rejected+8LOC/ambiguous-identity candidates,
nonmutating patch-header rejection and characterization compiler attempts remain
attributed in earlier reports; no repair/waiver hides them.

All27owned processes terminal; unique stack/ports/network/credentials removed,
3512tracked file hashes intact. Installed dependencies intact except disclosed
ordinary Vitest timing-cache update, retained without restore/reset. No production
write. Fresh full backend/worker suites are NOT certified for this slice and
remain due at global campaign closure.

## Ratchet, baseline provenance and reproducibility

Local change ratchet **PASS0** against immutable main55a after each integration.
Global `make complexity-check` **FAIL30**, makeexit2/scanner1; every complete
finding equals certificate and prior provenance. Historical15runtime regressions
and15worker-test divergences remain visible, not attributed to R12 or absorbed.
No baseline generation/repair/synchronization, threshold/scope/ignore change.
Baseline/tooling/config/package diff versus main remains empty.

Evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r12-capacitas/{author,reviewer,verifier,coordinator}/`.
Fresh Coordinator `integrated-complexity.json/.md`,
`integration-ast-provenance-audit.json`, `integrated-global-check.json/.exit`
and three `integrated-{source,review,certificate}-ratchet.log` files.
Verifier capsule/coverage/JUnit/browser/resource ledger contains exact expanded
commands, versions, full skip objects and failure provenance.

Reproduce from campaign worktree:
`make complexity-report REPORT_JSON=/tmp/gaia-r12.json REPORT_MD=/tmp/gaia-r12.md`;
`make complexity-ratchet BASE_REF=main`; read-only `make complexity-check`.
Frontend: explicit two-file inclusion and20spec coverage command in VERIFICATION;
`npm run test:unit -- --maxWorkers=2`, `npm test`, `npm run build:clean`.
Browser requires isolated synthetic stack, never production fixtures/credentials.

## Graphify and protected concurrent work

Dedicated root frontend force/pruning target PASS,650/650AST files; helper node
present and query follows token dependency.6048nodes/12648edges, HTML skipped
above5000node visualization limit, not AST failure. Author graph is separately
attributed6048/12645; graph cache counts are not complexity or equivalence proof.
Domain/platform documentation uses dedicated Make targets and semantic chunk
verification, not generic extraction from repository root. No graphs committed.

Concurrent main binary diff SHA2569f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b
and status0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87
remain untouched. Dedicated branches/worktrees retained; no reset/stash/pruning.

## Remaining top 30 hotspots

Current tail:5callables>300,17>200,55>100. This remains material global debt.

| Path / callable | Cognitive | Cyclomatic | LOC | Nesting |
| --- | ---: | ---: | ---: | ---: |
| `frontend/src/app/utenze/[id]/page.tsx` — DetailContent | 391 | 304 | 1908 | 2 |
| `frontend/src/app/catasto/anomalie/page.tsx` — CatastoAnomaliePageContent | 390 | 342 | 2109 | 2 |
| `frontend/src/app/presenze/giornaliere/page.tsx` — PresenzeGiornalierePage | 385 | 341 | 2023 | 2 |
| `frontend/src/components/elaborazioni/capacitas-workspace.tsx` — ElaborazioniCapacitasWorkspace | 359 | 336 | 2487 | 2 |
| `frontend/src/app/catasto/gis/page.tsx` — CatastoGisPage | 317 | 281 | 1889 | 4 |
| `backend/app/modules/operazioni/routes/analytics.py` — anomalies_analytics | 298 | 137 | 372 | 4 |
| `frontend/src/components/elaborazioni/settings-workspace.tsx` — ElaborazioniSettingsWorkspace | 296 | 265 | 1358 | 2 |
| `backend/app/modules/operazioni/routes/analytics.py` — fuel_analytics | 282 | 169 | 350 | 4 |
| `frontend/src/app/me/me-page-content.tsx` — MePageContent | 271 | 256 | 1133 | 2 |
| `backend/app/services/elaborazioni_bonifica_sync.py` — _run_bonifica_sync_background | 269 | 47 | 232 | 13 |
| `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx` — ElaborazioniBonificaSyncWorkspace | 259 | 202 | 835 | 4 |
| `frontend/src/components/catasto/gis/MapContainer.tsx` — MapContainer | 246 | 169 | 953 | 3 |
| `frontend/src/app/presenze/collaboratori/[id]/page.tsx` — PresenzeCollaboratoreDetailPage | 233 | 212 | 1600 | 2 |
| `frontend/src/components/elaborazioni/batch-detail-workspace.tsx` — ElaborazioneBatchDetailWorkspace | 216 | 177 | 751 | 3 |
| `frontend/src/app/presenze/export/page.tsx` — PresenzeExportPage | 209 | 172 | 1097 | 3 |
| `backend/app/modules/organigramma/services/whitecompany_sync.py` — sync_from_whitecompany | 205 | 77 | 290 | 6 |
| `frontend/src/app/ruolo/tributi/page.tsx` — RuoloTributiPageContent | 204 | 173 | 1064 | 3 |
| `backend/app/modules/network/services.py` — run_network_scan | 195 | 101 | 267 | 3 |
| `frontend/src/components/utenze/utenze-subjects-section.tsx` — UtenzeSubjectsSection | 184 | 169 | 991 | 3 |
| `frontend/src/app/network/tracking/page.tsx` — TrackingContent | 183 | 159 | 913 | 2 |
| `backend/app/modules/network/router/helpers/traffic.py` — _build_network_statistics_summary | 181 | 101 | 214 | 4 |
| `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx` — AnagraficaBulkPanel | 181 | 155 | 839 | 2 |
| `backend/app/modules/wiki/services/conversation_metrics.py` — refresh_wiki_conversation_daily_metrics | 178 | 49 | 153 | 6 |
| `frontend/src/app/catasto/import/page.tsx` — CatastoImportPage | 175 | 149 | 1114 | 3 |
| `frontend/src/app/utenze/import/page.tsx` — ImportContent | 173 | 160 | 971 | 1 |
| `frontend/src/app/ruolo/page.tsx` — RuoloDashboardPage | 168 | 157 | 1147 | 1 |
| `frontend/src/features/organigramma/organigramma-workspace.tsx` — OrganigrammaWorkspace | 167 | 147 | 1086 | 2 |
| `frontend/src/features/wiki/WikiRequestsPage.tsx` — WikiRequestsPage | 166 | 132 | 759 | 3 |
| `frontend/src/app/gaia/users/page.tsx` — GaiaUsersPage | 162 | 146 | 1011 | 2 |
| `frontend/src/app/presenze/configurazione/page.tsx` — PresenzeConfigurazionePage | 158 | 148 | 1135 | 1 |

## Recommended next slice and stop

Continue prioritizing the extreme tail, not minor warnings. A next Capacitas
wizard/validation responsibility requires new exclusive ownership, fresh original
full-file100% coverage and a bounded behavior-preserving design. Utenze391,
Catasto anomalie390 and Presenze385 remain candidates only where concurrency and
coverage permit. No next hotspot is started in this checkpoint. No global goal
completion, -50%error/-25%warning success or elimination of extremes is claimed.
