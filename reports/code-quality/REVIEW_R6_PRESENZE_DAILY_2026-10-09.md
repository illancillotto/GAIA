# R6 Presenze daily presentation — Independent Review

## Status

**APPROVED / IMPROVED** for exact author source
`56c46570f48c3281ba2db2b3e8220338b29c8e88`, reproduced in reviewer cherry-pick
`6b4f13d4fea7256905339f0bf3c8bc7a45eafd74`. Coordinator may integrate that
source only; independent final integration gates remain mandatory.
The global campaign remains ACTIVE/INCOMPLETE.

## Ownership and snapshot

- Reviewer branch `review/complexity-r6-presenze-daily`, initial clean HEAD
  `afebd6154fa1f2c0f76693f39f2e4d5fea6ae271`.
- Authoritative main/merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Reviewer owns only this report. Runtime and tests are read-only.
- Preventive registry:
  `docs/code-quality/MULTI_AGENT_OWNERSHIP_R6_PRESENZE_DAILY_2026-10-09.md`
  in the campaign integration worktree.
- Durable reviewer evidence:
  `/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/reviewer/`.

## Design review

One bounded responsibility: typed pure daily-record presentation projection,
including ordered indicator descriptors and repeated inline-KM display values.
The Coordinator authorized this scope after independent design inspection.
Neither whole-table JSX relocation nor extraction into a mega-component is
approved. All new helpers must be included in the measured aggregate.

### Behavioral invariants

- Indicator order and individual span classes remain exact: extra `▲`, KM
  `🚗`, travel `T`, availability `R`, authorization `✅` or request `✉`.
- Extra uses `> 0`, not truthiness; NaN, zero and negatives remain unmarked.
- KM uses non-null semantics, retaining zero. Travel is positive minutes OR
  the mountain-travel flag. Availability preserves `unit !== "none"`.
- Authorization takes precedence over requests. Empty authorization labels
  retain the original truthiness behavior. No new permission or API rule.
- KM draft lookup is nullish, not truthy: empty drafts survive. Nullable
  stored KM stays empty; zero becomes `"0"`; other values retain `String`.
- Monthly-table global edit permission and collaborator-modal per-record edit
  permission remain distinct inputs; saving-record equality is unchanged.
- Inputs remain uncontrolled with the same `defaultValue`, identity, DOM
  position, numeric input mode, placeholder, title/aria label and classes.
- Change and blur event behavior, state patching and persistence are retained
  in the parent. No handler, effect, hook dependency, lifecycle, selection,
  authentication, external call, transaction or identity-mapping change.
- Outer indicator container and empty-space/min-height behavior stay exact.

### Risks and acceptance conditions

Array rendering introduces keyed children; keys must be stable and unique and
must not remount the KM inputs. Conditions supplied to descriptors must retain
legacy null/zero/NaN semantics. The projection must not become a generic
manager/context or obscure existing permission differences.

Coverage is full-file, not changed lines. Approval requires all modified
runtime statements and branch arms at100%, characterization passing against
the original implementation first, measured aggregate reduction without
transferred findings, ratchet/main PASS0, and independent exact-source review.

## Independently revalidated baseline

Fresh reviewer run on the unmodified starting runtime, with two workers and
no overlapping author suite: **388 PASS / 4 specs / zero skips**, exit0.

| Full page coverage | Covered / total |
|---|---:|
| Statements | 1093 / 1093 |
| Branch arms | 1245 / 1245 |
| Functions | 301 / 301 |
| Lines | 894 / 894 |

All measures100%; fresh V8 counters are retained in
`before-coverage/coverage-final.json`. Raw command output and exit are
`before-tests.log` and `before-tests.exit`.

| Metric | Principal callable | Full page | Page + two existing models |
|---|---:|---:|---:|
| Cognitive | 437 | 1273 | 1332 |
| Cyclomatic | 385 | 1350 | 1414 |
| Callable LOC | 2080 | — | 4660 |
| File LOC | — | 2858 | 3046 |
| Nesting | 2 | — | — |
| Parameters | 0 | — | — |
| Findings | 3 | — | 41 (18 error,23 warning) |

