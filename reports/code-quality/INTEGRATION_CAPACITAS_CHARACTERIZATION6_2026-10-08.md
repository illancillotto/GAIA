# Capacitas — Independent characterization integration 6

## Ownership and authoritative snapshot

Coordinator registry `7aa9e1c5` authorizes this report and the exact approved C12
test-only source cherry-pick. Worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`. Initial clean HEAD
`7aa9e1c55e0de36f76af730d6334447aa2b9144c`; staging empty. Coordinator-only docs
advanced HEAD to `a721a79658de52fa8529354e0dba2bcf45e55575` before integration;
the frontend tree remained `1ddc7041881a24259e30dd81491aafba44fdb104`.
Merge-base and authoritative ratchet baseline against main remain
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Dirty main was not copied or modified.
Coordinator paused tracked-file writes for the integration/report operation.

This agent did not author the source implementation. Runtime, existing specs,
baseline, tooling, thresholds, scope and shared files remain read-only.

## Fresh measured before

Actual fifteen-spec union independently executed before cherry-pick:
**306 tests PASS, zero skip**. Same full-workspace V8 include and four unchanged
100% thresholds; command **exit1 / FAIL100** due to branch coverage97.20%.

| Counter | Actual before |
|---|---:|
| Statements | 857/857 |
| Branch arms | 903/929 |
| Functions | 251/251 |
| Lines | 748/748 |

Artifact `/tmp/gaia-capacitas-integration6-before-coverage/coverage-final.json`,
SHA256 `c5d4a38027b6876b7d0a7b76310edfd6876346bda707064e9f45f182e0a50fe1`;
log `/tmp/gaia-capacitas-integration6-before-coverage.log`, exit file alongside.
Statement/function/branch maps and all26 uncovered branch IDs match the prior
Integration5 artifact exactly. No inferred union or sum of percentages is used.

Fresh scoped AST `/tmp/gaia-capacitas-integration6-before-complexity.json`
exactly matches Integration5 files/callables, including fingerprints/positions.
Before main ratchet independently passes with zero findings, exit0.

## Independent source review and integration

Coordinator authorized exact READY source
`53e9405b2c929abd3f2951929c0e6164afd0b19c`, worktree
`GAIA-campaign-20261008-c12-tests`, branch
`refactor/complexity-capacitas-modal-race-tests`. Source working tree clean;
commit changes exactly its new spec and C12 report, no existing file.
Independently executed source spec: **6 PASS, zero skip**, before cherry-pick.
Integration staging and working tree were empty immediately before applying
that exact commit, yielding `acdc95151894d31df7e7cf4c6bd8d593e3dd3b99`.
No incomplete branch or unreviewed intermediate commit was integrated.

| Behavior | Independent review |
|---|---|
| Original request | Real Uras row/FRA-A public controls, exact token/UUID/payload, one API call; original busy close and synchronize disabled |
| Modal replacement | Enabled live Terralba background button receives focus and its public DOM action; new modal identity/FRA-C preserved, close enabled, no second API request |
| Close then late success | Modal remains null; only original Uras removed; reopened Terralba has no stale success |
| Close then late unsuccessful result | Modal stays null; both rows retained; reopened Terralba has no stale error |
| Close then late rejection | Modal stays null; both rows retained; reopened Terralba has no stale rejection |
| Replacement remains open | Three additional cases preserve current behavior: original response updates Terralba presentation while retaining Terralba selection, with only success removing Uras |

Fixtures use complete typed anomaly/resolution contracts, distinct coherent UUIDs
and actual result fields. The deferred Promise is only the API boundary; the real
workspace handlers, state, effects, polling hook and DOM render execute. No fake
setter, private closure/callback invocation, impossible parser output or detached
React update is used. Existing tests are neither weakened nor edited. Source
report retains initial invalid radio matcher/role-option diagnostics and their
corrections; independent review/tests operate on the exact corrected source.

### Native reachability versus jsdom characterization

Read-only review of `CAPACITAS_MODAL_REACHABILITY_2026-10-08.md` and the unchanged
runtime confirms the seven modal state writers and absence of a background focus
trap. Independently reran `node /tmp/gaia-modal-probe/coverage-audit.mjs` against
the saved raw precise-V8 evidence: six genuine native Tab/Enter browser cases,
including real StrictMode, prove nine null updater executions at3214/3217/3220.
The audit requires positive updater execution and zero object-arm execution in
the actual transformed `prev ? { ... } : null` functions. Saved API payloads,
rows and browser errors correspond to the public replacement/close sequence.
Artifact `/tmp/gaia-capacitas-integration6-modal-audit.log`, exit0. The browser
experiment itself was not rerun by this integration agent.

C12 jsdom `.focus()` plus `fireEvent.click` characterizes the resulting public
React/API transitions; it does not establish native Tab ordering, Enter default
activation, pointer hit-testing or deployed CSS. Acceptance of reachability
uses the separate genuine browser witness, not a forced pointer click over an
overlay. These tests intentionally preserve the current replacement-modal race;
they do not fix it or prove production authorization/external portal behavior.
Three asynchronous guards are necessary, not redundant. Synchronous guards3166
and3206 remain UNKNOWN; historical five-UNKNOWN text is superseded by this proof.

## Actual cumulative coverage and exhaustive residual ledger

Independent integrated sixteen-spec union: **312 tests PASS, zero skip**.
Same full-file denominator and four100% gates. Coverage **FAIL100 / exit1**,
not runtime clearance or policy compliance.

| Metric | Before covered/total | After covered/total | Covered delta | Final % |
|---|---:|---:|---:|---:|
| Statements | 857/857 | 857/857 | 0 | 100 |
| Branch arms | 903/929 | 906/929 | +3 | 97.52 |
| Functions | 251/251 | 251/251 | 0 | 100 |
| Lines | 748/748 | 748/748 | 0 | 100 |

Fresh statementMap/fnMap/branchMap exactly identical before/after. Exactly three
newly covered arms:3214 `436:1`,3217 `437:1`,3220 `439:1`; zero previously covered
arms lost. No uncovered statements/functions/lines. All23 remaining branch arms
retain exact source metadata, across22 source lines; zero without start location.

| Branch source line | Uncovered arms | IDs (branch:arm) | Arms without start-line location |
|---|---:|---|---:|
| 258 | 1 | 16:1 | 0 |
| 281 | 1 | 19:1 | 0 |
| 291 | 1 | 23:1 | 0 |
| 293 | 1 | 24:1 | 0 |
| 313 | 1 | 27:1 | 0 |
| 314 | 1 | 28:1 | 0 |
| 315 | 1 | 29:1 | 0 |
| 316 | 1 | 30:1 | 0 |
| 317 | 1 | 32:1 | 0 |
| 318 | 1 | 34:1 | 0 |
| 378 | 1 | 41:1 | 0 |
| 388 | 1 | 45:1 | 0 |
| 390 | 1 | 46:1 | 0 |
| 403 | 1 | 49:1 | 0 |
| 404 | 1 | 51:1 | 0 |
| 405 | 1 | 53:1 | 0 |
| 2056 | 1 | 285:1 | 0 |
| 2482 | 2 | 337:1, 338:1 | 0 |
| 2483 | 1 | 333:1 | 0 |
| 2484 | 1 | 334:1 | 0 |
| 3166 | 1 | 426:1 | 0 |
| 3206 | 1 | 434:1 | 0 |

Other21 candidates retain their separate conditional JS-construction/installed
SheetJS provenance. Neither that evidence nor this integration authorizes guard
removal, a coverage exemption or runtime change. The full-file gate stays FAIL.

Artifacts:
- `/tmp/gaia-capacitas-integration6-final-coverage/coverage-final.json`, SHA256
  `ddfb577d010e9796af9508b723880a938aa1ea36779875ccd6d6a72654d7d005`.
- `/tmp/gaia-capacitas-integration6-final-coverage.log` and `.exit`.
- `/tmp/gaia-capacitas-integration6-residual-ledger.json`, SHA256
  `7b03da550781acea29552bf15345980573dcea1c90e7a0ab4ab03159a93149f4`.
- `/tmp/gaia-capacitas-integration6-residual-ledger.md` and independent extractor
  `/tmp/gaia-capacitas-integration6-ledger.cjs`, with all zero arms/locations.

## Gates, frozen source and reproduction

| Gate | Actual result | Artifact |
|---|---|---|
| C12 independent source test | 6 PASS, zero skip, exit0 | `/tmp/gaia-capacitas-integration6-c12-source.log` |
| Before actual union | 306 PASS/15spec; coverage FAIL100 exit1 | `/tmp/gaia-capacitas-integration6-before-coverage.log` |
| Final actual union | 312 PASS/16spec; coverage FAIL100 exit1 | `/tmp/gaia-capacitas-integration6-final-coverage.log` |
| Before/after main ratchet | Both PASS0, exit0; baseline55a1b1d3 | `/tmp/gaia-capacitas-integration6-before-ratchet.log`, final counterpart |
| Explicit new-spec TypeScript | PASS exit0 | `/tmp/gaia-capacitas-integration6-final-types.log` |
| Scoped new-spec ESLint | PASS exit0, no warnings/errors | `/tmp/gaia-capacitas-integration6-final-lint.log` |
| Runtime/config/tooling/existing-spec preservation | Protected diff empty, exact hashes unchanged | `git diff --exit-code a721a796 -- ...` |
| Before/after scoped AST | Exact files/callables unchanged | `/tmp/gaia-capacitas-integration6-{before,final}-complexity.json` |
| Whitespace/staging check | PASS, no unrelated staged changes | `git diff --check`, `git diff --cached --name-only` |

Ratchets were parsed from the actual JSON opening line and verify
`base_ref:main`, `baseline_commit:55a1b1d35911451e018b662c2acc450bf5994ea2`,
and empty findings. No baseline repair/synchronization was executed. Scoped
lint retains only Next16's existing command deprecation notice, not a lint error.
Temporary type config explicitly includes the new spec, clears inherited test
exclusion and disables incremental output; no shared config is modified.

Frozen accepted source `acdc95151894d31df7e7cf4c6bd8d593e3dd3b99`, frontend tree
`14de55bb9d5eb2bc34d97d7411281969b6fda44e`. Report-only commit preserves that tree.

```sh
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-integration6-final-coverage
node_modules/.bin/tsc -p /tmp/gaia-capacitas-integration6-test-tsconfig.json --noEmit
npx next lint --file tests/unit/campaign-capacitas-modal-race.test.tsx
cd ..
make complexity-ratchet BASE_REF=main
node /tmp/gaia-capacitas-integration6-ledger.cjs
```

Preserved SHA256 runtime
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`,
original batch spec
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`,
baseline `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Diff since a721a796 contains only the authorized new source spec/report and this
independent integration report. No overlap, runtime import/layering change,
dependency cycle, component explosion, API alteration or test weakening occurs.

