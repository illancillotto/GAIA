# R34 Presenze — Complexity Slice Report

## Ownership

One responsibility: deduplicate monthly operational-summary selection and
presentation policy shared by the collaborator grid and dialog. Owned runtime
is only `frontend/src/app/presenze/giornaliere/page.tsx`. Existing seven public
mounted specs and all runtime companions/configuration remain immutable.
Coordinator registry precedes this worktree and author activation.

## Baseline

Author worktree starts at `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde`;
actual main/merge-base is `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Original page SHA256
`d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
Historical R26 rejected candidate was not copied or overwritten.

## Target callable

`PresenzeGiornalierePage`: cognitive385, cyclomatic341, callable LOC2023,
nesting2. File: cognitiveSUM1093, cyclomaticSUM1231, effectiveLOC2812,
308callables,21useState,13useEffect.

## Behavioral invariants

- Exact summary DOM, ordered label/value text, classes, leading spaces,
  Extra-only bottom border and intentional grid/modal emerald700/800 difference.
- Grid supplements remain direct-grid div pairs with keyed React Fragments;
  absence cause keys retain their own map domain and original `contents` wrapper.
- Extra eligibility remains strictly positive. Saturday sorting mutates the
  original array anew for each original render site; no copying/memoization.
- Absences are copied from the same Map, descending minutes with stable ties.
  Per-absence evaluation remains tone, then label, then formatted value.
- No hook/state/effect, cleanup, mutation command, API, auth, identity or
  aggregation changes. Canonical GAIA-INAZ identity is entirely out of scope.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| All eight summary-presence combinations, exact two-layout classes/borders | summary-r26 | None | None | Original PASS |
| Known/unknown causes, stable ties, Saturday chronology | summary-r26 | None | None | Original PASS |
| Zero/negative extra, cause-key collision, dialog reopen, async refresh | summary-r26 | None | None | Original PASS |
| Full page state/API/lifecycle regression surface | page,regressions,r6,r7,r8,r9 | None for this responsibility | None | Original PASS |

No redundant new test is proposed: the genuine public characterization already
covers this responsibility. No test is weakened, removed or skipped.

## Changes

Coordinator admitted exact NEW prospective bytes after fresh original100 and
independent `ADMIT_OBSERVABLE_EQUIVALENCE`. Source matches admitted SHA
`194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111`.
Conditional ordered supplemental descriptors eliminate repeated eligibility
and border decisions; separate absence projection retains cause keys. No new
component, hook, runtime file, generic schema or filter callback was introduced.

The eager model preserves per-absence tone→label→value ordering,
but moves these pure formatting calls before existing header formatters and
moves the pure Saturday-policy lookup after Saturday preparation. Independent
review proves observable equivalence using plain JSON typed primitive inputs,
internally allocated totals/Map/Saturday facts, total deterministic formatters,
independent enum lookup and no sideeffects/aliased reads. This is explicitly NOT
literal evaluation-trace equality.

## Metric before

Fresh native whole report exists in `author-evidence/original/complexity.json`.
Page metrics above agree with accepted original; no baseline modification.
Global1673files20323callables1924errors2739warnings4663findings.

## Metric after

Fresh native whole report `author-evidence/candidate/complexity.json` confirms
principal367/323/1988/nesting2, helper6/7/32/nesting0/params1/no finding.
File cognitiveSUM1062, cyclomaticSUM1201, effectiveLOC2809,309callables;
useState21/useEffect13 unchanged. Global1673files20324callables1922errors
2741warnings4663findings. File violations13error19warning→11error21warning:
two existing errors downgrade to warnings, not two new independent problems.

## Delta

Principal cognitive−18(−4.68%)/cyclomatic−18(−5.28%)/LOC−35(−1.73%).
File cognitiveSUM−31(−2.84%)/cyclomaticSUM−30(−2.44%)/LOC−3(−0.11%).
Normalized SUM(cyclomatic−1)923→892(−31). Duplication/aggregate decision debt
actually fall; new helper stays below every warning threshold. This is not
wrapper/move-only reduction. Extreme-tail counts stay5>300/17>200/55>100.

## Tests

Fresh original AND candidate native Vitest:496PASS/7specs,0failure,0pending;
each exits0. No skipped/todo case. Full-project `npm run typecheck --
--incremental false`0; scoped `next lint --file src/app/presenze/giornaliere/page.tsx`0.
Only three unchanged legacy warnings: unused `isLoadingRecordDetail`, effect
dependencies `closeSelectedRecord` and `contractProfileEditor`.
Explicit seven paths: `presenze-giornaliere-page`, `regressions`, `r6`, `r7`,
`r8`, `r9`, `summary-r26`, all under `frontend/tests/unit`, ending `.test.tsx`.
Command uses installed Vitest `--maxWorkers=1 --coverage --reporter=json`,
`VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx`, absolute
output and coverage directories; existing four100% thresholds unchanged.

## Coverage

Original full-file100:1035/1035statements,1139/1139branch outcomes,
306/306functions,847/847lines. Candidate full-file100:1041/1041statements,
1119/1119branch outcomes,307/307functions,854/854lines. Native V8/Istanbul JSON
counters checked: all statement, branch and function counters positive on both
runs. Twelve original inputs and eleven candidate protected inputs pass custody;
candidate source matches admitted SHA. No policy/config change.

## Ratchet

Actual `make complexity-ratchet BASE_REF=main` exits0 with `findings: []` against
`55a1b1d35911451e018b662c2acc450bf5994ea2`. No alternate base, baseline repair,
threshold/exclusion/ignore edit. Whole before/after reports and diff-check0.
Historical global30 is deliberately not absorbed or relabelled by this slice.

## Classification

IMPROVED / READY_FOR_REVIEW. Author gates pass and aggregate objective falls
without transfer; independent final review/integration remain Coordinator gates,
not a claim of campaign completion.

## Files changed

Only owned page and this NEW report. No new test needed. Private evidence:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/author-evidence`.
Before/after command argv/log/exit, native report, test JSON/raw coverage and input
manifest are retained there. Installed dependency directories are symlinks;
no installation or package/config modification.

## Commit

None; publication/commit belongs exclusively to Coordinator.

## Residual risks

Independent static observable-equivalence admission is recorded; native after
gates pass. Independent final reviewer/verifier and root integration remain
required. Historical global30 and whole-campaign suites stay separate. Principal
cognitive367 remains extreme; this slice does not close the larger hotspot.

Patch transport first rejected Git-coordinate hunk headers before source/native
candidate mutation. Bare `@@` conversion applies identical admitted bytes.
A report-only append precondition also rejected out-of-order hunk anchors before
mutation; reordered anchors resolve this documentation transport issue. Both
receipts are preserved. No native test/gate failed or was retried/weakened.

## Recommended next slice

None authorized. Stop after this responsibility; deliver exact bytes/evidence to
Coordinator for independent review/final verification. No further mutation,
successful-gate rerun, commit, merge or push by this author.
