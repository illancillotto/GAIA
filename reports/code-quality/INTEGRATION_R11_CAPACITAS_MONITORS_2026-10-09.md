# GAIA — R11 Capacitas monitor lifecycle integration

## Decision and snapshot

**IMPROVED — independently reviewed, certified and integrated bounded slice.**
Global campaign remains **ACTIVE / INCOMPLETE**. No next hotspot, functional
change, race repair, main merge, push or deployment is part of this checkpoint.
The previous GIS test failure remains closed by its separate certificate.

- Integration branch: `refactor/complexity-campaign-20261008`.
- Integration worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.
- Initial integration HEAD: `95e7440b4544fe1bc26daaa30eb827c030b4f2f3`.
- Main and authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Official initial metrics: 8 October; no 7 October operational baseline.
- Main concurrent work preserved: binary diff SHA256
  `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`,
  status SHA256 `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.

Ownership registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R11_CAPACITAS_MONITORS_2026-10-09.md`.
Author, independent reviewer/integrator and distinct final verifier used dedicated
branches/worktrees. Runtime/test/report ownership was exclusive and transferred
explicitly between phases; no concurrent runtime writes or shared-file edits.

## Exact sequential integration

| Stage | Source commit | Campaign integration | Actual gate |
| --- | --- | --- | --- |
| Original 58-case characterization | `b5d82b2a` | `2b06a885` | Main ratchet PASS, zero finding |
| Independent original reviews | `8a3cd89b` | `d384b912` | Main ratchet PASS, zero finding |
| Independent design/source reviews | `959ccff4` | `2e68bc61` | Main ratchet PASS, zero finding |
| Frozen runtime, SLICE and READINESS | `55827bded7a0dc36a7517d97c938ef4d067f076d` | `01a9ada481dc2b6bd839ef39ee0948692cfca17d` | Main ratchet exit 0, zero finding |
| Distinct certificate only | `5981be8da26b46b72e8961bb6fe5d10bac158820` | `81be6d419749dd47a499687c47ccffbffbac1468` | Main ratchet exit 0, zero finding |

Author branch `refactor/complexity-r11-capacitas-monitors` and worktree
`GAIA-campaign-20261009-r11-capacitas-monitors`; review branch
`review/complexity-r11-capacitas-monitors` and corresponding `-review` worktree;
verification branch `verify/complexity-r11-capacitas-monitors` and `-final` worktree.
The verifier checked out exact source 55827bde. Terminal Integration Agent
released the git window after both post-pick gates and complete AST comparison.
Only Coordinator governance/domain documents remained unstaged during integration.

| Frozen input | SHA256 |
| --- | --- |
| Workspace runtime | `a23270634778b1243fb8ce2e01deef704ee0620a857b93b6a79591cd11c7474e` |
| Original lifecycle test | `85206faf9efa7d50e81da478b4af61beee6940fd64377fd15ffbbe57178880b7` |
| SLICE report | `3f5df7f4e86edf1705f4d7c3063487f99cef0e2a126d47b860839d8aea02a2fd` |
| Distinct certificate | `2898c999f450840268f6ef18a8ffc0ec60598500c10a43e19f0ab87ca9645d34` |
| Unchanged fraction policy | `0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb` |
| Unchanged baseline | `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95` |

## Responsibility and behavioral invariants

Four existing loaders now share token acquisition, session expiry, loading,
authentication, error classification and finally behavior. Closed typed family
configuration retains each snapshot application and exact messages. Shared
status selectors remove real duplicated decisions; no new hook, reducer,
component, export, import or relocated mega-function was introduced.

Tokens are read synchronously at dispatch; missing tokens return before loading
or API calls. Silent ordinary errors do not read messages or change visible
errors/loading; silent auth errors still expire the monitor. Successful response
clears expiry before reading prior in-flight refs. Family application errors
remain inside the original catch boundary; normal finally releases loading.

Terreni opens the first tracked terminal modal before replacing refs. History
retains first valid terminal result ordering and repeated guard. Particelle and
inCASS preserve ref/jobs/notice ordering; inCASS still sends limit 300. Polling
callbacks/dependencies, 15/20/45-second intervals and 100-job boundary are unchanged.
Manual/polling overlaps, stale responses, captured render state and retained
guidance/errors are characterized, not repaired. No freshness/cancellation guard.

## Measured local reduction

Accounting includes all nested callbacks and the adjacent unchanged policy.

