# R21 author — Capacitas job-action presentation ANALYZE report

## Ownership and admission

**ANALYZE ONLY / NO_CHANGE / STOP FOR COORDINATOR DECISION.** No runtime or test
has been modified and no heavy native gate has been run. This is not an accepted
refactoring or an IMPROVED slice. The exact scope can eliminate10 physical
duplicate decisions, but contains only15 principal cognitive points and cannot
meet the registry's mandatory minimum20-point principal reduction.

Allocation read before work:
`/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/docs/code-quality/MULTI_AGENT_OWNERSHIP_R21_CAPACITAS_JOB_ACTIONS_2026-10-10.md`.
Dedicated worktree:
`/home/cbo/CursorProjects/GAIA-campaign-20261010-r21-capacitas-job-actions`.
Branch: `refactor/complexity-r21-capacitas-job-actions`.
Initial clean HEAD: `1cd01a7949acb273edb30aa4dc9af27fd9e7d846`.
Authoritative merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Owned-path initial diff was empty; latest runtime commit `1f565147` is the
accepted R20 credential-policy change, followed by `9e9e5421`, `673026e7`,
`01a9ada4`, `b12780e2`. No concurrent runtime edit was observed.

Only this NEW report is currently writable. Workspace and tests stay read-only;
the optional new `campaign-capacitas-job-actions-r21.test.tsx` has NOT been
created. Old R20 trees, source, reports and private evidence were not changed.
No install, cleanup, commit, push, source import, baseline generation/repair,
threshold, exclusion, coverage configuration or ignore change occurred.

## Baseline and evidence

Workspace SHA256:
`34afe117a828dca307e90f72f1318ac17b4597e14f0e80a897601c8911fe8913`.
Baseline SHA256:
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Registry source baseline: principal339cognitive/316cyclomatic/2439LOC;
file836cognitive/977cyclomatic/3085effectiveLOC;31useState/2useEffect.
Current official aggregate1673files/20321callables/1926errors/2741warnings/
4667finding records belongs to the accepted R20 integration, NOT a fresh R21
global scan. The global objective remains ACTIVE/INCOMPLETE.

NEW private evidence root `E`:
`/home/cbo/.cache/gaia-campaign/20261010-r21-capacitas-author`.
`E/preflight.log` records initial clean status, HEAD/base/path history and22
existing campaign-spec hashes. `E/analyze-actions.cjs` parses only the actual
owned TSX using the installed Babel parser and performs a small read-only
census with the current scanner's decision/nesting vocabulary. It does not
invoke a global report, ratchet, test, provider or virtual candidate gate.
`E/action-census.json/.log/.exit` retain exact six action JSX strings, spans,
hashes and measured decision nodes; exit0, no parser diagnostics.

Graphify orientation used only the existing integration frontend corpus through
`make graphify-frontend-query Q="ElaborazioniCapacitasWorkspace"`: exit0,
BFS depth2/47nodes, `E/graphify-orientation.log/.exit`. No refresh or raw-root
Graphify invocation. Graph relationships orient ownership; they do not prove
complexity or behavior. Available disk was approximately3.8GiB; no cleanup.

## Exact three clusters

All spans refer to the unchanged actual original workspace.

| Family | Rerun button lines | Delete button lines | Class / captions | Original IDs / callbacks |
| --- | --- | --- | --- | --- |
| History | 2086–2088 | 2089–2101 | btn-secondary; Rerun.../Rilancia; Elimina.../Elimina | historyJobBusyId/historyDeletingJobId; handleRerunHistoryJob/handleDeleteHistoryJob |
| Terreni | 2581–2583 | 2584–2596 | btn-secondary; Rerun.../Rilancia; Elimina.../Elimina | terreniJobBusyId/terreniDeletingJobId; handleRerunJob/handleDeleteJob |
| inCass | 2804–2806 | 2807–2819 | btn-secondary; Rerun.../Rilancia; Elimina.../Elimina | incassJobBusyId/incassDeletingJobId; handleRerunIncassJob/handleDeleteIncassJob |

Each rerun button is disabled exactly when its family's busy ID equals
`job.id`, with a single caption ternary. Each delete button is disabled by
`deletingId === job.id || job.status === "pending" || job.status === "processing"
|| job.status === "queued_resume"`, with a single caption ternary. Rerun does
NOT become disabled merely for pending/processing/queued_resume; delete does
NOT gain cancelling/unknown-status blocking or borrow Particelle semantics.

