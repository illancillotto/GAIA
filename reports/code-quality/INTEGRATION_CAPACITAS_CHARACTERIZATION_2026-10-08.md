# Capacitas — Independent characterization integration

## Ownership and snapshot

Independent Integration Agent `characterization_integration`, authorized in
`docs/code-quality/MULTI_AGENT_OWNERSHIP_2026-10-08.md` before work. Own only
this report and the three approved sequential test-only cherry-picks.
Integration worktree `GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`; initial HEAD
`43d4d9df1a315bb2915dab942776be3502696d66`, clean preflight. Merge-base main
remains `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Coordinator governance/report commits progressed concurrently on the same
integration branch, on separately owned paths. No coordinator file was edited
or staged by this agent; no main worktree, runtime, existing test, shared
configuration, threshold, baseline or complexity tooling was changed.

## Reviewed sources and sequential integration

| Slice | Source commit | Integrated commit | Independent source tests | Integrated cumulative tests | Ratchet |
|---|---|---|---:|---:|---|
| C6 Certificati | `7bc9ec173f8b42ee3332c8778bab0fe1b03f5da6` | `a7e21e9e` | 30 PASS | 30 PASS | PASS, 0 findings |
| C7 Anomalie | `bc312caf70e08140ed1d3ae9a2601e9d0385d611` | `c8ba3972` | 39 PASS | 50 PASS | PASS, 0 findings |
| C0 Credentials/shell | `14615c27d2207261d1ce5c2764a595ac600c2054` | `b52ab0af` | 36 PASS | 67 PASS | PASS, 0 findings |

Source worktrees were clean and shared the identical Capacitas runtime hash.
Each source commit adds exactly its exclusive new test spec and slice report.
Sources were reviewed and tested independently before their cherry-picks;
integration proceeds one slice at a time, with focused tests and authoritative
`make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python`
after each. No overlap, merge conflict, cycle, new runtime layering or component
explosion occurs: all three changes are test-only.

The final 67 cases comprise 19 unchanged batch cases and 48 new cases:
C6 11, C7 20, C0 17. Zero skips. Counts in earlier rows are cumulative, not
additional independent cases to sum into a global test count.

## Behavioral review matrix

| Responsibility | Observable behavior checked | Review outcome |
|---|---|---|
| C6 payload/result | Public controls dispatch exact token, nullable/numeric credential, limit and throttle; result values and tones | PASS |
| C6 async command | Old result/error clearing, busy/duplicate-click guard, edits affect only subsequent payload, deferred resolution/rejection | PASS |
| C6 failures/token | Explicit auth classification, Error/non-Error rejection, retry, token loss before/after dispatch | PASS |
| C6 polling | Real pending Terreni job continues polling while re-fetch is busy; unmount cleans timer/listener | PASS |
| C7 list | Explicit refresh only; API order, empty/nullable display, timestamps, loading/duplicate guard, previous rows retained on failure | PASS |
| C7 resolution | First/changed candidate, exact fraction and fetch flag, only successful row removed, empty candidates disable dispatch | PASS |
| C7 failure/async dialog | False result, Error/non-Error and real ApiError paths; busy close disabled, enabled radio change preserves dispatched payload, reopen resets | PASS |
| C0 credentials | Empty/single/multiple active/inactive pools, four independent selections, backend delegation and delayed singleton loading | PASS |
| C0 ordering | Delayed StrictMode replay preserves manual selections; credential error can be cleared by successful Terreni loading | PASS |
| C0 navigation/shell | Six panels, prop-driven section changes, retained forms, mount-only loading, embedded/protected boundary, settings open/close contract | PASS |

Tests import and render the real workspace. Doubles stay at API/auth and
ProtectedPage/modal boundaries; they do not prove actual authorization or native
modal internals. Error paths use explicit API rejection exports, not accidental
missing-mock-export exceptions. Deferred promises model valid async ordering.
StrictMode replay characterizes development effect replay, not a new production
refresh feature. Disabled-control assertions use ordinary DOM events; no
private closure/setter capture, artificial handler invocation, runtime exports,
patched language primitives, impossible parser fixtures or coverage ignores.

Isolated spec-local API doubles repeat necessary boundary setup, not domain
logic. Shared test-support extraction was deliberately not added to this scope.
No source assertion was weakened or production behavior changed at integration.
Agents' initial test-construction failures and corrections remain in their
individual reports; independent integration runs have no new unexplained failure.

## Independent full-file coverage

Fresh V8 runs on integration include the entire unchanged workspace, using the
existing `VITEST_COVERAGE_INCLUDE` mechanism and all four unchanged 100% gates.
Before runs only the existing 19 batch tests; after runs batch+C6+C7+C0.
Raw counters were read from actual `coverage-final.json`; line counters use
Istanbul `getLineCoverage`. Percentages were not added across source reports.

| Metric | Before covered/total | After covered/total | Covered delta | Before % | After % |
|---|---:|---:|---:|---:|---:|
| Statements | 305/857 | 401/857 | +96 | 35.58 | 46.79 |
| Branch arms | 263/929 | 371/929 | +108 | 28.31 | 39.93 |
| Functions | 46/251 | 89/251 | +43 | 18.32 | 35.45 |
| Lines | 288/748 | 365/748 | +77 | 38.50 | 48.79 |

Before tests **19 PASS**, after tests **67 PASS**, both commands **exit 1**
because the full-file 100% thresholds remain unmet. Coverage gate is **FAIL**,
not PASS. Remaining: 456 statements, 558 branch arms, 162 functions, 383 lines.
This checkpoint permits integrating meaningful test-only characterization,
not a Capacitas runtime refactor or bypass of the runtime coverage policy.

Artifacts:

- `/tmp/gaia-capacitas-integration-before-coverage/coverage-final.json`, SHA256
  `262fd42e82ff43dc05a3c7c3ffc259d95bcf1f851205a3a8fc5e19e6b1f7f877`.
- `/tmp/gaia-capacitas-integration-after-coverage/coverage-final.json`, SHA256
  `80e14ac94fdd5e2b33a4c0c955cab45f25259bd33b3ea52611244144d2535d65`.
- `/tmp/gaia-capacitas-integration-counters.json`, exact covered/total counts.
- `/tmp/gaia-capacitas-integration-{before,after}-coverage.log`, exit1 threshold
  failures preserved, not suppressed or presented as test failures.

Reproduction from integration frontend:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration-before-coverage

VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  tests/unit/campaign-capacitas-certificati.test.tsx \
  tests/unit/campaign-capacitas-anomalie.test.tsx \
  tests/unit/campaign-capacitas-credentials.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration-after-coverage
```

