# R6 Presenze daily UI — Complexity Slice Report

## Ownership

Author worktree `GAIA-campaign-20261009-r6-presenze-daily`, branch
`refactor/complexity-r6-presenze-daily`. Registry created before delegation:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R6_PRESENZE_DAILY_2026-10-09.md`
in the campaign integration checkout. Source ownership excludes existing test
suites, shared UI/lib/hooks, backend, baseline, tooling and configuration.

Preflight: clean `afebd6154fa1f2c0f76693f39f2e4d5fea6ae271`, main and merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Main's dirty concurrent work is
preserved and not an input. Owned frontend paths were clean in main, campaign
P1/R2/R3 and relevant Presenze worktrees; historical committed refactors are
not active edits and were not copied. Coordinator approved the bounded design
in plaintext before any runtime modification.

## Baseline and target callable

`PresenzeGiornalierePage`: cognitive **437**, cyclomatic **385**, effective
LOC **2080**, nesting **2**, params **0**. Page file LOC **2858**, 303 callables,
18 error / 23 warning. The scope is only operational cell presentation:
ordered indicators and duplicated KM initial/disabled properties. No whole
cell/component/JSX section is moved and no hook/state is extracted.

## Behavioral invariants

- Exact indicator order, span classes and symbols; the unchanged outer span
  retains its minimum height even with no indicators.
- Extra strictly >0; KM `!= null` includes0, negatives andNaN; travel nullish
  >0 OR mountain flag; availability unit !=none independently of quantity.
- Truthy authorized punch label precedes detail requests. Request description
  alone never invents a request icon; existing authorization readers remain
  unchanged in the page.
- KM draft nullish precedence retains empty string and zero. `String(value)`
  remains the formatter for any non-null value, including negative andNaN.
- Permission is supplied unchanged by the parent: main matrix uses global
  `canEdit`, collaborator modal uses per-record `rowCanEdit`. Saving disables
  both; no authorization rule is reconciled or fixed.
- Original uncontrolled input nodes, defaultValue, events, blur persistence,
  async completion, API payloads, errors and record navigation remain intact.
- No effect/dependency, hook, cache, query, transaction, mapping identity,
  race-sensitive flow or calculation changes. Inputs are not mutated.

## Characterization tests

Existing four giornaliere suites: **388 PASS** before runtime, full-file page
1093/1093 statements,1245/1245 branches,301/301 functions,894/894 lines.
Added15 actual-page characterizations pass on the original runtime before
refactoring. The ten later pure-model tests supplement rather than replace UI
tests. Existing tests are not edited, removed, skipped or weakened.

| Behavior | Existing test | Missing / added | Result |
|---|---|---|---|
| Indicator order/classes and authorized conflict | Existing request/cell cases | Exact all-icons DOM and title assertion | PASS before/after |
| Null, zero, negative andNaN predicates | Existing fallback cases | Four actual-page numeric cases | PASS before/after |
| Request status/direction/detail precedence | Existing authorized punch cases | Four conflicting-request cases | PASS before/after |
| KM null/zero/negative/NaN and empty draft | Existing KM saves | Four matrix→modal cases | PASS before/after |
| Per-record permission | Existing permission cases | Non-owned supervisor modal disabled | PASS before/after |
| Input identity and saving lifecycle | Existing save/error tests | Same input through draft/change/blur/pending/completion | PASS before/after |
| Pure output freshness/source immutability | None | Frozen record/array and independently mutable outputs | PASS |
| Formatter and disabled truth table | UI cases | Six value/draft and three permission/saving combinations | PASS |
| Remaining page, navigation, errors/races | Existing four suites | No changes | PASS |

An initial new-test fixture omitted pagination `total`, causing the original
pagination loop to keep running. The process was explicitly terminated, the
fixture corrected, and the final15-characterization run passed before any
runtime edit. This was a test authoring error, not an application regression.

## Changes

The adjacent pure model selects ordered typed indicator descriptors; the
parent renders one span per descriptor rather than nested conditional JSX.
A single KM projection removes duplicate formatting/disabled policy from
the two existing inputs. There is no component explosion or mega-context.
The page diff is15 lines,6 additions/9 removals; the model is22 effective LOC.
Both functions and the filter callback remain below warning thresholds.

## Metrics before / after / delta

Aggregates include **every callable** in the complete page and the complete
new model, including new map/filter callbacks, not only edited lines.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 437 | 420 | **-17** |
| Principal cyclomatic | 385 | 371 | -14 |
| Principal LOC | 2080 | 2076 | -4 |
| Principal nesting / params | 2 / 0 | 2 / 0 | 0 / 0 |
| Aggregate cognitive | 1273 | 1230 | **-43 (-3.38%)** |
| Aggregate cyclomatic | 1350 | 1319 | **-31 (-2.30%)** |
| Aggregate effective file LOC | 2858 | 2877 | **+19** |
| Aggregate callable LOC, overlapping ranges | 4508 | 4520 | **+12** |
| Aggregate callable count | 303 | 307 | +4 |
| Error findings | 18 | 17 | -1 |
| Warning findings | 23 | 21 | -2 |
| Page useState / useEffect | 21 / 13 | 21 / 13 | 0 / 0 |

Page cognitive1222/cyclomatic1309/LOC2855. Model cognitive8/cyclomatic10/LOC22,
zero findings. Exactly298/303 old callable records retain identical name,
fingerprint and all cognitive/cyclomatic/LOC metrics. LOC growth is disclosed;
this is not a LOC-reduction claim. Callback nesting accounts for the larger
aggregate decrease than principal decrease; every new callback is included.

| New model callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
|---|---:|---:|---:|---:|---:|
| dailyCellIndicators | 5 | 5 | 14 | 2 | 3 |
| filter callback | 0 | 1 | 1 | 0 | 1 |
| kmInputPresentation | 3 | 4 | 6 | 0 | 4 |

## Tests and coverage

Final focused run: **413 PASS / 5 files**, zero skips,34.02s,exit0.
Smoke: **18 PASS**,zero skips,exit0. Typecheck: **PASS**,exit0.

| Modified runtime | Statements | Branch outcomes | Functions | Result |
|---|---:|---:|---:|---|
| page.tsx | 1094/1094 | 1217/1217 | 302/302 | **100%** |
| daily-cell-model.ts | 8/8 | 14/14 | 3/3 | **100%** |

Combined lines903/903. All V8 counters inspected; no missing statement/branch
outcome. No coverage ignore, threshold, include/exclude configuration change.
Typecheck completed on the final runtime/test code. Final ESLint zero errors,
three old page warnings independently reproduced on starting-source snapshot:
unused detail-loading state and two missing effect dependencies. No new
warnings, suppression or inline comments. `git diff --check` PASS.

Commands from the author checkout:

```bash
git status --short
git rev-parse HEAD
git merge-base HEAD main
/home/cbo/CursorProjects/GAIA/backend/.venv/bin/python tools/code_quality/complexity.py report \
  frontend/src/app/presenze/giornaliere/page.tsx \
  frontend/src/app/presenze/giornaliere/daily-cell-model.ts \
  --json /home/cbo/.cache/gaia-campaign/20261009-r6-presenze/author/after.json \
  --markdown /home/cbo/.cache/gaia-campaign/20261009-r6-presenze/author/after.md
