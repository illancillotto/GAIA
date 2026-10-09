# R7 Presenze Anomaly Panel — Independent Final Verification

## Ownership and frozen source

This certifies only anomaly-panel ordering/grouping/count preparation. The
principal remains extreme; the original global campaign is ACTIVE/INCOMPLETE.

- Initial clean integration: `ef322424ff54e829daee5e4bd5bd01a7aab1ebb7`.
- Author source: `d879d2681841f2bbab6b885648ed6cfa8e847c1c`.
- Independent review: `a7341048abdd7a5b4877c1606dda675275d894dc`, APPROVED.
- Coordinator approval read verbatim from durable `VERIFY_APPROVAL.txt` before
  source application, tests or build; author/reviewer heavy suites terminal.
- Verifier source cherry-pick: `be4bc39540835dca3d166c44e6308ed83c6c27d1`.
- Worktree: `GAIA-campaign-20261009-r7-presenze-verification`.
- Branch: `verify/complexity-r7-presenze-anomaly`.
- Main/authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Verifier owns only this report. All five author files exactly match approved
source; the duplicate verifier source commit is not an integration deliverable.
No runtime/test/config edit, main merge, push or PR. Dirty main is not input,
copied, reset, stashed or committed. Worktree clean before this report.

| Frozen path | Git object |
|---|---|
| page.tsx | `f6b0f446a059c90b430a5da6b23f5dcd13ec1f1d` |
| anomaly-panel-model.ts | `6fc277fdef4ac20ff400e484c69da0d3a971ca0a` |
| frontend/src | `a16b5a9166a7ceeee6a07534bbf5a8296d0405e7` |
| frontend/tests | `d2239845b94a58c6197980deb1c3c8e7edfdaac5` |
| backend/app | `3e8bfdbaf692bbcbed3d24dccff11a7605d62049` |
| worker | `93d944ad6fa702e6f1407d1111d8ea5fe20fa06e` |

Backend, worker, shared frontend lib/hooks/UI/layout, tooling, quality config,
Makefile, manifests, Playwright/Vitest config and registered baseline unchanged.
No new skip, ignore, retry, timeout, exclusion, coverage waiver or gate change.

## Behavioral and characterization evidence

Independent verifier whole-program AST comparison removes only the three moved
types/score function/model imports and masks exactly four authorized memo
callbacks. Everything else is identical, including all75 hook calls in order
and their dependency arrays. Classification/filtering, first selection, JSX,
commands, permissions, lifecycle and state are not silently changed.
Original page SHA256 `c6dfa496e22acaa6634ed3fb9cb725606a567e50045579eebc70d10f289fc91e`;
candidate `06d0bec08f2f521d888e61fd2fdc892047333289d242382ce8f3da39be3c05b5`.

Priority arithmetic and strict `!==0` preserve NaN short-circuit. Month order
priority/date/name, day order priority/name, collaborator order priority/date,
native stable ties, Map insertion, duplicate references, exact-kind counts,
empty comparison fallback versus ID label fallback, and copied-array sorting
are exercised by independent focused execution of the committed tests.

Reviewer differential artifacts were separately inspected: original snapshot
hash matches verifier initial source; helper hash matches exact frozen model.
180 original-AST fixtures/2917 entries,59593 exact comparator pair results,
720 filtered grouping checks and3 throwing downstream-access traps passed.
The final verifier does not claim to have rerun that reviewer oracle. Verifier
own whole-program AST and fresh suites are additional independent evidence.

| Behavior | Existing tests | Added characterization | Final verification |
|---|---|---|---|
| Filters/counts/first-action selection | page/regressions |4UI cases |PASS |
| Priority/date/name and stable ties | page/regressions |model cases |PASS |
| NaN/undefined/null/infinities | broad page tests |UI/model traps |PASS |
| Empty/missing labels and duplicate identity | broad page tests |frozen-input model cases |PASS |
| Day/collaborator grouping and input immutability | page tests |UI/model cases |PASS |
| Commands, authorization, async transitions | unchanged existing suites |none outside ownership |PASS; protected AST exact |

Original characterization precedes runtime edits as proven by source/reviewer
reports and retained original test outputs, not by a post-refactor assertion.

## Tests

Durable evidence:
`/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/`.
External `run.cjs` records exact command, CWD, PID, timestamps, signal, terminal
exit and bounded-output logs. Heavy suites/build/browser execute serially;
no process is restarted because of an observation timeout. JUnit and V8 raw
counters are independently audited, not inferred from a headline percentage.