## Runtime preservation and metrics

Runtime SHA256 remains
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`;
original batch test SHA256 remains
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
Git diff versus preflight is empty for all runtime trees and protected
config/tooling/Makefile paths. No baseline inflation, scope or threshold change.
Fresh scoped AST report `/tmp/gaia-capacitas-integration-complexity.json`
has identical `files` and `callables` objects to source before evidence.

| Runtime metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive / cyclomatic | 472 / 416 | 472 / 416 | 0 / 0 |
| Principal LOC / nesting / params | 2631 / 2 / 1 | 2631 / 2 / 1 | 0 |
| File cognitive / cyclomatic sum | 1099 / 1174 | 1099 / 1174 | 0 / 0 |
| Effective file LOC / callable count | 3109 / 251 | 3109 / 251 | 0 / 0 |
| File error / warning / finding count | 24 / 20 / 44 | 24 / 20 / 44 | 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |

Classification for every integrated slice:
**NO_CHANGE — CHARACTERIZATION_ONLY**, never `IMPROVED`.

## Other gates and limits

- Explicit TypeScript check of all three new test files PASS using disposable
  `/tmp/gaia-capacitas-integration-test-tsconfig.json`; normal project config
  excludes tests, so this check deliberately includes them without repo edits.
  Log `/tmp/gaia-capacitas-integration-new-tests-typecheck.log`.
- Scoped Next ESLint for all three specs PASS, no lint errors or warnings;
  existing Next16 deprecation notice recorded in
  `/tmp/gaia-capacitas-integration-lint.log`.
- `git diff --check` PASS. Sequential ratchet logs
  `/tmp/gaia-capacitas-integration-{c6,c7,c0}-ratchet.log` each show
  `baseline_commit=55a1b1d35911451e018b662c2acc450bf5994ea2`, empty findings.
- Source focused logs `/tmp/gaia-capacitas-integration-{c6,c7,c0}-focused.log`;
  integrated focused logs use suffix `-integrated.log`.
- Dedicated `make graphify-frontend-query` executed for orientation, exit0;
  broad match led to unrelated anomaly nodes, so direct source review is the
  authority here. No runtime boundary/dependency changes requiring code refresh.
  Coordinator handles any required platform-doc graph refresh after governance.
- No new full-suite, build, E2E or live external portal certification is claimed.
  Historical R3 results are not reused as execution evidence for these new tests.
- Global baseline/provenance remains separately owned and unresolved historic
  findings must not be absorbed. This agent does not rerun/reclassify that audit.

## Stop and next checkpoint

Three approved test-only slices are integrated and independently verified.
Stop this ownership here. Other Capacitas sections and legitimate full-file
coverage closure need separate assigned owners and cumulative measurements.
Defensive/library-sensitive arms need provenance rather than fabricated tests.
Capacitas runtime remains **BLOCKED_BY_FULL_FILE_COVERAGE**. Future runtime
waves remain held pending Coordinator's explicit GIS residual-risk decision;
this characterization does not implicitly accept that risk or complete the
global complexity campaign.
