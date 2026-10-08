# Capacitas C8 — Template Download Characterization

## Ownership / baseline

Authorized test-only slice, registry `a31d9beb`, branch
`refactor/complexity-capacitas-templates-tests`, dedicated worktree
`/home/cbo/CursorProjects/GAIA-campaign-20261008-c8-tests`.
Preflight HEAD `39dbcc40273cfca699b576b8445ccd378e822a46`, authoritative
merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Tracked working tree clean; preflight additionally showed untracked `.venv`
dependency symlink. It disappeared during concurrent owner activity; this
agent did not modify/remove/stage it. Dependency link `frontend/node_modules`
was reused, not installed or rebuilt.

Ownership only:

- `frontend/tests/unit/campaign-capacitas-templates.test.tsx`
- `reports/code-quality/SLICE_CAPACITAS_C8_2026-10-08.md`

Read `PLAN_CAPACITAS_COVERAGE_2026-10-08.md` and project instructions. Existing
runtime/tests/shared/config/baseline/thresholds/ignores remain untouched.
Source commit is authorized; integration and new runtime work are not.

## Target / behavioral invariants

Characterize real public Terreni/history CSV/XLSX template buttons and browser
download lifetime. No refactoring or extraction. Actual runtime functions:
`triggerDownload`248–255, `downloadTerreniTemplate`341–373,
`downloadAnagraficaHistoryTemplate`416–435, and their public button callbacks.

- Terreni CSV/XLSX filenames remain `capacitas-terreni-template.*`; history
  filenames remain `capacitas-anagrafica-storico-template.*`.
- CSV MIME `text/csv;charset=utf-8`, exact header/ordered examples/empty fields.
- XLSX MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,
  real ZIP bytes and readable serialized workbook, not a fabricated fixture.
- Terreni sheet order `terreni`, `istruzioni`; history sheet `storico` only.
  All six Terreni instruction rows, their required flags and descriptions are
  preserved. Subject UUID/IDXANA examples retain their exact identifier strings.
- Created anchor has the actual object URL and filename at click time.
- Every object URL survives999ms, is revoked exactly at1000ms, once only.
  Staggered exports have independent URL/filename/revocation timing across
  section navigation, and scheduled release survives workspace unmount.
- History template buttons exist in file mode, not manual mode. Returning to
  manual mode does not cancel an already generated download.

## Tests / boundary design

Real workspace, React effects, `usePolling`, XLSX read/write/utils and Blob
execute. Only auth/API list boundaries and unused ProtectedPage/settings child
are doubled. Browser object-URL methods and anchor `click` are the explicit
I/O boundary spies. Anchor fields are captured from the actual DOM element;
real Blob contents are read back. URL property descriptors and prototype spies
are restored after each test; no shared test setup modification.

Fake timers begin **after** mount/list completion and control only download
timing. No fake parser, impossible XLSX structures, private closure invocation,
React-state manufacturing, new export, ignore or instrumentation.

| Behavior | Existing test | Missing / added | Result |
| --- | --- | --- | --- |
| Terreni CSV exact filename/MIME/header/two examples | Batch tests parse supplied files, no template assertions | Real button→Blob→exact text and XLSX parse | PASS |
| History CSV identifier columns and ordered examples | Absent | Real file-mode button→exact CSV/parsed rows | PASS |
| Terreni XLSX data plus six instruction rows | Absent | Real ZIP magic, sheets/order/content/required flags | PASS |
| History XLSX one sheet and identifiers | Absent | Real ZIP magic and workbook rows | PASS |
| Anchor URL/filename and1000ms lifetime | Absent | Checked in both formats/domains,999ms negative assertion | PASS |
| History manual/file controls and in-flight download | Absent | File-mode export→manual hides buttons; release still scheduled | PASS |
| Staggered cross-section exports | Absent | First URL release1000ms, second1250ms after250ms offset | PASS |
| Unmount after XLSX export | Absent | Actual generated workbook, release still occurs once at1000ms | PASS |

7 new tests (two CSV, two XLSX, three lifecycle/interaction cases).
Existing19 batch tests unchanged. Final focused suite: **26 PASS,2 files,
no skips,exit0**. C0/C6/C7 concurrent specs are not integrated into this branch
and are not represented in these cumulative counters.

## Changes / metrics before, after, delta

Fresh runtime-scoped `/tmp/capacitas-c8-complexity.json` has exactly the same
`files` and `callables` objects as `/tmp/p2-capacitas-before.json`.

| Runtime metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive / cyclomatic | 472 / 416 | 472 / 416 | 0 |
| Main callable LOC / nesting / params | 2631 / 2 / 1 | 2631 / 2 / 1 | 0 |
| File effective LOC / callables | 3109 / 251 | 3109 / 251 | 0 |
| File cognitive sum / cyclomatic sum | 1099 / 1174 | 1099 / 1174 | 0 |
| File errors / warnings | 24 / 20 | 24 / 20 | 0 |

Classification **NO_CHANGE / CHARACTERIZATION_ONLY**, not `IMPROVED`.
No code moved, no complexity transferred and no runtime hotspot closed.

## Coverage — full-file gate remains FAIL

Fresh baseline, C8-only and combined executions use the existing V8 provider
and full-workspace include mechanism with unchanged four100% thresholds.

