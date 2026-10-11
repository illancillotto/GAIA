# R30 Catasto AdE — Original Public Workflow Characterization

## Ownership

Author worktree `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/author-worktree`;
branch `refactor/complexity-r30-catasto-ade-characterization`,
HEAD `3b99dea5981dabf2feac1611366ea7405f3a2bcc`, actual main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Exclusive additions:

- `frontend/tests/unit/campaign-catasto-ade-scan-r30.test.tsx`;
- this report.

Coordinator registry R30 precedes author activation. No runtime edits, old-test
edits, shared config/tooling changes, baseline updates, commit, import, push or
main merge. Sole serial native gate token held by author during execution.

## Baseline

Original page SHA256
`855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7`.
Fresh original five-spec baseline: 235 PASS, zero failures/skips.
Native coverage exits 1 ONLY because four unchanged 100% thresholds are unmet.
Two old manual-test React act warnings reproduce the R29 baseline. No warning
suppression; the new AdE focus is warning-free.

Global prior measured snapshot: 1673 files, 20323 callable, 1924 errors,
2740 warnings, 4664 overlapping findings. The finding total is not a count of
independent defects. Baseline date remains October 8, never October 7.

## Target callable

`CatastoAnomaliePageContent`: cognitive 390, cyclomatic 342, effective callable
LOC 2109, nesting 2, parameters 0. File LOC 2267; 24 useState, 10 useEffect;
197 callable, cognitive sum 794, cyclomatic sum 868.

Only original public AdE scan-tab loading, presentation, queue command and
batch workspace boundary are characterized. No runtime decomposition admitted
while complete-page coverage remains below 100%. No manual mutation/wizard
responsibility is added to this slice.

## Behavioral invariants

- A mount loads AdE even on an inactive tab. The loader obtains the current
  token, requests summary, candidates with literal `{ limit: 8 }`, and user
  batches concurrently. It receives no context filters. Year/district/tab
  changes do not rerun this stable loader.
- Promise.all makes publication atomic: summary, candidates and batches become
  visible only when all succeed. Load failure preserves every prior dataset.
  Error objects expose their message; other rejections use the literal loader
  fallback. Later success clears the load error, not a queue success message.
- The literal case-sensitive name prefix is checked before descending
  created_at sort and top-six truncation. Null/empty names, changed case,
  leading whitespace and prefix-in-the-middle are excluded. Bare prefix and
  suffix without separator are accepted. Equal/invalid-date comparisons
  preserve the demonstrated response order. The response input is not mutated.
- Active means the first pending/processing entry in the retained sorted six,
  not any active batch in the complete response. Completed/failed/cancelled
  batches are not active. An old active batch outside the six is invisible.
- Summary zeroes remain zero, last_checked_at is formatted, absent timestamp
  means Mai eseguita; buckets show the first six in response order. Candidate
  rows retain server order without client truncation and show actual optional
  section/subalterno, reason/status fallbacks and PDF indicator.
- Queue command uses current token and literal `{}`. It clears old message and
  error before waiting. Positive created count produces the literal message
  and optional truthy skipped suffix; zero created ignores skipped count and
  reports no new parcel. Response batch_id does not auto-open the workspace.
- Busy disables both public queue and refresh controls through command and
  reload. No duplicate command is dispatched by a disabled click. Command
  success refreshes AdE only, not overview. Command rejection does not refresh.
  Successful queue and failed reload may display both success and loader error.
- Token absence/loss causes no-op without synthetic error; token restoration
  uses the replacement token. Loss after queue starts skips its successful
  reload, retains the success message, and releases busy.
- Late loaders still publish on hidden tabs; returning does not reload. A late
  command reloads while hidden. Unmount does not cancel a pending command or its
  subsequent API requests. These observed legacy semantics are invariants, not
  permission to introduce cancellation or race-policy fixes.
- Name/action/active buttons send batch href, title and literal description to
  the elaborazioni child boundary. Close clears modal state without reload or
  losing scan data; the workspace persists across tabs.

## Characterization tests

The NEW spec mounts the actual exported Next route component. Only public
token/navigation/API and page/modal boundaries are stand-ins. Actual scan JSX,
commands, effects and derived data execute. The modal stand-in verifies parent
props and close callback ONLY: it does not prove actual iframe, CAPTCHA,
worker, browser or authorization-enforcement semantics. Page required module
and roles are asserted, not a claim of real authentication coverage.