All six `onClick` arrows read the captured job object's `id` at event time:
`() => void handle...(job.id)`. Do not eagerly execute commands or replace the
closure with a captured numeric ID. Family busy/deleting scalar state, token
guards, shared command execution and every request/result/error/effect remain
outside this presentation slice.

Keep existing containers exactly: History's action div contains just this pair;
Terreni's action div has preceding Dettagli/Errori siblings; inCass has a preceding
conditional progress badge. A shared component must emit a fragment, not a div,
span or one-off per-family wrapper. Those siblings/cards are excluded and cannot
be absorbed just to meet a complexity target.

## AST census and feasibility

The existing scanner counts LogicalExpression and ConditionalExpression nodes,
not individual equality operators or JSX elements. A `.map` callback and JSX
conditional do not add nesting in the current implementation. Each selected
button pair is under nesting0 relative to the principal. These are source
facts, not speculative metrics from a rewritten candidate.

| Exact action region | ConditionalExpression | LogicalExpression | Physical decisions | Principal cognitive contribution |
| --- | ---: | ---: | ---: | ---: |
| History pair | 2 | 3 | 5 | 5 |
| Terreni pair | 2 | 3 | 5 | 5 |
| inCass pair | 2 | 3 | 5 | 5 |
| Current three pairs | 6 | 9 | 15 | 15 |
| One genuinely reused pair, expected | 2 | 3 | 5 | Outside principal |

The read-only actual file census confirms423physical decisions and the principal
cognitive339/315physical decisions (cyclomatic316), matching the registry.
Removing all three pairs from the principal can therefore reduce its cognitive
by **at most15**, to324, and cyclomatic by15, to301. One shared pair retains5
decisions, giving10 genuine eliminated physical nodes and a file census423→413.
Expected aggregate cognitive836→826 and cyclomatic977→968 (+1 component callable)
are projections only, not measured candidate results. New component expected
cognitive5/cyclomatic6, nesting0 and1 props parameter, below thresholds.

| Mandatory registry acceptance target | Exact-scope projection | Outcome |
| --- | --- | --- |
| At least10 physical duplicated decisions removed | 15→5, reduction10 | Feasible |
| Principal cognitive at least20 lower | Maximum reduction15;339→324 | **Not feasible in this scope** |
| Aggregate reduction, no new finding | Projected-10 cognitive; not yet measured | Unverified until admission/gates |
| Below300 stretch | Principal324 minimum from this scope | Not attainable here |

No subtraction of aggregate overlapping callable attribution is misrepresented
as a principal reduction. Counting each status equality as a decision would
invent extra points. Including the inCass progress ternary, Terreni Dettagli/
Errori conditionals or other card branches would violate explicit ownership.
Do not add synthetic branches, padding, exclusions or artificial wrappers to
make the target appear satisfied. Accordingly **stop before implementation**.

## Proposed typed contract, only if Coordinator revises admission

The common responsibility is real despite the target mismatch. A minimal local
private component could accept:

```tsx
interface CapacitasJobActionsProps {
  job: Pick<CapacitasMonitoredJob, "id" | "status">;
  busyId: number | null;
  deletingId: number | null;
  onRerun: () => void;
  onDelete: () => void;
}
```

Pass the original job reference, not a newly constructed snapshot object.
Render the two existing `btn-secondary`/`type="button"` buttons in a fragment;
evaluate existing equality/short-circuit/status checks at render time and keep
the ternary labels unchanged. Parent passes its exact original arrows,
`onRerun={() => void handleRerunHistoryJob(job.id)}` and corresponding delete
and family callbacks. The child assigns these callbacks directly as onClick;
it does not read the numeric ID earlier or add an async wrapper. No hooks,
memoization, generic manager, state container or per-family dispatch is needed.

This preserves click-time reference access even if the API job object is
mutated without a rerender; renderer-disabled state intentionally still reflects
the preceding render, as originally. Normal immutable refreshed rows get new
callbacks through render. Keeping this distinction avoids conflating render
inputs, command dispatch timing and response capture. The minimal shape is
structurally compatible with all three actual job types. Props are not permission
or API policy; the existing commands still own validation/auth/mutations.

