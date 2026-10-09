# R8 Presenze Presentation — Independent Final Verification

## Ownership and frozen source

This certifies only the finite daily-record label/badge presentation slice.
The global campaign remains ACTIVE/INCOMPLETE; principal399 is still extreme.

- Initial clean verifier HEAD: `c518727e0239aba1b3fceb7d854c4a30b862626a`.
- Author frozen source: `79bc9969d17111a098d37bc22e4e15f7172feb7d`.
- Independent review: `687a4a4928603664c61ea8b04cedf0e97f36e854`, APPROVED/IMPROVED.
- Exact verifier source cherry-pick: `a0c145b69326bf76f8add289e67a9db4172dbea0`.
- Main/authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Worktree: `GAIA-campaign-20261009-r8-presenze-verification`.
- Branch: `verify/complexity-r8-presenze-presentation`.

Coordinator durable `VERIFY_APPROVAL.txt` was read completely before source
application, tests or build. Author/reviewer heavy processes were terminal.
All four author blobs were verified exactly; verifier owns only this report.
The duplicate verifier source commit is NOT an integration deliverable.
Dirty main is not copied, modified, reset, stashed, committed or merged.

| Frozen path | Git object |
|---|---|
| frontend/src/app/presenze/giornaliere/page.tsx | `556c23d63cb06283ed11f4b2a823682b16caa1b2` |
| frontend/tests/unit/presenze-giornaliere-r8.test.tsx | `88686f94951f06348fcc078f87fa0edfb4c32387` |
| domain-docs/presenze/docs/RECORD_PRESENTATION_REFACTOR_2026-10-09.md | `514540dca29e7f578d9114950cd850103d0a1930` |
| reports/code-quality/SLICE_R8_PRESENZE_PRESENTATION_2026-10-09.md | `598329e69da2a5529a501e54f1085b0e778806c9` |
| frontend/src | `84d0c3d8e70e1cc02a694cfe880a81d9c12beeb1` |
| frontend/tests | `eb32eb9420c551a499bcaa3371dabe6bced048cd` |
| backend/app | `3e8bfdbaf692bbcbed3d24dccff11a7605d62049` |
| worker | `93d944ad6fa702e6f1407d1111d8ea5fe20fa06e` |

Runtime/tests/configuration stayed read-only throughout verifier execution.
Backend, worker, shared frontend lib/hooks/UI/layout, tooling, manifests,
Makefile, quality/coverage/Playwright configuration and baseline are unchanged
by this slice. No ignore, exclusion, retry, timeout or skip was introduced.

## Behavioral invariants and characterization

Fresh verifier whole-program AST comparison masks only the three assigned
label policies and one FormulaGAIA variant/text pair, removing the exact five
added helpers/eight local policy declarations. All other program AST is exact,
including all75 complete hook calls and dependency arrays. No lifecycle,
state, effect, cleanup, command, permission, API, classifier, DOM, controlled
input, tooltip/header or identity-mapping change is silently accepted.

Original SHA256 `06d0bec08f2f521d888e61fd2fdc892047333289d242382ce8f3da39be3c05b5`;
candidate `134a8b04c1dcd28ac8dd73b4e3a94bc24fe927f863256dfd4e28da8a3a1162f4`.
These equal reviewer independently frozen hashes. Original characterization
preceded runtime edits: retained author/reviewer424original tests plus44new
rendered original tests prove this; verifier does not claim their old execution
as a fresh verifier run. Final verifier independently executes all468 cases.

Reviewer oracle artifacts were separately inspected:2800adversarial fixtures,
13kinds,84020exact original-output comparisons and10FormulaGAIA pairs,
no input mutation. This verifier does not claim to have rerun that oracle.
Its own complete AST proof and fresh suites provide additional evidence.

| Behavior | Existing test | Added characterization | Fresh result |
|---|---|---|---|
| Primary substring priority, trim and nullish status fallback | page/regressions | R8 rendered label cases | PASS |
| Unknown/inherited keys and absence-cause fallback | page/regressions | R8 inherited-key/unknown cases | PASS |
| Authorization→extra→travel→KM→request secondary precedence | page/R6 | R8 cross-surface cases | PASS |
| Null/zero/negative/NaN/infinite minutes and holiday suppression | page/R6 | R8 edge cases | PASS |
| Detail regolare override and Formula known/unknown status pairs | page/regressions | R8 exact text/variant cases | PASS |
| Commands, permissions, transitions and async behavior | page/regressions/E2E | no changes outside slice | PASS; protected AST exact |

## Tests and reproducibility