make complexity-ratchet BASE_REF=main
make graphify-frontend
make graphify-frontend-query Q='dailyCellIndicators'
git diff --check
```

From frontend, with the existing ignored node_modules link:

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/app/presenze/giornaliere/daily-cell-model.ts \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  tests/unit/presenze-giornaliere-r6.test.tsx \
  --coverage.reportsDirectory=/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/author/final-coverage
npm run typecheck
./node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx \
  src/app/presenze/giornaliere/daily-cell-model.ts tests/unit/presenze-giornaliere-r6.test.tsx
npm test
```

Before report omits the then-absent model; before coverage explicitly includes
the full page using the same supported environment variable. Full frontend
unit/build/browser gates belong to the independent final verifier and are
**not claimed PASS in this author report**.

## Ratchet

**PASS0 findings**,authoritative main55a baseline,exit0. Baseline unchanged,
SHA256 `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No baseline generation,
repair, thresholds, exclusions, ignores or tooling change. Existing global30
divergences and Capacitas coverageFAIL remain separate and unresolved here.

## Classification

**IMPROVED**: genuine aggregate cognitive-43/cyclomatic-31, three findings
removed, model zero findings, behavior characterized and full-file100%.
The function remains420cognitive, still extreme; the original50% target and
global campaign are **not complete**. No artificial transfer to a mega helper.

## Files changed and commit

- `frontend/src/app/presenze/giornaliere/page.tsx`
- `frontend/src/app/presenze/giornaliere/daily-cell-model.ts`
- `frontend/tests/unit/presenze-giornaliere-r6.test.tsx`
- `domain-docs/presenze/docs/DAILY_CELL_REFACTOR_2026-10-09.md`
- This report.

Source commit: `refactor(presenze): consolidate daily operational presentation`;
resolve its exact SHA using `git log -1 --format=%H -- frontend/src/app/presenze/giornaliere/daily-cell-model.ts`.
No main edit/merge, push, PR or integration by the author.

## Architecture / Graphify

Fresh worktree orientation query initially had no graph; coordinator's
frontend corpus provided orientation. Dedicated `make graphify-frontend`
now updates AST code graph:6003nodes12568edges226communities,exit0; follow-up
query locates the new model boundary. HTML skipped by the existing5000-node
limit; not an analysis failure. No graph artifacts committed. Dedicated
`make graphify-presenze-docs` completed both chunks1/2 and2/2,zero semantic
failure,54nodes56edges9communities,exit0;99731input9006output tokens,estimated
$0.0543. The new domain doc preceded that successful refresh; no later domain
doc edits. Final typecheck after all25R6 tests also exit0.

## Residual risks and recommended next slice

One daily-cell responsibility only; stop after reviewed integration. The page
remains monolithic with21useState/13useEffect and many unrelated decisions.
Full frontend/build/browser verification is pending independent integration.
Next separately authorized responsibility should address another measured
cohesive decision model in this extreme page, not move a large render section.

Durable evidence: `/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/author/`:
before/after JSON+MD, before-tests.log, characterization-before.log and
reconstructed identical15-case characterization source, final-tests.log,
final-coverage/coverage-final.json,coverage-audit.json,metric-delta.json,
ratchet.log,typecheck.log,eslint-before.log,eslint-final.log,smoke.log,
graphify-code.log and graph-query-after.log. Transient external fixture replay
is not a repository test or coverage-scope modification.
