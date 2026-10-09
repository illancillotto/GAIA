# R15 Capacitas — Create-job Lifecycle Readiness

## Decision

**NO_CHANGE — three exterior designs REJECTED.** No selected runtime candidate,
no implementation permission requested, no runtime/test/configuration edits.
Do not spend a heavy validation window on a design already contradicted by
bounded metrics or timing evidence. This is a completed bounded readiness
allocation, not an implemented/refactored slice or global campaign closure.

The four handlers have genuine repeated phases, but the measured lifecycle
designs increase existing LOC debt. The smallest measured pure error formatter
also grows effective file LOC. The async-operation wrapper additionally changes
busy-release timing. None satisfies the ownership registry's non-growth rule.

## Ownership

- Allocated AFTER integration governance `b420b2fc`, BEFORE agent creation.
- Registry: `docs/code-quality/MULTI_AGENT_OWNERSHIP_R15_CAPACITAS_CREATE_JOBS_2026-10-09.md`
  in the integration worktree; authoritative source of this allocation.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261009-r15-capacitas-create-jobs`.
- Branch: `refactor/complexity-r15-capacitas-create-jobs`.
- Sole writable tracked-tree artifact: this new report, untracked/uncommitted.
- Exactly four read-only targets in
  `frontend/src/components/elaborazioni/capacitas-workspace.tsx`:
  `handleCreateParticelleSyncJob`, `handleCreateTerreniBatchJob`,
  `handleImportAnagraficaHistory`, `handleCreateIncassJob`.
- All21 existing specs, fraction policy, scanner, baseline, configuration,
  other reports and shared libraries/hooks/UI remain frozen.
- Harvest/refetch/parsing/rerun/delete/stop/speed/render/polling excluded.

## Preflight and provenance

Fresh `git status --short`, `git diff --stat`, `git diff --check`, HEAD,
merge-base, branch, owned-path history and worktree inventory were inspected.
Author tree was clean; HEAD remains
`68996649638772e1a1f97cc24a70c4bee6c68cfc`; merge-base with main is
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Owned source history includes R13 `9e9e5421`, R12 `673026e7`, R11 `01a9ada4`;
these are attributed prior changes, not new R15 reductions.
No other agent is allocated this runtime file. R14 is disjoint backend work;
all heavy gates remained prohibited during this allocation.

Frozen workspace SHA256:
`8111c1a4658055f29a4c0b56fb1113f8b06677f9e1e622e33d596ae3d9514f48`.
Frozen fraction-policy SHA256:
`0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb`.
Scanner SHA256, equal in author/integration:
`faf340a36a2a3730d313be34b17a89e1c96c6310084d3b63739e0a3fbf446b8d`.
Concurrent main remains untouched: binary diff SHA256
`9f85e574012050218a76c9e65f38248cb2e21f520adb338f90e07a969114664b`,
status SHA256
`0d54d4eb816db5afeaaf183918f3719aefd6c725eebf26af561d96261c735e87`.

Checkpoint skill, repository complexity skill/references, AGENTS and required
quality/style documents were loaded. No branch creation/reset/rebase/stash,
commit/pick, baseline generation/repair, threshold/exclusion/ignore change.

## Baseline metrics

Bounded unchanged scanner invocation on workspace and fraction policy ONLY.
This is not a full complexity report or ratchet.

| Scope | Cognitive sum | Cyclomatic sum | Decisions sum | Callable | Effective LOC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Workspace | 858 | 998 | 749 | 249 | 3091 |
| Frozen fraction policy | 3 | 9 | 3 | 6 | 35 |
| Combined authoritative local accounting | 861 | 1007 | 752 | 255 | 3126 |

| Target | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| ElaborazioniCapacitasWorkspace | 347 | 324 | 2455 | 2 | 1 |
| handleCreateParticelleSyncJob | 7 | 7 | 26 | 1 | 0 |
| handleCreateTerreniBatchJob | 11 | 10 | 28 | 1 | 0 |
| handleImportAnagraficaHistory | 6 | 6 | 23 | 1 | 0 |
| handleCreateIncassJob | 4 | 4 | 18 | 1 | 0 |

Workspace distinct scanner-style decision nodes429 plus policy3 give432.
R13's semantic source census excludes the workspace's SwitchStatement and
default SwitchCase, giving427+3=430; that R13-compatible census is used in the
candidate table. Both perimeters and identical deltas are retained explicitly.
This differs from sum(cyclomatic-1), which counts a nested decision in enclosing
callables too. No scanner or source-census definition was modified on disk.
Actual AST70 useState/2 useEffect; regex scanner31/2, because generic call syntax
omits39 state calls in that scanner regex. Both perimeters remain unchanged.
No scanner/baseline repair is part of this slice. The last integrated17error/
16warning local finding counts are attributed to R13, not freshly gated here.

## Behavioral invariants

| Family | Exact original lifecycle |
| --- | --- |
| Particelle | Read token; absent returns; busy true; inside try parse credential and trimmed limit without sanitation changes, construct exact seven fields, invoke imported API unbound; await job; clear expiry; captured-form speed/worker notice with returned ID; clear error; await nonsilent own reload; Error.message or exact fallback on exception; busy false finally. |
| Terreni | Read token BEFORE token-or-empty-items guard; busy true then batch error null OUTSIDE try; construct all execution flags and original items-array reference inside try; await API; clear monitor expiry; original count/speed/worker/throttle/auto-resume notice; await own reload; create exceptions affect BATCH error, reload exceptions normally affect MONITOR error; busy false finally. |
| History | Read token guard; importing true then error null OUTSIDE try; credential conversion occurs before file/manual item selection; preserve actual manual token parser and file array reference; payload auto_resume true; await API; clear expiry; notice counts the SAME locally selected items after response; await own reload; exact Error/fallback handling; importing false finally. |
| inCASS standard | Read token guard; busy true; keep actual buildCapacitasInCassSyncPayload and object spread inside try, not a copied substitute or direct reference; await API; clear expiry; returned-ID notice; clear error; await own reload; exact Error/fallback handling; busy false finally. |

No create handler calls isAuthError or invalidates auth directly. Each ORIGINAL
reload rereads the token via refreshCapacitasJobMonitor, has its own swallowed
load error/auth-expiry semantics, and can overwrite a success notice. Busy must
remain true until that reload settles; ordinary load failure does not turn a
successful creation into a failed API request. Terreni batch/monitor error
channels must not be conflated.

Render-captured forms persist through await; later renders do not rewrite an
in-flight payload or its captured confirmation. Batch arrays are references,
not deep copies. No reentrancy guard, cancellation, last-request-wins policy,
token caching across reload or race fix is authorized. Two dispatches before a
React rerender can overlap; the first completion can release a shared busy flag
while another remains pending, and final notices follow completion order.

## Existing tests and gap matrix

All21 frozen Capacitas campaign specs were parsed and their206 static test
bodies/assertion bodies inventoried. This is NOT206 executed tests: parameterized
expansion gave492 cases in prior R13 certification, which is attributed only.
Inventory contains exact source bodies, line locations and SHA256 for each spec.

| Behavior | Existing test/assertion evidence | Missing original coverage | Added | Result |
| --- | --- | --- | --- | --- |
| Exact Particelle defaults/options and ordered refresh | campaign-capacitas-particelle-commands.test.tsx:130/146/164; R13 execution-controls:270 | Direct request and reload separate deferred checkpoints for all error/auth variants | None | Static evidence only |
| Exact Terreni payload/complete array | campaign-capacitas-batch.test.tsx:97/119/145/198; terreni-residual:140 | Same-array identity/count behavior while pending and later input replacement | None | Static evidence only |
| History manual/file/order/credentials | campaign-capacitas-storico-input.test.tsx:138/156/179/275 | Pending file-to-manual switch with exact captured-array count and next payload | None | Static evidence only |
| inCASS defaults/numeric switches/real helper | campaign-capacitas-incass.test.tsx:118/131/150 | Defensive synchronous payload-builder throw; spread clone contract | None | Static evidence only |
| Busy through creation then refresh | batch:227; particelle-commands:130; storico-input:326; incass:221 | Microtask-sensitive release; two same-act submissions before rerender; first-completion early release | None | Static evidence plus exterior timing counterexample |
| Missing token | batch:261; particelle-commands parameterized commands; storico-input:385; incass:240 | Token A at dispatch then token B/null ONLY for post-create reload, in all four families | None | Static evidence only |
| Error/non-Error rejection and retry | batch:244; particelle-commands parameterized commands; storico-input:352; incass:249 | Synchronous imported API throw; explicit create401/403 no direct auth-expiry for all families | None | Static evidence; pure ports supplementary |
| Error-clearing phase/notice retention | storico-input:352/374; particelle-commands:276; incass:269/283 | Exact prior-error behavior at pending create and reload checkpoints for all four, Terreni split channels | None | Static evidence only |
| Stale speed/worker capture | execution-controls-r13:270 for Terreni/Particelle | History/inCASS pending-form capture and next-submission assertions | None | Static evidence only |
| Loader auth/error overwrite | incass:269/283; storico-input:374; monitor-lifecycle-r11 and family monitor specs | Cross-phase create success→rotated/lost token/auth reload for all four | None | Static evidence only |
| Concurrency/last completion/cross-family state isolation | R12 command lifecycle has analogous rerun/delete tests ONLY | Real public-UI create same-act overlap and reversed completions; concurrent different-family creation | None | Gap; R12 is NOT proof for creates |
| Success-mapping exception | No explicit create returned-ID accessor failure assertion found | Defensive supplementary untyped boundary test, not fictional invalid production DB fixture | None | Gap |

No missing cases were added under this readiness-only allocation. Full-file100%
coverage alone does not prove the missing ordering/race contracts.

## Exterior designs and measurements

Artifacts live ONLY at
`~/.cache/gaia-campaign/20261009-r15-capacitas-create-jobs/readiness/`.
The actual owned source never changed. Each candidate is a complete exterior
workspace, parsed by the same frozen scanner; all nested callable profiles are
retained, not merely principal scores. Fraction policy remains exact.

| Projection | Principal cog/cyclomatic/LOC | Combined cog/decisions/LOC | Combined callable | R13-compatible source census | Decision |
| --- | --- | --- | ---: | ---: | --- |
| Original | 347/324/2455 | 861/752/3126 | 255 | 430 | Actual unchanged |
| Direct request/accepted callbacks | 339/320/2458 | 860/759/3144 | 272 | 427 | REJECTED: decisions+7, file LOC+18, principal LOC+3 |
| Async-operation wrapper | 335/316/2459 | 850/748/3144 | 260 | 424 | REJECTED: file LOC+18, principal LOC+4, extra microtask |
| Pure shared error formatter | 339/320/2455 | 846/745/3129 | 256 | 427 | REJECTED: file LOC+3; does not isolate requested full lifecycle |

Direct design shares one try/await(request)/await(accepted)/catch/finally without
an async accepted callback. History requires per-invocation captured items for
the success notice. Adding16 callback bodies re-counts payload/notice/error
decisions in callable aggregates; the slight principal reduction is NOT enough.
Combined cyclomatic sum1007→1031. It is not an improved slice.

Async design shares exception classification/final release but awaits a new
async operation containing the original two awaits. Combined cyclomatic sum
1007→1008. Busy false is delayed by an additional microtask; source simplification
does not authorize changing that lifecycle contract.

Error-only design genuinely removes three duplicated source ternaries and has
helper1cognitive/2cyclomatic/3LOC/2params, but effective file LOC is already in
error-level debt and grows. Combined cyclomatic sum1007→1001. No formatting,
packing, unrelated trimming, relocation, matcher or baseline adjustment was
used to hide the three-line growth. It is NOT accepted as a smaller replacement
for the assigned lifecycle responsibility.

Candidate SHA256:
- Direct: `d12ddf93a077a46918b9d61c6fb7b090a63cde2213463110683a25c15732a0d5`.
- Async: `2a07a32f9de54ce24c434c44c5236a8fab38f8271643f605709babf965a411d6`.
- Error-only: `7936141f6e427b2adfa9cbc6fde071f22f5ab651c1e2f72e7e8ac58ec07b9b05`.

## Timing counterexample and pure evidence

Extracted ORIGINAL four function bodies and the actual manual parser were
transpiled in isolation, not rewritten into an oracle. Strict unbound API
doubles, deferred create/reload ports, real payload references and recorded
setter calls were used for41 bounded scenarios across four families: happy
path, sync throw, Error/non-Error/auth-message rejection, reload rejection,
rotated/lost/missing token, empty Terreni and captured option replacement.

Direct and formatter designs each matched41 ORIGINAL observable port traces.
These are supplementary proofs, NOT React/public-UI tests, real monitor/API
tests, project type validation, coverage or ratchet. Promise-return adoption
was not claimed identical; current UI calls discard these handler promises.

Async wrapper differed in36 traces. Concrete Particelle happy path: create
resolves at tick2; expiry/notice/error-clear and reload dispatch tick2 are exact;
reload resolves tick5. ORIGINAL calls setParticelleCreatingJob(false) at tick5;
wrapper calls it at tick6. The same extra boundary also affects immediate
sync-throw/error recovery. `timing-results.json` contains full before/after
traces and the explicit strict-receiver assertion. No rendered test PASS is
inferred from this pure harness.

## Tests, coverage, ratchet and Graphify

| Verification | This allocation |
| --- | --- |
| Bounded original/candidate scanner and full nested profiles | Executed terminal0; projections rejected |
| Four-handler supplementary41-case port traces | Executed terminal0;36 async timing counterexamples retained |
| Static all21-spec inventory and70state/2effect AST accounting | Executed terminal0 |
| Project type/lint/rendered original tests/coverage/build | NOT RUN; no authorized heavy window |
| Full-context immutable55a candidate comparator/full report | NOT RUN; rejected projections need no hypothetical PASS |
| Actual make complexity-ratchet | NOT RUN by R15; no source edit; prior R13 PASS0 attributed only |
| Code/docs Graphify refresh | NOT RUN; no runtime boundary or domain document changed |

Dedicated author `make graphify-frontend-query` failed because its ignored
corpus graph was absent; outer shell pipeline exit0 was not query success.
Existing INTEGRATION corpus was subsequently queried read-only using the same
dedicated target, terminal0, BFSdepth2 from MONITOR_MESSAGES/MonitorCard/api.ts.
It orients auth/API/chrome relationships but broad output is truncated and
does NOT prove ordering/complexity. No raw-root Graphify or graph copy/refresh.

## Failures, integrity and residual risk

`FAILURES.md` preserves the missing author graph, initial exterior Babel
finalizer-access failure, first timing harness's sloppy-receiver diagnostic,
initial finalizer policy-count assumption and each rejected design. Only
exterior scripts/accounting and this report were corrected. First/second/
third logs are retained; no runtime/test failure was waived or relabeled PASS.

Protected tracked manifest covers3525 paths; original source, all21 specs,
policy/scanner/config/baseline and concurrent main hashes remain exact.
No resource-intensive test/build/scan or persistent server was launched. Pure
Node processes and bounded Graphify query are terminal. No worktree dependency
symlink, configuration or shared cache was altered by this author.

Runtime metric after is IDENTICAL to before: principal347/324/2455,
combined861cognitive752decisions3126effectiveLOC; delta0, delta%0.
No added coverage, source improvement, fresh authoritative gate or global
finding reduction is claimed. Global campaign remains ACTIVE/INCOMPLETE.

## Stop condition and recommendation

Readiness allocation terminal **NO_CHANGE**. Heavy window was never acquired;
release any planned R15 heavy allocation rather than run already-rejected
candidates. No commit; only this report awaits Coordinator publication/review.

Recommend independently reviewing the rejection evidence, then selecting a
different coherently scoped Capacitas hotspot from current ranking, with a new
registry and real decision-heavy responsibility. Do NOT silently broaden this
four-handler slice, weaken non-growth/coverage, or implement one of these
designs because its principal cognitive score looks better.
