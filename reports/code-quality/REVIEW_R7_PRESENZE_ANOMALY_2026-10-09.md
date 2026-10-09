# R7 Presenze anomaly panel — Independent Review

## Ownership

Reviewer worktree `GAIA-campaign-20261009-r7-presenze-review`, branch
`review/complexity-r7-presenze-anomaly`, initial commit
`ef322424ff54e829daee5e4bd5bd01a7aab1ebb7`. Authoritative main and merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Sole writable repository path is
this report; source and tests remain read-only. Main dirty work is not input.

Integration ownership registry was read before review. Dedicated frontend
Graphify query used for orientation after the Presenze backend corpus query
reported its graph absent. No Graphify artifacts or configuration are edited.

## Design Review

CONDITIONALLY SAFE; this is not final source approval.

One responsibility: anomaly-panel comparator and grouping/count preparation.
The proposed typed domain comparator factory shares priority/date/name steps;
the collector shares insertion-ordered grouping and exact anomaly/analysis
counting. Separate day and collaborator builders retain their actual outer
order. No JSX relocation, giant helper or reducer/command/effect migration.

Mandatory invariants:

- Priority score remains `base * 100000 - operational_missing_minutes`.
  `NaN` is returned immediately because `NaN !== 0`; no `||`, coercion,
  normalization or fallback through subsequent tie-breakers is allowed.
- Month order is priority/date/name; day-item order priority/name;
  collaborator-item order priority/date. All existing `localeCompare` calls,
  comparator signs and stable ties remain unchanged.
- Comparator missing-name fallback is empty string; collaborator group-label
  fallback is collaborator ID. Empty labels, nullish names and absent map
  entries remain distinct. No identity reconciliation is introduced.
- Group order is day locale order or collaborator blocking-count/total/name
  order. Duplicate items, references, first insertion and original input
  immutability survive. A copied array is sorted, not the input array.
- Classification, record filtering, initial selected record, all commands,
  state/effect/memo ordering/dependencies, lifecycle, API and UI are unchanged.
- Original characterization precedes runtime edits; full-file coverage100%,
  independent original-AST differential, true affected aggregate reduction,
  zero helper findings and ratchet/mainPASS0 are prerequisites to approval.

## Independent Baseline

Reviewer executed the existing five focused suites, serially after the author:

```text
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx
npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx
  tests/unit/presenze-giornaliere-regressions.test.tsx
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts
  tests/unit/presenze-giornaliere-r6.test.tsx --maxWorkers=2
```

Terminal exit0:413PASS, full-page1094/1094statements1217/1217branches
302/302functions895/895lines,100% every metric, no skips.
No coverage policy, configuration, exclusion or thresholds were changed.

Original source frozen with SHA256
`c6dfa496e22acaa6634ed3fb9cb725606a567e50045579eebc70d10f289fc91e`.
Independent executable oracle extracts original comparator and memo callbacks
directly from the TypeScript AST;180 deterministic fixtures2917 entries cover
priority crossovers, negative/large minutes, NaN/undefined/null/infinities,
empty/missing/nullish/accented names, duplicate references and stable ties.
Frozen original outputs are persisted before any candidate source exists.

Independent protected AST baseline records71 untouched top-level functions,
75 hook calls with order/dependencies,107 principal statements with only the
four target callbacks masked, and464 unchanged principal JSX nodes.

Full AST complexity report generated independently with unchanged engine,
scope and baseline. Principal420cognitive371cyclomatic2076LOC remains extreme;
this review does not certify the initial50%/under250 target or global campaign.

## Final Source Review

APPROVED, strictly for source commit
`d879d2681841f2bbab6b885648ed6cfa8e847c1c` and its five owned files.
Coordinator explicitly authorized applying this frozen source to the reviewer
worktree, where its duplicate source cherry-pick is `7307d091`.
This duplicate is not an integration deliverable: integrate the author source
and the subsequent report-only reviewer commit, never both source copies.

Independent full-file after run:424PASS, six focused suites, zero skipped,
failed or error tests; exit0 and JUnit424tests/0failures/0errors confirmed.
Page1048/1048statements1189/1189branches288/288functions;
model39/39statements16/16branches18/18functions. Every metric100%, no missing
statements/branches, no coverage skips/exclusions added. Coverage JSON audited
directly rather than relying on rounded percentages.

Reviewer independently reran the final4UI characterization cases against the
original frozen page:4PASS,7 intentionally unselected new-model test cases,
not skipped integration tests. Original first execution had failed setup
resolution because the command CWD differed from the temporary config root;
retry from the declared root passed. Both failure and retry evidence retained;
this was a verification-harness path error, not a runtime failure.

Independent original-AST differential PASS:180 fixtures2917entries,
59593 exact month comparator pair results includingNaN,720 filtered grouping
checks, and3 throwing downstream-access traps proving NaN short-circuit.
Sorted outputs, counts, fallback labels, duplicates and original object/array
immutability agree with the oracle frozen before the candidate existed.
Frozen-source hashes match the candidate reviewed before commit.

