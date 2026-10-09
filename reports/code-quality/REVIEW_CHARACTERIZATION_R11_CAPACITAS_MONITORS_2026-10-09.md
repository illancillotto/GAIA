# R11 Capacitas — independent original characterization review

## Preparation checkpoint

Historical preparation status: **PREPARED / AWAITING SOURCE FREEZE AND EXPLICIT
SLOT TRANSFER**. The subsequent authorized review/replay is recorded below.
Campaign remains ACTIVE / INCOMPLETE. This report is the only writable review
artifact; exact test/report commit import was separately authorized.

Review worktree: `GAIA-campaign-20261009-r11-capacitas-monitors-review`;
branch `review/complexity-r11-capacitas-monitors`; HEAD
`d2f222f9b48a2e8b728ad2801a240f2d9bdd0ba5`.
Registry and Coordinator CHARACTERIZATION_APPROVAL/INTEGRATION_AGENT_READINESS
read. Root AGENTS, context-checkpoint and project complexity skill, metrics,
validation, quality ratchet, workflow and constraints apply. PROGRESS current
tail inspected with bounded output; historical 8131-line journal not dumped.

Read both frozen readiness reports and selected inline candidate diff against
actual original runtime. Fresh SHA256 checks match:

- Original workspace: `a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59`.
- External design candidate: `2a2199ccd52b942fab54a1fff0878431b1ff6b7516bcaff2c03bd875b39e60f5`.
- Frozen review readiness: `c74e515e969421b5718d5efbe0673ce798625d7c89a54f247ac6575d58ee1441`.

At this preparation inspection, author's allocated lifecycle-r11 spec and
CHARACTERIZATION report were absent. Author remains live owner; no partial test
copy, polling loop or restart attempted. Earlier readiness 338/18/full-file100%
and external candidate PASS0 are contextual evidence, not fresh results here.

## Independent review plan after handoff

1. Receive explicit freeze, exact test/report/runtime hashes and terminal author
   evidence; verify original runtime and frozen readiness remain unchanged.
   Test import into review worktree still requires explicit authorization.
2. Review all 58 rendered cases (8 genuine auth, 2 Terreni API-order,
   48 family/outcome/response-order pairs). Confirm meaningful intermediate and
   final DOM assertions, public controls, real usePolling, deferred API boundary
   and original ApiError constructor/classifier. Reject private React access,
   mocked polling, fabricated JSON getters, weakened existing tests or skips.
3. Check each family uses its real initialSection: terreni, particelle, storico,
   incass. Terreni/Particelle/History tick at15000ms; inCASS at20000ms through100
   rows and45000ms above100. Ensure mounting other-family APIs is deterministic
   and request counts distinguish initial load, manual dispatch and real tick.
4. Independently derive outcomes from original source, not candidate results:
   refs read at response resolution; manual requests overlap polling singleflight;
   both response orders retain stale row replacement and current-ref consumption.
   Assert loading, row identity, retained/cleared errors, completion/resume notices
   and observable expiry through subsequent real polling after token restoration.
5. Terreni must select FIRST tracked terminal in API order on silent refresh;
   manual refresh does not open its completion modal. Other families notify on
   manual completion only. History must retain stored report across empty/invalid
   lists, respect first-valid result/current displayed result precedence and
   characterize overlap order without changing the repeated runtime result guard.
6. After exclusive slot transfer and authorized test import, replay new spec on
   unchanged original, then union with18existing specs at actual full-file100%.
   Verify raw coverage maps for workspace and unchanged fraction policy; run
   scoped lint and explicit test TypeScript per frozen author commands. Record
   failures, skips, exact commands, hashes and exits; no build/browser/backend/
   worker or actual runtime ratchet claim in this phase.

## Risks and pending evidence

- Parameterization can hide family-specific assertions: case count alone does
  not prove all outcomes, intermediate states or completion orders.
- Batched promise resolution can erase intermediate DOM states; each response
  needs a separate awaited rendered checkpoint before resolving the other.
- Expiry/error strings can remain after successful silent recovery. Assert
  polling eligibility through API calls rather than inferring private expiry
  solely from visible retained messages.