## Behavioral test matrix

Tests below were READ, not executed for R21. Earlier green R20 runs are not used
to certify R21. New tests, if separately authorized, must operate mounted public
workspace controls and literal expected API calls/DOM properties; no copied
component/policy implementation, synthetic coverage or source-string tests.

| Behavior | Existing characterization read | Genuine missing case | Proposed new R21 test | Current result |
| --- | --- | --- | --- | --- |
| Terreni status eligibility, including cancelling/cancelled/unknown | campaign-capacitas-terreni.test.tsx status-label matrix checks disabled deletion | Exact two-button DOM order/classes/type and no new wrapper | All3 families action DOM/parent/sibling assertions | NOT RUN |
| inCass pending/processing/queued_resume deletion blocked, rerun enabled | campaign-capacitas-incass-monitor.test.tsx three active-status cases | Full terminal/cancelling/unknown action-only matrix across families | Three-family public status matrix, literal eligibility | NOT RUN |
| History active monitoring and successful/error rerun/delete | campaign-capacitas-storico-monitor.test.tsx status polling + command cases | Direct complete action status/disabled matrix and blocked click no request | Matrix on mounted History cards | NOT RUN |
| Selected-ID rerun stays busy through deferred refresh; other row enabled | Terreni/storico/incass command tests | Busy/deleting independence when both action kinds overlap, not scalar same-kind behavior | Deferred rerun/delete on same/different rows; all3 families | NOT RUN |
| Existing scalar busy behavior for overlapping reruns on different IDs | campaign-capacitas-command-lifecycle-r12.test.tsx both settlement orders | Do not inadvertently normalize scalar lifetime to a Set | Preserve old spec unchanged; new pair caption check if needed | NOT RUN |
| Deletion affects only selected ID and no reload; races with list retained | campaign-capacitas-command-lifecycle-r12.test.tsx poll/manual and settlement-order cases | Presentation remains separate from backend result and siblings | Keep frozen suite; explicit DOM labels while pending | NOT RUN |
| Parent closure reads job.id at click time, not render time | No direct object-ID mutation/click case found in frozen22specs | Actual original row identity changed after render, rerun/delete dispatch late ID | Mutate retained API response job.id between render/click; assert literal token/new ID on all3 families, no eager call | NOT RUN |
| Blocked native delete buttons do not dispatch requests | Existing disabled assertions; action failure/token-loss guards | Explicit disabled-click attempt for all3 blocked statuses/families | Public click then zero remove calls | NOT RUN |
| Family isolation and selected callbacks | Four-family R12/API cases | Same numeric IDs across hidden families do not share busy state | Navigate while pending; verify independent action caption/disabled state | NOT RUN |
| Terreni Dettagli/Errori and inCass progress remain siblings, untouched | Existing report/modal/card checks | Exact adjacency/shared parent of actions before/after | Public DOM structural assertions with real result fixtures | NOT RUN |

Object-ID mutation probes characterize an existing timing contract rather than
authorize an application feature. Use real returned response references, never
compiled extracts of JSX. If the original mounted controls do not reproduce
the intended mutation timing, stop and explain rather than fabricate evidence.

## Conditional gate and coverage plan

**Not authorized/executed now.** If root admits this responsibility with a
realistic target, first add ONLY NEW
`frontend/tests/unit/campaign-capacitas-job-actions-r21.test.tsx`, then run fresh
actual ORIGINAL focused tests and full union before runtime modification.
Expected frozen baseline remains22specs/505cases; the new spec increases the
count by genuine UI cases. Record actual counts instead of predicting PASS.

From dedicated frontend tree, use the existing native configuration:

```bash
./node_modules/.bin/vitest run tests/unit/campaign-capacitas-job-actions-r21.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  ./node_modules/.bin/vitest run tests/unit/campaign-capacitas- --coverage --maxWorkers=1 \
  --coverage.reportsDirectory="$E/original-coverage"
```

After authorized exact local refactor, repeat identical focused/union commands
against actual modified runtime with NEW candidate log/coverage directories.
Raw complete-file statement/branch/function/line counters must each be100%,
with positive denominators, zero skips/missing/partial, and exact worktree paths.
No config/threshold/exclusion or copied/runtime-overlay coverage. Add genuine
missing scenarios only if root authorizes correction after any explained failure.

