# Capacitas C12 — Complexity Slice Report

## Ownership and snapshot

Coordinator registry `87eab694` authorizes this TEST-ONLY modal-race slice.
Exclusive new files:

- `frontend/tests/unit/campaign-capacitas-modal-race.test.tsx`.
- `reports/code-quality/SLICE_CAPACITAS_C12_2026-10-08.md`.

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-c12-tests`, branch
`refactor/complexity-capacitas-modal-race-tests`. Clean preflight HEAD
`87eab6944574a6c00b42f18c5c98f18558c58ba5`; merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Checked `git status --short`, `git rev-parse HEAD`, `git merge-base HEAD main`,
`git diff` and owned runtime history. No concurrent main work is touched or
copied. Runtime, existing tests, shared files, baseline, configuration and
tooling remain read-only. No source branch is integrated by this agent.

## Baseline and target callable

Fresh read-only AST reports `/tmp/capacitas-c12-before.json` and
`/tmp/capacitas-c12-after.json` contain exactly identical `files` and `callables`.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 472 | 472 | 0 |
| Main cyclomatic | 416 | 416 | 0 |
| Main callable LOC | 2631 | 2631 | 0 |
| Main nesting / parameters | 2 / 1 | 2 / 1 | 0 |
| File effective LOC | 3109 | 3109 | 0 |
| File callables | 251 | 251 | 0 |
| File cognitive / cyclomatic sums | 1099 / 1174 | 1099 / 1174 | 0 |
| File useState / useEffect | 31 / 2 | 31 / 2 | 0 |

The slice targets genuine missing branch coverage for the late asynchronous
`setResolveModal` null guards at 3214, 3217 and 3220, not complexity reduction.

## Behavioral invariants

The actual workspace, polling hooks and rendered handlers run. Mocks cover
typed API/auth boundaries, ProtectedPage and the unrelated settings modal.
Anomaly rows have distinct coherent UUIDs and public candidate data; successful
and unsuccessful responses use the declared result fields. Errors reject the
real awaited boundary Promise. No setter, private closure, exported runtime
helper, React state substitution, detached event callback or parser mock is used.

Flow characterized:

```text
load valid Uras and Terralba rows
→ public Uras Risolvi
→ Sincronizza dispatches Uras/FRA-A, busy-close disabled
→ focus live background Terralba Risolvi and dispatch its public DOM action
→ visible modal becomes Terralba/FRA-C, close enabled
→ close or retain that replacement modal
→ settle the original Uras request
→ verify actual modal presentation and original-row filtering
```

Only success removes the original request's Uras row. Terralba is never removed
and no Terralba resolution request is sent. Pending request payload, request
count, manual-list count, candidate selection and modal transitions are asserted.
The existing late update of a still-open replacement modal is deliberately
preserved and recorded, not fixed or described as desirable behavior.

## Characterization test matrix

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Original close disabled while request pending | C7 deferred busy-close coverage | Replacement can expose another enabled close | All six cases verify original busy then replacement non-busy | PASS |
| Late success after replacement and enabled close | C7 success only with original modal present | Null arm3214 | One public-UI case: remains closed, only Uras removed, fresh Terralba reopen clean | PASS |
| Late `ok:false` after replacement and close | C7 unsuccessful response with modal present | Null arm3217 | One case: remains closed, both rows retained, no stale error on reopen | PASS |
| Late rejection after replacement and close | C7 rejection with modal present | Null arm3220 | One case: remains closed, both rows retained, no stale error on reopen | PASS |
| Late success with replacement modal still open | C7 does not switch modal target during pending resolution | Existing current-state/captured-row mismatch | One case: Terralba receives success display, Uras removed | PASS |
| Late unsuccessful result with replacement open | Same | Existing error presentation on replacement | One case: Terralba receives original error, retry remains enabled | PASS |
| Late rejection with replacement open | Same | Existing catch presentation on replacement | One case: Terralba receives original rejection message, retry enabled | PASS |

Six new tests, zero skip. Closed-state cases reopen Terralba only after checking
the completed late callback left null; open-state cases assert the old request
updates the current modal while retaining its Terralba identity and selection.

## Link to actual keyboard witness

`CAPACITAS_MODAL_REACHABILITY_2026-10-08.md`, accepted as `b0a4ac2a`, records
native browser Tab/Enter background activation against the unchanged workspace.
Its six regular/StrictMode browser cases prove nine actual null-arm executions
with V8 precise coverage, independently audited by Coordinator.

This jsdom spec uses a live enabled DOM button, `.focus()`, a focus assertion
and `fireEvent.click` on that public button. It characterizes the resulting
React/API transitions. **It does not prove native Tab order, Enter default
activation, pointer hit-testing, production CSS or real-browser focus trapping.**
Reachability comes from the separate native keyboard evidence, not from
pretending jsdom can reproduce those browser mechanics. No forced pointer
click is proposed as a browser witness.

## Tests and commands

Commands below run from this worktree, frontend commands from `frontend/`.

| Command | Result | Log |
| --- | --- | --- |
| `npm run test:unit -- tests/unit/campaign-capacitas-modal-race.test.tsx --maxWorkers=1` | Final 6 PASS, 0skip | `/tmp/capacitas-c12-focused-reviewed.log` |
| Actual union coverage command below, before | 306 PASS /15spec, 0skip; coverage gate FAIL exit1 | `/tmp/capacitas-c12-before-coverage.log` |
| Actual union coverage command below, after | 312 PASS /16spec, 0skip; coverage gate FAIL exit1 | `/tmp/capacitas-c12-after-coverage.log` |
| `node_modules/.bin/tsc -p /tmp/capacitas-c12-test-tsconfig.json --noEmit` | Explicit owned-spec typecheck PASS exit0 | `/tmp/capacitas-c12-test-typecheck-final.log` |
| `npm run typecheck` | Runtime typecheck PASS exit0 | `/tmp/capacitas-c12-runtime-typecheck.log` |
| `npx next lint --file tests/unit/campaign-capacitas-modal-race.test.tsx` | PASS, no ESLint warnings/errors | `/tmp/capacitas-c12-lint-final.log` |
| `npm test` | 18 smoke PASS, 0skip | `/tmp/capacitas-c12-smoke-final.log` |
| `make complexity-ratchet BASE_REF=main` | PASS exit0, 0findings | `/tmp/capacitas-c12-ratchet.log` |
| `node /tmp/capacitas-c12-ledger.cjs` | Map identity, exact three new arms, no lost arms, AST identity PASS | `/tmp/capacitas-c12-ledger.log` |

Temporary test tsconfig extends this worktree's frontend config, explicitly
includes the owned spec, clears inherited test exclusion and sets
`incremental:false` with absolute Vitest/jest-dom type paths. Normal runtime
typecheck excludes test specs, so it is not substituted for this explicit check.
No repository configuration is edited. Next lint's existing deprecation notice
is not an ESLint warning.

Initial evidence is retained: `/tmp/capacitas-c12-focused.log` has six failures
because jest-dom rejects `.toHaveValue()` for radio inputs. Replaced that invalid
matcher with exact value-attribute assertion plus the existing `.toBeChecked()`;
no behavior assertion was removed. First explicit types in
`/tmp/capacitas-c12-test-typecheck.log` rejected Playwright's `exact:true` option
on Testing Library role queries. Removed the unsupported option; string role
names retain their default exact matching. Final focused tests, explicit types
and actual cumulative coverage execute the corrected source.

Fresh AST report command, repeated with before/after artifact names:

```sh
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c12-before.json --markdown /tmp/capacitas-c12-before.md
```

## Actual before/after cumulative coverage

The before command finishes before creating the new spec. Both runs execute
the actual union, without percentage addition or changes to inherited tests.
All four full-file 100% thresholds and the same runtime denominator remain.

```sh
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c12-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c12-after-coverage
```

| Counter | Before | After | Covered delta |
| --- | ---: | ---: | ---: |
| Statements | 857/857,100% | 857/857,100% | 0 |
| Branch arms | 903/929,97.20% | 906/929,97.52% | +3 |
| Functions | 251/251,100% | 251/251,100% | 0 |
| Lines | 748/748,100% | 748/748,100% | 0 |

Branch gain is approximately **0.323 percentage points**. Both coverage
commands exit1 because full-file branch coverage remains below100%.
Statement100% is not a runtime-refactoring authorization or policy exemption.

| Source line | Branch:arm | Before hits | After hits |
| --- | --- | ---: | ---: |
| 3214 | 436:1 | 0 | 1 |
| 3217 | 437:1 | 0 | 1 |
| 3220 | 439:1 | 0 | 1 |

Ledger `/tmp/capacitas-c12-residual-ledger.json` SHA256
`f77fc74dc314aa3f488eaed578a2d3ff5e44f8182c8561e4a90726e306d38790`.
It asserts exactly these three new hits, zero previously-covered arms lost,
identical statement/function/branch maps and exactly23 remaining arms, all with
source positions. Residual lines:
258,281,291,293,313,314,315,316,317,318,378,388,390,403,404,405,2056,
2482(two arms),2483,2484,3166,3206. No statement/function/line residue remains.
The two synchronous modal guards remain UNKNOWN; the other21 conditional
construction/library candidates retain their separate provenance and defenses.

## Ratchet and preservation

Authoritative `BASE_REF=main` and merge-base remain unchanged. Ratchet PASS
with zero findings includes inherited campaign changes. No global check rerun
or global suite PASS is claimed by this local slice. Historical thirty global
divergences remain separately owned; no baseline repair or absorption occurs.

Before/after SHA256 identical:

- Runtime `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Baseline `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Original batch spec `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.