- A silent response must not release manual loading; manual finally can release
  it while polling remains pending. Timer advancement must not accidentally
  settle or add requests that conceal this distinction.
- Tokens are captured at dispatch, refs at resolution. Plain status401 objects
  are not authentic auth errors. inCASS always keeps limit300.
- Source/event oracles are supplementary; no rendered reachability or coverage
  credit. External candidate proof authorizes design only; actual implementation,
  source review, final certification and integration are distinct later gates.

## Work performed and resume boundary

Only read-only file inspection, git status, bounded source searches/diff and
SHA256 verification performed. No tests, metrics scanner, heavy slot, Graphify
batch, package/config/baseline changes, runtime edits or commits. Sole new file
is this preparation report; frozen readiness must remain byte-exact.
Resume on Coordinator follow-up with explicit source freeze and slot transfer;
do not autonomously import tests or begin replay.

## Authorized original replay and independent source review

Coordinator follow-up and `ORIGINAL_REPLAY_APPROVAL.md` explicitly froze original
source, transferred the exclusive focused slot and authorized the exact two-file
commit import. Cherry-pick `b5d82b2a7690bd69b04d56fed52fd1faa227d9ac` succeeded as
`0da2513c`; only lifecycle-r11 spec and frozen author CHARACTERIZATION report were
imported. Both untracked reviewer reports were preserved and never staged.

Imported hashes verified independently:

- Test: `85206faf9efa7d50e81da478b4af61beee6940fd64377fd15ffbbe57178880b7`.
- Author report: `1301492942b502555a87290afa6373fc7c966bc683f0f08793e652adb232bb5f`.

All58cases reviewed against actual original loaders, usePolling and core auth
classifier. No blocking finding in the bounded characterization matrix.

| Matrix | Independent assessment |
| --- | --- |
|8 genuine auth cases |Correct three-argument ApiError; real core isAuthError. Exact family expiry/resume messages, retained rows, manual recovery and real timer/visibility freeze/resume are asserted. |
|2 Terreni order cases |Unrelated terminal precedes two tracked IDs; reversed API order changes chosen first modal. Public close and no further timer dispatch are checked. |
|48 overlap cases |All4families ×6outcomes ×2orders. Public manual refresh precedes actual tick while manual remains pending; separate awaited act checkpoints preserve intermediate observation. token-A/token-B capture and inCASSlimit300 are asserted. |
|History report chronology |Initial valid report7, terminal invalid-first result then valid22/33, late active snapshots and later empty manual list preserve report22/7 according to original source. No fake getters or repeated-guard rewrite. |
|Family-specific completion |Terreni silent terminal opens actual completion modal; late manual active rows update its current-job view. Other families do not incorrectly announce silent completion. Unchanged original specs protect manual completion and remaining hook contracts. |

The loading-time absence of rows in silent-first cases reflects actual UI
rendering while manual remains pending, not a missing request. Final identity,
order and status checks distinguish response order. Next real API dispatch after
token restoration independently observes expiry eligibility; retained text alone
would not suffice. Status-only401 rejection correctly yields fallback, not auth.
No private React access, mocked polling, fabricated JSON getters, skips/only,
existing test edits or test-only runtime API found. ProtectedPage/unrelated modal
boundaries do not replace the real Terreni completion modal or monitor controls.

Bounded limitations: card lookup depends on existing rounded CSS classes (20px
and24px); cosmetic changes may require selector maintenance. Eight auth cases
exercise silent401/403; overlap exercises manual401/silent403, complemented by
existing normal/auth tests. New inCASS cases use20s; unchanged original spec
retains100/101row20s/45s coverage. This matrix is not exhaustive concurrency or
native-browser proof, and does not certify a future implementation.

## Attempt history retained