Scanner output `before.json` includes every callable in the page,
`collaborator-rows.ts` and `monthly-record-insights.ts`. Existing models have
zero findings. Hook counts reported by the official scanner are useState21,
useEffect13 and useReducer0; no hook change is approved.

Independent Babel traversal counts38 actual useState call expressions, versus
the official scanner's21. These are disclosed as distinct measurement
methods, not silently reconciled by changing tooling. Full direct hook count
is75:38 useState,13 useEffect,21 useMemo,1 useDeferredValue and2 useRef.
`before-invariants.json` freezes all75 hook-call source hashes and72 named
top-level helper source hashes for exact post-change comparison.

Commands from this reviewer worktree:

```bash
git status --short
git rev-parse HEAD
git merge-base HEAD main
python3 tools/code_quality/complexity.py report \
  frontend/src/app/presenze/giornaliere/page.tsx \
  frontend/src/app/presenze/giornaliere/collaborator-rows.ts \
  frontend/src/app/presenze/giornaliere/monthly-record-insights.ts \
  --json /home/cbo/.cache/gaia-campaign/20261009-r6-presenze/reviewer/before.json \
  --markdown /home/cbo/.cache/gaia-campaign/20261009-r6-presenze/reviewer/before.md
cd frontend
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  --maxWorkers=2 \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/reviewer/before-coverage
```

The existing coverage include environment option selects the measured runtime
without modifying configuration, exclusions, thresholds or gate policy.

## Exact source review

Pre-freeze inspection confirms a15-line page diff; a22-effective-LOC model
holds two pure projections and a filter callback. Existing named helpers72
and complete hook call source75 remain byte-identical. Unchanged JSX/event
attributes and input identities do not move; typed indicator mapping retains
unique stable glyph keys. No cyclic import: the new model imports only a type.
No component explosion, shared-config modification or domain rule change.

Two independently derived original-AST differential sweeps PASS:
24,192 indicator combinations compare ordered symbols and exact classes;
288 KM combinations compare both original expressions and edit/saving logic.
The sweeps include null,undefined,zero,negative,NaN,infinities,empty/nonempty
drafts,request/authorization priority and alternative travel semantics.
They supplement actual UI tests, not substitute for runtime coverage.
Reproducible artifact `differential.mjs` writes `differential-final.json` with
source hashes. Inputs outside declared nullable types are deliberate robustness
probes, not an expanded API contract.

Independent characterization against the **original** reviewer page passes
all15 new actual-UI cases. The ten pure helper cases are deliberately not
selected by the original-page replay and are recorded as10 filter skips, not
as passed original tests. Temporary external config points the page import at
the original source; no runtime or repository test was edited.
First external-config invocation failed in setup (wrong process cwd) with
zero collected tests. Retained `original-characterization.log`/`.exit` shows
that failure; retry from the configured author frontend cwd succeeds exit0
in `original-characterization-retry.log`/`.exit`. This harness path correction
is not an application/test behavior change or failure waiver.

Frozen source review confirms all five authored files exactly reproduce the
original author commit. `frozen-invariants-audit.json` records each file hash,
72 unchanged named helper hashes and75 unchanged hook-call hashes. All other
runtime/tests/configuration paths are unchanged relative to the starting
commit. New API/domain/config/coverage/complexity exclusions or ignores: zero.
No existing test was edited, removed, weakened or skipped.

Reproducible original characterization is now pointed at the durable original
page snapshot with source SHA256
`3753ab56630a1440fe4dd098e4ba426d025b50e0c2e2ab92af7ee3068145ce4b`.
The initial attempt after changing this external alias failed at module
resolution because a cache-hosted source cannot resolve React by itself,
collecting zero tests. External aliases for existing React/Next packages fixed
that harness path issue without repository edits; retained logs distinguish
failure from successful retry. The final frozen characterization replay again
passes15 actual UI cases,10 pure cases not selected by filter,exit0.

## Independently measured after / delta

