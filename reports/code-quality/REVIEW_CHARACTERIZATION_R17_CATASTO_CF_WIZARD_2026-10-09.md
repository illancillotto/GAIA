# Independent review — R17 original Catasto CF wizard

Decision: **ACCEPTED for original CF characterization only**.
Classification: **NO_CHANGE — ORIGINAL_CHARACTERIZED**, never IMPROVED.
Runtime: **BLOCKED_COVERAGE**. Global campaign: **ACTIVE / INCOMPLETE**.
Status: **TERMINAL / FROZEN — HEAVY RELEASED**.

## Ownership, policy and exact inputs

Reviewer `/root/r17_cf_review` worked only in the existing
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r16-capacitas-credential-defaults-review`,
branch `review/complexity-r17-catasto-cf`, unchanged HEAD
`08e85360c581c1005426524d27055af8d4236a51`.
The ownership registry allocated this review before activation. Author and
Coordinator gates were terminal and heavy explicitly transferred before replay.
Only this new repository report is reviewer-writable. Source, frozen incoming
spec/CHAR, previous tests/reports, config, tooling and baseline were protected.

Reviewed root AGENTS, checkpoint and repository complexity skills, README,
metrics/baseline, validation, ratchet, workflow, constraints and style policy.
The historical PROGRESS ledger was explored through relevant current campaign
and Catasto entries under checkpoint output bounds. No nested AGENTS was found
under the owned paths. Existing dedicated frontend Graphify query evidence was
read for orientation: page, CatastoAnomaliePageContent and getPageCount. It is
not metric or behavior proof. No runtime structure/routing/service/workflow was
changed; no graph extraction or refresh was performed or claimed.

| Frozen input | SHA256 |
| --- | --- |
| Original `frontend/src/app/catasto/anomalie/page.tsx` | `855e3ef09296d8024f894118ef6e9c0d6bf13dc63b4f653c6ce6202407a732f7` |
| Incoming `frontend/tests/unit/campaign-catasto-cf-wizard-r17.test.tsx` | `e4b97fcc3460641482b01f8d6b55b804b1c7f1d374f11b6cb0f60417e98840a2` |
| Incoming `CHARACTERIZATION_R17_CATASTO_CF_WIZARD_2026-10-09.md` | `b882beec4f3bd094f84f4fa2c973e69e8bdef623d1b61aa8d1ca48b13dca3545` |
| Reviewer protected-before manifest | `81de1797dff08253389376f2516f630f24b64294d8feab65259d1e953dc2930d` |
| Tracked root `tsconfig.tsbuildinfo` | `35e5b2b33872ecbdb4bc7e4204a58fab20b920a8d98ed5bdca6985dbbf48861b` |

The reviewer manifest contains **3546 protected tracked paths**. Both before
and after checks returned exit0, with every listed byte unchanged. This is a
reviewer snapshot, distinct from the author's earlier 3541-path snapshot.
Installed frontend dependencies were used through the existing link; no install.
The merge-base against immutable main is exactly
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

## Independent source and assertion review

Read the complete 612-line new spec and the original public URL/tab setup,
loadCfWizard, handleApplyCf, context/reset handlers and CF rendering. The spec
imports and renders the real default page, including original state, effects,
callbacks and refresh closures. React hooks, private handlers, pagination,
CF card/input/button rendering and page internals are not replaced or exposed.
Navigation, stored token, API clients, the outer Catasto authorization shell
and unrelated workspace modals are mocked at their boundaries. The shell mock
checks requiredModule/requiredRoles forwarding; it does not certify actual
authorization enforcement. Modal null mocks do not implement CF transitions.

Expected requests, messages, counters and draft values are literal assertions,
independently checked against the frozen source. They do not call production
helpers to manufacture expected results. Deferred API promises expose public
pending states and completion order. Tests use actual labels, buttons and
navigation, with DOM ancestry only to scope the original CF article/cards.
No state injection, copied runtime, hook instrumentation, ignore/skip, threshold
override or denominator substitution was found.

| Responsibility reviewed | Independent assessment |
| --- | --- |
| URL/tab/context/load guards | Explicit tab precedence and workspace fallback; CF open status, year/district, local page1/pageSize25; overview page/status/type/severity independence; other wizard APIs idle. |
| Loading/empty/page recovery | Visible initial busy/empty states; later empty positive-total page returns to1 before replacing old rows; first-page positive-total empty result does not loop. |
| Draft initialization and persistence | Nullish suggestion/current/empty precedence; empty suggestion overrides current CF; truthy drafts survive pending reload, off-page absence and return; empty drafts refill. |
| Edit and apply contract | Typing uppercases without trimming; suggestion restores raw text; mutation captures trim/uppercase value and exact anomaly-specific note for VAL-02 and VAL-03. Only nonempty validation is assumed. |
| Failure/token boundaries | Error and non-Error fallbacks; rows/drafts survive failed reload/apply; retry clears feedback; missing token prevents authenticated requests; token rechecked before feedback changes and refresh. |
| Mutation and refresh lifecycle | Success counts become visible before parallel refresh settles; row stays busy through CF and both overview promises; failed mutation performs no refresh; successful mutation and reload error coexist. |
| Captured context and original races | Older response may replace newer rows; one load clears busy while another is pending; suspended mutation refreshes old year/tab closures; independent rows overwrite the scalar applying ID, and either completion releases it. |

These concurrency observations faithfully characterize current behavior and
are not fixes or guarantees that such behavior is desirable. CF card/input
actions remain real. Manual navigation is exercised only for CF activation and
captured refresh; Comune, Particella and AdE/batch behavior was not expanded.
No blocking assertion/mock-boundary defect was identified for this allocation.

## Fresh reviewer replay and native terminal ledger

All gates ran serially, once, in the reviewer tree. Raw logs, exits, JUnit,
coverage, scoped AST and private verification config are retained at
`/home/cbo/.cache/gaia-campaign/20261009-r17-cf-independent-review/`.
The project typecheck excludes tests; the separate private tsconfig extends
the unchanged reviewer config and includes the new spec, original setup and
next-env declarations plus their real runtime imports. Both disable incremental
and emit, preserving the tracked root TS build artifact.

| Check | Native launch / terminal handle | Result | Private evidence |
| --- | --- | --- | --- |
| Focused new spec | session51171, launch5f5b09 / terminal5da946 | PASS0; 34 passed, 0 failed, 0 skipped | `focused-attempt1.log`, `focused.junit.xml` |
| New + P4 manual + utility union | session15649, launchb5daef / terminala954e7 | PASS0; 150 passed across 3 specs, 0 failed, 0 skipped | `union-attempt1.log`, `union.junit.xml` |
| Actual complete original page coverage | session35559, launch1e4ea6 / terminalc43de5 | EXPECTED FAIL1; 150 tests pass; all four 100% thresholds fail | `coverage-attempt1.log`, `coverage.junit.xml`, `coverage/coverage-final.json` |
| Project typecheck, incremental false | session24621, launch2a74ab / terminal2c3c79 | PASS0 | `type-project-attempt1.log` |
| New-spec typecheck, private config | session97775, launche9d1f0 / terminal8bb2ff | PASS0 | `type-new-spec-attempt1.log`, `tsconfig.new-spec.json` |
| Scoped new-spec lint | session83611, launch7442ce / terminal48bbfc | PASS0; no ESLint findings | `lint-attempt1.log` |
| Fresh scoped original page AST | synchronous chunk8dc51d | PASS0; 197 callables, 11 errors/16 warnings unchanged | `page-report-attempt1.log`, `page-after.json/md` |
| Actual Make immutable-main ratchet | session36598, launchc98e4a / terminal7f7749 | PASS0; baseline_commit55a; findings[] | `ratchet-attempt1.log`, `ratchet-result.json` |
| Independent metrics/raw coverage/JUnit analysis | synchronous chunk61035c | PASS0; exact original objects/counts/keys verified | `metric-comparison.json`, `coverage-analysis.json`, `junit-analysis.json` |
| 3546 protected before / after verification | synchronous chunks4e016b / e86dcd | PASS0 / PASS0 | `protected-precheck.log`, `protected-postcheck.log`, native exit files |

Executed frontend commands were the original npm unit/coverage scripts with
the named three-spec union and `--maxWorkers=2`; coverage used
`VITEST_COVERAGE_INCLUDE=src/app/catasto/anomalie/page.tsx` and only redirected
reports into private evidence. JUnit output was additionally requested. Project
type used `npm run typecheck -- --incremental false`; spec type used installed
tsc with `-p <private-config> --noEmit --incremental false`; lint used
`npm run lint -- --file tests/unit/campaign-catasto-cf-wizard-r17.test.tsx`.
Scoped AST used the original `tools/code_quality/complexity.py report` on only
the actual page. Actual ratchet was
`PYTHONDONTWRITEBYTECODE=1 NODE_PATH=/home/cbo/CursorProjects/GAIA/frontend/node_modules BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 make complexity-ratchet`.
No baseline update/check substitution or additional full-report scan occurred.

Union and coverage retain the existing P4 DataTable act warning; the focused
R17 replay has no such warning. Lint retains installed Next15's next-lint
deprecation, with no ESLint warning/error. No behavioral/type/lint/AST/ratchet
gate failed unexpectedly and none was rerun. Build, E2E and full repository
suites were not run here and are not claimed passing.

An auxiliary private JSON extraction helper failed at chunk64149b: first-brace
selection captured the `${BASE_REF:-origin/main}` text in Make's printed command
instead of JSON. Its Node SyntaxError was observed despite the composite shell
finishing exit0 after unrelated reads. The reviewer stopped that helper and
reported it to Coordinator. Coordinator explicitly authorized only correcting
private parsing of the already-terminal log. The corrected real-newline JSON
parser then passed at 61035c and verified baseline55a/findings[]. No gate restart,
repository tooling edit, input edit or threshold change occurred. A separate
read probe guessed a nonexistent frontend TS artifact; the protected manifest
identified the actual tracked root `tsconfig.tsbuildinfo`, unchanged. These are
explained evidence-handling observations, not hidden gate successes/failures.

## Actual full-page coverage and runtime stop

Raw coverage has exactly one source key, the real reviewer page:
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r16-capacitas-credential-defaults-review/frontend/src/app/catasto/anomalie/page.tsx`.
The complete original source was instrumented under unchanged 100% thresholds.
No source clone, line slice, missing-counter suppression or ignored branch.
Independent JUnit checks count 34 focused/150 union/150 coverage test cases and no
failure/error/skipped element. Independent counter calculations exactly match
the raw source and the author's result:

| Dimension | Covered / total | Percent | Missing | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Statements |449/643|69.82%|194|0|
| Branch arms |342/645|53.02%|303|0|
| Functions |125/194|64.43%|69|0|
| Lines |416/595|69.91%|179|0|

`coverage-analysis.json` independently enumerates every missing statement ID
and source location, branch ID/arm/type/location, function ID/name/location and
line. Remaining counters include other wizard routes/loaders, Comune/Particella
single/batch commands, AdE scan/workflows, lookup/manual fallbacks and unrelated
render callbacks. Full-page 100% is not achieved. The expected FAIL1 remains a
failure and **blocks runtime refactoring**, regardless of characterization
acceptance. No waiver or coverage differential was introduced. This unit review
does not certify browser/live API/server normalization or authorization behavior.

## Unchanged complexity and final freeze

Fresh reviewer page file/callable/violation objects compare exactly with both
Coordinator's original report at 429a8a1e and the author's fresh report at 3b120c3e.
The comparison ignores report timestamps/checkout provenance, not any metric
object. No parse or exception error exists. Principal cognitive 390,
cyclomatic 342, effective LOC 2109, nesting 2 and fingerprint 9933ead4497cdffc are
unchanged; file cognitive 794/cyclomatic 868, effective LOC 2267, 197 callables,
24 state/10 effect/25 imports and 11 error/16 warning findings also match exactly.
All runtime deltas are zero. There is no complexity improvement claim.

HEAD/branch and immutable55a merge-base remain unchanged; tracked and staged
diffs are empty. Only frozen incoming spec/CHAR and this reviewer report are
new untracked repository files. All 3546 protected paths remain byte-exact,
including old tests, source, config, tooling, baseline and root TS buildinfo.
Disk was 148 MiB on arrival and 152 MiB after gates; no ENOSPC occurred. No checkout,
cleanup, install, commit, push, merge, candidate diagnosis or R16 continuation.

Private evidence and this report are sealed by a separate SHA256 manifest,
avoiding a self-hash cycle. Every owned native test/type/lint/AST/ratchet process
is terminal; process inspection showed no running vitest/owned tsc/scanner.
No external browser, backend, container or credential resource was created.
**Heavy and external resources RELEASED.** Coordinator may review/integrate this
test-only result; runtime remains BLOCKED_COVERAGE and no next wizard is opened.