Durable evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/`.
External `run.cjs` records command/args/CWD/PID/timestamps/signal/terminal exit
and private bounded-output logs. Heavy suites, build, browser and scanner gates
run serially; live handles are polled, never restarted for an observation timeout.
JUnit/V8/browser JSON counters are audited directly rather than inferred from
headline percentages. All entries below are terminal, not planned or live.

| Gate | Actual terminal result | Runner elapsed |
|---|---|---:|
| Focused7files |468PASS,0skip/failure/error,exit0 |36.999s |
| Complete frontend units |4472PASS/301files,0skip/failure/error,exit0 |102.766s |
| Typecheck |PASS,exit0 |24.147s |
| Owned ESLint |0errors,3unchanged page warnings,exit0 |1.242s |
| Complete npm run lint |PASS with existing repository warnings,exit0 |9.383s |
| npm test smoke |18PASS,0skip/failure,exit0 |0.147s |
| Fresh npm run build:clean |PASS,exit0 |59.521s |
| Pertinent Presenze E2E |7PASS,0skip/unexpected/flaky,exit0 |10.353s |
| Complete E2E |54PASS,7existing skips,0unexpected/flaky,exit0 |70.128s |
| Complete complexity report |PASS,0parse/exception errors,exit0 |43.981s |
| Ratchet/main |PASS0findings,exit0 |45.661s |
| Recorded-baseline global check |FAIL30historicalfindings,Makeexit2 |54.647s |

Raw test durations102.07s units,9.707s pertinent E2E and69.565s full E2E are
distinct from runner elapsed time. Existing page warnings were freshly reproduced
from original source via ESLint stdin and matched by exact message/rule: unused
detail-loading state and two effect dependencies. Full lint/build retain other
legacy warnings; this is not a zero-warning repository. New R8 tests emit no
owned lint warning.

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  tests/unit/presenze-giornaliere-r6.test.tsx tests/unit/presenze-giornaliere-r7.test.tsx \
  tests/unit/presenze-giornaliere-r8.test.tsx \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/focused-coverage \
  --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/focused-junit.xml
npm run test:unit -- --maxWorkers=4 --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/full-unit-junit.xml
npm run typecheck
node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx tests/unit/presenze-giornaliere-r8.test.tsx
npm run lint
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build:clean
```

## Coverage

| Modified complete runtime | Statements | Branch outcomes | Functions | Lines |
|---|---:|---:|---:|---:|
| frontend/src/app/presenze/giornaliere/page.tsx |1033/1033 |1143/1143 |294/294 |846/846 |

All100%, all raw counters positive, zero uncovered arms. The established explicit
coverage include selects the entire modified file, not changed lines/functions.
Thresholds/exclusions/configuration remain unchanged. No claim of full-repository
100% coverage: separate Capacitas coverage failure is not waived by this result.
Backend/worker full suites were not freshly rerun for this frontend-only slice;
previous campaign verification remains separate evidence, not a new PASS.

## Isolated fresh browser stack and cleanup

Fresh production build from frozen verifier source, not reusedR7/GIS artifacts.
Installed Next15.5.25,React18.3.1,Playwright1.59.1,Vitest4.1.6. BuildID retained
in `build-id.txt`. Frontend loopback13012, proxy loopback18092; own internal
Docker network `gaia-r8-presenze-verifier-20261009`. Backend/proxy use the same
owned prefix. Backend image supplies dependencies only; exact verifier backend
is mounted read-only `/app`, syntheticSQLite `/e2e` and `/data` are tmpfs.
Metadata schema creation and real startup/uvicorn execute from this source.
No production database, environment, volume, credentials or service is touched.

Fresh random credentials are created0600, privately loaded into browser runners,
never printed, and deleted. Prepared health200 followed an initial connection000
before proxy startup; retry is recorded readiness, not a suite PASS. Production
login pageHTTP200 and21actual backend auth/loginHTTP200 requests are retained.
External Playwright config imports unchanged versioned configuration, overriding
only output locations/reporters/workers1/local URL/stable public deviceID.
No auth cookie/token is injected. Real/mock boundaries are unchanged: committed
mocked Presenze flows exercise production UI, not live INAZ/GATE/PostGIS/MCP.

