# R26 — Extreme-hotspot characterization and rejected runtime candidate

## Scope and decision

The full GAIA campaign remains ACTIVE / INCOMPLETE. R26 strengthens public
characterization of two extreme UI hotspots; it does not reduce accepted runtime
complexity. A real Presenze runtime candidate was implemented, then frozen and
excluded under its explicit stop condition. No baseline, threshold, exclusion,
ignore, package, shared-runtime or application behavior change was integrated.

## Snapshot, ownership and worktrees

Starting integration HEAD `de76117a6ad9405fd013c3c7114d18625c2b8620`, branch
`refactor/complexity-campaign-20261008`; main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Ownership registry precedes each
activation and phase admission. Four exclusive author/reviewer paths:

| Agent | Worktree suffix | Branch | Accepted responsibility |
| --- | --- | --- | --- |
| Presenze author | GAIA-campaign-20261009-r9-presenze-mutations | refactor/complexity-r26-presenze-summary | NEW24-case original monthly-summary spec/report; runtime candidate excluded |
| Presenze reviewer | GAIA-campaign-20261011-r26-presenze-review | review/complexity-r26-presenze-summary | Independent original496-case characterization, strict types and full-file coverage |
| Utenze author | GAIA-campaign-20261010-r21-capacitas-job-actions | characterize/complexity-r26-utenze-manual-upload | NEW49-case original manual-upload characterization/report |
| Utenze reviewer | GAIA-campaign-20261011-r26-utenze-review | review/complexity-r26-utenze-upload | Independent49/170-case public characterization and unchanged coverage-gap provenance |