Protected AST PASS:71 other top-level functions,75 hook calls and their exact
order/dependencies,107 principal statements with only four target callbacks
masked, and464 principal JSX nodes unchanged. The original score helper is
replaced only inside the bounded typed anomaly model. Classification, filters,
first selection and all unrelated effect/command/state/UI logic stay identical.
All five source/doc/test/report files match author commit bytes exactly.

### Metrics

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive |420|403|-17|
| Principal cyclomatic |371|356|-15|
| Principal effective callable LOC |2076|2020|-56|
| Principal nesting |2|2|0|
| Principal params |0|0|0|
| Affected cognitive, page plus model |1222|1192|-30|
| Affected cyclomatic, page plus model |1309|1284|-25|
| Affected effective callable LOC |4499|4433|-66|
| Affected file LOC |2855|2879|+24|
| Affected callable count |304|308|+4|
| Affected findings |38|38|0|
| Page useState |21|21|0|
| Page useEffect |13|13|0|

Model maxima cognitive3/cyclomatic4/LOC17/nesting2/params2; zero findings.
The aggregate reduction proves genuine shared comparator/grouping/counting
deduplication rather than merely relocating the old callable. Extra file LOC
is disclosed, not called an improvement; finding counts are unchanged.
The counts helper deliberately keeps the original two exact-kind filters:
unknown kinds are not automatically counted as analysis. No opportunistic
data normalization or complexity-laundering helper is introduced.

### Behavioral Matrix

| Behavior | Existing | Added | Independent check | Result |
| --- | --- | --- | --- | --- |
| Panel filters/counts/first selection | page/regression suites |4UI cases|Original-page replay; protected AST|PASS|
| Priority/date/name precedence | page suites |Model direct cases|59593 original-AST pair comparisons|PASS|
| Day/collaborator grouping/order | page suites |UI/model cases|180 fixtures and720 filtered checks|PASS|
| NaN and null arithmetic | indirect coverage |UI/4 nonfinite/model cases|Exact comparator equality and3 access traps|PASS|
| Empty/missing labels and duplicates | page suites |UI/frozen-input cases|Original-AST output/reference check|PASS|
| Unrelated React commands/lifecycle | existing413 cases |unchanged|71functions75hooks464JSX protected|PASS|

### Gates

- `make complexity-report` before and after:exit0; engines and configured
  include/exclude scope identical. The one extra measured file is the new model,
  not a scope configuration change. No baseline or exception update.
- `make complexity-ratchet BASE_REF=main`:PASS0findings,exit0, authoritative
  merge-base55a. No main/source/shared/tooling/coverage configuration edit.
- `npm run typecheck`:PASS,exit0.
- Focused ESLint source/new model/new test:exit0, no errors. Three old page
  warnings independently reproduced from the original source, unchanged except
  moved line numbers; no warnings on the model or test.
- Author forced frontend Graphify and Presenze docs completed; reviewer did
  not alter graph artifacts. Fresh complete frontend/build/browser gates belong
  to the separate final verifier; they are not claimed as run by this reviewer.

## Files Changed

Author source: `frontend/src/app/presenze/giornaliere/page.tsx`, adjacent
`anomaly-panel-model.ts`, `frontend/tests/unit/presenze-giornaliere-r7.test.tsx`,
`domain-docs/presenze/docs/ANOMALY_PANEL_REFACTOR_2026-10-09.md`, and
`reports/code-quality/SLICE_R7_PRESENZE_ANOMALY_2026-10-09.md`.
Reviewer own change: this report only.

## Evidence

Durable root
`/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/reviewer/`:
`before.json`, `before.md`, `before-metrics.log`/`.exit`,
`before-tests.log`/`.exit`, `before-coverage/coverage-final.json`,
`original-page.tsx`, `oracle.mjs`, `original-oracle.json`,
`invariants.mjs`, `invariants.json` and Graphify query logs;
`after.json`/`.md`, `after-metrics.log`/`.exit`, `after-tests.log`/`.exit`,
`after-junit.xml`, `after-coverage/coverage-final.json`, `audit.mjs`/`.json`,
`differential.mjs`/`.json`, `frozen-differential.log`/`.exit`,
original-characterization config/logs/exits, `ratchet.log`/`.exit`,
`typecheck.log`/`.exit`, and before/after lint logs/exits.

## Classification

IMPROVED, bounded real cognitive/cyclomatic/callable-LOC reduction.
No claim of50% principal reduction, under250 target, fewer aggregate findings
or completed strategic campaign: principal403 remains extreme. Next slice is
for the Coordinator to assign separately after final integration gates; this
reviewer stops without editing further runtime responsibilities.
Global campaign remains ACTIVE/INCOMPLETE; the historical30 baseline divergences
and separate Capacitas coverage failure cannot be absorbed by this slice.
