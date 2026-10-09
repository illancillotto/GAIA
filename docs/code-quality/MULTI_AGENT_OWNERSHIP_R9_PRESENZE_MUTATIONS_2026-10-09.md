# R9 Presenze daily-record mutations — exclusive ownership

Initial integration `a6e5fb7c405861b5f1aad4b55550d35f9d0115b6`, clean;
main/authoritative merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Previous goal turn PROGRESS: R8 reduced actual aggregate cognitive63/cyclomatic19,
removed5findings, independently reviewed/certified4472fullunits/build/E2E54PASS
7oldSKIP/fullpage100%/ratchetmain0. R8 source/review/verifier all terminal.
Global objective unchanged ACTIVE/INCOMPLETE; five>300callables remain.
Main dirty backend/Presenze/Ruolo/documentation concurrent work is not an input.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; reports/code-quality/MULTI_AGENT_COMPLEXITY_CAMPAIGN_2026-10-08.md | Exact design approval, ownership, integration gates | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | ACTIVE |
| R9 author — characterization complete | Presenze UI tests | frontend/tests/unit/presenze-giornaliere-r9.test.tsx | Frozen original characterization8833a587, integrated4e903a83 | GAIA-campaign-20261009-r9-presenze-mutations | refactor/complexity-r9-presenze-mutations | MERGED |
| Coordinator — R9 implementation | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; reports/code-quality/SLICE_R9_PRESENZE_MUTATIONS_2026-10-09.md; domain-docs/presenze/docs/DAILY_RECORD_MUTATIONS_REFACTOR_2026-10-09.md | Reviewed frozen source91f4c50d, waits final certification | GAIA-campaign-20261009-r9-presenze-mutations | refactor/complexity-r9-presenze-mutations | READY_FOR_REVIEW |
| R9 source reviewer — dedicated task | Independent review | reports/code-quality/REVIEW_R9_PRESENZE_MUTATIONS_2026-10-09.md only; source read-only | APPROVED exact source; report-only38c27eff | GAIA-campaign-20261009-r9-presenze-review | review/complexity-r9-presenze-mutations | READY_FOR_REVIEW |
| R9 verifier | Independent final certification | reports/code-quality/VERIFICATION_R9_PRESENZE_MUTATIONS_2026-10-09.md only; source read-only | Frozen-source full-file coverage/fullfrontend/build/browser/ratchet | GAIA-campaign-20261009-r9-presenze-verification | verify/complexity-r9-presenze-mutations | PLANNED |

## Initial assignment: analyze/design only

Target extreme principal399cognitive/352cyclomatic/2020LOC, pageaggregate1109/
1230/file2788LOC. Single responsibility: four daily-record mutation flows
`persistKm`, `persistReperibilita`, `handleSaveEditor`, `handleValidation`.
Inspect repeated request/cache-eviction/apply/error/finally lifecycle and propose
typed domain-specific consolidation with real decision/duplication reduction.
Do not just relocate four functions or introduce megaContext/GenericManager.
Keeping local domain adapter may be safer than a new hook. New file is optional.
No automatic useReducer/hook lifecycle change or generic callback framework.
All functions/helpers including nestedcallbacks count in before/after totals.

Before runtime approval reconstruct exact preflight/token/permission order,
payload construction timing, synchronous failure boundaries, saving/error/success
state transitions, await/rejection behavior, cache token/work_date semantics,
record identity replacement/detail map, overlapping/stale requests and closure
capture. Preserving known races is required, not permission to fix behavior.
KM and reperibilita intentionally differ in authorization/preflight behavior;
editor/validation have distinct permissions, flags and success reset/messages.
Explicit characterization must cover these differences on original source.
INAZ refresh/polling/profile-save/meal-voucher callbacks/identity mapping are
out of scope. Existing `applyUpdatedRecord` and cache helper stay unchanged
unless exact design approval explicitly includes them; no incidental cleanup.

## Gates and stop condition

Author and reviewer independently verify preflight/metrics/invariants first;
design approval then original characterization must precede runtime edits.
100% statement/branch for every complete runtime modified, pertinent tests and
typecheck/lint, real aggregate cognitive/cyclomatic improvement/no laundering,
ratchetmainPASS0, independent source review before sourcefreeze/commit/integration,
then independent fullfrontend/build/browser gates. Stop this responsibility only.
No sharedlib/hooks/UI/layout/core, backend/worker, package/config/tooling/baseline/
threshold/exclusions/ignores modifications. No maincommit/merge/push/PR.
Exact reviewed campaign-only source/report commits and cherry-picks authorized
in phases by Coordinator. Unknown equivalence/concurrent edit/unexplainedfailure
stops slice. Capacitascoverage97.52%FAIL100 and historical30 baseline findings
remain separate. Do not falsely claim global target or principalbelow300.

## Preflight impact evidence

All78existingworktrees inspected for ownedpage: no dirty path.15historical/tmp
worktree handles absent, not pruned/deleted. Dirtymainbackend preserved. Last
ownedpagecommit ecdcc93c is reviewedR8, no current owner other than this registry.
Dedicated frontend Graphify query used for impact; graph not complexity proof.
Durable evidence `~/.cache/gaia-campaign/20261009-r9-presenze/`.

## Resumption — original characterization authorized

The GIS-only request is closed with independently verified evidence; it did
not authorize copying campaign code into the concurrent main checkout. The
global objective remains ACTIVE/INCOMPLETE. The previous turn confirmed the
existing GIS disposition and produced fresh readiness/ratchet evidence, but
made no further complexity reduction; resume the registered R9 responsibility.

