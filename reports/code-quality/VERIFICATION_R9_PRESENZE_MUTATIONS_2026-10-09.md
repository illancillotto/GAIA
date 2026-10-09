# R9 Presenze mutations — independent final verification

Frozen R9 source independently verified: focused/full frontend tests, full-page
coverage, typecheck, lint, smoke, fresh production build and isolated browser
gates PASS. Authoritative complexity ratchet PASS with zero findings.
Global complexity-check remains **FAIL**, with all 30 complete finding objects
identical to R8 and zero R9 attribution. This verifies the bounded R9 slice;
the global campaign remains **ACTIVE/INCOMPLETE**.

## Authority and immutable source

- Approval: `~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/VERIFY_APPROVAL.md`.
- Authority registry: integration worktree
  `docs/code-quality/MULTI_AGENT_OWNERSHIP_R9_PRESENZE_MUTATIONS_2026-10-09.md`.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261009-r9-presenze-verification`;
  branch `verify/complexity-r9-presenze-mutations`.
- Source: `91f4c50de44adf433f20decfa31ccf0ba794a5c0`, initially clean.
  Independent source review: `38c27eff2a8d55578ff6ed0433b307471800e364`.
- Authoritative main/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
  Main concurrent work was neither input nor modified.
- Runtime SHA256:
  `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
- R9 test SHA256:
  `c337873289d2fd58736477a969f94f8f4c3fbcc1f2ce6328d3ff9bc651266f30`.
- All **3480 existing tracked files**, including complete source trees, tests,
  configuration, package manifests/lockfiles, tooling and baseline, hashed before
  and after: identical. No runtime/test/config/tooling source edit.
- Baseline exact to authoritative main; SHA256
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Only this report is writable/versioned. Installed matching frontend deps use
  the preapproved ignored node_modules link. No baseline synchronization,
  repair, scope/threshold/ignore change, source cherry-pick, integration or PR.

AGENTS, checkpoint and project complexity skill/references applied. Scope is
the four daily-record mutation flows; INAZ identity mapping, connector contracts,
backend/worker behavior and other hotspots remain outside this assignment.

## Fresh serial gates

Evidence directory: `~/.cache/gaia-campaign/20261009-r9-presenze/verifier/`,
mode0700. Each recorded invocation has `*-process.json`, `*-exit.json` and a
private mode0600 raw log, with actual arguments, cwd, UTC start/end, PID, exit
and signal. Times below are recorder wall time, not summed JUnit testcase time.
All suite/scanner handles were observed to termination; no timeout restart.

| Gate | Actual result | Exit | Wall seconds |
| --- | --- | --- | --- |
| Six focused UI suites, full-page coverage | 472 PASS; zero failure/error/skip | 0 | 36.848 |
| Full frontend unit suite, two workers | 4491 PASS / 302 files; zero failure/error/skip | 0 | 187.370 |
| Typecheck | PASS | 0 | 22.626 |
| Owned page + R9 test ESLint | PASS; three existing page warnings | 0 | 1.198 |
| Full frontend lint | PASS; existing warnings retained | 0 | 8.906 |
| Smoke | 18 PASS; zero skipped | 0 | 0.150 |
| Fresh build:clean, own worktree | PASS | 0 | 53.412 |
| Default browser environment inspection | PASS, reducedMotion=false | 0 | 0.437 |
| Pertinent Presenze E2E | 7 PASS; zero skipped/flaky/unexpected/retry | 0 | 10.275 |
| Full frontend E2E | 54 PASS, 7 existing SKIP; zero flaky/unexpected/retry | 0 | 69.674 |
| Browser JSON/complete skip comparison | PASS | 0 | 0.022 |
| Complexity report, external JSON/MD | PASS; counts below | 0 | 43.026 |
| Authoritative ratchet, BASE_REF=main | PASS, zero findings | 0 | 44.233 |
| Global complexity-check | FAIL, 30 historical findings | 2 | 52.853 |
| First external metrics audit | FAIL: wrong historical candidate artifact | 1 | 0.367 |
| Corrected full-object metrics/provenance audit | PASS; approved named candidate exact | 0 | 0.313 |
| Own resource cleanup | PASS | 0 | 0.725 |

Full unit Vitest duration was 186.71s, independently parsed JUnit confirms
4491 cases in 302 suites, zero skipped/failure/error. Pertinent Playwright
duration 9675.849ms; full Playwright duration 69112.061ms. Raw counters and
individual statuses, rather than expected numbers, govern this report.

### Actual commands

Commands executed from `frontend/` through the external recorder:

