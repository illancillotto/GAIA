# R34 — Independent Presenze Summary Final Verification

## Verdict and ownership

**ACCEPT_IMPROVED** for ONE monthly operational-summary projection responsibility.
The whole GAIA campaign remains **ACTIVE / INCOMPLETE**; this is not certification
of final repository suites or the original Presenze 50% reduction milestone.

Verifier owns this NEW report and private `final-evidence/` only. Coordinator
published the exact reviewed candidate into the verifier checkout using
`apply_patch`; verifier did not edit runtime, tests, shared files, configuration,
baseline, scope, thresholds or exclusions, and did not commit/merge/push.

- Worktree: `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/final-worktree`.
- Branch: `verify/complexity-r34-presenze-summary`.
- HEAD: `3e4ad9f030370a2d21cd4c28a6f7cc569c287dde`.
- Actual `main` and merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Original page SHA: `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
- Candidate page SHA: `194686c9f2887ff8551289081e9c483023e0047692753a8f3b522429520a6111`.

## Baseline and target

Runtime: `frontend/src/app/presenze/giornaliere/page.tsx`.
Target: remove duplicated Extra/Saturday/absence summary policy from the grid
and collaborator dialog, rather than relocate the page body or add a wrapper.

Fresh original report and mounted public tests completed before Coordinator
published candidate bytes. Existing seven specs remain byte-exact; the rejected
R26 runtime candidate was neither imported nor overwritten. No NEW spec needed:
existing R26 cases plus six broader specs already characterize this responsibility.

## Behavioral invariants

- Identical visible row ordering, labels, hours, classes, border policy, grid
  and dialog DOM; Extra eligibility stays strictly positive.
- Absences remain sorted by descending aggregate minutes with stable Map
  insertion order for ties; cause keys remain separate from supplement keys.
- Saturday sorting still mutates the SAME `totals.saturdayEntries` array once
  per existing summary evaluation; no copy, memoization or lifecycle timing change.
- Absence projection retains tone → label → value evaluation order. Formatting
  moves before unrelated headers: total, effect-free primitive formatting and
  locally allocated totals justify **observable equivalence**, not literal
  function-call trace equality. No permission to commute arbitrary effects.
- `buildMonthlyOperationalSummary` is NOT generally pure: the preexisting
  in-place Saturday sort is deliberately retained.
- State/effect declarations, dependencies, handlers, cleanup, API/auth/INAZ
  identity boundaries, input identity and mutation flows remain unchanged.

## Characterization test matrix

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| All 8 Extra/Saturday/absence combinations; exact two-layout DOM/classes | `presenze-giornaliere-summary-r26.test.tsx` | No | No | Before/after PASS |
| Known/fallback absence labels and tones; hours formatting | R26 summary parametrizations | No | No | Before/after PASS |
| Descending absence totals and stable ties | R26 tie-order case | No | No | Before/after PASS |
| Saturday ordering, separators and unworked-day absence | R26 Saturday cases | No | No | Before/after PASS |
| Negative/zero/positive Extra eligibility | R26 eligibility cases | No | No | Before/after PASS |
| Supplement/absence key collisions; dialog close/reopen identity | R26 key-collision case | No | No | Before/after PASS |
| Async KM update refreshes both summaries without replacing input/API drift | R26 pending/resolve transition | No | No | Before/after PASS |
| Existing page/filter/poll/mutation/render/error regressions | Six original mounted specs | No modified behavior uncovered | No | Before/after PASS |

## Metric before / after / delta

| Scope / metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 385 | 367 | -18 (-4.68%) |
| Principal cyclomatic | 341 | 323 | -18 |
| Principal callable LOC | 2023 | 1988 | -35 |
| Principal nesting / params | 2 / 0 | 2 / 0 | 0 |
| File cognitive SUM | 1093 | 1062 | -31 (-2.84%) |
| File cyclomatic SUM | 1231 | 1201 | -30 |
| File normalized decisions SUM(cyclomatic−1) | 923 | 892 | -31 |
| File effective LOC | 2812 | 2809 | -3 |
| File callables | 308 | 309 | +1 |
| File useState / useEffect / useReducer | 21 / 13 / 0 | 21 / 13 / 0 | 0 |
| File imports / dependency count | 20 / 20 | 20 / 20 | 0 |
| File error / warning findings | 13 / 19 | 11 / 21 | -2 / +2 |

New helper: cognitive6, cyclomatic7, LOC32, nesting0, params1, **no finding**.
Aggregate cognitive and normalized branching both decrease: no complexity
laundering. File finding total remains32; this does not negate real debt reduction.

Whole report: 1673 files retained; callable20323→20324, error1924→1922,
warning2739→2741, observations4663→4663. All nonowned file metrics, callable
records and finding records remain EXACT; report engines/schema/scope unchanged.
Finding counts are observations, not independent defect counts.

## Tests and coverage

Two distinct native runs, original and candidate, **496 PASS / 7 spec files**
each (17 internal describe-suite groups), zero failure, pending, todo or skipped
case; original and candidate assertion identities/statuses are exact.

The seven immutable mounted specs are suffixes `page`, `regressions`, `r6`,
`r7`, `r8`, `r9`, `summary-r26` under `frontend/tests/unit/presenze-giornaliere-*`.

| Full-page dimension | Original | Candidate | Coverage |
| --- | ---: | ---: | --- |
| Statements | 1035/1035 | 1041/1041 | 100% both |
| Branches | 1139/1139 | 1119/1119 | 100% both |
| Functions | 306/306 | 307/307 | 100% both |
| Lines | 847/847 | 854/854 | 100% both |

Independent raw audit binds the only coverage path to this exact runtime file;
statement/function/branch maps and counter IDs match, all branch-location
denominators are retained, every counter is strictly positive, line denominator
is reconstructed from raw statement start lines, and native summary agrees.
No missing dimension, synthetic execution, internal-policy mock or coverage union.
Config/package/setup/test/runtime hashes are captured before each native run.

## Native gates and reproduction

Private base: `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r34-presenze-summary/final-evidence`.
Every actual gate has absolute argv/cwd, launch metadata, native log and exit file.
The private `native.py` records all3648 tracked input hashes before launch;
original/candidate gate sequences leave their own inputs and status EXACT.
Across sequences the ONLY changed tracked input is the admitted runtime page.

| Gate | Original | Candidate |
| --- | --- | --- |
| `make complexity-report REPORT_JSON=<private>/complexity.json REPORT_MD=<private>/complexity.md` | Exit0 | Exit0 |
| `VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx vitest run <seven-specs> --maxWorkers=1 --coverage --reporter=json ...` | Exit0/full100 | Exit0/full100 |
| `npm run typecheck -- --incremental false` | Not repeated separately | Exit0 |
| `next lint --file src/app/presenze/giornaliere/page.tsx` | Not invoked | Exit0; three legacy warnings |
| `make complexity-ratchet BASE_REF=main` | Not invoked | Exit0/findings[] |
| `git diff --check` | Clean preflight | Exit0 |
| Raw tests/coverage/input audit | Complete original receipt | Exit0 |
| Whole-report/type-roots/old-case-identity/custody final audit | Compared to candidate | Exit0/ACCEPT_IMPROVED |

Type gate uses unchanged complete application project config, strict=true,
noEmit=true, incremental=false: **662 configured roots**, no root removed or
option relaxed. Existing project `skipLibCheck` setting is unchanged. Existing
unit specs remain excluded by project config and are exercised by native Vitest;
there is no NEW test source in this slice.

Lint warnings: existing unused `isLoadingRecordDetail`, existing `closeSelectedRecord`
and `contractProfileEditor` effect-dependency warnings. Their source responsibilities
are untouched; they are not hidden, fixed opportunistically or converted to errors.
Next lint deprecation is reported without changing tooling.

## Ratchet and global baseline status

Strict standalone JSON parsing ignores the literal Make echo `${BASE_REF:-origin/main}`,
then verifies actual `base_ref=main`, authoritative baseline commit55a, owned page
in changed_files, **findings=[]**. No substitution of BASE_REF or baseline repair.

`complexity-check` is NOT rerun in this independent narrow checkpoint; historical
EXACT30 divergences remain separate and open. Coordinator handles the global
baseline gate during integration. This verifier does not turn historical failure
into a new change failure or certify baseline reconciliation.

## Evidence integrity and classification

- Native original/candidate gates run once only; no successful gate rerun.
- `final-audit.json` SHA: `2d2e5f4010ebb4153a49e4f60b7b207862a6d8e018f2d2c2e923f65e4f3c4f8d`.
- Full raw coverage, test JSON, whole metrics, config/root custody and reproducible
  runner/auditor source are retained; terminal manifest binds report and evidence.
- Initial exploratory Node metadata read had one unmatched-parenthesis syntax
  typo, explained and corrected by a distinct static read. It was not a native
  test/tooling failure and did not cause any gate retry; observation retained.
- Original extra combined runner stdout was not separately archived; the actual
  gate argv/log/exit and completed raw/input audit receipt are archived intact.

Classification: **IMPROVED**. No rejected regression admitted; no new threshold
violation. Two error findings become warnings while real aggregate debt decreases.

## Files changed / commit

Runtime published by Coordinator: page only. Verifier publication: this report
only. Existing specs/shared tooling/baselines unchanged. No verifier commit;
Coordinator integration is a separate authorized step after this report/freeze.

## Residual risks and next slice

- Principal remains cognitive367 (>300), with21 useState/13 useEffect and large
  retained rendering/orchestration responsibility. Original campaign target not met.
- Observable-equivalence proof is scoped to supported JSON primitives/local totals;
  it is not a general guarantee about hostile getters, patched intrinsics or new
  future formatter side effects. Preserve the in-place sorting contract.
- Broad frontend suite/build/stack E2E/backend/worker suites are not run here and
  remain uncertified for current campaign HEAD. No unsupported PASS claim.
- Graphify boundary maintenance belongs to Coordinator integration, not complexity
  proof; this report does not assert an unexecuted graph refresh.
- Integrate this ONE accepted responsibility, root-check exact custody/gates and
  graph refresh; then reassess a separate substantive responsibility in the extreme
  Presenze callable under NEW ownership. No second runtime slice initiated here.
