# C9 — Actual No-Sheet Workbook Characterization

## Ownership / baseline / target callable

Root exclusively owns new `campaign-capacitas-empty-workbook.test.tsx` and
this report in `GAIA-campaign-20261008-c9-tests`, branch
`refactor/complexity-capacitas-empty-workbook-tests`, preventive registry91d1fbca.
Source39dbcc40, merge-base main55a1b1d35911451e018b662c2acc450bf5994ea2.
Runtime, original19batch tests, config/tooling/baseline are read-only and
byte-identical. Initial batch coverage305/857s263/929arms46/251f288/748lines,
already reproduced in identical runtime worktrees C2a/C2b. No runtime owner
granted; target is two actual missing-sheet reader guards285/382.

## Behavioral invariants / matrix / changes

No XLSX.read, sheet_to_json or private helper mock. Factory serializes an
actual single-sheet OOXML workbook through installedSheetJS0.20.3, edits its
archive workbook.xml sheet collection to `<sheets/>` using real CFB ZIP APIs,
and reserializes actual bytes. A precondition asserts the real parser returns
SheetNames[]; the workspace then independently reads those same bytes through
its File.arrayBuffer boundary. File polyfill returns the genuine binary buffer,
not a parser result. No binary fixture is committed. This is a malformed user
upload accepted by the installed parser, not a claim that no-sheet Excel is
valid or supported by every spreadsheet application.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Terreni parser accepts bytes but finds no first sheet | Existing empty sheet tests return a named sheet | Yes | Actual upload, empty-batch notice, rows cleared/button disabled, filename retained, no create call | PASS |
| Storico parser accepts bytes but finds no first sheet | Same gap | Yes | Actual upload in Batch da file, zero rows, disabled import, no create call, input re-enabled | PASS |

Public UI and real workspace, mocked API/token only at their actual boundary.
Authorization and live external portal behavior not asserted. Neither guard
removed; two reachable statement paths genuinely characterized.

## Metrics before / after / delta

Runtime SHA256 unchanged
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`:
principal cognitive472/cyclomatic416/LOC2631/nesting2/params1; fileLOC3109,
useState31/useEffect2,251callables,1099/1174sums,24error20warning; all delta0.
No complexity improvement, responsibility move, laundering or runtime edit.

## Tests / coverage / ratchet

```bash
cd frontend
npm run test:unit -- tests/unit/campaign-capacitas-empty-workbook.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-empty-workbook.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c9-after
./node_modules/.bin/tsc -p /tmp/capacitas-c9-test-tsconfig.json --noEmit
npm run typecheck
./node_modules/.bin/eslint tests/unit/campaign-capacitas-empty-workbook.test.tsx
npm test
cd ..
make complexity-ratchet BASE_REF=main
```

21testsPASS0skip, scopedlint/runtime and explicitnew-specTypeScriptPASS,
smoke18PASS,diffcheckPASS. Temporary supplemental test config only in/tmp;
project config excludes tests so runtime typecheck alone is insufficient.
Actual cumulativecoverage333/857statements304/929arms53/251functions314/748
lines (38.85/32.72/21.11/41.97%); **full-file gateFAIL exit1**. Delta vs
original batch+28s/+41arms/+7f/+26lines, not sums of other independent suites.
RatchetmainPASS0exit0, log`/tmp/capacitas-c9-ratchet.log`. No full suite/build/
E2E per micro-slice, no inherited full-suite acceptance of new test code.

All attempts retained: disposable probe initially failed lookup/update with
CFB relative paths; exact `Root Entry/xl/workbook.xml` fixes archive selection,
not application behavior. Probe correctedexit0 with actual SheetNames[].
Initial newUItests0/2PASS (19/21combined): incorrect assumption that parsing
error clears filename. Existing behavior retains File and clears parsed items,
so corrected exact UI assertions (filenameTerreni, zero rowsStorico), not
runtime. After21PASS, logs`/tmp/capacitas-c9-tests.log`/`...after.log`.

## Classification / files / commit / residual risks

**NO_CHANGE — CHARACTERIZATION_ONLY**. Exactly two owned new files. Source
coherent commit authorized; exact SHA supplied after commit. Independent
review/integration required; no self-integration. Runtime refactor remains
unauthorized while full-file coverage incomplete and GIS decision pending.
Defensivebranchprovenance separately proves16 candidate-unreachable arms;
these two missing-sheet guards are explicitly reachable and remain present.
Recommended next action: genuine combined coverage of all reviewed suites and
residual branch ledger, no impossible parser mocks or exclusions.