| Metric | R10 before | R11 after | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 455 | 391 | -64 (-14.07%) |
| Principal cyclomatic | 404 | 360 | -44 |
| Principal callable LOC | 2625 | 2527 | -98 |
| Combined cognitive | 1022 | 926 | -96 (-9.39%) |
| Combined decisions, sum(cyclomatic - 1) | 872 | 803 | -69 (-7.91%) |
| Combined raw cyclomatic | 1129 | 1062 | -67 |
| Combined callable LOC | 4789 | 4677 | -112 |
| Combined effective file LOC | 3140 | 3131 | -9 |
| Combined callables | 257 | 259 | +2 disclosed |
| Error findings | 22 | 17 | -5 |
| Warning findings | 19 | 16 | -3 |

Principal nesting 2/params 1 and workspace useState 31/useEffect 2 are unchanged.
The extra two callables are counted, not hidden. Aggregate cognitive, decisions
and LOC genuinely decrease without transferring violation debt to another file.
The principal remains extreme at 391: this is not full hotspot resolution.

## Characterization, tests and coverage

| Behavior or gate | Existing protection / added evidence | Fresh result |
| --- | --- | --- |
| Four public loading/polling families | Existing 18 specs unchanged; new rendered lifecycle spec | 396 tests / 19 specs PASS, zero skip |
| API auth and missing/restored token | 8 added original auth cases; native storage/session checks | PASS |
| Terreni first-terminal ordering | 2 added reversed-order cases | PASS |
| Manual/polling response/error ordering | 48 added original overlap cases; intermediate DOM assertions | PASS |
| Whole workspace and policy | Explicit complete-file V8 coverage, positive counters | Statement/branch/function/line 100% |
| Entire frontend unit suite | All existing unit specs, bounded two workers | 4575 tests / 305 files PASS, zero skip |
| TypeScript | Project plus explicit new-spec/setup program | PASS |
| Owned lint / full frontend lint | Exact source and 19 specs / complete frontend | PASS; 0 owned warnings, 35 unchanged global warnings |
| Smoke / clean build | Standard npm test / npm run build:clean | 18 PASS / PASS |
| Native browser | Public navigation/refresh, genuine auth, API-boundary fixtures | 24 monitor cases + 2 real logins PASS |
| Pertinent existing E2E | Dashboard/batch suite | 4 PASS |
| Full existing E2E | Isolated production-build/synthetic stack | 54 PASS, 7 SKIP, zero failure/retry/flaky |
| Original source-order proof | Independent original/candidate ordering and microtasks | 8248 comparisons PASS |

Complete workspace coverage is 789/789 statements, 818/818 branches, 253/253
functions and 684/684 lines. Policy is 9/9 statements, 6/6 branches, 6/6 functions,
8/8 lines. No skipped map entries, empty synthetic scope or partial-region claim.
The Coordinator independently inspected raw positive coverage counters and exact
unaffected AST objects, rather than trusting only summary percentages.

Native timing uses an explicitly disclosed Playwright browser clock with real
polling callbacks. This does not certify wall-clock interval boundaries. Real
login, session bootstrap and public native gestures remain active; no private
React state/instrumentation/test-only exports. The existing seven E2E skips and
their exact reasons are in VERIFICATION_R11; optional GIS, seeded PostGIS and
external provider/MCP paths remain unverified, not PASS.

Failed attempts retained: initial verifier broader coverage scope failed the
unchanged gate despite 396 passing tests; explicit assigned full files then
passed 100%. Initial native login hit startup 502 before backend readiness; a
separate ready-stack run passed. Earlier source draft introduced a hook warning
and was rejected; an extra EOF blank was corrected before final source freeze.
No suppression, threshold/config/baseline change, hidden retry or waiver.
No fresh full backend/worker suite is claimed in this frontend-only checkpoint.

## Global metrics and baseline provenance

| Metric | Official 8 October | Integrated R11 | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Files | 1665 | 1672 | +7 | +0.42% |
| Callables | 20261 | 20320 | +59 | +0.29% |
| Error | 1956 | 1926 | -30 | -1.53% |
| Warning | 2758 | 2741 | -17 | -0.62% |
| Finding | 4714 | 4667 | -47 | -1.00% |

Application excluding worker tests: 1618 files, 18999 callables, 318975 effective
LOC and 4604 findings. Effective LOC +119 (+0.04%) against official 318856.
Findings overlap: -47 is not a count of independent problems resolved.