| Gate | Terminal result | Runner duration |
|---|---|---:|
| Focused6files |424PASS,0skip/failure/error,exit0 |34.316s |
| Complete frontend units |4428PASS/300files,0skip/failure/error,exit0 |100.907s |
| Typecheck |PASS,exit0 |22.386s |
| Owned ESLint |0errors,3old page warnings,exit0 |1.172s |
| Complete npm run lint |PASS with existing repository warnings,exit0 |8.709s |
| npm test smoke |18PASS,0skip/failure,exit0 |0.143s |
| Fresh production build:clean |PASS,exit0 |56.546s |
| Pertinent Presenze E2E |7PASS,0skip/unexpected/flaky,exit0 |10.280s |
| Complete E2E |54PASS,7existing skips,0unexpected/flaky,exit0 |71.431s |
| Complete AST report |PASS,0parse/exception errors,exit0 |42.595s |
| Ratchet/main |PASS0findings,exit0 |43.735s |
| Recorded-baseline global check |FAIL30,Makeexit2 |51.811s |

Raw test duration100.26s units,9.671s pertinent E2E and70.871s full E2E differs
from runner elapsed time. Existing page warnings independently reproduced via
ESLint stdin on initial source: unused detail-loading state and two effect
dependencies, unchanged except line positions. Full lint/build warnings are
not described as a zero-warning repository. New model/test emit no warning.

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/app/presenze/giornaliere/anomaly-panel-model.ts \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  tests/unit/presenze-giornaliere-r6.test.tsx tests/unit/presenze-giornaliere-r7.test.tsx \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/focused-coverage \
  --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/focused-junit.xml
npm run test:unit -- --maxWorkers=4 --reporter=default --reporter=junit \
  --outputFile.junit=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/full-unit-junit.xml
npm run typecheck
node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx \
  src/app/presenze/giornaliere/anomaly-panel-model.ts tests/unit/presenze-giornaliere-r7.test.tsx
npm run lint
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build:clean
```

## Coverage

| Modified complete runtime | Statements | Branch outcomes | Functions | Coverage |
|---|---:|---:|---:|---|
| page.tsx |1048/1048 |1189/1189 |288/288 |100% |
| anomaly-panel-model.ts |39/39 |16/16 |18/18 |100% |

Combined1087statements/1205branches/306functions/888lines100%; every raw
counter positive, zero missing arms. Existing supported explicit coverage
include selects both entire modified files, not just changed lines. Versioned
100% thresholds, exclusions and coverage strategy remain unchanged. No claim
of full-repository100% coverage. Backend/worker full suites not freshly rerun
for this frontend-only slice; priorR5 evidence remains separate.

## Isolated fresh browser stack

Fresh verifier source production build, not reusedGIS/R6 build artifacts.
Installed Next15.5.25/React18.3.1/MapLibre6.9.0/Playwright1.59.1/Vitest4.1.6.
Own frontend loopback13011, proxy loopback18091. Exclusive Docker internal
network `gaia-r7-presenze-verifier-20261009`, backend and proxy with the same
owned prefix. Backend uses exact verifier/backend read-only `/app`, metadata
schema creation and real startup/uvicorn; syntheticSQLite on `/e2e`tmpfs and
`/data`tmpfs. Container image supplies dependencies, not trusted application
source. No production DB, credentials, volumes or service touched.

Fresh random credentials created0600, never printed, privately mapped into
the E2E runner and deleted at cleanup. Prepared health200 after initial proxy
startup connection000; frozen source health/login readiness200 before tests.
Backend actual `/auth/login` HTTP200 recorded. Readiness is not a suite PASS.
External Playwright config imports unchanged versioned config; only locations,
reporters, workers1, local baseURL and stable public deviceID supplied. No auth
token/cookie seeded by verifier. DeviceID avoids exhausting synthetic device
allocation without changing enforcement; committed fixtures can explicitly
mock API/auth as before. Mocked Presenze scenarios exercise real production UI
but do not certify live INAZ/GATE, PostGIS, externalGIS or MCP providers.

Browser147.0.7727.15,1280x720,dpr1,default motion: separate browser observation
proves reduced-motion=false. Project timeout90000ms, expect20000ms and retries0
unchanged; all actual result retries0. No native gesture/timing/readiness
predicate or motion modification used to obtain green results.

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18091 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/playwright.config.ts \
  tests/e2e/presenze-operational-controls.spec.ts \
  tests/e2e/presenze-hierarchy.spec.ts tests/e2e/presenze-whatsapp-dashboard.spec.ts
PLAYWRIGHT_BASE_URL=http://127.0.0.1:18091 npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/playwright.config.ts
```

Bootstrap admin variables must be loaded privately from newly generated owned
environment; public commands alone do not recreate disposable credentials.

## Existing skips — not PASS

