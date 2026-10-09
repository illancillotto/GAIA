# R9 Presenze mutations — terminal integration checkpoint

## Scope and disposition

**IMPROVED / R9 INTEGRATED. Global campaign ACTIVE/INCOMPLETE.**
Single responsibility: lifecycle shared by KM, reperibilita, editor save and
validation commands. Typed local preparation/request/finalization and pure
editor payload mapping remove repeated decisions without changing request,
cache, state, closure capture, error boundary, Promise timing or permissions.
No new runtime file, state, hook, API, JSX or behavioral correction.

Main/main merge-base remains `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Concurrent dirty main backend/Presenze/Ruolo/docs are not input or modified.
Worktree `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`. Integration never means merge to main.
Registry: `MULTI_AGENT_OWNERSHIP_R9_PRESENZE_MUTATIONS_2026-10-09.md`.

## Independently reviewed source and ordered integration

| Phase | Source SHA | Campaign integration SHA | Gate |
| --- | --- | --- | --- |
| Original characterization | 8833a587 | 4e903a83 | PASS0 |
| Actual-source independent review, report only | 38c27eff | 85e56512 | PASS0 |
| Frozen approved runtime/report/domain doc | 91f4c50d | c51b6038 | PASS0 |
| Independent final verification, report only | 0fa78703 | 8df92f9d | PASS0 |

Coordinator read the actual source diff, independent review/final reports,
fresh raw exits and coverage/browser audits before integration approval.
All three approved source blobs compare exact immediately after source
integration; the one verifier report also compares exact after integration.
No duplicate runtime source from reviewer/verifier. Protected backend/worker,
configuration, manifests, lockfiles, Makefile, tooling and baseline unchanged.
Only a report-only clarification changes the stale phrase “current399” to
“baseline399 / accepted385” after exact source acceptance; frozen runtime/test
hashes and all measured objects remain unchanged.

Runtime SHA256 `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`;
R9 test SHA256 `c337873289d2fd58736477a969f94f8f4c3fbcc1f2ce6328d3ff9bc651266f30`.
Independent verifier checks all3480preexisting tracked file hashes before/after.

## Local metrics — no complexity laundering

| Metric | R8 before | R9 integrated | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 399 | 385 | -14 |
| Principal cyclomatic | 352 | 341 | -11 |
| Principal callable LOC | 2020 | 2023 | +3 |
| Page aggregate cognitive | 1109 | 1093 | -16 |
| Page raw cyclomatic | 1230 | 1231 | +1 |
| Aggregate decisions, sum(cyclomatic-1) | 934 | 923 | -11 |
| Page callables | 296 | 308 | +12 |
| Page effective file LOC | 2788 | 2812 | +24 |
| Aggregate callable LOC | 4319 | 4364 | +45 |
| Page error/warning | 13/20 | 13/19 | 0/-1 |

Explicit tradeoff reviewed: more callable base units and LOC accompany fewer
actual decisions and shared domain-specific lifecycle. Not all metrics improve.
Principal385 is still extreme; original Presenze50%/below250 stop target is
not reached. No relocated hotspot, artificial wrapper or baseline inflation.
Fresh complete integration file/callable AST objects equal the approved named
candidate; all other runtime AST objects equal independently verified R8.

## Current global checkpoint — not final campaign metrics

| Metric | Authoritative initial snapshot | Current | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Files | 1665 | 1671 | +6 | +0.36% |
| Callables | 20261 | 20312 | +51 | +0.25% |
| Error findings | 1956 | 1933 | -23 | -1.18% |
| Warning findings | 2758 | 2745 | -13 | -0.47% |
| Findings | 4714 | 4678 | -36 | -0.76% |

Findings overlap; counts are not independent problem counts. Initial numbers
are the supplied authoritative8October audit, not the7October report.

| Domain | Error before | Error current | Warning before | Warning current |
| --- | ---: | ---: | ---: | ---: |
| Backend | 1035 | 1033 | 1688 | 1689 |
| Frontend | 878 | 857 | 881 | 867 |
| Worker runtime | 35 | 35 | 134 | 134 |
| Worker tests | 8 | 8 | 55 | 55 |

The backend warning+1 is disclosed, including legacy error-to-warning
reclassifications; a lower global total is not an anti-regression gate.
Extreme tail remains **5 cognitive>300 /17>200 /55>100**. Strategic targets
and elimination of extremes are not met. Runtime application findings excluding
worker tests:4615; worker test findings63 unchanged.

## Tests and behavioral equivalence

| Behavior/gate | Evidence | Result |
| --- | --- | --- |
| Original mutation guards, payload/error/finally/order/races | 19 rendered characterization tests on original, then six UI suites | 472 PASS |
| Captured token, response-date cache and async overlap/timing | Immutable original101case/64overlap/73timingcase/2352payload oracle and independent replay | PASS |
| Protected helpers/hooks/other statements/JSX | Complete protected AST comparison | PASS |
| Complete changed runtime coverage | Raw1035statements/1139branches/306functions/847lines | 100% |
| Fresh complete frontend unit suite | Independent302files/4491cases, zero skip/failure | PASS |
| Fresh typecheck, owned/full lint, smoke | Three unchanged owned warnings; smoke18 | PASS |
| Fresh production build | Independent own build:clean, exit0 | PASS |
| Pertinent browser UI | Own synthetic fixture, default motion, zero retries | 7 PASS |
| Full browser suite | 61collected, zero failure/flaky/retry | 54 PASS /7existing SKIP |
| Source then report integration | Authoritative make complexity-ratchet BASE_REF=main after each | PASS0 |
| Fresh complete integration metrics | Approved AST equality and unaffected R8 equality | PASS |

Skipped scenarios remain individually identified in the independent verifier
report: removed single search; two unseeded district drilldowns; two optional
GIS/Territorio smokes; live isolated MCP console; provider/model preview.
They are not PASS. Backend/worker suites are not rerun for this frontend-only
slice; whole-campaign final suites remain outstanding. No production-stack,
full-repository100% coverage or original historical GIS attribution claim.

## Ratchet, provenance and retained failures

Source and report integration ratchets compare immutable authoritative main55a
baseline and each return zero findings. Independent global complexity-check
is **FAIL30 /Make exit2**, with ALL complete finding objects identical to R8;
zero R9 attribution. Baseline hash remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No baseline generation/repair/update, ignore, exclusion or threshold change.

Previously rejected designs and the initial anonymous executor ratchet failure
remain documented. Only the genuinely new lifecycle executor receives a
semantic name; all53legacy anonymous metric/fingerprint entries are identical.
Verifier's first external metrics audit used the pre-naming candidate artifact
and failed; corrected approved-artifact comparison succeeds, no gate rerun.
Coordinator's first post-source log parser selected the shell `${BASE_REF}`
brace rather than the JSON document and failed. Correct `\n{` document start
decodes the same terminal exit0 ratchet as PASS0; no source/scanner change.
Inspection output truncation is not a gate PASS or source failure.

## Graphify and resource closure

Dedicated integration `make graphify-patch-force-pruning` and
`make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`:649sources,6029nodes,
12622edges,248communities, exit0. HTML omitted by existing>5000node policy.
`make graphify-presenze-docs`:gpt-reserve, chunk1/1done, no semantic failures,
82nodes86edges15communities,1185input/1761outputtokens, est.$0.0033. Graphs
are ignored, never committed, and not complexity evidence.
Platform documentation refresh accompanies the terminal registry update:
`make graphify-platform-docs`,gpt-reserve,chunk1/1done,no semanticfailure,
468nodes563edges85communities,8758input/3477outputtokens,estimated$0.0091.
Durable log:coordinator/integration-graphify-platform-docs.log, exit0.

Independent own services/network/credentials removed; actual ports13013/18093
free, all recorded children terminal, unchanged source. No production resource
or concurrent checkout touched. Durable evidence under
`~/.cache/gaia-campaign/20261009-r9-presenze/` (coordinator/verifier/reviewer-source).
Full fresh integration report:coordinator/integration-complexity.json/md;
complete object comparison/ranking:coordinator/integration-metrics.json.

## Remaining top30 — current integrated AST

| Rank | Callable | Cognitive | Cyclomatic | LOC | Path |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | ElaborazioniCapacitasWorkspace | 472 | 416 | 2631 | frontend/src/components/elaborazioni/capacitas-workspace.tsx |
| 2 | DetailContent | 391 | 304 | 1908 | frontend/src/app/utenze/[id]/page.tsx |
| 3 | CatastoAnomaliePageContent | 390 | 342 | 2109 | frontend/src/app/catasto/anomalie/page.tsx |
| 4 | PresenzeGiornalierePage | 385 | 341 | 2023 | frontend/src/app/presenze/giornaliere/page.tsx |
| 5 | CatastoGisPage | 317 | 281 | 1889 | frontend/src/app/catasto/gis/page.tsx |
| 6 | anomalies_analytics | 298 | 137 | 372 | backend/app/modules/operazioni/routes/analytics.py |
| 7 | ElaborazioniSettingsWorkspace | 296 | 265 | 1358 | frontend/src/components/elaborazioni/settings-workspace.tsx |
| 8 | fuel_analytics | 282 | 169 | 350 | backend/app/modules/operazioni/routes/analytics.py |
| 9 | MePageContent | 271 | 256 | 1133 | frontend/src/app/me/me-page-content.tsx |
| 10 | _run_bonifica_sync_background | 269 | 47 | 232 | backend/app/services/elaborazioni_bonifica_sync.py |
| 11 | ElaborazioniBonificaSyncWorkspace | 259 | 202 | 835 | frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx |
| 12 | MapContainer | 246 | 169 | 953 | frontend/src/components/catasto/gis/MapContainer.tsx |
| 13 | PresenzeCollaboratoreDetailPage | 233 | 212 | 1600 | frontend/src/app/presenze/collaboratori/[id]/page.tsx |
| 14 | ElaborazioneBatchDetailWorkspace | 216 | 177 | 751 | frontend/src/components/elaborazioni/batch-detail-workspace.tsx |
| 15 | PresenzeExportPage | 209 | 172 | 1097 | frontend/src/app/presenze/export/page.tsx |
| 16 | sync_from_whitecompany | 205 | 77 | 290 | backend/app/modules/organigramma/services/whitecompany_sync.py |
| 17 | RuoloTributiPageContent | 204 | 173 | 1064 | frontend/src/app/ruolo/tributi/page.tsx |
| 18 | run_network_scan | 195 | 101 | 267 | backend/app/modules/network/services.py |
| 19 | UtenzeSubjectsSection | 184 | 169 | 991 | frontend/src/components/utenze/utenze-subjects-section.tsx |
| 20 | TrackingContent | 183 | 159 | 913 | frontend/src/app/network/tracking/page.tsx |
| 21 | AnagraficaBulkPanel | 181 | 155 | 839 | frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx |
| 22 | _build_network_statistics_summary | 181 | 101 | 214 | backend/app/modules/network/router/helpers/traffic.py |
| 23 | refresh_wiki_conversation_daily_metrics | 178 | 49 | 153 | backend/app/modules/wiki/services/conversation_metrics.py |
| 24 | CatastoImportPage | 175 | 149 | 1114 | frontend/src/app/catasto/import/page.tsx |
| 25 | ImportContent | 173 | 160 | 971 | frontend/src/app/utenze/import/page.tsx |
| 26 | RuoloDashboardPage | 168 | 157 | 1147 | frontend/src/app/ruolo/page.tsx |
| 27 | OrganigrammaWorkspace | 167 | 147 | 1086 | frontend/src/features/organigramma/organigramma-workspace.tsx |
| 28 | WikiRequestsPage | 166 | 132 | 759 | frontend/src/features/wiki/WikiRequestsPage.tsx |
| 29 | GaiaUsersPage | 162 | 146 | 1011 | frontend/src/app/gaia/users/page.tsx |
| 30 | PresenzeConfigurazionePage | 158 | 148 | 1135 | frontend/src/app/presenze/configurazione/page.tsx |

## Next safe action and remaining risks

This responsibility is terminal; do not broaden R9. After the green terminal
checkpoint, choose a new bounded extreme-hotspot responsibility using this
ranking, fresh ownership and characterization before implementation. Presenze
still requires genuine render/model decision consolidation, not JSX relocation.
Capacitas full-file coverage closure remains separate; no unverified runtime
branch is integrated. All global target gaps are preserved, not redefined as
success around this one passing slice. No main merge, push or PR.