| Domain | Error before | Error after | Warning before | Warning after |
| --- | ---: | ---: | ---: | ---: |
| Backend | 1035 | 1033 | 1688 | 1689 |
| Frontend | 878 | 850 | 881 | 863 |
| Worker runtime | 35 | 35 | 134 | 134 |
| Worker tests | 8 | 8 | 55 | 55 |

All 1671 unaffected file and 20067 unaffected callable objects equal R10, as do
their complete finding objects. Complete registered global-check finding
objects also equal R10: **FAIL 30**, not a passing global baseline gate.
BASELINE_PROVENANCE classifies 15 historical runtime REAL_REGRESSION findings
and 15 TEST_ONLY_DIVERGENCE findings, none introduced by this campaign.
No baseline repair/generation/synchronization, threshold inflation, exclusion,
ignore, scanner/tooling or package/config modification. The authoritative
change gate is main55a ratchet, PASS with zero new finding after each pick.

## Remaining top 30 hotspots

Current full AST ranking; columns include all relevant callable dimensions.

| File:line | Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `frontend/src/components/elaborazioni/capacitas-workspace.tsx:631` | `ElaborazioniCapacitasWorkspace` | 391 | 360 | 2527 | 2 | 1 |
| `frontend/src/app/utenze/[id]/page.tsx:214` | `DetailContent` | 391 | 304 | 1908 | 2 | 1 |
| `frontend/src/app/catasto/anomalie/page.tsx:175` | `CatastoAnomaliePageContent` | 390 | 342 | 2109 | 2 | 0 |
| `frontend/src/app/presenze/giornaliere/page.tsx:880` | `PresenzeGiornalierePage` | 385 | 341 | 2023 | 2 | 0 |
| `frontend/src/app/catasto/gis/page.tsx:292` | `CatastoGisPage` | 317 | 281 | 1889 | 4 | 0 |
| `backend/app/modules/operazioni/routes/analytics.py:1069` | `anomalies_analytics` | 298 | 137 | 372 | 4 | 5 |
| `frontend/src/components/elaborazioni/settings-workspace.tsx:375` | `ElaborazioniSettingsWorkspace` | 296 | 265 | 1358 | 2 | 1 |
| `backend/app/modules/operazioni/routes/analytics.py:360` | `fuel_analytics` | 282 | 169 | 350 | 4 | 5 |
| `frontend/src/app/me/me-page-content.tsx:347` | `MePageContent` | 271 | 256 | 1133 | 2 | 1 |
| `backend/app/services/elaborazioni_bonifica_sync.py:354` | `_run_bonifica_sync_background` | 269 | 47 | 232 | 13 | 3 |
| `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:332` | `ElaborazioniBonificaSyncWorkspace` | 259 | 202 | 835 | 4 | 1 |
| `frontend/src/components/catasto/gis/MapContainer.tsx:453` | `MapContainer` | 246 | 169 | 953 | 3 | 1 |
| `frontend/src/app/presenze/collaboratori/[id]/page.tsx:100` | `PresenzeCollaboratoreDetailPage` | 233 | 212 | 1600 | 2 | 0 |
| `frontend/src/components/elaborazioni/batch-detail-workspace.tsx:53` | `ElaborazioneBatchDetailWorkspace` | 216 | 177 | 751 | 3 | 1 |
| `frontend/src/app/presenze/export/page.tsx:266` | `PresenzeExportPage` | 209 | 172 | 1097 | 3 | 0 |
| `backend/app/modules/organigramma/services/whitecompany_sync.py:198` | `sync_from_whitecompany` | 205 | 77 | 290 | 6 | 2 |
| `frontend/src/app/ruolo/tributi/page.tsx:404` | `RuoloTributiPageContent` | 204 | 173 | 1064 | 3 | 0 |
| `backend/app/modules/network/services.py:1158` | `run_network_scan` | 195 | 101 | 267 | 3 | 5 |
| `frontend/src/components/utenze/utenze-subjects-section.tsx:56` | `UtenzeSubjectsSection` | 184 | 169 | 991 | 3 | 1 |
| `frontend/src/app/network/tracking/page.tsx:406` | `TrackingContent` | 183 | 159 | 913 | 2 | 1 |
| `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:295` | `AnagraficaBulkPanel` | 181 | 155 | 839 | 2 | 0 |
| `backend/app/modules/network/router/helpers/traffic.py:271` | `_build_network_statistics_summary` | 181 | 101 | 214 | 4 | 2 |
| `backend/app/modules/wiki/services/conversation_metrics.py:156` | `refresh_wiki_conversation_daily_metrics` | 178 | 49 | 153 | 6 | 3 |
| `frontend/src/app/catasto/import/page.tsx:77` | `CatastoImportPage` | 175 | 149 | 1114 | 3 | 0 |
| `frontend/src/app/utenze/import/page.tsx:102` | `ImportContent` | 173 | 160 | 971 | 1 | 1 |
| `frontend/src/app/ruolo/page.tsx:176` | `RuoloDashboardPage` | 168 | 157 | 1147 | 1 | 0 |
| `frontend/src/features/organigramma/organigramma-workspace.tsx:1537` | `OrganigrammaWorkspace` | 167 | 147 | 1086 | 2 | 1 |
| `frontend/src/features/wiki/WikiRequestsPage.tsx:230` | `WikiRequestsPage` | 166 | 132 | 759 | 3 | 1 |
| `frontend/src/app/gaia/users/page.tsx:283` | `GaiaUsersPage` | 162 | 146 | 1011 | 2 | 0 |
| `frontend/src/app/presenze/configurazione/page.tsx:271` | `PresenzeConfigurazionePage` | 158 | 148 | 1135 | 1 | 0 |

