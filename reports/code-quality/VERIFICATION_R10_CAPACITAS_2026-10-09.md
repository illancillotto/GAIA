# R10 Capacitas — Independent Frozen-Source Verification

## Decision and ownership

**CERTIFIED for this bounded slice, IMPROVED; global campaign ACTIVE/INCOMPLETE.**
Fresh gates on the exact reviewed source preserve behavior, both complete runtime
files reach100% and main ratchet has0findings. No source integration, report
commit or campaign completion is performed by this verifier. Extreme principal
455 and fivecallables>300 remain; global final backend/worker suites remain due.

Owned repository output: this report only. Runtime/tests/config/baseline/tooling
read-only after explicitly authorized exact source custody. Evidence directory:
`~/.cache/gaia-campaign/20261009-r10-capacitas/verifier/`.
Checkpoint/project skills, AGENTS and current Coordinator registry applied.

## Snapshot and exact source custody

- Worktree `GAIA-campaign-20261009-r10-verification`, branch
  `verification/complexity-r10-capacitas`.
- Started clean `7316da7f1ffd6bfeb9fedad605b572405593b87b` with original runtime.
- Authoritative main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Approved source `be3847888b8b859c2169636d02915131f1690968`, exact four-file
  cherry-pick `47e5a85337e44e8ef1d0e018241a9f4648b07cf3`; no additional source pick.
- Original runtime SHA256
  `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Original rendered characterization SHA256
  `3fa5efef566e73057614810c250c77b7dde2f0b1859d33ddeec2c3a0a1d7520a` retained.
- All3487original tracked files unchanged except approved paths; all3490frozen
  tracked files identical before/after verification. Only this report added.
- Baseline exact merge-base SHA256
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
  No inflation, repair, new ignore/exclusion, threshold or matcher edit.
- Main concurrent work never copied, reset, stashed, merged or modified.

Frozen approved blobs:
- `frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts`: `0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`.
- `frontend/src/components/elaborazioni/capacitas-workspace.tsx`: `a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`.
- `frontend/tests/unit/campaign-capacitas-fraction-resolution-r10.test.ts`: `c2d0bf12003c5d5718af7b0c6b02af4fcc2b2e39721c68a7d7712dddb6e8848c`.
- `reports/code-quality/SLICE_R10_CAPACITAS_2026-10-09.md`: `1e8e0b0837690c2ac863d71212662ce589c56919b0c8d2c2899124e0fadaa05f`.

## Fresh gate results

| Gate | Result |
| --- | --- |
| Focused original rendered union plus direct policy |338PASS,18specs,0failure/error/skip |
| Both runtime full-file coverage |100% statement/branch/function/line |
| Full frontend unit suite |4517PASS,304files,0failure/error/skip |
| Project/runtime typecheck |PASS; project configuration excludes tests |
| Explicit R10 spec/runtime compilation |Coordinator fresh PASS with external config; not attributed to verifier |
| Both runtime and R10 specs ESLint |PASS,0warnings |
| Whole frontend lint |PASS,35existing warnings retained |
| Smoke `npm test` |18PASS,0skip |
| Fresh clean production build |PASS |
| Native production-build fraction-resolution checks |6PASS,0pageerrors/default motion |
| Pertinent existing dashboard/batch E2E |4PASS,0skip |
| Complete existing E2E |54PASS,7historicalSKIP,0failure/flaky/retry |
| Complete current AST report |PASS,0parse/exception errors |
| Main complexity ratchet |PASS,0findings |
| Registered global baseline check |FAIL30; complete finding objects identicalR9 |
| Source/package integrity and owned resource cleanup |PASS; one generated Vitest cache update disclosed |

Exitcode/wallclock metadata, not substituted test-runner durations:

| Command record | Exit | Wall seconds |
| --- | ---: | ---: |
| focused | 0 | 45.302 |
| full-unit | 0 | 226.758 |
| typecheck | 0 | 26.189 |
| lint-owned | 0 | 1.271 |
| lint-full | 0 | 11.662 |
| smoke | 0 | 0.145 |
| build | 0 | 88.087 |
| native-resolution | 0 | 4.955 |
| e2e-pertinent | 0 | 5.728 |
| e2e-full | 0 | 73.790 |
| complexity-report | 0 | 45.349 |
| ratchet | 0 | 64.255 |
| global-check | 2 | 77.129 |
| cleanup | 0 | 1.988 |

Whole unit runner duration226.08s; focused44.88s. Existing jsdom navigation
warnings and full-lint/build warnings remain visible, not hidden or converted
into failures. No suite re-run used to hide a failing test.

## Coverage and behavior matrix

| Runtime | Statements | Branch arms | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Capacitas workspace |857/857 |873/873 |251/251 |748/748 |
| Fraction-resolution policy |9/9 |6/6 |6/6 |8/8 |

Raw `focused-coverage/coverage-final.json` enumerates EXACTLY both complete
files, every recorded statement/branch/function counter positive. Existing
supported `VITEST_COVERAGE_INCLUDE` selects complete files, not changed lines;
unchanged thresholds100, no coverage ignore/config edit. Direct14policy tests
plus unchanged324rendered tests are genuine tests, not source rewriting.
`coverage-audit.json` and `junit-audit.json` retain independent counts.
Original906/929branch97.52%FAIL is before evidence only, never waived or reused
as the final result. Twenty-one contract-proven fallbacks removed; shared
nullable policy retains both UNKNOWN synchronous and reachable async defenses.

| Behavior | Fresh evidence | Result/limit |
| --- | --- | --- |
| CSV/XLSX import, aliases, headers and preview contracts |Frozen prior rendered import specs with real installedSheetJS0.20.3 |PASS; no parser replacement |
| Null retained for all five events, lazy candidate/error fields |Actual policy direct spec |PASS; synchronous UNKNOWN UI reachability remains UNKNOWN |
| Selected fraction and captured request ID/payload |RenderedR10state spec and native browser |PASS |
| Busy disables sync/close and completion re-enables |Rendered and native browser |PASS |
| Late success updates current replacement, removes captured original row |Rendered/modal-race and native browser |PASS; existing race semantics preserved, not fixed |
| Late unsuccessful/rejected request with closed modal retains null |Rendered/modal-race and native browser |PASS |
| Old success with other error retains both fields/current selection |Frozen renderedR10overlap matrix |PASS; not claimed native overlap coverage |
| Missing-token submit and restored-token retry |Frozen renderedR10state spec |PASS |
| Close/reopen retains replacement identity/reset |RenderedR10state and native browser |PASS |
| Unchanged GIS and unrelated application surfaces |Complete available unit/build/E2E; GIS AST exact R9 |Available GIS unit tests PASS; both optional GIS browser smokes remain SKIP. Prior GIS certificate is not a fresh R10 smoke execution. |

## Reproducible commands

Set ROOT to this worktree and E to the evidence directory. All invocations have
full argv/cwd/start/end/PID/exit/signal in corresponding process/exit JSONs.
Logs remain external and bounded summaries were used during execution.

```bash
cd "$ROOT/frontend"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 \
  --coverage.reportsDirectory="$E/focused-coverage" \
  --reporter=default --reporter=junit --outputFile.junit="$E/focused-junit.xml"
