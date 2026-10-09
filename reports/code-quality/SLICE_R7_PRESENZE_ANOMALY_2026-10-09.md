# R7 Presenze author — Complexity Slice Report

## Ownership

Exclusive `page.tsx`, adjacent new `anomaly-panel-model.ts`, new
`frontend/tests/unit/presenze-giornaliere-r7.test.tsx`, this report and
`domain-docs/presenze/docs/ANOMALY_PANEL_REFACTOR_2026-10-09.md`.
Registry established in integration before delegation. No shared files changed.

## Baseline

Clean branch `refactor/complexity-r7-presenze-anomaly`, initial
`ef322424ff54e829daee5e4bd5bd01a7aab1ebb7`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Main concurrent work preserved;
owned frontend paths clean at assignment. Dedicated ignored dependency symlink
uses the installed integration dependencies without manifest/config changes.

## Target callable

PresenzeGiornalierePage, one responsibility only: anomaly-panel grouping,
priority/date/name comparators and exact kind counting. Extreme queue target
50%/under250 is not achieved by this slice and remains open.

## Behavioral invariants

Priority arithmetic and strict `!== 0` short-circuit retain NaN; month priority→
date→name, day priority→name, collaborator priority→date. Native stable sorting,
localeCompare argument/evaluation order, Map insertion, duplicate references and
source immutability retained. Comparison fallback empty differs from group label
fallback ID; empty names stay empty. Group count/total/name sorting unchanged.
Memo positions/dependencies, classification/filtering, first record selection,
UI/JSX, API/permissions/state/commands and other helper functions unchanged.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Full daily page lifecycle/API/UI | page + regressions suites | no | none | PASS |
| Day/collaborator priority and filter/first action | existing broad UI | explicit ordered assertions | 2 UI | PASS original/result |
| NaN/undefined stable day order and first action | insufficient explicit trap | yes | 2 UI | PASS original/result |
| Empty and exact unknown-kind counts | no model before | direct model boundaries | 1 pure | PASS |
| Frozen duplicate identity/stable groups | no explicit frozen input | yes | 1 pure | PASS |
| NaN/undefined/±Infinity lazy priority | UI plus oracle | direct no-name trap | 4 pure | PASS |
| Null coercion/finite date fallback | broad comparisons | explicit boundary | 1 pure | PASS |

Four UI tests passed before runtime edits. Coordinator/reviewer approved typed
design after original characterization and independent page100% coverage.
Independent reviewer owns frozen-original AST differential; author does not
claim a copied expected implementation as an independent oracle.

## Changes

Typed domain model provides shared lazy comparison chain, keyed anomaly group
collector, exact shared two-filter count projection and day/collaborator builders.
Three comparator chains and two collection/count implementations no longer
duplicate branching. No JSX extraction, relocation mega-helper, reducer or new
state/effect. Model18callables maximum cognitive3/cyclomatic4; zero findings.

## Metric before / after / delta

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 420 | 403 | -17 |
| Principal cyclomatic | 371 | 356 | -15 |
| Principal callable LOC | 2076 | 2020 | -56 |
| Principal nesting/params | 2/0 | 2/0 | 0/0 |
| Page file LOC | 2855 | 2778 | -77 |
| Affected page+model cognitive | 1222 | 1192 | -30 |
| Affected cyclomatic | 1309 | 1284 | -25 |
| Affected file LOC | 2855 | 2879 | +24 |
| Affected callable LOC | 4499 | 4433 | -66 |
| Affected callables | 304 | 308 | +4 |
| Affected findings | 38 | 38 | 0 |
| Whole daily-directory cognitive | 1289 | 1259 | -30 |
| Whole daily-directory cyclomatic | 1383 | 1358 | -25 |
| Whole daily-directory file LOC | 3065 | 3089 | +24 |
| Page useState/useEffect | 21/13 | 21/13 | 0/0 |

New model101effectiveLOC, cognitive20/cyclomatic35 total. File LOC growth is
disclosed rather than claiming all metrics or finding counts decreased.

## Tests

- Before5focusedfiles413PASS, zero skips/exit0.
- Original new UI characterization4PASS before runtime; independent replay
  also4PASS. After6focusedfiles424PASS, zero skip/failure/exit0, durable JUnit.
- `npm run typecheck` PASS/exit0.
- Targeted ESLint PASS/exit0: three existing page warnings (unused loading state,
  two effect-dependency warnings), none in new runtime/tests; no ignores added.
- Full frontend/build/browser reserved for independent frozen-source verifier;
  not claimed PASS here.

## Coverage

Existing5focusedfiles original page1094/1094statements1217/1217branches302/302
functions100%. Final page1048/1048statements1189/1189branches288/288functions;
model39/39statements16/16branches18/18functions100%. No runtime exclusions or
coverage/config changes. VITEST_COVERAGE_INCLUDE selects both complete files.

## Ratchet

`make complexity-ratchet BASE_REF=main`: PASS0/exit0 using authoritative55a.
`make complexity-report REPORT_JSON=<durable>/after.json REPORT_MD=<durable>/after.md`:
PASS/exit0. No baseline generation/repair, threshold/scope/ignore updates.
Global30historical provenance divergences are not changed or absorbed.

## Classification

IMPROVED — aggregate cognitive-30/cyclomatic-25 without new helper findings or
artificial relocation. Not file-LOC/finding improvement; not global completion.

## Files changed

The five owned files only. Graphify artifacts ignored and never committed.

## Commit

Single campaign-only coherent commit `refactor(presenze): consolidate anomaly panel ordering`;
the actual source SHA is in the integration/review report (self-reference omitted).
No main merge, push or PR.

## Residual risks

Principal403 remains extreme; existing21states13effects and other responsibilities
unchanged. Native localeCompare/NaN sorting semantics intentionally preserved.
Coverage is full-file execution evidence, not proof of equivalence alone;
independent frozen-original differential/AST review and integration gates required.

## Recommended next slice

After review and green integration, choose another coherent extreme frontend
responsibility; do not extend this author's scope indiscriminately.

## Evidence

Durable `/home/cbo/.cache/gaia-campaign/20261009-r7-presenze/author/`:
before/afterJSON+MD, aggregateJSON, original characterization log, final focused
JUnit and coverageJSON, test/ratchet/lint exit files, typecheck and Graphify logs.
Graphify completion is captured in its exit/log artifacts and independently
checked before committing; semantic docs exit0 alone is not sufficient.
Forced frontend update6014nodes12594edges241communities/exit0. Presenze docs
extract34files46nodes49edges8communities/exit0, chunks1/2and2/2done, zero
semantic failures;100337input8255outputtokens, estimated$0.0533. No domain-doc
edits after this completed refresh; no graph artifacts included.