Native complete Make reports before/after and gate from worktree root:

```bash
make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/original-complexity.json" REPORT_MD="$E/original-complexity.md"
make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/candidate-complexity.json" REPORT_MD="$E/candidate-complexity.md"
make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 \
  QUALITY_PYTHON=backend/.venv/bin/python
```

Project `tsc --noEmit --incremental false`, explicit new-spec TypeScript using
actual source (project config excludes tests), existing-config scoped ESLint
with max-warnings0, source-only diff/custody audit and physical AST census must
also pass. One agent holds heavy; unexpected native failure stops and is retained
before any retry/correction. Independent reviewer reruns original/candidate
controls and native full-file/ratchet after source freeze, before publication.
Root owns accepted publication, integration, postcommit ratchet and dedicated
Graphify code/docs maintenance. Complete suite/build/E2E obligations remain
global campaign gates, not inferred from focused tests.

## Metric after / delta / classification

Actual runtime delta: **0 bytes**. Actual target metrics remain principal339/
316/2439 and file836/977/3085,31useState/2useEffect. No new source or test callable.
Candidate metrics above are feasibility projections, not certified evidence.
Current classification **NO_CHANGE — ANALYZED / TARGET_NOT_ATTAINABLE_IN_SCOPE**.
This does not claim architectural cleanup, characterization completion or
IMPROVED. Runtime implementation is held for Coordinator's decision.

## Files changed / commit / residual risks

Only NEW `reports/code-quality/SLICE_R21_CAPACITAS_JOB_ACTIONS_2026-10-10.md`.
No commit. No heavy activity needs waiting; author remains stopped after analysis.
Potential safe reuse is small and reviewable but cannot honestly meet20 points.
Main concurrent work, immutable baseline/tooling/shared paths and existing22
tests remain preserved; global historical30 and extreme tail remain separate.

## Recommended next action

Coordinator should either accept this genuinely shared action responsibility
with an explicit truthful15-point principal/10physical target, or reject/defer
R21 and allocate a different higher-impact coherent responsibility. That is an
admission decision, not a threshold/baseline change. Do not expand R21 into card
progress/error/response rendering or unrelated state merely to manufacture20.
No implementation or new test will be undertaken without explicit admission.

## Subsequent Coordinator admission and author execution — gate STOP

This appended section supersedes the historical ANALYZE-only disposition above;
the original analysis text remains unchanged and is preserved exactly as
`E/ANALYZE_REPORT_FROZEN.md`, SHA960349135f7ee3f8718d349e4abc7e43cf6d08d31f2d2c9e59e0e7d82f5ce0cf.
After an independent static reviewer confirmed mathematical maximum15 and no
substantive behavior blocker, Coordinator appended registry admission BEFORE
author followup: same exact action-only scope, honest principal reduction15 /
physical10 / aggregate at least10. No global-goal, scanner threshold, baseline,
coverage-policy or scope weakening. Principal below300 is NOT claimed.

### Characterization and actual source

ONLY NEW `frontend/tests/unit/campaign-capacitas-job-actions-r21.test.tsx` adds54
genuine mounted-public-control cases, with literal token/ID assertions and DOM
properties, not copied JSX/policies or synthetic coverage:

| Behavior | New expanded cases | Actual original | Actual candidate |
| --- | ---: | --- | --- |
| All three families: pending/processing/queued_resume blocked, terminal/cancelling/cancelled/unknown/case-sensitive/empty status policy; disabled delete attempts produce zero API calls | 33 | PASS | PASS |
| Actual retained API job reference ID mutated between render/click; rerun/delete dispatch literal92, not original11; no eager command | 6 | PASS | PASS |
| Same-row simultaneous rerun/delete in both orders; independent scalar IDs/captions; other row enabled; first failure clears only its own busy state | 6 | PASS | PASS |
| Same numeric11 across families stays isolated while navigating with pending rerun/delete | 6 | PASS | PASS |
| Direct parent/fragment shape, order, btn-secondary/type labels; Terreni Dettagli/Errori and inCass progress remain direct siblings | 3 | PASS | PASS |