No private-handler invocation, copied runtime source, generated AST execution,
fake coverage, skipped test, weakened existing assertion, console suppression
or exclusion is used. Deferred promises are genuinely resolved/rejected inside
async act; pending lifecycle is exercised through public controls.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Fixed-eight token query and context independence | old manual mount checks API call | full AdE/tab/context contract | public mount/context transitions | PASS |
| Concurrent atomic loading and failure retention | incomplete | slowest request and each source rejection | deferred load plus three rejection cases | PASS |
| Summary buckets, candidates and empty/fallback presentation | incomplete | literal order/options/zero counts | mounted DOM assertions | PASS |
| Prefix, sort, ties, invalid dates, top-six and active selection | absent dedicated coverage | all selection rules | batch fixtures and ordered table assertions | PASS |
| Queue outcomes, payload, skipped/zero and refresh order | absent dedicated coverage | success/error/busy rules | deferred command and exact API assertions | PASS |
| Loader/command message coexistence and clearing | incomplete | old-data retention and new-command clearing | genuine refresh transitions | PASS |
| Token absence/loss/restoration | incomplete | command/reload no-op variants | public actions and pending completion | PASS |
| Hidden tab, context, late response and unmount | incomplete | actual legacy lifecycle | mounted tab/unmount transitions | PASS |
| Batch open/close parent boundary | absent | href/title/description/persistence | name/action/active entry and close | PASS boundary only |

## Changes

34 new component tests, no runtime changes. Original five specs are unchanged.
The union executes 269 tests, all PASS, zero failure/skip.

## Metric before / after / delta

Native whole report exits0. All 1673 file objects and 20323 callable objects
match the independently verified R29 root report exactly, as do summary, scope
and engines; no parser/exception errors. Target and file metrics are unchanged.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Main cognitive | 390 | 390 | 0 |
| Main cyclomatic | 342 | 342 | 0 |
| Main LOC | 2109 | 2109 | 0 |
| Main nesting / params | 2 / 0 | 2 / 0 | 0 |
| File LOC | 2267 | 2267 | 0 |
| useState / useEffect | 24 / 10 | 24 / 10 | 0 |
| File cognitive sum | 794 | 794 | 0 |
| File cyclomatic sum | 868 | 868 | 0 |
| Global errors | 1924 | 1924 | 0 |
| Global warnings | 2740 | 2740 | 0 |
| Global overlapping findings | 4664 | 4664 | 0 |

## Tests

All commands execute in the dedicated tree using installed dependencies, no
install/build/browser. Private `evidence/gate.sh` serializes this author's gates
and records exact command, log, exit and disk-before/after. TMPDIR and bytecode
are under the isolated SSD directory. Root minimum 100 MiB is checked before
each gate. No cleanup, deletion, data movement or existing evidence overwrite.

- Native original five-spec coverage: 235 PASS, exit1 known full100 deficit.
- Initial strict project+NEWspec types: exit2 for five unsupported `exact:true`
  query options; failure source/log hashes retained. Initial lint0 launched in
  the same tool group before the type-result interpretation: sequence deviation
  disclosed, then STOP. Separate Coordinator recovery removed ONLY the five
  invalid properties; literal string names/assertions remained unchanged.
- Distinct options-corrected types: exit0.
- Initial focus: 31 PASS/3 FAIL, exit1. Actual accessible names concatenate
  label/count (`Scansione AdE31/77`); three exact selectors assumed a space.
  STOP and preserved failed source/log/XML/hash. Separate Coordinator recovery
  removed ONLY those three spaces, retaining role/count/aria assertions.
- Distinct `focus-name-corrected`: 34 PASS, exit0, zero act warning.
- Native complete-page six-spec union: 269 PASS, zero failure/skip, exactly the
  two old manual act warnings, exit1 solely four unchanged coverage100 deficits.
- Final-byte strict project+NEWspec TypeScript: exit0; scoped ESLint: exit0.
- Whole native complexity report: exit0; exact all-file/all-callable and raw
  JUnit/coverage/threshold/ratchet object audit: exit0.
- Final custody: exit0; all1673runtime, five protected old specs, eight shared
  files, main diff/status and baseline hashes exactly match admission.

These two author test errors are not application failures, hidden retries or
observation-timeout restarts. All native handles were polled to terminal.
Original failure evidence remains distinct from corrected final evidence.

## Coverage

Actual V8 coverage over the whole unmodified page, thresholds statements,
branches, functions, lines ALL unchanged at 100%.

