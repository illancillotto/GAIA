# Capacitas C3 — Storico input characterization

## Ownership and preflight

Explicit Coordinator assignment, registry integration `cfda21fa`, test-only
C3 ACTIVE. Dedicated worktree `GAIA-campaign-20261008-c3-tests`, branch
`refactor/complexity-capacitas-storico-input-tests` from clean
`39dbcc40273cfca699b576b8445ccd378e822a46`. Authoritative merge-base main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Own exclusively:

- `frontend/tests/unit/campaign-capacitas-storico-input.test.tsx`.
- This report `reports/code-quality/SLICE_CAPACITAS_C3_2026-10-08.md`.

Checkpoint/complexity skills, repository constraints and the integration copy
of `PLAN_CAPACITAS_COVERAGE_2026-10-08.md` applied. All runtime, original tests,
monitor/result expansion, C0/C6/C7 files, config/shared files, main and
integration read-only. No baseline, threshold, ignore, coverage exclusion,
export, private state seam or runtime correction. Existing 19 batch cases
preserved byte-for-byte.

## Responsibility and observable invariants

Manual/CSV/XLSX preparation → actual user submit → API call → feedback and
awaited refresh. Real React workspace, domain chrome, polling hook and XLSX
library; API/auth/ProtectedPage/unrelated settings-modal boundaries mocked.

- Manual delimiter normalization accepts newline, comma, semicolon, tab and
  space, trims and discards empty tokens. It does **not** deduplicate. Subjects
  always precede IDXANA tokens, each paired with the other field null.
- CSV header normalization preserves current `SUBJECT ID`, `Subject-ID`,
  `subject_id`, case and whitespace behavior; only canonical normalized
  subject_id/idxana aliases are accepted. No invented alias or parser rewrite.
- Actual CSV comma/semicolon/tab formats and actual XLSX/XLS workbooks parse
  through the unchanged library. Only first worksheet is read. Accepted rows
  preserve order, both identifier fields together, trimmed values and null
  counterpart. Empty required cells with extra-column data are skipped; real
  blank rows remain governed by XLSX's actual parser output.
- Missing required header or no valid data clears previous batch items and
  skipped count, disables submit/reset. Empty first worksheet is still empty
  even if a later worksheet has identifiers. No fake sparse arrays or missing
  worksheet manipulation used to hit defensive branches.
- File text/arrayBuffer I/O errors preserve Error messages or the non-Error
  fallback, clear prepared data and release file controls. A valid subsequent
  upload clears error. Empty file selection/reset clears file/items/error/
  skipped state, without erasing independent manual input.
- Manual/file mode changes preserve both inputs independently; only active
  mode contributes to payload. Selected credential becomes numeric; default
  is undefined. Continue-on-error is user's current boolean; auto_resume true.
- Create dispatches exact prepared items using current token. Busy submit
  blocks duplicate clicks through both create and its awaited refresh. Feedback
  precedes refresh completion; currently enabled manual textareas can change
  while pending without changing the captured payload. Inputs are not reset
  after successful import.
- Create failure does not refresh or discard input. Errors/auth ApiError use
  existing generic create catch, not invented monitor authentication behavior.
  Successful create with failed follow-up refresh retains its creation status,
  shows refresh error and releases import busy state. Token loss before submit
  causes silent no-request; restoration allows next genuine submission.

## Characterization matrix