Tail remains 5 callables above 300, 17 above 200 and 55 above 100 cognitive.
The strategic campaign target and earlier P1/P2 initial stop conditions are not
declared achieved. Pending full-backend/worker/global final suites and external
provider/seeded GIS paths are separate obligations, not blocked by this slice.

## Evidence, reproduction and residual risks

Durable evidence root: `/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/`.
`verifier/` contains raw gate logs, JUnit, full coverage maps, browser/E2E JSON,
all failed attempts, command/process ledgers and terminal resource audit.
`certified-integration/` contains source/certificate ratchet logs and actual
complete AST comparison. `coordinator/` contains independent coverage/object
checks and closure reports/Graphify/gate logs. The source certificate contains
complete commands and skip reasons; no secret values are part of this report.

From the dedicated integration checkout:

```bash
make complexity-report REPORT_JSON=/tmp/gaia-r11-complexity.json REPORT_MD=/tmp/gaia-r11-complexity.md
make complexity-ratchet BASE_REF=main
make complexity-check
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1
npm run test:unit -- --maxWorkers=2
npm run typecheck
npm run lint
npm test
npm run build:clean
```

Full E2E/native verification requires the isolated synthetic stack and genuine
login documented in the certificate; the former owned resources were actually
removed. Do not treat a missing stack as a passing rerun or use production data.
All 25 verifier processes are terminal, unique ports/containers/network and
credentials removed, sources unchanged. Only the ordinary shared Vitest timing
cache changed, disclosed without restore/delete; no dependency installation.

Dedicated frontend Graphify force/pruning and domain/platform documentation
refresh completed through their Make targets, including idempotent pruning and
OpenAI-base-URL patches. Frontend code graph has 6044 nodes / 12643 edges; HTML
was skipped by the existing 5000-node visualization limit, not a code-graph
failure. Domain and platform semantic refreshes each completed chunk 1/1 with
no semantic-chunk failure or partial results. Graphs are ignored and are not
proof of complexity; code query finds the actual typed monitor/lifecycle nodes.

Coordinator fresh `closure-full.json` reproduces every complete certified AST
object; `closure-ratchet.log` is exit 0 / zero findings against main55a;
`closure-global-check.log` is make exit 2 / 30 complete finding objects exactly
equal to the certificate, not a PASS. `closure-audit-final.json` is exit 0 and
confirms frozen hashes, empty protected baseline/config/tooling diff and all
objects. No broad application suite was rerun during byte-exact integration.
One premature Coordinator audit ran before the still-live ratchet emitted JSON
and failed its completeness assertion; the actual gate was not restarted.
That administrative attempt is retained in `coordinator/CLOSURE_ATTEMPTS.md`,
separate from the terminal passing audit; no application failure or waiver.

The large main component, 31 states, original races and history guard remain
deliberate residual debt. Next proposed bounded slice is Capacitas wizard,
validation or command responsibility, after separate ownership, original
full-file characterization and a green checkpoint. No new slice starts here.