All existing22specs remain unedited. Original focused54 and union559 across23
files passed BEFORE runtime modification. The identical focused/union commands
then passed on the actual modified source. No new skip/todo/error/failure in
those runs. Counts are genuine native JSON assertions, not hand-counted suites.

One private `CapacitasJobActions` component uses the original job reference,
family scalar IDs and exact parent callbacks. Its fragment emits only the two
existing buttons; all original containers/siblings survive. It has no hook,
memoization, callback wrapper, command execution or new external dependency.
The only runtime edits are this component/interface and exactly the three pairs.

`E/ast-custody.json/.exit` PASS0 proves the entire original/candidate AST equal
outside those exact regions (ignoring location/formatting metadata and whitespace-
only JSX text), both normalized hashes64b4dd939c17cca4899eaa6aba9cd7e1b6764f7fa22ca2755945402023beb05a.
All six parent arrow expressions are structurally exact and all three `job`
props are the original identifier, not an eagerly copied numeric ID/snapshot.
Thus command/effect/API/state/result/error/progress/Particelle logic is unchanged.

Actual candidate source SHA:
`7f9d7883680d10f536e058323f241413fc6192fce14ca634a1b181ae107d293c`.
New spec at the first gate STOP:
`c93e53fdcd03c09d60479dbb173fa60bdbba6cd52f70e94893f3ec5615f2effd`.

### Actual measured metrics, not the earlier projection

Both native complete Make reports passed0. `E/measured-metrics.json/.exit` PASS0
contains source census, full tuples and other-path equality proof.

| Metric | Actual original | Actual candidate | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 339 | 324 | -15 (-4.42%) |
| Principal cyclomatic | 316 | 301 | -15 |
| Principal LOC | 2439 | 2412 | -27 |
| Principal nesting / params | 2 / 1 | 2 / 1 | 0 / 0 |
| File aggregate cognitive | 836 | 811 | -25 (-2.99%) |
| File aggregate cyclomatic | 977 | 953 | -24 |
| Attributed sum(cyclomatic-1) | 727 | 702 | -25 |
| Physical distinct decision nodes | 423 | 413 | -10 |
| File effective LOC | 3085 | 3087 | +2 (disclosed) |
| Sum callable LOC | 4549 | 4517 | -32 |
| Callable count | 250 | 251 | +1 |
| File max nesting / params | 2 / 3 | 2 / 3 | 0 / 0 |
| useState / useEffect / useReducer | 31 / 2 / 0 | 31 / 2 / 0 | 0 / 0 / 0 |
| Imports / dependency count | 21 / 21 | 21 / 21 | 0 / 0 |
| Local Error / Warning records | 17 / 15 | 16 / 15 | -1 / 0 |
| Global files / callables | 1673 / 20321 | 1673 / 20322 | 0 / +1 |
| Global Error / Warning / records | 1926 / 2741 / 4667 | 1925 / 2741 / 4666 | -1 / 0 / -1 |

New reused component: cognitive5/cyclomatic6/LOC22/nesting0/params1, no finding.
Physical census removes4 conditional-expression and6 logical-expression sites;
all other node-kind counts are exact. The earlier estimated aggregate826/968
underestimated native nested `.map` attribution: actual811/953 is recorded here,
not25 independent decisions eliminated. Only10 distinct decision nodes disappear.
This is real shared presentation-policy deduplication, not a relocated mega JSX
block. FileLOC+2 is the disclosed typed/component boundary cost; it does not
erase aggregate/callable/physical reductions. Actual55a ratchet passed0.
All other native file/callable/finding objects are exact before/after.

### Native tests and full-file coverage

Native results: `E/original-focused.log/.exit/.json`54PASS0;
`E/original-union.log/.exit/.json`559PASS0/23files;
`E/candidate-focused.log/.exit/.json`54PASS0;
`E/candidate-union.log/.exit/.json`559PASS0/23files. Raw assertion-status audits
`E/{original,candidate}-tests-audit.jsonl/.exit` pass0; zero skipped/todo entries.

| Actual full-file runtime | Statements original→candidate | Branches original→candidate | Functions original→candidate | Lines original→candidate |
| --- | --- | --- | --- | --- |
| Workspace | 719/719→720/720 | 766/766→750/750 | 250/250→251/251 | 626/626→627/627 |
| Fraction policy, unchanged | 9/9→9/9 | 6/6→6/6 | 6/6→6/6 | 8/8→8/8 |
| Combined | 728/728→729/729 | 772/772→756/756 | 256/256→257/257 | 634/634→635/635 |