| Behavior | Existing direct workspace evidence | C3 addition | Result |
|---|---|---|---|
| Empty/delimiter-only manual input | None | Disabled submit, no API | PASS |
| Every manual delimiter/order/duplicates | None | 12 exact items, subjects before IDXANA, no reset | PASS |
| Credential/default and continue_on_error | None | Selected9, single7→backend default, flagfalse | PASS |
| Real CSV separators and normalized aliases | None | Three actual separator formats, trim and row pairs | PASS |
| Subject-only / IDXANA-only columns | None | Two exact null-counterpart payloads | PASS |
| Actual XLSX/XLS first-sheet selection | None | Two real workbook formats, populated later sheet ignored | PASS |
| Whitespace/extra-only/blank rows | None | Two skipped parser records, later valid IDs/order | PASS |
| Invalid/missing headers or no valid data | None | Three invalid CSV cases clear prior items | PASS |
| Empty first sheet | None | Actual empty worksheet + valid second sheet stays disabled | PASS |
| CSV/Excel I/O Error/non-Error | None | Four file-boundary rejections and valid retry | PASS |
| Mode preservation/reset | None | Active mode only; manual data survives batch reset | PASS |
| Empty file change after errors | None | Data/skipped/error cleared, no stale dispatch | PASS |
| Deferred read busy controls | None | No submit/reset until real read finishes | PASS |
| Deferred create→refresh ordering | None | Captured payload, edited textarea retained, busy until refresh | PASS |
| Create Error/non-Error/auth rejection | None | Three cases retain input, retry/clear error, no early refresh | PASS |
| Follow-up refresh failure | None | Successful-create feedback remains, submit released | PASS |
| Lost/restored submission token | None | No create without token; restored token used for create/refresh | PASS |
| Existing Terreni batch suite | Existing19 | Unchanged original suite rerun | PASS |

New C3 **29 PASS**, combined C3+batch **48 PASS / two files**, zero skipped.
Focused and coverage test assertions all pass on unchanged runtime. No monitor
rerun/delete, result expansion, harvest submission or template downloads added.

## Failures and explicit new-spec typing

First C3 run: **29 PASS**, no test failure; combined 48 also PASS.
Normal `npm run typecheck` PASS but repository tsconfig excludes `tests`, so
it does not certify the new spec. A temporary configuration in `/tmp` extends
the repository config and explicitly includes the new test, runtime and
next-env, with incremental disabled and Vitest/jest-dom types.

Initial temporary config failed TS2688: type names resolved relative to `/tmp`
instead of project node_modules. Corrected only the temporary config's type
entries to absolute worktree dependency paths. Final explicit new-spec
typecheck PASS, no repository configuration modification. Preserve initial
failure `/tmp/capacitas-c3-spec-typecheck.log`; successful v2/final logs and
exact temporary config `/tmp/capacitas-c3-tsconfig.json`.

## Before / after runtime metrics

Fresh AST measurements and structural-fingerprint comparison:

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 472 | 472 | 0 |
| Principal cyclomatic | 416 | 416 | 0 |
| Principal callable LOC | 2631 | 2631 | 0 |
| Principal nesting / params | 2 / 1 | 2 / 1 | 0 / 0 |
| Aggregate cognitive | 1099 | 1099 | 0 |
| Aggregate cyclomatic | 1174 | 1174 | 0 |
| Effective file LOC | 3109 | 3109 | 0 |
| Callables | 251 | 251 | 0 |
| Errors / warnings / findings | 24 / 20 / 44 | 24 / 20 / 44 | 0 |
| useState / useEffect | 31 / 2 | 31 / 2 | 0 / 0 |

File and callable metric objects are exactly identical, not an apparent
improvement caused by moving code. Classification **NO_CHANGE /
CHARACTERIZATION_ONLY**. Principal472 runtime refactor remains blocked.

## Full-file coverage — expected gate FAIL

Thresholds/scope unchanged: before existing 19 batch; after C3+batch 48.
Counters inspected directly, preserving every branch arm and denominator:

| Counter | Before covered/total | After covered/total | Delta covered | Percent before→after |
|---|---:|---:|---:|---:|
| Statements | 305/857 | 395/857 | +90 | 35.58→46.09 |
| Branch arms | 263/929 | 345/929 | +82 | 28.31→37.13 |
| Functions | 46/251 | 69/251 | +23 | 18.32→27.49 |
| Lines | 288/748 | 371/748 | +83 | 38.50→49.59 |