Browser147.0.7727.15,1280x720,dpr1,default motion: independent observation proves
reduced-motion=false. Project timeout90000ms,expect20000ms,retries0 unchanged;
every actual retry0. No timing, readiness predicate, motion or assertion workaround.

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18092 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/playwright.config.ts \
  tests/e2e/presenze-operational-controls.spec.ts tests/e2e/presenze-hierarchy.spec.ts \
  tests/e2e/presenze-whatsapp-dashboard.spec.ts
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18092 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/playwright.config.ts
```

New bootstrap credentials must be loaded privately; public commands alone do
not recreate them. Owned frontendPID657419 normally terminated/exit0; all owned
containers/network removed, ports13012/18092 free, backend.env deleted.
`cleanup.json` asserts terminal state; no live verifier suite/service remains.

## Existing skips — not PASS

| Scenario | Recorded cause | Unverified impact |
|---|---|---|
| catasto-anagrafica.spec.ts:14 | Single search removed, bulk-only | Removed single-search flow |
| catasto-drilldown.spec.ts:14 | No synthetic districts seeded | District/parcel drilldown |
| catasto-drilldown.spec.ts:52 | No synthetic districts seeded | District/anomaly drilldown |
| gis-territorio.spec.ts:381 | OptionalGIS flag disabled | Optional responsiveGIS smoke |
| gis-territorio.spec.ts:439 | OptionalGIS flag disabled | Optional territory/QGIS smoke |
| wiki-mcp-console.spec.ts:3 | Isolated gateway opt-in required | LiveMCP console |
| wiki-mcp-preview.spec.ts:3 | Provider/fixture opt-in required | LiveMCP/model flow |

Seven skip titles/annotations/locations exactly matchR7 after normalizing only
absolute worktree prefixes. Raw JSON retains full paths. No new skipped test.

## Metrics and classification

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive |403 |399 |-4(-0.99%) |
| Principal cyclomatic |356 |352 |-4 |
| Principal callable LOC |2020 |2020 |0 |
| Principal nesting/params |2/0 |2/0 |0/0 |
| Complete page cognitive sum |1172 |1109 |-63(-5.38%) |
| Complete page cyclomatic sum |1249 |1230 |-19(-1.52%) |
| Complete page callable LOC |4326 |4319 |-7 |
| Effective file LOC |2778 |2788 |+10 |
| Callable count |290 |296 |+6 |
| Error findings |17 |13 |-4 |
| Warning findings |21 |20 |-1 |
| Total metric findings |38 |33 |-5 |
| useState/useEffect |21/13 |21/13 |0/0 |

Primary helper53→11cognitive,secondary40→8,detail badge13→3. All five new
helpers plus callback have zero findings,max cognitive9/cyclomatic8. Local
finite policy removes actual decisions and duplicated badge conditional pairs,
not movedJSX, wrapper laundering or component explosion. Counts describe metric
findings, not independent problems. Classification IMPROVED for aggregate
cognitive/cyclomatic/callableLOC/findings; fileLOC+10 explicitly disclosed.

All unaffected complete file/callable AST objects exactly equal before; full
report files/callables/violations/engines/scope/schema/summary/parser results
exactly equal Coordinator integration report, excluding expected provenance/
timestamp/source-commit differences. Current1671files20300callables1933errors
2746warnings4679findings,cognitive81183,cyclomatic83289,fileLOC332334,
callableLOC327719. Five>300/seventeen>200 remain. Initial Presenze50%/under250
and global targets are NOT achieved; this is a bounded slice certification.

## Ratchet and baseline provenance

```bash
make complexity-report QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python \
  REPORT_JSON=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/complexity.json \
  REPORT_MD=/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/verifier/complexity.md
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
make complexity-check QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
```

Change gate PASS0; recorded global check FAIL30/Makeexit2. Every finding object
exactly equals historicalR7,zeroR8attribution; summary matches current report.
Registered baseline byte-identical to authoritative55a, SHA256
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No generation/repair, threshold inflation, scope/exclusion/ignore/config edit.

## Audit harness errors and Graphify

Preserved/explained external audit errors are not application regressions:
initial read-only schema inspection used files.find on a keyed object; initial
skip comparison wrongly included different absolute worktree prefixes; original
ESLint stdin launched from root instead of frontend and exited127. Raw failure
outputs/terminal codes and `HARNESS_ERRORS.txt` are retained. Only external audit
code/CWD was corrected; no test/runtime/config/source modification or suite
restart. Subsequent raw-counter/provenance/warning audits pass.

Coordinator Graphify logs independently inspected: forced frontend AST649/649,
6027nodes12618edges224communities; Presenze docs76nodes78edges13communities,
chunk1/1done,zero semantic failures,gpt-reserve. Generated graphs not committed.
Final platform-governance docs refresh remains Coordinator closure responsibility.

## Files changed, commit and residual risks

Sole verifier deliverable is this report; report-only commit SHA is returned
separately after commit. Never integrate duplicate verifier sourcea0c145b6.
All gates terminal and cleanup complete. No main merge,push or PR.

Residual principal399/2020LOC and21state/13effect concentration remain, as do
historical30global divergence and separate Capacitas coverage failure. Existing
mock/skip boundaries do not prove live external-service equivalence. Recommended
next action: Coordinator review/integrate report-only, post-report ratchet and
platform Graphify checkpoint; then separately owned coherent extreme-tail slice.
Global campaign remains ACTIVE/INCOMPLETE.