| Scenario | Cause | Unverified impact |
|---|---|---|
| catasto-anagrafica.spec.ts:14 |Single search removed, bulk-only |Removed single-search flow |
| catasto-drilldown.spec.ts:14 |No synthetic districts seeded |District/parcel drilldown |
| catasto-drilldown.spec.ts:52 |No synthetic districts seeded |District/anomaly drilldown |
| gis-territorio.spec.ts:381 |OptionalGIS flag not enabled |Optional responsiveGIS smoke |
| gis-territorio.spec.ts:439 |OptionalGIS flag not enabled |Optional territory/QGIS smoke |
| wiki-mcp-console.spec.ts:3 |Isolated gateway opt-in required |LiveMCP console |
| wiki-mcp-preview.spec.ts:3 |Provider/fixture opt-in required |LiveMCP/model flow |

Exact titles/annotations in e2e-full.json/e2e-audit.json. Seven existing skips,
not seven passed or newly hidden tests. No runtime/source workaround applied.

## Metrics and classification

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive |420 |403 |-17(-4.05%) |
| Principal cyclomatic |371 |356 |-15 |
| Principal callable LOC |2076 |2020 |-56 |
| Principal nesting/params |2/0 |2/0 |0/0 |
| Affected cognitive sum |1222 |1192 |-30(-2.45%) |
| Affected cyclomatic sum |1309 |1284 |-25(-1.91%) |
| Affected callable LOC |4499 |4433 |-66 |
| Affected effective file LOC |2855 |2879 |+24 |
| Affected callable count |304 |308 |+4 |
| Affected error/warning findings |17/21 |17/21 |0/0 |
| Page useState/useEffect |21/13 |21/13 |0/0 |

Affected complete page plus new model includes all nested callbacks, not only
the principal. Model18callables/max cognitive3/cyclomatic4/LOC17/nesting2/
params2; zero findings. Real shared comparator/group/count deduplication,
not movedJSX or a mega-helper. Classification IMPROVED for cognitive,
cyclomatic and callableLOC; not fileLOC/finding/nesting/state concentration.
The +24fileLOC increase is explicit rather than laundered.

All unaffected complete AST file/callable objects exactly match frozenR6;
engines/include/exclude unchanged. Verifier full-report objects independently
equal Coordinator final report, not merely its summary. Current1671files/
20294callables/1937errors/2747warnings/4684findings, cognitive81246,
cyclomatic83308,fileLOC332324. Five>300/seventeen>200 remain; principal403
is still extreme. Initial Presenze50%/under250 and global targets NOT achieved.

## Ratchet and baseline provenance

```bash
make complexity-report QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python \
  REPORT_JSON=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/complexity.json \
  REPORT_MD=/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/verifier/complexity.md
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
make complexity-check QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python
```

Change gate PASS0, registered global check FAIL30/Makeexit2. Every historical
finding object exactly equals R6, zero attributableR7; new global totals reflect
one model/four net callables and separately match the current AST report.
Baseline byte-identical to initial source; SHA256
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No baseline-generation/repair, threshold, scope or exclusion modification.

Two explained external verification-harness errors retained in
provenance-first-harness-error.json: initial overstrict whole-summary comparison
against R6 rejected the expected +1file/+4callable totals; subsequent git-show
default1MB subprocess buffer was insufficient for baseline bytes. Final audit
compares all finding objects exactly, current summary against current report,
and baseline bytes with a bounded32MB buffer. No runtime/test/gate change or
suite restart, and failed audit attempts are not declared PASS.

## Graphify and terminal cleanup

Author dedicated forced frontend-code target and Presenze-docs exits0 inspected;
docs chunk1/2 and2/2 done, zero semantic failure,46nodes49edges8communities.
Verifier does not claim its own graph refresh; Coordinator maintains integration
graphs. No graph artifacts committed. Report is outside the docs corpus.

All suites/build/report/check processes terminal with retained exits. Own
frontendPID518238 stopped normally/exit0; named proxy/backend containers and
internal network removed, ports18091/13011 free, private credentials deleted.
cleanup.json independently asserts absence and scope, no unrelated cleanup.

## Files, commit, risks and next slice

Verifier final commit contains this report only; actual report SHA returned to
Coordinator after commit. Do not cherry-pick duplicate source be4bc395.
No main merge/push/PR. Source remains exact approved d879d268. Residual risks:
synthetic/mock integrations and seven skipped scenarios are not certified live
domain behavior; coverage is execution evidence, not equivalence alone; extreme
principal403,21states13effects, Capacitas coverageFAIL and historical30 remain.
Stop this responsibility. Coordinator must assign any next coherent extreme
frontend slice separately after green integration; do not extend this verifier
or claim original campaign completion.