| Counter | Before: batch19 | C8-only7 | After: batch19+C8=26 | Covered delta |
| --- | ---: | ---: | ---: | ---: |
| Statements | 305/857 (35.58%) | 226/857 (26.37%) | 342/857 (39.90%) | +37 |
| Branch arms | 263/929 (28.31%) | 146/929 (15.71%) | 296/929 (31.86%) | +33 |
| Functions | 46/251 (18.32%) | 27/251 (10.75%) | 59/251 (23.50%) | +13 |
| Lines | 288/748 (38.50%) | 221/748 (29.54%) | 324/748 (43.31%) | +36 |

Missing after: **515 statements,633 branch arms,192 functions,424 lines**.
Every coverage command exits1 for unmet full-file thresholds despite passing
tests. This is explicitly **not coverage compliance**, a green coverage gate,
or permission for the cognitive472 runtime refactor.

Assigned download/template function regions move from0/26→26/26 statements,
0/4→4/4 functions,0/4→4/4 branch arms. Region100% is reported only as local
responsibility evidence; it does not replace the full-file gate.

Coverage JSON artifacts and SHA256:

- `/tmp/capacitas-c8-before-coverage/coverage-final.json`:
  `b26ee23fa479cc4899b1b69a47125e8f2f235c186a355a0c9b7a292bc376e9c7`.
- `/tmp/capacitas-c8-only-coverage/coverage-final.json`:
  `3f703ae239c831f11f54c886e57087df4c10146f3d5c25cce82e1a15b32ce45d`.
- `/tmp/capacitas-c8-after-coverage/coverage-final.json`:
  `fd72fe15c55108ae3bbb2d62ff6f8ada21386881c750eeec3fd57ac2542f8a66`.

## Reproducible validation

From the dedicated frontend directory:

```bash
npm run test:unit -- tests/unit/campaign-capacitas-templates.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2

VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-templates.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory=/tmp/capacitas-c8-after-coverage

npm run typecheck
npm test
npm run lint -- --file tests/unit/campaign-capacitas-templates.test.tsx
node_modules/.bin/tsc -p /tmp/capacitas-c8-test-tsconfig.json --noEmit
```

Root: `make complexity-ratchet BASE_REF=main`, and scoped
`python tools/code_quality/complexity.py report frontend/src/components/elaborazioni/capacitas-workspace.tsx --json /tmp/capacitas-c8-complexity.json --markdown /tmp/capacitas-c8-complexity.md`.

| Gate | Result | Local log, prefix `/tmp/capacitas-c8-` |
| --- | --- | --- |
| Final focused C8+batch | 26 PASS,exit0 | `characterization.log` |
| Baseline/C8-only/combined coverage tests | 19/7/26 PASS; each coverage gate FAIL exit1 | `before/only/after-coverage.log` |
| Repository frontend typecheck | PASS exit0 | `typecheck.log` |
| Supplemental new-test typecheck | PASS exit0 | `test-typecheck.log` |
| Existing smoke | 18 PASS exit0 | `smoke.log` |
| Scoped new-test ESLint | PASS exit0 | `lint-final.log` |
| Ratchet `main` against55a1b1 merge-base | PASS,0 findings,exit0 | `ratchet.log` |
| Fresh scoped AST | Exact existing file/callable metrics | `complexity.json/.md/.log` |

Repository TypeScript config excludes tests. Supplemental `/tmp` config extends
it and explicitly includes the new test with absolute Vitest/jest-dom type
locations. No committed config is changed. No full suite, build or E2E run.
No Graphify runtime refresh required: no runtime boundaries/dependencies change.

## Initial failures / review

Initial new suite3/7 PASS,4 failures retained in `focused.log`: three binary
reader assertions saw `Sheet1` when raw Blob ArrayBuffer was supplied to
SheetJS, despite the correct ZIP magic bytes. The new spec now uses a standard
`Uint8Array` view of the **same real bytes** as its supported array input;
workbook/sheet/example assertions are unchanged and pass. This is test-harness
input representation handling, not a mocked parser or modified download.
The fourth failure over-specified spacing in the composed nav accessible name;
the new spec uses its distinct `Storico anagrafico` prefix. No timeout/skip,
runtime, existing fixture or workbook assertion was weakened.

Review verifies exact content, Blob MIME, actual anchor attributes, negative
pre1000ms checks, once-only revocation, independent staggered lifetimes and
descriptor restoration. ESLint prints its existing Next16 deprecation notice,
not a new warning/error. No unrelated concurrent file was staged.

Unchanged SHA256 runtime
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`,
existing19 batch suite
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`,
baseline `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

## Commit / residual risks / next action

Authorized two-file source commit message:
`test(capacitas): characterize real CSV and XLSX template downloads`.
Actual SHA returned to Coordinator. Status **READY_FOR_REVIEW**, not integrated.

Browser OS save dialog/file-system persistence is not exercised; the meaningful
I/O seam verifies actual anchor/Blob/workbook and URL lifecycle. No claim of
native-browser download coverage or global compliance. Other workflows and
defensive branches remain governed by the coverage closure plan.
Recommended next action: independent integration review/cumulative measurement
with approved non-overlapping C0/C6/C7 sources, then a separately owned next
test-only slice. Runtime wave remains held pending Coordinator/GIS decision.
Stop here; no integration, governance edit or new runtime activity.