```sh
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx \
  npm run test:coverage -- \
  tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-r6.test.tsx \
  tests/unit/presenze-giornaliere-r7.test.tsx \
  tests/unit/presenze-giornaliere-r8.test.tsx \
  tests/unit/presenze-giornaliere-r9.test.tsx \
  --coverage.reportsDirectory=<evidence>/focused-coverage \
  --reporter=default --reporter=junit \
  --outputFile.junit=<evidence>/focused-junit.xml
npm run test:unit -- --maxWorkers=2 --reporter=default --reporter=junit \
  --outputFile.junit=<evidence>/full-unit-junit.xml
npm run typecheck
node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx \
  tests/unit/presenze-giornaliere-r9.test.tsx
npm run lint
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build:clean
node_modules/.bin/next start --hostname 127.0.0.1 --port 13013
npm run test:e2e -- --config=<evidence>/playwright.config.ts \
  tests/e2e/presenze-operational-controls.spec.ts \
  tests/e2e/presenze-hierarchy.spec.ts \
  tests/e2e/presenze-whatsapp-dashboard.spec.ts
npm run test:e2e -- --config=<evidence>/playwright.config.ts
```

`<evidence>` is the absolute evidence directory above; exact expanded arguments
are retained in invocation metadata. The existing supported coverage variable
selects the complete page; all four configured 100% thresholds were unchanged.
Browser credentials came only from the new private synthetic environment file.

Commands from the own repository root:

```sh
REPORT_JSON=<evidence>/complexity.json REPORT_MD=<evidence>/complexity.md \
  make complexity-report
BASE_REF=main make complexity-ratchet
make complexity-check
```

Scanner bytecode cache was directed externally with PYTHONPYCACHEPREFIX.
No baseline generation/repair/verify was invoked. Whole finding and AST
comparisons used the external scripts; no scanner or application gate rerun.

## Complete page coverage and warnings

Raw V8 counters: **1035/1035 statements, 1139/1139 branches, 306/306 functions**,
all positive. Raw Cobertura: **847/847 lines**, no missed lines, line-rate and
branch-rate1. Full-file statement/branch/function/line gate: **100%**.
Coverage contains exactly the frozen modified page, with no added exclusion.
Evidence: `focused-coverage/coverage-final.json`, `cobertura-coverage.xml`,
`coverage-audit.json`, `focused-junit.xml`, `junit-audit.json`.

Owned lint retains exactly the approved three warning messages: unused
`isLoadingRecordDetail`, effect dependency `closeSelectedRecord`, and effect
dependency `contractProfileEditor`. Full lint/build retain other existing
frontend warnings. No new suppression or lint/config edit.

## Fresh isolated browser stack

Next15.5.25, Vitest4.1.6, Playwright1.59.1, Chromium147.0.7727.15. Fresh own
build ID `gg8ffV3KuWHfYCRdaSgYs`; no prior build reuse. Observed viewport1280x720,
DPR1 and reducedMotion=false. Existing mobile/desktop assertions unchanged.

Own frontend loopback13013 and proxy loopback18093 were checked free before
binding. Own internal Docker network `gaia-r9-presenze-20261009`; only own
backend/proxy containers `gaia-r9-presenze-verifier-20261009-{backend,proxy}`.
Dependency image `dfd01b8c715a` mounts this frozen backend read-only at `/app`;
synthetic SQLite `/e2e` and `/data` are tmpfs. Metadata creation, real startup,
bootstrap and uvicorn run from this source. No real env/database/volume/provider
or production8080/8081 touch; public map assets are browser environmental inputs.

Fresh random password/JWT/credential key, synthetic admin identity, private
mode0600 env; values never printed. Login uses public authentication. Stable
`gaia.client_device_id` uses the public client contract and does not bypass auth.
External Playwright config imports unchanged repository config, changes only
fixture origin/paths/reporters, serial worker count and stable device storage.
Default motion, retries0, timeout90000ms, expect timeout20000ms and assertions
remain unchanged. No production suite PASS claim.

### Seven existing skipped scenarios — not PASS

Complete titles, locations and annotations match R8 after worktree-path
normalization. Individually retained in `e2e-audit.json` and `e2e-full.json`.