Each dimension100%, positive raw denominator, zero skipped maps/uncovered entries.
Exactly the two actual absolute author-runtime paths are present, not overlays or
synthetic copies. Raw source `E/{original,candidate}-coverage/coverage-final.json`;
counter/map audits `E/{original,candidate}-coverage-audit.json/.exit`, PASS0.
V8's16 branch-arm reduction is not the10 distinct source-decision reduction.

Exact native frontend commands used with new phase-specific output names:

```bash
./node_modules/.bin/vitest run tests/unit/campaign-capacitas-job-actions-r21.test.tsx \
  --maxWorkers=1 --reporter=default --reporter=json --outputFile.json="$E/original-focused.json"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  ./node_modules/.bin/vitest run tests/unit/campaign-capacitas- --coverage --maxWorkers=1 \
  --coverage.reportsDirectory="$E/original-coverage" --reporter=default --reporter=json \
  --outputFile.json="$E/original-union.json"
./node_modules/.bin/vitest run tests/unit/campaign-capacitas-job-actions-r21.test.tsx \
  --maxWorkers=1 --reporter=default --reporter=json --outputFile.json="$E/candidate-focused.json"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  ./node_modules/.bin/vitest run tests/unit/campaign-capacitas- --coverage --maxWorkers=1 \
  --coverage.reportsDirectory="$E/candidate-coverage" --reporter=default --reporter=json \
  --outputFile.json="$E/candidate-union.json"
```

Make commands before patch and after tests, using actual root source:

```bash
PYTHONDONTWRITEBYTECODE=1 make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/original-complexity.json" REPORT_MD="$E/original-complexity.md"
PYTHONDONTWRITEBYTECODE=1 make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON="$E/candidate-complexity.json" REPORT_MD="$E/candidate-complexity.md"
PYTHONDONTWRITEBYTECODE=1 make complexity-ratchet \
  BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 QUALITY_PYTHON=backend/.venv/bin/python
```

Both reports and native immutable55a Make ratchet exit0, findings[]; raw logs and
exits retained. No self-baseline, changed BASE_REF or projected comparator gate.
Private utilities audit native evidence rather than replacing native commands.
No successful native gate was restarted.

### NEW gate failure and exact stop

Project `./node_modules/.bin/tsc --noEmit --incremental false` passed0,
`E/project-type.log/.exit`. Explicit new-spec program
`node "$E/type-new-spec.cjs"` then **FAIL1**, `E/new-spec-type.log/.exit`:

```text
tests/unit/campaign-capacitas-job-actions-r21.test.tsx:88:73 TS2353:
Object literal may only specify known properties, and 'exact' does not exist in type 'ByRoleOptions'.
Actual imported worktree runtime files: 135; diagnostics: 1
```

Cause: newly authored test used `getByRole("button", { name, exact:true })`, an
unsupported typed role-query option. Testing-library's string name matcher is
already exact by default; proposed correction removes only this unsupported
option, keeping its string matcher and every assertion. This is a new test
typing defect, not a demonstrated runtime regression, but it fails an allocated
gate and cannot be ignored. Author stopped BEFORE any correction/retry and
notified Coordinator; `E/NEW_SPEC_TYPE_FAILURE_ATTEMPT1.md` retains diagnosis.
Scoped ESLint was NOT RUN because the command sequence immediately stopped.
No final freeze, READY, independent acceptance or integration is claimed.

Space was recorded before each heavy phase in `E/*-space.log`; approximately
2.1–2.3GiB remained. No install, build, cleanup, repeated report copy or Python
bytecode cache was created. Runtime and all22 old specs/config/shared paths/
baseline remain untouched outside the exact source slice; final full custody
certification remains pending along with the failed type gate and lint.

### Current classification and next action

**BLOCKED — NEW_SPEC_TYPE_GATE**, author heavy RELEASED pending root allocation.
Measured reduction satisfies the explicitly revised admission, but cannot be
classified as an accepted IMPROVED slice until all allocated gates and independent
review pass. No commit/import/publication. The full campaign remains incomplete;
principal324 is still extreme and whole suites/build/E2E/globalcheck are not run
or inferred from focused evidence. Await explicit correction authorization;
do not widen the scope or weaken the test assertions/policy.

