# R6 Presenze Daily — Independent Final Verification

## Ownership and frozen source

This report certifies only the approved daily-cell indicator/KM presentation
slice. The principal remains extreme; the global campaign is ACTIVE/INCOMPLETE.

- Initial clean integration snapshot: `afebd6154fa1f2c0f76693f39f2e4d5fea6ae271`.
- Author source: `56c46570f48c3281ba2db2b3e8220338b29c8e88`.
- Independent review: `c1475bb2e31efd4e2d1173a3233983fab2be361c`, APPROVED.
- Coordinator explicitly authorized exact source application after review.
- Isolated worktree: `GAIA-campaign-20261009-r6-presenze-verification`.
- Branch: `verify/complexity-r6-presenze-daily`.
- Verifier source cherry-pick: `c03ee32fa834d41df5d0d0ffa52ddaded02700e1`.
- Main/authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Verifier owns only this report. No runtime/test/config edits, main merge,
push or PR. Dirty main is not used, copied, reset, stashed or committed.

| Frozen path | Git object |
|---|---|
| page.tsx | `498f25362d845c50682ea83862b3318c4037ade0` |
| daily-cell-model.ts | `5261bacc02c8cdb1f2a179450042552668be697b` |
| frontend/src | `35403bea5e68cc20cc68928e3e355435df27716b` |
| frontend/tests | `5bb3a85b67e53cec6fadc8384e57aa1952c33ed5` |
| backend/app | `3e8bfdbaf692bbcbed3d24dccff11a7605d62049` |

Runtime/tests exactly match author source. Protected backend, worker,
shared frontend lib/hooks/UI/layout, quality tooling, Makefile, manifests,
Playwright/Vitest config, baseline/threshold/scope files remain unchanged
from initial verifier HEAD. `git diff --check` PASS; final worktree clean
before this report. No new ignore, skip, retry, timeout or coverage waiver.

## Behavioral and structural evidence

Verifier independently parses before/after AST: all72 top-level function
declarations and all75 hook-call ASTs are identical, preserving lifecycle,
dependencies and commands outside presentation. The original page SHA256 is
`3753ab56630a1440fe4dd098e4ba426d025b50e0c2e2ab92af7ee3068145ce4b`;
candidate is `c6dfa496e22acaa6634ed3fb9cb725606a567e50045579eebc70d10f289fc91e`.
The tiny runtime diff retains DOM, handlers, authorization scopes and
uncontrolled KM inputs; only ordered indicators and duplicate KM projection
are consolidated. Icon order/classes and authorized-before-request precedence,
null/zero/negative/NaN distinctions, draft precedence, selection, ownership
and saving transitions are asserted by the focused characterization tests.

All unaffected full-report callable and file objects exactly match frozenR5;
engines/include/exclude remain exact. Before-page objects independently match
the complete frozenR5 report, not only an author's aggregate summary.

## Tests and coverage