Both coverage commands exit 1 because full-file 100 thresholds are unmet;
their tests all pass. These runs are **coverage FAIL**, not compliance/PASS.
Source map reaches line 3268 of 3270 in before/after; no truncated tail,
whole-file ignore or reduced denominator. Coverage elsewhere still missing.

File-reader band 374–413 (partition by source location): statements 0/29→28/29,
branch arms 0/34→27/34. Seven unhit reader arms remain explicit:

- 378: impossible-to-empty `split('.').pop() ?? ''` fallback candidate.
- 382: no-first-sheet guard, not reached by real supported files tested.
- 388/390: `data[0] ?? {}` after nonempty `sheet_to_json` result.
- 403: `data[index] ?? {}` parser-contract dependent fallback.
- 404/405: header-map fallback for selected keys built from those same headers.

Do not universally label these dead or add exclusions. No runtime defense
removed; further provenance/decision belongs to a separate authorized unit.
Malformed header/empty/data/skip/I/O branches were reached through real files
or legitimate file-read errors, not fabricated XLSX outputs.

## Reproducible commands and gates

From `frontend/`:

```bash
npm run test:unit -- tests/unit/campaign-capacitas-storico-input.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-batch.test.tsx \
  --maxWorkers=1 --coverage.reportsDirectory=/tmp/capacitas-c3-before-coverage
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- tests/unit/campaign-capacitas-storico-input.test.tsx \
  tests/unit/campaign-capacitas-batch.test.tsx --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/capacitas-c3-after-coverage
npm run typecheck
node_modules/.bin/tsc -p /tmp/capacitas-c3-tsconfig.json --noEmit
npm test
node_modules/.bin/eslint tests/unit/campaign-capacitas-storico-input.test.tsx
```

From root:

```bash
backend/.venv/bin/python tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  --json /tmp/capacitas-c3-after-complexity.json \
  --markdown /tmp/capacitas-c3-after-complexity.md
make complexity-ratchet BASE_REF=main
git diff --check
```

Focused 48 PASS; smoke 18 PASS; ordinary and explicit-spec typecheck PASS;
ESLint exit 0 / zero diagnostics; ratchet **PASS, zero findings**, authoritative
main55a; diff-check PASS. No full-suite/build/E2E duplicated. No runtime changes
mean no new full-file coverage obligation on a modified production file;
existing gap still blocks future runtime refactor and is not waived.

Graphify dedicated orientation query attempted in fresh worktree, graph absent;
Make exits 2, `/tmp/capacitas-c3-graphify-query.log`. No graph-success claim.
Only tests change; no dependency/service/component relationship edited, so
no graph regeneration/API extraction needed for this unit.

## Integrity and evidence

Runtime SHA256 unchanged:
`d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
Existing batch SHA256 unchanged:
`4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
Runtime/batch/baseline/V8-config Git-object hashes compare byte-identical in
`/tmp/capacitas-c3-protected-{before,after}.hash`. Only two owned files added.

Logs `/tmp/capacitas-c3-{first-tests,focused-tests,before-coverage,after-coverage,
typecheck,spec-typecheck,spec-typecheck-v2,spec-typecheck-final,eslint,smoke,
ratchet}.log`; V8 JSON `/tmp/capacitas-c3-{before,after}-coverage/coverage-final.json`;
AST `/tmp/capacitas-c3-{before,after}-complexity.json` and Markdown.

## Commit, residual risks and stop

One expressly authorized test-only two-file source commit after scoped gates
and report completion. Retrieve exact SHA with
`git log -1 --format=%H -- reports/code-quality/SLICE_CAPACITAS_C3_2026-10-08.md`.
No integration, governance edit or follow-up responsibility.

Real UI/file tests do not certify actual provider availability/auth, full
monitor polling or server-side subject validation. Input retention, generic
create auth catch, refresh error behavior and parser defenses are preserved,
not production fixes. Runtime coverage still below policy; no call to begin
large complexity extraction based on these partial results.

STOP **READY_FOR_REVIEW / CHARACTERIZATION_ONLY**. Independent Coordinator
review/integration required; next scope only with fresh ownership.