Coordinator selects design A: one local named `DailyRecordMutation` type with
required `token`, `request`, `success`, `finish`, `errorMessage`. Preparation
executes synchronously inside the single async persistence helper before its
try; nonasync domain delegates return that exact Promise. Request payloads
execute inside try. Shared cache eviction and response application retain
their original ordering and captured token/response date. No new runtime file.

Author may now add only the registered R9 characterization test, and record
the original results in the assigned slice report. Runtime edits and commits
remain gated on explicit Coordinator approval after original tests and the
independent design oracle. Reviewer may inspect the external prototype and
extend the independent frozen-original oracle, without editing source/tests.
All overlapping microtask/error/preflight semantics must match exactly; count
every nested callback in the complexity comparison. No generic framework,
new state/hook, guard changes, or changes to the protected helpers/callsites.

Plaintext phase authorization:
`~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/CHARACTERIZATION_APPROVAL.md`.

## Measured design checkpoint

Initial wrapper design A rejected before application: page aggregate cognitive
1109→1136, cyclomatic1230→1271. Simple local factory also not selected:
cognitive−4, cyclomatic+15 and aggregate decision count+1. Original runtime
remains byte-identical throughout these external experiments.

Original characterization accepted: 19 new rendered tests, six suites472PASS,
page1033statement/1143branch/294function100%; Coordinator inspected raw counters
and unchanged runtime hash. Reviewer inspected test behaviors independently.
Characterization-only test/report commit is authorized; reviewer replay follows.

Refined bounded design selected in principle: local async-handler factory,
private pure editor payload mapper called inside request try, shared inline and
editor finish callbacks and shared no-op inline success. Independent external
oracle proves101cases,64overlap schedules,73timingcases/365microticks and2352
payload combinations, with protected helpers/hooks/JSX unchanged.

Measured alternative cognitive1109→1093 and principal399→385, aggregate decision
count934→923. Raw cyclomatic1230→1231 is disclosed and compensated by twelve
additional callable base units versus eleven removed aggregate decisions.
FileLOC+22/principalLOC+9 also disclosed; no artificial helper added to force a
number down. Final source must still pass full-file coverage, findings/ratchet,
type/lint, independent review and frozen final gates before integration.
Runtime approval remains a separate explicit phase after original replay.

## Runtime phase authorization and sequential ownership

Original independent replay completed472PASS/1033statement1143branch294function
100%, typecheck/new-test lint exit0, original runtime/test hashes exact. Reviewer
worktree9afd3bc5 clean. Coordinator separately replayed the same original gates.
Both original author and reviewer tasks are terminal at their reported phase.
Runtime ownership transfers sequentially to Coordinator in the same dedicated
source worktree; no concurrent owner or new branch for the same page.

Refined design is authorized locally, with the disclosed raw cyclomatic+1
tradeoff, because cognitive and actual aggregate decisions decrease and the
shared lifecycle/pure mapping are real responsibilities. Named local mutation
type and payload return type are required; no new runtime file/shared path.
Implementation is not acceptance: exact candidate measurements, full coverage,
ratchet, protected-source equivalence, review and final certification remain.
Plaintext approval is `~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/RUNTIME_APPROVAL.md`.

## Actual candidate — review-only handoff

Characterization-only8833a587 integrated4e903a83; integration ratchetPASS0.
Runtime exists only in dedicated source worktree, uncommitted and not integrated.
Frozen candidate SHA256d362df3199fbf65dc4566b56d4029fe72135c910f3e39e691b3e3535516fa940.
Actual six suites472PASS/fullpage1035statement1139branch306function100%, type/lint
exit0 with three unchanged legacy warnings. Metrics1093cognitive/1231cyclomatic,
923aggregate decisions/308callables/2812fileLOC; principal385/341/2023LOC.
One warning removed; zero new runtime finding. Named candidate ratchetPASS0.

An initial unnamed returned async function was assigned to Program<anonymous>
legacy debt and failed five metrics. The introduced lifecycle function now has
explicit semantic name executeDailyRecordMutation; no legacy symbol renamed,
algorithm unchanged, exact Promise/event/timing oracles rerun PASS. Failure and
identity provenance retained. No baseline/tooling/threshold change.

Independent original reviewer task is terminal. Actual-source review transfers
sequentially to a dedicated task using the same clean review worktree9afd3bc5;
only its report is writable. The source candidate remains frozen. No runtime
commit/integration or verifier final certification before review completion.

Dedicated actual-source reviewer task started after this registry:
`01a12041-d4a7-7431-a864-0c3fd0b21c5b`. Approval/input is the durable plaintext
`CANDIDATE_REVIEW_APPROVAL.md`; original reviewer finished before ownership
transfer. One report owner, runtime/test read-only, no duplicate source branch.

## Frozen source and final verifier preparation

Actual-source review38c27eff terminal APPROVED/IMPROVED. Source-only runtime/
report/domain-doc commit91f4c50de44adf433f20decfa31ccf0ba794a5c0 authorized after
review; dedicated source worktree clean, exact runtime/test hashes unchanged.
Coordinator fullfrontend functional suite terminal4491PASS/302files,185.71s;
no failure/skip. Domain graphchunk2/2done,zero semanticfailure,code graph current.
No source integration yet. Full-suite evidence is a new actual result, not R8 reuse.

Dedicated verifier worktree now exists at the planned path and branch, starting
exact91f4c50d; tracked files clean, only ignored frontend dependency symlink.
Verifier owns only its report. Final coverage/fullfrontend/type/lint/smoke/fresh
build/isolated browser/report/ratchet/global-status gates authorized in plaintext
`~/.cache/gaia-campaign/20261009-r9-presenze/coordinator/VERIFY_APPROVAL.md`.
No new hotspot, runtime/test edit, main integration, baseline update or wave close.
