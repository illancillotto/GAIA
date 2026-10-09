# R8 author — Complexity Slice Report

## Ownership

Exclusive source `frontend/src/app/presenze/giornaliere/page.tsx`, new assigned
`frontend/tests/unit/presenze-giornaliere-r8.test.tsx`, this report and
`domain-docs/presenze/docs/RECORD_PRESENTATION_REFACTOR_2026-10-09.md`.
No new model file required; no shared/config/baseline/tooling files changed.

## Baseline

Clean author branch `refactor/complexity-r8-presenze-presentation` at
`6a005f1a95ca212e56bcc4648ca430f0936a75e1`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Main concurrent work not copied,
modified, reset or committed. Applicable instructions and complexity skill read.
Fresh before AST agrees exactly with R7 final page file and callable objects.

## Target callable

One finite daily-record label/badge presentation responsibility. Primary and
secondary cell labels were independent error-level helpers (53/40 cognitive),
not just JSX inside the principal. Local finite policy reduces their actual
decision count; no JSX relocation or giant model/context introduced. The Formula
GAIA variant/text pair shares the same bounded badge vocabulary responsibility.

## Behavioral invariants

Preserve status substring precedence perm→fer→anom→malatt→rich; primary trim versus
detail badge nontrim; empty detail status suppressing stato; unknown causes and
inherited-key strings. Retain `??` versus `||`, zero/negative/NaN/infinite numeric
formatting, unworked holiday suppression, effective ordinary/theoretical fallback
and authorization→extra→travel→KM→request secondary priority. Detail `regolare`
status still wins over blocking classification. Formula unknown status defaults
success/Quadrata without creating a header badge. All classifiers/calculators,
DOM/classes/titles/keys/controlledness, hooks, state, effects, dependencies,
cleanup, commands, API calls, identity and permissions remain outside the diff.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Primary/status/cause precedence | page unit cases | composed status, inherited unknown cause | R8 primary cases | original/after PASS |
| Holiday and ordinary fallback | page unit cases | combined supplements and NaN effective ordinary | R8 holiday/minute cases | original/after PASS |
| Secondary priority | page unit cases | competing supplements, NaN/zero overrides | R8 secondary cases | original/after PASS |
| Detail badge vocabulary | page unit cases | regolare plus blocking, exact spaced/empty text | R8 detail cases | original/after PASS |
| Formula badge vocabulary | page unit cases | inherited unknown status | R8 seven formula cases | original/after PASS |
| Whole-page transitions/errors/permissions | original page/regression/R6/R7 suites | none removed | existing cases retained | 468 focused PASS |

## Changes

Finite map for direct absence labels, ordered textual status labels, sets for
worked/absence/critical kinds and a class-to-detail-variant table. Five small
domain-named helpers separate the existing primary analysis/status vocabulary,
worked/critical secondary priorities and Formula GAIA badge pair. No lifecycle,
classification or numeric calculations extracted or modified.

## Metric before

Principal cognitive/cyclomatic/LOC 403/356/2020. Primary 53/29/33LOC; secondary
40/22/24LOC; detail badge 13/11/10LOC. Full-page cognitive1172, cyclomatic1249,
fileLOC2778, callableLOC4326,290callables,38findings,21useState/13useEffect.

## Metric after

Principal399/352/2020. Primary11/9/14LOC; secondary8/7/14LOC; detail badge3/4/5LOC.
New helpers cognitive/cyclomatic: formula1/2, analysis3/4, status9/8, worked9/8,
critical3/4; all below warning. Their callback is counted in the full aggregate.
Full-page cognitive1109, cyclomatic1230, fileLOC2788, callableLOC4319,
296callables,33findings,21useState/13useEffect unchanged.

## Delta

Aggregate cognitive −63 (−5.38%), cyclomatic −19 (−1.52%), callableLOC −7;
fileLOC +10 (+0.36%) and callable +6 explicitly disclosed. Findings38→33,
errors −4/warnings −1 globally; no new helper finding. Principal cognitive−4,
cyclomatic−4; still extreme399, not below300 or initial50% target.
Finite decision chains really removed, not merely moved to another file.

## Tests

Original six focused suites424PASS, full-page100%; original new44UI casesPASS.
After seven focused suites468PASS/0failure/error/skip, exit0, durable JUnit.
Commands use `npm run test:coverage` with existing `VITEST_COVERAGE_INCLUDE` for
the entire modified page, `--maxWorkers=2` and external report directories.
Typecheckexit0; owned ESLintexit0 with three warnings independently reproduced
on untouched original page. `git diff --check` PASS.

Initial wrong `npm test` invocation used the node smoke runner,18smokePASS and
tsx loader failure; retained separately, not misrepresented as unit PASS. First
Vitest44 run43PASS1FAIL because TestingLibrary normalized spaced status text;
test-only exact header badge textContent/variant assertion fixed the selector,
runtime untouched, then original44PASS. No runtime workaround or test weakening.

## Coverage

Entire modified page before1048/1048statements1189/1189branches288/288functions
852/852lines; after1033/1033statements1143/1143branches294/294functions846/846lines.
All100%, no uncovered/partial branches or coverage configuration edits.

## Ratchet

`make complexity-ratchet BASE_REF=main` exit0,0findings, against authoritative55a.
Baseline/scope/exclusions/thresholds/ignore untouched; no baseline-generation or
repair command. Historical global30 diverging findings remain separate.

## Classification

IMPROVED: real aggregate cognitive/cyclomatic decrease with complete coverage;
independent review and integration certification still pending, not inferred.
Campaign remains ACTIVE/INCOMPLETE. Principal still399 and other extreme UI
hotspots are not resolved by this slice.

## Files changed

The four owned files listed in Ownership only. Runtime/test source frozen for
review; docs/reports may be completed after independent review and Graphify.

## Commit

Single Coordinator-authorized campaign source commit:
`refactor(presenze): consolidate daily record label policy`, parent
`6a005f1a95ca212e56bcc4648ca430f0936a75e1`. Obtain its exact SHA with
`git log -1 --format=%H -- reports/code-quality/SLICE_R8_PRESENZE_PRESENTATION_2026-10-09.md`.
No main commit, merge, push or PR.

## Residual risks

Finite label vocabulary is now explicit but the page remains monolithic.
Full frontend/build/browser certification pending independent verifier.
Historical global baseline divergence and Capacitas coverage fail untouched.
Small fileLOC growth disclosed; all unaffected responsibilities protected.

## Recommended next slice

After exact source review/integration certification, select a new coherent
principal responsibility rather than chase unrelated small predicates here.
Do not extend this author ownership automatically.

Durable evidence: `/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/author/`,
including before/after AST/aggregate/coverage/JUnit/exits, original warnings and
failed technical attempts. Dedicated Graphify updates terminal: forced frontend
6027nodes12615edges225communities; Presenze docs55nodes58edges9communities,
chunk1/2 and2/2done, no semantic failure, exit0. Generated artifacts not versioned.