npm run test:unit -- --maxWorkers=2 --reporter=default --reporter=junit \
  --outputFile.junit="$E/full-unit-junit.xml"
npm run typecheck
node_modules/.bin/eslint src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts \
  tests/unit/campaign-capacitas-resolution-state-r10.test.tsx \
  tests/unit/campaign-capacitas-fraction-resolution-r10.test.ts
npm run lint
npm test
npm run build:clean
node "$E/native-resolution.cjs"
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18094 npm run test:e2e -- \
  --config "$E/playwright.config.ts" elaborazioni-dashboard.spec.ts elaborazioni-batch-detail.spec.ts
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18094 npm run test:e2e -- --config "$E/playwright.config.ts"
cd "$ROOT"
make complexity-report REPORT_JSON="$E/complexity.json" REPORT_MD="$E/complexity.md"
make complexity-ratchet BASE_REF=main
make complexity-check
```

Browser commands require freshly prepared isolated resources described below;
private synthetic credentials are loaded by external run.cjs, not printed.
No old PASS claim/log reused. No full backend/worker suite for this frontend-only
slice: runtime unchanged; their global-final gates remain Coordinator work.

Coordinator post-certificate scope clarification: `npm run typecheck` checks
project/runtime sources but excludes tests. Coordinator independently compiles
both new R10 specs and their actual runtime imports using external
`coordinator/explicit-spec-tsconfig.json`, extending the unchanged project with
`exclude: []`, `incremental: false` and real Vitest/jest-dom types. Command
`node_modules/.bin/tsc --noEmit -p` that config exits0; exact log/exit file retained
under coordinator evidence. This is separately attributed Coordinator evidence,
not a verifier execution or a production config/coverage-policy change.

## Isolated browser evidence

Fresh own internalDocker network `gaia-r10-capacitas-20261009`, backend/proxy
prefix `gaia-r10-capacitas-verifier-20261009`; backend mount THIS checkout
read-only with SQLite/tmpfs under/e2e and/data, new synthetic auth/secrets,
APP_ENV=test. This is a disposable harness, not an architecture/DB change.
No production database, deployment, provider or portal used. Image IDs/mounts/
setup argv retained; own nginx binds ONLY127.0.0.1:18094 and freshly built
Next127.0.0.1:13014. No old verifier job or existing desktop browser reused.

Native script drives actual production UI via normal click/check and genuine
keyboard31Tab presses then Enter to enabled background replacement. No forced
click, direct focus, private React state or callback injection. Three outcomes
(success, unsuccessful result, HTTP500 rejection) each exercised with replacement
closed before completion versus retained open:6PASS. Captured originalID/FRA-B/
fetch_certificati true, selected replacementFRA-C, null persistence and fresh
reopen reset, captured-row filtering, disabled/enabled commands checked.
All6contexts confirm reducedMotion=false; no external origins/pageerrors.
Native routes are synthetic boundary fixtures, not proof of live Capacitas
portal behavior, nor native reachability of the two synchronous UNKNOWN guards.
Policy direct tests cover those retained nullable semantics without claiming
UI unreachability. Existing dashboard/batch E2E cover neighboring presentation,
not substituted for changed transition tests.

Repository Playwright timeouts90000/20000ms and retries0 preserved; external
config changes only resource URLs, artifact/report output, workers1 and client
storage fixture. Native standalone expectations use library defaults (stricter,
not increased); no timeout/motion workaround or selective retry.

All seven full-E2E skipped objects/annotations/normalized source positions match
R9 exactly; they are **SKIP, not PASS**:

| Spec | Skipped behavior | Reason |
| --- | --- | --- |
| `catasto-anagrafica.spec.ts:14` | admin executes catasto anagrafica single search | La ricerca singola è stata rimossa: resta solo l’elaborazione massiva. |
| `catasto-drilldown.spec.ts:14` | admin navigates catasto distretti -> distretto detail -> particella detail | Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down. |
| `catasto-drilldown.spec.ts:52` | admin navigates catasto distretti -> anomalie tab -> anomaly workspace | Nessun distretto disponibile nello stack locale: esegui seed/import shapefile prima del drill-down. |
| `gis-territorio.spec.ts:381` | GIS console and toolbar tools fit desktop and mobile viewports | Set PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true to run the optional smoke. |
| `gis-territorio.spec.ts:439` | territorio smokes map consultation, sheets, measurements, print and QGIS | Set PLAYWRIGHT_GIS_TERRITORIO_ENABLED=true to run the optional smoke. |
| `wiki-mcp-console.spec.ts:3` | local Docker synthetic console shows data and actual tool history | Requires isolated synthetic Docker gateway |
| `wiki-mcp-preview.spec.ts:3` | live synthetic login to gateway to MCP to model | Explicit synthetic fixture/provider opt-in required |

## Metrics, provenance and debt accounting

Full AST complete approved candidate-owned file/callable/violation objects
identical author actual two-file report. Every unaffected full file/callable/
violation object identical R9, engines/include/exclude exact, one genuine new
policyfile accounts for1671→1672. No report7October numbers used as baseline.

| Metric | R9 before | Frozen R10 after | Delta |
| --- | ---: | ---: | ---: |
| Total files |1671 |1672 |+1 |
| Total callable |20312 |20318 |+6 |
| Errors |1933 |1931 |-2 |
| Warnings |2745 |2744 |-1 |
| Findings |4678 |4675 |-3 |
| Combined target cognitive |1099 |1022 |-77 (-7.01%) |
| Combined raw cyclomatic |1174 |1129 |-45 |
| Combined decisions sum(cyclomatic-1) |923 |872 |-51 |
| Combined callable count |251 |257 |+6 |
| Combined callable LOC |4782 |4789 |+7 |
| Combined file LOC |3109 |3140 |+31 |
| Principal cognitive |472 |455 |-17 (-3.60%) |
| Principal cyclomatic |416 |404 |-12 |
| Principal callable LOC |2631 |2625 |-6 |

Workspace fileLOC3109→3105 and newpolicy35LOC; combined+31 disclosed, not hidden.
All6new policy callables below thresholds with0violations, no duplicated mega
function or transferred finding. useState31/useEffect2 unchanged; principal
nesting2/params1 unchanged. Actual combined reduction qualifies IMPROVED, not
mere relocation; a small safety-enabling slice is NOT drastic hotspot closure.
Modified responsibility findings44→41; aggregate gains and LOC cost reviewed.

Compared official8October campaign baseline1956errors/2758warnings/4714findings,
current totals improve25errors/14warnings/39findings; these are multi-metric
signals, not independent problem counts. Strategic debt reduction still small.

| Domain | Error before | Error after | Warning before | Warning after |
| --- | ---: | ---: | ---: | ---: |
| backend | 1033 | 1033 | 1689 | 1689 |
| frontend | 857 | 855 | 867 | 866 |
| workerRuntime | 35 | 35 | 134 | 134 |
| workerTests | 8 | 8 | 55 | 55 |

Main change gate PASS0. Registered global baseline gate FAIL30/Makeexit2;
complete30findingobjects identicalR9, not merely equal counts, and zeroR10
attribution. Baseline stale/provenance responsibility remains separate, neither
ignored nor repaired. Raw `global-check.json`, `ratchet.json`,
`metrics-audit.json` preserve evidence. Extreme tail5>300/17>200/55>100 unchanged.

## Remaining top30 callable

| Rank | Source | Callable | Cognitive | Cyclomatic | LOC |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | `frontend/src/components/elaborazioni/capacitas-workspace.tsx:530` | `ElaborazioniCapacitasWorkspace` | 455 | 404 | 2625 |
| 2 | `frontend/src/app/utenze/[id]/page.tsx:214` | `DetailContent` | 391 | 304 | 1908 |
| 3 | `frontend/src/app/catasto/anomalie/page.tsx:175` | `CatastoAnomaliePageContent` | 390 | 342 | 2109 |
| 4 | `frontend/src/app/presenze/giornaliere/page.tsx:880` | `PresenzeGiornalierePage` | 385 | 341 | 2023 |
| 5 | `frontend/src/app/catasto/gis/page.tsx:292` | `CatastoGisPage` | 317 | 281 | 1889 |
| 6 | `backend/app/modules/operazioni/routes/analytics.py:1069` | `anomalies_analytics` | 298 | 137 | 372 |
| 7 | `frontend/src/components/elaborazioni/settings-workspace.tsx:375` | `ElaborazioniSettingsWorkspace` | 296 | 265 | 1358 |
| 8 | `backend/app/modules/operazioni/routes/analytics.py:360` | `fuel_analytics` | 282 | 169 | 350 |
| 9 | `frontend/src/app/me/me-page-content.tsx:347` | `MePageContent` | 271 | 256 | 1133 |
| 10 | `backend/app/services/elaborazioni_bonifica_sync.py:354` | `_run_bonifica_sync_background` | 269 | 47 | 232 |
| 11 | `frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx:332` | `ElaborazioniBonificaSyncWorkspace` | 259 | 202 | 835 |
| 12 | `frontend/src/components/catasto/gis/MapContainer.tsx:453` | `MapContainer` | 246 | 169 | 953 |
| 13 | `frontend/src/app/presenze/collaboratori/[id]/page.tsx:100` | `PresenzeCollaboratoreDetailPage` | 233 | 212 | 1600 |
| 14 | `frontend/src/components/elaborazioni/batch-detail-workspace.tsx:53` | `ElaborazioneBatchDetailWorkspace` | 216 | 177 | 751 |
| 15 | `frontend/src/app/presenze/export/page.tsx:266` | `PresenzeExportPage` | 209 | 172 | 1097 |
| 16 | `backend/app/modules/organigramma/services/whitecompany_sync.py:198` | `sync_from_whitecompany` | 205 | 77 | 290 |
| 17 | `frontend/src/app/ruolo/tributi/page.tsx:404` | `RuoloTributiPageContent` | 204 | 173 | 1064 |
| 18 | `backend/app/modules/network/services.py:1158` | `run_network_scan` | 195 | 101 | 267 |
| 19 | `frontend/src/components/utenze/utenze-subjects-section.tsx:56` | `UtenzeSubjectsSection` | 184 | 169 | 991 |
| 20 | `frontend/src/app/network/tracking/page.tsx:406` | `TrackingContent` | 183 | 159 | 913 |
| 21 | `frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx:295` | `AnagraficaBulkPanel` | 181 | 155 | 839 |
| 22 | `backend/app/modules/network/router/helpers/traffic.py:271` | `_build_network_statistics_summary` | 181 | 101 | 214 |
| 23 | `backend/app/modules/wiki/services/conversation_metrics.py:156` | `refresh_wiki_conversation_daily_metrics` | 178 | 49 | 153 |
| 24 | `frontend/src/app/catasto/import/page.tsx:77` | `CatastoImportPage` | 175 | 149 | 1114 |
| 25 | `frontend/src/app/utenze/import/page.tsx:102` | `ImportContent` | 173 | 160 | 971 |
| 26 | `frontend/src/app/ruolo/page.tsx:176` | `RuoloDashboardPage` | 168 | 157 | 1147 |
| 27 | `frontend/src/features/organigramma/organigramma-workspace.tsx:1537` | `OrganigrammaWorkspace` | 167 | 147 | 1086 |
| 28 | `frontend/src/features/wiki/WikiRequestsPage.tsx:230` | `WikiRequestsPage` | 166 | 132 | 759 |
| 29 | `frontend/src/app/gaia/users/page.tsx:283` | `GaiaUsersPage` | 162 | 146 | 1011 |
| 30 | `frontend/src/app/presenze/configurazione/page.tsx:271` | `PresenzeConfigurazionePage` | 158 | 148 | 1135 |

## Graphify, diagnostics and cleanup

Author's dedicated `make graphify-frontend` actual exit0 evidence inspected:
650ASTsources/6034nodes/12627edges/250communities, fresh absent graph, no stale
incremental symbols. HTML visualization skipped at5000node configured limit;
JSON/report built. No graph versioned, no semantic API claimed. Domain docs
Graphify governance remains Coordinator responsibility, not a complexity proof.
Verifier changes no component/service boundary beyond frozen approved source.

External harness diagnostics preserved and explained, not application failures:

- First metrics audit exit1 compared entire scope including derived files1671
  versus legitimate1672. Corrected strict include/exclude equality plus exactly
  one new file; all unaffected complete AST already exact. Fresh report not rerun.
- Initial approved-candidate comparison mistakenly compared full1672file report
  to author's TWO-file scoped report. Own comparison process terminated(exit143)
  to bound huge assertion-diff memory; corrected full owned objects comparison
  PASS. No scanner/source edit, baseline change or application test retry.
- Strict dependency ALL-entry comparison detected one generated Vitest result
  cache update, not an installed package change. Exact diff retained; every
  installed package/library entry unchanged. No shared cache restoration.

Existing ignored node_modules symlink to main's installed dependency directory
only; no generated code/build copied or npm install. All32122entries captured
before/after: exactly `.vite/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`
changes64216fe2…→6853f470… because Vitest writes timing/status results. Cache
retains historical stale entries and is NOT test evidence; fresh JUnit is the
suite authority. Dependency versions: Node24.14.0/npm11.9.0, Vitest4.1.6,
SheetJS0.20.3, Playwright1.59.1, TypeScript5.8.3, Next15.5.25.

Actual cleanup completed: checked own Next PID/cwd/cmdline, SIGTERM, exit0;
archived own container logs mode0600, removed ONLYown containers/network,
deleted synthetic credentials, both loopback portsfree and every recorded
process terminal. External directory0700. Fresh terminal manifest3490frozen
tracked hashes exact; original3487hashes unchanged except approved4file custody;
all installed package blobs exact, generatedcache difference disclosed.
`terminal-audit.json`, `cleanup-commands.json`, source/dependency manifests and
`dependency-diff.json` retain evidence. No test/build/browser/backend remains.

## Handoff and residual risks

Slice independently CERTIFIED/IMPROVED with no identified functional or new
complexity regression; final source/report integration belongs Coordinator.
No report commit authorized. Preserve unexplained UNKNOWN guard reachability,
legacy modal race behavior, extreme principal455, state concentration and LOC
cost. Do not broaden this slice, change baseline or infer campaign completion.
Global campaign remains ACTIVE/INCOMPLETE; historical30baseline provenance,
large extreme tail and global-final application suites remain open.