Diff against source HEAD for runtime, baseline/config, Makefile, package,
coverage configuration and tooling is empty. Existing specs are untouched.

## Classification

**NO_CHANGE — CHARACTERIZATION_ONLY**. Coverage increases by three genuine
arms; cognitive472 and every runtime AST metric stay unchanged. No debt is
moved and no complexity reduction is claimed. Runtime hold remains effective.

## Files changed and commit

Only the two owned new files enter authorized source commit
`test(capacitas): characterize late anomaly modal responses`.
Exact source SHA is returned after committing and can be recovered through
`git log -1 --format=%H -- frontend/tests/unit/campaign-capacitas-modal-race.test.tsx`.
Status: **READY_FOR_REVIEW**. No integration/cherry-pick by source author.

## Graphify, residual risks and recommended next slice

Test-only changes create no runtime component boundary, service relationship,
dependency or routing change, so no code graph update is required. This report
does not replace Coordinator's aggregate docs Graphify refresh.

The native keyboard witness is Chromium-specific and separate from jsdom;
these tests characterize existing race behavior, not a functional fix. Pending
original responses can alter a replacement modal, which would need a separate
decision to change. Two synchronous guards remain UNKNOWN and are not removed.
Full-file100% still FAIL; redundant-defense cleanup remains a separate explicitly
authorized runtime slice, not an automatic consequence of this coverage gain.

Next action: independent source review and sequential integration of this
test-only slice; reproduce the actual312-test union and23-arm residual ledger.
Stop here rather than beginning another hotspot or altering the guards.