Independent inspection of author attempt logs confirms48PASS/10FAIL followed by
55PASS/3FAIL: inCASS initial presentation is running-first, Terreni has multiple
close buttons, and terminal Particelle cards use20px instead of24px rounding.
Final spec retains strong row/status/modal assertions with corrected public DOM
selectors and expected original presentation. Earlier explicit test TypeScript
TS2322 came from unknown result_json; final annotation is the actual API union.
No runtime/config/gate change concealed those failures. These were author harness
attempts; independent replay attempts here have no test failure.
Author package-export probe and missing fresh-worktree Graphify corpus remain
documented in its frozen report; neither is presented as a passed check here.

## Fresh replay evidence

External evidence directory:
`/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/integration-review/`.
Runtime unchanged throughout. Standalone58/58 PASS,5.99s, session93667 exit0.
Union396/19specs PASS, zero skips,50.72s, session13320 exit0. Fresh raw coverage
contains exactly both complete files and original statementMap/fnMap/branchMap;
all hit counters positive. Coverage summary lines also100%.

| Actual original file | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
|Workspace |857/857 |873/873 |251/251 |748/748 |
|R10 policy |9/9 |6/6 |6/6 |8/8 |
|Combined |866/866 |879/879 |257/257 |756/756 |

Fresh AST files/callables/violations/summary exactly match author original
objects, not candidate metrics. Actual principal455cognitive/404cyclomatic/
2625LOC; combined1022cognitive/1129cyclomatic/872decisions/4789callableLOC/
3140fileLOC/257callables,22errors19warnings. Workspace31state2effect unchanged.
Classification remains **NO_CHANGE — CHARACTERIZATION_ONLY**; no runtime debt
reduction or actual candidate ratchet is claimed.

Reproduction from review frontend (E is the external evidence directory):

```bash
npm run test:unit -- tests/unit/campaign-capacitas-monitor-lifecycle-r11.test.tsx --maxWorkers=1 --reporter=default --reporter=junit --outputFile.junit="$E/new-junit.xml"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 --coverage.reportsDirectory="$E/coverage" --reporter=default --reporter=junit --outputFile.junit="$E/union-junit.xml"
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/eslint src/components/elaborazioni/capacitas-workspace.tsx src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
```

Logs `new.log`, `union.log`, JUnit XML, complete `coverage/coverage-final.json`,
`project-typecheck.log`, `lint.log`, `explicit-test-typecheck.log` and fresh
`original-metrics.json`/`.md` remain external. AST command is the exact two-file
read-only report invocation in the imported author report. Explicit test compiler
program also follows that report: original project options/fileNames plus
tests/setup-vitest.ts and allocated lifecycle-r11 spec; incrementalfalse/noEmit.
Project tsc alone excludes tests and is not substituted for explicit test typing.

## Gate decision and terminal handoff

**APPROVED — ORIGINAL CHARACTERIZATION GATE ONLY.** The exact frozen58case
spec is meaningful behavior protection and independently passes on unchanged
original source alongside338existing cases at genuine complete-file100%.
No blocking review finding or unexplained new failure remains.

Project TypeScript session91352 exit0; scoped runtime/all19spec ESLint session24394
exit0; explicit allocated-spec plus setup/project TypeScript session49663 exit0,
zero diagnostics. Fresh read-only AST exit0 and exact original-object comparison
PASS. All independent commands completed without failed attempts; author harness
attempts remain disclosed above and in frozen author evidence.

Final protected SHA manifest and18original-spec manifest both PASS after replay;
original runtimea409e887, imported test85206faf, imported report13014929 and
frozen readinessc74e515e remain byte-exact. Baseline, exceptions, scanner,
packages/lock, test configuration and existing tests unchanged. Git has only
the two untracked reviewer reports, nothing staged, and the exact authorized
two-file cherry-pick difference from initial HEAD. This review report is not
committed. No other worktree or integration/main changed by this agent.

All replay/compiler/lint process handles are terminal; exclusive focused slot
is released to Coordinator. Stop here. Coordinator may decide the next bounded
runtime phase separately; this approval does not grant source implementation,
report commit, integration/main changes or final certification. Candidate2a2199cc
still has design-only status; actual original principal remains455cognitive.
No broad frontend suite/build/browser/backend/worker, Graphify batch or actual
runtime ratchet was launched. Global campaign remains ACTIVE / INCOMPLETE.