## V2 — Allocated correction and final author evidence

The sections above are preserved historical evidence, not current gate results.
Coordinator appended the bounded V2 allocation to the authoritative ownership
registry before implementation. The ONLY correction is removing unsupported
`exact:true` from the new spec's role query, retaining `{ name }`; the installed
string role-name matcher already uses exact equality. No assertion, runtime,
configuration, policy, baseline, scanner threshold or ownership was broadened.

Attempt1 failed spec/report/type log/exit/diagnosis remain byte-exact under
`E/failed-type-attempt1-preserved.sha256`. Final corrected spec SHA:
`409b5da6fc4eed9a18eae39f6e56700d194353d134cb02a6fd4f1569913826e2`.
Original ANALYZE and failed-attempt report remain exact prefixes of this report.

### Original/candidate source recovery and custody

Runtime was temporarily restored with controlled reverse `apply_patch` to exact
ORIGINAL `34afe117a828dca307e90f72f1318ac17b4597e14f0e80a897601c8911fe8913`,
verified with `cmp` against the original byte snapshot BEFORE V2 original gates.
The corrected final spec ran on that actual worktree runtime, not an overlay.

At context handoff there was no separate frozen candidate TSX snapshot. Root
explicitly authorized reapplying the SAME original four-hunk patch, with a hard
requirement to match the previously measured candidate hash. Restored source is
EXACT `7f9d7883680d10f536e058323f241413fc6192fce14ca634a1b181ae107d293c`;
there is no redesigned or newly refactored runtime. Candidate bytes, corrected
spec and exact diff are now frozen separately in `E/V2_CANDIDATE_FROZEN.tsx`,
`E/V2_SPEC_FROZEN.tsx`, `E/V2_SOURCE_DIFF_FROZEN.patch` with manifest
`E/v2-restored-frozen.sha256`. Before/after restoration source bindings are in
`E/v2-before-restoration.sha256` and `E/v2-candidate-test-input.log`.

### Fresh V2 behavior matrix

| Behavior | Final tests | Actual original | Actual candidate |
| --- | ---: | --- | --- |
| Three-family status matrix, disabled attempted clicks produce no API request | 33 | PASS | PASS |
| Retained job-object ID mutated before click; literal92 dispatch, no eager call | 6 | PASS | PASS |
| Independent rerun/delete scalar IDs, captions and error settlement ordering | 6 | PASS | PASS |
| Same numeric11 across families remains isolated during pending/navigation | 6 | PASS | PASS |
| Exact direct parent/classes/type/order and existing siblings | 3 | PASS | PASS |
| All22 immutable existing specs | 505 | PASS | PASS |

Both actual runtimes: focused54 PASS and union559 PASS/23files, zero failures,
pending/skipped/todo assertions. Native JSON/log/exit use fresh names
`E/v2-{original,candidate}-{focused,union}.*`. Status audits are
`E/v2-{original,candidate}-tests-audit.log/.exit`, PASS0.

### Fresh V2 full-file coverage

| Actual runtime | Statements original→candidate | Branches original→candidate | Functions original→candidate | Lines original→candidate |
| --- | --- | --- | --- | --- |
| Workspace | 719/719→720/720 | 766/766→750/750 | 250/250→251/251 | 626/626→627/627 |
| Fraction policy, unchanged | 9/9→9/9 | 6/6→6/6 | 6/6→6/6 | 8/8→8/8 |

All four dimensions100%, raw-positive denominators, zero skipped/uncovered map
entries and EXACT actual worktree runtime paths. Native files:
`E/v2-{original,candidate}-coverage/coverage-final.json`; raw map/counter audits:
`E/v2-{original,candidate}-coverage-audit.log/.exit`, PASS0. The command/config is
identical to the earlier documented native test command, with V2 output names;
no synthetic coverage, config edit, exclusion or dependency installation.

### Fresh V2 types, lint, measurement and ratchet