All worktrees reside under `/home/cbo/CursorProjects/`. Coordinator alone stages
exact paths, commits and integrates accepted tests/reports. Native heavy commands
are serial; source-writing phases run without a native token. Main concurrent
binary diff SHA `9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`
and short-status SHA `0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`
remain unchanged. Baseline SHA `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

## Accepted behavioral evidence

### Presenze

NEW spec SHA `ea775e5ca3a1356a3b59be9a70ca3daf13abb9b4b886e46128bd9746f95c666e`.
Original runtime SHA `d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940`.
Twenty-four public mounted cases cover all eight Extra/Saturday/absence presence
combinations, exact two-layout DOM/classes/borders, known/unknown cause tones,
descending aggregate order and stable ties, valid Saturday chronology, zero and
negative extra eligibility, supplement-like cause keys, close/reopen and async
KM response refresh with unchanged API payload/input identity. Existing six
specs remain immutable. No aggregation/handler/React state or coverage mocks.

Root original472/6spec and extended496/7spec PASS; distinct reviewer independently
focused24 and union496 PASS/no skips/todo. Full-file original coverage remains
100% across1035statements1139branch outcomes306functions847lines, raw audited.
Corrected complete-project+spec strict types0,662roots661runtime0diagnostics;
scoped lint0 with only three unchanged page warnings. Explicit independent
ACCEPT_ORIGINAL_CHARACTERIZATION, report SHA6d569ca7. It does not accept runtime.

### Utenze

NEW spec SHA `24878b60ce520369b94fc456c6ef28626a8bcc8511dc62085511cd825bd1e720`.
Original runtime SHA `b0f822daf809b0744b912f0f159a2e833c556dda289466b6ed45329a79e3d6b1`.
Forty-nine cases mount the actual default page and real domain components via
supported embedded route; only external API/auth/navigation boundaries mocked.
Selection does NOT deduplicate; native input/drop order and real File identity,
per-item metadata, sequential captured uploads, partial retry duplication,
reload/status ordering, absorbed status failures, Escape/late completion,
route/token capture and callback-identity listener cleanup are preserved.

Root and distinct reviewer fresh49focused/170union4spec PASS/no skips/todo,
full-project+new-spec types0 (662roots661runtime0diagnostics), scoped lint0,
raw coverage/input custody0. Reviewer actual-main55a ratchet0/findings[].
Explicit ACCEPT_CHARACTERIZATION_ONLY, report SHA637906a7.

| Dimension | Before covered / total | After covered / total | Delta |
| --- | ---: | ---: | ---: |
| Statements |370/576 |437/576 |+67 |
| Branch outcomes |408/610 |460/610 |+52 |
| Functions |80/176 |109/176 |+29 |
| Lines |364/536 |426/536 |+62 |

After percentages75.86/75.40/61.93/79.47. Native full-file coverage command exits1
SOLELY because the unchanged four100% thresholds are unmet. This is NOT coverage
PASS or a waiver. Runtime remains BLOCKED_COVERAGE:139statements150branch arms
67functions110lines still uncovered. Original runtime behavior remains unchanged.

## Actual Presenze candidate — excluded

Candidate SHA `3e68dbf4ffd19bcb1e971b3d3685cd948dee90b04fea86b55fd576a6a0685d9d`,
source patch SHA28a0b3b4, author report SHAeaa1fd9b. Local typed monthly-summary
projection was actually implemented, using keyed Fragment/direct supplement DOM,
separate cause keys and same-array Saturday sort. Source branch-site estimate
22→7 is NOT native cognitive credit. Scanner-equivalent source LOC2812→2813
exceeds the explicit non-growth condition; absence tone/formatter evaluation
order also changed without equivalence certification. Author STOPPED, no native
candidate gate/test/metric/commit or integration; no minification, unrelated line
removal, baseline repair or name trick used to force admission.

Candidate remains the ONLY dirty runtime file in its dedicated author tree,
including after exact test/report publication. Integrated Presenze page stays
originald362. Classification NO_SAFE_CHANGE / NOT_ADMITTED for candidate;
CHARACTERIZED_ONLY / NO_CHANGE complexity for accepted tests. R25 excluded
candidate and historical globalFAIL30 are separate unresolved provenance work.

## Publication and ratchet

| Slice | Author commit | Integration commit | Post-integration actual-main gate |
| --- | --- | --- | --- |
| Utenze NEW test+CHAR |0e1661d5 |d019710f |PASS0/findings[] |
| Utenze review-only |fb0cf15c |4aeb1398 |PASS0/findings[] |
| Presenze NEW test+SLICE, runtime NOT staged |19197441 |16a7816b |PASS0/findings[] |
| Presenze original review-only |388b052b |276f356d |PASS0/findings[] |

The exact original test/spec bytes, not runtime candidates, are integrated one
commit at a time. Native `make complexity-ratchet BASE_REF=main` uses immutable
actual55a; no base substitution or baseline update. Root all1673runtime custody
remains exact against accepted R24 both before and after new test publication.

## Tooling failures retained, not hidden

| Command/problem | Failure | Cause | Impact / handling |
| --- | --- | --- | --- |
| Root SHA check from root rather than frontend |1 | Relative paths missing | Explicit correct-CWD manifest verified, no test rerun |
| Root manifest brace path |Missing presenze-giornaliere.test.tsx | Incorrect file expansion | Complete explicit-path manifest retained separately |
| Private partial-root new-spec strict types |1/20diagnostics |18GeoJSON namespace misses from omitted project roots;2unsupported new role exact options | STOP before lint, original failure retained; complete-project verifier/new test-only correction, all assertions unchanged |
| Reviewer focused CLI with --minWorkers |1 before collection |Unsupported option in Vitest4.1.6 |STOP confirmed; explicit Coordinator corrected invocation, new artifacts; no test failed |
| Reviewer ratchet JSON reader |Auxiliary audit1 |Make substitution brace then absent merge_base field |Failure retained; native Make0/direct baseline_commit55a/findings[] separately verified |
| Static report append anchors |Patch precondition failures |Wrong existing-text anchor |No source overwritten; corrected explicit append, no native retry |

No failed native application assertion was silently rerun or weakened.

## Root integration verification and Graphify

Post-all-integration mounted union:666PASS/11spec/no skips/todo; raw auditor0
and input SHA0. Presenze full1001035/1139/306/847; Utenze437/576statements
460/610branch outcomes109/176functions426/536lines. Native coverage exit1
SOLELY unchanged four100thresholds; test PASS does NOT imply coverage PASS.
Fresh native whole report0 confirms1673files20322callables1924errors2740warnings
4664findings, matching accepted R24. Custody verifies all1673runtime inputs
byte-identical to R24, unchanged main9f85/0d54 and baseline38e6; baseline diff
against immutable55a empty. Global baseline Make2/CLI1 retains exactly30
historical finding objects, deep-equal to accepted R24; raw equality audit0,
classification UNCHANGED_HISTORICAL_FAIL30. It remains FAIL, not silently
relabelled PASS or absorbed into baseline.
Graphify runtime boundaries are unchanged (test/report-only integration), so no
code graph refresh is needed. General technical docs use dedicated
`make graphify-platform-docs` and require semantic chunk completion/no failures,
not merely exit0. Actual platform-docs Make0 and semantic audit PASS: chunk1/1
done,174cached/3re-extracted,784nodes1116edges114communities, no warning/partial
results/semantic failure. Local base-URL patch target confirms already patched;
default gpt-reserve, max-concurrency1, api-timeout180 unchanged. Extraction
16132input/3473outputtokens, estimated USD0.0120. Graph output is ignored/
uncommitted and not complexity proof. Final governance publication ratchet
and custody are recorded in integrated evidence as ratchet-post-governance.*
and custody-after-governance.json; no broad campaign certification implied.

## Metrics, residual risk and continuation

Fresh original native report1673files20322callables1924errors2740warnings4664
findings. No accepted runtime delta; extreme tail5>300/17>200/55>100 unchanged.
Both huge components remain hotspots; no strategic campaign target satisfied.
All final full backend/frontend/worker suites, frontend build and stack E2E
remain uncertified. R26 narrow public tests cannot support broad completion.

Fresh root storage2.63GiB at03:17, tmpfs `/dev/shm` about273MiB. Cache inventory
only; no new deletion, browser/dependency/worktree/evidence loss. Additional
`/tmp/jest_rs`1.58GiB is external Jest work with incompletely established
ownership/active external suite and is not admitted for automatic cleanup.
Total listed cache4.49GiB including external Jest stores, nonexternal candidates
about1.86GiB; live databases/binaries/dotslash remain protected.
Next action after this narrow governance publication: retain candidate rejection,
then choose substantial protected UI responsibility/remaining genuine coverage
from current ranking without broadening this frozen slice or waiving100%.

Evidence: `~/.cache/gaia-campaign/20261011-r26-{presenze-original,presenze-characterization,
presenze-review,utenze-original,utenze-characterization,utenze-review,governance,integrated}/`
and compact `R26_LATEST.md`. The full original goal stays ACTIVE / INCOMPLETE.