Main callable stays472cognitive/416cyclomatic/2631LOC/nesting2/params1; file
1099cognitive/1174cyclomatic/3109effectiveLOC/251callables,31useState/2useEffect,
24error/20warning/44findings. All complexity deltas0; no reduction is claimed.

## Classification, remaining gates and stop

**NO_CHANGE — CHARACTERIZATION_ONLY.** Six meaningful cases and three genuine
branch arms added, current late-response race preserved. Commit SHA for this
report is returned after committing rather than self-referentially embedded.

Globalcheck/fullfrontend/build/backend/worker/E2E **NOT_RUN by this agent**.
Historical30 global divergences are not absorbed or independently recertified
here. Coordinator owns the fullfrontend gate on the frozen tree; prior runtime
suite evidence is not relabeled as newly executed. No runtime boundary or
dependency changed, so no runtime Graphify refresh is required; dedicated
platform-docs refresh remains Coordinator-owned. No threshold, ignore, scope,
exclusion, baseline inflation or dirty-main integration occurs.

Mission remains ACTIVE/INCOMPLETE. Runtime hold and GIS UNKNOWN decision remain
outside this test-only authorization. Two synchronous modal arms still UNKNOWN;
the21 separate candidates do not become coverage waivers. Recommended next step
is frozen-source verification and an explicit decision for any separately owned
defensive-expression/runtime slice, not automatic cleanup. Stop after report
delivery; no second hotspot or runtime wave is started by this agent.