The reviewer reports the whole page plus both existing models before, adding
the complete new model after. Unchanged model aggregates cancel; this agrees
with the author's page-plus-new-model delta, not only its principal metric.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 437 | 420 | -17 (-3.89%) |
| Principal cyclomatic | 385 | 371 | -14 |
| Principal callable LOC | 2080 | 2076 | -4 |
| Principal nesting / params | 2 / 0 | 2 / 0 | 0 / 0 |
| Whole affected cognitive | 1332 | 1289 | -43 |
| Whole affected cyclomatic | 1414 | 1383 | -31 |
| Whole affected callable LOC | 4660 | 4672 | +12 |
| Whole affected file LOC | 3046 | 3065 | +19 |
| Whole affected callable count | 322 | 326 | +4 |
| Errors | 18 | 17 | -1 |
| Warnings | 23 | 21 | -2 |
| Findings | 41 | 38 | -3 |

Page-only cognitive1273→1222/cyclomatic1350→1309; new model cognitive8,
cyclomatic10,LOC22,zero findings. Its function maxima are cognitive5,
cyclomatic5,LOC14,nesting2,params4. The remaining map callback is included in
the page aggregate. Real decision deduplication and flatter typed presentation
remove duplicate KM projection and nested icon rendering rather than moving
a mega-function or hiding complexity. LOC grows and is not claimed improved.

## Independent final tests / coverage / gates

| Gate | Independent result | Durable evidence |
|---|---|---|
| Existing four suites, before | 388 PASS,zero skips,exit0 | `before-tests.log`/`.exit` |
| Focused five suites, frozen after | 413 PASS,zero skips,exit0,34.86s | `after-tests.log`/`.exit` |
| Page full-file coverage | 1094/1094 statements,1217/1217 arms,302/302 functions | `after-coverage/coverage-final.json` |
| Model full-file coverage | 8/8 statements,14/14 arms,3/3 functions | `after-coverage/coverage-final.json` |
| All runtime coverage | 100%,903/903 lines,zero uncovered counters | `after-coverage-audit.json` |
| Original UI replay | 15 PASS,10 pure cases filtered,exit0 | `original-frozen-characterization-retry.log`/`.exit` |
| Original-AST differential | 24,192 indicator+288 KM cases PASS | `differential.mjs`,`differential-final.json` |
| All hooks/helper bodies | 75/75 hooks,72/72 named helpers exact | `frozen-invariants-audit.json` |
| Typecheck | PASS,exit0 | `typecheck.log`/`.exit` |
| ESLint | PASS,exit0;3 identical legacy warnings | `eslint.log`/`.exit`,`eslint-before.log`/`.exit` |
| Complexity ratchet against main55a | PASS,0 findings,exit0 | `ratchet.log`/`.exit` |
| Diff whitespace | PASS | `git diff --check` |

The ESLint warnings were independently reproduced from the initial source via
stdin with its original filename: unused detail-loading state and two existing
effect dependency warnings. Line positions shift with the import, but warning
identities do not change. No suppression or unrelated repair is added.

All tests still exercise actual page state and DOM with API-boundary mocks:
icon order/classes, empty spacing, title/selection, matrix/modal empty draft,
non-owned supervisor disabled state, identical uncontrolled node throughout
pending/completed saving and exact persisted payload. The corrected fixture
provides `total:1,page:1,page_size:5000`, ending original pagination normally;
it does not mock or bypass the runtime presentation projections. Later pure
tests check frozen inputs, output freshness and formatting/disabled truth
table, supplementing complete original UI regression/race coverage.

Source Graphify evidence was inspected: dedicated frontend code graph
6003nodes/12568edges/226communities; dedicated Presenze docs54nodes/56edges/
9communities,semantic chunks1/2 and2/2 done,zero semantic-failure warning.
The reviewer does not regenerate source graphs because its only edit is this
report outside documentation corpora; no generated graph is versioned.

## Classification / residual risks

**IMPROVED** for this bounded presentation responsibility; no rejection or
unexplained application failure. Principal remains cognitive420 and therefore
extreme; neither the initial50% reduction target nor the global campaign is
complete. Raw useState38 and official21 both remain unchanged, as do13 effects.
No full frontend/build/E2E result is claimed here: independent final verifier
owns those gates. Global30 divergences and Capacitas coverageFAIL remain
separate. No main integration, push, PR or whole-wave certification by reviewer.

## Commit

Report-only commit: resolve with
`git log -1 --format=%H -- reports/code-quality/REVIEW_R6_PRESENZE_DAILY_2026-10-09.md`.
Do not cherry-pick the review branch's duplicate source commit a second time.
Coordinator integrates original source56c46570 and this report separately.