| Spec | Scenario | Existing skip reason |
| --- | --- | --- |
| catasto-anagrafica.spec.ts:14 | admin executes catasto anagrafica single search | Single search removed; only bulk processing remains |
| catasto-drilldown.spec.ts:14 | admin navigates catasto distretti -> distretto detail -> particella detail | Synthetic stack has no distretto seed/import |
| catasto-drilldown.spec.ts:52 | admin navigates catasto distretti -> anomalie tab -> anomaly workspace | Synthetic stack has no distretto seed/import |
| gis-territorio.spec.ts:381 | GIS console and toolbar tools fit desktop and mobile viewports | Optional PLAYWRIGHT_GIS_TERRITORIO_ENABLED fixture absent |
| gis-territorio.spec.ts:439 | territorio smokes map consultation, sheets, measurements, print and QGIS | Optional PLAYWRIGHT_GIS_TERRITORIO_ENABLED fixture absent |
| wiki-mcp-console.spec.ts:3 | local Docker synthetic console shows data and actual tool history | Requires separate isolated synthetic Docker gateway |
| wiki-mcp-preview.spec.ts:3 | live synthetic login to gateway to MCP to model | Explicit synthetic fixture/provider opt-in absent |

## Fresh complexity and historical failure attribution

Whole report: **1671 files, 20312 callables** (backend6305/frontend12110/
worker1897), **1933 errors, 2745 warnings, 4678 findings**. Parse/exception
errors zero. Complete objects for callables/files/violations/engines/scope/
summary match the approved `coordinator/named-candidate/complexity.json` exactly.
Every unaffected complete runtime file/callable object matches R8.

| Page metric | R8 before | Frozen R9 | Delta |
| --- | ---: | ---: | ---: |
| Aggregate cognitive | 1109 | 1093 | -16 |
| Raw aggregate cyclomatic | 1230 | 1231 | +1 |
| Aggregate decisions, sum(cyclomatic-1) | 934 | 923 | -11 |
| Callable count | 296 | 308 | +12 |
| Effective file LOC | 2788 | 2812 | +24 |
| Aggregate callable LOC | 4319 | 4364 | +45 |
| Findings | 33 | 32 | -1 warning |
| Principal cognitive/cyclomatic/LOC | 399/352/2020 | 385/341/2023 | -14/-11/+3 |

Classification **IMPROVED** is consistent with independently reviewed genuine
lifecycle/payload responsibilities and the explicit raw-cyclomatic/LOC tradeoff.
Raw cyclomatic+1 is not relabeled a decrease: twelve extra callable base units
accompany eleven fewer aggregate decisions. Principal385 remains extreme;
five callables still exceed cognitive300. No transferred or new runtime finding.

Authoritative ratchet uses the immutable merge-base/main baseline: **PASS0**.
Global check: scanner exit1/Make exit2, **FAIL30**. ALL thirty finding objects,
including path/symbol/reason/metric/baseline/value/delta, are identical to
R8 `coordinator/final-global-check.json`; zero R9 attribution. No repair,
baseline update or historical failure erased. Evidence: `ratchet.json`,
`global-check.json`, `metrics-audit.json`, `provenance-audit.json`.

## Retained inspection/audit failures

First external metrics comparison exited1 because its scaffold loaded older
`coordinator/candidate-complexity.json`, before the newly introduced executor
received its semantic name. Exactly three callable-object differences (name/
fingerprints) were recorded; metrics/summary were equal. Correct artifact
`coordinator/named-candidate/complexity.json` yields complete exact equality.
Coordinator subsequently confirmed that path. Failed log/exit and complete
`metrics-first-comparison-diff.json` remain; corrected audit has a separate
invocation/log/exit. No application suite rerun or source/threshold change.

Initial own healthHTTP502 occurred during import/startup; same backend became
readyHTTP200 without restart. Non-gate exploratory missing paths and first
overlarge mandatory-doc read are explicitly documented in INSPECTION_ERRORS.md.
Original author/reviewer harnesses, provenance and frozen goldens untouched.
These observations are not relabeled as passing gates.

## Cleanup, graph and limits

All recorded children terminal, including frontend exit0 after own SIGTERM.
Own backend/proxy logs preserved privately, containers/network removed, private
credentials deleted, reserved ports13013/18093 free. `cleanup.json` and
`terminal-audit.json` assert no owned container/network/listener/live recorded
process, source hashes unchanged, and only this report in writable scope.

Graphify source/domain refresh already terminal before assignment: dedicated
frontend force refresh and Presenze docs gpt-reserve chunks1/2 and2/2 done,
zero semantic failure. No source/domain docs edit by verifier; no graph output
committed or redundant refresh. Report-only commit authorized after gates and
cleanup; its exact SHA is published in external REPORT_SHA.txt/VERIFIER_RESULT.md.

Backend/worker application suites not rerun because R9 changes neither; their
whole-campaign final gates remain Coordinator work. No global coverage PASS:
reported Capacitas97.52% is inherited unresolved context, not a fresh measurement.
Seven skipped E2E scenarios, thirty historical findings, five cognitive>300
hotspots and strategic targets remain open. Integration belongs Coordinator;
global objective remains **ACTIVE/INCOMPLETE**.