Both original and candidate project `tsc --noEmit --incremental false` PASS0;
the explicit corrected-spec TypeScript program imports135 actual runtime files,
reports zero diagnostics and PASS0. Scoped ESLint `--max-warnings=0` over the
workspace, fraction policy and all23 Capacitas specs PASS0 on both runtimes.
Exact logs/exits: `E/v2-{original,candidate}-{project-type,new-spec-type,scoped-lint}.*`.
The historical TS2353 failure remains preserved; it is not erased or relabeled.

Fresh full native reports `E/v2-{original,candidate}-complexity.json/.md/.log/.exit`
both PASS0. `E/v2-native-report-binding.jsonl/.exit` proves all summary/files/
callables/violation objects exactly equal their separately retained attempt1
native reports, binding the reused read-only metric auditor to V2 native data.
Fresh physical census/metric output `E/v2-measured-metrics.json/.exit` PASS0;
fresh outside-scope AST/callback/job-reference proof `E/v2-ast-custody.json/.exit`
PASS0, outside normalized source hash64b4dd939c17cca4899eaa6aba9cd7e1b6764f7fa22ca2755945402023beb05a.

| Metric | Actual before | Actual after | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive / cyclomatic / LOC | 339 / 316 / 2439 | 324 / 301 / 2412 | -15 / -15 / -27 |
| File cognitive / cyclomatic aggregate | 836 / 977 | 811 / 953 | -25 / -24 |
| Physical distinct decisions | 423 | 413 | -10 |
| Callable-attributed decisions, overlapping | 727 | 702 | -25, NOT25 physical |
| File effective LOC | 3085 | 3087 | +2, disclosed |
| Callable count / sum callable LOC | 250 / 4549 | 251 / 4517 | +1 / -32 |
| File useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |
| Local error / warning finding records | 17 / 15 | 16 / 15 | -1 / 0 |
| Global files / callables | 1673 / 20321 | 1673 / 20322 | 0 / +1 |
| Global error / warning / all finding records | 1926 / 2741 / 4667 | 1925 / 2741 / 4666 | -1 / 0 / -1 |

Genuine three-family reuse removes4 physical ternaries and6 physical logical
nodes, not just relocating decisions. Helper cognitive5/cyclomatic6/LOC22/
nesting0/params1 is below every fixed callable threshold, with no finding.
Other paths' complete file/callable/violation objects are EXACTLY unchanged.
Principal -15 (-4.42%), aggregate cognitive -25 (-2.99%); the former20-point
projection and below300 target are NOT claimed. The +2 fileLOC increase is
explicitly visible, not hidden; the actual fixed ratchet permits this candidate.

Actual native `make complexity-ratchet BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2`
with `QUALITY_PYTHON=backend/.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`:
PASS0, authoritative baseline_commit55a, findings[]. Evidence:
`E/v2-actual55a-ratchet.log/.exit`. No baseline inflation, self-baseline,
threshold/exclusion change, comparator projection or automatic gate retry.

### Author terminal and remaining obligations

Classification: **IMPROVED — author evidence; independent acceptance pending**.
Status: **READY_FOR_REVIEW**, terminal STOP / EXCLUSIVE HEAVY RELEASED after
final custody/freeze. Only the three allocated repository paths changed;
HEAD1cd01a7949acb273edb30aa4dc9af27fd9e7d846 and merge-base55a unchanged,
all22 old specs and authoritative baseline38e6 unchanged, main diff9f85 and
status0d54 preserved. Final raw custody report/exit and source/spec/report freeze
are `E/v2-final-custody.json/.exit` and `E/V2_FINAL_INPUTS.sha256`.

No commit, import, publication or independent ACCEPT is delegated or claimed.
Fresh independent original/candidate native review must precede publication;
coordinator still owns integration/Graphify maintenance. Full application suites,
build, E2E and global historical-divergence check were NOT run or inferred here.
The campaign remains ACTIVE/INCOMPLETE; principal324 is still above300.

Disk snapshots are retained before every V2 heavy phase. Shared-host free disk
dropped from2.13GB to about445MB during candidate tests while author evidence
was only36MB. Root later reported explicitly user-authorized cache-only cleanup,
bringing free space to about817MB. Author did no cleanup/build/install and did
not modify active caches, existing evidence or concurrent work.

Recommended next action: independent native review of these exact frozen inputs,
then coordinator-only serial integration gates if accepted. Do not widen R21
into a second responsibility or classify the whole campaign as complete.