Durable verifier evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/`.
External `run.cjs` records exact commands, working directory, PID, timestamps,
exit code/signal and logs. Suites/build are serial; no live process was
restarted. Separate rawJUnit audit proves case/failure/error/skip counts.

| Gate | Result | Runner duration | Evidence |
|---|---|---:|---|
| Focused5 files | 413PASS,0skip/failure/error; exit0 | 37.352s | focused.log/junit/exits |
| Complete frontend units | 4417PASS/299files,0skip/failure/error; exit0 | 102.125s | full-unit.log/junit/exits |
| Typecheck | PASS,exit0 | 22.295s | typecheck.log/exits |
| Owned runtime/test ESLint | 0errors,3preexisting page warnings; exit0 | 1.194s | lint.log/lint-before.log |
| npm test smoke | 18PASS,0skip; exit0 | 0.143s | smoke.log/exits |
| Fresh production build:clean | PASS,exit0 | 52.807s | build.log/exits/build-id.txt |
| Pertinent Presenze E2E | 7PASS,0skip/unexpected/flaky; exit0 | 10.257s | e2e-presenze.log/json/exits |
| Complete E2E | 54PASS,7existing skips,0unexpected/flaky; exit0 | 69.134s | e2e-full.log/json/exits |
| Ratchet/main | PASS,0findings; exit0 | 44.727s | ratchet.log/exits |
| Complete AST report | PASS,0parse/exception errors; exit0 | 43.506s | complexity.json/md/exits |
| Global recorded-baseline check | FAIL30,Makeexit2 | 54.558s | global-check.log/json/exits |

Raw test durations are36.94s focused,101.48s units,9.667s pertinent browser
and68.596s complete browser; runner durations include process overhead.
Existing three lint warnings are independently reproduced from afebd615
via ESLint stdin: unused detail-loading state and two effect dependencies.
No suppressions or source changes are used. Production build has repository
warnings; its successful exit is not a claim of zero-warning repository lint.

| Modified complete runtime file | Statements | Branch outcomes | Functions | Coverage |
|---|---:|---:|---:|---|
| page.tsx | 1094/1094 | 1217/1217 | 302/302 | 100% |
| daily-cell-model.ts | 8/8 | 14/14 | 3/3 | 100% |

Combined lines903/903. Raw V8 statement, function and individual branch-arm
counters independently audited: zero misses. Existing supported explicit
`VITEST_COVERAGE_INCLUDE` selects both entire modified runtime files;
versioned policy/config/scope and100% thresholds remain unchanged.
No claim of full-repository100% coverage is made.

Commands from verifier frontend:

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/app/presenze/giornaliere/daily-cell-model.ts \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  tests/unit/presenze-giornaliere-r6.test.tsx \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/focused-coverage \
  --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/focused-junit.xml
npm run test:unit -- --maxWorkers=4 --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/full-unit-junit.xml
npm run typecheck
node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx \
  src/app/presenze/giornaliere/daily-cell-model.ts tests/unit/presenze-giornaliere-r6.test.tsx
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build:clean
```

## Fresh isolated browser stack

This verifier builds its own frozen source, not reusedGIS artifacts. Installed
Next15.5.25/React18.3.1/MapLibre6.9.0/Playwright1.59.1/Vitest4.1.6.
Fresh production frontend binds loopback13010, proxy loopback18090. Backend
uses verifier/backend read-only at `/app`, actual metadata/startup/uvicorn,
new syntheticSQLite on `/e2e`tmpfs and `/data`tmpfs, exclusive internalDocker
network `gaia-r6-presenze-verifier-20261009`. Image supplies dependencies;
bind/source objects prove application code is frozen, not trusted implicitly
from an older image. No real DB, credentials, volumes or running services used.

Random disposable credentials are created mode0600, never printed, and
privately mapped to Playwright admin environment. Initial prepared-health502
was before backend startup; actual source-health and frontend readiness200
preceded suites. Preparation readiness is not counted as source verification.
Temporary external runner imports unchanged versioned Playwright config;
only test/output/report locations, loopbackbaseURL, workers1 and a stable
public `gaia.client_device_id` are supplied. No auth token/cookie is seeded
by the runner. Stable device identity avoids allocating repeated synthetic
devices, without changing authentication enforcement or the20-device cap.
Existing public fixtures may explicitly mock API/auth as committed; those
scenarios verify actual production frontend behavior, not live INAZ/GATE.

Chromium147.0.7727.15,1280x720,dpr1,default motion. Separate browser observation
confirms reduced-motion=false. Project timeout90000ms,expect20000ms,retries0
unchanged; all actual result retries0. No interception, native gesture,
timing, GIS readiness predicate or skip modification introduced by verifier.