| Coverage | Original five specs | Union six specs | Covered delta |
| --- | ---: | ---: | ---: |
| Statements | 598/643 = 93% | 624/643 = 97.04% | +26 |
| Branches | 521/645 = 80.77% | 580/645 = 89.92% | +59 |
| Functions | 174/194 = 89.69% | 188/194 = 96.90% | +14 |
| Lines | 554/595 = 93.10% | 579/595 = 97.31% | +25 |

Coverage gate remains **FAIL**. Missing: 19 statements, 65 branches,
6 functions, 16 lines. No full-page100 claim or runtime admission.

Statement locations: 124,127,486,499–500,618–620,687–689,805,850,995,1000,
2037,2045,2368 (two statements). Missing functions: callbacks at 995,1000,
2037,2045,2368 (two). Exact branch ids, arm indices and source locations are
preserved in private audit JSON, not inferred from percentages.

The name fallbacks at 798/1435 cannot be reached through this loader when null
names are filtered out; they are not covered by a fabricated modal handler.
Zero-selection guards at 618–620/687–689 also remain separate from genuine
public coverage. Other missing branches belong to wizard/manual responsibilities
outside this bounded AdE slice. Any unreachable-runtime decision is separate.

## Ratchet

Authoritative `make complexity-ratchet BASE_REF=main`: native exit0,
`findings: []`, actual baseline_commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`. No BASE_REF change, threshold,
scope, baseline or ignore adjustment. Historical integral baseline30 status
is not recertified or absorbed by this author; local gate and global baseline
remain distinct. Final1673runtime/old5/shared8/main/baseline custody PASS.

Raw evidence is frozen separately under
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r30-catasto-ade/evidence/`:
`baseline.*`, `baseline.command-exact`, original type/focus failure inputs and
logs, corrected focus/type final logs, `union.*`, `coverage/coverage-final.json`,
`complexity-after.json`, `ratchet.*`, `audit.json`, `custody-final.json` and
`FREEZE.json`. The freeze identifies source/spec/report bytes and every raw
member; exact full command arguments and per-gate exit codes remain available.

## Reproduction

From the dedicated worktree frontend, with TMPDIR on isolated SSD:

```bash
VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx npm run test:coverage -- \
  tests/unit/campaign-catasto-anomalie-page.test.tsx \
  tests/unit/catasto-anomalie.test.ts \
  tests/unit/campaign-catasto-cf-wizard-r17.test.tsx \
  tests/unit/campaign-catasto-comune-wizard-r18.test.tsx \
  tests/unit/campaign-catasto-particella-wizard-r29.test.tsx \
  tests/unit/campaign-catasto-ade-scan-r30.test.tsx --maxWorkers=2 \
  --coverage.reportsDirectory="$SSD_EVIDENCE/coverage" \
  --coverage.reporter=text --coverage.reporter=json --coverage.reporter=cobertura
```

Expected native exit1 for unchanged full-page100 deficits, not a PASS. Remove
ONLY the new AdE spec argument to reproduce the original235 baseline. Focus
uses `npm run test:unit -- tests/unit/campaign-catasto-ade-scan-r30.test.tsx
--maxWorkers=2`. Strict types use the private config extending the actual
project config and including NEWspec, `--noEmit --incremental false`.
Scoped lint uses installed eslint on the NEWspec. From worktree root:

```bash
make complexity-report REPORT_JSON="$SSD_EVIDENCE/complexity-after.json" \
  REPORT_MD="$SSD_EVIDENCE/complexity-after.md"
make complexity-ratchet BASE_REF=main
```

Do not overwrite frozen outputs during review/replay; use a fresh evidence
directory. Run heavy gates serially and check root/SSD space before each.

## Classification

**NO_CHANGE — ORIGINAL_CHARACTERIZED**.

Real public contracts and coverage improve, but runtime complexity remains
unchanged. This is not IMPROVED or a reduction of any finding. Full campaign
remains ACTIVE / INCOMPLETE.

## Files changed

Only the new AdE spec and this report.

## Commit

None by author. Independent review and Coordinator publication are required.

## Residual risks

- Full-page100 still fails; runtime refactor remains BLOCKED_COVERAGE.
- True modal iframe, external AdE/SISTER/worker behavior and full authorization
  enforcement are not certified by the boundary stand-in.
- No final whole-project frontend/backend/worker/build/E2E suite is certified.
- Public-inaccessible guards/fallbacks require a separate explicit decision.
- Two historical manual-test act warnings persist, unsuppressed.
- Root remains storage-constrained; new heavy output lives only on SSD.

## Recommended next slice

Independent review of this original AdE characterization, then a separately
owned public manual residual characterization if authorized. Do not alter
runtime or synthesize inaccessible handler execution to reach coverage100.