Privately load credentials from the owned bootstrap environment, then run:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18090 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/playwright.config.ts \
  tests/e2e/presenze-operational-controls.spec.ts \
  tests/e2e/presenze-hierarchy.spec.ts tests/e2e/presenze-whatsapp-dashboard.spec.ts
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18090 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/playwright.config.ts
```

## Existing E2E skips — not PASS

| Scenario | Cause | Unverified impact |
|---|---|---|
| catasto-anagrafica.spec.ts:14 | Single search removed, bulk-only | Removed single-search flow |
| catasto-drilldown.spec.ts:14 | No synthetic districts seeded | District/parcel drilldown |
| catasto-drilldown.spec.ts:52 | No synthetic districts seeded | District/anomaly drilldown |
| gis-territorio.spec.ts:381 | OptionalGIS flag not enabled | Optional responsiveGIS smoke |
| gis-territorio.spec.ts:439 | OptionalGIS flag not enabled | Optional territory/QGIS smoke |
| wiki-mcp-console.spec.ts:3 | Isolated synthetic gateway opt-in required | LiveMCP console |
| wiki-mcp-preview.spec.ts:3 | Explicit provider/fixture opt-in required | LiveMCP/model flow |

Exact annotations retained in e2e-full.json/e2e-audit.json. No new skip.
Backend/worker complete suites are not rerun for this frontend-only slice;
their earlierR5 evidence is separate, not substituted fresh certification.

## Metrics and no debt transfer

Aggregates include every callable across complete page and model, including
the new filter/map callbacks. Frozen before-report exactly matches R5 source.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 437 | 420 | -17(-3.89%) |
| Principal cyclomatic | 385 | 371 | -14 |
| Principal callable LOC | 2080 | 2076 | -4 |
| Affected cognitive sum | 1273 | 1230 | -43(-3.38%) |
| Affected cyclomatic sum | 1350 | 1319 | -31(-2.30%) |
| Affected callable LOC, overlapping ranges | 4508 | 4520 | +12 |
| Affected effective file LOC | 2858 | 2877 | +19 |
| Affected callable count | 303 | 307 | +4 |
| Affected error findings | 18 | 17 | -1 |
| Affected warning findings | 23 | 21 | -2 |
| Page useState/useEffect | 21/13 | 21/13 | 0/0 |

New model cognitive8/cyclomatic10/effectiveLOC22,3callables,zero findings;
largest helper cognitive5/cyclomatic5/LOC14. Genuine ordered presentation and
duplicate-KM policy simplification: not a moved component/mega-helper.
LOC grows explicitly; this is not a LOC/nesting/state-concentration reduction.

Complete current report1670files/20290callables/1937errors/2747warnings/
4684findings,cognitive81276,cyclomatic83333,fileLOC332300.
R6 deltas are-1error/-2warnings/-43cognitive/-31cyclomatic/+19fileLOC.
The five>300 and seventeen>200 callable counts remain unchanged; Presenze420
is still extreme. No50% principal reduction or original campaign completion
is claimed. Independent AST exactness outside the two paths prevents unrelated
or moved debt from being silently attributed to this slice.

## Ratchet and baseline provenance

From verifier root, using existing backend Python environment:

```bash
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
make complexity-report QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python \
  REPORT_JSON=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/complexity.json \
  REPORT_MD=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/verifier/complexity.md
make complexity-check QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
```

Change gate PASS0, authoritative55a main baseline. Recorded global check
FAIL30/Makeexit2: all30 full finding objects exactly match frozenR5 final
global-check evidence. Zero attributableR6; not ignored or repaired.
Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No baseline-generation/repair/scope/threshold/exclusion/ignore changes executed.

## Terminal processes, cleanup and disposition

All exact process/exits persist under verifier evidence. FocusedPID370800,
units379378,build389376,pertinentE2E390899/fullE2E391585,
ratchet396642/report406546/globalcheck416489 are terminal. Own production
frontendPID390744/session66527 stopped normally after all suites; owned backend
container9b4276a5/proxye44a9544/internalnetwork removed. Final backend/proxy
logs retained, credential environment removed, loopback18090/13010free.
No other process/container/network cleanup performed; no live suite remains.

Verification disposition: **PASS WITH SEVEN EXISTING E2E SKIPS**.
Slice classification: **IMPROVED**, modest real aggregate simplification.
Full-file coverage100%, no change regressions, independent tests/build/browser
gates terminal. Graphify code/domain/platform refresh belongs to Coordinator
and author evidence; report changes no code boundaries and contains no new
claim of independent semantic graph extraction.

Remaining risks: external browser/map assets and synthetic/mocked domain
services, preexisting lint/build warnings and seven unverified scenarios.
Extreme frontend debt, Capacitas coverageFAIL and historical30 divergences
remain separate. This report authorizes no new responsibility, waiver, main
merge or campaign-completion claim.
